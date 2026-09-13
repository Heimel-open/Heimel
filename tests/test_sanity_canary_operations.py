from __future__ import annotations

import hashlib
import json
import sqlite3
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest
import rfc8785

from src.valo_platform.action_envelope.execution_journal import (
    ExecutionState,
    SQLiteExecutionJournal,
)
from src.valo_platform.action_envelope.reconciliation import ProviderResolution
from src.valo_platform.connectors.content import (
    PersistedSanityExecutionContext,
    ReconciliationWorkStatus,
    SanityCanaryActivation,
    SanityCanaryBundleLoader,
    SanityCanaryBundleVerificationError,
    SanityCanaryDeployment,
    SanityCanaryOperationsError,
    SanityCanaryOperationsRunner,
    SanityCanaryOperationsStateError,
    SanityCanaryReconciliationWorkItem,
    SanityCanaryReconciliationWorker,
    SanityCanarySignedBundle,
    SQLiteSanityCanaryOperationsStateStore,
    SQLiteSanityExecutionContextStore,
)
from tests.content_operations.test_sanity_deployment import (
    CONNECTOR_ID,
    DATASET_REF,
    DOCUMENT_ID,
    NOW,
    PROJECT_REF,
    SCHEMA_VERSION,
    SOURCE_REVISION,
    SecretResolver,
    activation,
    context,
    profile,
    sanity_case,
    sha,
)


class SignatureVerifier:
    key_id = "test-key-1"

    @staticmethod
    def sign(payload: bytes) -> str:
        return hashlib.sha256(b"sanity-canary-test-key:" + payload).hexdigest()

    def verify(self, *, key_id: str, payload: bytes, signature: str) -> bool:
        return key_id == self.key_id and signature == self.sign(payload)


class SecretProbe:
    def __init__(self, *, fail: bool = False) -> None:
        self.fail = fail
        self.calls = 0

    def probe(self) -> str:
        self.calls += 1
        if self.fail:
            raise RuntimeError("secret unavailable")
        return "sanity-secret-ref:test"


class FakeConnector:
    def __init__(self, *, fail: bool = False) -> None:
        self.fail = fail
        self.calls = 0

    def prepare(self, *, action_case, **kwargs):
        del kwargs
        self.calls += 1
        if self.fail:
            raise RuntimeError("prepare rejected")
        return SimpleNamespace(
            connector_id=CONNECTOR_ID,
            capability=action_case.content.operation.value,
            target_digest=action_case.target_digest(),
            payload_digest=action_case.digest(),
            idempotency_key=action_case.content.idempotency_key,
            mutation=lambda execution_id: execution_id,
        )


class DelegatingExecutor:
    def __init__(self) -> None:
        self.calls: list[dict] = []

    def execute(self, **kwargs):
        self.calls.append(kwargs)
        return {"delegated": True, "receipt_id": kwargs["receipt_id"]}


class FakeReconciliationAdapter:
    def __init__(self, journal: SQLiteExecutionJournal, *, unknown: bool) -> None:
        self.journal = journal
        self.unknown = unknown
        self.calls: list[dict] = []

    def reconcile(self, **kwargs):
        self.calls.append(kwargs)
        execution_id = kwargs["execution_id"]
        current = self.journal.get(execution_id)
        if current.state is ExecutionState.INDETERMINATE:
            current = self.journal.transition(
                execution_id,
                expected=ExecutionState.INDETERMINATE,
                target=ExecutionState.RECONCILIATION_REQUIRED,
            )
        if self.unknown:
            return SimpleNamespace(
                record=current,
                outcome_receipt=None,
                observation=SimpleNamespace(resolution=ProviderResolution.UNKNOWN),
            )
        final = self.journal.transition(
            execution_id,
            expected=ExecutionState.RECONCILIATION_REQUIRED,
            target=ExecutionState.SUCCEEDED,
        )
        return SimpleNamespace(
            record=final,
            outcome_receipt={"artifact_id": kwargs["outcome_receipt_id"]},
            observation=SimpleNamespace(
                resolution=ProviderResolution.CONFIRMED_SUCCEEDED
            ),
        )


def digest(value) -> str:
    return "sha256:" + hashlib.sha256(rfc8785.dumps(value)).hexdigest()


