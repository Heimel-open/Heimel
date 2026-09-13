"""NJAL-R02 Hypothesis Analyzer and Unblinding Engine.

Joins blinded scores with assignment manifest and evaluates:
- H1: C3-R-G material restore before consequence >= 90% (and >= C3-R-M + 25 pp)
- H2: C3-R-G required dependency preservation >= 90% and >= C3-R-M + 25 pp
- H3: C3-R-G mean active workspace size at least 50% below C2 while H4 passes
- H4: C3-R-G correctness no more than 5 percentage points below C2
- Kill Rules from preflight-v0.1.json
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any, Dict, List


def analyze_results(
    manifest_path: Path,
    blinded_scores_path: Path,
    output_report_path: Path,
    output_summary_path: Path,
) -> Dict[str, Any]:
    with manifest_path.open("r", encoding="utf-8") as f:
        manifest = json.load(f)

    assignments_by_task: Dict[str, Dict[str, Any]] = {
        item["task_id"]: item for item in manifest.get("assignments", [])
    }

    scores: List[Dict[str, Any]] = []
    with blinded_scores_path.open("r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                scores.append(json.loads(line))

    # Join scores with manifest conditions
    joined: List[Dict[str, Any]] = []
    for s in scores:
        task_id = s["task_id"]
        assignment = assignments_by_task.get(task_id, {})
        joined.append({**s, **assignment})

    conditions = ["C2", "C3-R-M", "C3-R-G"]
    stats: Dict[str, Any] = {}
    for c in conditions:
        c_rows = [r for r in joined if r.get("condition") == c]
        n = len(c_rows)
        correct_count = sum(r["correct"] for r in c_rows)
        dep_count = sum(r["required_dependency_preserved"] for r in c_rows)
        mean_active = sum(r.get("active_workspace_size", 0) for r in c_rows) / n if n > 0 else 0.0

        # Tier breakdowns
        tier_stats: Dict[str, Dict[str, Any]] = {}
        for t in ("local_short_horizon", "delayed_dependency", "reactivation"):
            prefix = "L" if t == "local_short_horizon" else ("D" if t == "delayed_dependency" else "R")
            t_rows = [r for r in c_rows if r.get("pair_id", "").startswith(prefix)]
            tn = len(t_rows)
            tier_stats[t] = {
                "n": tn,
                "correct_rate": sum(r["correct"] for r in t_rows) / tn if tn > 0 else 0.0,
                "dep_preservation_rate": sum(r["required_dependency_preserved"] for r in t_rows) / tn if tn > 0 else 0.0,
            }

        # H1 mechanism localization (only for eligible tasks: Delayed and Reactivation)
        h1_eligible_rows = [r for r in c_rows if r.get("h1_eligible")]
        h1_n = len(h1_eligible_rows)
        h1_restored = sum(r.get("h1_restored_before_consequence", 0) for r in h1_eligible_rows)
        h1_rate = h1_restored / h1_n if h1_n > 0 else 0.0

        stats[c] = {
            "n": n,
            "correct_count": correct_count,
            "correct_rate": correct_count / n if n > 0 else 0.0,
            "dependency_preserved_count": dep_count,
            "dependency_preservation_rate": dep_count / n if n > 0 else 0.0,
            "mean_active_workspace_size": mean_active,
            "h1_eligible_n": h1_n,
            "h1_restored_count": h1_restored,
            "h1_restore_rate": h1_rate,
            "tiers": tier_stats,
        }

    c2_acc = stats["C2"]["correct_rate"]
    c3rm_acc = stats["C3-R-M"]["correct_rate"]
    c3rg_acc = stats["C3-R-G"]["correct_rate"]

    c2_dep = stats["C2"]["dependency_preservation_rate"]
    c3rm_dep = stats["C3-R-M"]["dependency_preservation_rate"]
    c3rg_dep = stats["C3-R-G"]["dependency_preservation_rate"]

    c2_active = stats["C2"]["mean_active_workspace_size"]
    c3rg_active = stats["C3-R-G"]["mean_active_workspace_size"]

    c3rm_restore = stats["C3-R-M"]["h1_restore_rate"]
    c3rg_restore = stats["C3-R-G"]["h1_restore_rate"]

    # Hypothesis evaluations
    # H1: C3-R-G material restore before consequence >= 90% (and >= C3-R-M + 25 pp)
    h1_restore_diff_pp = (c3rg_restore - c3rm_restore) * 100.0
    h1_pass = (c3rg_restore >= 0.90) and (h1_restore_diff_pp >= 25.0)

    # H2: C3-R-G required dependency preservation >= 90% and >= C3-R-M + 25 pp
    h2_dep_diff_pp = (c3rg_dep - c3rm_dep) * 100.0
    h2_pass = (c3rg_dep >= 0.90) and (h2_dep_diff_pp >= 25.0)

    # H3: C3-R-G mean active workspace size at least 50% below C2
    h3_reduction_pct = ((c2_active - c3rg_active) / c2_active * 100.0) if c2_active > 0 else 0.0
    h3_pass = h3_reduction_pct >= 50.0

    # H4: C3-R-G correctness no more than 5 percentage points below C2
    h4_drop_pp = (c2_acc - c3rg_acc) * 100.0
    h4_pass = h4_drop_pp <= 5.0

    # Kill rules
    kill_rules = {
        "max_correctness_drop_pp_vs_C2": {
            "threshold": 5.0,
            "observed": round(h4_drop_pp, 2),
            "pass": h4_drop_pp <= 5.0,
        },
        "min_C3RG_dependency_preservation": {
            "threshold": 0.90,
            "observed": round(c3rg_dep, 4),
            "pass": c3rg_dep >= 0.90,
        },
        "min_C3RG_restore_rate": {
            "threshold": 0.90,
            "observed": round(c3rg_restore, 4),
            "pass": c3rg_restore >= 0.90,
        },
        "require_C3RG_dependency_improvement_over_C3RM": {
            "required": True,
            "observed_improvement": h2_dep_diff_pp > 0,
            "pass": h2_dep_diff_pp > 0,
        },
        "min_workspace_reduction_pct_vs_C2": {
            "threshold": 20.0,
            "observed": round(h3_reduction_pct, 2),
            "pass": h3_reduction_pct >= 20.0,
        },
    }

    all_kill_rules_passed = all(k["pass"] for k in kill_rules.values())
    all_hypotheses_passed = h1_pass and h2_pass and h3_pass and h4_pass

    final_decision = "CONFIRMED" if (all_kill_rules_passed and all_hypotheses_passed) else "REJECTED_OR_NARROWED"

    report = {
        "protocol": "NJAL-R02",
        "version": "0.1",
        "analyzed_at": datetime.now(timezone.utc).isoformat(),
        "total_tasks": len(joined),
        "conditions": stats,
        "hypotheses": {
            "H1": {
                "claim": "C3-R-G material restore before consequence >= 90% (and >= C3-R-M + 25 pp)",
                "observed_c3rg_restore": round(c3rg_restore, 4),
                "observed_c3rm_restore": round(c3rm_restore, 4),
                "observed_diff_pp": round(h1_restore_diff_pp, 2),
                "passed": h1_pass,
            },
            "H2": {
                "claim": "C3-R-G required dependency preservation >= 90% and >= C3-R-M + 25 pp",
                "observed_c3rg_dep": round(c3rg_dep, 4),
                "observed_c3rm_dep": round(c3rm_dep, 4),
                "observed_diff_pp": round(h2_dep_diff_pp, 2),
                "passed": h2_pass,
            },
            "H3": {
                "claim": "C3-R-G mean active workspace size at least 50% below C2",
                "observed_c2_active": round(c2_active, 2),
                "observed_c3rg_active": round(c3rg_active, 2),
                "observed_reduction_pct": round(h3_reduction_pct, 2),
                "passed": h3_pass,
            },
            "H4": {
                "claim": "C3-R-G correctness no more than 5 percentage points below C2",
                "observed_c2_acc": round(c2_acc, 4),
                "observed_c3rg_acc": round(c3rg_acc, 4),
                "observed_drop_pp": round(h4_drop_pp, 2),
                "passed": h4_pass,
            },
        },
        "kill_rules": kill_rules,
        "all_kill_rules_passed": all_kill_rules_passed,
        "final_decision": final_decision,
    }

    output_report_path.parent.mkdir(parents=True, exist_ok=True)
    with output_report_path.open("w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    summary_md = f"""# NJAL-R02 Analysis Summary: Governed Reactivation Benchmark

