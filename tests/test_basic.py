"""Testsuite for svglib.

This module tests basic functionality. Run with one of these lines from
inside the test directory:

    $ make test
    $ uv run pytest -v -s test_basic.py
"""

import io
import os
import pathlib
import textwrap
from tempfile import NamedTemporaryFile
from typing import Any, Callable, List, Tuple

import pytest
from reportlab.graphics.shapes import (
    _CLOSEPATH,
    _CURVETO,
    _LINETO,
    _MOVETO,
    Group,
    Line,
    Path,
    Polygon,
    PolyLine,
    Rect,
)
from reportlab.lib import colors
from reportlab.lib.units import cm, inch
from reportlab.pdfgen.canvas import FILL_EVEN_ODD

from svglib import svglib, utils
from tests.utils import drawing_from_svg, minimal_svg_node


def _testit(
    func: Callable[..., Any], mapping: List[Tuple[Any, Any]]
) -> List[Tuple[Any, Any, Any]]:
    "Call `func` on input in mapping and return list of failed tests."

    failed: List[Tuple[Any, Any, Any]] = []
    for input, expected in mapping:
        if isinstance(input, dict):
            result = func(**input)
        else:
            result = func(input)
        if not result == expected:
            failed.append((input, result, expected))

    if failed:
        print("failed tests (input, result, expected):")
        for input, result, expected in failed:
            print(f"  {input!r} : {result} != {expected}")

    return failed


class TestSvg2rlgInput:
    test_content = textwrap.dedent(
        """\
        <?xml version="1.0"?>
        <svg xmlns="http://www.w3.org/2000/svg"
             width="1200" height="800"
             viewBox="0 0 36 24">
            <rect y="10" width="36" height="4"/>
        </svg>
    """
    )

    def test_path_as_string_input(self):
        try:
            with NamedTemporaryFile(mode="w", suffix=".svg", delete=False) as fp:
                fp.write(self.test_content)
                file_path = fp.name
            drawing = svglib.svg2rlg(file_path)
            assert drawing is not None
        finally:
            os.unlink(file_path)

    def test_path_as_pathlib_input(self):
        try:
            with NamedTemporaryFile(mode="w", suffix=".svg", delete=False) as fp:
                fp.write(self.test_content)
                file_path = pathlib.Path(fp.name)
            drawing = svglib.svg2rlg(file_path)
            assert drawing is not None
        finally:
            os.unlink(file_path)

    def test_filelike_input(self):
        drawing = svglib.svg2rlg(io.StringIO(self.test_content))
        assert drawing is not None

    def test_filehandle_input(self):
        try:
            with NamedTemporaryFile(mode="w", suffix=".svg", delete=False) as fp:
                fp.write(self.test_content)
                file_path = fp.name
            with open(file_path, "rb") as fp:
                drawing = svglib.svg2rlg(fp)
                assert drawing is not None
        finally:
            os.unlink(file_path)


