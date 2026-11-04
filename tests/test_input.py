"""Conversion of the different kinds of SVG sources (svg2rlg input)."""

import gzip
import io
import os
import pathlib
import textwrap
from tempfile import NamedTemporaryFile

import pytest
from PIL import Image as PILImage
from reportlab.graphics import renderPDF

from svglib import svglib
from tests.utils import find_image_in_drawing


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

    @pytest.mark.parametrize("suffix", [".svgz", ".SVGZ"])
    @pytest.mark.parametrize("path_type", [str, pathlib.Path])
    def test_svgz_preserves_sibling_svg(self, tmp_path, suffix, path_type):
        source = tmp_path / f"drawing{suffix}"
        source.write_bytes(gzip.compress(self.test_content.encode()))
        compressed = source.read_bytes()
        sibling = source.with_suffix(suffix[:-1])
        sibling.write_bytes(b"an independent SVG file")

        drawing = svglib.svg2rlg(path_type(source))

        assert drawing is not None
        assert drawing.contents
        assert sibling.exists()
        assert sibling.read_bytes() == b"an independent SVG file"
        assert source.read_bytes() == compressed

    def test_svgz_invalid_xml_leaves_no_intermediate(self, tmp_path):
        source = tmp_path / "invalid.svgz"
        source.write_bytes(gzip.compress(b"not an XML document"))

        assert svglib.svg2rlg(source) is None
        assert list(tmp_path.iterdir()) == [source]

    def test_svgz_resolves_relative_image(self, tmp_path, monkeypatch):
        source_dir = tmp_path / "source"
        source_dir.mkdir()
        PILImage.new("RGB", (2, 2), (12, 34, 56)).save(source_dir / "pixel.png")
        source = source_dir / "drawing.svgz"
        source.write_bytes(
            gzip.compress(
                b'<svg xmlns="http://www.w3.org/2000/svg" width="4" height="4">'
                b'<image href="pixel.png" width="4" height="4"/></svg>'
            )
        )
        monkeypatch.chdir(tmp_path)

        drawing = svglib.svg2rlg(source)

        assert drawing is not None
        image = find_image_in_drawing(drawing)
        assert image is not None
        with PILImage.open(image.path) as pixels:
            assert pixels.getpixel((0, 0)) == (12, 34, 56)
        assert renderPDF.drawToString(drawing).startswith(b"%PDF-")
        assert not source.with_suffix(".svg").exists()
