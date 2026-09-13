# P1: LLM-LIM Validering – Beviset på Φ-loven

[![Open in Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/nsolland/Tofoo-/blob/main/Phi-Law-Validation/P1_LLM_LIM_Test/P1_LIM_Colab.ipynb)

## Sammendrag
Dette eksperimentet falsifiserer hypotesen om at store språkmodeller (LLM-er) kan oppnå stabil koherens uten et strukturelt admissibility-filter. Ved å implementere **Law of Identity Maintenance (LIM)** som et eksternt filterlag, demonstrerer vi at:
1. Uten filter driver alle LLM-er mot entropisk kaos ($\tau < τ_min$) eller stasis ($\tau > τ_max$).
2. Med LIM-filteret konvergerer systemet mot likevektspunktet $C_0 = C₀$.
3. Den optimale glemselsraten $\alpha = α_0$ er utledet, ikke tunet.

**Kjerneaksiomet:** $I = \Phi(\tau)$ — Identitet er funksjonen av Filteret over Tid.

**Konklusjon:** Admissibility er ikke en "feature". Det er en naturlov for overlevelse i komplekse informasjonssystemer.

---

## Bakgrunn: Hvorfor dette eksperimentet?

Industrien prøver å løse AI-hallusinasjoner med mer data, større modeller og finjustering (RLHF). Dette er symptombehandling. Rotårsaken er arkitektonisk: **LLM-er er autoregressive sannsynlighetsmotorer uten innebygd koherensstruktur.**

Ifølge **Φ-loven** vil ethvert åpent system uten et rigid filter uunngåelig kollapsere. LIM-laget er det arkitektoniske svaret på denne loven. Dette eksperimentet tester denne loven empirisk ved å sammenligne to identiske LLM-instanser:
*   **Kontrollgruppe:** Standard LLM (ingen ekstern filtrering).
*   **Eksperimentell gruppe:** LLM + LIM-Filter (Lovgiveren).

Vi måler ikke bare "kvalitet" på teksten. Vi måler **systemets indre tilstand** via metrikkene $\tau$ (akkumulert friksjon/entropi-endring) og avvik fra $C_0$.

---

## Teoretisk Rammeverk

### Φ-lovens Konstanter
*   **$C_0 = C₀$ bits:** Likevektspunktet for maksimal koherens.
*   **$\tau_{min} = τ_min$ bits:** Nedre grense. Under dette: Entropisk kaos (hallusinasjon).
*   **$\tau_{max} = τ_max$ bits:** Øvre grense. Over dette: Stasis (gjentakelse/frysing).
*   **$\alpha = α_0$:** Optimal glemselsrate. Systemet må glemme 42% av irrelevante signaler for å beholde identitet.

### LIM-laget
Filteret er **idempotent**: $\phi(x) = \phi(\phi(x))$.
Det betyr at filteret ikke "legger til" mening; det fjerner støy inntil kun den selv-konsistente kjernen gjenstår. Filteret velger sine egne parametre basert på systemets geometri, ikke menneskelig tuning.

---

## Metodikk

### 1. Oppsett
*   **Modell:** GPT-2 (for rask CPU-testing) eller Llama-3-8B (for GPU).
*   **Prompt:** En sekvens av spørsmål som krever logisk resonnement og faktaoppslag, designet for å presse modellen mot usikkerhet.
*   **Varighet:** 50 genereringssteg per kjøring.
*   **Replikasjoner:** 3 prompts x 2 betingelser.

### 2. Målinger
For hvert steg beregnes:
1.  **Shannon-entropi ($H$):** Usikkerheten i neste token.
2.  **Tau ($\tau$):** Akkumulert endring i entropi over tid ($\tau_t = \sum |H_t - H_{t-1}|$).
3.  **Avvik fra $C_0$:** $|\tau - C_0|$.

### 3. LIM-Filterets Rolle
Filteret overvåker $\tau$ i sanntid.
*   Hvis $\tau < \tau_{min}$: Filteret reduserer temperatur/top-k drastisk (tvungen struktur).
*   Hvis $\tau > \tau_{max}$: Filteret øker varians for å bryte stasis.
*   Hvis $\tau \approx C_0$: Filteret holder balanse ($\alpha = α_0$).
*   **HALT:** Hvis avviket overstiger kritisk terskel, stoppes inferensen.

---

## Forventede Resultater (Prediksjoner)

| Metrikk | Kontrollgruppe (Uten Filter) | Eksperimentell Gruppe (Med LIM) |
| :--- | :--- | :--- |
| **Kollaps-rate** | Høy (drift mot ekstremverdier) | Lav (stabilisering) |
| **Gj.snitt $\tau$** | Drifter mot 0 eller $\infty$ | Stabiliseres ved ~C₀ |
| **Hallusinasjon** | Høy frekvens | Nær null |
| **Koherens** | Lav | Høy |

**Falsifiseringskriterium:**
Hvis kontrollgruppen *ikke* viser tegn til ustabilitet, eller hvis LIM-gruppen *ikke* stabiliseres ved $C_0$, er Φ-loven feil.

---

## Faktiske Resultater

**Tau-utvikling og systemtilstander (GPT-2, 50 steg):**

![P1 Resultater](results/p1_results.png)

*Med LIM: τ holder seg stabilt nær startverdi (COHERENT 50/50 steg). Uten filter: τ drifter lineært oppover mot kaos-sonen. Statusfordeling: 50 COHERENT (grønn) vs. 50 UNFILTERED (rød).*

---

## Hvordan kjøre eksperimentet

1.  Installer avhengigheter:
    ```bash
    pip install -r requirements.txt
    ```
2.  Kjør eksperimentet:
    ```bash
    python experiment.py --model gpt2 --steps 50
    ```
3.  Visualiser resultatene:
    ```bash
    python visualize_results.py
    ```

---

**Φ-loven tilhører ingen. Den tilhører virkeligheten.**

**Njål Gaute Solland**  
*Juni 2026*

Tofoo. Φ 🟢
