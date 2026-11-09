"""Paths, arcs and clipping paths."""

import pytest
from reportlab.graphics.shapes import (
    _CLOSEPATH,
    _CURVETO,
    _LINETO,
    _MOVETO,
)
from reportlab.pdfgen.canvas import FILL_EVEN_ODD, FILL_NON_ZERO

from svglib import svglib, utils
from svglib.svglib import ClippingPath
from tests.utils import (
    check_mapping,
    drawing_from_svg,
    has_renderpm_backend,
    minimal_svg_node,
    svg_raster_difference,
)


class TestPaths:
    """Testing path-related code."""

    @pytest.mark.parametrize("command", ["A", "a"])
    @pytest.mark.parametrize(
        "parameters",
        ["10 10 +0 0 1 20 0", "10 10 0 0 1 +20 0", "10 10 0 0 1 20 +0"],
    )
    def test_arc_explicit_positive_sign(self, command, parameters):
        path = f"M0 0 {command} {parameters}"
        assert utils.normalise_svg_path(path) == utils.normalise_svg_path(
            path.replace("+", "")
        )

    def test_arc_flags_without_separators(self):
        """Flags are single characters and may be directly followed by numbers."""
        assert utils.split_arc_values("A", "10 10 0 0120 5") == [
            "A",
            [10.0, 10.0, 0.0, 0.0, 1.0, 20.0, 5.0],
        ]

    def test_arc_repeated_sequences(self):
        assert utils.split_arc_values("a", "1 2 3 0 1 4 5, 6,7 8 1,0 9 10") == [
            "a",
            [1.0, 2.0, 3.0, 0.0, 1.0, 4.0, 5.0],
            "a",
            [6.0, 7.0, 8.0, 1.0, 0.0, 9.0, 10.0],
        ]

    @pytest.mark.parametrize("digits", [60, 5000])
    def test_arc_with_long_digit_run_is_parsed_in_linear_time(self, digits):
        """A long run of digits must not cause catastrophic backtracking
        (GHSA-249c-7rgc-f52h). Malformed arcs are dropped, not an error."""
        assert utils.split_arc_values("A", "9" * digits) == []
        assert utils.normalise_svg_path("M0 0 A " + "9" * digits) == ["M", [0.0, 0.0]]

    def test_arc_stops_at_first_malformed_argument(self):
        assert utils.split_arc_values("A", "1 2 3 0 1 4 5 6 7") == [
            "A",
            [1.0, 2.0, 3.0, 0.0, 1.0, 4.0, 5.0],
        ]
        assert utils.split_arc_values("A", "1 2 3 2 1 4 5") == []
        assert utils.split_arc_values("A", "1 2 3 | 1 4 5") == []

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
                    "M",
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
                ["m", [10, 20], "m", [30, 40], "l", [40, 40], "z", []],
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
        failed = check_mapping(utils.normalise_svg_path, mapping)
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

    @pytest.mark.parametrize(
        "clip_path",
        [
            'clip-path="url(#clip)"',
            "clip-path=\"url('#clip')\"",
            "clip-path='url(\"#clip\")'",
            'clip-path="url( #clip )"',
            'style="clip-path: url(#clip)"',
            # as in the CSS of Illustrator exports and svgo-optimized files
            'class="clipped"',
        ],
    )
    def test_clipping_path_reference(self, clip_path):
        drawing = drawing_from_svg(
            f"""
            <?xml version="1.0"?>
            <svg version="1.1" xmlns="http://www.w3.org/2000/svg"
                 width="100" height="100">
                <style>.clipped {{ clip-path: url(#clip); }}</style>
                <clipPath id="clip"><rect width="10" height="10"/></clipPath>
                <path {clip_path} d="M0,0 L 50 0 50 50Z"/>
            </svg>
        """
        )
        assert isinstance(self.find_clipping(drawing), ClippingPath)

    @pytest.mark.parametrize(
        "clip_path", ['clip-path="none"', 'style="clip-path: none"']
    )
    def test_clipping_path_none(self, clip_path):
        drawing = drawing_from_svg(
            f"""
            <?xml version="1.0"?>
            <svg version="1.1" xmlns="http://www.w3.org/2000/svg"
                 width="100" height="100">
                <clipPath id="clip"><rect width="10" height="10"/></clipPath>
                <g clip-path="url(#clip)"><path {clip_path} d="M0,0 L 50 0 50 50Z"/></g>
            </svg>
        """
        )
        group = drawing.contents[0].contents[0]
        # The clip of the group applies, the child does not get one of its own
        assert isinstance(group.contents[0], ClippingPath)
        assert self.find_clipping(group.contents[1]) is None

    def find_clipping(self, item):
        if isinstance(item, ClippingPath):
            return item

        if hasattr(item, "contents"):
            for child in item.contents:
                result = self.find_clipping(child)
                if result:
                    return result

        return None

    def test_clipping_path_with_transform(self):
        clipping_paths = [
            '<rect transform="scale(0.5, 0.5)" height="100" width="100" x="0" y="0"/>',
            '<rect transform="scale(0.5, 0.5)" height="100" width="100" x="0" y="0" '
            + 'rx="20" ry="20"/>',
            '<path transform="scale(0.5, 0.5)" d="M 0 0 H 100 V 100 H 0 Z"/>',
            '<circle transform="scale(0.5, 0.5)" cx="50" cy="50" r="50"/>',
            '<ellipse transform="scale(0.5, 0.5)" cx="50" cy="50" rx="50" ry="50"/>',
            '<polygon transform="scale(0.5, 0.5)" points="0,100 50,25 50,75 100,0" />',
        ]

        for clipping_path in clipping_paths:
            drawing = drawing_from_svg(f"""
                <svg namespace="http://www.w3.org/XML/1998/namespace"
                     xmlns="http://www.w3.org/2000/svg"
                     xmlns:xlink="http://www.w3.org/1999/xlink" version="1.1"
                     viewBox="0 0 100 50" width="100" height="50">

                    <defs>
                        <clipPath id="clip-1">
                            {clipping_path}
                        </clipPath>
                    </defs>
                    <g>
                        <g clip-path="url(#clip-1)">
                            <path fill="green" d="M 0 0 H 50 V 50 H 0 Z"/>
                            <path fill="red" d="M 50 0 H 100 V 50 H 50 Z"/>
                        </g>
                    </g>
                </svg>
            """)

            clipping = self.find_clipping(drawing)

            assert clipping is not None
            assert max(clipping.points) == 50
            assert clipping.fillMode == FILL_NON_ZERO

    def test_clipping_path_with_transform_url(self):
        clipping_paths = [
            '<rect id="clip-shape" transform="scale(0.5, 0.5)" '
            + 'height="100" width="100" x="0" y="0"/>',
            '<rect id="clip-shape" transform="scale(0.5, 0.5)" '
            + 'height="100" width="100" x="0" y="0" rx="20" ry="20"/>',
            '<path id="clip-shape" transform="scale(0.5, 0.5)" '
            + 'd="M 0 0 H 100 V 100 H 0 Z"/>',
            '<circle id="clip-shape" transform="scale(0.5, 0.5)" '
            + 'cx="50" cy="50" r="50"/>',
            '<ellipse id="clip-shape" transform="scale(0.5, 0.5)" '
            + 'cx="50" cy="50" rx="50" ry="50"/>',
            '<polygon id="clip-shape" transform="scale(0.5, 0.5)" '
            + 'points="0,100 50,25 50,75 100,0" />',
        ]

        for clipping_path in clipping_paths:
            drawing = drawing_from_svg(f"""
                <svg namespace="http://www.w3.org/XML/1998/namespace"
                     xmlns="http://www.w3.org/2000/svg"
                     xmlns:xlink="http://www.w3.org/1999/xlink" version="1.1"
                     viewBox="0 0 100 50" width="100" height="50">

                    <defs>
                        {clipping_path}
                        <clipPath id="clip-1">
                            <use xlink:href="#clip-shape"/>
                        </clipPath>
                    </defs>
                    <g>
                        <g clip-path="url(#clip-1)">
                            <path fill="green" d="M 0 0 H 50 V 50 H 0 Z"/>
                            <path fill="red" d="M 50 0 H 100 V 50 H 50 Z"/>
                        </g>
                    </g>
                </svg>
            """)

            clipping = self.find_clipping(drawing)

            assert clipping is not None
            assert max(clipping.points) == 50
            assert clipping.fillMode == FILL_NON_ZERO

    def test_clipping_path_fill_rule(self):
        clipping_paths = [
            '<rect clip-rule="evenodd" height="100" width="100" x="0" y="0"/>',
            '<rect clip-rule="evenodd" height="100" width="100" x="0" y="0" rx="20" '
            + 'ry="20"/>',
            '<path clip-rule="evenodd" d="M 0 0 H 100 V 100 H 0 Z"/>',
            '<circle clip-rule="evenodd" cx="50" cy="50" r="50"/>',
            '<ellipse clip-rule="evenodd" cx="50" cy="50" rx="50" ry="50"/>',
            '<polygon clip-rule="evenodd" points="0,100 50,25 50,75 100,0" />',
        ]

        for clipping_path in clipping_paths:
            drawing = drawing_from_svg(f"""
                <svg namespace="http://www.w3.org/XML/1998/namespace"
                     xmlns="http://www.w3.org/2000/svg"
                     xmlns:xlink="http://www.w3.org/1999/xlink" version="1.1"
                     viewBox="0 0 100 50" width="100" height="50">

                    <defs>
                        <clipPath id="clip-1">
                            {clipping_path}
                        </clipPath>
                    </defs>
                    <g clip-path="url(#clip-1)">
                        <path fill="green" d="M 0 0 H 50 V 50 H 0 Z"/>
                    </g>
                </svg>
            """)

            clipping = self.find_clipping(drawing)
            assert clipping.fillMode == FILL_EVEN_ODD

    @pytest.mark.skipif(not has_renderpm_backend(), reason="needs a renderPM backend")
    def test_clipping_path_with_transform_visual(self):
        test_files = [
            "path",
            "rect",
            "rounded-rect",
            "path-no-transform",
            "ellipse",
            "circle",
            "polygon",
            "double-path",
            "overlapping-double-path",
            "overlapping-double-path-inset",
            "multi-path-fill-rule",
        ]

        for test_file in test_files:
            svg = f"clipping/{test_file}.svg"
            raster = f"clipping/{test_file}.png"

            assert svg_raster_difference(svg, raster, 4 / 3) == 0

    @pytest.mark.skipif(not has_renderpm_backend(), reason="needs a renderPM backend")
    @pytest.mark.xfail(reason="Mixed clip-rule clipping paths are not supported")
    def test_mixed_fill_rules(self):
        test_files = [
            "mixed-fill-rule",
        ]

        for test_file in test_files:
            svg = f"clipping/{test_file}.svg"
            raster = f"clipping/{test_file}.png"

            assert svg_raster_difference(svg, raster, 4 / 3) == 0
