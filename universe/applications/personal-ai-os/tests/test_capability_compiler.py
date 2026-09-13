from paios.capability_compiler import (
    CapabilityCompiler,
    Outcome,
    Resource,
    demo_resources,
    invoice_demo_evaluator,
    run_invoice_demo,
)


def test_invoice_demo_finds_minimal_low_cost_composition():
    certificate = run_invoice_demo()
    assert certificate.realized is True
    assert certificate.minimal is True
    assert certificate.resource_ids == (
        "ocr-local",
        "policy-agent",
        "erp-connector",
    )
    assert certificate.total_cost == 0.15


def test_each_member_of_minimal_composition_is_necessary():
    certificate = run_invoice_demo()
    assert certificate.necessary_resource_ids == certificate.resource_ids
    assert all(item.still_realized is False for item in certificate.ablations)


def test_no_individual_resource_realizes_invoice_outcome():
    outcome = Outcome("invoice-ready-to-post", "invoice")
    for resource in demo_resources():
        assert invoice_demo_evaluator(outcome, (resource,)) is False


def test_compiler_returns_unrealized_when_no_composition_works():
    compiler = CapabilityCompiler(lambda outcome, composition: False)
    certificate = compiler.compile(
        Outcome("never", "never"),
        (Resource("a", "x", 1.0), Resource("b", "y", 2.0)),
    )
    assert certificate.realized is False
    assert certificate.resource_ids == ()
    assert certificate.minimal is False


def test_cardinality_beats_cost_for_minimal_composition():
    outcome = Outcome("x", "x")
    resources = (
        Resource("single", "single", 100.0),
        Resource("cheap-a", "a", 1.0),
        Resource("cheap-b", "b", 1.0),
    )

    def evaluator(_outcome, composition):
        ids = {item.resource_id for item in composition}
        return "single" in ids or {"cheap-a", "cheap-b"}.issubset(ids)

    certificate = CapabilityCompiler(evaluator).compile(outcome, resources)
    assert certificate.resource_ids == ("single",)
    assert certificate.total_cost == 100.0
