"""CLI for deterministic LastSeen camera replay and privacy verification."""

from __future__ import annotations

import argparse
from dataclasses import asdict
import json
from pathlib import Path
from typing import Sequence

from valo_edge.lastseen.camera import (
    CameraPrivacyPipeline,
    LocalCropStore,
    ReplayDetectorAdapter,
    ZoneMap,
)
from valo_edge.lastseen.service import LastSeenService


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="lastseen-camera",
        description="Replay a local detector event through governed LastSeen camera privacy.",
    )
    parser.add_argument("--db", default="lastseen.db", help="Local SQLite database")
    parser.add_argument("--crop-dir", default="lastseen-crops", help="Governed object crop directory")
    parser.add_argument("--zones", required=True, type=Path, help="Local camera zone YAML")
    parser.add_argument("--policy-version", default="lastseen-policy-v1")
    parser.add_argument("--minimum-confidence", type=float, default=0.5)
    commands = parser.add_subparsers(dest="command", required=True)
    replay = commands.add_parser("replay", help="Replay a detector JSON event")
    replay.add_argument("event_file", type=Path)
    return parser


def _observation_payload(result) -> dict:
    return {
        "object": result.object_name,
        "location": result.location,
        "observed_at": result.observed_at_iso,
        "source_id": result.source_id,
        "camera_id": result.camera_id,
        "zone_id": result.zone_id,
        "image_ref": result.image_ref,
        "confidence": result.confidence,
        "source_receipt": result.source_receipt_digest,
        "read_or_store_receipt": result.receipt_digest,
        "metadata": result.metadata or {},
    }


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    zone_map = ZoneMap.from_yaml(args.zones)
    adapter = ReplayDetectorAdapter.from_json(args.event_file)
    with LastSeenService(args.db, policy_version=args.policy_version) as service:
        pipeline = CameraPrivacyPipeline(
            service,
            LocalCropStore(args.crop_dir),
            zone_map,
            minimum_confidence=args.minimum_confidence,
        )
        result = pipeline.process_adapter(adapter)

    payload = {
        "stored": [_observation_payload(item) for item in result.observations],
        "rejected": [asdict(item) for item in result.rejected],
        "raw_frame_disposal": asdict(result.disposal_receipt),
        "raw_frame_persisted": False,
    }
    print(json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True))
    return 0 if result.disposal_receipt.verified else 2


if __name__ == "__main__":
    raise SystemExit(main())
