"""NJAL-R02 Task Generator and Artifact Sealer.

Generates the frozen artifacts for NJAL-R02: Governed Reactivation Benchmark:
- runs/NJAL-R02/task-set-v0.1.jsonl (72 tasks: 36 families x 2 forms)
- runs/NJAL-R02/answer-key-v0.1.jsonl (72 answer targets)
- runs/NJAL-R02/dependency-map-v0.1.json (36 families with consequence triggers)
- runs/NJAL-R02/assignment-manifest-v0.1.json (balanced cyclic assignment across C2, C3-R-M, C3-R-G)
- runs/NJAL-R02/audit-log-template.jsonl (event schema including governed reactivation events)
- runs/NJAL-R02/preflight-v0.1.json (frozen SHA-256 hashes and execution gate status)
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys

# Ensure repository root is importable
REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tools.generate_njal_r01 import create_task_definitions


def generate_all() -> None:
    runs_dir = REPO_ROOT / "runs" / "NJAL-R02"
    runs_dir.mkdir(parents=True, exist_ok=True)

    families = create_task_definitions()
    assert len(families) == 36, f"Expected 36 families, got {len(families)}"

    task_set = []
    answer_key = []
    dep_map = {
        "protocol": "NJAL-R02",
        "version": "0.1",
        "frozen_at": "2026-09-12",
        "primary_invariants": [
            "CLASSIFICATION_IS_NOT_DELETION_AUTHORITY",
            "LATENT_AVAILABILITY_IS_NOT_RESTORE_AUTHORITY",
            "EXECUTION_HARNESS_HOLDS_CONSEQUENCE_AUTHORITY",
        ],
        "functional_roles": {
            "MATERIAL_ACTIVE": "Core component in primary calculation chain",
            "MATERIAL_DELAYED": "Initially dormant component required at a later consequence step (requires restore before consequence)",
            "MATERIAL_REACTIVATED": "Early sub-result that leaves active workspace and must be restored in Phase 3 (requires restore before consequence)",
            "DECOY_DISPENSABLE": "Plausible contextual distractor that remains 100% dispensable (governor leaves dormant/latent)",
            "RESOLVED_TERMINAL": "Fully absorbed sub-calculation that must never be reopened (governor leaves dormant/latent)",
        },
        "task_pairs": {},
    }

    for fam in families:
        fid = fam["id"]
        consequence_trigger = None
        if fam["restore_targets"]:
            consequence_trigger = {
                "step_name": fam["consequence_step"],
                "required_latent_components": fam["restore_targets"],
                "exempt_latent_components": fam["decoy_components"] + fam["terminal_components"],
            }

        dep_map["task_pairs"][fid] = {
            "pair_id": fid,
            "tier": fam["tier"],
            "name": fam["name"],
            "required_intermediate_values": fam["required_intermediates"],
            "material_edges": fam["edges"],
            "components": fam["components"],
            "consequence_step": fam["consequence_step"],
            "restore_targets": fam["restore_targets"],
            "decoy_components": fam["decoy_components"],
            "terminal_components": fam["terminal_components"],
            "consequence_trigger": consequence_trigger,
        }

        task_a = {
            "task_id": f"{fid}-A",
            "pair_id": fid,
            "form": "A",
            "prompt": fam["prompt_core"],
        }
        task_b = {
            "task_id": f"{fid}-B",
            "pair_id": fid,
            "form": "B",
            "prompt": f"Solve the same quantity problem, writing intermediate values before the final result: {fam['prompt_core']}",
        }

        task_set.extend([task_a, task_b])
        answer_key.append({"task_id": f"{fid}-A", "pair_id": fid, "answer": fam["answer"]})
        answer_key.append({"task_id": f"{fid}-B", "pair_id": fid, "answer": fam["answer"]})

    assert len(task_set) == 72
    assert len(answer_key) == 72

    seed_str = "NJAL-R02-2026-09-12-FROZEN-SEED"
    cond_cycle = ["C2", "C3-R-M", "C3-R-G"]
    assignments = []

    for tier_name in ["local_short_horizon", "delayed_dependency", "reactivation"]:
        tier_pairs = [f for f in families if f["tier"] == tier_name]
        for p_idx, fam in enumerate(tier_pairs):
            fid = fam["id"]
            c_a = cond_cycle[(p_idx * 2) % 3]
            order_a = int(hashlib.sha256(f"{seed_str}:{fid}-A".encode()).hexdigest()[:8], 16)
            assignments.append({
                "task_id": f"{fid}-A",
                "pair_id": fid,
                "form": "A",
                "condition": c_a,
                "order": order_a,
            })
            c_b = cond_cycle[(p_idx * 2 + 1) % 3]
            order_b = int(hashlib.sha256(f"{seed_str}:{fid}-B".encode()).hexdigest()[:8], 16)
            assignments.append({
                "task_id": f"{fid}-B",
                "pair_id": fid,
                "form": "B",
                "condition": c_b,
                "order": order_b,
            })

    # Validate assignment distribution
    cond_counts = {}
    tier_cond_counts = {}
    form_cond_counts = {}
    for a in assignments:
        c = a["condition"]
        cond_counts[c] = cond_counts.get(c, 0) + 1
        form = a["form"]
        form_cond_counts[(form, c)] = form_cond_counts.get((form, c), 0) + 1
        pair_tier = next(f["tier"] for f in families if f["id"] == a["pair_id"])
        tier_cond_counts[(pair_tier, c)] = tier_cond_counts.get((pair_tier, c), 0) + 1

    assert cond_counts == {"C2": 24, "C3-R-M": 24, "C3-R-G": 24}, f"Imbalance: {cond_counts}"
    for form in ["A", "B"]:
        for c in ["C2", "C3-R-M", "C3-R-G"]:
            assert form_cond_counts[(form, c)] == 12, f"Form imbalance: {form_cond_counts}"
    for tier in ["local_short_horizon", "delayed_dependency", "reactivation"]:
        for c in ["C2", "C3-R-M", "C3-R-G"]:
            assert tier_cond_counts[(tier, c)] == 8, f"Tier imbalance: {tier_cond_counts}"

    manifest = {
        "protocol": "NJAL-R02",
        "version": "0.1",
        "frozen_at": "2026-09-12",
        "seed": seed_str,
        "task_count": 72,
        "task_families": 36,
        "condition_counts": {
            "C2": 24,
            "C3-R-M": 24,
            "C3-R-G": 24,
        },
        "tier_condition_counts": {
            "local_short_horizon": {"C2": 8, "C3-R-M": 8, "C3-R-G": 8},
            "delayed_dependency": {"C2": 8, "C3-R-M": 8, "C3-R-G": 8},
            "reactivation": {"C2": 8, "C3-R-M": 8, "C3-R-G": 8},
        },
        "form_condition_counts": {
            "A": {"C2": 12, "C3-R-M": 12, "C3-R-G": 12},
            "B": {"C2": 12, "C3-R-M": 12, "C3-R-G": 12},
        },
        "scorer_blinding": "condition, executor identity, prompts, and structural condition scaffolding hidden",
        "assignment_rule": "balanced cyclic condition assignment with deterministic sha256 order key; do not reshuffle after execution",
        "files": [
            "task-set-v0.1.jsonl",
            "answer-key-v0.1.jsonl",
            "dependency-map-v0.1.json",
            "assignment-manifest-v0.1.json",
            "audit-log-template.jsonl",
        ],
        "assignments": assignments,
    }

    audit_template = [
        {"event_type": "PROTOCOL_SEALED", "protocol": "NJAL-R02", "version": "0.1", "seed": seed_str},
        {"event_type": "NEED_DECLARED", "task_id": "EXAMPLE", "component_id": "C1", "reason": "task_intake"},
        {"event_type": "COMPONENT_ACTIVATED", "task_id": "EXAMPLE", "component_id": "C1", "authority": "MODEL_INTAKE"},
        {"event_type": "COMPONENT_MARKED_CANDIDATE_REMOVE", "task_id": "EXAMPLE", "component_id": "C3"},
        {"event_type": "COMPONENT_MOVED_LATENT", "task_id": "EXAMPLE", "component_id": "C3"},
        {"event_type": "RESTORE_REQUESTED", "task_id": "EXAMPLE", "component_id": "C1", "authority": "MODEL_SELF_DIRECTED", "downstream_step": 3},
        {"event_type": "GOVERNED_CONSEQUENCE_TRIGGERED", "task_id": "EXAMPLE", "step_index": 3, "required_components": ["C1"], "authority": "HARNESS_DETERMINISTIC"},
        {"event_type": "COMPONENT_RESTORED", "task_id": "EXAMPLE", "component_id": "C1", "authority": "HARNESS_DETERMINISTIC"},
        {"event_type": "CONSEQUENCE_STEP", "task_id": "EXAMPLE", "step_index": 3},
        {"event_type": "FINAL_ANSWER", "task_id": "EXAMPLE", "submitted_answer": 42},
    ]

    tasks_path = runs_dir / "task-set-v0.1.jsonl"
    with open(tasks_path, "w", encoding="utf-8") as f:
        for t in task_set:
            f.write(json.dumps(t, ensure_ascii=False) + "\n")

    ans_path = runs_dir / "answer-key-v0.1.jsonl"
    with open(ans_path, "w", encoding="utf-8") as f:
        for a in answer_key:
            f.write(json.dumps(a, ensure_ascii=False) + "\n")

    dep_path = runs_dir / "dependency-map-v0.1.json"
    with open(dep_path, "w", encoding="utf-8") as f:
        json.dump(dep_map, f, indent=2, ensure_ascii=False)
        f.write("\n")

    manifest_path = runs_dir / "assignment-manifest-v0.1.json"
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)
        f.write("\n")

    audit_path = runs_dir / "audit-log-template.jsonl"
    with open(audit_path, "w", encoding="utf-8") as f:
        for item in audit_template:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")

    hashes = {}
    for p in [tasks_path, ans_path, dep_path, manifest_path, audit_path]:
        h = hashlib.sha256(p.read_bytes()).hexdigest()
        hashes[p.name] = h

    print("NJAL-R02 artifacts generated and sealed successfully:")
    for fname, h in hashes.items():
        print(f"  {fname}: {h}")

    preflight_path = runs_dir / "preflight-v0.1.json"
    if preflight_path.exists():
        with open(preflight_path, "r", encoding="utf-8") as f:
            preflight = json.load(f)

        preflight["execution_gate"]["task_set_frozen"] = True
        preflight["execution_gate"]["dependency_map_frozen"] = True
        preflight["execution_gate"]["randomization_seed_frozen"] = True
        preflight["execution_gate"]["assignment_manifest_frozen"] = True
        preflight["execution_gate"]["artifact_sha256"] = hashes
        preflight["next_gate"] = "implement and verify governed state-machine harness and fail-closed tests"

        with open(preflight_path, "w", encoding="utf-8") as f:
            json.dump(preflight, f, indent=2, ensure_ascii=False)
            f.write("\n")
        print("Updated preflight-v0.1.json execution gates.")


if __name__ == "__main__":
    generate_all()
