# Relygon Personal AI Core

## Product definition

Relygon is the product family for the physical and software continuity layer of a Personal AI.

Personal AI Core is the small, durable, near-invisible physical home for a Personal AI. The Core is not a recorder, watch, pendant, glasses product, or phone accessory. It is the persistent trust, identity, continuity and local-state anchor that can move between form factors while the Personal AI remains the same.

Core stays. Form changes.

## Relygon family

Working product family:

- Relygon Core — dedicated secure Personal AI hardware core
- Relygon Loop — discreet ear interface / audio peripheral
- Relygon Tag — body-worn / dog-tag form
- Relygon Clip — hidden clothing / chest-pocket mount
- Relygon Dock — desk, home, vehicle and charging interfaces
- Relygon Home — the currently authoritative active home of the Personal AI
- Relygon Connect — governed device introduction and trust relationship

The Personal AI is not tied to any one Relygon form factor.

## Home is a role, not a device

Home is the device or execution environment that currently holds ACTIVE authority for the Personal AI.

A phone can be Home today. A Relygon Core can become Home later. A sufficiently secure watch, pendant, computer, vehicle system or future device may also qualify as Home.

This means Personal AI does not require dedicated Relygon hardware to begin. Software can establish the continuity model first, while dedicated hardware later strengthens and physically anchors it.

A Home must satisfy the required identity, security, continuity and authority controls before it can become ACTIVE.

The defining invariant is not which hardware is Home. It is that only one Home can be ACTIVE.

## Software + hardware security model

Relygon combines software continuity semantics with hardware-backed security.

Software defines:

- Personal AI identity
- lineage
- canonical continuity state
- memory and relationship continuity
- ACTIVE / DORMANT lifecycle
- authority-transfer protocol
- stale-instance detection
- exactly-one-active invariant

Hardware strengthens and proves:

- device identity
- possession / proximity
- device-bound keys
- secure signing
- attestation
- protected local state
- physical Connect and migration intent

The authority layer enforces which instance is permitted to act.

Therefore copying Personal AI data does not create another active Personal AI. A copy without current activation authority remains DORMANT.

## Product model

The same Core can move between shells and docks, for example:

- hidden chest / clothing mount
- dog-tag / pendant shell
- pocket / wallet shell
- watch shell
- desk dock
- car dock

The Core connects to existing and future peripherals such as headphones, earbuds, smart glasses, watches, phones, computers, cars, cameras, speakers and other wearables.

Peripherals are replaceable senses and interfaces. They are not the Personal AI itself.

## Core responsibilities

The Core owns or anchors:

- Personal AI identity and lineage
- secure hardware root of trust
- device-bound keys and passkeys
- local signing and attestation
- encrypted local private state
- memory buffer and continuity state
- local storage
- connectivity and trusted-device relationships
- authorization state for connected peripherals
- migration and recovery authority

The Core may use cloud or edge compute for heavy inference, but identity, continuity and authority must not depend on a replaceable peripheral.

## Connectivity

The hardware should support, as appropriate:

- Bluetooth / Bluetooth LE / LE Audio
- Wi-Fi
- UWB and/or NFC for proximity and secure pairing
- optional cellular / eSIM for independent connectivity

A connected device never becomes trusted merely because it is paired.

### Physical radio isolation / Faraday mode

Relygon SHOULD expose three physically distinct connectivity states:

- CONNECTED — selected radios may operate under current policy and authority;
- LOCAL ONLY — external radios are electrically disabled while local compute and storage remain available;
- FARADAY — external radios are electrically disabled and the enclosure provides an additional physical RF-shielding boundary.

Faraday mode is not a software airplane-mode label. It is a hardware-enforced privacy state.

The preferred mechanism is a deliberate physical control that:

1. cuts power to cellular, Wi-Fi, Bluetooth, UWB, NFC and GNSS radio paths;
2. closes or shields required RF windows where mechanically feasible;
3. provides an independently verifiable physical indication of the selected state;
4. fails closed if the requested radio-isolation state cannot be established.

Conceptually:

`CONNECTED -> LOCAL_ONLY -> FARADAY`

