#!/usr/bin/env python

"""Testsuite for svglib.

This tests basic functionality. Run with one of these lines from
inside the test directory:

    py.test -v -s test_basic.py
"""

import sys
import io

from reportlab.lib import colors
from reportlab.lib.units import cm, inch

# import svglib from distribution
sys.path.insert(0, "..")
from svglib import svglib
del sys.path[0]


def _testit(func, mapping):
    "Call 'func' on input in mapping and return list of failed tests."
    
    failed = []
    for input, expected in mapping:
        result = func(input)
        if not result == expected:
            failed.append((input, result, expected))

    if failed:
        print("failed tests (input, result, expected):")
        for input, result, expected in failed:
            print("  %s : %s != %s" % (repr(input), result, expected))

    return failed
    

class TestNormBezierPathTestCase(object):
    "Testing Bezier paths."

    def test_0(self):
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
                
            ("  M 10 20, M 30 40, L 40 40, Z M 40 50, l 50 60, Z",
                ["M", [10, 20], "L", [30, 40], "L", [40, 40], "Z", [],
                 "M", [40, 50], "l", [50, 60], "Z", []]),
                
            ("  m 10 20, m 30 40, l 40 40, z",
                ["m", [10, 20], "l", [30, 40], "l", [40, 40], "z", []]),

            ("  m 10,20 30,40, l 40 40, z ",
                ["m", [10, 20], "l", [30, 40], "l", [40, 40], "z", []]),

            ("M 10,20 30,40, l 40 40, z",
                ["M", [10, 20], "L", [30, 40], "l", [40, 40], "z", []]),

            ("M0,0 500,300M500,0 0,300",
                ["M", [0, 0], "L", [500, 300], "M", [500, 0], "L", [0, 300]]),

            ("M10 20, l 5e-5,0",
                ["M", [10, 20], "l", [5e-5, 0]]),

            ("m246.026 120.178c-.558-.295-1.186-.768-1.395-1.054-.314-.438-.132-.456 1.163-.104 "
             "2.318.629 3.814.383 5.298-.873l1.308-1.103 1.54.784c.848.428 1.748.725 "
             "2.008.656.667-.176 2.05-1.95 2.005-2.564-.054-.759.587-.568.896.264.615 1.631-.281 "
             "3.502-1.865 3.918-.773.201-1.488.127-2.659-.281-1.438-.502-1.684-.494-2.405.058-1.618 "
             "1.239-3.869 1.355-5.894.299z",
                ['m', [246.026, 120.178], 'c', [-0.558, -0.295, -1.186, -0.768, -1.395, -1.054],
                 'c', [-0.314, -0.438, -0.132, -0.456, 1.163, -0.104],
                 'c', [2.318, 0.629, 3.814, 0.383, 5.298, -0.873],
                 'l', [1.308, -1.103], 'l', [1.54, 0.784],
                 'c', [0.848, 0.428, 1.748, 0.725, 2.008, 0.656],
                 'c', [0.667, -0.176, 2.05, -1.95, 2.005, -2.564],
                 'c', [-0.054, -0.759, 0.587, -0.568, 0.896, 0.264],
                 'c', [0.615, 1.631, -0.281, 3.502, -1.865, 3.918],
                 'c', [-0.773, 0.201, -1.488, 0.127, -2.659, -0.281],
                 'c', [-1.438, -0.502, -1.684, -0.494, -2.405, 0.058],
                 'c', [-1.618, 1.239, -3.869, 1.355, -5.894, 0.299],
                 'z', []
                ]),
        )
        failed = _testit(svglib.normaliseSvgPath, mapping)
        assert len(failed) == 0


class TestColorAttrConverterTestCase(object):
    "Testing color attribute conversion."

    def test_0(self):
        "Test color attribute conversion."

        mapping = (
            ("red", colors.red),
            ("#ff0000", colors.red),
            ("#f00", colors.red),
            ("rgb(100%,0%,0%)", colors.red),
        )
        ac = svglib.Svg2RlgAttributeConverter()
        failed = _testit(ac.convertColor, mapping)
        assert len(failed) == 0


class TestLengthAttrConverterTestCase(object):
    "Testing length attribute conversion."

    def test_0(self):
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
        failed = _testit(ac.convertLength, mapping)
        assert len(failed) == 0


    def test_1(self):
        "Test length attribute conversion."

        ac = svglib.Svg2RlgAttributeConverter()
        attr = "1e1%"
        expected = 1
        obj = ac.convertLength(attr, 10)
        assert obj == expected


class TestLengthListAttrConverterTestCase(object):
    "Testing length attribute conversion."

    def test_0(self):
        "Test length list attribute conversion."

        mapping = (
            (" 5cm 5in", [5*cm, 5*inch]),
            (" 5, 5", [5, 5]),
        )
        ac = svglib.Svg2RlgAttributeConverter()
        failed = _testit(ac.convertLengthList, mapping)
        assert len(failed) == 0


class TestTransformAttrConverterTestCase(object):
    "Testing transform attribute conversion."

    def test_0(self):
        "Test transform attribute conversion."

        mapping = (
            ("", 
                []),
            ("scale(2) translate(10,20)", 
                [("scale", 2), ("translate", (10,20))]),
        )
        ac = svglib.Svg2RlgAttributeConverter()
        failed = _testit(ac.convertTransform, mapping)
        assert len(failed) == 0


class TestAttrConverterTestCase(object):
    "Testing multi-attribute conversion."

    def test_0(self):
        "Test multi-attribute conversion."

        mapping = (
            ("fill: black; stroke: yellow", 
                {"fill":"black", "stroke":"yellow"}),
        )
        ac = svglib.Svg2RlgAttributeConverter()
        failed = _testit(ac.parseMultiAttributes, mapping)
        assert len(failed) == 0

    def test_no_fill_on_shape(self):
        """
        Any shape with no fill property should set black color in rlg syntax.
        """
        drawing = svglib.svg2rlg(io.StringIO(
u'''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="800" viewBox="0 0 36 24">
<rect y="10" width="36" height="4"/>
</svg>'''
        ))
        assert drawing.contents[0].contents[0].fillColor == colors.black


class TestUseNode(object):
    def test_use(self):
        drawing = svglib.svg2rlg(io.StringIO(
u'''<?xml version="1.0"?>
<svg width="10cm" height="3cm" viewBox="0 0 100 30" version="1.1"
     xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink">
  <defs>
    <rect id="MyRect" width="60" height="10"/>
  </defs>
  <rect x=".1" y=".1" width="99.8" height="29.8"
        fill="none" stroke="blue" stroke-width=".2" />
  <use x="20" y="10" xlink:href="#MyRect" />
</svg>'''
        ))
        # First Rect
        assert drawing.contents[0].contents[1].__class__.__name__ == 'Rect'
        # Second Rect defined by the use node (inside a Group)
        assert drawing.contents[0].contents[2].contents[0].__class__.__name__ ==  'Rect'

    def test_transform_inherited_by_use(self):
        drawing = svglib.svg2rlg(io.StringIO(
u'''<?xml version="1.0"?>
<svg version="1.1" width="900" height="600" xmlns:xlink="http://www.w3.org/1999/xlink">
  <g id="c">
    <path id="t" d="M 0,-100 V 0 H 50" transform="rotate(18 0,-100)"/>
    <use xlink:href="#t" transform="scale(-1,1)"/>
  </g>
</svg>'''
        ))
        cgroup_node = drawing.contents[0].contents[0]
        assert (
            cgroup_node.contents[0].transform == cgroup_node.contents[1].contents[0].transform
        ), "The transform of the original path is different from the transform of the reused path."
