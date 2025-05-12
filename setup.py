#
# Copyright 2016 University of Southern California
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

""" Installation script for the BDBag utilities.
"""
import io
import re
from setuptools import setup, find_packages

__version__ = re.search(
    r'__version__\s*=\s*[\'"]([^\'"]*)[\'"]',
    io.open('bdbag/__init__.py', encoding='utf_8_sig').read()
    ).group(1)

with open('README.md') as readme_file:
    readme = readme_file.read()

setup(
    name="bdbag",
    description="Big Data Bag Utilities",
    long_description=readme,
    long_description_content_type='text/markdown',
    url='https://github.com/fair-research/bdbag/',
    author="Mike D'Arcy",
    maintainer='USC Information Sciences Institute, Informatics Systems Research Division',
    maintainer_email='isrd-support@isi.edu',
    version=__version__,
    packages=find_packages(exclude=["test"]),
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
        'pytz',
        'tzlocal',
        'requests',
        'certifi',
        'importlib_metadata',
        'packaging',
        'bagit',
        'bagit_profile'
    ],
    install_requires=['pytz',
                      'tzlocal<3; python_version<"3"',
                      'tzlocal',
                      'certifi',
                      'packaging',
                      'importlib_metadata;python_version<"3.8"',
                      'requests',
                      'setuptools_scm',
                      'setuptools_scm<6.0; python_version<"3.9"',  # for bagit which does not properly include it in install_requires
                      'bagit==1.8.1',
                      'bagit-profile==1.3.1'
                      ],
    extras_require={
        'boto': ["boto3>=1.9.5", "botocore", "awscli"],
        'globus': ["globus_sdk>=2,<4"],
        'gcs': ["google_cloud_storage"]
    },
    python_requires='>=2.7, !=3.0.*, !=3.1.*, !=3.2.*, !=3.3.*, !=3.4.*, !=3.5.*, !=3.6.*, <4',
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
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
        'Programming Language :: Python :: 3.11',
        'Programming Language :: Python :: 3.12'

    ]
)

