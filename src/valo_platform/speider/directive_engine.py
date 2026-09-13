"""
Speider Directive Engine for routing observation directives (Phase 13)

Routes BARO-generated directives and operator commands to Speider connectors,
adjusting sampling frequencies and observation targets.
"""

import logging
from typing import Optional, Dict, Any, List
from datetime import datetime, timezone
from enum import Enum

logger = logging.getLogger(__name__)


class SamplingFrequency(str, Enum):
    """Speider connector sampling frequencies."""
    PAUSE = "pause"          # Stop sampling (0h)
    DAILY = "daily"          # Once per 24h
    NORMAL = "normal"        # Default (6h)
    HIGH = "high"            # Every 2h
    HOURLY = "hourly"        # Every 1h
    INTENSIVE = "intensive"  # Every 15min (emergency only)


class DirectiveStatus(str, Enum):
    """Directive lifecycle states."""
    ISSUED = "issued"                # Just created
    ACKNOWLEDGED = "acknowledged"    # Speider received it
    ACTIVE = "active"                # Being followed
    RECEIVING_SIGNALS = "receiving_signals"  # Signals coming in
    EXPIRED = "expired"              # Time-based expiration
    SUPERSEDED = "superseded"        # Replaced by newer directive
    COMPLETED = "completed"          # Operator goal achieved


class SpeiderDirectiveEngine:
    """Routes and manages Speider observation directives."""

    def __init__(self, persistence_manager):
        """Initialize directive engine."""
        self.persistence_manager = persistence_manager
        self.connector_state = {}  # Track current state of each connector

    def issue_directive(self, directive_data: Dict[str, Any]) -> Optional[str]:
        """
        Issue a Speider directive (from BARO or operator).

        Args:
            directive_data: {
                "source": "baro|operator",
                "target_domain": "Supply_Chain",
                "connector_name": "Supply_Chain_Speider",
                "directive_type": "intensify|pause|validate",
                "sampling_frequency": "normal|hourly|daily",
                "reason": "...",
                "expires_at": "ISO timestamp" (optional)
            }

        Returns: directive_id or None if failed
        """
        if not self.persistence_manager:
            logger.error("No persistence manager; directive not stored")
            return None

        try:
            # Store directive to database
            directive_id = self.persistence_manager.store_speider_directive(directive_data)

            # Update connector state
            connector = directive_data.get("connector_name")
            if connector:
                self._update_connector_state(
                    connector,
                    directive_data.get("sampling_frequency", "normal"),
                    directive_id
                )

            logger.info(
                f"Directive {directive_id} issued: {directive_data.get('directive_type')} "
                f"on {connector} ({directive_data.get('sampling_frequency')})"
            )

            return directive_id
        except Exception as e:
            logger.error(f"Error issuing directive: {e}")
            return None

    def adjust_connector_sampling(
        self, connector_name: str, frequency: SamplingFrequency
    ) -> bool:
        """
        Adjust sampling frequency for a Speider connector.

        Frequencies:
        - PAUSE: Stop sampling entirely
        - DAILY: Once per 24 hours
        - NORMAL: Default (6 hours)
        - HIGH: Every 2 hours
        - HOURLY: Every 1 hour (intensive)
        - INTENSIVE: Every 15 minutes (emergency)
        """
        try:
            # In production, this would communicate with the actual Speider connector
            # For now, update local state
            self.connector_state[connector_name] = {
                "sampling_frequency": frequency.value,
                "updated_at": datetime.now(timezone.utc).replace(tzinfo=None).isoformat(),
                "status": "active" if frequency != SamplingFrequency.PAUSE else "paused",
            }

            logger.info(f"Connector {connector_name} sampling adjusted to {frequency.value}")
            return True
        except Exception as e:
            logger.error(f"Error adjusting connector sampling: {e}")
            return False

    def get_directive_status(self, directive_id: str) -> Optional[Dict[str, Any]]:
        """
        Get the current status of a directive.

        Returns:
            {
                "directive_id": "...",
                "status": "active|acknowledged|receiving_signals|expired",
                "issued_at": "...",
                "signals_received": N,
                "last_signal_at": "...",
                "sampling_frequency": "hourly"
            }
        """
        if not self.persistence_manager:
            return None

        try:
            # In Phase 13b, this would query signal metadata from database
            # For now, return placeholder
            return {
                "directive_id": directive_id,
                "status": DirectiveStatus.ACTIVE.value,
                "issued_at": datetime.now(timezone.utc).replace(tzinfo=None).isoformat(),
                "signals_received": 0,
                "last_signal_at": None,
                "sampling_frequency": "normal",
            }
        except Exception as e:
            logger.error(f"Error getting directive status: {e}")
            return None

    def retire_directive(self, directive_id: str, reason: str) -> bool:
        """
        Retire a directive (operator action or auto-expiration).

        Logs reason and updates status in database.
        """
        try:
            logger.info(f"Directive {directive_id} retired: {reason}")
            # In Phase 13b, update directive status to "retired" in database
            return True
        except Exception as e:
            logger.error(f"Error retiring directive: {e}")
            return False

    def supersede_directive(self, old_directive_id: str, new_directive_id: str) -> bool:
        """Replace one directive with another (e.g., refine from BARO)."""
        try:
            logger.info(f"Directive {old_directive_id} superseded by {new_directive_id}")
            # In Phase 13b, mark old as "superseded", new as "active"
            return True
        except Exception as e:
            logger.error(f"Error superseding directive: {e}")
            return False

    def get_active_directives(
        self, domain: Optional[str] = None, connector: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get all currently active directives, optionally filtered."""
        if not self.persistence_manager:
            return []

        try:
            directives = self.persistence_manager.get_active_speider_directives(
                domain=domain, connector=connector
            )
            return directives
        except Exception as e:
            logger.error(f"Error retrieving directives: {e}")
            return []

    def get_connector_state(self, connector_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Get current state of Speider connectors.

        Returns map of connector → {sampling_frequency, status, last_signal}.
        """
        if connector_name:
            return self.connector_state.get(connector_name, {})
        return self.connector_state

    def _update_connector_state(
        self, connector_name: str, frequency: str, directive_id: str
    ) -> None:
        """Internal: update local connector state."""
        self.connector_state[connector_name] = {
            "sampling_frequency": frequency,
            "directive_id": directive_id,
            "updated_at": datetime.now(timezone.utc).replace(tzinfo=None).isoformat(),
            "signals_received": 0,
            "last_signal_at": None,
        }

    def record_signal_received(
        self, connector_name: str, signal_count: int = 1
    ) -> None:
        """Record that Speider connector sent signals in response to directive."""
        if connector_name not in self.connector_state:
            return

        state = self.connector_state[connector_name]
        state["signals_received"] = state.get("signals_received", 0) + signal_count
        state["last_signal_at"] = datetime.now(timezone.utc).replace(tzinfo=None).isoformat()
        state["status"] = "receiving_signals"

        logger.debug(
            f"Connector {connector_name} received ({signal_count} signals, "
            f"total: {state['signals_received']})"
        )
