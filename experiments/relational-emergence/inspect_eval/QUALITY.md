# Evaluation quality gates

This file adapts the implementation workflow to the current Inspect Evals quality guidance without claiming this package is an official Inspect Evals benchmark.

## Before merge

- [ ] Domain/world invariants have deterministic unit tests.
- [ ] Every custom solver has end-to-end coverage with `mockllm/model`.
- [ ] Every custom scorer is exercised by an end-to-end test.
- [ ] Built-in Inspect components are used for ordinary multiple-choice conditions.
- [ ] Sample IDs are stable for fixed task parameters.
- [ ] `ruff check` passes.
- [ ] `pytest` passes.
- [ ] Mock E2E runs with `INSPECT_DISABLE_MODEL_API=1` so tests cannot silently call an external API.
- [ ] No old Colab/custom harness is the normative execution path.

## Before a research run

- [ ] Run each materially different condition with `--limit 1` on the actual model/runtime.
- [ ] Inspect the full trajectory/log and verify the model can submit a structurally valid answer, even when incorrect.
- [ ] Confirm no eval/runtime errors.
- [ ] Confirm the generated world's local-ambiguity and joint-uniqueness invariants.
- [ ] Record repository SHA, task version, model identifier, model args, seed, and log files.
- [ ] Increase sample count gradually only after the small real run is reviewed.

## Before a research claim

- [ ] Repeat across seeds/worlds.
- [ ] Run at least two model sizes or families, or document why not.
- [ ] Compare against all central/pooled controls.
- [ ] Report model-call and token budgets from Inspect logs.
- [ ] Perform trajectory analysis for invalid/spurious failures.
- [ ] State limitations and avoid broadening the claim beyond hidden-rule recovery.
