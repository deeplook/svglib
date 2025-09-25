"""Testsuite for svglib.

This module tests conversion of sample SVG files into PDF files.
Some tests try using a tool called uniconv (if installed)
to convert SVG files into PDF for comparision with svglib.

Run with one of these lines from inside the test directory:

    $ make test
    $ uv run pytest -v -s test_samples.py
"""

import glob
import gzip
import io
import json
import os
import re
import tarfile
import textwrap
from http.client import HTTPSConnection
from os.path import basename, dirname, exists, getsize, join, splitext
from typing import Any
from urllib.parse import quote, unquote, urlparse

import pytest
from reportlab.graphics import renderPDF, renderPM
from reportlab.graphics.shapes import Group, Rect

from svglib import svglib

TEST_ROOT = dirname(__file__)


def found_uniconv() -> bool:
    "Do we have uniconv installed?"

    res = os.popen("which uniconv").read().strip()
    return len(res) > 0


def fetch_file(
    url: str,
    mime_accept: str = "text/svg",
    uncompress: bool = True,
    raise_exc: bool = False,
) -> Any:
    """
    Get given URL content using http.client module, uncompress if needed and
    `uncompress` is True.
    """

    parsed = urlparse(url)
    conn = HTTPSConnection(parsed.netloc)
    conn.request(
        "GET",
        parsed.path,
        headers={
            "Host": parsed.netloc,
            "Accept": mime_accept,
            "User-Agent": "Python/http.client",
        },
    )
    response = conn.getresponse()
    if (response.status, response.reason) == (200, "OK"):
        data: Any = response.read()
        content_type = response.getheader("content-type")
        if (
            uncompress
            and (
                response.getheader("content-encoding") == "gzip"
                or (content_type is not None and "gzip" in content_type)
            )
            and data[:2] == b"\x1f\x8b"
        ):
            with gzip.open(io.BytesIO(data), mode="rb") as zfile:
                data = zfile.read()
        if "text" in mime_accept:
            data = data.decode("utf-8")
    else:
        if raise_exc:
            conn.close()
            raise Exception(
                f"Unable to fetch file {url}, got {response.status} response "
                f"({response.reason})"
            )
        data = None
    conn.close()

    return data


class TestSVGSamples:
    "Tests on misc. sample SVG files included in this test suite."

    def cleanup(self):
        "Remove generated files created by this class."

        paths = glob.glob(f"{TEST_ROOT}/samples/misc/*.pdf")
        for i, path in enumerate(paths):
            print(f"deleting [{i}] {path}")
            os.remove(path)

    def test_convert_pdf(self):
        "Test convert sample SVG files to PDF using svglib."

        paths = glob.glob(f"{TEST_ROOT}/samples/misc/*")
        paths = [p for p in paths if splitext(p.lower())[1] in [".svg", ".svgz"]]
        for i, path in enumerate(paths):
            print(f"working on [{i}] {path}")

            # convert
            drawing = svglib.svg2rlg(path)

            # save as PDF
            base = splitext(path)[0] + "-svglib.pdf"
            renderPDF.drawToFile(drawing, base, showBoundary=0)

    @pytest.mark.skipif(not found_uniconv(), reason="needs uniconv")
    def test_create_pdf_uniconv(self):
        "Test converting sample SVG files to PDF using uniconverter."

        paths = glob.glob(f"{TEST_ROOT}/samples/misc/*.svg")
        for path in paths:
            out = splitext(path)[0] + "-uniconv.pdf"
            cmd = f"uniconv '{path}' '{out}'"
            os.popen(cmd).read()
            if exists(out) and getsize(out) == 0:
                os.remove(out)


