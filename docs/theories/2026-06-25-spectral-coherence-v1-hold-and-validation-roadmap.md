# Spectral Coherence v1: hold, validation roadmap, and research boundary

Dato: 2026-06-25
Status: intern forskningsstatus / handoff-note
Scope: Tofoo / spectral coherence / tau / paper maturity
Claim maturity: M1-M2 for roadmap, M3 only where real hidden-state data exists

## Kort konklusjon

v1 er ute.

La v1 stå.

Ikke publiser v1.1 nå bare fordi nye AI-analyser finner nye svakheter eller nye eksperimentforslag.

Det som mangler nå er ikke mer tekst.

Det som mangler er ekte data.

## Hvorfor vi venter med v1.1

Kimi-analysen var eksplisitt syntetisk.

Den sa selv:

```text
Since I don't have live model access, I'll generate physically plausible synthetic data grounded in the paper's reported properties.
```

Derfor kan tallene ikke brukes som empiriske resultater.

Dette gjelder særlig:

```text
layerwise tau trajectories
3-5 percent tokenizer effect
97-99 percent classification accuracy
GMM with three components
benchmark correlations
scale-invariance failures from synthetic spectra
```

Disse er nyttige som forskningsdesign.

De er ikke evidens.

## Riktig bruk av Kimi-analysen

Ikke bruk Kimi-figurene i paperet som resultater.

Ikke skriv:

```text
confirmed
strong evidence
GMM proves classes
```

Skriv heller:

```text
These simulations do not validate tau empirically, but define a validation protocol and expected failure modes.
```

Kimi-analysen skal behandles som:

```text
Validation Roadmap
```

ikke:

```text
Empirical Results
```

## Status på v1

v1 har gjort jobben sin dersom den dokumenterer den første observasjonen.

Den trenger ikke bevise hele forskningsprogrammet.

Riktig vitenskapelig posisjon:

```text
We observe X.
We propose Y as an interpretation.
Further work must test Z.
```

Ikke:

```text
We have proven a universal coherence law.
```

## Hva AI-kritikkene faktisk sier

Flere uavhengige AI-analyser peker i samme retning:

```text
De sier ikke at tau er umulig.
De sier ikke at observasjonen er matematisk feil.
De sier: vis mer empiri.
```

Det er en modenhetskritikk, ikke en dødsdom.

Konklusjon:

```text
v1 står som første observasjon.
v1.1 bør vente til det finnes nye ekte eksperimenter.
```

## Ikke la paperet bli et treårig forskningsprogram

Det opprinnelige spørsmålet var smalt:

```text
Kan tau brukes som et strukturelt mål på hidden-state spectra?
```

Det utvidede spørsmålet er stort:

```text
Hva er representasjonell koherens i LLM-er?
```

Det siste er et forskningsprogram.

Ikke gjør alt før v1.1.

## De tre avgjørende eksperimentene

Hvis noe skal gjøres i Colab eller med begrensede ressurser, gjør bare disse tre først.

### 1. Layerwise tau

Spørsmål:

```text
Er fenomenet synlig gjennom lagene, eller bare i final layer?
```

Test:

```text
coherent input
random input
repetitive input
output_hidden_states=True
compute tau per layer
```

Hvis ordering holder gjennom lagene, styrker det observasjonen.

Hvis ordering bare finnes i final layer, må claimet snevres inn.

### 2. Tau vs effective rank

Spørsmål:

```text
Tilfører tau noe, eller er tau bare normalized effective rank?
```

Riktig ærlig formulering:

```text
tau is equivalent to normalized effective rank of the hidden-state spectrum.
The contribution is the empirical characterization and interpretation, not a new formula.
```

Dette må inn før sterke claims.

### 3. GMM / class discovery på ekte data

Spørsmål:

```text
Finnes det naturlige strukturelle klasser, eller har vi selv tegnet dem?
```

Test:

```text
Compute tau for unlabeled coherent/random/repetitive samples.
Fit Gaussian Mixture Models with k=1..5.
Compare BIC/AIC.
Check whether k=3 emerges without labels.
```

Hvis GMM finner én komponent, faller class-claimet.

Hvis GMM finner tre stabile komponenter på ekte data, styrkes v1.1 betydelig.

## Eksperimenter som kan vente

Disse er nyttige, men ikke nødvendige før en mulig v1.1:

```text
tokenizer control
padding control
downstream benchmark correlation
architecture-controlled sweep
temporal tau during generation
MoE / RNN / state-space comparison
scale sensitivity beyond full-spectrum warning
```

De hører hjemme i v2 eller egne follow-up papers.

## Falsifikasjonsterskler

Tau-ideen svekkes hvis:

```text
repetitive input consistently has higher tau than coherent input
GMM on unlabeled real hidden-state data is unimodal
tau is dominated by one trivial implementation variable
tokenizer or padding effects erase the signal
full-spectrum tau fails to separate input regimes across multiple real models
```

Tau-ideen styrkes hvis:

```text
layerwise ordering holds across real models
GMM finds stable multimodal regimes without labels
tau/effective-rank behavior is reproducible across architectures
tokenizer effects remain secondary to input-regime effects
```

## Research boundary

This is the boundary:

```text
Do not rewrite v1 because AI reviewers generated more possible experiments.
Do not publish v1.1 until there are real new hidden-state experiments.
Do not mix synthetic data with empirical claims.
```

If v1 is challenged later, answer with the validation roadmap.

If real data is produced later, publish v1.1 as a genuine empirical update.

## Current decision

```text
v1: published; let it stand.
v1.1: hold.
Next action: either run three decisive experiments or move attention back to VALO/ACS/governance work.
```

## Short formulation

```text
The paper does not need more speculation.
It needs either real validation data or silence until such data exists.
```

Tofoo. Phi.
