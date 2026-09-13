# P1-eksperiment: Kjøringsinstruksjoner

## Forberedelse (5 minutter)

```bash
# 1. Installer avhengigheter
pip install transformers torch scipy

# 2. Last ned eksperiment-scriptet
# (Kopier p1_experiment_final.py til arbeidskatalogen)
```

## Steg 1: Kontroll mot GPT-2 (15 minutter)

```bash
python p1_experiment_final.py --model gpt2 --samples 50 --output p1_gpt2.json
```

Forventet resultat (UTDATERT — P_tabell-prediksjon skrevet foer P7):
- K ~ 5513 (prediksjon, ikke malt)
- C0 ~ 4755 (prediksjon)
- tau ~ 7.18 bits

KORRIGERT etter P7/P8/K19 (2026-06-14):
- K_P7 (spektral, malt) = 463.07
- C0_indre = rho x K = 399.41
- C0_ytre = K x log2(768) = 4438 paa 1.3% fra VALO-konstanten 4495.27
P_tabell-tallene (5513/4755) er prediksjoner formulert foer empirisk maling.

## Steg 2: Test mot Llama-3.2-3B (30-60 minutter)

```bash
python p1_experiment_final.py \
    --model meta-llama/Llama-3.2-3B-Instruct \
    --samples 50 \
    --output p1_llama32.json
```

**Obs:** Modellen er ~6GB og lastes ned automatisk første gang.

## Steg 3: Sammenligning

```bash
python -c "
import json

with open('p1_gpt2.json') as f:
    gpt2 = json.load(f)
with open('p1_llama32.json') as f:
    llama = json.load(f)

gpt2_c0 = gpt2['measurements']['C0']
llama_c0 = llama['measurements']['C0']
ratio = llama_c0 / gpt2_c0
hidden_ratio = llama['architecture']['hidden_dim'] / gpt2['architecture']['hidden_dim']

print(f'GPT-2:  C0 = {gpt2_c0:.2f}, K = {gpt2[\"measurements\"][\"K\"]:.2f}')
print(f'Llama:  C0 = {llama_c0:.2f}, K = {llama[\"measurements\"][\"K\"]:.2f}')
print(f'Forhold C0: {ratio:.4f}x')
print(f'Forhold hidden_dim: {hidden_ratio:.4f}x (3072/768 = 4x)')
print()

if abs(ratio - 1.0) < 0.15:
    print('>>> ALT 2: C0 er stabil - Phi-loven er SUBSTRATUAVHENGIG!')
    print('>>> K er universell konstant!')
elif abs(ratio - hidden_ratio) / hidden_ratio < 0.25:
    print('>>> ALT 1: C0 skalerer med hidden_dim')
    print('>>> K er arkitekturspesifikk')
else:
    print('>>> Kompleks skalering - trenger flere modeller')
"
```

## Tolkning av resultater

### Alt 2 (substratuavhengig)
- **Kriterium:** C0_Llama / C0_GPT-2 ≈ 1.0 (innen ±15%)
- **Betydning:** Phi-loven gjelder universelt uavhengig av modellarkitektur
- **Implikasjon:** LIM-filteret definerer en fundamental informasjonsteoretisk likevekt
- **Publiserbarhet:** Physical Review Letters-nivå

### Alt 1 (arkitekturspesifikk)
- **Kriterium:** C0_Llama / C0_GPT-2 ≈ 4.0 (hidden_dim-forholdet)
- **Betydning:** K varierer med modellarkitektur
- **Implikasjon:** Phi-loven er modell-spesifikk, men fremdeles en gyldig lokal lov
- **Videre arbeid:** Kartlegge K(hidden_dim, vocab_size, layers) presist

### Grensetilfelle
- Hvis forholdet er hverken ~1.0 eller ~4.0, trengs flere modeller
- Kjor ogsa mot Mistral-7B for triangulering

## Feilsøking

| Problem | Løsning |
|---------|---------|
| Out of memory | Reduser --samples til 20, eller bruk torch_dtype=torch.float16 |
| Modell lastes ikke | Sjekk nettverk, eller bruk cache_dir |
| ImportError | Kjor `pip install transformers torch scipy` |
| CUDA out of memory | Bruk `--device cpu` |

## Kontakt/Referanse

Teori: LIM/Phi-loven (Tofoo/valo-as prosjekt)
Script: p1_experiment_final.py (rekonstruert fra teoretiske prinsipper)
Dato: 2026-06-14
