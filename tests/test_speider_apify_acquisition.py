"""Contract tests for governed Apify acquisition through Speider (issue #466)."""

from __future__ import annotations

from dataclasses import fields
from datetime import datetime, timedelta, timezone
from decimal import Decimal
import inspect
import socket

import pytest

from services.baro.connectors import BaroObservationService
from src.valo_platform.speider_acquisition import (
    AcquisitionConstraintError,
    AcquisitionEvent,
    AcquisitionProvider,
    AcquisitionProviderError,
    AcquisitionRequest,
    ApifyAcquisitionProvider,
    ApifyProviderConfig,
    ApifyProviderError,
    ActorLifecycleState,
    ActorRegistry,
    ActorRegistryEntry,
    CostEstimate,
    ProviderAcquisitionRequest,
    ProviderRunHandle,
    ProviderRunState,
    ProviderRunStatus,
    RawAcquisitionRecord,
    RegistryExecutionGrant,
    RetentionRule,
    RunFrequencyLimit,
    SpeiderAcquisitionService,
)


NOW = datetime(2026, 7, 13, 12, 0, tzinfo=timezone.utc)


class FakeApifyExecutor:
    """Network-free provider double with no Store discovery or decision API."""

    provider_name = "apify"

    def __init__(self, result: RawAcquisitionRecord) -> None:
        self.result = result
        self.calls: list[tuple[str, object]] = []
        self.handle = ProviderRunHandle(
            provider_name="apify",
            run_id=result.run_id,
            actor_id=result.actor_id,
            actor_version=result.actor_version,
            started_at=result.executed_at,
            dataset_ref=result.dataset_ref,
        )

    def validate_request(self, request):
        self.calls.append(("validate_request", request))

    def estimate_cost(self, request):
        self.calls.append(("estimate_cost", request))
        return CostEstimate(0.25, True, "test-hard-ceiling")

    def start_run(self, request):
        self.calls.append(("start_run", request))
        return self.handle

    def get_run_status(self, handle):
        self.calls.append(("get_run_status", handle))
        return ProviderRunStatus(
            handle=handle,
            state=ProviderRunState.SUCCEEDED,
            checked_at=(NOW + timedelta(seconds=2)).isoformat(),
            dataset_ref=self.result.dataset_ref,
            cost_metadata=self.result.cost_metadata,
            execution_metadata=self.result.execution_metadata,
        )

    def fetch_dataset(self, handle):
        self.calls.append(("fetch_dataset", handle))
        return self.result

    def cancel_run(self, handle):
        self.calls.append(("cancel_run", handle))


def actor_entry(**overrides) -> ActorRegistryEntry:
    data = {
        "registry_entry_id": "actor-reg-1",
        "actor_id": "apify/web-scraper",
        "human_readable_name": "Approved website scraper",
        "pinned_version": "1.2.3",
        "permitted_sources": ("example.com",),
        "allowed_input_schema": {
            "type": "object",
            "required": ["startUrls"],
            "properties": {
                "startUrls": {"type": "array"},
                "maxItems": {"type": "integer"},
            },
            "additionalProperties": False,
        },
        "expected_output_schema": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["source_url", "title"],
                "properties": {
                    "source_url": {"type": "string"},
                    "title": {"type": "string"},
                    "body": {"type": "string"},
                },
                "additionalProperties": False,
            },
        },
        "legal_constraints": ("public-content-only",),
        "contractual_constraints": ("respect-source-terms",),
        "run_frequency_limit": RunFrequencyLimit(max_runs=1, window_seconds=3600),
        "max_cost_usd": 2.0,
        "resource_limits": {"max_timeout_seconds": 120, "max_dataset_items": 100},
        "retention_rule": RetentionRule(max_days=30, deletion_required=True),
        "provenance_requirements": (
            "actor_id",
            "actor_version",
            "requester_id",
            "purpose",
            "source",
            "input_hash",
            "dataset_ref",
        ),
        "quality_metrics": {"minimum_source_coverage": 1.0},
        "failure_metrics": {"max_collection_errors": 0},
        "owner": "speider-platform",
        "approval_authority": "authority:collection-board",
        "review_date": (NOW + timedelta(days=30)).isoformat(),
        "permitted_tenant_ids": ("tenant-1",),
        "created_at": NOW.isoformat(),
        "updated_at": NOW.isoformat(),
    }
    data.update(overrides)
    return ActorRegistryEntry(**data)


def approved_registry(entry: ActorRegistryEntry | None = None) -> ActorRegistry:
    registry = ActorRegistry(clock=lambda: NOW)
    registry.register(entry or actor_entry())
    registry.transition(
        "actor-reg-1",
        ActorLifecycleState.REVIEW,
        changed_by="owner:alice",
        authority_ref="authority:collection-board",
        reason="technical and legal review requested",
    )
    registry.transition(
        "actor-reg-1",
        ActorLifecycleState.APPROVED,
        changed_by="approver:bob",
        authority_ref="authority:collection-board",
        reason="approved for bounded collection",
    )
    return registry


def acquisition_request(**overrides) -> AcquisitionRequest:
    data = {
        "request_id": "req-1",
        "registry_entry_ref": "actor-reg-1",
        "actor_id": "apify/web-scraper",
        "actor_version": "1.2.3",
        "requested_source": "https://news.example.com/article/1",
        "source_platform": "web",
        "actor_input": {
            "startUrls": [{"url": "https://news.example.com/article/1"}],
            "maxItems": 10,
        },
        "purpose": "collect public product-change evidence",
        "tenant_id": "tenant-1",
        "organizational_context": "competitive-monitoring",
        "requester_id": "user:alice",
        "authority_ref": "authority:collection-board",
        "cost_ceiling_usd": 1.0,
        "timeout_seconds": 60,
        "deadline_at": (NOW + timedelta(minutes=5)).isoformat(),
        "correlation_id": "corr-1",
        "requested_at": NOW.isoformat(),
    }
    data.update(overrides)
    return AcquisitionRequest(**data)


