"""
Database constants and enums.
Centralized location for all database-related constants to avoid magic strings.
"""
from enum import Enum


class UserType(str, Enum):
    """User type enumeration for authentication."""
    STUDENT = "student"
    PROFESSIONAL = "professional"


class AssignmentStatus(str, Enum):
    """Assignment status enumeration."""
    ACTIVE = "active"
    COMPLETED = "completed"
    PAST_DUE = "past_due"


class SuggestionStatus(str, Enum):
    """Tool suggestion status enumeration."""
    PENDING = "pending"
    APPROVED = "approved"
    DENIED = "denied"


class GradeLevel(str, Enum):
    """Grade level enumeration."""
    M1 = "M1"
    M2 = "M2"


class FormationType(str, Enum):
    """Formation type enumeration."""
    FI = "FI"
    FA = "FA"

