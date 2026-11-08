"""Text nodes: whitespace, fonts, baseline shifts and tspans."""

from reportlab.lib import colors

from tests.utils import (
    drawing_from_svg,
)


class TestTextNode:
    def test_space_preservation(self):
        drawing = drawing_from_svg(
            """
            <?xml version="1.0"?>
            <svg width="777" height="267">
              <text style="fill:#000000; stroke:none; font-size:28;">
                <tspan>TITLE    1</tspan>
                <tspan x="-10.761" y="33.487">Subtitle</tspan>
              </text>
            </svg>
        """
        )
        main_group = drawing.contents[0]
        # By default, only two tspans produce String objects + 1 for the space
        # *between tspans, the start/end spaces/newlines are ignored.
        assert len(main_group.contents[0].contents) == 3
        assert main_group.contents[0].contents[0].text == "TITLE 1"

        drawing = drawing_from_svg(
            """
            <?xml version="1.0"?>
            <svg width="777" height="267" xml:space="preserve">
              <text style="fill:#000000; stroke:none; font-size:28;">
                <tspan>TITLE    1</tspan>
                <tspan x="-10.761" y="33.487">Subtitle</tspan>
              </text>
            </svg>
        """
        )
        main_group = drawing.contents[0]
        assert main_group.contents[0].contents[0].text == "     "
        assert main_group.contents[0].contents[1].text == "TITLE    1"

        drawing = drawing_from_svg(
            """
            <?xml version="1.0"?>
            <svg width="777" height="267">
              <text style="fill:#000000; stroke:none; font-size:28;">
                <tspan>TITLE    1</tspan>
                <tspan x="-10.761" y="33.487">Subtitle</tspan>
              </text>
              <text xml:space="preserve">  with   spaces </text>
            </svg>
        """
        )
        main_group = drawing.contents[0]
        # xml:space can be overriden per text node
        assert main_group.contents[0].contents[0].text == "TITLE 1"
        assert main_group.contents[1].contents[0].text == "  with   spaces "

    def test_font_shorthand(self):
        """The CSS `font` shorthand sets style, weight, size and family (#343)."""
        drawing = drawing_from_svg(
            """
            <svg viewBox="0 0 240 40" xmlns="http://www.w3.org/2000/svg">
              <style>
                text  { font: italic 12px serif; }
                tspan { font: bold 10px/1.2 sans-serif; fill: red; }
              </style>
              <text x="10" y="30">You are <tspan>not</tspan> a banana!</text>
              <text style="font: bold 20px monospace; font-size: 8px">x</text>
            </svg>
        """
        )
        strings = drawing.contents[0].contents[0].contents
        assert [(s.text, s.fontName, s.fontSize) for s in strings] == [
            ("You are ", "Times-Italic", 12),
            ("not", "Helvetica-Bold", 10),
            (" a banana!", "Times-Italic", 12),
        ]
        assert strings[1].fillColor == colors.red
        # A longhand after the shorthand still wins.
        last = drawing.contents[0].contents[1].contents[0]
        assert (last.fontName, last.fontSize) == ("Courier-Bold", 8)

    def test_font_size_keywords(self):
        """CSS font-size keywords are sizes, in the attribute and the shorthand."""
        drawing = drawing_from_svg(
            """
            <svg xmlns="http://www.w3.org/2000/svg" width="100" height="100">
              <text font-size="medium">x</text>
              <text font-size="large">x</text>
              <text style="font-size: xx-small">x</text>
              <text style="font: bold x-large serif">x</text>
              <text font-size="larger">x</text>
            </svg>
        """
        )
        sizes = [text.contents[0].fontSize for text in drawing.contents[0].contents]
        assert sizes == [16, 18, 9, 24, 16 * 1.2]

    def test_invalid_font_shorthand_is_ignored(self):
        drawing = drawing_from_svg(
            """
            <svg xmlns="http://www.w3.org/2000/svg" width="100" height="100">
              <text style="font-size: 20px; font: bold">x</text>
            </svg>
        """
        )
        string = drawing.contents[0].contents[0].contents[0]
        assert (string.fontName, string.fontSize) == ("Helvetica", 20)

    def test_relative_font_size_uses_parent_font_size(self):
        """Percent and em font sizes are relative to the parent's font size."""
        drawing = drawing_from_svg(
            """
            <svg xmlns="http://www.w3.org/2000/svg" width="200" height="100">
              <g font-size="20">
                <text x="10" y="50">a<tspan style="font-size:70%">b</tspan><tspan
                      font-size="2em">c<tspan font-size="50%">d</tspan></tspan></text>
                <text x="10" y="80" font-size="150%">e</text>
              </g>
            </svg>
        """
        )
        texts = drawing.contents[0].contents[0].contents
        sizes = {s.text: s.fontSize for text in texts for s in text.contents}
        assert sizes == {"a": 20, "b": 14, "c": 40, "d": 20, "e": 30}

    def test_baseline_shift_sources_and_units(self):
        drawing = drawing_from_svg(
            """
            <svg xmlns="http://www.w3.org/2000/svg" width="200" height="100">
              <style>.up { baseline-shift: super }</style>
              <text x="10" y="50" font-size="20">a<tspan
                    style="baseline-shift: sub">b</tspan><tspan
                    baseline-shift="50%">c</tspan><tspan
                    class="up">d<tspan>e</tspan>f</tspan>g</text>
            </svg>
        """
        )
        strings = drawing.contents[0].contents[0].contents
        # The text group is flipped, so a String's y is minus its baseline.
        baselines = {s.text: -s.y for s in strings}
        assert baselines == {
            "a": 50,
            "b": 60,  # sub: half the font size down
            "c": 40,  # 50% of the font size up
            "d": 40,  # super from a <style> rule
            "e": 40,  # nested in the shifted tspan
            "f": 40,  # tail text inside the shifted tspan
            "g": 50,
        }

    def test_baseline_shift_is_not_inherited_from_group(self):
        drawing = drawing_from_svg(
            """
            <svg xmlns="http://www.w3.org/2000/svg" width="200" height="100">
              <g baseline-shift="super">
                <text x="10" y="50" font-size="20">a<tspan>b</tspan></text>
              </g>
            </svg>
        """
        )
        strings = drawing.contents[0].contents[0].contents[0].contents
        assert {s.text: -s.y for s in strings} == {"a": 50, "b": 50}

    def test_tspan_position(self):
        """
        The x/y positions of a tspan are either relative to the current text
        position, or can be absoluted by specifying the x/y attributes.
        """
        drawing = drawing_from_svg(
            """
            <?xml version="1.0"?>
            <svg width="777" height="267">
              <text x="10" y="20" style="fill:#000000; stroke:none; font-size:28;">
                The start
                <tspan>TITLE 1</tspan>
                <!-- x position relative to current text position
                     y position offset in em -->
                <tspan dy="1.3em">(after title)</tspan>
                <!-- absolute position -->
                <tspan x="16.75" y="33.487">Subtitle</tspan>
                <!-- absolute position + shifting -->
                <tspan x="10" y="20" dx="3em" dy="1.5em">Complete</tspan>
                The end
              </text>
            </svg>
        """
        )
        main_group = drawing.contents[0]
        assert main_group.contents[0].contents[0].x == 10
        assert main_group.contents[0].contents[0].y == -20
        assert main_group.contents[0].contents[0].text == "The start "
        assert main_group.contents[0].contents[1].x > 10
        assert main_group.contents[0].contents[1].text == "TITLE 1"
        assert main_group.contents[0].contents[2].text == " "
        assert main_group.contents[0].contents[3].y == -20 - (1.3 * 28)
        assert main_group.contents[0].contents[3].text == "(after title)"
        assert main_group.contents[0].contents[4].text == " "
        assert main_group.contents[0].contents[5].x == 16.75
        assert main_group.contents[0].contents[5].y == -33.487
        assert main_group.contents[0].contents[5].text == "Subtitle"
        assert main_group.contents[0].contents[6].text == " "
        assert main_group.contents[0].contents[7].x == 10 + (3 * 28)
        assert main_group.contents[0].contents[7].y == -20 - (1.5 * 28)
        assert main_group.contents[0].contents[7].text == "Complete"
        assert main_group.contents[0].contents[8].text == " The end"
