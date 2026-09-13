# Attention Content Factory

Status: product-line seed

## Objective

Turn a bounded domain objective into a continuously operated, multi-channel attention and content system whose unit of success is verified outcome, not content volume.

```text
domain + objective + audience + constraints
→ demand / topic discovery
→ evidence-backed research
→ canonical knowledge asset
→ channel-native transformations
→ quality + provenance gate
→ governed publish decision
→ distribution
→ outcome observation
→ GCU accounting
→ feedback
→ next-best production action
```

The factory is not a bulk text generator. Blog posts, videos, social posts, newsletters, podcasts, shorts, landing pages and future channels are replaceable output surfaces of one system.

## Primary objective

Maximize verified value created from attention within the supplied mandate and constraints.

Content volume, impressions, clicks and posting frequency are supporting signals. They must not silently replace the primary objective.

## Factory contract

A run begins with a bounded `AttentionMissionV1` containing:

- domain;
- objective and target outcome;
- intended audience;
- allowed claims and evidence requirements;
- brand / voice constraints;
- allowed channels;
- publishing authority;
- budget and rate limits;
- prohibited topics / actions;
- measurement contract.

A mission produces one or more `ContentUnitV1` records with lineage to the research and evidence used to create them.

## Core lanes

### 1. Discover

Identify questions, demand, events, gaps, competing narratives and useful opportunities. Discovery proposes work; it does not authorize publication.

### 2. Research

Build a reusable evidence package. Claims carry provenance, freshness and confidence. Unsupported material is removed, qualified or escalated.

### 3. Canonical asset

Create the underlying knowledge object before channel adaptation. The canonical asset captures the actual idea, evidence, intended value and factual boundaries.

### 4. Transform

Render channel-native outputs from the canonical asset. Transformation is semantic, not copy/paste.

Initial adapters:

- web / blog;
- YouTube long-form script;
- YouTube Shorts;
- LinkedIn;
- Instagram / Facebook;
- X;
- newsletter;
- podcast script;
- landing page.

Adapters are commodity slots. New channels must not require a new core primitive.

### 5. Gate

Before an external effect, evaluate:

- factual support;
- provenance completeness;
- duplication / low-value repetition;
- channel policy constraints;
- mission constraints;
- current publishing authority;
- budget / rate limits.

The generation lane has no direct effect path.

```text
direct_effect_path = false
```

Publishing, advertising spend, account changes, replies, outreach and other consequential actions must cross the existing governed execution boundary with fresh authority at consequence time.

### 6. Distribute

Approved channel adapters publish or schedule the exact bound artifact. Distribution receipts bind the executed artifact, channel, account, timestamp and authorization decision.

### 7. Observe

Collect outcome evidence such as qualified attention, completion, retention, subscriber conversion, lead quality, purchase, task completion or another mission-defined result.

Raw attention is not automatically value.

### 8. Account

GCU records value at the outcome boundary. Cost and performance can therefore be compared across humans, models, channels and strategies without using words, tokens, posts or hours as the economic unit.

Useful operational measures include:

- cost per accepted ContentUnit;
- cost per verified GCU;
- GCU per channel;
- GCU per canonical asset;
- evidence failure rate;
- publish rejection rate;
- content decay / refresh rate.

### 9. Learn

Feed observed outcomes back into discovery, selection, format and distribution decisions. Learning may change the plan, but not the mission objective or authority.

## Anti-slop invariant

AI-generated and human-generated low-value content are treated identically.

A ContentUnit is rejected when it is materially duplicative, unsupported, irrelevant to the mission, or has no plausible audience value merely to increase output volume.

The system optimizes cost per accepted and effective output, not cost per generated item.

## Scale model

One factory may operate many independent missions:

```text
1 factory
→ N domains
→ N canonical knowledge streams
→ M channel adapters per domain
→ governed parallel production
→ shared measurement and learning substrate
```

Mission state, authority, evidence and outcome accounting remain isolated. Cross-domain reuse requires explicit provenance and mission admissibility.

## Relationship to VALO Factory

This is a Factory product line, not a new governance stack.

Reuse:

- existing Factory orchestration and bounded build/run contracts;
- REHT for fresh consequence-time authority;
- RACS / governed execution boundary for ALLOW, DENY or ESCALATE;
- Veritas-compatible effect evidence;
- replaceable model, media, scheduler, storage and connector slots;
- GCU as the outcome/value accounting boundary.

No publishing platform, social network, model vendor or analytics provider becomes a strategic dependency.

## First executable slice

The smallest useful implementation is one mission with:

```text
research package
→ canonical article
→ blog + LinkedIn + YouTube-script transforms
→ deterministic quality/provenance gate
→ dry-run distribution receipts
→ synthetic outcome events
→ GCU ledger
→ next-action recommendation
```

No live publishing is required to prove the core loop. Live channel adapters are added only after the governed dry-run path is green.

## Exit criterion

The seed becomes an executable product line when the same canonical asset can pass through at least three channel adapters, preserve evidence lineage, produce deterministic gate decisions and distribution receipts, ingest outcome evidence, and calculate comparable GCU without introducing a direct effect path.
