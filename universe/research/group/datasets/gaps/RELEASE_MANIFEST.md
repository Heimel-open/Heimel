# Governance Gaps Database — Release Manifest

Status date: 2026-08-14
Release state: METHODOLOGY PRESENT — dataset payload source not materialized

## Current verified state

The publication repository contains:

- `datasets/gaps/README.md`, describing VALO-owned governance-gap research;
- `methodology/GOVERNANCE-GAP-DATABASE.md`, describing the research/method layer.

The corresponding source dataset payload is not present under `datasets/gaps/` in the publication tree, and `agentic-execution-risk/data/gaps/` is not tracked in Git.

No source-backed row count, exact schema or release checksum can therefore be asserted for a public dataset package at this point.

## Release boundary

Methodology and high-level findings may be reviewed and shared separately when they pass the applicable publication/IP check.

A methodology document is not a substitute for a dataset. Do not describe the Governance Gaps Database as downloadable until a concrete, versioned payload exists.

## Required payload-release procedure

1. locate the authoritative source table/database used by the research process;
2. record source location, version/date, byte size and SHA-256;
3. define the canonical public schema and field dictionary;
4. identify and remove internal-only, partner, customer or sensitive fields;
5. preserve source/provenance references needed to audit each derived gap claim;
6. create a versioned CSV/JSON/JSONL release package;
7. record exact row count and package SHA-256;
8. bind the package to the corresponding methodology version;
9. run claim/IP/privacy review before public release.

## Current allowed external claim

Allowed:

> VALO Research has a documented governance-gap methodology and publication metadata. The versioned dataset payload is not yet published.

Not allowed:

> The Governance Gaps Database is currently available as a downloadable dataset.

## Honest completion state

This manifest establishes a fail-closed release boundary. Dataset publication remains incomplete until the authoritative source payload is recovered and converted into a versioned, reviewable package.
