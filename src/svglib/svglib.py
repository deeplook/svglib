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

import sys
import os
import glob
import types
import re
import operator
import gzip
import xml.dom.minidom
from functools import reduce

from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.graphics.shapes import (
    _CLOSEPATH, Circle, Drawing, Ellipse, Group, Image, Line, Path, PolyLine,
    Polygon, Rect, String,
)
from reportlab.graphics import renderPDF
from reportlab.lib import colors
from reportlab.lib.units import cm, inch, mm, pica, toLength


__version__ = "0.6.3"
__license__ = "LGPL 3"
__author__ = "Dinu Gherman"
__date__ = "2010-03-01"


pt = 1
LOGMESSAGES = 0


### helpers ###

def convertQuadraticToCubicPath(Q0, Q1, Q2):
    "Convert a quadratic Bezier curve through Q0, Q1, Q2 to a cubic one."

    C0 = Q0
    C1 = (Q0[0]+2./3*(Q1[0]-Q0[0]), Q0[1]+2./3*(Q1[1]-Q0[1]))
    C2 = (C1[0]+1./3*(Q2[0]-Q0[0]), C1[1]+1./3*(Q2[1]-Q0[1]))
    C3 = Q2

    return C0, C1, C2, C3


def fixSvgPath(aList):
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
    for i in xrange(len(aList)):
        hPos.append(aList[i]=='h')
        vPos.append(aList[i]=='v')
        HPos.append(aList[i]=='H')
        VPos.append(aList[i]=='V')
        numPos.append(type(aList[i])==type(1.0))

    fixedList = []

    i = 0
    while i < len(aList):
        if hPos[i] + vPos[i] + HPos[i] + VPos[i] == 0:
            fixedList.append(aList[i])
        elif hPos[i] == 1 or vPos[i] == 1:
            fixedList.append(aList[i])
            sum = 0
            j = i+1
            while j < len(aList) and numPos[j] == 1:
                sum = sum + aList[j]
                j = j+1
            fixedList.append(sum)
            i = j-1
        elif HPos[i] == 1 or VPos[i] == 1:
            fixedList.append(aList[i])
            last = 0
            j = i+1
            while j < len(aList) and numPos[j] == 1:
                last = aList[j]
                j = j+1
            fixedList.append(last)
            i = j-1
        i = i+1

    return fixedList


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

        newAttrs = {}
        for a in attrs:
            k, v = a.split(':')
            k, v = [s.strip() for s in (k, v)]
            newAttrs[k] = v

        return newAttrs


    def findAttr(self, svgNode, name):
        """Search an attribute with some name in some node or above.

        First the node is searched, then its style attribute, then
        the search continues in the node's parent node. If no such
        attribute is found, '' is returned. 
        """

        # This needs also to lookup values like "url(#SomeName)"...    

        try:
            attrValue = svgNode.getAttribute(name)
        except:
            return ''

        if attrValue and attrValue != "inherit":
            return attrValue
        elif svgNode.getAttribute("style"):
            dict = self.parseMultiAttributes(svgNode.getAttribute("style"))
            if name in dict:
                return dict[name]
        else:
            if svgNode.parentNode:
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
        for i in range(len(line)):
           if line[i] in "()": brackets.append(i)
        for i in range(0, len(brackets), 2):
            bi, bj = brackets[i], brackets[i+1]
            subline = line[bi+1:bj]
            subline = subline.strip()
            subline = subline.replace(',', ' ')
            subline = re.sub("[ ]+", ',', subline)
            indices.append(eval(subline))
            ops = ops[:bi] + ' '*(bj-bi+1) + ops[bj+1:]
        ops = ops.split()

        assert len(ops) == len(indices)
        result = []
        for i in range(len(ops)):
            result.append((ops[i], indices[i]))

        return result


