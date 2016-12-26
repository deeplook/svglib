.. -*- mode: rst -*-

========
Svglib
========

.. WARNING::
      This repository was imported from https://bitbucket.org/deeplook/svglib
      and is being worked on to incorporate pull requests from other forks
      in order to bring it back in shape, apply some pending fixes and
      support Python 2 and 3. There will be a new release like 0.7.0, really
      soon... Please stay tuned!

---------------------------------------------------------------------------
A pure-Python library for reading and converting SVG
---------------------------------------------------------------------------

:Author:     Dinu Gherman
:Homepage:   https://github.com/deeplook/svglib
:Version:    Version 0.6.3
:Date:       2010-03-01
:Copyright:  GNU Lesser General Public Licence v3 (LGPLv3)


About
-----

``Svglib`` is a pure-Python library for reading SVG_ files and converting
them (to a reasonable degree) to other formats using the ReportLab_ Open
Source toolkit.
Used as a package you can read existing SVG files and convert them into
ReportLab ``Drawing`` objects that can be used in a variety of contexts,
e.g. as ReportLab Platypus ``Flowable`` objects or in RML_.
As a command-line tool it converts SVG files into PDF ones (but adding
other output formats like bitmap ones would be really simple).

Tests include a vast amount of tests from the `W3C SVG test suite`_ plus
ca. 190 `flags from Wikipedia`_ and some selected `symbols from Wikipedia`_
for test purposes (some of them hinting at more work to be done).

This release introduces a lot of contributions by Claude Paroz,
who stepped forward to give this project a long needed overhaul, for
which I'm very grateful. Thanks, Claude!
 

Features
--------

- convert SVG_ files into ReportLab_ Graphics ``Drawing`` objects
- handle plain or compressed SVG files (.svg and .svgz)
- allow patterns for output files on command-line
- install a Python package named ``svglib``
- install a Python command-line script named ``svg2pdf``
- provide a PyTest_ test suite
- test entire `W3C SVG test suite`_ after pulling from the internet
- test all SVG `flags from Wikipedia`_ after pulling from the internet
- test selected SVG `symbols from Wikipedia`_ after pulling from the net
- run on Python 2.7 and Python 3.5


Examples
--------

You can use ``svglib`` as a Python package e.g. like in the following
interactive Python session::

    >>> from svglib.svglib import svg2rlg
    >>> from reportlab.graphics import renderPDF
    >>>
    >>> drawing = svg2rlg("file.svg")
    >>> renderPDF.drawToFile(drawing, "file.pdf")

In addition a script named ``svg2pdf`` can be used more easily from 
the system command-line. Here is the output from ``svg2pdf -h``::

    usage: svg2pdf [-h] [-v] [-o PATH_PAT] [PATH [PATH ...]]

    svg2pdf v. 0.6.3
    An experimental SVG to PDF converter (via ReportLab Graphics)

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

    Copyleft by Dinu Gherman, 2008-2010 (LGPL 3):
        http://www.gnu.org/copyleft/gpl.html


Installation
------------

There are two ways to install ``svglib``.

1. Using ``pip``
++++++++++++++++

With the ``pip`` command on your system and a working internet 
connection you can install the newest version of ``svglib`` with only
one command in a terminal::

  $ pip install svglib


2. Manual installation
+++++++++++++++++++++++

Alternatively, you can install the ``svglib`` tarball after downloading 
a tar ball like ``svglib-0.6.3.tar.gz`` from the `svglib page on PyPI`_
and executing a sequence of commands like shown here::

  $ tar xfz svglib-0.6.3.tar.gz
  $ cs svglib-0.6.3
  $ python setup.py install
  
This will install a Python package named ``svglib`` in the
``site-packages`` subfolder of your Python installation and a script 
tool named ``svg2pdf`` in your ``bin`` directory, e.g. in 
``/usr/local/bin``.


Dependencies
------------

``Svglib`` depends on the ``reportlab`` package... ``svg.path``...


Testing
-------

The ``svglib`` tarball distribution contains a PyTest_ test suite 
in the file ``tests`` directory which can be run like shown in the 
following lines on the system command-line::
 
  $ tar xfz svglib-0.6.3.tar.gz
  $ cd svglib/src/test
  $ py.test -v -s
  ......


Bug reports
-----------

Please report bugs and on the `svglib issue tracker`_ on GitHub (pull
requests are also appreciated)!
If necessary, please include information about the operating system, as
well as the versions of ``svglib``, ReportLab and Python being used!
Warning: there is no support for Windows, sorry for that!


.. _SVG: http://www.w3.org/Graphics/SVG/
.. _W3C SVG test suite: http://www.w3.org/Graphics/SVG/WG/wiki/Test_Suite_Overview
.. _flags from Wikipedia: https://en.wikipedia.org/wiki/Gallery_of_sovereign_state_flags
.. _symbols from Wikipedia: http://en.wikipedia.org/wiki/List_of_symbols
.. _ReportLab: http://www.reportlab.org
.. _RML: http://www.reportlab.com/software/rml-reference/
.. _svglib issue tracker: https://github.com/deeplook/svglib/issues
.. _PyTest: http://pytest.org
.. _svglib page on PyPI: 
