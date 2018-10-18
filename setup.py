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
    maintainer='USC Information Sciences Institute, Informatics Systems Research Division',
    maintainer_email='isrd-support@isi.edu',
    version=__version__,
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
                      'certifi',
                      'requests>=2.7.0',
                      'bagit==1.7.0'],
    extras_require={
        'boto': ["boto3>=1.9.5", "botocore", "awscli"],
        'globus': ["globus_sdk>=1.6.0"],
    },
    python_requires='>=2.7.9, !=3.0.*, !=3.1.*, !=3.2.*, <4',
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

