"""Tests for SVG length-unit handling and output dimensions.

SVG lives in a 96 dpi world (1 user unit = 1 CSS px = 1/96 inch).
ReportLab works in points (1 pt = 1/72 inch).
The bridge: 1 px = 0.75 pt  (PX_TO_PT).

These tests document and protect the expected behaviour so that users
can predict what they will get when they convert an SVG to a PDF or
bitmap with svglib:

  - Drawing.width / Drawing.height are always in ReportLab points.
  - Bare numbers and ``px`` units on the <svg> element give the same
    Drawing size (both = value × 0.75 pt).
  - Explicit ``pt`` units are passed through unchanged (value pt).
  - Physical units (``mm``, ``cm``, ``in``) produce the correct point
    size for the declared physical measurement.
  - Font sizes follow the same rules: a bare-number/px font-size of N
    renders at N × 0.75 pt. That is the size in the *output*; inside the
    Drawing, ``String.fontSize`` is in user units like every other
    coordinate below the viewport group.

Run with: uv run pytest -v tests/test_units.py
"""

import io
import math

from lxml import etree
from reportlab.graphics.shapes import Rect, String
from reportlab.pdfbase.pdfmetrics import stringWidth

from svglib.svglib import PX_TO_PT, SvgRenderer
from tests.utils import drawing_from_svg

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _drawing(width_attr, height_attr, extra_attrs=""):
    """Return a Drawing for an SVG whose root element has the given
    width / height attribute strings (e.g. ``'100'``, ``'100px'``,
    ``'72pt'``, ``'25.4mm'``).
    """
    svg = f"""<?xml version="1.0"?>
    <svg xmlns="http://www.w3.org/2000/svg"
         width="{width_attr}" height="{height_attr}" {extra_attrs}>
        <rect x="0" y="0" width="10" height="10" fill="red"/>
    </svg>"""
    return drawing_from_svg(svg)


def _render(svg):
    """Return the Drawing for an SVG string."""
    root = etree.parse(io.BytesIO(svg.encode())).getroot()
    return SvgRenderer("").render(root)


def _shapes_with_scale(drawing):
    """Yield every leaf shape with the total scale applied to it.

    Shapes below the viewport group are in user units; multiplying by the
    scale yielded here gives their size in the output.
    """

    def walk(node, scale):
        for item in getattr(node, "contents", []):
            item_scale = scale * abs(getattr(item, "transform", (1,))[0])
            if hasattr(item, "contents"):
                yield from walk(item, item_scale)
            else:
                yield item, item_scale

    yield from walk(drawing, abs(drawing.transform[0]))


def _rendered_font_size(
    fs_attr, root_attrs='width="200" height="50" viewBox="0 0 200 50"'
):
    """Return the size in pt at which a <text> is rendered.

    Deliberately not ``String.fontSize``: that lives below the viewport
    transform and so does not tell you how large the text comes out.
    """
    svg = f"""<?xml version="1.0"?>
    <svg xmlns="http://www.w3.org/2000/svg" {root_attrs}>
        <text font-size="{fs_attr}">x</text>
    </svg>"""
    for shape, scale in _shapes_with_scale(_render(svg)):
        if isinstance(shape, String):
            return shape.fontSize * scale
    raise AssertionError("no String shape in the drawing")


# ---------------------------------------------------------------------------
# Drawing dimensions — user units / px
# ---------------------------------------------------------------------------


class TestDrawingDimensionsUserUnits:
    """Bare numbers and ``px`` on the root <svg> element.

    SVG spec: bare numbers are user units; 1 user unit = 1 CSS px.
    svglib converts to pt: Drawing size = value × PX_TO_PT.
    """

    def test_bare_number_width(self):
        """width="100" (bare) → Drawing.width == 75 pt."""
        d = _drawing("100", "50")
        assert math.isclose(d.width, 100 * PX_TO_PT)

    def test_bare_number_height(self):
        """height="50" (bare) → Drawing.height == 37.5 pt."""
        d = _drawing("100", "50")
        assert math.isclose(d.height, 50 * PX_TO_PT)

    def test_px_width(self):
        """width="100px" → same Drawing.width as bare "100"."""
        d_bare = _drawing("100", "50")
        d_px = _drawing("100px", "50px")
        assert math.isclose(d_px.width, d_bare.width)
        assert math.isclose(d_px.height, d_bare.height)

    def test_bare_and_px_are_identical(self):
        """Drawing dimensions for bare-number and px must agree (issue #439)."""
        for val in (50, 96, 200, 480):
            d_bare = _drawing(str(val), str(val))
            d_px = _drawing(f"{val}px", f"{val}px")
            assert math.isclose(d_bare.width, d_px.width), f"width mismatch for {val}"
            assert math.isclose(d_bare.height, d_px.height), (
                f"height mismatch for {val}"
            )


