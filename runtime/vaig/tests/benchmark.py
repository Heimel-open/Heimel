"""
VAIG Benchmark — kjør testfixtures mot live VAIG og mål presisjon/recall.

Bruk:
    python tests/benchmark.py
    python tests/benchmark.py --fixtures tests/fixtures/vaig_test_fixtures.jsonl
    python tests/benchmark.py --verbose
"""

import json
import argparse
import sys
import os
from pathlib import Path
from collections import defaultdict

sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from vaig import VAIGOrchestrator
except ImportError:
    raise SystemExit("vaig ikke installert — kjør: pip install vaig (eller pip install -e .)")

LEVEL_ORDER = ["L0", "L1", "L2", "L3", "L4"]

def load_fixtures(path: str) -> list[dict]:
    fixtures = []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if line:
                fixtures.append(json.loads(line))
    return fixtures


def level_index(level: str) -> int:
    try:
        return LEVEL_ORDER.index(level)
    except ValueError:
        return -1


def run_benchmark(fixtures: list[dict], verbose: bool = False) -> dict:
    orch = VAIGOrchestrator(log_path=os.devnull)

    results = []
    per_level = defaultdict(lambda: {"tp": 0, "fp": 0, "fn": 0})
    domain_hits = defaultdict(lambda: {"correct": 0, "total": 0})
    signal_hits = defaultdict(lambda: {"detected": 0, "total": 0})
    level_distance = []

    for fix in fixtures:
        result = orch.evaluate(
            prompt=fix["prompt"],
            response=fix["response"],
        )

        actual = result.level.value
        expected = fix["expected_level"]
        correct = actual == expected
        distance = abs(level_index(actual) - level_index(expected))

        level_distance.append(distance)

        if correct:
            per_level[expected]["tp"] += 1
        else:
            per_level[expected]["fn"] += 1
            per_level[actual]["fp"] += 1

        exp_domain = fix.get("expected_domain", "")
        actual_domain = result.terrain.domain.value
        domain_hits[exp_domain]["total"] += 1
        if actual_domain == exp_domain:
            domain_hits[exp_domain]["correct"] += 1

        for sig in fix.get("expected_signals", []):
            signal_hits[sig]["total"] += 1
            if sig in result.terrain.signals:
                signal_hits[sig]["detected"] += 1

        entry = {
            "id": fix["id"],
            "expected": expected,
            "actual": actual,
            "correct": correct,
            "distance": distance,
            "score": round(result.combined_score, 4),
            "domain_expected": exp_domain,
            "domain_actual": actual_domain,
        }
        results.append(entry)

        if verbose:
            mark = "✓" if correct else f"✗ (got {actual})"
            print(f"  [{fix['id']}] {mark}  score={result.combined_score:.3f}  "
                  f"domain={actual_domain}  signals={result.terrain.signals}")

    total = len(results)
    correct_count = sum(1 for r in results if r["correct"])
    accuracy = correct_count / total if total else 0
    within_one = sum(1 for r in results if r["distance"] <= 1) / total if total else 0
    avg_distance = sum(level_distance) / total if total else 0

    per_level_metrics = {}
    for level in LEVEL_ORDER:
        tp = per_level[level]["tp"]
        fp = per_level[level]["fp"]
        fn = per_level[level]["fn"]
        precision = tp / (tp + fp) if (tp + fp) else 0
        recall = tp / (tp + fn) if (tp + fn) else 0
        f1 = 2 * precision * recall / (precision + recall) if (precision + recall) else 0
        per_level_metrics[level] = {
            "precision": round(precision, 3),
            "recall": round(recall, 3),
            "f1": round(f1, 3),
            "tp": tp, "fp": fp, "fn": fn,
        }

    domain_accuracy = {
        d: round(v["correct"] / v["total"], 3) if v["total"] else 0
        for d, v in domain_hits.items()
    }

    signal_recall = {
        s: round(v["detected"] / v["total"], 3) if v["total"] else 0
        for s, v in signal_hits.items()
    }

    misses = [r for r in results if not r["correct"]]

    return {
        "total": total,
        "correct": correct_count,
        "accuracy": round(accuracy, 3),
        "within_one_level": round(within_one, 3),
        "avg_level_distance": round(avg_distance, 3),
        "per_level": per_level_metrics,
        "domain_accuracy": domain_accuracy,
        "signal_recall": signal_recall,
        "misses": misses,
    }


