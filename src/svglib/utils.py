#!/usr/bin/env python
# _*_ coding: UTF-8 _*_

"""
Helper functions for the conversion of SVG files on the command-line.

For further information please check the file README.txt!
"""

import sys
import argparse
import textwrap
from datetime import datetime
from os.path import dirname, basename, splitext, exists

from reportlab.graphics import renderPDF, renderPM, renderPS, renderSVG

from svglib import svglib


def convert_file(path, outputPat=None):
    "Convert an SVG file to one in another format."

    _format = splitext(outputPat)[1][1:].lower()
    # derive output filename from output pattern
    file_info = {
        'dirname': dirname(path) or '.',
        'basename': basename(path),
        'base': basename(splitext(path)[0]),
        'ext': splitext(path)[1],
        'now': datetime.now(),
        'format': _format
    }
    out_pattern = outputPat or '%(dirname)s/%(base)s.%(format)s'
    # allow classic %%(name)s notation
    out_path = out_pattern % file_info
    # allow also newer {name} notation
    out_path = out_path.format(**file_info)

    # generate a drawing from the SVG file
    try:
        drawing = svglib.svg2rlg(path)
    except:
        print('Rendering failed.')
        raise

    # save drawing into a new file
    if drawing:
        fmt = file_info['format'].upper()
        if fmt == 'PDF':
            renderPDF.drawToFile(drawing, out_path, showBoundary=0)
        elif fmt == 'EPS':
            renderPS.drawToFile(drawing, out_path, showBoundary=0)
        elif fmt in 'JPG JPEG PNG BMP PPM GIF PCT PICT TIFF TIFFP TIFFL TIF TIFF1'.split(): # PY SVG
            renderPM.drawToFile(drawing, out_path, fmt=fmt)


# command-line usage stuff

def cli_main():
    args = dict(
        prog=basename(sys.argv[0]),
        version=svglib.__version__,
        author=svglib.__author__,
        license=svglib.__license__,
        copyleft_year=svglib.__date__[:svglib.__date__.find('-')],
        ts_pattern="{{dirname}}/out-"\
                   "{{now.hour}}-{{now.minute}}-{{now.second}}-"\
                   "%(base)s",
    )
    if args['prog'].endswith('2ps'):
        args['ext'] = 'eps'
    elif args['prog'].endswith('2pdf'):
        args['ext'] = 'pdf'
    elif args['prog'].endswith('2pm'):
        args['ext'] = 'pm'
    args['ext_caps'] = args['ext'].upper()
    args['ts_pattern'] += ('.%s' % args['ext'])
    desc = '{prog} v. {version}\n'.format(**args)
    # import pdb; pdb.set_trace()
    desc += 'A converter from SVG to {} (via ReportLab Graphics)\n'.format(args['ext_caps'])
    if args['prog'].endswith('2pm'):
        desc += '(Replace extensions PM below with something like PNG, JPEG, etc.)\n'
    epilog = textwrap.dedent('''\
        examples:
          # convert path/file.svg to path/file.{ext}
          {prog} path/file.svg

          # convert file1.svg to file1.{ext} and file2.svgz to file2.{ext}
          {prog} file1.svg file2.svgz

          # convert file.svg to out.{ext}
          {prog} -o out.{ext} file.svg

          # convert all SVG files in path/ to {ext_caps} files with names like:
          # path/file1.svg -> file1.{ext}
          {prog} -o "%(base)s.{ext}" path/file*.svg

          # like before but with timestamp in the {ext_caps} files:
          # path/file1.svg -> path/out-12-58-36-file1.{ext}
          {prog} -o {ts_pattern} path/file*.svg

        issues/pull requests:
            https://github.com/deeplook/svglib

        Copyleft by {author}, 2008-{copyleft_year} ({license}):
            http://www.gnu.org/copyleft/gpl.html'''.format(**args))
    p = argparse.ArgumentParser(
        description=desc,
        epilog=epilog,
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    p.add_argument('-v', '--version',
        help='Print version number and exit.', 
        action='store_true')

    p.add_argument('-o', '--output',
        metavar='PATH_PAT',
        help='Set output path (incl. the placeholders: dirname, basename,'
             'base, ext, now) in both, %%(name)s and {name} notations.'
    )

    line_filter_default = u''
    p.add_argument('input',
        metavar='PATH',
        nargs='*',
        help='Input SVG file path with extension .svg or .svgz.')

    args = p.parse_args()

    if args.version:
        print(svglib.__version__)
        sys.exit()

    if not args.input:
        p.print_usage()
        sys.exit()

    paths = [a for a in args.input if exists(a)]
    for path in paths:
        convert_file(path, outputPat=args.output)
