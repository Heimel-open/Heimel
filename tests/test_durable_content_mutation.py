from __future__ import annotations

import base64
import copy
import inspect
from dataclasses import replace
from datetime import datetime, timedelta, timezone

import pytest
import rfc8785
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from src.valo_platform.action_envelope.bounded_connector import (
    BoundedConnectorBoundary,
    DefiniteProviderFailure,
    SQLiteTokenConsumptionStore,
    TrustedCoreKey,
)
from src.valo_platform.action_envelope.durable_execution import DurableConnectorExecutor
from src.valo_platform.action_envelope.execution_journal import (
    ExecutionState,
    IdempotencyConflict,
    SQLiteExecutionJournal,
)
from src.valo_platform.action_envelope.reconciliation import (
    ProviderReconciliationService,
    ReconciliationError,
)
from src.valo_platform.connectors.content import (
    ClearedContentMutationConnector,
    ConditionalContentFixtureTransport,
    ContentMutationReconciliationAdapter,
    ContentMutationRequest,
    ContentMutationResult,
    DurableContentMutationExecutor,
)
from tests.content_operations.test_cleared_content_mutation_connector import (
    CLEARANCE_DIGEST,
    CONNECTOR_ID,
    CONTENT_SYSTEM,
    ReceiptSigner,
    digest,
    integrity_evidence,
    make_case,
    make_policy,
    make_transport,
    sha,
    signed_token,
)


class OutcomeSigner:
    issuer_id = "outcome:content-fixture:test"
    issuer_role = "OUTCOME_RECEIPT_ISSUER"
    key_id = "key:outcome:content-fixture:1"
    algorithm = "Ed25519"

    def __init__(self) -> None:
        self._key = Ed25519PrivateKey.generate()

    def sign(self, data: bytes) -> str:
        return base64.b64encode(self._key.sign(data)).decode("ascii")


class PostconditionMismatchTransport:
    """Apply exactly once, then report a mismatched target version."""

    def __init__(self, fixture: ConditionalContentFixtureTransport) -> None:
        self.fixture = fixture
        self.calls = 0

    def mutate_if_current(self, request: ContentMutationRequest) -> ContentMutationResult:
        self.calls += 1
        observed = self.fixture.mutate_if_current(request)
        return replace(observed, current_version_refs=("version:unexpected",))


def token_for(
    action_case,
    now: datetime,
    *,
    key: Ed25519PrivateKey,
    execution_id: str,
    token_id: str,
) -> dict:
    """Build the canonical test token with explicit durable identities."""

    token, _ = signed_token(action_case, now)
    token = copy.deepcopy(token)
    payload = token["payload"]
    payload["commit_token_id"] = token_id
    payload["execution_id"] = execution_id
    payload["reservation_id"] = "reservation:" + execution_id
    token["artifact_id"] = token_id
    token["payload_digest"] = digest(payload)
    token["signature"]["value"] = ""
    token["signature"]["value"] = base64.b64encode(
        key.sign(rfc8785.dumps(token))
    ).decode("ascii")
    return token


def runtime(
    tmp_path,
    *,
    key: Ed25519PrivateKey,
    provider_lookup: ConditionalContentFixtureTransport,
):
    journal = SQLiteExecutionJournal(tmp_path / "journal.db")
    boundary = BoundedConnectorBoundary(
        trusted_core_key=TrustedCoreKey(
            issuer_id="core:test",
            issuer_role="CORE_COMMIT_TOKEN_ISSUER",
            key_id="key:core:1",
            tenant_id="tenant-1",
            trust_domain="tenant-1:test",
            public_key=key.public_key(),
        ),
        consumption_store=SQLiteTokenConsumptionStore(tmp_path / "tokens.db"),
        receipt_signer=ReceiptSigner(),
        receipt_trust_domain="tenant-1:test",
    )
    cleared = ClearedContentMutationConnector(
        boundary=boundary,
        connector_id=CONNECTOR_ID,
        content_system=CONTENT_SYSTEM,
    )
    durable = DurableContentMutationExecutor(
        connector=cleared,
        durable_executor=DurableConnectorExecutor(
            journal=journal,
            boundary=boundary,
        ),
    )
    service = ProviderReconciliationService(
        journal=journal,
        provider_lookup=provider_lookup,
        outcome_signer=OutcomeSigner(),
        trust_domain="tenant-1:test",
    )
    reconciliation = ContentMutationReconciliationAdapter(
        journal=journal,
        reconciliation_service=service,
        connector_id=CONNECTOR_ID,
    )
    return journal, durable, reconciliation


