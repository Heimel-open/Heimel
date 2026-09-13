//! VALO V5.0 — L3 Context Engine: Simulation Process
//! Reads failure signals from stdin, emits max_spread to stdout.
//!
//! Input line format:  "<source_index> <0|1>"  (0=ok, 1=failed)
//! Output line format: "<max_spread>"

use l3_context::distrust::DistrustManager;
use std::io::{self, BufRead, Write};

fn main() {
    let mut mgr = DistrustManager::new();
    let stdin = io::stdin();
    let stdout = io::stdout();

    for line in stdin.lock().lines() {
        let line = match line {
            Ok(l) => l,
            Err(_) => break,
        };
        let parts: Vec<&str> = line.trim().split_whitespace().collect();
        if parts.len() == 2 {
            if let (Ok(idx), Ok(failed)) = (parts[0].parse::<usize>(), parts[1].parse::<u8>()) {
                mgr.update_score(idx, failed != 0);
            }
        }
        let spread = mgr.max_spread_for_level();
        let mut out = stdout.lock();
        writeln!(out, "{spread}").ok();
        out.flush().ok();
    }
}
