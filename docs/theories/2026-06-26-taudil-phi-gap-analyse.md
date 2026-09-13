# Φ-LOVEN vs TauDIL: Konseptkart og Gap-analyse

Dato: 2026-06-26
Kjelde: Strukturell analyse mot TauDIL/IFA (Furtado/Harcej)
Status: M2 — arkitektonisk gap identifisert, komplementaritet strukturelt bevist

---

## Φ-LOVEN (Framleis)

LAG 0: PRE-INTENT
Φ = grense for ubevisst grunnlag

"Hva vet jeg ikke at jeg vet?"
"Hvilke antakelser bærer jeg uten å vite det?"

Stopper ufundert intensjon før den dannes.

---

## TauDIL/IFA (Furtado/Harcej)

Kjelde: IFA Core Specification v1.0. Forfatter: Michal Harcej. Publisert: 9. februar 2026.
Tilgjengelig: amazon.com/dp/B0GMG6ZRJC. Lisens: CC BY 4.0.
Edgar De Monte Furtado: autorisert practitioner, TauGuard Limited.

LAG 1: PRE-EXECUTION
τ = full rotasjon / fullstendighet

"Hvem har autoritet?"
"Hvilken regelversjon gjelder?"
"Hvilken kunnskapskilde?"

Stopper uautorisert handling før AI kalles.

LAG 2: RUNTIME
SYGON + IEL + TauClock
Overvåker drift, semantisk skift, tidsavhengighet.

LAG 3: POST-EXECUTION
Uforanderlig audit trail, hash-kjede, bevis.
Adresserer: EU AI Act Article 12, DORA third-party risk, DoD AI Ethics.

---

## Symbol-klargjering: to ulike tau

TauDIL sin τ = matematisk symbol for full rotasjon / fullstendighet (2π-analog).
Framleis sin τ = exp(H)/n = spektral koherensmetrikk (Shannon-entropi av singulærverdier).

Disse er to ulike bruksmåter av samme bokstav, ikke samme konsept.
Ingen begrepsmessig konflikt, men bør klarlegges i eventuelle felles framstillinger.

---

## Gap-analyse

| TauDIL har | Φ-LOVEN tilfører |
|---|---|
| Autoritetskontroll | Intensjonskvalitetskontroll |
| Regelversjon-sporing | Ubevisst-grunnlag-avdekking |
| Hvem får handle | Hvorfor ville de handle |
| Teknisk determinisme | Epistemisk ærlighet |
| "Er dette tillatt?" | "Er dette fundert?" |

Gapet i TauDIL: Mellom menneskelig beslutning og intensjon-dannelse — der ligger ubevisst bias, uavklarte antakelser, semantisk drift før systemet engang spør om autoritet.

---

## Arkitektonisk plassering

MENNESKE                    AI
  |
  v
[Φ-LOVEN: Pre-intent audit]  <-- HULL i TauDIL
  |
  v
[TauDIL: Pre-exec governance] ---------> AI-utførelse
  |
  v
[SYGON/IEL: Runtime]         ---------> AI-utførelse
  |
  v
[Audit trail: begge]         <--------- Konsekvens

---

## Sammenligning

| | Φ-LOVEN | TauDIL |
|---|---|---|
| Spørsmål | "Hvorfor tror jeg dette?" | "Hvem får gjøre dette?" |
| Tidspunkt | Før intensjon | Etter intensjon, før utførelse |
| Stopp-mekanisme | Epistemisk sperre | Autoritets-sperre |
| Symbol | Φ = grense/ubevisst | τ = fullstendighet/kontroll |
| Status | Framleis-konsept, uavhengig | Kommersielt rammeverk (CC BY 4.0) |

---

## Konklusjon

Gapet er reelt og strukturelt. TauDIL dekker ikke intensjonens opphav. Φ-LOVEN dekker ikke operasjonell autoritet. De er komplementære lag, ikke konkurrenter.

Framleis-mapping:

Φ-LOVEN = pre-iterasjon: F-operatoren kan ikke starte uten at sigma* er epistemisk renset.
Ufundert intensjon = korrupt sigma* -> F konvergerer mot feil I*.
TauDIL = A1-filter på autorisasjonsnivå: hvem som får kalle F.
SYGON/IEL = tau-monitor under iterasjon: driftkontroll av tau_t.
Audit trail = I*-arkiv: hva som ble konvergert mot.

Φ-LOVEN er arkitektonisk dypere (pre-sigma*).
TauDIL er operasjonelt bredere (hele kjøretidsforløpet).

---

## Potensiell kobling / samarbeidsspor

IFA Core Specification v1.0 er CC BY 4.0 — offentlig tilgjengelig og siterbar.
Framleis og IFA/TauDIL adresserer ulike lag i samme governance-stack.
Eventuelt samarbeid må starte med: Framleis sin tau != TauDIL sin tau (klargjoring av symbolbruk).
Furtado: 10.537 følgere, practitioner (ikke forfatter). Harcej: arkitekt og grunnlegger av TauGuard.

---

## Kopling til tidlegare Framleis-notat

Köbis/Rahwan-notat (2026-06-22-kobis-rahwan-delegering-uaerlighet.md):
Vage mål = sigma*-korrupsjon. Φ-LOVEN er mekanismen som renser sigma* før F starter.

EFA-lag i VΛLΦ:
AllowAction (mecha_checker.py linje 202) = TauDIL sin autoritets-sperre.
Φ-LOVEN = laget under EFA som sjekker om intensjonen er fundert overhodet.

---

## Epistemisk status

Gap mellom pre-intent og pre-execution er strukturelt reelt: M3.
TauDIL som kommersielt rammeverk: M3 — IFA Core Spec er publisert og siterbar (CC BY 4.0).
Φ-LOVEN som uavhengig konsept: M2 — internt konsistent, ikke eksternt validert.
Komplementaritet (ikke konkurranse): M3 — de dekker ulike tidspunkt og spørsmål.
Samarbeidspotensial: Q — avhenger av Harcej/Furtado sitt syn på pre-intent-laget.