class TestPaths:
    """Testing path-related code."""

    def test_path_normalisation(self):
        "Test path normalisation."

        mapping = (
            ("", []),
            ("M10 20, L 30 40 ", ["M", [10, 20], "L", [30, 40]]),
            ("M10 20, L 40 40Z", ["M", [10, 20], "L", [40, 40], "Z", []]),
            (
                "M10 20, L 30 40 40 40Z",
                ["M", [10, 20], "L", [30, 40], "L", [40, 40], "Z", []],
            ),
            (
                "  M10 20,L30 40,40 40Z  ",
                ["M", [10, 20], "L", [30, 40], "L", [40, 40], "Z", []],
            ),
            (
                "  M 10 20, M 30 40, L 40 40, Z M 40 50, l 50 60, Z",
                [
                    "M",
                    [10, 20],
                    "L",
                    [30, 40],
                    "L",
                    [40, 40],
                    "Z",
                    [],
                    "M",
                    [40, 50],
                    "l",
                    [50, 60],
                    "Z",
                    [],
                ],
            ),
            (
                "  m 10 20, m 30 40, l 40 40, z",
                ["m", [10, 20], "l", [30, 40], "l", [40, 40], "z", []],
            ),
            (
                "  m 10,20 30,40, l 40 40, z ",
                ["m", [10, 20], "l", [30, 40], "l", [40, 40], "z", []],
            ),
            (
                "M 10,20 30,40, l 40 40, z",
                ["M", [10, 20], "L", [30, 40], "l", [40, 40], "z", []],
            ),
            (
                "M0,0 500,300M500,0 0,300",
                ["M", [0, 0], "L", [500, 300], "M", [500, 0], "L", [0, 300]],
            ),
            ("M10 20, l 5e-5,0", ["M", [10, 20], "l", [5e-5, 0]]),
            (
                "a1.518 1.518  0 011.195-.547 2.401,2.401,0,00-.602,-.297 ",
                [
                    "a",
                    [1.518, 1.518, 0, 0, 1, 1.195, -0.547],
                    "a",
                    [2.401, 2.401, 0, 0, 0, -0.602, -0.297],
                ],
            ),
            (
                (
                    "m246.026 120.178c-.558-.295-1.186-.768-1.395-1.054-.314-.438"
                    "-.132-.456 1.163-.104 2.318.629 3.814.383 5.298-.873l1.308"
                    "-1.103 1.54.784c.848.428 1.748.725 2.008.656.667-.176 2.05"
                    "-1.95 2.005-2.564-.054-.759.587-.568.896.264.615 1.631-.281 "
                    "3.502-1.865 3.918-.773.201-1.488.127-2.659-.281-1.438-.502"
                    "-1.684-.494-2.405.058-1.618 1.239-3.869 1.355-5.894.299z"
                ),
                [
                    "m",
                    [246.026, 120.178],
                    "c",
                    [-0.558, -0.295, -1.186, -0.768, -1.395, -1.054],
                    "c",
                    [-0.314, -0.438, -0.132, -0.456, 1.163, -0.104],
                    "c",
                    [2.318, 0.629, 3.814, 0.383, 5.298, -0.873],
                    "l",
                    [1.308, -1.103],
                    "l",
                    [1.54, 0.784],
                    "c",
                    [0.848, 0.428, 1.748, 0.725, 2.008, 0.656],
                    "c",
                    [0.667, -0.176, 2.05, -1.95, 2.005, -2.564],
                    "c",
                    [-0.054, -0.759, 0.587, -0.568, 0.896, 0.264],
                    "c",
                    [0.615, 1.631, -0.281, 3.502, -1.865, 3.918],
                    "c",
                    [-0.773, 0.201, -1.488, 0.127, -2.659, -0.281],
                    "c",
                    [-1.438, -0.502, -1.684, -0.494, -2.405, 0.058],
                    "c",
                    [-1.618, 1.239, -3.869, 1.355, -5.894, 0.299],
                    "z",
                    [],
                ],
            ),
            # scientific notation
            (
                "M 114.2,1.919e2 1e-4,22.5E-1",
                ["M", [114.2, 191.9], "L", [0.0001, 2.25]],
            ),
            (
                "a1518e-3 .1518E2  0 011.195E+2-.547",
                ["a", [1.518, 15.18, 0, 0, 1, 119.5, -0.547]],
            ),
        )
        failed = _testit(utils.normalise_svg_path, mapping)
        assert len(failed) == 0

    def test_relative_move_after_closepath(self):
        """
        A relative subpath is relative to the point *after* the previous
        closePath op (which is not recorded in path.points).
        """
        converter = svglib.Svg2RlgShapeConverter(None)
        node = minimal_svg_node('<path d="M0 0,0 1,1 1z m-1-1 0 1 1 0z"/>')
        # last point of this path should be 0 0
        path = converter.convertPath(node).contents[0]
        assert path.points[-2:] == [0, 0]

    def test_cubic_bezier_shorthand(self):
        # If there is no previous command or if the previous command was not
        # an C, c, S or s, assume the first control point is coincident with
        # the current point.
        converter = svglib.Svg2RlgShapeConverter(None)
        node = minimal_svg_node(
            '<path d="M3,4c-0.5-0.25-1.3-0.77-1.3-1.8h2.5s0.04,0.46,0.04,1.48z"/>'
        )
        path = converter.convertPath(node).contents[0]
        assert path.operators == [_MOVETO, _CURVETO, _LINETO, _CURVETO, _CLOSEPATH]
        assert path.points == [
            3.0,
            4.0,
            2.5,
            3.75,
            1.7,
            3.23,
            1.7,
            2.2,
            4.2,
            2.2,
            4.2,
            2.2,
            4.24,
            2.66,
            4.24,
            3.68,
        ]

    def test_elliptical_arc(self):
        converter = svglib.Svg2RlgShapeConverter(None)
        node = minimal_svg_node(
            '<path d="M334.500000 0.000000 A185.000000 185.000000 0 0 1 '
            "334.500000 0.000000 L334.500000 185.000000 A0.000000 0.000000 0 0 0 "
            '334.500000 185.000000 z"/>'
        )
        # First elliptical arc with identical start/end points, ignored
        path = converter.convertPath(node).contents[0]
        assert path.points == [334.5, 0.0, 334.5, 185.0, 334.5, 185.0]

    def test_unclosed_paths(self):
        converter = svglib.Svg2RlgShapeConverter(None)
        node = minimal_svg_node('<path d="M0,0 4.5,3 0,6M4.5,3H9" id="W"/>')
        group = converter.convertPath(node)
        assert len(group.contents) == 2
        closed_path = group.contents[0]
        unclosed_path = group.contents[1]
        assert len(closed_path.points) == len(unclosed_path.points)
        assert closed_path.operators == [
            _MOVETO,
            _LINETO,
            _LINETO,
            _CLOSEPATH,
            _MOVETO,
            _LINETO,
            _CLOSEPATH,
        ]
        assert unclosed_path.operators == [_MOVETO, _LINETO, _LINETO, _MOVETO, _LINETO]

    def test_empty_path(self):
        converter = svglib.Svg2RlgShapeConverter(None)
        node = minimal_svg_node('<path id="W"/>')
        group = converter.convertPath(node)
        assert group is None

    def test_clipped_path(self):
        drawing = drawing_from_svg(
            """
            <?xml version="1.0"?>
            <svg version="1.1" xmlns="http://www.w3.org/2000/svg"
                 xmlns:xlink="http://www.w3.org/1999/xlink" width="660" height="480">
                <defs>
                    <path id="my-clipping-path" d="M99,176 L 110 170 112 172Z"/>
                    <rect id="my-clipping-rect" x="88.155" y="163" width="419.69"
                          height="20.68" fill="red" stroke="blue"/>
                </defs>
                <clipPath id="my-clip-path">
                    <use xlink:href="#my-clipping-path"/>
                </clipPath>
                <clipPath id="my-clip-rect">
                    <use xlink:href="#my-clipping-rect"/>
                </clipPath>
                <path clip-path="url(#my-clip-path)" d="M99,176 L 110 170 112 172Z"/>
                <path clip-path="url(#my-clip-rect)" d="M99,176 L 110 170 112 172Z"/>
            </svg>
        """
        )
        assert isinstance(
            drawing.contents[0].contents[0].contents[0], svglib.ClippingPath
        )
        # Clipping rect was converted to a path
        rect_clip = drawing.contents[0].contents[1].contents[0]
        assert isinstance(rect_clip, svglib.ClippingPath)
        # Fill and stroke properties are force-deleted.
        assert rect_clip.getProperties()["fillColor"] is None
        assert rect_clip.getProperties()["strokeColor"] is None


