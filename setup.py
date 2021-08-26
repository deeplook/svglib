#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
from setuptools import setup

with open('requirements.txt', 'r') as f:
    install_requires = f.read().strip().split()

needs_pytest = {'pytest', 'test', 'ptr'}.intersection(sys.argv)
pytest_runner = ['pytest-runner'] if needs_pytest else []

setup(
    install_requires=install_requires,
    setup_requires=[]+pytest_runner,
    data_files=[
        ('share/man/man1', ['svg2pdf.1'])
    ]
)
