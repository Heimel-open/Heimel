# Document Source Standing v1

External document libraries are not authoritative state stores. They are sources of candidate material for VALO State Admission.

The StartupLab resource library reviewed on 2026-08-12 makes the failure mode concrete: documents presented together as startup resources can have materially different ages and revision histories. The SLIP files carry recent modifications, while shareholder, employment and tax templates are older. One tax template still contains an older deduction ceiling. The correct response is not to trust or reject a library as a whole; it is to govern the standing of each source and each claim before operative use.

## Canonical rule

```text
available document
  -> source identity + fingerprint + revision/freshness
  -> candidate claims / rights / obligations / constraints
  -> VALO State Admission
  -> explicit derived-state transition
  -> maintained Kernel state
```

A document may be authentic and still be stale. It may be current and still lack authority for the purpose at hand. It may be signed and still contain claims that depend on conditions, interpretation or effective dates. Possession, retrieval, signature, NDA status or admission therefore never means all content is operative.

## Required source standing

Before document-derived material may support operative state, VALO must retain or deterministically resolve:

- source identity and content fingerprint;
- source revision/version where available;
- capture/retrieval time and source update time where available;
- issuer/publisher identity and the basis for treating that issuer as relevant to the claim;
- effective/validity window;
- supersedes/superseded-by lineage where known;
- tenant and jurisdiction context;
- purpose for which the material is being used;
- contradictions, unresolved references and missing dependencies;
- the current VALO admission decision bound to the exact material.

A label such as template, latest, standard, approved or a stable URL is not sufficient evidence of current standing.

## Mapping into the Kernel

The document itself enters as `Evidence`. State Admission determines whether that exact material may support operative derived state. The derived state remains typed explicitly:

- investment instruments such as SLIP -> `Contract`, rights, obligations, constraints and future conditional events;
- dilution/pro-rata protection -> explicit investor `Right`, never an implication inferred later from prose;
- shareholder agreement -> ownership-related rights, obligations, transfer constraints, board/decision constraints and contract state;
- vesting/leaver provisions -> time-bound rights/obligations and transfer constraints;
- employment agreement -> employment relationship, obligations, confidentiality/IP constraints and applicable rights;
- NDA / rules of engagement -> purpose-bound disclosure/use constraints, not a general authority grant;
- tax guidance or application forms -> evidence supporting a tax/compliance claim, never self-authorizing legal truth.

Admission cannot create authority. Contract parsing cannot create authority. A right, obligation or authority becomes operative only through the relevant explicit Kernel transition with admitted evidence and the correct basis.

## Freshness and supersession

Document freshness is semantic, not merely chronological.

A newer file does not automatically supersede an older one unless the source relationship supports that conclusion. Conversely, an older document can remain operative when it is the signed governing instrument for specific parties even if a newer public template exists.

VALO therefore distinguishes:

- source-template freshness: which public/reference template is current;
- instrument validity: which executed agreement governs the parties;
- claim validity: whether a particular clause, amount, right or obligation is currently operative;
- evidence standing: whether the evidence may still support maintained state.

When a source is superseded, revoked, contradicted or no longer current for its purpose, it must not support new operative state. Existing dependent state must be re-evaluated through the existing admission/standing mechanisms rather than silently surviving because the old document remains stored.

## Disclosure and partner boundaries

The StartupLab Rules of Engagement pattern is useful but should be represented more strictly in VALO:

```text
enterprise possesses information
        !=
recipient may receive it
        !=
recipient may use it for any purpose
        !=
recipient may create operative state from it
        !=
recipient may act on it
```

Each boundary is separate. NDA status, corporate relationship or meeting participation is evidence relevant to disclosure constraints; none is a general execution authority.

This preserves the VALO ordering:

```text
information standing
  -> maintained governed state
  -> purpose-bounded workspace
  -> worker candidate
  -> conformance
  -> fresh REHT authorization
  -> execution
```

## External adapters

Document parsers, legal extraction systems, Aurora-Lens or any other external framework may produce candidate claims, contradictions, unresolved references or provider assessments. They remain replaceable adapters. VALO owns admission and maintained standing, and the native path must work without any named provider.

## Source-derived lesson

The useful asset in a template library is not only the prose. It is the latent operational model: capital instruments create conditional future rights; shareholder agreements create constrained ownership/decision relationships; employment agreements bind work, IP and confidentiality; partner rules bind disclosure purpose.

VALO should ingest those structures as governed candidate semantics, while refusing the shortcut that a document's presence, title or apparent legitimacy makes its contents current or operative.
