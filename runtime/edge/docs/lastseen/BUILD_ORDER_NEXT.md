# Kanonisk byggordre: VALO Edge

Status: ACTIVE
Repository: `nsolland/valo-edge`
Canonical base: `4763e06bcf94c0048cf25a98845184c2337ceb0c`

## Produktidentitet

VALO Edge er produktområdet. Tiny Edge er profilen for begrenset maskinvare. micro-REHT er den lokale deterministiske autorisasjonskjernen. TinyLLM og små multimodale modeller er utskiftbare forslagsgivere uten autoritet. Device gateway er mekanisk enforcement og ikke et LA-lag. Veritas Edge registrerer etterprøvbar evidens om autorisasjon, enforcement og observert konsekvens. LastSeen er første produktdemo, ikke selve kjernen.

## PR 1 — Repository truth og Edge Contracts V1

Status: MERGED
PR: `#8`
Merge SHA: `7764f9b20d289b4c5846ee81ae7c665e9c5d7248`

Levert:

- kanonisk UTF-8 JSON-serialisering og stabile digests
- versjonerte proposal-, evidence-, clearance-, enforcement- og observation-kontrakter
- binding av action, device, modell, firmware, runtime, sensorgrunnlag, fysisk state og authority envelope
- signaturfelt, key-ID, boot-epoch, sequence og gyldighetsperiode
- repository hygiene og testvektorer

## PR 2 — Local VAIG Edge Profile

Status: MERGED
PR: `#10`
Merge SHA: `4f418b5180490752ba3212dd47b87aad15dbd4cc`

Levert:

- deterministisk Local VAIG-evaluator
- kanonisk EdgeEvidenceV1 bundet til proposal
- device-, firmware-, runtime-, modell- og sensorproveniens
- freshness, fysisk state og state-konsistens
- eksplisitt model-free path
- MISSING, STALE, CONTRADICTORY og UNTRUSTED evidensgap
- ingen autorisasjonsbeslutning i VAIG

## PR 3 — micro-REHT V1

Status: MERGED
PR: `#11`
Merge SHA: `b7510ecaf0211bbf9c122550ff4de7f5e77c1b04`

Levert:

- signert offline authority envelope
- eksakt device-, action- og parameterscope
- modell-, firmware-, runtime-, sensor- og state-binding
- use-, rate-, energy-, duration- og value-budsjett
- begrensede, forbrukbare permits
- replay-, mutasjons- og sequence-beskyttelse
- persistent HALT og eksplisitt recovery
- model-free autorisasjon når modellen ikke deltar

## PR 4 — Device Enforcement Gateway V1

Status: MERGED
PR: `#14`
Merge SHA: `4763e06bcf94c0048cf25a98845184c2337ceb0c`

Levert:

- verifisert ALLOW-clearance som eneste drivervei
- eksakt proposal-, clearance-, permit-use- og device-command-binding
- permit konsumert før driverkall og aldri gjenopprettet ved driverfeil
- duplicate command og permit-use blokkert
- DENY, DEFER, STEP_UP og HALT når aldri driver
- faktisk driverutfall bevart som executed, partial, failed eller timeout
- EdgeEnforcementV1 for Veritas-observasjon
- mekanisk gateway uten policy, evaluering eller autoritet

## PR 5 — Veritas Edge V1

Status: IN PROGRESS
PR: `#15`
Branch: `feat/veritas-edge-v1`
Base SHA: `4763e06bcf94c0048cf25a98845184c2337ceb0c`

Leveransen skal:

- registrere authorization receipt før gateway-konsekvens
- registrere enforcement receipt fra gateway-grensen
- registrere execution observation etter driverutfall
- bevare epistemisk skille mellom driver-rapport, gateway-avvisning og timeout-usikkerhet
- lagre append-only lokal hash-kjede med durable JSONL-arkiv
- binde reboot gjennom boot-epoch og forrige tail-digest
- registrere failure-, partial- og compensation-evidens
- eksportere selvverifiserbar og attestert edge evidence package
- registrere sentral reconciliation uten å gi Veritas autoritet

Gate: Evidenskjeden skal lokalt kunne verifisere hva som ble autorisert, hva gatewayen aksepterte, hva driveren rapporterte, og når gatewayen avviste før driverkall. Timeout skal forbli UNKNOWN, aldri omskrives til «ikke utført».

## Neste leveranser

1. Offline Authority State
2. Første fysiske konsekvensdemo
3. Rust/C Tiny Edge Core
4. OEM SDK og conformance

## Sluttgate

VALO Edge Core er klar for OEM-pilot når modellen ikke har direkte vei til aktuator eller styrt lagring, autoritet er eksplisitt og forbrukbar, proposal/clearance/device command er kryptografisk bundet, replay blokkeres over restart, HALT er lokalt og persistent, faktisk konsekvens dokumenteres med eksplisitt evidensnivå av Veritas, og Python/Rust består samme conformance-vektorer offline.
