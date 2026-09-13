# VAIG Canonical Manifest

Denne fila erklærer at `VAIG/vaig/` er den **eininge autoritative implementasjonen** av VAIG-pakken.

## Canonical Declaration

- **Canonical repo:** nsolland/VAIG
- **Canonical path:** `VAIG/vaig/`
- **Package name:** `vaig`
- **Supports:** Python 3.9+
- **License:** Apache 2.0

## Migration Rule

Alle repos som tidligere hadde:
- Embedded kopier under `src/vaig/`
- Parallelle implementeringar under `vaig/` i andre katalogar
- Importer som peker til `src.vaig` eller relativ-sti-import

Skal:
1. Bruke `VAIG/vaig/` via PYTHONPATH eller pip-installasjon
2. Oppdatere alle imports til `from vaig.` eller `import vaig`
3. Fjerne eller arkiver de ikke-kanoniske kopiene

## CI Enforcement

CI-gate i hvert repo som bruker `vaig` skal:
- Feile dersom `src/vaig/` eller annen parallell kopi eksisterer
- Feile dersom imports peker til gamle stier som `src.vaig`, `src.vaig_pkg.vaig`, `valo-as.vaig-pkg.vaig`
- Feile dersom nye filer opprettes i den ikke-kanoniske kopien

## Reference

- RACS replacement for ACS/VACS as execution decision layer
- VAIG provides: Evidence → Intent → Authorization → Execution/Refusal
- RACS provides: Executive Decision Controls (6 outcomes)
