import pytest

from src.valo_platform.advisor_fabric import (
    AdvisorAuthorityBoundary,
    AdvisorSurfaceAdapter,
    AdvisorSurfaceKind,
    DashboardSurfaceInput,
    OlavCaptureSurfaceInput,
)


def test_olav_capture_is_wrapped_into_advisor_context_package() -> None:
    package = AdvisorSurfaceAdapter().from_olav_capture(
        package_id="surface-pkg-1",
        role="ciso",
        capture=OlavCaptureSurfaceInput(
            capture_id="capture-1",
            selected_text="API gateway RCE has active exploit pressure in production.",
            source="browser",
            url="https://example.com/security-note",
            page_title="Security note",
            app_name="Chrome",
            user_intent="save_idea",
            suggested_actions=["review_patch", "notify_owner"],
        ),
    )

    assert package.surface_kind == AdvisorSurfaceKind.OLAV_CAPTURE
    assert package.context_package.role == "ciso"
    assert package.context_package.authority_boundary == AdvisorAuthorityBoundary.ADVISORY_ONLY
    assert package.context_package.context_refs[0].source_type == "olav_surface_context"
    assert package.surface_summary["suggested_actions"] == ["review_patch", "notify_owner"]


def test_dashboard_entry_is_wrapped_into_enterprise_context_package() -> None:
    package = AdvisorSurfaceAdapter().from_dashboard_entry(
        package_id="surface-pkg-2",
        role="cfo",
        entry=DashboardSurfaceInput(
            signal_id="signal-42",
            title="Renewal concentration is climbing",
            decision="MONITOR",
            authority_required="CFO",
            total_exposure_usd=2400000,
            advisor_consensus="MONITOR",
        ),
    )

    assert package.surface_kind == AdvisorSurfaceKind.DASHBOARD_ENTRY
    assert package.context_package.role == "cfo"
    assert package.context_package.context_refs[0].source_type == "enterprise_context"
    assert package.context_package.context_refs[0].metadata["authority_required"] == "CFO"


def test_adapter_rejects_empty_olav_text() -> None:
    with pytest.raises(ValueError, match="cannot be empty"):
        AdvisorSurfaceAdapter().from_olav_capture(
            package_id="surface-pkg-3",
            role="ciso",
            capture=OlavCaptureSurfaceInput(
                capture_id="capture-2",
                selected_text="   ",
                source="browser",
            ),
        )


def test_adapter_does_not_import_legacy_surface_runtimes() -> None:
    import src.valo_platform.advisor_fabric.surface_adapters as adapters

    assert "valo_platform.api.capture_routes" not in adapters.__dict__
    assert "valo_platform.api.conversational_advisor_routes" not in adapters.__dict__
    assert "valo_platform.floating_advisor" not in adapters.__dict__
