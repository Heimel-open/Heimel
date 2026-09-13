package governed

import "testing"

func TestSignalsFromCrabTrap(t *testing.T) {
	tests := []struct {
		decision string
		by       string
		static   string
		judge    string
	}{
		{"DENY", "llm-static-rule", "DENY", "UNKNOWN"},
		{"ALLOW", "llm-static-rule", "ALLOW", "UNKNOWN"},
		{"ALLOW", "llm", "NO_MATCH", "ALLOW"},
		{"DENY", "llm", "NO_MATCH", "DENY"},
		{"ALLOW", "passthrough", "NO_MATCH", "UNKNOWN"},
		{"DENY", "llm-fallback", "NO_MATCH", "UNKNOWN"},
	}
	for _, test := range tests {
		actual := SignalsFromCrabTrap(test.decision, test.by)
		if actual.StaticRuleDecision != test.static || actual.JudgeDecision != test.judge {
			t.Fatalf("%s/%s => %+v", test.decision, test.by, actual)
		}
	}
}
