# Copyright (c) 2015 Florian Wagner, Razvan Panea
#
# This file is part of GO-PCA Web Server.
#
# GO-PCA Web Server is free software: you can redistribute it and/or
# modify it under the terms of the GNU General Public License,
# Version 3, as published by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.

import sys
import os

from setuptools import setup, find_packages, Extension
from codecs import open
from os import path

here = path.abspath(path.dirname(__file__))
description = 'GO-PCA Web Server: A tornado-based web server for running GO-PCA'

long_description = ''
with open(path.join(here, 'README.rst'), encoding='utf-8') as f:
    long_description = f.read()

setup(
    name='gopca-server',

    version='0.1rc',

    description=description,
    long_description=long_description,

    url='https://github.com/flo-compbio/gopca-server',

    author='Florian Wagner',
    author_email='florian.wagner@duke.edu',

    license='GPLv3',

    # See https://pypi.python.org/pypi?%3Aaction=list_classifiers
    classifiers=[
        'Development Status :: 3 - Alpha',

        'Intended Audience :: Developers',
        'Intended Audience :: Science/Research',
        'Topic :: Scientific/Engineering :: Bio-Informatics',

        'License :: OSI Approved :: GNU General Public License v3 (GPLv3)',

        'Programming Language :: Python :: 2.7',
    ],

    keywords='server web application go-pca interface',

    #packages=find_packages(exclude=['contrib', 'docs', 'tests*']),
    packages=['go_pca_server'],

	#libraries = [],

    install_requires=['tornado','jinja2','python-dateutil','genometools'],
    #'sphinx','sphinx-rtd-theme','sphinx-argparse','mock'],

	# development dependencies
    #extras_require={},

	# data
    package_data={'go_pca_server': ['templates/*.html','templates/*.sh','static/*.css']},

	# data outside package
    #data_files=[],

	# executable scripts
    entry_points={
        'console_scripts': [
			'go-pca-server.py = go_pca_server.server:main',
        ],
    },
)
