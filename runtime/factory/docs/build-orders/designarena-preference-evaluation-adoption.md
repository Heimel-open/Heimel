# Build order: DesignArena-style preference evaluation

Goal: make comparative, blind, provider-neutral evaluation a native Software Factory capability without weakening VALO governance.

## Deliverables

1. Preference Arena runtime
   - define EvaluationTask, CandidateRun, BlindPair, PairwiseVote and RankingSnapshot contracts;
   - fan out one task to 2+ provider/model candidates through existing adapters;
   - bind prompt/task, harness, tool surface, environment and artifact digests;
   - randomize pair ordering and hide provider/model identity until vote sealing.

2. Evidence and ranking
   - append-only pairwise vote records;
   - Bradley-Terry/Elo-style relative strength calculation with sample-count/confidence metadata;
   - separate subjective preference from objective QC, cost, latency, failure/retry and outcome evidence;
   - persist comparison evidence into Factory Experience Memory with freshness/version scope.

3. Agentic evaluation
   - compare complete runs, not only final artifacts;
   - capture tool calls, retries, errors, re-prompts, duration, cost and final postconditions;
   - require comparable harness/tool surfaces or explicit capability-difference evidence.

4. Governance binding
   - winning rank produces selection evidence only;
   - independent QC remains mandatory for promotion;
   - VAIG may aggregate evaluation evidence but has no authority;
   - REHT is the sole final authorization boundary for merge/deploy/publish/send/production mutation;
   - RACS expresses the deterministic outcome; gateway executes; Veritas seals execution evidence.

5. Routing
   - use arena history as one bounded routing signal for model/provider selection by task class;
   - decay/stale results when model, harness, tool surface or environment changes materially;
   - allow external DesignArena leaderboard/API data only as optional weak-prior evidence, never as authority.

## Initial factory arenas

- frontend/UI quality
- full-stack implementation
- code patch/refactor
- test generation and bug repair
- slide/document generation
- research synthesis
- long-horizon agent trajectory

## Acceptance gates

- candidate identity cannot leak into blind vote payloads;
- equal task digest across candidates in a comparison;
- every vote binds both artifact digests and evaluator identity/pseudonymous evaluator key;
- ranking reproducible from sealed pairwise records;
- objective failing candidate cannot be promoted because it wins preference;
- arena winner cannot cause a consequence-bearing action without fresh REHT clearance;
- provider swap does not require governance-code changes;
- tests cover ties, low sample counts, stale ranking evidence, provider failure, unequal harness conditions and REHT denial after preference win.

Source signal: DesignArena methodology observed 2026-08-09. Pattern adoption only; no required vendor dependency.
