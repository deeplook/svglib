"""Basic shapes: rectangles, lines, polylines and polygons."""

from reportlab.graphics.shapes import (
    Line,
    Polygon,
    PolyLine,
)
from reportlab.lib import colors

from svglib import svglib
from tests.utils import (
    minimal_svg_node,
)


class TestRectNode:
    def test_rx_ry(self):
        converter = svglib.Svg2RlgShapeConverter(None)
        node = minimal_svg_node(
            '<rect rx="10" ry="4" width="10" height="3" x="0" y="0"/>'
        )
        rect = converter.convertRect(node)
        # rx/ry cannot be more than half the rect lengths.
        assert rect.rx == 5
        assert rect.ry == 1.5

    def test_rx_ry_lonely(self):
        """If only rx or ry is present, the other default to the same value."""
        converter = svglib.Svg2RlgShapeConverter(None)
        node = minimal_svg_node('<rect rx="2.5" width="10" height="3" x="0" y="0"/>')
        rect = converter.convertRect(node)
        assert rect.ry == 2.5
        node = minimal_svg_node('<rect ry="1" width="10" height="3" x="0" y="0"/>')
        rect = converter.convertRect(node)
        assert rect.rx == 1

    def test_strokewidth_0(self):
        """
        When strokeWidth = 0, we force strokeColor to None to avoid the stroke
        to be displayed.
        """
        converter = svglib.Svg2RlgShapeConverter(None)
        node = minimal_svg_node(
            '<rect style="stroke: rgb(100, 84, 0); fill: rgb(255, 255, 255); '
            'fill-opacity: 1; stroke-width: 0;" width="135" height="86" x="10" y="10"/>'
        )
        rect = converter.convertShape("rect", node)
        assert rect.strokeColor is None


class TestLineNode:
    def test_length_zero(self):
        converter = svglib.Svg2RlgShapeConverter(None)
        node = minimal_svg_node(
            '<line stroke="#000000" x1="10" y1="20" x2="10" y2="20" />'
        )
        line = converter.convertLine(node)
        assert isinstance(line, Line)

        # Force a slight change in the first coordinate, so it's not invisible.
        assert line.x1 != 10

    def test_length_not_zero(self):
        """No change needed when length is not zero."""
        converter = svglib.Svg2RlgShapeConverter(None)
        node = minimal_svg_node(
            '<line stroke="#000000" x1="10" y1="20" x2="10" y2="30" />'
        )
        line = converter.convertLine(node)
        assert isinstance(line, Line)

        assert line.x1 == 10


class TestPolylineNode:
    def test_filling(self):
        converter = svglib.Svg2RlgShapeConverter(None)
        node = minimal_svg_node(
            '<polyline fill="none" stroke="#000000" '
            'points="10,50,35,150,60,50,85,150,110,50,135,150" />'
        )
        polyline = converter.convertPolyline(node)
        assert isinstance(polyline, PolyLine)

        # svglib simulates polyline filling by a fake polygon.
        node = minimal_svg_node(
            '<polyline fill="#fff" stroke="#000000" '
            'points="10,50,35,150,60,50,85,150,110,50,135,150" />'
        )
        group = converter.convertPolyline(node)
        assert isinstance(group.contents[0], Polygon)
        assert group.contents[0].fillColor == colors.white
        assert isinstance(group.contents[1], PolyLine)

    def test_length_zero(self):
        converter = svglib.Svg2RlgShapeConverter(None)
        node = minimal_svg_node(
            '<polyline fill="none" stroke="#000000" points="10,50,10,50" />'
        )
        polyline = converter.convertPolyline(node)
        assert isinstance(polyline, PolyLine)

        # Force a slight change in the first coordinate, so it's not invisible.
        assert polyline.points[0] != 10

    def test_odd_length(self):
        converter = svglib.Svg2RlgShapeConverter(None)
        node = minimal_svg_node(
            '<polyline fill="none" stroke="#000000" points="10,50,10,50,10" />'
        )
        polyline = converter.convertPolyline(node)
        assert polyline is None


class TestPolygonNode:
    def test_length_zero(self):
        converter = svglib.Svg2RlgShapeConverter(None)
        node = minimal_svg_node(
            '<polygon fill="none" stroke="#000000" points="10,50,10,50" />'
        )
        polygon = converter.convertPolygon(node)
        assert isinstance(polygon, Polygon)

        # Force a slight change in the first coordinate, so it's not invisible.
        assert polygon.points[0] != 10

    def test_odd_length(self):
        converter = svglib.Svg2RlgShapeConverter(None)
        node = minimal_svg_node(
            '<polygon fill="none" stroke="#000000" points="10,50,10,50,10" />'
        )
        polygon = converter.convertPolygon(node)
        assert polygon is None
