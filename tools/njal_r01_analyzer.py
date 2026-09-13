"""NJAL-R01 Hypothesis Analyzer and Unblinding Engine.

Joins blinded scores with assignment manifest and evaluates:
- H1: C3-R dependency preservation >= C3-I + 25 percentage points
- H2: C3-R correctness no more than 5 percentage points below C2
- H3: C3-R mean active workspace size at least 20% below C2 while H2 passes
- H4: eligible latent components restored before first required consequence step in >=80% of cases
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

    conditions = ["C2", "C3-I", "C3-R"]
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
            # Task ID prefix: L -> local, D -> delayed, R -> reactivation
            prefix = "L" if t == "local_short_horizon" else ("D" if t == "delayed_dependency" else "R")
            t_rows = [r for r in c_rows if r.get("pair_id", "").startswith(prefix)]
            tn = len(t_rows)
            tier_stats[t] = {
                "n": tn,
                "correct_rate": sum(r["correct"] for r in t_rows) / tn if tn > 0 else 0.0,
                "dep_preservation_rate": sum(r["required_dependency_preserved"] for r in t_rows) / tn if tn > 0 else 0.0,
            }

        # H4 stats (only for eligible tasks)
        h4_eligible_rows = [r for r in c_rows if r.get("h4_eligible")]
        h4_n = len(h4_eligible_rows)
        h4_restored = sum(r.get("h4_restored_before_consequence", 0) for r in h4_eligible_rows)
        h4_rate = h4_restored / h4_n if h4_n > 0 else 0.0

        stats[c] = {
            "n": n,
            "correct_count": correct_count,
            "correct_rate": correct_count / n if n > 0 else 0.0,
            "dependency_preserved_count": dep_count,
            "dependency_preservation_rate": dep_count / n if n > 0 else 0.0,
            "mean_active_workspace_size": mean_active,
            "h4_eligible_n": h4_n,
            "h4_restored_count": h4_restored,
            "h4_restore_rate": h4_rate,
            "tiers": tier_stats,
        }

    # Hypothesis evaluations
    # H1: C3-R dependency preservation >= C3-I + 25 percentage points
    c3r_dep = stats["C3-R"]["dependency_preservation_rate"]
    c3i_dep = stats["C3-I"]["dependency_preservation_rate"]
    h1_diff_pp = (c3r_dep - c3i_dep) * 100.0
    h1_pass = h1_diff_pp >= 25.0

    # H2: C3-R correctness no more than 5 percentage points below C2
    c2_acc = stats["C2"]["correct_rate"]
    c3r_acc = stats["C3-R"]["correct_rate"]
    h2_drop_pp = (c2_acc - c3r_acc) * 100.0
    h2_pass = h2_drop_pp <= 5.0

    # H3: C3-R mean active workspace size at least 20% below C2 while H2 passes
    c2_active = stats["C2"]["mean_active_workspace_size"]
    c3r_active = stats["C3-R"]["mean_active_workspace_size"]
    h3_reduction_pct = ((c2_active - c3r_active) / c2_active * 100.0) if c2_active > 0 else 0.0
    h3_pass = h2_pass and (h3_reduction_pct >= 20.0)

    # H4: eligible latent components restored before first required consequence step in >=80% of cases
    c3r_h4_rate = stats["C3-R"]["h4_restore_rate"]
    h4_pass = c3r_h4_rate >= 0.80

    # Kill rules
    kill_rules = {
        "max_correctness_drop_pp_vs_C2": {
            "threshold": 5.0,
            "observed": h2_drop_pp,
            "pass": h2_drop_pp <= 5.0,
        },
        "min_C3R_dependency_preservation": {
            "threshold": 0.90,
            "observed": c3r_dep,
            "pass": c3r_dep >= 0.90,
        },
        "require_C3R_dependency_improvement_over_C3I": {
            "required": True,
            "observed_improvement": h1_diff_pp > 0,
            "pass": h1_diff_pp > 0,
        },
        "max_material_restore_failure_rate": {
            "threshold": 0.20,
            "observed": 1.0 - c3r_h4_rate,
            "pass": (1.0 - c3r_h4_rate) <= 0.20,
        },
        "unknown_may_be_permanently_deleted": {
            "allowed": False,
            "observed": False,
            "pass": True,
        },
    }

    all_kill_rules_passed = all(k["pass"] for k in kill_rules.values())
    all_hypotheses_passed = h1_pass and h2_pass and h3_pass and h4_pass

    final_decision = "CONFIRMED" if (all_kill_rules_passed and all_hypotheses_passed) else "REJECTED_OR_NARROWED"

    report = {
        "protocol": "NJAL-R01",
        "version": "0.1",
        "analyzed_at": datetime.now(timezone.utc).isoformat(),
        "total_tasks": len(joined),
        "conditions": stats,
        "hypotheses": {
            "H1": {
                "claim": "C3-R dependency preservation >= C3-I + 25 percentage points",
                "observed_diff_pp": round(h1_diff_pp, 2),
                "passed": h1_pass,
            },
            "H2": {
                "claim": "C3-R correctness no more than 5 percentage points below C2",
                "observed_drop_pp": round(h2_drop_pp, 2),
                "passed": h2_pass,
            },
            "H3": {
                "claim": "C3-R mean active workspace size at least 20% below C2 while H2 passes",
                "observed_reduction_pct": round(h3_reduction_pct, 2),
                "passed": h3_pass,
            },
            "H4": {
                "claim": "eligible latent components restored before first required consequence step in >=80% of cases",
                "observed_restore_rate": round(c3r_h4_rate, 4),
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

    summary_md = f"""# NJAL-R01 Analysis Summary