def force_cmyk(rgb: Any) -> Any:
    c, m, y, k = colors.rgb2cmyk(rgb.red, rgb.green, rgb.blue)
    return colors.CMYKColor(c, m, y, k, alpha=rgb.alpha)


class TestColorAttrConverter:
    "Testing color attribute conversion."

    def test_0(self):
        "Test color attribute conversion."

        mapping = (
            ("red", colors.red),
            ("#ff0000", colors.red),
            ("#ff000055", colors.Color(1, 0, 0, 1 / 3)),
            ("#f00", colors.red),
            ("#f00f", colors.red),
            ("rgb(100%,50%,10%)", colors.Color(1, 128 / 255, 26 / 255, 1)),
            ("rgb(255, 0, 0)", colors.red),
            ("rgba(255, 255, 128, .5)", colors.Color(1, 1, 128 / 255, 0.5)),
            ("fuchsia", colors.Color(1, 0, 1, 1)),
            ("slategrey", colors.HexColor(0x708090)),
            ("transparent", colors.Color(0, 0, 0, 0)),
            ("whatever", None),
        )
        ac = svglib.Svg2RlgAttributeConverter()
        failed = _testit(ac.convertColor, mapping)
        assert len(failed) == 0

    def test_1(self):
        "Test color attribute conversion to CMYK"

        mapping = (
            ("red", force_cmyk(colors.red)),
            ("#ff0000", force_cmyk(colors.red)),
            ("#f00", force_cmyk(colors.red)),
            ("rgb(100%,0%,0%)", force_cmyk(colors.red)),
            ("rgb(255, 0, 0)", force_cmyk(colors.red)),
            ("rgb(0,255, 0)", force_cmyk(colors.Color(0, 1, 0))),
            ("rgb(0, 0, 255)", force_cmyk(colors.Color(0, 0, 1))),
        )
        ac = svglib.Svg2RlgAttributeConverter(color_converter=force_cmyk)
        failed = _testit(ac.convertColor, mapping)
        assert len(failed) == 0


class TestLengthAttrConverter:
    "Testing length attribute conversion."

    def test_length_conversion(self):
        "Test length attribute conversion."

        mapping = (
            ("0", 0),
            ("316", 316),
            ("-316", -316),
            ("-3.16", -3.16),
            ("-1e-2", -0.01),
            ("1e-5", 1e-5),
            ("1e1cm", 10 * cm),
            ("1e1in", 10 * inch),
            ("-8e-2cm", (-8e-2) * cm),
            ("20px", 20 * 0.75),
            ("20pt", 20),
            ("1.5em", 12 * 1.5),
            ("10.5mm", 10.5 * (cm * 0.1)),
            ("3, 5 -7", [3, 5, -7]),
            ("2pt  12pt", [2, 12]),
            ("10 20 30", [10.0, 20.0, 30.0]),
        )
        ac = svglib.Svg2RlgAttributeConverter()
        failed = _testit(ac.convertLength, mapping)
        assert len(failed) == 0
        assert ac.convertLength("1.5em", em_base=16.5) == 24.75

    def test_percentage_conversion(self):
        "Test percentage length attribute conversion."

        ac = svglib.Svg2RlgAttributeConverter()
        ac.set_box(svglib.Box(0, 0, 50, 150))
        # Percentages depend on current viewport and type of attribute
        length = ac.convertLength("1e1%", attr_name="width")
        assert length == 5
        length = ac.convertLength("1e1%", attr_name="height")
        assert length == 15

    def test_length_list_conversion(self):
        "Test length list attribute conversion."

        mapping = (
            (" 5cm 5in", [5 * cm, 5 * inch]),
            (" 5, 5", [5, 5]),
        )
        ac = svglib.Svg2RlgAttributeConverter()
        failed = _testit(ac.convertLengthList, mapping)
        assert len(failed) == 0


class TestTransformAttrConverter:
    "Testing transform attribute conversion."

    def test_0(self):
        "Test transform attribute conversion."

        mapping = (
            ("", []),
            (
                "scale(2) translate(10,-20.5)",
                [("scale", 2.0), ("translate", (10.0, -20.5))],
            ),
            (
                "scale(0.9), translate(27,40)",
                [("scale", 0.9), ("translate", (27.0, 40.0))],
            ),
            # Invalid/unsupported expressions return empty list
            ("scale(0.9), translate", []),
            ("ref(svg)", []),
        )
        ac = svglib.Svg2RlgAttributeConverter()
        failed = _testit(ac.convertTransform, mapping)
        assert len(failed) == 0


