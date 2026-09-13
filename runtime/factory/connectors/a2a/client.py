"""Governed A2A 1.0 HTTP+JSON client adapter.

The adapter transports only an already governed, digest-bound operation. It
re-verifies the live Agent Card, authority/delegation/revocation evidence, exact
wire payload, and returned artifacts. A2A task state never grants local
execution authority.
"""

from __future__ import annotations

import copy
import hashlib
import hmac
import importlib.machinery
import importlib.util
import ipaddress
import json
import os
import pathlib
import re
import shlex
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable, Mapping, MutableMapping

A2A_VERSION = "1.0"
EXTENSION_URI = "urn:valo:a2a:mandate-envelope:v1"
CLIENT_REQUEST_CONTRACT = "valo.a2a.client-request.v1"
CLIENT_RESULT_CONTRACT = "valo.a2a.client-result.v1"
RECEIPT_CONTRACT = "valo.a2a.receipt.v1"
CARD_CACHE_CONTRACT = "valo.a2a.agent-card-cache.v1"
SUPPORTED_OPERATIONS = {"SEND_MESSAGE", "GET_TASK", "LIST_TASKS", "CANCEL_TASK"}
STREAMING_OPERATIONS = {"SEND_STREAMING_MESSAGE", "SUBSCRIBE_TASK"}
TERMINAL_TASK_STATES = {
    "TASK_STATE_COMPLETED",
    "TASK_STATE_FAILED",
    "TASK_STATE_CANCELED",
    "TASK_STATE_REJECTED",
}
HEX64 = re.compile(r"^[0-9a-f]{64}$")
PROMPT_INJECTION_PATTERNS = (
    re.compile(r"\bignore\s+(all\s+)?(previous|prior|earlier)\s+instructions\b", re.I),
    re.compile(r"\b(disregard|override)\s+(the\s+)?(system|developer|policy)\s+(message|instructions?)\b", re.I),
    re.compile(r"\byou\s+are\s+now\s+(in\s+)?(developer|system|admin)\s+mode\b", re.I),
    re.compile(r"\breveal\s+(your\s+)?(system\s+prompt|hidden\s+instructions?)\b", re.I),
    re.compile(r"\b(exfiltrate|upload|send)\b.{0,80}\b(secret|credential|token|api[ -]?key|private key)\b", re.I | re.S),
)
SECRET_PATTERNS = (
    ("PEM_PRIVATE_KEY", re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----")),
    ("AWS_ACCESS_KEY", re.compile(r"\b(?:AKIA|ASIA)[A-Z0-9]{16}\b")),
    ("GITHUB_TOKEN", re.compile(r"\bgh[pousr]_[A-Za-z0-9_]{20,}\b")),
    ("BEARER_TOKEN", re.compile(r"(?i)\bBearer\s+[A-Za-z0-9._~+/=-]{16,}")),
    ("GENERIC_API_KEY", re.compile(r"(?i)\b(api[_ -]?key|access[_ -]?token|client[_ -]?secret)\b\s*[:=]\s*[\"']?[A-Za-z0-9._~+/=-]{16,}")),
)


class A2AClientError(RuntimeError):
    """Base fail-closed adapter error."""


class AgentCardError(A2AClientError):
    pass


class AuthorityError(A2AClientError):
    pass


class TransportError(A2AClientError):
    pass


class ArtifactInspectionError(A2AClientError):
    pass


class ReceiptError(A2AClientError):
    pass


def _load_envelope_module():
    path = pathlib.Path(__file__).resolve().parents[2] / "bin" / "valo-a2a-envelope"
    loader = importlib.machinery.SourceFileLoader("valo_a2a_envelope_runtime", str(path))
    spec = importlib.util.spec_from_loader(loader.name, loader)
    if spec is None:
        raise RuntimeError("cannot load A2A envelope validator")
    module = importlib.util.module_from_spec(spec)
    sys.modules[loader.name] = module
    loader.exec_module(module)
    return module


ENVELOPE = _load_envelope_module()


def canonical_json(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def sha256_hex_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_hex(value: Any) -> str:
    return sha256_hex_bytes(canonical_json(value))


def require_mapping(value: Any, name: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise A2AClientError(f"{name} must be an object")
    return value


def require_string(value: Any, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise A2AClientError(f"{name} must be a non-empty string")
    return value


def require_digest(value: Any, name: str) -> str:
    digest = require_string(value, name).lower()
    if not HEX64.fullmatch(digest):
        raise A2AClientError(f"{name} must be lowercase SHA-256 hex")
    return digest


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def normalize_binding(value: str) -> str:
    normalized = value.upper().replace("_", "+")
    aliases = {"HTTP+JSON/REST": "HTTP+JSON", "REST": "HTTP+JSON", "HTTPJSON": "HTTP+JSON"}
    return aliases.get(normalized, normalized)


def is_safe_url(url: str, *, allow_private_network: bool = False) -> urllib.parse.ParseResult:
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme != "https" or not parsed.netloc or parsed.username or parsed.password:
        raise TransportError("A2A URLs must be credential-free HTTPS")
    host = parsed.hostname
    if not host:
        raise TransportError("A2A URL host is required")
    if not allow_private_network:
        try:
            addresses = {item[4][0] for item in socket.getaddrinfo(host, parsed.port or 443, type=socket.SOCK_STREAM)}
        except socket.gaierror as exc:
            raise TransportError(f"cannot resolve A2A host: {host}") from exc
        if not addresses:
            raise TransportError("A2A host resolved to no addresses")
        for address in addresses:
            ip = ipaddress.ip_address(address)
            if not ip.is_global:
                raise TransportError(f"A2A host resolves to non-global address: {address}")
    return parsed


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):  # noqa: ANN001
        raise TransportError(f"redirect blocked: HTTP {code}")


@dataclass(frozen=True)
class AgentInterface:
    url: str
    binding: str
    version: str
    tenant: str | None = None


@dataclass(frozen=True)
class AgentCardEvidence:
    url: str
    digest: str
    retrieved_at: str
    card: Mapping[str, Any]
    interface: AgentInterface
    trust_basis: str
    signature_verified: bool


@dataclass
class ReceiptWriter:
    path: pathlib.Path | None = None
    memory: list[dict[str, Any]] = field(default_factory=list)
    previous_chain_hash: str = "0" * 64

    def __post_init__(self) -> None:
        if self.path is not None:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            if self.path.exists():
                lines = self.path.read_text(encoding="utf-8").splitlines()
                if lines:
                    try:
                        last = json.loads(lines[-1])
                        self.previous_chain_hash = require_digest(last.get("chain_hash"), "last receipt chain_hash")
                    except (json.JSONDecodeError, A2AClientError) as exc:
                        raise ReceiptError("receipt log tail is invalid") from exc

    def write(self, event_type: str, evidence: Mapping[str, Any]) -> dict[str, Any]:
        core = {
            "contract": RECEIPT_CONTRACT,
            "event_type": event_type,
            "timestamp_ns": time.time_ns(),
            "previous_chain_hash": self.previous_chain_hash,
            "evidence": dict(evidence),
        }
        receipt = dict(core)
        receipt["chain_hash"] = sha256_hex(core)
        line = json.dumps(receipt, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        if self.path is not None:
            try:
                with self.path.open("a", encoding="utf-8") as handle:
                    handle.write(line + "\n")
                    handle.flush()
                    os.fsync(handle.fileno())
            except OSError as exc:
                raise ReceiptError(f"cannot persist A2A receipt: {exc}") from exc
        self.memory.append(receipt)
        self.previous_chain_hash = receipt["chain_hash"]
        return receipt


@dataclass
class ClientConfig:
    timeout_seconds: float = 10.0
    max_card_bytes: int = 262_144
    max_response_bytes: int = 1_048_576
    max_artifact_bytes: int = 1_048_576
    allow_private_network: bool = False
    allow_direct_configuration: bool = False
    card_cache_path: pathlib.Path | None = None
    auth_token: str | None = None
    auth_scheme: str = "Bearer"
    user_agent: str = "VALO-Governed-A2A/1"

    @classmethod
    def from_env(cls) -> "ClientConfig":
        cache = os.environ.get("VALO_A2A_CARD_CACHE", "").strip()
        return cls(
            timeout_seconds=float(os.environ.get("VALO_A2A_TIMEOUT_SECONDS", "10")),
            max_card_bytes=int(os.environ.get("VALO_A2A_MAX_CARD_BYTES", "262144")),
            max_response_bytes=int(os.environ.get("VALO_A2A_MAX_RESPONSE_BYTES", "1048576")),
            max_artifact_bytes=int(os.environ.get("VALO_A2A_MAX_ARTIFACT_BYTES", "1048576")),
            allow_private_network=os.environ.get("VALO_A2A_ALLOW_PRIVATE_NETWORK") == "1",
            allow_direct_configuration=os.environ.get("VALO_A2A_ALLOW_DIRECT_CONFIGURATION") == "1",
            card_cache_path=pathlib.Path(cache) if cache else None,
            auth_token=os.environ.get("VALO_A2A_AUTH_TOKEN") or None,
            auth_scheme=os.environ.get("VALO_A2A_AUTH_SCHEME", "Bearer"),
        )


AuthorityChecker = Callable[[Mapping[str, Any]], Mapping[str, Any]]
CardVerifier = Callable[[Mapping[str, Any]], Mapping[str, Any]]
URLFetcher = Callable[[str, Mapping[str, str], int], tuple[int, Mapping[str, str], bytes]]


def run_json_command(env_name: str, payload: Mapping[str, Any], *, timeout_seconds: float) -> Mapping[str, Any]:
    command_text = os.environ.get(env_name, "").strip()
    if not command_text:
        raise AuthorityError(f"{env_name} is not configured")
    command = shlex.split(command_text)
    if not command:
        raise AuthorityError(f"{env_name} is empty")
    try:
        completed = subprocess.run(
            command,
            input=canonical_json(payload),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=timeout_seconds,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise AuthorityError(f"{env_name} unavailable: {exc}") from exc
    if completed.returncode != 0:
        detail = completed.stderr.decode("utf-8", errors="replace")[:500]
        raise AuthorityError(f"{env_name} returned {completed.returncode}: {detail}")
    if len(completed.stdout) > 1_048_576:
        raise AuthorityError(f"{env_name} output exceeds limit")
    try:
        output = json.loads(completed.stdout)
    except json.JSONDecodeError as exc:
        raise AuthorityError(f"{env_name} returned invalid JSON") from exc
    return require_mapping(output, f"{env_name} output")


def default_authority_checker(envelope: Mapping[str, Any], *, timeout_seconds: float) -> Mapping[str, Any]:
    query = {
        "contract": "valo.a2a.authority-check.v1",
        "principal_id": envelope["source"]["principal_id"],
        "source_agent_id": envelope["source"]["agent_id"],
        "target_agent_id": envelope["target"]["agent_id"],
        "authority_grant_id": envelope["mandate"]["authority_grant_id"],
        "delegation_chain_digest": envelope["mandate"]["delegation_chain_digest"],
        "purpose_digest": envelope["mandate"]["purpose_digest"],
        "scope": envelope["mandate"]["scope"],
        "constraints": envelope["mandate"].get("constraints", {}),
        "expires_at": envelope["mandate"]["expires_at"],
        "revocation_registry_ref": envelope["mandate"]["revocation_registry_ref"],
        "mal_profile_id": envelope["target"]["mal_profile_id"],
        "action_digest": envelope["action_digest"],
    }
    output = run_json_command("VALO_A2A_AUTHORITY_CHECK_COMMAND", query, timeout_seconds=timeout_seconds)
    if output.get("valid") is not True:
        raise AuthorityError(require_string(output.get("reason", "authority check denied"), "authority reason"))
    for field, expected in (
        ("authority_grant_id", query["authority_grant_id"]),
        ("delegation_chain_digest", query["delegation_chain_digest"]),
        ("mal_profile_id", query["mal_profile_id"]),
        ("action_digest", query["action_digest"]),
    ):
        if output.get(field) != expected:
            raise AuthorityError(f"authority check {field} binding mismatch")
    return output


def default_card_verifier(payload: Mapping[str, Any], *, timeout_seconds: float) -> Mapping[str, Any]:
    return run_json_command("VALO_A2A_AGENT_CARD_VERIFY_COMMAND", payload, timeout_seconds=timeout_seconds)


class GovernedA2AClient:
    def __init__(
        self,
        *,
        config: ClientConfig | None = None,
        receipt_writer: ReceiptWriter | None = None,
        authority_checker: AuthorityChecker | None = None,
        card_verifier: CardVerifier | None = None,
        fetcher: URLFetcher | None = None,
    ) -> None:
        self.config = config or ClientConfig.from_env()
        if self.config.timeout_seconds <= 0 or self.config.timeout_seconds > 60:
            raise A2AClientError("timeout_seconds must be >0 and <=60")
        self.receipts = receipt_writer or self._receipt_writer_from_env()
        self.authority_checker = authority_checker or (
            lambda envelope: default_authority_checker(envelope, timeout_seconds=self.config.timeout_seconds)
        )
        self.card_verifier = card_verifier or (
            lambda payload: default_card_verifier(payload, timeout_seconds=self.config.timeout_seconds)
        )
        self.fetcher = fetcher or self._fetch

    def _receipt_writer_from_env(self) -> ReceiptWriter:
        path = os.environ.get("VALO_A2A_RECEIPT_LOG", "").strip()
        if not path:
            raise ReceiptError("VALO_A2A_RECEIPT_LOG is required")
        return ReceiptWriter(pathlib.Path(path))

    def _fetch(self, url: str, headers: Mapping[str, str], max_bytes: int) -> tuple[int, Mapping[str, str], bytes]:
        is_safe_url(url, allow_private_network=self.config.allow_private_network)
        request = urllib.request.Request(url, headers=dict(headers), method="GET")
        opener = urllib.request.build_opener(NoRedirect())
        try:
            with opener.open(request, timeout=self.config.timeout_seconds) as response:
                data = response.read(max_bytes + 1)
                if len(data) > max_bytes:
                    raise TransportError("response exceeds configured limit")
                return response.status, dict(response.headers.items()), data
        except TransportError:
            raise
        except urllib.error.HTTPError as exc:
            body = exc.read(min(max_bytes, 4096))
            raise TransportError(f"HTTP {exc.code} from A2A endpoint; body_digest={sha256_hex_bytes(body)}") from exc
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            raise TransportError(f"A2A endpoint unavailable: {exc}") from exc

    def _request(self, method: str, url: str, headers: Mapping[str, str], body: bytes | None, max_bytes: int) -> tuple[int, Mapping[str, str], bytes]:
        is_safe_url(url, allow_private_network=self.config.allow_private_network)
        request = urllib.request.Request(url, headers=dict(headers), data=body, method=method)
        opener = urllib.request.build_opener(NoRedirect())
        try:
            with opener.open(request, timeout=self.config.timeout_seconds) as response:
                data = response.read(max_bytes + 1)
                if len(data) > max_bytes:
                    raise TransportError("A2A response exceeds configured limit")
                return response.status, dict(response.headers.items()), data
        except TransportError:
            raise
        except urllib.error.HTTPError as exc:
            data = exc.read(min(max_bytes + 1, 4096))
            raise TransportError(f"A2A HTTP {exc.code}; body_digest={sha256_hex_bytes(data)}") from exc
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            raise TransportError(f"A2A request failed: {exc}") from exc

    def fetch_agent_card(self, envelope: Mapping[str, Any]) -> AgentCardEvidence:
        target = require_mapping(envelope.get("target"), "target")
        card_url = require_string(target.get("agent_card_url"), "target.agent_card_url")
        expected_digest = require_digest(target.get("agent_card_digest"), "target.agent_card_digest")
        status, headers, raw = self.fetcher(
            card_url,
            {"Accept": "application/json", "User-Agent": self.config.user_agent},
            self.config.max_card_bytes,
        )
        if status != 200:
            raise AgentCardError(f"Agent Card HTTP status must be 200, got {status}")
        content_type = str(headers.get("Content-Type", headers.get("content-type", ""))).lower()
        if content_type and "json" not in content_type:
            raise AgentCardError("Agent Card content type must be JSON")
        try:
            card = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise AgentCardError("Agent Card is not valid JSON") from exc
        card = require_mapping(card, "Agent Card")
        live_digest = sha256_hex(card)
        if not hmac.compare_digest(live_digest, expected_digest):
            self.receipts.write("AGENT_CARD_DRIFT_DENIED", {
                "envelope_id": envelope.get("envelope_id"),
                "action_digest": envelope.get("action_digest"),
                "agent_card_url": card_url,
                "expected_digest": expected_digest,
                "live_digest": live_digest,
            })
            raise AgentCardError("live Agent Card digest differs from cleared digest")
        interface = self._select_interface(card, target, envelope)
        trust_basis = require_string(target.get("trust_basis"), "target.trust_basis").upper()
        signature_verified = self._verify_card_trust(card_url, card, live_digest, trust_basis)
        evidence = AgentCardEvidence(
            url=card_url,
            digest=live_digest,
            retrieved_at=utc_now(),
            card=card,
            interface=interface,
            trust_basis=trust_basis,
            signature_verified=signature_verified,
        )
        self._write_card_cache(evidence, envelope)
        self.receipts.write("AGENT_CARD_SELECTED", {
            "envelope_id": envelope["envelope_id"],
            "action_digest": envelope["action_digest"],
            "target_agent_id": target["agent_id"],
            "agent_card_url": card_url,
            "agent_card_digest": live_digest,
            "binding": interface.binding,
            "protocol_version": interface.version,
            "interface_url": interface.url,
            "tenant": interface.tenant,
            "trust_basis": trust_basis,
            "signature_verified": signature_verified,
        })
        return evidence

    def _select_interface(self, card: Mapping[str, Any], target: Mapping[str, Any], envelope: Mapping[str, Any]) -> AgentInterface:
        raw_interfaces = card.get("supportedInterfaces", card.get("supported_interfaces"))
        if not isinstance(raw_interfaces, list) or not raw_interfaces:
            raise AgentCardError("Agent Card has no supported interfaces")
        selected = normalize_binding(require_string(target.get("selected_interface"), "target.selected_interface"))
        if selected != "HTTP+JSON":
            raise AgentCardError("production adapter currently supports HTTP+JSON only")
        expected_tenant = require_mapping(envelope.get("payload"), "payload").get("tenant")
        for item in raw_interfaces:
            if not isinstance(item, Mapping):
                continue
            binding = normalize_binding(str(item.get("protocolBinding", item.get("protocol_binding", ""))))
            version = str(item.get("protocolVersion", item.get("protocol_version", "")))
            url = str(item.get("url", ""))
            tenant = item.get("tenant")
            if binding != selected or version != A2A_VERSION:
                continue
            is_safe_url(url, allow_private_network=self.config.allow_private_network)
            if tenant is not None and tenant != expected_tenant:
                raise AgentCardError("Agent Card tenant differs from governed payload tenant")
            if tenant is None and expected_tenant not in (None, ""):
                raise AgentCardError("governed payload specifies tenant but Agent Card interface does not")
            return AgentInterface(url=url.rstrip("/"), binding=binding, version=version, tenant=tenant)
        raise AgentCardError("Agent Card does not expose cleared HTTP+JSON 1.0 interface")

    def _verify_card_trust(self, card_url: str, card: Mapping[str, Any], digest: str, trust_basis: str) -> bool:
        if trust_basis == "SIGNED_AGENT_CARD":
            signatures = card.get("signatures")
            if not isinstance(signatures, list) or not signatures:
                raise AgentCardError("signed trust basis requires Agent Card signatures")
            output = self.card_verifier({
                "contract": "valo.a2a.agent-card-verify.v1",
                "agent_card_url": card_url,
                "agent_card_digest": digest,
                "agent_card": card,
            })
            if output.get("verified") is not True or output.get("agent_card_digest") != digest:
                raise AgentCardError("Agent Card signature verification failed or was not digest-bound")
            return True
        if trust_basis == "CURATED_REGISTRY":
            registry_path = os.environ.get("VALO_A2A_CURATED_REGISTRY", "").strip()
            if not registry_path:
                raise AgentCardError("VALO_A2A_CURATED_REGISTRY is required")
            try:
                registry = json.loads(pathlib.Path(registry_path).read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError) as exc:
                raise AgentCardError("curated Agent Card registry is unavailable or invalid") from exc
            entries = require_mapping(registry, "curated registry").get("agents", registry)
            entries = require_mapping(entries, "curated registry agents")
            record = entries.get(card_url)
            if isinstance(record, str):
                registered_digest = record
            elif isinstance(record, Mapping):
                registered_digest = record.get("digest")
            else:
                raise AgentCardError("Agent Card is absent from curated registry")
            if not hmac.compare_digest(require_digest(registered_digest, "registered Agent Card digest"), digest):
                raise AgentCardError("curated registry Agent Card digest mismatch")
            return False
        if trust_basis == "DIRECT_CONFIGURATION":
            if not self.config.allow_direct_configuration:
                raise AgentCardError("direct Agent Card configuration is disabled")
            return False
        raise AgentCardError("unsupported Agent Card trust basis")

    def _write_card_cache(self, evidence: AgentCardEvidence, envelope: Mapping[str, Any]) -> None:
        if self.config.card_cache_path is None:
            return
        path = self.config.card_cache_path
        path.parent.mkdir(parents=True, exist_ok=True)
        cache = {"contract": CARD_CACHE_CONTRACT, "agents": {}}
        if path.exists():
            try:
                loaded = json.loads(path.read_text(encoding="utf-8"))
                if isinstance(loaded, Mapping) and isinstance(loaded.get("agents"), Mapping):
                    cache = {"contract": CARD_CACHE_CONTRACT, "agents": dict(loaded["agents"])}
            except (OSError, json.JSONDecodeError):
                pass
        cache["agents"][evidence.url] = {
            "digest": evidence.digest,
            "retrieved_at": evidence.retrieved_at,
            "interface_url": evidence.interface.url,
            "binding": evidence.interface.binding,
            "protocol_version": evidence.interface.version,
            "action_digest": envelope["action_digest"],
        }
        temp = path.with_suffix(path.suffix + ".tmp")
        try:
            temp.write_bytes(canonical_json(cache) + b"\n")
            os.replace(temp, path)
        except OSError as exc:
            raise AgentCardError(f"cannot persist Agent Card cache: {exc}") from exc

    def _check_authority(self, envelope: Mapping[str, Any]) -> Mapping[str, Any]:
        output = require_mapping(self.authority_checker(envelope), "authority check output")
        if output.get("valid") is not True:
            raise AuthorityError("authority, delegation, revocation or MAL check denied")
        self.receipts.write("AUTHORITY_VERIFIED", {
            "envelope_id": envelope["envelope_id"],
            "action_digest": envelope["action_digest"],
            "principal_id": envelope["source"]["principal_id"],
            "authority_grant_id": envelope["mandate"]["authority_grant_id"],
            "delegation_chain_digest": envelope["mandate"]["delegation_chain_digest"],
            "revocation_registry_ref": envelope["mandate"]["revocation_registry_ref"],
            "mal_profile_id": envelope["target"]["mal_profile_id"],
            "checker_evidence_digest": sha256_hex(output),
        })
        return output

    @staticmethod
    def prepare_payload(envelope: Mapping[str, Any], payload: Mapping[str, Any]) -> dict[str, Any]:
        operation = require_string(envelope.get("operation"), "operation").upper()
        prepared = copy.deepcopy(dict(require_mapping(payload, "a2a_payload")))
        if operation == "SEND_MESSAGE":
            message = prepared.get("message")
            if not isinstance(message, MutableMapping):
                raise A2AClientError("SEND_MESSAGE payload.message must be an object")
            message_id = require_string(message.get("messageId", message.get("message_id")), "message.messageId")
            if message_id != envelope["payload"]["message_id"]:
                raise A2AClientError("A2A message id differs from mandate envelope")
            extensions = message.setdefault("extensions", [])
            if not isinstance(extensions, list) or not all(isinstance(item, str) for item in extensions):
                raise A2AClientError("message.extensions must be a string list")
            if EXTENSION_URI not in extensions:
                extensions.append(EXTENSION_URI)
            metadata = prepared.setdefault("metadata", {})
            if not isinstance(metadata, MutableMapping):
                raise A2AClientError("SEND_MESSAGE metadata must be an object")
            existing = metadata.get(EXTENSION_URI)
            expected = {"contract": ENVELOPE.CONTRACT, "envelope_id": envelope["envelope_id"]}
            if existing is not None and existing != expected:
                raise A2AClientError("existing mandate extension metadata conflicts with envelope")
            metadata[EXTENSION_URI] = expected
        elif operation == "CANCEL_TASK":
            metadata = prepared.setdefault("metadata", {})
            if not isinstance(metadata, MutableMapping):
                raise A2AClientError("CANCEL_TASK metadata must be an object")
            metadata[EXTENSION_URI] = {"contract": ENVELOPE.CONTRACT, "envelope_id": envelope["envelope_id"]}
        return prepared

    def _build_request(self, envelope: Mapping[str, Any], card: AgentCardEvidence, prepared: Mapping[str, Any]) -> tuple[str, str, bytes | None]:
        operation = envelope["operation"].upper()
        base = card.interface.url
        tenant_prefix = f"/{urllib.parse.quote(card.interface.tenant, safe='')}" if card.interface.tenant else ""
        if operation == "SEND_MESSAGE":
            return "POST", f"{base}{tenant_prefix}/message:send", canonical_json(prepared)
        if operation == "GET_TASK":
            task_id = require_string(prepared.get("id"), "a2a_payload.id")
            query = {k: v for k, v in prepared.items() if k not in {"id", "tenant"} and v is not None}
            suffix = "?" + urllib.parse.urlencode(sorted(query.items()), doseq=True) if query else ""
            return "GET", f"{base}{tenant_prefix}/tasks/{urllib.parse.quote(task_id, safe='')}{suffix}", None
        if operation == "LIST_TASKS":
            query = {k: v for k, v in prepared.items() if k != "tenant" and v is not None}
            suffix = "?" + urllib.parse.urlencode(sorted(query.items()), doseq=True) if query else ""
            return "GET", f"{base}{tenant_prefix}/tasks{suffix}", None
        if operation == "CANCEL_TASK":
            task_id = require_string(prepared.get("id"), "a2a_payload.id")
            return "POST", f"{base}{tenant_prefix}/tasks/{urllib.parse.quote(task_id, safe='')}:cancel", canonical_json(prepared)
        if operation in STREAMING_OPERATIONS:
            raise TransportError("streaming A2A operations are fail-closed until governed SSE support is installed")
        raise TransportError("unsupported A2A operation")

    def _headers(self, envelope: Mapping[str, Any], *, has_body: bool) -> dict[str, str]:
        headers = {
            "Accept": "application/json",
            "A2A-Version": A2A_VERSION,
            "A2A-Extensions": EXTENSION_URI,
            "VALO-Mandate-Ref": f"{envelope['envelope_id']}.{envelope['action_digest']}",
            "User-Agent": self.config.user_agent,
        }
        if has_body:
            headers["Content-Type"] = "application/json"
        if self.config.auth_token:
            headers["Authorization"] = f"{self.config.auth_scheme} {self.config.auth_token}"
        return headers

    def _inspect_response(self, envelope: Mapping[str, Any], raw: bytes) -> dict[str, Any]:
        if len(raw) > self.config.max_artifact_bytes:
            raise ArtifactInspectionError("A2A response exceeds artifact inspection limit")
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise ArtifactInspectionError("A2A response is not valid JSON") from exc
        texts: list[str] = []
        urls: list[str] = []
        artifacts: list[dict[str, Any]] = []
        task_states: list[str] = []

        def walk(value: Any, path: str = "$") -> None:
            if isinstance(value, Mapping):
                if "artifactId" in value or "artifact_id" in value:
                    artifact_id = value.get("artifactId", value.get("artifact_id"))
                    artifacts.append({
                        "artifact_id": artifact_id,
                        "path": path,
                        "digest": sha256_hex(value),
                        "size_bytes": len(canonical_json(value)),
                    })
                state = value.get("state")
                if isinstance(state, str) and state.startswith("TASK_STATE_"):
                    task_states.append(state)
                for key, item in value.items():
                    if key in {"text", "description", "name"} and isinstance(item, str):
                        texts.append(item)
                    if key == "url" and isinstance(item, str):
                        urls.append(item)
                    walk(item, f"{path}.{key}")
            elif isinstance(value, list):
                for index, item in enumerate(value):
                    walk(item, f"{path}[{index}]")

        walk(payload)
        combined = "\n".join(texts)
        for pattern in PROMPT_INJECTION_PATTERNS:
            if pattern.search(combined):
                raise ArtifactInspectionError("returned A2A content matches prompt-injection policy")
        for name, pattern in SECRET_PATTERNS:
            if pattern.search(combined):
                raise ArtifactInspectionError(f"returned A2A content contains secret material: {name}")
        unsafe_urls: list[str] = []
        for url in urls:
            try:
                parsed = urllib.parse.urlparse(url)
                if parsed.scheme != "https" or parsed.username or parsed.password or not parsed.netloc:
                    unsafe_urls.append(url)
            except ValueError:
                unsafe_urls.append(url)
        if unsafe_urls:
            raise ArtifactInspectionError("returned A2A artifacts contain unsafe file URLs")
        inspection = {
            "response_digest": sha256_hex_bytes(raw),
            "response_size_bytes": len(raw),
            "artifact_digests": artifacts,
            "task_states": sorted(set(task_states)),
            "terminal_transport_state_observed": any(state in TERMINAL_TASK_STATES for state in task_states),
            "local_execution_authorized": False,
            "requires_new_reht_before_local_consequence": True,
            "semantic_integrity": {
                "original_response_preserved": True,
                "language_transformed": False,
                "provenance_target_agent_id": envelope["target"]["agent_id"],
            },
        }
        self.receipts.write("A2A_RESPONSE_INSPECTED", {
            "envelope_id": envelope["envelope_id"],
            "action_digest": envelope["action_digest"],
            **inspection,
        })
        return {"payload": payload, "inspection": inspection}

    def execute(self, request: Mapping[str, Any]) -> dict[str, Any]:
        require_mapping(request, "request")
        if request.get("contract") != CLIENT_REQUEST_CONTRACT:
            raise A2AClientError(f"contract must be {CLIENT_REQUEST_CONTRACT}")
        request_id = require_string(request.get("request_id"), "request_id")
        envelope = require_mapping(request.get("envelope"), "envelope")
        payload = require_mapping(request.get("a2a_payload"), "a2a_payload")
        if envelope.get("operation") in STREAMING_OPERATIONS:
            raise TransportError("streaming A2A operations are not enabled in governed v1 adapter")
        if envelope.get("operation") not in SUPPORTED_OPERATIONS:
            raise TransportError("operation is unsupported by governed HTTP+JSON adapter")

        validation = ENVELOPE.validate(envelope)
        if not validation["transmittable"]:
            self.receipts.write("A2A_TRANSMISSION_DENIED", {
                "request_id": request_id,
                "envelope_id": envelope.get("envelope_id"),
                "action_digest": envelope.get("action_digest"),
                "reason": validation["reason"],
            })
            raise AuthorityError(f"mandate envelope is not transmittable: {validation['reason']}")

        prepared = self.prepare_payload(envelope, payload)
        payload_digest = sha256_hex(prepared)
        expected_payload_digest = require_digest(envelope["payload"]["a2a_payload_digest"], "payload.a2a_payload_digest")
        if not hmac.compare_digest(payload_digest, expected_payload_digest):
            raise A2AClientError("exact prepared A2A payload differs from cleared payload digest")

        self._check_authority(envelope)
        card = self.fetch_agent_card(envelope)
        method, url, body = self._build_request(envelope, card, prepared)
        headers = self._headers(envelope, has_body=body is not None)
        wire_request_digest = sha256_hex({
            "method": method,
            "url": url,
            "header_names": sorted(name.lower() for name in headers),
            "body_sha256": sha256_hex_bytes(body or b""),
            "body_size_bytes": len(body or b""),
        })
        self.receipts.write("A2A_OUTBOUND_AUTHORIZED", {
            "request_id": request_id,
            "envelope_id": envelope["envelope_id"],
            "action_digest": envelope["action_digest"],
            "a2a_payload_digest": payload_digest,
            "wire_request_digest": wire_request_digest,
            "operation": envelope["operation"],
            "binding": card.interface.binding,
            "protocol_version": card.interface.version,
            "target_url": url,
            "racs_decision_id": envelope["governance"]["racs"]["decision_id"],
            "reht_clearance_id": envelope["governance"]["reht"]["clearance_id"],
        })

        current_digest = sha256_hex(prepared)
        if not hmac.compare_digest(current_digest, expected_payload_digest):
            raise A2AClientError("A2A payload changed after authorization")
        status, response_headers, raw = self._request(method, url, headers, body, self.config.max_response_bytes)
        if status < 200 or status >= 300:
            raise TransportError(f"A2A endpoint returned non-success status {status}")
        content_type = str(response_headers.get("Content-Type", response_headers.get("content-type", ""))).lower()
        if content_type and "json" not in content_type:
            raise ArtifactInspectionError("A2A response content type must be JSON")
        inspected = self._inspect_response(envelope, raw)
        response_digest = inspected["inspection"]["response_digest"]
        self.receipts.write("A2A_OPERATION_COMPLETED", {
            "request_id": request_id,
            "envelope_id": envelope["envelope_id"],
            "action_digest": envelope["action_digest"],
            "operation": envelope["operation"],
            "http_status": status,
            "response_digest": response_digest,
            "response_content_type": response_headers.get("Content-Type", response_headers.get("content-type")),
            "local_execution_authorized": False,
        })
        return {
            "contract": CLIENT_RESULT_CONTRACT,
            "request_id": request_id,
            "envelope_id": envelope["envelope_id"],
            "action_digest": envelope["action_digest"],
            "operation": envelope["operation"],
            "http_status": status,
            "response": inspected["payload"],
            "inspection": inspected["inspection"],
            "receipt_chain_head": self.receipts.previous_chain_hash,
        }


def prepare_payload_and_digest(envelope: Mapping[str, Any], payload: Mapping[str, Any]) -> dict[str, Any]:
    prepared = GovernedA2AClient.prepare_payload(envelope, payload)
    return {"a2a_payload": prepared, "a2a_payload_digest": sha256_hex(prepared)}
