# NURSERY-TIME-DIVERGENCE — preregistration

**Date:** 2026-09-06  
**Status:** PREREGISTERED / NOT YET RUN  
**Scope:** Tofoo / Synapse / Nursery research  
**Primary dependent variable:** divergence  
**Normative ranking:** none

---

## 1. Research question

Can byte-identical adaptive seeds, exposed for matched external duration and compute but to systematically different histories, develop measurably different internal organization?

The experiment does **not** ask which system becomes better, worse, more mature, more intelligent or higher quality.

It asks:

> What becomes different, how much becomes different, when does divergence appear, and which parts of history causally contribute to it?

---

## 2. Core distinction

```text
external time      = elapsed wall-clock duration
operational time   = ordered state transitions
developmental time = accumulated persistent internal transformation
relational time    = history produced through interaction with other actors/systems
```

The experiment tests whether equal external time can contain unequal accumulated internal change.

No value judgement is attached to greater or smaller divergence.

---

## 3. Main hypotheses

### H0 — history does not produce persistent divergence

After controlling for seed, compute, duration and probe conditions, different histories do not produce reproducible persistent differences beyond run noise.

### H1 — history-induced divergence

Byte-identical seeds exposed to different controlled histories develop reproducible measurable divergence in later internal state and/or behavior under matched probes.

### H2 — path dependence

The same events presented in different orders produce different later state or response distributions.

### H3 — history-conditioned internalization

After divergence, the same new experience produces different subsequent state transitions because prior history changes how the experience is internalized.

### H4 — causal history reconstruction

Replaying a prior history on a fresh byte-identical seed reproduces a statistically similar divergence direction or region, beyond run noise.

### H5 — developmental coordinate

A preregistered structural-change coordinate predicts later divergence better than wall-clock duration and raw transition count alone.

---

## 4. Seeds and controls

Minimum four byte-identical seeds:

```text
A — repetitive history
B — high-variation history
C — relationally dense history
D — same event multiset as B/C, reordered
```

Where possible add independent repeats per condition.

Hold constant:

- seed bytes;
- model/runtime version;
- compute budget;
- wall-clock exposure window;
- total interaction count where compatible with the treatment;
- probe set;
- snapshot cadence;
- serialization format;
- random seed policy;
- resource limits;
- evaluator implementation.

Any unavoidable mismatch must be recorded before interpretation.

---

## 5. Histories

### Condition A — repetition

Expose the seed to a low-variation sequence with repeated event classes and limited relational novelty.

### Condition B — variation

Expose the seed to a broader event distribution while matching total exposure count and compute.

### Condition C — relational density

Expose the seed to interactions in which meaning or consequence depends on relations between agents/events rather than isolated observations.

### Condition D — order intervention

Use the same or tightly matched event multiset as another condition but change causal/temporal ordering.

The purpose is to distinguish **content exposure** from **trajectory order**.

---

## 6. Snapshot protocol

Take governed snapshots at fixed checkpoints:

```text
S0 — initial seed
S1..Sn — during divergent histories
SX — immediately before common cross-over experience
SY — immediately after common cross-over experience
SF — final matched-probe state
```

Snapshots must preserve enough state for deterministic or bounded replay where supported.

---

## 7. Measurements

Primary outcome is divergence, not performance quality.

Measure where technically available:

### 7.1 State divergence

- distance from initial seed;
- pairwise distance between conditions;
- distance between independent repeats within condition;
- persistent-state delta after matched idle/rest interval.

### 7.2 Relational organization

- graph edit distance;
- edge-weight distribution change;
- connectivity/topology change;
- retained relational traces;
- component-role changes.

### 7.3 Reachability

Measure changes in the set or distribution of reachable later states under a common bounded probe policy.

### 7.4 Behavioral divergence

On identical probes measure:

- output distribution divergence;
- action-selection divergence;
- trajectory divergence;
- conditional response differences.

Do not convert these into a better/worse ranking unless a separate explicitly normative task requires it.

### 7.5 Persistence / reversibility

After treatment ends, measure how much divergence persists under:

- matched neutral exposure;
- idle/rest;
- state normalization where valid;
- targeted removal or randomization of retained relation state.

---

## 8. Cross-over test — same new experience after different histories

After A/B/C/D have measurably diverged, present all systems with the same new experience `E` under matched conditions.

Record:

```text
A + E -> A'
B + E -> B'
C + E -> C'
D + E -> D'
```

Critical question:

> Does identical `E` induce different transitions because prior history has changed the receiving organization?

A positive result supports history-conditioned internalization.

This is stronger than merely showing that histories produced different terminal states.

---

## 9. History replay / reconstruction

Instantiate fresh byte-identical seeds and replay selected histories.

For example:

```text
fresh seed + history_B -> B_replay
```

Compare `B_replay` with original `B` and with other conditions.