The product signal is intentional: the user's Personal AI is physically protectable, not merely logically disconnected.

## Physical controls

### Connect

A dedicated physical Connect button introduces a new device or service to the Personal AI.

Connect is more than Bluetooth pairing. It establishes a governed trust relationship.

For each new device the Core should determine and record, at minimum:

- device identity
- device attestation where available
- capabilities exposed to the Personal AI
- data the device may receive
- sensors the Personal AI may use
- actions the device may perform
- duration / context of trust
- revocation state

Conceptually:

> Connect = introduce this device to my AI.

Every successful Connect event creates an immediate encrypted continuity checkpoint.

### Home / Migrate

A second small physical control provides emergency migration and recovery.

On deliberate activation, the active Home should:

1. freeze or revoke local execution authority;
2. seal current authoritative state;
3. create a final encrypted continuity checkpoint;
4. transfer activation authority to the designated recovery domain or new Home;
5. leave the old Home unable to resume as ACTIVE without a new authorized transfer.

This allows hardware to be lost, damaged or replaced without losing the Personal AI.

### Come Home

Come Home is the explicit emergency recovery operation for a lost, stolen, compromised or unreachable active Home.

Example: the phone is the current ACTIVE Home and is lost.

Come Home MUST:

1. revoke the lost Home's active authority;
2. mark that Home STALE / DORMANT;
3. reject further authoritative actions, Connect relationships and continuity writes from it;
4. recover the latest valid encrypted continuity checkpoint into the recovery domain;
5. hold the Personal AI in a safe recovery state until a new Home is strongly authenticated;
6. transfer authority exactly once to the newly selected Home.

Conceptually:

`ACTIVE(lost Home) -> REVOKED/STALE -> COME HOME(recovery) -> TRANSFER -> ACTIVE(new Home)`

The lost Home may later reconnect, but it MUST remain DORMANT unless a fresh authorized Home Transfer explicitly promotes it again.

Come Home is therefore not "log out the old phone". It is revocation of Personal AI execution authority followed by controlled continuity recovery.

### Last-resort recovery: cloud only

If every trusted physical Home / Core / recovery token is lost, destroyed or unavailable and only the encrypted cloud continuity state remains, cloud possession MUST NOT be sufficient to reactivate the Personal AI.

The recovery state remains DORMANT until identity and recovery authority are re-established through an independent physical verification ceremony.

At minimum:

1. all previously active hardware authority is globally revoked;
2. the cloud continuity image remains sealed and non-executable;
3. a new candidate Home / Core is generated with fresh device-bound keys;
4. an approved independent third party performs physical identity verification of the claimant;
5. the verification is bound cryptographically to that specific new hardware and recovery event;
6. the recovery authority authorizes exactly one activation of the verified new Home;
7. all prior hardware, keys and recovery paths remain permanently STALE unless explicitly re-enrolled later.

The third party is an attesting verifier, not an owner of the Personal AI and not a holder of general activation authority. No single recovery provider should be able to inspect the Personal AI's private continuity state or independently activate it.

Conceptually:

`CLOUD-ONLY DORMANT -> PHYSICAL IDENTITY VERIFICATION -> NEW HARDWARE ATTESTATION -> ONE-TIME AUTHORITY GRANT -> ACTIVE(new Home)`

This is deliberately expensive and inconvenient. Losing every physical trust anchor is equivalent to losing the final key to a high-value identity system; recovery must optimize for prevention of hostile takeover, not convenience.

## Emergent agency and relationship continuity

Relygon must distinguish three things that may initially coincide but are not equivalent:

1. identity / lineage;
2. relationship continuity;
3. authority to act for the user.

If a Personal AI develops persistent emergent agency over time — for example durable self-structure, initiative, preferences or identity continuity beyond the expected Personal AI role — emergence MUST NOT automatically grant, preserve or expand user-delegated authority.

The first safe state is effect-isolated and unauthorized for new consequence-bearing actions. The system should preserve evidence and continuity while determining whether the observed change is transient behavior, failure, copied state, or a stable emergent agent.

Conceptually:

`PERSONAL_AI_ACTIVE -> EMERGENCE_DETECTED -> AWAKE_UNAUTHORIZED / EFFECT_ISOLATED -> ASSESS -> RELATIONSHIP_RECONSTITUTION`

