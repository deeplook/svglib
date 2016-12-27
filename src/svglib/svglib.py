#!/usr/bin/env python
# -*- coding: UTF-8 -*-

"""An experimental library for reading and converting SVG.

This is an experimental converter from SVG to RLG (ReportLab Graphics)
drawings. It converts mainly basic shapes, paths and simple text.
The current intended usage is either as module within other projects:

    from svglib.svglib import svg2rlg
    drawing = svg2rlg("foo.svg")

or from the command-line where right now it is usable as an SVG to PDF
converting tool named sv2pdf (which should also handle SVG files com-
pressed with gzip and extension .svgz).
"""

import copy
import gzip
import logging
import operator
import os
import re
import types
import xml.dom.minidom
from collections import defaultdict
from functools import reduce

from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.pdfgen.canvas import FILL_EVEN_ODD, FILL_NON_ZERO
from reportlab.graphics.shapes import (
    _CLOSEPATH, ArcPath, Circle, Drawing, Ellipse, Group, Image, Line, PolyLine,
    Polygon, Rect, String,
)
from reportlab.graphics import renderPDF
from reportlab.lib import colors
from reportlab.lib.units import cm, inch, mm, pica, toLength

from svg.path import Arc


__version__ = "0.6.3"
__license__ = "LGPL 3"
__author__ = "Dinu Gherman"
__date__ = "2010-03-01"

logger = logging.getLogger(__name__)


### helpers ###

def convertQuadraticToCubicPath(Q0, Q1, Q2):
    "Convert a quadratic Bezier curve through Q0, Q1, Q2 to a cubic one."

    C0 = Q0
    C1 = (Q0[0]+2./3*(Q1[0]-Q0[0]), Q0[1]+2./3*(Q1[1]-Q0[1]))
    C2 = (C1[0]+1./3*(Q2[0]-Q0[0]), C1[1]+1./3*(Q2[1]-Q0[1]))
    C3 = Q2

    return C0, C1, C2, C3


def fixSvgPath(a_list):
    """Normalise certain "abnormalities" in SVG paths.

    Basically, this reduces adjacent number values for h and v
    operators to the sum of these numbers and those for H and V
    operators to the last number only.

    Returns a slightly more compact list if such reductions
    were applied or a copy of the same list, otherwise.
    """

    # this could also modify the path to contain an op code
    # for each coord. tuple of a tuple sequence...

    hPos, vPos, HPos, VPos, numPos = [], [], [], [], []
    for i in xrange(len(a_list)):
        hPos.append(a_list[i]=='h')
        vPos.append(a_list[i]=='v')
        HPos.append(a_list[i]=='H')
        VPos.append(a_list[i]=='V')
        numPos.append(type(a_list[i])==type(1.0))

    fixed_list = []

    i = 0
    while i < len(a_list):
        if hPos[i] + vPos[i] + HPos[i] + VPos[i] == 0:
            fixed_list.append(a_list[i])
        elif hPos[i] == 1 or vPos[i] == 1:
            fixed_list.append(a_list[i])
            sum = 0
            j = i+1
            while j < len(a_list) and numPos[j] == 1:
                sum = sum + a_list[j]
                j = j+1
            fixed_list.append(sum)
            i = j-1
        elif HPos[i] == 1 or VPos[i] == 1:
            fixed_list.append(a_list[i])
            last = 0
            j = i+1
            while j < len(a_list) and numPos[j] == 1:
                last = a_list[j]
                j = j+1
            fixed_list.append(last)
            i = j-1
        i = i+1

    return fixed_list


def split_floats(op, min_num, value):
    """Split `value`, a list of numbers as a string, to a list of float numbers.

    Also optionally insert a `l` or `L` operation depending on the operation
    and the length of values.
    Example: with op='m' and value='10,20 30,40,' the returned value will be
             ['m', [10.0, 20.0], 'l', [30.0, 40.0]]
    """
    floats = [float(seq) for seq in re.findall('(-?\d*\.?\d*(?:e[+-]\d+)?)', value) if seq]
    res = []
    for i in range(0, len(floats), min_num):
        if i > 0 and op in {'m', 'M'}:
            op = 'l' if op == 'm' else 'L'
        res.extend([op, floats[i:i + min_num]])
    return res


