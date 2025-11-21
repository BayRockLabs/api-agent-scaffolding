"""
Widget schemas for Generative UI (CopilotKit).
This is CORE INFRASTRUCTURE - Do not modify.
"""

from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional, Literal


class TableWidget(BaseModel):
    """Table widget for displaying tabular data"""

    type: Literal["table"] = "table"
    title: str
    columns: List[str]
    rows: List[List[Any]]
    metadata: Optional[Dict[str, Any]] = None


class ChartWidget(BaseModel):
    """Chart widget for visualizations"""

    type: Literal["chart"] = "chart"
    chart_type: str = Field(..., description="bar, line, pie, scatter")
    title: str
    data: Dict[str, Any]
    options: Optional[Dict[str, Any]] = None


class MapWidget(BaseModel):
    """Map widget for geospatial data"""

    type: Literal["map"] = "map"
    title: str
    markers: List[Dict[str, Any]]  # [{lat, lng, label, data}]
    center: Dict[str, float]  # {lat, lng}
    zoom: int = 10


class CardWidget(BaseModel):
    """Card widget for single item display"""

    type: Literal["card"] = "card"
    title: str
    subtitle: Optional[str] = None
    content: str
    metadata: Optional[Dict[str, Any]] = None


class ListWidget(BaseModel):
    """List widget for items"""

    type: Literal["list"] = "list"
    title: str
    items: List[Dict[str, Any]]
    metadata: Optional[Dict[str, Any]] = None
