# LOCAL EXECUTION REQUIRED

GEOMETRIC-SI experiment runs are not executed in GitHub Actions.

GitHub is used for source, review, branches and evidence references only. Any run that produces experimental evidence must be executed locally in the controlled research environment.

## Rule

- Do not treat GitHub Actions status as an experiment result.
- Do not add CI as a substitute for the experiment run.
- Code/unit tests may exist in the repository, but empirical GEOMETRIC-SI evidence requires a local run.
- Every task that reaches a local-only gate must state `LOCAL EXECUTION REQUIRED` explicitly in its handoff/status.
- Commit local result artifacts back only after the run, with provenance sufficient to distinguish code version, parameters, seed set and runtime environment.

## Current anchor

- repo: nsolland/PersonalAI-OS
- canonical base: 06750ddef1bd5d08c7756986d3154a9155e346cd
- branch: experiment/geometric-si-cost-equivalence
- owner: njal / relAIon research
- owned files: experiments/geometric_si/**
