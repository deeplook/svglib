"""Linear and radial gradients."""

import pytest
from reportlab.graphics.shapes import (
    Group,
    Rect,
)
from reportlab.lib import colors

from svglib.svglib import LinearGradientShape
from tests.utils import (
    drawing_from_svg,
)


class TestGradients:
    """Tests for SVG linearGradient and radialGradient support."""

    @staticmethod
    def _find_groups(shape):
        """Recursively collect all Group objects in a drawing."""
        from reportlab.graphics.shapes import Group as RLGroup

        result = []
        if isinstance(shape, RLGroup):
            result.append(shape)
        if hasattr(shape, "contents"):
            for item in shape.contents:
                result.extend(TestGradients._find_groups(item))
        return result

    def test_linear_gradient_rect(self):
        """A rect with a linearGradient fill must produce a Group (not a bare Rect)."""
        drawing = drawing_from_svg(
            """
            <?xml version="1.0"?>
            <svg xmlns="http://www.w3.org/2000/svg" width="100" height="100">
                <defs>
                    <linearGradient id="grad1" x1="0" y1="0" x2="1" y2="0"
                                    gradientUnits="objectBoundingBox">
                        <stop offset="0" stop-color="red" stop-opacity="1"/>
                        <stop offset="1" stop-color="blue" stop-opacity="1"/>
                    </linearGradient>
                </defs>
                <rect x="10" y="10" width="80" height="80" fill="url(#grad1)"/>
            </svg>
        """
        )
        groups = self._find_groups(drawing)
        # The rect's fill must have been replaced by a gradient group
        assert len(groups) > 1
        # The gradient shape must implement getBounds() so the drawing can be
        # measured (e.g. when used as a flowable by rst2pdf); see issue #466.
        x0, y0, x1, y1 = drawing.getBounds()
        assert x1 > x0 and y1 > y0

    def test_radial_gradient_circle(self):
        """A circle with a radialGradient fill must produce a Group."""
        drawing = drawing_from_svg(
            """
            <?xml version="1.0"?>
            <svg xmlns="http://www.w3.org/2000/svg" width="100" height="100">
                <defs>
                    <radialGradient id="rgrad" cx="0.5" cy="0.5" r="0.5"
                                    gradientUnits="objectBoundingBox">
                        <stop offset="0" stop-color="yellow" stop-opacity="1"/>
                        <stop offset="1" stop-color="green" stop-opacity="1"/>
                    </radialGradient>
                </defs>
                <circle cx="50" cy="50" r="40" fill="url(#rgrad)"/>
            </svg>
        """
        )
        groups = self._find_groups(drawing)
        assert len(groups) > 1
        # See issue #466: the gradient shape must implement getBounds().
        x0, y0, x1, y1 = drawing.getBounds()
        assert x1 > x0 and y1 > y0

    def test_gradient_stops_parsed(self):
        """Stop colors and offsets must be correctly stored in gradient_defs."""
        from io import BytesIO

        from svglib.svglib import SvgRenderer, load_svg_file

        svg_content = b"""<?xml version="1.0"?>
            <svg xmlns="http://www.w3.org/2000/svg" width="100" height="100">
                <defs>
                    <linearGradient id="g1">
                        <stop offset="0" stop-color="#ff0000" stop-opacity="1"/>
                        <stop offset="0.5" stop-color="#00ff00" stop-opacity="0.5"/>
                        <stop offset="1" stop-color="#0000ff" stop-opacity="1"/>
                    </linearGradient>
                </defs>
            </svg>"""
        root = load_svg_file(BytesIO(svg_content))
        renderer = SvgRenderer("")
        renderer.render(root)
        grad = renderer.gradient_defs.get("g1")
        assert grad is not None
        assert len(grad["stops"]) == 3
        assert grad["stops"][0][0] == 0.0
        assert grad["stops"][1][0] == 0.5
        assert grad["stops"][2][0] == 1.0

    @pytest.mark.parametrize(
        "before_defs, in_defs, after_defs",
        [
            pytest.param("", "{css}", "", id="style-in-defs"),
            pytest.param("{css}", "", "", id="style-before-defs"),
            pytest.param("", "", "{css}", id="style-after-defs"),
        ],
    )
    def test_gradient_stops_styled_by_css_rules(self, before_defs, in_defs, after_defs):
        """The stop-color and stop-opacity of a stop can be set by a CSS rule.

        Illustrator exports its gradients this way, with a class for each stop.
        """
        from io import BytesIO

        from svglib.svglib import SvgRenderer, load_svg_file

        css = (
            "<style>.a { stop-color: red } "
            "stop.b { stop-color: #0000ff; stop-opacity: 0.5 }</style>"
        )
        svg_content = f"""<?xml version="1.0"?>
            <svg xmlns="http://www.w3.org/2000/svg" width="100" height="100">
                {before_defs.format(css=css)}
                <defs>
                    {in_defs.format(css=css)}
                    <linearGradient id="g1">
                        <stop offset="0" class="a"/>
                        <stop offset="1" class="b"/>
                    </linearGradient>
                </defs>
                {after_defs.format(css=css)}
            </svg>""".encode()
        renderer = SvgRenderer("")
        renderer.render(load_svg_file(BytesIO(svg_content)))
        (_, first), (_, second) = renderer.gradient_defs["g1"]["stops"]
        assert (first.red, first.green, first.blue, first.alpha) == (1, 0, 0, 1)
        assert (second.red, second.green, second.blue, second.alpha) == (0, 0, 1, 0.5)

    def test_style_applies_to_shapes_before_it(self):
        """A <style> applies to the whole document, as in browsers.

        A shape that comes before the <style> is styled by it too.
        """
        drawing = drawing_from_svg(
            """
            <svg xmlns="http://www.w3.org/2000/svg" width="100" height="100">
                <rect class="a" width="10" height="10"/>
                <style>.a { fill: red }</style>
                <rect class="a" width="10" height="10"/>
            </svg>
            """
        )
        before, after = drawing.contents[0].contents
        assert before.fillColor == colors.red
        assert after.fillColor == colors.red

    def test_gradient_stop_style_attribute_beats_css_rule(self):
        """A style attribute wins over a CSS rule, which wins over an attribute."""
        from io import BytesIO

        from svglib.svglib import SvgRenderer, load_svg_file

        svg_content = b"""<?xml version="1.0"?>
            <svg xmlns="http://www.w3.org/2000/svg" width="100" height="100">
                <style>.a { stop-color: red }</style>
                <defs>
                    <linearGradient id="g1">
                        <stop offset="0" class="a" stop-color="blue"/>
                        <stop offset="1" class="a" style="stop-color: lime"/>
                    </linearGradient>
                </defs>
            </svg>"""
        renderer = SvgRenderer("")
        renderer.render(load_svg_file(BytesIO(svg_content)))
        (_, first), (_, second) = renderer.gradient_defs["g1"]["stops"]
        assert (first.red, first.green, first.blue) == (1, 0, 0)
        assert (second.red, second.green, second.blue) == (0, 1, 0)

    def test_gradient_href_inheritance(self):
        """A gradient that references another via href must inherit its stops."""
        from io import BytesIO

        from svglib.svglib import SvgRenderer, load_svg_file

        svg_content = b"""<?xml version="1.0"?>
            <svg xmlns="http://www.w3.org/2000/svg"
                 xmlns:xlink="http://www.w3.org/1999/xlink"
                 width="100" height="100">
                <defs>
                    <linearGradient id="base">
                        <stop offset="0" stop-color="red"/>
                        <stop offset="1" stop-color="blue"/>
                    </linearGradient>
                    <linearGradient id="derived" xlink:href="#base"
                                    x1="0" y1="0" x2="0" y2="1"/>
                </defs>
            </svg>"""
        root = load_svg_file(BytesIO(svg_content))
        renderer = SvgRenderer("")
        renderer.render(root)
        resolved = renderer._resolve_gradient("derived")
        assert resolved is not None
        assert len(resolved["stops"]) == 2  # inherited from "base"
        assert resolved["x2"] == 0.0  # from derived
        assert resolved["y2"] == 1.0  # from derived

    def test_gradient_userSpaceOnUse(self):
        """A gradient with gradientUnits=userSpaceOnUse must also produce a Group."""
        drawing = drawing_from_svg(
            """
            <?xml version="1.0"?>
            <svg xmlns="http://www.w3.org/2000/svg" width="200" height="200">
                <defs>
                    <linearGradient id="usg" x1="0" y1="0" x2="200" y2="0"
                                    gradientUnits="userSpaceOnUse">
                        <stop offset="0" stop-color="black"/>
                        <stop offset="1" stop-color="white"/>
                    </linearGradient>
                </defs>
                <rect x="0" y="0" width="200" height="200" fill="url(#usg)"/>
            </svg>
        """
        )
        groups = self._find_groups(drawing)
        assert len(groups) > 1

    def test_gradient_stop_opacity_in_style(self):
        """Stop opacity specified in a style attribute must be respected."""
        from io import BytesIO

        from svglib.svglib import SvgRenderer, load_svg_file

        svg_content = b"""<?xml version="1.0"?>
            <svg xmlns="http://www.w3.org/2000/svg" width="100" height="100">
                <defs>
                    <linearGradient id="g2">
                        <stop offset="0"
                              style="stop-color:rgb(255,0,0);stop-opacity:0.5"/>
                        <stop offset="1"
                              style="stop-color:#0000ff;stop-opacity:1"/>
                    </linearGradient>
                </defs>
            </svg>"""
        root = load_svg_file(BytesIO(svg_content))
        renderer = SvgRenderer("")
        renderer.render(root)
        grad = renderer.gradient_defs.get("g2")
        assert grad is not None
        stop0_color = grad["stops"][0][1]
        assert stop0_color.alpha == pytest.approx(0.5)

    def _get_svg(self, fill, name):
        return f"""
            <?xml version="1.0"?>
            <svg xmlns="http://www.w3.org/2000/svg" width="100" height="100">
                <defs>
                    <linearGradient id="{name}" x1="0" y1="0" x2="1" y2="0"
                            gradientUnits="objectBoundingBox">
                        <stop offset="0" stop-color="red" stop-opacity="1"/>
                        <stop offset="1" stop-color="blue" stop-opacity="1"/>
                    </linearGradient>
                </defs>
                <rect x="10" y="10" width="80" height="80" fill={fill}/>
            </svg>"""

    def _process_test_fill_url(self, fill, name="grad1"):
        """Process test fill url."""
        drawing = drawing_from_svg(self._get_svg(fill, name))

        assert len(drawing.contents) == 1
        group = drawing.contents[0]
        assert isinstance(group, Group)

        assert len(group.contents) == 1
        group2 = group.contents[0]
        assert isinstance(group2, Group)

        gradient, rect = group2.contents
        assert isinstance(gradient, LinearGradientShape)
        assert isinstance(rect, Rect)

        assert gradient._positions == [0.0, 1.0]
        assert gradient._rl_colors == [
            colors.Color(1, 0, 0, 1),
            colors.Color(0, 0, 1, 1),
        ]

    def test_fill_url_witout_quotes(self):
        """Fill url witout quotes."""
        self._process_test_fill_url('"url(#grad1)"')

    def test_fill_url_witout_quotes_space(self):
        """Fill url witout quotes."""
        self._process_test_fill_url('"url(#grad 1)"', "grad 1")

    def test_fill_url_witout_quotes_parenthesis(self):
        """Fill url witout quotes."""
        self._process_test_fill_url('"url(#grad)1)"', "grad)1")

    def test_fill_url_witout_quotes_strip(self):
        """Fill url witout quotes."""
        self._process_test_fill_url('"url( #grad1 )"')

    def test_fill_url_witout_quotes_strip_space(self):
        """Fill url witout quotes."""
        self._process_test_fill_url('"url( #grad 1 )"', "grad 1")

    def test_fill_url_enclosed_single_quotes(self):
        """Fill url enclosed single quotes."""
        self._process_test_fill_url('''"url('#grad1')"''')

    def test_fill_url_enclosed_single_quotes_space(self):
        """Fill url enclosed single quotes."""
        self._process_test_fill_url('''"url('#grad 1')"''', "grad 1")

    def test_fill_url_enclosed_single_quotes_strip(self):
        """Fill url enclosed single quotes."""
        self._process_test_fill_url('''"url( '#grad1' )"''')

    def test_fill_url_enclosed_single_quotes_strip_space(self):
        """Fill url enclosed single quotes."""
        self._process_test_fill_url('''"url( '#grad 1' )"''', "grad 1")

    def test_fill_url_enclosed_double_quotes(self):
        """Fill url enclosed double quotes."""
        self._process_test_fill_url("""'url("#grad1")'""")

    def test_fill_url_enclosed_double_quotes_parenthesis(self):
        """Fill url enclosed double quotes."""
        self._process_test_fill_url("""'url("#grad())1")'""", "grad())1")

    def test_fill_url_enclosed_double_quotes_strip(self):
        """Fill url enclosed double quotes."""
        self._process_test_fill_url("""'url( "#grad1" )'""")

    def test_fill_url_enclosed_double_quotes_strip_space(self):
        """Fill url enclosed double quotes."""
        self._process_test_fill_url("""'url( "#grad 1" )'""", "grad 1")

    def test_fill_url_enclosed_double_quotes_strip_parenthesis(self):
        """Fill url enclosed double quotes."""
        self._process_test_fill_url("""'url( "#grad)1" )'""", "grad)1")

    @pytest.mark.parametrize(
        "root, gradient, stop, expected",
        [
            pytest.param('color="green"', "", "", (0, 0.502, 0), id="root"),
            pytest.param("", 'color="red"', "", (1, 0, 0), id="gradient"),
            pytest.param('color="green"', "", 'color="lime"', (0, 1, 0), id="stop"),
            pytest.param("", "", "", (0, 0, 0), id="initial-color-is-black"),
            pytest.param('color="currentColor"', "", "", (0, 0, 0), id="color-itself"),
        ],
    )
    @pytest.mark.parametrize(
        "stop_color",
        [
            'stop-color="currentColor"',
            'style="stop-color: CurrentColor !important"',
        ],
    )
    def test_gradient_stop_current_color(
        self, root, gradient, stop, expected, stop_color
    ):
        """stop-color: currentColor is the color of the stop, not an error.

        It made svg2rlg() fail with AttributeError: 'str' object has no 'clone'.
        """
        from io import BytesIO

        from svglib.svglib import SvgRenderer, load_svg_file

        svg_content = f"""<?xml version="1.0"?>
            <svg xmlns="http://www.w3.org/2000/svg" width="100" height="100" {root}>
                <defs>
                    <linearGradient id="g1" {gradient}>
                        <stop offset="0" {stop} {stop_color}/>
                        <stop offset="1" stop-color="blue"/>
                    </linearGradient>
                </defs>
            </svg>""".encode()
        renderer = SvgRenderer("")
        renderer.render(load_svg_file(BytesIO(svg_content)))
        (_, first), (_, second) = renderer.gradient_defs["g1"]["stops"]
        assert (first.red, first.green, first.blue) == pytest.approx(expected, abs=1e-3)
        assert (second.red, second.green, second.blue) == (0, 0, 1)

    @pytest.mark.parametrize(
        "base, derived, expected",
        [
            pytest.param(
                'x1="0.1" y1="0.2" x2="0.5" y2="0.6"',
                "",
                {"x1": 0.1, "y1": 0.2, "x2": 0.5, "y2": 0.6},
                id="linear-geometry",
            ),
            pytest.param(
                'x1="0.1" x2="0.5"',
                'x2="25%"',
                {"x1": 0.1, "x2": 0.25},
                id="linear-own-attribute",
            ),
            pytest.param(
                'spreadMethod="reflect" gradientUnits="userSpaceOnUse"',
                "",
                {"spreadMethod": "reflect", "gradientUnits": "userSpaceOnUse"},
                id="units-and-spread",
            ),
            pytest.param(
                'spreadMethod="reflect"',
                'spreadMethod="repeat"',
                {"spreadMethod": "repeat"},
                id="own-spread",
            ),
        ],
    )
    def test_gradient_attributes_inherited_through_href(self, base, derived, expected):
        """A gradient takes the attributes of its href that it does not set itself.

        It used its own defaults instead, so x2 was 1 and the spread was pad.
        """
        from io import BytesIO

        from svglib.svglib import SvgRenderer, load_svg_file

        svg_content = f"""<?xml version="1.0"?>
            <svg xmlns="http://www.w3.org/2000/svg" width="100" height="100">
                <defs>
                    <linearGradient id="base" {base}>
                        <stop offset="0" stop-color="red"/>
                        <stop offset="1" stop-color="blue"/>
                    </linearGradient>
                    <linearGradient id="g1" href="#base" {derived}/>
                </defs>
            </svg>""".encode()
        renderer = SvgRenderer("")
        renderer.render(load_svg_file(BytesIO(svg_content)))
        resolved = renderer._resolve_gradient("g1")
        assert resolved is not None
        assert {key: resolved.get(key) for key in expected} == pytest.approx(expected)
        assert len(resolved["stops"]) == 2

    def test_radial_gradient_attributes_inherited_through_href(self):
        from io import BytesIO

        from svglib.svglib import SvgRenderer, load_svg_file

        svg_content = b"""<?xml version="1.0"?>
            <svg xmlns="http://www.w3.org/2000/svg" width="100" height="100">
                <defs>
                    <radialGradient id="base" cx="0.3" cy="0.4" r="0.2">
                        <stop offset="0" stop-color="red"/>
                        <stop offset="1" stop-color="blue"/>
                    </radialGradient>
                    <radialGradient id="g1" href="#base" cx="0.7"/>
                </defs>
            </svg>"""
        renderer = SvgRenderer("")
        renderer.render(load_svg_file(BytesIO(svg_content)))
        resolved = renderer._resolve_gradient("g1")
        assert resolved is not None
        assert (resolved["cx"], resolved["cy"], resolved["r"]) == pytest.approx(
            (0.7, 0.4, 0.2)
        )
