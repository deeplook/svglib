.. -*- mode: rst -*-

========
Svglib
========

---------------------------------------------------------------------------
A pure-Python library for reading and converting SVG
---------------------------------------------------------------------------


About
-----

``Svglib`` is a pure-Python library for reading SVG_ files and converting
them (to a reasonable degree) to other formats using the ReportLab_ Open
Source toolkit.

Used as a package you can read existing SVG files and convert them into
ReportLab ``Drawing`` objects that can be used in a variety of contexts,
e.g. as ReportLab Platypus ``Flowable`` objects or in RML_.
As a command-line tool it converts SVG files into PDF ones (but adding
other output formats like bitmap or EPS is really easy and will be better
supported, soon).

Tests include a huge `W3C SVG test suite`_ plus ca. 200 `flags from
Wikipedia`_ and some selected `symbols from Wikipedia`_ (with increasingly
less pointing to missing features).

This release introduces *many* contributions by Claude Paroz, who
stepped forward to give this project a long needed overhaul after ca.
six years of taking a nap, for which I'm really very grateful! Thanks,
Claude!

Previous versions were hosted at https://bitbucket.org/deeplook/svglib.


Features
--------

- convert SVG_ files into ReportLab_ Graphics ``Drawing`` objects
- handle plain or compressed SVG files (.svg and .svgz)
- allow patterns for output files on command-line
- install a Python package named ``svglib``
- install a Python command-line script named ``svg2pdf``
- provide a PyTest_ test suite with over 90% code coverage
- test entire `W3C SVG test suite`_ after pulling from the internet
- test all SVG `flags from Wikipedia`_ after pulling from the internet
- test selected SVG `symbols from Wikipedia`_ after pulling from the net
- run on Python 2.7 and Python 3.5


Known limitations
-----------------

- stylesheets are not supported (only the style attribute)
- clipping is limited to single paths, no mask support
- color gradients are not supported


Examples
--------

You can use ``svglib`` as a Python package e.g. like in the following
interactive Python session::

    >>> from svglib.svglib import svg2rlg
    >>> from reportlab.graphics import renderPDF, renderPM
    >>>
    >>> drawing = svg2rlg("file.svg")
    >>> renderPDF.drawToFile(drawing, "file.pdf")
    >>> renderPM.drawToFile(drawing, "file.png")

In addition a script named ``svg2pdf`` can be used more easily from 
the system command-line. Here is the output from ``svg2pdf -h``::

    usage: svg2pdf [-h] [-v] [-o PATH_PAT] [PATH [PATH ...]]

    svg2pdf v. 0.8.0
    A converter from SVG to PDF (via ReportLab Graphics)

    positional arguments:
      PATH                  Input SVG file path with extension .svg or .svgz.

    optional arguments:
      -h, --help            show this help message and exit
      -v, --version         Print version number and exit.
      -o PATH_PAT, --output PATH_PAT
                            Set output path (incl. the placeholders: dirname,
                            basename,base, ext, now) in both, %(name)s and {name}
                            notations.

    examples:
      # convert path/file.svg to path/file.pdf
      svg2pdf path/file.svg

      # convert file1.svg to file1.pdf and file2.svgz to file2.pdf
      svg2pdf file1.svg file2.svgz

      # convert file.svg to out.pdf
      svg2pdf -o out.pdf file.svg

      # convert all SVG files in path/ to PDF files with names like:
      # path/file1.svg -> file1.pdf
      svg2pdf -o "%(base)s.pdf" path/file*.svg

      # like before but with timestamp in the PDF files:
      # path/file1.svg -> path/out-12-58-36-file1.pdf
      svg2pdf -o {{dirname}}/out-{{now.hour}}-{{now.minute}}-{{now.second}}-%(base)s.pdf path/file*.svg

    issues/pull requests:
        https://github.com/deeplook/svglib

    Copyleft by Dinu Gherman, 2008-2017 (LGPL 3):
        http://www.gnu.org/copyleft/gpl.html


Dependencies
------------

``Svglib`` depends mainly on the ``reportlab`` package, which provides
the abstractions for building complex ``Drawings`` which it can render
into different fileformats, including PDF, EPS, SVG and various bitmaps
ones. Other dependancies are ``lxml`` which is used in the context of SVG
CSS stylesheets.


Installation
------------

There are two ways to install ``svglib``.

1. Using ``pip``
++++++++++++++++

With the ``pip`` command on your system and a working internet 
connection you can install the newest version of ``svglib`` with only
one command in a terminal::

  $ pip install svglib

You can also use ``pip`` to install the very latest version of the
repository from GitHub, but then you won't be able to conveniently
run the test suite:

  $ pip install git+https://github.com/deeplook/svglib


2. Manual installation
+++++++++++++++++++++++

Alternatively, you can install the ``svglib`` tarball after downloading 
a tar ball like ``svglib-0.8.0.tar.gz`` from the `svglib page on PyPI`_
and executing a sequence of commands like shown here::

  $ tar xfz svglib-0.8.0.tar.gz
  $ cs svglib-0.8.0
  $ python setup.py install
  
This will install a Python package named ``svglib`` in the
``site-packages`` subfolder of your Python installation and a script 
tool named ``svg2pdf`` in your ``bin`` directory, e.g. in 
``/usr/local/bin``.


Testing
-------

The ``svglib`` tarball distribution contains a PyTest_ test suite 
in the ``tests`` directory. There, in ``tests/README.rst``, you can
also read more about testing. You can run the testsuite e.g. like
shown in the following lines on the command-line::
 
  $ tar xfz svglib-0.8.0.tar.gz
  $ cd svglib-0.8.0
  $ PYTHONPATH=. py.test
  ======================== test session starts =========================
  platform darwin -- Python 3.5.2, pytest-3.0.5, py-1.4.32, pluggy-0.4.0
  rootdir: /Users/dinu/repos/github/deeplook/svglib, inifile:
  plugins: cov-2.4.0
  collected 33 items

  tests/test_basic.py .........................
  tests/test_samples.py .s.s.s.s

  =============== 29 passed, 4 skipped in 40.25 seconds ================


Bug reports
-----------

Please report bugs and on the `svglib issue tracker`_ on GitHub (pull
requests are also appreciated)!
If necessary, please include information about the operating system, as
well as the versions of ``svglib``, ReportLab and Python being used!
Warning: there is no support for Windows, sorry for that!


.. _SVG: http://www.w3.org/Graphics/SVG/
.. _W3C SVG test suite:
      http://www.w3.org/Graphics/SVG/WG/wiki/Test_Suite_Overview
.. _flags from Wikipedia:
      https://en.wikipedia.org/wiki/Gallery_of_sovereign_state_flags
.. _symbols from Wikipedia:
      http://en.wikipedia.org/wiki/List_of_symbols
.. _ReportLab: http://www.reportlab.org
.. _RML: http://www.reportlab.com/software/rml-reference/
.. _svglib issue tracker: https://github.com/deeplook/svglib/issues
.. _PyTest: http://pytest.org
.. _svglib page on PyPI: 
