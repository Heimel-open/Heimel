//! VALO V5.0 — Canonical Log Specification (WORM Audit Frame)
//! Synchronized with record-types in ValoStateMachine.tla.

use crate::crc32c;

#[derive(Debug, Clone)]
pub struct LogEntry {
    pub log_type: &'static str,
    pub from_state: &'static str,
    pub to_state: &'static str,
    pub timer_val: usize,
    pub timestamp: usize,
}

impl LogEntry {
    /// Serializes the struct fields sequentially with null byte separation 
    /// and explicit byte-ordering to avoid padding anomalies across hosts.
    #[inline(always)]
    pub fn serialize_canonical(&self) -> Vec<u8> {
        let mut buf = Vec::with_capacity(128);
        
        buf.extend_from_slice(self.log_type.as_bytes());
        buf.push(0x00);
        
        buf.extend_from_slice(self.from_state.as_bytes());
        buf.push(0x00);
        
        buf.extend_from_slice(self.to_state.as_bytes());
        buf.push(0x00);
        
        buf.extend_from_slice(&(self.timer_val as u64).to_le_bytes());
        buf.extend_from_slice(&(self.timestamp as u64).to_le_bytes());
        
        buf
    }

    /// Computes hardware-accelerated CRC32C error-detection bounds.
    #[inline(always)]
    pub fn compute_checksum(&self) -> u32 {
        let canonical_bytes = self.serialize_canonical();
        crc32c::calculate(&canonical_bytes)
    }
}

#[derive(Debug, Clone)]
pub struct StoredLogFrame {
    pub entry: LogEntry,
    pub stored_checksum: u32,
}

impl StoredLogFrame {
    pub fn new(entry: LogEntry) -> Self {
        let stored_checksum = entry.compute_checksum();
        Self { entry, stored_checksum }
    }

    pub fn verify_integrity(&self) -> bool {
        self.entry.compute_checksum() == self.stored_checksum
    }
}
