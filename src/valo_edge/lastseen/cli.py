"""Command-line interface for governed local LastSeen memory."""

from __future__ import annotations

import argparse
from dataclasses import asdict
import json
from pathlib import Path
from typing import Sequence

from valo_edge.lastseen.service import LastSeenService, MemoryScope


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="lastseen",
        description="Your home remembers. The cloud doesn't.",
    )
    parser.add_argument("--db", default="lastseen.db", help="Local SQLite database path")
    parser.add_argument(
        "--policy-version",
        default="lastseen-policy-v1",
        help="Local policy version recorded in source provenance and receipts",
    )
    commands = parser.add_subparsers(dest="command", required=True)

    remember = commands.add_parser("remember", help="Record where an object was seen")
    remember.add_argument("object_name")
    remember.add_argument("location")
    remember.add_argument("--image", dest="image_ref")
    remember.add_argument("--confidence", type=float, default=1.0)
    remember.add_argument("--observed-at")
    remember.add_argument("--source-id")
    remember.add_argument("--source-type", default="local-observation")
    remember.add_argument("--source-device-id")
    remember.add_argument("--camera-id")
    remember.add_argument("--zone-id")
    remember.add_argument("--alias", action="append", default=[])

    find = commands.add_parser("find", help="Find authorized local observations")
    find.add_argument("object_name")
    find.add_argument("--alias", action="append", default=[])
    find.add_argument("--camera-id", action="append", default=[])
    find.add_argument("--zone-id", action="append", default=[])
    find.add_argument("--since")
    find.add_argument("--until")
    find.add_argument("--history", action="store_true")
    find.add_argument("--limit", type=int, default=100)

    forget = commands.add_parser("forget", help="Delete source history and derived indexes")
    forget.add_argument("object_name")

    ingest = commands.add_parser("ingest", help="Ingest a detector event JSON file")
    ingest.add_argument("event_file", type=Path)

    commands.add_parser("rebuild-index", help="Rebuild derived indexes from source observations")
    commands.add_parser("demo", help="Run the camera-ready LastSeen demo")
    return parser


def _scope(args: argparse.Namespace) -> MemoryScope:
    return MemoryScope(
        camera_ids=tuple(getattr(args, "camera_id", ()) or ()),
        zone_ids=tuple(getattr(args, "zone_id", ()) or ()),
        since_iso=getattr(args, "since", None),
        until_iso=getattr(args, "until", None),
    )


def _result_payload(result) -> dict:
    return {
        "object": result.object_name,
        "location": result.location,
        "last_seen": result.observed_at_iso,
        "ingested_at": result.ingested_at_iso,
        "image_ref": result.image_ref,
        "confidence": result.confidence,
        "source_id": result.source_id,
        "source_type": result.source_type,
        "source_device_id": result.source_device_id,
        "camera_id": result.camera_id,
        "zone_id": result.zone_id,
        "policy_version": result.policy_version,
        "source_receipt": result.source_receipt_digest,
        "read_receipt": result.receipt_digest,
        "metadata": result.metadata or {},
    }


def _print_json(payload) -> None:
    print(json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True))


def _run_demo(service: LastSeenService) -> int:
    service.remember(
        "keys",
        "kitchen counter, beside the coffee machine",
        image_ref="crops/keys-kitchen.jpg",
        confidence=0.98,
        observed_at_iso="2026-08-04T08:42:00Z",
        camera_id="kitchen-01",
        zone_id="counter-coffee-machine",
        aliases=["nøkler", "keyring"],
    )
    service.remember(
        "glasses",
        "living room, under the blue cushion",
        image_ref="crops/glasses-sofa.jpg",
        confidence=0.95,
        observed_at_iso="2026-08-04T09:11:00Z",
        camera_id="living-room-01",
        zone_id="sofa",
        aliases=["briller"],
    )
    result = service.find("nøkler")
    print("Where are my keys?")
    if result is None:
        print("I have not seen them.")
        return 1
    print(f"Last seen: {result.location} at {result.observed_at_iso}")
    print(f"Source: {result.source_id}")
    print(f"Local receipt: {result.receipt_digest}")
    print("No video left the device.")
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    with LastSeenService(args.db, policy_version=args.policy_version) as service:
        if args.command == "remember":
            result = service.remember(
                args.object_name,
                args.location,
                image_ref=args.image_ref,
                confidence=args.confidence,
                observed_at_iso=args.observed_at,
                source_id=args.source_id,
                source_type=args.source_type,
                source_device_id=args.source_device_id,
                camera_id=args.camera_id,
                zone_id=args.zone_id,
                aliases=args.alias,
            )
            _print_json(_result_payload(result))
            return 0

        if args.command == "find":
            scope = _scope(args)
            if args.history:
                results = service.history(
                    args.object_name,
                    aliases=args.alias,
                    scope=scope,
                    limit=args.limit,
                )
                _print_json(
                    {
                        "found": bool(results),
                        "count": len(results),
                        "results": [_result_payload(result) for result in results],
                    }
                )
                return 0 if results else 1

            result = service.find(args.object_name, aliases=args.alias, scope=scope)
            if result is None:
                _print_json({"found": False, "object": args.object_name})
                return 1
            _print_json(_result_payload(result))
            return 0

        if args.command == "forget":
            deletion = service.forget_with_receipt(args.object_name)
            _print_json(asdict(deletion))
            return 0

        if args.command == "ingest":
            event = json.loads(args.event_file.read_text(encoding="utf-8"))
            metadata = event.get("metadata") or {}
            result = service.remember(
                event["object_name"],
                event["location"],
                image_ref=event.get("image_ref"),
                confidence=float(event.get("confidence", 1.0)),
                observed_at_iso=event.get("observed_at_iso"),
                metadata=metadata,
                source_id=event.get("source_id"),
                source_type=event.get("source_type", "detector-observation"),
                source_device_id=event.get("source_device_id"),
                camera_id=event.get("camera_id") or metadata.get("camera_id"),
                zone_id=event.get("zone_id") or metadata.get("zone_id"),
                policy_version=event.get("policy_version"),
                aliases=event.get("aliases", ()),
            )
            _print_json(_result_payload(result))
            return 0

        if args.command == "rebuild-index":
            _print_json(asdict(service.rebuild_indexes()))
            return 0

        return _run_demo(service)


if __name__ == "__main__":
    raise SystemExit(main())