class TestWikipediaSymbols:
    "Tests on sample symbol SVG files from wikipedia.org."

    def setup_method(self):
        "Check if files exists, else download and unpack it."

        self.folder_path = f"{TEST_ROOT}/samples/wikipedia/symbols"

        # create directory if not existing
        if not exists(self.folder_path):
            os.mkdir(self.folder_path)

        # list sample files, found on:
        # http://en.wikipedia.org/wiki/List_of_symbols
        server = "upload.wikimedia.org"
        paths = (
            textwrap.dedent(
                """\
            /wikipedia/commons/f/f7/Biohazard.svg
            /wikipedia/commons/1/11/No_smoking_symbol.svg
            /wikipedia/commons/b/b0/Dharma_wheel.svg
            /wikipedia/commons/a/a7/Eye_of_Horus_bw.svg
            /wikipedia/commons/1/17/Yin_yang.svg
            /wikipedia/commons/a/a7/Olympic_flag.svg
            /wikipedia/commons/4/46/Ankh.svg
            /wikipedia/commons/5/5b/Star_of_life2.svg
            /wikipedia/commons/9/97/Tudor_rose.svg
            /wikipedia/commons/0/08/Flower-of-Life-small.svg
            /wikipedia/commons/d/d0/Countries_by_Population_Density_in_2015.svg
            /wikipedia/commons/8/84/CO2_responsibility_1950-2000.svg
        """
            )
            .strip()
            .split()
        )

        # convert
        for path in paths:
            data = None
            p = join(os.getcwd(), self.folder_path, basename(path))
            if not exists(p):
                try:
                    data = fetch_file(f"https://{server}{path}")
                except Exception:
                    print("Check your internet connection and try again!")
                    break
                if data:
                    with open(p, "w", encoding="UTF-8") as fh:
                        fh.write(data)

    def cleanup(self):
        "Remove generated files when running this test class."

        paths = glob.glob(join(self.folder_path, "*.pdf"))
        for i, path in enumerate(paths):
            print(f"deleting [{i}] {path}")
            os.remove(path)

    def test_convert_pdf(self):
        "Test converting symbol SVG files to PDF using svglib."

        paths = glob.glob(f"{self.folder_path}/*")
        paths = [p for p in paths if splitext(p.lower())[1] in [".svg", ".svgz"]]
        for i, path in enumerate(paths):
            print(f"working on [{i}] {path}")

            # convert
            drawing = svglib.svg2rlg(path)

            # save as PDF
            base = splitext(path)[0] + "-svglib.pdf"
            renderPDF.drawToFile(drawing, base, showBoundary=0)

    @pytest.mark.skipif(not found_uniconv(), reason="needs uniconv")
    def test_convert_pdf_uniconv(self):
        "Test converting symbol SVG files to PDF using uniconverter."

        paths = glob.glob(f"{self.folder_path}/*")
        paths = [p for p in paths if splitext(p.lower())[1] in [".svg", ".svgz"]]
        for path in paths:
            out = splitext(path)[0] + "-uniconv.pdf"
            cmd = f"uniconv '{path}' '{out}'"
            os.popen(cmd).read()
            if exists(out) and getsize(out) == 0:
                os.remove(out)


