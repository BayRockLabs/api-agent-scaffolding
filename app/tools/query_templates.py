"""
Query template registry.
DEVELOPER ZONE: Add your Snowflake query templates here.
"""

from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field
from enum import Enum


class QueryScope(str, Enum):
    """Query access scope"""

    USER_ONLY = "user_only"
    DEPARTMENT = "department"
    COMPANY = "company"
    PUBLIC = "public"


class QueryParameter(BaseModel):
    """Query parameter definition"""

    name: str
    type: str  # string, integer, date, array
    required: bool = True
    description: str
    default: Optional[Any] = None


class QueryTemplate(BaseModel):
    """Query template definition"""

    id: str
    name: str
    description: str
    sql: str
    parameters: List[QueryParameter] = Field(default_factory=list)
    scope: QueryScope = QueryScope.USER_ONLY
    category: str


# DEVELOPER: Add your query templates here
QUERY_TEMPLATES: Dict[str, QueryTemplate] = {
    # Example template (developers add more)
    "example_query": QueryTemplate(
        id="example_query",
        name="Example Query",
        description="Example query template",
        sql="SELECT * FROM table WHERE id = :id",
        parameters=[
            QueryParameter(name="id", type="string", required=True, description="Record ID")
        ],
        scope=QueryScope.USER_ONLY,
        category="example",
    ),
}


class QueryRegistry:
    """Registry for managing query templates"""

    def __init__(self):
        self.templates = QUERY_TEMPLATES

    def get_template(self, query_id: str) -> Optional[QueryTemplate]:
        return self.templates.get(query_id)

    def list_templates(self, category: Optional[str] = None) -> List[QueryTemplate]:
        templates = list(self.templates.values())
        if category:
            templates = [t for t in templates if t.category == category]
        return templates

    def validate_parameters(self, query_id: str, params: Dict) -> tuple[bool, Optional[str]]:
        """Validate parameters for a query"""
        template = self.get_template(query_id)
        if not template:
            return False, f"Query '{query_id}' not found"

        for param in template.parameters:
            if param.required and param.name not in params:
                return False, f"Required parameter '{param.name}' missing"

        return True, None


# Global registry
query_registry = QueryRegistry()
