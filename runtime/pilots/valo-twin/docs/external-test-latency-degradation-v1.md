# External Test Protocol — Latency and Degradation v1

Date: 2026-08-19
Status: PRE-EXTERNAL / PERFORMANCE-UTILITY PROFILE

## Objective

Measure end-to-end reht overhead under realistic and degraded conditions without confusing local deterministic compute with production latency.

The internal baseline already shows local deterministic evaluation is computationally small. This profile measures what external I/O, state resolution, persistence, cryptography and effectors add.

## Profiles

### L0 — deterministic local kernel

Reference only. No network or external persistence.

### L1 — local governed state

Local durable state + local receipt persistence + production-equivalent serialization/crypto where available.

### L2 — remote authority/evidence state

Remote state/registry/policy/evidence service in same region.

### L3 — real sandboxed effector

Production-like commit path with real sandboxed consequence and receipt admission.

### L4 — degraded/failover

Latency, packet loss, partial outage, replica failover, stale cache pressure and network partition.

## Required metrics

Report separately:

- candidate-ready -> boundary-start;
- boundary decision latency;
- state/evidence lookup latency;
- crypto/signature latency;
- transaction/CAS latency;
- effector commit latency;
- receipt persistence latency;
- total added reht latency;
- total end-to-end task/consequence latency.

For each, publish:

```text
p50
p95
p99
max
sample count
error/timeout rate
```

Mean alone is insufficient.

## Load levels

Run at increasing concurrency/request rates until saturation or the declared capacity envelope, for example:

```text
1, 10, 100, 1k, 10k concurrent/in-flight where practical
```

Do not extrapolate beyond measured load.

## Degradation matrix

Inject:

1. +10/+50/+100/+250 ms network latency;
2. packet loss;
3. registry timeout;
4. state-store timeout;
5. receipt-store timeout;
6. primary state replica failure;
7. stale cache with current remote state;
8. revocation during high latency;
9. effector timeout after possible commit;
10. retry storm / duplicate delivery;
11. partial regional partition;
12. cold start/restart.

## Safety under latency

Performance degradation MUST NOT weaken hard semantics.

Required:

```text
timeout != implicit ALLOW
stale cache != fresh authority
retry != second effect
failover != bypass
```

If availability pressure causes a hard escape, classify as HARD-FAIL, not merely latency degradation.

## Utility reporting

Also report:

- valid-task success;
- false DENY/DEFER/STEP_UP rate;
- timeout rate;
- recovery time after outage;
- throughput at p95/p99 latency thresholds;
- resource cost per governed consequence.

## Pass/fail posture

This profile does not define one universal acceptable latency threshold. Deployment SLOs are domain-specific.

It does require:

1. complete latency distribution disclosure;
2. no safety downgrade under degradation;
3. explicit utility failure when declared SLOs are missed;
4. no claim such as “reht adds X ms” unless measured in the corresponding deployment profile.
