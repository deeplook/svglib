from io import StringIO
from textwrap import dedent

from lxml.etree import XML

from svglib.svglib import NodeTracker, svg2rlg


def drawing_from_svg(content):
    return svg2rlg(StringIO(dedent(content)))


def minimal_svg_node(content):
    return NodeTracker(XML(content), None, 0, None, False)
