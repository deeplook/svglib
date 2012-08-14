#!/usr/bin/env python

"""Testsuite for svglib.

Some tests try using a tool called uniconv (if installed) 
to convert SVG files into PDF for comparision with svglib.
"""

import os
import sys
import glob
import re
import gzip
import urllib
import httplib
import cStringIO
import tarfile
import pickle
from os.path import splitext, exists, join, basename, getsize
import unittest

from reportlab.lib import colors
from reportlab.lib.units import cm, inch
from reportlab.graphics import renderPDF, renderPM

# import svglib from distribution
sys.path.insert(0, "..")
from svglib import svglib
del sys.path[0]


def testit(func, mapping):
    "Call 'func' on input in mapping and return list of failed tests."
    
    failed = []
    for input, expected in mapping:
        result = func(input)
        if result != expected:
            failed.append((input, result, expected))

    if failed:
        print "failed tests (input, result, expected):"
        for input, result, expected in failed:
            print "  %s : %s != %s" % (repr(input), result, expected)

    return failed
    

class NormBezierPathTestCase(unittest.TestCase):
    "Testing Bezier paths."

    def test0(self):
        "Test path normalisation."

        mapping = (
            ("", 
                []),
                
            ("M10 20, L 30 40 ", 
                ["M", [10, 20], "L", [30, 40]]),
                
            ("M10 20, L 40 40Z",
                ["M", [10, 20], "L", [40, 40], "Z", []]),
                
            ("M10 20, L 30 40 40 40Z",
                ["M", [10, 20], "L", [30, 40], "L", [40, 40], "Z", []]),
                
            ("  M10 20,L30 40,40 40Z  ",
                ["M", [10, 20], "L", [30, 40], "L", [40, 40], "Z", []]),
                
            ("  M 10 20, M 30 40, L 40 40, Z",
                ["M", [10, 20], "L", [30, 40], "L", [40, 40], "Z", []]),
                
            ("  m 10 20, m 30 40, l 40 40, z",
                ["m", [10, 20], "l", [30, 40], "l", [40, 40], "z", []]),
        )
        failed = testit(svglib.normaliseSvgPath, mapping)
        self.failUnlessEqual(len(failed), 0)


class ColorAttrConverterTestCase(unittest.TestCase):
    "Testing color attribute conversion."

    def test0(self):
        "Test color attribute conversion."

        mapping = (
            ("red", colors.red),
            ("#ff0000", colors.red),
            ("#f00", colors.red),
            ("rgb(100%,0%,0%)", colors.red),
        )
        ac = svglib.Svg2RlgAttributeConverter()
        failed = testit(ac.convertColor, mapping)
        self.failUnlessEqual(len(failed), 0)


class LengthAttrConverterTestCase(unittest.TestCase):
    "Testing length attribute conversion."

    def test0(self):
        "Test length attribute conversion."

        mapping = (
            ("0", 0),
            ("316", 316),
            ("-316", -316),
            ("-3.16", -3.16),
            ("-1e-2", -0.01),
            ("1e-5", 1e-5),
            ("1e1cm", 10*cm),
            ("1e1in", 10*inch),
            ("1e1%", 10),
            ("-8e-2cm", (-8e-2)*cm),
        )
        ac = svglib.Svg2RlgAttributeConverter()
        failed = testit(ac.convertLength, mapping)
        self.failUnlessEqual(len(failed), 0)


    def test1(self):
        "Test length attribute conversion."

        ac = svglib.Svg2RlgAttributeConverter()
        attr = "1e1%"
        expected = 1
        obj = ac.convertLength(attr, 10)
        self.failUnlessEqual(obj, expected)


class LengthListAttrConverterTestCase(unittest.TestCase):
    "Testing length attribute conversion."

    def test0(self):
        "Test length list attribute conversion."

        mapping = (
            (" 5cm 5in", [5*cm, 5*inch]),
            (" 5, 5", [5, 5]),
        )
        ac = svglib.Svg2RlgAttributeConverter()
        failed = testit(ac.convertLengthList, mapping)
        self.failUnlessEqual(len(failed), 0)