class TestWikipediaFlags:
    "Tests using SVG flags from Wikipedia.org."

    def flag_url2filename(self, url):
        """Convert given flag URL into a local filename.

        http://upload.wikimedia.org/wikipedia/commons
        /9/91/Flag_of_Bhutan.svg
        -> Bhutan.svg
        /f/fa/Flag_of_the_People%27s_Republic_of_China.svg
        -> The_People's_Republic_of_China.svg
        """

        path = basename(url)[len("Flag_of_") :]
        path = path.capitalize()  # capitalise leading "the_"
        path = unquote(path)

        return path

    def setup_method(self):
        "Check if files exists, else download."

        self.folder_path = f"{TEST_ROOT}/samples/wikipedia/flags"

        # create directory if not already present
        if not exists(self.folder_path):
            os.mkdir(self.folder_path)

        # fetch flags.html, if not already present
        path = join(self.folder_path, "flags.html")
        if not exists(path):
            u = "https://en.wikipedia.org/wiki/Gallery_of_sovereign_state_flags"
            data = fetch_file(u)
            if data:
                with open(path, "w", encoding="UTF-8") as f:
                    f.write(data)
        else:
            with open(path, encoding="UTF-8") as f:
                data = f.read()

        # find all flag base filenames
        # ["Flag_of_Bhutan.svg", "Flag_of_Bhutan.svg", ...]
        flag_names = re.findall(r"\:(Flag_of_.*?\.svg)", data)
        flag_names = [unquote(fn) for fn in flag_names]

        # save flag URLs into a JSON file, if not already present
        json_path = join(self.folder_path, "flags.json")
        if not exists(json_path):
            flag_url_map = []
            prefix = "https://en.wikipedia.org/wiki/File:"
            for i, fn in enumerate(flag_names):
                # load single flag HTML page, like
                # https://en.wikipedia.org/wiki/Image:Flag_of_Bhutan.svg
                flag_html = fetch_file(prefix + quote(fn))

                # search link to single SVG file to download, like
                # https://upload.wikimedia.org/wikipedia/commons/9/91/Flag_of_Bhutan.svg
                svg_pat = "//upload.wikimedia.org/wikipedia/commons"
                p = rf"({svg_pat}/.*?/{quote(fn)})\""
                print(f"check {prefix}{fn}")

                m = re.search(p, flag_html)
                if m:
                    flag_url = m.groups()[0]
                    flag_url_map.append((prefix + fn, flag_url))
            with open(json_path, "w", encoding="UTF-8") as fh:
                json.dump(flag_url_map, fh)

        # download flags in SVG format, if not present already
        with open(json_path, encoding="UTF-8") as fh:
            flag_url_map = json.load(fh)
        for dummy, flag_url in flag_url_map:
            path = join(self.folder_path, self.flag_url2filename(flag_url))
            if not exists(path):
                print(f"fetch {flag_url}")
                flag_svg = fetch_file(flag_url, raise_exc=True)
                with open(path, "w", encoding="UTF-8") as f:
                    f.write(flag_svg)

    def cleanup(self):
        "Remove generated files when running this test class."

        paths = glob.glob(join(self.folder_path, "*.pdf"))
        for i, path in enumerate(paths):
            print(f"deleting [{i}] {path}")
            os.remove(path)

    def test_convert_pdf(self):
        "Test converting flag SVG files to PDF using svglib."

        paths = glob.glob(f"{self.folder_path}/*")
        paths = [p for p in paths if splitext(p.lower())[1] in [".svg", ".svgz"]]
        for i, path in enumerate(paths):
            print(f"working on [{i}] {path}")

            # convert
            drawing = svglib.svg2rlg(path)

            # save as PDF
            base = splitext(path)[0] + "-svglib.pdf"
            renderPDF.drawToFile(drawing, base, showBoundary=0)

    @pytest.mark.skipif(not found_uniconv(), reason="needs uniconv")
    def test_convert_pdf_uniconv(self):
        "Test converting flag SVG files to PDF using uniconverer."

        paths = glob.glob(f"{self.folder_path}/*")
        paths = [p for p in paths if splitext(p.lower())[1] in [".svg", ".svgz"]]
        for path in paths:
            out = splitext(path)[0] + "-uniconv.pdf"
            cmd = f"uniconv '{path}' '{out}'"
            os.popen(cmd).read()
            if exists(out) and getsize(out) == 0:
                os.remove(out)


class TestW3CSVG:
    "Tests using the official W3C SVG testsuite."

    def setup_method(self):
        "Check if testsuite archive exists, else download and unpack it."

        server = "https://www.w3.org"
        path = "/Graphics/SVG/Test/20070907/W3C_SVG_12_TinyTestSuite.tar.gz"
        url = server + path

        archive_path = basename(url)
        tar_path = splitext(archive_path)[0]
        self.folder_path = join(TEST_ROOT, "samples", splitext(tar_path)[0])
        if not exists(self.folder_path):
            print(f"downloading {url}")
            try:
                data = fetch_file(url, mime_accept="application/gzip", uncompress=True)
            except OSError as details:
                print(details)
                print("Check your internet connection and try again!")
                return
            with open(join(TEST_ROOT, "samples", tar_path), "wb") as f:
                f.write(data)
            print(f"extracting into {self.folder_path}")
            os.mkdir(self.folder_path)
            tar_file = tarfile.TarFile(join(TEST_ROOT, "samples", tar_path))
            tar_file.extractall(self.folder_path)
            tar_file.close()
            if exists(join(TEST_ROOT, "samples", tar_path)):
                os.remove(join(TEST_ROOT, "samples", tar_path))

    def cleanup(self):
        "Remove generated files when running this test class."

        paths = glob.glob(join(self.folder_path, "svg/*-svglib.pdf"))
        paths += glob.glob(join(self.folder_path, "svg/*-uniconv.pdf"))
        paths += glob.glob(join(self.folder_path, "svg/*-svglib.png"))
        for i, path in enumerate(paths):
            print(f"deleting [{i}] {path}")
            os.remove(path)

    def test_convert_pdf_png(self):
        """
        Test converting W3C SVG files to PDF and PNG using svglib.

        ``renderPM.drawToFile()`` used in this test is known to trigger an
        error sometimes in reportlab which was fixed in reportlab 3.3.26.
        See https://github.com/deeplook/svglib/issues/47
        """

        exclude_list = [
            "animate-elem-41-t.svg",  # Freeze renderPM in pathFill()
            "animate-elem-78-t.svg",  # id
            "paint-stroke-06-t.svg",
            "paint-stroke-207-t.svg",
            "coords-trans-09-t.svg",  # renderPDF issue (div by 0)
        ]

        paths = glob.glob(f"{self.folder_path}/svg/*.svg")
        msg = f"Destination folder '{self.folder_path}/svg' not found."
        assert len(paths) > 0, msg

        for i, path in enumerate(paths):
            print(f"working on [{i}] {path}")

            if basename(path) in exclude_list:
                print("excluded (to be tested later)")
                continue

            # convert
            drawing = svglib.svg2rlg(path)

            # save as PDF
            base = splitext(path)[0] + "-svglib.pdf"
            renderPDF.drawToFile(drawing, base, showBoundary=0)

            # save as PNG
            # (endless loop for file paint-stroke-06-t.svg)
            base = splitext(path)[0] + "-svglib.png"
            try:
                # Can trigger an error in reportlab < 3.3.26.
                renderPM.drawToFile(drawing, base, "PNG")
            except TypeError:
                print("Svglib: Consider upgrading reportlab to version >= 3.3.26!")
                raise

    @pytest.mark.skipif(not found_uniconv(), reason="needs uniconv")
    def test_convert_pdf_uniconv(self):
        "Test converting W3C SVG files to PDF using uniconverter."

        paths = glob.glob(f"{self.folder_path}/svg/*")
        paths = [p for p in paths if splitext(p.lower())[1] in [".svg", ".svgz"]]
        for path in paths:
            out = splitext(path)[0] + "-uniconv.pdf"
            cmd = f"uniconv '{path}' '{out}'"
            os.popen(cmd).read()
            if exists(out) and getsize(out) == 0:
                os.remove(out)