def authorized_provider_request(
    registry: ActorRegistry,
    request: AcquisitionRequest | None = None,
) -> ProviderAcquisitionRequest:
    acquisition = request or acquisition_request()
    entry, grant = registry.authorize_run(acquisition)
    return ProviderAcquisitionRequest(
        request_id=acquisition.request_id,
        registry_entry_ref=entry.registry_entry_id,
        actor_id=entry.actor_id,
        actor_version=entry.pinned_version,
        actor_input=acquisition.actor_input,
        requested_source=acquisition.requested_source,
        source_platform=acquisition.source_platform,
        tenant_id=acquisition.tenant_id,
        correlation_id=acquisition.correlation_id,
        timeout_seconds=acquisition.timeout_seconds,
        max_cost_usd=acquisition.cost_ceiling_usd,
        resource_limits={**entry.resource_limits, "memory_mbytes": 256},
        authorization_grant=grant,
    )


def typed_apify_run(**overrides):
    """Construct the exact response model returned by apify-client 3.0.6."""
    apify_models = pytest.importorskip("apify_client._models")
    data = {
        "id": "run-live-typed",
        "act_id": "apify/web-scraper",
        "user_id": "user-apify",
        "started_at": NOW + timedelta(seconds=1),
        "finished_at": NOW + timedelta(seconds=4),
        "status": "SUCCEEDED",
        "meta": {},
        "stats": {"computeUnits": 0.02},
        "charged_event_counts": {"actor-start": 1},
        "options": {},
        "build_id": "build-typed-1",
        "general_access": {},
        "default_key_value_store_id": "kv-typed-1",
        "default_dataset_id": "dataset-typed-1",
        "default_request_queue_id": "queue-typed-1",
        "build_number": "1.2.3",
        "usage_total_usd": 0.31,
        "usage_usd": {},
    }
    data.update(overrides)
    return apify_models.Run.model_construct(**data)


def actor_result(**overrides) -> RawAcquisitionRecord:
    data = {
        "actor_id": "apify/web-scraper",
        "actor_version": "1.2.3",
        "run_id": "run-123",
        "dataset_ref": "dataset:abc",
        "source_identifier": "https://news.example.com/article/1",
        "source_platform": "web",
        "retrieved_at": (NOW + timedelta(seconds=3)).isoformat(),
        "executed_at": (NOW + timedelta(seconds=1)).isoformat(),
        "payload": [
            {
                "source_url": "https://news.example.com/article/1",
                "title": "Product page changed",
                "body": "Public source content",
            }
        ],
        "cost_metadata": {"total_usd": 0.25, "compute_units": 0.02},
        "collection_errors": (),
    }
    data.update(overrides)
    return RawAcquisitionRecord(**data)


def test_registry_rejects_schema_keywords_the_validator_does_not_enforce():
    unsupported_schema = {
        "type": "object",
        "required": ["startUrls"],
        "properties": {
            "startUrls": {"type": "array", "maxItems": 1},
        },
        "additionalProperties": False,
    }
    registry = ActorRegistry(clock=lambda: NOW)
    registry.register(actor_entry(allowed_input_schema=unsupported_schema))
    registry.transition(
        "actor-reg-1",
        ActorLifecycleState.REVIEW,
        changed_by="owner:alice",
        authority_ref="authority:collection-board",
        reason="review",
    )

    with pytest.raises(AcquisitionConstraintError, match="input schema"):
        registry.transition(
            "actor-reg-1",
            ActorLifecycleState.APPROVED,
            changed_by="approver:bob",
            authority_ref="authority:collection-board",
            reason="unsupported schema must fail closed",
        )


def test_registry_lifecycle_preserves_history_and_authority_provenance():
    registry = approved_registry()

    entry = registry.get("actor-reg-1")
    history = registry.history("actor-reg-1")

    assert entry.lifecycle_state is ActorLifecycleState.APPROVED
    assert [item.to_state for item in history] == [
        ActorLifecycleState.REVIEW,
        ActorLifecycleState.APPROVED,
    ]
    assert history[-1].authority_ref == "authority:collection-board"
    assert history[-1].changed_by == "approver:bob"


@pytest.mark.parametrize(
    ("start", "target"),
    [
        (ActorLifecycleState.PROPOSED, ActorLifecycleState.APPROVED),
        (ActorLifecycleState.REVIEW, ActorLifecycleState.SUSPENDED),
        (ActorLifecycleState.REVOKED, ActorLifecycleState.APPROVED),
    ],
)
def test_invalid_lifecycle_transitions_fail_closed(start, target):
    registry = ActorRegistry(clock=lambda: NOW)
    registry.register(actor_entry())
    if start in {
        ActorLifecycleState.REVIEW,
        ActorLifecycleState.REVOKED,
    }:
        registry.transition(
            "actor-reg-1",
            ActorLifecycleState.REVIEW,
            changed_by="owner:alice",
            authority_ref="authority:collection-board",
            reason="review",
        )
    if start is ActorLifecycleState.REVOKED:
        registry.transition(
            "actor-reg-1",
            ActorLifecycleState.APPROVED,
            changed_by="approver:bob",
            authority_ref="authority:collection-board",
            reason="approve",
        )
        registry.transition(
            "actor-reg-1",
            ActorLifecycleState.REVOKED,
            changed_by="approver:bob",
            authority_ref="authority:collection-board",
            reason="revoke",
        )

    with pytest.raises(
        AcquisitionConstraintError, match="invalid lifecycle transition"
    ):
        registry.transition(
            "actor-reg-1",
            target,
            changed_by="user:any",
            authority_ref="authority:collection-board",
            reason="attempted invalid transition",
        )


@pytest.mark.parametrize(
    "target", [ActorLifecycleState.SUSPENDED, ActorLifecycleState.REVOKED]
)
def test_approved_actor_can_be_disabled_with_authority(target):
    registry = approved_registry()
    registry.transition(
        "actor-reg-1",
        target,
        changed_by="approver:bob",
        authority_ref="authority:collection-board",
        reason="collection authority withdrawn",
    )

    assert registry.get("actor-reg-1").lifecycle_state is target


