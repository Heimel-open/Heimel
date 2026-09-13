import json
from pathlib import Path

from PIL import Image
import pytest

from valo_edge.lastseen import LastSeenService
from valo_edge.lastseen.camera import (
    BoundingBox,
    CameraFrame,
    CameraPrivacyPipeline,
    LocalCropStore,
    ObjectDetection,
    ReplayDetectorAdapter,
    ZoneMap,
)


def _write_fixture(tmp_path: Path) -> tuple[Path, Path]:
    image_path = tmp_path / "frame.png"
    Image.new("RGB", (8, 4), (24, 48, 72)).save(image_path)
    zones_path = tmp_path / "zones.yaml"
    zones_path.write_text(
        """cameras:
  kitchen-01:
    zones:
      - id: counter
        location: kitchen counter
        box: [0, 0, 4, 4]
      - id: doorway
        location: kitchen doorway
        box: [4, 0, 8, 4]
""",
        encoding="utf-8",
    )
    replay_path = tmp_path / "replay.json"
    replay_path.write_text(
        json.dumps(
            {
                "image": image_path.name,
                "camera_id": "kitchen-01",
                "frame_timestamp_iso": "2026-08-04T12:00:00Z",
                "detector_id": "deterministic-replay-v1",
                "detections": [
                    {
                        "object_name": "keys",
                        "bounding_box": [0, 0, 2, 2],
                        "confidence": 0.98,
                        "detection_id": "a-keys",
                        "aliases": ["nøkler"],
                    },
                    {
                        "object_name": "person",
                        "bounding_box": [4, 0, 8, 4],
                        "confidence": 0.99,
                        "detection_id": "b-person",
                    },
                    {
                        "object_name": "wallet",
                        "bounding_box": [3, 0, 5, 2],
                        "confidence": 0.95,
                        "detection_id": "c-wallet",
                    },
                ],
            }
        ),
        encoding="utf-8",
    )
    return replay_path, zones_path


def test_camera_pipeline_persists_only_safe_object_crop(tmp_path):
    replay_path, zones_path = _write_fixture(tmp_path)
    adapter = ReplayDetectorAdapter.from_json(replay_path)
    frame = adapter.open_frame()

    with LastSeenService(tmp_path / "lastseen.db") as service:
        pipeline = CameraPrivacyPipeline(
            service,
            LocalCropStore(tmp_path / "crops"),
            ZoneMap.from_yaml(zones_path),
        )
        result = pipeline.process(
            frame,
            adapter.detect(frame),
            detector_id=adapter.detector_id,
        )

        assert service.count() == 1
        assert len(result.observations) == 1
        observation = result.observations[0]
        assert observation.object_name == "keys"
        assert observation.location == "kitchen counter"
        assert observation.camera_id == "kitchen-01"
        assert observation.zone_id == "counter"
        assert observation.metadata["raw_frame_persisted"] is False
        assert len(observation.metadata["crop_receipt_digest"]) == 64
        assert Path(observation.image_ref).exists()
        with Image.open(observation.image_ref) as crop:
            assert crop.size == (2, 2)

        assert [item.reason for item in result.rejected] == [
            "person-detection-excluded",
            "person-overlap-fail-closed",
        ]
        assert frame.disposed is True
        assert not any(frame.pixels)
        assert result.disposal_receipt.verified is True
        assert len(result.disposal_receipt.receipt_digest) == 64


def test_duplicate_replay_does_not_delete_existing_crop(tmp_path):
    replay_path, zones_path = _write_fixture(tmp_path)
    adapter = ReplayDetectorAdapter.from_json(replay_path)

    with LastSeenService(tmp_path / "lastseen.db") as service:
        pipeline = CameraPrivacyPipeline(
            service,
            LocalCropStore(tmp_path / "crops"),
            ZoneMap.from_yaml(zones_path),
        )
        first = pipeline.process_adapter(adapter)
        crop_path = Path(first.observations[0].image_ref)
        assert crop_path.exists()

        second = pipeline.process_adapter(adapter)
        assert service.count() == 1
        assert crop_path.exists()
        assert second.observations == ()
        assert any(item.reason.startswith("memory-store-failed:ValueError") for item in second.rejected)
        assert second.disposal_receipt.verified is True


