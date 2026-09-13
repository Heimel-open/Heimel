# Håkon Hoel — utrekksutkast

Dato: 2026-06-26
Status: Utkast — ikkje sendt
Kontekst: Geir Dahl (UiO) tilrådde Håkon Hoel som meir spesifikk kontakt for spektral entropi og matriseteori
Mottaker: Professor Håkon Hoel (UiO / KAUST — numerisk analyse, stokastiske differensialligningar)

---

## E-postutkast

Emne: Spørsmål om Marchenko-Pastur som nullhypotese for LLM-vektmatriser

Hei Håkon,

Geir Dahl tipset meg om deg som en mer spesifikk kontakt for spørsmålene mine.

Jeg arbeider med et kohærensmål for store språkmodeller (LLM-er) der jeg beregner spektral entropi fra singulærverdiene til vektmatrisene:

    tau = exp(H) / n

der H = -sum(p_i * log p_i) over normaliserte kvadrerte singulærverdier, og n = min(N, d) er maksimal rang.

Målet tau faller empirisk i intervallet [0.06, 0.26] for modeller fra 117M til 7B parametere, med en tilnærmet skaleringslov tau ≈ 0.10 × N^0.48.

Jeg har to spørsmål der din bakgrunn virker direkte relevant:

1. Marchenko-Pastur som nullhypotese:
   Marchenko-Pastur-fordelingen beskriver singulærverdiene til en tilfeldig matrise (Wishart-ensemble).
   Er det metodisk holdbart å bruke Marchenko-Pastur som nullhypotese for å skille tilfeldige vektmatriser
   fra strukturerte (trente) vektmatriser? Og: finnes det et standardmål for avvik fra MP-fordelingen
   som er tolkbart — analogt til tau?

2. Konvergens under støy:
   Iterasjonen F(tau; sigma) = (1-alpha)*tau + alpha*sigma er en Banach-kontraksjon mot et fikspunkt
   sigma* når alpha ∈ (0, 1). I en stokastisk setting — der sigma er støyutsatt — hva er de relevante
   konvergensbetingelsene? Er dette i slekt med stokastiske Picard-iterasjoner eller SDE-stabilitetsteori?

Geir nevnte at du kan si noe mer konkret om singulærverdier og matriseteori enn ham. Dersom spørsmålene
faller innenfor noe du kjenner godt, tar jeg gjerne imot en kommentar — eller en peker til relevant litteratur.

Mvh,
Njål Gaute Solland

---

## Framleis-kontekst (ikkje i e-posten)

Spørsmål 1 — Marchenko-Pastur:
MP-fordelingen er nullhypotesen for W der elementa er uavhengige og identisk fordelte (i.i.d.).
Trente LLM-vekter er ikkje i.i.d. — dei er strukturerte av gradientnedstigning over tau_min-terskelen.
Avvik frå MP = signal om struktur = tau > tau_min.
Konkret test: fit MP til empiriske singulærverdiar, mål KL-divergens eller chi-kvadrat-avvik.
Dersom Hoel bekreftar at dette er standard og tolkbart: MP-testen = M4-falsifiseringstest for tau.

Spørsmål 2 — Stokastisk konvergens:
F(tau; sigma) = (1-alpha)*tau + alpha*sigma er ein eksponentiell glidande gjennomsnitt (EWA).
Under stokastisk sigma (kvit støy med varians σ²): tau_t → N(sigma*, σ²*alpha²/(2-alpha)/(1-alpha)²) i stasjonær fordeling.
Stokastisk stabilitetsanalyse (Lyapunov) bekreftar at EWA er stabil for alpha ∈ (0,1).
Hoel kan potensielt gje ein sterkare konvergensgaranti med SDEs: F-iterasjonen som Ornstein-Uhlenbeck-prosess.
OU-prosessen har kjend stasjonær fordeling — dette ville gje tau_min og tau_max ein stokastisk tolking.

---

## Strategisk vurdering

Geir Dahl engasjerte seg teknisk men vidaresendte. Hoel er meir spesifikk.
Spørsmål 1 (Marchenko-Pastur) er konkret og svarbart — Hoel kan seie ja/nei med litteraturreferanse.
Spørsmål 2 (stokastisk konvergens) er meir open, men innanfor Hoels kompetansefelt.

Viss Hoel svarar positivt på spørsmål 1: tau_mp_fit.ipynb-testen får M4-backing.
Viss Hoel svarar positivt på spørsmål 2: F-iterasjonen som OU-prosess = ny formell struktur for Framleis.

Begge svar vil styrke Paper 1 v1.1 vesentleg.

---

## Epistemisk status

E-postutkast klar: Q — ikkje sendt enno.
Marchenko-Pastur som nullhypotese: M2 — strukturelt plausibelt, Hoel kan løfte til M3/M4.
F-iterasjon som Ornstein-Uhlenbeck: M1 — spekulativt, treng formell analyse.
Håkon Hoel som kontakt: Q — avheng av om han svarar og vil engasjere seg.