def test_actor_cannot_be_approved_by_wrong_authority():
    registry = ActorRegistry(clock=lambda: NOW)
    registry.register(actor_entry())
    registry.transition(
        "actor-reg-1",
        ActorLifecycleState.REVIEW,
        changed_by="owner:alice",
        authority_ref="authority:collection-board",
        reason="review",
    )

    with pytest.raises(AcquisitionConstraintError, match="approval authority"):
        registry.transition(
            "actor-reg-1",
            ActorLifecycleState.APPROVED,
            changed_by="model:untrusted",
            authority_ref="authority:other",
            reason="self approval",
        )


def test_only_active_approved_pinned_actor_can_execute():
    registry = approved_registry()
    executor = FakeApifyExecutor(actor_result())
    service = SpeiderAcquisitionService(registry, executor, clock=lambda: NOW)

    event = service.acquire(acquisition_request())

    assert event.actor_id == "apify/web-scraper"
    assert event.actor_version == "1.2.3"
    assert [name for name, _ in executor.calls] == [
        "validate_request",
        "estimate_cost",
        "start_run",
        "get_run_status",
        "fetch_dataset",
    ]
    provider_request = executor.calls[0][1]
    assert isinstance(provider_request, ProviderAcquisitionRequest)
    assert provider_request.actor_id == "apify/web-scraper"
    assert provider_request.actor_version == "1.2.3"
    assert provider_request.registry_entry_ref == "actor-reg-1"
    assert not hasattr(executor, "discover_actors")


@pytest.mark.parametrize(
    ("request_changes", "message"),
    [
        ({"registry_entry_ref": "missing"}, "registry entry"),
        ({"actor_id": "apify/arbitrary-actor"}, "actor identifier"),
        ({"actor_version": "latest"}, "pinned version"),
        ({"requested_source": "https://evil.example.net/data"}, "permitted source"),
        ({"tenant_id": "tenant-2"}, "tenant scope"),
        ({"authority_ref": "authority:evil"}, "request authority"),
        ({"cost_ceiling_usd": 3.0}, "cost ceiling"),
        ({"cost_ceiling_usd": float("nan")}, "cost ceiling"),
        ({"timeout_seconds": 121}, "timeout"),
        ({"actor_input": {"unexpected": True}}, "input schema"),
        ({"deadline_at": (NOW - timedelta(seconds=1)).isoformat()}, "deadline"),
    ],
)
def test_request_constraints_fail_before_actor_execution(request_changes, message):
    executor = FakeApifyExecutor(actor_result())
    service = SpeiderAcquisitionService(
        approved_registry(), executor, clock=lambda: NOW
    )

    with pytest.raises(AcquisitionConstraintError, match=message):
        service.acquire(acquisition_request(**request_changes))

    assert executor.calls == []


def test_suspended_or_revoked_actor_cannot_execute():
    for target in (ActorLifecycleState.SUSPENDED, ActorLifecycleState.REVOKED):
        registry = approved_registry()
        registry.transition(
            "actor-reg-1",
            target,
            changed_by="approver:bob",
            authority_ref="authority:collection-board",
            reason="disabled",
        )
        executor = FakeApifyExecutor(actor_result())

        with pytest.raises(AcquisitionConstraintError, match="active approved"):
            SpeiderAcquisitionService(registry, executor, clock=lambda: NOW).acquire(
                acquisition_request()
            )
        assert executor.calls == []


def test_disallowed_source_embedded_in_actor_input_is_rejected():
    registry = approved_registry()
    provider = FakeApifyExecutor(actor_result())

    with pytest.raises(AcquisitionConstraintError, match="Actor input source"):
        SpeiderAcquisitionService(registry, provider, clock=lambda: NOW).acquire(
            acquisition_request(
                actor_input={"startUrls": [{"url": "https://evil.example.net/private"}]}
            )
        )

    assert provider.calls == []


def test_frequency_limit_is_enforced_per_actor_and_tenant():
    registry = approved_registry()
    executor = FakeApifyExecutor(actor_result())
    service = SpeiderAcquisitionService(registry, executor, clock=lambda: NOW)
    service.acquire(acquisition_request())

    with pytest.raises(AcquisitionConstraintError, match="frequency"):
        service.acquire(acquisition_request(request_id="req-2"))

    assert len(executor.calls) == 5


def test_nested_output_url_outside_scope_is_rejected_before_baro():
    output_schema = {
        "type": "array",
        "items": {
            "type": "object",
            "required": ["source_url", "title", "links"],
            "properties": {
                "source_url": {"type": "string"},
                "title": {"type": "string"},
                "links": {
                    "type": "object",
                    "required": ["detail_url"],
                    "properties": {"detail_url": {"type": "string"}},
                    "additionalProperties": False,
                },
            },
            "additionalProperties": False,
        },
    }
    registry = approved_registry(actor_entry(expected_output_schema=output_schema))
    provider = FakeApifyExecutor(
        actor_result(
            payload=[
                {
                    "source_url": "https://news.example.com/article/1",
                    "title": "Changed",
                    "links": {"detail_url": "https://evil.example.net/leak"},
                }
            ]
        )
    )
    forwarded = []

    with pytest.raises(AcquisitionConstraintError, match="output source"):
        SpeiderAcquisitionService(
            registry, provider, baro_sink=forwarded.append, clock=lambda: NOW
        ).acquire(acquisition_request())

    assert forwarded == []
    assert [name for name, _ in provider.calls][-1] == "cancel_run"


def test_output_schema_fails_closed_before_baro_forwarding():
    forwarded = []
    invalid = actor_result(payload=[{"title": "missing source"}])
    executor = FakeApifyExecutor(invalid)
    service = SpeiderAcquisitionService(
        approved_registry(), executor, baro_sink=forwarded.append, clock=lambda: NOW
    )

    with pytest.raises(AcquisitionConstraintError, match="output schema"):
        service.acquire(acquisition_request())

    assert forwarded == []


