# Build Order: LastSeen Governed Retention

Status: VERIFIED — READY TO MERGE
Owner: ChatGPT implementation worker
Independent verification: GitHub Actions
Repository: `nsolland/valo-edge`
Canonical base: `0e4a2fc055defbea9cb6543a2f86282e20d0296f`
Branch: `feat/lastseen-governed-retention`
PR: `#19`
Dependency: merged Camera Alpha, temporal memory and Veritas Edge V1

## Delivered

- deterministic whole-object retention cutoff using source observation time
- no mutation when any retained observation is newer than or equal to the cutoff
- separately authorized crop staging into local quarantine
- existing LastSeen governed source/index deletion remains authoritative
- separately authorized crop commit and permanent unlink after memory deletion
- separately authorized crop restoration if memory deletion fails
- crop-root containment and quarantine path rejection
- content digest binding before stage, commit, restore and final deletion
- duplicate crop references deduplicated before mutation
- missing crops represented explicitly without fabricated deletion success
- source scope re-read before deletion to catch concurrent history changes
- bounded history scope aligned with LastSeen's public 1000-row contract; reaching the cap fails closed
- retained evidence contains subject/path/content/source digests and outcomes, never deleted crop bytes or recoverable object names
- module CLI supports explicit deletion and cutoff-based expiry without model or network dependency

## Verification

GitHub Actions run `31332237422`:

- Python 3.10: 156 passed, 1 skipped; memory, camera and API smoke passed
- Python 3.11: tests and all smoke gates passed
- Python 3.12: tests and all smoke gates passed

Initial CI run `31332131336` found one concrete contract mismatch: retention requested 100000 history rows while `LastSeenService.history()` permits at most 1000. The implementation now uses a maximum of 1000 and refuses deletion when the result reaches that cap, preserving fail-closed scope semantics.

## Acceptance gates

- complete explicit deletion removes source rows, derived indexes and referenced crops
- cutoff retention is a no-op when newer evidence exists
- expired history removes all object rows and each unique crop once
- missing crops remain explicit evidence while already-absent private content stays absent
- path escape fails before any memory mutation
- memory deletion failure restores staged crop under a new authorization
- ambiguous bounded history fails closed without touching crop or memory
- object identifiers retained by the retention layer are salted HMAC digests

## Owned files

- `src/valo_edge/lastseen/retention.py`
- `tests/test_lastseen_retention.py`
- `docs/lastseen/BUILD_ORDER_GOVERNED_RETENTION.md`

## Explicit non-goals

- changing micro-REHT or RACS semantics
- retention for arbitrary non-LastSeen storage
- secure erase guarantees below the filesystem abstraction
- cloud lifecycle policies
- automatic face/person retention