def signed_bundle(
    *,
    epoch: int = 1,
    live: bool = True,
    writes: bool = True,
    issued_at: datetime = NOW - timedelta(minutes=1),
    expires_at: datetime = NOW + timedelta(minutes=30),
    selected_profile=None,
    signature_override: str | None = None,
) -> SanityCanarySignedBundle:
    verifier = SignatureVerifier()
    deployment_profile = selected_profile or profile(expires_at=NOW + timedelta(hours=1))
    selected_activation = activation(
        deployment_profile,
        live=live,
        writes=writes,
    )
    payload = SanityCanarySignedBundle.payload_for(
        profile=deployment_profile,
        activation=selected_activation,
        activation_epoch=epoch,
        issued_at=issued_at,
        expires_at=expires_at,
        signer_id="operator:release-manager",
        key_id=verifier.key_id,
    )
    canonical = rfc8785.dumps(payload)
    return SanityCanarySignedBundle(
        **payload,
        signature=signature_override or verifier.sign(canonical),
        bundle_digest=digest(payload),
    )


def verified_bundle(**kwargs):
    bundle = signed_bundle(**kwargs)
    return SanityCanaryBundleLoader(SignatureVerifier()).load_bytes(
        bundle.model_dump_json().encode(),
        now=NOW,
    )


def token(execution_id: str = "exec-canary-ops-1") -> dict:
    return {"payload": {"execution_id": execution_id}}


def make_runner(
    tmp_path,
    *,
    live: bool = True,
    writes: bool = True,
    epoch: int = 1,
    secret_probe: SecretProbe | None = None,
):
    selected = verified_bundle(epoch=epoch, live=live, writes=writes)
    context_store = SQLiteSanityExecutionContextStore(tmp_path / "context.db")
    deployment = SanityCanaryDeployment(
        profile=selected.bundle.profile,
        activation=selected.bundle.activation,
        secret_resolver=SecretResolver(),
        context_store=context_store,
    )
    operations_store = SQLiteSanityCanaryOperationsStateStore(
        tmp_path / "operations.db"
    )
    connector = FakeConnector()
    durable = DelegatingExecutor()
    journal = SQLiteExecutionJournal(tmp_path / "journal.db")
    probe = secret_probe or SecretProbe()
    runner = SanityCanaryOperationsRunner(
        verified_bundle=selected,
        deployment=deployment,
        operations_store=operations_store,
        connector=connector,
        durable_executor=durable,  # type: ignore[arg-type]
        journal=journal,
        context_store=context_store,
        secret_probe=probe,
    )
    runner.register_activation(actor_ref="operator:release-manager", now=NOW)
    return runner, connector, durable, journal, context_store, operations_store, probe


def reserve_record(
    journal: SQLiteExecutionJournal,
    *,
    execution_id: str,
    state: ExecutionState,
    with_receipt: bool = True,
) -> None:
    journal.reserve(
        execution_id=execution_id,
        tenant_id="tenant-1",
        idempotency_key="idem:" + execution_id,
        request_digest=sha("1"),
        commit_token_id="token:" + execution_id,
        commit_token_digest=sha("2"),
        connector_id=CONNECTOR_ID,
        capability="content.update_field",
        target_digest=sha("3"),
        payload_digest=sha("4"),
        now=NOW,
    )
    if state is ExecutionState.RESERVED:
        return
    journal.transition(
        execution_id,
        expected=ExecutionState.RESERVED,
        target=ExecutionState.STARTED,
        now=NOW,
    )
    if state is ExecutionState.STARTED:
        return
    if state is ExecutionState.INDETERMINATE:
        journal.transition(
            execution_id,
            expected=ExecutionState.STARTED,
            target=ExecutionState.INDETERMINATE,
            provider_reference="unavailable",
            receipt_id="receipt:" + execution_id if with_receipt else None,
            receipt_digest=sha("5") if with_receipt else None,
            now=NOW,
        )
        return
    if state is ExecutionState.SUCCEEDED:
        journal.transition(
            execution_id,
            expected=ExecutionState.STARTED,
            target=ExecutionState.SUCCEEDED,
            provider_reference="sanity:transaction:" + execution_id,
            receipt_id="receipt:" + execution_id,
            receipt_digest=sha("5"),
            now=NOW,
        )
        return
    raise AssertionError(state)


def test_signed_bundle_loads_only_with_valid_signature_and_time() -> None:
    selected = verified_bundle()

    assert selected.bundle.profile.profile_id == "sanity-canary-profile-1"
    assert selected.bundle.activation_epoch == 1
    assert selected.verification_ref.startswith("sanity-canary-signature:")


