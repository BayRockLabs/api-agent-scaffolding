"""
Base service for business logic.
DEVELOPER ZONE: Extend this for your services.
"""

from app.infrastructure.snowflake.repository import BaseSnowflakeRepository
from app.infrastructure.storage.file_service import file_service


class BaseService:
    """
    Base service providing access to infrastructure.
    All domain services should inherit from this.
    """

    def __init__(self):
        # Snowflake repository for data access
        self.snowflake_repo = BaseSnowflakeRepository()

        # File service for file operations
        self.file_service = file_service

    # Developers add their business logic methods here
