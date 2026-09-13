# From fixed points to fixed classes

Dato: 2026-06-24
Status: syntese-note / forskningsretning
Claim maturity: M1 konseptuell, M2 der formell mapping er eksplisitt
Scope: Tofoo / LIM / Framleis / persistence grammar

## Kjerne

Tidlegare formulering:

```text
Identitet er det som forblir invariant.
```

Dette er nyttig, men kan bli tautologisk.

Sterkare formulering:

```text
Stabil identitet er medlemskap i ein ekvivalensklasse som blir bevart under deklarerte transformasjonar.
```

Enda kortare:

```text
No identity without declared transformation.
```

eller:

```text
Persistent identity is meaningful only relative to an admissible transformation class and preserved equivalence criteria.
```

## Kvifor dette er betre

Identitet er sjeldan eitt fikspunkt.

Oftare er identitet ein klasse:

```text
universality class
isomorphism class
topological conjugacy class
attractor basin
phase regime
autopoietic organization
persistent homology class
causal-state equivalence class
```

Det viktige er ikkje at systemet returnerer til nøyaktig same punkt.

Det viktige er at systemet blir verande innanfor same klasse under tillaten endring.

## Minimal grammatikk

Alle seriøse påstandar om vedvarande identitet bør deklarere:

```text
S  = state space
T  = admissible transformation class
~  = equivalence relation
I  = invariant set / preserved structure
C  = collapse condition
```

Ein identitetspåstand er svak eller tom dersom han ikkje seier:

```text
Kva kan endrast?
Kva må bevarast?
Kva tel som same klasse?
Når bryt identiteten saman?
Korleis blir dette oppdaga?
```

## Eksempel

Renormalisering:

Identiteten er ikkje mikroskopiske detaljar, men universalitetsklassen som blir bevart under coarse-graining og skalaendring.

Dynamiske system:

Identiteten er ikkje eitt punkt, men kvalitativ dynamikk, topologisk ekvivalensklasse, invariant manifold eller attraktor-basseng.

Genregulatoriske nettverk:

Cellens identitet er ikkje molekylmengda i eitt øyeblikk, men eit stabilt regulatorisk regime eller attractor i ekspresjonslandskapet.

Autopoiesis:

Organismen er ikkje same materiale over tid. Identiteten ligg i operasjonell lukking og sjølvvedlikehaldande organisasjon.

Termodynamikk:

Ein fase er ikkje ein partikkeltilstand, men eit stabilt regime i state-space med definerte overgangsbetingelsar.

AI governance:

Ein agent eller arbeidsflyt kan endrast utan å miste identitet berre dersom policy, authority, evidence, audit trail og accountability-kjede blir bevart.

## Kobling til Tofoo

Framleis:

```text
Det som fortsetter å vere seg sjølv gjennom endring.
```

LIM:

```text
Invariant-bevarande transformasjon over tid.
```

Ny presisering:

```text
LIM handlar ikkje berre om å bevare invariantar.
LIM handlar om å erklære kva transformasjonar som er admissible, og kva klasse systemet må bli verande i.
```

Dette flyttar Tofoo frå:

```text
fixed point
```

til:

```text
fixed class
```

## Forskningsbidrag

Det nye bidraget er ikkje at invarians finst.

Det nye bidraget er ei persistence grammar:

```text
Vedvarande identitetspåstandar er ugyldige eller ufullstendige utan deklarert transformasjonsklasse, bevart invariantsett, ekvivalenskriterium og kollapsbetingelse.
```

Dette gjer Tofoo meir publiserbart enn ein brei påstand om universell lov.

Det blir eit minimalt rammeverk for å vurdere identitetspåstandar på tvers av felt.

## Falsifisering

Ein lokal identitetsmodell blir svekka dersom:

```text
1. Identitet held fram sjølv om deklarerte invariantar blir øydelagde.
2. Invariantane blir bevarte, men systemet blir likevel ikkje vurdert som same identitet.
3. Transformasjonsklassen blir vald post hoc for å redde påstanden.
4. Kollapsbetingelsen ikkje kan spesifiserast før observasjonen.
```

Dette er viktig:

```text
Invarians åleine er ikkje nok.
Transformasjonsklassen må vere deklarert før testen.
```

## Arbeidssetningar

```text
No identity without declared transformation.
```

```text
Identity is not a fixed point. Identity is membership in a preserved class.
```

```text
A system persists when admissible transformations preserve its defining equivalence class.
```

```text
If you cannot say what may change, you cannot say what remains the same.
```

## Kort konklusjon

Tofoo bør ikkje leite etter ein ny total lov først.

Tofoo bør formulere grammatikken for vedvarande identitet:

```text
state space
admissible transformations
equivalence relation
invariants
collapse condition
```

Det er her konsiliensen blir presis.

Ikkje fixed point.

Fixed class.

Tofoo. Phi.
