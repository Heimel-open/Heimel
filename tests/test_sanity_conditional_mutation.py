from __future__ import annotations

import hashlib
from datetime import datetime, timezone

import pytest
import rfc8785
from pydantic import ValidationError

from src.valo_platform.action_envelope.bounded_connector import (
    ConnectorExecutionResult,
    DefiniteProviderFailure,
    IndeterminateProviderFailure,
    ProviderResult,
)
from src.valo_platform.action_envelope.durable_execution import DurableConnectorExecutor
from src.valo_platform.action_envelope.execution_journal import (
    ExecutionState,
    SQLiteExecutionJournal,
)
from src.valo_platform.action_envelope.reconciliation import (
    ProviderObservation,
    ProviderReconciliationService,
    ProviderResolution,
    ReconciliationError,
)
from src.valo_platform.connectors.content import (
    ClearedContentMutationConnector,
    ContentMutationReconciliationAdapter,
    ContentMutationRequest,
    SanityConditionalMutationTransport,
    SanityDefiniteNoEffectError,
    SanityDocumentPatch,
    SanityMutationResponse,
    SanityMutationTransaction,
    SanityPatchArtifact,
    SanityPatchInstruction,
    SanityPatchVerb,
    SanitySchemaSnapshot,
    SanityTransactionEvidence,
    SanityTransactionStatus,
    SanityUnknownEffectError,
)
from src.valo_platform.content_operations import ContentOperation


def digest(value: object) -> str:
    return "sha256:" + hashlib.sha256(rfc8785.dumps(value)).hexdigest()


def sha(char: str) -> str:
    return "sha256:" + char * 64


class ArtifactResolver:
    def __init__(self, artifact: SanityPatchArtifact) -> None:
        self.artifact = artifact
        self.calls: list[str] = []

    def resolve(self, change_ref: str) -> SanityPatchArtifact:
        self.calls.append(change_ref)
        if change_ref != self.artifact.change_ref:
            raise KeyError(change_ref)
        return self.artifact


class ValueResolver:
    def __init__(self) -> None:
        self.values = {
            "value:title": "New title",
            "value:one": 1,
        }
        self.calls: list[str] = []

    def resolve(self, value_ref: str):
        self.calls.append(value_ref)
        return self.values[value_ref]


class Client:
    def __init__(
        self,
        *,
        response: SanityMutationResponse | None = None,
        evidence: SanityTransactionEvidence | None = None,
        mutation_error: Exception | None = None,
    ) -> None:
        self.response = response
        self.evidence = evidence
        self.mutation_error = mutation_error
        self.mutation_calls: list[SanityMutationTransaction] = []
        self.lookup_calls: list[tuple[str, str, str]] = []

    def mutate(self, transaction: SanityMutationTransaction) -> SanityMutationResponse:
        self.mutation_calls.append(transaction)
        if self.mutation_error is not None:
            raise self.mutation_error
        assert self.response is not None
        return self.response

    def lookup_transaction(
        self,
        *,
        project_ref: str,
        dataset_ref: str,
        transaction_id: str,
    ) -> SanityTransactionEvidence | None:
        self.lookup_calls.append((project_ref, dataset_ref, transaction_id))
        return self.evidence


class Boundary:
    def __init__(self) -> None:
        self.calls = 0

    def execute(
        self,
        *,
        signed_commit_token,
        connector_id,
        capability,
        target_digest,
        payload_digest,
        mutation,
        receipt_id,
        now,
    ) -> ConnectorExecutionResult:
        del connector_id, capability, target_digest, payload_digest, now
        self.calls += 1
        execution_id = signed_commit_token["payload"]["execution_id"]
        provider = mutation(execution_id)
        return ConnectorExecutionResult(
            receipt={
                "artifact_id": receipt_id,
                "payload": {
                    "technical_outcome": "SUCCEEDED",
                    "provider_reference": provider.provider_reference,
                },
            },
            provider_result=provider,
        )


class Signer:
    issuer_id = "outcome:test"
    issuer_role = "OUTCOME_RECEIPT_ISSUER"
    key_id = "key:test"
    algorithm = "test"

    def sign(self, data: bytes) -> str:
        return digest(data.decode("latin1"))


class Lookup:
    def __init__(self, observation: ProviderObservation) -> None:
        self.observation = observation

    def lookup(self, **kwargs) -> ProviderObservation:
        del kwargs
        return self.observation


def schema() -> SanitySchemaSnapshot:
    return SanitySchemaSnapshot(
        project_ref="project:products",
        dataset_ref="dataset:test",
        schema_version="schema-v1",
        schema_digest=sha("a"),
        document_types=("product",),
        schema_refs=("schema:product:v1",),
    )