def governance(action_case, policy, now: datetime):
    _, _, baseline, checkpoint = integrity_evidence(
        action_case=action_case,
        policy=policy,
        now=now,
    )
    return baseline, checkpoint


def reserve_indeterminate(
    journal: SQLiteExecutionJournal,
    action_case,
    *,
    execution_id: str,
    token_id: str,
) -> None:
    journal.reserve(
        execution_id=execution_id,
        tenant_id=action_case.content.tenant_id,
        idempotency_key=action_case.content.idempotency_key,
        request_digest=digest(
            {
                "connector_id": CONNECTOR_ID,
                "capability": action_case.content.operation.value,
                "target_digest": action_case.target_digest(),
                "payload_digest": action_case.digest(),
            }
        ),
        commit_token_id=token_id,
        commit_token_digest=sha("d"),
        connector_id=CONNECTOR_ID,
        capability=action_case.content.operation.value,
        target_digest=action_case.target_digest(),
        payload_digest=action_case.digest(),
    )
    journal.transition(
        execution_id,
        expected=ExecutionState.RESERVED,
        target=ExecutionState.STARTED,
    )
    journal.transition(
        execution_id,
        expected=ExecutionState.STARTED,
        target=ExecutionState.INDETERMINATE,
        provider_reference="unavailable",
        receipt_id="execution-receipt:" + execution_id,
        receipt_digest=sha("e"),
        error_class="IndeterminateProviderFailure",
    )


def reconcile(
    adapter: ContentMutationReconciliationAdapter,
    *,
    execution_id: str,
    action_case,
    baseline,
    outcome_id: str,
):
    return adapter.reconcile(
        execution_id=execution_id,
        action_case=action_case,
        integrity_baseline=baseline,
        outcome_receipt_id=outcome_id,
        observation_window={
            "from": "2026-07-31T20:00:00Z",
            "to": "2026-07-31T21:00:00Z",
        },
        attribution_score=1.0,
        confidence=0.99,
    )


def test_durable_success_and_exact_replay_do_not_duplicate_mutation(tmp_path) -> None:
    now = datetime.now(timezone.utc)
    key = Ed25519PrivateKey.generate()
    transport = make_transport()
    policy = make_policy(now)
    action_case = make_case(policy=policy, transport=transport)
    baseline, checkpoint = governance(action_case, policy, now)
    token = token_for(
        action_case,
        now,
        key=key,
        execution_id="execution-durable-1",
        token_id="token-durable-1",
    )
    journal, durable, _ = runtime(tmp_path, key=key, provider_lookup=transport)

    first = durable.execute(
        action_case=action_case,
        signed_commit_token=token,
        integrity_baseline=baseline,
        integrity_checkpoint=checkpoint,
        transport=transport,
        receipt_id="receipt-durable-1",
        now=now + timedelta(seconds=2),
    )
    replay = durable.execute(
        action_case=action_case,
        signed_commit_token=token,
        integrity_baseline=baseline,
        integrity_checkpoint=checkpoint,
        transport=transport,
        receipt_id="receipt-durable-replay",
        now=now + timedelta(seconds=3),
    )

    assert first.record.state is ExecutionState.SUCCEEDED
    assert first.record.execution_receipt_id == "receipt-durable-1"
    assert first.record.execution_receipt_digest
    assert first.replayed is False
    assert replay.record.state is ExecutionState.SUCCEEDED
    assert replay.connector_result is None
    assert replay.replayed is True
    assert transport.successful_mutations == 1
    assert len(transport.attempts) == 1
    assert journal.events("execution-durable-1")[-1]["to_state"] == "SUCCEEDED"


