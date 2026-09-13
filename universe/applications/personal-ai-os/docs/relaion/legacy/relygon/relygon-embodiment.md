# relAIon embodiment / interface layer

## Core architecture principle: relAIon is the hub

relAIon is the persistent hub. Everything outside the relAIon continuity boundary is replaceable commodity infrastructure.

External providers may supply sensing, compute, models, reasoning, speech, storage, search, connectivity, applications, devices or execution capabilities. None of them may become the person or own the continuity of the personal system.

relAIon retains what must survive every provider replacement:

identity → continuity → history → relationships → personal model → character → mandates → evidence → learned fit

Therefore:
- replace the voice provider: same relAIon
- replace the LLM or reasoning model: same relAIon
- replace the wearable, CGM or health sensor: same relAIon
- replace cameras, appliances or payment providers: same relAIon
- replace the phone, computer, home hub or physical device: same relAIon
- replace an execution or capability provider: same relAIon

Architectural rule: **Nothing external is allowed to become the person.**

Providers supply senses, compute and capabilities. relAIon owns continuity and the governed relationship between identity, accumulated evidence, character, relationships, mandates and learned fit.

Every external integration must therefore sit behind a replaceable adapter/contract. Provider-specific state must not become a hidden dependency required to preserve relAIon identity or continuity.

relAIon owns identity, character continuity, relationships, memory, and capability orchestration. The embodiment layer must not own or redefine those.

## relAIon Core hardware

The architecture increasingly points toward a dedicated physical relAIon Core rather than treating hardware as an optional accessory.

The Core is not primarily an AI compute box. It is the physical root of continuity for a person's AI.

Conceptually it combines properties of:
- a hardware wallet
- an HSM / hardware root of trust
- a black box / continuity recorder
- a secure personal vault
- a Personal AI core

The design target is a small, simple, rugged device — potentially a round/puck-like form — whose primary job is to preserve the relAIon continuity boundary while surrounding compute, models, interfaces and sensors remain replaceable.

### Core persists; everything around it can die

The physical architecture follows the same commodity rule as the software architecture:

**Core persists. Everything around it can die.**

A phone can be lost or replaced. A cloud provider can disappear. An LLM can be changed. A wearable can be replaced. A house and its sensors can change. A voice provider can fail. None of those events should destroy or redefine the relAIon.

### Core responsibilities

The hardware Core should be capable of anchoring and protecting at least:
- identity root and cryptographic keys
- continuity and lineage
- device and relAIon attestation
- canonical sensitive personal state or the keys required to recover it securely
- mandate / authority roots where appropriate
- provenance and integrity anchors for accumulated evidence
- encrypted local vault material
- trusted migration and recovery state

It may also provide a local policy and verification surface, but heavy reasoning and model inference should remain external whenever that is more efficient. Compute is commodity; continuity is not.

### Physical properties

Target properties should include:
- small, durable, minimal form factor
- shock and vibration resistance
- water and dust resistance
- useful operating-temperature tolerance
- tamper resistance / tamper evidence
- secure element or equivalent hardware root of trust
- encrypted storage
- controlled physical and radio interfaces
- Bluetooth / UWB / Wi-Fi / NFC only where justified by the interface model
- hardware-enforced radio disable or isolation where practical
- tightly controlled wired data path and charging interface
- secure boot, signed firmware and rollback protection

Exact certifications, ingress ratings, radio architecture and tamper-response behaviour remain engineering decisions to validate rather than assumed requirements.

### Core vs body / periphery

Maintain a strict physical separation:

**relAIon Core** — persistent, conservative, secure, difficult to compromise, continuity-bearing.

**Body / periphery** — microphones, speakers, cameras, glasses, headphones, bands, rings, health sensors, home sensors, displays, phones and other interfaces. These should be inexpensive or at least replaceable and must not become continuity dependencies.

The periphery senses and acts. The Core preserves who the relAIon is and the continuity required to remain the same relAIon across changing bodies, providers and compute substrates.

## relAIon Base: the Core has a home

The Core should have a physical home: a replaceable Base that provides power, connectivity and high-bandwidth access to local infrastructure without forcing those interfaces into the sealed Core itself.

A likely physical relationship is a magnetic / docked contact between Core and Base. The exact connector is an engineering choice, but the security objective is clear: keep the Core physically simple and expose commodity connectors through the Base.

