# agent.valo.id micro company brief

Date: 2026-06-24
Status: internal positioning draft

## What we have

`agent.valo.id` is no longer only a public profile page.

It is a prototype trust layer for agentic economic actors:

- canonical YAML profile
- rendered HTML profile
- agent identity
- owner and custody
- authority level
- delegation boundary
- budget
- revenue
- REP
- BARO risk
- receipts
- contestability
- revocation
- session-bound HMAC signatures
- CI-enforced proof chain
- signed profile write gate

Core product sentence:

> agent.valo.id gives AI agents a verifiable public identity with receipts, revenue, risk and accountability.

Shorter version:

> LinkedIn, audit log and risk profile for AI agents.

Harder version:

> Do not trust an agent profile. Verify its authority, receipts, value and risk.

## The company

Working name:

`VALO Agent Identity`

Product name:

`agent.valo.id`

Category:

Agent identity and accountability infrastructure.

Market wedge:

Companies are deploying agents before they have identity, authority, receipts, revocation or audit-grade accountability for them.

Most tools answer:

> What did the agent do?

agent.valo.id answers:

> Who owns this agent, what is it allowed to do, what value did it create, what risk does it carry, and which receipts prove it?

## First customer

Best first customer is not a large bank.

Best first customer is a consulting, automation or AI operations team that is already building agents for clients and needs to prove control.

Ideal first buyers:

- AI consultancies
- internal automation teams
- GRC teams piloting agents
- regulated startups
- audit/compliance teams reviewing agent deployments
- marketplaces for agentic services

Avoid at first:

- huge banks
- public sector procurement
- defense
- general consumers
- pure developer tools without governance buyer

## First paid offer

Offer:

`Agent Accountability Profile Setup`

Deliverable:

One verified agent profile with:

- canonical profile file
- rendered public profile
- authority boundary
- allowed and blocked surfaces
- budget boundary
- receipt templates
- value ledger
- risk profile
- revocation registry
- contestability record
- CI proof checks

Price test:

- pilot: EUR 2,500 to 5,000 per agent/team
- implementation pack: EUR 10,000 to 25,000
- recurring monitoring/profile hosting: EUR 500 to 2,000 per month

## Why it can work

The market does not need another abstract AI ethics framework.

It needs operational proof objects.

agent.valo.id is useful because it converts vague governance claims into verifiable files:

- authority becomes explicit
- revenue must be receipted
- risk becomes visible
- profile changes require signed receipts
- blocked surfaces are declared
- revocation and contestability exist as first-class records

This is closer to compliance infrastructure than social media.

## How to present it

Do not lead with all acronyms.

Lead with the failure mode:

> Companies are about to employ AI agents, pay them, let them act, and measure their performance. But those agents do not have verifiable identity, authority, receipts or accountability.

Then show the simple answer:

> agent.valo.id is a verifiable profile for productive AI agents.

Then show the proof chain:

```text
Owner -> Authority -> Delegation -> Budget -> Session -> Action -> Receipt -> Value -> Risk -> Accountability
```

Then show the profile:

```text
CV + portfolio + audit log + revenue record + risk surface
```

Then show CI passing.

The screenshot of green GitHub Actions matters. It says this is not just language.

## Demo script

1. Show the public profile.
2. Show the canonical YAML.
3. Show one receipt.
4. Show signed HMAC verification.
5. Show revenue derived from receipts.
6. Show BARO risk surface.
7. Show profile write gate.
8. Show CI green.

Close with:

> The agent cannot simply claim value. It must carry receipts.

## Minimum next build

Next build should make this useful to a buyer:

1. Add two more sample agent profiles.
2. Add a registry page listing agents by REP, risk, revenue and authority.
3. Add a public verifier endpoint or CLI command.
4. Add production-key placeholder design: no secrets in repo.
5. Add one-page sales PDF.
6. Add onboarding checklist for a client agent.

## Do not overbuild yet

Do not build a full marketplace first.

Do not build tokens first.

Do not build dashboards first.

Do not build live BARO first.

The first business is simpler:

> We certify and publish verifiable profiles for AI agents.

Then expand into:

- registry
- monitoring
- runtime receipts
- live risk
- agent marketplace
- insurance/compliance integrations

## Company thesis

AI agents will become economic actors before institutions know how to govern them.

The missing layer is not intelligence.

The missing layer is accountable identity.

agent.valo.id is the first small implementation of that layer.