def test_same_content_idempotency_key_with_changed_request_fails(tmp_path) -> None:
    now = datetime.now(timezone.utc)
    key = Ed25519PrivateKey.generate()
    transport = make_transport()
    policy = make_policy(now)
    original = make_case(policy=policy, transport=transport)
    changed = make_case(
        policy=policy,
        transport=transport,
        case_id="case-durable-content-2",
        target_version_refs=("version:record-1:v3",),
        change_digest=sha("f"),
    )
    original_baseline, original_checkpoint = governance(original, policy, now)
    changed_baseline, changed_checkpoint = governance(changed, policy, now)
    original_token = token_for(
        original,
        now,
        key=key,
        execution_id="execution-idempotency-1",
        token_id="token-idempotency-1",
    )
    changed_token = token_for(
        changed,
        now,
        key=key,
        execution_id="execution-idempotency-2",
        token_id="token-idempotency-2",
    )
    _, durable, _ = runtime(tmp_path, key=key, provider_lookup=transport)

    durable.execute(
        action_case=original,
        signed_commit_token=original_token,
        integrity_baseline=original_baseline,
        integrity_checkpoint=original_checkpoint,
        transport=transport,
        receipt_id="receipt-idempotency-1",
        now=now + timedelta(seconds=2),
    )
    with pytest.raises(IdempotencyConflict, match="another request"):
        durable.execute(
            action_case=changed,
            signed_commit_token=changed_token,
            integrity_baseline=changed_baseline,
            integrity_checkpoint=changed_checkpoint,
            transport=transport,
            receipt_id="receipt-idempotency-2",
            now=now + timedelta(seconds=3),
        )

    assert transport.successful_mutations == 1
    assert len(transport.attempts) == 1


def test_indeterminate_replay_never_retries_and_reconciliation_confirms_success(
    tmp_path,
) -> None:
    now = datetime.now(timezone.utc)
    key = Ed25519PrivateKey.generate()
    fixture = make_transport()
    mismatched = PostconditionMismatchTransport(fixture)
    policy = make_policy(now)
    action_case = make_case(policy=policy, transport=fixture)
    baseline, checkpoint = governance(action_case, policy, now)
    token = token_for(
        action_case,
        now,
        key=key,
        execution_id="execution-indeterminate-1",
        token_id="token-indeterminate-1",
    )
    _, durable, adapter = runtime(tmp_path, key=key, provider_lookup=fixture)

    first = durable.execute(
        action_case=action_case,
        signed_commit_token=token,
        integrity_baseline=baseline,
        integrity_checkpoint=checkpoint,
        transport=mismatched,
        receipt_id="receipt-indeterminate-1",
        now=now + timedelta(seconds=2),
    )
    replay = durable.execute(
        action_case=action_case,
        signed_commit_token=token,
        integrity_baseline=baseline,
        integrity_checkpoint=checkpoint,
        transport=mismatched,
        receipt_id="receipt-indeterminate-replay",
        now=now + timedelta(seconds=3),
    )
    resolved = reconcile(
        adapter,
        execution_id="execution-indeterminate-1",
        action_case=action_case,
        baseline=baseline,
        outcome_id="outcome-indeterminate-1",
    )

    assert first.record.state is ExecutionState.INDETERMINATE
    assert first.connector_result is not None
    assert first.connector_result.receipt["payload"]["technical_outcome"] == "INDETERMINATE"
    assert replay.replayed is True
    assert replay.connector_result is None
    assert mismatched.calls == 1
    assert fixture.successful_mutations == 1
    assert resolved.record.state is ExecutionState.SUCCEEDED
    assert resolved.outcome_receipt is not None
    assert resolved.outcome_receipt["artifact_type"] == "OUTCOME_RECEIPT"
    assert resolved.outcome_receipt["payload"]["execution_receipt_id"] == (
        "receipt-indeterminate-1"
    )
    assert len(fixture.lookup_calls) == 1


def test_confirmed_no_effect_finalizes_failed_before_effect(tmp_path) -> None:
    now = datetime.now(timezone.utc)
    key = Ed25519PrivateKey.generate()
    transport = make_transport(version_ref="version:record-1:other")
    policy = make_policy(now)
    action_case = make_case(policy=policy, transport=transport)
    baseline, _ = governance(action_case, policy, now)
    request = ContentMutationRequest.from_action_case(
        execution_id="execution-no-effect-1",
        action_case=action_case,
    )
    with pytest.raises(DefiniteProviderFailure, match="source-version"):
        transport.mutate_if_current(request)
    journal, _, adapter = runtime(tmp_path, key=key, provider_lookup=transport)
    reserve_indeterminate(
        journal,
        action_case,
        execution_id="execution-no-effect-1",
        token_id="token-no-effect-1",
    )

    result = reconcile(
        adapter,
        execution_id="execution-no-effect-1",
        action_case=action_case,
        baseline=baseline,
        outcome_id="outcome-no-effect-1",
    )

    assert result.record.state is ExecutionState.FAILED_BEFORE_EFFECT
    assert result.outcome_receipt is not None
    assert result.observation.observed_effect["effect"] == "confirmed_absent"
    assert transport.successful_mutations == 0


