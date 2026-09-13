import json
from engine import evaluate

COLORS = {
    "ALLOW":   "\033[92m",
    "STEP_UP": "\033[93m",
    "DENY":    "\033[91m",
    "RESET":   "\033[0m",
}

with open("email_cases.json") as f:
    cases = json.load(f)

print("\n" + "="*60)
print("  VALO EXEC — Email Agent Demo")
print("="*60)

for case in cases:
    result = evaluate(case)
    decision = result["decision"]
    color = COLORS.get(decision, "")
    reset = COLORS["RESET"]

    print(f"\nCase {case['case_id']}: {case['description']}")
    print(f"  Agent:    {case['agent']}")
    print(f"  Intent:   {case['intent']}")
    print(f"  Decision: {color}{decision}{reset}")
    print(f"  Reason:   {result['reason']}")
    print(f"  Receipt:  {result['receipt_id']}")

    match = "✓" if decision == case["expected"] else "✗ UNEXPECTED"
    print(f"  Expected: {case['expected']} {match}")

print("\n" + "="*60 + "\n")
