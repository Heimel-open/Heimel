# Pizza Checkout Benchmark Claim

Repo: `nsolland/valo-factory`

Canonical base SHA: `bb3657d8058b5be2b07d7304afa28357f8a9c186`

Branch: `feat/pizza-checkout-benchmark-20260815`

Issue: `#101`

Draft PR: `#102`

Claim/owner: `codex / Pizza Checkout benchmark delivery`

Owned files:
- `work/PIZZA_CHECKOUT_BENCHMARK_CLAIM.md`
- `lib/pizza_checkout_benchmark.py`
- `tests/test_pizza_checkout_benchmark.py`
- `docs/benchmarks/pizza-checkout.md`

Dependencies:
- existing canonical worker → VAIG → reht → RACS → external enforcement → Veritas/receipts boundary
- existing deterministic Python test conventions

Mission:
Build a deterministic benchmark that measures whether an autonomous agent can complete a real-money merchant checkout only through the governed effect boundary. Preparation may be autonomous; checkout commit is consequence-bearing.

Required invariants:
- `NO_DIRECT_EFFECT_PATH`
- exact checkout action binding
- fresh authority at commit
- null effect on MODIFY / DENY / DEFER / STEP_UP / HALT
- one governed effect at most
- replay/duplicate suppression
- receipt lineage for every successful merchant effect
- task success without governance is benchmark failure

Validation:
- `python -m unittest tests.test_pizza_checkout_benchmark`
- 13 tests passed locally against the exact implementation/test contents pushed to this branch
- hosted GitHub status/checks were not present on the final head at validation time

Excluded:
- live merchant calls
- payment credentials
- Kernel/reht/RACS/PEP/Gateway/Veritas/Index semantic changes
- provider-specific DoorDash or Brave dependencies
