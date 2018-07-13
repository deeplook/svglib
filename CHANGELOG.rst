.. -*- mode: rst -*-

ChangeLog
=========

Sadly, no condensed changelog exists prior to version 0.6.3.

0.6.3:

- frozen last version maintained at https://bitbucket.org/deeplook/svglib/

0.8.0:

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

0.8.1:

- added support for the ``stroke-opacity`` property
- added basic em unit support for text placement
- added respecting absolute coordinates for tspan
- fixed crash with empty path definitions
- symbol definitions are considered when referenced in nodes
- fixed compatibility with recent ReportLab versions

0.8.2:

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