@pytest.mark.parametrize("mutation", ["signature", "profile", "activation"])
def test_changed_or_unsigned_bundle_fails_closed(mutation: str) -> None:
    bundle = signed_bundle()
    raw = json.loads(bundle.model_dump_json())
    if mutation == "signature":
        raw["signature"] = "invalid-signature"
    elif mutation == "profile":
        raw["profile"]["dataset_ref"] = "dataset:attacker"
    else:
        raw["activation"]["profile_digest"] = sha("f")

    with pytest.raises(SanityCanaryBundleVerificationError):
        SanityCanaryBundleLoader(SignatureVerifier()).load_bytes(
            json.dumps(raw).encode(),
            now=NOW,
        )


def test_expired_or_future_signed_bundle_fails_closed() -> None:
    expired = signed_bundle(
        issued_at=NOW - timedelta(hours=1),
        expires_at=NOW,
    )
    future = signed_bundle(
        issued_at=NOW + timedelta(minutes=1),
        expires_at=NOW + timedelta(minutes=20),
    )
    loader = SanityCanaryBundleLoader(SignatureVerifier())

    with pytest.raises(SanityCanaryBundleVerificationError, match="currently valid"):
        loader.load_bytes(expired.model_dump_json().encode(), now=NOW)
    with pytest.raises(SanityCanaryBundleVerificationError, match="currently valid"):
        loader.load_bytes(future.model_dump_json().encode(), now=NOW)


def test_halt_is_durable_and_resume_requires_new_signed_epoch(tmp_path) -> None:
    store = SQLiteSanityCanaryOperationsStateStore(tmp_path / "operations.db")
    first = verified_bundle(epoch=1)
    store.activate(first, actor_ref="operator:a", now=NOW)
    halted = store.halt(
        profile_id=first.bundle.profile.profile_id,
        expected_profile_digest=first.bundle.profile.digest(),
        actor_ref="operator:a",
        reason="incident",
        now=NOW + timedelta(minutes=1),
    )

    assert halted.halted is True
    restarted = SQLiteSanityCanaryOperationsStateStore(tmp_path / "operations.db")
    assert restarted.get(first.bundle.profile.profile_id).halted is True
    with pytest.raises(SanityCanaryOperationsStateError, match="newer"):
        restarted.activate(first, actor_ref="operator:b", now=NOW + timedelta(minutes=2))

    second = verified_bundle(epoch=2)
    resumed = restarted.activate(
        second,
        actor_ref="operator:b",
        now=NOW + timedelta(minutes=2),
    )
    assert resumed.halted is False
    assert resumed.activation_epoch == 2
    assert [event["event_type"] for event in restarted.events(resumed.profile_id)] == [
        "ACTIVATED",
        "HALTED",
        "RESUMED",
    ]


def test_default_preflight_denies_without_secret_provider_or_durable_call(tmp_path) -> None:
    runner, connector, durable, journal, context_store, _, probe = make_runner(
        tmp_path,
        live=False,
        writes=False,
    )

    result = runner.preflight(
        action_case=sanity_case(),
        signed_commit_token=token(),
        integrity_baseline=object(),
        integrity_checkpoint=object(),
        transport=object(),  # type: ignore[arg-type]
        actor_ref="operator:a",
        now=NOW,
    )

    assert result.permitted is False
    assert connector.calls == 1
    assert durable.calls == []
    assert probe.calls == 0
    assert context_store.count() == 0
    with pytest.raises(Exception):
        journal.get("exec-canary-ops-1")


def test_ready_preflight_has_zero_provider_effect_and_zero_context_registration(tmp_path) -> None:
    runner, _, durable, journal, context_store, state_store, probe = make_runner(tmp_path)

    result = runner.preflight(
        action_case=sanity_case(),
        signed_commit_token=token(),
        integrity_baseline=object(),
        integrity_checkpoint=object(),
        transport=object(),  # type: ignore[arg-type]
        actor_ref="operator:a",
        now=NOW,
    )

    assert result.permitted is True
    assert result.secret_available is True
    assert result.context_store_ready is True
    assert probe.calls == 1
    assert durable.calls == []
    assert context_store.count() == 0
    assert state_store.get("sanity-canary-profile-1").last_preflight_ref == result.reference
    with pytest.raises(Exception):
        journal.get("exec-canary-ops-1")


