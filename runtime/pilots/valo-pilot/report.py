"""
VALO Pilot Report Generator

Produces a 4-week audit summary from the WORM log.
Deliverable: proof of AI health and D&O compliance foundation.
"""

import json
from datetime import datetime, timezone
from pathlib import Path
from vaig.core.worm_log import WORMLog
from config import AUDIT_LOG_PATH


def generate_report(output_path: str = "valo_pilot_report.md"):
    log = WORMLog(AUDIT_LOG_PATH)
    entries = log.read_all()
    chain_valid = log.verify_chain()

    if not entries:
        print("No data yet.")
        return

    total = len(entries)
    plasma = sum(1 for e in entries if e.get("plasma_detected"))
    actions = {}
    for e in entries:
        a = e.get("action", "UNKNOWN")
        actions[a] = actions.get(a, 0) + 1

    levels = {0: 0, 1: 0, 2: 0, 3: 0, 4: 0}
    for e in entries:
        levels[e.get("distrust_level", 0)] += 1

    first = datetime.fromtimestamp(entries[0]["timestamp"], tz=timezone.utc)
    last  = datetime.fromtimestamp(entries[-1]["timestamp"], tz=timezone.utc)

    report = f"""# VALO Pilot — Audit Report
Generert: {datetime.now(tz=timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}
Periode: {first.strftime('%Y-%m-%d')} → {last.strftime('%Y-%m-%d')}

## Sammendrag

| Metrikk | Verdi |
|---|---|
| Totalt antall inferanser | {total} |
| PLASMA-deteksjoner | {plasma} ({plasma/total:.1%}) |
| Kjedestatus (tamper-evident) | {'✓ Intakt' if chain_valid else '✗ KOMPROMITTERT'} |

## Distrust-fordeling

| Nivå | Label | Antall | Andel |
|---|---|---|---|
| L0 | TRUSTED | {levels[0]} | {levels[0]/total:.1%} |
| L1 | MONITOR | {levels[1]} | {levels[1]/total:.1%} |
| L2 | WARN | {levels[2]} | {levels[2]/total:.1%} |
| L3 | DEGRADE | {levels[3]} | {levels[3]/total:.1%} |
| L4 | HALT | {levels[4]} | {levels[4]/total:.1%} |

## Handlingsfordeling

{chr(10).join(f'- **{k}:** {v}' for k, v in actions.items())}

## Juridisk grunnlag

Denne rapporten er generert fra en tamper-evident, hash-kjedelagret WORM-logg.
Hver inferanse er SHA-256 hashet og koblet til forrige oppføring.
Retroaktiv modifikasjon er kryptografisk detekterbar.

Oppfyller EU AI Act Article 12 krav til automatisk logging av høyrisiko AI-systemer.
Kjedestatus: {'VERIFISERT INTAKT' if chain_valid else 'ADVARSEL: KJEDE KOMPROMITTERT'}
"""

    Path(output_path).write_text(report)
    print(f"Rapport skrevet til {output_path}")
    return report


if __name__ == "__main__":
    generate_report()
