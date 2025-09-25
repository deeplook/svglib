from io import StringIO
from textwrap import dedent
from typing import Any

from lxml.etree import XML

from svglib.svglib import NodeTracker, svg2rlg


def drawing_from_svg(content: str) -> Any:
    """Convert a SVG string to a ReportLab Drawing."""
    return svg2rlg(StringIO(dedent(content)))  # type: ignore


def minimal_svg_node(content: str) -> NodeTracker:
    """Convert a minimal SVG snippet to a NodeTracker."""
    return NodeTracker(XML(content), None, 0, None, False)
