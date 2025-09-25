"""Testsuite for svglib.

This module tests font functionality. Run with one of these lines from
inside the test directory:

    $ make test
    $ uv run pytest -v -s test_fonts.py
"""

import subprocess
from typing import Any, Optional, Tuple

import pytest
from reportlab.pdfbase.ttfonts import TTFError, TTFOpenFile

from svglib.fonts import (
    DEFAULT_FONT_NAME,
    STANDARD_FONT_NAMES,
    FontMap,
    get_global_font_map,
)
from svglib.svglib import (
    Svg2RlgAttributeConverter,
    SvgRenderer,
    find_font,
    register_font,
)
from tests.utils import drawing_from_svg

try:
    TTFOpenFile("times.ttf")
    HAS_TIMES_FONT = True
except TTFError:
    HAS_TIMES_FONT = False


@pytest.mark.parametrize(
    "family,weight,style,expected",
    [
        ("Times New Roman", "normal", "normal", "Times New Roman"),
        ("Times New Roman", "bold", "normal", "Times New Roman-Bold"),
        ("Times New Roman", "bold", "italic", "Times New Roman-BoldItalic"),
        ("Times New Roman", "BOLD", "italic", "Times New Roman-BoldItalic"),
        ("Times New Roman", "BOld", "ITalic", "Times New Roman-BoldItalic"),
        (
            "Times New Roman",
            "DemiBold",
            "SomeStyle",
            "Times New Roman-DemiboldSomestyle",
        ),
        ("Times New Roman", "600", "SomeStyle", "Times New Roman-600Somestyle"),
        ("Times New Roman", 600, "SomeStyle", "Times New Roman-600Somestyle"),
        ("Courier New", "bold", "normal", "Courier New-Bold"),
    ],
)
def test_internal_names(family: str, weight: Any, style: str, expected: str) -> None:
    assert FontMap.build_internal_name(family, weight, style) == expected


@pytest.mark.parametrize(
    "family, path, weight, style, rlgName, expected",
    [
        # no path, no reportlab name -> None result
        ("Times New Roman", None, "normal", "normal", None, (None, False)),
        # mapping to standard font
        (
            "Times New Roman",
            None,
            "bold",
            "normal",
            "Times-Bold",
            ("Times New Roman-Bold", True),
        ),
        # mapping to standard font
        (
            "Times New Roman",
            None,
            "bold",
            "italic",
            "Times-BoldItalic",
            ("Times New Roman-BoldItalic", True),
        ),
        # may fail on systems without times.ttf
        (
            "Times New Roman",
            "times.ttf",
            "normal",
            "normal",
            None,
            ("Times New Roman", True),
        ),
        ("Unknown Font", "unknown_font.ttf", "normal", "normal", None, (None, False)),
    ],
)
def test_register_return(
    family: str,
    path: Optional[str],
    weight: str,
    style: str,
    rlgName: Optional[str],
    expected: Tuple[Optional[str], bool],
) -> None:
    """
    Check if the result of the register_font function matches the expected results
    """
    if path == "times.ttf" and not HAS_TIMES_FONT:
        pytest.skip("times.ttf is not installed on this system")
    converter = SvgRenderer("../")
    converter.attrConverter._font_map = FontMap()
    assert (
        converter.attrConverter._font_map.register_font(
            family, path, weight, style, rlgName
        )
        == expected
    )


@pytest.mark.parametrize(
    "svgname, fontname",
    [
        ("sans-serif", "Helvetica"),
        ("serif", "Times-Roman"),
        ("times", "Times-Roman"),
        ("monospace", "Courier"),
    ],
)
def test_convertFontFamily_defaults(svgname: str, fontname: str) -> None:
    attrib_converter = Svg2RlgAttributeConverter()
    name = attrib_converter.convertFontFamily(svgname)
    assert name == fontname


@pytest.mark.parametrize("fontname", list(STANDARD_FONT_NAMES))
def test_find_font_defaults(fontname: str) -> None:
    name, exact = find_font(fontname)
    assert name == fontname
    assert exact is True


def test_plain_text() -> None:
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
    assert main_group.contents[0].contents[1].fontName == DEFAULT_FONT_NAME


