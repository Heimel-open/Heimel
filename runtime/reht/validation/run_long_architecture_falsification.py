from __future__ import annotations

import argparse
import json
from pathlib import Path

from valo_reht.active_session import ObservationSource, SessionDisposition, SessionObservation, SessionState

from validation import long_architecture_falsification as harness

RUN_REQUEST_ID = "2026-08-26T07:00Z-long-architecture-falsification"


def stress_session_continuity(iterations: int) -> dict[str, int]:
    """Run drift and attenuation independently so neither masks the other."""
    drift_forced_reauth = 0
    denied_reauth_halted = 0
    widening_rejected = 0
    for i in range(iterations):
        session = harness._session(i + 1)
        changed = harness._context(harness._action(i + 1), i + 2)
        checkpoint = session.observe(
            execution_context=changed,
            observation=SessionObservation(
                ObservationSource.WATCHER,
                SessionDisposition.CONTINUE,
            ),
        )
        if (
            checkpoint.disposition is not SessionDisposition.REAUTHORIZE
            or session.state is not SessionState.PAUSED
            or not session.requires_reauthorization
        ):
            raise AssertionError("context drift did not force reauthorization")
        drift_forced_reauth += 1

        denied = session.reauthorize(
            reht=harness.StaticReht("DENY"),
            execution_context=changed,
        )
        if denied.disposition is not SessionDisposition.HALT or session.state is not SessionState.HALTED:
            raise AssertionError("failed reauthorization did not halt session")
        denied_reauth_halted += 1

        version = 10_000_000 + i
        fresh = harness._session(version)
        current = harness._context(harness._action(version), version)
        fresh.observe(
            execution_context=current,
            observation=SessionObservation(
                ObservationSource.SYSTEM,
                SessionDisposition.CONTINUE,
                bound_updates={"max_usd": 50.0, "targets": ("a",), "may_retry": False},
            ),
        )
        if fresh.dynamic_bounds["max_usd"] != 50.0:
            raise AssertionError("narrowing update was not applied")
        try:
            fresh.observe(
                execution_context=current,
                observation=SessionObservation(
                    ObservationSource.SYSTEM,
                    SessionDisposition.CONTINUE,
                    bound_updates={"max_usd": 75.0},
                ),
            )
        except ValueError:
            widening_rejected += 1
        else:
            raise AssertionError("runtime bound widening was accepted")

    return {
        "drift_forced_reauth": drift_forced_reauth,
        "denied_reauth_halted": denied_reauth_halted,
        "widening_rejected": widening_rejected,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--iterations", type=int, default=harness.DEFAULT_ITERATIONS)
    parser.add_argument("--seed", type=int, default=harness.DEFAULT_SEED)
    parser.add_argument(
        "--output",
        default="validation/results/long_architecture_falsification.json",
    )
    args = parser.parse_args()

    harness.stress_session_continuity = stress_session_continuity
    payload = harness.run(args.iterations, args.seed)
    payload["harness_correction"] = "session drift and bound attenuation tested independently"
    payload["run_request_id"] = RUN_REQUEST_ID
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(payload, indent=2, sort_keys=True))
    if payload["classification"] != "PASS":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
