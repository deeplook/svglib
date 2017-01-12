#!/usr/bin/env python
# -*- coding: UTF-8 -*-

"""A library for reading and converting SVG.

This is a converter from SVG to RLG (ReportLab Graphics) drawings.
It converts mainly basic shapes, paths and simple text. The intended
usage is either as module within other projects:

    from svglib.svglib import svg2rlg
    drawing = svg2rlg("foo.svg")

or from the command-line where it is usable as an SVG to PDF converting
tool named sv2pdf (which should also handle SVG files compressed with
gzip and extension .svgz).
"""

import copy
import gzip
import itertools
import logging
import operator
import os
import re
import types
from collections import defaultdict, namedtuple

from reportlab.pdfgen.pdfimages import PDFImage
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.pdfgen.canvas import FILL_EVEN_ODD, FILL_NON_ZERO
from reportlab.graphics.shapes import (
    _CLOSEPATH, ArcPath, Circle, Drawing, Ellipse, Group, Image, Line, PolyLine,
    Polygon, Rect, String, mmult, rotate, translate, transformPoint
)
from reportlab.graphics import renderPDF
from reportlab.lib import colors
from reportlab.lib.units import cm, inch, mm, pica, toLength
from lxml import etree


__version__ = "0.6.3"
__license__ = "LGPL 3"
__author__ = "Dinu Gherman"
__date__ = "2010-03-01"

XML_NS = 'http://www.w3.org/XML/1998/namespace'

logger = logging.getLogger(__name__)


### helpers ###

Box = namedtuple('Box', ['x', 'y', 'width', 'height'])


def convertQuadraticToCubicPath(Q0, Q1, Q2):
    "Convert a quadratic Bezier curve through Q0, Q1, Q2 to a cubic one."

    C0 = Q0
    C1 = (Q0[0]+2./3*(Q1[0]-Q0[0]), Q0[1]+2./3*(Q1[1]-Q0[1]))
    C2 = (C1[0]+1./3*(Q2[0]-Q0[0]), C1[1]+1./3*(Q2[1]-Q0[1]))
    C3 = Q2

    return C0, C1, C2, C3

from math import cos, sin, pi, sqrt, acos, ceil, copysign, fabs, hypot, degrees, radians
def vectorAngle(u,v):
    d = hypot(*u)*hypot(*v)
    c = (u[0]*v[0]+u[1]*v[1])/d
    if c<-1: c = -1
    elif c>1: c = 1
    s = u[0]*v[1]-u[1]*v[0]
    return degrees(copysign(acos(c),s))

def endPointToCenterParameters(x1,y1,x2,y2,fA,fS,rx,ry,phi=0):
    '''
    see http://www.w3.org/TR/SVG/implnote.html#ArcImplementationNotes F.6.5
    note that we reduce phi to zero outside this routine 
    '''
    rx = fabs(rx)
    ry = fabs(ry)

    #step 1
    if phi:
        phiRad = radians(phi)
        sinPhi = sin(phiRad)
        cosPhi = cos(phiRad)
        tx = 0.5*(x1-x2)
        ty = 0.5*(y1-y2)
        x1d = cosPhi*tx - sinPhi*ty
        y1d = sinPhi*tx + cosPhi*ty
    else:
        x1d = 0.5*(x1-x2)
        y1d = 0.5*(y1-y2)

    #step 2
    #we need to calculate
    # (rx*rx*ry*ry-rx*rx*y1d*y1d-ry*ry*x1d*x1d)
    # -----------------------------------------
    #     (rx*rx*y1d*y1d+ry*ry*x1d*x1d)
    #
    # that is equivalent to
    # 
    #          rx*rx*ry*ry 
    # = -----------------------------  -    1
    #   (rx*rx*y1d*y1d+ry*ry*x1d*x1d)
    #
    #              1
    # = -------------------------------- - 1
    #   x1d*x1d/(rx*rx) + y1d*y1d/(ry*ry)
    #
    # = 1/r - 1
    #
    # it turns out r is what they recommend checking
    # for the negative radicand case
    r = x1d*x1d/(rx*rx) + y1d*y1d/(ry*ry)
    if r>1:
        rr = sqrt(r)
        rx *= rr
        ry *= rr
        r = x1d*x1d/(rx*rx) + y1d*y1d/(ry*ry)
    r = 1/r - 1
    if -1e-10<r<0: r = 0
    r = sqrt(r)
    if fA==fS: r = -r
    cxd = (r*rx*y1d)/ry
    cyd = -(r*ry*x1d)/rx

    #step3
    if phi:
        cx = cosPhi*cxd - sinPhi*cyd + 0.5*(x1+x2)
        cy = sinPhi*cxd + cosPhi*cyd + 0.5*(y1+y2)
    else:
        cx = cxd + 0.5*(x1+x2)
        cy = cyd + 0.5*(y1+y2)

    #step 4
    theta1 = vectorAngle((1,0),((x1d-cxd)/rx,(y1d-cyd)/ry))
    dtheta = vectorAngle(((x1d-cxd)/rx,(y1d-cyd)/ry),((-x1d-cxd)/rx,(-y1d-cyd)/ry)) % 360
    if fS==0 and dtheta>0: dtheta -= 360
    elif fS==1 and dtheta<0: dtheta += 360
    return cx, cy, rx, ry, -theta1, -dtheta

