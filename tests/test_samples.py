#!/usr/bin/env python

"""Testsuite for svglib.

This tests conversion of sample SVG files into PDF files.
Some tests try using a tool called uniconv (if installed)
to convert SVG files into PDF for comparision with svglib.

Read ``tests/README.rst`` for more information on testing!
"""

import os
import glob
import re
import gzip
import io
import json
import tarfile
import textwrap
from http.client import HTTPSConnection
from os.path import dirname, splitext, exists, join, basename, getsize
from urllib.parse import quote, unquote, urlparse
from urllib.request import urlopen

from reportlab.lib.utils import haveImages
from reportlab.graphics import renderPDF, renderPM
from reportlab.graphics.shapes import Group, Rect
import pytest

from svglib import svglib


TEST_ROOT = dirname(__file__)


def found_uniconv():
    "Do we have uniconv installed?"

    res = os.popen("which uniconv").read().strip()
    return len(res) > 0


class TestSVGSamples:
    "Tests on misc. sample SVG files included in this test suite."

    def cleanup(self):
        "Remove generated files created by this class."

        paths = glob.glob("%s/samples/misc/*.pdf" % TEST_ROOT)
        for i, path in enumerate(paths):
            print("deleting [%d] %s" % (i, path))
            os.remove(path)

    def test_convert_pdf(self):
        "Test convert sample SVG files to PDF using svglib."

        paths = glob.glob("%s/samples/misc/*" % TEST_ROOT)
        paths = [p for p in paths if splitext(p.lower())[1] in [".svg", ".svgz"]]
        for i, path in enumerate(paths):
            print("working on [%d] %s" % (i, path))

            # convert
            drawing = svglib.svg2rlg(path)

            # save as PDF
            base = splitext(path)[0] + '-svglib.pdf'
            renderPDF.drawToFile(drawing, base, showBoundary=0)

    @pytest.mark.skipif(not found_uniconv(), reason="needs uniconv")
    def test_create_pdf_uniconv(self):
        "Test converting sample SVG files to PDF using uniconverter."

        paths = glob.glob("%s/samples/misc/*.svg" % TEST_ROOT)
        for path in paths:
            out = splitext(path)[0] + '-uniconv.pdf'
            cmd = "uniconv '%s' '%s'" % (path, out)
            os.popen(cmd).read()
            if exists(out) and getsize(out) == 0:
                os.remove(out)


class TestWikipediaSymbols:
    "Tests on sample symbol SVG files from wikipedia.org."

    def fetch_file(self, server, path):
        "Fetch file using httplib module."

        print("downloading https://%s%s" % (server, path))

        req = HTTPSConnection(server)
        req.putrequest('GET', path)
        req.putheader('Host', server)
        req.putheader('Accept', 'text/svg')
        req.endheaders()
        r1 = req.getresponse()
        data = r1.read().decode('utf-8')
        req.close()

        return data

    def setup_method(self):
        "Check if files exists, else download and unpack it."

        self.folder_path = "%s/samples/wikipedia/symbols" % TEST_ROOT

        # create directory if not existing
        if not exists(self.folder_path):
            os.mkdir(self.folder_path)

        # list sample files, found on:
        # http://en.wikipedia.org/wiki/List_of_symbols
        server = "upload.wikimedia.org"
        paths = textwrap.dedent("""\
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
        """).strip().split()

        # convert
        for path in paths:
            data = None
            p = join(os.getcwd(), self.folder_path, basename(path))
            if not exists(p):
                try:
                    data = self.fetch_file(server, path)
                except Exception:
                    print("Check your internet connection and try again!")
                    break
                if data:
                    with io.open(p, "w", encoding='UTF-8') as fh:
                        fh.write(data)

    def cleanup(self):
        "Remove generated files when running this test class."

        paths = glob.glob(join(self.folder_path, '*.pdf'))
        for i, path in enumerate(paths):
            print("deleting [%d] %s" % (i, path))
            os.remove(path)

    def test_convert_pdf(self):
        "Test converting symbol SVG files to PDF using svglib."

        paths = glob.glob("%s/*" % self.folder_path)
        paths = [p for p in paths if splitext(p.lower())[1] in [".svg", ".svgz"]]
        for i, path in enumerate(paths):
            print("working on [%d] %s" % (i, path))

            # convert
            drawing = svglib.svg2rlg(path)

            # save as PDF
            base = splitext(path)[0] + '-svglib.pdf'
            renderPDF.drawToFile(drawing, base, showBoundary=0)

    @pytest.mark.skipif(not found_uniconv(), reason="needs uniconv")
    def test_convert_pdf_uniconv(self):
        "Test converting symbol SVG files to PDF using uniconverter."

        paths = glob.glob("%s/*" % self.folder_path)
        paths = [p for p in paths if splitext(p.lower())[1] in [".svg", ".svgz"]]
        for path in paths:
            out = splitext(path)[0] + '-uniconv.pdf'
            cmd = "uniconv '%s' '%s'" % (path, out)
            os.popen(cmd).read()
            if exists(out) and getsize(out) == 0:
                os.remove(out)


