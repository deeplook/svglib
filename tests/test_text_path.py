"""<textPath> support and the helpers behind it."""

from math import atan2, degrees
from typing import Any
from xml.etree import ElementTree

import pytest
from reportlab.graphics import renderPDF
from reportlab.graphics.shapes import (
    Drawing,
    String,
)
from reportlab.lib import colors
from reportlab.pdfbase.pdfmetrics import stringWidth

from svglib import svglib, utils
from tests import textpath_sheet
from tests.utils import (
    drawing_from_svg,
)


class TestTextPath:
    @staticmethod
    def _glyphs_on_path(drawing: Drawing) -> list[tuple[str, float, float, float]]:
        """Return (char, x, y, angle) of the midpoint of each <textPath> glyph.

        The angle is in degrees, in the SVG's own (y down) coordinate system.
        """
        found: list[tuple[str, float, float, float]] = []

        def walk(shape: Any) -> None:
            for child in getattr(shape, "contents", []):
                if isinstance(child, String):
                    a, b, _c, _d, e, f = shape.transform
                    found.append(
                        (
                            child.text,
                            round(e, 6),
                            round(-f, 6),
                            round(-degrees(atan2(b, a)), 6),
                        )
                    )
                else:
                    walk(child)

        walk(drawing)
        return found

    TEXT_PATH_SVG = """
        <svg xmlns="http://www.w3.org/2000/svg"
             xmlns:xlink="http://www.w3.org/1999/xlink" width="200" height="200">
          <defs>{defs}</defs>
          <text font-size="10" {text_attrs}>{before}<textPath
              xlink:href="#p" {path_attrs}>{content}</textPath>{after}</text>
        </svg>
    """

    def _text_path(
        self,
        d: str = "M10,50 L110,50",
        content: str = "abc",
        defs_attrs: str = "",
        text_attrs: str = "",
        path_attrs: str = "",
        before: str = "",
        after: str = "",
    ) -> Drawing:
        return drawing_from_svg(
            self.TEXT_PATH_SVG.format(
                defs=f'<path id="p" d="{d}" {defs_attrs}/>',
                text_attrs=text_attrs,
                path_attrs=path_attrs,
                content=content,
                before=before,
                after=after,
            )
        )

    def test_text_path_straight_line(self):
        glyphs = self._glyphs_on_path(self._text_path())
        widths = [stringWidth(c, "Helvetica", 10) for c in "abc"]
        assert [g[0] for g in glyphs] == ["a", "b", "c"]
        expected_x = [10 + sum(widths[:i]) + w / 2 for i, w in enumerate(widths)]
        assert [g[1] for g in glyphs] == pytest.approx(expected_x)
        assert [g[2] for g in glyphs] == pytest.approx([50, 50, 50])
        assert [g[3] for g in glyphs] == pytest.approx([0, 0, 0])

    def test_text_path_follows_direction(self):
        glyphs = self._glyphs_on_path(self._text_path(d="M50,10 L50,110"))
        # Running downwards in SVG coordinates is a quarter turn clockwise.
        assert [g[3] for g in glyphs] == pytest.approx([90, 90, 90])
        assert [g[1] for g in glyphs] == pytest.approx([50, 50, 50])
        assert glyphs[0][2] == pytest.approx(10 + stringWidth("a", "Helvetica", 10) / 2)

    def test_text_path_follows_curve(self):
        glyphs = self._glyphs_on_path(
            self._text_path(
                d="M10,100 Q60,0 110,100",
                content="a" * 20,
                path_attrs='startOffset="50%" text-anchor="middle"',
            )
        )
        angles = [g[3] for g in glyphs]
        # The text climbs, flattens at the top of the curve, then descends.
        assert angles == sorted(angles)
        assert angles[0] < -30 and angles[-1] > 30
        assert angles[0] == pytest.approx(-angles[-1], abs=2)

    def test_text_path_start_offset(self):
        plain = self._glyphs_on_path(self._text_path())
        for offset, shift in (("20", 20), ("50%", 50), ("-5", -5)):
            glyphs = self._glyphs_on_path(
                self._text_path(path_attrs=f'startOffset="{offset}"')
            )
            got = [g[1] for g in glyphs]
            want = [g[1] + shift for g in plain]
            # Glyphs starting before the path are dropped.
            assert got == pytest.approx(want[len(want) - len(got) :])

    def test_text_path_anchor(self):
        widths = sum(stringWidth(c, "Helvetica", 10) for c in "abc")
        for anchor, shift in (("start", 0), ("middle", -widths / 2), ("end", -widths)):
            glyphs = self._glyphs_on_path(
                self._text_path(
                    d="M10,50 L110,50",
                    path_attrs=f'startOffset="50" text-anchor="{anchor}"',
                )
            )
            # The anchor is the start offset, so glyphs move back with it.
            assert glyphs[0][1] == pytest.approx(
                10 + 50 + shift + stringWidth("a", "Helvetica", 10) / 2
            )

    def test_text_path_text_anchor_set_on_text(self):
        glyphs = self._glyphs_on_path(
            self._text_path(
                text_attrs='text-anchor="end"', path_attrs='startOffset="100"'
            )
        )
        assert glyphs[-1][1] < 110

    def test_text_path_drops_glyphs_beyond_path_end(self):
        glyphs = self._glyphs_on_path(
            self._text_path(d="M10,50 L25,50", content="abcdefgh")
        )
        assert 0 < len(glyphs) < 8
        assert all(g[1] <= 25 for g in glyphs)

    def test_text_path_applies_path_transform(self):
        glyphs = self._glyphs_on_path(
            self._text_path(defs_attrs='transform="translate(0,30) rotate(90)"')
        )
        # M10,50 L110,50 turned a quarter clockwise around the origin, then moved.
        assert glyphs[0][3] == pytest.approx(90)
        assert glyphs[0][1] == pytest.approx(-50)
        assert glyphs[0][2] == pytest.approx(
            30 + 10 + stringWidth("a", "Helvetica", 10) / 2
        )

    def test_text_path_closed_path_returns_to_start(self):
        glyphs = self._glyphs_on_path(
            self._text_path(d="M10,10 L50,10 L50,50 Z", content="a" * 20)
        )
        angles = {round(g[3]) for g in glyphs}
        assert {0, 90} <= angles
        # The closing edge runs back up to the start of the triangle.
        assert any(a < -90 or a > 90 for a in angles)

    def test_text_path_with_tspan_styles(self):
        drawing = self._text_path(
            content='ab<tspan fill="#ff0000" font-size="20">cd</tspan>',
        )
        strings = {s.text: s for s in self._shapes(drawing)}
        assert strings["a"].fontSize == 10
        assert strings["c"].fontSize == 20
        assert strings["c"].fillColor == colors.red
        assert strings["a"].textAnchor == "start"
        # Wider glyphs push the later ones further along the path.
        glyphs = self._glyphs_on_path(drawing)
        gap = glyphs[3][1] - glyphs[2][1]
        assert gap == pytest.approx(
            (stringWidth("c", "Helvetica", 20) + stringWidth("d", "Helvetica", 20)) / 2
        )

    @staticmethod
    def _shapes(drawing: Drawing) -> list[String]:
        found: list[String] = []

        def walk(shape: Any) -> None:
            for child in getattr(shape, "contents", []):
                if isinstance(child, String):
                    found.append(child)
                else:
                    walk(child)

        walk(drawing)
        return found

    def test_text_path_keeps_surrounding_text(self):
        drawing = drawing_from_svg(
            """
            <svg xmlns="http://www.w3.org/2000/svg"
                 xmlns:xlink="http://www.w3.org/1999/xlink" width="200" height="200">
              <defs><path id="p" d="M10,50 L110,50"/></defs>
              <text x="5" y="150" font-size="10">before <textPath xlink:href="#p"
                >on path</textPath> after</text>
            </svg>
            """
        )
        texts = [s.text for s in self._shapes(drawing)]
        assert [t for t in texts if len(t) > 1] == ["before ", " after"]
        assert [t for t in texts if len(t) == 1] == list("onpath")

    @pytest.mark.parametrize(
        "href",
        ["#missing", "", "#q", "other.svg#p"],
    )
    def test_text_path_with_unusable_target(self, href):
        drawing = drawing_from_svg(
            f"""
            <svg xmlns="http://www.w3.org/2000/svg"
                 xmlns:xlink="http://www.w3.org/1999/xlink" width="200" height="200">
              <defs>
                <path id="p" d="M10,50 L110,50"/>
                <rect id="q" width="5" height="5"/>
              </defs>
              <text font-size="10"><textPath xlink:href="{href}">abc</textPath></text>
            </svg>
            """
        )
        assert self._shapes(drawing) == []

    def test_text_path_href_without_namespace(self):
        drawing = drawing_from_svg(
            """
            <svg xmlns="http://www.w3.org/2000/svg" width="200" height="200">
              <defs><path id="p" d="M10,50 L110,50"/></defs>
              <text font-size="10"><textPath href="#p">abc</textPath></text>
            </svg>
            """
        )
        assert len(self._shapes(drawing)) == 3

    def test_text_path_renders_to_pdf(self):
        drawing = self._text_path(d="M10,100 Q60,0 110,100", content="Hello world")
        assert renderPDF.drawToString(drawing).startswith(b"%PDF")

    def test_flatten_path_closes_subpath_and_skips_moves(self):
        segments = utils.flatten_path(
            [0, 1, 1, 3, 0, 1], [0, 0, 10, 0, 10, 10, 50, 50, 60, 50]
        )
        assert segments == [
            (0, 0, 10, 0),
            (10, 0, 10, 10),
            (10, 10, 0, 0),
            (50, 50, 60, 50),
        ]

    def test_flatten_path_curve_ends_on_endpoint(self):
        segments = utils.flatten_path([0, 2], [0, 0, 0, 10, 10, 10, 10, 0], 4)
        assert len(segments) == 4
        assert segments[-1][2:] == pytest.approx((10, 0))

    def test_path_sampler(self):
        sampler = utils.PathSampler([(0, 0, 10, 0), (10, 0, 10, 10)])
        assert sampler.length == 20
        assert sampler.at(5) == (5, 0, 0)
        assert sampler.at(15) == (10, 5, 90)
        assert sampler.at(10) is not None
        assert sampler.at(-1) is None
        assert sampler.at(21) is None
        assert utils.PathSampler([]).at(0) is None

    def test_place_glyphs_on_path(self):
        sampler = utils.PathSampler([(0, 0, 10, 0)])
        placements = utils.place_glyphs_on_path([4, 4, 4], sampler, 0)
        # The midpoint of the third glyph is at 10, the very end, which counts.
        assert [p[0] if p else None for p in placements] == [2, 6, 10]
        placements = utils.place_glyphs_on_path([4, 4, 4], sampler, 1)
        assert [p[0] if p else None for p in placements] == [3, 7, None]

    def test_text_path_samples_are_described(self):
        paths = textpath_sheet.sample_paths()
        assert len(paths) >= 10
        assert all(textpath_sheet.description(p) for p in paths)

    def test_text_path_samples_render_every_glyph_that_fits(self):
        """Every sample draws all its non-space characters, bar the overflow one."""
        for path in textpath_sheet.sample_paths():
            root = ElementTree.parse(path).getroot()
            text = "".join(root.find(".//{*}textPath").itertext())
            expected = len("".join(text.split()))
            drawing = svglib.svg2rlg(str(path))
            count = len(self._glyphs_on_path(drawing))
            if path.stem == "overflow":
                assert 0 < count < expected
            else:
                assert count == expected, path.name

    def test_text_path_contact_sheet(self, tmp_path):
        out = tmp_path / "sheet.pdf"
        count = textpath_sheet.build_contact_sheet(out)
        assert count == len(textpath_sheet.sample_paths())
        assert out.read_bytes().startswith(b"%PDF")
