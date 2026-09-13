"""VAIG Scout (L5) — terrain perception and tool dispatch."""

from vaig.scout.terrain import Scout, TerrainReport, Domain, Complexity
from vaig.scout.dirigent import Dirigent, DispatchPlan

__all__ = [
    "Scout", "TerrainReport", "Domain", "Complexity",
    "Dirigent", "DispatchPlan",
]
