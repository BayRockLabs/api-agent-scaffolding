"""
Base repository for Snowflake data access.
This is CORE INFRASTRUCTURE - Do not modify.
"""

from typing import List, Dict, Any, Optional
import structlog

from app.infrastructure.snowflake.engine import snowflake_engine
from app.core.auth import UserContext, UserRole
from app.core.exceptions import SnowflakeException

logger = structlog.get_logger()


class BaseSnowflakeRepository:
    """
    Base repository providing common data access patterns.
    All developer-created repositories should inherit from this.
    """

    def __init__(self):
        self.engine = snowflake_engine

    def execute_query(
        self,
        query: str,
        params: Optional[Dict[str, Any]] = None,
        user_context: Optional[UserContext] = None,
    ) -> List[Dict[str, Any]]:
        """
        Execute query with automatic role-based filtering.

        Args:
            query: SQL query
            params: Query parameters
            user_context: User context for RBAC filtering

        Returns:
            List of result dictionaries
        """
        # Apply role-based filters if user context provided
        if user_context:
            query, params = self._apply_role_filter(query, params or {}, user_context)

        return self.engine.execute_query(query, params)

    def execute_query_one(
        self,
        query: str,
        params: Optional[Dict[str, Any]] = None,
        user_context: Optional[UserContext] = None,
    ) -> Optional[Dict[str, Any]]:
        """Execute query and return first result"""
        results = self.execute_query(query, params, user_context)
        return results[0] if results else None

    def _apply_role_filter(
        self,
        query: str,
        params: Dict[str, Any],
        user_context: UserContext,
    ) -> tuple[str, Dict[str, Any]]:
        """
        Apply role-based filtering to query.

        Override this method in subclasses for custom filtering logic.
        """
        # Add user_id to params for role-based filtering
        params["_user_id"] = user_context.user_id
        params["_user_role"] = user_context.role or ""

        return query, params

    def validate_query_permissions(
        self,
        user_context: UserContext,
        requires_financial: bool = False,
    ) -> bool:
        """
        Validate if user has permission to execute query.

        Args:
            user_context: User context
            requires_financial: Whether query accesses financial data

        Returns:
            True if permitted

        Raises:
            SnowflakeException: If not permitted
        """
        if requires_financial and not user_context.can_access_financial_data():
            raise SnowflakeException(
                "Access denied: Financial data requires finance or admin role",
                details={"user_role": user_context.role},
            )

        return True