class Svg2RlgAttributeConverter(AttributeConverter):
    "A concrete SVG to RLG attribute converter."

    def convertLength(self, svgAttr, percentOf=100):
        "Convert length to points."

        text = svgAttr
        if not text:
            return 0.0
        if ' ' in text.replace(',', ' ').strip():
            if LOGMESSAGES:
                print("Only getting first value of %s" % text)
            text = text.replace(',', ' ').split()[0]

        if text[-1] == '%':
            if LOGMESSAGES:
                print("Fiddling length unit: %")
            return float(text[:-1]) / 100 * percentOf
        elif text[-2:] == "pc":
            return float(text[:-2]) * pica

        newSize = text[:]
        for u in "em ex px".split():
            if newSize.find(u) >= 0:
                if LOGMESSAGES:
                    print("Ignoring unit: %s" % u)
                newSize = newSize.replace(u, '')

        newSize = newSize.strip()
        length = toLength(newSize)

        return length


    def convertLengthList(self, svgAttr):
        "Convert a list of lengths."

        t = svgAttr.replace(',', ' ')
        t = t.strip()
        t = re.sub("[ ]+", ' ', t)
        a = t.split(' ')

        return [self.convertLength(a) for a in a]


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
        elif text[:3] == "rgb" and text.find('%') < 0:
            t = text[:][3:]
            t = t.replace('%', '')
            tup = eval(t)
            tup = [h[2:] for h in [hex(t) for t in tup]]
            tup = [(2 - len(h)) * '0' + h for h in tup]
            col = "#%s%s%s" % tuple(tup)
            return colors.HexColor(col)
        elif text[:3] == 'rgb' and text.find('%') >= 0:
            t = text[:][3:]
            t = t.replace('%', '')
            tup = eval(t)
            tup = [c/100.0 for c in tup]
            return colors.Color(*tup)

        if LOGMESSAGES:
            print("Can't handle color: %s" % text)

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
        fontMapping = {"sans-serif":"Helvetica", 
                       "serif":"Times-Roman", 
                       "monospace":"Courier"}
        fontName = svgAttr
        if not fontName:
            return ''
        try:
            fontName = fontMapping[fontName]
        except KeyError:
            pass
        if fontName not in ("Helvetica", "Times-Roman", "Courier"):
            fontName = "Helvetica"

        return fontName


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
        self.shapeConverter = Svg2RlgShapeConverter()
        self.shapeConverter.svgSourceFile = path
        self.handledShapes = self.shapeConverter.getHandledShapes()
        self.drawing = None
        self.mainGroup = Group()
        self.definitions = {}
        self.verbose = 0
        self.level = 0
        self.path = path
        self.logFile = None
        #if self.path:
        #    logPath = os.path.splitext(self.path)[0] + ".log"
        #    self.logFile = open(logPath, 'w')


    def render(self, node, parent=None):
        if parent is None:
            parent = self.mainGroup
        name = node.nodeName
        if self.verbose:
            format = "%s%s"
            args = ('  '*self.level, name)
            #if not self.logFile:
            #    print format % args
            #else:
            #    self.logFile.write((format+"\n") % args)

        n = NodeTracker(node)
        nid = n.getAttribute("id")
        ignored = False
        item = None

        if name == "svg":
            self.level = self.level + 1
            drawing = self.renderSvg(n)
            children = n.childNodes
            for child in children:
                if child.nodeType != 1:
                    continue
                self.render(child, self.mainGroup)
            self.level = self.level - 1
        elif name == "defs":
            self.level = self.level + 1
            item = self.renderG(n)
            parent.add(item)
            self.level = self.level - 1
        elif name == 'a':
            self.level = self.level + 1
            item = self.renderA(n)
            parent.add(item)
            self.level = self.level - 1
        elif name == 'g':
            self.level = self.level + 1
            display = n.getAttribute("display")
            if display != "none":
                item = self.renderG(n)
                parent.add(item)
            self.level = self.level - 1
        elif name == "symbol":
            self.level = self.level + 1
            item = self.renderSymbol(n)
            # parent.add(item)
            self.level = self.level - 1
        elif name == "use":
            self.level = self.level + 1
            item = self.renderUse(n)
            if item:
                parent.add(item)
            self.level = self.level - 1
        elif name in self.handledShapes:
            methodName = "convert"+name[0].upper()+name[1:]
            item = getattr(self.shapeConverter, methodName)(n)
            if item:
                self.shapeConverter.applyStyleOnShape(item, n)
                transform = n.getAttribute("transform")
                display = n.getAttribute("display")
                if transform and display != "none": 
                    gr = Group()
                    self.shapeConverter.applyTransformOnGroup(transform, gr)
                    gr.add(item)
                    parent.add(gr)
                    item = gr
                elif display != "none":
                    parent.add(item)
        else:
            ignored = True
            if LOGMESSAGES:
                print("Ignoring node: %s" % name)
        if not ignored:
            if nid and item:
                self.definitions[nid] = item
            self.printUnusedAttributes(node, n)


    def printUnusedAttributes(self, node, n):
        allAttrs = self.attrConverter.getAllAttributes(node).keys()
        unusedAttrs = []

        for a in allAttrs:
            if a not in n.usedAttrs:
                unusedAttrs.append(a)

        if self.verbose and unusedAttrs:
            format = "%s-Unused: %s"
            args = ("  "*(self.level+1), unusedAttrs.join(", "))
            #if not self.logFile:
            #    print format % args
            #else:
            #    self.logFile.write((format+"\n") % args)

        if LOGMESSAGES and unusedAttrs:
            #print "Used attrs:", n.nodeName, n.usedAttrs
            #print "All attrs:", n.nodeName, allAttrs
            print("Unused attrs: %s %s" % (n.nodeName, unusedAttrs))


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
            width, height = viewBox[2:4]
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
            self.shapeConverter.applyTransformOnGroup(transform, gr)

        return gr


    def renderSymbol(self, node):
        return self.renderG(node, display=0)


    def renderA(self, node):
        # currently nothing but a group...
        # there is no linking info stored in shapes, maybe a group should?
        return self.renderG(node)


    def renderUse(self, node):
        xlink_href = node.getAttributeNS("http://www.w3.org/1999/xlink", "href")
        if not xlink_href:
            return
        if xlink_href[1:] not in self.definitions:
            if self.verbose and LOGMESSAGES:
                print("Ignoring unavailable object width ID '%s'." % xlink_href)
            return None
        item = self.definitions[xlink_href[1:]]
        grp = Group()
        grp.add(item)
        getAttr = node.getAttribute
        transform = getAttr("transform")
        x, y = map(getAttr, ("x", "y"))
        if x or y:
            transform += " translate(%s, %s)" % (x or '0', y or '0')
        if transform:
            self.shapeConverter.applyTransformOnGroup(transform, grp)
        # TODO: apply other 'use' properties to the group

        return grp


    def finish(self):
        height = self.drawing.height
        self.mainGroup.scale(1, -1)
        self.mainGroup.translate(0, -height)
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

    def __init__(self):
        self.attrConverter = AttributeConverter()
        self.svgSourceFile = ''


    def getHandledShapes(self):
        "Determine a list of handled shape elements."

        items = dir(self)
        items = self.__class__.__dict__.keys()
        keys = []
        for i in items:
            keys.append(getattr(self, i))
        keys = filter(lambda k:type(k) == types.MethodType, keys)
        keys = map(lambda k:k.__name__, keys)
        keys = filter(lambda k:k[:7] == "convert", keys)
        keys = filter(lambda k:k != "convert", keys)
        keys = map(lambda k:k[7:], keys)
        shapeNames = [k.lower() for k in keys]

        return shapeNames


