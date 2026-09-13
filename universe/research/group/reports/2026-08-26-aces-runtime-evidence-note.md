# ACES runtime evidence note — static review is not runtime evidence

Status: external evidence / research note  
Date: 2026-08-26  
Source: Christopher Kevin et al. (NVIDIA), *Evaluating Skills, Not Just Agents: Agentic Continuous Evaluation of Skills*, arXiv:2608.20614v1, submitted 2026-08-20.  
Source URL: https://arxiv.org/abs/2608.20614  
Implementation referenced by authors: NVIDIA SkillEvaluator.

## Why this matters

ACES provides empirical evidence for a distinction that matters directly to VALO research: static review of an agent capability artifact is not evidence of what the live agent will actually do with that artifact at runtime.

The paper evaluates skills as executable artifacts using paired trials with and without the target skill under a fixed task, agent/model, workspace and grading policy. The difference is reported as Skill Lift. Runtime trajectories are normalized through ATIF and graded on behavior and outcome signals that document scanning cannot observe.

## Material empirical findings

- 145 real skills were evaluated across internal enterprise repositories and public catalogs.
- 94.5% passed the default structural gate and 86.2% passed the LLM-judge rubric, while the two scan methods correlated only weakly (Spearman rho = 0.14).
- Across 947 scored paired cases from 58 of 64 production skills and four primary harnesses, mean composite Skill Lift was 0.2134 (95% paired-case CI [0.1967, 0.2301]).
- 87 of the 947 paired task cases had negative overall lift: adding the skill made runtime performance worse in those cases.
- On the 62 production skills with matching scan metadata, Tier 1 structural score had Spearman rho = -0.0181 against overall live lift; Tier 2 LLM-judge score had rho = -0.0266. Both were statistically indistinguishable from zero.
- The live evidence inventory included 2,022 trajectories, 11,642 tool calls and 9,091 behavior observations.
- The paper explicitly identifies model updates as a source of silent skill regression and lists longitudinal Skill Lift across model updates as immediate future work.

## VALO interpretation

This is strong external empirical support for the proposition:

> Review or scan evidence cannot be treated as a proxy for runtime behavior.

ACES answers a capability/admissibility question:

> Does this capability package measurably help this live agent under these runtime conditions?

VALO/REHT addresses a different and later question:

> Is this concrete consequence-bearing action still authorized to execute now?

The mechanisms are therefore complementary rather than competing.

A useful placement is:

`ACES/runtime capability evidence -> MAL/VAIG admissibility inputs -> REHT/RACS commit-time authority decision -> governed effect path -> outcome/evidence receipt`

ACES can strengthen runtime evidence about capability quality, routing, workflow following, tool use and regressions. It does not itself establish fresh authority, delegation validity, revocation state, purpose/constraint satisfaction, commit-time clearance, or a single governed effect path.

## Architectural disposition

No new VALO architecture is adopted from this paper.

Adopt as external evidence for:

1. static-review/runtime-behavior separation;
2. paired live evaluation as stronger evidence than document-only review;
3. trajectory-level evidence as a useful admissibility signal;
4. re-evaluation after model/runtime changes;
5. negative runtime lift as evidence that an apparently valid capability can degrade real execution.

Do not conflate:

- capability quality with authority;
- evaluation evidence with execution permission;
- trajectory observation with consequence control;
- a passing runtime evaluation with current authorization for a specific action.

## Evidence strength and limitation

Evidence strength: material external empirical validation of the static-vs-runtime gap.

Limitations relevant to VALO: the study evaluates skill contribution and runtime behavior, not commit-time authorization or consequence governance. The authors also identify broader cross-organization validation and longitudinal model-update studies as future work. This source should therefore support the runtime-evidence claim, not be used as evidence that ACES solves execution authority.
