"""Render the ``<textPath>`` samples as a contact sheet.

Usage, from the repository root::

    uv run python -m tests.textpath_sheet textpath-sheet.pdf

The sheet shows every sample in ``tests/samples/textpath`` with its file name
and description, so the result can be checked by eye.
"""

import argparse
import re
from pathlib import Path
from typing import Optional

from reportlab.graphics import renderPDF
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen.canvas import Canvas

from svglib.svglib import svg2rlg

SAMPLES_DIR = Path(__file__).parent / "samples" / "textpath"


def sample_paths() -> list[Path]:
    """Return the sample SVG files, sorted by name."""
    return sorted(SAMPLES_DIR.glob("*.svg"))


def description(path: Path) -> str:
    """Return the text of the first XML comment of a sample."""
    match = re.search(r"<!--\s*(.*?)\s*-->", path.read_text(encoding="utf-8"))
    return match.group(1) if match else ""


def build_contact_sheet(out_path: Path, columns: int = 2) -> int:
    """Write a PDF with every sample and its description, returns their count."""
    paths = sample_paths()
    page_width, page_height = A4
    margin, gap, label_height = 36.0, 18.0, 28.0
    cell_width = (page_width - 2 * margin - (columns - 1) * gap) / columns
    canvas = Canvas(str(out_path), pagesize=A4)
    canvas.setTitle("svglib <textPath> samples")

    x = margin
    y = page_height - margin
    column = 0
    for path in paths:
        drawing = svg2rlg(str(path))
        assert drawing is not None
        scale = cell_width / drawing.width
        cell_height = drawing.height * scale + label_height
        if y - cell_height < margin:
            canvas.showPage()
            y = page_height - margin
        canvas.setFont("Helvetica-Bold", 8)
        canvas.drawString(x, y - 9, path.stem)
        canvas.setFont("Helvetica", 8)
        canvas.drawString(x, y - 19, description(path))
        drawing.scale(scale, scale)
        drawing.width *= scale
        drawing.height *= scale
        renderPDF.draw(drawing, canvas, x, y - cell_height)
        canvas.rect(x, y - cell_height, drawing.width, drawing.height)
        column += 1
        if column == columns:
            column = 0
            x = margin
            y -= cell_height + gap
        else:
            x += cell_width + gap
        # Rows hold equal-sized samples, so one height per row is enough.
    canvas.save()
    return len(paths)


def main(argv: Optional[list[str]] = None) -> None:
    """Parse the command line and do what it asks."""
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("out", type=Path, help="where to write the contact sheet PDF")
    args = parser.parse_args(argv)
    print(f"{build_contact_sheet(args.out)} samples written to {args.out}")


if __name__ == "__main__":
    main()
