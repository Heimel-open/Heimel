from datetime import datetime, timezone
from decimal import Decimal

from services.organizational_simulation.speider_value_scout import (
    SpeiderProfileAdapter,
    SpeiderValueScout,
    build_all_vertical_seed_profiles,
    run_all_vertical_seed_simulation,
)
from services.organizational_simulation.vertical_catalog import (
    ALL_VERTICAL_SEEDS,
    build_assumption_benchmarks,
    classify_vertical,
)
from src.valo_platform.speider_connectors.business_registry import (
    BusinessRegistryConnector,
)
from src.valo_platform.speider_connectors.models import Company, Role, RoleType


class FakeAllVerticalConnector(BusinessRegistryConnector):
    def get_company(self, org_number):
        return None

    def find_company_by_name(self, name):
        return []

    def get_company_shareholders(self, org_number):
        return []

    def get_company_roles(self, org_number):
        return [
            Role(
                role_id=f"{org_number}:ceo",
                person_name="Example Executive",
                role_type=RoleType.CEO,
                org_number=org_number,
                source="fake-registry",
            )
        ]

    def get_person_holdings(self, person_id):
        return []

    def get_company_financials(self, org_number):
        return {
            "org_number": org_number,
            "fiscal_year": 2025,
            "revenue": 200_000_000,
            "currency": "NOK",
            "source": "fake-accounts",
        }

    def get_company_grants(self, org_number):
        return []

    def search_companies(
        self,
        location=None,
        business_code=None,
        min_employees=None,
        max_employees=None,
    ):
        if business_code is None:
            return []
        return [
            Company(
                org_number=f"ORG-{business_code}",
                name=f"Company {business_code}",
                business_code=business_code,
                employee_count=max(min_employees or 0, 100),
                status="active",
                source="fake-registry",
                last_updated=datetime(2026, 7, 23, tzinfo=timezone.utc),
            )
        ]

    def get_connector_name(self):
        return "fake-registry"

    def is_healthy(self):
        return True

    def get_last_updated(self):
        return datetime(2026, 7, 23, tzinfo=timezone.utc)


def test_catalog_covers_all_nace_sections_and_sizes():
    assert [seed.section for seed in ALL_VERTICAL_SEEDS] == list("ABCDEFGHIJKLMNOPQRSTU")
    assert len(ALL_VERTICAL_SEEDS) == 21
    assert len(build_assumption_benchmarks()) == 105
    assert classify_vertical("62.010").vertical_id == "information_communication_media"
    assert classify_vertical("86.100").vertical_id == "healthcare_social_care"
    assert classify_vertical(None) is None


def test_speider_adapter_preserves_sources_and_rejects_missing_size_data():
    adapter = SpeiderProfileAdapter()
    accepted = adapter.build_profile(
        Company(
            org_number="123",
            name="Observed Company",
            business_code="64.190",
            employee_count=500,
            source="registry",
        ),
        financials={
            "revenue": 1_000_000_000,
            "currency": "NOK",
            "fiscal_year": 2025,
            "source": "accounts",
        },
        roles=[
            Role(
                role_id="role-1",
                person_name="Executive",
                role_type=RoleType.CEO,
                org_number="123",
                source="roles",
            )
        ],
    )

    assert accepted.accepted
    assert accepted.profile.vertical == "financial_services_insurance"
    assert accepted.profile.employees == 500
    assert accepted.profile.contactability == Decimal("0.75")
    assert any(ref.startswith("speider:company:") for ref in accepted.source_refs)
    assert "assumption:all-vertical-prior-v1" in accepted.source_refs

    rejected = adapter.build_profile(
        Company(
            org_number="missing",
            name="Missing Employees",
            business_code="62.010",
            employee_count=None,
            source="registry",
        )
    )
    assert not rejected.accepted
    assert "employee_count_missing" in rejected.reasons


def test_live_pipeline_discovers_and_simulates_every_vertical():
    run = SpeiderValueScout([FakeAllVerticalConnector()]).run_all_verticals(
        min_employees=10,
        max_companies_per_vertical=1,
    )

    assert len(run.estimates) == 21
    assert len(run.profiles) == 21
    assert run.verticals_with_estimates == 21
    assert run.sources_consulted == ("fake-registry",)
    assert run.benchmark_basis == "assumption_only_until_shadow_calibrated"
    assert all(item.simulated == 1 for item in run.coverage.values())
    assert not run.rejected


def test_commissioning_seed_starts_motor_without_claiming_real_companies():
    profiles = build_all_vertical_seed_profiles()
    estimates = run_all_vertical_seed_simulation()

    assert len(profiles) == 21
    assert len(estimates) == 21
    assert {profile.organization_id for profile in profiles} == {
        f"SYNTH-{section}" for section in "ABCDEFGHIJKLMNOPQRSTU"
    }
    assert all(
        "synthetic:all-vertical-commissioning-v1" in estimate.source_refs
        for estimate in estimates
    )
    assert all(estimate.estimate_confidence < Decimal("0.05") for estimate in estimates)
