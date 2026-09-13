"""Relational Intelligence Observatory v0.

A zero-dependency falsification instrument for the claim that task-relevant
capability can be carried by higher-order relations and their history rather
than by any single node or current snapshot alone.

This module does not detect consciousness, agency, or extraterrestrial life.
It detects a narrower observable signature: information/function that becomes
available only when relational and/or historical structure is preserved.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass
from typing import Callable, Iterable, Mapping, Sequence

Row = Mapping[str, int]
FeatureSet = Sequence[str]


@dataclass(frozen=True)
class ObservatoryResult:
    node_a_accuracy: float
    node_b_accuracy: float
    snapshot_accuracy: float
    relational_history_accuracy: float
    shuffled_history_accuracy: float
    rewired_relation_accuracy: float

    @property
    def synergy_gain(self) -> float:
        return self.relational_history_accuracy - max(
            self.node_a_accuracy,
            self.node_b_accuracy,
            self.snapshot_accuracy,
        )

    @property
    def history_dependence(self) -> float:
        return self.relational_history_accuracy - self.shuffled_history_accuracy

    @property
    def relation_specificity(self) -> float:
        return self.relational_history_accuracy - self.rewired_relation_accuracy

    def candidate_signature(
        self,
        *,
        min_full_accuracy: float = 0.95,
        min_gain: float = 0.20,
        min_ablation_drop: float = 0.20,
    ) -> bool:
        """Return True only for a bounded relational/historical signature.

        This is deliberately conservative. A positive result is a candidate
        signature for further falsification, never proof of intelligence.
        """

        return (
            self.relational_history_accuracy >= min_full_accuracy
            and self.synergy_gain >= min_gain
            and self.history_dependence >= min_ablation_drop
            and self.relation_specificity >= min_ablation_drop
        )


def bayes_optimal_accuracy(rows: Iterable[Row], features: FeatureSet, target: str = "y") -> float:
    """Empirical Bayes-optimal classification accuracy for discrete features."""

    grouped: dict[tuple[int, ...], Counter[int]] = defaultdict(Counter)
    total = 0
    for row in rows:
        key = tuple(row[name] for name in features)
        grouped[key][row[target]] += 1
        total += 1

    if total == 0:
        raise ValueError("rows must not be empty")

    correct = sum(max(counts.values()) for counts in grouped.values())
    return correct / total


def _rotate(values: Sequence[int], shift: int = 1) -> list[int]:
    if not values:
        return []
    shift %= len(values)
    return list(values[-shift:] + values[:-shift]) if shift else list(values)


def ablate_history(rows: Sequence[Row]) -> list[dict[str, int]]:
    """Break temporal alignment while preserving current-node marginals."""

    prev_a = _rotate([row["prev_a"] for row in rows], 1)
    prev_b = _rotate([row["prev_b"] for row in rows], 5)
    out: list[dict[str, int]] = []
    for idx, row in enumerate(rows):
        copy = dict(row)
        copy["prev_a"] = prev_a[idx]
        copy["prev_b"] = prev_b[idx]
        out.append(copy)
    return out


def rewire_relation(rows: Sequence[Row]) -> list[dict[str, int]]:
    """Preserve node values but pair each previous A with the wrong previous B."""

    prev_b = _rotate([row["prev_b"] for row in rows], 3)
    out: list[dict[str, int]] = []
    for idx, row in enumerate(rows):
        copy = dict(row)
        copy["prev_b"] = prev_b[idx]
        out.append(copy)
    return out


def observe(rows: Sequence[Row]) -> ObservatoryResult:
    """Measure node, snapshot, relational-history and ablation performance."""

    full_features = ("a", "b", "prev_a", "prev_b")
    shuffled = ablate_history(rows)
    rewired = rewire_relation(rows)

    return ObservatoryResult(
        node_a_accuracy=bayes_optimal_accuracy(rows, ("a",)),
        node_b_accuracy=bayes_optimal_accuracy(rows, ("b",)),
        snapshot_accuracy=bayes_optimal_accuracy(rows, ("a", "b")),
        relational_history_accuracy=bayes_optimal_accuracy(rows, full_features),
        shuffled_history_accuracy=_frozen_predictor_accuracy(rows, shuffled, full_features),
        rewired_relation_accuracy=_frozen_predictor_accuracy(rows, rewired, full_features),
    )


def _majority_predictor(rows: Sequence[Row], features: FeatureSet, target: str = "y") -> Callable[[Row], int]:
    grouped: dict[tuple[int, ...], Counter[int]] = defaultdict(Counter)
    global_counts: Counter[int] = Counter()
    for row in rows:
        key = tuple(row[name] for name in features)
        grouped[key][row[target]] += 1
        global_counts[row[target]] += 1

    fallback = global_counts.most_common(1)[0][0]
    table = {key: counts.most_common(1)[0][0] for key, counts in grouped.items()}

    def predict(row: Row) -> int:
        key = tuple(row[name] for name in features)
        return table.get(key, fallback)

    return predict


def _frozen_predictor_accuracy(
    train_rows: Sequence[Row],
    test_rows: Sequence[Row],
    features: FeatureSet,
    target: str = "y",
) -> float:
    predictor = _majority_predictor(train_rows, features, target)
    correct = sum(int(predictor(row) == row[target]) for row in test_rows)
    return correct / len(test_rows)


def synthetic_path_dependent_rows(repeats: int = 16) -> list[dict[str, int]]:
    """Balanced synthetic corpus with a deliberately relational target.

    y = XOR(current A, current B, previous A, previous B)

    No current node or current pair alone determines y. The exact previous
    relation is required. This dataset validates the instrument only; it is
    not evidence that natural intelligence has this form.
    """

    rows: list[dict[str, int]] = []
    for _ in range(repeats):
        for prev_a in (0, 1):
            for prev_b in (0, 1):
                for a in (0, 1):
                    for b in (0, 1):
                        rows.append(
                            {
                                "a": a,
                                "b": b,
                                "prev_a": prev_a,
                                "prev_b": prev_b,
                                "y": a ^ b ^ prev_a ^ prev_b,
                            }
                        )
    return rows


def main() -> None:
    rows = synthetic_path_dependent_rows()
    result = observe(rows)
    print(result)
    print(f"synergy_gain={result.synergy_gain:.3f}")
    print(f"history_dependence={result.history_dependence:.3f}")
    print(f"relation_specificity={result.relation_specificity:.3f}")
    print(f"candidate_signature={result.candidate_signature()}")


if __name__ == "__main__":
    main()
