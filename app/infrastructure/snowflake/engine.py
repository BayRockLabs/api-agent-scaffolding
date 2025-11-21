"""
Snowflake SQLAlchemy engine with connection pooling.
This is CORE INFRASTRUCTURE - Do not modify.
"""

from sqlalchemy import create_engine, text
from sqlalchemy.pool import QueuePool
from sqlalchemy.engine import Engine
from typing import List, Dict, Any, Optional
import structlog

from app.core.config import settings
from app.core.exceptions import SnowflakeException

logger = structlog.get_logger()


class SnowflakeEngine:
    """
    Snowflake database engine with connection pooling.
    Shared across all services and tools.
    """

    def __init__(self):
        self.engine: Optional[Engine] = None
        self._initialize_engine()

    def _initialize_engine(self):
        """Initialize SQLAlchemy engine with connection pooling"""
        try:
            self.engine = create_engine(
                settings.snowflake_url,
                poolclass=QueuePool,
                pool_size=settings.SNOWFLAKE_POOL_SIZE,
                max_overflow=settings.SNOWFLAKE_MAX_OVERFLOW,
                pool_pre_ping=True,  # Verify connections before using
                pool_recycle=3600,  # Recycle connections after 1 hour
                echo=settings.DEBUG,
            )

            logger.info(
                "Snowflake engine initialized",
                account=settings.SNOWFLAKE_ACCOUNT,
                database=settings.SNOWFLAKE_DATABASE,
                warehouse=settings.SNOWFLAKE_WAREHOUSE,
                pool_size=settings.SNOWFLAKE_POOL_SIZE,
            )

        except Exception as e:
            logger.error("Failed to initialize Snowflake engine", error=str(e))
            raise SnowflakeException(f"Engine initialization failed: {str(e)}")

    def execute_query(
        self, query: str, params: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Execute a SQL query and return results as list of dicts.

        Args:
            query: SQL query string (can use :param_name for parameters)
            params: Dictionary of parameter values

        Returns:
            List of dictionaries (one per row)

        Raises:
            SnowflakeException: If query execution fails
        """
        if not self.engine:
            raise SnowflakeException("Engine not initialized")

        try:
            with self.engine.connect() as connection:
                result = connection.execute(text(query), params or {})

                # Convert to list of dicts
                columns = result.keys()
                rows = [dict(zip(columns, row)) for row in result.fetchall()]

                logger.info(
                    "Query executed successfully",
                    rows_returned=len(rows),
                    has_params=bool(params),
                )

                return rows

        except Exception as e:
            logger.error(
                "Query execution failed",
                error=str(e),
                query=query[:200],  # Log first 200 chars
            )
            raise SnowflakeException(
                f"Query execution failed: {str(e)}",
                details={"query": query[:200]},
            )

    def execute_query_one(
        self, query: str, params: Optional[Dict[str, Any]] = None
    ) -> Optional[Dict[str, Any]]:
        """Execute query and return first row only"""
        results = self.execute_query(query, params)
        return results[0] if results else None

    def test_connection(self) -> bool:
        """Test database connection"""
        try:
            self.execute_query("SELECT 1 AS test")
            logger.info("Snowflake connection test successful")
            return True
        except Exception as e:
            logger.error("Snowflake connection test failed", error=str(e))
            return False

    def dispose(self):
        """Dispose of engine and close all connections"""
        if self.engine:
            self.engine.dispose()
            logger.info("Snowflake engine disposed")


# Global shared instance
snowflake_engine = SnowflakeEngine()
