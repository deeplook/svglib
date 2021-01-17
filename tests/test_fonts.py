import pytest
from svglib.svglib import register_font, find_font, SvgRenderer, Svg2RlgAttributeConverter, STANDARD_FONT_NAMES, svg2rlg, DEFAULT_FONT_NAME, FontMap
import io
import textwrap
from lxml import etree


@pytest.mark.parametrize("family,weight,style,expected", [
    ("Times New Roman","normal", "normal", "Times New Roman"),
    ("Times New Roman","bold", "normal", "Times New Roman-Bold"),
    ("Times New Roman","bold", "italic", "Times New Roman-BoldItalic"),
    ("Times New Roman","BOLD", "italic", "Times New Roman-BoldItalic"),
    ("Times New Roman","BOld", "ITalic", "Times New Roman-BoldItalic"),
    ("Times New Roman","DemiBold", "SomeStyle", "Times New Roman-DemiboldSomestyle"),
    ("Times New Roman", "600", "SomeStyle", "Times New Roman-600Somestyle"),
    ("Times New Roman",600, "SomeStyle", "Times New Roman-600Somestyle"),
    ("Courier New","bold", "normal", "Courier New-Bold"),
])
def test_internal_names(family, weight, style, expected):
    assert FontMap.build_internal_name(family, weight, style) == expected


@pytest.mark.parametrize("family, path, weight, style, rlgName, expected", [
    ("Times New Roman", None, "normal", "normal", None,  None), # no path, no reportlab name -> None result
    ("Times New Roman", None, "bold", "normal", "Times-Bold", ("Times New Roman-Bold", True)), # mapping to standard font 
    ("Times New Roman", None, "bold", "italic", 'Times-BoldItalic', ("Times New Roman-BoldItalic", True)),  # mapping to standard font 
    ("Times New Roman", 'times.ttf', "normal", "normal", None, ("Times New Roman", True)), # may fail on systems without times.ttf
    ("Unknown Font", 'unknown_font.ttf', "normal", "normal", None, (None, False))])
def test_register_return(family, path, weight, style,rlgName, expected):
    """
    Check if the result of the register_font function matches the expected results
    """
    converter = SvgRenderer('../')
    converter.font_map = FontMap()
    assert converter.font_map.register_font(family, path, weight, style, rlgName) == expected


@pytest.mark.parametrize("svgname, fontname", [
    ("sans-serif", "Helvetica"), 
    ("serif", "Times-Roman"), 
    ("times", "Times-Roman"), 
    ("monospace", "Courier"),
    ])
def test_convertFontFamily_defaults(svgname, fontname):
    attrib_converter = Svg2RlgAttributeConverter()
    name = attrib_converter.convertFontFamily(svgname)
    assert name == fontname


@pytest.mark.parametrize("fontname", list(STANDARD_FONT_NAMES)
    )
def test_find_font_defaults(fontname):    
    name, exact = find_font(fontname)
    assert name == fontname
    assert exact == True


def test_plain_text():
    drawing = svg2rlg(io.StringIO(textwrap.dedent(u'''\
            <?xml version="1.0"?>
            <svg width="777" height="267" xml:space="preserve">
              <text style="fill:#000000; stroke:none; font-size:28;">
                <tspan>TITLE    1</tspan>
                <tspan x="-10.761" y="33.487">Subtitle</tspan>
              </text>
            </svg>
        ''')))
    main_group = drawing.contents[0]
    assert main_group.contents[0].contents[1].fontName == DEFAULT_FONT_NAME

