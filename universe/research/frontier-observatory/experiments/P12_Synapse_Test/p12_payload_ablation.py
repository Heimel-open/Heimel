from __future__ import annotations

import hashlib
import json
import math
import os
from dataclasses import asdict
from pathlib import Path
from typing import Any, Optional

import p12_runner as p12

PAYLOAD_VARIANTS = ["P0", "P1", "P2", "P3", "P4", "P5", "P6"]
PACKET_FIELDS = [
    "observation",
    "relevance_context",
    "uncertainty",
    "state_delta",
    "provenance",
]
RETENTION_THRESHOLD = float(os.getenv("P12_PAYLOAD_RETENTION_THRESHOLD", "0.95"))

PACKET_SCHEMA_INSTRUCTION = """
Returner KUN ett gyldig JSON-objekt med nøyaktig disse feltene:
{
  "analysis": "kort, men rik rolle-spesifikk analyse som representerer full upstream-kontekst",
  "observation": "hva du faktisk observerer i kildepakken",
  "relevance_context": "hvorfor observasjonen er relevant for spørsmålet og hvilke relasjoner/premisser den avhenger av",
  "uncertainty": "hva som er usikkert, motsagt eller mangler",
  "state_delta": "den minste endringen mottakeren bør gjøre i sin nåværende forståelse",
  "provenance": "kildeetiketter som bærer state_delta"
}
"analysis" kan være rikere enn de andre feltene. De fem state-feltene skal være korte strenger.
Ikke legg til andre felt. Ikke bruk eksterne fakta.
""".strip()

SYNTHESIS_BOUNDARY_SYSTEM = (
    p12.BASE_SYSTEM
    + " Du er synteseansvarlig bak en eksplisitt Synapse-grense. "
    "Du får IKKE den opprinnelige kildepakken. Bare overført payload og selve spørsmålet er tilgjengelig. "
    "Ikke rekonstruer eller fyll inn evidens som ikke finnes i payloaden. "
    "Bygg premisskart, bevar konflikt og avslutt med kalibrert konklusjon."
)


def _source_labels(task: dict[str, Any]) -> str:
    return ", ".join(str(item.get("label", "?")) for item in task.get("packet", []))


def _clean_text(value: Any) -> str:
    if isinstance(value, str):
        return " ".join(value.split())
    if isinstance(value, list):
        return "; ".join(_clean_text(v) for v in value)
    if value is None:
        return ""
    return " ".join(str(value).split())


def _parse_state_packet(raw: str, role: str, task: dict[str, Any]) -> tuple[dict[str, str], bool]:
    try:
        obj = p12.parse_json_object(raw)
        packet = {field: _clean_text(obj.get(field)) for field in PACKET_FIELDS}
        if not packet["state_delta"]:
            raise ValueError("state_delta missing")
        if not packet["provenance"]:
            packet["provenance"] = _source_labels(task)
        return packet, True
    except Exception:
        fallback = {
            "observation": _clean_text(raw),
            "relevance_context": f"role={role}",
            "uncertainty": "packet_parse_failed",
            "state_delta": _clean_text(raw),
            "provenance": _source_labels(task),
        }
        return fallback, False


def _node_records(task: dict[str, Any], stage: int, prompt: str, budget: int) -> tuple[list[dict[str, Any]], list[p12.CallResult], dict[str, str]]:
    specs = p12._rotated_specs(task["id"], stage)
    roles = ["hypothesis", "evidence", "counter"]
    node_budget = max(100, round(budget * 0.1875))
    calls: list[p12.CallResult] = []
    records: list[dict[str, Any]] = []
    route: dict[str, str] = {}

    for role, spec in zip(roles, specs):
        route[role] = f"{spec.provider}:{spec.model}"
        system = p12.ROLE_SYSTEMS[role] + " " + PACKET_SCHEMA_INSTRUCTION
        call = p12.call_model(spec, system, prompt, node_budget)
        packet, valid = _parse_state_packet(call.text, role, task)
        calls.append(call)
        records.append(
            {
                "role": role,
                "provider": spec.provider,
                "model": spec.model,
                "raw": call.text,
                "packet": packet,
                "packet_parse_valid": valid,
                "call_id": call.call_id,
            }
        )
    return records, calls, route


