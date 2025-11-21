"""
Widget factory for constructing Generative UI components.
This is CORE INFRASTRUCTURE - Do not modify.
"""

from typing import Dict, Any, List, Optional
import structlog

from app.widgets.schemas import (
    TableWidget,
    ChartWidget,
    MapWidget,
    CardWidget,
    ListWidget,
)

logger = structlog.get_logger()


class WidgetFactory:
    """Factory for constructing widgets from data"""

    @staticmethod
    def create_table(
        title: str,
        columns: List[str],
        rows: List[List[Any]],
        metadata: Optional[Dict] = None,
    ) -> Dict:
        """Create table widget"""
        widget = TableWidget(
            title=title,
            columns=columns,
            rows=rows,
            metadata=metadata,
        )
        logger.info("Table widget created", title=title, rows=len(rows))
        return widget.dict()

    @staticmethod
    def create_chart(
        chart_type: str,
        title: str,
        data: Dict,
        options: Optional[Dict] = None,
    ) -> Dict:
        """Create chart widget"""
        widget = ChartWidget(
            chart_type=chart_type,
            title=title,
            data=data,
            options=options,
        )
        logger.info("Chart widget created", title=title, type=chart_type)
        return widget.dict()

    @staticmethod
    def create_map(
        title: str,
        markers: List[Dict],
        center: Dict[str, float],
        zoom: int = 10,
    ) -> Dict:
        """Create map widget"""
        widget = MapWidget(
            title=title,
            markers=markers,
            center=center,
            zoom=zoom,
        )
        logger.info("Map widget created", title=title, markers=len(markers))
        return widget.dict()

    @staticmethod
    def create_card(
        title: str,
        content: str,
        subtitle: Optional[str] = None,
        metadata: Optional[Dict] = None,
    ) -> Dict:
        """Create card widget"""
        widget = CardWidget(
            title=title,
            subtitle=subtitle,
            content=content,
            metadata=metadata,
        )
        logger.info("Card widget created", title=title)
        return widget.dict()

    @staticmethod
    def create_list(
        title: str,
        items: List[Dict],
        metadata: Optional[Dict] = None,
    ) -> Dict:
        """Create list widget"""
        widget = ListWidget(
            title=title,
            items=items,
            metadata=metadata,
        )
        logger.info("List widget created", title=title, items=len(items))
        return widget.dict()


# Global factory instance
widget_factory = WidgetFactory()