def test_unknown_zone_and_low_confidence_fail_closed(tmp_path):
    Image.new("RGB", (4, 4), (1, 2, 3)).save(tmp_path / "frame.png")
    (tmp_path / "zones.yaml").write_text(
        """cameras:
  camera-a:
    zones:
      - id: top-left
        location: top left
        box: [0, 0, 2, 2]
""",
        encoding="utf-8",
    )
    frame = CameraFrame.from_image(
        tmp_path / "frame.png",
        camera_id="camera-a",
        timestamp_iso="2026-08-04T12:00:00Z",
    )
    detections = [
        ObjectDetection("remote", BoundingBox(2, 2, 4, 4), 0.99, "remote"),
        ObjectDetection("keys", BoundingBox(0, 0, 1, 1), 0.2, "keys"),
    ]

    with LastSeenService(tmp_path / "lastseen.db") as service:
        pipeline = CameraPrivacyPipeline(
            service,
            LocalCropStore(tmp_path / "crops"),
            ZoneMap.from_yaml(tmp_path / "zones.yaml"),
            minimum_confidence=0.5,
        )
        result = pipeline.process(frame, detections, detector_id="replay")
        assert service.count() == 0
        assert {item.reason for item in result.rejected} == {
            "no-authorized-zone",
            "below-minimum-confidence",
        }
        assert result.disposal_receipt.verified is True


def test_invalid_person_boundary_zeroizes_frame_and_stores_nothing(tmp_path):
    Image.new("RGB", (4, 4), (1, 2, 3)).save(tmp_path / "frame.png")
    (tmp_path / "zones.yaml").write_text(
        """cameras:
  camera-a:
    zones:
      - id: all
        location: room
        box: [0, 0, 4, 4]
""",
        encoding="utf-8",
    )
    frame = CameraFrame.from_image(
        tmp_path / "frame.png",
        camera_id="camera-a",
        timestamp_iso="2026-08-04T12:00:00Z",
    )
    detections = [
        ObjectDetection("keys", BoundingBox(0, 0, 1, 1), 0.9, "keys"),
        ObjectDetection("person", BoundingBox(2, 2, 6, 4), 0.9, "person"),
    ]

    with LastSeenService(tmp_path / "lastseen.db") as service:
        pipeline = CameraPrivacyPipeline(
            service,
            LocalCropStore(tmp_path / "crops"),
            ZoneMap.from_yaml(tmp_path / "zones.yaml"),
        )
        with pytest.raises(ValueError, match="exceeds frame dimensions"):
            pipeline.process(frame, detections, detector_id="replay")
        assert service.count() == 0
        assert frame.disposed is True
        assert not any(frame.pixels)


def test_detector_failure_zeroizes_frame_before_reraising(tmp_path):
    Image.new("RGB", (2, 2), (1, 2, 3)).save(tmp_path / "frame.png")
    (tmp_path / "zones.yaml").write_text(
        """cameras:
  camera-a:
    zones:
      - id: all
        location: room
        box: [0, 0, 2, 2]
""",
        encoding="utf-8",
    )
    frame = CameraFrame.from_image(
        tmp_path / "frame.png",
        camera_id="camera-a",
        timestamp_iso="2026-08-04T12:00:00Z",
    )

    class FailingAdapter:
        detector_id = "failing-adapter"

        def open_frame(self):
            return frame

        def detect(self, _frame):
            raise RuntimeError("detector failed")

    with LastSeenService(tmp_path / "lastseen.db") as service:
        pipeline = CameraPrivacyPipeline(
            service,
            LocalCropStore(tmp_path / "crops"),
            ZoneMap.from_yaml(tmp_path / "zones.yaml"),
        )
        with pytest.raises(RuntimeError, match="detector failed"):
            pipeline.process_adapter(FailingAdapter())
        assert service.count() == 0
        assert frame.disposed is True
        assert not any(frame.pixels)
