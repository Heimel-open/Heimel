# Public repository publication policy

This repository is already a publication surface. A branch push is public disclosure; merge review is therefore too late to be the primary IP gate.

## Mandatory rule

No person, model, agent, automation or external tool may push new substantive protocol, research, architecture or implementation material to this repository until an explicit human IP/publication review has approved the exact material for public disclosure.

Development of unreleased or potentially IP-sensitive material must happen in a private repository or other non-public workspace. Only the minimum approved interoperability surface may be promoted here.

## Public by design

The approved public surface is limited to material required for independent PEACE interoperability:

- normative core protocol semantics;
- public envelope schemas;
- public conformance vectors;
- licensing, governance, contribution and security process;
- released interoperability corrections and clarifications.

## Not public by default

A separate explicit publication decision is required for material that is not necessary to implement or verify the released interoperability contract, including:

- unpublished research, derivations, discovery lineage or experimental results;
- proprietary mechanisms, implementation strategies or non-normative system composition;
- internal topology, dependency relationships, sequencing, roadmaps or commercial plans;
- cross-project synthesis that materially reduces the search space around protected work;
- partner/customer material, private data, credentials, internal thresholds or assurance methods.

The public exclusion list is intentionally expressed as information classes rather than a catalogue of protected project names, research directions or internal components.

## Review test

Before promotion to this public repository, the reviewer must answer:

1. Is every disclosed element necessary for interoperability, adoption, auditability or a deliberate public standard claim?
2. Could the material be combined with other public artifacts to reconstruct protected work?
3. Does disclosure weaken patent, trade-secret, licensing, standards, negotiation or competitive position?
4. Can the same public objective be achieved with less disclosure?
5. Has the exact proposed public diff, not merely its topic, been reviewed?

If any answer is uncertain, do not push the material here.

## Secondary CI gate

Public CI checks generic publication hygiene, required protocol artifacts, schema/conformance validity and obvious credential material. Protected IP/research policy must be evaluated before public push using a private policy source; a public deny-list or reversible fingerprint catalogue would itself create disclosure risk.

CI is defense in depth only. It does not replace pre-push IP review because a failed branch in a public repository is already public.
