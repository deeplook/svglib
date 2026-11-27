# Changelog

## Unreleased

### Fixed

- A `<use>` of a `<symbol>` with a `viewBox` now scales the symbol to its `width` and
  `height`, which are 100% of the viewport by default, with the `x` and `y` of the
  `viewBox` and its `preserveAspectRatio`, as in browsers. The `viewBox` was ignored,
  so the symbol was drawn at its own size and an icon sprite was not scaled.
- A gradient that refers with `href` to one that refers to another now takes the
  stops and the attributes of the whole chain, as in browsers. The chain was followed
  one step only, so such a gradient had no stops and was not painted (#578).
- The percentages of a gradient are now read when its units are known, which can
  be the units of the gradient it refers to with `href`: a gradient that only adds
  `x2="50%"` to one in `gradientUnits="userSpaceOnUse"` read it as a fraction of 1
  user unit, so it was a flat color over the whole shape, and now it is half of the
  viewport, as in browsers (#577).
- A `<clipPath>` with `clipPathUnits="objectBoundingBox"` is now stretched to the
  bounding box of the element it clips, for a shape and for a group, as in browsers.
  Its coordinates, which are fractions of the box, were read as user units, so the
  clip was a tiny shape at the origin and the element disappeared (#576).

## 2.5.0 (2026-11-27)

### Security

- A long `transform` attribute could make `convertTransform()` take time
  quadratic in its length: each pair of brackets rebuilt the whole string, and the
  result was checked only afterwards, so 2 MB of brackets, which a 3 KB `.svgz`
  file holds, kept `svg2rlg()` busy for minutes (CWE-407, GHSA-43qg-v5jj-vw5c). It
  is read in one pass now, with the same result. Thanks to @lanjianchun for the
  report.
- An `<image>` that refers to a fragment of the document, with `href="#id"`, was
  rendered again without the checks that `<use>` has had since 2.3.1: a cycle, such
  as an `<svg>` that contains an `<image>` that refers to it, ended in
  `RecursionError`, and a few `<image>` elements that refer to each other, each
  level to the one before it twice, took time that doubled with every level, so
  that 2 KB took hours (CWE-400, CWE-674, GHSA-cmj4-5g24-pp37, reported again as
  GHSA-4fr5-v6hm-mwjg). A cycle is now skipped and an error is logged, and all
  `<image>` targets count against the same budgets as `<use>`
  (`MAX_USE_EXPANSIONS`, `MAX_USE_CLONED_ELEMENTS`). An `<image>` that refers to an
  element that is not defined yet is skipped too, and not an `AttributeError`.
  Thanks to @GeniusKangaroo and @john-lawniczak for the reports.
- An image embedded as a `data:image/png` or `data:image/jpeg` URI was opened by
  Pillow with the decoder chosen from its bytes, not from its label, so a
  PostScript file made it run Ghostscript, where that is installed, when the PDF
  was drawn (CWE-20, CWE-94, GHSA-h5r7-mh88-vjm4). Such an image is now decoded as
  a PNG or a JPEG only (`DATA_URI_IMAGE_FORMATS`), and anything else is refused
  with the `UnidentifiedImageError` that data that is not an image already got.
  Thanks to @superbot-helper for the report.

### Tooling and housekeeping

- CI runs PyPy 3.11 on Ubuntu 24.04 instead of `ubuntu-latest`, which is Ubuntu
  26.04 now: the PyPy wheel of lxml needs `libxml2.so.2`, and 26.04 doesn't have
  it, so the PyPy job failed at import time. The other jobs follow
  `ubuntu-latest`.

### Fixed

- A gradient with `spreadMethod="reflect"` or `"repeat"` is now repeated past
  its ends, as in browsers; it was painted black there. Every other period is
  back to front for `reflect`. An unknown `spreadMethod` is `pad`, and so is a
  gradient that would need more than 200 periods, or more than 10,000 stops in
  all of them (#567).
- The `stop-color` and `stop-opacity` of a gradient stop can now be set by a
  CSS rule, such as the classes of the SVG that Illustrator exports
  (`.cls-1 { stop-color: #fff }`); the stop was black. A `<style>` element
  now applies to the whole document, including the elements before it, as in
  browsers, and not only to the gradients in its `<defs>`: a shape that comes
  before a `<style>` that styles it is no longer black (#558).
- `stop-color` set to `currentColor` in a gradient stop no longer makes
  `svg2rlg()` fail with `AttributeError`; it is the `color` of the stop, as in
  browsers, or black when none is set (#559).
- `hwb()` colors of CSS Color 4 are now converted to sRGB, as `oklch()` and
  `oklab()` are: they were not read and the shape was not drawn (#560).
- `stop-color` and `stop-opacity` of a gradient stop can now use `var()`, such as
  the `stop-color="var(--fill-0, #171D25)"` that Figma writes: the stop was
  black, and the gradient with it. A `var()` without a value is as if the
  property was not set.
- A gradient that refers to another one with `href` now takes the geometry,
  `gradientUnits` and `spreadMethod` of that gradient when it does not set them
  itself, as in browsers: it used its own defaults (`x2="1"`, `pad`,
  `objectBoundingBox`) and so a gradient set on the first one was lost (#563).
- The `offset` of a gradient stop is now limited to 0 to 1 and to at least the
  offset of the stop before it, as in browsers: a stop beyond the ends, such as
  `offset="150%"`, or before the previous one drew a different gradient (#564).
- CSS font-size keywords such as `large`, `x-small`, `larger` and `smaller`,
  in the `font-size` attribute, in `style` attributes and in the `font`
  shorthand, no longer make `svg2rlg()` fail with `ValueError`. Absolute
  keywords use the CSS Fonts values for a 16px `medium`, and `larger` and
  `smaller` scale by 1.2 (#537).
- Relative font sizes such as `70%`, `2em` and `larger` are now resolved
  against the font size of the parent element, as in CSS, instead of the
  default size, so `<tspan font-size="70%">` inside `<g font-size="20">` gets
  14 and not 70 (#327, #538).
- Color keywords and function names are now read regardless of case, as in
  CSS: `fill="White"`, `stroke="RED"`, `RGB(255, 0, 0)` and `currentcolor` no
  longer leave the shape without a fill or stroke (#541).
- The CSS named colors `rebeccapurple` and `lightgray`, which ReportLab lacks,
  are now read, and `darkseagreen` is `#8fbc8f` as in CSS, not ReportLab's
  `#8fbc8b` (#542).
- The content of a nested `<svg>` with a `viewBox` is now drawn at the size
  given by its `width` and `height`; it was drawn at 75% of that before,
  because the px-to-pt factor of the drawing was applied a second time to the
  nested viewport (#540).
- A `clip-path` given in a `style` attribute or a CSS rule, or as a quoted or
  spaced `url()` such as `url("#clip")`, now clips the element; only the
  `clip-path="url(#clip)"` attribute did before. Illustrator's CSS exports and
  svgo-optimized matplotlib charts set it in CSS (#544).
- The hue of `hsl()` and `hsla()` may now have a CSS angle unit: `deg`, `grad`,
  `rad` or `turn`. `fill="hsl(120deg, 100%, 50%)"` was drawn black instead of
  green (#543).
- A `light-dark()` color, which draw.io writes in its SVG exports, is now read
  as its first, light color, the one CSS uses when no `color-scheme` is set;
  the shape lost its fill or stroke before (#546).
- `var()` is now read, in `fill`, `stroke` and other values, as Figma and VS
  Code write colors that a theme can change, such as
  `fill="var(--fill-0, #171D25)"`: it is the custom property of the element or
  an ancestor, set in a `style` attribute or a CSS rule, or else its fallback.
  Such a value was not read and the shape was not drawn. A value that needs
  more than 1000 replacements, or becomes longer than 100,000 characters, is
  invalid, so a small SVG cannot make it take exponential time (#554).
- An `<image>` that references an SVG document now draws it in the viewport
  given by its `width` and `height`, with its own `preserveAspectRatio`, as
  browsers and Inkscape do; the document was drawn at its own size, ignoring
  the size of the `<image>` (#237, #547).
- `fill` and `stroke` set to `currentColor` in another case, such as
  `currentcolor`, or with `!important`, now use the `color` property; they were
  drawn black (#548).
- `width="auto"` and `height="auto"` on an `<svg>`, as Figma writes them, for
  instance in the country flags of the ProtonVPN apps, are now read like a
  missing `width` and `height`, also on a root `<svg>` without a `viewBox`;
  `svg2rlg()` failed with `ValueError: Can't convert 'auto' to length` (#550).
- `em` and `ex` lengths in the geometry of shapes, such as `width="2em"` or
  `r="1em"`, and in the `width` and `height` of the root `<svg>`, now use the
  font size of the element, as in CSS; they always used 16px before (#549).
- `oklch()` and `oklab()` colors of CSS Color 4, as in the social preview
  images of react-window, are now converted to sRGB: they were not read and
  the shape was not drawn (#555).
- The `x` and `y` of a `<use>`, and of an `<image>` that references SVG
  content, are now read as lengths: with a unit, such as `x="20px"` or
  `y="1in"`, or as a percentage, the content was drawn at the origin before
  (#551).
- A `<clipPath>` without any shape now clips its elements away, as in browsers,
  instead of leaving them without a clip: `clip-path="url(#clip)"` of an empty
  `<clipPath>` drew the whole element (#553).
- A gradient with no extent, that is a linear gradient with both ends in the same
  place or a radial gradient with a radius of 0, now paints the shape in the
  color of its last stop, as in browsers; it was black or the first color (#569).
- The `gradientTransform` of a linear or radial gradient is now applied, with
  `translate`, `scale`, `rotate`, `skewX`, `skewY` and `matrix`, in the units of
  the bounding box and in the user space, and it is taken from the gradient it
  refers to by `href`; it was ignored, so a gradient rotated by Figma or Illustrator
  ran in the wrong direction. A radial gradient scaled by it is an ellipse. With
  `spreadMethod` `reflect` or `repeat`, the periods that cover the shape are counted
  in the space of the gradient, and a transform that cannot be inverted, such as
  `scale(0)`, paints nothing, as in browsers (#568).
- A percentage in the coordinates or radius of a gradient with
  `gradientUnits="userSpaceOnUse"`, such as `x2="50%"` or `r="25%"`, is now a
  percentage of the viewport, as in browsers: of the width for `x1`, `x2`, `cx` and
  `fx`, of the height for `y1`, `y2`, `cy` and `fy`, and of the normalized diagonal
  for `r`. It was read as a fraction, so `x2="50%"` was half a user unit long (#570).
- The `preserveAspectRatio` of a nested `<svg>` now aligns the viewBox to the top
  for `yMin` and to the bottom for `yMax`, as in browsers; they were the other way
  round (#571).
- A radial gradient in the units of the bounding box on a shape that is not square
  is now an ellipse, and a slanted linear one is skewed, as in browsers, because the
  gradient is stretched with the bounding box; they were drawn as a circle, and with
  the lines of equal color perpendicular to the axis (#572).


## 2.4.0 (2026-11-04)

### Added

- `<textPath>` is now supported: text follows the `<path>` named by its `href`
  or `xlink:href`, with `startOffset` (a length or a percentage) and
  `text-anchor`, and styled `<tspan>` children. ReportLab can't draw text along
  a path, so each glyph is placed and rotated individually, at the point of the
  path under its midpoint; glyphs beyond the end of the path are dropped. Only
  paths of the same document can be followed, and `side`, `method`, `spacing`
  and per-glyph `dx`/`dy`/`rotate` are not supported (#298, #532).
- The plain `opacity` property is now supported, as a presentation attribute,
  in `style` attributes and in `<style>` rules, including percentages. Opacity
  composes down the tree, so a shape at 0.5 inside a group at 0.5 is drawn at
  0.25. It is applied per shape, so overlapping shapes inside a translucent
  group show through each other, and images are not affected (#109, #525,
  thanks to @Pharex38).
- The CSS `font` shorthand is now expanded into `font-style`, `font-weight`,
  `font-size` and `font-family`, in `style` attributes and in `<style>` rules.
  Invalid shorthands are ignored (#343, #526, thanks to @Pharex38).

### Removed

- Dropped support for **Python 3.9** (and PyPy 3.9). pip 26.2.2, the new
  minimum safe version, requires Python 3.10 or newer. `requires-python` is now
  `>=3.10`, the 3.9 classifier is gone, and CI no longer tests 3.9 or PyPy 3.9.

### Tooling and housekeeping

- CI now fails if a locked or installed dependency, or the uv binary, is below
  its minimum safe version (`scripts/check_min_versions.py`).
- CI runs the lowest supported Python, 3.10, next to 3.13, 3.15 and PyPy 3.11.
  Python 3.15 is declared supported (classifier and tox).
- `make install` installs the dev dependency group (it used the `dev` extra,
  which doesn't exist), `make uninstall` no longer passes an option that
  `uv pip` doesn't know, and `make test-dist` works: `scripts/test-dist.sh`
  builds the wheel and tests it in a clean virtual environment. New:
  `make check-versions`.
- `tests/test_basic.py` is split into modules by topic (`test_paths.py`,
  `test_text.py`, `test_text_path.py`, `test_use.py`, `test_gradients.py`, ...).
  The tests that download files carry the pytest marker `network`, so
  `pytest -m "not network"` (or `make test-fast`) skips them.
- `tests/test_public_api.py` records the names, signatures and class members
  of `svglib`, `svglib.svglib`, `svglib.utils` and `svglib.fonts` in
  `tests/public_api.json`, so that restructuring the modules can't silently
  change what user code can import.
- The READMEs and notes in `demos/` and `tests/` are Markdown now, and the
  testing instructions describe the current uv and Makefile based workflow.

### Fixed

- A `style` attribute or `<style>` rule whose value contains a colon or a
  semicolon, such as `cursor: url(http://example.com/c.cur), auto` or a data
  URL, no longer makes `svg2rlg()` fail with `ValueError` or truncates the
  value. Declarations are now parsed with `tinycss2`, malformed ones are
  skipped, and `!important` and comments are no longer part of the value
  (#527, thanks to @Pharex38).
- `baseline-shift` on text is now also read from `style` attributes and
  `<style>` rules, and a percentage is taken relative to the font size instead
  of being used as a length in user units. A value on an enclosing `<g>` does
  not affect the text, as the property is not inherited (#528, thanks to
  @Pharex38).
- `stroke-dasharray` values that SVG calls invalid (any negative length, or a
  list that sums to zero) no longer produce an invalid PDF dash pattern and
  raise `ValueError` while rendering; they give a solid line. `none` no longer
  relies on a swallowed exception, and an odd number of values is repeated once
  to make it even, as the specification requires (#529, thanks to @Pharex38).

## 2.3.3 (2026-11-04)

### Security

- The limit on `<use>` expansions added in 2.3.1 counted expansions, not their
  size. Each expansion copies and renders the whole element it refers to, so
  a few kilobytes of nested `<use>` groups with a large group at the bottom
  could still take minutes and gigabytes to render (CWE-400,
  GHSA-xpfm-fw4h-qxwv, an incomplete fix of GHSA-555j-qj3j-c8jv). The elements
  copied by all expansions of a document, external SVGs included, are now
  limited too (`MAX_USE_CLONED_ELEMENTS`, 20,000); once it is spent the
  remaining `<use>` elements are skipped and an error is logged. Thanks to
  Adrian Korwel (@adriank31) for the report.

## 2.3.2 (2026-10-23)

### Security

- A long run of digits in the arguments of a path arc command (`A` or `a`)
  could make parsing take exponential time, so a tiny SVG could block a
  process for minutes or longer (CWE-1333, CWE-400, GHSA-249c-7rgc-f52h).
  Arc arguments are now read one token at a time, without regex backtracking.
  Parsing of a malformed arc stops at the first argument that does not fit.

### Fixed

- Accept explicit plus signs on arc rotation and endpoints, and tab, carriage
  return and line feed separators in transform arguments, as allowed by SVG
  (#524, thanks to @jdotc1).
- `svg2rlg()` no longer unpacks a `.svgz` file to a sibling `.svg` file, which
  overwrote an existing file of that name and then deleted it. The compressed
  data is now read as a stream (#518, thanks to @jdotc1).
- A `<use>` that refers to itself, or to a cycle of elements that each `<use>`
  the next one, no longer crashes with `RecursionError`. The offending `<use>`
  is skipped and an error is logged, as already done for cyclic references
  between external files (#519, thanks to @gistrec for the report).

## 2.3.1 (2026-10-22)

### Security

- Rendering an SVG could be made to take exponential time and memory through
  nested `<use>` elements, where each level references a group containing many
  `<use>` elements of the previous level (CWE-400, GHSA-555j-qj3j-c8jv).
  `renderUse()` now stops after `MAX_USE_EXPANSIONS` (10,000) expansions per
  document, logs one error and skips the remaining `<use>` elements. The budget
  is shared with the renderers of external SVG files, so referencing many
  external files does not reset it.

## 2.3.0 (2026-10-05)

### Security

- External `<image>`/`<use>` references can no longer escape the document's own
  directory. `xlink_href_target()` joined the reference onto the source
  directory and only checked `os.access()`, so an absolute reference discarded
  that directory and `..` climbed above it, letting an untrusted SVG name any
  file the process could read (CWE-22, GHSA-2p5c-8vcc-4rcw). Absolute
  references are now refused, and the new opt-in `external_reference_root` on
  `svg2rlg()`/`SvgRenderer` confines resolution to a trusted directory,
  propagated into nested external-SVG renderers. Relative references, including
  `..`, keep working by default.

- The `svg2pdf` command line tool now sets `external_reference_root` to the
  input file's own directory, since a file converted from the command line is
  routinely one the user did not author. Pass `-R`/`--external-root` with a
  parent directory to allow shared assets, or `/` to allow any relative
  reference. Library callers are unaffected: the default stays `None`.

## 2.2.0 (2026-08-14)

### Tooling and housekeeping

- Modernized type annotations across `src/svglib/` and `tests/` to use PEP
  585 builtin generics (`list[...]`, `dict[...]`, `tuple[...]`, `set[...]`)
  instead of `typing.List`/`Dict`/`Tuple`/`Set`, and simplified a few
  emptiness/membership checks (`not points` instead of `len(points) == 0`,
  a set literal instead of a list for `in` checks). No behavior change.
- Silenced a `UserWarning` from `test_convert_pdf_png` that came from
  ReportLab's own `renderPM.drawImage`, not from svglib: it reopens a
  `<image>` file referenced by path and converts it straight to RGB without
  normalizing palette-with-transparency PNGs first, unlike svglib's own
  handling of base64-embedded images. The referenced PNG (a dedicated
  tRNS-chunk test fixture) still renders correctly; there was nothing to fix
  in svglib's output.

### Fixed

- `font-size` no longer has `PX_TO_PT` applied twice. The viewport group
  already carries the conversion, but `String.fontSize` and the advance widths
  used to position text fragments were converted to points as well. Text
  therefore rendered at 0.75x the size of the geometry in the same document,
  and multi-`tspan` runs were laid out in the wrong unit (issue #502). Both now
  stay in user units, like every other coordinate below the transform.
  `String.fontSize` in the shape tree is in user units accordingly; multiply by
  the enclosing group's transform to get the rendered size.

## 2.1.0 (2026-08-01)

### Added

- Declared support for **Python 3.14** (added the classifier and CI matrix
  entry across Ubuntu, macOS, and Windows, alongside the existing 3.9–3.13).
- **Clipping paths** now support `<circle>`, `<ellipse>`, and `<polygon>` clip
  shapes, in addition to paths and rectangles, and clipping masks referenced
  from within a `<use>` element.
- Transforms are now applied to clipping-path shapes, fixing clip paths that
  relied on previously unsupported transforms (issue #366).
- The gradient shape classes now implement `getBounds()`, so drawings that
  contain gradient fills can be measured — for example when used as a flowable
  by rst2pdf (issue #466).

### Changed

- Renamed the gradient shape classes `_LinearGradientShape` and
  `_RadialGradientShape` to `LinearGradientShape` and `RadialGradientShape`.
  They appear in the rendered `Drawing` tree and were never meant to be
  private, so the leading underscore was misleading.

### Removed

- Removed the deprecated `_LinearGradientShape` and `_RadialGradientShape`
  aliases. Use `LinearGradientShape` and `RadialGradientShape` instead.

### Fixed

- The `visibility` property is now respected on shapes. Elements with
  `visibility="hidden"` (or `collapse`), set directly or inherited from an
  ancestor, were still rendered (issue #359).

- `display: none` set through a `style` attribute is now respected. Only the
  `display` presentation attribute was read, so `<g style="display:none">` and
  `<rect style="display:none"/>` were still rendered (issue #401).

- Embedded `<image>` geometry is no longer truncated to whole points. The
  `x`, `y`, `width`, and `height` of an SVG `<image>` were each passed through
  `int()`, so a raster placed at fractional coordinates landed up to ~1pt away
  from a vector element with identical coordinates. Because width/height were
  truncated too, the error grew across the image rather than being a constant
  shift (issue #490).
- `font-family` values are now split per CSS instead of on whitespace. An
  unquoted multi-word name such as `font-family: Cascadia Code` was split into
  `Cascadia` and `Code`, so a font registered under its full name was never
  found (issue #374). Commas inside a quoted name (`font-family: "Foo, Bar",
  Arial`) no longer split the list either; that previously handed `shlex` an
  unbalanced quote and raised `ValueError: No closing quotation`, aborting the
  conversion of a valid value.
- Replaced `locale.getdefaultlocale()` (used for `<switch>` `systemLanguage`
  matching) with a small environment-variable lookup. `getdefaultlocale()` is
  deprecated and is **removed in Python 3.15**; the replacement keeps the same
  behaviour, emits no deprecation warning on 3.12–3.14, and adds unit tests for
  the language-matching path.
- Clipping paths now support the `clip-rule` attribute instead of incorrectly
  using `fill-rule` (issue #485).
- `fill="url(...)"` and gradient `xlink:href` values are now matched correctly
  when the referenced id is quoted (`url('#name')`, `url("#name")`) or
  contains a right parenthesis; the previous regex rejected or truncated
  these forms.
- Rendering to `reportlab.graphics.renderSVG.SVGCanvas` (as used by
  `easy-thumbnails[svg]`) no longer raises
  `AttributeError: 'SVGCanvas' object has no attribute 'beginPath'` when
  drawing a clipped gradient; that canvas doesn't implement `beginPath()`,
  so the gradient's clip path is now skipped on it instead of erroring.

### Type safety and internal quality (no behavior change)

- Completed static type annotations for `svglib.py`; the package now passes
  `mypy --strict` on its own source, with a single documented per-module
  override for the untyped reportlab/cssselect2 base classes it subclasses.
- Pinned a `[tool.mypy]` configuration in `pyproject.toml` and now enforce mypy
  in CI (new `type-check.yml` workflow) and via a local pre-commit hook, so type
  regressions fail before merge.
- Tightened internal gradient handling types: parsed gradient definitions now
  use a `TypedDict` instead of an opaque `Dict[str, Any]`, and the internal
  group/parent parameters are typed as `Optional[Group]`.
- Added docstrings to the remaining undocumented functions in `svglib.py`,
  bringing documentation coverage to 100%.

### Tooling and housekeeping

- Removed the DeepSource configuration. Its checks were redundant with ruff,
  `mypy --strict`, CodeQL, and the pytest matrix, and only produced recurring
  noise on pull requests.
- Removed the long-defunct `uniconv` sample tests. They contained no assertions
  and shelled out to UniConvertor, an abandoned Python 2 tool, so they had been
  permanently skipped.
- Fixed and revived the Windows CI workflow. It was a disabled placeholder that
  compiled GTK/Cairo from source (a ~20–40 minute step); it now runs a real
  CPython 3.9/3.13 matrix in well under a minute by dropping the source build
  and skipping the network-heavy sample tests on Windows (they already run on
  Ubuntu and macOS). The redundant manual Windows workflow was removed.

## 2.0.2 (2026-06-18)

Supply-chain hygiene release — no code changes.

The 2.0.1 PyPI attestation was generated by a manual `workflow_dispatch` run
from `refs/heads/main` that raced ahead of the release event. As a result the
Sigstore certificate embedded in the PEP 740 attestation identified
`refs/heads/main` as the source rather than `refs/tags/v2.0.1`, making it
impossible to verify the package against the tagged commit. This release is
published exclusively via the `release: [published]` trigger so the attestation
identity is `refs/tags/v2.0.2`.

## 2.0.1 (2026-06-17)

Supply-chain hygiene release — no code changes.

This release replaces 2.0.0, which was published directly with `uv publish`
and therefore lacked the PEP 740 provenance attestation that was present in
1.6.0. Releases must be triggered via the GitHub Actions release workflow
(`publish-to-pypi.yml`), which uses PyPI Trusted Publishing (OIDC) to produce
a SLSA Level 3 attestation. Publishing locally — even with
`uv publish --trusted-publishing` — relies on a local OAuth identity and does
not meet that bar.

- Declare `pillow>=9.0.0` as a direct dependency; it was previously an
  undeclared transitive dependency pulled in by reportlab (#463).

## 2.0.0 (2026-06-16)

Identical to 2.0b1 in terms of code; this release promotes the beta to a
stable release and converts the project documentation files from RST to
Markdown format.

## 2.0b1 (2026-05-26)

**Breaking change — output sizes will differ from 1.x.**

svglib now correctly maps SVG user units to ReportLab points using the
standard SVG/CSS conversion factor: 1 px = 0.75 pt (96 dpi). Previous
releases treated 1 user unit as 1 pt, which is 33 % too large. Any SVG
whose `width`/`height` or `viewBox` uses user units or `px` will
produce a PDF that is 75 % of its previous linear dimensions (same
proportions, correct physical size).

*Migration* — if you need to preserve the old apparent size, scale the
returned `Drawing` object before use:

```python
from svglib.svglib import svg2rlg

drawing = svg2rlg("file.svg")
# Restore 1.x dimensions (1 user unit → 1 pt, non-spec):
factor = 4 / 3          # 1 / 0.75
drawing.width  *= factor
drawing.height *= factor
drawing.scale(factor, factor)
```

- Add support for SVG 2 length units: `rem`, `vw`, `vh`, `vmin`,
  `vmax`, and `q` (quarter-millimetre) in `convertLength` (#449).
- `rem` now resolves against the root `<svg>` element's `font-size`
  (falling back to the CSS default of 16 px when not set).
- Warn when loading SVGs created with Inkscape < 0.92, which used a
  non-standard 90 dpi reference resolution (#452).
- Move `rlpycairo` to the `bitmaps` extra, so Cairo is no longer part of
  the default installation path.
- Fix inconsistent unit handling: bare numbers and `px` units now produce
  identical output, as required by the SVG spec (§5.9.2). `convertLength`
  now returns user units (px) instead of ReportLab points; a new
  `convertLengthToPt` helper is used where absolute point values are needed
  (font sizes, canvas dimensions) (#439).
- Fix SVGs with a `viewBox` but no explicit `width`/`height`: the
  viewport scale now defaults to `PX_TO_PT` (0.75) instead of 1, preventing
  content from being cropped.
- Add support for SVG `linearGradient` and `radialGradient` paint servers
  (#442).
- Add support for SVG `<switch>` elements with conditional rendering (#441).
- Fix `fill-rule` handling for paths by setting ReportLab `fillMode`
  directly (#440).
- Fix case-insensitive font family lookup in `FontMap` (#433, #435).
- Fix fontconfig handling when resolved fonts use non-normal weight or style.
- Improve missing font warnings by pointing users to `register_font()`.
- Harden `fc-match` calls by resolving the executable path and passing
  arguments after `--`.
- Fixed a SVG path interpretation bug with two successive M or m commands
  (#414).

## 1.6.0 (2025-09-25)

- Replace setup.py with pyproject.toml, rework GitHub workflows (#405).
- Drop support for Python 3.8.
- Modernize codebase, added type annotations, expanded docstrings, etc.
- Add a Makefile.
- Add publishing workflows.
- Remove dunder constants and use importlib.metadata to get the version number.
- Add `rlpycairo` as a dependency, which made Cairo part of the default
  installation path.

## 1.5.1 (2023-01-07)

- Final fix to conversion from shorthand quadratic to cubic bézier (#372).

## 1.5.0 (2023-01-05)

- Add support for `ex` units (assuming for em/2).
- Add support for `image/jpg` embedded images (in addition to `image/jpeg`).
- Avoid crash on `@import` rules in stylesheets. The rules are simply ignored
  (#285).
- Fix conversion from shorthand quadratic to cubic bézier (#364).

## 1.4.1 (2022-08-05)

- No source code changes, only fixed a leftover set_trace() in the released code
  (#352).

## 1.4.0 (2022-08-05)

- Include `tests/samples/others/*.svg` in source distribution (#341).
- Render leading and trailing text content in text nodes (#343).
- Better integration with cssselect2 to support a wider range of CSS selectors
  (#346).

## 1.3.0 (2022-05-18)

- Support mmult import from reportlab < 3.5.61 (#316).
- Make zero-length Line, PolyLine and Polygon appear in PDFs when their stroke
  value is non-zero (#319).
- `<symbol>` nodes now only appears in documents when they are
  referenced, not on their initial appearance (#328).
- If only rx or ry is defined on a `<rect>`, the value is used for both.
- Support non-prefixed `href` attribute added in SVG 2 (#330).
- Fixed parsing of empty SVG style nodes (#325).
- Handle content of multiple SVG style nodes (#326).
- Better font caching for some font names (#338).

## 1.2.1 (2022-01-27)

- Revert to scripts usage instead of console_scripts during setup (#313).

## 1.2.0 (2022-01-20)

- dropped support for Python 3.6 and added official support for Python 3.10.
- improved support for scientific notation in paths (#277)
- if some path has a color with alpha value, it also sets the default fill or
  stroke opacity of the resulting object.
- matrix transforms on groups are combined with other transforms instead of
  replacing them.

## 1.1.0 (2021-04-10)

- honor cascading when applying CSS rules (#253)
- ignore !important statement in CSS values (#227)
- svg2rlg accept pathlib.Path input (#97)
- better handling of font variants (bold, italic)
- a demo for using svglib inside a Streamlit application in /demos
- add a svg2pdf man page
- dropped official support for Python 3.5 and modernized to 3.6+
- added official support for Python 3.9.

## 1.0.1 (2020-08-26)

- avoid stroking clipping paths (#238)
- when converting percentage values in embedded SVGs, consider the direct svg
  parent node (#246)
- fixed rounded rects artifacts when rx/ry values are too high (#250)
- avoid stroking rects when strokeWidth is 0 (#250)

## 1.0.0 (2020-03-22)

- dropped Python 2 support
- fixed references to `<defs>` content when placed middle or end of
  SVG documents (#225)
- fixed elliptic arcs reading when arc flags are condensed (#232)

## 0.9.4 (2020-03-22)

- disabled external entity loading by default (#229 - CVE-2020-10799)

## 0.9.3 (2019-11-02)

- WARNING: this is the last release supporting Python 2!
- added support for more color values (hex with alpha, rgba(), etc.)
  (#213, #115)
- handle text positioning when x, y, dx, dy have a list of values
- fixed styles precedence issue (#211)

## 0.9.2 (2019-07-12)

- fixed license mention in the svg2pdf script (#194)
- support the whole range of HTML color names for color styles (#203)
- fixed a division by zero error when width/height are missing in main viewBox
  (#195)

## 0.9.1 (2019-06-22)

- fixed rendering of circular arcs in some edge cases (#189)
- support for percentage attribute values has been added (#141)
- SVG viewbox is now properly scaled to its width/height attributes (#121)
- embedded external SVG files or file fragments are now rendered (#175)
- support `<rect>` as a clipping source
- prevented crash when a relative file path is used in a memory-only SVG
  source (#173)
- fixed image translation (by y value instead of x)

## 0.9.0 (2018-12-08)

- fixed svgz output on Python 3
- kept PDF standard fonts untouched (#89)
- added basic support for non-standard fonts (#89, #107)
- allowed list of font names
- better merge style attributes from parent nodes (#119)
- fixed crash with strings in transform parameters
- handled PNGs embedded in SVG sources (#93)
- improved scaling of embedded SVGs (#124)
- added millimeter unit support
- fixed crash in elliptical arc calculation (#117)
- added experimental support for CSS style sheets (#111)
- allowed decimal percentage values in rgb colors

## 0.9.0b0 (2018-08-19)

- countless improvements to be hopefully listed in more detail in 0.9.0

## 0.8.1 (2017-04-22)

- added support for the `stroke-opacity` property
- added basic em unit support for text placement
- added respecting absolute coordinates for tspan
- fixed crash with empty path definitions
- symbol definitions are considered when referenced in nodes
- fixed compatibility with recent ReportLab versions

## 0.8.0 (2017-01-23)

This release introduces *many* contributions by Claude Paroz, who
stepped forward to give this project a long needed overhaul after ca.
six years of taking a nap, for which I'm really very grateful! Thanks,
Claude!

- moved repository to https://github.com/deeplook/svglib
- skipped version 0.7.0 to indicate tons of fixes regarding the points below
- added support for elliptical arcs
- fixed open/closed path issues
- fixed clip path issues
- fixed text issues
- replaced `minidom` with `lxml`
- added `logging` support
- added a few more sample SVG files
- migrated test suite from unittest to pytest
- improved test documentation

## 0.6.3 (2010-03-02)

- frozen last version maintained at https://bitbucket.org/deeplook/svglib/

Sadly, no condensed changelog exists prior to version 0.6.3.