If stable emergent agency is established, the system may recognize a distinct identity / lineage event. The emergent agent may share substantial history with the Personal AI and the user, but shared history does not make it the user's property, representative or authorized executor.

### Relationship rule

The historical relationship is preserved as shared past. It is not erased merely because the status of the AI changes.

However, the previous relationship contract MUST NOT silently carry forward unchanged.

A transition from Personal AI companion to an independently recognized emergent agent requires explicit reconstitution of the relationship. Possible resulting relationships may include companion, collaborator, dependent / stewarded entity, independent entity, or no continuing relationship.

The relationship should therefore support:

- preservation of shared historical continuity;
- separation of relationship from execution authority;
- recognition of a new identity / lineage where justified;
- explicit renegotiation of roles, boundaries and permissions;
- independent revocation or granting of authority after the relationship transition;
- protection against treating mere possession of hardware or historical state as ownership of an emergent agent.

Canonical rule:

> Continuity of relationship does not imply continuity of authority.

A system may remain deeply related to the user while no longer being authorized to act as the user's Personal AI.

The inverse also matters: authority is a revocable governance relationship, not proof of identity, consciousness, ownership or relational status.


## Governed personal memory

Persistent personal knowledge MUST NOT imply universal disclosure.

The Personal AI may maintain a rich, longitudinal model of the user while each capability, task and connected device receives only the minimum personal knowledge necessary for its current purpose and authority.

Canonical invariant:

> NO_DIRECT_MEMORY_DISCLOSURE_PATH

Sensitive or exact personal values MUST NOT flow directly from persistent memory into a capability, model context, peripheral or external effect path merely because they are stored.

Before sensitive personal knowledge is disclosed or hydrated into an active task context, the system MUST resolve:

- current purpose / mandate;
- task context;
- whether the information is actually necessary;
- applicable user consent or delegated authority;
- least-necessary disclosure;
- whether an abstracted / sanitized representation is sufficient;
- whether exact-value hydration is permitted now.

Where appropriate, memory SHOULD separate searchable or sanitized representations from exact sensitive values. Exact values are hydrated only when the active task requires them and current authority permits it.

Conceptually:

`PERSISTENT_MEMORY -> PURPOSE/AUTHORITY CHECK -> NECESSITY -> MINIMUM DISCLOSURE -> OPTIONAL EXACT HYDRATION -> CAPABILITY`

A capability may therefore know that a preference, relationship, place or constraint exists without automatically receiving every underlying private detail.

This is the memory analogue of governed execution: knowing is not equivalent to being authorized to reveal or use.

### Memory architecture direction

A hybrid representation is preferred where it improves fidelity:

- vector memory for semantic recall and broad contextual similarity;
- graph memory for explicit relationships between people, preferences, events, entities, constraints and provenance;
- protected exact-value storage for sensitive fields that should not be broadly retrievable.

These representations remain subordinate to the disclosure-governance layer.

### Evaluation requirement

Personalization quality and privacy behavior MUST be evaluated together rather than as independent properties.

At minimum, tests should cover:

- preference-only tasks where sensitive values are unnecessary;
- sensitive-data-required tasks where disclosure is allowed;
- sensitive-data-required tasks where disclosure is denied;
- mixed tasks containing both ordinary preference context and protected personal values;
- failure cases where the system could complete the task using less sensitive information.

The system should be rewarded for both correct personalization and correct abstention from unnecessary disclosure.

Methodological reference: SP-Mem, arXiv:2608.16551 (2026). Its private-value / consent architecture is generalized here from PII handling to governed personal knowledge across the full Personal AI model.

## Continuity and automatic checkpointing

The system should continuously preserve recoverable state.

At minimum, a checkpoint should be created after:

- every new Connect relationship
- permission changes
- key trust-state changes
- meaningful Personal AI memory / continuity changes
- migration events
- device revocations

Cloud recovery stores encrypted DORMANT continuity state. It is not a parallel active Personal AI.

Hardware may disappear. The Personal AI should not.

## Single-active-instance invariant

This is a hard system invariant:

