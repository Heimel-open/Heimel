# P5 — Swarm Coherence Simulation

## Hypotese
Et kollektiv av autonome agenter under eksogent Phi-Lov-filter (Lovgiveren)
vil konvergere mot konsensus uten sentralisert kontroll.

## Eksperiment
100 agenter simuleres over 1000 tidssteg i to betingelser:

| Betingelse | Beskrivelse |
|---|---|
| **Kaos (ingen filter)** | Agentene oppdaterer tilstand fritt |
| **Phi-filter** | Eksogent filter (Lovgiveren) korrigerer avvik |

Konsensus-metrikk (gjennomsnittlig avstand fra median-tilstand) logges hvert tidssteg.

## Kjøre simuleringen
```bash
pip install numpy matplotlib
python swarm_sim.py
python visualization.py
```

## Forventede funn
- Uten filter: vedvarende kaos eller split i sub-klynger
- Med filter: konvergens mot konsensus innen ~200 tidssteg

## Parametere
Se toppen av `swarm_sim.py` for konfigurasjon.