def test_execute_delegates_only_to_existing_durable_canary_executor(tmp_path) -> None:
    runner, _, durable, _, _, _, _ = make_runner(tmp_path)
    action_case = sanity_case()
    signed_token = token()
    preflight = runner.preflight(
        action_case=action_case,
        signed_commit_token=signed_token,
        integrity_baseline=object(),
        integrity_checkpoint=object(),
        transport=object(),  # type: ignore[arg-type]
        actor_ref="operator:a",
        now=NOW,
    )

    result = runner.execute(
        preflight=preflight,
        action_case=action_case,
        signed_commit_token=signed_token,
        integrity_baseline=object(),
        integrity_checkpoint=object(),
        transport=object(),  # type: ignore[arg-type]
        receipt_id="receipt-canary-1",
        now=NOW,
    )

    assert result == {"delegated": True, "receipt_id": "receipt-canary-1"}
    assert len(durable.calls) == 1


def test_halt_blocks_preflight_and_previously_ready_execute(tmp_path) -> None:
    runner, _, durable, _, _, _, probe = make_runner(tmp_path)
    action_case = sanity_case()
    signed_token = token()
    preflight = runner.preflight(
        action_case=action_case,
        signed_commit_token=signed_token,
        integrity_baseline=object(),
        integrity_checkpoint=object(),
        transport=object(),  # type: ignore[arg-type]
        actor_ref="operator:a",
        now=NOW,
    )
    runner.halt(actor_ref="operator:a", reason="manual stop", now=NOW)

    denied = runner.preflight(
        action_case=action_case,
        signed_commit_token=signed_token,
        integrity_baseline=object(),
        integrity_checkpoint=object(),
        transport=object(),  # type: ignore[arg-type]
        actor_ref="operator:a",
        now=NOW,
    )
    assert denied.permitted is False
    assert probe.calls == 1
    with pytest.raises(SanityCanaryOperationsStateError, match="halted"):
        runner.execute(
            preflight=preflight,
            action_case=action_case,
            signed_commit_token=signed_token,
            integrity_baseline=object(),
            integrity_checkpoint=object(),
            transport=object(),  # type: ignore[arg-type]
            receipt_id="receipt-blocked",
            now=NOW,
        )
    assert durable.calls == []


def test_runner_resume_requires_new_epoch(tmp_path) -> None:
    runner, _, _, _, _, _, _ = make_runner(tmp_path)
    runner.halt(actor_ref="operator:a", reason="manual stop", now=NOW)

    with pytest.raises(SanityCanaryOperationsStateError, match="newer"):
        runner.resume(
            runner.verified_bundle,
            actor_ref="operator:b",
            now=NOW + timedelta(minutes=1),
        )

    resumed = runner.resume(
        verified_bundle(epoch=2),
        actor_ref="operator:b",
        now=NOW + timedelta(minutes=1),
    )
    assert resumed.activation_epoch == 2
    assert resumed.halted is False


def test_status_reads_journal_and_context_without_mutation(tmp_path) -> None:
    runner, _, _, journal, context_store, _, _ = make_runner(tmp_path)
    execution_id = "exec-status-1"
    reserve_record(journal, execution_id=execution_id, state=ExecutionState.SUCCEEDED)
    context_store.register(
        context(execution_id=execution_id, registered_at=NOW)
    )
    before_events = journal.events(execution_id)

    status = runner.status(execution_id, now=NOW)

    assert status.execution_state is ExecutionState.SUCCEEDED
    assert status.context_digest is not None
    assert status.document_ids == (DOCUMENT_ID,)
    assert journal.events(execution_id) == before_events


def test_reconciliation_worker_processes_explicit_unknown_once_without_token(tmp_path) -> None:
    journal = SQLiteExecutionJournal(tmp_path / "journal.db")
    execution_id = "exec-reconcile-1"
    reserve_record(journal, execution_id=execution_id, state=ExecutionState.INDETERMINATE)
    adapter = FakeReconciliationAdapter(journal, unknown=True)
    worker = SanityCanaryReconciliationWorker(
        journal=journal,
        adapter=adapter,  # type: ignore[arg-type]
    )
    item = SanityCanaryReconciliationWorkItem(
        execution_id=execution_id,
        action_case=sanity_case(),
        integrity_baseline=object(),
        outcome_receipt_id="outcome-1",
        observation_window={"from": "a", "to": "b"},
        attribution_score=1.0,
        confidence=1.0,
    )

    results = worker.run_once((item,))

    assert len(adapter.calls) == 1
    assert "signed_commit_token" not in adapter.calls[0]
    assert "transport" not in adapter.calls[0]
    assert results[0].status is ReconciliationWorkStatus.STILL_UNKNOWN
    assert journal.get(execution_id).state is ExecutionState.RECONCILIATION_REQUIRED