class TestAttrConverter:
    "Testing multi-attribute conversion."

    def test_0(self):
        "Test multi-attribute conversion."

        mapping = (
            ("fill: black; stroke: yellow", {"fill": "black", "stroke": "yellow"}),
        )
        ac = svglib.Svg2RlgAttributeConverter()
        failed = _testit(ac.parseMultiAttributes, mapping)
        assert len(failed) == 0

    def test_findAttr(self):
        """
        Test various attribute peculiarities.
        """
        ac = svglib.Svg2RlgAttributeConverter()
        # Whitespace in attribute values shouldn't disturb parsing.
        node = minimal_svg_node('<rect fill=" #00A1DE\n"/>')
        assert ac.findAttr(node, "fill") == "#00A1DE"

        # Attributes starting with '-' are not supported.
        node = minimal_svg_node('<text style="-inkscape-font-specification:Arial"/>')
        assert ac.findAttr(node, "-inkscape-font-specification") == ""

    def test_findAttr_parents(self):
        ac = svglib.Svg2RlgAttributeConverter()
        rect_node = next(
            minimal_svg_node(
                '<g style="fill:#008000;stroke:#008000;"><rect style="fill:#ff0;"/></g>'
            ).iter_children()
        )
        assert ac.findAttr(rect_node, "fill") == "#ff0"
        assert ac.findAttr(rect_node, "stroke") == "#008000"

    def test_no_fill_on_shape(self):
        """
        Any shape with no fill property should set black color in rlg syntax.
        """
        drawing = drawing_from_svg(
            """
            <?xml version="1.0"?>
            <svg xmlns="http://www.w3.org/2000/svg"
                 width="1200" height="800"
                 viewBox="0 0 36 24">
                <rect y="10" width="36" height="4"/>
            </svg>
        """
        )
        assert drawing.contents[0].contents[0].fillColor == colors.black

    def test_fillopacity(self):
        """
        The fill-opacity property set the alpha of the color.
        """
        drawing = drawing_from_svg(
            """
            <?xml version="1.0"?>
            <svg version="1.1"
                 xmlns="http://www.w3.org/2000/svg"
                 width="660" height="480">
                <polygon id="triangle" points="0,-29.14 -25.23, 14.57 25.23, 14.57"
                         stroke="#0038b8" stroke-width="5.5" fill-opacity="0"/>
            </svg>
        """
        )
        assert drawing.contents[0].contents[0].fillColor == colors.Color(0, 0, 0, 0)

    def test_fillcolor_alpha_set_fillopacity(self):
        converter = svglib.Svg2RlgShapeConverter(None)
        node = minimal_svg_node('<polygon fill="#ff000080"/>')
        poly = Polygon()
        converter.applyStyleOnShape(poly, node)
        assert poly.fillOpacity == 128 / 255
        assert poly.strokeOpacity == 1

    def test_strokecolor_alpha_set_strokeopacity(self):
        converter = svglib.Svg2RlgShapeConverter(None)
        node = minimal_svg_node('<polygon stroke="#cccccca0"/>')
        poly = Polygon()
        converter.applyStyleOnShape(poly, node)
        assert poly.fillOpacity == 1
        assert poly.strokeOpacity == 160 / 255

    def test_fillrule(self):
        converter = svglib.Svg2RlgShapeConverter(None)
        node = minimal_svg_node('<polygon fill-rule="evenodd"/>')
        poly = Polygon()
        converter.applyStyleOnShape(poly, node)
        assert poly._fillRule == FILL_EVEN_ODD

    def test_stroke(self):
        converter = svglib.Svg2RlgShapeConverter(None)
        node = minimal_svg_node(
            '<path d="m0,6.5h27m0,5H0" stroke="#FFF" stroke-opacity="0.5"/>'
        )
        path = Path()
        converter.applyStyleOnShape(path, node)
        assert path.strokeColor == colors.white
        assert path.strokeOpacity == 0.5
        assert path.strokeWidth == 1


class TestApplyTransformOnGroup:
    def test_translate_only_x(self):
        """
        When the second translate value is missing, 0 is assumed.
        """
        group = Group()
        converter = svglib.Svg2RlgShapeConverter(None)
        transform = "translate(10)"
        converter.applyTransformOnGroup(transform, group)
        assert group.transform == (1, 0, 0, 1, 10, 0)

    def test_transform_matrix(self):
        NEUTRAL_TRANSFORM = (1, 0, 0, 1, 0, 0)
        group = Group()
        converter = svglib.Svg2RlgShapeConverter(None)
        # if the values are not 6, ignore
        transform = "matrix(1 2 3 4 5)"
        converter.applyTransformOnGroup(transform, group)
        assert group.transform == NEUTRAL_TRANSFORM

        # Matrix-only
        group = Group()
        transform = "matrix(3 1 -1 3 30 40)"
        converter.applyTransformOnGroup(transform, group)
        assert group.transform == (3, 1, -1, 3, 30, 40)

        # Combination of matrix and translation
        group = Group()
        transform = "translate(40 40) matrix(3 1 -1 3 30 40)"
        converter.applyTransformOnGroup(transform, group)
        assert group.transform == (3, 1, -1, 3, 70, 80)


class TestStyleSheets:
    def test_css_stylesheet(self):
        drawing = drawing_from_svg(
            """
            <?xml version="1.0"?>
            <svg width="777" height="267" xml:space="preserve">
              <defs>
                <style type="text/css">
                path { fill:none; }
                #p1 { fill:rgb(255,0,0) !important; }
                #p2 { fill:rgb(255,0,0); }
                .paths { stroke-width:1.5; }
                </style>
              </defs>
              <g id="g1">
                <path id="p1" class="paths" d="M 0,-100 V 0 H 50"/>
                <path id="p2" class="paths other" style="fill: #000000"
                      d="M 0,100 V 0 H 50"/>
              </g>
            </svg>
        """
        )
        main_group = drawing.contents[0]
        assert main_group.contents[0].contents[0].contents[0].fillColor == colors.red
        # The style on the element has precedence over the global style
        assert main_group.contents[0].contents[1].contents[0].fillColor == colors.black
        assert main_group.contents[0].contents[1].contents[0].strokeWidth == 1.5

    def test_css_stylesheet_multiple_style_tags(self):
        drawing = drawing_from_svg(
            """
            <?xml version="1.0"?>
            <svg width="777" height="267" xml:space="preserve">
              <defs>
                <style type="text/css">
                #p1 { fill:rgb(255,0,0) }
                </style>
                <style type="text/css">
                #p2 { fill:rgb(0,0,0); }
                </style>
              </defs>
              <g>
                <path id="p1" d="M 0,-100 V 0 H 50"/>
                <path id="p2" d="M 0,100 V 0 H 50"/>
              </g>
            </svg>
        """
        )
        main_group = drawing.contents[0]
        assert main_group.contents[0].contents[0].contents[0].fillColor == colors.red
        assert main_group.contents[0].contents[1].contents[0].fillColor == colors.black

    def test_css_nth_of_type(self):
        drawing = drawing_from_svg(
            """
            <?xml version="1.0"?>
            <svg viewBox="0 0 649 487">
              <style type="text/css">
.bold1:nth-of-type(2n) { font-weight: bold; font-size: 1.1em; }
</style>
              <g>
                <text class="bold1" x="324" y="304">A</text>
                <text class="bold1" x="324" y="384">B</text>
                <text class="bold1" x="324" y="464">C</text>
              </g>
            </svg>
        """
        )
        main_group = drawing.contents[0]
        assert main_group.contents[0].contents[0].contents[0].fontName == "Helvetica"
        assert (
            main_group.contents[0].contents[1].contents[0].fontName == "Helvetica-Bold"
        )
        assert main_group.contents[0].contents[2].contents[0].fontName == "Helvetica"

    def test_import_rule_no_crash(self):
        # Just test that svglib does not crash. Import rules are currently ignored.
        drawing = drawing_from_svg(
            """
            <svg>
              <defs>
                <style type="text/css">
                  @import url('https://fonts.example.org/css2?family=Ubuntu+Condensed');
                </style>
              </defs>
            </svg>
        """
        )
        assert drawing is not None