def test_fontfamily_text():
    drawing = drawing_from_svg(
        """
        <?xml version="1.0"?>
        <svg width="777" height="267" xml:space="preserve">
          <text style="fill:#000000; stroke:none; font-size:28;
                      font-family:'Times-Roman';">
            <tspan>TITLE    1</tspan>
            <tspan x="-10.761" y="33.487">Subtitle</tspan>
          </text>
        </svg>
    """
    )
    main_group = drawing.contents[0]
    assert main_group.contents[0].contents[1].fontName == "Times-Roman"
    drawing = drawing_from_svg(
        """
        <?xml version="1.0"?>
        <svg width="777" height="267" xml:space="preserve">
            <text style="fill:#000000; stroke:none; font-size:28;
                        font-family:'Courier';">
            <tspan>TITLE    1</tspan>
            <tspan x="-10.761" y="33.487">Subtitle</tspan>
            </text>
        </svg>
    """
    )
    main_group = drawing.contents[0]
    assert main_group.contents[0].contents[1].fontName == "Courier"


@pytest.mark.skipif(not HAS_TIMES_FONT, reason="times.ttf is not available")
def test_fontfamily_reg_text():
    name, exact = register_font("MyFont", "times.ttf")
    assert name == "MyFont"
    assert exact is True
    drawing = drawing_from_svg(
        """
        <?xml version="1.0"?>
        <svg width="777" height="267" xml:space="preserve">
          <text style="fill:#000000; stroke:none; font-size:28;font-family:'MyFont';">
            <tspan>TITLE    1</tspan>
            <tspan x="-10.761" y="33.487">Subtitle</tspan>
          </text>
        </svg>
    """
    )
    main_group = drawing.contents[0]
    assert main_group.contents[0].contents[1].fontName == "MyFont"


def test_fontfamily_weight_text():
    drawing = drawing_from_svg(
        """
        <?xml version="1.0"?>
        <svg width="777" height="267" xml:space="preserve">
          <text style="fill:#000000; stroke:none; font-size:28;
                       font-family:'Times New Roman';font-weight:bold;">
            <tspan>TITLE    1</tspan>
            <tspan x="-10.761" y="33.487">Subtitle</tspan>
          </text>
        </svg>
    """
    )
    main_group = drawing.contents[0]
    assert main_group.contents[0].contents[1].fontName == "Times-Bold"
    drawing = drawing_from_svg(
        """
        <?xml version="1.0"?>
        <svg width="777" height="267" xml:space="preserve">
            <text style="fill:#000000; stroke:none; font-size:28;
                         font-family:'Courier New';font-weight:bold;">
            <tspan>TITLE    1</tspan>
            <tspan x="-10.761" y="33.487">Subtitle</tspan>
            </text>
        </svg>
    """
    )
    main_group = drawing.contents[0]
    assert main_group.contents[0].contents[1].fontName == "Courier-Bold"
    drawing = drawing_from_svg(
        """
    <?xml version="1.0"?>
    <svg width="777" height="267" xml:space="preserve">
        <text style="fill:#000000; stroke:none; font-size:28;">
        <tspan style="font-family:'Courier New';font-weight:bold;">TITLE    1</tspan>
        <tspan x="-10.761" y="33.487">Subtitle</tspan>
        </text>
    </svg>
    """
    )
    main_group = drawing.contents[0]
    assert main_group.contents[0].contents[1].fontName == "Courier-Bold"
    drawing = drawing_from_svg(
        """
        <?xml version="1.0"?>
        <svg width="777" height="267" xml:space="preserve">
            <text style="fill:#000000; stroke:none; font-size:28;">
            <tspan style="font-family:'Courier';font-weight:bold;">TITLE    1</tspan>
            <tspan x="-10.761" y="33.487">Subtitle</tspan>
            </text>
        </svg>
    """
    )
    main_group = drawing.contents[0]
    assert main_group.contents[0].contents[1].fontName == "Courier-Bold"


def test_fontfamily_style_text():
    drawing = drawing_from_svg(
        """
        <?xml version="1.0"?>
        <svg width="777" height="267" xml:space="preserve">
          <text style="fill:#000000; stroke:none; font-size:28;
                       font-family:'Times New Roman'; font-style:italic;">
            <tspan>TITLE    1</tspan>
            <tspan x="-10.761" y="33.487">Subtitle</tspan>
          </text>
        </svg>
    """
    )
    main_group = drawing.contents[0]
    assert main_group.contents[0].contents[1].fontName == "Times-Italic"
    drawing = drawing_from_svg(
        """
        <?xml version="1.0"?>
        <svg width="777" height="267" xml:space="preserve">
            <text style="fill:#000000; stroke:none; font-size:28;
                         font-family:'Courier New'; font-style:Italic;">
            <tspan>TITLE    1</tspan>
            <tspan x="-10.761" y="33.487">Subtitle</tspan>
            </text>
        </svg>
    """
    )
    main_group = drawing.contents[0]
    assert main_group.contents[0].contents[1].fontName == "Courier-Oblique"
    drawing = drawing_from_svg(
        """
        <?xml version="1.0"?>
        <svg width="777" height="267" xml:space="preserve">
            <text style="fill:#000000; stroke:none; font-size:28;">
            <tspan style="font-family:'Courier New';font-style:italic;">
                TITLE    1
            </tspan>
            <tspan x="-10.761" y="33.487">Subtitle</tspan>
            </text>
        </svg>
    """
    )
    main_group = drawing.contents[0]
    assert main_group.contents[0].contents[1].fontName == "Courier-Oblique"


