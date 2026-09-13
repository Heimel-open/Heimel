"""
Tests for model routing decisions.

Run: pytest tests/test_model_routing.py -v
"""
import pytest
from vaig.economy.router import ModelTier, RoutingContext, route_model


class TestModelRouting:
    def test_low_risk_formatting_routes_to_small(self):
        """Acceptance test: low-risk formatting → small model."""
        ctx = RoutingContext(risk_level=0.1, consequence_level=0.1, cost_pressure=0.0)
        assert route_model(ctx) == ModelTier.SMALL

    def test_high_consequence_not_downgraded_under_cost_pressure(self):
        """Acceptance test: high-consequence governance task is never downgraded for cost."""
        ctx = RoutingContext(risk_level=0.2, consequence_level=0.9, cost_pressure=0.99)
        tier = route_model(ctx)
        assert tier == ModelTier.LARGE
        assert tier != ModelTier.SMALL

    def test_high_consequence_not_downgraded_even_at_max_cost_pressure(self):
        ctx = RoutingContext(risk_level=0.0, consequence_level=1.0, cost_pressure=1.0)
        assert route_model(ctx) == ModelTier.LARGE

    def test_medium_risk_high_cost_pressure_routes_medium(self):
        ctx = RoutingContext(risk_level=0.5, consequence_level=0.2, cost_pressure=0.9)
        assert route_model(ctx) == ModelTier.MEDIUM

    def test_high_risk_routes_large(self):
        ctx = RoutingContext(risk_level=0.8, consequence_level=0.3, cost_pressure=0.0)
        assert route_model(ctx) == ModelTier.LARGE

    def test_boundary_consequence_level(self):
        """Exactly at consequence lock threshold routes large."""
        ctx = RoutingContext(risk_level=0.1, consequence_level=0.6, cost_pressure=0.99)
        assert route_model(ctx) == ModelTier.LARGE

    def test_just_below_consequence_lock_can_route_lower(self):
        """Just below consequence lock threshold with high cost pressure → medium."""
        ctx = RoutingContext(risk_level=0.4, consequence_level=0.59, cost_pressure=0.9)
        assert route_model(ctx) == ModelTier.MEDIUM
