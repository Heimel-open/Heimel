# VALO Research Group — Public Release Index

Status date: 2026-08-14
Repository visibility: private
Purpose: select bounded, source-backed research artifacts for external distribution without exposing the full working repository.

## Release rule

`present in repository` does not mean `ready to publish`.

An item is externally releasable only when its exact artifact/version is identified, provenance and IP boundaries are known, and the claims made about its availability match what actually exists.

## Papers

### Agentic Execution Risk Report 2026

Release status: **CANONICAL EXTERNAL ARTIFACT SELECTED**.

Canonical artifact:

- file: `Agentic_Execution_Risk_Report_2026_Professional.pdf`;
- Drive file ID: `1-OeqCrT6CB39-_u8XvhL9NjL64__YWMD`;
- size: 929,023 bytes;
- SHA-256: `0d0151fa67396cadd66d7c5d2e0888672ba4235c9de4639ec26084601f8b93e4`;
- format: 20-page English PDF;
- stated dataset snapshot: 1,571 documented incidents / 7,314 media reports.

See `papers/agentic-execution-risk-2026/CANONICAL_RELEASE.md` for the decision record and distribution boundary.

Why selected: the Professional edition explicitly presents the work as a challengeable stress model, exposes its assumptions, distinguishes modeled outputs from observations, includes technical and limitations sections, and states that it does not establish an inevitable incident count.

Other PDFs in the folder are historical/design/working variants unless separately promoted by a later release decision. In particular, the existing `Agentic_Execution_Risk_Report_2026.pdf` is not canonical for external research distribution.

Remaining gate before broad public/media release: citation-by-citation and quantitative-claim review against the selected SHA-256. Bounded peer/researcher review may use the selected artifact without representing feedback as endorsement.

### Regulator / policy paper (`paper-legacy-v1-regulator`)

Release status: **REVIEW / CANONICAL ARTIFACT SELECTION REQUIRED**.

The six-part manuscript and compiled regulatory outputs remain available internally, but more than one compiled artifact exists and the folder is explicitly named `legacy-v1`. Do not infer a current external release from filename alone.

## Datasets

### AIID Import

Recorded metadata:

- 1,615 incidents;
- 7,314 reports;
- adopted external source: AI Incident Database.

Release status: **SOURCE RECOVERY REQUIRED — PAYLOAD NOT PUBLISHED**.

The original research process refers to a local approximately 503 MB MongoDB BSON snapshot under `data/aiid-import/mongodump_full_snapshot/aiidprod/`. That payload is not tracked in the accessible Git repositories and was not located in the connected Drive search performed for this release step.

Do not replace the historical source silently with a newly downloaded AIID snapshot. That would create a different dataset/provenance chain.

See `datasets/aiid-import/RELEASE_MANIFEST.md` for the recovery, normalization, attribution and checksum procedure.

Allowed claim: VALO Research metadata records a historical AIID snapshot with 1,615 incidents and 7,314 reports; the distributable payload has not yet been published from the original source snapshot.

### Governance Gaps Database

Release status: **METHODOLOGY PRESENT — DATASET PAYLOAD SOURCE NOT MATERIALIZED**.

`datasets/gaps/README.md` and `methodology/GOVERNANCE-GAP-DATABASE.md` exist, but the underlying source table/database is not present as a versioned publication payload and is not tracked at `agentic-execution-risk/data/gaps/`.

See `datasets/gaps/RELEASE_MANIFEST.md` for the source-recovery, schema, privacy/IP and checksum gate.

Allowed claim: VALO Research has documented governance-gap methodology and metadata; the versioned dataset payload is not yet published.

### Claims / Evidence datasets

Release status: **VERIFY BEFORE SHARE**.

Metadata folders exist, but payload and licensing/provenance status must be verified individually before external distribution.

## Methodology

Potential bounded external assets already present:

- `methodology/METHODOLOGY.md`;
- `methodology/EVIDENCE-GRAPH.md`;
- `methodology/GOVERNANCE-GAP-DATABASE.md`;
- `methodology/FORECAST-DATASET.md`.

Release status: **REVIEW BEFORE PUBLICATION**.

These may support research outreach, but methodology must not be presented as proof that an associated dataset payload is publicly available.

## Recommended first research packet

For author/researcher outreach, do not send the repository.

Use a bounded packet:

1. the selected canonical paper or a concise executive extract;
2. one evidence/method note relevant to the recipient;
3. one directly relevant executable mapping/test link when externally shareable;
4. one explicit question asking for technical challenge or validation.

For the Mind Viruses authors, use the paper citation plus the `SELF_PROPAGATING_STATE / CONTEXT_CONTAMINATION` implementation mapping and focused negative tests, not the full VALO portfolio.

## Repository publication status

This repository remains private. Individual artifacts may be deliberately shared through approved channels. A private GitHub repository must not be represented as a publicly browsable publications hub.

Repository visibility is a separate decision from selecting and releasing bounded paper/dataset artifacts.
