//! VALO V5.0 — Hardened Execution Server with full error logging and resilience.

#[path = "racs_permit.rs"]
pub mod racs_permit;

#[path = "racs_cancellation.rs"]
pub mod racs_cancellation;

#[path = "racs_continuity.rs"]
pub mod racs_continuity;

impl Copy for racs_continuity::ExecutionContinuityState {}

#[cfg(test)]
impl PartialEq for racs_permit::SignedArtifact {
    fn eq(&self, other: &Self) -> bool {
        self.artifact_id == other.artifact_id && self.payload_digest == other.payload_digest
    }
}

use crate::{ValoGuardrail, ValoState};
use hmac::{Hmac, Mac};
use racs_continuity::CoreContinuityDirective;
use sha2::Sha256;
use std::env;
use std::fs;
use std::io::{Read, Write};
use std::net::TcpListener;
use std::os::unix::net::UnixListener;
use std::thread::sleep;
use std::time::Duration;

type HmacSha256 = Hmac<Sha256>;

#[repr(C, packed)]
#[derive(Debug, Clone, Copy)]
pub struct InferenceTelemetryPacket {
    pub ai_confidence_scaled: u64,
    pub c0_threshold_scaled: u64,
    pub syntax_valid_flag: u8,
    pub latency_ok_flag: u8,
}

pub struct ValoExecutionServer {
    pub guardrail: ValoGuardrail,
    pub is_running: bool,
    pub hmac_signature_vault: Vec<[u8; 32]>,
    hmac_key: Vec<u8>,
}

impl ValoExecutionServer {
    pub fn new(max_degraded: usize, max_context: usize, max_log: usize) -> Self {
        let hmac_key = env::var("VALO_HSM_KEY")
            .map(|v| v.into_bytes())
            .unwrap_or_else(|_| {
                if cfg!(feature = "simulation") {
                    eprintln!("[WARN] VALO_HSM_KEY not set; using test-only key (SIMULATION ONLY)");
                    b"test-key-simulation-only-not-for-production".to_vec()
                } else {
                    panic!("VALO_HSM_KEY env var required for production builds")
                }
            });
        Self {
            guardrail: ValoGuardrail::new(max_degraded, max_context, max_log),
            is_running: true,
            hmac_signature_vault: Vec::with_capacity(max_log),
            hmac_key,
        }
    }

    pub fn process_incoming_telemetry(&mut self, raw_bytes: &[u8]) -> u8 {
        let expected_size = std::mem::size_of::<InferenceTelemetryPacket>();
        if raw_bytes.len() != expected_size {
            eprintln!(
                "[ERROR] Invalid packet size: got {}, expected {}",
                raw_bytes.len(),
                expected_size
            );
            self.guardrail.trigger_emergency_halt("INVALID_PACKET_SIZE");
            self.is_running = false;
            return ValoState::Halt as u8;
        }

        let packet: InferenceTelemetryPacket = unsafe {
            std::ptr::read_unaligned(raw_bytes.as_ptr() as *const InferenceTelemetryPacket)
        };

        let raw_confidence = u64::from_be(packet.ai_confidence_scaled);
        let raw_c0 = u64::from_be(packet.c0_threshold_scaled);

        if raw_confidence > 9_007_199_254_740_992 || raw_c0 > 9_007_199_254_740_992 {
            eprintln!(
                "[ERROR] Precision overflow: confidence={}, c0={}",
                raw_confidence, raw_c0
            );
            self.guardrail.trigger_emergency_halt("PRECISION_OVERFLOW");
            self.is_running = false;
            return ValoState::Halt as u8;
        }

        let ai_confidence = raw_confidence as f64 / 1_000_000.0;
        let c0_threshold = raw_c0 as f64 / 1_000_000.0;

        if packet.syntax_valid_flag > 1 || packet.latency_ok_flag > 1 {
            eprintln!(
                "[ERROR] Invalid flags: syntax={}, latency={}",
                packet.syntax_valid_flag, packet.latency_ok_flag
            );
            let old_log_count = self.guardrail.audit_log.len();
            self.guardrail
                .trigger_emergency_halt("INVALID_TELEMETRY_FLAGS");
            self.is_running = false;
            self.sign_latest_log_if_appended(old_log_count);
            return ValoState::Halt as u8;
        }

        let is_syntax_valid = packet.syntax_valid_flag == 1;
        let is_latency_ok = packet.latency_ok_flag == 1;

        let old_log_count = self.guardrail.audit_log.len();
        self.guardrail
            .evaluate_tick(ai_confidence, c0_threshold, is_syntax_valid, is_latency_ok);
        self.sign_latest_log_if_appended(old_log_count);

        let current = self.guardrail.current_state();
        if current == ValoState::Halt || current == ValoState::LogFullHalt {
            self.is_running = false;
        }
        eprintln!("[INFO] Processed packet → state {:?}", current);
        current as u8
    }