def _serialize_full(records: list[dict[str, Any]], *, omit: Optional[str] = None) -> str:
    transfer = []
    for record in records:
        packet = dict(record["packet"])
        if omit is not None:
            packet.pop(omit, None)
        transfer.append({"role": record["role"], **packet})
    return json.dumps(transfer, ensure_ascii=False, indent=2, sort_keys=True)


def _serialize_compact(records: list[dict[str, Any]]) -> str:
    compact = []
    for record in records:
        packet = record["packet"]
        compact.append(
            {
                "r": record["role"],
                "o": packet["observation"],
                "c": packet["relevance_context"],
                "u": packet["uncertainty"],
                "d": packet["state_delta"],
                "p": packet["provenance"],
            }
        )
    return json.dumps(compact, ensure_ascii=False, separators=(",", ":"), sort_keys=True)


def _serialize_scrambled(records: list[dict[str, Any]], task_id: str, stage: int) -> str:
    scrambled = []
    for record in records:
        packet = record["packet"]
        values = [packet[field] for field in PACKET_FIELDS]
        offset = 1 + (
            p12.stable_seed(p12.GLOBAL_SEED, task_id, stage, record["role"], "P6")
            % (len(values) - 1)
        )
        rotated = values[offset:] + values[:offset]
        scrambled.append(
            {
                "role": record["role"],
                **{field: value for field, value in zip(PACKET_FIELDS, rotated)},
            }
        )
    return json.dumps(scrambled, ensure_ascii=False, indent=2, sort_keys=True)


def build_payload(variant: str, records: list[dict[str, Any]], task_id: str, stage: int = 1) -> str:
    if variant not in PAYLOAD_VARIANTS:
        raise ValueError(f"Unknown payload variant: {variant}")
    if variant == "P0":
        return "\n\n".join(
            f"{record['role'].upper()}-NODE RAW:\n{record['raw']}" for record in records
        )
    if variant == "P1":
        return _serialize_full(records)
    if variant == "P2":
        return _serialize_compact(records)
    if variant == "P3":
        return _serialize_full(records, omit="provenance")
    if variant == "P4":
        return _serialize_full(records, omit="uncertainty")
    if variant == "P5":
        return _serialize_full(records, omit="relevance_context")
    return _serialize_scrambled(records, task_id, stage)


def payload_metrics(payload: str) -> dict[str, Any]:
    encoded = payload.encode("utf-8")
    return {
        "payload_chars": len(payload),
        "payload_bytes": len(encoded),
        "payload_estimated_tokens": max(1, math.ceil(len(payload) / 4)),
        "payload_sha256": hashlib.sha256(encoded).hexdigest(),
    }


def _synthesis_header(task: dict[str, Any]) -> str:
    return (
        f"OPPGAVE {task['id']} — {task['title']}\n\n"
        f"SPØRSMÅL:\n{task['question']}\n\n"
        "Den opprinnelige kildepakken er med vilje skjult ved denne grensen. "
        "Bruk bare payloaden under som evidens/state fra upstream-nodene."
    )


