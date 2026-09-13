package governed

import "strings"

// SignalsFromCrabTrap maps CrabTrap's native approval result to transport
// evidence. Only a matched static deny is authoritative enough to stop early.
// Every allow and every LLM result remains advisory to VAIG/REHT/RACS.
func SignalsFromCrabTrap(decision, approvedBy string) TransportSignals {
	result := TransportSignals{
		Adapter:            "crabtrap",
		StaticRuleDecision: "NO_MATCH",
		JudgeDecision:      "UNKNOWN",
	}
	normalizedDecision := strings.ToUpper(decision)
	switch approvedBy {
	case "llm-static-rule":
		if normalizedDecision == "DENY" {
			result.StaticRuleDecision = "DENY"
		} else if normalizedDecision == "ALLOW" {
			result.StaticRuleDecision = "ALLOW"
		}
	case "llm":
		if normalizedDecision == "ALLOW" || normalizedDecision == "DENY" {
			result.JudgeDecision = normalizedDecision
		}
	}
	return result
}
