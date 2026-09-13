# Capability-on-Demand ROI Stress & Falsification

Status: executable synthetic stress harness  
Issue: #34  
Epistemic status: `implementation_claim` + `falsification_criterion`

## Purpose

The earlier capability-on-demand reference case showed a favorable synthetic comparison.

This harness asks the opposite question:

> Under what conditions does the elastic-organization thesis stop working?

The goal is not to maximize a headline ROI. The goal is to force the model through economic, capability, routing and latency conditions where it must fail.

## Reference case

Frozen reference assumptions:

```text
annual cases                 1,000
fixed-staff headcount            12
elastic core headcount             7
fully-loaded employee cost   2.0 MNOK/year
external specialist rate     2,500/hour
external specialist cases          25%
principal-required cases            5%
expert work per external case       3 h
discovery/context overhead          1 h
expert availability               100%
stale capability                    0%
wrong-route rate                     0%
sourcing latency                     2 h
case slack                          24 h
```

Executable result:

```text
fixed annual cost            24.0 MNOK
elastic annual cost          16.5 MNOK
permanent cost avoided       10.0 MNOK
external spend                2.5 MNOK
net savings                   7.5 MNOK
savings rate                    31.25%
ROI on external spend            3.0x
purchased specialist hours     1,000 h
break-even expert rate       10,000/hour
break-even external cases        1,000
```

The 3.0x value means net savings divided by external specialist spend. It is not enterprise ROI, valuation uplift or a forecast.

## Hard falsification conditions

A scenario fails if **any** of the following occur:

```text
NO_COST_ADVANTAGE
UNRESOLVED_CAPABILITY
WRONG_EXPERT_ROUTING
SOURCING_LATENCY
CAPABILITY_COVERAGE
PRINCIPAL_BOTTLENECK
```

Frozen thresholds:

```text
unresolved external cases       <= 2%
wrong expert routes             <= 2%
deadline misses                 <= 5%
external capability coverage    >= 95%
principal-required cases        <= 25%
net savings                      > 0
```

These thresholds are research assumptions. They are not validated operational tolerances.

## Named hostile tests

### 1. Economic break

Low permanent employee cost, expensive specialists, high external-case volume and high discovery overhead make the elastic model more expensive than fixed staffing.

Expected result:

```text
NO_COST_ADVANTAGE
```

This is important: capability-on-demand is **not** automatically cheaper.

### 2. Capability break

When expert availability falls to 80% and 10% of represented capability is stale, usable external coverage drops to 72%.

Expected result:

```text
UNRESOLVED_CAPABILITY
CAPABILITY_COVERAGE
```

Cheap external labor is irrelevant if the required capability cannot actually be supplied reliably.

### 3. Routing break

A 10% wrong-specialist rate fails the model even while the economics can remain positive.

Expected result:

```text
WRONG_EXPERT_ROUTING
```

This prevents cost savings from masking degraded judgement quality.

### 4. Latency break

If sourcing takes 36 hours and the decision window has 24 hours of slack, the specialist arrives too late.

Expected result:

```text
SOURCING_LATENCY
```

A capability that arrives after the consequence boundary is not an available capability.

### 5. Principal bottleneck

If 50% of cases still require genuinely fresh principal judgement, the small-core scaling thesis is rejected for that workload.

Expected result:

```text
PRINCIPAL_BOTTLENECK
```

The model must not relabel irreducible principal judgement as delegable expertise simply to improve utilization.

## Frozen broad stress grid

The harness sweeps a deliberately hostile deterministic grid across:

```text
employee annual cost       1.0 / 2.0 / 3.0 MNOK
expert hourly rate         1,000 / 3,000 / 8,000
external-case share        10% / 30% / 60%
discovery overhead         0.5 / 2 / 8 hours
expert availability        99% / 95% / 80%
wrong-route rate           0.5% / 2% / 10%
sourcing latency           2 / 12 / 36 hours
principal-required share   5% / 20% / 50%
```

Invalid case-share combinations above 100% are removed.

Frozen result:

```text
scenarios                  5,832
survive all thresholds       464
falsified                  5,368
survival rate                7.96%
```

Failure counts are overlapping because one scenario may violate several conditions:

```text
UNRESOLVED_CAPABILITY      3,888
WRONG_EXPERT_ROUTING       1,944
SOURCING_LATENCY           1,944
CAPABILITY_COVERAGE        1,944
PRINCIPAL_BOTTLENECK       1,458
NO_COST_ADVANTAGE          1,431
```

The 7.96% survival rate is **not a probability of business success**. The grid is not sampled from a real-world distribution. It intentionally contains many hostile combinations and exists to demonstrate that the thesis has narrow, explicit failure boundaries rather than being made unfalsifiable.

## What the stress test tells us

The thesis is stronger than a staffing-cost story, but also more conditional.

It requires all four layers to work simultaneously:

```text
1. economic viability
2. capability availability/freshness
3. correct expert routing
4. delivery before the decision boundary
```

and it fails as an organization-scaling mechanism if too much work remains principal-irreducible.

Therefore the actual product value cannot be demonstrated by showing only:

```text
external expert rate < permanent salary
```

The real empirical claim must be closer to:

> Can the organization identify capability gaps early enough, acquire the correct current expertise with low enough context-transfer overhead, and return valid judgement before the decision boundary at lower total cost than owning that capability permanently?

## Break-even interpretation

In the frozen reference case, five permanent positions represent 10 MNOK of avoided annual fully-loaded cost.

At 1,000 purchased specialist hours, break-even is:

```text
10,000 NOK/hour
```

At 2,500 NOK/hour and four purchased hours per external case, the economic break-even is:

```text
1,000 external cases/year
```

That is far above the 250 external cases in the reference case.

But this statement is valid **only under the frozen reference assumptions**. More discovery overhead, rework, lower availability, or a smaller permanent-cost differential lowers the break-even point quickly.

## What must be tested with historical replay

The synthetic model now has enough failure conditions to interrogate actual historical work.

For each historical VALO decision, record:

```text
case timestamp
required capability
capability known at the time?
internal capability available?
external capability identifiable?
context/discovery effort actually required
latency before useful judgement
wrong-route/rework evidence
whether principal judgement was irreducible
what the permanent alternative would have required
```

Only after that evidence exists should the economic parameters begin moving from synthetic assumptions toward observed distributions.

## Canonical boundary

Capability does not imply authority.

The stress harness evaluates organizational capability acquisition economics and failure modes only. It contains no execute or authorize primitive. Consequence-bearing actions remain downstream of governed state, conformance and REHT.