def artifact(
    *,
    source_revision: str = "rev-source-1",
    snapshot_digest: str = sha("1"),
) -> SanityPatchArtifact:
    return SanityPatchArtifact(
        change_ref="change:product-1:v2",
        content_snapshot_digest=snapshot_digest,
        documents=(
            SanityDocumentPatch(
                document_id="product-1",
                source_revision=source_revision,
                instructions=(
                    SanityPatchInstruction(
                        verb=SanityPatchVerb.SET,
                        path="title",
                        value_ref="value:title",
                        value_digest=digest("New title"),
                    ),
                    SanityPatchInstruction(
                        verb=SanityPatchVerb.INC,
                        path="views",
                        value_ref="value:one",
                        value_digest=digest(1),
                    ),
                    SanityPatchInstruction(
                        verb=SanityPatchVerb.UNSET,
                        path="legacyField",
                    ),
                ),
            ),
        ),
    )


def request(
    patch: SanityPatchArtifact,
    *,
    source_revision: str = "rev-source-1",
    target_revisions: tuple[str, ...] = (),
    proposed_change_digest: str | None = None,
) -> ContentMutationRequest:
    return ContentMutationRequest(
        execution_id="exec-sanity-1",
        action_id="case-sanity-1",
        tenant_id="tenant-1",
        content_system="sanity",
        workspace_ref="workspace:catalogue",
        project_ref="project:products",
        dataset_ref="dataset:test",
        operation=ContentOperation.UPDATE_FIELD,
        record_ids=("product-1",),
        schema_version="schema-v1",
        source_version_refs=(source_revision,),
        target_version_refs=target_revisions,
        content_snapshot_digest=sha("1"),
        payload_digest=sha("2"),
        target_digest=sha("3"),
        state_binding_digest=sha("4"),
        proposed_change_ref=patch.change_ref,
        proposed_change_digest=proposed_change_digest or patch.digest(),
        idempotency_key="sanity-product-1-v2",
    )


def response(
    *,
    document_ids: tuple[str, ...] = ("product-1",),
    previous_revisions: tuple[str, ...] = ("rev-source-1",),
    current_revisions: tuple[str, ...] = ("rev-provider-generated-2",),
) -> SanityMutationResponse:
    return SanityMutationResponse(
        transaction_id="exec-sanity-1",
        provider_reference="sanity:transaction:exec-sanity-1",
        status="committed",
        document_ids=document_ids,
        previous_revisions=previous_revisions,
        current_revisions=current_revisions,
        snapshot_digest=sha("5"),
        evidence_refs=("sanity:history:exec-sanity-1",),
        response={"result_ref": "sanity:result:exec-sanity-1"},
    )


def transport(
    patch: SanityPatchArtifact,
    client: Client,
    *,
    writes_enabled: bool = True,
) -> SanityConditionalMutationTransport:
    return SanityConditionalMutationTransport(
        client=client,
        patch_resolver=ArtifactResolver(patch),
        value_resolver=ValueResolver(),
        project_ref="project:products",
        dataset_ref="dataset:test",
        schema=schema(),
        writes_enabled=writes_enabled,
    )


def evidence(
    patch: SanityPatchArtifact,
    *,
    status: SanityTransactionStatus = SanityTransactionStatus.COMMITTED,
    change_digest: str | None = None,
) -> SanityTransactionEvidence:
    return SanityTransactionEvidence(
        transaction_id="exec-sanity-1",
        provider_reference="sanity:transaction:exec-sanity-1",
        project_ref="project:products",
        dataset_ref="dataset:test",
        status=status,
        operation=ContentOperation.UPDATE_FIELD,
        document_ids=("product-1",),
        previous_revisions=("rev-source-1",),
        current_revisions=(
            ("rev-provider-generated-2",)
            if status is SanityTransactionStatus.COMMITTED
            else ()
        ),
        proposed_change_digest=change_digest or patch.digest(),
        snapshot_digest=sha("5") if status is SanityTransactionStatus.COMMITTED else None,
        evidence_refs=("sanity:history:exec-sanity-1",),
        observed_at=datetime.now(timezone.utc),
        response={"status": status.value},
    )


def expected_effect(patch: SanityPatchArtifact) -> dict[str, object]:
    return {
        "content_system": "sanity",
        "project_ref": "project:products",
        "dataset_ref": "dataset:test",
        "operation": ContentOperation.UPDATE_FIELD.value,
        "record_ids": ["product-1"],
        "source_version_refs": ["rev-source-1"],
        "target_version_refs": [],
        "proposed_change_digest": patch.digest(),
    }


def test_writes_are_disabled_by_default_without_provider_call() -> None:
    patch = artifact()
    client = Client(response=response())
    adapter = transport(patch, client, writes_enabled=False)

    with pytest.raises(DefiniteProviderFailure, match="disabled"):
        adapter.mutate_if_current(request(patch))

    assert client.mutation_calls == []