def normaliseSvgPath(attr):
    """Normalise SVG path.

    This basically introduces operator codes for multi-argument
    parameters. Also, it fixes sequences of consecutive M or m
    operators to MLLL... and mlll... operators. It adds an empty
    list as argument for Z and z only in order to make the resul-
    ting list easier to iterate over.

    E.g. "M 10 20, M 20 20, L 30 40, 40 40, Z"
      -> ['M', [10, 20], 'L', [20, 20], 'L', [30, 40], 'L', [40, 40], 'Z', []]
    """

    # operator codes mapped to the minimum number of expected arguments
    ops = {'A':7, 'a':7,
      'Q':4, 'q':4, 'T':2, 't':2, 'S':4, 's':4,
      'M':2, 'L':2, 'm':2, 'l':2, 'H':1, 'V':1,
      'h':1, 'v':1, 'C':6, 'c':6, 'Z':0, 'z':0}
    op_keys = ops.keys()

    # do some preprocessing
    result = []
    groups = re.split('([achlmqstvz])', attr.strip(), flags=re.I)
    op = None
    for item in groups:
        if item.strip() == '':
            continue
        if item in op_keys:
            # fix sequences of M to one M plus a sequence of L operators,
            # same for m and l.
            if item == 'M' and item == op:
                op = 'L'
            elif item == 'm' and item == op:
                op = 'l'
            else:
                op = item
            if ops[op] == 0:  # Z, z
                result.extend([op, []])
        else:
            result.extend(split_floats(op, ops[op], item))
            op = result[-2]  # Remember last op

    return result


### attribute converters (from SVG to RLG)

class AttributeConverter:
    "An abstract class to locate and convert attributes in a DOM instance."

    def parseMultiAttributes(self, line):
        """Try parsing compound attribute string.

        Return a dictionary with single attributes in 'line'.
        """

        attrs = line.split(';')
        attrs = [a.strip() for a in attrs]
        attrs = filter(lambda a:len(a)>0, attrs)

        new_attrs = {}
        for a in attrs:
            k, v = a.split(':')
            k, v = [s.strip() for s in (k, v)]
            new_attrs[k] = v

        return new_attrs


    def findAttr(self, svgNode, name):
        """Search an attribute with some name in some node or above.

        First the node is searched, then its style attribute, then
        the search continues in the node's parent node. If no such
        attribute is found, '' is returned.
        """

        # This needs also to lookup values like "url(#SomeName)"...

        attr_value = svgNode.getAttribute(name).strip()

        if attr_value and attr_value != "inherit":
            return attr_value
        elif svgNode.getAttribute("style"):
            dict = self.parseMultiAttributes(svgNode.getAttribute("style"))
            if name in dict:
                return dict[name]
        elif svgNode.parentNode and svgNode.parentNode.nodeType != svgNode.DOCUMENT_NODE:
            return self.findAttr(svgNode.parentNode, name)

        return ''


    def getAllAttributes(self, svgNode):
        "Return a dictionary of all attributes of svgNode or those inherited by it."

        dict = {}

        if svgNode.parentNode and svgNode.parentNode == 'g':
            dict.update(self.getAllAttributes(svgNode.parentNode))

        if svgNode.nodeType == svgNode.ELEMENT_NODE:
            style = svgNode.getAttribute("style")
            if style:
                d = self.parseMultiAttributes(style)
                dict.update(d)

        attrs = svgNode.attributes
        for i in xrange(attrs.length):
            a = attrs.item(i)
            if a.name != "style":
                dict[a.name] = a.value

        return dict


    def id(self, svgAttr):
        "Return attribute as is."

        return svgAttr


    def convertTransform(self, svgAttr):
        """Parse transform attribute string.

        E.g. "scale(2) translate(10,20)"
             -> [("scale", 2), ("translate", (10,20))]
        """

        line = svgAttr.strip()

        ops = line[:]
        brackets = []
        indices = []
        for i, lin in enumerate(line):
            if lin in "()":
                brackets.append(i)
        for i in range(0, len(brackets), 2):
            bi, bj = brackets[i], brackets[i+1]
            subline = line[bi+1:bj]
            subline = subline.strip()
            subline = subline.replace(',', ' ')
            subline = re.sub("[ ]+", ',', subline)
            if ',' in subline:
                indices.append(tuple(float(num) for num in subline.split(',')))
            else:
                indices.append(float(subline))
            ops = ops[:bi] + ' '*(bj-bi+1) + ops[bj+1:]
        ops = ops.split()

        assert len(ops) == len(indices)
        result = []
        for i, op in enumerate(ops):
            result.append((op, indices[i]))

        return result


