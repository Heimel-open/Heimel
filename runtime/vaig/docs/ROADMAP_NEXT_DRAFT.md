# ROADMAP — DRAFT / forslag (2026-08-05)

Status: DRAFT — forslag til gjennomgang. Ikke et akseptert bygge-anchor.
Repo: `nsolland/VAIG` · Base: `main` (`53c96c1`)
Prinsipp: hver leveranse får eget synlig anker (branch + draft PR + SHA) før endring, i tråd med VALO-koordinasjonsprinsippene. Ingen leveranse attesterer seg selv.

## Utgangspunkt

- `vaig/aarm.py`: kanonsk AARM (6-verdikter) er nå koblet inn i API, orchestrator og agent_loop; monoton latching, replay, rate, digest og MODIFY-kontrakt på plass.
- Eksperimenter (swarm, vaig_embedded) er tatt ut av levende kode.
- 766 tester grønne, versjon 0.3.0.
- Deferred/draft i `TEST_EVIDENCE.md` §5 er fremdeles **ikke** produksjon.

## Prinsipp for rekkefølge

Billigst + størst sikkerhetsverdi først. D1 og D2 lukker fail-closed-hull i *eksisterende* runtime. D3–D5 er nye evner som krever egen design/audit og skal ikke haste-inn.

---

## D1 — WHY Gate runtime-kabling

**Problem:** WHY Gate v2 (4-dimensjons score, min-aggregasjon, hash-kjede) er implementert og testet (`tests/test_why_gate_runtime.py`) men påvirker ikke runtime-verdikten. `should`-forklaringen når ikke AARM-receipten.

**Scope:**
- Definer hvordan WHY Gate-scoren bindes inn i `AARMSignal` (forslag: avledet `observation_trust`/`evidence_valid`-komponent + eksplisitt `why_gate`-felt i `AARMSignal`).
- Bind forklaringen inn i `AARMDecision`/digest slik at "why" er tilgjengelig i receipten.
- Ikke la WHY Gate få egen verdiktmakt — den skjerper AARM-signalet, aldri overstyrer.

**Akseptkriterier:**
- [ ] WHY Gate-score endrer AARM-verdikt på dokumentert, deterministisk måte.
- [ ] Forklaringen er en del av `AARMDecision` og digestet.
- [ ] Nye tester: WHY Gate lav → lavere tillit → DEFER/STEP_UP-rettede utfall; WHY Gate høy → uendret.

---

## D2 — Unknown-fallback runtime-kabling

**Problem:** "unknown" skal falle lukket til HALT i runtime, men er i dag bare dekket i enkelttester (`test_unknown_fallback.py`).

**Scope:**
- Inventar over alle "unknown"-utføringsveier (instrumenter, evidensstater, API-input, orchestrator).
- Koble hver til kanonsk AARM HALT; ingen "unknown" kan resultere i ALLOW/MODIFY.
- Eksponer HALT-årsak i receipt/digest.

**Akseptkriterier:**
- [ ] Ingen unknown-state gir ALLOW/MODIFY i orchestrator eller agent_loop.
- [ ] Tvunget unknown → HALT med digest i API, orchestrator og `vaig_gate`.
- [ ] Tester for hver utføringsvei.

---

## D3 — On-chain WORM-receipts

**Problem:** WORM-kjeden er lokal og kan bare verifiseres med intern tilstand.

**Scope:**
- Eksportgrensesnitt for verifiserbar kjede (commitment/Merkle) uten intern tilstand.
- Ekstern verifiserbarhet av kjede-integritet (uavhengig av VAIG-instansen).
- Behold eksisterende `WORMLog`-kjede som kilde; legg til verifiseringsprotokoll på toppen.

**Akseptkriterier:**
- [ ] Tredjepart kan verifisere kjeden uten tilgang til VAIG-lagring.
- [ ] Tampering detekteres i ekstern verifisering.
- [ ] Test: utvidet kjede → ekstern verifiserer OK; tuklet → avvist.

---

## D4 — ZK-terskelbevis

**Problem:** "minst k av n godkjente" uten å avsløre hvem — avhenger av en signaturmodell som ikke finnes i levende kode (swarm ble tatt ut).

**Scope:**
- Avgrens til ett proof-schema med dokumentert threat model.
- Avhengig av fornyet signaturmodell; vurdér å holde som research inntil signaturprimitiv er audited.
- Ikke produksjon før uavhengig audit.

**Akseptkriterier:**
- [ ] Proof verifiseres av tredjepart.
- [ ] Signatur-/bevisprimitiv er audited; ellers holdes research-only (claim-discipline).
- [ ] Dokumentert threat model.

---

## D5 — Distributed Council

**Problem:** koordinert beslutningsorgan på tvers av instanser — størst scope.

**Scope:**
- Begrenset pilot: konsensus- og stemmegrensesnitt for autorisasjon.
- Bygg på RACS/REHT-grensesnitt, ikke egne semantikker.
- Ikke kritisk sti før D1–D3 er lukket.

**Akseptkriterier:**
- [ ] Pilot med dokumentert konsensusprotokoll og stemmekvitteringer.
- [ ] Verifiserbar, audited; ellers pilot-only.
- [ ] Ikke-claim: distribuerte vedtak er produksjons-garanterte.

---

## Cross-cutting

- Alle leveranser får eget branch + draft PR-anchor før kode.
- `TEST_EVIDENCE.md`-tall oppdateres per leveranse (krav: faktisk kjøring, ikke historiske).
- Roadmap-elementene er **ikke** feil i nåværende kode — de er nye evner/designvalg.
- Foreslått rekkefølge: **D1 → D2 → D3 → (D4 research) → D5 pilot**.

## Non-goals

- Ikke hevde produksjonssikkerhet for ZK/Council før uavhengig audit.
- Ikke gjeninnføre swarm/vaig_embedded i levende kode uten full bygging.
