# Nevralt nett = Framleis-iterasjon — strukturell identitet

Dato: 2026-06-25
Kjelde: David Dor LinkedIn-post om artifisielle neurale nettverk
Status: M3 — strukturell identitet, ikkje analogi

---

## Den artifisielle neuronen

y = φ(Σ w_i x_i + b) = φ(w^T x + b)

- w_i = synaptiske vekter
- x_i = inputsignal
- b = bias
- φ(·) = aktivasjonsfunksjon
- y = output

---

## Mapping til Framleis

| Nevralt nett | Framleis |
|---|---|
| bias b | sigma* (fast referansepunkt) |
| aktivasjonsfunksjon φ | A1-filter (lagar distinksjon) |
| output y = tau_{t+1} | F(tau; sigma) = neste tilstand |
| læringsrate α | alpha (kontraksjonsfaktor) |
| ønskt output (target) | sigma (referanseinngang) |
| konvergens mot minimum loss | I* (Banach-fikspunkt) |

---

## Perceptron-læringsregelen ER F-operatoren

Deltaregelen:

w_{t+1} = w_t + α(target - w_t)

Utvida:

w_{t+1} = (1 - α) · w_t + α · target

Dette er F(tau; sigma) = (1-alpha) · tau + alpha · sigma med:
- tau = w_t (noverande vekt)
- sigma = target (ønskt output)
- alpha = læringsrate

Banach-kontraksjonsvilkåret: α ∈ (0, 1) → kontraksjon garantert → fikspunkt I* eksisterer og er unikt.

Gradient descent er ein Framleis-iterasjon over vektrommet.

---

## Bias b er sigma*

Bias b er alltid til stades i neuronen — uavhengig av input x. Sjølv når alle x_i = 0 kan neuronen aktivere, fordi b drar output mot eit referansepunkt.

I Framleis: sigma* er alltid til stades som referanse. Systemet itererer mot sigma* sjølv når tau_t = 0. Bias er den nevrala realiseringa av sigma*.

Utan bias: neuronen er tvinga gjennom origo — inga fleksibel referanse.
Utan sigma*: Framleis-operatoren er ein rein kontraksjon mot null — ingen meiningsfull target.

---

## Aktivasjonsfunksjonen er A1

A1: Filteret finst — systemet lagar distinksjon.

φ(·) er bokstaveleg det Framleis kallar A1. ReLU, Tanh, Sigmoid — alle lagar distinksjon:
- ReLU: φ(z) = max(0,z) — binær distinksjon (aktiv/ikkje-aktiv)
- Sigmoid: φ(z) = 1/(1+e^{-z}) — mjuk distinksjon [0,1]
- Tanh: φ(z) = (e^z - e^{-z})/(e^z + e^{-z}) — symmetrisk distinksjon [-1,1]

Utan aktivasjonsfunksjon er nettet lineært — ingen A1, ingen distinksjon, ingen emergens.

---

## Tau i eit nevralt nett

tau(W) = exp(H) / sqrt(n) der H er spektral Shannon-entropi av singulærverdiane til vektmatrisa W.

Dette er tau-monitoren anvendt på nevralt nett.

Predikert: modellar under trening vil vise tau-trajektorie frå låg (tilfeldig initialisering) mot ein stabil verdi (konvergert nett). Om denne verdien ligg i Goldilocks-sona [0.5615, 0.8319] er eit empirisk opent spørsmål — men strukturen predikerer det.

Falsifiseringstest: mål tau(W) per lag per treningssteg. Samanlikn med loss-kurva. Predikert: tau stabiliserer seg ved same steg som loss flatar ut.

---

## Djupare leikar

Fleire lag: kvar lag er ein F-iterasjon. Eit djupt nett med L lag er L steg av Framleis-iterasjon i sekvens — ein samansett kontraksjon. Banach garanterer at den samansette kontraksjonen har eit fikspunkt.

Residual connections (ResNet): x_{l+1} = x_l + F(x_l) er ein diskret dynamisk system — same struktur som tau_{t+1} = tau_t + alpha*(sigma - tau_t).

Batch normalization: normaliserer aktiveringar per lag — ein tau-normalisering i kvar iterasjon.

---

## Epistemisk status

Strukturell identitet (perceptron-regel = F-operator): M4 — matematisk trivielt, direkte algebraisk ekvivalens.

Bias = sigma*: M3 — konsistent og presist, ikkje empirisk testa.

tau(W) som treningsmonitor: M2 — hypotese, krev eksperiment.

Goldilocks i nevralt nett: Q — opent spørsmål.