def bezierArcFromCentre(cx,cy, rx, ry, startAng=0, extent=90):
    if abs(extent) <= 90:
        arcList = [startAng]
        fragAngle = float(extent)
        Nfrag = 1
    else:
        arcList = []
        Nfrag = int(ceil(abs(extent)/90.))
        fragAngle = float(extent) / Nfrag

    fragRad = radians(fragAngle)
    halfRad = fragRad * 0.5
    kappa = abs(4. / 3. * (1. - cos(halfRad)) / sin(halfRad))

    if fragAngle < 0:
        kappa = -kappa

    pointList = []
    pointList_append = pointList.append
    theta1 = radians(startAng)
    startRad = theta1 + fragRad

    c1 = cos(theta1)
    s1 = sin(theta1)
    for i in xrange(Nfrag):
        c0 = c1
        s0 = s1
        theta1 = startRad + i*fragRad
        c1 = cos(theta1)
        s1 = sin(theta1)
        pointList_append((cx + rx * c0,
                          cy - ry * s0,
                          cx + rx * (c0 - kappa * s0),
                          cy - ry * (s0 + kappa * c0),
                          cx + rx * (c1 + kappa * s1),
                          cy - ry * (s1 - kappa * c1),
                          cx + rx * c1,
                          cy - ry * s1))
    return pointList

def bezierArcFromBox(x1,y1, x2,y2, startAng=0, extent=90):
    """bezierArcFromBox(x1,y1, x2,y2, startAng=0, extent=90) --> List of Bezier
curve control points.

(x1, y1) and (x2, y2) are the corners of the enclosing rectangle.  The
coordinate system has coordinates that increase to the right and down.
Angles, measured in degress, start with 0 to the right (the positive X
axis) and increase counter-clockwise.  The arc extends from startAng
to startAng+extent.  I.e. startAng=0 and extent=180 yields an openside-down
semi-circle.

The resulting coordinates are of the form (x1,y1, x2,y2, x3,y3, x4,y4)
such that the curve goes from (x1, y1) to (x4, y4) with (x2, y2) and
(x3, y3) as their respective Bezier control points.

Contributed by Robert Kern.

The algorithm is an elliptical generalization of the formulae in
Jim Fitzsimmon's TeX tutorial <URL: http://www.tinaja.com/bezarc1.pdf>.
"""
    cx, cy, rx,ry = _bd2cr(x1,y1,x2,y2)
    return bezierArcFromCentre(cx,cy, rx, ry, startAng, extent)

