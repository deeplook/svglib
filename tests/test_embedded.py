"""Embedded and referenced images and SVGs."""

import pytest
from reportlab.graphics.shapes import Group

from svglib.svglib import svg2rlg
from tests.utils import (
    drawing_from_svg,
    find_image_in_drawing,
)


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
        assert embedded_svg_group.getProperties()["transform"][-2:] == pytest.approx(
            (0, 100)
        )
        # viewBox scaling: 105mm is 396.85 user units of the parent, for 210
        # user units of the nested viewBox
        assert (
            pytest.approx(1.89, 0.001)
            == embedded_svg_group.getProperties()["transform"][0]
        )
        assert (
            pytest.approx(1.89, 0.001)
            == embedded_svg_group.getProperties()["transform"][3]
        )

    @pytest.mark.parametrize(
        "image_attributes",
        [
            'width="40" height="20" preserveAspectRatio="none"',
            'width="40" height="20"',
            'width="40" height="20" preserveAspectRatio="xMinYMax slice"',
        ],
    )
    def test_svg_in_image_fills_the_image_viewport(self, tmp_path, image_attributes):
        """An <image> of an SVG document draws it in the image's viewport, with
        the image's preserveAspectRatio, like a nested <svg> (issue #237)."""
        (tmp_path / "square.svg").write_text(
            '<svg xmlns="http://www.w3.org/2000/svg" width="200mm" height="200mm"'
            ' viewBox="0 0 10 10" preserveAspectRatio="xMaxYMin meet">'
            '<rect width="10" height="10"/></svg>'
        )
        header = (
            '<svg xmlns="http://www.w3.org/2000/svg"'
            ' xmlns:xlink="http://www.w3.org/1999/xlink" width="100" height="100">'
        )
        image = tmp_path / "image.svg"
        image.write_text(
            header + f'<image xlink:href="square.svg" x="5" y="5" {image_attributes}/>'
            # The same document again, at another size
            '<image xlink:href="square.svg" x="60" y="60" width="10" height="10"/>'
            "</svg>"
        )
        inline = tmp_path / "inline.svg"
        nested = '<rect width="10" height="10"/></svg>'
        inline.write_text(
            header
            + f'<svg x="5" y="5" viewBox="0 0 10 10" {image_attributes}>{nested}'
            + f'<svg x="60" y="60" width="10" height="10" viewBox="0 0 10 10">{nested}'
            + "</svg>"
        )
        image_groups = svg2rlg(str(image)).contents[0].contents
        inline_groups = svg2rlg(str(inline)).contents[0].contents
        assert len(image_groups) == len(inline_groups) == 2
        for image_group, inline_group in zip(image_groups, inline_groups):
            assert image_group.getBounds() == pytest.approx(inline_group.getBounds())

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

    def test_nested_svg_without_width_height(self):
        """A nested <svg viewBox="..."> with omitted width/height should
        default to 100% of the parent viewport (SVG 1.1 §5.1.2). Without
        the fallback, the viewBox-to-viewport scaling was skipped and
        inner content rendered at viewBox-unit size instead of filling
        the slot."""
        drawing = drawing_from_svg(
            """
            <?xml version="1.0"?>
            <svg xmlns="http://www.w3.org/2000/svg" version="1.1"
                 width="200" height="200">
              <svg viewBox="0 0 50 50">
                <rect x="0" y="0" width="50" height="50"/>
              </svg>
            </svg>
        """
        )
        # Measured in the drawing, after the parent's scaling
        xmin, ymin, xmax, ymax = drawing.contents[0].getBounds()
        # Parent viewport is 200x200px = 150x150pt (px→pt at 0.75). The inner
        # SVG inherits the parent slot, so the rect fills 150×150pt — not
        # 50×50 (viewBox units without scaling), which is what happens without
        # the fallback.
        assert xmax - xmin == pytest.approx(150)
        assert ymax - ymin == pytest.approx(150)

    @pytest.mark.parametrize(
        "outer",
        [
            'width="400" height="400"',
            'width="400" height="400" viewBox="0 0 400 400"',
            'width="210mm" height="297mm" viewBox="0 0 210 297"',
        ],
    )
    def test_nested_svg_fills_its_viewport(self, outer):
        """The content of a nested <svg> fills the rectangle given by its x, y,
        width and height, in the user units of the parent."""
        drawing = drawing_from_svg(
            f"""
            <svg xmlns="http://www.w3.org/2000/svg" {outer}>
              <rect x="50" y="50" width="70" height="70"/>
              <svg x="50" y="50" width="70" height="70" viewBox="0 0 200 200">
                <rect x="0" y="0" width="200" height="200"/>
              </svg>
            </svg>
        """
        )
        main_group = drawing.contents[0]

        def bounds_in_drawing(shape):
            return Group(shape, transform=main_group.transform).getBounds()

        reference, nested = main_group.contents
        assert bounds_in_drawing(nested) == pytest.approx(bounds_in_drawing(reference))

    def test_old_inkscape_warning(self, caplog):
        """SVGs from Inkscape <0.92 (90 dpi) should log a warning; newer should not."""
        old_svg = """<?xml version="1.0"?>
            <svg xmlns="http://www.w3.org/2000/svg"
                 xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape"
                 inkscape:version="0.91 r13725"
                 width="100" height="100">
              <rect width="100" height="100"/>
            </svg>"""
        new_svg = """<?xml version="1.0"?>
            <svg xmlns="http://www.w3.org/2000/svg"
                 xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape"
                 inkscape:version="0.92.4 (5da689c313, 2019-01-14)"
                 width="100" height="100">
              <rect width="100" height="100"/>
            </svg>"""
        plain_svg = """<?xml version="1.0"?>
            <svg xmlns="http://www.w3.org/2000/svg" width="100" height="100">
              <rect width="100" height="100"/>
            </svg>"""
        import logging

        with caplog.at_level(logging.WARNING, logger="svglib.svglib"):
            drawing_from_svg(old_svg)
        assert any("pre-0.92" in r.message for r in caplog.records)

        caplog.clear()
        with caplog.at_level(logging.WARNING, logger="svglib.svglib"):
            drawing_from_svg(new_svg)
        assert not caplog.records

        with caplog.at_level(logging.WARNING, logger="svglib.svglib"):
            drawing_from_svg(plain_svg)
        assert not caplog.records

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

    def test_image_size_fallback_no_size(self):
        # The embedded image is a 5px x 5px red square.
        drawing = drawing_from_svg(
            """
            <?xml version="1.0"?>
            <svg xmlns="http://www.w3.org/2000/svg"
                 xmlns:xlink="http://www.w3.org/1999/xlink"
                 viewBox="0,0,5,5" width="5" height="5" version="1.1">

                <image id="image-1" xlink:href="data:image/png;base64,iVBORw0KGgoAAAANS
                UhEUgAAAAUAAAAFCAYAAACNbyblAAAACXBIWXMAAAPoAAAD6AG1e1JrAAAAGXRFWHRTb2Z0
                d2FyZQB3d3cuaW5rc2NhcGUub3Jnm+48GgAAABVJREFUCJlj/M/A8J8BDTChC1BBEADOqQI
                IH8PejQAAAABJRU5ErkJggg=="/>
            </svg>
        """
        )

        image = find_image_in_drawing(drawing)

        assert image is not None
        assert image.width == 5
        assert image.height == 5

    def test_image_size_fallback_only_width(self):
        """
        The image size aspect ratio should be preserved. The image is 5px x 10px
        and a width of 3px should scale the height to 6px.
        """
        drawing = drawing_from_svg(
            """
            <?xml version="1.0"?>
            <svg xmlns="http://www.w3.org/2000/svg"
                 xmlns:xlink="http://www.w3.org/1999/xlink"
                 viewBox="0,0,5,5" width="5" height="5" version="1.1">

                <image xlink:href="data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAUAAA
                AKCAYAAAB8OZQwAAAACXBIWXMAAAPoAAAD6AG1e1JrAAAAGXRFWHRTb2Z0d2FyZQB3d3cua
                W5rc2NhcGUub3Jnm+48GgAAABVJREFUCJlj/M/A8J8BDTChCwwlQQCmdgISIETfOwAAAABJ
                RU5ErkJggg==" width="3"/>
            </svg>
        """
        )

        image = find_image_in_drawing(drawing)

        assert image is not None
        assert image.width == 3
        assert image.height == 6

    def test_image_size_fallback_only_height(self):
        """
        The image size aspect ratio should be preserved. The image is 5px x 10px
        and a height of 8px should scale the width to 4px.
        """
        drawing = drawing_from_svg(
            """
            <?xml version="1.0"?>
            <svg xmlns="http://www.w3.org/2000/svg"
                 xmlns:xlink="http://www.w3.org/1999/xlink"
                 viewBox="0,0,5,5" width="5" height="5" version="1.1">

                <image xlink:href="data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAUAAA
                AKCAYAAAB8OZQwAAAACXBIWXMAAAPoAAAD6AG1e1JrAAAAGXRFWHRTb2Z0d2FyZQB3d3cua
                W5rc2NhcGUub3Jnm+48GgAAABVJREFUCJlj/M/A8J8BDTChCwwlQQCmdgISIETfOwAAAABJ
                RU5ErkJggg==" height="8"/>
            </svg>
        """
        )

        image = find_image_in_drawing(drawing)

        assert image is not None
        assert image.width == 4
        assert image.height == 8

    def test_image_with_transform(self):
        """
        This test will ensure that the image transform is correctly applied
        to the image in a single group.
        """
        drawing = drawing_from_svg("""
        <svg version="1.1" viewBox="0 0 50 50" width="50" height="50"
            xmlns:xlink="http://www.w3.org/1999/xlink"
            xmlns="http://www.w3.org/2000/svg"
            xmlns:svg="http://www.w3.org/2000/svg">
            <image x="0" y="0" width="100" height="100" transform="scale(0.5, 0.5)"
            xlink:href="data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAGQAAABkCAYAAA
            Bw4pVUAAAACXBIWXMAAAfPAAAHzwGGUVlPAAAAGXRFWHRTb2Z0d2FyZQB3d3cuaW5rc2NhcG
            Uub3Jnm+48GgAAAQxJREFUeJzt3LENwEAIwEA+++/8qTNBLHQ3Acii5dyZOwucFVvMPH8PwJ
            cgMYLECBIjSIwgMYLECBIjSIwgMYLECBIjSIwgMYLECBIjSIwgMYLECBIjSIwgMYLECBIjSI
            wgMYLECBIjSIwgMYLECBIjSIwgMYLECBIjSIwgMYLECBIjSIwgMYLECBIjSIwgMYLECBIjSM
            yZu+Oj3BYuJEaQGEFiBIkRJEaQGEFiBIkRJEaQGEFiBIkRJEaQGEFiBIkRJEaQGEFiBIkRJE
            aQGEFiBIkRJEaQGEFiBIkRJEaQGEFiBIkRJEaQGEFiBIkRJEaQGEFiBIkRJEaQGEFiBIkRJE
            aQGEFiBIkRJOYFi6UFwwW3DeAAAAAASUVORK5CYII="/>
        </svg>
        """)

        image_group = drawing.contents[0].contents[0]
        assert image_group.transform == (0.5, 0.0, 0.0, -0.5, 0.0, 100.0)

    def test_image_fractional_geometry_not_truncated(self):
        """Fractional <image> geometry must be preserved, not truncated to ints.

        A raster placed at fractional coordinates should land at the same
        position as a vector element with identical coordinates. Truncating
        x/y/width/height to whole points offset the raster by up to ~1pt and,
        because width/height were truncated too, the error grew across the
        image rather than being a constant shift (see issue #490).
        """
        drawing = drawing_from_svg(
            """
            <?xml version="1.0"?>
            <svg xmlns="http://www.w3.org/2000/svg"
                 xmlns:xlink="http://www.w3.org/1999/xlink"
                 width="100" height="100" version="1.1">

                <image x="10.7" y="20.7" width="50.7" height="50.7"
                    xlink:href="data:image/png;base64,iVBORw0KGgoAAAANS
                UhEUgAAAAUAAAAFCAYAAACNbyblAAAACXBIWXMAAAPoAAAD6AG1e1JrAAAAGXRFWHRTb2Z0
                d2FyZQB3d3cuaW5rc2NhcGUub3Jnm+48GgAAABVJREFUCJlj/M/A8J8BDTChC1BBEADOqQI
                IH8PejQAAAABJRU5ErkJggg=="/>
            </svg>
        """
        )

        image = find_image_in_drawing(drawing)

        assert image is not None
        assert image.x == 10.7
        assert image.width == 50.7
        assert image.height == 50.7
        # y is stored flipped as y + height; the enclosing group re-flips it.
        assert image.y == pytest.approx(20.7 + 50.7)