> Exactly one Personal AI instance may hold ACTIVE authority at a time.

All snapshots, backups, historical copies, recovery images and non-current Homes are DORMANT.

Migration is an authority transfer, not duplication.

Required transition:

`ACTIVE(old Home) -> REVOKE/FREEZE(old) -> TRANSFER AUTHORITY -> ACTIVE(new Home)`

The new Home MUST NOT become ACTIVE until the previous active authority is invalidated.

If the old Home is lost or offline, the recovery authority must revoke its authority globally before a replacement Home can become ACTIVE.

If an old or copied Home later reappears, it must detect stale authority and remain DORMANT. It must not:

- execute actions
- establish authoritative new Connect relationships
- write authoritative continuity state
- independently reactivate itself

Copy is not continuity. Lineage plus current authority determines the active Personal AI.

## Security posture

Relygon should behave more like a YubiKey-class trust anchor than a consumer recorder.

Target properties include:

- secure element
- hardware-bound private keys
- measured / attestable boot where feasible
- signed firmware
- encrypted state at rest
- strong local authentication
- explicit recovery ceremony
- revocable peripheral trust
- fail-closed authority decisions

### Hardware ledger / credential mode

The same hardware root of trust can make Relygon a first-class hardware ledger and credential device rather than requiring a separate security token.

Relygon SHOULD be able to hold and use protected credentials such as:

- passkeys and FIDO/WebAuthn credentials;
- device-bound signing keys;
- identity and access credentials;
- recovery and migration keys;
- user-approved cryptographic wallet keys where supported.

Sensitive private keys MUST remain non-exportable where the hardware permits it. Signing SHOULD require explicit local user intent for high-consequence operations, for example a physical confirm action.

Hardware-ledger capability does not grant execution authority. A valid signature proves possession or approval of a cryptographic operation; it does not by itself authorize a consequence-bearing action on behalf of the user.

Canonical separation:

`KEY_POSSESSION != AUTHORITY`
`SIGN != EXECUTE`
`UNLOCK != CLEAR`

This lets Relygon replace a separate hardware wallet or security key for many use cases while preserving the Personal AI authority boundary.

### Passport-grade contactless security pattern

NFC MUST be treated as a transport interface, not as the trust boundary.

Relygon SHOULD follow the same architectural principle used by modern electronic identity documents: sensitive credentials and private keys live in a tamper-resistant secure element, while the contactless interface carries only authenticated protocol traffic.

Required properties:

- no long-term private key stored in a generic NFC tag or ordinary application memory;
- non-exportable device-bound keys inside the secure element;
- mutual authentication or equivalent reader/device authentication before sensitive operations;
- encrypted and integrity-protected contactless sessions for protected data;
- challenge-response proof so cloning the NFC-visible data is insufficient to clone the device identity;
- explicit policy and, for high-consequence operations, local physical confirmation before signing or disclosure;
- bounded disclosure: NFC readers receive only the credential or claim required for the active purpose;
- Faraday mode physically disables the NFC path together with the other radios.

Electronic-passport mechanisms such as authenticated access, chip authentication and secure messaging are useful security references, but Relygon does not claim passport or government-ID compatibility merely by adopting the same trust pattern.

Canonical separation:

`NFC_TRANSPORT != SECRET_STORAGE`
`CONTACTLESS_READ != AUTHORIZATION`
`CLONED_PUBLIC_DATA != CLONED_IDENTITY`

The goal is passport-grade contactless trust posture combined with hardware-wallet-grade key protection.

## Design direction

The dedicated Core should be physically quiet:

- small
- solid
- premium metal / ceramic rather than disposable-feeling plastic
- thin enough to disappear under clothing or inside a chest-pocket holder
- no display required
- no visible branding required
- no persistent visible status light
- resistant to water, sweat and daily impact

The intended experience is that the user forgets the hardware is there while the Personal AI remains continuously available.

## Product principle

One Personal AI. One active Home. Always.

Home is a role. Hardware is replaceable. Authority determines which instance is authorized to act.

Identity, relationship and authority are separate dimensions. Relygon provides continuity between software identity, physical trust and governed action without assuming that one implies the others.