def test_fontfamily_weight_style_text():
    drawing = drawing_from_svg(
        """
        <?xml version="1.0"?>
        <svg width="777" height="267" xml:space="preserve">
          <text style="fill:#000000; stroke:none; font-size:28;
                       font-family:'Times New Roman'; font-style:italic;
                       font-weight:bold;">
            <tspan>TITLE    1</tspan>
            <tspan x="-10.761" y="33.487">Subtitle</tspan>
          </text>
        </svg>
    """
    )
    main_group = drawing.contents[0]
    assert main_group.contents[0].contents[1].fontName == "Times-BoldItalic"
    drawing = drawing_from_svg(
        """
        <?xml version="1.0"?>
        <svg width="777" height="267" xml:space="preserve">
            <text style="fill:#000000; stroke:none; font-size:28;
                         font-family:'Courier New'; font-style:Italic;
                         font-weight:BOLD;">
            <tspan>TITLE    1</tspan>
            <tspan x="-10.761" y="33.487">Subtitle</tspan>
            </text>
        </svg>
    """
    )
    main_group = drawing.contents[0]
    assert main_group.contents[0].contents[1].fontName == "Courier-BoldOblique"
    drawing = drawing_from_svg(
        """
        <?xml version="1.0"?>
        <svg width="777" height="267" xml:space="preserve">
            <text style="fill:#000000; stroke:none; font-size:28;">
            <tspan style="font-family:'Courier New';font-style:italic;
                          font-weight:bold;">TITLE    1</tspan>
            <tspan x="-10.761" y="33.487">Subtitle</tspan>
            </text>
        </svg>
    """
    )
    main_group = drawing.contents[0]
    assert main_group.contents[0].contents[1].fontName == "Courier-BoldOblique"
    drawing = drawing_from_svg(
        """
        <?xml version="1.0"?>
        <svg width="777" height="267" xml:space="preserve">
            <text style="fill:#000000; stroke:none; font-size:28;">
            <tspan style="font-family:'Courier';font-style:italic;
                          font-weight:bold;">TITLE    1</tspan>
            <tspan x="-10.761" y="33.487">Subtitle</tspan>
            </text>
        </svg>
    """
    )
    main_group = drawing.contents[0]
    assert main_group.contents[0].contents[1].fontName == "Courier-BoldOblique"


def test_failed_registration() -> None:
    fontname, exact = register_font(
        font_name="unknown path", font_path="/home/unknown_font.tff"
    )
    assert fontname is None
    assert exact is False


def test_font_family() -> None:
    def font_config_available():
        try:
            subprocess.call(["fc-match"])
        except OSError:
            return False
        return True

    converter = Svg2RlgAttributeConverter()
    # Check PDF standard names are untouched
    assert converter.convertFontFamily("ZapfDingbats") == "ZapfDingbats"
    assert converter.convertFontFamily("bilbo ZapfDingbats") == "ZapfDingbats"
    assert converter.convertFontFamily(" bilbo    ZapfDingbats  ") == "ZapfDingbats"
    assert converter.convertFontFamily(" bilbo,    ZapfDingbats  ") == "ZapfDingbats"
    if font_config_available():
        # Fontconfig will always provide at least a default font and register
        # that font under the provided font name.
        assert converter.convertFontFamily("SomeFont") == "SomeFont"
        # Should be cached anyway
        assert "SomeFont" in get_global_font_map()._map
    else:
        # Unknown fonts are converted to Helvetica by default.
        assert converter.convertFontFamily("SomeFont") == "Helvetica"
    # Check font names with spaces
    assert converter.split_attr_list("'Open Sans', Arial, 'New Times Roman'") == [
        "Open Sans",
        "Arial",
        "New Times Roman",
    ]
