"""Document structure: groups, switch, symbol and view boxes."""

import pytest
from reportlab.graphics.shapes import (
    Group,
    Path,
    Rect,
)

from svglib import svglib
from tests.utils import (
    drawing_from_svg,
)


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

    def test_display_none_in_style_attribute(self):
        """display:none set through the style attribute hides the node."""
        drawing = drawing_from_svg(
            """
            <?xml version="1.0"?>
            <svg width="100" height="100">
                <rect x="5" y="5" width="10" height="10"/>
                <rect x="5" y="25" width="10" height="10" style="display:none"/>
                <g style="display:none">
                    <rect x="5" y="45" width="10" height="10"/>
                </g>
            </svg>
        """
        )
        rects = []

        def collect(node):
            for child in getattr(node, "contents", []):
                if isinstance(child, Rect):
                    rects.append(child)
                collect(child)

        collect(drawing)
        assert [rect.y for rect in rects] == [5]

    def test_visibility_hidden(self):
        """visibility hidden/collapse hides the node, and is inheritable."""
        drawing = drawing_from_svg(
            """
            <?xml version="1.0"?>
            <svg width="100" height="100">
                <rect x="5" y="5" width="10" height="10"/>
                <rect x="5" y="25" width="10" height="10" visibility="hidden"/>
                <rect x="5" y="45" width="10" height="10" style="visibility:collapse"/>
                <g visibility="hidden">
                    <rect x="5" y="65" width="10" height="10"/>
                    <rect x="5" y="85" width="10" height="10" visibility="visible"/>
                </g>
            </svg>
        """
        )
        rects = []

        def collect(node):
            for child in getattr(node, "contents", []):
                if isinstance(child, Rect):
                    rects.append(child)
                collect(child)

        collect(drawing)
        assert [rect.y for rect in rects] == [5, 85]

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


