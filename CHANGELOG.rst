.. -*- mode: rst -*-

ChangeLog
=========

1.0.1 (2020-08-26)
------------------

- avoid stroking clipping paths (#238)
- when converting percentage values in embedded SVGs, consider the direct svg
  parent node (#246)
- fixed rounded rects artifacts when rx/ry values are too high (#250)
- avoid stroking rects when strokeWidth is 0 (#250)

1.0.0 (2020-03-22)
------------------

- dropped Python 2 support
- fixed references to <defs> content when placed middle or end of
  SVG documents (#225)
- fixed elliptic arcs reading when arc flags are condensed (#232)

0.9.4 (2020-03-22)
------------------

- disabled external entity loading by default (#229 - CVE-2020-10799)

0.9.3 (2019-11-02)
------------------

- WARNING: this is the last release supporting Python 2!
- added support for more color values (hex with alpha, rgba(), etc.)
  (#213, #115)
- handle text positioning when x, y, dx, dy have a list of values
- fixed styles precedence issue (#211)

0.9.2 (2019-07-12)
------------------

- fixed license mention in the svg2pdf script (#194)
- support the whole range of HTML color names for color styles (#203)
- fixed a division by zero error when width/height are missing in main viewBox
  (#195)


0.9.1 (2019-06-22)
------------------

- fixed rendering of circular arcs in some edge cases (#189)
- support for percentage attribute values has been added (#141)
- SVG viewbox is now properly scaled to its width/height attributes (#121)
- embedded external SVG files or file fragments are now rendered (#175)
- support <rect> as a clipping source
- prevented crash when a relative file path is used in a memory-only SVG
  source (#173)
- fixed image translation (by y value instead of x)

0.9.0 (2018-12-08)
------------------

- fixed svgz output on Python 3
- kept PDF standard fonts untouched (#89)
- added basic support for non-standard fonts (#89, #107)
- allowed list of font names
- better merge style attributes from parent nodes (#119)
- fixed crash with strings in transform parameters
- handled PNGs embedded in SVG sources (#93)
- improved scaling of embedded SVGs (#124)
- added millimeter unit support
- fixed crash in elliptical arc calculation (#117)
- added experimental support for CSS style sheets (#111)
- allowed decimal percentage values in rgb colors

0.9.0b0 (2018-08-19)
--------------------

- countless improvements to be hopefully listed in more detail in 0.9.0

0.8.1 (2017-04-22)
------------------

- added support for the ``stroke-opacity`` property
- added basic em unit support for text placement
- added respecting absolute coordinates for tspan
- fixed crash with empty path definitions
- symbol definitions are considered when referenced in nodes
- fixed compatibility with recent ReportLab versions

0.8.0 (2017-01-23)
------------------

This release introduces *many* contributions by Claude Paroz, who
stepped forward to give this project a long needed overhaul after ca.
six years of taking a nap, for which I'm really very grateful! Thanks,
Claude!

- moved repository to https://github.com/deeplook/svglib
- skipped version 0.7.0 to indicate tons of fixes regarding the points below
- added support for elliptical arcs
- fixed open/closed path issues
- fixed clip path issues
- fixed text issues
- replaced ``minidom`` with ``lxml``
- added ``logging`` support
- added a few more sample SVG files
- migrated test suite from unittest to pytest
- improved test documentation

0.6.3 (2010-03-02)
------------------

- frozen last version maintained at https://bitbucket.org/deeplook/svglib/

Sadly, no condensed changelog exists prior to version 0.6.3.