def test_unknown_observation_remains_reconciliation_required(tmp_path) -> None:
    now = datetime.now(timezone.utc)
    key = Ed25519PrivateKey.generate()
    transport = make_transport()
    policy = make_policy(now)
    action_case = make_case(policy=policy, transport=transport)
    baseline, _ = governance(action_case, policy, now)
    journal, _, adapter = runtime(tmp_path, key=key, provider_lookup=transport)
    reserve_indeterminate(
        journal,
        action_case,
        execution_id="execution-unknown-1",
        token_id="token-unknown-1",
    )

    result = reconcile(
        adapter,
        execution_id="execution-unknown-1",
        action_case=action_case,
        baseline=baseline,
        outcome_id="outcome-unknown-1",
    )

    assert result.record.state is ExecutionState.RECONCILIATION_REQUIRED
    assert result.outcome_receipt is None
    assert len(transport.lookup_calls) == 1
    assert transport.successful_mutations == 0


def test_recovered_started_routes_to_reconciliation_without_provider_retry(tmp_path) -> None:
    now = datetime.now(timezone.utc)
    key = Ed25519PrivateKey.generate()
    transport = make_transport()
    policy = make_policy(now)
    action_case = make_case(policy=policy, transport=transport)
    journal, durable, _ = runtime(tmp_path, key=key, provider_lookup=transport)
    journal.reserve(
        execution_id="execution-recovered-1",
        tenant_id=action_case.content.tenant_id,
        idempotency_key=action_case.content.idempotency_key,
        request_digest=sha("1"),
        commit_token_id="token-recovered-1",
        commit_token_digest=sha("2"),
        connector_id=CONNECTOR_ID,
        capability=action_case.content.operation.value,
        target_digest=action_case.target_digest(),
        payload_digest=action_case.digest(),
    )
    journal.transition(
        "execution-recovered-1",
        expected=ExecutionState.RESERVED,
        target=ExecutionState.STARTED,
    )

    record = durable.require_reconciliation("execution-recovered-1")

    assert record.state is ExecutionState.RECONCILIATION_REQUIRED
    assert transport.attempts == []
    assert transport.lookup_calls == []
    assert [event["to_state"] for event in journal.events("execution-recovered-1")] == [
        "RESERVED",
        "STARTED",
        "INDETERMINATE",
        "RECONCILIATION_REQUIRED",
    ]


def test_reconciliation_action_or_baseline_mismatch_blocks_before_lookup(tmp_path) -> None:
    now = datetime.now(timezone.utc)
    key = Ed25519PrivateKey.generate()
    transport = make_transport()
    policy = make_policy(now)
    action_case = make_case(policy=policy, transport=transport)
    changed = make_case(
        policy=policy,
        transport=transport,
        case_id="case-durable-content-other",
        target_version_refs=("version:record-1:v3",),
        change_digest=sha("f"),
    )
    baseline, _ = governance(action_case, policy, now)
    journal, _, adapter = runtime(tmp_path, key=key, provider_lookup=transport)
    reserve_indeterminate(
        journal,
        action_case,
        execution_id="execution-binding-1",
        token_id="token-binding-1",
    )

    with pytest.raises(ReconciliationError, match="baseline"):
        reconcile(
            adapter,
            execution_id="execution-binding-1",
            action_case=changed,
            baseline=baseline,
            outcome_id="outcome-binding-1",
        )

    assert transport.lookup_calls == []


def test_reconciliation_surface_accepts_no_token_or_mutation_transport() -> None:
    parameters = inspect.signature(
        ContentMutationReconciliationAdapter.reconcile
    ).parameters

    assert "signed_commit_token" not in parameters
    assert "transport" not in parameters
    assert "mutation" not in parameters
