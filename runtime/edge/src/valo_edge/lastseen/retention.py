"""Governed retention and complete crop deletion for LastSeen.

Retention is deliberately separate from perception and memory retrieval. It
coordinates already-governed LastSeen memory deletion with separately governed
filesystem consequences for camera crops. No model is involved.
"""

from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import hashlib
import hmac
import json
import os
from pathlib import Path
from typing import Any, Protocol, Sequence
from uuid import uuid4

from valo_edge.contracts import EdgeActionProposal, EdgeDecision, OfflineAuthorityEnvelope
from valo_edge.gateway import HardwareNeutralGateway
from valo_edge.runtime import MicroRehtEngine
from valo_edge.lastseen.service import LastSeenService


_RETENTION_ACTIONS = [
    "STAGE_OBJECT_CROP_DELETE",
    "COMMIT_OBJECT_CROP_DELETE",
    "FINALIZE_OBJECT_CROP_DELETE",
    "RESTORE_OBJECT_CROP",
]


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _canonical_iso(value: str) -> str:
    candidate = value.strip()
    if not candidate:
        raise ValueError("timestamp must not be empty")
    parsed = datetime.fromisoformat(candidate.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("timestamp must include a timezone")
    return parsed.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _sha256_text(value: str) -> str:
    return _sha256_bytes(value.encode("utf-8"))


def _file_digest(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while True:
            chunk = handle.read(1024 * 1024)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


def _normalize_subject(value: str) -> str:
    normalized = " ".join(value.strip().lower().split())
    if not normalized:
        raise ValueError("object_name must not be empty")
    return normalized


class RetentionMemory(Protocol):
    """Minimal LastSeen memory boundary consumed by retention."""

    def history(self, object_name: str, *, limit: int = 100) -> Sequence[Any]: ...

    def forget_with_receipt(self, object_name: str) -> Any: ...


@dataclass(frozen=True)
class CropRetentionReceipt:
    action_type: str
    path_digest: str
    content_digest: str
    receipt_digest: str
    timestamp_iso: str


@dataclass(frozen=True)
class MissingCropEvidence:
    path_digest: str
    source_ids_digest: str


@dataclass(frozen=True)
class RetentionResult:
    status: str
    subject_digest: str
    cutoff_iso: str | None
    observations_considered: int
    deleted_observations: int
    crops_deleted: int
    crops_missing: int
    memory_receipt_digest: str
    crop_receipts: tuple[CropRetentionReceipt, ...]
    missing_crops: tuple[MissingCropEvidence, ...]

    @property
    def complete(self) -> bool:
        return self.status in {"DELETED", "DELETED_WITH_MISSING_CROPS", "NO_MATCH"}


@dataclass(frozen=True)
class _CropRef:
    original: Path
    relative_path: str
    path_digest: str
    source_ids: tuple[str, ...]


@dataclass
class _StagedCrop:
    ref: _CropRef
    staged: Path
    committed: Path | None
    content_digest: str
    stage_receipt: CropRetentionReceipt


class RetentionScopeError(RuntimeError):
    """Retention cannot prove that its deletion scope is complete."""


class RetentionCompensationError(RuntimeError):
    """Memory deletion failed and at least one staged crop could not be restored."""


class GovernedRetentionService:
    """Coordinate retention with separate authorization for every mutation."""

    def __init__(
        self,
        memory: RetentionMemory,
        crop_root: str | Path,
        *,
        device_id: str = "lastseen-retention-01",
        subject_salt: bytes | None = None,
        max_history: int = 1000,
    ) -> None:
        if max_history < 2 or max_history > 1000:
            raise ValueError("max_history must be between 2 and 1000")
        self.memory = memory
        self.crop_root = Path(crop_root).expanduser().resolve()
        self.crop_root.mkdir(parents=True, exist_ok=True)
        self.quarantine_root = self.crop_root / ".retention-quarantine"
        self.quarantine_root.mkdir(parents=True, exist_ok=True)
        self.device_id = device_id
        self.subject_salt = subject_salt or os.urandom(32)
        self.max_history = max_history
        self._engine = MicroRehtEngine()
        self._gateway = HardwareNeutralGateway()

    def _subject_digest(self, object_name: str) -> str:
        normalized = _normalize_subject(object_name)
        return hmac.new(self.subject_salt, normalized.encode("utf-8"), hashlib.sha256).hexdigest()

    def _proposal(
        self,
        action_type: str,
        parameters: dict[str, Any],
        timestamp_iso: str,
    ) -> EdgeActionProposal:
        return EdgeActionProposal(
            proposal_id=f"retention-{uuid4().hex[:16]}",
            device_id=self.device_id,
            action_type=action_type,
            parameters=parameters,
            timestamp_iso=timestamp_iso,
            nonce=uuid4().hex,
        )

    def _authorize(
        self,
        action_type: str,
        parameters: dict[str, Any],
        timestamp_iso: str,
    ):
        proposal = self._proposal(action_type, parameters, timestamp_iso)
        envelope = OfflineAuthorityEnvelope(
            envelope_id=f"lastseen-retention-envelope-{self.device_id}",
            device_id=self.device_id,
            allowed_action_types=list(_RETENTION_ACTIONS),
            max_rate_per_sec=100.0,
            valid_until_iso="2099-12-31T23:59:59Z",
            is_revoked=False,
        )
        clearance = self._engine.evaluate_proposal(proposal, envelope, timestamp_iso)
        if clearance.decision is not EdgeDecision.ALLOW:
            receipt = self._gateway.execute_action(proposal, clearance, timestamp_iso)
            raise PermissionError(f"{clearance.reason} receipt={receipt.receipt_digest}")
        return proposal, clearance

    def _complete(
        self,
        action_type: str,
        proposal: EdgeActionProposal,
        clearance: Any,
        *,
        path_digest: str,
        content_digest: str,
        timestamp_iso: str,
    ) -> CropRetentionReceipt:
        receipt = self._gateway.execute_action(proposal, clearance, timestamp_iso)
        return CropRetentionReceipt(
            action_type=action_type,
            path_digest=path_digest,
            content_digest=content_digest,
            receipt_digest=receipt.receipt_digest or "",
            timestamp_iso=timestamp_iso,
        )

    def _history(self, object_name: str) -> tuple[Any, ...]:
        # LastSeen's public history contract is intentionally bounded at 1000.
        # Reaching our configured cap is therefore ambiguous: there may be more
        # source rows. Retention fails closed instead of deleting a partial scope.
        rows = tuple(self.memory.history(object_name, limit=self.max_history))
        if len(rows) >= self.max_history:
            raise RetentionScopeError(
                f"history reached max_history={self.max_history}; refusing incomplete deletion scope"
            )
        return rows

    def _resolve_crop(self, image_ref: str) -> tuple[Path, str]:
        candidate = Path(image_ref).expanduser()
        if not candidate.is_absolute():
            candidate = self.crop_root / candidate
        resolved = candidate.resolve(strict=False)
        try:
            relative = resolved.relative_to(self.crop_root)
        except ValueError as exc:
            raise RetentionScopeError("crop path escapes configured crop root") from exc
        if relative.parts and relative.parts[0] == ".retention-quarantine":
            raise RetentionScopeError("source crop points into retention quarantine")
        return resolved, relative.as_posix()

    def _collect_crop_refs(self, rows: Sequence[Any]) -> tuple[_CropRef, ...]:
        grouped: dict[str, dict[str, Any]] = {}
        for row in rows:
            image_ref = getattr(row, "image_ref", None)
            if not image_ref:
                continue
            path, relative = self._resolve_crop(str(image_ref))
            source_id = str(getattr(row, "source_id", "") or "")
            item = grouped.setdefault(relative, {"path": path, "source_ids": set()})
            if source_id:
                item["source_ids"].add(source_id)
        refs = []
        for relative in sorted(grouped):
            item = grouped[relative]
            refs.append(
                _CropRef(
                    original=item["path"],
                    relative_path=relative,
                    path_digest=_sha256_text(relative),
                    source_ids=tuple(sorted(item["source_ids"])),
                )
            )
        return tuple(refs)

    def _stage(
        self,
        ref: _CropRef,
        subject_digest: str,
    ) -> _StagedCrop | MissingCropEvidence:
        if not ref.original.exists():
            return MissingCropEvidence(
                path_digest=ref.path_digest,
                source_ids_digest=_sha256_text("\n".join(ref.source_ids)),
            )
        if not ref.original.is_file():
            raise RetentionScopeError("crop reference is not a regular file")
        content_digest = _file_digest(ref.original)
        staged = self.quarantine_root / f"{ref.path_digest}-{content_digest}.staged"
        if staged.exists():
            raise RetentionScopeError("existing staged crop requires explicit recovery")
        timestamp_iso = _utc_now_iso()
        parameters = {
            "subject_digest": subject_digest,
            "path_digest": ref.path_digest,
            "content_digest": content_digest,
            "source_ids_digest": _sha256_text("\n".join(ref.source_ids)),
        }
        proposal, clearance = self._authorize(
            "STAGE_OBJECT_CROP_DELETE",
            parameters,
            timestamp_iso,
        )
        os.replace(ref.original, staged)
        stage_receipt = self._complete(
            "STAGE_OBJECT_CROP_DELETE",
            proposal,
            clearance,
            path_digest=ref.path_digest,
            content_digest=content_digest,
            timestamp_iso=timestamp_iso,
        )
        return _StagedCrop(
            ref=ref,
            staged=staged,
            committed=None,
            content_digest=content_digest,
            stage_receipt=stage_receipt,
        )

    def _restore(
        self,
        staged: _StagedCrop,
        subject_digest: str,
    ) -> CropRetentionReceipt:
        if not staged.staged.exists():
            raise RetentionCompensationError("staged crop disappeared before restoration")
        if _file_digest(staged.staged) != staged.content_digest:
            raise RetentionCompensationError("staged crop digest changed before restoration")
        if staged.ref.original.exists():
            raise RetentionCompensationError("original crop path was recreated before restoration")
        timestamp_iso = _utc_now_iso()
        proposal, clearance = self._authorize(
            "RESTORE_OBJECT_CROP",
            {
                "subject_digest": subject_digest,
                "path_digest": staged.ref.path_digest,
                "content_digest": staged.content_digest,
            },
            timestamp_iso,
        )
        staged.ref.original.parent.mkdir(parents=True, exist_ok=True)
        os.replace(staged.staged, staged.ref.original)
        return self._complete(
            "RESTORE_OBJECT_CROP",
            proposal,
            clearance,
            path_digest=staged.ref.path_digest,
            content_digest=staged.content_digest,
            timestamp_iso=timestamp_iso,
        )

    def _commit_delete(
        self,
        staged: _StagedCrop,
        subject_digest: str,
    ) -> CropRetentionReceipt:
        if not staged.staged.exists() or _file_digest(staged.staged) != staged.content_digest:
            raise RetentionScopeError("staged crop missing or mutated before delete commit")
        committed = staged.staged.with_suffix(".delete")
        if committed.exists():
            raise RetentionScopeError("committed deletion artifact already exists")
        timestamp_iso = _utc_now_iso()
        proposal, clearance = self._authorize(
            "COMMIT_OBJECT_CROP_DELETE",
            {
                "subject_digest": subject_digest,
                "path_digest": staged.ref.path_digest,
                "content_digest": staged.content_digest,
            },
            timestamp_iso,
        )
        os.replace(staged.staged, committed)
        staged.committed = committed
        return self._complete(
            "COMMIT_OBJECT_CROP_DELETE",
            proposal,
            clearance,
            path_digest=staged.ref.path_digest,
            content_digest=staged.content_digest,
            timestamp_iso=timestamp_iso,
        )

    def _finalize(
        self,
        staged: _StagedCrop,
        subject_digest: str,
    ) -> CropRetentionReceipt:
        committed = staged.committed
        if committed is None or not committed.exists():
            raise RetentionScopeError("committed crop deletion artifact is missing")
        if _file_digest(committed) != staged.content_digest:
            raise RetentionScopeError("committed crop digest changed before final deletion")
        timestamp_iso = _utc_now_iso()
        proposal, clearance = self._authorize(
            "FINALIZE_OBJECT_CROP_DELETE",
            {
                "subject_digest": subject_digest,
                "path_digest": staged.ref.path_digest,
                "content_digest": staged.content_digest,
            },
            timestamp_iso,
        )
        committed.unlink()
        return self._complete(
            "FINALIZE_OBJECT_CROP_DELETE",
            proposal,
            clearance,
            path_digest=staged.ref.path_digest,
            content_digest=staged.content_digest,
            timestamp_iso=timestamp_iso,
        )

    def delete_object(
        self,
        object_name: str,
        *,
        cutoff_iso: str | None = None,
    ) -> RetentionResult:
        """Delete complete object history plus all referenced crops.

        If ``cutoff_iso`` is supplied, the object is deleted only when its newest
        retained observation is strictly older than the cutoff. A newer or equal
        observation makes the entire operation a no-op.
        """
        subject_digest = self._subject_digest(object_name)
        cutoff = _canonical_iso(cutoff_iso) if cutoff_iso else None
        rows = self._history(object_name)
        if not rows:
            return RetentionResult(
                status="NO_MATCH",
                subject_digest=subject_digest,
                cutoff_iso=cutoff,
                observations_considered=0,
                deleted_observations=0,
                crops_deleted=0,
                crops_missing=0,
                memory_receipt_digest="",
                crop_receipts=(),
                missing_crops=(),
            )

        if cutoff is not None:
            newest = max(
                _canonical_iso(str(getattr(row, "observed_at_iso")))
                for row in rows
            )
            if newest >= cutoff:
                return RetentionResult(
                    status="RETAINED",
                    subject_digest=subject_digest,
                    cutoff_iso=cutoff,
                    observations_considered=len(rows),
                    deleted_observations=0,
                    crops_deleted=0,
                    crops_missing=0,
                    memory_receipt_digest="",
                    crop_receipts=(),
                    missing_crops=(),
                )

        refs = self._collect_crop_refs(rows)
        staged: list[_StagedCrop] = []
        missing: list[MissingCropEvidence] = []
        receipts: list[CropRetentionReceipt] = []

        try:
            for ref in refs:
                result = self._stage(ref, subject_digest)
                if isinstance(result, MissingCropEvidence):
                    missing.append(result)
                else:
                    staged.append(result)
                    receipts.append(result.stage_receipt)

            # Re-read after staging to catch normal concurrent writes before the
            # memory mutation. The existing memory boundary remains authoritative.
            verification_rows = self._history(object_name)
            before_ids = tuple(
                sorted(str(getattr(row, "source_id", "")) for row in rows)
            )
            after_ids = tuple(
                sorted(str(getattr(row, "source_id", "")) for row in verification_rows)
            )
            if before_ids != after_ids:
                raise RetentionScopeError(
                    "object history changed during retention preflight"
                )

            memory_result = self.memory.forget_with_receipt(object_name)
        except Exception as exc:
            restore_errors = []
            for item in reversed(staged):
                if item.staged.exists():
                    try:
                        receipts.append(self._restore(item, subject_digest))
                    except Exception as restore_exc:  # pragma: no cover
                        restore_errors.append(str(restore_exc))
            if restore_errors:
                raise RetentionCompensationError(
                    "memory deletion failed and crop restoration was incomplete: "
                    + "; ".join(restore_errors)
                ) from exc
            raise

        deleted_observations = int(
            getattr(memory_result, "deleted_observations", 0)
        )
        memory_receipt_digest = str(
            getattr(memory_result, "receipt_digest", "") or ""
        )
        if deleted_observations != len(rows):
            # Memory is already mutated. Keep crops quarantined rather than
            # silently finalizing an unproven deletion scope.
            return RetentionResult(
                status="MEMORY_SCOPE_MISMATCH",
                subject_digest=subject_digest,
                cutoff_iso=cutoff,
                observations_considered=len(rows),
                deleted_observations=deleted_observations,
                crops_deleted=0,
                crops_missing=len(missing),
                memory_receipt_digest=memory_receipt_digest,
                crop_receipts=tuple(receipts),
                missing_crops=tuple(missing),
            )

        committed: list[_StagedCrop] = []
        try:
            for item in staged:
                receipts.append(self._commit_delete(item, subject_digest))
                committed.append(item)
            for item in committed:
                receipts.append(self._finalize(item, subject_digest))
        except Exception:
            # Memory deletion is complete. Never restore a crop whose source row is
            # gone. Remaining quarantine artifacts require explicit recovery.
            return RetentionResult(
                status="CROP_FINALIZATION_REQUIRED",
                subject_digest=subject_digest,
                cutoff_iso=cutoff,
                observations_considered=len(rows),
                deleted_observations=deleted_observations,
                crops_deleted=sum(
                    1
                    for item in committed
                    if item.committed is not None and not item.committed.exists()
                ),
                crops_missing=len(missing),
                memory_receipt_digest=memory_receipt_digest,
                crop_receipts=tuple(receipts),
                missing_crops=tuple(missing),
            )

        status = "DELETED_WITH_MISSING_CROPS" if missing else "DELETED"
        return RetentionResult(
            status=status,
            subject_digest=subject_digest,
            cutoff_iso=cutoff,
            observations_considered=len(rows),
            deleted_observations=deleted_observations,
            crops_deleted=len(staged),
            crops_missing=len(missing),
            memory_receipt_digest=memory_receipt_digest,
            crop_receipts=tuple(receipts),
            missing_crops=tuple(missing),
        )


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Governed LastSeen crop retention")
    parser.add_argument("--db", default="lastseen.db")
    parser.add_argument("--crop-root", required=True)
    commands = parser.add_subparsers(dest="command", required=True)
    delete = commands.add_parser(
        "delete",
        help="delete complete object history and crops",
    )
    delete.add_argument("object_name")
    expire = commands.add_parser(
        "expire",
        help="delete only if newest observation is older than cutoff",
    )
    expire.add_argument("object_name")
    expire.add_argument("--before", required=True, dest="cutoff_iso")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    with LastSeenService(args.db) as memory:
        retention = GovernedRetentionService(memory, args.crop_root)
        cutoff = args.cutoff_iso if args.command == "expire" else None
        result = retention.delete_object(args.object_name, cutoff_iso=cutoff)
    print(json.dumps(asdict(result), sort_keys=True, ensure_ascii=False, indent=2))
    return 0 if result.complete or result.status == "RETAINED" else 2


if __name__ == "__main__":
    raise SystemExit(main())
