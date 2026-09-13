use crate::context_engine::DistrustLevel;

#[derive(Clone, Copy)]
pub struct SourceDistrust {
    pub score: u8,
    pub failure_count: u32,
}

pub struct DistrustManager {
    pub global_level: DistrustLevel,
    pub sources: [Option<SourceDistrust>; 16],
}

fn score_from_failures(count: u32) -> u8 {
    match count {
        0 => 0,
        1..=2 => 1,
        3..=5 => 2,
        6..=9 => 3,
        _ => 4,
    }
}

fn level_from_score(score: u8) -> DistrustLevel {
    match score {
        0 => DistrustLevel::L0Trusted,
        1 => DistrustLevel::L1Monitor,
        2 => DistrustLevel::L2Caution,
        3 => DistrustLevel::L3Suspicious,
        _ => DistrustLevel::L4Untrusted,
    }
}

impl DistrustManager {
    pub fn new() -> Self {
        Self {
            global_level: DistrustLevel::L0Trusted,
            sources: [const { None }; 16],
        }
    }

    pub fn update_score(&mut self, index: usize, failed: bool) {
        if index < 16 {
            let entry = if let Some(mut src) = self.sources[index] {
                if failed {
                    src.failure_count += 1;
                }
                src.score = score_from_failures(src.failure_count);
                src
            } else {
                let failure_count = if failed { 1 } else { 0 };
                SourceDistrust {
                    score: score_from_failures(failure_count),
                    failure_count,
                }
            };
            self.sources[index] = Some(entry);
            self.recompute_global_level();
        }
    }

    fn recompute_global_level(&mut self) {
        let max_score = self.sources.iter()
            .filter_map(|s| s.map(|src| src.score))
            .max()
            .unwrap_or(0);
        self.global_level = level_from_score(max_score);
    }

    pub fn max_spread_for_level(&self) -> f64 {
        match self.global_level {
            DistrustLevel::L0Trusted    => 5.0,
            DistrustLevel::L1Monitor    => 4.0,
            DistrustLevel::L2Caution    => 3.0,
            DistrustLevel::L3Suspicious => 2.0,
            DistrustLevel::L4Untrusted  => -1.0, // sentinel: immediate Halt regardless of spread
        }
    }

    /// Minimum acceptable token confidence for VAIG mode.
    /// L4Untrusted returns >1.0 to block all tokens unconditionally.
    pub fn confidence_floor_for_level(&self) -> f64 {
        match self.global_level {
            DistrustLevel::L0Trusted    => 0.05,
            DistrustLevel::L1Monitor    => 0.10,
            DistrustLevel::L2Caution    => 0.20,
            DistrustLevel::L3Suspicious => 0.35,
            DistrustLevel::L4Untrusted  => 1.01,
        }
    }
}
