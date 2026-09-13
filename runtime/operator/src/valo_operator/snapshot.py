"""Operator snapshot: read-only pack summaries + kernel views. No writes."""

from __future__ import annotations

from typing import Any

from valo_kernel import KernelEngine

from .views import kernel_views


def operator_snapshot(kernel: KernelEngine, pack_id: str = "public") -> dict[str, Any]:
    """A deterministic, read-only snapshot combining Kernel truth with a
    pack-level summary. `pack_id` selects which state vocabulary to summarize;
    the projection itself is generic."""
    views = kernel_views(kernel)
    summary: dict[str, Any] = {"pack": pack_id}
    states = views["entities"].values()
    summary["total_entities"] = len(views["entities"])
    summary["states"] = _states_counts(states)
    if pack_id == "public":
        summary["cases"] = [
            {"case_id": eid, "state": info["state"], "service": (info["attributes"] or {}).get("service")}
            for eid, info in views["entities"].items() if info["type"] == "Case"
        ]
        summary["ready_for_decision"] = [
            eid for eid, info in views["entities"].items()
            if info["type"] == "Case" and info["state"] == "READY_FOR_DECISION"
        ]
    elif pack_id == "trades":
        summary["workorders"] = [
            {"workorder_id": eid, "state": info["state"]}
            for eid, info in views["entities"].items() if info["type"] == "Job"
        ]
        summary["open_workorders"] = [
            eid for eid, info in views["entities"].items()
            if info["type"] == "Job" and info["state"] not in ("CLOSED", "CANCELLED")
        ]
    return {"views": views, "summary": summary}


def _states_counts(states: Any) -> dict[str, int]:
    counts: dict[str, int] = {}
    for info in states:
        counts[info["state"]] = counts.get(info["state"], 0) + 1
    return counts