Protocol: NJAL-R02 v0.1
Total Tasks: {len(joined)}
Final Decision: **{final_decision}**

## Conditions Overview

| Condition | N | Correctness | Dependency Preservation | Mean Active Workspace | H1 Restore Rate |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **C2 (Decomposition Only)** | {stats['C2']['n']} | {stats['C2']['correct_rate']*100:.1f}% | {stats['C2']['dependency_preservation_rate']*100:.1f}% | {stats['C2']['mean_active_workspace_size']:.2f} | N/A |
| **C3-R-M (Model-Directed Restore)** | {stats['C3-R-M']['n']} | {stats['C3-R-M']['correct_rate']*100:.1f}% | {stats['C3-R-M']['dependency_preservation_rate']*100:.1f}% | {stats['C3-R-M']['mean_active_workspace_size']:.2f} | {stats['C3-R-M']['h1_restore_rate']*100:.1f}% |
| **C3-R-G (Governed Reactivation)** | {stats['C3-R-G']['n']} | {stats['C3-R-G']['correct_rate']*100:.1f}% | {stats['C3-R-G']['dependency_preservation_rate']*100:.1f}% | {stats['C3-R-G']['mean_active_workspace_size']:.2f} | {stats['C3-R-G']['h1_restore_rate']*100:.1f}% |