def test_fontfamily_text():
    drawing = svg2rlg(io.StringIO(textwrap.dedent(u'''\
            <?xml version="1.0"?>
            <svg width="777" height="267" xml:space="preserve">
              <text style="fill:#000000; stroke:none; font-size:28;font-family:'Times-Roman';">
                <tspan>TITLE    1</tspan>
                <tspan x="-10.761" y="33.487">Subtitle</tspan>
              </text>
            </svg>
        ''')))
    main_group = drawing.contents[0]
    assert main_group.contents[0].contents[1].fontName == 'Times-Roman'
    drawing = svg2rlg(io.StringIO(textwrap.dedent(u'''\
        <?xml version="1.0"?>
        <svg width="777" height="267" xml:space="preserve">
            <text style="fill:#000000; stroke:none; font-size:28;font-family:'Courier';">
            <tspan>TITLE    1</tspan>
            <tspan x="-10.761" y="33.487">Subtitle</tspan>
            </text>
        </svg>
    ''')))
    main_group = drawing.contents[0]
    assert main_group.contents[0].contents[1].fontName == 'Courier'


def test_fontfamily_reg_text():
    name, exact = register_font('MyFont', 'times.ttf')
    assert name == 'MyFont'
    assert  exact == True
    drawing = svg2rlg(io.StringIO(textwrap.dedent(u'''\
            <?xml version="1.0"?>
            <svg width="777" height="267" xml:space="preserve">
              <text style="fill:#000000; stroke:none; font-size:28;font-family:'MyFont';">
                <tspan>TITLE    1</tspan>
                <tspan x="-10.761" y="33.487">Subtitle</tspan>
              </text>
            </svg>
        ''')))
    main_group = drawing.contents[0]
    assert main_group.contents[0].contents[1].fontName == 'MyFont'


def test_fontfamily_weight_text():
    drawing = svg2rlg(io.StringIO(textwrap.dedent(u'''\
            <?xml version="1.0"?>
            <svg width="777" height="267" xml:space="preserve">
              <text style="fill:#000000; stroke:none; font-size:28;font-family:'Times New Roman';font-weight:bold;">
                <tspan>TITLE    1</tspan>
                <tspan x="-10.761" y="33.487">Subtitle</tspan>
              </text>
            </svg>
        ''')))
    main_group = drawing.contents[0]
    assert main_group.contents[0].contents[1].fontName == 'Times-Bold'
    drawing = svg2rlg(io.StringIO(textwrap.dedent(u'''\
        <?xml version="1.0"?>
        <svg width="777" height="267" xml:space="preserve">
            <text style="fill:#000000; stroke:none; font-size:28;font-family:'Courier New';font-weight:bold;">
            <tspan>TITLE    1</tspan>
            <tspan x="-10.761" y="33.487">Subtitle</tspan>
            </text>
        </svg>
    ''')))
    main_group = drawing.contents[0]
    assert main_group.contents[0].contents[1].fontName == 'Courier-Bold'
    drawing = svg2rlg(io.StringIO(textwrap.dedent(u'''\
    <?xml version="1.0"?>
    <svg width="777" height="267" xml:space="preserve">
        <text style="fill:#000000; stroke:none; font-size:28;">
        <tspan style="font-family:'Courier New';font-weight:bold;">TITLE    1</tspan>
        <tspan x="-10.761" y="33.487">Subtitle</tspan>
        </text>
    </svg>
    ''')))
    main_group = drawing.contents[0]
    assert main_group.contents[0].contents[1].fontName == 'Courier-Bold'
    drawing = svg2rlg(io.StringIO(textwrap.dedent(u'''\
        <?xml version="1.0"?>
        <svg width="777" height="267" xml:space="preserve">
            <text style="fill:#000000; stroke:none; font-size:28;">
            <tspan style="font-family:'Courier';font-weight:bold;">TITLE    1</tspan>
            <tspan x="-10.761" y="33.487">Subtitle</tspan>
            </text>
        </svg>
    ''')))
    main_group = drawing.contents[0]
    assert main_group.contents[0].contents[1].fontName == 'Courier-Bold'