# ---------------------------------------------------------------------------
# Drawing dimensions — point units
# ---------------------------------------------------------------------------


class TestDrawingDimensionsPt:
    """Explicit ``pt`` units on the root <svg> element.

    ``pt`` in SVG is an absolute unit (1/72 inch).  After the round-trip
    through user units and back to pt, the numeric value must be
    preserved: width="100pt" → Drawing.width == 100 pt.
    """

    def test_pt_width_preserved(self):
        """width="72pt" → Drawing.width == 72 pt."""
        d = _drawing("72pt", "72pt")
        assert math.isclose(d.width, 72.0, rel_tol=1e-4)

    def test_pt_height_preserved(self):
        """height="36pt" → Drawing.height == 36 pt."""
        d = _drawing("100pt", "36pt")
        assert math.isclose(d.height, 36.0, rel_tol=1e-4)

    def test_pt_differs_from_bare(self):
        """width="100pt" must give a larger Drawing than width="100" (bare px)."""
        d_pt = _drawing("100pt", "100pt")
        d_bare = _drawing("100", "100")
        # 100 pt > 75 pt (100 × 0.75)
        assert d_pt.width > d_bare.width


# ---------------------------------------------------------------------------
# Drawing dimensions — physical units
# ---------------------------------------------------------------------------


class TestDrawingDimensionsPhysical:
    """mm, cm, in on the root <svg> element.

    Physical units must round-trip to the correct point size:
      1 in  = 72 pt
      25.4 mm = 1 in = 72 pt
      2.54 cm = 1 in = 72 pt
    """

    def test_one_inch_width(self):
        """width="1in" → Drawing.width == 72 pt."""
        d = _drawing("1in", "1in")
        assert math.isclose(d.width, 72.0, rel_tol=1e-4)

    def test_25_4mm_equals_one_inch(self):
        """width="25.4mm" → Drawing.width == 72 pt (1 inch)."""
        d = _drawing("25.4mm", "25.4mm")
        assert math.isclose(d.width, 72.0, rel_tol=1e-3)

    def test_2_54cm_equals_one_inch(self):
        """width="2.54cm" → Drawing.width == 72 pt (1 inch)."""
        d = _drawing("2.54cm", "2.54cm")
        assert math.isclose(d.width, 72.0, rel_tol=1e-3)

    def test_mm_and_in_agree(self):
        """25.4 mm and 1 in must produce the same Drawing size."""
        d_mm = _drawing("25.4mm", "25.4mm")
        d_in = _drawing("1in", "1in")
        assert math.isclose(d_mm.width, d_in.width, rel_tol=1e-4)

    def test_96px_equals_one_inch(self):
        """96 CSS px == 1 inch; Drawing.width for width="96" == 72 pt."""
        d = _drawing("96", "96")
        assert math.isclose(d.width, 72.0, rel_tol=1e-4)

    def test_96px_and_1in_agree(self):
        """width="96" and width="1in" must produce the same Drawing size."""
        d_px = _drawing("96", "96")
        d_in = _drawing("1in", "1in")
        assert math.isclose(d_px.width, d_in.width, rel_tol=1e-4)


# ---------------------------------------------------------------------------
# Font sizes
# ---------------------------------------------------------------------------


class TestFontSizeUnits:
    """Font-size unit handling.

    Font sizes are lengths like any other in SVG. They are parsed to user
    units (px) and converted to points once by the viewport transform.

    Key fact: font-size="16" (bare/px) → 12 pt in the PDF,
              font-size="12pt"          → 12 pt in the PDF.

    These assert the *rendered* size: ``String.fontSize`` alone cannot express
    that, since the viewport transform still applies to it.
    """

    def test_bare_font_size_scaled_to_pt(self):
        """font-size="16" (bare) → renders at 12 pt."""
        assert math.isclose(_rendered_font_size("16"), 16 * PX_TO_PT)

    def test_px_font_size_scaled_to_pt(self):
        """font-size="16px" → renders at 12 pt."""
        assert math.isclose(_rendered_font_size("16px"), 16 * PX_TO_PT)

    def test_pt_font_size_preserved(self):
        """font-size="12pt" → renders at 12 pt (no scaling surprise)."""
        assert math.isclose(_rendered_font_size("12pt"), 12.0, rel_tol=1e-4)

    def test_bare_and_px_font_size_identical(self):
        """font-size="N" and font-size="Npx" must render identically."""
        for n in (10, 13, 16, 24):
            assert math.isclose(
                _rendered_font_size(str(n)),
                _rendered_font_size(f"{n}px"),
            ), f"font-size mismatch for {n}"

    def test_16px_equals_12pt(self):
        """font-size="16px" and font-size="12pt" must render at the same size.

        16 CSS px × 0.75 = 12 pt — both specify the same physical text size.
        """
        assert math.isclose(
            _rendered_font_size("16px"),
            _rendered_font_size("12pt"),
            rel_tol=1e-4,
        )

    def test_96px_equals_72pt_font(self):
        """font-size="96px" and font-size="72pt" — one inch of text."""
        assert math.isclose(
            _rendered_font_size("96px"),
            _rendered_font_size("72pt"),
            rel_tol=1e-4,
        )


