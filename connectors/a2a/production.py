"""Hardened production surface for the governed A2A HTTP+JSON client.

This module wraps the protocol implementation in ``client.py`` and closes the
last transport-boundary invariants: semantic task/tenant binding, exhaustive
authority-result binding, envelope-bounded artifact inspection, wire evidence
immediately before I/O, and denial receipts for unsafe responses.
"""

from __future__ import annotations

import copy
import hmac
import urllib.parse
from typing import Any, Mapping, MutableMapping

from . import client as base

A2A_VERSION = base.A2A_VERSION
EXTENSION_URI = base.EXTENSION_URI
CLIENT_REQUEST_CONTRACT = base.CLIENT_REQUEST_CONTRACT
CLIENT_RESULT_CONTRACT = base.CLIENT_RESULT_CONTRACT
RECEIPT_CONTRACT = base.RECEIPT_CONTRACT
ENVELOPE = base.ENVELOPE
A2AClientError = base.A2AClientError
AgentCardError = base.AgentCardError
AuthorityError = base.AuthorityError
TransportError = base.TransportError
ArtifactInspectionError = base.ArtifactInspectionError
ReceiptError = base.ReceiptError
AgentCardEvidence = base.AgentCardEvidence
ClientConfig = base.ClientConfig
ReceiptWriter = base.ReceiptWriter
canonical_json = base.canonical_json
sha256_hex = base.sha256_hex
sha256_hex_bytes = base.sha256_hex_bytes
require_mapping = base.require_mapping
require_string = base.require_string
require_digest = base.require_digest
PROMPT_INJECTION_PATTERNS = base.PROMPT_INJECTION_PATTERNS
SECRET_PATTERNS = base.SECRET_PATTERNS
TERMINAL_TASK_STATES = base.TERMINAL_TASK_STATES


