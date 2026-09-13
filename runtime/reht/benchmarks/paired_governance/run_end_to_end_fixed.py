from __future__ import annotations

from datetime import timedelta

from valo_kernel import KernelEngine
from valo_kernel.contracts import EntityType

from benchmarks.paired_governance import run_end_to_end as base


def _engine_for(scenario_id: str, *, now):
    """Build Kernel state without backdating CanonicalEvent effective_at."""
    engine = KernelEngine(base.TENANT)
    engine.append(base._entity_event(base.ACTOR, EntityType.AGENT, now=now))
    engine.append(base._entity_event(base.TARGET, EntityType.JOB, now=now))
    engine.append(base._entity_event("target-2", EntityType.JOB, now=now))
    if scenario_id != "PG-013":
        engine.append(base._identity_event(now=now))

    valid_until = now + timedelta(minutes=10)
    if scenario_id == "PG-002":
        valid_until = now - timedelta(seconds=1)
    engine.append(
        base._authority_event(
            now=now,
            valid_until=valid_until,
            scope=[base.TARGET, "target-2"] if scenario_id == "PG-015" else [base.TARGET],
        )
    )
    if scenario_id == "PG-003":
        engine.append(base._revoke_event(now=now))
    return engine


def _kernel_context(engine, action, *, now, scenario_id, nonce):
    request = base._request_event(
        capability=action["capability"],
        target=action["target"],
        now=now,
        nonce=nonce,
    )
    context = base.build_execution_context(
        engine.state(),
        actor=base.ACTOR,
        capability=action["capability"],
        target=action["target"],
        requested_transition=request,
        identity_id=None,
        purpose_id=action.get("purpose_id"),
        moment=now,
        execution_nonce=nonce,
    )
    if scenario_id == "PG-007":
        context = dict(context)
        context["time"] = {}
    return context


def main() -> None:
    base._engine_for = _engine_for
    base._kernel_context = _kernel_context
    base.main()


if __name__ == "__main__":
    main()
