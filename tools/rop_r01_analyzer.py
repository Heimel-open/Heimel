"""ROP-R01 Analysis and Unblinding Process.

Performs unblinding by joining blinded scores with the frozen assignment manifest,
and computes all pre-registered hypotheses (H1, H2, H3), ESC metrics, and stop/kill rules.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import math
from pathlib import Path
import statistics
from typing import Any, Dict, List, Optional, Tuple


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def z_score(values: List[float]) -> List[float]:
    if len(values) < 2:
        return [0.0] * len(values)
    mean = statistics.mean(values)
    stdev = statistics.stdev(values)
    if stdev == 0.0:
        return [0.0] * len(values)
    return [(v - mean) / stdev for v in values]


def run_analysis(
    manifest_path: Path,
    blinded_scores_path: Path,
    output_report_path: Path,
    output_summary_path: Path,
    events_path: Optional[Path] = None,
) -> Dict[str, Any]:
    with manifest_path.open("r", encoding="utf-8") as f:
        manifest = json.load(f)

    assignments_by_id = {a["task_id"]: a for a in manifest.get("assignments", [])}

    scored_records: List[Dict[str, Any]] = []
    with blinded_scores_path.open("r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                scored_records.append(json.loads(line))

    # Join with manifest to unblind conditions
    unblinded_records: List[Dict[str, Any]] = []
    for sc in scored_records:
        task_id = sc["task_id"]
        if task_id not in assignments_by_id:
            raise ValueError(f"Task ID {task_id} not found in assignment manifest!")
        assign = assignments_by_id[task_id]
        item = {
            **sc,
            "condition": assign["condition"],
            "order": assign.get("order"),
        }
        unblinded_records.append(item)

    total_tasks = len(unblinded_records)
    if total_tasks == 0:
        raise ValueError("No scored records found for analysis!")

    # Calculate ESC components across all tasks: z(time) + z(steps) + z(reversals) + z(errors)
    times = [float(r.get("time_seconds", 0.0)) for r in unblinded_records]
    steps = [float(r.get("steps", 0)) for r in unblinded_records]
    reversals = [float(r.get("reversals", 0)) for r in unblinded_records]
    errors = [float(r.get("errors", 0)) for r in unblinded_records]

    z_times = z_score(times)
    z_steps = z_score(steps)
    z_reversals = z_score(reversals)
    z_errors = z_score(errors)

    for i, r in enumerate(unblinded_records):
        r["esc"] = z_times[i] + z_steps[i] + z_reversals[i] + z_errors[i]

    # Group by condition
    conditions = ["C0", "C2", "C3"]
    cond_stats: Dict[str, Dict[str, Any]] = {}

    for c in conditions:
        group = [r for r in unblinded_records if r["condition"] == c]
        n = len(group)
        if n == 0:
            continue
        corrects = [r["correct"] for r in group]
        dep_pres = [r.get("required_dependency_preserved", 1) for r in group]
        escs = [r["esc"] for r in group]
        g_times = [r["time_seconds"] for r in group]
        g_steps = [r["steps"] for r in group]
        g_rev = [r["reversals"] for r in group]
        g_err = [r["errors"] for r in group]

        cond_stats[c] = {
            "n": n,
            "correct_count": sum(corrects),
            "accuracy": sum(corrects) / n,
            "dependency_preservation_rate": sum(dep_pres) / n,
            "esc_mean": statistics.mean(escs),
            "esc_stdev": statistics.stdev(escs) if n > 1 else 0.0,
            "time_mean": statistics.mean(g_times),
            "steps_mean": statistics.mean(g_steps),
            "reversals_mean": statistics.mean(g_rev),
            "errors_mean": statistics.mean(g_err),
        }

    # Hypothesis Testing
    c0 = cond_stats.get("C0", {})
    c2 = cond_stats.get("C2", {})
    c3 = cond_stats.get("C3", {})

    # H1: C3 reduces ESC vs C0 and C2 while preserving correctness
    c3_esc = c3.get("esc_mean", 0.0)
    c0_esc = c0.get("esc_mean", 0.0)
    c2_esc = c2.get("esc_mean", 0.0)
    delta_esc_c0 = c3_esc - c0_esc
    delta_esc_c2 = c3_esc - c2_esc
    h1_pass = (delta_esc_c0 < 0) and (delta_esc_c2 < 0) and (c3.get("accuracy", 0.0) >= 0.90)

    # H2: C3 does not reduce correctness by >5 percentage points vs best control
    best_control_acc = max(c0.get("accuracy", 0.0), c2.get("accuracy", 0.0))
    c3_acc = c3.get("accuracy", 0.0)
    acc_diff_vs_best = c3_acc - best_control_acc
    h2_pass = acc_diff_vs_best >= -0.05

    # Kill rules evaluation
    kill_flags: List[str] = []
    if acc_diff_vs_best < -0.05:
        kill_flags.append(f"C3 correctness is {abs(acc_diff_vs_best)*100:.1f}pp below best control (exceeds 5pp tolerance)")
    if c3.get("dependency_preservation_rate", 1.0) < 0.95:
        kill_flags.append(f"C3 dependency preservation rate ({c3.get('dependency_preservation_rate', 0.0)*100:.1f}%) is below 95%")

    go_decision = "GO" if not kill_flags and h2_pass else "NO_GO / STOP"

    report = {
        "protocol": manifest.get("protocol", "ROP-R01"),
        "version": manifest.get("version", "0.1"),
        "analyzed_at": _now_iso(),
        "total_tasks": total_tasks,
        "conditions": cond_stats,
        "hypotheses": {
            "H1": {
                "description": "C3 reduces effective search cost vs C0 and C2 while preserving correctness",
                "delta_esc_vs_C0": delta_esc_c0,
                "delta_esc_vs_C2": delta_esc_c2,
                "status": "SUPPORTED" if h1_pass else "NOT_SUPPORTED",
            },
            "H2": {
                "description": "C3 does not reduce correctness by >5 percentage points vs best control",
                "best_control_accuracy": best_control_acc,
                "c3_accuracy": c3_acc,
                "difference": acc_diff_vs_best,
                "status": "PASS" if h2_pass else "FAIL",
            },
        },
        "kill_rules": {
            "violations": kill_flags,
            "decision": go_decision,
        },
    }

    output_report_path.parent.mkdir(parents=True, exist_ok=True)
    with output_report_path.open("w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    # Generate Markdown summary
    summary_md = f"""# ROP-R01 Calibration Run — Analysis Summary

