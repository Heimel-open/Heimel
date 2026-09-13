# PEACE certified recovery federation

PEACE recovery MUST provide a humanly credible place to turn when access is lost without turning that support layer into a sovereign owner of the actor or domain.

> Sovereignty without support feels like abandonment.

The recovery service layer therefore uses a certified, rotating federation of independent recovery providers.

## Core invariant

> Loss of access must permit recovery of control without permitting transfer of identity.

No single recovery provider may be sufficient to restore control. Recovery requires a current quorum of independently certified providers bound to the current federation epoch.

## Provider certification

A PEACE-compatible recovery provider may be certified against a conformance profile covering at minimum:

- operator independence;
- dual-control / no single-employee recovery;
- inability to read sovereign state as a condition of providing recovery;
- strong identity-verification procedures;
- revocation and incident handling;
- auditable recovery receipts;
- liability and accountable legal identity;
- conformance with recovery quorum and compartmentalization requirements.

Certification is evidence of conformance, not authority to recover an actor by itself.

## Rotating federation

Recovery providers are assigned to a versioned recovery epoch. Provider membership MUST rotate under a governed policy so that a historical provider set cannot remain a permanent attack surface.

A stale recovery request bound to an old epoch does not silently inherit recovery authority. It is deferred until current federation state is established.

Rotation must preserve the configured minimum number of independent providers.

## Compartmentalization

Recovery providers MUST NOT receive the complete federation membership list merely because they participate in recovery.

Each provider receives only the information necessary to perform its own recovery role and an opaque reference to its current slot or cohort. Peer membership is not a capability granted by default.

This reduces the ability of one compromised provider to identify, target or coordinate against every other provider required for recovery.

Compartmentalization is not anonymity against the governed resolver. The PEACE domain must still be able to establish that the required current certified quorum exists without disclosing the complete provider graph to each participant.

## Quorum

Recovery is admitted only when all of the following are established:

1. the request is bound to the current recovery epoch;
2. the configured minimum federation size is at least two and, in normal profiles, three or more;
3. the recovery quorum requires at least two independent providers;
4. each contributing provider is currently certified and not revoked;
5. each provider occupies a currently valid recovery slot;
6. duplicate provider identities do not count twice;
7. the resulting recovery transition is admitted through the governed state boundary and produces a receipt.

A single provider, single employee, single device, single credential or single cloud account MUST NOT be able to transfer control of the actor.

## Human support layer

A user may still experience recovery as one clear human service:

> If you lose access, call your recovery service.

That front door may coordinate the process, but it must not collapse the underlying independent quorum into one sovereign operator. The coordinator can help the user through the process; it cannot unilaterally become the user, decrypt the user's state or manufacture recovery standing.

## Relationship to PEACE state replication

Recovery federation and state replication solve different problems:

- replication preserves valid governed state and lineage across device/provider loss;
- recovery federation re-establishes control over that domain when normal access credentials are lost;
- neither replica possession nor recovery-provider participation creates sovereignty by itself.

The actor remains **Framleis** across device replacement, credential revocation, provider rotation and successful recovery.

## Canonical reduction

> A recovery provider can help you get back to yourself. It cannot become you.

> No single provider knows or controls the whole recovery path.