def test_exact_patch_builds_one_revision_conditional_transaction() -> None:
    patch = artifact()
    client = Client(response=response())
    result = transport(patch, client).mutate_if_current(request(patch))

    assert result.current_version_refs == ("rev-provider-generated-2",)
    assert len(client.mutation_calls) == 1
    transaction = client.mutation_calls[0]
    assert transaction.transaction_id == "exec-sanity-1"
    assert transaction.visibility == "sync"
    assert transaction.return_ids is True
    provider_patch = transaction.mutations[0]["patch"]
    assert provider_patch["id"] == "product-1"
    assert provider_patch["ifRevisionID"] == "rev-source-1"
    assert provider_patch["set"] == {"title": "New title"}
    assert provider_patch["inc"] == {"views": 1}
    assert provider_patch["unset"] == ["legacyField"]


def test_patch_artifact_digest_mismatch_fails_before_provider_call() -> None:
    patch = artifact()
    client = Client(response=response())

    with pytest.raises(DefiniteProviderFailure, match="digest mismatch"):
        transport(patch, client).mutate_if_current(
            request(patch, proposed_change_digest=sha("9"))
        )

    assert client.mutation_calls == []


def test_stale_source_revision_fails_before_provider_call() -> None:
    patch = artifact()
    client = Client(response=response())

    with pytest.raises(DefiniteProviderFailure, match="source revision"):
        transport(patch, client).mutate_if_current(
            request(patch, source_revision="rev-stale")
        )

    assert client.mutation_calls == []


def test_provider_revision_precondition_failure_is_definite_no_effect() -> None:
    patch = artifact()
    client = Client(
        mutation_error=SanityDefiniteNoEffectError("ifRevisionID rejected; no effect")
    )

    with pytest.raises(DefiniteProviderFailure, match="no effect"):
        transport(patch, client).mutate_if_current(request(patch))

    assert len(client.mutation_calls) == 1


def test_unknown_provider_failure_is_indeterminate() -> None:
    patch = artifact()
    client = Client(mutation_error=SanityUnknownEffectError("timeout after submit"))

    with pytest.raises(IndeterminateProviderFailure, match="timeout"):
        transport(patch, client).mutate_if_current(request(patch))


def test_provider_generated_revision_satisfies_postcondition_without_explicit_target() -> None:
    patch = artifact()
    mutation_request = request(patch)
    result = transport(patch, Client(response=response())).mutate_if_current(
        mutation_request
    )

    ClearedContentMutationConnector._verify_postcondition(
        observed=result,
        request=mutation_request,
    )


def test_explicit_target_revision_must_match_provider_result() -> None:
    patch = artifact()
    mutation_request = request(
        patch,
        target_revisions=("rev-cleared-target",),
    )
    result = transport(patch, Client(response=response())).mutate_if_current(
        mutation_request
    )

    with pytest.raises(IndeterminateProviderFailure, match="target versions"):
        ClearedContentMutationConnector._verify_postcondition(
            observed=result,
            request=mutation_request,
        )


def test_malformed_provider_success_is_indeterminate() -> None:
    patch = artifact()
    client = Client(response=response(document_ids=("other-product",)))

    with pytest.raises(IndeterminateProviderFailure, match="bind"):
        transport(patch, client).mutate_if_current(request(patch))


def test_exact_durable_replay_performs_zero_additional_sanity_calls(tmp_path) -> None:
    patch = artifact()
    client = Client(response=response())
    adapter = transport(patch, client)
    mutation_request = request(patch)
    boundary = Boundary()
    durable = DurableConnectorExecutor(
        journal=SQLiteExecutionJournal(tmp_path / "journal.db"),
        boundary=boundary,  # type: ignore[arg-type]
    )
    token = {
        "payload": {
            "execution_id": mutation_request.execution_id,
            "tenant_id": mutation_request.tenant_id,
            "commit_token_id": "token-sanity-1",
        }
    }

    def mutate(execution_id: str) -> ProviderResult:
        assert execution_id == mutation_request.execution_id
        observed = adapter.mutate_if_current(mutation_request)
        return ProviderResult(
            provider_reference=observed.provider_reference,
            response=observed.response,
        )

    first = durable.execute(
        signed_commit_token=token,
        connector_id="connector.content.sanity",
        capability=mutation_request.operation.value,
        target_digest=mutation_request.target_digest,
        payload_digest=mutation_request.payload_digest,
        mutation=mutate,
        receipt_id="receipt-sanity-1",
        idempotency_key=mutation_request.idempotency_key,
    )
    second = durable.execute(
        signed_commit_token=token,
        connector_id="connector.content.sanity",
        capability=mutation_request.operation.value,
        target_digest=mutation_request.target_digest,
        payload_digest=mutation_request.payload_digest,
        mutation=mutate,
        receipt_id="receipt-sanity-2",
        idempotency_key=mutation_request.idempotency_key,
    )

    assert first.record.state is ExecutionState.SUCCEEDED
    assert first.replayed is False
    assert second.record.state is ExecutionState.SUCCEEDED
    assert second.replayed is True
    assert len(client.mutation_calls) == 1
    assert boundary.calls == 1


