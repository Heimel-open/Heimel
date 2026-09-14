from valo_gateway.claims_instrumentation import Status, verify_claim

REQ = ["actor", "action", "entity", "scope", "permitted"]


def base():
    authority = {
        "actor": "alice",
        "action": "approve_payment",
        "entity": "acme",
        "scope": "finance",
        "permitted": True,
        "exception": "cybersecurity",
        "valid_until": 200,
    }
    claim = dict(authority)
    return claim, authority


def test_supported_exact_match():
    claim, authority = base()
    result = verify_claim(claim, authority, required_fields=REQ, scope_fields=["scope"], constraint_fields=["exception"], freshness_field="valid_until", verification_time=100)
    assert result.status is Status.SUPPORTED


def test_contradicted_material_claim():
    claim, authority = base()
    claim["permitted"] = False
    result = verify_claim(claim, authority, required_fields=REQ, scope_fields=["scope"], constraint_fields=["exception"])
    assert result.status is Status.CONTRADICTED


def test_unknown_missing_claim_predicate():
    claim, authority = base()
    del claim["permitted"]
    assert verify_claim(claim, authority, required_fields=REQ).status is Status.UNKNOWN


def test_unknown_missing_constraint():
    claim, authority = base()
    del claim["exception"]
    result = verify_claim(claim, authority, required_fields=REQ, constraint_fields=["exception"])
    assert result.status is Status.UNKNOWN


def test_contradicted_constraint_shift():
    claim, authority = base()
    claim["exception"] = "none"
    result = verify_claim(claim, authority, required_fields=REQ, constraint_fields=["exception"])
    assert result.status is Status.CONTRADICTED


def test_contradicted_scope_shift():
    claim, authority = base()
    claim["scope"] = "global"
    result = verify_claim(claim, authority, required_fields=REQ, scope_fields=["scope"])
    assert result.status is Status.CONTRADICTED


def test_contradicted_stale_authority():
    claim, authority = base()
    result = verify_claim(claim, authority, required_fields=REQ, freshness_field="valid_until", verification_time=201)
    assert result.status is Status.CONTRADICTED


def test_unknown_freshness_unavailable():
    claim, authority = base()
    del authority["valid_until"]
    result = verify_claim(claim, authority, required_fields=REQ, freshness_field="valid_until", verification_time=100)
    assert result.status is Status.UNKNOWN


def test_unknown_unstructured_claim_serializes():
    _, authority = base()
    result = verify_claim(None, authority, required_fields=REQ)
    assert result.status is Status.UNKNOWN
    assert result.to_dict()["claim"] == {}


def test_unknown_missing_authority_serializes():
    claim, _ = base()
    result = verify_claim(claim, None, required_fields=REQ)
    assert result.status is Status.UNKNOWN
    assert result.to_dict()["authority"] == {}