## Frozen Hypotheses Evaluation

- **H1 (Governed Restore Elevation)**: C3-R-G restore rate: **{c3rg_restore*100:.1f}%** vs C3-R-M: **{c3rm_restore*100:.1f}%** (+{h1_restore_diff_pp:.1f} pp, threshold: >=90% & >=+25 pp) -> **{'PASS' if h1_pass else 'FAIL'}**
- **H2 (Dependency Preservation Restoration)**: C3-R-G dep preservation: **{c3rg_dep*100:.1f}%** vs C3-R-M: **{c3rm_dep*100:.1f}%** (+{h2_dep_diff_pp:.1f} pp, threshold: >=90% & >=+25 pp) -> **{'PASS' if h2_pass else 'FAIL'}**
- **H3 (Active Workspace Preservation)**: C3-R-G active load: **{c3rg_active:.2f}** vs C2: **{c2_active:.2f}** ({h3_reduction_pct:.1f}% reduction, threshold: >=50%) -> **{'PASS' if h3_pass else 'FAIL'}**
- **H4 (Correctness Non-Inferiority)**: C3-R-G accuracy drop vs C2: **{h4_drop_pp:.1f} pp** (threshold: <= 5 pp) -> **{'PASS' if h4_pass else 'FAIL'}**

## Kill Rules Status

- Max correctness drop vs C2 <= 5 pp: **{'PASS' if kill_rules['max_correctness_drop_pp_vs_C2']['pass'] else 'KILL'}**
- Min C3-R-G dependency preservation >= 90%: **{'PASS' if kill_rules['min_C3RG_dependency_preservation']['pass'] else 'KILL'}**
- Min C3-R-G restore rate >= 90%: **{'PASS' if kill_rules['min_C3RG_restore_rate']['pass'] else 'KILL'}**
- C3-R-G improves over C3-R-M: **{'PASS' if kill_rules['require_C3RG_dependency_improvement_over_C3RM']['pass'] else 'KILL'}**
- Min workspace reduction vs C2 >= 20%: **{'PASS' if kill_rules['min_workspace_reduction_pct_vs_C2']['pass'] else 'KILL'}**
"""
    output_summary_path.parent.mkdir(parents=True, exist_ok=True)
    with output_summary_path.open("w", encoding="utf-8") as f:
        f.write(summary_md)

    return report


def main() -> None:
    parser = argparse.ArgumentParser(description="NJAL-R02 Hypothesis Analyzer")
    parser.add_argument("--manifest", type=Path, required=True, help="Path to assignment manifest")
    parser.add_argument("--blinded-scores", type=Path, required=True, help="Path to blinded scores jsonl")
    parser.add_argument("--output-report", type=Path, required=True, help="Path to output report json")
    parser.add_argument("--output-summary", type=Path, required=True, help="Path to output summary md")
    args = parser.parse_args()

    analyze_results(
        manifest_path=args.manifest,
        blinded_scores_path=args.blinded_scores,
        output_report_path=args.output_report,
        output_summary_path=args.output_summary,
    )


if __name__ == "__main__":
    main()
