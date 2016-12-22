.. -*- mode: rst -*-

========
Svglib
========

---------------------------------------------------------------------------
An experimental library for reading and converting SVG
---------------------------------------------------------------------------

:Author:     Dinu Gherman <gherman@darwin.in-berlin.de>
:Homepage:   http://www.dinu-gherman.net/
:Version:    Version 0.6.3
:Date:       2010-03-01
:Copyright:  GNU Lesser General Public Licence v3 (LGPLv3)


About
-----

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
--------

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
--------

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
  

Installation
------------

There are two ways to install `svglib`, depending on whether you have
the `easy_install` command available on your system or not.

1. Using `easy_install`
++++++++++++++++++++++++

With the `easy_install` command on your system and a working internet 
connection you can install `svglib` with only one command in a terminal::

  $ easy_install svglib

If the `easy_install` command is not available to you and you want to
install it before installing `svglib`, you might want to go to the 
`Easy Install homepage <http://peak.telecommunity.com/DevCenter/EasyInstall>`_ 
and follow the `instructions there <http://peak.telecommunity.com/DevCenter/EasyInstall#installing-easy-install>`_.

2. Manual installation
+++++++++++++++++++++++

Alternatively, you can install the `svglib` tarball after downloading 
the file ``svglib-0.6.3.tar.gz`` and decompressing it with the following 
command::

  $ tar xfz svglib-0.6.3.tar.gz

Then change into the newly created directory ``svglib`` and install 
`svglib` by running the following command::

  $ python setup.py install
  
This will install a Python module file named ``svglib.py`` in the 
``site-packages`` subfolder of your Python interpreter and a script 
tool named ``svglib`` in your ``bin`` directory, usually in 
``/usr/local/bin``.


Dependencies
------------

`Svglib` depends on the `reportlab` package, which, as of now, you
have to install manually, before you can use `svglib`. Unfortunately,
up to its latest release, `reportlab` 2.2, this package cannot be
installed automatically using `easy_install`.


Testing
-------

The `svglib` tarball distribution contains a Unittest test suite 
in the file ``test_svglib.py`` which can be run like shown in the 
following lines on the system command-line::
 
  $ tar xfz svglib-0.6.3.tar.gz
  $ cd svglib/src/test
  $ python test_svglib.py
  ......
  [...]
  working on [0] wikipedia/Ankh.svg
  working on [1] wikipedia/Biohazard.svg
  working on [2] wikipedia/Dharma_wheel.svg
  working on [3] wikipedia/Eye_of_Horus_bw.svg
  [...]
  ----------------------------------------------------------------------
  Ran 12 tests in 87.536s

  OK


Bug reports
-----------

Please report bugs and patches to Dinu Gherman 
<gherman@darwin.in-berlin.de>. Don't forget to include information 
about the operating system, ReportLab and Python versions being used.
