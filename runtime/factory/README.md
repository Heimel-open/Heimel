# VALO Factory — Factory OS Runtime

Policy-driven orchestration runtime for the VALO / REHT factory ecosystem. Human-in-command; not a transport layer and not an authority source.

## Canonical boundary

- `nsolland/Index` is the architecture and truth plane.
- `nsolland/nsolland-valo-control` is the command and policy plane.
- `nsolland/valo-factory` is the Factory OS orchestration runtime.
- VAIG, REHT, VALO Core and RACS govern consequence-bearing execution.

Factory OS reads policy and commands from `nsolland-valo-control`, creates bounded missions, assigns workers, brokers scoped access, runs QC and emits status and receipts. It may not infer authority from the command channel or from possession of credentials.

## Prinsipp

Agentar arbeider autonomt innan førehandsgodkjente, testbare, avgrensa rammer.
Berre authority-endringar, destruktive handlingar, uklare konfliktar og
policyavvik krev menneskeleg avgjerd. Du er exception authority, ikkje
manuell godkjennar.

## Komponentar (~/.valo/bin/)
| Verktøy | Rolle | Skriv? |
|---|---|---|
| `valoctl` | Global modus-token (NORMAL/MAINTENANCE/INCIDENT_HOLD) | mode + state.json |
| `valo-git` | Agent-safe git-shim; blokkerer primærrepo-write + mode-fence | (via git) |
| `valo-run` | Opprettar isolert worktree + run-metadata (runs.db) | runs.db |
| `valo-claim` | Leased claims (claims.db + GH label/assignee/comment) | claims.db + GH |
| `valo-orchestrator` | ÉIN kontrollprosess; tilstandsmaskina | orchestrator.db |
| `valo-qc` | QC-agent; køyrer qc_policy.yaml-portar; signert attestasjon | attestasjon (stdout) |
| `valo-classify` | Risikoklasse A/B/C frå policy | (read) |
| `valo-merge` | Merge-controller; SoD; krev att+CI+klasse | gh pr merge |
| `valo-watchdog` | STRICTLY read-only detect/classify/report | ingen |
| `valo-report` | Exception-only kompakt kontrollpanel | ingen |
| `valo-graft` | Governed wrapper for replaceable Graft code-context | lokal regenererbar context-cache |

## Tilstandsmaskina (orchestrator.db)
DISCOVERED → CLAIMED → IMPLEMENTING → PR_OPEN → QC_PENDING
→ READY_TO_MERGE → MERGED
Feil: BLOCKED | NEEDS_HUMAN | CANCELLED | INCIDENT_HOLD

## Command-plane integration

Before each mission, Factory OS must:

1. fetch current policy and HALT state from `nsolland-valo-control`
2. validate command schema, principal, authority basis, scope, expiry and idempotency
3. classify risk and required execution-governance path
4. issue a bounded mission to the selected worker
5. write acknowledgement, progress and terminal receipts

The command queue is evidence of transmission. It is never authority by itself.

## Credential brokering

Factory OS owns runtime credential brokering. Specialist repositories and workers must not hold permanent ecosystem-wide credentials.

Target architecture:

- dedicated GitHub App installed only on approved repositories
- short-lived installation tokens per mission
- read-only `Contents` and `Metadata` by default
- separate capabilities for write, pull request, merge and deployment
- no implicit secrets, administration or policy-change access
- receipt for credential issuance and consequential use

`FACTORY_REPO_TOKEN` is a temporary compatibility mechanism. When used, it must be read-only, repository-scoped and stored only as a deployment secret. It should be removed from `research-factory` when Factory OS credential brokering is operational.

## Governed connector protocols

Factory OS supports provider-neutral connector contracts while preserving the authority boundary:

- HTTP/HTTPS egress through the governed CrabTrap-compatible connector
- A2A 1.0 for agent-to-agent discovery, messaging, tasks and artifacts
- MCP for agent-to-tool, resource and prompt-server interaction

Transport capability, Agent Cards, endpoint access and credentials are evidence only. They do not create authority. Every consequence-bearing connector operation must bind principal, mandate, exact payload, VAIG evaluation, REHT clearance, RACS decision and receipt evidence.

A2A implementation:

