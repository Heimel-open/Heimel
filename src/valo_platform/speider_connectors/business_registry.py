"""Abstract Business Registry Connector Interface

Speider uses this interface. Concrete implementations (Firmafakta, Brønnøysund, etc.)
are swappable without changing Speider's composition logic.
"""

from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
from datetime import datetime

from .models import Company, Person, Shareholder, Role


class BusinessRegistryConnector(ABC):
    """Abstract interface for business registry data sources."""

    @abstractmethod
    def get_company(self, org_number: str) -> Optional[Company]:
        """Retrieve company by organization number."""
        pass

    @abstractmethod
    def find_company_by_name(self, name: str) -> List[Company]:
        """Search for companies by name."""
        pass

    @abstractmethod
    def get_company_shareholders(self, org_number: str) -> List[Shareholder]:
        """Get shareholders of a company."""
        pass

    @abstractmethod
    def get_company_roles(self, org_number: str) -> List[Role]:
        """Get board members, CEO, and other roles."""
        pass

    @abstractmethod
    def get_person_holdings(self, person_id: str) -> List[Dict[str, Any]]:
        """Get stock holdings for a person."""
        pass

    @abstractmethod
    def get_company_financials(self, org_number: str) -> Dict[str, Any]:
        """Get latest financial statement."""
        pass

    @abstractmethod
    def get_company_grants(self, org_number: str) -> List[Dict[str, Any]]:
        """Get grants/subsidies awarded to company."""
        pass

    @abstractmethod
    def search_companies(
        self,
        location: Optional[str] = None,
        business_code: Optional[str] = None,
        min_employees: Optional[int] = None,
        max_employees: Optional[int] = None,
    ) -> List[Company]:
        """Search companies by criteria."""
        pass

    @abstractmethod
    def get_connector_name(self) -> str:
        """Get connector name (e.g., 'Firmafakta', 'Brønnøysund')."""
        pass

    @abstractmethod
    def is_healthy(self) -> bool:
        """Check if connector is operational."""
        pass

    @abstractmethod
    def get_last_updated(self) -> Optional[datetime]:
        """Get last update timestamp from source."""
        pass
