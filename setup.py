import sys
from setuptools import setup

__version__ = '1.1.0'
__license__ = 'LGPL 3'
__author__ = 'Dinu Gherman'
__date__ = '2021-04-10'

with open('README.rst', 'r') as f:
    long_description = f.read()

with open('requirements.txt', 'r') as f:
    install_requires = f.read().strip().split()

needs_pytest = {'pytest', 'test', 'ptr'}.intersection(sys.argv)
pytest_runner = ['pytest-runner'] if needs_pytest else []

setup(
    name='svglib',
    version=__version__,
    author=__author__,
    author_email='@'.join(['gherman', 'darwin.in-berlin.de']),
    description='A pure-Python library for reading and converting SVG',
    long_description=long_description,
    license='LGPL 3',
    platforms=['Posix', 'Windows'],
    keywords='SVG, PDF, reportlab, conversion, graphics',
    url='https://github.com/deeplook/svglib',
    python_requires='>=3',
    install_requires=install_requires,
    setup_requires=[] + pytest_runner,
    tests_require=['pytest'],
    package_dir={'svglib': 'svglib'},
    packages=['svglib'],
    py_modules=[],
    scripts=['scripts/svg2pdf'],
    data_files = [('share/man/man1', ['svg2pdf.1'])],
    classifiers=[
        # see http://pypi.python.org/pypi?%3Aaction=list_classifiers
        'Development Status :: 4 - Beta',
        'Environment :: Console',
        'Intended Audience :: End Users/Desktop',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: GNU Lesser General Public License v3 (LGPLv3)',
        'Operating System :: MacOS :: MacOS X',
        'Operating System :: Microsoft :: Windows',
        'Operating System :: POSIX',
        'Natural Language :: English',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3 :: Only',
        'Topic :: Documentation',
        'Topic :: Utilities',
        'Topic :: Printing',
        'Topic :: Multimedia :: Graphics :: Graphics Conversion',
        'Topic :: Software Development :: Libraries :: Python Modules',
        'Topic :: Text Processing :: Markup :: XML',
    ],
)
