from __future__ import annotations

from ..compiler import validate_function_definition
from ..contracts.pack import Pack
from ..registry.store import FunctionRegistry


class PackError(ValueError):
    """A pack tried to weaken core governance or bypass a boundary."""


def apply_pack(registry: FunctionRegistry, pack: Pack) -> int:
    """Apply a domain/country pack. Packs may add domain types, functions,
    rules and mappings. They can NEVER weaken core governance, redefine ISA
    semantics, bypass REHT, or write Kernel state directly."""
    for rule in pack.rules:
        if rule.severity not in ("REQUIRED", "ADVISORY"):
            raise PackError(f"pack {pack.pack}: unknown rule severity {rule.severity}")
        if rule.constraint_type == "WEAKEN" or "weaken" in rule.predicate.lower():
            raise PackError(f"pack {pack.pack}: rules may tighten, never weaken core governance")

    available = set(registry.snapshot().graphs)
    count = 0
    for definition in pack.functions:
        graph_identity = definition.workflow_ref
        if graph_identity not in available:
            raise PackError(
                f"pack {pack.pack}: function {definition.identity} references unregistered workflow {definition.workflow_ref}"
            )
        validate_function_definition(definition, registry.graph_for(definition))
        # A pack may tighten, never weaken: compare against the current active version.
        try:
            existing = registry.resolve(definition.function_id)
        except Exception:
            existing = None
        if existing is not None:
            from ..registry.upgrade import UpgradeComparison

            comparison = UpgradeComparison(existing, definition)
            if comparison.is_breaking_governance():
                raise PackError(
                    f"pack {pack.pack}: {definition.identity} weakens governance "
                    f"({comparison.breaking_change_label().value})"
                )
        registry.register(definition, registry.graph_for(definition))
        count += 1
    return count


def country_pack(country: str) -> Pack:
    """Extension point for country packs (countries/no, countries/se, ...).
    A country pack adds jurisdiction mappings, legal references and channel
    mappings; it does not change Function semantics."""
    mapping: dict[str, str] = {
        "jurisdiction": country.upper(),
        "identity_source": f"registry.{country.lower()}",
        "payment_format": f"format.{country.lower()}",
    }
    return Pack(pack=f"country-{country}", version="1.0.0", mappings=mapping)

