#!/usr/bin/env python

"""Testsuite for svglib.

This tests conversion of sample SVG files into PDF files.
Some tests try using a tool called uniconv (if installed) 
to convert SVG files into PDF for comparision with svglib.

Run with one of these lines from inside the test directory:

    py.test -v -s test_samples.py

The following needs pytest 3.0.5 and will run functions that
are named `cleanup` only:

    py.test -v -s --override-ini=python_functions=cleanup
"""

import os
import sys
import glob
import re
import gzip
import io
import json
import tarfile
from os.path import splitext, exists, join, basename, getsize
try:
    from httplib import HTTPSConnection  # PY2
except ImportError:
    from http.client import HTTPSConnection  # PY3
try:
    from urllib import quote, unquote, urlopen  # PY2
    from urlparse import urlparse
except ImportError:
    from urllib.parse import quote, unquote, urlparse  # PY3
    from urllib.request import urlopen

from reportlab.lib import colors
from reportlab.lib.units import cm, inch
from reportlab.graphics import renderPDF, renderPM
import pytest

# import svglib from distribution
sys.path.insert(0, "..")
from svglib import svglib
del sys.path[0]


def found_uniconv():
    "Do we have uniconv installed?"

    res = os.popen("which uniconv").read().strip()
    return len(res) > 0


class TestSVGSamples(object):
    "Tests on sample SVG files included in svglib test suite."

    def cleanup(self):
        "Remove generated files when running this test class."

        paths = glob.glob("samples/misc/*.pdf")
        for i, path in enumerate(paths):
            print("deleting [%d] %s" % (i, path))
            os.remove(path)


    def test_0(self):
        "Test sample SVG files included in svglib test suite."

        paths = glob.glob("samples/misc/*")
        paths = [p for p in paths 
            if splitext(p.lower())[1] in [".svg", ".svgz"]]
        for i, path in enumerate(paths):            
            print("working on [%d] %s" % (i, path))

            # convert
            try:
                drawing = svglib.svg2rlg(path)
            except:
                print("could not convert [%d]" % i, path)
                continue

            # save as PDF
            base = splitext(path)[0] + '-svglib.pdf'
            try:
                renderPDF.drawToFile(drawing, base, showBoundary=0)
            except:
                print("could not save as PDF [%d] %s" % (i, path))


    @pytest.mark.skipif(not found_uniconv(), reason="needs uniconv")
    def test_1(self):
        "Test converting W3C SVG files to PDF using uniconverter."

        paths = glob.glob("samples/misc/*.svg")
        for path in paths:
            out = splitext(path)[0] + '-uniconv.pdf'
            cmd = "uniconv '%s' '%s'" % (path, out)
            os.popen(cmd).read()
            if exists(out) and getsize(out) == 0:
                os.remove(out)


class TestWikipediaSymbols(object):
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

        self.folder_path = "samples/wikipedia/symbols"

        # create directory if not existing
        if not exists(self.folder_path):
            os.mkdir(self.folder_path)

        # list sample files, found on:
        # http://en.wikipedia.org/wiki/List_of_symbols
        server = "upload.wikimedia.org"
        paths = """\
/wikipedia/commons/f/f7/Biohazard.svg
/wikipedia/commons/1/11/No_smoking_symbol.svg
/wikipedia/commons/b/b0/Dharma_wheel.svg
/wikipedia/commons/a/a7/Eye_of_Horus_bw.svg
/wikipedia/commons/1/17/Yin_yang.svg
/wikipedia/commons/a/a7/Olympic_flag.svg
/wikipedia/commons/4/46/Ankh.svg
/wikipedia/commons/5/5b/Star_of_life2.svg
/wikipedia/commons/9/97/Tudor_rose.svg""".split()

        # convert
        for path in paths:
            url = server + path
            data = None
            p = join(os.getcwd(), self.folder_path, basename(path))
            if not exists(p):
                try:
                    data = self.fetch_file(server, path)
                except:
                    print("Check your internet connection and try again!")
                    break
                if data:
                    with open(p, "w") as fh:
                        fh.write(data)


    def cleanup(self):
        "Remove generated files when running this test class."

        paths = glob.glob(join(self.folder_path, '*.pdf'))
        for i, path in enumerate(paths):
            print("deleting [%d] %s" % (i, path))
            os.remove(path)


    def test_0(self):
        "Test converting symbol SVG files to PDF using svglib."

        paths = glob.glob("%s/*" % self.folder_path)
        paths = [p for p in paths 
            if splitext(p.lower())[1] in [".svg", ".svgz"]]
        for i, path in enumerate(paths):            
            print("working on [%d] %s" % (i, path))

            # convert
            drawing = svglib.svg2rlg(path)

            # save as PDF
            base = splitext(path)[0] + '-svglib.pdf'
            renderPDF.drawToFile(drawing, base, showBoundary=0)

    @pytest.mark.skipif(not found_uniconv(), reason="needs uniconv")
    def test_1(self):
        "Test converting symbol SVG files to PDF using uniconverter."

        paths = glob.glob("%s/*" % self.folder_path)
        paths = [p for p in paths 
            if splitext(p.lower())[1] in [".svg", ".svgz"]]
        for path in paths:
            out = splitext(path)[0] + '-uniconv.pdf'
            cmd = "uniconv '%s' '%s'" % (path, out)
            os.popen(cmd).read()
            if exists(out) and getsize(out) == 0:
                os.remove(out)            