class TestSwitchNode:
    @staticmethod
    def _find_rects(shape):
        from reportlab.graphics.shapes import Rect

        results = []
        if isinstance(shape, Rect):
            results.append(shape)
        if hasattr(shape, "contents"):
            for item in shape.contents:
                results.extend(TestSwitchNode._find_rects(item))
        return results

    def test_switch_skips_unsupported_extension(self):
        """<switch> skips children with requiredExtensions and renders the fallback."""
        drawing = drawing_from_svg(
            """
            <?xml version="1.0"?>
            <svg xmlns="http://www.w3.org/2000/svg" width="100" height="100">
                <switch>
                    <rect requiredExtensions="http://ns.adobe.com/AdobeIllustrator/10.0/"
                          width="100" height="100" fill="red"/>
                    <rect width="50" height="50" fill="blue"/>
                </switch>
            </svg>
        """
        )
        rects = self._find_rects(drawing)
        assert len(rects) == 1
        assert rects[0].fillColor.hexval() == "0x0000ff"

    def test_switch_skips_unsupported_feature(self):
        """<switch> must skip children with unsupported requiredFeatures."""
        drawing = drawing_from_svg(
            """
            <?xml version="1.0"?>
            <svg xmlns="http://www.w3.org/2000/svg" width="100" height="100">
                <switch>
                    <rect requiredFeatures="http://www.w3.org/TR/SVG11/feature#Animation"
                          width="100" height="100" fill="red"/>
                    <rect width="50" height="50" fill="green"/>
                </switch>
            </svg>
        """
        )
        rects = self._find_rects(drawing)
        assert len(rects) == 1
        assert rects[0].fillColor.hexval() == "0x008000"

    def test_switch_renders_supported_feature(self):
        """<switch> renders the first child whose requiredFeatures are all supported."""
        drawing = drawing_from_svg(
            """
            <?xml version="1.0"?>
            <svg xmlns="http://www.w3.org/2000/svg" width="100" height="100">
                <switch>
                    <rect requiredFeatures="http://www.w3.org/TR/SVG11/feature#Shape"
                          width="100" height="100" fill="blue"/>
                    <rect width="50" height="50" fill="red"/>
                </switch>
            </svg>
        """
        )
        rects = self._find_rects(drawing)
        assert len(rects) == 1
        assert rects[0].fillColor.hexval() == "0x0000ff"

    def test_switch_matches_system_language(self, monkeypatch):
        """<switch> renders the first child whose systemLanguage matches the locale."""
        for var in ("LC_ALL", "LC_CTYPE", "LANGUAGE"):
            monkeypatch.delenv(var, raising=False)
        monkeypatch.setenv("LANG", "de_DE.UTF-8")
        drawing = drawing_from_svg(
            """
            <?xml version="1.0"?>
            <svg xmlns="http://www.w3.org/2000/svg" width="100" height="100">
                <switch>
                    <rect systemLanguage="fr" width="100" height="100" fill="red"/>
                    <rect systemLanguage="de" width="80" height="80" fill="green"/>
                    <rect width="50" height="50" fill="blue"/>
                </switch>
            </svg>
        """
        )
        rects = self._find_rects(drawing)
        assert len(rects) == 1
        assert rects[0].fillColor.hexval() == "0x008000"  # "de" matches "de_DE"

    def test_switch_skips_nonmatching_system_language(self, monkeypatch):
        """<switch> skips a non-matching systemLanguage and renders the fallback."""
        for var in ("LC_ALL", "LC_CTYPE", "LANGUAGE"):
            monkeypatch.delenv(var, raising=False)
        monkeypatch.setenv("LANG", "en_US.UTF-8")
        drawing = drawing_from_svg(
            """
            <?xml version="1.0"?>
            <svg xmlns="http://www.w3.org/2000/svg" width="100" height="100">
                <switch>
                    <rect systemLanguage="fr" width="100" height="100" fill="red"/>
                    <rect width="50" height="50" fill="blue"/>
                </switch>
            </svg>
        """
        )
        rects = self._find_rects(drawing)
        assert len(rects) == 1
        assert rects[0].fillColor.hexval() == "0x0000ff"  # "fr" skipped, fallback used


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
        assert drawing.contents[0].transform == (7.5, 0.0, 0.0, -7.5, 450.0, 300.0)

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
        assert (drawing.width, drawing.height) == (360.0, 270.0)

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
        assert (drawing.width, drawing.height) == (360.0, 270.0)

    def test_preserve_aspect_ratio_meet_default(self):
        """Mismatched aspect ratios use uniform (min) scale by default."""
        drawing = drawing_from_svg(
            """
            <?xml version="1.0"?>
            <svg xmlns="http://www.w3.org/2000/svg"
                 width="12cm" height="5.25cm" viewBox="0 0 1200 400">
                <rect width="100" height="100"/>
            </svg>
        """
        )
        t = drawing.contents[0].transform
        x_scale = t[0]
        y_scale = abs(t[3])
        assert pytest.approx(x_scale) == y_scale

    def test_preserve_aspect_ratio_none(self):
        """preserveAspectRatio="none" uses independent x/y scales."""
        drawing = drawing_from_svg(
            """
            <?xml version="1.0"?>
            <svg xmlns="http://www.w3.org/2000/svg"
                 width="12cm" height="5.25cm" viewBox="0 0 1200 400"
                 preserveAspectRatio="none">
                <rect width="100" height="100"/>
            </svg>
        """
        )
        t = drawing.contents[0].transform
        x_scale = t[0]
        y_scale = abs(t[3])
        assert x_scale != pytest.approx(y_scale)

    def test_preserve_aspect_ratio_slice(self):
        """preserveAspectRatio="xMidYMid slice" uses uniform (max) scale."""
        drawing = drawing_from_svg(
            """
            <?xml version="1.0"?>
            <svg xmlns="http://www.w3.org/2000/svg"
                 width="12cm" height="5.25cm" viewBox="0 0 1200 400"
                 preserveAspectRatio="xMidYMid slice">
                <rect width="100" height="100"/>
            </svg>
        """
        )
        t = drawing.contents[0].transform
        x_scale = t[0]
        y_scale = abs(t[3])
        # slice uses max scale, so the larger scale (y_scale ~0.372) should be used
        assert pytest.approx(x_scale) == y_scale
        # The uniform scale should be the larger one (max of the two raw scales, ~0.372)
        assert x_scale > 0.284

    def test_preserve_aspect_ratio_matched_aspect_ratio(self):
        """When aspect ratios match exactly, scale is unchanged."""
        drawing = drawing_from_svg(
            """
            <?xml version="1.0"?>
            <svg xmlns="http://www.w3.org/2000/svg"
                 width="1200" height="800" viewBox="-60 -40 120 80">
                <rect width="10" height="10"/>
            </svg>
        """
        )
        t = drawing.contents[0].transform
        x_scale = t[0]
        y_scale = abs(t[3])
        assert pytest.approx(x_scale) == y_scale


def test_malformed_viewbox_is_ignored():
    # A viewBox that is not four numbers used to raise TypeError from
    # Box(*values); per the SVG spec an invalid viewBox is ignored, falling
    # back to width/height, instead of crashing.
    for view_box in ("0 0 100", "0 0 100 100 200", "0 0 abc 100", "0,0,100"):
        drawing = drawing_from_svg(
            '<svg xmlns="http://www.w3.org/2000/svg" width="50" height="40" '
            'viewBox="%s"><rect x="1" y="1" width="5" height="5"/></svg>' % view_box
        )
        assert drawing is not None