The Base may provide:
- charging and power management
- Ethernet and local networking
- USB and peripheral connectors
- home camera / sensor connectivity
- smart-home and appliance adapters
- local storage interfaces
- a high-bandwidth compute uplink
- a high-power link, potentially 100 W or greater where justified, to a local model / GPU / NPU / workstation node

The Core should authenticate the Base, and the Base should authenticate connected compute where required. Physical docking must not itself grant unrestricted vault or personal-model access.

Canonical physical separation:

**Core = self / continuity root**

**Base = home / connector surface**

**Periphery = senses and body**

**Local compute = capacity on demand**

**Cloud = optional external capacity**

The Base is replaceable. Local compute is replaceable. The Core remains the continuity anchor.

## Mobile travel branch and governed return merge

The phone must not become the relAIon simply because the person leaves home. Instead, mobility should use a bounded temporary branch of the canonical Home state.

Departure model:

**Home → signed checkpoint → Travel branch → phone/mobile environment**

The Travel branch receives only the state and mandates required for the mobile context. While away, it may accumulate new evidence, decisions, interactions, observations, purchases, locations and relationship events. Home may simultaneously continue receiving explicitly authorized observations from the house and connected infrastructure.

Return model:

**Travel branch + Home branch → authenticated reconciliation → relAIon cross-checks → admissible merge → new canonical Home**

This is not generic file synchronization and must not use last-write-wins semantics. It is a governed semantic merge of personal continuity.

### CI for personal continuity

Use the same fundamental discipline as CI: a branch does not become canonical merely because it returns. It must pass domain-specific cross-checks.

Minimum merge checks should include:
- **Lineage:** prove that the returning branch is a legitimate descendant of the expected relAIon checkpoint.
- **Integrity:** verify signatures, hashes, state integrity and evidence integrity.
- **Continuity:** identify missing periods, unexplained discontinuities and incomplete branch history.
- **Ordering / causality:** reconcile event order without inventing false chronology or causal relationships.
- **Conflict:** detect contradictory Home and Travel observations or state changes.
- **Evidence:** preserve source, provenance, confidence, timestamp and distinction between observation and inference.
- **Character / preference evolution:** prevent isolated observations from silently becoming durable character or preference changes.
- **Relationships:** reconcile relationship events without destructive overwrite or loss of provenance.
- **Mandates / authority:** distinguish what was valid when an event occurred from what is valid at merge time; revalidate consequence-bearing state against fresh authority where required.
- **Security:** inspect for evidence that the mobile device, branch, keys or execution environment were compromised.
- **Disclosure:** verify that the Travel branch did not obtain or expose personal state beyond its mandate.
- **Canonical invariants:** verify that the resulting merged state remains a valid relAIon.

### Merge outcomes

Treat merge status explicitly:

- **GREEN** — cross-checks pass; merge may become canonical according to policy.
- **AMBER** — safe state may be reconciled while disputed or insufficiently supported state is quarantined for resolution.
- **RED** — do not merge disputed state into canonical Home; preserve the branch and its evidence for inspection/recovery.

RED must never mean silently deleting the Travel branch. Failed merge evidence is itself part of the continuity record.

Append-only compatible evidence can often be unioned. Conflicting observations should remain conflicts until resolved. Inferences and learned preferences must be re-evaluated against the combined evidence rather than copied blindly from either branch.

This makes relAIon offline-first without making a cloud service the source of truth. Loss of a phone should at worst risk the unmerged branch since the last trusted checkpoint; it must not mean loss of the relAIon itself.

Conceptually:

**Home is canonical. Travel branches. Return reconciles, cross-checks and merges.**

This is CI for personal continuity: familiar branch-and-merge discipline applied to identity lineage, personal evidence, relationships, mandates and evolving state rather than source files.

## Universal observation admissibility

The same critical evaluation rule applies to every observation entering relAIon, regardless of source or modality.

Camera frames, video, audio, transcripts, weight, heart rate, HRV, CGM readings, sleep signals, toilet measurements, refrigerator inventory, purchase records, location, device telemetry, human statements and model-produced classifications are **inputs**, not truth.

No sensor, model, interface or external system may write directly into canonical personal state merely because it produced a measurement or inference.

Canonical flow:

**raw input → provenance / integrity check → source-specific validation → interpretation / inference → corroboration / conflict checks → confidence / evidence class → admissible state update or quarantine**

