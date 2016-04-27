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
    version="0.6.0",
    packages=find_packages(),
    package_data={'bdbag': ['profiles/*.*']},
    entry_points={
        'console_scripts': [
            'bdbag = bdbag.bdbag_cli:main'
        ],
        'gui_scripts': [
          #  'bdbag-gui = bdbag.bdbag_gui:main',
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
    install_requires=['ordereddict',
                      'requests',
                      'certifi',
                      'bagit==1.5.4.dev',
                      'bagit-profile==1.0.2.dev',
                      'globusonline-transfer-api-client'],
    dependency_links=[
         "http://github.com/ini-bdds/bagit-python/archive/master.zip#egg=bagit-1.5.4.dev",
         "http://github.com/ini-bdds/bagit-profiles-validator/archive/master.zip#egg=bagit-profile-1.0.2.dev"
    ],
    license='Apache 2.0',
    classifiers=[
        'Intended Audience :: Science/Research',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: Apache Software License',
        'Programming Language :: Python',
        'Programming Language :: Python :: 2.7',
    ])

