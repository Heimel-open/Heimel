"""ITSM system connectors (Jira, ServiceNow, etc.)."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
from enum import Enum
import uuid
import json


class ITSMEventType(str, Enum):
    """Events from ITSM systems."""
    PROCEDURE_CREATED = "procedure_created"
    PROCEDURE_UPDATED = "procedure_updated"
    PROCEDURE_DELETED = "procedure_deleted"
    CHANGE_REQUEST_CREATED = "change_request_created"
    CHANGE_REQUEST_APPROVED = "change_request_approved"
    CHANGE_REQUEST_EXECUTED = "change_request_executed"


@dataclass
class ITSMProcedure:
    """Generic procedure from ITSM system."""
    procedure_id: str
    title: str
    description: str
    owner: str
    owner_email: str
    version: int
    created_at: str
    updated_at: str
    status: str  # draft, active, archived
    source_system: str  # jira, servicenow, etc.
    source_id: str  # Issue key, change request ID, etc.
    custom_fields: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)


@dataclass
class SyncResult:
    """Result of a sync operation."""
    success: bool
    message: str
    procedures_synced: int = 0
    procedures_failed: int = 0
    errors: List[str] = None

    def __post_init__(self):
        if self.errors is None:
            self.errors = []


class ITSMConnector(ABC):
    """Abstract base class for ITSM connectors."""

    @abstractmethod
    def authenticate(self) -> bool:
        """Authenticate with ITSM system."""
        pass

    @abstractmethod
    def get_procedures(self, project_key: Optional[str] = None) -> List[ITSMProcedure]:
        """Get all procedures from ITSM system."""
        pass

    @abstractmethod
    def get_procedure(self, procedure_id: str) -> Optional[ITSMProcedure]:
        """Get a specific procedure."""
        pass

    @abstractmethod
    def create_procedure(self, procedure: ITSMProcedure) -> Optional[ITSMProcedure]:
        """Create a new procedure in ITSM system."""
        pass

    @abstractmethod
    def update_procedure(self, procedure: ITSMProcedure) -> bool:
        """Update a procedure in ITSM system."""
        pass

    @abstractmethod
    def delete_procedure(self, procedure_id: str) -> bool:
        """Delete a procedure from ITSM system."""
        pass

    @abstractmethod
    def log_enforcement_event(self, procedure_id: str, event: Dict[str, Any]) -> bool:
        """Log an enforcement event back to ITSM."""
        pass


class JiraConnector(ITSMConnector):
    """Jira integration connector."""

    def __init__(self, instance_url: str, api_token: str, email: str):
        """Initialize Jira connector."""
        self.instance_url = instance_url
        self.api_token = api_token
        self.email = email
        self.authenticated = False
        self.procedures_cache: Dict[str, ITSMProcedure] = {}

    def authenticate(self) -> bool:
        """Authenticate with Jira."""
        try:
            # In production, would call Jira REST API to validate credentials
            # For testing, accept any non-empty credentials
            if self.instance_url and self.api_token and self.email:
                self.authenticated = True
                return True
            return False
        except Exception:
            return False

    def get_procedures(self, project_key: Optional[str] = None) -> List[ITSMProcedure]:
        """Get procedures from Jira (mocked: return cached procedures)."""
        if not self.authenticated:
            return []

        # Return cached procedures or empty list
        return list(self.procedures_cache.values())

    def get_procedure(self, procedure_id: str) -> Optional[ITSMProcedure]:
        """Get a specific procedure from Jira."""
        if not self.authenticated:
            return None

        return self.procedures_cache.get(procedure_id)

    def create_procedure(self, procedure: ITSMProcedure) -> Optional[ITSMProcedure]:
        """Create a new procedure in Jira."""
        if not self.authenticated:
            return None

        # Simulate Jira creating an issue
        jira_issue_key = f"PROC-{len(self.procedures_cache) + 1}"
        procedure.source_id = jira_issue_key

        self.procedures_cache[procedure.procedure_id] = procedure
        return procedure

    def update_procedure(self, procedure: ITSMProcedure) -> bool:
        """Update a procedure in Jira."""
        if not self.authenticated:
            return False

        if procedure.procedure_id in self.procedures_cache:
            procedure.updated_at = datetime.now(timezone.utc).replace(tzinfo=None).isoformat()
            procedure.version += 1
            self.procedures_cache[procedure.procedure_id] = procedure
            return True

        return False

    def delete_procedure(self, procedure_id: str) -> bool:
        """Delete a procedure from Jira."""
        if not self.authenticated:
            return False

        if procedure_id in self.procedures_cache:
            del self.procedures_cache[procedure_id]
            return True

        return False

    def log_enforcement_event(self, procedure_id: str, event: Dict[str, Any]) -> bool:
        """Log enforcement event back to Jira."""
        if not self.authenticated:
            return False

        procedure = self.procedures_cache.get(procedure_id)
        if not procedure:
            return False

        # In production, would add a comment to the Jira issue
        # For testing, just log it internally
        return True


class ServiceNowConnector(ITSMConnector):
    """ServiceNow integration connector."""

    def __init__(self, instance_url: str, client_id: str, client_secret: str):
        """Initialize ServiceNow connector."""
        self.instance_url = instance_url
        self.client_id = client_id
        self.client_secret = client_secret
        self.authenticated = False
        self.procedures_cache: Dict[str, ITSMProcedure] = {}

    def authenticate(self) -> bool:
        """Authenticate with ServiceNow."""
        try:
            # In production, would call ServiceNow OAuth2 endpoint
            # For testing, accept any non-empty credentials
            if self.instance_url and self.client_id and self.client_secret:
                self.authenticated = True
                return True
            return False
        except Exception:
            return False

    def get_procedures(self, project_key: Optional[str] = None) -> List[ITSMProcedure]:
        """Get procedures from ServiceNow (mocked: return cached procedures)."""
        if not self.authenticated:
            return []

        # Return cached procedures or empty list
        return list(self.procedures_cache.values())

    def get_procedure(self, procedure_id: str) -> Optional[ITSMProcedure]:
        """Get a specific procedure from ServiceNow."""
        if not self.authenticated:
            return None

        return self.procedures_cache.get(procedure_id)

    def create_procedure(self, procedure: ITSMProcedure) -> Optional[ITSMProcedure]:
        """Create a new procedure in ServiceNow."""
        if not self.authenticated:
            return None

        # Simulate ServiceNow creating a change request
        sn_change_id = f"CHG{uuid.uuid4().hex[:8].upper()}"
        procedure.source_id = sn_change_id

        self.procedures_cache[procedure.procedure_id] = procedure
        return procedure

    def update_procedure(self, procedure: ITSMProcedure) -> bool:
        """Update a procedure in ServiceNow."""
        if not self.authenticated:
            return False

        if procedure.procedure_id in self.procedures_cache:
            procedure.updated_at = datetime.now(timezone.utc).replace(tzinfo=None).isoformat()
            procedure.version += 1
            self.procedures_cache[procedure.procedure_id] = procedure
            return True

        return False

    def delete_procedure(self, procedure_id: str) -> bool:
        """Delete a procedure from ServiceNow."""
        if not self.authenticated:
            return False

        if procedure_id in self.procedures_cache:
            del self.procedures_cache[procedure_id]
            return True

        return False

    def log_enforcement_event(self, procedure_id: str, event: Dict[str, Any]) -> bool:
        """Log enforcement event back to ServiceNow."""
        if not self.authenticated:
            return False

        procedure = self.procedures_cache.get(procedure_id)
        if not procedure:
            return False

        # In production, would update the ServiceNow change request
        # For testing, just log it internally
        return True


class ITSMConnectorFactory:
    """Factory for creating ITSM connectors."""

    @staticmethod
    def create_connector(
        system: str,
        instance_url: str,
        credentials: Dict[str, str],
    ) -> Optional[ITSMConnector]:
        """Create a connector for the specified ITSM system."""
        system_lower = system.lower()

        if system_lower == "jira":
            return JiraConnector(
                instance_url=instance_url,
                api_token=credentials.get("api_token", ""),
                email=credentials.get("email", ""),
            )

        elif system_lower == "servicenow":
            return ServiceNowConnector(
                instance_url=instance_url,
                client_id=credentials.get("client_id", ""),
                client_secret=credentials.get("client_secret", ""),
            )

        else:
            raise ValueError(f"Unsupported ITSM system: {system}")
