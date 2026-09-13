# NURSERY-TIME-DIVERGENCE

Kjørbar lokal implementasjon av preregistreringen:

`experiments/research/2026-09-06-nursery-time-divergence-preregistration.md`

## Formål

Teste om byte-identiske seeds med samme antall transitions, men ulik kontrollert historie, utvikler målbar intern divergens.

Primærvariabelen er **divergens**. Ingen rangering av bedre/dårligere eller kvalitet inngår.

## Betingelser

- `A_repetition` — repetitiv historie
- `B_variation` — variert historie
- `C_relational` — samme grunnstimuli med annen relasjonell kobling
- `D_reordered` — samme event-sett som B, reversert rekkefølge

Alle har 8 transitions.

## Målinger

Runneren produserer:

- state-distance fra seed og mellom betingelser
- relasjonell matrisestans
- behavior-divergens under identiske probes
- reachability-divergens via identiske ett-stegs intervensjoner
- akkumulert strukturell endring
- crossover med samme nye event etter ulik historie
- deterministisk history replay
- backward event ablation

Dette er et syntetisk mekanikk-/instrumenteringsløp. Det er ikke i seg selv evidens for SI-utvikling i en språkmodell eller biologisk subjektiv tid.

## Lokal kjøring

Fra repo-root:

```bash
python experiments/NURSERY_TIME_DIVERGENCE/runner.py \
  --out /tmp/nursery_time_divergence_report.json
```

Tester:

```bash
cd experiments/NURSERY_TIME_DIVERGENCE
python -m unittest -v test_runner.py
```

Krever `numpy`, som allerede ligger i repoets `requirements.txt`.

## Viktig kontrollgrense

V1 matcher transition count og er deterministisk. Den simulerer ikke reell wall-clock-variasjon. Wall-clock schedule invariance må kjøres som et separat runtime-løp dersom faktisk elapsed time skal manipuleres.

## Tolkning

Et positivt syntetisk resultat viser bare at den implementerte adaptive mekanismen er path-dependent og at historien kan måles som persistent strukturell divergens. Neste steg er å koble samme instrumentering til et faktisk Nursery/Synapse-substrat uten å endre den preregistrerte hovedvariabelen.