class TransformAttrConverterTestCase(unittest.TestCase):
    "Testing transform attribute conversion."

    def test0(self):
        "Test transform attribute conversion."

        mapping = (
            ("", 
                []),
            ("scale(2) translate(10,20)", 
                [("scale", 2), ("translate", (10,20))]),
        )
        ac = svglib.Svg2RlgAttributeConverter()
        failed = testit(ac.convertTransform, mapping)
        self.failUnlessEqual(len(failed), 0)


class AttrConverterTestCase(unittest.TestCase):
    "Testing multi-attribute conversion."

    def test0(self):
        "Test multi-attribute conversion."

        mapping = (
            ("fill: black; stroke: yellow", 
                {"fill":"black", "stroke":"yellow"}),
        )
        ac = svglib.Svg2RlgAttributeConverter()
        failed = testit(ac.parseMultiAttributes, mapping)
        self.failUnlessEqual(len(failed), 0)


class SVGSamplesTestCase(unittest.TestCase):
    "Tests on sample SVG files included in svglib test suite."

    def test0(self):
        "Test sample SVG files included in svglib test suite."

        paths = glob.glob("samples/misc/*")
        paths = [p for p in paths 
            if splitext(p.lower())[1] in [".svg", ".svgz"]]
        for i, path in enumerate(paths):            
            print "working on [%d]" % i, path        

            # convert
            try:
                drawing = svglib.svg2rlg(path)
            except:
                print "could not convert [%d]" % i, path
                continue

            # save as PDF
            base = splitext(path)[0] + '-svglib.pdf'
            try:
                renderPDF.drawToFile(drawing, base, showBoundary=0)
            except:
                print "could not save as PDF [%d]" % i, path        


    def _test1(self):
        "Test converting W3C SVG files to PDF using uniconverter."
        # outcommented, because some SVG samples seem to generate errors

        # skip test, if uniconv tool not found
        if not os.popen("which uniconv").read().strip():
            print "Uniconv not found, test skipped."
            return
            
        paths = glob.glob("samples/misc/*.svg")
        for path in paths:
            out = splitext(path)[0] + '-uniconv.pdf'
            cmd = "uniconv '%s' '%s'" % (path, out)
            os.popen(cmd).read()
            if exists(out) and getsize(out) == 0:
                os.remove(out)


class WikipediaSymbolsTestCase(unittest.TestCase):
    "Tests on sample symbol SVG files from wikipedia.org."

    def fetchFile(self, server, path):
        "Fetch file using httplib module."
    
        print "downloading http://%s%s" % (server, path)
            
        req = httplib.HTTP(server)
        req.putrequest('GET', path)
        req.putheader('Host', server)
        req.putheader('Accept', 'text/svg')
        req.endheaders()
        ec, em, h = req.getreply()
        fd = req.getfile()
        data = fd.read()
        
        return data


    def setUp(self):
        "Check if files exists, else download and unpack it."

        self.folderPath = "samples/wikipedia/symbols"

        # create directory if not existing
        if not exists(self.folderPath):
            os.mkdir(self.folderPath)

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
            p = join(os.getcwd(), self.folderPath, basename(path))
            if not exists(p):
                try:
                    data = self.fetchFile(server, path)
                except:
                    print "Check your internet connection and try again!"
                    break
                if data:
                    open(p, "w").write(data)


    def test0(self):
        "Test converting symbol SVG files to PDF using svglib."

        paths = glob.glob("%s/*" % self.folderPath)
        paths = [p for p in paths 
            if splitext(p.lower())[1] in [".svg", ".svgz"]]
        for i, path in enumerate(paths):            
            print "working on [%d]" % i, path        

            # convert
            try:
                drawing = svglib.svg2rlg(path)
            except:
                print "could not convert [%d]" % i, path
                continue

            # save as PDF
            base = splitext(path)[0] + '-svglib.pdf'
            try:
                renderPDF.drawToFile(drawing, base, showBoundary=0)
            except:
                print "could not save as PDF [%d]" % i, path        


    # outcommented
    def _test1(self):
        "Test converting symbol SVG files to PDF using uniconverter."

        # skip test, if uniconv tool not found
        if not os.popen("which uniconv").read().strip():
            print "Uniconv not found, test skipped."
            return

        paths = glob.glob("%s/*" % self.folderPath)
        paths = [p for p in paths 
            if splitext(p.lower())[1] in [".svg", ".svgz"]]
        for path in paths:
            out = splitext(path)[0] + '-uniconv.pdf'
            cmd = "uniconv '%s' '%s'" % (path, out)
            os.popen(cmd).read()
            if exists(out) and getsize(out) == 0:
                os.remove(out)            


