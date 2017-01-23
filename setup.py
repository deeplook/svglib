import sys
from setuptools import setup
import distutils.core

__version__ = '0.8.0'
__license__ = 'LGPL 3'
__author__ = 'Dinu Gherman'
__date__ = '2017-01-23'

install_requires = open('requirements.txt').read().strip().split()
v = sys.version_info
if (v.major, v.minor) < (2, 7):
    install_requires.append('argparse')

setup(
    name='svglib',
    version=__version__,
    author=__author__,
    author_email='@'.join(['gherman', 'darwin.in-berlin.de']),
    description='A pure-Python library for reading and converting SVG',
    long_description=open('README.rst').read(),
    license='LGPL 3',
    platforms = ['Posix', 'Windows'],
    keywords='SVG, PDF, reportlab, conversion, graphics',
    url='https://github.com/deeplook/svglib',
    install_requires=install_requires,
    setup_requires=['pytest-runner'],
    tests_require=['pytest'],
    package_dir = {'svglib': 'svglib'},
    packages = ['svglib'],
    py_modules = [],
    scripts = ['scripts/svg2pdf'],
    classifiers=[
        # see http://pypi.python.org/pypi?%3Aaction=list_classifiers
        'Development Status :: 4 - Beta',
        'Environment :: Console',
        'Intended Audience :: End Users/Desktop',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: GNU General Public License (GPL)',
        'Operating System :: MacOS :: MacOS X',
        'Operating System :: POSIX',
        'Operating System :: Microsoft :: Windows',
        'Natural Language :: English',
        'Programming Language :: Python',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3.5',
        'Topic :: Documentation',
        'Topic :: Utilities',
        'Topic :: Printing',
        'Topic :: Multimedia :: Graphics :: Graphics Conversion',
        'Topic :: Software Development :: Libraries :: Python Modules',
        'Topic :: Text Processing :: Markup :: XML',
    ],
)