class TestOtherFiles:
    def test_png_in_svg(self):
        path = join(TEST_ROOT, "samples", "others", "png_in_svg.svg")
        drawing = svglib.svg2rlg(path)
        result = renderPDF.drawToString(drawing)
        # If the PNG image is really included, the size is over 7k.
        assert len(result) > 7000

    def test_external_svg_in_svg(self):
        path = join(TEST_ROOT, "samples", "others", "svg_in_svg.svg")
        drawing = svglib.svg2rlg(path)
        img_group = drawing.contents[0].contents[0]
        # First image points to SVG rendered as a group
        assert isinstance(img_group.contents[0], Group)
        assert isinstance(img_group.contents[0].contents[0].contents[0], Rect)
        assert img_group.contents[0].transform, (1, 0, 0, 1, 200.0, 100.0)
        # Second image points directly to a Group with Rect element
        assert isinstance(img_group.contents[1], Group)
        assert isinstance(img_group.contents[1].contents[0], Rect)
        assert img_group.contents[1].transform, (1, 0, 0, 1, 100.0, 200.0)

    def test_units_svg(self):
        path = join(TEST_ROOT, "samples", "others", "units.svg")
        drawing = svglib.svg2rlg(path)
        unit_widths = [line.getBounds()[0] for line in drawing.contents[0].contents]
        assert unit_widths == sorted(unit_widths)
        unit_names = ["px", "pt", "mm", "ex", "ch", "em", "pc", "cm"]
        lengths_by_name = dict(zip(unit_names, unit_widths))
        assert lengths_by_name["px"] == lengths_by_name["pt"] * 0.75
        assert lengths_by_name["em"] == svglib.DEFAULT_FONT_SIZE  # 1 em == font size
        assert lengths_by_name["ex"] == lengths_by_name["em"] / 2
        assert lengths_by_name["ch"] == lengths_by_name["ex"]

    def test_empty_style(self):
        path = join(TEST_ROOT, "samples", "others", "empty_style.svg")
        svglib.svg2rlg(path)

    def test_convert_quadratic_to_cubic(self):
        path = join(TEST_ROOT, "samples", "others", "quadratic_path.svg")
        svg_root = svglib.load_svg_file(path, resolve_entities=False)
        renderer = svglib.SvgRenderer(path)
        drawing = renderer.render(svg_root)
        cubic_path = (
            "M 0 5 C 0 8.333333 1.666667 10 5 10 C 8.333333 10 10 8.333333 10 5 C 10 "
            "1.666667 8.333333 0 5 0 C 1.666667 0 0 1.666667 0 5 Z"
        )
        assert cubic_path in drawing.asString("svg")
