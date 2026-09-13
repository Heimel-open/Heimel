# Serena semantic adapter claim

Status: active
Owner: execution worker
Repository: nsolland/valo-factory
Canonical base SHA: 8774dd444660fa2f883c100516a46f975649edac
Branch: feat/serena-semantic-adapter
Draft PR: #96

Owned files:
- work/SERENA_SEMANTIC_ADAPTER_CLAIM.md
- bin/valo-serena
- config/serena_adapter.json
- docs/serena-semantic-adapter.md
- tests/test_serena_adapter_contract.py

Dependencies:
- upstream reference: oraios/serena
- CubeSandbox or equivalent isolated execution substrate for consequence-capable Serena operation
- existing Factory governed workspace and worker contracts
- existing independent QC/conformance path
- existing REHT/RACS/PEP execution boundary and receipts

Scope:
Adopt Serena as an optional, replaceable semantic code-intelligence MCP adapter for coding workers. Serena may provide symbol-aware retrieval, references, refactoring and diagnostics inside a bounded workspace. Serena memory is non-authoritative context/cache only. Serena must not hold production credentials or create a direct effect path; consequence-bearing operation runs inside the sandbox and all external effects remain governed by the existing execution boundary.
