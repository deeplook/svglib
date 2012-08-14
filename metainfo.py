#!/usr/bin/env python
# -*- coding: UTF-8 -*-

"Project meta information"


__version__ = "0.6.3"
__license__ = "LGPL 3"
__author__ = "Dinu Gherman"
__date__ = "2010-03-01"


name = "svglib"
version = __version__
date = __date__
description = "An experimental library for reading and converting SVG."
long_description = """\
`Svglib` is an experimental library for reading `SVG 
<http://www.w3.org/Graphics/SVG/>`_ files and converting them (to a 
reasonable degree) to other formats using the Open Source `ReportLab 
Toolkit <http://www.reportlab.org>`_. As a package it reads existing 
SVG files and returns them converted to ReportLab Drawing objects that 
can be used in a variety of ReportLab-related contexts, e.g. as Platypus 
Flowable objects or in RML2PDF. As a command-line tool it converts SVG 
files into PDF ones. 

Tests include a vast amount of tests from the `W3C SVG test suite 
<http://www.w3.org/Graphics/SVG/WG/wiki/Test_Suite_Overview>`_.
It also accesses around `200 flags from Wikipedia.org 
<http://en.wikipedia.org/wiki/Gallery_of_sovereign_state_flags>`_ 
for test purposes (some of them hinting at more work to be done).

This release changes the license from GPL 3 to LGPL 3, introduces
tiny bug fix reported by Harald Armin Massa and adapts to changed 
URLs for Wikipedia SVG flags used for test purposes.


Features
++++++++

- convert SVG files into ReportLab Graphics Drawing objects
- handle plain or compressed SVG files (.svg and .svgz)
- allow patterns for output files on command-line
- install a Python package named ``svglib``
- install a Python command-line script named ``svg2pdf``
- provide a Unittest test suite
- test on some standard W3C SVG tests available online
- test on some Wikipedia sample SVG symbols available online
- test on some Wikipedia sample SVG flags available online


Examples
++++++++

You can use `svglib` as a Python package e.g. like in the following
interactive Python session::

    >>> from svglib.svglib import svg2rlg
    >>> from reportlab.graphics import renderPDF
    >>>
    >>> drawing = svg2rlg("file.svg")
    >>> renderPDF.drawToFile(drawing, "file.pdf")

In addition a script named ``svg2pdf`` can be used more easily from 
the system command-line like this (you can see more examples when 
typing ``svg2pdf -h``)::

    $ svg2pdf file1.svg file2.svgz
    $ svg2pdf -o "%(basename)s.pdf" /path/file[12].svgz?
"""
author = 'Dinu Gherman'
author_email = '@'.join(['gherman', 'darwin.in-berlin.de'])
maintainer = author
maintainer_email = author_email
license_short = 'GNU GPL'
license = __license__
platforms = ["Posix", "Windows"]
keywords = ["svg", "reportlab", "PDF"]
_baseURL = "http://www.dinu-gherman.net/"
url = _baseURL
download_url = _baseURL + "tmp/%s-%s.tar.gz" % (name, __version__)
package_dir = {"svglib": "src/svglib"}
packages = ["svglib"]
py_modules = []
scripts = ["src/scripts/svg2pdf"]
classifiers = [
    # see http://pypi.python.org/pypi?%3Aaction=list_classifiers
    "Development Status :: 4 - Beta",
    "Environment :: Console",
    "Intended Audience :: End Users/Desktop",
    "Intended Audience :: Developers",
    "License :: OSI Approved :: GNU General Public License (GPL)",
    "Operating System :: MacOS :: MacOS X",
    "Operating System :: POSIX",
    "Operating System :: Microsoft :: Windows",
    "Natural Language :: English",
    "Programming Language :: Python",
    "Topic :: Documentation",
    "Topic :: Utilities",
    "Topic :: Printing",
    "Topic :: Multimedia :: Graphics :: Graphics Conversion",
    "Topic :: Software Development :: Libraries :: Python Modules",
    "Topic :: Text Processing :: Markup :: XML",
]

# for setuptools, only:
# install_requires = ["reportlab>2.0"],