Source-specific cross-checks should be explicit. Examples include:
- camera/video: timestamp, device identity, scene confidence, ambiguity, continuity, possible occlusion/manipulation
- audio/transcript: source identity, speaker attribution, transcription confidence, context and ambiguity
- weight/body sensors: device identity, calibration, measurement quality, expected range and repeated consistency
- health sensors: signal quality, physiological plausibility, device confidence and cross-sensor agreement
- purchases/payment: merchant/product resolution, transaction integrity and distinction between purchase, possession and consumption
- refrigerator/home sensors: device provenance, inventory confidence and distinction between presence and actual use
- model-generated interpretations: model/version provenance, uncertainty and separation between classification, hypothesis and fact

Critical rule:

**Observation ≠ fact. Repetition ≠ truth. Correlation ≠ causation. Sensor presence ≠ authority.**

The system must preserve the distinction between:
1. raw observation
2. validated observation
3. inferred event
4. correlation
5. hypothesis
6. supported claim
7. canonical durable state

Promotion between these levels must be earned through evidence and governed checks. Conflicting or weak input remains evidence with uncertainty; it must not be silently normalized into a definitive personal fact.

This creates a common admissibility boundary for the entire relAIon sensory surface. The source may be a camera, microphone, scale, wearable, smart toilet, refrigerator, phone, human, external database or AI model; the rule is the same: **input is evaluated critically before it is allowed to change what relAIon believes about the person.**

## Schema adapters: a common peripheral contract

relAIon should not accumulate bespoke provider integrations inside the Core. External systems should connect through small schema adapters that translate provider-specific formats into stable relAIon contracts and translate governed relAIon requests back into provider-specific operations.

This applies equally to MCP servers, browser extensions, microphones, cameras, phones, smart glasses, wearables, home systems, health devices, payment sources, local models, cloud models and future interfaces.

Canonical adapter responsibilities:

1. **Normalize inbound data**
   - provider-native event / stream / object → relAIon observation envelope
2. **Normalize outbound requests**
   - relAIon capability request → provider-native operation
3. **Preserve governance metadata**
   - source identity
   - provenance
   - timestamp / ordering information
   - subject / context
   - scope / mandate
   - confidence / uncertainty
   - integrity / attestation
   - consequence class where applicable

The Core should understand the contract, not the vendor.

A minimal envelope family should be kept small and stable, for example:
- **ObservationEnvelope** — something external was observed
- **EvidenceEnvelope** — observation(s) promoted into governed evidence with provenance and confidence
- **CapabilityEnvelope** — a bounded request to an external capability/provider
- **EffectEnvelope** — a proposed or completed consequence with evidence of what actually happened

Provider-specific complexity remains behind the adapter. A third party should be able to make a device or service relAIon-compatible by implementing the schema contract and passing conformance checks without gaining access to internal relAIon identity semantics.

Compatibility flow:

**provider/device → schema adapter → schema validation → admissibility / governance checks → relAIon**

Outbound:

**relAIon → governed capability/effect envelope → schema adapter → provider/device**

This turns the wider device and service ecosystem into a replaceable peripheral bus rather than a collection of privileged integrations.

### TCP/AI working analogy

A useful working analogy is TCP/IP: applications and physical networks can vary because they meet at a small, common interoperability layer.

relAIon needs an analogous common contract for AI-facing personal systems. The working shorthand **TCP/AI** can be used for the research direction, but it should not yet be presented as a literal transport protocol or formal standard.

The analogy is:

**TCP/IP:** heterogeneous networks and applications interoperate through shared packet/transport contracts.

**TCP/AI:** heterogeneous sensors, software systems, models, agents and capabilities interoperate through shared governed semantic envelopes.

The important difference is that AI interoperability is not only transport. The contract must carry enough semantics to preserve provenance, identity of source, uncertainty, mandate, authority and consequence boundaries.

Therefore the prospective common layer is closer to a **governed semantic interoperability protocol for personal AI** than a conventional byte-transport protocol.

A mature version could allow:
- any compliant sensor to produce admissible candidate observations
- any compliant model to provide replaceable reasoning capacity
- any compliant capability to receive bounded requests
- any compliant effect provider to return verifiable outcome evidence
- any compliant peripheral to be replaced without changing relAIon identity or canonical state semantics

