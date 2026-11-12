"""Attribute converters (colors, lengths, transforms), style sheets."""

from typing import Any

import pytest
from reportlab.graphics.shapes import (
    Group,
    Path,
    Polygon,
    Rect,
)
from reportlab.lib import colors
from reportlab.lib.units import cm, inch
from reportlab.pdfgen.canvas import FILL_EVEN_ODD

from svglib import svglib
from tests.utils import (
    check_mapping,
    drawing_from_svg,
    minimal_svg_node,
)


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
        failed = check_mapping(ac.convertColor, mapping)
        assert len(failed) == 0

    def test_color_keywords_ignore_case(self):
        "Color keywords and function names are ASCII case-insensitive, as in CSS."

        mapping = (
            ("Red", colors.red),
            ("WHITE", colors.white),
            ("SlateGrey", colors.HexColor(0x708090)),
            ("Transparent", colors.Color(0, 0, 0, 0)),
            ("RGB(255, 0, 0)", colors.red),
            ("Rgba(255, 255, 128, .5)", colors.Color(1, 1, 128 / 255, 0.5)),
            ("currentcolor", "currentColor"),
            ("CURRENTCOLOR", "currentColor"),
            ("None", None),
        )
        ac = svglib.Svg2RlgAttributeConverter()
        failed = check_mapping(ac.convertColor, mapping)
        assert len(failed) == 0

    def test_current_color_ignores_case(self):
        "fill and stroke use the color property for currentColor in any case."

        drawing = drawing_from_svg(
            """
            <svg xmlns="http://www.w3.org/2000/svg" width="100" height="100">
              <g color="red">
                <rect width="10" height="10" fill="currentcolor"/>
                <rect width="10" height="10" fill="CURRENTCOLOR" stroke="CurrentColor"/>
                <rect width="10" height="10" style="fill: currentColor !important"/>
              </g>
            </svg>
        """
        )
        rects = drawing.contents[0].contents[0].contents
        assert [r.fillColor for r in rects] == [colors.red] * 3
        assert rects[1].strokeColor == colors.red

    def test_css_named_colors_missing_in_reportlab(self):
        "CSS named colors that ReportLab lacks or defines differently."

        mapping = (
            ("rebeccapurple", colors.HexColor(0x663399)),
            ("lightgray", colors.HexColor(0xD3D3D3)),
            ("LightGray", colors.HexColor(0xD3D3D3)),
            ("darkseagreen", colors.HexColor(0x8FBC8F)),
        )
        ac = svglib.Svg2RlgAttributeConverter()
        failed = check_mapping(ac.convertColor, mapping)
        assert len(failed) == 0

    def test_hsl_hue_with_angle_unit(self):
        "The hue of hsl() may have a deg, grad, rad or turn unit, as in CSS Color 4."

        mapping = (
            ("hsl(120deg, 100%, 50%)", colors.Color(0, 1, 0, 1)),
            ("HSL(120DEG, 100%, 50%)", colors.Color(0, 1, 0, 1)),
            ("hsl(0.5turn, 100%, 50%)", colors.Color(0, 1, 1, 1)),
            ("hsl(200grad, 100%, 50%)", colors.Color(0, 1, 1, 1)),
            ("hsla(240deg, 100%, 50%, 0.5)", colors.Color(0, 0, 1, 0.5)),
        )
        ac = svglib.Svg2RlgAttributeConverter()
        failed = check_mapping(ac.convertColor, mapping)
        assert len(failed) == 0

    def test_light_dark_color(self):
        "light-dark() is its light color, as in draw.io exports."

        mapping = (
            (
                "light-dark(rgb(99, 222, 23), rgb(237, 237, 237))",
                colors.HexColor(0x63DE17),
            ),
            ("Light-Dark(#00f, white)", colors.HexColor(0x0000FF)),
            ("light-dark(hsl(120, 100%, 50%), red)", colors.HexColor(0x00FF00)),
            ("light-dark(red)", colors.HexColor(0xFF0000)),
        )
        ac = svglib.Svg2RlgAttributeConverter()
        failed = check_mapping(ac.convertColor, mapping)
        assert len(failed) == 0
        assert ac.convertColor("light-dark(currentColor, red)") == "currentColor"

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
        failed = check_mapping(ac.convertColor, mapping)
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
            ("1e1cm", 10 * cm / 0.75),
            ("1e1in", 10 * inch / 0.75),
            ("-8e-2cm", (-8e-2) * cm / 0.75),
            ("20px", 20),
            ("20pt", 20 * (96 / 72)),
            ("1.5em", 16 * 1.5),
            ("10.5mm", 10.5 * (cm * 0.1) / 0.75),
            ("3, 5 -7", [3, 5, -7]),
            ("2pt  12pt", [2 * (96 / 72), 12 * (96 / 72)]),
            ("10 20 30", [10.0, 20.0, 30.0]),
        )
        ac = svglib.Svg2RlgAttributeConverter()
        failed = check_mapping(ac.convertLength, mapping)
        assert len(failed) == 0
        assert ac.convertLength("1.5em", em_base=16.5) == 24.75

    def test_bare_number_equals_px(self):
        "Bare numbers and px units must produce identical lengths (issue #439)."
        ac = svglib.Svg2RlgAttributeConverter()
        # In user-unit space, "N" and "Npx" are the same (SVG spec §5.9.2).
        assert ac.convertLength("13") == ac.convertLength("13px")
        assert ac.convertLength("100") == ac.convertLength("100px")
        assert ac.convertLength("0.5") == ac.convertLength("0.5px")
        # convertLengthToPt must be consistent too (used for font-size).
        assert ac.convertLengthToPt("13") == ac.convertLengthToPt("13px")

    def test_font_size_bare_number_vs_px(self):
        "font-size='N' and font-size='Npx' must produce the same fontSize (issue #439)."
        svg_tmpl = """<svg xmlns="http://www.w3.org/2000/svg"
                          width="200" height="50" viewBox="0 0 200 50">
            <text font-size="{fs}">x</text>
        </svg>"""
        import io

        from lxml import etree

        def font_size_for(fs_attr):
            root = etree.parse(
                io.BytesIO(svg_tmpl.format(fs=fs_attr).encode())
            ).getroot()
            drawing = svglib.SvgRenderer("").render(root)
            # Walk into the drawing to find the first String object.
            group = drawing.contents[0]
            while hasattr(group, "contents"):
                group = group.contents[0]
            return group.fontSize

        assert font_size_for("13") == font_size_for("13px")
        assert font_size_for("24") == font_size_for("24px")

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
            (" 5cm 5in", [5 * cm / 0.75, 5 * inch / 0.75]),
            (" 5, 5", [5, 5]),
        )
        ac = svglib.Svg2RlgAttributeConverter()
        failed = check_mapping(ac.convertLengthList, mapping)
        assert len(failed) == 0


