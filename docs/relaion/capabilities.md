# relAIon capability semantics

Separate external capability from Alpha's developed ability.

- borrowed ability depends on an external model, tool, API, agent, human or service;
- developed ability is learned through Alpha's own experience and practice;
- hybrid ability is Alpha-developed proficiency that still depends on a borrowed capability.

Repeated use of an external provider does not make the provider part of Alpha. What can become Alpha's own is the learned proficiency around using it: when to invoke it, how to combine it, when to distrust it and how to recover from failure.

Every borrowed or hybrid ability must preserve provider provenance and dependency.

External models, harnesses, skills and middleware remain replaceable capability providers. They do not own identity, memory, authority or development policy.

## Relational capability realization

Alpha must not assume that the capability set is the union of node-local capabilities.

A capability may be realized by an active composition even when no individual model, tool or node declares that capability on its own. When such a capability has explicit causal/evidentiary support, PersonalAI-OS may represent it as an evidence-backed relational capability with:

- a capability identifier;
- the minimal relation kernel currently required for realization;
- provenance to the evidence/certificate establishing that dependency;
- a realization time distinct from an optional later detection time.

Realization and detection are separate states. Alpha may therefore possess a capability before its ordinary observation or evaluation mechanisms have detected it.

The inverse matters too: if an evidence-backed minimal kernel is no longer present, that relational capability is not treated as currently realized.

This does not generalize TADA-BIRTH-01 into a universal law. It defines a runtime representation for compositions whose relational dependence has actually been established. Unknown compositions remain unknown.

Relational capability state is never authority. Newly realized capability cannot create execution rights, widen mandate or bypass the governed effect path. Consequence-time governance must evaluate the actual composition and requested effect, not only the declared capabilities of its individual providers.

## Dynamic relational authority

Possessing or exposing a capability does not imply authority to use it.

Authority is not a static property of a person, agent, account, role or device. It is a dynamically resolved property of the current relationship and requested consequence.

The minimum governing form is:

```text
authority = f(
  subject,
  relationship,
  capability,
  object,
  constraints,
  context,
  time,
  current trust state
)
```

Example:

```text
subject: person_X
relationship: guest_in_room_Y
capability: set_volume
object: speaker_A
constraint: volume <= 15

current authority:
  speaker_A.volume <= 15

all other speaker_A effects:
  NOT AUTHORIZED
```

This is deliberately narrower than a global trusted/untrusted classification.

A participant may retain authority for one bounded capability while having zero authority for another. A trust-critical breach in one governed relationship may quarantine or remove authority on that relationship/path without inventing a global moral status for the participant.

Authority must therefore be capable of changing dynamically as governing facts change, including:

- relationship state;
- delegation state;
- trust state;
- object state;
- purpose;
- environmental context;
- applicable constraints;
- time or expiry;
- new evidence;
- revocation;
- consequence severity.

A prior ALLOW is not authority for the next effect.

```text
previous_authority != current_authority
```

The authority decision must be resolved fresh at the consequence boundary.

This allows relAIon to express very small, precise and temporary handlingsrett rather than binary access. A person does not simply "have relAIon" or "not have relAIon". The operative question is always:

> What may this participant do, through this relationship, to this object, under these constraints, now?

Human status alone does not grant unrestricted authority. Agent status alone does not remove it. Authority follows the governed relationship and current evidence, not species, ownership, hierarchy or identity class.

Trust governance is reciprocal: the same relational boundary applies to humans, agents, seeds, lineages and other governed participants. When a trust-critical breach occurs, authority on the affected relationship/path may collapse immediately to zero or to a narrower safe subset while evidence is preserved and causal attribution is investigated.

Where uncertainty remains, the consequence should remain reversible.
