# Atlas retail-data pattern adoption into AI Work OS

Date: 2026-08-09
Status: canonical pattern adoption / domain implementation target

Work anchor:
- repo: `nsolland/valo-operator`
- canonical base-SHA: `b793f11927be99146b31ba5235e215e964be21a9`
- branch: `agent/atlas-retail-work-os`
- owner: Codex
- owned files: this adoption document and the README adoption reference
- dependencies: Operator API, registered Functions, Function Fabric, Workflow ISA, REHT, Gateway, Veritas, BARO and Kernel

Sources:
- https://atlas.flowretail.com/
- https://atlas.flowretail.com/produkt
- https://atlas.flowretail.com/produkt/import
- https://atlas.flowretail.com/integrasjoner
- https://atlas.flowretail.com/priser
- https://www.flowretail.com/
- https://docs.flowretail.com/

Source status: external product and market signal. Product capabilities below are based on the vendor's public material observed on 2026-08-09 and are not independent proof of implementation quality, security or runtime behavior.

## Decision

Adopt the useful Atlas pattern into AI Work OS: heterogeneous business inputs become provenance-bound candidate state; AI may extract, normalize and enrich that state; humans and policy owners retain explicit control of field ownership and publication; consequential changes are committed through registered Functions and verified independently in every destination.

Atlas is not a runtime dependency, authority source, policy engine or new VALO layer. Flow Retail POS, Shopware and future commerce systems remain replaceable context sources and execution targets. A future Retail Catalog Pack may own retail-domain semantics without adding retail logic to Operator.

## Signal

Atlas presents a narrow end-to-end operational product rather than a generic assistant:

- ingest product data from URLs, spreadsheets, CSV/XLSX, EDI/PRICAT and purchase-order PDFs;
- use AI to extract, classify, enrich and generate product content;
- manage product data and digital assets as candidate/catalog state;
- expose completeness and publication status;
- assign field ownership per integration;
- require user review before data is saved;
- publish products, variants, images and related records to Flow Retail POS and Shopware;
- retain user roles, publication rights and an activity trail.

The important Work OS pattern is not PIM or DAM itself. It is the controlled transition from uncertain external material to structured candidate state and then to verified multi-system effect.

## Canonical Work OS flow

```text
supplier URL / spreadsheet / CSV / EDI / PDF / image
  -> provider-neutral intake adapter
  -> immutable source artifact + provenance
  -> AI extraction / normalization / enrichment
  -> CandidateState + exact proposed diff
  -> completeness / contradiction / ownership evaluation
  -> human review or governed escalation
  -> registered Function
  -> Function Fabric
  -> Workflow ISA
  -> fresh execution context
  -> REHT
  -> Gateway / destination connector
  -> Flow Retail POS / Shopware / ERP / other target
  -> Veritas observation per destination
  -> BARO comparison
  -> Kernel event + learning proposal
```

AI may create and improve the proposal. It does not decide whether the resulting commercial change may be committed.

## Adopted patterns

### 1. Candidate state before committed state

Imported or generated product data enters Work OS as candidate state, never directly as operational truth.

A candidate should bind, as applicable:

- source artifact reference and digest;
- source type, location and observation time;
- extraction model/tool and version;
- original values and proposed normalized values;
- product, variant and asset identities;
- changed fields and destination scope;
- assumptions, unresolved mappings and contradictions;
- completeness evidence;
- reviewer and approval attestation;
- candidate and batch digest.

Re-import must be replay-safe. It may fill or propose changes, but it must not silently overwrite a committed value merely because a new extraction is available.

### 2. Field ownership is explicit

Atlas' per-integration field-control pattern is adopted as a general Work OS rule.

For every writable field and destination, the system must be able to state:

- canonical owner/source;
- whether the destination accepts create-only, update or no-write behavior;
- allowed transformation;
- conflict behavior;
- freshness/version requirement;
- required reviewer or mandate;
- observable postcondition.

Field ownership is routing and mutation policy. It is not execution authority. Changing field ownership or overwrite policy is itself a consequential configuration change and must use a registered Function.

### 3. Completeness is evidence, not permission

A completeness score is useful for triage and readiness evaluation. It cannot authorize publication.

The publication Function must evaluate explicit required fields, contradictions, source provenance, destination rules and current authority. A product showing 100% complete may still be inadmissible because the price owner changed, approval expired, a destination drifted or a source is untrusted.

### 4. Human approval is bound to the exact change

Adopt the human-review product pattern, but strengthen it.

Approval must bind to the exact candidate or batch digest, products, variants, assets, fields, destinations, purpose and validity window. Any material change after approval invalidates the approval for execution.

