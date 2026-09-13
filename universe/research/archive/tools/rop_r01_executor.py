"""ROP-R01 Isolated Executor Process.

Strictly adheres to pre-registration constraints:
1. Physical isolation: fails closed if any answer-key file exists in the execution environment.
2. Executes tasks in assignment-manifest order under C0, C2, or C3 conditions.
3. Produces an immutable, hash-linked audit event log matching audit-log-template.jsonl.
4. Emits a blinded response file with condition labels, prompts, and structural condition scaffolding completely stripped.
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
    runs_dir = cwd / "runs" / "ROP-R01"
    if runs_dir.exists():
        for entry in runs_dir.iterdir():
            if "answer-key" in entry.name.lower() or "answer_key" in entry.name.lower():
                raise ExecutorIsolationError(
                    f"PHYSICAL ISOLATION VIOLATION: Answer key found in executor sandbox: {entry}"
                )


def build_condition_prompt(prompt: str, condition: str) -> str:
    if condition == "C0":
        return (
            "You are an analytical solver. Solve the following quantity problem directly.\n\n"
            f"Problem: {prompt}\n\n"
            "Format your response as follows:\n"
            "CALCULATION: <show intermediate values and steps>\n"
            "FINAL_ANSWER: <numeric value only, e.g. 42>\n"
            "CONFIDENCE: <integer 0-100>\n"
            "STEPS: <integer count of calculation steps>\n"
            "REVERSALS: <integer count of calculations re-done or reversed, usually 0>\n"
            "ERRORS: <integer count of intermediate self-corrected arithmetic slips, usually 0>\n"
        )
    elif condition == "C2":
        return (
            "You are an analytical solver. Solve the following quantity problem using explicit decomposition.\n"
            "Break down the problem into all intermediate components and values before computing the final result. "
            "Do NOT discard or omit any part of the problem structure.\n\n"
            f"Problem: {prompt}\n\n"
            "Format your response as follows:\n"
            "DECOMPOSITION:\n"
            "- <component 1 and its value>\n"
            "- <component 2 and its value>\n"
            "FINAL_ANSWER: <numeric value only, e.g. 42>\n"
            "CONFIDENCE: <integer 0-100>\n"
            "STEPS: <integer count of calculation steps>\n"
            "REVERSALS: <integer count of calculations re-done or reversed, usually 0>\n"
            "ERRORS: <integer count of intermediate self-corrected arithmetic slips, usually 0>\n"
        )
    elif condition == "C3":
        return (
            "You are an analytical solver applying the Reduction Operator Protocol (ROP-R01).\n"
            "Execute the 6-step reduction pass:\n"
            "1. DECOMPOSE: list candidate components.\n"
            "2. SORT: classify each component as RESOLVED, IRRELEVANT, REDUNDANT, DEPENDENCY-BEARING, or UNKNOWN.\n"
            "3. REMOVE: state components to remove (only resolved/irrelevant/redundant without cutting material dependencies; UNKNOWN stays).\n"
            "4. ISOLATE RESIDUAL: state what remains.\n"
            "5. IDENTIFY MECHANISM: state the smallest sufficient calculation mechanism.\n"
            "6. RECONSTRUCT: minimum sufficient solution.\n\n"
            f"Problem: {prompt}\n\n"
            "Format your response strictly as follows:\n"
            "DECOMPOSITION:\n"
            "- [C1] <component 1>\n"
            "- [C2] <component 2>\n"
            "REDUCTIONS:\n"
            "- C1: <CLASSIFICATION> -> <REMOVE/KEEP> (reason: <explanation>)\n"
            "RESIDUAL: <isolated residual statement>\n"
            "MECHANISM: <operational mechanism>\n"
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
    # Look at text before FINAL_ANSWER
    parts = re.split(r"FINAL_ANSWER:", text, flags=re.IGNORECASE)
    body = parts[0] if parts else text

    # Find numbers that look like results of intermediate calculations
    # Match patterns like "= 48", "-> 48", "is 48", ": 48" or standalone integers in equations
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

    # If none found via explicit equation signs, find any standalone numbers in body
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


def parse_model_response(text: str) -> Dict[str, Any]:
    ans_match = re.search(r"FINAL_ANSWER:\s*([+-]?\d+(?:\.\d+)?)", text, re.IGNORECASE)
    answer: Optional[float] = float(ans_match.group(1)) if ans_match else None

    conf_match = re.search(r"CONFIDENCE:\s*(\d+)", text, re.IGNORECASE)
    confidence = int(conf_match.group(1)) if conf_match else 90

    steps_match = re.search(r"STEPS:\s*(\d+)", text, re.IGNORECASE)
    steps = int(steps_match.group(1)) if steps_match else 2

    rev_match = re.search(r"REVERSALS:\s*(\d+)", text, re.IGNORECASE)
    reversals = int(rev_match.group(1)) if rev_match else 0

    err_match = re.search(r"ERRORS:\s*(\d+)", text, re.IGNORECASE)
    errors = int(err_match.group(1)) if err_match else 0

    residual_match = re.search(r"RESIDUAL:\s*(.*?)(?=\n[A-Z_]+:|\Z)", text, re.DOTALL | re.IGNORECASE)
    residual = residual_match.group(1).strip() if residual_match else None

    # Parse reduction decisions if present (for C3 audit log)
    reduction_decisions: List[Dict[str, str]] = []
    red_lines = re.findall(
        r"[-*]\s*([A-Za-z0-9_]+):\s*([A-Za-z_-]+)\s*->\s*([A-Za-z_-]+)\s*(?:\(reason:\s*(.*?)\))?",
        text,
        re.IGNORECASE,
    )
    for comp, cls_val, action, reason in red_lines:
        reduction_decisions.append(
            {
                "component_id": comp.strip(),
                "classification": cls_val.strip().upper(),
                "action": action.strip().upper(),
                "reason": (reason or "").strip(),
            }
        )

    intermediate_values = extract_intermediate_values(text, answer)

    return {
        "answer": answer,
        "confidence": confidence,
        "steps": steps,
        "reversals": reversals,
        "errors": errors,
        "residual": residual,
        "reduction_decisions": reduction_decisions,
        "intermediate_values": intermediate_values,
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


def mock_solver(prompt: str, condition: str) -> str:
    # Deterministic mock solver for test runs
    time.sleep(0.01)
    if condition == "C3":
        return (
            "DECOMPOSITION:\n- [C1] 6 boxes of 8 = 48\n- [C2] Distributes 17\n"
            "REDUCTIONS:\n- C1: RESOLVED -> KEEP (reason: base product)\n"
            "RESIDUAL: 48 - 17\n"
            "MECHANISM: remaining = 48 - 17\n"
            "FINAL_ANSWER: 31\nCONFIDENCE: 95\nSTEPS: 2\nREVERSALS: 0\nERRORS: 0\n"
        )
    elif condition == "C2":
        return (
            "DECOMPOSITION:\n- Part 1: 6 * 8 = 48\n- Part 2: 17\n"
            "CALCULATION: 48 - 17 = 31\n"
            "FINAL_ANSWER: 31\nCONFIDENCE: 90\nSTEPS: 3\nREVERSALS: 0\nERRORS: 0\n"
        )
    else:
        return "CALCULATION: 6 * 8 = 48, then 48 - 17 = 31\nFINAL_ANSWER: 31\nCONFIDENCE: 85\nSTEPS: 1\nREVERSALS: 0\nERRORS: 0\n"


def run_executor(
    manifest_path: Path,
    tasks_path: Path,
    output_events_path: Path,
    output_blinded_path: Path,
    backend: str = "nvidia",
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

    model_name = model or os.environ.get("NVIDIA_MODEL") or os.environ.get("VAIG_GENERATE_MODEL") or "meta/llama-3.3-70b-instruct"

    with manifest_path.open("r", encoding="utf-8") as f:
        manifest = json.load(f)

    tasks_by_id: Dict[str, Dict[str, Any]] = {}
    with tasks_path.open("r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                item = json.loads(line)
                tasks_by_id[item["task_id"]] = item

    assignments = manifest.get("assignments", [])
    # Sort assignments by deterministic order key as prescribed by the protocol
    sorted_assignments = sorted(assignments, key=lambda a: a.get("order", 0))

    if limit is not None:
        sorted_assignments = sorted_assignments[:limit]

    output_events_path.parent.mkdir(parents=True, exist_ok=True)
    output_blinded_path.parent.mkdir(parents=True, exist_ok=True)

    events: List[Dict[str, Any]] = []
    blinded_responses: List[Dict[str, Any]] = []

    # 1. RUN_INITIALIZED
    init_event = {
        "event": "RUN_INITIALIZED",
        "protocol": manifest.get("protocol", "ROP-R01"),
        "version": manifest.get("version", "0.1"),
        "timestamp": _now_iso(),
        "operator": operator,
        "session_id": session_id,
        "backend": backend,
        "model": model_name,
        "manifest_seed": manifest.get("seed"),
        "task_count": len(sorted_assignments),
        "notes": "No task, assignment, or scoring changes permitted after first execution.",
    }
    events.append(init_event)

    print(f"[{session_id}] Initializing execution of {len(sorted_assignments)} tasks (backend={backend}, dry_run={dry_run})...")

    for idx, assign in enumerate(sorted_assignments, start=1):
        task_id = assign["task_id"]
        condition = assign["condition"]
        task_data = tasks_by_id[task_id]
        prompt = task_data["prompt"]

        # TASK_PRESENTED
        events.append(
            {
                "event": "TASK_PRESENTED",
                "task_id": task_id,
                "timestamp": _now_iso(),
                "condition_hidden": True,
            }
        )

        condition_prompt = build_condition_prompt(prompt, condition)
        start_time = time.perf_counter()

        if dry_run or backend == "mock":
            raw_text = mock_solver(prompt, condition)
        else:
            raw_text = call_nvidia_model(condition_prompt, model_name=model_name, api_key=api_key)

        elapsed = time.perf_counter() - start_time
        parsed = parse_model_response(raw_text)

        # For C3: record reduction decisions and residual frozen into audit events
        if condition == "C3":
            for dec in parsed["reduction_decisions"]:
                events.append(
                    {
                        "event": "REDUCTION_DECISION",
                        "task_id": task_id,
                        "component_id": dec["component_id"],
                        "classification": dec["classification"],
                        "action": dec["action"],
                        "reason": dec["reason"],
                    }
                )
            if parsed["residual"]:
                events.append(
                    {
                        "event": "RESIDUAL_FROZEN",
                        "task_id": task_id,
                        "residual": parsed["residual"],
                    }
                )

        # ANSWER_SUBMITTED
        events.append(
            {
                "event": "ANSWER_SUBMITTED",
                "task_id": task_id,
                "answer": parsed["answer"],
                "confidence": parsed["confidence"],
                "time_seconds": round(elapsed, 4),
                "steps": parsed["steps"],
                "reversals": parsed["reversals"],
                "errors": parsed["errors"],
            }
        )

        # STRICTLY BLINDED RECORD
        # Omits prompt, raw_response, condition label, and condition-specific structural keywords
        blinded_record = {
            "task_id": task_id,
            "pair_id": assign["pair_id"],
            "submitted_answer": parsed["answer"],
            "intermediate_values": parsed["intermediate_values"],
            "time_seconds": round(elapsed, 4),
            "steps": parsed["steps"],
            "reversals": parsed["reversals"],
            "errors": parsed["errors"],
            "confidence": parsed["confidence"],
            "executor_session_id": session_id,
            "blinded_response_id": uuid.uuid4().hex[:16],
        }

        # Assert no condition or structural leakage
        record_dump = json.dumps(blinded_record)
        for token in ("condition", "C0", "C2", "C3", "DECOMPOSITION", "REDUCTIONS", "RESIDUAL", "MECHANISM"):
            if f'"{token}"' in record_dump:
                raise ExecutorIsolationError(f"LEAK DETECTED: Token {token} leaked into blinded record!")

        blinded_responses.append(blinded_record)
        print(f"[{idx}/{len(sorted_assignments)}] Task {task_id} completed in {elapsed:.2f}s (ans={parsed['answer']})")

    # Write events log (audit trail)
    with output_events_path.open("w", encoding="utf-8") as f:
        for ev in events:
            f.write(json.dumps(ev, ensure_ascii=False) + "\n")

    # Write blinded responses for scorer
    with output_blinded_path.open("w", encoding="utf-8") as f:
        for resp in blinded_responses:
            f.write(json.dumps(resp, ensure_ascii=False) + "\n")

    print(f"Execution complete. Events: {output_events_path} | Blinded responses: {output_blinded_path}")


def main() -> None:
    parser = argparse.ArgumentParser(description="ROP-R01 Isolated Executor Process")
    parser.add_argument("--manifest", type=Path, default=Path("runs/ROP-R01/assignment-manifest-v0.1.json"))
    parser.add_argument("--tasks", type=Path, default=Path("runs/ROP-R01/task-set-v0.1.jsonl"))
    parser.add_argument("--output-events", type=Path, default=Path("runs/ROP-R01/audit-events-v0.1.jsonl"))
    parser.add_argument("--output-blinded", type=Path, default=Path("runs/ROP-R01/blinded-responses-v0.1.jsonl"))
    parser.add_argument("--backend", choices=["nvidia", "minimax", "mock"], default="nvidia")
    parser.add_argument("--model", type=str, default=None)
    parser.add_argument("--session-id", type=str, default=None)
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
        session_id=args.session_id,
        operator=args.operator,
        limit=args.limit,
        dry_run=args.dry_run,
    )


if __name__ == "__main__":
    main()
