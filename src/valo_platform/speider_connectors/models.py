"""Speider Connector Data Models

Normalized representations of business registry data.
"""

from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


class RoleType(str, Enum):
    """Types of organizational roles."""
    CEO = "ceo"
    BOARD_CHAIR = "board_chair"
    BOARD_MEMBER = "board_member"
    ACCOUNTANT = "accountant"
    AUDITOR = "auditor"
    OWNER = "owner"
    DIRECTOR = "director"


class Company(BaseModel):
    """Normalized company record."""
    org_number: str
    name: str
    short_name: Optional[str] = None
    business_code: Optional[str] = None
    business_description: Optional[str] = None
    municipality: Optional[str] = None
    county: Optional[str] = None
    founded_year: Optional[int] = None
    employee_count: Optional[int] = None
    status: str = "active"  # active, dissolved, etc.
    source: str  # connector name: Firmafakta, Brønnøysund, etc.
    last_updated: datetime = None
    metadata: Dict[str, Any] = {}


class Person(BaseModel):
    """Normalized person record."""
    person_id: str
    name: str
    birth_year: Optional[int] = None
    nationality: Optional[str] = None
    source: str
    metadata: Dict[str, Any] = {}


class Shareholder(BaseModel):
    """Shareholder record."""
    shareholder_id: str
    shareholder_name: str
    shareholder_type: str  # person, company
    ownership_percentage: Optional[float] = None
    share_count: Optional[int] = None
    org_number: str  # company being analyzed
    source: str
    metadata: Dict[str, Any] = {}


class Role(BaseModel):
    """Organizational role (board member, CEO, etc.)."""
    role_id: str
    person_name: str
    person_id: Optional[str] = None
    role_type: RoleType
    org_number: str  # company
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    source: str
    metadata: Dict[str, Any] = {}


class FinancialStatement(BaseModel):
    """Financial data from annual statement."""
    org_number: str
    fiscal_year: int
    revenue: Optional[float] = None
    operating_profit: Optional[float] = None
    equity: Optional[float] = None
    assets: Optional[float] = None
    liabilities: Optional[float] = None
    equity_ratio: Optional[float] = None
    source: str
    last_updated: datetime
    metadata: Dict[str, Any] = {}


class Grant(BaseModel):
    """Grant/subsidy award."""
    grant_id: str
    org_number: str
    grant_type: str  # skattefunn, EU, Innovasjonsrådet, etc.
    amount: float
    currency: str = "NOK"
    awarded_year: int
    program_name: Optional[str] = None
    source: str
    metadata: Dict[str, Any] = {}