def run_payload_ablation_task(
    task: dict[str, Any],
    variants: Optional[list[str]] = None,
    budget: Optional[int] = None,
) -> list[dict[str, Any]]:
    if task.get("late_evidence"):
        raise ValueError(
            "Payload-ablation v1 excludes late-evidence tasks so all variants can share identical upstream node outputs."
        )

    selected_variants = variants or PAYLOAD_VARIANTS
    unknown = sorted(set(selected_variants) - set(PAYLOAD_VARIANTS))
    if unknown:
        raise ValueError(f"Unknown variants: {unknown}")

    total_budget = budget or p12.TOTAL_OUTPUT_BUDGET
    node_budget = max(100, round(total_budget * 0.1875))
    synth_budget = total_budget - 3 * node_budget
    prompt = p12.task_prompt(task, stage=1)
    records, node_calls, route = _node_records(task, 1, prompt, total_budget)
    specs = p12._rotated_specs(task["id"], 1)
    synthesizer = specs[0]
    route = {**route, "synthesizer": f"{synthesizer.provider}:{synthesizer.model}"}
    source_fingerprint_material = "\n".join(
        f"{record['provider']}|{record['model']}|{record['role']}|{record['raw']}"
        for record in records
    )
    source_fingerprint = hashlib.sha256(
        source_fingerprint_material.encode("utf-8")
    ).hexdigest()

    outputs = []
    for variant in selected_variants:
        payload = build_payload(variant, records, task["id"], 1)
        metrics = payload_metrics(payload)
        synthesis_prompt = (
            _synthesis_header(task)
            + f"\n\nPAYLOAD VARIANT {variant}:\n{payload}\n\n"
            "Lag endelig svar uten å innføre evidens som ikke krysset Synapse-grensen."
        )
        synth_call = p12.call_model(
            synthesizer,
            SYNTHESIS_BOUNDARY_SYSTEM,
            synthesis_prompt,
            synth_budget,
        )
        outputs.append(
            {
                "condition": f"C3-{variant}",
                "payload_variant": variant,
                "task_id": task["id"],
                "family": task["family"],
                "title": task["title"],
                "answer": synth_call.text,
                "created_at": p12.utc_now(),
                "shared_upstream": True,
                "shared_source_fingerprint": source_fingerprint,
                "node_budget_each": node_budget,
                "synthesis_budget": synth_budget,
                "model_route": route,
                "packet_parse_valid": {
                    record["role"]: record["packet_parse_valid"] for record in records
                },
                "source_packets": [
                    {
                        "role": record["role"],
                        "provider": record["provider"],
                        "model": record["model"],
                        "packet": record["packet"],
                        "packet_parse_valid": record["packet_parse_valid"],
                        "call_id": record["call_id"],
                    }
                    for record in records
                ],
                "shared_node_trace": [asdict(call) for call in node_calls],
                "synthesis_call": asdict(synth_call),
                **metrics,
            }
        )
    return outputs