def test_normalization_preserves_nonempty_schema_valid_records_with_empty_title():
    output_schema = {
        "type": "array",
        "items": {
            "type": "object",
            "required": ["source_url", "title", "price"],
            "properties": {
                "source_url": {"type": "string"},
                "title": {"type": "string"},
                "price": {"type": "number"},
            },
            "additionalProperties": False,
        },
    }
    payload = [
        {
            "source_url": "https://news.example.com/article/1",
            "title": "",
            "price": 10,
        }
    ]
    registry = approved_registry(actor_entry(expected_output_schema=output_schema))
    event = SpeiderAcquisitionService(
        registry, FakeApifyExecutor(actor_result(payload=payload)), clock=lambda: NOW
    ).acquire(acquisition_request())

    assert event.normalized_payload == payload
    assert event.quality_indicators["retained_item_count"] == 1


def test_acquisition_event_reconstructs_execution_and_normalization_provenance():
    executor = FakeApifyExecutor(actor_result())
    event = SpeiderAcquisitionService(
        approved_registry(), executor, clock=lambda: NOW
    ).acquire(acquisition_request())

    assert event.request_id == "req-1"
    assert event.apify_run_id == "run-123"
    assert event.dataset_reference == "dataset:abc"
    assert event.content_hash == event.normalized_payload_hash
    assert event.raw_payload_hash
    assert event.request_input_hash
    assert event.normalization_changed is False
    assert {step.stage for step in event.provenance_chain} == {
        "request",
        "actor_execution",
        "normalization",
    }
    execution = next(
        step for step in event.provenance_chain if step.stage == "actor_execution"
    )
    assert execution.evidence["requester_id"] == "user:alice"
    assert execution.evidence["purpose"] == "collect public product-change evidence"
    assert execution.evidence["dataset_ref"] == "dataset:abc"
    assert event.cost_metadata["total_usd"] == 0.25


def test_event_contains_no_analysis_risk_admissibility_or_governance_decision_fields():
    forbidden = {
        "analysis",
        "risk",
        "risk_score",
        "admissibility",
        "decision",
        "authorized",
        "governance_decision",
        "governance_clearance",
    }
    assert forbidden.isdisjoint({field.name for field in fields(AcquisitionEvent)})
    assert forbidden.isdisjoint({field.name for field in fields(AcquisitionRequest)})


def test_speider_forwards_candidate_event_to_existing_baro_pipeline():
    baro = BaroObservationService()
    executor = FakeApifyExecutor(actor_result())
    service = SpeiderAcquisitionService(
        approved_registry(),
        executor,
        baro_sink=baro.ingest_acquisition_event,
        clock=lambda: NOW,
    )

    event = service.acquire(acquisition_request())
    observations = baro.get_observations(tenant_id="tenant-1", source_id="apify-web")
    signals = baro.normalize_observations(tenant_id="tenant-1")

    assert len(observations) == 1
    assert (
        observations[0].payload["acquisition_event"]["acquisition_id"]
        == event.acquisition_id
    )
    assert observations[0].payload["acquisition_event"]["provenance_chain"]
    candidate = observations[0].payload["candidate_signal"]
    assert candidate["source_reference"] == event.source_url_or_identifier
    assert candidate["acquisition_provenance"] == event.to_dict()["provenance_chain"]
    assert candidate["normalized_observation"] == event.normalized_payload
    assert candidate["collection_integrity_confidence"] == 1.0
    assert candidate["quality_indicators"] == event.quality_indicators
    assert candidate["timestamp"] == event.retrieval_timestamp
    assert candidate["actor_reference"] == {
        "registry_entry_ref": "actor-reg-1",
        "actor_id": "apify/web-scraper",
        "actor_version": "1.2.3",
        "provider": "apify",
        "run_id": "run-123",
    }
    assert candidate["fact_status"] == "uninterpreted_candidate"
    assert observations[0].confidence == 1.0
    assert len(signals) == 1
    assert signals[0].source_id == "apify-web"


def test_apify_provider_pins_build_and_enforces_provider_limits():
    class Page:
        items = [
            {"source_url": "https://news.example.com/article/1", "title": "Changed"}
        ]

    run_data = {
        "id": "run-live-1",
        "actId": "apify/web-scraper",
        "status": "SUCCEEDED",
        "buildNumber": "1.2.3",
        "buildId": "build-1",
        "defaultDatasetId": "dataset-live-1",
        "startedAt": "2026-07-13T12:00:01+00:00",
        "finishedAt": "2026-07-13T12:00:04+00:00",
        "usageTotalUsd": 0.31,
        "usageUsd": {"ACTOR_COMPUTE_UNITS": 0.2},
        "stats": {"computeUnits": 0.02},
    }

    class Actor:
        def __init__(self):
            self.start_kwargs = None

        def start(self, **kwargs):
            self.start_kwargs = kwargs
            return dict(run_data)

    class Run:
        def get(self, **kwargs):
            return dict(run_data)

        def abort(self, **kwargs):
            return {**run_data, "status": "ABORTED"}

    class Dataset:
        def list_items(self, **kwargs):
            assert kwargs == {"clean": True, "limit": 101}
            return Page()

    class Client:
        def __init__(self):
            self.actor_client = Actor()

        def actor(self, actor_id):
            assert actor_id == "apify/web-scraper"
            return self.actor_client

        def run(self, run_id):
            assert run_id == "run-live-1"
            return Run()

        def dataset(self, dataset_id):
            assert dataset_id == "dataset-live-1"
            return Dataset()

    registry = approved_registry()
    client = Client()
    provider = ApifyAcquisitionProvider(
        client,
        grant_verifier=registry.verify_execution_grant,
        clock=lambda: NOW,
    )
    request = authorized_provider_request(registry)

    provider.validate_request(request)
    estimate = provider.estimate_cost(request)
    handle = provider.start_run(request)
    status = provider.get_run_status(handle)
    result = provider.fetch_dataset(handle)

    call = client.actor_client.start_kwargs
    assert call is not None
    assert call["build"] == "1.2.3"
    assert str(call["max_total_charge_usd"]) == "1.0"
    assert call["max_items"] == 100
    assert call["memory_mbytes"] == 256
    assert int(call["run_timeout"].total_seconds()) == 60
    assert call["wait_for_finish"] == 0
    assert estimate.is_hard_ceiling is True
    assert status.state is ProviderRunState.SUCCEEDED
    assert result.actor_version == "1.2.3"
    assert result.dataset_ref == "dataset-live-1"
    assert result.cost_metadata["total_usd"] == 0.31
    assert result.raw_payload == Page.items


