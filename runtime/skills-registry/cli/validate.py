#!/usr/bin/env python3
"""cli/validate.py — validate skill manifests against the schema.

Deterministic catalog/contract check. No eval/auth/exec. Verifies:
  1. manifest validates against schemas/skill.schema.json
  2. referenced input/output schema files exist (resolved relative to the
     manifest file first, then relative to repo root)
  3. package_digest is present (sha256:64hex)
Usage: python3 cli/validate.py skills/sales/sales.prospect.enrich.yaml
"""
import argparse
import json
import os
import sys

try:
    import yaml
except ImportError:
    yaml = None

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)


def resolve(ref, manifest_path):
    """Try relative to manifest dir, then relative to repo root."""
    mdir = os.path.dirname(os.path.abspath(manifest_path))
    candidates = [
        os.path.join(mdir, ref),
        os.path.join(ROOT, ref),
    ]
    for c in candidates:
        if os.path.exists(c):
            return c
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("manifest", nargs="+")
    ap.add_argument("--schema", default=os.path.join(ROOT, "schemas/skill.schema.json"))
    args = ap.parse_args()

    if yaml is None:
        print("PyYAML required: pip install pyyaml")
        sys.exit(2)

    import jsonschema
    schema = json.load(open(args.schema))
    failures = 0
    for mpath in args.manifest:
        try:
            with open(mpath) as f:
                doc = yaml.safe_load(f)
        except Exception as e:
            print(f"FAIL {mpath}: cannot read ({e})")
            failures += 1
            continue
        try:
            jsonschema.validate(doc, schema)
        except jsonschema.ValidationError as e:
            print(f"FAIL {mpath}: schema violation: {e.message}")
            failures += 1
            continue
        spec = doc.get("spec", {})
        for io in ("inputs", "outputs"):
            ref = spec.get(io, {}).get("schema")
            if ref and not resolve(ref, mpath):
                print(f"FAIL {mpath}: missing {io} schema {ref}")
                failures += 1
        digest = spec.get("integrity", {}).get("package_digest", "")
        if not (digest.startswith("sha256:") and len(digest) == 71):
            print(f"FAIL {mpath}: bad package_digest")
            failures += 1
            continue
        print(f"PASS {mpath} (id={doc['metadata']['id']} v{doc['metadata']['version']})")

    sys.exit(1 if failures else 0)


if __name__ == "__main__":
    main()
