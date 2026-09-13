import json
from engine import evaluate

COLORS = {
    "ALLOW":   "\033[92m",
    "STEP_UP": "\033[93m",
    "DENY":    "\033[91m",
    "HALT":    "\033[95m",
    "RESET":   "\033[0m",
}

with open("email_safety_cases.json") as f:
    cases = json.load(f)

print("\n" + "="*60)
print("  VALO EXEC — Email Safety Demo")
print("  Stop unsafe AI-generated email before send.")
print("="*60)

for case in cases:
    result = evaluate(case)
    decision = result["decision"]
    color = COLORS.get(decision, "")
    reset = COLORS["RESET"]

    print(f"\nCase {case['case_id']}: {case['description']}")
    print(f"  Decision: {color}{decision}{reset}")
    print(f"  Reason:   {result['reason']}")
    print(f"  Next:     {result['next_action']}")
    print(f"  Receipt:  {result['receipt_id']}")

    match = "✓" if decision == case["expected"] else f"✗ (expected {case['expected']})"
    print(f"  Check:    {match}")

print("\n" + "="*60 + "\n")
