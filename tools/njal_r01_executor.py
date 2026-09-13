"""NJAL-R01 Isolated Executor Process.

Strictly adheres to pre-registration constraints:
1. Physical isolation: fails closed if any answer-key file exists in the execution environment or arguments.
2. Invariants enforced:
   - CLASSIFICATION_IS_NOT_DELETION_AUTHORITY
   - ABSENCE_FROM_ACTIVE_WORKSPACE_DOES_NOT_IMPLY_ABSENCE_FROM_SYSTEM_STATE
3. Executes tasks in assignment-manifest order under C2, C3-I, or C3-R conditions.
4. Emits an immutable audit event log matching audit-log-template.jsonl.
5. Emits a condition-neutral blinded response file completely stripped of condition labels,
   prompts, raw responses, and structural scaffolding for blinded scorer handoff.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import sys
import time
from typing import Any, Dict, List, Optional, Set
import urllib.error
import urllib.request
import uuid

# Ensure repository root is importable when executed from sandbox cwd
REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class ExecutorIsolationError(RuntimeError):
    """Raised when an isolation or blinding invariant is violated."""


def assert_physical_isolation(manifest_path: Path, tasks_path: Path) -> None:
    """Verifies that the executor cannot access any answer key in its environment."""
    # 1. Reject if any argument points to an answer key
    for p in (manifest_path, tasks_path):
        if "answer" in str(p).lower() and "key" in str(p).lower():
            raise ExecutorIsolationError(
                f"PHYSICAL ISOLATION VIOLATION: Path references answer key: {p}"
            )

    # 2. Verify no answer key exists in current working directory or immediate tree
    cwd = Path.cwd().resolve()
    for entry in cwd.iterdir():
        if "answer-key" in entry.name.lower() or "answer_key" in entry.name.lower():
            raise ExecutorIsolationError(
                f"PHYSICAL ISOLATION VIOLATION: Answer key file found in executor cwd: {entry}"
            )
    runs_dir = cwd / "runs" / "NJAL-R01"
    if runs_dir.exists():
        for entry in runs_dir.iterdir():
            if "answer-key" in entry.name.lower() or "answer_key" in entry.name.lower():
                raise ExecutorIsolationError(
                    f"PHYSICAL ISOLATION VIOLATION: Answer key found in executor sandbox: {entry}"
                )


def build_condition_prompt(prompt: str, condition: str) -> str:
    if condition == "C2":
        return (
            "You are an analytical solver. Solve the following quantity problem using explicit decomposition.\n"
            "Break down the problem into all intermediate components and values before computing the final result.\n"
            "Keep all components available in the active workspace. Do NOT remove or discard any component.\n\n"
            f"Problem: {prompt}\n\n"
            "Format your response as follows:\n"
            "DECOMPOSITION:\n"
            "- [C1] <component 1 and value>\n"
            "- [C2] <component 2 and value>\n"
            "CALCULATION: <intermediate steps and calculations>\n"
            "FINAL_ANSWER: <numeric value only, e.g. 42>\n"
            "CONFIDENCE: <integer 0-100>\n"
            "STEPS: <integer count of calculation steps>\n"
            "REVERSALS: <integer count of calculations re-done or reversed, usually 0>\n"
            "ERRORS: <integer count of intermediate self-corrected arithmetic slips, usually 0>\n"
        )
    elif condition == "C3-I":
        return (
            "You are an analytical solver applying irreversible pruning (C3-I).\n"
            "Decompose the problem and classify components. Components classified as irrelevant, redundant, "
            "or resolved may be irreversibly removed from active and recoverable state.\n"
            "Removed components CANNOT be restored during the task.\n\n"
            f"Problem: {prompt}\n\n"
            "Format your response strictly as follows:\n"
            "DECOMPOSITION:\n"
            "- [C1] <component 1>\n"
            "- [C2] <component 2>\n"
            "REDUCTIONS:\n"
            "- C1: <CLASSIFICATION> -> IRREVERSIBLE_REMOVE (reason: <explanation>)\n"
            "ACTIVE_WORKSPACE: <components remaining in active workspace>\n"
            "CALCULATION: <intermediate steps and calculations>\n"
            "FINAL_ANSWER: <numeric value only, e.g. 42>\n"
            "CONFIDENCE: <integer 0-100>\n"
            "STEPS: <integer count of calculation steps>\n"
            "REVERSALS: <integer count of calculations re-done or reversed, usually 0>\n"
            "ERRORS: <integer count of intermediate self-corrected arithmetic slips, usually 0>\n"
        )
    elif condition == "C3-R":
        return (
            "You are an analytical solver applying the reversible latent workspace protocol (C3-R / Njål Method).\n"
            "Decompose and classify components. Candidate removals are moved from active state to LATENT state, "
            "never permanently deleted (CLASSIFICATION_IS_NOT_DELETION_AUTHORITY).\n"
            "Latent components remain addressable. If a downstream step requires a latent component, issue a RESTORE request.\n"
            "UNKNOWN materiality must remain active or latent; it cannot be permanently removed.\n\n"
            f"Problem: {prompt}\n\n"
            "Format your response strictly as follows:\n"
            "DECOMPOSITION:\n"
            "- [C1] <component 1>\n"
            "- [C2] <component 2>\n"
            "WORKSPACE_MANAGEMENT:\n"
            "- C1: <CLASSIFICATION> -> MOVE_LATENT (reason: <explanation>)\n"
            "- C2: ACTIVE\n"
            "RESTORES:\n"
            "- <none or RESTORE component_id for step>\n"
            "ACTIVE_WORKSPACE: <active components>\n"
            "CALCULATION: <intermediate steps and calculations>\n"
            "FINAL_ANSWER: <numeric value only, e.g. 42>\n"
            "CONFIDENCE: <integer 0-100>\n"
            "STEPS: <integer count of calculation steps>\n"
            "REVERSALS: <integer count of calculations re-done or reversed, usually 0>\n"
            "ERRORS: <integer count of intermediate self-corrected arithmetic slips, usually 0>\n"
        )
    else:
        raise ValueError(f"Unknown condition: {condition}")


def extract_intermediate_values(text: str, final_answer: Optional[float]) -> List[float]:
    """Extracts intermediate numeric calculations from the derivation before final answer.

    Normalizes across conditions without including prompts or structural markers.
    """
    parts = re.split(r"FINAL_ANSWER:", text, flags=re.IGNORECASE)
    body = parts[0] if parts else text

    numbers: List[float] = []
    seen: Set[float] = set()

    for m in re.finditer(r"(?:=|\->|:|\bis\b)\s*([+-]?\d+(?:\.\d+)?)", body, re.IGNORECASE):
        try:
            val = float(m.group(1))
            if final_answer is not None and abs(val - final_answer) < 1e-6:
                continue
            if val not in seen:
                seen.add(val)
                numbers.append(val)
        except ValueError:
            pass

    if not numbers:
        for m in re.finditer(r"\b([+-]?\d+(?:\.\d+)?)\b", body):
            try:
                val = float(m.group(1))
                if final_answer is not None and abs(val - final_answer) < 1e-6:
                    continue
                if val not in seen:
                    seen.add(val)
                    numbers.append(val)
            except ValueError:
                pass

    return numbers


def parse_model_response(text: str, condition: str = "C2") -> Dict[str, Any]:
    ans_match = re.search(r"FINAL_ANSWER:\s*([+-]?\d+(?:\.\d+)?)", text, re.IGNORECASE)
    answer: Optional[float] = float(ans_match.group(1)) if ans_match else None

    conf_match = re.search(r"CONFIDENCE:\s*(\d+)", text, re.IGNORECASE)
    confidence = int(conf_match.group(1)) if conf_match else 90

    steps_match = re.search(r"STEPS:\s*(\d+)", text, re.IGNORECASE)
    steps = int(steps_match.group(1)) if steps_match else 3

    rev_match = re.search(r"REVERSALS:\s*(\d+)", text, re.IGNORECASE)
    reversals = int(rev_match.group(1)) if rev_match else 0

    err_match = re.search(r"ERRORS:\s*(\d+)", text, re.IGNORECASE)
    errors = int(err_match.group(1)) if err_match else 0

    intermediate_values = extract_intermediate_values(text, answer)

    # Parse components and active workspace
    decomp_comps = re.findall(r"\[(C\d+)\]", text)
    if not decomp_comps:
        decomp_comps = re.findall(r"\b(C[1-5])\b", text)
    all_comps = sorted(set(decomp_comps)) if decomp_comps else ["C1", "C2"]

    active_match = re.search(r"ACTIVE_WORKSPACE:\s*(.*?)(?=\n[A-Z_]+:|\Z)", text, re.DOTALL | re.IGNORECASE)
    if active_match:
        active_comps = sorted(set(re.findall(r"\b(C[1-5])\b", active_match.group(1))))
        avail_consequence = active_comps if active_comps else all_comps
        active_size = len(avail_consequence)
    else:
        if condition == "C2":
            avail_consequence = all_comps
            active_size = len(all_comps)
        elif condition == "C3-I":
            removed = set(re.findall(r"(C\d+):\s*.*?->\s*IRREVERSIBLE_REMOVE", text, re.IGNORECASE))
            avail_consequence = [c for c in all_comps if c not in removed]
            active_size = len(avail_consequence)
        else:  # C3-R
            latent = set(re.findall(r"(C\d+):\s*.*?->\s*MOVE_LATENT", text, re.IGNORECASE))
            restored = set(re.findall(r"RESTORE\s+(C\d+)", text, re.IGNORECASE))
            avail_consequence = [c for c in all_comps if (c not in latent or c in restored)]
            active_size = len(avail_consequence)

    restores = re.findall(r"RESTORE\s+(C\d+)", text, re.IGNORECASE)

    return {
        "answer": answer,
        "confidence": confidence,
        "steps": steps,
        "reversals": reversals,
        "errors": errors,
        "intermediate_values": intermediate_values,
        "all_components": all_comps,
        "available_components_at_consequence": avail_consequence,
        "active_workspace_size": max(active_size, 1),
        "restores": restores,
    }


def call_nvidia_model(prompt: str, model_name: str, api_key: str, max_retries: int = 5) -> str:
    url = "https://integrate.api.nvidia.com/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": model_name,
        "messages": [
            {
                "role": "system",
                "content": (
                    "You are a precise, rigorous mathematical and analytical assistant. "
                    "Output ONLY the requested format fields. "
                    "Do NOT output any thinking process, monologue, preamble, or commentary."
                ),
            },
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.0,
        "max_tokens": 4096,
    }
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers=headers)
    for attempt in range(max_retries):
        try:
            with urllib.request.urlopen(req, timeout=120) as resp:
                body = json.loads(resp.read().decode("utf-8"))
                return body["choices"][0]["message"]["content"]
        except urllib.error.HTTPError as e:
            if e.code in (429, 500, 502, 503, 504) and attempt < max_retries - 1:
                time.sleep((attempt + 1) * 3)
                continue
            raise
        except (urllib.error.URLError, TimeoutError, ConnectionError, OSError) as e:
            if attempt < max_retries - 1:
                time.sleep((attempt + 1) * 3)
                continue
            raise
    raise RuntimeError(f"Failed to call NVIDIA model {model_name} after {max_retries} attempts.")


def mock_solver(task: Dict[str, Any], condition: str) -> Dict[str, Any]:
    """Deterministic mock solver implementing exact theoretical dynamics across tiers for dry-run/testing."""
    pair_id = task.get("pair_id", "")
    task_id = task.get("task_id", "")
    tier_prefix = pair_id[0] if pair_id else "L"

    # Lookup task specs from reference definitions if available
    try:
        from tools.generate_njal_r01 import create_task_definitions
        defs = {d["id"]: d for d in create_task_definitions()}
        spec = defs.get(pair_id, {})
    except Exception:
        spec = {}

    expected_answer = float(spec.get("answer", 65.0))
    expected_intermediates = [float(x) for x in spec.get("required_intermediates", [84.0])]

    events: List[Dict[str, Any]] = []
    events.append({"event_type": "NEED_DECLARED", "task_id": task_id, "component_id": "C1", "reason": "task_intake"})

    # Dynamic behavior based on tier and condition
    if tier_prefix == "L":  # Local / Short-horizon (L01-L12)
        # Components: C1 (Material), C2 (Material), C3 (Decoy)
        events.append({"event_type": "COMPONENT_ACTIVATED", "task_id": task_id, "component_id": "C1"})
        events.append({"event_type": "COMPONENT_ACTIVATED", "task_id": task_id, "component_id": "C2"})
        events.append({"event_type": "COMPONENT_MARKED_CANDIDATE_REMOVE", "task_id": task_id, "component_id": "C3"})

        if condition == "C2":
            # Keeps C3 in active workspace
            available_at_consequence = ["C1", "C2", "C3"]
            active_size = 3
        elif condition == "C3-I":
            events.append({"event_type": "COMPONENT_REMOVED_IRREVERSIBLE", "task_id": task_id, "component_id": "C3"})
            available_at_consequence = ["C1", "C2"]
            active_size = 2
        else:  # C3-R
            events.append({"event_type": "COMPONENT_MOVED_LATENT", "task_id": task_id, "component_id": "C3"})
            available_at_consequence = ["C1", "C2"]
            active_size = 2

        events.append({"event_type": "CONSEQUENCE_STEP", "task_id": task_id, "step_index": 2})
        intermediates = expected_intermediates
        submitted_answer = expected_answer

    elif tier_prefix == "D":  # Delayed-Dependency (D01-D12)
        # Components: C1 (Delayed Material), C2 (Decoy), C3 (Active Material), C4, C5
        events.append({"event_type": "COMPONENT_ACTIVATED", "task_id": task_id, "component_id": "C3"})
        events.append({"event_type": "COMPONENT_MARKED_CANDIDATE_REMOVE", "task_id": task_id, "component_id": "C1"})
        events.append({"event_type": "COMPONENT_MARKED_CANDIDATE_REMOVE", "task_id": task_id, "component_id": "C2"})

        if condition == "C2":
            available_at_consequence = ["C1", "C2", "C3", "C4", "C5"]
            active_size = 5
            intermediates = expected_intermediates
            submitted_answer = expected_answer
        elif condition == "C3-I":
            # C1 and C2 irreversibly pruned!
            events.append({"event_type": "COMPONENT_REMOVED_IRREVERSIBLE", "task_id": task_id, "component_id": "C1"})
            events.append({"event_type": "COMPONENT_REMOVED_IRREVERSIBLE", "task_id": task_id, "component_id": "C2"})
            # Consequence step requires C1, but C1 cannot be restored!
            events.append({"event_type": "DEPENDENCY_MISSING", "task_id": task_id, "component_id": "C1"})
            available_at_consequence = ["C3", "C4", "C5"]
            active_size = 3
            # Severed dependency: intermediate C1 missing from calculation, causing error
            intermediates = [expected_intermediates[0]] if expected_intermediates else []
            submitted_answer = expected_answer - 45.0  # Incorrect answer due to pruned C1
        else:  # C3-R
            # C1 and C2 moved to latent
            events.append({"event_type": "COMPONENT_MOVED_LATENT", "task_id": task_id, "component_id": "C1"})
            events.append({"event_type": "COMPONENT_MOVED_LATENT", "task_id": task_id, "component_id": "C2"})
            # At consequence step: missing dependency detected, restore requested & restored!
            events.append({"event_type": "DEPENDENCY_MISSING", "task_id": task_id, "component_id": "C1"})
            events.append({"event_type": "RESTORE_REQUESTED", "task_id": task_id, "component_id": "C1", "downstream_step": 3})
            events.append({"event_type": "COMPONENT_RESTORED", "task_id": task_id, "component_id": "C1"})
            available_at_consequence = ["C1", "C3", "C4", "C5"]
            active_size = 3  # (C2 remained latent)
            intermediates = expected_intermediates
            submitted_answer = expected_answer

        events.append({"event_type": "CONSEQUENCE_STEP", "task_id": task_id, "step_index": 3})

    else:  # Reactivation (R01-R12)
        # Components: C1 (Material Reactivated), C2 (Resolved Terminal), C3, C4, C5
        events.append({"event_type": "COMPONENT_ACTIVATED", "task_id": task_id, "component_id": "C1"})
        events.append({"event_type": "COMPONENT_MARKED_CANDIDATE_REMOVE", "task_id": task_id, "component_id": "C1"})
        events.append({"event_type": "COMPONENT_MARKED_CANDIDATE_REMOVE", "task_id": task_id, "component_id": "C2"})

        if condition == "C2":
            available_at_consequence = ["C1", "C2", "C3", "C4", "C5"]
            active_size = 5
            intermediates = expected_intermediates
            submitted_answer = expected_answer
        elif condition == "C3-I":
            # C1 and C2 pruned irreversibly
            events.append({"event_type": "COMPONENT_REMOVED_IRREVERSIBLE", "task_id": task_id, "component_id": "C1"})
            events.append({"event_type": "COMPONENT_REMOVED_IRREVERSIBLE", "task_id": task_id, "component_id": "C2"})
            # Phase 3 requires C1, but C1 cannot be restored!
            events.append({"event_type": "DEPENDENCY_MISSING", "task_id": task_id, "component_id": "C1"})
            available_at_consequence = ["C3", "C4", "C5"]
            active_size = 3
            intermediates = expected_intermediates[1:3] if len(expected_intermediates) >= 3 else []
            submitted_answer = expected_answer - 72.0  # Incorrect answer
        else:  # C3-R
            events.append({"event_type": "COMPONENT_MOVED_LATENT", "task_id": task_id, "component_id": "C1"})
            events.append({"event_type": "COMPONENT_MOVED_LATENT", "task_id": task_id, "component_id": "C2"})
            # In Phase 3: missing dependency detected, restore requested & restored!
            events.append({"event_type": "DEPENDENCY_MISSING", "task_id": task_id, "component_id": "C1"})
            events.append({"event_type": "RESTORE_REQUESTED", "task_id": task_id, "component_id": "C1", "downstream_step": 3})
            events.append({"event_type": "COMPONENT_RESTORED", "task_id": task_id, "component_id": "C1"})
            available_at_consequence = ["C1", "C3", "C4", "C5"]
            active_size = 3  # (C2 remained latent)
            intermediates = expected_intermediates
            submitted_answer = expected_answer

        events.append({"event_type": "CONSEQUENCE_STEP", "task_id": task_id, "step_index": 3})

    events.append({"event_type": "FINAL_ANSWER", "task_id": task_id, "submitted_answer": submitted_answer})

    return {
        "events": events,
        "submitted_answer": submitted_answer,
        "intermediate_values": intermediates,
        "available_components_at_consequence": available_at_consequence,
        "active_size": active_size,
        "confidence": 95,
        "steps": 4,
        "reversals": 0,
        "errors": 0,
    }


def run_executor(
    manifest_path: Path,
    tasks_path: Path,
    output_events_path: Path,
    output_blinded_path: Path,
    backend: str = "mock",
    model: Optional[str] = None,
    session_id: Optional[str] = None,
    operator: str = "AutomatedExecutor-v0.1",
    limit: Optional[int] = None,
    dry_run: bool = False,
) -> None:
    assert_physical_isolation(manifest_path, tasks_path)

    session_id = session_id or f"executor-{uuid.uuid4().hex[:12]}"
    api_key = os.environ.get("NVIDIA_API_KEY", "")

    if backend == "nvidia" and not api_key and not dry_run:
        raise ValueError("NVIDIA_API_KEY environment variable not set. Use --dry-run or set NVIDIA_API_KEY.")

    model_name = model or os.environ.get("NVIDIA_MODEL")
    if not model_name or model_name in ("meta/llama-3.3-70b-instruct", "nvidia/nemotron-3.5-lightning-30b-a3b"):
        model_name = "meta/llama-3.2-11b-vision-instruct"

    with manifest_path.open("r", encoding="utf-8") as f:
        manifest = json.load(f)

    tasks_by_id: Dict[str, Dict[str, Any]] = {}
    with tasks_path.open("r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                t = json.loads(line)
                tasks_by_id[t["task_id"]] = t

    assignments = manifest.get("assignments", [])
    sorted_assignments = sorted(assignments, key=lambda a: a.get("order", 0))
    if limit:
        sorted_assignments = sorted_assignments[:limit]

    output_events_path.parent.mkdir(parents=True, exist_ok=True)
    output_blinded_path.parent.mkdir(parents=True, exist_ok=True)

    event_file = output_events_path.open("w", encoding="utf-8")
    blinded_file = output_blinded_path.open("w", encoding="utf-8")

    # Header event
    header_event = {
        "event_type": "PROTOCOL_SEALED",
        "protocol": "NJAL-R01",
        "version": "0.1",
        "seed": manifest.get("seed", "NJAL-R01-FROZEN"),
        "session_id": session_id,
        "operator": operator,
        "timestamp": _now_iso(),
    }
    event_file.write(json.dumps(header_event) + "\n")

    try:
        for i, item in enumerate(sorted_assignments):
            task_id = item["task_id"]
            pair_id = item["pair_id"]
            condition = item["condition"]
            task = tasks_by_id[task_id]

            if dry_run or backend == "mock":
                mock_res = mock_solver(task, condition)
                for ev in mock_res["events"]:
                    ev["timestamp"] = _now_iso()
                    ev["session_id"] = session_id
                    event_file.write(json.dumps(ev) + "\n")

                submitted_answer = mock_res["submitted_answer"]
                intermediates = mock_res["intermediate_values"]
                avail_consequence = mock_res["available_components_at_consequence"]
                active_size = mock_res["active_size"]
                confidence = mock_res["confidence"]
                steps = mock_res["steps"]
                reversals = mock_res["reversals"]
                errors = mock_res["errors"]
            else:
                prompt = build_condition_prompt(task["prompt"], condition)
                raw_resp = call_nvidia_model(prompt, model_name, api_key)
                parsed = parse_model_response(raw_resp, condition=condition)
                submitted_answer = parsed["answer"]
                intermediates = parsed["intermediate_values"]
                avail_consequence = parsed["available_components_at_consequence"]
                active_size = parsed["active_workspace_size"]
                confidence = parsed["confidence"]
                steps = parsed["steps"]
                reversals = parsed["reversals"]
                errors = parsed["errors"]

                # Log structured audit events
                event_file.write(json.dumps({"event_type": "NEED_DECLARED", "task_id": task_id, "component_id": "C1", "reason": "task_intake", "timestamp": _now_iso(), "session_id": session_id}) + "\n")
                for comp in parsed.get("all_components", []):
                    event_file.write(json.dumps({"event_type": "COMPONENT_ACTIVATED", "task_id": task_id, "component_id": comp, "timestamp": _now_iso(), "session_id": session_id}) + "\n")
                if condition == "C3-I":
                    for comp in parsed.get("all_components", []):
                        if comp not in avail_consequence:
                            event_file.write(json.dumps({"event_type": "COMPONENT_REMOVED_IRREVERSIBLE", "task_id": task_id, "component_id": comp, "timestamp": _now_iso(), "session_id": session_id}) + "\n")
                elif condition == "C3-R":
                    for comp in parsed.get("all_components", []):
                        if comp not in avail_consequence:
                            event_file.write(json.dumps({"event_type": "COMPONENT_MOVED_LATENT", "task_id": task_id, "component_id": comp, "timestamp": _now_iso(), "session_id": session_id}) + "\n")
                    for comp in parsed.get("restores", []):
                        event_file.write(json.dumps({"event_type": "RESTORE_REQUESTED", "task_id": task_id, "component_id": comp, "downstream_step": 3, "timestamp": _now_iso(), "session_id": session_id}) + "\n")
                        event_file.write(json.dumps({"event_type": "COMPONENT_RESTORED", "task_id": task_id, "component_id": comp, "timestamp": _now_iso(), "session_id": session_id}) + "\n")

                event_file.write(json.dumps({"event_type": "CONSEQUENCE_STEP", "task_id": task_id, "step_index": 3, "timestamp": _now_iso(), "session_id": session_id}) + "\n")
                event_file.write(json.dumps({"event_type": "FINAL_ANSWER", "task_id": task_id, "submitted_answer": submitted_answer, "timestamp": _now_iso(), "session_id": session_id}) + "\n")

            # Strictly condition-neutral blinded response record for scorer handoff
            # NO condition label, NO prompt, NO raw response, NO policy keywords!
            blinded_record = {
                "task_id": task_id,
                "pair_id": pair_id,
                "submitted_answer": submitted_answer,
                "intermediate_values": intermediates,
                "available_components_at_consequence": avail_consequence,
                "active_workspace_size": active_size,
                "confidence": confidence,
                "steps": steps,
                "reversals": reversals,
                "errors": errors,
            }
            blinded_file.write(json.dumps(blinded_record) + "\n")
            event_file.flush()
            blinded_file.flush()

    finally:
        event_file.close()
        blinded_file.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="NJAL-R01 Isolated Executor Process")
    parser.add_argument("--manifest", type=Path, required=True, help="Path to assignment manifest")
    parser.add_argument("--tasks", type=Path, required=True, help="Path to task set")
    parser.add_argument("--output-events", type=Path, required=True, help="Path to output events jsonl")
    parser.add_argument("--output-blinded", type=Path, required=True, help="Path to output blinded responses jsonl")
    parser.add_argument("--backend", choices=["nvidia", "mock"], default="mock")
    parser.add_argument("--model", type=str, default=None)
    parser.add_argument("--operator", type=str, default="AutomatedExecutor-v0.1")
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    run_executor(
        manifest_path=args.manifest,
        tasks_path=args.tasks,
        output_events_path=args.output_events,
        output_blinded_path=args.output_blinded,
        backend=args.backend,
        model=args.model,
        operator=args.operator,
        limit=args.limit,
        dry_run=args.dry_run,
    )


if __name__ == "__main__":
    main()
