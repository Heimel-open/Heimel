//! VALO V5.0 — Overgangslogikk og telemetri-evaluering
//! Formelt synkronisert med ValoStateMachine.tla og renset for gjerdestolpefeil.
//!
//! # C0 Multipliers
//!
//! C0/α/τ are configured via environment variables (Concept #252):
//! - `VALO_C0_LOW_MULTIPLIER`  — default `"0.42"`
//! - `VALO_C0_HIGH_MULTIPLIER` — default `"1.06"`
//!
//! Read once per process lifetime via `std::sync::OnceLock` caching.
//! This is deterministic — env vars are snapshotted at first read.

use crate::{ValoGuardrail, ValoState};
#[cfg(not(kani))]
use std::sync::OnceLock;

/// Read the low C0 multiplier from `VALO_C0_LOW_MULTIPLIER`.
/// Falls back to `0.42` if unset. Cached via OnceLock.
#[cfg(not(kani))]
fn get_c0_low_multiplier() -> f64 {
    static C0_LOW: OnceLock<f64> = OnceLock::new();
    *C0_LOW.get_or_init(|| {
        std::env::var("VALO_C0_LOW_MULTIPLIER")
            .unwrap_or_else(|_| "0.42".to_string())
            .parse()
            .expect("VALO_C0_LOW_MULTIPLIER must parse as f64")
    })
}

// The safety harness verifies the transition relation, not process-environment
// parsing. Keeping that boundary concrete prevents Kani from symbolically
// expanding std::env/string internals while preserving the production path.
#[cfg(kani)]
fn get_c0_low_multiplier() -> f64 {
    0.42
}

/// Read the high C0 multiplier from `VALO_C0_HIGH_MULTIPLIER`.
/// Falls back to `1.06` if unset. Cached via OnceLock.
#[cfg(not(kani))]
fn get_c0_high_multiplier() -> f64 {
    static C0_HIGH: OnceLock<f64> = OnceLock::new();
    *C0_HIGH.get_or_init(|| {
        std::env::var("VALO_C0_HIGH_MULTIPLIER")
            .unwrap_or_else(|_| "1.06".to_string())
            .parse()
            .expect("VALO_C0_HIGH_MULTIPLIER must parse as f64")
    })
}
#[cfg(kani)]
fn get_c0_high_multiplier() -> f64 {
    1.06
}

impl ValoGuardrail {
    /// Evaluering per inferens-tick.
    /// Tar inn uavhengige, ikke-ML-baserte telemetrisignaler for å nøytralisere hallusinasjoner.
    pub fn evaluate_tick(
        &mut self,
        ai_confidence: f64,
        c0_threshold: f64,
        is_syntax_valid: bool,
        latency_ok: bool,
    ) {
        // Sjekk om loggen ble full i forrige skritt (TLA+ Gren 4)
        if self.audit_log.len() >= self.max_log_size && self.state != ValoState::LogFullHalt {
            self.state = ValoState::LogFullHalt;
            return;
        }

        self.clock += 1;

        match self.state {
            ValoState::Active => {
                // Matematisk evaluering av den konfidensielle sikkerhetssonen (Artikkel 15)
                // C0 multipliers are env-driven per canonical rule (Concept #252).
                let c0_low = get_c0_low_multiplier();
                let c0_high = get_c0_high_multiplier();
                let is_coherence_valid = ai_confidence >= (c0_low * c0_threshold)
                    && ai_confidence <= (c0_high * c0_threshold);

                if !is_coherence_valid || !is_syntax_valid || !latency_ok {
                    self.state = ValoState::Degraded;
                    self.timer = self.max_degraded_time;
                    self.append_log("EnterDegraded", "Active", "Degraded", self.timer);
                } else if self.context_age >= self.max_context_age - 1 {
                    // LØSNING PÅ GJERDESTOLPEFEIL: Hvis neste skritt vil nå grensen,
                    // tvinger vi frem umiddelbar DirectHalt for å beskytte SafetyInvariant (< MaxContextAge)
                    self.state = ValoState::Halt;
                    self.timer = 0;
                    self.append_log("DirectHalt", "Active", "Halt", 0);
                } else {
                    // Siden vi sjekket (MaxContextAge - 1) over, er det matematisk umulig
                    // for denne inkrementeringen å bryte den strenge ulikheten i TLA+
                    self.context_age += 1;
                    self.append_log("ActiveUpdate", "Active", "Active", 0);
                }
            }
            ValoState::Degraded => {
                if self.timer > 0 {
                    self.timer -= 1;
                    self.append_log("DegradedTick", "Degraded", "Degraded", self.timer);
                } else {
                    self.state = ValoState::Halt;
                    self.timer = 0;
                    self.append_log("TimeoutHalt", "Degraded", "Halt", 0);
                }
            }
            ValoState::Halt => {
                // Systemet er låst i nødmodus. Venter på ekstern autorisert SystemReset.
            }
            ValoState::LogFullHalt => {
                // Terminal tilstand. Alt minne og eksekvering er bunnfrosset.
            }
        }
    }   // end fn evaluate_tick
}       // end impl ValoGuardrail