class TestWikipediaFlags:
    "Tests using SVG flags from Wikipedia.org."

    def fetch_file(self, url):
        "Get content with some given URL, uncompress if needed."

        parsed = urlparse(url)
        conn = HTTPSConnection(parsed.netloc)
        conn.request("GET", parsed.path)
        r1 = conn.getresponse()
        if (r1.status, r1.reason) == (200, "OK"):
            data = r1.read()
            if r1.getheader("content-encoding") == "gzip":
                zbuf = io.BytesIO(data)
                zfile = gzip.GzipFile(mode="rb", fileobj=zbuf)
                data = zfile.read()
                zfile.close()
            data = data.decode('utf-8')
        else:
            data = None
        conn.close()

        return data

    def flag_url2filename(self, url):
        """Convert given flag URL into a local filename.

        http://upload.wikimedia.org/wikipedia/commons
        /9/91/Flag_of_Bhutan.svg
        -> Bhutan.svg
        /f/fa/Flag_of_the_People%27s_Republic_of_China.svg
        -> The_People's_Republic_of_China.svg
        """

        path = basename(url)[len("Flag_of_"):]
        path = path.capitalize()  # capitalise leading "the_"
        path = unquote(path)

        return path

    def setup_method(self):
        "Check if files exists, else download."

        self.folder_path = "%s/samples/wikipedia/flags" % TEST_ROOT

        # create directory if not already present
        if not exists(self.folder_path):
            os.mkdir(self.folder_path)

        # fetch flags.html, if not already present
        path = join(self.folder_path, "flags.html")
        if not exists(path):
            u = "https://en.wikipedia.org/wiki/Gallery_of_sovereign_state_flags"
            data = self.fetch_file(u)
            if data:
                with io.open(path, "w", encoding='UTF-8') as f:
                    f.write(data)
        else:
            with io.open(path, 'r', encoding='UTF-8') as f:
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
                flag_html = self.fetch_file(prefix + quote(fn))

                # search link to single SVG file to download, like
                # https://upload.wikimedia.org/wikipedia/commons/9/91/Flag_of_Bhutan.svg
                svg_pat = "//upload.wikimedia.org/wikipedia/commons"
                p = r"(%s/.*?/%s)\"" % (svg_pat, quote(fn))
                print("check %s" % prefix + fn)

                m = re.search(p, flag_html)
                if m:
                    flag_url = m.groups()[0]
                    flag_url_map.append((prefix + fn, flag_url))
            with io.open(json_path, "w", encoding='UTF-8') as fh:
                json.dump(flag_url_map, fh)

        # download flags in SVG format, if not present already
        with io.open(json_path, "r", encoding='UTF-8') as fh:
            flag_url_map = json.load(fh)
        for dummy, flag_url in flag_url_map:
            path = join(self.folder_path, self.flag_url2filename(flag_url))
            if not exists(path):
                print("fetch %s" % flag_url)
                flag_svg = self.fetch_file(flag_url)
                with io.open(path, "w", encoding='UTF-8') as f:
                    f.write(flag_svg)

    def cleanup(self):
        "Remove generated files when running this test class."

        paths = glob.glob(join(self.folder_path, '*.pdf'))
        for i, path in enumerate(paths):
            print("deleting [%d] %s" % (i, path))
            os.remove(path)

    def test_convert_pdf(self):
        "Test converting flag SVG files to PDF using svglib."

        paths = glob.glob("%s/*" % self.folder_path)
        paths = [p for p in paths if splitext(p.lower())[1] in [".svg", ".svgz"]]
        for i, path in enumerate(paths):
            print("working on [%d] %s" % (i, path))

            # convert
            drawing = svglib.svg2rlg(path)

            # save as PDF
            base = splitext(path)[0] + '-svglib.pdf'
            renderPDF.drawToFile(drawing, base, showBoundary=0)

    @pytest.mark.skipif(not found_uniconv(), reason="needs uniconv")
    def test_convert_pdf_uniconv(self):
        "Test converting flag SVG files to PDF using uniconverer."

        paths = glob.glob("%s/*" % self.folder_path)
        paths = [p for p in paths if splitext(p.lower())[1] in [".svg", ".svgz"]]
        for path in paths:
            out = splitext(path)[0] + '-uniconv.pdf'
            cmd = "uniconv '%s' '%s'" % (path, out)
            os.popen(cmd).read()
            if exists(out) and getsize(out) == 0:
                os.remove(out)


