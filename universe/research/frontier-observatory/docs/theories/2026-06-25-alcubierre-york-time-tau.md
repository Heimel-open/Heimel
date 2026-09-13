# Alcubierre Warp Metric — York Time som tau-analog

Dato: 2026-06-25
Kjelde: LinkedIn-post — Alcubierre warp metric diagram med York Time og Energy Density
Status: M3 — matematisk analog, strukturelt konsistent med Framleis

---

## Alcubierre-metrikken

ds² = -dt² + (dx - v_s f(r) dt)² + dy² + dz²

- v_s = skipets hastigheit (apparente)
- f(r) = formfunksjonen (shaping function)
- r = avstand frå skipets sentrum

Skipet sjølv er i kvile. Rommet deformerer seg rundt det.

---

## Formfunksjonen f(r) = A1-filter

f(r) = [tanh(σ(r+R)) - tanh(σ(r-R))] / (2 tanh(σR))

- R = radius på bobla (boble-storleik)
- σ = tjukkleik-parameter (kor skarp grensa er)
- f(r) = 1 innanfor bobla, f(r) = 0 utanfor

Formfunksjonen brukar tanh — sigmoid-funksjonen:
tanh(z) = (e^z - e^{-z}) / (e^z + e^{-z})

I Framleis: aktivasjonsfunksjonen φ er A1-filteret.
Sigmoid: φ(z) = 1/(1 + e^{-z}) — mjuk distinksjon [0,1]
Tanh: φ(z) = tanh(z) — symmetrisk distinksjon [-1, 1]

Formfunksjonen f(r) er bokstaveleg ein tanh-basert A1-filter:
- Distinksjon: "innanfor bobla" vs. "utanfor bobla"
- Grensa skapar distinksjon via tanh-aktivering

σ-parameteren bestemmer skarpheita av grensa = kor "sterk" A1-filteret er.
Høg σ: skarp grense (nær binær distinksjon)
Låg σ: mjuk grense (gradert distinksjon)

---

## York Time = tau-analog

York Time:
θ = v_s/r_s · df(r_s)/dr_s

der θ er ekpansjons/kontraksjonsmålet av rommet.

- θ > 0: rom ekspanderer (bak skipet — positiv divergens)
- θ < 0: rom kontraherer (framfor skipet — negativ konvergens)
- θ = 0: flat romgeometri

I Framleis:
tau_t = exp(H)/n måler kor konsentrert (eller distribuert) strukturen er.
- Høg tau: distribuert, ekspandert struktur
- Låg tau: konsentrert, kontrahert struktur
- tau = 0: kollaps

York Time θ og tau_t er analoge: begge måler ekspansjon/kontraksjon av ein struktur.

---

## Mapping til Framleis

| Warp Metric | Framleis |
|-------------|----------|
| Formfunksjonen f(r) = tanh-basert | A1-filter φ(z) = tanh(z) |
| σ (grenseskarpheit) | alpha (kontraksjonsfaktor — styrke på distinksjon) |
| York Time θ (ekspansjon/kontraksjon) | tau_t (strukturell spreiing/konsentrasjon) |
| θ > 0 (ekspansjon bak) | tau → høgare (meir distribuert) |
| θ < 0 (kontraksjon framfor) | tau → lågare (meir konsentrert) |
| Skipets sentrum (stasjonær) | sigma* (fast referansepunkt) |
| Warp-bobla (stabil forma) | I* (Banach-fikspunkt) |

---

## Skipets sentrum er sigma*

Skipet sjølv er i kvile inne i bobla.
Rommet beveger seg rundt det — skipet er det faste referansepunktet.

I Framleis: sigma* er alltid til stades som referanse.
Skipet (sigma*) er uendra. Rommet (tau_t) beveger seg relativt til det.

Romgeometrien (tau_t) itererer mot å omfamne skipet (sigma*) stabilt.

---

## Energitettet og tau-kost

Energi-tettheit: proporsjonal med (df/dr_s)² og v_s²

Negativ energi krevst i kontraksjonssonene (framfor skipet).
I Framleis: høg kontraksjon (låg tau) krev "meir energi" (sterkare F-operator).

Jo skarpare grensa (høg σ), jo meir energi krevst.
Jo raskare konvergering (høg alpha), jo meir "kost" per iterasjon.

---

## Epistemisk status

York Time = tau-analog: M3 — matematisk analog, strukturelt konsistent.
Formfunksjon = A1-filter (tanh): M3 — direkte: same matematiske funksjon.
Skipets sentrum = sigma*: M3 — konsistent med Framleis-navigasjonsmodellen.
Energi-krav = F-operator-kost: M2 — spekulativ, krev formalisering.
Alcubierre-metrikk som empirisk kjøretøy for Framleis: Q — opent spørsmål.