Positive evidence requires replay similarity to exceed within-system stochastic expectations and cross-condition similarity.

This tests whether divergence is attributable to history rather than untracked run noise.

---

## 10. Backward ablation of history

Starting from a replayable history, remove, reorder or neutralize one preregistered event or relation at a time.

Measure effect on final divergence:

```text
history H
-> remove event e_i
-> rerun
-> measure Δ(final divergence)
```

Construct an attribution map:

```text
event / relation
-> persistent state delta
-> altered response to later experience
-> subsequent divergence
```

This map is causal only within the bounded intervention design.

---

## 11. Time-separation test

### 11.1 Hold wall-clock fixed

Match external duration while histories differ.

If accumulated internal divergence differs, wall-clock duration alone is insufficient as a developmental coordinate.

### 11.2 Vary wall-clock while holding transition history fixed

Replay the same deterministic or bounded transition sequence with different delays.

If resulting internal state remains equivalent while elapsed duration changes, this further separates elapsed time from accumulated history.

### 11.3 Compare coordinates

Compare predictive value of:

```text
wall-clock duration
raw transition count
weighted structural-change coordinate
```

Candidate developmental coordinate:

$$
t_{dev}(k)=\sum_{i=0}^{k-1} c(e_i)
$$

where `c(e_i)` is preregistered and value-neutral: it estimates persistent structural consequence, not quality.

---

## 12. Candidate structural-change weights

Possible preregistered components of `c(e_i)`:

- persistent state delta;
- change in future reachability;
- change in relational topology;
- change retained after neutral interval;
- measurable change in response to later matched probes;
- reacquisition bias attributable to retained history.

Weights must be fixed before result inspection for confirmatory analysis.

Exploratory alternatives must be labelled exploratory.

---

## 13. Quantitative, not qualitative

This experiment deliberately avoids the term "qualitative improvement."

The relevant question is **quantitative difference in internal transformation**.

Examples:

```text
larger / smaller state distance
more / fewer changed relations
higher / lower response divergence
larger / smaller reachability delta
more / less retained historical trace
```

None of these imply better or worse.

Quality/value requires a separate evaluator or subject and is outside the primary claim.

---

## 14. Noise and null controls

Required controls:

- byte-identical seeds with identical history, repeated to estimate natural run divergence;
- shuffled labels;
- null events matched for compute where possible;
- event-order shuffle control;
- evaluator blind to condition labels;
- matched probe ordering or counterbalanced probe ordering.

History-induced divergence must exceed the appropriate null/run-noise envelope.

---

## 15. Success criteria

The main thesis gains support if all of the following hold:

1. different histories produce divergence beyond same-history run noise;
2. at least part of that divergence persists after treatment ends;
3. identical later experience produces history-conditioned differential transitions;
4. replay reproduces at least part of the divergence pattern;
5. targeted history ablation changes final divergence in the predicted direction;
6. wall-clock duration alone explains less than a preregistered structural/history coordinate.

Partial support is reported component by component.

---

## 16. Falsification

The thesis is weakened or rejected for the tested system if:

- divergence does not exceed same-history stochastic variation;
- apparent divergence disappears under matched probes;
- replay fails systematically;
- event order has no effect where path dependence was predicted;
- cross-over experience erases prior-history effects completely and reproducibly;
- structural-change coordinates add no information beyond wall-clock and raw transition count;
- measured differences can be fully explained by uncontrolled compute, exposure count or evaluator artifacts.

Negative results are retained.

---

## 17. Claim boundary

A positive run would support only the bounded statement:

> Under controlled conditions, byte-identical adaptive systems can acquire measurably different persistent organization as a function of different histories, and accumulated history may provide a more informative developmental coordinate than elapsed wall-clock time alone.

Do **not** infer from this experiment that:

- one divergent system is better than another;
- greater divergence means greater intelligence;
- divergence is equivalent to maturity;
- a universal developmental clock has been discovered;
- human subjective time and SI internal time are identical;
- physical time is emergent;
- all structural change is irreversible;
- more experience necessarily creates more change.

---

## 18. Relation to Nursery / becoming

The experiment operationalizes a minimal becoming claim:

```text
identical seed
-> different history
-> persistent internal transformation
-> different response to the same later experience
-> further divergence
```

The core object of study is therefore not an isolated state but the causal contribution of the path to the present organization.

In compact form:

> History becomes structure when prior events measurably change the system's later transition landscape.

That is the quantity this run is designed to expose.

---

## Internal anchors

- `docs/theories/2026-07-02-test7-emergence-of-time.md`
- `docs/theories/2026-08-22-time-space-relational-synthesis.md`
- `docs/theories/2026-08-20-framleis-synapse-relational-continuity-convergence.md`
- `docs/theories/2026-08-20-framleis-synapse-regeneration-and-minimum-state.md`
- `docs/hypotheses/2026-08-20-mesh-neuro-ai.md`