- architecture: `docs/architecture/governed-a2a.md`
- mandate contract: `schemas/a2a_mandate_envelope.schema.json`
- client contract: `schemas/a2a_client_request.schema.json`
- receipt contract: `schemas/a2a_receipt.schema.json`
- envelope validator: `bin/valo-a2a-envelope`
- production client CLI: `bin/valo-a2a-client`
- HTTP+JSON adapter: `connectors/a2a/client.py`
- deployment profile: `config/a2a_connector.yaml.example`

## Governed code context

`valo-graft` exposes NanoNets/Graft as a replaceable context engine for bounded software workspaces. It may build/query code graphs, map callers and provide blast-radius/context evidence, but it cannot admit state, create authority, approve code, merge or execute effects.

The adapter blocks Graft's machine-global `init`, upgrade and MCP-registration surfaces. Structural mode removes ambient model-provider credentials and isolates Graft's machine-global maintenance cache. LLM-backed `ask` / `build --deep` is opt-in and restricted to localhost or literal private-network OpenAI-compatible endpoints.

See `docs/graft-context-adapter.md` and `config/graft_policy.json`.

## BLOCKER #1 — Primærrepo er read-only for agentar
/home/njaal/valo-platform = operatørcheckout. Agentar MÅ bruke
/tmp/valo-runs/<run_id>/valo-platform (valo-run). pre-commit hook
(.git/hooks/pre-commit.d/00-agent-primary-guard) blokkerer agent-commit;
valo-git blokkerer checkout/reset/merge/push i primærtreet når
VALO_AGENT_RUN=1. Kvar write-handling sjekker valoctl-mode rett før utføring.

## Blokker #2 — claimed.json fjerna frå PR-flyt
Claims er IKKJE lenger versjonerte repoendringar. Bruk `valo-claim`:
- skriv claims.db (issue_id, actor_id, run_id, claimed_at, expires_at,
  heartbeat_at, status)
- mirror til GitHub: label `claimed`, assignee, comment med run_id
- `valo-claim expire` frigjer utgåtte leases automatisk
- ingen stale claim kan kome inn i PR-diff (dei ligg ikkje i repoet)
MIGRERING: claimed.json skal slettast frå greiner (konfliktregel:
use_main). Ikkje commit claimed.json i nye PRar — QC port `claims`
blokkerer det (såg #764 inneheld claimed.json → BLOCKED).

## Blokker #3 — Éin orkestrator
Cron køyrer BERRE valo-orchestrator (job 566507681528, pausa). Gamle
sjølvstendige jobbar (valo-foreman, branch-sweep, issue-watcher, QC x2,
fabrikk-watchdog, auto-merge) er pausa og konsolidert. Ingen jobb styrer
andre via cron/filer.

## Blokker #4 — QC maskinlesbart + head-SHA-bunde
qc_policy.yaml (qc-v1): 6 portar + conflict_rules + risk_classes.
valo-qc returnerer signert JSON-attestasjon bunden til head_sha.
Endrar PR-head seg → attestasjon ugyldig (merge-controller sjekkar).

## Blokker #5 — Risikoklassar + SoD
A = automatisk merge (docs/test/additiv). B = automatisk etter dobbel
kontroll (prod/adapter, ikkje authority). C = berre menneske.
Merge-controller krev: mode==NORMAL, gyldig att (head==live), CI grøn,
klasse A/B, ingen endring sidan att. Worker kan ikkje godkjenne eigen PR /
merge / endre policy. QC kan ikkje endre kode / pushe / merge.

## Blokker #6 — Watchdog read-only + exception-only
valo-watchdog les berre (allow-list); blokkerer valoctl enter, git reset,
osv. valo-report gir kompakt panel; STILLE når grønt. Du får melding berre
ved: NEEDS_HUMAN, INCIDENT, POLICY_CHANGE, AUTHORITY_CHANGE, REPEATED_FAILURE.

## Modus-kontroll (menneske)
  valoctl status
  valoctl enter MAINTENANCE --cancel-queued --drain-running
  valoctl enter INCIDENT_HOLD
  valoctl exit        # -> NORMAL, fabrikken kan starte
Før du flipar til NORMAL: fjern claimed.json frå greiner, og fjern/paus
utdaterte cron-jobbar (dei er allereie pausa).

## Kontrollpanel
  valo-report
  valo-orchestrator status
