.. -*- mode: rst -*-

This folder contains the testsuite for `svglib`. In order to run it 
open a terminal, change into this folder and execute the following 
command::
 
  $ py.test -v

This assumes you have installed ``pytest`` which is a simple
``pip install pytest``. More information to come...

This will run the entire testsuite and produce result files in PDF
format in the subdirectories `samples`, `wikipedia/flags` and
`wikipedia/symbols`, if the corresponding SVG input files could 
be downloaded from the internet at the start of the test or if 
they are still available locally.

Run this in order to clean-up all generated files:

    py.test -v -s --override-ini=python_functions=cleanup

As an experimental feature some of the tests try using a vector 
conversion tool named `UniConvertor 
<http://sourceforge.net/projects/uniconvertor>`_ 
(if installed) for producing PDFs for comparison with `svglib`.