class TestGroupNode:
    def test_svg_groups_have_svgid(self):
        drawing = drawing_from_svg(
            """
            <?xml version="1.0"?>
            <svg width="777" height="267">
                <g id="g856">
                    <rect
                         y="107.07929"
                         x="64.942139"
                         height="19.506001"
                         width="34.690311"
                         id="rect850"
                </g>
            </svg>
        """
        )
        main_group = drawing.contents[0]

        (gr,) = main_group.contents
        assert gr.svgid == "g856"
        assert isinstance(gr, Group)

    def test_created_groups_have_svgid_of_their_content(self):
        drawing = drawing_from_svg(
            """
            <?xml version="1.0"?>
            <svg width="777" height="267">
                <g id="g856">
                    <rect
                         y="107.07929"
                         x="64.942139"
                         height="19.506001"
                         width="34.690311"
                         id="rect850"
                    <rect
                         y="136.5135"
                         x="108.62624"
                         height="17.637161"
                         width="29.083796"
                         id="rect852"
                    <path
                       d="M 601.06712,388.63166 H 954.67961"
                       id="path819" />
                </g>
            </svg>
        """
        )
        main_group = drawing.contents[0]
        (gr,) = main_group.contents

        r1_gr, r2_gr, pth_gr = gr.contents
        assert r1_gr.svgid == "rect850"
        assert r2_gr.svgid == "rect852"
        assert pth_gr.svgid == "path819"
        assert isinstance(pth_gr, Group)

    def test_svg_layers_have_label(self):
        drawing = drawing_from_svg(
            """
            <?xml version="1.0"?>
            <svg width="777" height="267">
                <g inkscape:groupmode="layer"
                 id="layer2"
                 inkscape:label="x_axis"
                 style="display:inline"
                 transform="translate(-476.20282,35.510971)">
                <path
                   d="M 601.06712,388.63166 H 954.67961"
                   id="path819" />
                </g>
            </svg>
        """
        )
        main_group = drawing.contents[0]
        (gr,) = main_group.contents
        assert gr.label == "x_axis"


class TestTextNode:
    def test_space_preservation(self):
        drawing = drawing_from_svg(
            """
            <?xml version="1.0"?>
            <svg width="777" height="267">
              <text style="fill:#000000; stroke:none; font-size:28;">
                <tspan>TITLE    1</tspan>
                <tspan x="-10.761" y="33.487">Subtitle</tspan>
              </text>
            </svg>
        """
        )
        main_group = drawing.contents[0]
        # By default, only two tspans produce String objects + 1 for the space
        # *between tspans, the start/end spaces/newlines are ignored.
        assert len(main_group.contents[0].contents) == 3
        assert main_group.contents[0].contents[0].text == "TITLE 1"

        drawing = drawing_from_svg(
            """
            <?xml version="1.0"?>
            <svg width="777" height="267" xml:space="preserve">
              <text style="fill:#000000; stroke:none; font-size:28;">
                <tspan>TITLE    1</tspan>
                <tspan x="-10.761" y="33.487">Subtitle</tspan>
              </text>
            </svg>
        """
        )
        main_group = drawing.contents[0]
        assert main_group.contents[0].contents[0].text == "     "
        assert main_group.contents[0].contents[1].text == "TITLE    1"

        drawing = drawing_from_svg(
            """
            <?xml version="1.0"?>
            <svg width="777" height="267">
              <text style="fill:#000000; stroke:none; font-size:28;">
                <tspan>TITLE    1</tspan>
                <tspan x="-10.761" y="33.487">Subtitle</tspan>
              </text>
              <text xml:space="preserve">  with   spaces </text>
            </svg>
        """
        )
        main_group = drawing.contents[0]
        # xml:space can be overriden per text node
        assert main_group.contents[0].contents[0].text == "TITLE 1"
        assert main_group.contents[1].contents[0].text == "  with   spaces "

    def test_tspan_position(self):
        """
        The x/y positions of a tspan are either relative to the current text
        position, or can be absoluted by specifying the x/y attributes.
        """
        drawing = drawing_from_svg(
            """
            <?xml version="1.0"?>
            <svg width="777" height="267">
              <text x="10" y="20" style="fill:#000000; stroke:none; font-size:28;">
                The start
                <tspan>TITLE 1</tspan>
                <!-- x position relative to current text position
                     y position offset in em -->
                <tspan dy="1.3em">(after title)</tspan>
                <!-- absolute position -->
                <tspan x="16.75" y="33.487">Subtitle</tspan>
                <!-- absolute position + shifting -->
                <tspan x="10" y="20" dx="3em" dy="1.5em">Complete</tspan>
                The end
              </text>
            </svg>
        """
        )
        main_group = drawing.contents[0]
        assert main_group.contents[0].contents[0].x == 10
        assert main_group.contents[0].contents[0].y == -20
        assert main_group.contents[0].contents[0].text == "The start "
        assert main_group.contents[0].contents[1].x > 10
        assert main_group.contents[0].contents[1].text == "TITLE 1"
        assert main_group.contents[0].contents[2].text == " "
        assert main_group.contents[0].contents[3].y == -20 - (1.3 * 28)
        assert main_group.contents[0].contents[3].text == "(after title)"
        assert main_group.contents[0].contents[4].text == " "
        assert main_group.contents[0].contents[5].x == 16.75
        assert main_group.contents[0].contents[5].y == -33.487
        assert main_group.contents[0].contents[5].text == "Subtitle"
        assert main_group.contents[0].contents[6].text == " "
        assert main_group.contents[0].contents[7].x == 10 + (3 * 28)
        assert main_group.contents[0].contents[7].y == -20 - (1.5 * 28)
        assert main_group.contents[0].contents[7].text == "Complete"
        assert main_group.contents[0].contents[8].text == " The end"


