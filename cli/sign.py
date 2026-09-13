#!/usr/bin/env python3
"""cli/sign.py — operator-side signing helper (NOT run inside the registry CI).

Computes the package digest over the manifest + referenced schemas and writes it
into the manifest's integrity.package_digest. Signature is produced by the
operator's private key (kept outside this repo) and stored in integrity.signature.

This script only fills the digest deterministically; the actual cryptographic
signature is performed by the operator's key and the result pasted into the
manifest. Keeping the key out of the repo honors the distribution boundary.
Usage: python3 cli/sign.py skills/sales/sales.prospect.enrich.yaml
"""
import argparse
import hashlib
import os
import sys

try:
    import yaml
except ImportError:
    yaml = None

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)


def digest_of(mpath):
    h = hashlib.sha256()
    with open(mpath, "rb") as f:
        h.update(f.read())
    # include referenced schemas for a complete package digest
    with open(mpath) as f:
        doc = yaml.safe_load(f)
    for io in ("inputs", "outputs"):
        ref = doc.get("spec", {}).get(io, {}).get("schema")
        if ref:
            with open(os.path.join(ROOT, ref), "rb") as sf:
                h.update(sf.read())
    return "sha256:" + h.hexdigest()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("manifest")
    args = ap.parse_args()
    if yaml is None:
        print("PyYAML required")
        sys.exit(2)
    d = digest_of(args.manifest)
    with open(args.manifest) as f:
        doc = yaml.safe_load(f)
    doc.setdefault("spec", {}).setdefault("integrity", {})["package_digest"] = d
    with open(args.manifest, "w") as f:
        yaml.safe_dump(doc, f, sort_keys=False)
    print(f"DIGEST_WRITTEN {d} (signature must be added by operator key)")


if __name__ == "__main__":
    main()
