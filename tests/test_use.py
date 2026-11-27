"""The <use> element: references, cycles and expansion limits."""

import logging
from typing import Any

from reportlab.graphics.shapes import (
    Group,
    Rect,
)
from reportlab.lib import colors

from svglib import svglib
from tests.utils import (
    drawing_from_svg,
)


class TestUseNode:
    def test_use(self, drawing_source=None):
        drawing = drawing_from_svg(
            drawing_source
            or """
            <?xml version="1.0"?>
            <svg version="1.1"
                 xmlns="http://www.w3.org/2000/svg"
                 xmlns:xlink="http://www.w3.org/1999/xlink"
                 width="10cm" height="3cm" viewBox="0 0 100 30">
              <defs>
                  <rect id="MyRect" width="60" height="10"/>
              </defs>
              <rect x=".1" y=".1" width="99.8" height="29.8"
                    fill="none" stroke="blue" stroke-width=".2" />
              <use x="20" y="10" xlink:href="#MyRect" />
              <use x="30" y="20" xlink:href="#MyRect" fill="#f00" />
            </svg>
        """
        )
        main_group = drawing.contents[0]
        # First Rect
        assert isinstance(main_group.contents[0], Rect)
        # Second Rect defined by the use node (inside a Group)
        assert isinstance(main_group.contents[1].contents[0], Rect)
        assert main_group.contents[1].contents[0].fillColor == colors.black  # default
        # Attributes on the use node are applied to the referenced content
        assert isinstance(main_group.contents[2].contents[0], Rect)
        assert main_group.contents[2].contents[0].fillColor == colors.red

    def test_use_href_svg2(self):
        """In SVG 2, xlink:href="" can be simply href=""."""
        drawing = drawing_from_svg(
            """
            <svg xmlns="http://www.w3.org/2000/svg"
                 width="10cm" height="3cm" viewBox="0 0 100 30">
              <defs>
                <rect id="MyRect" x=".1" y=".1" width="99.8" height="29.8"
                      fill="none" stroke="blue" />
              </defs>
              <use x="20" y="10" href="#MyRect" />
            </svg>
        """
        )
        assert isinstance(drawing.contents[0].contents[0].contents[0], Rect)

    def test_use_position_lengths(self):
        """The x and y of a <use> are lengths, so they can have a unit."""
        drawing = drawing_from_svg(
            """
            <svg xmlns="http://www.w3.org/2000/svg" width="200" height="100">
              <defs>
                <rect id="MyRect" width="10" height="10"/>
              </defs>
              <use href="#MyRect" x="20px" y="1in"/>
              <use href="#MyRect" x="50%" y="10%"/>
              <g font-size="10"><use href="#MyRect" x="2em"/></g>
            </svg>
        """
        )
        main_group = drawing.contents[0]
        assert main_group.contents[0].transform == (1, 0, 0, 1, 20, 96)
        assert main_group.contents[1].transform == (1, 0, 0, 1, 100, 10)
        assert main_group.contents[2].contents[0].transform == (1, 0, 0, 1, 20, 0)

    def test_use_with_defs_at_end(self):
        self.test_use(
            drawing_source="""
            <?xml version="1.0"?>
            <svg version="1.1"
                 xmlns="http://www.w3.org/2000/svg"
                 xmlns:xlink="http://www.w3.org/1999/xlink"
                 width="10cm" height="3cm" viewBox="0 0 100 30">
              <rect x=".1" y=".1" width="99.8" height="29.8"
                    fill="none" stroke="blue" stroke-width=".2" />
              <use x="20" y="10" xlink:href="#MyRect" />
              <use x="30" y="20" xlink:href="#MyRect" fill="#f00" />
              <defs>
                  <rect id="MyRect" width="60" height="10"/>
              </defs>
            </svg>
        """
        )

    def test_transform_inherited_by_use(self):
        drawing = drawing_from_svg(
            """
            <?xml version="1.0"?>
            <svg version="1.1"
                 xmlns:xlink="http://www.w3.org/1999/xlink"
                 width="900" height="600">
                <g id="c">
                    <path id="t" d="M 0,-100 V 0 H 50"
                          transform="rotate(18 0,-100)"/>
                    <use xlink:href="#t" transform="scale(-1,1)"/>
                </g>
            </svg>
        """
        )
        cgroup_node = drawing.contents[0].contents[0]
        assert (
            cgroup_node.contents[0].transform
            == cgroup_node.contents[1].contents[0].transform
        ), (
            "The transform of the original path is different from the transform of "
            "the reused path."
        )

    def test_use_forward_reference(self):
        """
        Sometimes, a node definition pointed to by xlink:href can appear after
        it has been referenced. But the order should remain.
        """
        drawing = drawing_from_svg(
            """
            <?xml version="1.0"?>
            <svg version="1.1"
                 xmlns:xlink="http://www.w3.org/1999/xlink"
                 width="900" height="600">
                <use xlink:href="#back" x="-100"/>
                <rect id="back" x="42" y="42" width="416" height="216" fill="#007a5e"/>
            </svg>
        """
        )
        assert len(drawing.contents[0].contents) == 2
        assert isinstance(drawing.contents[0].contents[0], Group)
        assert isinstance(drawing.contents[0].contents[1], Rect)

    def test_use_nested_expansion_is_bounded(self, caplog):
        """
        Nested <use> elements referencing groups of <use> elements multiply
        and must not expand without limit.
        """
        levels = ['<rect id="l0" width="1" height="1"/>']
        for i in range(1, 6):
            levels.append(
                f'<g id="l{i}">' + f'<use xlink:href="#l{i - 1}"/>' * 10 + "</g>"
            )
        with caplog.at_level(logging.ERROR, logger="svglib.svglib"):
            drawing = drawing_from_svg(
                '<svg xmlns="http://www.w3.org/2000/svg" '
                'xmlns:xlink="http://www.w3.org/1999/xlink" width="10" height="10">'
                f'<defs>{"".join(levels)}</defs><use xlink:href="#l5"/></svg>'
            )
        assert drawing is not None
        limit_hits = [r for r in caplog.records if "Too many <use>" in r.message]
        assert len(limit_hits) == 1

    @staticmethod
    def _count_rects(shape: Any) -> int:
        return sum(
            1 if isinstance(child, Rect) else TestUseNode._count_rects(child)
            for child in getattr(shape, "contents", [])
        )

    def test_use_expansion_of_large_groups_is_bounded(self, caplog, monkeypatch):
        """
        The number of <use> expansions is not the only cost: each one copies and
        renders its whole target, so a big leaf group must not be expanded
        thousands of times either (GHSA-xpfm-fw4h-qxwv).
        """
        # A small budget keeps this fast. Without a limit on cloned elements the
        # same document clones about 450,000 rects, which takes minutes and
        # gigabytes. The cost is in the <defs>, so the drawing can't show it:
        # the budget running out is the result to check.
        monkeypatch.setattr(svglib, "MAX_USE_CLONED_ELEMENTS", 2_000, raising=False)
        levels = ['<g id="l0">' + '<rect width="1" height="1"/>' * 50 + "</g>"]
        for i in range(1, 5):
            levels.append(
                f'<g id="l{i}">' + f'<use xlink:href="#l{i - 1}"/>' * 10 + "</g>"
            )
        with caplog.at_level(logging.ERROR, logger="svglib.svglib"):
            drawing = drawing_from_svg(
                '<svg xmlns="http://www.w3.org/2000/svg" '
                'xmlns:xlink="http://www.w3.org/1999/xlink" width="10" height="10">'
                f'<defs>{"".join(levels)}</defs><use xlink:href="#l4"/></svg>'
            )
        assert drawing is not None
        hits = [r for r in caplog.records if "cloned elements" in r.message]
        assert len(hits) == 1

    def test_use_cloned_elements_budget(self, caplog, monkeypatch):
        """Each expansion is charged the size of its target, then <use> stops."""
        monkeypatch.setattr(svglib, "MAX_USE_CLONED_ELEMENTS", 100)
        # 31 elements per clone (the group and 30 rects): three fit in 100.
        with caplog.at_level(logging.ERROR, logger="svglib.svglib"):
            drawing = drawing_from_svg(
                '<svg xmlns="http://www.w3.org/2000/svg" '
                'xmlns:xlink="http://www.w3.org/1999/xlink" width="10" height="10">'
                '<defs><g id="g">'
                + '<rect width="1" height="1"/>' * 30
                + "</g></defs>"
                + '<use xlink:href="#g"/>' * 10
                + "</svg>"
            )
        assert self._count_rects(drawing) == 90
        hits = [r for r in caplog.records if "cloned elements" in r.message]
        assert len(hits) == 1

    def test_use_self_reference_is_skipped(self, caplog):
        """
        A <use> pointing at itself must be skipped, not recurse forever.
        """
        with caplog.at_level(logging.ERROR, logger="svglib.svglib"):
            drawing = drawing_from_svg(
                '<svg xmlns="http://www.w3.org/2000/svg" '
                'xmlns:xlink="http://www.w3.org/1999/xlink" width="10" height="10">'
                '<use id="a" xlink:href="#a"/></svg>'
            )
        assert drawing is not None
        assert any("Circular <use>" in r.message for r in caplog.records)

    def test_use_cycle_is_skipped(self, caplog):
        """
        Cycles of two and three elements, each pointing at the next through
        a <use>, must be skipped, not recurse forever.
        """
        cycles = {
            "two": (
                '<g id="a"><use xlink:href="#b"/></g>'
                '<g id="b"><use xlink:href="#a"/></g>'
            ),
            "three": (
                '<g id="a"><use xlink:href="#b"/></g>'
                '<g id="b"><use xlink:href="#c"/></g>'
                '<g id="c"><use xlink:href="#a"/></g>'
            ),
        }
        for name, defs in cycles.items():
            caplog.clear()
            with caplog.at_level(logging.ERROR, logger="svglib.svglib"):
                drawing = drawing_from_svg(
                    '<svg xmlns="http://www.w3.org/2000/svg" '
                    'xmlns:xlink="http://www.w3.org/1999/xlink" '
                    f'width="10" height="10"><defs>{defs}</defs>'
                    '<use xlink:href="#a"/></svg>'
                )
            assert drawing is not None, name
            assert any("Circular <use>" in r.message for r in caplog.records), name

    def test_use_cycle_through_nested_group_is_skipped(self, caplog):
        """
        Rendering a clone of #c rebinds #a to the cloned element; the cycle
        must still be detected.
        """
        with caplog.at_level(logging.ERROR, logger="svglib.svglib"):
            drawing = drawing_from_svg(
                '<svg xmlns="http://www.w3.org/2000/svg" width="10" height="10">'
                '<defs><g id="c"><g id="a"><use href="#c"/><use href="#a"/></g></g>'
                '</defs><use href="#a"/></svg>'
            )
        assert drawing is not None
        assert any("Circular <use>" in r.message for r in caplog.records)

    def test_use_repeated_reference_is_not_a_cycle(self, caplog):
        """
        Reusing the same definition many times, also nested, is legitimate
        and must not be reported as a cycle.
        """
        with caplog.at_level(logging.ERROR, logger="svglib.svglib"):
            drawing = drawing_from_svg(
                '<svg xmlns="http://www.w3.org/2000/svg" '
                'xmlns:xlink="http://www.w3.org/1999/xlink" width="10" height="10">'
                '<defs><rect id="r" width="1" height="1"/>'
                '<g id="g"><use xlink:href="#r"/><use xlink:href="#r"/></g></defs>'
                '<use xlink:href="#g"/><use xlink:href="#g"/></svg>'
            )
        assert drawing is not None
        assert not caplog.records

    def test_use_node_properties(self):
        """
        Properties on the use node apply to the referenced item.
        """
        drawing = drawing_from_svg(
            """
            <?xml version="1.0"?>
            <svg version="1.1"
                 xmlns:xlink="http://www.w3.org/1999/xlink"
                 width="900" height="600">
                <path id="a" fill="#FF0000" d="M-15 37.57h60L-15 0v80h60l-60-60z"/>
                <use stroke="#003893" stroke-width="5" xlink:href="#a"/>
                <use stroke="#003893" stroke-width="2" xlink:href="#a"/>
            </svg>
        """
        )
        use_path1 = drawing.contents[0].contents[1].contents[0].contents[0]
        use_path2 = drawing.contents[0].contents[2].contents[0].contents[0]
        # Attribute from <path> node
        assert use_path1.fillColor == colors.Color(1, 0, 0, 1)
        # Attribute from <use> node
        assert use_path1.strokeWidth == 5
        assert use_path2.strokeWidth == 2

    def test_use_node_with_unclosed_path(self):
        """
        When a <use> node references an unclosed path (which is a group with two
        different paths for filling and stroking), the use properties shouldn't
        affect the no-stroke property of the fake stroke-only path.
        """
        drawing = drawing_from_svg(
            """
            <?xml version="1.0"?>
            <svg xmlns="http://www.w3.org/2000/svg"
                 xmlns:xlink="http://www.w3.org/1999/xlink"
                 width="900" height="600" viewBox="0 0 9 6">
                <defs>
                    <path d="M0,0 4.5,3 0,6" id="X"/>
                </defs>
                <use xlink:href="#X" fill="#f00" stroke="#ffb612" stroke-width="2"/>
            </svg>
        """
        )
        use_group = drawing.contents[0].contents[0].contents[0]
        assert use_group.contents[0].getProperties()["strokeWidth"] == 0
        assert use_group.contents[0].getProperties()["strokeColor"] is None