def bezierArcFromEndPoints(x1,y1,rx,ry,phi,fA,fS,x2,y2):
    if phi:
        #our box bezier arcs can't handle rotations directly
        #move to a well known point, eliminate phi and transform the other point
        mx = mmult(rotate(-phi),translate(-x1,-y1))
        tx2,ty2 = transformPoint(mx,(x2,y2))
        #convert to box form in unrotated coords
        cx, cy, rx, ry, startAng, extent = endPointToCenterParameters(0,0,tx2,ty2,fA,fS,rx,ry)
        bp = bezierArcFromCentre(cx,cy, rx, ry, startAng, extent)
        #re-rotate by the desired angle and add back the translation
        mx = mmult(translate(x1,y1),rotate(phi))
        res = []
        for x1,y1,x2,y2,x3,y3,x4,y4 in bp:
            res.append(transformPoint(mx,(x1,y1))+transformPoint(mx,(x2,y2))+transformPoint(mx,(x3,y3))+transformPoint(mx,(x4,y4)))
        return res
    else:
        cx, cy, rx, ry, startAng, extent = endPointToCenterParameters(x1,y1,x2,y2,fA,fS,rx,ry)
        return bezierArcFromCentre(cx,cy, rx, ry, startAng, extent)


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


class NoStrokeArcPath(ArcPath):
    """
    This path object never gets a stroke width whatever the properties it's
    getting assigned.
    """
    def __init__(self, *args, **kwargs):
        copy_from = kwargs.pop('copy_from', None)
        ArcPath.__init__(self, *args, **kwargs)  # we're old-style class on PY2
        if copy_from:
            self.__dict__.update(copy.deepcopy(copy_from.__dict__))

    def getProperties(self, *args, **kwargs):
        # __getattribute__ wouldn't suit, as RL is directly accessing self.__dict__
        props = ArcPath.getProperties(self, *args, **kwargs)
        if 'strokeWidth' in props:
            props['strokeWidth'] = 0
        if 'strokeColor' in props:
            props['strokeColor'] = None
        return props


