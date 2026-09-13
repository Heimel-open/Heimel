# Aurora-Lens / OECD due-diligence alignment — external evidence note

Status: external evidence; VALO interpretation only
Date recorded: 2026-08-07
Source date: 2026-02-21
Author / IP owner: Margaret Stokes
VALO owner: VALO Research for this boundary analysis only

## Source

Margaret Stokes, *Operational Alignment of Aurora-Lens with OECD Due Diligence Guidance for Responsible AI (2026)*, version 1.0, Zenodo, published 2026-02-21.

DOI: https://doi.org/10.5281/zenodo.18719033
Record: https://zenodo.org/records/18719033

The Zenodo record describes Aurora-Lens as a deterministic transport-layer AI governance proxy mapped to the OECD 2026 Due Diligence Guidance for Responsible AI. It states that the OECD framework provides six procedural Responsible Business Conduct steps but does not prescribe runtime enforcement mechanisms, and positions Aurora-Lens as an operational implementation path using admissibility gating, deterministic intervention outcomes and tamper-evident audit.

The record also describes a Persistent Existence Frame (PEF) as the state substrate supporting replayable decision state and audit reconstruction, and places Aurora-Lens between applications and LLM providers without modifying the underlying model.

## VALO boundary interpretation

This source strengthens the case for Aurora-Lens as an external admissibility capability, but does not move the VALO execution-authorization boundary.

The boundary remains:

1. Aurora-Lens may determine whether supplied model output, evidence, communication or persistent-state conditions are admissible within Aurora-Lens semantics.
2. The adapter preserves those determinations as governed inputs. It does not reinterpret a non-admit into an admit.
3. REHT alone determines whether the concrete ActionEnvelope is authorized to proceed at the VALO execution boundary.
4. RACS expresses the resulting VALO decision contract; an external PEP enforces it; Veritas preserves the resulting evidence.

An Aurora-Lens admission is therefore necessary where the integration contract requires it, but never sufficient for VALO execution authorization. A binding Aurora-Lens non-admit remains preclusive within its declared scope.

## Terminology guard

Aurora-Lens public materials may use terms such as governance, authorization, execution boundary or consequence. Those terms must not be imported as VALO authority semantics.

Within VALO:

- Aurora-Lens: external admissibility / epistemic and communication governance input.
- REHT: sole execution-authorization boundary.
- RACS: deterministic expression of the decision contract.
- External PEP: enforcement without independent authority.
- Veritas: immutable evidence preservation without analysis or authority.

## OECD usage rule

The paper is evidence that Aurora-Lens has a published OECD due-diligence alignment claim. It is not, by itself:

- OECD certification or endorsement;
- proof that VALO is OECD-conformant;
- authority to copy or absorb Aurora-Lens IP;
- a reason to create a new VALO component;
- a substitute for exact control mapping and deployment evidence.

Any future VALO/OECD claim must be made from VALO's own control mapping, implementation evidence and receipts. Aurora-Lens alignment may be cited only as evidence concerning the external Aurora capability.

## IP and implementation rule

Aurora-Lens remains independently owned by Margaret Stokes. VALO may define and implement its own provider-neutral adapter contract, subject to agreed licensing and approval of Aurora-specific semantics. No Aurora-Lens implementation, terminology set or proprietary mechanism is incorporated by this note.

Related profile: `INTERFACE_PROFILE_V0_1.md`
