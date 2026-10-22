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


USE_BOMB = """<?xml version="1.0"?>
<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink"
     width="10" height="10">
  <defs>{levels}</defs>
</svg>
"""


class TestUseExpansionLimit:
    def test_budget_is_shared_with_external_svgs(self, tmp_path, caplog):
        levels = ['<rect id="l0" width="1" height="1"/>']
        for i in range(1, 6):
            levels.append(
                f'<g id="l{i}">' + f'<use xlink:href="#l{i - 1}"/>' * 10 + "</g>"
            )
        uses = []
        for n in range(3):
            (tmp_path / f"ext{n}.svg").write_text(
                USE_BOMB.format(levels="".join(levels))
            )
            uses.append(f'<use xlink:href="ext{n}.svg#l5"/>')
        doc = tmp_path / "doc.svg"
        doc.write_text(
            DOC.replace(
                '<image xlink:href="{href}" width="64" height="64"/>', "".join(uses)
            )
        )
        with caplog.at_level(logging.ERROR, logger="svglib.svglib"):
            svglib.svg2rlg(str(doc))
        limit_hits = [r for r in caplog.records if "Too many <use>" in r.message]
        assert len(limit_hits) == 1


class TestUseCycles:
    def test_fragment_referencing_itself_through_its_file(self, tmp_path, caplog):
        (tmp_path / "self.svg").write_text(
            """<?xml version="1.0"?>
<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink"
     width="10" height="10">
  <defs><g id="x"><use xlink:href="self.svg#x"/></g></defs>
  <use xlink:href="#x"/>
</svg>
"""
        )
        with caplog.at_level(logging.ERROR, logger="svglib.svglib"):
            drawing = svglib.svg2rlg(str(tmp_path / "self.svg"))
        assert drawing is not None
        assert any("Circular" in r.message for r in caplog.records)

    def test_cycle_across_two_files(self, tmp_path, caplog):
        header = (
            '<?xml version="1.0"?>\n'
            '<svg xmlns="http://www.w3.org/2000/svg" '
            'xmlns:xlink="http://www.w3.org/1999/xlink" width="10" height="10">\n'
        )
        (tmp_path / "a.svg").write_text(
            header
            + '<defs><g id="y"><use xlink:href="b.svg#x"/></g></defs>'
            + '<use xlink:href="b.svg#x"/></svg>'
        )
        (tmp_path / "b.svg").write_text(
            header + '<defs><g id="x"><use xlink:href="a.svg#y"/></g></defs></svg>'
        )
        with caplog.at_level(logging.ERROR, logger="svglib.svglib"):
            drawing = svglib.svg2rlg(str(tmp_path / "a.svg"))
        assert drawing is not None
        assert any("Circular" in r.message for r in caplog.records)

    def test_external_fragment_reusing_a_local_id_is_rendered(self, tmp_path, caplog):
        """An id inside an external fragment that matches the local <use> target
        is not a cycle."""
        header = (
            '<?xml version="1.0"?>\n'
            '<svg xmlns="http://www.w3.org/2000/svg" '
            'xmlns:xlink="http://www.w3.org/1999/xlink" width="10" height="10">\n'
        )
        (tmp_path / "ext.svg").write_text(
            header + '<defs><g id="root"><rect id="a" width="1" height="1"/>'
            '<use xlink:href="#a"/></g></defs></svg>'
        )
        (tmp_path / "doc.svg").write_text(
            header + '<defs><g id="a"><use xlink:href="ext.svg#root"/></g></defs>'
            '<use xlink:href="#a"/></svg>'
        )
        with caplog.at_level(logging.ERROR, logger="svglib.svglib"):
            drawing = svglib.svg2rlg(str(tmp_path / "doc.svg"))
        assert drawing is not None
        assert not caplog.records
