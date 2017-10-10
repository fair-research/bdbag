#
# Copyright 2015 University of Southern California
# Distributed under the Apache License, Version 2.0. See LICENSE for more info.
#

""" Installation script for the BDBag utilities.
"""

from setuptools import setup, find_packages

setup(
    name="bdbag",
    description="Big Data Bag Utility",
    url='https://github.com/ini-bdds/bdbag/',
    maintainer='USC Information Sciences Institute ISR Division',
    maintainer_email='misd-support@isi.edu',
    version="1.1.0",
    packages=find_packages(),
    package_data={'bdbag': ['profiles/*.*']},
    test_suite='test',
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
        'urlparse'],
    install_requires=['pytz',
                      'tzlocal',
                      'requests',
                      'certifi',
                      'bagit>=1.6.0b8',
                      'globus-sdk'],
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
        'Programming Language :: Python :: 3.5'
    ]
)

