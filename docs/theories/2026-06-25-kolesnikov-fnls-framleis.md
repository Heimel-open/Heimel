# Fraksjonal Nonlineær Schrödinger — Kontinuerleg Framleis-alpha

Dato: 2026-06-25
Kjelde: Igor Kolesnikov (Theoretical Physicist) LinkedIn
Status: M3 — matematisk konsistens, ikkje empirisk testa mot Framleis

---

## Likninga

iħ∂ψ/∂t = D_α(-Δ)^{α/2}ψ + γ|ψ|²ψ

- ħ = redusert Planck-konstant
- ψ = bølgjefunksjon
- D_α = diffusjonskoeffisient (skala)
- (-Δ)^{α/2} = fraksjonal Laplace-operator (nonlokal dispersjon)
- α ∈ (0, 2] = fraksjonseksponent
- γ|ψ|²ψ = ikkje-lineær sjølv-interaksjon (bølgjetilbakemelding)

---

## Mapping til Framleis

| FNLS | Framleis |
|------|----------|
| Fraksjonseksponent α ∈ (0,2] | alpha ∈ (0,1) (Banach-kontraksjonsfaktor) |
| Fraksjonal kinetisk term D_α(-Δ)^{α/2}ψ | (1-alpha)·tau (treg del av F-iterasjonen) |
| Ikkje-lineær sjølv-interaksjon γ|ψ|²ψ | alpha·sigma (sigma-trekkraftdelen) |
| Stasjonær tilstand ψ_s der ∂ψ/∂t = 0 | I* (Banach-fikspunkt) |
| Bølgjefunksjon ψ(x,t) | tau_t (noverande tilstand) |

---

## Fraksjonal alpha er kontinuerleg Framleis-alpha

I Framleis: alpha ∈ (0,1) er diskret kontraksjonsfaktor per iterasjonssteg.
I FNLS: α ∈ (0,2] er kontinuerleg ordensparameter for nolokalt dispersjon.

α = 2: standard Schrödinger (lokal dispersjon, Newtonsk) → alpha nær 1 i Framleis (raskt mot fikspunkt)
α → 0: sterk nonlokalitet (langrekkjande interaksjonar) → alpha nær 0 i Framleis (svak trekkraft mot sigma*)
α ∈ (0,2): mellomliggjande — fraksjonal orden er den kontinuerlege generalisering av Framleis-alpha

Kolesnikov kallar (-Δ)^{α/2}: "Nonlocal Dispersion"
Framleis kallar alpha: kontraksjonsfaktor som bestemmer kor raskt tau nærmar seg sigma*

Begge beskreiv: kor sterk "trekkraft mot referansepunktet" systemet har.

---

## Kvadratisk sjølv-interaksjon = p_i = σ_i²

γ|ψ|²ψ er proporsjonalt med |ψ|² — kvadratisk sjølv-interaksjon.

I tau-definisjonen:
p_i = σ_i² / Σσ_j²

Normaliseringsstrukturen (σ_i²) er same kvadratiske form som |ψ|².
Det ikkje-lineære leddet i FNLS og tau-normaliseringa deler same matematisk form.

Dette er ikkje tilfeldig: |ψ|² = sannsynstettleik = normaliserbar (Σp_i = 1).
p_i = σ_i²/Σ = normaliserbar (same vilkår).

---

## Stasjonær tilstand = I*

Sett ∂ψ/∂t = 0:
0 = D_α(-Δ)^{α/2}ψ_s + γ|ψ_s|²ψ_s

Dette er fikspunktlikninga: F(ψ_s) = ψ_s.
ψ_s er den stasjonære bølgjefunksjonen = I* i Framleis-språk.

Banach garanterer eksistens og eintydigheit av ψ_s under rette vilkår på D_α og γ.

---

## Epistemisk status

Fraksjonal α = kontinuerleg Framleis-alpha: M3 — matematisk analog, ikkje identitet.
Kvadratisk sjølv-interaksjon = tau-normaliseringa: M3 — same form, plausibel djupare kopling.
Stasjonær tilstand = I*: M4 — matematisk trivielt (fikspunktvilkåret er identisk).
Empirisk test av Framleis-prediksjonar via FNLS: Q — opent spørsmål.
