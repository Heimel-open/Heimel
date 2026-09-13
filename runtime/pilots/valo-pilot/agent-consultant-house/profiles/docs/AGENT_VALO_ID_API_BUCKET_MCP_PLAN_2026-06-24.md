# agent.valo.id API, bucket and MCP plan

Date: 2026-06-24
Status: minimum technical next layer

## Current demo status

The current demo is enough to show the product thesis:

- public agent profile
- canonical YAML source of truth
- receipts
- revenue ledger
- REP
- BARO risk
- budget
- contestability
- revocation
- signed receipt verification
- signed profile write gate
- GitHub Actions proof chain

This is enough for a buyer conversation.

It is not yet enough for external developers or agent runtimes.

The missing technical layer is access:

```text
profile files -> public bucket -> API -> MCP tools
```

## Bucket

Purpose:

Make canonical profile artifacts publicly readable and cacheable.

Minimum bucket layout:

```text
agent.valo.id/
  registry.json
  agents/
    research-01/
      profile.yaml
      profile.json
      profile.html
      receipts/
        251b505882c1ebdb.receipt.yaml
      risk.yaml
      rep.yaml
      value_ledger.yaml
      budget.yaml
      revocation.yaml
      contestability.yaml
      proof.json
```

Rules:

- bucket is read-only for public clients
- writes only through signed profile write gate
- canonical profile remains YAML/JSON
- HTML is only rendered view
- `proof.json` contains hashes, signature status and last CI result

Recommended first implementation:

GitHub Pages or static object bucket.

Do not start with a database.

## API

Purpose:

Let humans, systems and agents verify an agent profile without reading GitHub manually.

Minimum endpoints:

```text
GET /v1/agents
GET /v1/agents/{agent_id}
GET /v1/agents/{agent_id}/proof
GET /v1/agents/{agent_id}/receipts
GET /v1/agents/{agent_id}/risk
GET /v1/agents/{agent_id}/rep
POST /v1/verify/receipt
POST /v1/verify/profile
```

First API response should answer:

```text
Is this agent active?
Who owns it?
What is it allowed to do?
What is blocked?
What risk does it carry?
What value has it produced?
Are the receipts valid?
Can the profile be changed?
```

Minimum `proof` response:

```json
{
  "agent_id": "agt_research_01",
  "profile_id": "research_01_agent_valo_id",
  "active": true,
  "revoked": false,
  "open_contests": 0,
  "receipt_signatures_valid": true,
  "profile_write_gate": "ALLOW",
  "baro_route": "WATCH",
  "ci_status": "green"
}
```

Recommended first implementation:

Tiny FastAPI service over the static files.

Do not build auth first for public reads.

Auth is only needed for writes.

## MCP

Purpose:

Let AI tools and agent runtimes ask VALO about an agent before interacting with it.

Minimum MCP tools:

```text
valo_agent_lookup(agent_id)
valo_agent_verify(agent_id)
valo_receipt_verify(receipt_id)
valo_agent_risk(agent_id)
valo_agent_authority(agent_id, requested_surface)
valo_profile_write_check(agent_id)
```

Critical MCP question:

```text
Should I trust this agent for this action?
```

Minimum MCP output:

```json
{
  "agent_id": "agt_research_01",
  "decision": "ALLOW",
  "authority_level": "MEDIUM",
  "requested_surface": "research_briefs",
  "surface_allowed": true,
  "risk_level": "low_to_medium",
  "receipt_signatures_valid": true,
  "revoked": false,
  "contestable": true
}
```

MCP is the real strategic layer.

A profile is for humans.

API is for systems.

MCP is for agents.

## Demo ladder

Demo 1: human trust

Show HTML profile, YAML, receipts and CI green.

Demo 2: system trust

Call API:

```text
GET /v1/agents/agt_research_01/proof
```

Show machine-readable proof.

Demo 3: agent trust

Call MCP:

```text
valo_agent_authority("agt_research_01", "research_briefs")
```

Show ALLOW/DENY/STEP_UP.

## What to build next

Build in this order:

1. `profile.json` renderer from canonical YAML.
2. `proof.json` generator with hashes and verification status.
3. static bucket layout in repo.
4. tiny read-only API over the static files.
5. MCP server exposing lookup, verify, risk and authority tools.
6. write API only after production key custody exists.

## What not to build yet

Do not build marketplace.

Do not build payments.

Do not build live runtime dashboard.

Do not build user accounts.

Do not build complex onboarding.

The next proof is simpler:

> A machine can ask whether an agent is legitimate, safe enough and authorized before trusting it.

## Product line

The company becomes three layers:

```text
agent.valo.id profile   -> human-readable trust
agent.valo.id API       -> system-readable trust
agent.valo.id MCP       -> agent-readable trust
```

This is the minimum bridge from profile to infrastructure.