class TestRectNode:
    def test_rx_ry(self):
        converter = svglib.Svg2RlgShapeConverter(None)
        node = minimal_svg_node(
            '<rect rx="10" ry="4" width="10" height="3" x="0" y="0"/>'
        )
        rect = converter.convertRect(node)
        # rx/ry cannot be more than half the rect lengths.
        assert rect.rx == 5
        assert rect.ry == 1.5

    def test_rx_ry_lonely(self):
        """If only rx or ry is present, the other default to the same value."""
        converter = svglib.Svg2RlgShapeConverter(None)
        node = minimal_svg_node('<rect rx="2.5" width="10" height="3" x="0" y="0"/>')
        rect = converter.convertRect(node)
        assert rect.ry == 2.5
        node = minimal_svg_node('<rect ry="1" width="10" height="3" x="0" y="0"/>')
        rect = converter.convertRect(node)
        assert rect.rx == 1

    def test_strokewidth_0(self):
        """
        When strokeWidth = 0, we force strokeColor to None to avoid the stroke
        to be displayed.
        """
        converter = svglib.Svg2RlgShapeConverter(None)
        node = minimal_svg_node(
            '<rect style="stroke: rgb(100, 84, 0); fill: rgb(255, 255, 255); '
            'fill-opacity: 1; stroke-width: 0;" width="135" height="86" x="10" y="10"/>'
        )
        rect = converter.convertShape("rect", node)
        assert rect.strokeColor is None


class TestLineNode:
    def test_length_zero(self):
        converter = svglib.Svg2RlgShapeConverter(None)
        node = minimal_svg_node(
            '<line stroke="#000000" x1="10" y1="20" x2="10" y2="20" />'
        )
        line = converter.convertLine(node)
        assert isinstance(line, Line)

        # Force a slight change in the first coordinate, so it's not invisible.
        assert line.x1 != 10

    def test_length_not_zero(self):
        """No change needed when length is not zero."""
        converter = svglib.Svg2RlgShapeConverter(None)
        node = minimal_svg_node(
            '<line stroke="#000000" x1="10" y1="20" x2="10" y2="30" />'
        )
        line = converter.convertLine(node)
        assert isinstance(line, Line)

        assert line.x1 == 10


class TestPolylineNode:
    def test_filling(self):
        converter = svglib.Svg2RlgShapeConverter(None)
        node = minimal_svg_node(
            '<polyline fill="none" stroke="#000000" '
            'points="10,50,35,150,60,50,85,150,110,50,135,150" />'
        )
        polyline = converter.convertPolyline(node)
        assert isinstance(polyline, PolyLine)

        # svglib simulates polyline filling by a fake polygon.
        node = minimal_svg_node(
            '<polyline fill="#fff" stroke="#000000" '
            'points="10,50,35,150,60,50,85,150,110,50,135,150" />'
        )
        group = converter.convertPolyline(node)
        assert isinstance(group.contents[0], Polygon)
        assert group.contents[0].fillColor == colors.white
        assert isinstance(group.contents[1], PolyLine)

    def test_length_zero(self):
        converter = svglib.Svg2RlgShapeConverter(None)
        node = minimal_svg_node(
            '<polyline fill="none" stroke="#000000" points="10,50,10,50" />'
        )
        polyline = converter.convertPolyline(node)
        assert isinstance(polyline, PolyLine)

        # Force a slight change in the first coordinate, so it's not invisible.
        assert polyline.points[0] != 10

    def test_odd_length(self):
        converter = svglib.Svg2RlgShapeConverter(None)
        node = minimal_svg_node(
            '<polyline fill="none" stroke="#000000" points="10,50,10,50,10" />'
        )
        polyline = converter.convertPolyline(node)
        assert polyline is None


class TestPolygonNode:
    def test_length_zero(self):
        converter = svglib.Svg2RlgShapeConverter(None)
        node = minimal_svg_node(
            '<polygon fill="none" stroke="#000000" points="10,50,10,50" />'
        )
        polygon = converter.convertPolygon(node)
        assert isinstance(polygon, Polygon)

        # Force a slight change in the first coordinate, so it's not invisible.
        assert polygon.points[0] != 10

    def test_odd_length(self):
        converter = svglib.Svg2RlgShapeConverter(None)
        node = minimal_svg_node(
            '<polygon fill="none" stroke="#000000" points="10,50,10,50,10" />'
        )
        polygon = converter.convertPolygon(node)
        assert polygon is None