def test_installed_apify_client_accepts_provider_contract():
    from importlib.metadata import version

    apify_client = pytest.importorskip("apify_client")
    apify_models = pytest.importorskip("apify_client._models")

    assert version("apify-client") == "3.0.6"
    assert {
        "id",
        "act_id",
        "status",
        "build_id",
        "build_number",
        "default_dataset_id",
        "started_at",
        "finished_at",
        "usage_total_usd",
    } <= set(apify_models.Run.model_fields)

    start = apify_client.ApifyClient(token="not-used").actor("apify/web-scraper").start
    inspect.signature(start).bind(
        run_input={},
        build="1.2.3",
        max_items=10,
        max_total_charge_usd=Decimal("1.0"),
        restart_on_error=False,
        memory_mbytes=256,
        run_timeout=timedelta(seconds=30),
        wait_for_finish=0,
    )


def test_apify_provider_accepts_typed_sdk_run_for_start_get_and_abort():
    typed_running = typed_apify_run(
        status="RUNNING", finished_at=None, usage_total_usd=None
    )
    typed_succeeded = typed_apify_run()
    typed_aborted = typed_apify_run(status="ABORTED")

    class Actor:
        def start(self, **kwargs):
            return typed_running

    class RunClient:
        def get(self, **kwargs):
            return typed_succeeded

        def abort(self, **kwargs):
            return typed_aborted

    class Client:
        def actor(self, actor_id):
            return Actor()

        def run(self, run_id):
            return RunClient()

        def dataset(self, dataset_id):
            raise AssertionError("typed run contract test must not fetch data")

    registry = approved_registry()
    provider = ApifyAcquisitionProvider(
        Client(),
        grant_verifier=registry.verify_execution_grant,
        clock=lambda: NOW,
    )

    handle = provider.start_run(authorized_provider_request(registry))
    status = provider.get_run_status(handle)
    provider.cancel_run(handle)

    assert handle.run_id == "run-live-typed"
    assert handle.dataset_ref == "dataset-typed-1"
    assert status.state is ProviderRunState.SUCCEEDED
    assert status.cost_metadata["total_usd"] == 0.31


@pytest.mark.parametrize(
    ("response", "error"),
    [
        (lambda: typed_apify_run(id=None), "run identity"),
        (lambda: typed_apify_run(act_id=123), "registered Actor"),
        (lambda: typed_apify_run(build_number=None), "pinned build"),
        (lambda: typed_apify_run(started_at=None), "start timestamp"),
    ],
)
def test_typed_sdk_start_fails_closed_for_invalid_required_fields(response, error):
    class Actor:
        def start(self, **kwargs):
            return response()

    class RunClient:
        def get(self, **kwargs):
            raise AssertionError("invalid start must not poll")

        def abort(self, **kwargs):
            return typed_apify_run(status="ABORTED")

    class Client:
        def actor(self, actor_id):
            return Actor()

        def run(self, run_id):
            return RunClient()

        def dataset(self, dataset_id):
            raise AssertionError("invalid start must not fetch")

    registry = approved_registry()
    provider = ApifyAcquisitionProvider(
        Client(), grant_verifier=registry.verify_execution_grant, clock=lambda: NOW
    )

    with pytest.raises(ApifyProviderError, match=error):
        provider.start_run(authorized_provider_request(registry))


def test_typed_sdk_get_and_abort_fail_closed_for_invalid_required_fields():
    class Actor:
        def start(self, **kwargs):
            return typed_apify_run(status="RUNNING", finished_at=None)

    class RunClient:
        def get(self, **kwargs):
            return typed_apify_run(act_id=None)

        def abort(self, **kwargs):
            return typed_apify_run(id=None, status="ABORTED")

    class Client:
        def actor(self, actor_id):
            return Actor()

        def run(self, run_id):
            return RunClient()

        def dataset(self, dataset_id):
            raise AssertionError("invalid run response must not fetch")

    registry = approved_registry()
    provider = ApifyAcquisitionProvider(
        Client(), grant_verifier=registry.verify_execution_grant, clock=lambda: NOW
    )
    handle = provider.start_run(authorized_provider_request(registry))

    with pytest.raises(ApifyProviderError, match="registered Actor"):
        provider.get_run_status(handle)
    with pytest.raises(ApifyProviderError, match="cancellation identity"):
        provider.cancel_run(handle)


@pytest.mark.parametrize("provider_status", ["TIMING-OUT", "ABORTING"])
def test_apify_transitional_statuses_remain_pollable(provider_status):
    class Actor:
        def start(self, **kwargs):
            return typed_apify_run(status="RUNNING", finished_at=None)

    class RunClient:
        def get(self, **kwargs):
            return typed_apify_run(
                status=provider_status, finished_at=None, usage_total_usd=None
            )

        def abort(self, **kwargs):
            return typed_apify_run(status="ABORTING", finished_at=None)

    class Client:
        def actor(self, actor_id):
            return Actor()

        def run(self, run_id):
            return RunClient()

        def dataset(self, dataset_id):
            raise AssertionError("transitional status must not fetch data")

    registry = approved_registry()
    provider = ApifyAcquisitionProvider(
        Client(), grant_verifier=registry.verify_execution_grant, clock=lambda: NOW
    )
    handle = provider.start_run(authorized_provider_request(registry))

    status = provider.get_run_status(handle)
    provider.cancel_run(handle)

    assert status.state is ProviderRunState.RUNNING
    assert status.cost_metadata["cost_final"] is False


