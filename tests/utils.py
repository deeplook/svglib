from io import StringIO
from textwrap import dedent
from typing import Any

from lxml.etree import XML

from svglib.svglib import NodeTracker, svg2rlg


def drawing_from_svg(content: str) -> Any:
    return svg2rlg(StringIO(dedent(content)))  # type: ignore


def minimal_svg_node(content: str) -> NodeTracker:
    return NodeTracker(XML(content), None, 0, None, False)