    /// Apply a directive already verified and durably sequenced by the RACS
    /// continuity ingress. This method does not verify signatures or bindings.
    ///
    /// Per-execution STOP and bounds state are enforced by
    /// `DurableContinuityRegistry`. The global guardrail only receives the
    /// bounded effects it owns: audit, safe-mode escalation and HALT.
    /// No directive can reset or resume a halted/degraded guardrail.
    pub fn apply_racs_continuity_directive(
        &mut self,
        directive: &CoreContinuityDirective,
    ) -> ValoState {
        let old_log_count = self.guardrail.audit_log.len();
        match directive {
            CoreContinuityDirective::Continue => {
                self.guardrail.append_log(
                    "RacsContinuityContinue",
                    "Any",
                    "Any",
                    self.guardrail.timer,
                );
            }
            CoreContinuityDirective::ApplyNarrowedBounds { .. } => {
                self.guardrail
                    .append_log("RacsBoundsNarrowed", "Any", "Any", self.guardrail.timer);
            }
            CoreContinuityDirective::Pause => {
                if self.guardrail.state == ValoState::Active {
                    self.guardrail.state = ValoState::Degraded;
                    self.guardrail.timer = 0;
                    self.guardrail
                        .append_log("RacsContinuityPause", "Active", "Degraded", 0);
                } else {
                    self.guardrail.append_log(
                        "RacsContinuityPause",
                        "Any",
                        "Any",
                        self.guardrail.timer,
                    );
                }
            }
            CoreContinuityDirective::Stop => {
                self.guardrail
                    .append_log("RacsExecutionStop", "Any", "Any", self.guardrail.timer);
            }
            CoreContinuityDirective::Halt => {
                self.guardrail
                    .trigger_emergency_halt("RACS_CONTINUITY_HALT");
                self.is_running = false;
            }
        }
        self.sign_latest_log_if_appended(old_log_count);
        self.guardrail.current_state()
    }

    fn sign_latest_log_if_appended(&mut self, old_log_count: usize) {
        if self.guardrail.audit_log.len() > old_log_count {
            if let Some(entry) = self.guardrail.audit_log.last() {
                let canonical = entry.serialize_canonical();
                let signature = self.generate_hmac_signature(&canonical);
                if self.hmac_signature_vault.len() < self.guardrail.max_log_size {
                    self.hmac_signature_vault.push(signature);
                }
            }
        }
    }

    fn generate_hmac_signature(&self, data: &[u8]) -> [u8; 32] {
        let mut mac = HmacSha256::new_from_slice(&self.hmac_key).expect("HMAC init failed");
        mac.update(data);
        mac.finalize().into_bytes().into()
    }
}