# ---------------------------------------------------------------------------
# Text relative to the geometry it belongs to (issue #502)
# ---------------------------------------------------------------------------


class TestTextToGeometryScale:
    """Text and geometry must be scaled by the same amount.

    A conversion applied to ``font-size`` on top of the viewport transform
    shows up in no single absolute measurement, only as a ratio: text ends up
    at 0.75x the size of the artwork it labels (issue #502).
    """

    # In any renderer the text is a third of the bar.
    BAR_WIDTH = 48
    FONT_SIZE = 16

    def _ratio(self, root_attrs):
        """Return rendered font size / rendered bar width for a root element."""
        svg = f"""<?xml version="1.0"?>
        <svg xmlns="http://www.w3.org/2000/svg" {root_attrs}>
            <rect x="0" y="0" width="{self.BAR_WIDTH}" height="8"/>
            <text x="10" y="50" font-size="{self.FONT_SIZE}">x</text>
        </svg>"""
        font_size = bar_width = None
        for shape, scale in _shapes_with_scale(_render(svg)):
            if isinstance(shape, String):
                font_size = shape.fontSize * scale
            elif isinstance(shape, Rect):
                bar_width = shape.width * scale
        assert font_size is not None and bar_width is not None
        return font_size / bar_width

    def test_ratio_is_preserved_for_every_root_unit(self):
        """The ratio survives every way of sizing the root.

        The last two give a viewport scale of 1.0 and 1.5 rather than 0.75, so
        a fix that merely cancels one particular factor still fails here.
        """
        expected = self.FONT_SIZE / self.BAR_WIDTH
        for root_attrs in (
            'viewBox="0 0 96 96"',
            'width="96" height="96" viewBox="0 0 96 96"',
            'width="96px" height="96px" viewBox="0 0 96 96"',
            'width="72pt" height="72pt" viewBox="0 0 96 96"',
            'width="96" height="96"',
            'width="100pt" height="100pt" viewBox="0 0 96 96"',
            'width="96" height="96" viewBox="0 0 48 48"',
        ):
            assert math.isclose(self._ratio(root_attrs), expected, rel_tol=1e-6), (
                f"text-to-geometry ratio wrong for {root_attrs}"
            )


class TestTextFragmentPositioning:
    """Advance widths must be measured in the units of the coordinates.

    ``convertText`` places each fragment after the first by adding the width of
    the preceding text to an x coordinate in user units. Measuring in points
    instead shifts every fragment but the first (issue #502).
    """

    def _strings(self, body, root_attrs='width="200" height="50" viewBox="0 0 200 50"'):
        """Return the String shapes for an SVG body, in document order."""
        svg = f"""<?xml version="1.0"?>
        <svg xmlns="http://www.w3.org/2000/svg" {root_attrs}>{body}</svg>"""
        return [
            shape
            for shape, _scale in _shapes_with_scale(_render(svg))
            if isinstance(shape, String)
        ]

    def test_second_tspan_starts_where_the_first_ends(self):
        """A tspan without its own x continues where the previous one ends.

        The gap is derived from the font size in the source, not from the
        String's own fontSize, which would make the assertion self-consistent.
        """
        body = (
            '<text x="0" y="20" font-size="16" font-family="Helvetica">'
            "<tspan>AAA</tspan><tspan>BBB</tspan></text>"
        )
        first, second = self._strings(body)

        assert math.isclose(
            second.x - first.x,
            stringWidth("AAA", "Helvetica", 16),
            rel_tol=1e-6,
        )

    def test_per_character_positions_advance_in_user_units(self):
        """Characters beyond the x list advance by their own width.

        Fewer ``x`` values than characters reaches the per-character branch,
        which calls stringWidth separately from the fragment case above.
        """
        body = '<text x="0 30" y="20" font-size="16" font-family="Helvetica">abc</text>'
        shapes = self._strings(body)

        assert [s.text for s in shapes] == ["a", "b", "c"]
        # "c" has no x of its own and must follow "b" by b's width.
        assert math.isclose(
            shapes[2].x,
            30.0 + stringWidth("b", "Helvetica", 16),
            rel_tol=1e-6,
        )


# ---------------------------------------------------------------------------
# SVG 2 viewport and root-relative units (issue #449)
# ---------------------------------------------------------------------------


