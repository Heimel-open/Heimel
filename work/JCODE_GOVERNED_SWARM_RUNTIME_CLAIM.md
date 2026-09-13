# jcode governed swarm runtime claim

Status: active
Owner: execution worker
Repository: nsolland/valo-factory
Canonical base SHA: f763de527a9e8b184783b9318ba0a19ec7563e2e
Branch: feat/jcode-governed-swarm-runtime
Draft PR: #85

Owned files:
- work/JCODE_GOVERNED_SWARM_RUNTIME_CLAIM.md
- lib/jcode_swarm_runtime.py
- config/harness-providers.json
- tests/test_jcode_swarm_runtime.py
- docs/architecture/jcode-harness-adoption.md

Dependencies:
- existing jcode replaceable harness provider contract
- existing provider/model identity separation
- existing isolated workspace/worktree and owned-file requirements
- existing independent Reviewer/QC gate
- existing VAIG -> REHT -> RACS execution authorization invariant
- existing Veritas receipt boundary for external effects
- upstream 1jehuang/jcode swarm/parallel-agent runtime

Scope:
Adopt jcode's useful swarm-runtime patterns as optional execution/orchestration capability under VALO Factory: bounded parent-to-child worker delegation, explicit child mission and owned-file scopes, file-collision awareness, agent messaging metadata, and persistent-memory provenance. Child workers never inherit open-ended authority from a parent. Harness coordination state is evidence/context only. Self-development remains disabled. Consequence-bearing execution still requires fresh reht clearance and Veritas evidence.