class TestTransformAttrConverter:
    "Testing transform attribute conversion."

    @pytest.mark.parametrize("separator", ["\t", "\r", "\n"])
    def test_svg_whitespace(self, separator):
        ac = svglib.Svg2RlgAttributeConverter()
        assert ac.convertTransform(f"translate(10{separator}20)") == (
            ac.convertTransform("translate(10 20)")
        )

    @pytest.mark.parametrize("separator", ["&#9;", "&#13;", "&#10;"])
    def test_whitespace_character_reference(self, separator):
        template = (
            '<svg xmlns="http://www.w3.org/2000/svg" width="100" height="100">'
            '<rect width="10" height="10" transform="translate(10{}20)"/></svg>'
        )
        actual = drawing_from_svg(template.format(separator))
        expected = drawing_from_svg(template.format(" "))
        assert actual.getBounds() == pytest.approx(expected.getBounds())

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
            # Unbalanced parentheses used to raise IndexError
            ("scale(2", []),
            ("rotate(45", []),
        )
        ac = svglib.Svg2RlgAttributeConverter()
        failed = check_mapping(ac.convertTransform, mapping)
        assert len(failed) == 0


class TestAttrConverter:
    "Testing multi-attribute conversion."

    def test_0(self):
        "Test multi-attribute conversion."

        mapping = (
            ("fill: black; stroke: yellow", {"fill": "black", "stroke": "yellow"}),
            # Colons and semicolons inside a value don't split it.
            (
                "fill:red;cursor:url(http://example.com/c.cur), auto",
                {"fill": "red", "cursor": "url(http://example.com/c.cur), auto"},
            ),
            (
                "mask:url(data:image/png;base64,AAAA);fill:blue",
                {"mask": "url(data:image/png;base64,AAAA)", "fill": "blue"},
            ),
            # A malformed declaration is skipped instead of raising.
            ("fill; stroke: red", {"stroke": "red"}),
        )
        ac = svglib.Svg2RlgAttributeConverter()
        failed = check_mapping(ac.parseMultiAttributes, mapping)
        assert len(failed) == 0

    def test_colon_in_style_value(self):
        drawing = drawing_from_svg(
            """
            <svg xmlns="http://www.w3.org/2000/svg" width="100" height="100">
              <style>
                .a { cursor: url(http://example.com/c.cur), auto; fill: blue }
              </style>
              <rect class="a" width="10" height="10"/>
              <rect width="10" height="10"
                    style="fill: red; cursor: url(http://example.com/c.cur), auto"/>
            </svg>
        """
        )
        rects = drawing.contents[0].contents
        assert rects[0].fillColor == colors.blue
        assert rects[1].fillColor == colors.red

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

    def test_opacity_applies_to_fill_and_stroke(self):
        converter = svglib.Svg2RlgShapeConverter(None)
        node = minimal_svg_node(
            '<polygon fill="red" stroke="blue" fill-opacity="0.5" opacity="0.4"/>'
        )
        poly = Polygon()
        converter.applyStyleOnShape(poly, node)
        assert poly.fillOpacity == pytest.approx(0.2)
        assert poly.fillColor.alpha == pytest.approx(0.2)
        assert poly.strokeOpacity == pytest.approx(0.4)

    def test_opacity_in_style_attribute(self):
        converter = svglib.Svg2RlgShapeConverter(None)
        node = minimal_svg_node('<polygon fill="red" style="opacity: 50%"/>')
        poly = Polygon()
        converter.applyStyleOnShape(poly, node)
        assert poly.fillOpacity == pytest.approx(0.5)

    def test_opacity_composes_with_ancestors(self):
        drawing = drawing_from_svg(
            """
            <svg xmlns="http://www.w3.org/2000/svg" width="100" height="100">
                <g opacity="0.5">
                    <g>
                        <rect width="10" height="10" fill="red" opacity="0.5"/>
                    </g>
                    <rect width="10" height="10" fill="blue"/>
                </g>
                <rect width="10" height="10" fill="green"/>
            </svg>
        """
        )
        rects = []

        def collect(shape):
            if isinstance(shape, Rect):
                rects.append(shape)
            for child in getattr(shape, "contents", []):
                collect(child)

        collect(drawing)
        assert [r.fillColor.alpha for r in rects] == [0.25, 0.5, 1]

    def test_fillrule(self):
        converter = svglib.Svg2RlgShapeConverter(None)
        node = minimal_svg_node('<polygon fill-rule="evenodd"/>')
        poly = Polygon()
        converter.applyStyleOnShape(poly, node)
        assert poly.fillMode == FILL_EVEN_ODD

    def test_dasharray(self):
        converter = svglib.Svg2RlgAttributeConverter()
        # normal
        assert converter.convertDashArray("5,3") == [5, 3]
        assert converter.convertDashArray("5 3") == [5, 3]
        # none / empty is a solid line, and must not raise
        assert converter.convertDashArray("none") == []
        assert converter.convertDashArray("") == []
        # per the spec: a negative value makes the whole list invalid,
        # and a list summing to zero is a solid line
        assert converter.convertDashArray("5,-3") == []
        assert converter.convertDashArray("0") == []
        assert converter.convertDashArray("0,0") == []
        # an odd number of values is repeated once
        assert converter.convertDashArray("1,2,3") == [1, 2, 3, 1, 2, 3]

    def test_dasharray_none_applies_cleanly(self):
        # stroke-dasharray="none" used to raise ValueError (swallowed), leaving
        # the shape's default; it should simply set no dashing.
        converter = svglib.Svg2RlgShapeConverter(None)
        node = minimal_svg_node(
            '<path d="M0,0 L9,0" stroke="black" stroke-dasharray="none"/>'
        )
        path = Path()
        converter.applyStyleOnShape(path, node)
        assert path.strokeDashArray == []

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
