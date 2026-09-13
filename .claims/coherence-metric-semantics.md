# Claim — Coherence metric semantics

Owner: ChatGPT
Status: complete
Canonical base: `77ef58133c96a6365a5aa77d60f06817ace79fab`
Branch: `feat/coherence-metric-semantics`

Primary objective:
- Make preregistered VAIG metrics operational rather than documentary: threshold direction and observed value must be explicit, digest-bound and deterministically evaluated.

Invariants:
- VAIG never infers whether a metric is higher-is-better or lower-is-better.
- Missing observation or comparison remains OPEN.
- A known threshold breach is FAIL.
- Non-finite metric values are invalid input.
- High-stakes metric threshold sources require registered lineage.
- Replay uses the same metric semantics and cannot launder a threshold breach to PASS.
- Evaluation remains non-authoritative; REHT remains the execution-authorization boundary.

Validation coverage added:
- GTE/LTE threshold direction
- missing observation/comparison remains OPEN
- threshold breach becomes FAIL
- non-finite metrics rejected
- high-stakes source lineage required
- HTTP transport preserves comparison
- second-operator replay preserves threshold breach

Hosted GitHub Actions may still encounter the repository's existing startup failure before jobs; no hosted test success is claimed here.
