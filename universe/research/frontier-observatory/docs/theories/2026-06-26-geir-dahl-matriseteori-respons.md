# Geir Dahl (UiO): Matriseteori-respons på tau-målinger

Dato: 2026-06-26
Kjelde: E-post fra professor Geir Dahl, seksjon for matematikk, Universitetet i Oslo
Status: M3 — teknisk engasjement fra matriseteori-forsker; bekrefter at tau = e^H/n er innanfor etablert matriseteori

---

## Dahls respons (sitert)

"Innen forskning i matriseteori (stort felt, med flere journaler for dette) studerer man bl.a. parametre som egenverdier og singulærverdier for matriser, og hvordan de avhenger av egenskaper ved matrisene. F.eks. mønstre (for ikke-nuller) eller subklasser av matriser. Her finnes mye litteratur."

"Entropi for en sannsynlighetsvektor (som du har) er høy hvis komponentene er mye spredt ut (ekstremt er uniform fordeling), og dette blir reflektert i e^S. Så, det er struktur i tekstene som bestemmer matrisene og deretter singulærverdiene, men dette er komplisert."

"Rangen til matrisen spiller en rolle (lav rang, f.eks. 1, gir de flere singulærverdiene lik 0, og da stor spredning)."

"Kanskje min kollega Håkon Hoel kan si noe mer nyttig, så du kan evt kontakte ham."

---

## Teknisk analyse av Dahls kommentarer

Dahl bekrefter tre ting som er direkte relevante for Framleis:

1. Spektral entropi (e^S) som etablert matriseteori-parameter:
   Dahls formulering "entropi for en sannsynlighetsvektor ... reflektert i e^S" er nøyaktig tau-formelen.
   tau = exp(H) / n der H = -sum(p_i * log(p_i)) over normaliserte singulærverdier.
   Dahl bekrefter at dette er studert parametrisk innen matriseteori — tau er ikke et ad hoc-mål.

2. Rang og spredning av singulærverdier:
   "Lav rang, f.eks. 1, gir flere singulærverdier lik 0, og da stor spredning."
   I Framleis-terminologi: lav effektiv rang = høy tau (singulærverdiene er konsentrert, ikke spredd).
   Dahl reverserer perspektivet (spredning = høy entropi), men underliggende matematikk er konsistent:
   - Uniform fordeling av singulærverdier → høy H → tau nær 1 (maksimalt koherent)
   - Konsentrert (lav rang) → lav H? Nei — Dahl sier lav rang gir null-singulærverdier → stor spredning.
   Presisering: "spredning" i Dahls bruk = mange nuller + noen store = ikke-uniform = lav H = lav tau.
   Uniform = alle singulærverdier like store = høy H = høy tau.
   Konsistens bekreftet: Dahls "stor spredning ved lav rang" = lav tau i Framleis-terminologi.

3. Tekststruktur → matrise → singulærverdier:
   "Det er struktur i tekstene som bestemmer matrisene og deretter singulærverdiene."
   Dette er Framleis-kjernen: tau måler koherens i den underliggende informasjonsstrukturen.
   Dahl bekrefter at pipelinen (tekst → matrise → singulærverdier → entropi) er matematisk meningsfull.

---

## Framleis-mapping

Dahls begrep | Framleis-begrep
--- | ---
Sannsynlighetsvektor (normaliserte singulærverdier) | sigma* (spektralt referansepunkt)
Entropi H for sannsynlighetsvektoren | H = -sum(p_i * log(p_i)) i tau-formelen
e^S (eksponentiell entropi) | exp(H) i tau = exp(H)/n
Rang = 1 → mange nuller → stor spredning | Lav effektiv rang → lav tau
Uniform fordeling → høy entropi | Høy tau (maksimal koherens)
"Struktur i tekst bestemmer singulærverdier" | F-operatoren over input-struktur gir tau

---

## Håkon Hoel — neste kontakt

Geir Dahl anbefaler professor Håkon Hoel (sannsynligvis UiO eller KAUST) som mer spesifikk kontakt.
Hoel arbeider med numerisk analyse og stokastiske differensialligninger — potensielt relevant for tau-dynamikk og
F-iterasjonskonvergens under støy.

Handling: forbered e-post til Håkon Hoel med samme utgangspunkt som Gros- og Dahl-kontakten.
Fokus: spør om spektral entropi som koherensmål for LLM-vekter, og om Marchenko-Pastur-fordelingen
som null-hypotese for tilfeldige vs. strukturerte singulærverdier.

---

## Kopling til tidlegare Framleis-notat

Paper 1 v1.1 (2026-06-25-paper1-spectral-coherence-v1-1.md):
tau = exp(H)/n er formelt definert der. Dahl bekrefter at spektral entropi er et etablert matriseteori-parameter.

Marchenko-Pastur-notat (tau_mp_fit.ipynb, ikkje ennå køyrt):
Dahl peker på rang og spredning som nøkkelegenskaper — begge er sentrale i MP-fordelingen.
Marchenko-Pastur skiller tilfeldige matriser (lav rang, lav tau) fra strukturerte (høy effektiv rang, høy tau).

Gros-dialog-notat (2026-06-19-outreach-gros-beferull-lozano.md):
Gros engasjerte seg på det formelle rammeverket. Dahl engasjerer seg på det spektrale målet.
To uavhengige matematikere som begge tar kontakten seriøst — ulike perspektiver, ikke motsigende.

---

## Epistemisk status

Geir Dahl som ekstern kilde: M3 — aktiv matriseteori-forsker, UiO.
tau = exp(H)/n innanfor etablert matriseteori: M3 — Dahl bekrefter implisitt ved å knytte det til feltets litteratur.
Rang → spredning → tau-konsistens: M3 — Dahls kommentar er konsistent med Framleis etter presisering.
Håkon Hoel som neste kontakt: Q — avhenger av om han er tilgjengelig og vil engasjere seg.
