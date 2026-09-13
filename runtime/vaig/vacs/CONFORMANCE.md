# ACS / VACS Conformance v0.1

ACS-compatible means: valid ACS v0.1 packet, typed evidence, bounded risk/policy fields, one of six primitive decisions, and ACS receipt output.

VACS-compatible means ACS-compatible plus VALO authority profile:

- `vacs_profile == "valo-authority-v0.1"`
- `principal.who` matches `agent_id`
- `principal.whom` is present
- `principal.authority_source` is present
- `policy.policy_id` is present
- `policy.policy_hash` starts with `sha256:`
- signoff is validated when policy requires it
- revoked signoff is rejected
- target is inside `boundary.resources`
- action is outside `boundary.forbidden_domains`
- execution handoff is built only for `decision == ALLOW`
- receipt path exists before handoff

Primitive decisions remain exactly:

- ALLOW
- MODIFY
- DEFER
- DENY
- STEP_UP
- HALT

`DEGRADE` is not ACS/VACS-compatible as a primitive.

Execution-compatible means VACS-compatible plus adapter handoff. STEP_UP, DEFER, DENY and HALT must not reach an execution adapter. MODIFY must be revalidated into ALLOW before execution.