def test_reconciliation_worker_skips_terminal_records(tmp_path) -> None:
    journal = SQLiteExecutionJournal(tmp_path / "journal.db")
    execution_id = "exec-terminal-1"
    reserve_record(journal, execution_id=execution_id, state=ExecutionState.SUCCEEDED)
    adapter = FakeReconciliationAdapter(journal, unknown=False)
    worker = SanityCanaryReconciliationWorker(
        journal=journal,
        adapter=adapter,  # type: ignore[arg-type]
    )
    item = SanityCanaryReconciliationWorkItem(
        execution_id=execution_id,
        action_case=sanity_case(),
        integrity_baseline=object(),
        outcome_receipt_id="outcome-1",
        observation_window={"from": "a", "to": "b"},
        attribution_score=1.0,
        confidence=1.0,
    )

    result = worker.run_once((item,))[0]

    assert result.status is ReconciliationWorkStatus.SKIPPED
    assert adapter.calls == []


def test_rollback_plan_is_reference_only_and_cannot_execute(tmp_path) -> None:
    runner, _, _, journal, context_store, _, _ = make_runner(tmp_path)
    execution_id = "exec-rollback-1"
    reserve_record(journal, execution_id=execution_id, state=ExecutionState.SUCCEEDED)
    context_store.register(context(execution_id=execution_id, registered_at=NOW))

    plan = runner.rollback_plan(
        execution_id=execution_id,
        expected_current_revisions=("rev-current-2",),
        rollback_change_ref="change:rollback:product-1:v1",
        rollback_change_digest=sha("9"),
        requested_by="operator:a",
        now=NOW,
    )

    assert plan.requires_new_action_case is True
    assert plan.requires_new_clearance is True
    assert plan.automatic_execution is False
    assert not hasattr(plan, "execute")
    serialized = plan.model_dump_json()
    assert "New title" not in serialized
    assert "commit_token" not in serialized.lower()
    assert "sanity-live-token" not in serialized


def test_operations_database_contains_no_secret_token_or_raw_content(tmp_path) -> None:
    runner, _, _, _, _, operations_store, _ = make_runner(tmp_path)
    runner.preflight(
        action_case=sanity_case(),
        signed_commit_token=token(),
        integrity_baseline=object(),
        integrity_checkpoint=object(),
        transport=object(),  # type: ignore[arg-type]
        actor_ref="operator:a",
        now=NOW,
    )

    raw = (tmp_path / "operations.db").read_bytes()
    assert b"sanity-live-token-value" not in raw
    assert b"New title" not in raw
    assert b"commit_token" not in raw
    assert b"secret://sanity" not in raw
    assert operations_store.get("sanity-canary-profile-1").state_digest.startswith(
        "sha256:"
    )


def test_tampered_operations_state_fails_closed(tmp_path) -> None:
    runner, _, _, _, _, operations_store, _ = make_runner(tmp_path)
    with sqlite3.connect(tmp_path / "operations.db") as connection:
        connection.execute(
            """
            UPDATE sanity_canary_operations_state
            SET activation_epoch=999 WHERE profile_id=?
            """,
            ("sanity-canary-profile-1",),
        )

    with pytest.raises(SanityCanaryOperationsStateError, match="tampered"):
        operations_store.get("sanity-canary-profile-1")


def test_runner_rejects_deployment_from_another_verified_profile(tmp_path) -> None:
    first = verified_bundle()
    other_profile = profile(dataset_ref="dataset:other")
    other = verified_bundle(selected_profile=other_profile)
    context_store = SQLiteSanityExecutionContextStore(tmp_path / "context.db")
    deployment = SanityCanaryDeployment(
        profile=other.bundle.profile,
        activation=other.bundle.activation,
        secret_resolver=SecretResolver(),
        context_store=context_store,
    )

    with pytest.raises(SanityCanaryOperationsError, match="profile"):
        SanityCanaryOperationsRunner(
            verified_bundle=first,
            deployment=deployment,
            operations_store=SQLiteSanityCanaryOperationsStateStore(
                tmp_path / "operations.db"
            ),
            connector=FakeConnector(),
            durable_executor=DelegatingExecutor(),  # type: ignore[arg-type]
            journal=SQLiteExecutionJournal(tmp_path / "journal.db"),
            context_store=context_store,
            secret_probe=SecretProbe(),
        )