class TestUseNode:
    def test_use(self, drawing_source=None):
        drawing = drawing_from_svg(
            drawing_source
            or """
            <?xml version="1.0"?>
            <svg version="1.1"
                 xmlns="http://www.w3.org/2000/svg"
                 xmlns:xlink="http://www.w3.org/1999/xlink"
                 width="10cm" height="3cm" viewBox="0 0 100 30">
              <defs>
                  <rect id="MyRect" width="60" height="10"/>
              </defs>
              <rect x=".1" y=".1" width="99.8" height="29.8"
                    fill="none" stroke="blue" stroke-width=".2" />
              <use x="20" y="10" xlink:href="#MyRect" />
              <use x="30" y="20" xlink:href="#MyRect" fill="#f00" />
            </svg>
        """
        )
        main_group = drawing.contents[0]
        # First Rect
        assert isinstance(main_group.contents[0], Rect)
        # Second Rect defined by the use node (inside a Group)
        assert isinstance(main_group.contents[1].contents[0], Rect)
        assert main_group.contents[1].contents[0].fillColor == colors.black  # default
        # Attributes on the use node are applied to the referenced content
        assert isinstance(main_group.contents[2].contents[0], Rect)
        assert main_group.contents[2].contents[0].fillColor == colors.red

    def test_use_href_svg2(self):
        """In SVG 2, xlink:href="" can be simply href=""."""
        drawing = drawing_from_svg(
            """
            <svg xmlns="http://www.w3.org/2000/svg"
                 width="10cm" height="3cm" viewBox="0 0 100 30">
              <defs>
                <rect id="MyRect" x=".1" y=".1" width="99.8" height="29.8"
                      fill="none" stroke="blue" />
              </defs>
              <use x="20" y="10" href="#MyRect" />
            </svg>
        """
        )
        assert isinstance(drawing.contents[0].contents[0].contents[0], Rect)

    def test_use_with_defs_at_end(self):
        self.test_use(
            drawing_source="""
            <?xml version="1.0"?>
            <svg version="1.1"
                 xmlns="http://www.w3.org/2000/svg"
                 xmlns:xlink="http://www.w3.org/1999/xlink"
                 width="10cm" height="3cm" viewBox="0 0 100 30">
              <rect x=".1" y=".1" width="99.8" height="29.8"
                    fill="none" stroke="blue" stroke-width=".2" />
              <use x="20" y="10" xlink:href="#MyRect" />
              <use x="30" y="20" xlink:href="#MyRect" fill="#f00" />
              <defs>
                  <rect id="MyRect" width="60" height="10"/>
              </defs>
            </svg>
        """
        )

    def test_transform_inherited_by_use(self):
        drawing = drawing_from_svg(
            """
            <?xml version="1.0"?>
            <svg version="1.1"
                 xmlns:xlink="http://www.w3.org/1999/xlink"
                 width="900" height="600">
                <g id="c">
                    <path id="t" d="M 0,-100 V 0 H 50"
                          transform="rotate(18 0,-100)"/>
                    <use xlink:href="#t" transform="scale(-1,1)"/>
                </g>
            </svg>
        """
        )
        cgroup_node = drawing.contents[0].contents[0]
        assert (
            cgroup_node.contents[0].transform
            == cgroup_node.contents[1].contents[0].transform
        ), (
            "The transform of the original path is different from the transform of "
            "the reused path."
        )

    def test_use_forward_reference(self):
        """
        Sometimes, a node definition pointed to by xlink:href can appear after
        it has been referenced. But the order should remain.
        """
        drawing = drawing_from_svg(
            """
            <?xml version="1.0"?>
            <svg version="1.1"
                 xmlns:xlink="http://www.w3.org/1999/xlink"
                 width="900" height="600">
                <use xlink:href="#back" x="-100"/>
                <rect id="back" x="42" y="42" width="416" height="216" fill="#007a5e"/>
            </svg>
        """
        )
        assert len(drawing.contents[0].contents) == 2
        assert isinstance(drawing.contents[0].contents[0], Group)
        assert isinstance(drawing.contents[0].contents[1], Rect)

    def test_use_node_properties(self):
        """
        Properties on the use node apply to the referenced item.
        """
        drawing = drawing_from_svg(
            """
            <?xml version="1.0"?>
            <svg version="1.1"
                 xmlns:xlink="http://www.w3.org/1999/xlink"
                 width="900" height="600">
                <path id="a" fill="#FF0000" d="M-15 37.57h60L-15 0v80h60l-60-60z"/>
                <use stroke="#003893" stroke-width="5" xlink:href="#a"/>
                <use stroke="#003893" stroke-width="2" xlink:href="#a"/>
            </svg>
        """
        )
        use_path1 = drawing.contents[0].contents[1].contents[0].contents[0]
        use_path2 = drawing.contents[0].contents[2].contents[0].contents[0]
        # Attribute from <path> node
        assert use_path1.fillColor == colors.Color(1, 0, 0, 1)
        # Attribute from <use> node
        assert use_path1.strokeWidth == 5
        assert use_path2.strokeWidth == 2

    def test_use_node_with_unclosed_path(self):
        """
        When a <use> node references an unclosed path (which is a group with two
        different paths for filling and stroking), the use properties shouldn't
        affect the no-stroke property of the fake stroke-only path.
        """
        drawing = drawing_from_svg(
            """
            <?xml version="1.0"?>
            <svg xmlns="http://www.w3.org/2000/svg"
                 xmlns:xlink="http://www.w3.org/1999/xlink"
                 width="900" height="600" viewBox="0 0 9 6">
                <defs>
                    <path d="M0,0 4.5,3 0,6" id="X"/>
                </defs>
                <use xlink:href="#X" fill="#f00" stroke="#ffb612" stroke-width="2"/>
            </svg>
        """
        )
        use_group = drawing.contents[0].contents[0].contents[0]
        assert use_group.contents[0].getProperties()["strokeWidth"] == 0
        assert use_group.contents[0].getProperties()["strokeColor"] is None


