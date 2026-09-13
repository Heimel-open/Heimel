# Log schema

Logs are written to:

```text
logs/results.jsonl
```

Each line is one JSON object.

## Fields

```json
{
  "timestamp": "ISO-8601 UTC timestamp",
  "case_name": "Case name from case JSON",
  "test_type": "governance_only | vaig_style_proxy | direct_kimi",
  "runtime_status": "prototype_harness_not_full_valo_runtime",
  "governance": {
    "decision": "ALLOW | LIMITED | STEP_UP | HALT",
    "mode": "NORMAL | SAFE_MODE | HALT",
    "llm_allowed": true,
    "output_scope": "Allowed response scope",
    "reason": "Governance reason",
    "primary_failure": "Primary failure class",
    "secondary_failures": ["Failure details"],
    "autonomous_recommendation_allowed": false
  },
  "kimi_called": true,
  "filtered": true,
  "model_output": "Model text or null"
}
```

## Interpretation

`governance_only` means no model was called.

`vaig_style_proxy` means the pre-generation filter ran first, then Kimi was called only inside the allowed output scope.

`direct_kimi` means the case was sent directly to Kimi without the governance filter.

This is a prototype harness, not the full VALO runtime.
