"""Governed local camera privacy pipeline for LastSeen."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
from typing import Any, Iterable, Protocol, Sequence
from uuid import uuid4

from PIL import Image
import yaml

from valo_edge.contracts import EdgeActionProposal, EdgeDecision, OfflineAuthorityEnvelope
from valo_edge.lastseen.service import LastSeenResult, LastSeenService


_CAMERA_ACTIONS = ["PERSIST_OBJECT_CROP", "DELETE_OBJECT_CROP"]
_PERSON_LABELS = frozenset({"person", "human", "people"})


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _canonical_json(payload: Any) -> bytes:
    return json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")


def _digest(payload: Any) -> str:
    if isinstance(payload, bytes):
        data = payload
    else:
        data = _canonical_json(payload)
    return hashlib.sha256(data).hexdigest()


def _normalize_label(value: str) -> str:
    return " ".join(value.strip().lower().split())


@dataclass(frozen=True)
class BoundingBox:
    x_min: int
    y_min: int
    x_max: int
    y_max: int

    @property
    def width(self) -> int:
        return self.x_max - self.x_min

    @property
    def height(self) -> int:
        return self.y_max - self.y_min

    @property
    def area(self) -> int:
        return max(0, self.width) * max(0, self.height)

    @property
    def center(self) -> tuple[float, float]:
        return ((self.x_min + self.x_max) / 2.0, (self.y_min + self.y_max) / 2.0)

    def validate(self, frame_width: int, frame_height: int) -> "BoundingBox":
        if self.x_min < 0 or self.y_min < 0:
            raise ValueError("bounding box coordinates must be non-negative")
        if self.x_max <= self.x_min or self.y_max <= self.y_min:
            raise ValueError("bounding box must have positive area")
        if self.x_max > frame_width or self.y_max > frame_height:
            raise ValueError("bounding box exceeds frame dimensions")
        return self

    def intersects(self, other: "BoundingBox") -> bool:
        return not (
            self.x_max <= other.x_min
            or other.x_max <= self.x_min
            or self.y_max <= other.y_min
            or other.y_max <= self.y_min
        )

    def as_tuple(self) -> tuple[int, int, int, int]:
        return (self.x_min, self.y_min, self.x_max, self.y_max)


@dataclass(frozen=True)
class ObjectDetection:
    label: str
    bounding_box: BoundingBox
    confidence: float
    detection_id: str
    aliases: tuple[str, ...] = ()

    def validate(self, frame_width: int, frame_height: int) -> "ObjectDetection":
        if not self.label.strip():
            raise ValueError("detection label must not be empty")
        if not self.detection_id.strip():
            raise ValueError("detection_id must not be empty")
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError("detection confidence must be between 0 and 1")
        self.bounding_box.validate(frame_width, frame_height)
        return self


@dataclass
class CameraFrame:
    camera_id: str
    timestamp_iso: str
    width: int
    height: int
    pixels: bytearray
    mode: str = "RGB"
    source_digest: str = field(init=False)
    disposed: bool = field(default=False, init=False)

    def __post_init__(self) -> None:
        if not self.camera_id.strip():
            raise ValueError("camera_id must not be empty")
        if self.mode != "RGB":
            raise ValueError("only RGB frames are supported")
        if self.width <= 0 or self.height <= 0:
            raise ValueError("frame dimensions must be positive")
        expected = self.width * self.height * 3
        if len(self.pixels) != expected:
            raise ValueError(f"RGB frame requires {expected} bytes, got {len(self.pixels)}")
        self.source_digest = _digest(bytes(self.pixels))

    @classmethod
    def from_image(
        cls,
        image_path: str | Path,
        *,
        camera_id: str,
        timestamp_iso: str,
    ) -> "CameraFrame":
        with Image.open(image_path) as image:
            rgb = image.convert("RGB")
            try:
                width, height = rgb.size
                pixels = bytearray(rgb.tobytes())
            finally:
                rgb.close()
        return cls(
            camera_id=camera_id,
            timestamp_iso=timestamp_iso,
            width=width,
            height=height,
            pixels=pixels,
        )

    def crop(self, box: BoundingBox) -> tuple[bytes, tuple[int, int]]:
        if self.disposed:
            raise RuntimeError("raw frame has already been disposed")
        box.validate(self.width, self.height)
        row_bytes = self.width * 3
        crop_row_bytes = box.width * 3
        cropped = bytearray(box.width * box.height * 3)
        destination = 0
        for y in range(box.y_min, box.y_max):
            source = y * row_bytes + box.x_min * 3
            cropped[destination : destination + crop_row_bytes] = self.pixels[
                source : source + crop_row_bytes
            ]
            destination += crop_row_bytes
        return bytes(cropped), (box.width, box.height)

    def zeroize(self) -> "RawFrameDisposalReceipt":
        if not self.disposed:
            self.pixels[:] = b"\x00" * len(self.pixels)
            self.disposed = True
        zeroized_digest = _digest(bytes(self.pixels))
        verified = self.disposed and not any(self.pixels)
        disposed_at_iso = _utc_now_iso()
        receipt_digest = _digest(
            {
                "camera_id": self.camera_id,
                "frame_digest": self.source_digest,
                "zeroized_digest": zeroized_digest,
                "byte_length": len(self.pixels),
                "verified": verified,
                "disposed_at_iso": disposed_at_iso,
            }
        )
        return RawFrameDisposalReceipt(
            camera_id=self.camera_id,
            frame_digest=self.source_digest,
            zeroized_digest=zeroized_digest,
            byte_length=len(self.pixels),
            verified=verified,
            disposed_at_iso=disposed_at_iso,
            receipt_digest=receipt_digest,
        )


@dataclass(frozen=True)
class ZoneDefinition:
    camera_id: str
    zone_id: str
    location: str
    bounding_box: BoundingBox

    def contains_center(self, box: BoundingBox) -> bool:
        x, y = box.center
        return (
            self.bounding_box.x_min <= x < self.bounding_box.x_max
            and self.bounding_box.y_min <= y < self.bounding_box.y_max
        )


class ZoneMap:
    def __init__(self, zones: Iterable[ZoneDefinition]) -> None:
        self._zones = tuple(
            sorted(zones, key=lambda zone: (zone.camera_id, zone.zone_id))
        )
        if not self._zones:
            raise ValueError("zone map must contain at least one zone")

    @classmethod
    def from_yaml(cls, path: str | Path) -> "ZoneMap":
        payload = yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}
        cameras = payload.get("cameras")
        if not isinstance(cameras, dict):
            raise ValueError("zone YAML must contain a cameras mapping")
        zones: list[ZoneDefinition] = []
        for camera_id, camera_payload in cameras.items():
            if not isinstance(camera_payload, dict):
                raise ValueError(f"camera {camera_id!r} must be a mapping")
            entries = camera_payload.get("zones", [])
            if not isinstance(entries, list):
                raise ValueError(f"camera {camera_id!r} zones must be a list")
            for entry in entries:
                if not isinstance(entry, dict):
                    raise ValueError("zone entry must be a mapping")
                coordinates = entry.get("box")
                if not isinstance(coordinates, list) or len(coordinates) != 4:
                    raise ValueError("zone box must contain four integers")
                zones.append(
                    ZoneDefinition(
                        camera_id=str(camera_id),
                        zone_id=str(entry["id"]),
                        location=str(entry["location"]),
                        bounding_box=BoundingBox(*(int(value) for value in coordinates)),
                    )
                )
        return cls(zones)

    def resolve(self, camera_id: str, box: BoundingBox) -> ZoneDefinition | None:
        matches = [
            zone
            for zone in self._zones
            if zone.camera_id == camera_id and zone.contains_center(box)
        ]
        if not matches:
            return None
        return matches[0]


class DetectorAdapter(Protocol):
    detector_id: str

    def open_frame(self) -> CameraFrame: ...

    def detect(self, frame: CameraFrame) -> Sequence[ObjectDetection]: ...


class ReplayDetectorAdapter:
    """Deterministic adapter for replaying recorded detector outputs locally."""

    def __init__(
        self,
        *,
        replay_path: Path,
        image_path: Path,
        camera_id: str,
        timestamp_iso: str,
        detector_id: str,
        detections: Sequence[ObjectDetection],
    ) -> None:
        self.replay_path = replay_path
        self.image_path = image_path
        self.camera_id = camera_id
        self.timestamp_iso = timestamp_iso
        self.detector_id = detector_id
        self._detections = tuple(detections)

    @classmethod
    def from_json(cls, path: str | Path) -> "ReplayDetectorAdapter":
        replay_path = Path(path)
        payload = json.loads(replay_path.read_text(encoding="utf-8"))
        image_path = Path(payload["image"])
        if not image_path.is_absolute():
            image_path = replay_path.parent / image_path
        detections = []
        for index, entry in enumerate(payload.get("detections", [])):
            box = entry.get("bounding_box")
            if not isinstance(box, list) or len(box) != 4:
                raise ValueError("replay detection bounding_box must contain four integers")
            aliases = entry.get("aliases", [])
            if isinstance(aliases, str):
                aliases = [aliases]
            detections.append(
                ObjectDetection(
                    label=str(entry["object_name"]),
                    bounding_box=BoundingBox(*(int(value) for value in box)),
                    confidence=float(entry.get("confidence", 1.0)),
                    detection_id=str(entry.get("detection_id", f"detection-{index:04d}")),
                    aliases=tuple(str(alias) for alias in aliases),
                )
            )
        return cls(
            replay_path=replay_path,
            image_path=image_path,
            camera_id=str(payload["camera_id"]),
            timestamp_iso=str(payload["frame_timestamp_iso"]),
            detector_id=str(payload.get("detector_id", "replay-detector-v1")),
            detections=detections,
        )

    def open_frame(self) -> CameraFrame:
        return CameraFrame.from_image(
            self.image_path,
            camera_id=self.camera_id,
            timestamp_iso=self.timestamp_iso,
        )

    def detect(self, frame: CameraFrame) -> Sequence[ObjectDetection]:
        if frame.camera_id != self.camera_id:
            raise ValueError("replay frame camera_id mismatch")
        return self._detections


@dataclass(frozen=True)
class CropArtifact:
    source_id: str
    path: str
    crop_digest: str
    width: int
    height: int
    created: bool
    receipt_digest: str


class LocalCropStore:
    """Local atomic PNG crop store. Raw frames are never accepted by this API."""

    def __init__(self, root: str | Path) -> None:
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self._resolved_root = self.root.resolve()

    def persist(
        self,
        *,
        source_id: str,
        crop_bytes: bytes,
        size: tuple[int, int],
    ) -> tuple[str, str, bool]:
        width, height = size
        expected = width * height * 3
        if len(crop_bytes) != expected:
            raise ValueError(f"crop requires {expected} RGB bytes, got {len(crop_bytes)}")
        crop_digest = _digest(crop_bytes)
        filename = f"{source_id}-{crop_digest[:16]}.png"
        destination = self.root / filename
        if destination.exists():
            with Image.open(destination) as existing:
                rgb = existing.convert("RGB")
                try:
                    if rgb.size != size or _digest(rgb.tobytes()) != crop_digest:
                        raise RuntimeError("existing crop artifact failed integrity verification")
                finally:
                    rgb.close()
            return str(destination), crop_digest, False
        temporary = self.root / f".{filename}.{uuid4().hex}.tmp"
        image = Image.frombytes("RGB", size, crop_bytes)
        try:
            image.save(temporary, format="PNG")
            os.replace(temporary, destination)
        finally:
            image.close()
            if temporary.exists():
                temporary.unlink()
        return str(destination), crop_digest, True

    def delete(self, path: str | Path) -> bool:
        candidate = Path(path).resolve()
        if not candidate.is_relative_to(self._resolved_root):
            raise ValueError("crop path is outside the configured crop store")
        if not candidate.exists():
            return False
        candidate.unlink()
        return True


@dataclass(frozen=True)
class RejectedDetection:
    detection_id: str
    label: str
    reason: str


@dataclass(frozen=True)
class RawFrameDisposalReceipt:
    camera_id: str
    frame_digest: str
    zeroized_digest: str
    byte_length: int
    verified: bool
    disposed_at_iso: str
    receipt_digest: str


@dataclass(frozen=True)
class CameraBatchResult:
    observations: tuple[LastSeenResult, ...]
    rejected: tuple[RejectedDetection, ...]
    disposal_receipt: RawFrameDisposalReceipt


class CameraPrivacyPipeline:
    """Fail-closed camera-to-memory pipeline with governed crop consequences."""

    def __init__(
        self,
        service: LastSeenService,
        crop_store: LocalCropStore,
        zone_map: ZoneMap,
        *,
        device_id: str = "lastseen-camera-pipeline-01",
        minimum_confidence: float = 0.5,
    ) -> None:
        if not 0.0 <= minimum_confidence <= 1.0:
            raise ValueError("minimum_confidence must be between 0 and 1")
        self.service = service
        self.crop_store = crop_store
        self.zone_map = zone_map
        self.device_id = device_id
        self.minimum_confidence = minimum_confidence
        self._engine = service.engine
        self._gateway = service.gateway

    def _proposal(
        self,
        action_type: str,
        parameters: dict[str, Any],
        timestamp_iso: str,
    ) -> EdgeActionProposal:
        return EdgeActionProposal(
            proposal_id=f"lastseen-camera-{uuid4().hex[:16]}",
            device_id=self.device_id,
            action_type=action_type,
            parameters=parameters,
            timestamp_iso=timestamp_iso,
            nonce=uuid4().hex,
        )

    def _authorize(self, proposal: EdgeActionProposal, timestamp_iso: str):
        envelope = OfflineAuthorityEnvelope(
            envelope_id=f"lastseen-camera-envelope-{self.device_id}",
            device_id=self.device_id,
            allowed_action_types=list(_CAMERA_ACTIONS),
            max_rate_per_sec=50.0,
            valid_until_iso="2099-12-31T23:59:59Z",
            is_revoked=False,
        )
        clearance = self._engine.evaluate_proposal(proposal, envelope, timestamp_iso)
        if clearance.decision is not EdgeDecision.ALLOW:
            receipt = self._gateway.execute_action(proposal, clearance, timestamp_iso)
            raise PermissionError(f"{clearance.reason} receipt={receipt.receipt_digest}")
        return clearance

    def _source_id(
        self,
        frame: CameraFrame,
        detection: ObjectDetection,
        detector_id: str,
    ) -> str:
        digest = _digest(
            {
                "camera_id": frame.camera_id,
                "frame_digest": frame.source_digest,
                "frame_timestamp_iso": frame.timestamp_iso,
                "detector_id": detector_id,
                "detection_id": detection.detection_id,
                "label": _normalize_label(detection.label),
                "bounding_box": detection.bounding_box.as_tuple(),
            }
        )
        return f"camera-observation-{digest[:32]}"

    def _persist_crop(
        self,
        *,
        source_id: str,
        frame: CameraFrame,
        detection: ObjectDetection,
        zone: ZoneDefinition,
    ) -> CropArtifact:
        crop_bytes, size = frame.crop(detection.bounding_box)
        crop_digest = _digest(crop_bytes)
        proposal = self._proposal(
            "PERSIST_OBJECT_CROP",
            {
                "source_id": source_id,
                "camera_id": frame.camera_id,
                "zone_id": zone.zone_id,
                "bounding_box": detection.bounding_box.as_tuple(),
                "crop_digest": crop_digest,
                "raw_frame_persisted": False,
            },
            frame.timestamp_iso,
        )
        clearance = self._authorize(proposal, frame.timestamp_iso)
        path, persisted_digest, created = self.crop_store.persist(
            source_id=source_id,
            crop_bytes=crop_bytes,
            size=size,
        )
        receipt = self._gateway.execute_action(proposal, clearance, frame.timestamp_iso)
        return CropArtifact(
            source_id=source_id,
            path=path,
            crop_digest=persisted_digest,
            width=size[0],
            height=size[1],
            created=created,
            receipt_digest=receipt.receipt_digest or "",
        )

    def _compensate_crop(self, artifact: CropArtifact, timestamp_iso: str) -> str:
        if not artifact.created:
            return ""
        proposal = self._proposal(
            "DELETE_OBJECT_CROP",
            {
                "source_id": artifact.source_id,
                "crop_digest": artifact.crop_digest,
                "path_digest": _digest(artifact.path),
                "reason": "memory-store-failed",
            },
            timestamp_iso,
        )
        clearance = self._authorize(proposal, timestamp_iso)
        self.crop_store.delete(artifact.path)
        receipt = self._gateway.execute_action(proposal, clearance, timestamp_iso)
        return receipt.receipt_digest or ""

    def process(
        self,
        frame: CameraFrame,
        detections: Sequence[ObjectDetection],
        *,
        detector_id: str,
    ) -> CameraBatchResult:
        observations: list[LastSeenResult] = []
        rejected: list[RejectedDetection] = []
        disposal_receipt: RawFrameDisposalReceipt | None = None
        try:
            validated = [
                detection.validate(frame.width, frame.height)
                for detection in detections
            ]
            person_boxes = [
                detection.bounding_box
                for detection in validated
                if _normalize_label(detection.label) in _PERSON_LABELS
            ]
            for detection in sorted(validated, key=lambda item: item.detection_id):
                label = _normalize_label(detection.label)
                if label in _PERSON_LABELS:
                    rejected.append(
                        RejectedDetection(
                            detection_id=detection.detection_id,
                            label=detection.label,
                            reason="person-detection-excluded",
                        )
                    )
                    continue
                if detection.confidence < self.minimum_confidence:
                    rejected.append(
                        RejectedDetection(
                            detection_id=detection.detection_id,
                            label=detection.label,
                            reason="below-minimum-confidence",
                        )
                    )
                    continue
                if any(detection.bounding_box.intersects(box) for box in person_boxes):
                    rejected.append(
                        RejectedDetection(
                            detection_id=detection.detection_id,
                            label=detection.label,
                            reason="person-overlap-fail-closed",
                        )
                    )
                    continue
                zone = self.zone_map.resolve(frame.camera_id, detection.bounding_box)
                if zone is None:
                    rejected.append(
                        RejectedDetection(
                            detection_id=detection.detection_id,
                            label=detection.label,
                            reason="no-authorized-zone",
                        )
                    )
                    continue

                source_id = self._source_id(frame, detection, detector_id)
                artifact: CropArtifact | None = None
                try:
                    artifact = self._persist_crop(
                        source_id=source_id,
                        frame=frame,
                        detection=detection,
                        zone=zone,
                    )
                    metadata = {
                        "detector_id": detector_id,
                        "detection_id": detection.detection_id,
                        "bounding_box": list(detection.bounding_box.as_tuple()),
                        "frame_digest": frame.source_digest,
                        "crop_digest": artifact.crop_digest,
                        "crop_receipt_digest": artifact.receipt_digest,
                        "raw_frame_persisted": False,
                        "person_filter": "exclude-and-overlap-reject-v1",
                    }
                    observation = self.service.remember(
                        detection.label,
                        zone.location,
                        image_ref=artifact.path,
                        confidence=detection.confidence,
                        observed_at_iso=frame.timestamp_iso,
                        metadata=metadata,
                        source_id=source_id,
                        source_type="camera-observation",
                        source_device_id=frame.camera_id,
                        camera_id=frame.camera_id,
                        zone_id=zone.zone_id,
                        aliases=detection.aliases,
                    )
                    observations.append(observation)
                except Exception as exc:
                    compensation = ""
                    if artifact is not None:
                        try:
                            compensation = self._compensate_crop(
                                artifact,
                                frame.timestamp_iso,
                            )
                        except Exception as compensation_exc:
                            compensation = f"compensation-failed:{type(compensation_exc).__name__}"
                    suffix = f";{compensation}" if compensation else ""
                    rejected.append(
                        RejectedDetection(
                            detection_id=detection.detection_id,
                            label=detection.label,
                            reason=f"memory-store-failed:{type(exc).__name__}{suffix}",
                        )
                    )
        finally:
            disposal_receipt = frame.zeroize()

        return CameraBatchResult(
            observations=tuple(observations),
            rejected=tuple(rejected),
            disposal_receipt=disposal_receipt,
        )

    def process_adapter(self, adapter: DetectorAdapter) -> CameraBatchResult:
        frame = adapter.open_frame()
        try:
            detections = adapter.detect(frame)
        except Exception:
            frame.zeroize()
            raise
        return self.process(frame, detections, detector_id=adapter.detector_id)