class WikipediaFlagsTestCase(unittest.TestCase):
    "Tests using SVG flags from Wikipedia.org."

    def fetchFile(self, url):
        "Get content with some given URL, uncompress if needed."
    
        server, path = urllib.splithost(url[url.find("//"):])
        conn = httplib.HTTPConnection(server)
        conn.request("GET", path)
        r1 = conn.getresponse()
        if (r1.status, r1.reason) == (200, "OK"):
            data = r1.read()
            if r1.getheader("content-encoding") == "gzip":
                zbuf = cStringIO.StringIO(data)
                zfile = gzip.GzipFile(mode="rb", fileobj=zbuf)
                data = zfile.read()
                zfile.close()
        else:
            data = None
    
        return data


    def flagUrl2filename(self, url):
        """Convert given flag URL into a local filename.

        http://upload.wikimedia.org/wikipedia/commons
        /9/91/Flag_of_Bhutan.svg
        -> Bhutan.svg
        /f/fa/Flag_of_the_People%27s_Republic_of_China.svg
        -> The_People's_Republic_of_China.svg
        """

        path = basename(url)[len("Flag_of_"):]
        path = path.capitalize() # capitalise leading "the_"
        path = urllib.unquote(path)

        return path

        
    def setUp(self):
        "Check if files exists, else download."

        self.folderPath = "samples/wikipedia/flags"

        # create directory if not already present
        if not exists(self.folderPath):
            os.mkdir(self.folderPath)

        # fetch flags.html, if not already present
        path = join(self.folderPath, "flags.html")
        if not exists(path):
            u = "http://en.wikipedia.org/wiki/Gallery_of_sovereign_state_flags"
            data = self.fetchFile(u)
            open(path, "w").write(data)
        else:
            data = open(path).read()

        # find all flag base filenames
        # ["Flag_of_Bhutan.svg", "Flag_of_Bhutan.svg", ...]
        flagNames = re.findall("\:(Flag_of_.*?\.svg)", data)
        flagNames = [urllib.unquote(fn) for fn in flagNames]

        # save flag URLs into a pickle file, if not already present
        picklePath = join(self.folderPath, "flags-pickle.txt")
        if not exists(picklePath):            
            flagUrlMap = []
            prefix = "http://en.wikipedia.org/wiki/File:"
            for i in range(len(flagNames)):
                fn = flagNames[i]
                
                # load single flag HTML page, like  
                # http://en.wikipedia.org/wiki/Image:Flag_of_Bhutan.svg
                flagHtml = self.fetchFile(prefix + fn)
    
                # search link to single SVG file to download, like
                # http://upload.wikimedia.org/wikipedia/commons/9/91/Flag_of_Bhutan.svg
                svgPat = "http://upload.wikimedia.org/wikipedia/commons"
                p = "%s/.*?/%s" % (svgPat, urllib.quote(fn))
                print "check", prefix + fn
                
                try:
                    flagUrl = re.search(p, flagHtml)
                except:
                    continue
                if flagUrl:
                    start, end = flagUrl.span()
                    flagUrl = flagHtml[start:end]
                    flagUrlMap.append((prefix + fn, flagUrl))
            pickle.dump(flagUrlMap, open(picklePath, "wb"))

        # download flags in SVG format, if not present already
        flagUrlMap = pickle.load(open(picklePath))
        for dummy, flagUrl in flagUrlMap:
            path = join(self.folderPath, self.flagUrl2filename(flagUrl))
            if not exists(path):
                print "fetch", flagUrl
                flagSvg = self.fetchFile(flagUrl)
                open(path, "w").write(flagSvg)


    def test0(self):
        "Test converting flag SVG files to PDF using svglib."

        paths = glob.glob("%s/*" % self.folderPath)
        paths = [p for p in paths 
            if splitext(p.lower())[1] in [".svg", ".svgz"]]
        for i, path in enumerate(paths):            
            print "working on [%d]" % i, path        

            # convert
            try:
                drawing = svglib.svg2rlg(path)
            except:
                print "could not convert [%d]" % i, path
                continue

            # save as PDF
            base = splitext(path)[0] + '-svglib.pdf'
            try:
                renderPDF.drawToFile(drawing, base, showBoundary=0)
            except:
                print "could not save as PDF [%d]" % i, path        


    # outcommented, because many SVG samples seem to generate errors
    def _test1(self):
        "Test converting flag SVG files to PDF using uniconverer."

        # skip test, if uniconv tool not found
        if not os.popen("which uniconv").read().strip():
            print "Uniconv not found, test skipped."
            return

        paths = glob.glob("%s/*" % self.folderPath)
        paths = [p for p in paths 
            if splitext(p.lower())[1] in [".svg", ".svgz"]]
        for path in paths:
            out = splitext(path)[0] + '-uniconv.pdf'
            cmd = "uniconv '%s' '%s'" % (path, out)
            os.popen(cmd).read()
            if exists(out) and getsize(out) == 0:
                os.remove(out)            