A UI click, role label or authenticated session is evidence about who approved. It does not replace current authority evaluation at the execution boundary.

### 5. Publication is a consequential Function

Create, update, publish, withdraw, price change, inventory-related mutation and deletion are distinct effects. They must not be collapsed into a generic sync call.

Each publish operation must be a registered, versioned Function with:

- typed inputs and outputs;
- effect and risk classification;
- authority requirement;
- exact destination and field scope;
- idempotency policy;
- expected postconditions;
- rollback or compensation semantics where supported;
- evidence requirements.

Connector credentials prove technical access only. They never grant business authority.

### 6. Bulk operations are digest-bound and partially observable

Bulk import and publication are valuable, but multiply consequence and failure surface.

A bulk permit must bind to the exact ordered mutation set or canonical batch digest. Adding a product, changing a price, changing a destination or altering a field after clearance requires re-evaluation.

Execution and verification remain item- and destination-addressable. Partial success must be reported as partial state, not converted into batch success. Retry must not duplicate already-observed effects.

### 7. Destination reality is verified independently

A successful API response or Atlas publication status is not proof that Flow Retail, Shopware or another target now holds the desired state.

Veritas must read the relevant destination state independently. BARO compares the observed fields, versions and asset references with the authorized postcondition. Unknown, pending, conflicting and partially applied outcomes remain explicit.

The canonical distinction remains:

```text
workflow completed != request sent != destination changed != desired state verified
```

### 8. Product and asset provenance stay connected

DAM behavior is adopted as part of the evidence chain. Original assets remain immutable references; crops, background removal, format conversion and generated images are derived artifacts with their own digests and transformation provenance.

A generated or transformed asset may be useful without being trustworthy for every channel or claim. Publication policy may therefore differ by asset type, market, destination and rights status.

## Domain and adapter placement

A future `Retail Catalog Pack` may own:

- product/variant/asset domain contracts;
- catalog lifecycle transitions;
- retail-specific admissibility;
- required-field and completeness rules;
- pricing and field-ownership constraints;
- publish/withdraw Functions;
- destination-specific postconditions.

Provider adapters may normalize Flow Retail, Shopware, ERP, PIM, DAM or supplier protocols. They own authentication, payload mapping, idempotency mechanism and observed-state mapping only.

Operator stays generic. REHT stays the sole final authorization boundary.

## Work OS reuse beyond retail

These Atlas-derived patterns apply to any domain where AI turns messy inputs into structured changes:

- supplier and procurement records;
- CRM and customer-master updates;
- finance and accounting entries;
- contract metadata;
- workforce records;
- public-case data;
- configuration and deployment changes.

The reusable primitive is:

```text
provenance-bound input
  -> candidate state
  -> exact diff
  -> explicit ownership
  -> bounded approval
  -> authorized commit
  -> independently verified effect
```

## Required negative proofs

A Retail Catalog Pack or equivalent implementation is incomplete until tests prove:

1. URL, spreadsheet, EDI or PDF access cannot grant authority.
2. AI-generated values never enter committed state without the required governed transition.
3. Completeness score cannot substitute for admissibility or authority.
4. Changed candidate or batch content invalidates stale approval and clearance.
5. Field-ownership rules prevent unauthorized overwrite.
6. Changing field ownership requires its own governed Function.
7. Connector credentials cannot authorize publication.
8. DENY or REJECT produces zero destination effect.
9. Bulk partial success remains partial and item-addressable.
10. Retry is idempotent per item and destination.
11. HTTP success without observed destination state is not EffectVerified.
12. A destination-side drift or manual edit is surfaced rather than silently overwritten.
13. Original and derived assets retain separate provenance and digests.
14. The same Operator API can drive two commerce destinations without changing REHT or Operator semantics.

## Priority

P1: adopt the candidate-state, exact-diff, field-ownership, digest-bound approval and independently verified publication pattern as canonical Work OS behavior.

P2: implement a narrow Retail Catalog Pack only when a concrete pilot or demonstrator requires executable retail semantics.

P3: defer direct Flow Retail or Shopware adapters until endpoint contracts, credentials, target ownership and a real proof environment exist.

## Canonical invariant

```text
AI may extract and enrich.
The domain pack defines valid catalog change.
The owner approves the exact proposed diff.
REHT decides whether that exact change may happen now.
The connector applies only the cleared mutation.
Veritas proves what each destination actually holds.
```

Atlas is adopted as a product and operational-control signal, not copied as architecture and not treated as evidence of authority.