class TestSymbolNode:
    def test_symbol_unused(self):
        """<symbol> by itself should not be rendered."""
        drawing = drawing_from_svg(
            """
            <?xml version="1.0"?>
            <svg xmlns="http://www.w3.org/2000/svg"
                 width="900" height="600" viewBox="0 0 100 100">
                <symbol id="X">
                    <path d="M 0,0100 V 0 H 50"/>
                </symbol>
            </svg>
        """
        )
        assert drawing.contents[0].contents == []

    def test_symbol_node(self):
        drawing = drawing_from_svg(
            """
            <?xml version="1.0"?>
            <svg xmlns="http://www.w3.org/2000/svg"
                 xmlns:xlink="http://www.w3.org/1999/xlink"
                 width="900" height="600" viewBox="0 0 100 100">
                <defs>
                    <symbol id="X">
                        <path d="M 0,-100 V 0 H 50"/>
                    </symbol>
                </defs>
                <use xlink:href="#X" fill="#f00"/>
            </svg>
        """
        )
        use_group = drawing.contents[0].contents[0].contents[0]
        assert isinstance(use_group.contents[0].contents[0], svglib.NoStrokePath)
        assert isinstance(use_group.contents[0].contents[1], Path)


class TestViewBox:
    def test_nonzero_origin(self):
        drawing = drawing_from_svg(
            """
            <?xml version="1.0"?>
            <svg xmlns="http://www.w3.org/2000/svg"
                 width="1200" height="800"
                 viewBox="-60 -40 120 80">
                <g fill="#E70013">
                    <rect x="-60" y="-40" width="120" height="80"/>
                </g>
            </svg>
        """
        )
        # Main group coordinates are translated to match the viewBox origin
        assert drawing.contents[0].transform == (10, 0, 0, -10, 600.0, 400.0)

    def test_percent_width_height(self):
        drawing = drawing_from_svg(
            """
            <?xml version="1.0"?>
            <svg xmlns="http://www.w3.org/2000/svg"
                 width="100%" height="100%"
                 viewBox="0 0 480 360">
                <g fill="#E70013">
                    <rect x="60" y="40" width="120" height="80"/>
                </g>
            </svg>
        """
        )
        assert (drawing.width, drawing.height) == (480, 360)

    def test_no_width_height(self):
        drawing = drawing_from_svg(
            """
            <?xml version="1.0"?>
            <svg xmlns="http://www.w3.org/2000/svg"
                 viewBox="0 0 480 360">
                <g fill="#E70013">
                    <rect x="60" y="40" width="120" height="80"/>
                </g>
            </svg>
        """
        )
        assert (drawing.width, drawing.height) == (480, 360)


class TestEmbedded:
    def test_svg_in_svg(self):
        drawing = drawing_from_svg(
            """
            <?xml version="1.0"?>
            <svg xmlns="http://www.w3.org/2000/svg" version="1.1"
                 viewBox="0 0 210 297" height="297mm" width="210mm">
              <g>
                <rect ry="5" y="15" x="11" height="85" width="90"
                   style="fill:#b8393d;stroke:#dfd8c3;stroke-width:0.75;" />
                <text id="text8866" y="32" x="25"
                   style="font-size:10px;line-height:1.25;font-family:sans-serif;">
                   <tspan x="25" y="31" style="stroke-width:0.2">Test 1,2,3</tspan>
                </text>
              </g>
              <g>
              <svg xmlns="http://www.w3.org/2000/svg" version="1.1"
                 viewBox="0 0 210 50" x="0" y="100" height="25mm" width="105mm">
                <g>
                  <text y="30" x="5"
                   style="line-height:1.25;font-family:sans-serif;">
                   <tspan x="5" y="30"
                     style="font-size:25px;stroke-width:0.2">TEST</tspan></text>
                </g>
              </svg>
              </g>
            </svg>
        """
        )
        embedded_svg_group = drawing.contents[0].contents[1].contents[0]
        # x / y translation
        assert embedded_svg_group.getProperties()["transform"][-2:] == (0, 100)
        # viewBox scaling
        assert (
            pytest.approx(1.417, 0.001)
            == embedded_svg_group.getProperties()["transform"][0]
        )
        assert (
            pytest.approx(1.417, 0.001)
            == embedded_svg_group.getProperties()["transform"][3]
        )

    def test_embedded_svg_with_percentages(self):
        drawing = drawing_from_svg(
            """
            <?xml version="1.0"?>
            <svg xmlns="http://www.w3.org/2000/svg" version="1.1" height="100"
                 width="100">
                <rect height="100%" width="100%" x="0" y="0" />
                <svg height="15" width="15" x="45" y="45">
                    <rect fill="black" height="100%" width="100%" x="0" y="0" />
                </svg>
            </svg>
        """
        )
        inner_rect = drawing.contents[0].contents[1].contents[0]
        assert inner_rect.width == 15

    def test_png_in_svg_file_like(self):
        drawing = drawing_from_svg(
            """
            <?xml version="1.0"?>
            <svg xmlns="http://www.w3.org/2000/svg" version="1.1"
                 xmlns:xlink="http://www.w3.org/1999/xlink"
                 viewBox="0 0 210 297" height="297mm" width="210mm">
              <image id="refImage" xlink:href="../png/jpeg-required-201-t.png"
                     height="36" width="48" y="77" x="50" />
            </svg>
        """
        )
        # FIXME: test the error log when we can require pytest >= 3.4
        # No image as relative path in file-like input cannot be determined.
        assert drawing.contents[0].contents == []