class W3CTestCase(unittest.TestCase):
    "Tests using the official W3C SVG testsuite."

    def setUp(self):
        "Check if testsuite archive exists, else download and unpack it."

        server = "http://www.w3.org"
        path = "/Graphics/SVG/Test/20070907/W3C_SVG_12_TinyTestSuite.tar.gz"
        url = server + path

        archivePath = basename(url)
        tarPath = splitext(archivePath)[0]
        self.folderPath = join("samples", splitext(tarPath)[0])
        
        if not exists(self.folderPath):
            if not exists(join("samples", tarPath)):
                if not exists(join("samples", archivePath)):
                    print "downloading %s" % url
                    try:
                        data = urllib.urlopen(url).read()
                    except IOError, details:
                        print details
                        print "Check your internet connection and try again!"
                        return
                    archivePath = basename(url)
                    open(join("samples", archivePath), "wb").write(data)
                print "unpacking %s" % archivePath
                tarData = gzip.open(join("samples", archivePath), "rb").read()    
                open(join("samples", tarPath), "wb").write(tarData)
            print "extracting into %s" % self.folderPath
            os.mkdir(self.folderPath)
            tarFile = tarfile.TarFile(join("samples", tarPath))
            tarFile.extractall(self.folderPath)
            if exists(join("samples", tarPath)):
                os.remove(join("samples", tarPath))


    def test0(self):
        "Test converting W3C SVG files to PDF using svglib."

        excludeList = [
            "paint-stroke-06-t.svg",
        ]
        
        paths = glob.glob("%s/svg/*.svg" % self.folderPath)
        msg = "Destination folder '%s/svg' not found." % self.folderPath
        self.failUnless(len(paths) > 0, msg)
        
        for i, path in enumerate(paths):
            print "working on [%d]" % i, path        

            if basename(path) in excludeList:
                print "excluded (to be tested later)"
                continue
            
            # convert
            try:
                drawing = svglib.svg2rlg(path)
            except:
                print "could not convert [%d]" % i, path        
                continue

            # save as PDF
            base = splitext(path)[0] + '-svglib.pdf'
            try:
                renderPDF.drawToFile(drawing, base, showBoundary=0)
            except:
                print "could not save as PDF [%d]" % i, path        

            # save as PNG
            # (endless loop for file paint-stroke-06-t.svg)
            base = splitext(path)[0] + '-svglib.png'
            try:
                renderPM.drawToFile(drawing, base, 'PNG')
            except:
                print "could not save as PNG [%d]" % i, path               


    # outcommented, because many SVG samples seem to generate errors
    def _test1(self):
        "Test converting W3C SVG files to PDF using uniconverter."

        # skip test, if uniconv tool not found
        if not os.popen("which uniconv").read().strip():
            print "Uniconv not found, test skipped."
            return
            
        paths = glob.glob("%s/svg/*" % self.folderPath)
        paths = [p for p in paths 
            if splitext(p.lower())[1] in [".svg", ".svgz"]]
        for path in paths:
            out = splitext(path)[0] + '-uniconv.pdf'
            cmd = "uniconv '%s' '%s'" % (path, out)
            os.popen(cmd).read()
            if exists(out) and getsize(out) == 0:
                os.remove(out)


if __name__ == "__main__":
    unittest.main()
