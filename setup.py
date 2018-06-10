#
# Copyright 2015 University of Southern California
# Distributed under the Apache License, Version 2.0. See LICENSE for more info.
#

""" Installation script for the BDBag utilities.
"""

from setuptools import setup, find_packages

with open('README.md') as readme_file:
    readme = readme_file.read()

setup(
    name="bdbag",
    description="Big Data Bag Utilities",
    long_description=readme,
    long_description_content_type='text/markdown',
    url='https://github.com/fair-research/bdbag/',
    maintainer='USC Information Sciences Institute, Informatics Systems Research Division',
    maintainer_email='isrd-support@isi.edu',
    version="1.3.1",
    packages=find_packages(),
    package_data={'bdbag': ['profiles/*.*']},
    test_suite='test',
    tests_require=['mock', 'coverage'],
    entry_points={
        'console_scripts': [
            'bdbag = bdbag.bdbag_cli:main',
            'bdbag-utils = bdbag.bdbag_utils:main'
        ]
    },
    requires=[
        'argparse',
        'os',
        'sys',
        'platform',
        'logging',
        'time',
        'datetime',
        'json',
        'shutil',
        'tempfile',
        'tarfile',
        'zipfile',
        'urlparse',
        'pytz',
        'tzlocal',
        'requests',
        'certifi',
        'bagit'
    ],
    install_requires=['pytz',
                      'tzlocal',
                      'requests',
                      'certifi',
                      'bagit==1.6.4'],
    license='Apache 2.0',
    classifiers=[
        'Intended Audience :: Science/Research',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: Apache Software License',
        "Operating System :: POSIX",
        "Operating System :: MacOS :: MacOS X",
        "Operating System :: Microsoft :: Windows",
        'Programming Language :: Python',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3.3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6'
    ]
)