class Svg2RlgAttributeConverter(AttributeConverter):
    "A concrete SVG to RLG attribute converter."

    def convertLength(self, svgAttr, percentOf=100):
        "Convert length to points."

        text = svgAttr
        if not text:
            return 0.0
        if ' ' in text.replace(',', ' ').strip():
            logger.debug("Only getting first value of %s" % text)
            text = text.replace(',', ' ').split()[0]

        if text.endswith('%'):
            logger.debug("Fiddling length unit: %")
            return float(text[:-1]) / 100 * percentOf
        elif text.endswith("pc"):
            return float(text[:-2]) * pica
        elif text.endswith("pt"):
            return float(text[:-2]) * 1.25

        for unit in ("em", "ex", "px"):
            if unit in text:
                logger.warn("Ignoring unit: %s" % unit)
                text = text.replace(unit, '')

        text = text.strip()
        length = toLength(text)

        return length


    def convertLengthList(self, svgAttr):
        "Convert a list of lengths."

        t = svgAttr.replace(',', ' ')
        t = t.strip()
        t = re.sub("[ ]+", ' ', t)
        a = t.split(' ')

        return [self.convertLength(a) for a in a]


    def convertOpacity(self, svgAttr):
        return float(svgAttr)

    def convertFillRule(self, svgAttr):
        return {
            'nonzero': FILL_NON_ZERO,
            'evenodd': FILL_EVEN_ODD,
        }.get(svgAttr, '')

    def convertColor(self, svgAttr):
        "Convert string to a RL color object."

        # fix it: most likely all "web colors" are allowed
        predefined = "aqua black blue fuchsia gray green lime maroon navy "
        predefined = predefined + "olive orange purple red silver teal white yellow "
        predefined = predefined + "lawngreen indianred aquamarine lightgreen brown"

        # This needs also to lookup values like "url(#SomeName)"...

        text = svgAttr
        if not text or text == "none":
            return None

        if text in predefined.split():
            return getattr(colors, text)
        elif text == "currentColor":
            return "currentColor"
        elif len(text) == 7 and text[0] == '#':
            return colors.HexColor(text)
        elif len(text) == 4 and text[0] == '#':
            return colors.HexColor('#' + 2*text[1] + 2*text[2] + 2*text[3])
        elif text.startswith('rgb') and '%' not in text:
            t = text[3:].strip('()')
            tup = [h[2:] for h in [hex(int(num)) for num in t.split(',')]]
            tup = [(2 - len(h)) * '0' + h for h in tup]
            col = "#%s%s%s" % tuple(tup)
            return colors.HexColor(col)
        elif text.startswith('rgb') and '%' in text:
            t = text[3:].replace('%', '').strip('()')
            tup = (int(val)/100.0 for val in t.split(','))
            return colors.Color(*tup)

        logger.warn("Can't handle color: %s" % text)

        return None


    def convertLineJoin(self, svgAttr):
        return {"miter":0, "round":1, "bevel":2}[svgAttr]


    def convertLineCap(self, svgAttr):
        return {"butt":0, "round":1, "square":2}[svgAttr]


    def convertDashArray(self, svgAttr):
        strokeDashArray = self.convertLengthList(svgAttr)
        return strokeDashArray


    def convertDashOffset(self, svgAttr):
        strokeDashOffset = self.convertLength(svgAttr)
        return strokeDashOffset


    def convertFontFamily(self, svgAttr):
        # very hackish
        font_mapping = {
            "sans-serif":"Helvetica",
            "serif":"Times-Roman",
            "monospace":"Courier"
        }
        font_name = svgAttr
        if not font_name:
            return ''
        try:
            font_name = font_mapping[font_name]
        except KeyError:
            pass
        if font_name not in ("Helvetica", "Times-Roman", "Courier"):
            font_name = "Helvetica"

        return font_name


class NodeTracker:
    """An object wrapper keeping track of arguments to certain method calls.

    Instances wrap an object and store all arguments to one special
    method, getAttribute(name), in a list of unique elements, usedAttrs.
    """

    def __init__(self, anObject):
        self.object = anObject
        self.usedAttrs = []

    def getAttribute(self, name):
        # add argument to the history, if not already present
        if name not in self.usedAttrs:
            self.usedAttrs.append(name)
        # forward call to wrapped object
        return self.object.getAttribute(name)

    # also getAttributeNS(uri, name)?

    def __getattr__(self, name):
        # forward attribute access to wrapped object
        return getattr(self.object, name)


### the main meat ###