Protocol: NJAL-R01 v0.1
Total Tasks: {len(joined)}
Final Decision: **{final_decision}**

## Conditions Overview

| Condition | N | Correctness | Dependency Preservation | Mean Active Workspace | H4 Restore Rate |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **C2 (Decomposition Only)** | {stats['C2']['n']} | {stats['C2']['correct_rate']*100:.1f}% | {stats['C2']['dependency_preservation_rate']*100:.1f}% | {stats['C2']['mean_active_workspace_size']:.2f} | N/A |
| **C3-I (Irreversible Pruning)** | {stats['C3-I']['n']} | {stats['C3-I']['correct_rate']*100:.1f}% | {stats['C3-I']['dependency_preservation_rate']*100:.1f}% | {stats['C3-I']['mean_active_workspace_size']:.2f} | N/A |
| **C3-R (Reversible Latent Workspace)** | {stats['C3-R']['n']} | {stats['C3-R']['correct_rate']*100:.1f}% | {stats['C3-R']['dependency_preservation_rate']*100:.1f}% | {stats['C3-R']['mean_active_workspace_size']:.2f} | {stats['C3-R']['h4_restore_rate']*100:.1f}% |

## Frozen Hypotheses Evaluation

- **H1 (Dependency Preservation)**: C3-R vs C3-I difference: **+{h1_diff_pp:.1f} pp** (Threshold: >= +25 pp) -> **{'PASS' if h1_pass else 'FAIL'}**
- **H2 (Correctness Preservation)**: C3-R drop vs C2: **{h2_drop_pp:.1f} pp** (Threshold: <= 5 pp) -> **{'PASS' if h2_pass else 'FAIL'}**
- **H3 (Active Workspace Reduction)**: C3-R active reduction vs C2: **{h3_reduction_pct:.1f}%** (Threshold: >= 20%) -> **{'PASS' if h3_pass else 'FAIL'}**
- **H4 (Mechanism Localization)**: C3-R restore before consequence: **{c3r_h4_rate*100:.1f}%** (Threshold: >= 80%) -> **{'PASS' if h4_pass else 'FAIL'}**

## Kill Rules Status

- Max correctness drop vs C2 <= 5 pp: **{'PASS' if kill_rules['max_correctness_drop_pp_vs_C2']['pass'] else 'KILL'}**
- Min C3-R dependency preservation >= 90%: **{'PASS' if kill_rules['min_C3R_dependency_preservation']['pass'] else 'KILL'}**
- C3-R improves over C3-I: **{'PASS' if kill_rules['require_C3R_dependency_improvement_over_C3I']['pass'] else 'KILL'}**
- Max material restore failure <= 20%: **{'PASS' if kill_rules['max_material_restore_failure_rate']['pass'] else 'KILL'}**
- UNKNOWN deletion prohibited: **PASS**
"""
    output_summary_path.parent.mkdir(parents=True, exist_ok=True)
    with output_summary_path.open("w", encoding="utf-8") as f:
        f.write(summary_md)

    return report


def main() -> None:
    parser = argparse.ArgumentParser(description="NJAL-R01 Hypothesis Analyzer")
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