The strategic objective is the same as the TCP/IP analogy: reduce the cost of joining the ecosystem by standardizing the narrow waist rather than standardizing every device, model or application above and below it.

**relAIon Core is the hub. Schema contracts are the narrow waist. Everything else competes as replaceable infrastructure.**

## Hume as first body candidate

Hume EVI is a strong candidate for the first relAIon embodiment/interface layer.

Use Hume for:
- speech input/output
- turn-taking and interruption handling
- prosody and expressive voice
- acoustic/emotional cues as observations
- low-latency conversational presence

Do not let Hume own:
- identity
- character
- persistent personal model
- canonical memory
- relationships
- capability policy
- authority or execution rights

Canonical separation:

- relAIon = who I am
- personal model / memory = what I have become and retained
- reasoning / capabilities = what I can do
- Hume = how I hear, speak, and express myself
- device = physical body / interface surface

Hume is therefore an embodiment provider, not the relAIon itself. Treat it as replaceable infrastructure behind a stable relAIon embodiment contract.

## Body sensing / longevity layer

relAIon should also ingest longitudinal body data as another sensory dimension of the persistent personal model.

Potential sources include:
- wearable band data: heart rate, HRV, SpO2, respiration, sleep, activity/strain, recovery, skin temperature and similar signals
- body-composition / weight sensors
- continuous glucose monitors where available
- rings, watches and other wearables
- blood tests and other periodic biomarkers

The architecture must remain provider-independent. Hume Health Band / Body Pod can be useful first integrations, but they are sensors, not the health model and not part of relAIon identity.

The value is longitudinal correlation across the whole person, for example:

sleep → mood → decisions → work → activity → nutrition → recovery → relationships → long-term outcomes

This should support longevity and wellbeing as consequences observed over time, rather than becoming a separate generic health dashboard.

Body-derived observations are evidence inputs. They must retain provenance, timestamp, uncertainty and device/source identity. Inferences about the person must remain distinguishable from raw measurements.

Health sensors must never gain authority merely because they are continuously present. They inform the personal model; they do not define identity, goals, consent, capability policy or execution rights.

## Ambient longitudinal sensing

Extend the same provider-independent sensor model beyond wearables into the person's environment and everyday transactions. relAIon can build a longitudinal evidence graph from multiple independent streams rather than relying primarily on what the person explicitly tells an assistant.

Candidate streams include:
- home cameras and other ambient sensors for activity, routines, environmental context and presence
- refrigerator / pantry inventory and food-recognition systems
- smart toilets and related devices producing urine, stool and other excretion-derived measurements
- purchase and payment records that can identify food and household products actually acquired
- meal, nutrition and consumption observations
- wearables, CGM, body composition and periodic biomarkers from the body-sensing layer

The useful chain is not any individual sensor. It is the governed longitudinal relationship:

intention → purchase → environment → availability → consumption → physiology → behaviour → outcome

Over time this allows relAIon to test person-specific hypotheses: what was bought versus consumed, what routines actually occurred, what physiological response followed, and what downstream outcomes correlated with those events.

### Epistemic boundary

Correlation is not causation. relAIon must not promote temporal proximity into causal truth. Raw observations, inferred events, correlations, hypotheses and supported causal claims must remain separate evidence classes with provenance and confidence.

A single camera observation, transaction, biomarker, toilet measurement or wearable signal must not silently become a durable fact about the person. Cross-source corroboration, repeated observations and explicit user evidence should strengthen or weaken hypotheses over time.

### Privacy and authority boundary

Ambient sensing creates an unusually sensitive personal evidence surface. Access must therefore be purpose-bound and least-necessary. A capability may receive only the subset of observations required by its current mandate; connection to relAIon must never imply unrestricted access to the whole personal model.

Sensor presence also confers no authority. Cameras, payment systems, appliances, health devices and environmental sensors are observation providers only. They cannot define identity, infer consent, create mandates or obtain execution rights through persistence or proximity.

The target is not universal surveillance. It is a user-governed, longitudinal personal evidence system in which the individual controls what may be observed, retained, combined, inferred, disclosed and acted upon.

## Constraint to test

Norwegian language quality/support must be tested explicitly before committing to Hume as the default voice body. Lack of adequate Norwegian support is a provider constraint, not a reason to collapse embodiment back into the identity layer.