class ClippingArcPath(ArcPath):
    def __init__(self, *args, **kwargs):
        copy_from = kwargs.pop('copy_from', None)
        ArcPath.__init__(self, *args, **kwargs)
        if copy_from:
            self.__dict__.update(copy.deepcopy(copy_from.__dict__))
        self.isClipPath = 1

    def getProperties(self, *args, **kwargs):
        props = ArcPath.getProperties(self, *args, **kwargs)
        if 'fillColor' in props:
            props['fillColor'] = None
        return props


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

        attr_value = svgNode.attrib.get(name, '').strip()

        if attr_value and attr_value != "inherit":
            return attr_value
        elif svgNode.attrib.get("style"):
            dict = self.parseMultiAttributes(svgNode.attrib.get("style"))
            if name in dict:
                return dict[name]
        elif svgNode.getparent() is not None:
            return self.findAttr(svgNode.getparent(), name)

        return ''


    def getAllAttributes(self, svgNode):
        "Return a dictionary of all attributes of svgNode or those inherited by it."

        dict = {}

        if node_name(svgNode.getparent()) == 'g':
            dict.update(self.getAllAttributes(svgNode.getparent()))

        style = svgNode.attrib.get("style")
        if style:
            d = self.parseMultiAttributes(style)
            dict.update(d)

        for key, value in svgNode.attrib.items():
            if key != "style":
                dict[key] = value

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
        ops = ops.replace(',', ' ').split()

        if len(ops) != len(indices):
            logger.warn("Unable to parse transform expression '%s'" % svgAttr)
            return []

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
        return self.object.attrib.get(name, '')

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
        self.definitions = {}
        self.waiting_use_nodes = defaultdict(list)
        self.box = Box(x=0, y=0, width=0, height=0)

    def render(self, svg_node):
        main_group = self.renderNode(svg_node)
        for xlink in self.waiting_use_nodes.keys():
            logger.debug("Ignoring unavailable object width ID '%s'." % xlink)

        main_group.scale(1, -1)
        main_group.translate(0 - self.box.x, -self.box.height - self.box.y)
        drawing = Drawing(self.box.width, self.box.height)
        drawing.add(main_group)
        return drawing

    def renderNode(self, node, parent=None):
        n = NodeTracker(node)
        nid = n.getAttribute("id")
        ignored = False
        item = None
        name = node_name(node)

        clipping = self.get_clippath(n)
        if name == "svg":
            if n.getAttribute("{%s}space" % XML_NS) == 'preserve':
                self.shape_converter.preserve_space = True
            item = self.renderSvg(n)
            return item
        elif name == "defs":
            item = self.renderG(n)
        elif name == 'a':
            item = self.renderA(n)
            parent.add(item)
        elif name == 'g':
            display = n.getAttribute("display")
            item = self.renderG(n, clipping=clipping)
            if display != "none":
                parent.add(item)
        elif name == "symbol":
            item = self.renderSymbol(n)
            # parent.add(item)
        elif name == "use":
            item = self.renderUse(n, clipping=clipping)
            parent.add(item)
        elif name == "clipPath":
            item = self.renderG(n)
        elif name in self.handled_shapes:
            display = n.getAttribute("display")
            item = self.shape_converter.convertShape(name, n, clipping)
            if item and display != "none":
                parent.add(item)
        else:
            ignored = True
            logger.debug("Ignoring node: %s" % name)

        if not ignored:
            if nid and item:
                self.definitions[nid] = node
            if nid in self.waiting_use_nodes.keys():
                to_render = self.waiting_use_nodes.pop(nid)
                for use_node, group in to_render:
                    self.renderUse(use_node, group=group)
            self.print_unused_attributes(node, n)

    def get_clippath(self, node):
        """
        Return the clipping Path object referenced by the node 'clip-path'
        attribute, if any.
        """
        def get_path_from_node(node):
            for child in node.getchildren():
                if node_name(child) == 'path':
                    group = self.shape_converter.convertShape('path', NodeTracker(child))
                    return group.contents[-1]
                else:
                    return get_path_from_node(child)

        clip_path = node.getAttribute('clip-path')
        if clip_path:
            m = re.match(r'url\(#([^\)]*)\)', clip_path)
            if m:
                ref = m.groups()[0]
                if ref in self.definitions:
                    path = get_path_from_node(self.definitions[ref])
                    if path:
                        path = ClippingArcPath(copy_from=path)
                        return path

    def print_unused_attributes(self, node, n):
        if logger.level > logging.DEBUG:
            return
        all_attrs = self.attrConverter.getAllAttributes(node).keys()
        unused_attrs = [attr for attr in all_attrs if attr not in n.usedAttrs]
        if unused_attrs:
            logger.debug("Unused attrs: %s %s" % (node_name(n), unused_attrs))


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
            self.box = Box(*viewBox)
        else:
            self.box = Box(0, 0, width, height)
        group = Group()
        for child in node.getchildren():
            self.renderNode(child, group)
        return group


    def renderG(self, node, clipping=None, display=1):
        getAttr = node.getAttribute
        id, transform = map(getAttr, ("id", "transform"))
        gr = Group()
        if clipping:
            gr.add(clipping)
        for child in node.getchildren():
            item = self.renderNode(child, parent=gr)
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


    def renderUse(self, node, group=None, clipping=None):
        if group is None:
            group = Group()

        xlink_href = node.attrib.get('{http://www.w3.org/1999/xlink}href')
        if not xlink_href:
            return
        if xlink_href[1:] not in self.definitions:
            # The missing definition should appear later in the file
            self.waiting_use_nodes[xlink_href[1:]].append((node, group))
            return group

        if clipping:
            group.add(clipping)
        if len(node.getchildren()) == 0:
            # Append a copy of the referenced node as the <use> child (if not already done)
            node.append(copy.deepcopy(self.definitions[xlink_href[1:]]))
        self.renderNode(node.getchildren()[-1], parent=group)
        getAttr = node.getAttribute
        transform = getAttr("transform")
        x, y = map(getAttr, ("x", "y"))
        if x or y:
            transform += " translate(%s, %s)" % (x or '0', y or '0')
        if transform:
            self.shape_converter.applyTransformOnGroup(transform, group)
        return group


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
        self.preserve_space = False

    @classmethod
    def get_handled_shapes(cls):
        """Dynamically determine a list of handled shape elements based on
           convert<shape> method existence.
        """
        return [key[7:].lower() for key in dir(cls) if key.startswith('convert')]


