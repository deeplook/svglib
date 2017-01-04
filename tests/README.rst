.. -*- mode: rst -*-

This folder contains the testsuite for `svglib`. In order to run it 
open a terminal, change into this folder and execute the following 
command (assuming you have ``pytest`` installed which is a simple
``pip install pytest``)::
 
    $ py.test -v

If for any reason you don't want to install `pytest` you can also
run the following (which installs `pytest-runner` during testing)::

    $ python setup.py test

Both will run the entire testsuite and produce result files in PDF
format in the subdirectories `samples`, `wikipedia/flags` and
`wikipedia/symbols`, if the corresponding SVG input files could 
be downloaded from the internet at the start of the test or if 
they are still available locally.

Run this in order to clean-up all generated files::

    $ py.test -v -s --override-ini=python_functions=cleanup

As an experimental feature some of the tests try using a vector 
conversion tool named `UniConvertor 
<http://sourceforge.net/projects/uniconvertor>`_ 
(if installed) for producing PDFs for comparison with `svglib`.
(This was not used for years, though, during development/testing.)

Calling ``renderPM.drawToFile()`` in ``TestW3CSVG.test_convert_pdf_png()``
is known to raise a ``TypeError`` sometimes in reportlab which was
fixed in ``reportlab`` 3.3.26. See
https://github.com/deeplook/svglib/issues/47.
