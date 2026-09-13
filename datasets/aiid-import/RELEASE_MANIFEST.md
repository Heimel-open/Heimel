# AIID Import — Release Manifest

Status date: 2026-08-14
Release state: SOURCE RECOVERY REQUIRED — payload not published

## Recorded source facts

Publication metadata currently records:

- source: AI Incident Database (external/adopted);
- 1,615 incident records;
- 7,314 report records;
- research-side source location: `data/aiid-import/mongodump_full_snapshot/aiidprod/`;
- source form: MongoDB BSON snapshot;
- historical research audit records the local snapshot at approximately 503 MB.

The research loader expects `incidents.bson` under that source tree.

## Current accessible-state verification

As of 2026-08-14:

- the publication repository contains metadata, not the incident/report payloads;
- `agentic-execution-risk` does not contain the `data/aiid-import/` payload in Git;
- the original 503 MB BSON snapshot was not located in the connected Drive search performed for this release;
- therefore the recorded 1,615 / 7,314 counts cannot be independently reproduced from an accessible source artifact in this release step.

## Provenance rule

Do **not** substitute a newly downloaded/current AI Incident Database snapshot and present it as the source behind the 2026 report. That would create a different dataset with different provenance, record counts and potentially different schema/content.

The original source snapshot must be recovered or an explicitly new dataset version must be created with a new provenance chain.

## Required payload-release procedure

After recovering the original snapshot:

1. record source filename(s), byte size and SHA-256 before transformation;
2. decode BSON deterministically;
3. define the public field schema and remove fields that should not be republished;
4. retain source record identifiers sufficient for traceability where licensing permits;
5. produce normalized versioned JSON/JSONL or CSV packages;
6. include field dictionary, transformation code/version and AIID attribution/license notice;
7. record output counts and SHA-256 checksums;
8. verify the released counts against the exact package;
9. run a privacy/licensing/IP review before making payloads public.

## Current allowed external claim

Allowed:

> VALO Research metadata records a historical AIID snapshot used in this research line, with 1,615 incidents and 7,314 reports. The distributable dataset payload has not yet been published from the original source snapshot.

Not allowed:

> The 1,615-incident dataset is currently downloadable from this repository.

## Honest completion state

This manifest closes ambiguity about what exists. It does **not** claim dataset materialization is complete. Payload release remains blocked on recovery of the original source snapshot or an explicit decision to create a new, separately versioned dataset from a new source snapshot.