def test_apify_dataset_overflow_is_detected_instead_of_hidden_by_truncation():
    requested_limits = []

    class Page:
        items = [
            {
                "source_url": f"https://news.example.com/article/{index}",
                "title": f"Item {index}",
            }
            for index in range(101)
        ]

    class Actor:
        def start(self, **kwargs):
            return typed_apify_run(status="RUNNING", finished_at=None)

    class RunClient:
        def get(self, **kwargs):
            return typed_apify_run()

        def abort(self, **kwargs):
            return typed_apify_run(status="ABORTED")

    class Dataset:
        def list_items(self, **kwargs):
            requested_limits.append(kwargs["limit"])
            return Page()

    class Client:
        def actor(self, actor_id):
            return Actor()

        def run(self, run_id):
            return RunClient()

        def dataset(self, dataset_id):
            return Dataset()

    registry = approved_registry()
    provider = ApifyAcquisitionProvider(
        Client(), grant_verifier=registry.verify_execution_grant, clock=lambda: NOW
    )
    handle = provider.start_run(authorized_provider_request(registry))

    with pytest.raises(ApifyProviderError, match="dataset item limit"):
        provider.fetch_dataset(handle)
    assert requested_limits == [101]


def test_apify_pending_status_does_not_require_final_cost():
    responses = iter(
        (
            {
                "id": "run-live-1",
                "actId": "apify/web-scraper",
                "status": "RUNNING",
                "buildNumber": "1.2.3",
                "defaultDatasetId": "dataset-live-1",
            },
            {
                "id": "run-live-1",
                "actId": "apify/web-scraper",
                "status": "SUCCEEDED",
                "buildNumber": "1.2.3",
                "defaultDatasetId": "dataset-live-1",
                "usageTotalUsd": 0.2,
                "finishedAt": "2026-07-13T12:00:03+00:00",
            },
        )
    )

    class Actor:
        def start(self, **kwargs):
            return {
                "id": "run-live-1",
                "actId": "apify/web-scraper",
                "status": "RUNNING",
                "buildNumber": "1.2.3",
                "defaultDatasetId": "dataset-live-1",
                "startedAt": "2026-07-13T12:00:01+00:00",
            }

    class Run:
        def get(self, **kwargs):
            return next(responses)

        def abort(self, **kwargs):
            return {"id": "run-live-1", "status": "ABORTED"}

    class Client:
        def actor(self, actor_id):
            return Actor()

        def run(self, run_id):
            return Run()

        def dataset(self, dataset_id):
            raise AssertionError("status polling must not fetch the dataset")

    registry = approved_registry()
    provider = ApifyAcquisitionProvider(
        Client(),
        grant_verifier=registry.verify_execution_grant,
        clock=lambda: NOW,
    )
    handle = provider.start_run(authorized_provider_request(registry))

    pending = provider.get_run_status(handle)
    terminal = provider.get_run_status(handle)

    assert pending.state is ProviderRunState.RUNNING
    assert pending.cost_metadata["total_usd"] is None
    assert pending.cost_metadata["cost_final"] is False
    assert terminal.state is ProviderRunState.SUCCEEDED
    assert terminal.cost_metadata["total_usd"] == 0.2
    assert terminal.cost_metadata["cost_final"] is True


def test_apify_provider_rejects_wrong_build_before_status_or_dataset_access():
    aborted = []

    class Actor:
        def start(self, **kwargs):
            return {
                "id": "run-wrong",
                "actId": "apify/web-scraper",
                "status": "RUNNING",
                "buildNumber": "latest",
                "defaultDatasetId": "dataset-live-1",
                "startedAt": "2026-07-13T12:00:01+00:00",
            }

    class Run:
        def get(self, **kwargs):
            raise AssertionError("wrong build must fail before status access")

        def abort(self, **kwargs):
            aborted.append(kwargs)
            return {"id": "run-wrong", "status": "ABORTED"}

    class Client:
        def actor(self, actor_id):
            return Actor()

        def run(self, run_id):
            assert run_id == "run-wrong"
            return Run()

        def dataset(self, dataset_id):
            raise AssertionError("wrong build must fail before dataset access")

    registry = approved_registry()
    provider = ApifyAcquisitionProvider(
        Client(),
        grant_verifier=registry.verify_execution_grant,
        clock=lambda: NOW,
    )
    request = authorized_provider_request(registry)

    with pytest.raises(ApifyProviderError, match="pinned build"):
        provider.start_run(request)
    assert aborted == [{"gracefully": True}]


def test_post_run_cost_ceiling_is_enforced_before_baro_forwarding():
    forwarded = []
    expensive = actor_result(cost_metadata={"total_usd": 1.5})
    service = SpeiderAcquisitionService(
        approved_registry(),
        FakeApifyExecutor(expensive),
        baro_sink=forwarded.append,
        clock=lambda: NOW,
    )

    with pytest.raises(AcquisitionProviderError, match="cost"):
        service.acquire(acquisition_request(cost_ceiling_usd=1.0))
    assert forwarded == []


@pytest.mark.parametrize("invalid_cost", [float("nan"), float("inf"), float("-inf")])
def test_non_finite_provider_cost_fails_before_baro(invalid_cost):
    forwarded = []
    result = actor_result(cost_metadata={"total_usd": invalid_cost})
    service = SpeiderAcquisitionService(
        approved_registry(),
        FakeApifyExecutor(result),
        baro_sink=forwarded.append,
        clock=lambda: NOW,
    )

    with pytest.raises(AcquisitionProviderError, match="cost"):
        service.acquire(acquisition_request())
    assert forwarded == []


def test_platform_permission_requires_explicit_platform_prefix():
    registry = approved_registry(actor_entry(permitted_sources=("web",)))
    executor = FakeApifyExecutor(actor_result())
    service = SpeiderAcquisitionService(registry, executor, clock=lambda: NOW)

    with pytest.raises(AcquisitionConstraintError, match="permitted source"):
        service.acquire(acquisition_request())
    assert executor.calls == []


def test_suspended_actor_can_be_reapproved_but_revoked_actor_cannot():
    registry = approved_registry()
    registry.transition(
        "actor-reg-1",
        ActorLifecycleState.SUSPENDED,
        changed_by="approver:bob",
        authority_ref="authority:collection-board",
        reason="pause",
    )
    registry.transition(
        "actor-reg-1",
        ActorLifecycleState.APPROVED,
        changed_by="approver:bob",
        authority_ref="authority:collection-board",
        reason="reviewed and restored",
    )
    assert registry.get("actor-reg-1").lifecycle_state is ActorLifecycleState.APPROVED