class TestImageReferences:
    """An <image> that refers to a fragment of the document is limited as a <use>."""

    HEAD = (
        '<svg xmlns="http://www.w3.org/2000/svg" '
        'xmlns:xlink="http://www.w3.org/1999/xlink" width="100" height="100">'
    )

    def test_image_cycle_is_skipped(self, caplog):
        """
        An <image> that refers to a group or <svg> that contains it must be
        skipped, not recurse until RecursionError.
        """
        cycles = {
            "nested-svg": (
                '<svg id="inner" width="50" height="50">'
                '<image xlink:href="#inner" width="50" height="50"/></svg>'
                '<image xlink:href="#inner" width="50" height="50"/>'
            ),
            "two": (
                '<g id="a"><image href="#b"/></g><g id="b"><image href="#a"/></g>'
                '<image href="#a"/>'
            ),
        }
        for name, content in cycles.items():
            caplog.clear()
            with caplog.at_level(logging.ERROR, logger="svglib.svglib"):
                drawing = drawing_from_svg(f"{self.HEAD}{content}</svg>")
            assert drawing is not None, name
            assert any("Circular" in r.message for r in caplog.records), name

    def test_image_referring_to_itself_is_skipped(self):
        """
        An <image> that refers to its own id is not defined yet at that point:
        it was an AttributeError, and is skipped now, as any forward reference.
        """
        drawing = drawing_from_svg(f'{self.HEAD}<image id="a" href="#a"/></svg>')
        assert drawing is not None

    def test_image_nested_expansion_is_bounded(self, caplog):
        """
        Groups of two <image> elements, each referring to the group before it,
        double with every level: 22 levels are about 4 million expansions from
        a 2 KB file, which took hours, and must stop at the budget.
        """
        levels = ['<g id="g0"><rect width="1" height="1"/></g>']
        for i in range(1, 23):
            levels.append(
                f'<g id="g{i}"><image href="#g{i - 1}"/><image href="#g{i - 1}"/></g>'
            )
        with caplog.at_level(logging.ERROR, logger="svglib.svglib"):
            drawing = drawing_from_svg(
                f'{self.HEAD}<defs>{"".join(levels)}</defs><image href="#g22"/></svg>'
            )
        assert drawing is not None
        limit_hits = [r for r in caplog.records if "Too many <use>" in r.message]
        assert len(limit_hits) == 1

    def test_image_repeated_reference_is_not_a_cycle(self, caplog):
        """
        Referring to the same fragment many times, also nested, is legitimate
        and must be rendered every time, not reported as a cycle.
        """
        with caplog.at_level(logging.ERROR, logger="svglib.svglib"):
            drawing = drawing_from_svg(
                f'{self.HEAD}<defs><g id="r"><rect width="1" height="1"/></g>'
                '<g id="g"><image href="#r"/><image href="#r"/></g></defs>'
                '<image href="#g"/><image href="#g"/></svg>'
            )
        assert drawing is not None
        assert not caplog.records
        assert TestUseNode._count_rects(drawing) == 4