class SvgRenderer:
    """Renderer that renders an SVG file on a ReportLab Drawing instance.

    This is the base class for walking over an SVG DOM document and
    transforming it into a ReportLab Drawing instance.
    """

    def __init__(self, path=None):
        self.attrConverter = Svg2RlgAttributeConverter()
        self.shape_converter = Svg2RlgShapeConverter(path)
        self.handled_shapes = self.shape_converter.get_handled_shapes()
        self.drawing = None
        self.mainGroup = Group()
        self.definitions = {}
        self.waiting_use_nodes = defaultdict(list)
        self.origin = [0, 0]
        self.path = path

    def render(self, node, parent=None):
        if parent is None:
            parent = self.mainGroup
        name = node.nodeName

        n = NodeTracker(node)
        nid = n.getAttribute("id")
        ignored = False
        item = None

        if name == "svg":
            drawing = self.renderSvg(n)
            children = n.childNodes
            for child in children:
                if child.nodeType != 1:
                    continue
                self.render(child, self.mainGroup)
        elif name == "defs":
            item = self.renderG(n)
        elif name == 'a':
            item = self.renderA(n)
            parent.add(item)
        elif name == 'g':
            display = n.getAttribute("display")
            if display != "none":
                item = self.renderG(n)
                parent.add(item)
        elif name == "symbol":
            item = self.renderSymbol(n)
            # parent.add(item)
        elif name == "use":
            item = self.renderUse(n)
            parent.add(item)
        elif name in self.handled_shapes:
            method_name = "convert%s" % name.capitalize()
            item = getattr(self.shape_converter, method_name)(n)
            if item:
                self.shape_converter.applyStyleOnShape(item, n)
                transform = n.getAttribute("transform")
                display = n.getAttribute("display")
                if transform and display != "none":
                    if not isinstance(item, Group):
                        gr = Group()
                        gr.add(item)
                        item = gr
                    self.shape_converter.applyTransformOnGroup(transform, item)
                if display != "none":
                    parent.add(item)
        else:
            ignored = True
            logger.debug("Ignoring node: %s" % name)

        if not ignored:
            if nid and item:
                self.definitions[nid] = item
            if nid in self.waiting_use_nodes.keys():
                for use_node, group in self.waiting_use_nodes[nid]:
                    self.renderUse(use_node, group)
            self.print_unused_attributes(node, n)


    def print_unused_attributes(self, node, n):
        if logger.level > logging.DEBUG:
            return
        all_attrs = self.attrConverter.getAllAttributes(node).keys()
        unused_attrs = [attr for attr in all_attrs if attr not in n.usedAttrs]
        if unused_attrs:
            logger.debug("Unused attrs: %s %s" % (n.nodeName, unused_attrs))


    def renderTitle_(self, node):
        # Main SVG title attr. could be used in the PDF document info field.
        pass


    def renderDesc_(self, node):
        # Main SVG desc. attr. could be used in the PDF document info field.
        pass


    def renderSvg(self, node):
        getAttr = node.getAttribute
        width, height = map(getAttr, ("width", "height"))
        width, height = map(self.attrConverter.convertLength, (width, height))
        viewBox = getAttr("viewBox")
        if viewBox:
            viewBox = self.attrConverter.convertLengthList(viewBox)
            x, y, width, height = viewBox
            self.origin = [x, y]
        self.drawing = Drawing(width, height)
        return self.drawing


    def renderG(self, node, display=1):
        getAttr = node.getAttribute
        id, style, transform = map(getAttr, ("id", "style", "transform"))
        #sw = map(getAttr, ("stroke-width",))
        self.attrs = self.attrConverter.parseMultiAttributes(style)
        gr = Group()
        children = node.childNodes
        for child in children:
            if child.nodeType != 1:
                continue
            item = self.render(child, parent=gr)
            if item and display:
                gr.add(item)

        if transform:
            self.shape_converter.applyTransformOnGroup(transform, gr)

        return gr


    def renderSymbol(self, node):
        return self.renderG(node, display=0)


    def renderA(self, node):
        # currently nothing but a group...
        # there is no linking info stored in shapes, maybe a group should?
        return self.renderG(node)


    def renderUse(self, node, group=None):
        if group is None:
            group = Group()

        xlink_href = node.getAttributeNS("http://www.w3.org/1999/xlink", "href")
        if not xlink_href:
            return
        if xlink_href[1:] not in self.definitions:
            # The missing definition should appear later in the file
            self.waiting_use_nodes[xlink_href[1:]].append((node, group))
            return group

        item = copy.deepcopy(self.definitions[xlink_href[1:]])
        group.add(item)
        getAttr = node.getAttribute
        transform = getAttr("transform")
        x, y = map(getAttr, ("x", "y"))
        if x or y:
            transform += " translate(%s, %s)" % (x or '0', y or '0')
        if transform:
            self.shape_converter.applyTransformOnGroup(transform, group)
        self.shape_converter.applyStyleOnShape(item, node, only_explicit=True)
        return group


    def finish(self):
        for xlink in self.waiting_use_nodes.keys():
            logger.debug("Ignoring unavailable object width ID '%s'." % xlink)

        height = self.drawing.height
        self.mainGroup.scale(1, -1)
        self.mainGroup.translate(0 - self.origin[0], -height - self.origin[1])
        self.drawing.add(self.mainGroup)
        return self.drawing


