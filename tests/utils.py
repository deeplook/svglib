from io import StringIO
from textwrap import dedent

from svglib.svglib import svg2rlg


def drawing_from_svg(content):
    return svg2rlg(StringIO(dedent(content)))
