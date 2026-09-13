"""NJAL-R02 Two-Process Isolated Pipeline Orchestrator.

Orchestrates execution, scoring, and analysis in strictly isolated subprocesses.
Guarantees:
1. Physical isolation: Executor runs inside an isolated temporary sandbox with NO answer key on filesystem.
2. Governed state machine: Deterministic consequence gating operates in executor harness.
3. Condition-neutral handoff: Executor emits blinded responses strictly stripped of condition labels, prompts,
   and structural scaffolding.
4. Blind scoring: Scorer independently scores correctness and dependency preservation without condition context.
5. Gated unblinding: Conditions are unblinded strictly post-scoring in the analyzer.
"""

from __future__ import annotations

import argparse
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile


def run_pipeline(
    manifest_path: Path,
    tasks_path: Path,
    answer_key_path: Path,
    dependency_map_path: Path,
    output_dir: Path,
    backend: str = "mock",
    model: str | None = None,
    operator: str = "AutomatedExecutor-v0.2",
    scorer_id: str = "AutomatedScorer-v0.2",
    dry_run: bool = False,
    limit: int | None = None,
) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)

    events_path = output_dir / "audit-events-v0.1.jsonl"
    blinded_responses_path = output_dir / "blinded-responses-v0.1.jsonl"
    blinded_scores_path = output_dir / "blinded-scores-v0.1.jsonl"
    report_json_path = output_dir / "analysis-report-v0.1.json"
    report_md_path = output_dir / "analysis-summary-v0.1.md"

    print("=" * 75)
    print("STEP 1: LAUNCHING PHYSICALLY ISOLATED EXECUTOR SUBPROCESS (NJAL-R02)")
    print("Physical Isolation: Sandboxed temporary directory with NO answer-key file.")
    print("Governed State Machine: Consequence triggers evaluated by execution harness.")
    print("Condition-Neutral Blinding: Emits responses stripped of condition labels & prompts.")
    print("=" * 75)

    with tempfile.TemporaryDirectory(prefix="njal_r02_executor_sandbox_") as sandbox_dir:
        sandbox_path = Path(sandbox_dir)
        sandbox_manifest = sandbox_path / "assignment-manifest.json"
        sandbox_tasks = sandbox_path / "task-set.jsonl"
        sandbox_dep_map = sandbox_path / "dependency-map.json"
        shutil.copy2(manifest_path, sandbox_manifest)
        shutil.copy2(tasks_path, sandbox_tasks)
        shutil.copy2(dependency_map_path, sandbox_dep_map)

        # Confirm answer key is NOT in sandbox
        assert not (sandbox_path / "answer-key-v0.1.jsonl").exists()
        assert not any("answer" in f.name.lower() for f in sandbox_path.iterdir())

        sandbox_events = sandbox_path / "audit-events.jsonl"
        sandbox_blinded = sandbox_path / "blinded-responses.jsonl"

        repo_root = Path(__file__).resolve().parents[1]
        executor_script = repo_root / "tools" / "njal_r02_executor.py"

        executor_cmd = [
            sys.executable,
            str(executor_script),
            "--manifest",
            str(sandbox_manifest),
            "--tasks",
            str(sandbox_tasks),
            "--dependency-map",
            str(sandbox_dep_map),
            "--output-events",
            str(sandbox_events),
            "--output-blinded",
            str(sandbox_blinded),
            "--backend",
            backend,
            "--operator",
            operator,
        ]
        if model:
            executor_cmd.extend(["--model", model])
        if dry_run:
            executor_cmd.append("--dry-run")
        if limit:
            executor_cmd.extend(["--limit", str(limit)])

        res1 = subprocess.run(executor_cmd, cwd=str(sandbox_path), check=True)
        if res1.returncode != 0:
            raise RuntimeError(f"Executor process failed with exit code {res1.returncode}")

        # Move generated artifacts from sandbox to target output directory
        shutil.copy2(sandbox_events, events_path)
        shutil.copy2(sandbox_blinded, blinded_responses_path)

    print("\n" + "=" * 75)
    print("STEP 2: LAUNCHING ISOLATED BLIND SCORER SUBPROCESS (NJAL-R02)")
    print("Invariants: Zero condition tokens. Evaluates correctness and dependency preservation.")
    print("=" * 75)

    scorer_script = repo_root / "tools" / "njal_r02_scorer.py"
    scorer_cmd = [
        sys.executable,
        str(scorer_script),
        "--blinded-responses",
        str(blinded_responses_path),
        "--answer-key",
        str(answer_key_path),
        "--dependency-map",
        str(dependency_map_path),
        "--output-scores",
        str(blinded_scores_path),
        "--scorer-id",
        scorer_id,
    ]
    res2 = subprocess.run(scorer_cmd, cwd=str(repo_root), check=True)
    if res2.returncode != 0:
        raise RuntimeError(f"Blind scorer process failed with exit code {res2.returncode}")

    print("\n" + "=" * 75)
    print("STEP 3: LAUNCHING HYPOTHESIS ANALYZER & GATED UNBLINDING (NJAL-R02)")
    print("Invariants: Manifest joined strictly post-scoring to evaluate H1-H4.")
    print("=" * 75)

    analyzer_script = repo_root / "tools" / "njal_r02_analyzer.py"
    analyzer_cmd = [
        sys.executable,
        str(analyzer_script),
        "--manifest",
        str(manifest_path),
        "--blinded-scores",
        str(blinded_scores_path),
        "--output-report",
        str(report_json_path),
        "--output-summary",
        str(report_md_path),
    ]
    res3 = subprocess.run(analyzer_cmd, cwd=str(repo_root), check=True)
    if res3.returncode != 0:
        raise RuntimeError(f"Analyzer process failed with exit code {res3.returncode}")

    print("\n" + "=" * 75)
    print("NJAL-R02 ISOLATED PIPELINE EXECUTION COMPLETE")
    print(f"Audit log: {events_path}")
    print(f"Blinded responses: {blinded_responses_path}")
    print(f"Blinded scores: {blinded_scores_path}")
    print(f"Analysis report: {report_json_path}")
    print(f"Analysis summary: {report_md_path}")
    print("=" * 75)


def main() -> None:
    parser = argparse.ArgumentParser(description="NJAL-R02 Isolated Two-Process Pipeline")
    parser.add_argument("--runs-dir", type=Path, default=Path("runs/NJAL-R02"))
    parser.add_argument("--backend", choices=["nvidia", "mock"], default="mock")
    parser.add_argument("--model", type=str, default=None)
    parser.add_argument("--operator", type=str, default="AutomatedExecutor-v0.2")
    parser.add_argument("--scorer-id", type=str, default="AutomatedScorer-v0.2")
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    runs_dir = args.runs_dir.resolve()
    manifest_path = runs_dir / "assignment-manifest-v0.1.json"
    tasks_path = runs_dir / "task-set-v0.1.jsonl"
    answer_key_path = runs_dir / "answer-key-v0.1.jsonl"
    dependency_map_path = runs_dir / "dependency-map-v0.1.json"

    run_pipeline(
        manifest_path=manifest_path,
        tasks_path=tasks_path,
        answer_key_path=answer_key_path,
        dependency_map_path=dependency_map_path,
        output_dir=runs_dir,
        backend=args.backend,
        model=args.model,
        operator=args.operator,
        scorer_id=args.scorer_id,
        dry_run=args.dry_run,
        limit=args.limit,
    )


if __name__ == "__main__":
    main()
