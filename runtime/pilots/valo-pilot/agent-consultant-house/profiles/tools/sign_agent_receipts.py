#!/usr/bin/env python3
"""Sign or verify session-bound agent.valo.id receipts.

Prototype cryptographic binding for profile receipts. Production deployments must
replace the demo secret with a real key source and rotation policy.
"""

from pathlib import Path
import argparse
import copy
import hashlib
import hmac
import json
import os
import sys

try:
    import yaml
except ImportError as exc:
    raise SystemExit("PyYAML is required: python -m pip install pyyaml") from exc

DEMO_SECRET = "valo-agent-profile-demo-secret-not-production"


def load_yaml(path):
    return yaml.safe_load(Path(path).read_text())


def dump_yaml(path, doc):
    Path(path).write_text(yaml.safe_dump(doc, sort_keys=False), encoding="utf-8")


def canonical_payload(receipt):
    payload = copy.deepcopy(receipt)
    payload.get("verification", {}).pop("signature", None)
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")


def signing_key():
    return os.environ.get("VALO_PROFILE_RECEIPT_SECRET", DEMO_SECRET).encode("utf-8")


def expected_signature(receipt):
    return hmac.new(signing_key(), canonical_payload(receipt), hashlib.sha256).hexdigest()


def receipt_paths(profile_path):
    profile = load_yaml(profile_path)
    base = Path(profile_path).parent
    for receipt in profile["receipts"]["public_recent"]:
        yield base / receipt["receipt_file"]


def verify_receipt(path):
    receipt = load_yaml(path)
    errors = []
    verification = receipt.get("verification", {})
    authority = receipt.get("authority", {})

    if verification.get("signature_alg") != "hmac-sha256":
        errors.append("signature_alg must be hmac-sha256")
    if not authority.get("session_bound"):
        errors.append("receipt is not session-bound")
    if not authority.get("session_id"):
        errors.append("missing session_id")
    if verification.get("signature", "").startswith("sample-"):
        errors.append("sample signature is not allowed")
    if verification.get("signature") != expected_signature(receipt):
        errors.append("signature mismatch")

    return errors


def sign_receipt(path):
    receipt = load_yaml(path)
    verification = receipt.setdefault("verification", {})
    verification["verified"] = True
    verification["verification_method"] = "session_bound_demo_receipt"
    verification["signature_alg"] = "hmac-sha256"
    verification["signature_key_ref"] = "demo://valo-agent-profile-proof-v0.1"
    verification["signature_scope"] = "receipt_without_signature"
    verification["signature_status"] = "demo_signed"
    receipt.setdefault("authority", {}).setdefault("session_id", "session-research-01-profile-v0.1")
    verification["signature"] = expected_signature(receipt)
    dump_yaml(path, receipt)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("profile", help="agent profile YAML")
    parser.add_argument("--verify", action="store_true", help="verify signatures")
    parser.add_argument("--write", action="store_true", help="write signatures in place")
    args = parser.parse_args()

    if not args.verify and not args.write:
        raise SystemExit("use --verify or --write")

    if args.write:
        for path in receipt_paths(args.profile):
            sign_receipt(path)
            print(f"SIGNED: {path}")

    if args.verify:
        failed = False
        for path in receipt_paths(args.profile):
            errors = verify_receipt(path)
            if errors:
                failed = True
                for error in errors:
                    print(f"DENY: {path}: {error}")
            else:
                print(f"ALLOW: {path}: signature valid")
        if failed:
            raise SystemExit(1)


if __name__ == "__main__":
    main()