class TestW3CSVG:
    "Tests using the official W3C SVG testsuite."

    def setup_method(self):
        "Check if testsuite archive exists, else download and unpack it."

        server = "http://www.w3.org"
        path = "/Graphics/SVG/Test/20070907/W3C_SVG_12_TinyTestSuite.tar.gz"
        url = server + path

        archive_path = basename(url)
        tar_path = splitext(archive_path)[0]
        self.folder_path = join(TEST_ROOT, "samples", splitext(tar_path)[0])
        if not exists(self.folder_path):
            if not exists(join(TEST_ROOT, "samples", tar_path)):
                if not exists(join(TEST_ROOT, "samples", archive_path)):
                    print("downloading %s" % url)
                    try:
                        data = urlopen(url).read()
                    except IOError as details:
                        print(details)
                        print("Check your internet connection and try again!")
                        return
                    archive_path = basename(url)
                    with open(join(TEST_ROOT, "samples", archive_path), "wb") as f:
                        f.write(data)
                print("unpacking %s" % archive_path)
                tar_data = gzip.open(join(TEST_ROOT, "samples", archive_path), "rb").read()
                with open(join(TEST_ROOT, "samples", tar_path), "wb") as f:
                    f.write(tar_data)
            print("extracting into %s" % self.folder_path)
            os.mkdir(self.folder_path)
            tar_file = tarfile.TarFile(join(TEST_ROOT, "samples", tar_path))
            tar_file.extractall(self.folder_path)
            tar_file.close()
            if exists(join(TEST_ROOT, "samples", tar_path)):
                os.remove(join(TEST_ROOT, "samples", tar_path))

    def cleanup(self):
        "Remove generated files when running this test class."

        paths = glob.glob(join(self.folder_path, 'svg/*-svglib.pdf'))
        paths += glob.glob(join(self.folder_path, 'svg/*-uniconv.pdf'))
        paths += glob.glob(join(self.folder_path, 'svg/*-svglib.png'))
        for i, path in enumerate(paths):
            print("deleting [%d] %s" % (i, path))
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

        paths = glob.glob("%s/svg/*.svg" % self.folder_path)
        msg = "Destination folder '%s/svg' not found." % self.folder_path
        assert len(paths) > 0, msg

        for i, path in enumerate(paths):
            print("working on [%d] %s" % (i, path))

            if basename(path) in exclude_list:
                print("excluded (to be tested later)")
                continue

            # convert
            drawing = svglib.svg2rlg(path)

            # save as PDF
            base = splitext(path)[0] + '-svglib.pdf'
            renderPDF.drawToFile(drawing, base, showBoundary=0)

            # save as PNG
            # (endless loop for file paint-stroke-06-t.svg)
            base = splitext(path)[0] + '-svglib.png'
            try:
                # Can trigger an error in reportlab < 3.3.26.
                renderPM.drawToFile(drawing, base, 'PNG')
            except TypeError:
                print('Svglib: Consider upgrading reportlab to version >= 3.3.26!')
                raise

    @pytest.mark.skipif(not found_uniconv(), reason="needs uniconv")
    def test_convert_pdf_uniconv(self):
        "Test converting W3C SVG files to PDF using uniconverter."

        paths = glob.glob("%s/svg/*" % self.folder_path)
        paths = [p for p in paths if splitext(p.lower())[1] in [".svg", ".svgz"]]
        for path in paths:
            out = splitext(path)[0] + '-uniconv.pdf'
            cmd = "uniconv '%s' '%s'" % (path, out)
            os.popen(cmd).read()
            if exists(out) and getsize(out) == 0:
                os.remove(out)


class TestOtherFiles:
    @pytest.mark.skipif(not haveImages, reason="missing pillow library")
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
