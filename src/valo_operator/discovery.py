"""Read-only discovery of registered Functions and their capability surface."""

from __future__ import annotations

from typing import Any


def discover_functions(registry: Any) -> list[dict[str, Any]]:
    """Deterministic, read-only listing of every registered Function: identity,
    name, effects, risk, capability requirements, typed input/output and
    idempotency. Clients use this to discover what actions exist and what they
    require — never to mutate anything."""
    snapshot = registry.snapshot()
    entries = sorted(snapshot.functions.items())
    discovered = []
    for _identity, entry in entries:
        d = entry.definition
        discovered.append(
            {
                "function_id": d.function_id,
                "name": d.name,
                "version": d.version,
                "effects": list(d.effects),
                "risk_class": d.risk_class.value,
                "capabilities": sorted({a.capability for a in d.authority_requirements}),
                "input_type": {"name": d.input_type.name, "type": d.input_type.type},
                "output_type": {"name": d.output_type.name, "type": d.output_type.type},
                "idempotency": d.idempotency_requirement.value,
            }
        )
    return discovered


def capabilities(registry: Any) -> list[str]:
    """The full set of capabilities required across all registered Functions."""
    caps: set[str] = set()
    for info in discover_functions(registry):
        caps.update(info["capabilities"])
    return sorted(caps)


def find_functions_by_capability(registry: Any, capability: str) -> list[str]:
    """Functions that require the given capability (discovery aid, not an
    authorization decision)."""
    return [
        info["function_id"]
        for info in discover_functions(registry)
        if capability in info["capabilities"]
    ]