class TestWikipediaFlags(object):
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
        path = path.capitalize() # capitalise leading "the_"
        path = unquote(path)

        return path

        
    def setup_method(self):
        "Check if files exists, else download."

        self.folder_path = "samples/wikipedia/flags"

        # create directory if not already present
        if not exists(self.folder_path):
            os.mkdir(self.folder_path)

        # fetch flags.html, if not already present
        path = join(self.folder_path, "flags.html")
        if not exists(path):
            u = "https://en.wikipedia.org/wiki/Gallery_of_sovereign_state_flags"
            data = self.fetch_file(u)
            if data:
                open(path, "w").write(data)
        else:
            data = open(path).read()

        # find all flag base filenames
        # ["Flag_of_Bhutan.svg", "Flag_of_Bhutan.svg", ...]
        flag_names = re.findall("\:(Flag_of_.*?\.svg)", data)
        flag_names = [unquote(fn) for fn in flag_names]

        # save flag URLs into a JSON file, if not already present
        json_path = join(self.folder_path, "flags.json")
        if not exists(json_path):
            flag_url_map = []
            prefix = "https://en.wikipedia.org/wiki/File:"
            for i in range(len(flag_names)):
                fn = flag_names[i]
                
                # load single flag HTML page, like  
                # https://en.wikipedia.org/wiki/Image:Flag_of_Bhutan.svg
                flag_html = self.fetch_file(prefix + quote(fn))
    
                # search link to single SVG file to download, like
                # https://upload.wikimedia.org/wikipedia/commons/9/91/Flag_of_Bhutan.svg
                svgPat = "//upload.wikimedia.org/wikipedia/commons"
                p = "%s/.*?/%s" % (svgPat, quote(fn))
                print("check %s" % prefix + fn)
                
                flag_url = re.search(p, flag_html)
                if flag_url:
                    start, end = flag_url.span()
                    flag_url = flag_html[start:end]
                    flag_url_map.append((prefix + fn, flag_url))
            with open(json_path, "w") as fh:
                json.dump(flag_url_map, fh)

        # download flags in SVG format, if not present already
        with open(json_path, "r") as fh:
            flag_url_map = json.load(fh)
        for dummy, flag_url in flag_url_map:
            path = join(self.folder_path, self.flag_url2filename(flag_url))
            if not exists(path):
                print("fetch %s" % flag_url)
                flag_svg = self.fetch_file(flag_url)
                open(path, "w").write(flag_svg)


    def cleanup(self):
        "Remove generated files when running this test class."

        paths = glob.glob(join(self.folder_path, '*.pdf'))
        for i, path in enumerate(paths):
            print("deleting [%d] %s" % (i, path))
            os.remove(path)


    def test_0(self):
        "Test converting flag SVG files to PDF using svglib."

        paths = glob.glob("%s/*" % self.folder_path)
        paths = [p for p in paths 
            if splitext(p.lower())[1] in [".svg", ".svgz"]]
        for i, path in enumerate(paths):            
            print("working on [%d] %s" % (i, path))

            # convert
            drawing = svglib.svg2rlg(path)

            # save as PDF
            base = splitext(path)[0] + '-svglib.pdf'
            renderPDF.drawToFile(drawing, base, showBoundary=0)


    @pytest.mark.skipif(not found_uniconv(), reason="needs uniconv")
    def test_1(self):
        "Test converting flag SVG files to PDF using uniconverer."

        paths = glob.glob("%s/*" % self.folder_path)
        paths = [p for p in paths 
            if splitext(p.lower())[1] in [".svg", ".svgz"]]
        for path in paths:
            out = splitext(path)[0] + '-uniconv.pdf'
            cmd = "uniconv '%s' '%s'" % (path, out)
            os.popen(cmd).read()
            if exists(out) and getsize(out) == 0:
                os.remove(out)            


