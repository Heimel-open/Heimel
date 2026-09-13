from enum import Enum


class VACSDecision(str, Enum):
    ALLOW = "ALLOW"
    MODIFY = "MODIFY"
    DEFER = "DEFER"
    DENY = "DENY"
    STEP_UP = "STEP_UP"
    HALT = "HALT"


class VACSStatus(str, Enum):
    ACTIVE = "ACTIVE"
    EXPIRED = "EXPIRED"
    REVOKED = "REVOKED"
    INVALID = "INVALID"
    UNAUTHORIZED = "UNAUTHORIZED"
