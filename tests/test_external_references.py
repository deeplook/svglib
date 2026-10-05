"""Testsuite for the resolution of external <image>/<use> references.

Rendering an SVG that came from an untrusted source must not let that SVG pull
in files from outside the directory it lives in. Run with:

    $ uv run pytest -v -s tests/test_external_references.py
"""

import logging
import os
import sys

import svglib as svglib_pkg
from svglib import svglib

DOC = """<?xml version="1.0"?>
<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink"
     width="64" height="64">
  <image xlink:href="{href}" width="64" height="64"/>
</svg>
"""

TARGET = """<?xml version="1.0"?>
<svg xmlns="http://www.w3.org/2000/svg" width="64" height="64">
  <rect width="64" height="64" fill="#b8393d"/>
</svg>
"""


def build_tree(tmp_path):
    """Lay out an "uploads" directory with a file sitting outside of it."""
    uploads = tmp_path / "uploads"
    outside = tmp_path / "outside"
    uploads.mkdir()
    outside.mkdir()
    (outside / "target.svg").write_text(TARGET)
    (uploads / "target.svg").write_text(TARGET)
    return uploads, outside


def resolved(path, **kwargs):
    """Return True if the referenced file made it into the drawing."""
    drawing = svglib.svg2rlg(str(path), **kwargs)
    return bool(drawing.contents[0].contents)


class TestExternalReferences:
    def test_absolute_reference_is_refused(self, tmp_path):
        uploads, outside = build_tree(tmp_path)
        doc = uploads / "doc.svg"
        doc.write_text(DOC.format(href=outside / "target.svg"))
        assert resolved(doc) is False

    def test_relative_reference_still_resolves(self, tmp_path):
        uploads, _ = build_tree(tmp_path)
        doc = uploads / "doc.svg"
        doc.write_text(DOC.format(href="target.svg"))
        assert resolved(doc) is True

    def test_parent_reference_still_resolves_without_a_root(self, tmp_path):
        # Documents legitimately share assets through "../"; the default must
        # keep rendering them.
        uploads, _ = build_tree(tmp_path)
        doc = uploads / "doc.svg"
        doc.write_text(DOC.format(href=os.path.join("..", "outside", "target.svg")))
        assert resolved(doc) is True

    def test_parent_reference_is_refused_under_a_root(self, tmp_path):
        uploads, _ = build_tree(tmp_path)
        doc = uploads / "doc.svg"
        doc.write_text(DOC.format(href=os.path.join("..", "outside", "target.svg")))
        assert resolved(doc, external_reference_root=str(uploads)) is False

    def test_in_root_reference_resolves_under_a_root(self, tmp_path):
        uploads, _ = build_tree(tmp_path)
        doc = uploads / "doc.svg"
        doc.write_text(DOC.format(href="target.svg"))
        assert resolved(doc, external_reference_root=str(uploads)) is True

    def test_root_propagates_to_nested_external_svg(self, tmp_path):
        # The nested document is in-root, but what it references is not: the
        # renderer it spawns must inherit the root.
        uploads, outside = build_tree(tmp_path)
        chain = uploads / "chain.svg"
        chain.write_text(DOC.format(href=os.path.join("..", "outside", "target.svg")))
        doc = uploads / "doc.svg"
        doc.write_text(DOC.format(href="chain.svg"))
        drawing = svglib.svg2rlg(str(doc), external_reference_root=str(uploads))
        nested = drawing.contents[0].contents[0]
        assert not nested.contents[0].contents


def run_cli(tmp_path, doc, *extra_args):
    """Run the svg2pdf CLI on `doc`, as a user converting a file they were sent."""
    argv = ["svg2pdf", "-o", str(tmp_path / "out.pdf"), *extra_args, str(doc)]
    old, sys.argv = sys.argv, argv
    try:
        svglib_pkg.main()
    finally:
        sys.argv = old


def refused(caplog):
    return any("out-of-root" in record.message for record in caplog.records)


class TestCommandLineContainment:
    """The CLI converts files it did not author, so it contains by default."""

    def test_parent_reference_is_refused_by_default(self, tmp_path, caplog):
        uploads, _ = build_tree(tmp_path)
        doc = uploads / "doc.svg"
        doc.write_text(DOC.format(href=os.path.join("..", "outside", "target.svg")))
        with caplog.at_level(logging.ERROR, logger="svglib.svglib"):
            run_cli(tmp_path, doc)
        assert refused(caplog)

    def test_in_directory_reference_still_resolves(self, tmp_path, caplog):
        uploads, _ = build_tree(tmp_path)
        doc = uploads / "doc.svg"
        doc.write_text(DOC.format(href="target.svg"))
        with caplog.at_level(logging.ERROR, logger="svglib.svglib"):
            run_cli(tmp_path, doc)
        assert not refused(caplog)

    def test_external_root_widens_the_allowed_directory(self, tmp_path, caplog):
        uploads, _ = build_tree(tmp_path)
        doc = uploads / "doc.svg"
        doc.write_text(DOC.format(href=os.path.join("..", "outside", "target.svg")))
        with caplog.at_level(logging.ERROR, logger="svglib.svglib"):
            run_cli(tmp_path, doc, "--external-root", str(tmp_path))
        assert not refused(caplog)
