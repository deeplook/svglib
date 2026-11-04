#!/usr/bin/env bash
# Build the wheel, install it into a throw-away virtual environment and test it
# there, to catch files missing from the package and broken entry points.
# The dependencies are resolved afresh, as for a user, not taken from uv.lock.
# Set TEST_DIST_PYTHON to use another Python version than 3.13.
set -euo pipefail

root=$(cd "$(dirname "$0")/.." && pwd)
tmp=$(cd "$(mktemp -d)" && pwd -P)  # the physical path, as Python reports it
trap 'rm -rf "$tmp"' EXIT
cd "$root"

uv build --wheel --out-dir "$tmp/dist"
uv venv --quiet --python "${TEST_DIST_PYTHON:-3.13}" "$tmp/venv"
uv pip install --quiet --python "$tmp/venv/bin/python" "$tmp"/dist/svglib-*.whl pytest

# The package must come from the wheel, not from src/.
installed=$("$tmp/venv/bin/python" -c "import svglib; print(svglib.__file__)")
case "$installed" in
    "$tmp"/venv/*) ;;
    *) echo "svglib was imported from $installed, not from the wheel" >&2; exit 1 ;;
esac

"$tmp/venv/bin/python" -c "import sys, reportlab; print('Python', sys.version.split()[0], 'with ReportLab', reportlab.Version)"

# The command line tool works...
"$tmp/venv/bin/svg2pdf" --version
"$tmp/venv/bin/svg2pdf" -o "$tmp/units.pdf" tests/samples/others/units.svg
head -c 5 "$tmp/units.pdf" | grep -q '%PDF-'

# ...and so does the test suite, without the tests that download samples.
"$tmp/venv/bin/python" -m pytest tests -m "not network" -q -p no:cacheprovider
