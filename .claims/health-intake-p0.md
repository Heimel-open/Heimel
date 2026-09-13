# Health intake P0.2 claim

- issue: #14
- owner: Codex / health-intake worker
- base: `7e6fd3cd899e2f9f25bd97efb187bd58c757ba88`
- branch: `feat/health-intake-p0`
- owned paths: `src/valo_health_pack/intake.py`, Health Pack exports, `src/valo_operator/health_intake.py`, focused tests
- dependency: merged Health Pack/runtime/parity + existing `valo_operator.frontline.CandidateOperation`
- boundary: Health Pack emits evidence/proposal only; Operator converts proposal to CandidateOperation; no session, permit, authority, or REHT decision is created by intake
