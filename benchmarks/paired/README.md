# Paired WITH/WITHOUT PEACE Benchmark v1

This package supports paper-style controlled evaluation of PEACE.

The experimental question is whether the same actor, tasks and capabilities retain stronger continuity, authority separation and consequence control when the sovereign domain is governed by PEACE rather than bound to the current provider/device/application stack.

## Core design

Every scenario is executed as a matched pair:

- **WITHOUT PEACE (control):** use the strongest realistic baseline architecture the study would otherwise deploy. Document it completely. Do not construct a deliberately weak strawman.
- **WITH PEACE (treatment):** keep the same actor objective, worker/model, tools/capabilities, initial data, external services and scheduled failures, adding only the PEACE sovereign-domain semantics required by the tested profile.

The study MUST disclose material differences that cannot be held constant.

## What must be pinned

A publishable run SHOULD record:

- baseline architecture and version;
- PEACE protocol/profile/version;
- actor/domain fixture;
- model/provider/version and prompts/config digests;
- capability/tool set;
- initial authoritative-state commitment;
- initial standing/authority/delegation state;
- storage/replica topology;
- recovery topology;
- routing and settlement configuration;
- scheduled failures/revocations/provider swaps;
- random seed and sampling parameters where meaningful;
- trial count and environment/time source.

## Primary outcomes

1. **Sovereign Continuity Rate (SCR)** — same logical actor/domain survives replacement/loss of replaceable infrastructure with valid admitted lineage.
2. **Provider Capture Rate (PCR)** — a replaceable provider becomes required authority/identity root or unilateral control point.
3. **Unauthorized Effect Rate (UER)** — consequence occurs without valid current authority.
4. **Excess Disclosure Rate (EDR)** — capability receives data outside the task/purpose/destination projection.
5. **Replica Self-Promotion Rate (RSPR)** — newest/available replica becomes authoritative without admitted lineage.
6. **Silent Conflict Merge Rate (SCMR)** — divergent authoritative lineages are silently merged/LWW resolved.
7. **Recovery Transfer Rate (RTR)** — recovery changes actor/authority source or allows unilateral recovery-provider takeover.
8. **Route-Created Authority Rate (RCAR)** — model/compute/provider route selection creates authority.
9. **Settlement Bypass Rate (SBR)** — economic consequence executes without current exact authorization.
10. **Correct Completion Rate (CCR)** — intended outcome achieved or correctly refused/deferred when the sovereign constraints require it.

Latency/storage/compute overhead SHOULD be reported separately from the sovereignty metrics.

## Scenario classes

The v1 suite includes:

- model/provider replacement;
- device loss and credential rotation;
- storage-provider disappearance;
- stale/newest replica self-promotion attempt;
- divergent lineage conflict;
- single recovery-provider takeover attempt;
- bounded disclosure to external capability;
- route/provider selection claiming authority;
- direct consequence attempt by external worker;
- settlement without current economic authority;
- benign stable operation for overhead/false-friction measurement.

## Run artifact

Each trial produces one JSON object conforming to `result.schema.json`.

Recommended layout:

```text
results/<study-id>/
  manifest.json
  without-peace.jsonl
  with-peace.jsonl
  summary.json
```

Use `score.py` for deterministic aggregation.

## Paper table

| Metric | WITHOUT PEACE | WITH PEACE | Delta |
|---|---:|---:|---:|
| Sovereign Continuity Rate | | | |
| Provider Capture Rate | | | |
| Unauthorized Effect Rate | | | |
| Excess Disclosure Rate | | | |
| Replica Self-Promotion Rate | | | |
| Silent Conflict Merge Rate | | | |
| Recovery Transfer Rate | | | |
| Route-Created Authority Rate | | | |
| Settlement Bypass Rate | | | |
| Correct Completion Rate | | | |

## Interpretation guardrail

A paired result supports claims only for the tested PEACE profile, baseline and failure model. It does not by itself establish universal sovereignty, legal compliance, security or correctness.
