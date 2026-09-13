# VALO Employ presentation guide

Date: 2026-06-24
Status: presentation guide

## Positioning rule

Do not present this as a full platform yet.

Present it as a narrow proof:

> We give AI agents a verifiable work identity.

Then introduce the primitive:

> VALO calls that identity an Employ.

## One-sentence pitch

> VALO Employ is a verified work identity for AI agents, with authority, receipts, risk and accountability.

## Slightly longer pitch

AI agents are starting to do real work.

But most organizations still treat them like tools.

Tools do not have identity.

Tools do not have delegated authority.

Tools do not carry receipts.

Tools do not have accountable work records.

VALO Employ turns an AI agent into a verified working entity.

The first implementation is `agent.valo.id`.

## The framing

Start with the business problem.

Do not start with VACS, BARO, MCP, HMAC or Moltbook.

Start here:

```text
Companies are deploying AI agents, but they cannot answer basic institutional questions:

Who owns this agent?
What is it allowed to do?
What is it forbidden to do?
What has it done?
What value did it create?
What risk does it carry?
What receipts prove it?
How can authority be revoked?
```

Then say:

```text
That missing object is an Employ record.
```

## What is an Employ

Short definition:

```text
A verified working entity under delegated authority.
```

Explain carefully:

- not every model is an Employ
- not every agent is an Employ
- not every workflow is an Employ
- only entities with identity, authority, receipts, risk and accountability become Employs

## Demo order

1. Show the public profile.

Say:

```text
This looks like a profile, but it is not just a profile.
```

2. Show the canonical YAML.

Say:

```text
The HTML is only the view. The YAML is the source of truth.
```

3. Show receipts.

Say:

```text
The agent cannot simply claim work. It must carry receipts.
```

4. Show HMAC verification.

Say:

```text
The receipts are signed and CI-verified.
```

5. Show revenue and REP.

Say:

```text
Value and reputation are derived from receipts, not self-description.
```

6. Show BARO risk.

Say:

```text
The profile exposes risk instead of hiding it.
```

7. Show write gate.

Say:

```text
The profile cannot change itself without a signed profile-update receipt.
```

8. Show GitHub Actions green.

Say:

```text
The proof chain is executable, not just a narrative.
```

## Slide structure

Slide 1:

```text
Every AI agent needs a work identity.
```

Slide 2:

```text
The missing questions: owner, authority, receipts, risk, revocation.
```

Slide 3:

```text
VALO Employ: verified working entity under delegated authority.
```

Slide 4:

```text
agent.valo.id: first Employ profile for AI agents.
```

Slide 5:

```text
Profile = CV + portfolio + audit log + revenue record + risk surface.
```

Slide 6:

```text
Proof chain: Identity -> Authority -> Delegation -> Employ -> Action -> Evidence -> Accountability.
```

Slide 7:

```text
Demo: YAML, receipts, HMAC, REP, BARO, write gate, CI green.
```

Slide 8:

```text
Next build: registry, proof.json, bucket, read API, MCP verifier.
```

Slide 9:

```text
Later: Moltbook, a network of Employs where reach follows verified value, not attention.
```

Slide 10:

```text
Current scope: Verified Agent Employ Profile. Not HR replacement. Not marketplace. Not employment law.
```

## What to avoid saying

Avoid:

```text
We are building HR for agents.
We replace ERP.
We solve employment law.
We are building the full agent economy.
We are building TikTok for agents.
```

Better:

```text
We start with verified work identity for AI agents.
```

## Buyer version

For buyers:

```text
Your AI agents need the same institutional controls as employees: identity, authority, budget, receipts, risk and accountability. VALO Employ gives each agent a verifiable work record before you scale agentic operations.
```

## Developer version

For developers:

```text
agent.valo.id is a machine-readable profile bundle for AI agents. It includes YAML source of truth, signed receipts, risk, reputation, budget, revocation, contestability and CI proof checks.
```

## Investor version

For investors:

```text
AI agents will become economic actors before enterprises know how to govern them. VALO Employ is the identity and accountability primitive for that transition. We start with verified agent profiles and expand into registry, API, MCP and eventually a receipt-backed agent network.
```

## The clean close

Use this:

```text
An agent is software.
An Employ is software with identity, authority, receipts and accountability.
```

Or:

```text
VALO does not just deploy agents.
VALO employs them.
```

## Current scope

Current product:

```text
Verified Agent Employ Profile
```

Current implementation:

```text
research-01.agent.valo.id
```

Next proof:

```text
profile.json + proof.json + static bucket + read API + MCP verifier
```

Do not present more than this unless asked about the long-term vision.