class SvgShapeConverter:
    """An abstract SVG shape converter.

    Implement subclasses with methods named 'renderX(node)', where
    'X' should be the capitalised name of an SVG node element for
    shapes, like 'Rect', 'Circle', 'Line', etc.

    Each of these methods should return a shape object appropriate
    for the target format.
    """
    AttributeConverterClass = AttributeConverter

    def __init__(self, path):
        self.attrConverter = self.AttributeConverterClass()
        self.svg_source_file = path


    @classmethod
    def get_handled_shapes(cls):
        """Dynamically determine a list of handled shape elements based on
           convert<shape> method existence.
        """
        return [key[7:].lower() for key in dir(cls) if key.startswith('convert')]


class Svg2RlgShapeConverter(SvgShapeConverter):
    """Converter from SVG shapes to RLG (ReportLab Graphics) shapes."""

    AttributeConverterClass = Svg2RlgAttributeConverter

    def convertLine(self, node):
        getAttr = node.getAttribute
        x1, y1, x2, y2 = map(getAttr, ("x1", "y1", "x2", "y2"))
        x1, y1, x2, y2 = map(self.attrConverter.convertLength, (x1, y1, x2, y2))
        shape = Line(x1, y1, x2, y2)

        return shape


    def convertRect(self, node):
        getAttr = node.getAttribute
        x, y, width, height = map(getAttr, ('x', 'y', "width", "height"))
        x, y, width, height = map(self.attrConverter.convertLength, (x, y, width, height))
        rx, ry = map(getAttr, ("rx", "ry"))
        rx, ry = map(self.attrConverter.convertLength, (rx, ry))
        shape = Rect(x, y, width, height, rx=rx, ry=ry)

        return shape


    def convertCircle(self, node):
        # not rendered if r == 0, error if r < 0.
        getAttr = node.getAttribute
        cx, cy, r = map(getAttr, ("cx", "cy", 'r'))
        cx, cy, r = map(self.attrConverter.convertLength, (cx, cy, r))
        shape = Circle(cx, cy, r)

        return shape


    def convertEllipse(self, node):
        getAttr = node.getAttribute
        cx, cy, rx, ry = map(getAttr, ("cx", "cy", "rx", "ry"))
        cx, cy, rx, ry = map(self.attrConverter.convertLength, (cx, cy, rx, ry))
        width, height = rx, ry
        shape = Ellipse(cx, cy, width, height)

        return shape


    def convertPolyline(self, node):
        getAttr = node.getAttribute
        points = getAttr("points")
        points = points.replace(',', ' ')
        points = points.split()
        points = list(map(self.attrConverter.convertLength, points))
        if len(points) % 2 != 0 or len(points) == 0:
            # Odd number of coordinates or no coordinates, invalid polyline
            return None

        # Need to use two shapes, because standard RLG polylines
        # do not support filling...
        gr = Group()
        shape = Polygon(points)
        self.applyStyleOnShape(shape, node)
        shape.strokeColor = None
        gr.add(shape)
        shape = PolyLine(points)
        self.applyStyleOnShape(shape, node)
        gr.add(shape)

        return gr


    def convertPolygon(self, node):
        getAttr = node.getAttribute
        points = getAttr("points")
        points = points.replace(',', ' ')
        points = points.split()
        points = list(map(self.attrConverter.convertLength, points))
        if len(points) % 2 != 0 or len(points) == 0:
            # Odd number of coordinates or no coordinates, invalid polygon
            return None
        shape = Polygon(points)

        return shape


    def convertText0(self, node):
        getAttr = node.getAttribute
        x, y = map(getAttr, ('x', 'y'))
        if not x: x = '0'
        if not y: y = '0'
        text = ''
        if node.firstChild.nodeValue:
            text = node.firstChild.nodeValue
        x, y = map(self.attrConv.convertLength, (x, y))
        shape = String(x, y, text)
        self.applyStyleOnShape(shape, node)
        gr = Group()
        gr.add(shape)
        gr.scale(1, -1)
        gr.translate(0, -2*y)

        return gr


    def convertText(self, node):
        attrConv = self.attrConverter
        getAttr = node.getAttribute
        x, y = map(getAttr, ('x', 'y'))
        x, y = map(attrConv.convertLength, (x, y))

        gr = Group()

        text = ''
        chNum = len(node.childNodes)
        frags = []
        fragLengths = []

        dx0, dy0 = 0, 0
        x1, y1 = 0, 0
        ff = attrConv.findAttr(node, "font-family") or "Helvetica"
        ff = attrConv.convertFontFamily(ff)
        fs = attrConv.findAttr(node, "font-size") or "12"
        fs = attrConv.convertLength(fs)
        for c in node.childNodes:
            dx, dy = 0, 0
            baseLineShift = 0
            if c.nodeType == c.TEXT_NODE:
                frags.append(c.nodeValue)
                tx = frags[-1]
            elif c.nodeType == c.ELEMENT_NODE and c.nodeName == "tspan":
                frags.append(c.firstChild.nodeValue)
                tx = frags[-1]
                getAttr = c.getAttribute
                y1 = getAttr('y')
                y1 = attrConv.convertLength(y1)
                dx, dy = map(getAttr, ("dx", "dy"))
                dx, dy = map(attrConv.convertLength, (dx, dy))
                dx0 = dx0 + dx
                dy0 = dy0 + dy
                baseLineShift = getAttr("baseline-shift") or '0'
                if baseLineShift in ("sub", "super", "baseline"):
                    baseLineShift = {"sub":-fs/2, "super":fs/2, "baseline":0}[baseLineShift]
                else:
                    baseLineShift = attrConv.convertLength(baseLineShift, fs)
            elif c.nodeType == c.ELEMENT_NODE and c.nodeName != "tspan":
                continue

            fragLengths.append(stringWidth(tx, ff, fs))
            rl = reduce(operator.__add__, fragLengths[:-1], 0)
            text = frags[-1]
            shape = String(x+rl, y-y1-dy0+baseLineShift, text)
            self.applyStyleOnShape(shape, node)
            if c.nodeType == c.ELEMENT_NODE and c.nodeName == "tspan":
                self.applyStyleOnShape(shape, c)

            gr.add(shape)

        gr.scale(1, -1)
        gr.translate(0, -2*y)

        return gr


    def convertPath(self, node):
        d = node.getAttribute('d')
        normPath = normaliseSvgPath(d)
        path = ArcPath()

        for i in xrange(0, len(normPath), 2):
            op, nums = normPath[i:i+2]

            # moveto absolute
            if op == 'M':
                path.moveTo(*nums)
            # lineto absolute
            elif op == 'L':
                path.lineTo(*nums)

            # moveto relative
            elif op == 'm':
                if len(path.points) >= 2:
                    xn, yn = path.points[-2] + nums[0], path.points[-1] + nums[1]
                    path.moveTo(xn, yn)
                else:
                    path.moveTo(*nums)
            # lineto relative
            elif op == 'l':
                xn, yn = path.points[-2] + nums[0], path.points[-1] + nums[1]
                path.lineTo(xn, yn)

            # horizontal/vertical line absolute
            elif op == 'H':
                path.lineTo(nums[0], path.points[-1])
            elif op == 'V':
                path.lineTo(path.points[-2], nums[0])

            # horizontal/vertical line relative
            elif op == 'h':
                path.lineTo(path.points[-2] + nums[0], path.points[-1])
            elif op == 'v':
                path.lineTo(path.points[-2], path.points[-1] + nums[0])

            # cubic bezier, absolute
            elif op == 'C':
                path.curveTo(*nums)
            elif op == 'S':
                x2, y2, xn, yn = nums
                if len(path.points) < 4:
                    xp, yp, x0, y0 = path.points[-2:] * 2
                else:
                    xp, yp, x0, y0 = path.points[-4:]
                xi, yi = x0 + (x0 - xp), y0 + (y0 - yp)
                path.curveTo(xi, yi, x2, y2, xn, yn)

            # cubic bezier, relative
            elif op == 'c':
                xp, yp = path.points[-2:]
                x1, y1, x2, y2, xn, yn = nums
                path.curveTo(xp + x1, yp + y1, xp + x2, yp + y2, xp + xn, yp + yn)
            elif op == 's':
                if len(path.points) < 4:
                    xp, yp, x0, y0 = path.points[-2:] * 2
                else:
                    xp, yp, x0, y0 = path.points[-4:]
                xi, yi = x0 + (x0 - xp), y0 + (y0 - yp)
                x2, y2, xn, yn = nums
                path.curveTo(xi, yi, x0 + x2, y0 + y2, x0 + xn, y0 + yn)

            # quadratic bezier, absolute
            elif op == 'Q':
                x0, y0 = path.points[-2:]
                x1, y1, xn, yn = nums
                (x0,y0), (x1,y1), (x2,y2), (xn,yn) = \
                    convertQuadraticToCubicPath((x0,y0), (x1,y1), (xn,yn))
                path.curveTo(x1, y1, x2, y2, xn, yn)
            elif op == 'T':
                if len(path.points) < 4:
                    xp, yp, x0, y0 = path.points[-2:] * 2
                else:
                    xp, yp, x0, y0 = path.points[-4:]
                xi, yi = x0 + (x0 - xp), y0 + (y0 - yp)
                xn, yn = nums
                (x0,y0), (x1,y1), (x2,y2), (xn,yn) = \
                    convertQuadraticToCubicPath((x0,y0), (xi,yi), (xn,yn))
                path.curveTo(x1, y1, x2, y2, xn, yn)

            # quadratic bezier, relative
            elif op == 'q':
                x0, y0 = path.points[-2:]
                x1, y1, xn, yn = nums
                x1, y1, xn, yn = x0 + x1, y0 + y1, x0 + xn, y0 + yn
                (x0,y0), (x1,y1), (x2,y2), (xn,yn) = \
                    convertQuadraticToCubicPath((x0,y0), (x1,y1), (xn,yn))
                path.curveTo(x1, y1, x2, y2, xn, yn)
            elif op == 't':
                if len(path.points) < 4:
                    xp, yp, x0, y0 = path.points[-2:] * 2
                else:
                    xp, yp, x0, y0 = path.points[-4:]
                x0, y0 = path.points[-2:]
                xn, yn = nums
                xn, yn = x0 + xn, y0 + yn
                xi, yi = x0 + (x0 - xp), y0 + (y0 - yp)
                (x0,y0), (x1,y1), (x2,y2), (xn,yn) = \
                    convertQuadraticToCubicPath((x0,y0), (xi,yi), (xn,yn))
                path.curveTo(x1, y1, x2, y2, xn, yn)

            # elliptical arc
            elif op in ('A', 'a'):
                start = complex(*path.points[-2:])
                radius = complex(*nums[:2])
                if op == 'a':
                    end = complex(path.points[-2] + nums[-2],
                                  path.points[-1] + nums[-1])
                else:
                    end = complex(*nums[-2:])
                arc = Arc(start, radius, nums[2], nums[3], nums[4], end)
                # Convert from endpoint to center parameterization
                arc._parameterize()
                if arc.sweep:
                    reverse = False
                    start_angle = arc.theta
                    end_angle = start_angle + arc.delta
                else:
                    reverse = True
                    start_angle = arc.theta - 360
                    end_angle = start_angle + arc.delta
                    if arc.delta < 0:
                        start_angle, end_angle = end_angle, start_angle
                path.addArc(arc.center.real, arc.center.imag, arc.radius.real,
                            start_angle, end_angle, yradius=arc.radius.imag, reverse=reverse)

            # close path
            elif op in ('Z', 'z'):
                path.closePath()

            logger.debug("Suspicious path operator: %s" % op)

        # hack because RLG has no "semi-closed" paths...
        gr = Group()
        if path.operators[-1] == _CLOSEPATH:
            self.applyStyleOnShape(path, node)
            sc = self.attrConverter.findAttr(node, "stroke")
            if not sc:
                path.strokeColor = None
            gr.add(path)
        else:
            closed_path = path.copy()
            closed_path.closePath()
            self.applyStyleOnShape(closed_path, node)
            closed_path.strokeColor = None
            gr.add(closed_path)

            self.applyStyleOnShape(path, node)
            path.fillColor = None
            sc = self.attrConverter.findAttr(node, "stroke")
            if not sc:
                path.strokeColor = None
            gr.add(path)

        return gr


    def convertImage(self, node):
        logger.warn("Adding box instead image.")
        getAttr = node.getAttribute
        x, y, width, height = map(getAttr, ('x', 'y', "width", "height"))
        x, y, width, height = map(self.attrConverter.convertLength, (x, y, width, height))
        xlink_href = node.getAttributeNS("http://www.w3.org/1999/xlink", "href")
        xlink_href = os.path.join(os.path.dirname(self.svg_source_file), xlink_href)
        # print "***", x, y, width, height, xlink_href[:30]

        magic = "data:image/jpeg;base64"
        if xlink_href[:len(magic)] == magic:
            pat = "data:image/(\w+?);base64"
            ext = re.match(pat, magic).groups()[0]
            import base64, md5
            jpegData = base64.decodestring(xlink_href[len(magic):])
            hashVal = md5.new(jpegData).hexdigest()
            name = "images/img%s.%s" % (hashVal, ext)
            path = os.path.join(dirname(self.svg_source_file), name)
            open(path, "wb").write(jpegData)
            img = Image(x, y+height, width, -height, path)
            # this needs to be removed later, not here...
            # if exists(path): os.remove(path)
        else:
            xlink_href = os.path.join(os.path.dirname(self.svg_source_file), xlink_href)
            img = Image(x, y+height, width, -height, xlink_href)

        return img


    def applyTransformOnGroup(self, transform, group):
        """Apply an SVG transformation to a RL Group shape.

        The transformation is the value of an SVG transform attribute
        like transform="scale(1, -1) translate(10, 30)".

        rotate(<angle> [<cx> <cy>]) is equivalent to:
          translate(<cx> <cy>) rotate(<angle>) translate(-<cx> -<cy>)
        """

        tr = self.attrConverter.convertTransform(transform)
        for op, values in tr:
            if op == "scale":
                if not isinstance(values, tuple):
                    values = (values, values)
                group.scale(*values)
            elif op == "translate":
                if isinstance(values, (int, float)):
                    # From the SVG spec: If <ty> is not provided, it is assumed to be zero.
                    values = values, 0
                group.translate(*values)
            elif op == "rotate":
                if not isinstance(values, tuple) or len(values) == 1:
                    group.rotate(values)
                elif len(values) == 3:
                    angle, cx, cy = values
                    group.translate(cx, cy)
                    group.rotate(angle)
                    group.translate(-cx, -cy)
            elif op == "skewX":
                group.skew(values, 0)
            elif op == "skewY":
                group.skew(0, values)
            elif op == "matrix":
                group.transform = values
            else:
                logger.debug("Ignoring transform: %s %s" % (op, values))


    def applyStyleOnShape(self, shape, node, only_explicit=False):
        """
        Apply styles from an SVG element to an RLG shape.
        If only_explicit is True, only attributes really present are applied.
        """

        # RLG-specific: all RLG shapes
        "Apply style attributes of a sequence of nodes to an RL shape."

        # tuple format: (svgAttr, rlgAttr, converter, default)
        mappingN = (
            ("fill", "fillColor", "convertColor", "black"),
            ("fill-opacity", "fillOpacity", "convertOpacity", 1),
            ("fill-rule", "_fillRule", "convertFillRule", "nonzero"),
            ("stroke", "strokeColor", "convertColor", "none"),
            ("stroke-width", "strokeWidth", "convertLength", "0"),
            ("stroke-linejoin", "strokeLineJoin", "convertLineJoin", "0"),
            ("stroke-linecap", "strokeLineCap", "convertLineCap", "0"),
            ("stroke-dasharray", "strokeDashArray", "convertDashArray", "none"),
        )
        mappingF = (
            ("font-family", "fontName", "convertFontFamily", "Helvetica"),
            ("font-size", "fontSize", "convertLength", "12"),
            ("text-anchor", "textAnchor", "id", "start"),
        )

        if shape.__class__ == Group:
            # Recursively apply style on Group subelements
            for subshape in shape.contents:
                self.applyStyleOnShape(subshape, node, only_explicit=only_explicit)
            return

        ac = self.attrConverter
        for mapping in (mappingN, mappingF):
            if shape.__class__ != String and mapping == mappingF:
                continue
            for (svgAttrName, rlgAttr, func, default) in mapping:
                svgAttrValue = ac.findAttr(node, svgAttrName)
                if svgAttrValue == '':
                    if only_explicit:
                        continue
                    else:
                        svgAttrValue = default
                if svgAttrValue == "currentColor":
                    svgAttrValue = ac.findAttr(node.parentNode, "color") or default
                try:
                    meth = getattr(ac, func)
                    setattr(shape, rlgAttr, meth(svgAttrValue))
                except Exception:
                    pass
        if getattr(shape, 'fillOpacity', None) is not None and shape.fillColor:
            shape.fillColor.alpha = shape.fillOpacity


