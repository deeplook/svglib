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
    results in a ReportLab fontSize of N × 0.75 pt.

Run with: uv run pytest -v tests/test_units.py
"""

import io
import math

from lxml import etree
from reportlab.graphics.shapes import String

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


def _font_size_pt(fs_attr):
    """Return the ReportLab fontSize (in pt) for a <text> element whose
    font-size attribute is *fs_attr*.
    """
    svg = f"""<?xml version="1.0"?>
    <svg xmlns="http://www.w3.org/2000/svg"
         width="200" height="50" viewBox="0 0 200 50">
        <text font-size="{fs_attr}">x</text>
    </svg>"""
    root = etree.parse(io.BytesIO(svg.encode())).getroot()
    drawing = SvgRenderer("").render(root)
    # Walk into the drawing tree to find the first String shape.
    node = drawing.contents[0]
    while hasattr(node, "contents"):
        node = node.contents[0]
    assert isinstance(node, String), f"Expected String, got {type(node)}"
    return node.fontSize


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

    Font sizes are lengths like any other in SVG.  They are parsed to
    user units (px) and then multiplied by PX_TO_PT for ReportLab.

    Key fact: font-size="16" (bare/px) → 12 pt in the PDF,
              font-size="12pt"          → 12 pt in the PDF.
    """

    def test_bare_font_size_scaled_to_pt(self):
        """font-size="16" (bare) → fontSize == 12 pt in ReportLab."""
        assert math.isclose(_font_size_pt("16"), 16 * PX_TO_PT)

    def test_px_font_size_scaled_to_pt(self):
        """font-size="16px" → fontSize == 12 pt in ReportLab."""
        assert math.isclose(_font_size_pt("16px"), 16 * PX_TO_PT)

    def test_pt_font_size_preserved(self):
        """font-size="12pt" → fontSize == 12 pt (no scaling surprise)."""
        assert math.isclose(_font_size_pt("12pt"), 12.0, rel_tol=1e-4)

    def test_bare_and_px_font_size_identical(self):
        """font-size="N" and font-size="Npx" must produce identical fontSize."""
        for n in (10, 13, 16, 24):
            assert math.isclose(
                _font_size_pt(str(n)),
                _font_size_pt(f"{n}px"),
            ), f"font-size mismatch for {n}"

    def test_16px_equals_12pt(self):
        """font-size="16px" and font-size="12pt" must produce the same fontSize.

        16 CSS px × 0.75 = 12 pt — both specify the same physical text size.
        """
        assert math.isclose(
            _font_size_pt("16px"),
            _font_size_pt("12pt"),
            rel_tol=1e-4,
        )

    def test_96px_equals_72pt_font(self):
        """font-size="96px" and font-size="72pt" — one inch of text."""
        assert math.isclose(
            _font_size_pt("96px"),
            _font_size_pt("72pt"),
            rel_tol=1e-4,
        )
