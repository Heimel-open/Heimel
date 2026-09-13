# Refusal Resolution Protocol (RRP) — Implementation Architecture

## Service Boundaries

### 1. VAIG Refusal Emitter (External to RRP)
**Responsibility:** Detect boundary crossing, emit structured refusal event.
**Interface:** POST /rrp/v1/refusal
**Payload:** RefusalEvent schema
**Guarantee:** At-least-once delivery. Idempotency via refusal_id.

### 2. RRP Enrichment Service
**Responsibility:** Populate UncertaintyInventory from refusal context.
**Interface:** Internal queue consumer
**Actions:**
- Query model state for contamination assessment
- Check pattern database for historical matches
- Generate uncertainty dimensions with confidence scores
- Emit enriched event to router

### 3. RRP Router
**Responsibility:** Assign refusal to correct BOA based on category/scope.
**Interface:** Internal queue consumer + BOA registry lookup
**Actions:**
- Map refusal.category → boa_role
- Check BOA availability and latency SLA
- Create AuthorityAssignment record
- Push to BOA work queue

### 4. BOA Review Interface
**Responsibility:** Human or delegated review of refusal.
**Interface:** Web UI + API
**Actions:**
- View refusal + uncertainty inventory + pattern evidence
- Record review notes and evidence citations
- Issue decision: APPROVED / REJECTED / ESCALATED
- Provide operator coaching if applicable

### 5. RRP Resolution Service
**Responsibility:** Close thread, update system state, archive.
**Interface:** Internal queue consumer
**Actions:**
- Validate final state transition
- Execute session actions (context reset, etc.)
- Close AccountabilityThread
- Set audit level and retention policy

## Data Stores

### Accountability Thread Store (ATS)
- Append-only, immutable events
- Indexed by thread_id, refusal_id, operator_id, session_id
- Retention: 7 years for STANDARD, indefinite for ESCALATED

### BOA Registry
- Role → scope mapping
- Entity → availability status
- Latency SLA tracking
- Delegation chains

### Pattern Database
- Refusal fingerprinting
- Historical match correlation
- Attack pattern clustering

## Wire Protocol Summary

```text
VAIG ──POST──> RRP Enrichment ──queue──> RRP Router ──queue──> BOA Review
                                              │
                                              └──> (advisory) ──> RRP Resolution
BOA Review ──API──> RRP Resolution ──queue──> ATS (archive)
```

## Failure Modes

| Failure | Mitigation |
|---------|-----------|
| Enrichment timeout | Emit with empty inventory, flag for manual review |
| BOA unavailable | Auto-escalate to next BOA in chain |
| BOA latency SLA breach | Auto-escalate, notify ops |
| Resolution service down | Queue events, replay on recovery |
| ATS write failure | Halt pipeline, alert ops, do not lose events |

## Operational Invariants

1. Every refusal has exactly one AccountabilityThread.
2. Every thread has at least one event (REFUSAL_EMITTED).
3. No thread can transition to RESOLVED without a BOA decision or explicit auto-resolution policy.
4. The ATS is the source of truth for all refusal lifecycle state.
5. No event can be modified or deleted from a thread.
