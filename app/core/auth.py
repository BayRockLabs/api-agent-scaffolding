"""
Core authentication and RBAC system.
This is CORE INFRASTRUCTURE - Do not modify.
"""

from pydantic import BaseModel, Field
from typing import Optional
from enum import Enum


class UserRole(str, Enum):
    """Predefined user roles"""

    SALES_REP = "sales_rep"
    MANAGER = "manager"
    ANALYST = "analyst"
    FINANCE = "finance"
    ADMIN = "admin"


class UserContext(BaseModel):
    """User context extracted from request headers"""

    user_id: str = Field(..., description="Unique user identifier")
    email: str = Field(..., description="User email address")
    role: Optional[str] = Field(None, description="User role for RBAC")

    def has_role(self, role: str) -> bool:
        """Check if user has specific role"""
        return self.role == role if self.role else False

    def is_admin(self) -> bool:
        """Check if user is admin"""
        return self.role == UserRole.ADMIN.value

    def can_access_financial_data(self) -> bool:
        """Check if user can access financial data"""
        return self.role in [UserRole.FINANCE.value, UserRole.ADMIN.value]


def validate_user_context(
    user_id: Optional[str],
    email: Optional[str],
    role: Optional[str] = None,
) -> UserContext:
    """"""
    Validate and create user context from headers.

    Raises:
        ValueError: If required fields are missing
    """
    if not user_id or not email:
        raise ValueError(
            f"Missing authentication headers. " f"user_id={user_id}, email={email}"
        )

    return UserContext(user_id=user_id, email=email, role=role)