def test_speider_preserves_schema_valid_records_with_empty_content_fields():
    result = actor_result(
        payload=[
            {"source_url": "https://news.example.com/empty", "title": "", "body": ""},
            {
                "source_url": "https://news.example.com/article/1",
                "title": "Candidate fact",
                "body": "public content",
            },
        ]
    )
    event = SpeiderAcquisitionService(
        approved_registry(), FakeApifyExecutor(result), clock=lambda: NOW
    ).acquire(acquisition_request())

    assert len(event.normalized_payload) == 2
    assert event.normalized_payload[0]["source_url"].endswith("/empty")
    assert event.normalized_payload[1]["title"] == "Candidate fact"
    assert event.normalization_changed is False
    assert event.quality_indicators["raw_item_count"] == 2
    assert event.quality_indicators["retained_item_count"] == 2


@pytest.mark.parametrize(
    ("entry_changes", "message"),
    [
        ({"allowed_input_schema": {"type": "magic"}}, "input schema"),
        ({"max_cost_usd": float("nan")}, "cost limit"),
        ({"resource_limits": {"max_timeout_seconds": 120}}, "dataset resource"),
        (
            {"retention_rule": RetentionRule(max_days=0, deletion_required=True)},
            "retention",
        ),
    ],
)
def test_unverifiable_registry_constraints_block_approval(entry_changes, message):
    registry = ActorRegistry(clock=lambda: NOW)
    registry.register(actor_entry(**entry_changes))
    registry.transition(
        "actor-reg-1",
        ActorLifecycleState.REVIEW,
        changed_by="owner:alice",
        authority_ref="authority:collection-board",
        reason="review",
    )

    with pytest.raises(AcquisitionConstraintError, match=message):
        registry.transition(
            "actor-reg-1",
            ActorLifecycleState.APPROVED,
            changed_by="approver:bob",
            authority_ref="authority:collection-board",
            reason="attempt approval",
        )


def test_registry_quality_threshold_is_collection_metric_not_baro_analysis():
    output_schema = {
        "type": "array",
        "items": {
            "type": "object",
            "required": ["title"],
            "properties": {"title": {"type": "string"}},
            "additionalProperties": False,
        },
    }
    registry = approved_registry(actor_entry(expected_output_schema=output_schema))
    result = actor_result(payload=[{"title": "candidate without item source"}])

    with pytest.raises(AcquisitionConstraintError, match="source quality threshold"):
        SpeiderAcquisitionService(
            registry, FakeApifyExecutor(result), clock=lambda: NOW
        ).acquire(acquisition_request())


def test_provider_contract_exposes_only_governed_collection_operations():
    required = {
        "validate_request",
        "start_run",
        "get_run_status",
        "fetch_dataset",
        "cancel_run",
        "estimate_cost",
    }
    forbidden = {
        "discover_actors",
        "list_actors",
        "search_store",
        "allow",
        "deny",
        "halt",
        "decide",
    }

    assert required <= set(AcquisitionProvider.__dict__)
    assert required <= set(ApifyAcquisitionProvider.__dict__)
    assert not (forbidden & set(AcquisitionProvider.__dict__))
    assert not (forbidden & set(ApifyAcquisitionProvider.__dict__))


def test_raw_acquisition_record_is_explicit_and_uninterpreted():
    record = actor_result()

    assert isinstance(record, RawAcquisitionRecord)
    assert record.raw_payload is record.payload
    assert record.provider_name == "apify"


def test_fabricated_registry_grant_cannot_start_apify_actor():
    class Client:
        def actor(self, actor_id):
            raise AssertionError("invalid grant must fail before Apify client access")

        def run(self, run_id):
            raise AssertionError("invalid grant must fail before Apify client access")

        def dataset(self, dataset_id):
            raise AssertionError("invalid grant must fail before Apify client access")

    registry = approved_registry()
    fake_grant = RegistryExecutionGrant(
        token="fabricated",
        request_id="req-1",
        registry_entry_ref="actor-reg-1",
        actor_id="apify/web-scraper",
        actor_version="1.2.3",
        source_identifier="https://news.example.com/article/1",
        tenant_id="tenant-1",
        expires_at=(NOW + timedelta(minutes=1)).isoformat(),
    )
    request = ProviderAcquisitionRequest(
        request_id="req-1",
        registry_entry_ref="actor-reg-1",
        actor_id="apify/web-scraper",
        actor_version="1.2.3",
        actor_input={"startUrls": []},
        requested_source="https://news.example.com/article/1",
        source_platform="web",
        tenant_id="tenant-1",
        correlation_id="corr-1",
        timeout_seconds=60,
        max_cost_usd=1.0,
        resource_limits={"max_dataset_items": 10},
        authorization_grant=fake_grant,
    )
    provider = ApifyAcquisitionProvider(
        Client(),
        grant_verifier=registry.verify_execution_grant,
        clock=lambda: NOW,
    )

    with pytest.raises(ApifyProviderError, match="grant"):
        provider.start_run(request)


def test_revocation_invalidates_unconsumed_provider_grant():
    class Client:
        def actor(self, actor_id):
            raise AssertionError("revoked grant must fail before Apify client access")

        def run(self, run_id):
            raise AssertionError("revoked grant must fail before Apify client access")

        def dataset(self, dataset_id):
            raise AssertionError("revoked grant must fail before Apify client access")

    registry = approved_registry()
    request = authorized_provider_request(registry)
    registry.transition(
        "actor-reg-1",
        ActorLifecycleState.REVOKED,
        changed_by="approver:bob",
        authority_ref="authority:collection-board",
        reason="source permission withdrawn",
    )
    provider = ApifyAcquisitionProvider(
        Client(),
        grant_verifier=registry.verify_execution_grant,
        clock=lambda: NOW,
    )

    with pytest.raises(ApifyProviderError, match="grant"):
        provider.validate_request(request)


