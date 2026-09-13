# Work anchor — Reliability Conformance Pack v1

- Repository: `nsolland/valo-kernel`
- Canonical base SHA: `0a8205f8a3c169eede7b7d8e50c4d66a950d5c32`
- Branch: `feat/reliability-conformance-pack-v1`
- Draft PR: `#61`
- Claim / owner: ChatGPT on behalf of Njål / VALO
- Active delivery: add a general deterministic reliability-conformance layer,
  with healthcare as the first domain profile
- Owned files: `src/valo_kernel/reliability.py`,
  `tests/test_reliability_conformance.py`,
  `docs/reliability_conformance_pack_v1.md`, this work anchor
- Dependencies: Pydantic, existing Kernel-before-REHT boundary, downstream RACS,
  Gateway and Veritas contracts
- Non-goals: manual healthcare evaluation service, certification, model-quality
  scoring, authority creation, external framework dependency