def test_transaction_lookup_confirms_exact_effect_binding() -> None:
    patch = artifact()
    client = Client(evidence=evidence(patch))
    observation = transport(patch, client).lookup(
        execution_id="exec-sanity-1",
        provider_reference="unavailable",
        idempotency_key="sanity-product-1-v2",
    )

    assert observation.resolution is ProviderResolution.CONFIRMED_SUCCEEDED
    assert observation.observed_effect["current_version_refs"] == [
        "rev-provider-generated-2"
    ]
    ContentMutationReconciliationAdapter._verify_observed_effect(
        observation,
        expected_effect(patch),
    )
    assert client.mutation_calls == []
    assert len(client.lookup_calls) == 1


def test_unknown_transaction_remains_unknown_without_mutation() -> None:
    patch = artifact()
    client = Client(evidence=None)
    observation = transport(patch, client).lookup(
        execution_id="exec-sanity-1",
        provider_reference="unavailable",
        idempotency_key="sanity-product-1-v2",
    )

    assert observation.resolution is ProviderResolution.UNKNOWN
    assert observation.observed_effect == {}
    assert client.mutation_calls == []


def test_mismatched_provider_effect_is_rejected_before_outcome_finalization() -> None:
    patch = artifact()
    observation = transport(
        patch,
        Client(evidence=evidence(patch, change_digest=sha("8"))),
    ).lookup(
        execution_id="exec-sanity-1",
        provider_reference="unavailable",
        idempotency_key="sanity-product-1-v2",
    )

    with pytest.raises(ReconciliationError, match="proposed_change_digest"):
        ContentMutationReconciliationAdapter._verify_observed_effect(
            observation,
            expected_effect(patch),
        )


def test_reconciliation_service_runs_verifier_before_terminal_transition(tmp_path) -> None:
    journal = SQLiteExecutionJournal(tmp_path / "verify.db")
    journal.reserve(
        execution_id="exec-sanity-1",
        tenant_id="tenant-1",
        idempotency_key="sanity-product-1-v2",
        request_digest=sha("1"),
        commit_token_id="token-1",
        commit_token_digest=sha("2"),
        connector_id="connector.content.sanity",
        capability=ContentOperation.UPDATE_FIELD.value,
        target_digest=sha("3"),
        payload_digest=sha("4"),
    )
    journal.transition(
        "exec-sanity-1",
        expected=ExecutionState.RESERVED,
        target=ExecutionState.STARTED,
    )
    journal.transition(
        "exec-sanity-1",
        expected=ExecutionState.STARTED,
        target=ExecutionState.INDETERMINATE,
        provider_reference="unavailable",
        receipt_id="execution-receipt-1",
        receipt_digest=sha("5"),
    )
    observation = ProviderObservation(
        resolution=ProviderResolution.CONFIRMED_SUCCEEDED,
        provider_reference="sanity:transaction:exec-sanity-1",
        observed_effect={"wrong": True},
        evidence_refs=("sanity:history:exec-sanity-1",),
        measurement_method="sanity-transaction-history",
        observed_at=datetime.now(timezone.utc),
        response={"status": "committed"},
    )
    service = ProviderReconciliationService(
        journal=journal,
        provider_lookup=Lookup(observation),
        outcome_signer=Signer(),
        trust_domain="tenant-1:test",
    )

    def reject(_observation, _expected):
        raise ReconciliationError("provider effect mismatch")

    with pytest.raises(ReconciliationError, match="mismatch"):
        service.reconcile(
            "exec-sanity-1",
            outcome_receipt_id="outcome-1",
            observation_window={"from": "a", "to": "b"},
            expected_effect={"effect": "expected"},
            baseline_ref="baseline:1",
            attribution_score=1.0,
            confidence=1.0,
            observation_verifier=reject,
        )

    assert journal.get("exec-sanity-1").state is ExecutionState.RECONCILIATION_REQUIRED


def test_patch_artifact_rejects_system_fields_and_contains_no_raw_values() -> None:
    with pytest.raises(ValidationError, match="system field"):
        SanityPatchInstruction(
            verb=SanityPatchVerb.SET,
            path="_rev",
            value_ref="value:title",
            value_digest=digest("New title"),
        )

    payload = artifact().model_dump_json()
    assert "New title" not in payload
    assert "credential" not in payload.lower()
    assert "commit_token" not in payload.lower()