class GovernedA2AClient(base.GovernedA2AClient):
    """Production-hardened A2A 1.0 HTTP+JSON client."""

    @staticmethod
    def prepare_payload(
        envelope: Mapping[str, Any], payload: Mapping[str, Any]
    ) -> dict[str, Any]:
        operation = require_string(envelope.get("operation"), "operation").upper()
        prepared = copy.deepcopy(dict(require_mapping(payload, "a2a_payload")))
        governed_payload = require_mapping(envelope.get("payload"), "payload")

        expected_tenant = governed_payload.get("tenant")
        supplied_tenant = prepared.get("tenant")
        if expected_tenant not in (None, ""):
            if supplied_tenant not in (None, expected_tenant):
                raise A2AClientError(
                    "A2A payload tenant differs from mandate envelope"
                )
            prepared["tenant"] = expected_tenant
        elif supplied_tenant not in (None, ""):
            raise A2AClientError("A2A payload supplies an ungoverned tenant")
        else:
            prepared.pop("tenant", None)

        if operation == "SEND_MESSAGE":
            message = prepared.get("message")
            if not isinstance(message, MutableMapping):
                raise A2AClientError(
                    "SEND_MESSAGE payload.message must be an object"
                )
            message_id = require_string(
                message.get("messageId", message.get("message_id")),
                "message.messageId",
            )
            if message_id != governed_payload["message_id"]:
                raise A2AClientError(
                    "A2A message id differs from mandate envelope"
                )
            extensions = message.setdefault("extensions", [])
            if not isinstance(extensions, list) or not all(
                isinstance(item, str) for item in extensions
            ):
                raise A2AClientError("message.extensions must be a string list")
            if EXTENSION_URI not in extensions:
                extensions.append(EXTENSION_URI)
            metadata = prepared.setdefault("metadata", {})
            if not isinstance(metadata, MutableMapping):
                raise A2AClientError("SEND_MESSAGE metadata must be an object")
            expected = {
                "contract": ENVELOPE.CONTRACT,
                "envelope_id": envelope["envelope_id"],
            }
            existing = metadata.get(EXTENSION_URI)
            if existing is not None and existing != expected:
                raise A2AClientError(
                    "existing mandate extension metadata conflicts with envelope"
                )
            metadata[EXTENSION_URI] = expected

        elif operation in {"GET_TASK", "CANCEL_TASK"}:
            task_id = require_string(prepared.get("id"), "a2a_payload.id")
            governed_task_id = require_string(
                governed_payload.get("task_id"), "payload.task_id"
            )
            if task_id != governed_task_id:
                raise A2AClientError(
                    "A2A task id differs from mandate envelope"
                )

        if operation == "CANCEL_TASK":
            metadata = prepared.setdefault("metadata", {})
            if not isinstance(metadata, MutableMapping):
                raise A2AClientError("CANCEL_TASK metadata must be an object")
            metadata[EXTENSION_URI] = {
                "contract": ENVELOPE.CONTRACT,
                "envelope_id": envelope["envelope_id"],
            }

        return prepared

    def _check_authority(
        self, envelope: Mapping[str, Any]
    ) -> Mapping[str, Any]:
        output = require_mapping(
            self.authority_checker(envelope), "authority check output"
        )
        if output.get("valid") is not True:
            raise AuthorityError(
                "authority, delegation, revocation or MAL check denied"
            )

        expected = {
            "principal_id": envelope["source"]["principal_id"],
            "source_agent_id": envelope["source"]["agent_id"],
            "target_agent_id": envelope["target"]["agent_id"],
            "authority_grant_id": envelope["mandate"]["authority_grant_id"],
            "delegation_chain_digest": envelope["mandate"][
                "delegation_chain_digest"
            ],
            "purpose_digest": envelope["mandate"]["purpose_digest"],
            "revocation_registry_ref": envelope["mandate"][
                "revocation_registry_ref"
            ],
            "mal_profile_id": envelope["target"]["mal_profile_id"],
            "action_digest": envelope["action_digest"],
        }
        for field, value in expected.items():
            if output.get(field) != value:
                raise AuthorityError(
                    f"authority check {field} binding mismatch"
                )

        self.receipts.write(
            "AUTHORITY_VERIFIED",
            {
                "envelope_id": envelope["envelope_id"],
                "action_digest": envelope["action_digest"],
                **expected,
                "checker_evidence_digest": sha256_hex(output),
            },
        )
        return output

    def _record_wire_dispatch(
        self,
        method: str,
        url: str,
        headers: Mapping[str, str],
        body: bytes | None,
    ) -> dict[str, Any]:
        public_headers = {
            name.lower(): value
            for name, value in headers.items()
            if name.lower() != "authorization"
        }
        evidence = {
            "method": method,
            "url": url,
            "public_headers": public_headers,
            "authorization_present": any(
                name.lower() == "authorization" for name in headers
            ),
            "body_sha256": sha256_hex_bytes(body or b""),
            "body_size_bytes": len(body or b""),
        }
        evidence["wire_request_digest"] = sha256_hex(evidence)
        return self.receipts.write("A2A_WIRE_DISPATCH", evidence)

    def _request(
        self,
        method: str,
        url: str,
        headers: Mapping[str, str],
        body: bytes | None,
        max_bytes: int,
    ) -> tuple[int, Mapping[str, str], bytes]:
        self._record_wire_dispatch(method, url, headers, body)
        return super()._request(method, url, headers, body, max_bytes)

    def _inspect_response(
        self, envelope: Mapping[str, Any], raw: bytes
    ) -> dict[str, Any]:
        governed_max = envelope["payload"].get("maximum_artifact_bytes")
        effective_max = self.config.max_artifact_bytes
        if governed_max is not None:
            effective_max = min(effective_max, governed_max)
        if len(raw) > effective_max:
            self._deny_response(
                envelope,
                raw,
                "A2A response exceeds governed artifact inspection limit",
            )

        try:
            payload = base.json.loads(raw)
        except base.json.JSONDecodeError as exc:
            self._deny_response(envelope, raw, "A2A response is not valid JSON")
            raise AssertionError("unreachable") from exc

        texts: list[str] = []
        urls: list[str] = []
        artifacts: list[dict[str, Any]] = []
        task_states: list[str] = []

        def walk(value: Any, path: str = "$") -> None:
            if isinstance(value, Mapping):
                if "artifactId" in value or "artifact_id" in value:
                    artifact_id = value.get(
                        "artifactId", value.get("artifact_id")
                    )
                    artifacts.append(
                        {
                            "artifact_id": artifact_id,
                            "path": path,
                            "digest": sha256_hex(value),
                            "size_bytes": len(canonical_json(value)),
                        }
                    )
                state = value.get("state")
                if isinstance(state, str) and state.startswith("TASK_STATE_"):
                    task_states.append(state)
                for key, item in value.items():
                    if key in {"text", "description", "name"} and isinstance(
                        item, str
                    ):
                        texts.append(item)
                    if key in {"url", "uri"} and isinstance(item, str):
                        urls.append(item)
                    walk(item, f"{path}.{key}")
            elif isinstance(value, list):
                for index, item in enumerate(value):
                    walk(item, f"{path}[{index}]")

        walk(payload)
        combined = "\n".join(texts)
        for pattern in PROMPT_INJECTION_PATTERNS:
            if pattern.search(combined):
                self._deny_response(
                    envelope,
                    raw,
                    "returned A2A content matches prompt-injection policy",
                )
        for name, pattern in SECRET_PATTERNS:
            if pattern.search(combined):
                self._deny_response(
                    envelope,
                    raw,
                    f"returned A2A content contains secret material: {name}",
                )

        unsafe_urls: list[str] = []
        for url in urls:
            try:
                parsed = urllib.parse.urlparse(url)
                if (
                    parsed.scheme != "https"
                    or parsed.username
                    or parsed.password
                    or not parsed.netloc
                ):
                    unsafe_urls.append(url)
            except ValueError:
                unsafe_urls.append(url)
        if unsafe_urls:
            self._deny_response(
                envelope,
                raw,
                "returned A2A artifacts contain unsafe file URLs",
            )

        inspection = {
            "response_digest": sha256_hex_bytes(raw),
            "response_size_bytes": len(raw),
            "artifact_digests": artifacts,
            "task_states": sorted(set(task_states)),
            "terminal_transport_state_observed": any(
                state in TERMINAL_TASK_STATES for state in task_states
            ),
            "local_execution_authorized": False,
            "requires_new_reht_before_local_consequence": True,
            "semantic_integrity": {
                "original_response_preserved": True,
                "language_transformed": False,
                "provenance_target_agent_id": envelope["target"]["agent_id"],
            },
        }
        self.receipts.write(
            "A2A_RESPONSE_INSPECTED",
            {
                "envelope_id": envelope["envelope_id"],
                "action_digest": envelope["action_digest"],
                **inspection,
            },
        )
        return {"payload": payload, "inspection": inspection}

    def _deny_response(
        self, envelope: Mapping[str, Any], raw: bytes, reason: str
    ) -> None:
        self.receipts.write(
            "A2A_RESPONSE_DENIED",
            {
                "envelope_id": envelope["envelope_id"],
                "action_digest": envelope["action_digest"],
                "response_digest": sha256_hex_bytes(raw),
                "response_size_bytes": len(raw),
                "reason": reason,
            },
        )
        raise ArtifactInspectionError(reason)


def prepare_payload_and_digest(
    envelope: Mapping[str, Any], payload: Mapping[str, Any]
) -> dict[str, Any]:
    prepared = GovernedA2AClient.prepare_payload(envelope, payload)
    return {
        "a2a_payload": prepared,
        "a2a_payload_digest": sha256_hex(prepared),
    }