pub fn run_tcp(addr: &str) -> ! {
    let listener =
        TcpListener::bind(addr).unwrap_or_else(|e| panic!("Failed to bind TCP {}: {}", addr, e));
    eprintln!("[VALO] TCP server listening on {}", addr);
    let mut server = ValoExecutionServer::new(5, 3, 5);
    let pkt_size = std::mem::size_of::<InferenceTelemetryPacket>();

    while server.is_running {
        match listener.accept() {
            Ok((mut stream, peer)) => {
                eprintln!("[VALO] New connection from {}", peer);
                let mut buffer = vec![0u8; pkt_size];
                while server.is_running {
                    match stream.read_exact(&mut buffer) {
                        Ok(_) => {
                            let state = server.process_incoming_telemetry(&buffer);
                            let response = [state, 0, 0, 0];
                            if let Err(e) = stream.write_all(&response) {
                                eprintln!("[VALO] Write error to {}: {}", peer, e);
                                break;
                            }
                            eprintln!("[VALO] Sent response byte {}", state);
                            if state >= 2 {
                                eprintln!(
                                    "[VALO] Terminal state reached, closing connection to {}",
                                    peer
                                );
                                break;
                            }
                        }
                        Err(e) => {
                            eprintln!("[VALO] Read error from {}: {}", peer, e);
                            break;
                        }
                    }
                }
            }
            Err(e) => {
                eprintln!("[VALO] Accept error: {}", e);
                sleep(Duration::from_millis(100));
            }
        }
    }
    eprintln!("[VALO] Server is no longer running – this should not happen. Exiting.");
    std::process::exit(0);
}

pub fn run_uds(path: &str) -> ! {
    let _ = fs::remove_file(path);
    let listener =
        UnixListener::bind(path).unwrap_or_else(|e| panic!("Failed to bind UDS {}: {}", path, e));
    eprintln!("[VALO] UDS server listening on {}", path);
    let mut server = ValoExecutionServer::new(5, 3, 5);
    let pkt_size = std::mem::size_of::<InferenceTelemetryPacket>();

    while server.is_running {
        match listener.accept() {
            Ok((mut stream, _)) => {
                eprintln!("[VALO] New UDS connection");
                let mut buffer = vec![0u8; pkt_size];
                while server.is_running {
                    match stream.read_exact(&mut buffer) {
                        Ok(_) => {
                            let state = server.process_incoming_telemetry(&buffer);
                            let response = [state, 0, 0, 0];
                            if let Err(e) = stream.write_all(&response) {
                                eprintln!("[VALO] UDS write error: {}", e);
                                break;
                            }
                            if state >= 2 {
                                break;
                            }
                        }
                        Err(e) => {
                            eprintln!("[VALO] UDS read error: {}", e);
                            break;
                        }
                    }
                }
            }
            Err(e) => {
                eprintln!("[VALO] UDS accept error: {}", e);
                sleep(Duration::from_millis(100));
            }
        }
    }
    let _ = fs::remove_file(path);
    eprintln!("[VALO] UDS server exiting.");
    std::process::exit(0);
}

#[cfg(test)]
mod telemetry_tests {
    use super::*;

    fn packet(confidence: u64, c0: u64, syntax: u8, latency: u8) -> Vec<u8> {
        let mut bytes = Vec::with_capacity(std::mem::size_of::<InferenceTelemetryPacket>());
        bytes.extend_from_slice(&confidence.to_be_bytes());
        bytes.extend_from_slice(&c0.to_be_bytes());
        bytes.push(syntax);
        bytes.push(latency);
        bytes
    }

    fn assert_halt(raw: &[u8]) {
        let mut server = ValoExecutionServer::new(5, 3, 20);
        let audit_before = server.guardrail.audit_log.len();
        let response = server.process_incoming_telemetry(raw);
        assert_eq!(response, ValoState::Halt as u8);
        assert_eq!(server.guardrail.current_state(), ValoState::Halt);
        assert!(!server.is_running);
        assert!(server.guardrail.audit_log.len() > audit_before);
    }

    #[test]
    fn syntax_flag_above_one_halts_internally_and_externally() {
        assert_halt(&packet(500_000, 500_000, 2, 1));
    }

    #[test]
    fn latency_flag_above_one_halts_internally_and_externally() {
        assert_halt(&packet(500_000, 500_000, 1, 2));
    }

    #[test]
    fn invalid_packet_size_halts_internally_and_externally() {
        assert_halt(&[0; 3]);
    }

    #[test]
    fn precision_overflow_halts_internally_and_externally() {
        assert_halt(&packet(9_007_199_254_740_993, 500_000, 1, 1));
    }
}