class Svg2RlgShapeConverter(SvgShapeConverter):
    "Converterer from SVG shapes to RLG (ReportLab Graphics) shapes."

    def __init__(self):
        self.attrConverter = Svg2RlgAttributeConverter()
        self.svgSourceFile = ''


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
        path = Path()

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

            # elliptic arc, unsupported (simplified to line)
            elif op in ('A', 'a'):
                path.lineTo(*nums[-2:])
                if LOGMESSAGES:
                    print ("(Replaced with straight line)")

            # close path
            elif op in ('Z', 'z'):
                path.closePath()

            elif LOGMESSAGES:
                print("Suspicious path operator: %s" % op)

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
        if LOGMESSAGES:
            print("Adding box instead image.")
        getAttr = node.getAttribute
        x, y, width, height = map(getAttr, ('x', 'y', "width", "height"))
        x, y, width, height = map(self.attrConverter.convertLength, (x, y, width, height))
        xlink_href = node.getAttributeNS("http://www.w3.org/1999/xlink", "href")
        xlink_href = os.path.join(os.path.dirname(self.svgSourceFile), xlink_href)
        # print "***", x, y, width, height, xlink_href[:30]

        magic = "data:image/jpeg;base64"
        if xlink_href[:len(magic)] == magic:
            pat = "data:image/(\w+?);base64"
            ext = re.match(pat, magic).groups()[0]
            import base64, md5
            jpegData = base64.decodestring(xlink_href[len(magic):])
            hashVal = md5.new(jpegData).hexdigest()
            name = "images/img%s.%s" % (hashVal, ext)
            path = os.path.join(dirname(self.svgSourceFile), name)
            open(path, "wb").write(jpegData)
            img = Image(x, y+height, width, -height, path)
            # this needs to be removed later, not here...
            # if exists(path): os.remove(path)
        else:
            xlink_href = os.path.join(os.path.dirname(self.svgSourceFile), xlink_href)
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
                try: # HOTFIX
                    values = values[0], values[1]
                except TypeError:
                    return
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
                if LOGMESSAGES:
                    print("Ignoring transform: %s %s" % (op, values))


    def applyStyleOnShape(self, shape, *nodes):
        "Apply styles from SVG elements to an RLG shape."

        # RLG-specific: all RLG shapes
        "Apply style attributes of a sequence of nodes to an RL shape."

        # tuple format: (svgAttr, rlgAttr, converter, default)
        mappingN = (
            ("fill", "fillColor", "convertColor", "black"),
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

        ac = self.attrConverter
        for node in nodes:
            for mapping in (mappingN, mappingF):
                if shape.__class__ != String and mapping == mappingF:
                    continue
                for (svgAttrName, rlgAttr, func, default) in mapping:
                    try:
                        svgAttrValue = ac.findAttr(node, svgAttrName) or default
                        if svgAttrValue == "currentColor":
                            svgAttrValue = ac.findAttr(node.parentNode, "color") or default
                        meth = getattr(ac, func)
                        setattr(shape, rlgAttr, meth(svgAttrValue))
                    except:
                        pass


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
        print("Failed to load input file!")
        return

    # convert to a RLG drawing
    svgRenderer = SvgRenderer(path)
    svgRenderer.render(svg)
    drawing = svgRenderer.finish()

    # remove unzipped .svgz file (.svg)
    if unzipped:
        os.remove(path)
        
    return drawing