def _preregister(
    run_dir: Path,
    tasks: list[dict[str, Any]],
    variants: list[str],
    actual_sha: str,
) -> None:
    record = {
        "protocol": "P12-Synapse-Payload-Ablation-v1",
        "base_protocol": "P12-Synapse-MVP-v1",
        "created_at": p12.utc_now(),
        "global_seed": p12.GLOBAL_SEED,
        "task_pack_sha256": actual_sha,
        "task_ids": [task["id"] for task in tasks],
        "families": sorted({task["family"] for task in tasks}),
        "payload_variants": variants,
        "retention_threshold": RETENTION_THRESHOLD,
        "hypothesis": (
            "H-MESH-7: compact contextual state transfer retains most capability of raw transfer "
            "while using materially less communication."
        ),
        "causal_controls": [
            "same upstream node calls shared by every payload variant for a task",
            "same node models and role topology",
            "same synthesis model and synthesis output budget",
            "synthesizer cannot see original source packet",
            "P0 carries the full raw node object, including rich analysis; P1-P5 carry only state fields",
            "P6 preserves transferred text volume approximately while breaking field semantics",
        ],
        "payload_definitions": {
            "P0": "full/raw node output including rich upstream analysis",
            "P1": "contextualized state packet: observation + relevance/context + uncertainty + state_delta + provenance",
            "P2": "same P1 semantics in compact canonical encoding",
            "P3": "P1 without provenance",
            "P4": "P1 without uncertainty",
            "P5": "P1 without relevance/context",
            "P6": "deterministically scrambled field semantics control",
        },
        "limitations": [
            "v1 excludes T3 late-evidence tasks to preserve identical upstream state across variants",
            "payload token count is estimated from characters; provider input-token usage includes task header and payload",
            "results compare P0-P6 internally and are not directly budget-equivalent to the original C0/C1/C3/C5 MVP",
            "partial per-task resume is rejected because regenerating only missing variants would violate the shared-upstream invariant",
        ],
        "mock_mode": p12.MOCK_MODE,
    }
    (run_dir / "payload_ablation_preregistration.json").write_text(
        json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def run_payload_ablation_experiment(
    tasks: list[dict[str, Any]],
    task_limit: Optional[int] = None,
    families: Optional[list[str]] = None,
    variants: Optional[list[str]] = None,
    label: str = "payload-ablation",
    existing_run_dir: Optional[str] = None,
) -> Path:
    p12.validate_config()
    selected_variants = variants or PAYLOAD_VARIANTS
    unknown = sorted(set(selected_variants) - set(PAYLOAD_VARIANTS))
    if unknown:
        raise ValueError(f"Unknown variants: {unknown}")

    selected_families = set(families or ["T1", "T2", "T4"])
    eligible = [
        task for task in tasks
        if task.get("family") in selected_families and not task.get("late_evidence")
    ]
    selected_tasks = eligible[:task_limit] if task_limit else eligible
    if not selected_tasks:
        raise ValueError("No eligible tasks selected for payload ablation.")

    actual_sha = p12.task_pack_sha256(tasks)
    if actual_sha != p12.CANONICAL_TASK_PACK_SHA256:
        raise ValueError(
            f"Task pack SHA mismatch: {actual_sha} != {p12.CANONICAL_TASK_PACK_SHA256}"
        )

    run_dir = Path(existing_run_dir) if existing_run_dir else p12.new_run_dir(label)
    run_dir.mkdir(parents=True, exist_ok=True)
    outputs_path = run_dir / "payload_ablation_outputs.jsonl"
    judgments_path = run_dir / "payload_ablation_judgments.jsonl"

    if not (run_dir / "payload_ablation_preregistration.json").exists():
        _preregister(run_dir, selected_tasks, selected_variants, actual_sha)

    done_outputs = {
        (item["task_id"], item["payload_variant"])
        for item in p12.load_jsonl(outputs_path)
    }
    done_judgments = {
        (item["task_id"], item["payload_variant"], item["judge"])
        for item in p12.load_jsonl(judgments_path)
    }

    for task_index, task in enumerate(selected_tasks, start=1):
        existing_variants = [
            variant for variant in selected_variants
            if (task["id"], variant) in done_outputs
        ]
        missing_variants = [
            variant for variant in selected_variants
            if (task["id"], variant) not in done_outputs
        ]
        if existing_variants and missing_variants:
            raise ValueError(
                f"Partial payload resume for {task['id']} would violate shared-upstream invariance. "
                "Start a new run or restore the complete task payload set."
            )
        if missing_variants:
            print(f"[{task_index}/{len(selected_tasks)}] {task['id']} payload={','.join(selected_variants)}")
            new_outputs = run_payload_ablation_task(task, variants=selected_variants)
            for output in new_outputs:
                p12.append_jsonl(outputs_path, output)
                done_outputs.add((task["id"], output["payload_variant"]))

        task_outputs = {
            item["payload_variant"]: item
            for item in p12.load_jsonl(outputs_path)
            if item["task_id"] == task["id"]
        }
        fingerprints = {
            task_outputs[variant]["shared_source_fingerprint"]
            for variant in selected_variants
        }
        if len(fingerprints) != 1:
            raise ValueError(f"Shared-upstream invariant failed for {task['id']}")

        for variant in selected_variants:
            output = task_outputs[variant]
            condition = output["condition"]
            for judge_name in p12.JUDGE_NAMES:
                key = (task["id"], variant, judge_name)
                if key in done_judgments:
                    continue
                judged = p12.judge_answer(task, condition, output["answer"], judge_name)
                judged.update(
                    {
                        "task_id": task["id"],
                        "family": task["family"],
                        "condition": condition,
                        "payload_variant": variant,
                        "created_at": p12.utc_now(),
                    }
                )
                p12.append_jsonl(judgments_path, judged)
                done_judgments.add(key)

    payload_ablation_report(run_dir)
    print("Payload ablation complete:", run_dir)
    return run_dir


def _mean(values: list[float]) -> float:
    return sum(values) / len(values) if values else math.nan


def payload_ablation_report(run_dir: Path) -> dict[str, Any]:
    outputs = p12.load_jsonl(run_dir / "payload_ablation_outputs.jsonl")
    judgments = p12.load_jsonl(run_dir / "payload_ablation_judgments.jsonl")
    if not outputs or not judgments:
        raise ValueError("Payload ablation outputs/judgments are incomplete.")

    scores: dict[str, list[float]] = {variant: [] for variant in PAYLOAD_VARIANTS}
    for item in judgments:
        active_scores = [
            float(value)
            for value in item["judgment"]["scores"].values()
            if value is not None
        ]
        if active_scores:
            scores[item["payload_variant"]].append(_mean(active_scores))

    bytes_by_variant: dict[str, list[float]] = {variant: [] for variant in PAYLOAD_VARIANTS}
    tokens_by_variant: dict[str, list[float]] = {variant: [] for variant in PAYLOAD_VARIANTS}
    for item in outputs:
        variant = item["payload_variant"]
        bytes_by_variant[variant].append(float(item["payload_bytes"]))
        tokens_by_variant[variant].append(float(item["payload_estimated_tokens"]))

    summary: dict[str, dict[str, Any]] = {}
    p0_score = _mean(scores["P0"])
    for variant in PAYLOAD_VARIANTS:
        mean_score = _mean(scores[variant])
        retention = mean_score / p0_score if not math.isnan(mean_score) and p0_score > 0 else math.nan
        summary[variant] = {
            "mean_score": mean_score,
            "mean_payload_bytes": _mean(bytes_by_variant[variant]),
            "mean_payload_estimated_tokens": _mean(tokens_by_variant[variant]),
            "score_retention_vs_P0": retention,
            "n_judgments": len(scores[variant]),
        }

    candidates = []
    for variant in ["P1", "P2", "P3", "P4", "P5"]:
        retention = summary[variant]["score_retention_vs_P0"]
        if not math.isnan(retention) and retention >= RETENTION_THRESHOLD:
            candidates.append(variant)
    minimum_sufficient = min(
        candidates,
        key=lambda variant: summary[variant]["mean_payload_bytes"],
        default=None,
    )

    p1_score = summary["P1"]["mean_score"]
    p6_score = summary["P6"]["mean_score"]
    report = {
        "created_at": p12.utc_now(),
        "retention_threshold": RETENTION_THRESHOLD,
        "summary": summary,
        "minimum_sufficient_noncontrol_variant": minimum_sufficient,
        "field_ablation_delta_vs_P1": {
            "without_provenance_P3": p1_score - summary["P3"]["mean_score"],
            "without_uncertainty_P4": p1_score - summary["P4"]["mean_score"],
            "without_relevance_context_P5": p1_score - summary["P5"]["mean_score"],
            "scrambled_semantics_P6": p1_score - p6_score,
        },
        "preliminary_h_mesh_7_pass": bool(
            minimum_sufficient is not None
            and not math.isnan(p1_score)
            and not math.isnan(p6_score)
            and p1_score > p6_score
        ),
        "interpretation_guard": (
            "A pass is only a preliminary result for this payload boundary. It does not establish general mesh-level intelligence."
        ),
    }
    (run_dir / "payload_ablation_report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return report
