from __future__ import annotations

import pytest
from pydantic import ValidationError

from valo_kernel.contracts.authority_root import AuthorityRootBinding
from valo_kernel.kernel.authority_root import seal_authority_root_binding


def _root(**updates):
    values = {
        "root_id": "authority-root-1",
        "principal_id": "principal-1",
        "identity_artifact_digest": "a" * 64,
        "governance_artifact_digest": "b" * 64,
        "recovery_plan_digest": "c" * 64,
        "credential_epoch": 7,
    }
    values.update(updates)
    return seal_authority_root_binding(**values)


def test_authority_root_belongs_to_logical_principal() -> None:
    root = _root()

    assert root.principal_is_authority_root is True
    assert root.credentials_rotatable is True
    assert root.compute_location_confers_authority is False
    assert root.hardware_endorsement_confers_authority is False
    assert root.provider_account_confers_authority is False
    assert root.model_identity_confers_authority is False
    assert root.can_issue_clearance is False
    assert root.root_digest == root.computed_digest


def test_credential_rotation_does_not_move_authority_root() -> None:
    before = _root(credential_epoch=7)
    after = _root(credential_epoch=8)

    assert before.principal_id == after.principal_id
    assert before.root_id == after.root_id
    assert before.root_digest != after.root_digest
    assert after.principal_is_authority_root is True


@pytest.mark.parametrize(
    ("field", "value"),
    (
        ("compute_location_confers_authority", True),
        ("hardware_endorsement_confers_authority", True),
        ("provider_account_confers_authority", True),
        ("model_identity_confers_authority", True),
        ("credentials_rotatable", False),
        ("can_issue_clearance", True),
    ),
)
def test_infrastructure_cannot_become_authority_root(field: str, value: bool) -> None:
    values = {
        "root_id": "authority-root-1",
        "principal_id": "principal-1",
        "identity_artifact_digest": "a" * 64,
        "governance_artifact_digest": "b" * 64,
        "recovery_plan_digest": "c" * 64,
        "credential_epoch": 7,
        field: value,
    }

    with pytest.raises(ValidationError):
        AuthorityRootBinding(**values)
