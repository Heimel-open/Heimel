# Coherence metric semantics

VAIG treats preregistered metrics as executable evaluation conditions, not documentation.

Each metric declares:
- `threshold`: the preregistered numeric boundary
- `observed_value`: the measured value
- `comparison`: `GTE` or `LTE`
- `source_ref`: the metric/threshold source
- `locked_before_outcome`: whether the rule was fixed before the measured outcome

VAIG does not infer threshold direction from the metric name or prose. Missing `threshold`, `observed_value`, or `comparison` keeps the evaluation OPEN. A known breach of the declared threshold is FAIL. High-stakes evaluations require metric source lineage in the source register.

These are evaluation semantics only. A VAIG PASS still grants no execution authority and requires downstream REHT clearance.
