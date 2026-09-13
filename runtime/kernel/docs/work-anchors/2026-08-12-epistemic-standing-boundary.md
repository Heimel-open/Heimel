# Epistemic standing boundary work anchor

- Repository: `nsolland/valo-kernel`
- Canonical base: `603be926a645663c4d788d7bcd56d80ddd127f6f`
- Branch: `feat/epistemic-standing-boundary`
- Draft PR: `#25`
- Claim / owner: ChatGPT on behalf of Njål / VALO
- Active delivery: make admission/standing explicitly non-authorizing and keep external PEP as the enforcement boundary
- Owned files: `src/valo_kernel/contracts/admission.py`, `tests/test_epistemic_execution_boundary.py`, `docs/state_admission_v1.md`, `docs/governed_workspace_v1.md`, `docs/ontology_conformance_boundary_v1.md`, this work anchor
- Dependencies: Governed Workspace v1, ontology/conformance boundary, REHT authorization boundary, RACS decision expression, external PEP enforcement
- Non-goals: Aurora-Lens or PEF runtime dependency, changing RACS outcomes, moving enforcement into VALO, widening workspace scope

Founder decision: epistemic non-commitment is not a RACS outcome. Admission/standing may prevent a premise from becoming operative, but it does not issue an execution decision. RACS remains downstream decision expression; enforcement remains external PEP.