def test_lifecycle_transition_permanently_invalidates_old_grant():
    registry = approved_registry()
    request = authorized_provider_request(registry)
    registry.transition(
        "actor-reg-1",
        ActorLifecycleState.SUSPENDED,
        changed_by="approver:bob",
        authority_ref="authority:collection-board",
        reason="temporary hold",
    )
    registry.transition(
        "actor-reg-1",
        ActorLifecycleState.APPROVED,
        changed_by="approver:bob",
        authority_ref="authority:collection-board",
        reason="new approval cycle",
    )

    assert registry.verify_execution_grant(request, False) is False


def test_substituted_provider_run_is_rejected_and_cancelled():
    class SubstitutingProvider(FakeApifyExecutor):
        def fetch_dataset(self, handle):
            self.calls.append(("fetch_dataset", handle))
            return actor_result(run_id="run-substituted")

    forwarded = []
    provider = SubstitutingProvider(actor_result())

    with pytest.raises(AcquisitionProviderError, match="identity"):
        SpeiderAcquisitionService(
            approved_registry(), provider, baro_sink=forwarded.append, clock=lambda: NOW
        ).acquire(acquisition_request())

    assert forwarded == []
    assert [name for name, _ in provider.calls][-1] == "cancel_run"


def test_provider_failure_cancels_run_and_never_forwards_to_baro():
    class FailingProvider(FakeApifyExecutor):
        def fetch_dataset(self, handle):
            self.calls.append(("fetch_dataset", handle))
            raise AcquisitionProviderError("dataset failed closed")

    forwarded = []
    provider = FailingProvider(actor_result())
    service = SpeiderAcquisitionService(
        approved_registry(), provider, baro_sink=forwarded.append, clock=lambda: NOW
    )

    with pytest.raises(AcquisitionProviderError, match="failed closed"):
        service.acquire(acquisition_request())

    assert forwarded == []
    assert [name for name, _ in provider.calls][-1] == "cancel_run"


def test_unverifiable_cost_estimate_fails_before_start():
    class ExpensiveProvider(FakeApifyExecutor):
        def estimate_cost(self, request):
            self.calls.append(("estimate_cost", request))
            return CostEstimate(1.01, True, "test-estimate")

    provider = ExpensiveProvider(actor_result())

    with pytest.raises(AcquisitionProviderError, match="hard ceiling"):
        SpeiderAcquisitionService(
            approved_registry(), provider, clock=lambda: NOW
        ).acquire(acquisition_request(cost_ceiling_usd=1.0))

    assert [name for name, _ in provider.calls] == [
        "validate_request",
        "estimate_cost",
    ]


def test_provider_timeout_cancels_run():
    class RunningProvider(FakeApifyExecutor):
        def get_run_status(self, handle):
            self.calls.append(("get_run_status", handle))
            return ProviderRunStatus(
                handle=handle,
                state=ProviderRunState.RUNNING,
                checked_at=NOW.isoformat(),
                dataset_ref=None,
                cost_metadata={"total_usd": 0.1},
            )

    ticks = iter((0.0, 61.0))
    provider = RunningProvider(actor_result())
    service = SpeiderAcquisitionService(
        approved_registry(),
        provider,
        clock=lambda: NOW,
        monotonic=lambda: next(ticks),
        sleeper=lambda _: None,
    )

    with pytest.raises(AcquisitionProviderError, match="timed out"):
        service.acquire(acquisition_request())

    assert [name for name, _ in provider.calls][-1] == "cancel_run"


def test_revocation_during_run_blocks_baro_handoff_and_cancels():
    registry = approved_registry()

    class RevokingProvider(FakeApifyExecutor):
        def get_run_status(self, handle):
            registry.transition(
                "actor-reg-1",
                ActorLifecycleState.REVOKED,
                changed_by="approver:bob",
                authority_ref="authority:collection-board",
                reason="emergency revocation",
            )
            return super().get_run_status(handle)

    forwarded = []
    provider = RevokingProvider(actor_result())

    with pytest.raises(AcquisitionConstraintError, match="approval changed"):
        SpeiderAcquisitionService(
            registry, provider, baro_sink=forwarded.append, clock=lambda: NOW
        ).acquire(acquisition_request())

    assert forwarded == []
    assert [name for name, _ in provider.calls][-1] == "cancel_run"


def test_unit_acquisition_path_never_opens_a_network_socket(monkeypatch):
    attempts = []

    def reject_network(*args, **kwargs):
        attempts.append((args, kwargs))
        raise AssertionError("unit tests must not open network sockets")

    monkeypatch.setattr(socket.socket, "connect", reject_network)
    event = SpeiderAcquisitionService(
        approved_registry(), FakeApifyExecutor(actor_result()), clock=lambda: NOW
    ).acquire(acquisition_request())

    assert event.provider_run_id == "run-123"
    assert attempts == []


def test_apify_configuration_comes_from_environment_and_redacts_token():
    config = ApifyProviderConfig.from_env(
        {
            "APIFY_API_TOKEN": "test-secret-not-a-live-token",
            "APIFY_API_URL": "https://apify.invalid",
            "APIFY_API_PUBLIC_URL": "https://public.apify.invalid",
            "SPEIDER_APIFY_POLL_INTERVAL_SECONDS": "0.5",
        }
    )

    assert config.api_url == "https://apify.invalid"
    assert config.poll_interval_seconds == 0.5
    assert "test-secret" not in repr(config)
    with pytest.raises(ApifyProviderError, match="APIFY_API_TOKEN"):
        ApifyProviderConfig.from_env({})


def test_collection_components_have_no_governance_decision_vocabulary():
    forbidden = {"ALLOW", "DENY", "HALT"}

    assert forbidden.isdisjoint({state.value for state in ProviderRunState})
    for component in (
        AcquisitionProvider,
        ApifyAcquisitionProvider,
        SpeiderAcquisitionService,
    ):
        public_names = {
            name.upper() for name in component.__dict__ if not name.startswith("_")
        }
        assert forbidden.isdisjoint(public_names)
