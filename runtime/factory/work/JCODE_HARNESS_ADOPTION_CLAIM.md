# jcode harness adoption claim

Status: active
Owner: execution worker
Repository: nsolland/valo-factory
Canonical base SHA: 301c2c76c9000b53581b85f7a93fb7f5e400b3ce
Branch: feat/jcode-harness-adoption
Draft PR: #73

Owned files:
- work/JCODE_HARNESS_ADOPTION_CLAIM.md
- lib/harness_provider_adapters.py
- lib/workflow_harness.py
- config/harness-providers.json
- tests/test_jcode_harness_adapter.py
- docs/architecture/jcode-harness-adoption.md

Dependencies:
- existing provider-neutral Factory workflow harness
- existing model/provider entitlement identities
- existing REHT final authorization invariant
- upstream reference: 1jehuang/jcode@dd8755f7e71f0673911d481b625b8a559c81a8b6 (v0.71.1)

Scope:
Adopt jcode as an optional, replaceable coding-agent harness, separate from model/provider identity. Bind harness identity to Factory workflow invocations. Preserve native provider adapters. Do not import jcode safety/permission semantics as VALO authority. Do not enable self-development or autonomous mutation of governance/control code. Fail closed for jcode read-only mode until an upstream read-only wrapper contract is documented and conformance-tested.
