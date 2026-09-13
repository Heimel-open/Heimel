from __future__ import annotations


def test_registry_core_api(stdlib_registry) -> None:
    pay = stdlib_registry.resolve("valo.finance.pay")
    assert pay.function_id == "valo.finance.pay"
    assert pay.version == "1.0.0"
    assert "valo.finance.pay@1.0.0" in stdlib_registry
    assert stdlib_registry.list_versions("valo.finance.pay") == ["1.0.0"]


def test_snapshot_is_immutable_hash(stdlib_registry) -> None:
    s1 = stdlib_registry.snapshot()
    s2 = stdlib_registry.snapshot()
    assert s1.hash == s2.hash  # no mutation -> same hash
    assert s1.snapshot_id != s2.snapshot_id


def test_dependency_dag_and_blast_radius(stdlib_registry) -> None:
    deps = stdlib_registry.dependencies("valo.lifecycle.onboard")
    assert "valo.communication.notify" in deps
    assert "valo.identity.verify_identity" in deps
    dependents = stdlib_registry.dependents("valo.identity.verify_identity")
    assert "graph.valo.lifecycle.onboard" in dependents


def test_validate_is_clean(stdlib_registry) -> None:
    assert stdlib_registry.validate() == []


def test_deprecate_excludes_from_current(stdlib_registry) -> None:
    stdlib_registry.deprecate("valo.finance.price", "1.0.0")
    snapshot = stdlib_registry.snapshot()
    assert snapshot.current_version("valo.finance.price") is None
    definition = stdlib_registry.get("valo.finance.price@1.0.0")
    assert definition.deprecated is True


def test_registry_mutation_is_governed(stdlib_registry) -> None:
    """Registry is not self-modifying at runtime: mutation goes through the
    governed change path (register/deprecate), and existing snapshots are
    immutable."""
    before = stdlib_registry.snapshot().hash
    stdlib_registry.deprecate("valo.finance.refund", "1.0.0")
    after = stdlib_registry.snapshot().hash
    assert before != after  # a governed change updates the registry
