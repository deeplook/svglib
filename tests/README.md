# Testing

This folder contains the test suite for `svglib`. Run everything from the
repository root with [uv](https://docs.astral.sh/uv/), which creates the
virtual environment and installs the package together with the `dev`
dependency group (pytest, pytest-cov, tox, ruff, mypy, pre-commit) on first use:

```console
$ uv run pytest
```

That is also what the CI workflows run, on Linux, macOS and Windows, with
CPython 3.10, 3.13 and 3.14 (and PyPy 3.10 on Linux). Python 3.10 is the oldest
supported version.

## Quick runs

The tests in `tests/test_samples.py` download SVG files from the internet (see
below) and are by far the slowest. For a fast run without them:

```console
$ uv run pytest --ignore=tests/test_samples.py
```

Run a single file, a single test, or tests matching a keyword:

```console
$ uv run pytest tests/test_basic.py
$ uv run pytest tests/test_basic.py::TestTextNode::test_text_path_straight_line
$ uv run pytest -k "text_path or arc"
```

## What is where

| File | What it tests |
|---|---|
| `test_basic.py` | The converter in detail: paths, shapes, text, styles, transforms, gradients, clipping, `<use>`, `<switch>`, embedded images, view boxes. |
| `test_external_references.py` | Resolution of `xlink:href` to other files, the `external_reference_root` containment, limits on `<use>` expansion and cyclic references. |
| `test_fonts.py` | Font registration and the font family mapping. |
| `test_units.py` | Length and unit conversion. |
| `test_samples.py` | Conversion of real-world SVG files (see below). |
| `utils.py` | Helpers shared by the tests, e.g. `drawing_from_svg()` and `svg_raster_difference()`. |
| `textpath_sheet.py` | Not a test: renders the `<textPath>` samples as a contact sheet. |

## Sample files and downloads

`tests/samples/` holds the SVG files used by the tests. Small ones are part of
the repository (`clipping/`, `misc/`, `others/`, `textpath/`).
`test_samples.py` also needs bigger collections, which are downloaded on the
first run into folders that are not under version control:

- `samples/wikipedia/flags` and `samples/wikipedia/symbols`, from Wikimedia,
- `samples/W3C_SVG_12_TinyTestSuite`, the W3C SVG 1.2 Tiny test suite.

Delete these folders to force a fresh download. Without an internet connection
those tests can't run.

The tests convert the files to PDF (and the W3C files to PNG as well) and leave
the results next to the SVG files, as `*-svglib.pdf`. These are ignored by git.
`tests/NOTES.md` lists files with known rendering issues, observed by eye.

## Bitmap backend

Tests that rasterize drawings, such as the clipping comparisons, need one of
ReportLab's renderPM backends and are skipped without it. To run them, install
the optional extra, which needs the Cairo development libraries:

```console
$ uv pip install -e ".[bitmaps]"
```

## Coverage

```console
$ make test
```

runs the suite with coverage, prints the lines that were not executed and
writes an HTML report to `htmlcov/`.

## Cleaning up

Delete the generated PDF files with

```console
$ make testclean
```

or, to run the cleanup hooks of the test classes instead:

```console
$ uv run pytest -v -s --override-ini=python_functions=cleanup
```

`make clean` removes caches and other temporary files, `make distclean` also
the virtual environment.

## Other checks

```console
$ make lint            # ruff format and ruff check --fix
$ make typecheck       # mypy src tests
$ make hooks           # all pre-commit hooks
$ make check-versions  # locked and installed tools above their minimum safe versions
$ make test-dist       # build the wheel, install it in a clean venv, test it there
$ make all             # lint, typecheck, hooks, check-versions and tests
```

`make test-dist` resolves the dependencies afresh, as a user would get them, and
uses Python 3.13 unless `TEST_DIST_PYTHON` says otherwise.

To run the suite on several Python versions, use [tox](https://tox.wiki/)
(the interpreters must be installed):

```console
$ uv run tox
$ uv run tox -e py312
```

## The `<textPath>` samples

`tests/samples/textpath/` has one small SVG per supported `<textPath>`
feature. The tests check that every glyph is placed. To look at the result,
render all samples into one PDF, each labeled with its file name and
description:

```console
$ uv run python -m tests.textpath_sheet textpath-sheet.pdf
```
