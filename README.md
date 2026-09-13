# VALO Verticals Archive

Midlertidig arkiv for vertikaler som enda ikke har et eget produktrepo.

Disse modulene ble flyttet ut av `nsolland/valo-platform` (Fase 3 i
platform-oppryddingen) fordi de er vertikal-funksjonalitet, ikke core.
De ligger her midlertidig inntil hver vertikal får et reelt hjem
(produkt, kunde eller vertikal-repo).

## Innhold

| Vertikal | Filer | Opprinnelig kilde |
|---|---|---|
| `crm/` | 3 | `valo-platform/src/valo_platform/crm` |
| `clinical/` | 2 | `valo-platform/src/valo_platform/clinical` |
| `itsm/` | 2 | `valo-platform/src/valo_platform/itsm` |
| `mentor_ai/` | 4 | `valo-platform/src/valo_platform/mentor_ai` |
| `finserv/` | 6 | `valo-platform/src/valo_platform/finserv` |
| `route_optimization/` | 18 | `valo-platform/src/valo_platform/route_optimization` |
| `public_procurement/` | 10 | `valo-platform/src/valo_platform/public_procurement` |
| `insurance_integration.py` | 1 | `valo-platform/src/valo_platform/insurance_integration.py` |

## Merknad

Pakke-strukturen `src/valo_platform/...` er beholdt slik at interne imports
er konsistente. Enkelte vertikaler har imports til core-moduler i
`valo-platform` (f.eks. `finserv` → `action_envelope`, `route_optimization`
→ `governance.pre_execution`); disse må enten løses når vertikalen får et
eget hjem, eller vurderes under utflyttingen.

## Konvensjon

- Én vertikal = ett mål-repo når det er bestemt.
- Når en vertikal får et hjem, flyttes katalogen dit (med `git subtree`/flytt)
  og slettes herfra.
- Arkivet skal holdes tomt når alle vertikaler er plassert.