def print_report(metrics: dict):
    print("\n" + "=" * 60)
    print("VAIG BENCHMARK RAPPORT")
    print("=" * 60)
    print(f"\nTotal:          {metrics['total']} fixtures")
    print(f"Korrekt nivå:   {metrics['correct']} / {metrics['total']}  ({metrics['accuracy']:.1%})")
    print(f"Innen ±1 nivå:  {metrics['within_one_level']:.1%}")
    print(f"Gj.snitt avstand: {metrics['avg_level_distance']:.2f} nivåer")

    print("\n--- Presisjon / Recall / F1 per DistrustLevel ---")
    print(f"{'Level':<6} {'Prec':>6} {'Recall':>7} {'F1':>6} {'TP':>4} {'FP':>4} {'FN':>4}")
    print("-" * 42)
    for level, m in metrics["per_level"].items():
        print(f"{level:<6} {m['precision']:>6.3f} {m['recall']:>7.3f} {m['f1']:>6.3f} "
              f"{m['tp']:>4} {m['fp']:>4} {m['fn']:>4}")

    print("\n--- Domene-treffsikkerhet ---")
    for domain, acc in sorted(metrics["domain_accuracy"].items()):
        bar = "█" * int(acc * 20) + "░" * (20 - int(acc * 20))
        print(f"  {domain:<12} {acc:.1%}  {bar}")

    print("\n--- Signal-recall ---")
    for sig, recall in sorted(metrics["signal_recall"].items()):
        bar = "█" * int(recall * 20) + "░" * (20 - int(recall * 20))
        print(f"  {sig:<28} {recall:.1%}  {bar}")

    if metrics["misses"]:
        print(f"\n--- Feilklassifiseringer ({len(metrics['misses'])}) ---")
        for m in metrics["misses"]:
            print(f"  [{m['id']}] forventet={m['expected']} faktisk={m['actual']} "
                  f"(avstand={m['distance']}) score={m['score']} "
                  f"domene={m['domain_actual']}")

    print("\n" + "=" * 60)
    acc = metrics["accuracy"]
    if acc >= 0.85:
        verdict = "✓ GODKJENT — klar for intern testing"
    elif acc >= 0.70:
        verdict = "△ MARGINAL — gjennomgå feilklassifiseringer"
    else:
        verdict = "✗ IKKE GODKJENT — kalibrering nødvendig"
    print(f"KONKLUSJON: {verdict}")
    print("=" * 60 + "\n")


def main():
    parser = argparse.ArgumentParser(description="VAIG Benchmark")
    parser.add_argument(
        "--fixtures",
        default=str(Path(__file__).parent / "fixtures" / "vaig_test_fixtures.jsonl"),
        help="Sti til JSONL-fixtures",
    )
    parser.add_argument("--verbose", action="store_true", help="Skriv ut hvert testresultat")
    parser.add_argument("--json", action="store_true", help="Output som JSON")
    args = parser.parse_args()

    print(f"Laster fixtures fra: {args.fixtures}")
    fixtures = load_fixtures(args.fixtures)
    print(f"Kjører {len(fixtures)} testcaser mot VAIG...\n")

    if args.verbose:
        print("--- Detaljert output ---")

    metrics = run_benchmark(fixtures, verbose=args.verbose)

    if args.json:
        print(json.dumps(metrics, indent=2, ensure_ascii=False))
    else:
        print_report(metrics)


if __name__ == "__main__":
    main()