def _converter_with_box(width: float, height: float):
    """Return an Svg2RlgAttributeConverter with main_box set to the given size."""
    from svglib.svglib import Box, Svg2RlgAttributeConverter

    conv = Svg2RlgAttributeConverter()
    conv.set_box(Box(0, 0, width, height))
    return conv


class TestSVG2ViewportUnits:
    """rem, vw, vh, vmin, vmax, q — SVG 2 / CSS length units."""

    def test_rem_equals_16px_default(self):
        """1rem == 16 user units when root has no explicit font-size (CSS default)."""
        conv = _converter_with_box(400, 300)
        assert math.isclose(conv.convertLength("1rem"), 16.0)
        assert math.isclose(conv.convertLength("2rem"), 32.0)

    def test_rem_matches_16px_literal(self):
        """1rem and 16px must produce identical lengths when using the default."""
        conv = _converter_with_box(400, 300)
        assert math.isclose(conv.convertLength("1rem"), conv.convertLength("16px"))

    def test_rem_uses_root_font_size_from_svg(self):
        """rem resolves against the root <svg> font-size, not always 16px."""
        drawing = drawing_from_svg(
            """<?xml version="1.0"?>
            <svg xmlns="http://www.w3.org/2000/svg"
                 width="400" height="300" viewBox="0 0 400 300"
                 font-size="20px">
              <rect x="0" y="0" width="2rem" height="1rem"/>
            </svg>"""
        )
        rect = drawing.contents[0].contents[0]
        # 2rem = 2 * 20px = 40 user units; 1rem = 20 user units
        assert math.isclose(rect.width, 40.0, rel_tol=1e-4)
        assert math.isclose(rect.height, 20.0, rel_tol=1e-4)

    def test_rem_default_when_no_root_font_size(self):
        """rem defaults to 16px when root <svg> has no explicit font-size."""
        drawing = drawing_from_svg(
            """<?xml version="1.0"?>
            <svg xmlns="http://www.w3.org/2000/svg"
                 width="400" height="300" viewBox="0 0 400 300">
              <rect x="0" y="0" width="1rem" height="1rem"/>
            </svg>"""
        )
        rect = drawing.contents[0].contents[0]
        assert math.isclose(rect.width, 16.0, rel_tol=1e-4)
        assert math.isclose(rect.height, 16.0, rel_tol=1e-4)

    def test_vw_fraction_of_viewport_width(self):
        """50vw == 50% of viewport width (200 user units for a 400-wide box)."""
        conv = _converter_with_box(400, 300)
        assert math.isclose(conv.convertLength("50vw"), 200.0)
        assert math.isclose(conv.convertLength("100vw"), 400.0)

    def test_vh_fraction_of_viewport_height(self):
        """50vh == 50% of viewport height (150 user units for a 300-tall box)."""
        conv = _converter_with_box(400, 300)
        assert math.isclose(conv.convertLength("50vh"), 150.0)
        assert math.isclose(conv.convertLength("100vh"), 300.0)

    def test_vmin_uses_smaller_dimension(self):
        """100vmin == the smaller of viewport width and height."""
        conv = _converter_with_box(400, 300)
        assert math.isclose(conv.convertLength("100vmin"), 300.0)

    def test_vmax_uses_larger_dimension(self):
        """100vmax == the larger of viewport width and height."""
        conv = _converter_with_box(400, 300)
        assert math.isclose(conv.convertLength("100vmax"), 400.0)

    def test_vmin_vmax_square_viewport_equal(self):
        """For a square viewport, vmin == vmax."""
        conv = _converter_with_box(200, 200)
        assert math.isclose(conv.convertLength("50vmin"), conv.convertLength("50vmax"))

    def test_q_quarter_millimetre(self):
        """4q == 1mm (q is a quarter-millimetre)."""
        conv = _converter_with_box(400, 300)
        assert math.isclose(
            conv.convertLength("4q"), conv.convertLength("1mm"), rel_tol=1e-4
        )

    def test_q_100_equals_25mm(self):
        """100q == 25mm."""
        conv = _converter_with_box(400, 300)
        assert math.isclose(
            conv.convertLength("100q"), conv.convertLength("25mm"), rel_tol=1e-4
        )

    def test_vw_used_in_svg_rect(self):
        """A rect with width="50vw" in a 400-unit viewport is 200 user units wide."""
        drawing = drawing_from_svg(
            """<?xml version="1.0"?>
            <svg xmlns="http://www.w3.org/2000/svg"
                 width="400" height="300" viewBox="0 0 400 300">
              <rect id="r" x="0" y="0" width="50vw" height="50vh"/>
            </svg>"""
        )
        rect = drawing.contents[0].contents[0]
        # rect stores dimensions in user units; the group transform converts to pts
        assert math.isclose(rect.width, 200.0, rel_tol=1e-4)
        assert math.isclose(rect.height, 150.0, rel_tol=1e-4)