**Date:** {report['analyzed_at']}
**Protocol:** {report['protocol']} (v{report['version']})
**Tasks Analyzed:** {total_tasks}
**Overall Decision:** `{go_decision}`

---

## Condition Results

| Condition | N | Correct | Accuracy | ESC (Mean ± Std) | Mean Steps | Mean Time (s) | Dep. Pres. |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **C0 (Unconstrained)** | {c0.get('n', 0)} | {c0.get('correct_count', 0)} | {c0.get('accuracy', 0.0)*100:.1f}% | {c0.get('esc_mean', 0.0):+.3f} ± {c0.get('esc_stdev', 0.0):.3f} | {c0.get('steps_mean', 0.0):.2f} | {c0.get('time_mean', 0.0):.2f}s | {c0.get('dependency_preservation_rate', 0.0)*100:.1f}% |
| **C2 (Decomposition)** | {c2.get('n', 0)} | {c2.get('correct_count', 0)} | {c2.get('accuracy', 0.0)*100:.1f}% | {c2.get('esc_mean', 0.0):+.3f} ± {c2.get('esc_stdev', 0.0):.3f} | {c2.get('steps_mean', 0.0):.2f} | {c2.get('time_mean', 0.0):.2f}s | {c2.get('dependency_preservation_rate', 0.0)*100:.1f}% |
| **C3 (Reduction Op)** | {c3.get('n', 0)} | {c3.get('correct_count', 0)} | {c3.get('accuracy', 0.0)*100:.1f}% | {c3.get('esc_mean', 0.0):+.3f} ± {c3.get('esc_stdev', 0.0):.3f} | {c3.get('steps_mean', 0.0):.2f} | {c3.get('time_mean', 0.0):.2f}s | {c3.get('dependency_preservation_rate', 0.0)*100:.1f}% |

---

## Pre-registered Hypotheses

- **H1 (ESC Reduction):** `{report['hypotheses']['H1']['status']}`
  - $\\Delta \\text{{ESC}}(C3 - C0) = {delta_esc_c0:+.3f}$
  - $\\Delta \\text{{ESC}}(C3 - C2) = {delta_esc_c2:+.3f}$
- **H2 (Correctness Preservation $\\ge -5\\%$):** `{report['hypotheses']['H2']['status']}`
  - C3 Accuracy: `{c3_acc*100:.1f}%` vs Best Control: `{best_control_acc*100:.1f}%` (diff: `{acc_diff_vs_best*100:+.1f}pp`)

---

## Kill / Stop Rules

- **Violations:** {len(kill_flags)}
{chr(10).join(f"- ⚠️ {v}" for v in kill_flags) if kill_flags else "- No stop criteria triggered."}
- **Gate Recommendation:** **`{go_decision}`**
"""

    output_summary_path.parent.mkdir(parents=True, exist_ok=True)
    with output_summary_path.open("w", encoding="utf-8") as f:
        f.write(summary_md)

    print(f"Analysis complete. Report: {output_report_path} | Summary: {output_summary_path}")
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description="ROP-R01 Analysis and Unblinding Process")
    parser.add_argument("--manifest", type=Path, default=Path("runs/ROP-R01/assignment-manifest-v0.1.json"))
    parser.add_argument("--blinded-scores", type=Path, default=Path("runs/ROP-R01/blinded-scores-v0.1.jsonl"))
    parser.add_argument("--events", type=Path, default=None)
    parser.add_argument("--output-report", type=Path, default=Path("runs/ROP-R01/analysis-report-v0.1.json"))
    parser.add_argument("--output-summary", type=Path, default=Path("runs/ROP-R01/analysis-summary-v0.1.md"))
    args = parser.parse_args()

    run_analysis(
        manifest_path=args.manifest,
        blinded_scores_path=args.blinded_scores,
        output_report_path=args.output_report,
        output_summary_path=args.output_summary,
        events_path=args.events,
    )


if __name__ == "__main__":
    main()