def test_fontfamily_style_text():
    drawing = svg2rlg(io.StringIO(textwrap.dedent(u'''\
            <?xml version="1.0"?>
            <svg width="777" height="267" xml:space="preserve">
              <text style="fill:#000000; stroke:none; font-size:28;font-family:'Times New Roman';font-style:italic;">
                <tspan>TITLE    1</tspan>
                <tspan x="-10.761" y="33.487">Subtitle</tspan>
              </text>
            </svg>
        ''')))
    main_group = drawing.contents[0]
    assert main_group.contents[0].contents[1].fontName == 'Times-Italic'
    drawing = svg2rlg(io.StringIO(textwrap.dedent(u'''\
        <?xml version="1.0"?>
        <svg width="777" height="267" xml:space="preserve">
            <text style="fill:#000000; stroke:none; font-size:28;font-family:'Courier New';font-style:Italic;">
            <tspan>TITLE    1</tspan>
            <tspan x="-10.761" y="33.487">Subtitle</tspan>
            </text>
        </svg>
    ''')))
    main_group = drawing.contents[0]
    assert main_group.contents[0].contents[1].fontName == 'Courier-Oblique'
    drawing = svg2rlg(io.StringIO(textwrap.dedent(u'''\
        <?xml version="1.0"?>
        <svg width="777" height="267" xml:space="preserve">
            <text style="fill:#000000; stroke:none; font-size:28;">
            <tspan style="font-family:'Courier New';font-style:italic;">TITLE    1</tspan>
            <tspan x="-10.761" y="33.487">Subtitle</tspan>
            </text>
        </svg>
    ''')))
    main_group = drawing.contents[0]
    assert main_group.contents[0].contents[1].fontName == 'Courier-Oblique'


def test_fontfamily_weight_style_text():
    drawing = svg2rlg(io.StringIO(textwrap.dedent(u'''\
            <?xml version="1.0"?>
            <svg width="777" height="267" xml:space="preserve">
              <text style="fill:#000000; stroke:none; font-size:28;font-family:'Times New Roman';font-style:italic;font-weight:bold;">
                <tspan>TITLE    1</tspan>
                <tspan x="-10.761" y="33.487">Subtitle</tspan>
              </text>
            </svg>
    ''')))
    main_group = drawing.contents[0]
    assert main_group.contents[0].contents[1].fontName == 'Times-BoldItalic'
    drawing = svg2rlg(io.StringIO(textwrap.dedent(u'''\
        <?xml version="1.0"?>
        <svg width="777" height="267" xml:space="preserve">
            <text style="fill:#000000; stroke:none; font-size:28;font-family:'Courier New';font-style:Italic;font-weight:BOLD;">
            <tspan>TITLE    1</tspan>
            <tspan x="-10.761" y="33.487">Subtitle</tspan>
            </text>
        </svg>
    ''')))
    main_group = drawing.contents[0]
    assert main_group.contents[0].contents[1].fontName == 'Courier-BoldOblique'
    drawing = svg2rlg(io.StringIO(textwrap.dedent(u'''\
        <?xml version="1.0"?>
        <svg width="777" height="267" xml:space="preserve">
            <text style="fill:#000000; stroke:none; font-size:28;">
            <tspan style="font-family:'Courier New';font-style:italic;font-weight:bold;">TITLE    1</tspan>
            <tspan x="-10.761" y="33.487">Subtitle</tspan>
            </text>
        </svg>
    ''')))
    main_group = drawing.contents[0]
    assert main_group.contents[0].contents[1].fontName == 'Courier-BoldOblique'
    drawing = svg2rlg(io.StringIO(textwrap.dedent(u'''\
        <?xml version="1.0"?>
        <svg width="777" height="267" xml:space="preserve">
            <text style="fill:#000000; stroke:none; font-size:28;">
            <tspan style="font-family:'Courier';font-style:italic;font-weight:bold;">TITLE    1</tspan>
            <tspan x="-10.761" y="33.487">Subtitle</tspan>
            </text>
        </svg>
    ''')))
    main_group = drawing.contents[0]
    assert main_group.contents[0].contents[1].fontName == 'Courier-BoldOblique'
