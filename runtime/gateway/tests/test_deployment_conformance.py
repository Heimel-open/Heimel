import pytest

from valo_gateway.deployment_conformance import (
    DeploymentConformanceError,
    EffectGrant,
    GrantKind,
    require_no_direct_effect_path,
    verify_no_direct_effect_path,
)


def test_gateway_only_effect_access_conforms():
    grants = [
        EffectGrant("heimel-gateway", "stripe", GrantKind.API_CREDENTIAL),
        EffectGrant("heimel-gateway", "erp", GrantKind.NETWORK_PATH),
    ]
    result = verify_no_direct_effect_path(
        grants, gateway_principals={"heimel-gateway"}
    )
    assert result.conformant
    assert result.violations == ()


@pytest.mark.parametrize(
    "kind",
    [
        GrantKind.API_CREDENTIAL,
        GrantKind.IAM_PERMISSION,
        GrantKind.DATABASE_WRITE,
        GrantKind.SERVICE_ACCOUNT,
        GrantKind.NETWORK_PATH,
        GrantKind.HUMAN_ADMIN,
    ],
)
def test_any_parallel_consequence_path_fails(kind):
    grants = [
        EffectGrant("heimel-gateway", "erp", GrantKind.NETWORK_PATH),
        EffectGrant("agent-runtime", "erp", kind),
    ]
    result = verify_no_direct_effect_path(
        grants, gateway_principals={"heimel-gateway"}
    )
    assert not result.conformant
    assert result.violations[0].principal == "agent-runtime"


def test_non_consequence_grant_is_not_violation():
    grants = [
        EffectGrant(
            "observability", "erp-read-replica", GrantKind.DATABASE_WRITE,
            consequence_capable=False,
        )
    ]
    assert verify_no_direct_effect_path(
        grants, gateway_principals={"heimel-gateway"}
    ).conformant


def test_require_fails_closed_with_visible_path():
    with pytest.raises(DeploymentConformanceError, match="agent-runtime->stripe"):
        require_no_direct_effect_path(
            [EffectGrant("agent-runtime", "stripe", GrantKind.API_CREDENTIAL)],
            gateway_principals={"heimel-gateway"},
        )