class Svg2RlgShapeConverter(SvgShapeConverter):
    """Converter from SVG shapes to RLG (ReportLab Graphics) shapes."""

    AttributeConverterClass = Svg2RlgAttributeConverter

    def convertShape(self, name, node, clipping=None):
        method_name = "convert%s" % name.capitalize()
        shape = getattr(self, method_name)(node)
        if not shape:
            return
        if name not in ('path', 'polyline', 'text'):
            # Only apply style where the convert method did not apply it.
            self.applyStyleOnShape(shape, node)
        transform = node.getAttribute("transform")
        if not (transform or clipping):
            return shape
        else:
            group = Group()
            if transform:
                self.applyTransformOnGroup(transform, group)
            if clipping:
                group.add(clipping)
            group.add(shape)
            return group

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

        polyline = PolyLine(points)
        self.applyStyleOnShape(polyline, node)
        has_fill = self.attrConverter.findAttr(node, 'fill') not in ('', 'none')

        if has_fill:
            # ReportLab doesn't fill polylines, so we are creating a polygon
            # polygon copy of the polyline, but without stroke.
            group = Group()
            polygon = Polygon(points)
            self.applyStyleOnShape(polygon, node)
            polygon.strokeColor = None
            group.add(polygon)
            group.add(polyline)
            return group

        return polyline


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

    def clean_text(self, text, preserve_space):
        """Text cleaning as per https://www.w3.org/TR/SVG/text.html#WhiteSpace
        """
        if text is None:
            return
        if preserve_space:
            text = text.replace('\r\n', ' ').replace('\n', ' ').replace('\t', ' ')
        else:
            text = text.replace('\r\n', '').replace('\n', '').replace('\t', ' ')
            text = text.strip()
            while ('  ' in text):
                text = text.replace('  ', ' ')
        return text

    def convertText(self, node):
        attrConv = self.attrConverter
        x, y = map(node.getAttribute, ('x', 'y'))
        x, y = map(attrConv.convertLength, (x, y))
        xml_space = node.getAttribute("{%s}space" % XML_NS)
        if xml_space:
            preserve_space = xml_space == 'preserve'
        else:
            preserve_space = self.preserve_space

        gr = Group()

        frag_lengths = []

        dx0, dy0 = 0, 0
        x1, y1 = 0, 0
        ff = attrConv.findAttr(node, "font-family") or "Helvetica"
        ff = attrConv.convertFontFamily(ff)
        fs = attrConv.findAttr(node, "font-size") or "12"
        fs = attrConv.convertLength(fs)
        for c in itertools.chain([node], node.getchildren()):
            has_x = False
            dx, dy = 0, 0
            baseLineShift = 0
            if node_name(c) == 'text':
                text = self.clean_text(c.text, preserve_space)
                if not text:
                    continue
            elif node_name(c) == 'tspan':
                text = self.clean_text(c.text, preserve_space)
                if not text:
                    continue
                x1, y1, dx, dy = [c.attrib.get(name, '') for name in ("x", "y", "dx", "dy")]
                has_x = x1 != ''
                x1, y1, dx, dy = map(attrConv.convertLength, (x1, y1, dx, dy))
                dx0 = dx0 + dx
                dy0 = dy0 + dy
                baseLineShift = c.attrib.get("baseline-shift", '0')
                if baseLineShift in ("sub", "super", "baseline"):
                    baseLineShift = {"sub":-fs/2, "super":fs/2, "baseline":0}[baseLineShift]
                else:
                    baseLineShift = attrConv.convertLength(baseLineShift, fs)
            else:
                continue

            frag_lengths.append(stringWidth(text, ff, fs))
            new_x = x1 if has_x else sum(frag_lengths[:-1])
            shape = String(x + new_x, y - y1 - dy0 + baseLineShift, text)
            self.applyStyleOnShape(shape, node)
            if node_name(c) == 'tspan':
                self.applyStyleOnShape(shape, c)

            gr.add(shape)

        gr.scale(1, -1)
        gr.translate(0, -2*y)

        return gr


    def convertPath(self, node):
        d = node.getAttribute('d')
        normPath = normaliseSvgPath(d)
        path = ArcPath()
        pts = path.points
        # Track subpaths needing to be closed later
        unclosed_subpath_pointers = []
        subpath_start = []
        lastop = ''

        for i in xrange(0, len(normPath), 2):
            op, nums = normPath[i:i+2]

            if op in ('m', 'M') and i > 0 and path.operators[-1] != _CLOSEPATH:
                unclosed_subpath_pointers.append(len(path.operators))

            # moveto absolute
            if op == 'M':
                path.moveTo(*nums)
                subpath_start = pts[-2:]
            # lineto absolute
            elif op == 'L':
                path.lineTo(*nums)

            # moveto relative
            elif op == 'm':
                if len(pts) >= 2:
                    if lastop in ('Z', 'z'):
                        starting_point = subpath_start
                    else:
                        starting_point = pts[-2:]
                    xn, yn = starting_point[0] + nums[0], starting_point[1] + nums[1]
                    path.moveTo(xn, yn)
                else:
                    path.moveTo(*nums)
                subpath_start = pts[-2:]
            # lineto relative
            elif op == 'l':
                xn, yn = pts[-2] + nums[0], pts[-1] + nums[1]
                path.lineTo(xn, yn)

            # horizontal/vertical line absolute
            elif op == 'H':
                path.lineTo(nums[0], pts[-1])
            elif op == 'V':
                path.lineTo(pts[-2], nums[0])

            # horizontal/vertical line relative
            elif op == 'h':
                path.lineTo(pts[-2] + nums[0], pts[-1])
            elif op == 'v':
                path.lineTo(pts[-2], pts[-1] + nums[0])

            # cubic bezier, absolute
            elif op == 'C':
                path.curveTo(*nums)
            elif op == 'S':
                x2, y2, xn, yn = nums
                if len(pts) < 4 or lastop not in {'c', 'C', 's', 'S'}:
                    xp, yp, x0, y0 = pts[-2:] * 2
                else:
                    xp, yp, x0, y0 = pts[-4:]
                xi, yi = x0 + (x0 - xp), y0 + (y0 - yp)
                path.curveTo(xi, yi, x2, y2, xn, yn)

            # cubic bezier, relative
            elif op == 'c':
                xp, yp = pts[-2:]
                x1, y1, x2, y2, xn, yn = nums
                path.curveTo(xp + x1, yp + y1, xp + x2, yp + y2, xp + xn, yp + yn)
            elif op == 's':
                x2, y2, xn, yn = nums
                if len(pts) < 4 or lastop not in {'c', 'C', 's', 'S'}:
                    xp, yp, x0, y0 = pts[-2:] * 2
                else:
                    xp, yp, x0, y0 = pts[-4:]
                xi, yi = x0 + (x0 - xp), y0 + (y0 - yp)
                path.curveTo(xi, yi, x0 + x2, y0 + y2, x0 + xn, y0 + yn)

            # quadratic bezier, absolute
            elif op == 'Q':
                x0, y0 = pts[-2:]
                x1, y1, xn, yn = nums
                (x0,y0), (x1,y1), (x2,y2), (xn,yn) = \
                    convertQuadraticToCubicPath((x0,y0), (x1,y1), (xn,yn))
                path.curveTo(x1, y1, x2, y2, xn, yn)
            elif op == 'T':
                if len(pts) < 4:
                    xp, yp, x0, y0 = pts[-2:] * 2
                else:
                    xp, yp, x0, y0 = pts[-4:]
                xi, yi = x0 + (x0 - xp), y0 + (y0 - yp)
                xn, yn = nums
                (x0,y0), (x1,y1), (x2,y2), (xn,yn) = \
                    convertQuadraticToCubicPath((x0,y0), (xi,yi), (xn,yn))
                path.curveTo(x1, y1, x2, y2, xn, yn)

            # quadratic bezier, relative
            elif op == 'q':
                x0, y0 = pts[-2:]
                x1, y1, xn, yn = nums
                x1, y1, xn, yn = x0 + x1, y0 + y1, x0 + xn, y0 + yn
                (x0,y0), (x1,y1), (x2,y2), (xn,yn) = \
                    convertQuadraticToCubicPath((x0,y0), (x1,y1), (xn,yn))
                path.curveTo(x1, y1, x2, y2, xn, yn)
            elif op == 't':
                if len(pts) < 4:
                    xp, yp, x0, y0 = pts[-2:] * 2
                else:
                    xp, yp, x0, y0 = pts[-4:]
                x0, y0 = pts[-2:]
                xn, yn = nums
                xn, yn = x0 + xn, y0 + yn
                xi, yi = x0 + (x0 - xp), y0 + (y0 - yp)
                (x0,y0), (x1,y1), (x2,y2), (xn,yn) = \
                    convertQuadraticToCubicPath((x0,y0), (xi,yi), (xn,yn))
                path.curveTo(x1, y1, x2, y2, xn, yn)

            elif op in 'aA':
                rx,ry,phi,fA,fS,x2,y2 = nums
                if op=='a':
                    x1, y1 = pts[-2:]
                    x2 += x1
                    y2 += y1
                if abs(rx)<=1e-10 or abs(ry)<=1e-10:
                    path.lineTo(x2,y2)
                else:
                    bp = bezierArcFromEndPoints(x1,y1,rx,ry,phi,fA,fS,x2,y2)
                    for _x,_y,x1,y1,x2,y2,xn,yn in bp:
                        path.curveTo(x1,y1,x2,y2,xn,yn)

            # close path
            elif op in ('Z', 'z'):
                path.closePath()

            else:
                logger.debug("Suspicious path operator: %s" % op)
            lastop = op

        gr = Group()
        self.applyStyleOnShape(path, node)

        if path.operators[-1] != _CLOSEPATH:
            unclosed_subpath_pointers.append(len(path.operators))

        if unclosed_subpath_pointers and path.fillColor is not None:
            # ReportLab doesn't fill unclosed paths, so we are creating a copy
            # of the path with all subpaths closed, but without stroke.
            # https://bitbucket.org/rptlab/reportlab/issues/99/
            closed_path = NoStrokeArcPath(copy_from=path)
            for pointer in reversed(unclosed_subpath_pointers):
                closed_path.operators.insert(pointer, _CLOSEPATH)
            gr.add(closed_path)
            path.fillColor = None

        gr.add(path)
        return gr


    def convertImage(self, node):
        logger.warn("Adding box instead image.")
        getAttr = node.getAttribute
        x, y, width, height = map(getAttr, ('x', 'y', "width", "height"))
        x, y, width, height = map(self.attrConverter.convertLength, (x, y, width, height))
        xlink_href = node.attrib.get('{http://www.w3.org/1999/xlink}href')

        magic = "data:image/jpeg;base64"
        if xlink_href[:len(magic)] == magic:
            import base64, tempfile
            pat = "data:image/(\w+?);base64"
            ext = re.match(pat, magic).groups()[0]
            jpeg_data = base64.decodestring(xlink_href[len(magic):].encode('ascii'))
            _, path = tempfile.mkstemp(suffix='.%s' % ext)
            with open(path, 'wb') as fh:
                fh.write(jpeg_data)
            img = Image(int(x), int(y+height), int(width), int(-height), path)
            # this needs to be removed later, not here...
            # if exists(path): os.remove(path)
        else:
            xlink_href = os.path.join(os.path.dirname(self.svg_source_file), xlink_href)
            img = Image(int(x), int(y+height), int(width), int(-height), xlink_href)
            try:
                # This will catch unvalid image
                PDFImage(xlink_href, 0, 0)
            except IOError:
                logger.error("Unable to read the image %s. Skipping..." % img.path)
                return None
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
            ("stroke-width", "strokeWidth", "convertLength", "1"),
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
                    svgAttrValue = ac.findAttr(node.getparent(), "color") or default
                try:
                    meth = getattr(ac, func)
                    setattr(shape, rlgAttr, meth(svgAttrValue))
                except (AttributeError, KeyError, ValueError):
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
    parser = etree.XMLParser(remove_comments=True, recover=True)
    try:
        doc = etree.parse(path, parser=parser)
        svg = doc.getroot()
    except Exception as exc:
        logger.error("Failed to load input file! (%s)" % exc)
        return

    # convert to a RLG drawing
    svgRenderer = SvgRenderer(path)
    drawing = svgRenderer.render(svg)

    # remove unzipped .svgz file (.svg)
    if unzipped:
        os.remove(path)

    return drawing


def node_name(node):
    """Return lxml node name without the namespace prefix."""

    try:
        return node.tag.split('}')[-1]
    except AttributeError:
        pass


from distutils.version import LooseVersion
import reportlab
if LooseVersion(reportlab.__version__)<LooseVersion('3.3.28'):
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
            else:
                self._fillMode = FILL_NON_ZERO
            original_drawPath(self, path, **kwargs)
            self._fillMode = current
        Canvas.drawPath = patchedDrawPath

    monkeypatch_reportlab()
