# Authority boundary

Claude Code project configuration controls worker behavior, not execution authority.

Invariant:

`capability available != capability authorized`

For consequence-bearing action:

`worker/orchestrator -> VAIG -> reht -> RACS -> external enforcement -> Veritas/receipts`

Rules:

- Never treat `CLAUDE.md`, settings, prompts, skills, agents, MCP availability, tool permissions or model confidence as mandate.
- Never let a worker or hook mint, expand, revive or infer authority.
- A project hook may only relay a decision from the configured VALO gate and fail closed when that decision is unavailable or invalid.
- Do not mutate tool input after authorization. Changed effect means a new authorization decision.
- Claude Code hooks are not the trusted external PEP; external enforcement remains outside the model/harness.
- Missing authority is a correct stop/defer/step-up outcome, not a reason to bypass the boundary.