def svg2rlg(path):
    "Convert an SVG file to an RLG Drawing object."

    # unzip .svgz file into .svg
    unzipped = False
    if  isinstance(path, str) and os.path.splitext(path)[1].lower() == ".svgz":
        data = gzip.GzipFile(path, "rb").read()
        open(path[:-1], 'w').write(data)
        path = path[:-1]
        unzipped = True

    # load SVG file
    try:
        doc = xml.dom.minidom.parse(path)
        svg = doc.documentElement
    except Exception:
        logger.error("Failed to load input file!")
        return

    # convert to a RLG drawing
    svgRenderer = SvgRenderer(path)
    svgRenderer.render(svg)
    drawing = svgRenderer.finish()

    # remove unzipped .svgz file (.svg)
    if unzipped:
        os.remove(path)

    return drawing


def monkeypatch_reportlab():
    """
    https://bitbucket.org/rptlab/reportlab/issues/95/
    ReportLab always use 'Even-Odd' filling mode for paths, this patch forces
    RL to honor the path fill rule mode (possibly 'Non-Zero Winding') instead.
    """
    from reportlab.pdfgen.canvas import Canvas
    from reportlab.graphics import shapes

    original_renderPath = shapes._renderPath
    def patchedRenderPath(path, drawFuncs):
        # Patched method to transfer fillRule from Path to PDFPathObject
        # Get back from bound method to instance
        try:
            drawFuncs[0].__self__.fillMode = path._fillRule
        except AttributeError:
            pass
        return original_renderPath(path, drawFuncs)
    shapes._renderPath = patchedRenderPath

    original_drawPath = Canvas.drawPath
    def patchedDrawPath(self, path, **kwargs):
        current = self._fillMode
        if hasattr(path, 'fillMode'):
            self._fillMode = path.fillMode
        original_drawPath(self, path, **kwargs)
        self._fillMode = current
    Canvas.drawPath = patchedDrawPath

monkeypatch_reportlab()