class TestW3CTestCase(object):
    "Tests using the official W3C SVG testsuite."

    def setup_method(self):
        "Check if testsuite archive exists, else download and unpack it."

        server = "http://www.w3.org"
        path = "/Graphics/SVG/Test/20070907/W3C_SVG_12_TinyTestSuite.tar.gz"
        url = server + path

        archive_path = basename(url)
        tar_path = splitext(archive_path)[0]
        self.folder_path = join("samples", splitext(tar_path)[0])
        
        if not exists(self.folder_path):
            if not exists(join("samples", tar_path)):
                if not exists(join("samples", archive_path)):
                    print("downloading %s" % url)
                    try:
                        data = urlopen(url).read()
                    except IOError as details:
                        print(details)
                        print("Check your internet connection and try again!")
                        return
                    archive_path = basename(url)
                    open(join("samples", archive_path), "wb").write(data)
                print("unpacking %s" % archive_path)
                tar_data = gzip.open(join("samples", archive_path), "rb").read()
                open(join("samples", tar_path), "wb").write(tar_data)
            print("extracting into %s" % self.folder_path)
            os.mkdir(self.folder_path)
            tar_file = tarfile.TarFile(join("samples", tar_path))
            tar_file.extractall(self.folder_path)
            if exists(join("samples", tar_path)):
                os.remove(join("samples", tar_path))


    def cleanup(self):
        "Remove generated files when running this test class."

        paths = glob.glob(join(self.folder_path, 'svg/*.pdf'))
        for i, path in enumerate(paths):
            print("deleting [%d] %s" % (i, path))
            os.remove(path)


    def test_0(self):
        "Test converting W3C SVG files to PDF using svglib."

        exclude_list = [
            "paint-stroke-06-t.svg",
            "coords-trans-09-t.svg",  # renderPDF issue (div by 0)
            # ExpatError while parsing due to the ev namespace
            "interact-order-04-t.svg",
            "interact-order-05-t.svg",
            "media-video-220-t.svg",
            "script-listener-201-t.svg",
            # Unsupported 'transform="ref(svg, ...)"' expression
            "coords-constr-201-t.svg",
            "coords-constr-202-t.svg",
            "coords-constr-203-t.svg",
            "coords-constr-204-t.svg",
            # Errors to be investigated
            "paint-grad-201-t.svg",
            "media-alevel-201-t.svg",
            "media-alevel-202-t.svg",
            "udom-event-207-t.svg",
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
            renderPM.drawToFile(drawing, base, 'PNG')

    @pytest.mark.skipif(not found_uniconv(), reason="needs uniconv")
    def test_1(self):
        "Test converting W3C SVG files to PDF using uniconverter."

        paths = glob.glob("%s/svg/*" % self.folder_path)
        paths = [p for p in paths 
            if splitext(p.lower())[1] in [".svg", ".svgz"]]
        for path in paths:
            out = splitext(path)[0] + '-uniconv.pdf'
            cmd = "uniconv '%s' '%s'" % (path, out)
            os.popen(cmd).read()
            if exists(out) and getsize(out) == 0:
                os.remove(out)
