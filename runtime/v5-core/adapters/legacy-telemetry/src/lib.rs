#![forbid(unsafe_code)]

use ai_pls_core::{Clearance, ExecutionSignal};

/// Legacy compatibility input for the old telemetry surface.
#[derive(Debug, Clone, Copy, PartialEq)]
pub struct LegacyClearanceInputs {
    pub ai_confidence: f64,
    pub c0_threshold: f64,
    pub syntax_valid: bool,
    pub latency_ok: bool,
}

#[derive(Debug, Clone, Copy, PartialEq)]
pub struct LegacyClearanceThresholds {
    pub low_multiplier: f64,
    pub high_multiplier: f64,
}

impl Default for LegacyClearanceThresholds {
    fn default() -> Self {
        Self {
            low_multiplier: 0.42,
            high_multiplier: 1.06,
        }
    }
}

/// Temporary migration adapter only.
///
/// This preserves old telemetry behavior while keeping AI-specific evaluation
/// outside the new enforcement core.
pub fn translate_legacy_clearance_inputs(
    telemetry: LegacyClearanceInputs,
    thresholds: LegacyClearanceThresholds,
) -> ExecutionSignal {
    let finite = telemetry.ai_confidence.is_finite()
        && telemetry.c0_threshold.is_finite()
        && telemetry.c0_threshold > 0.0;

    if !finite {
        return ExecutionSignal {
            clearance: Clearance::Invalid,
            envelope_integrity_valid: false,
            ..ExecutionSignal::clear()
        };
    }

    let low = thresholds.low_multiplier * telemetry.c0_threshold;
    let high = thresholds.high_multiplier * telemetry.c0_threshold;
    let coherence_valid = telemetry.ai_confidence >= low && telemetry.ai_confidence <= high;

    ExecutionSignal {
        clearance: if coherence_valid && telemetry.syntax_valid && telemetry.latency_ok {
            Clearance::Clear
        } else {
            Clearance::Uncertain
        },
        envelope_integrity_valid: true,
        receipt_valid: true,
        context_valid: true,
        not_expired: true,
        replay_free: true,
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn legacy_valid_input_maps_to_clear() {
        let signal = translate_legacy_clearance_inputs(
            LegacyClearanceInputs {
                ai_confidence: 0.5,
                c0_threshold: 1.0,
                syntax_valid: true,
                latency_ok: true,
            },
            LegacyClearanceThresholds::default(),
        );
        assert_eq!(signal.clearance, Clearance::Clear);
    }

    #[test]
    fn legacy_breach_maps_to_uncertain() {
        let signal = translate_legacy_clearance_inputs(
            LegacyClearanceInputs {
                ai_confidence: 100.0,
                c0_threshold: 1.0,
                syntax_valid: true,
                latency_ok: true,
            },
            LegacyClearanceThresholds::default(),
        );
        assert_eq!(signal.clearance, Clearance::Uncertain);
    }
}
