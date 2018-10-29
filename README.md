# bdbag
[![Build Status](https://travis-ci.org/fair-research/bdbag.svg)](https://travis-ci.org/fair-research/bdbag)
[![Coverage Status](https://img.shields.io/coveralls/github/fair-research/bdbag/master.svg)](https://coveralls.io/github/fair-research/bdbag?branch=master)
[![PyPi Version](https://img.shields.io/pypi/v/bdbag.svg)](https://pypi.python.org/pypi/bdbag)
[![PyPi Wheel](https://img.shields.io/pypi/wheel/bdbag.svg)](https://pypi.python.org/pypi/bdbag)
[![Python Versions](https://img.shields.io/pypi/pyversions/bdbag.svg)](https://pypi.python.org/pypi/bdbag)
[![License](https://img.shields.io/pypi/l/bdbag.svg)](http://www.apache.org/licenses/LICENSE-2.0)

## Big Data Bag Utilities

The `bdbag` utilities are a collection of software programs for working with
[BagIt](https://datatracker.ietf.org/doc/draft-kunze-bagit/) packages that conform to the BDBag and Bagit/RO profiles.

The `bdbag` [profiles](https://github.com/fair-research/bdbag/tree/master/profiles) specify the use of the fetch.txt file, require serialization, and specify what manifests must be provided with a *bdbag*.

These utilities combine various other components such as the
[Bagit-Python](https://github.com/LibraryOfCongress/bagit-python) bag creation utility and the
[Bagit-Profiles-Validator](https://github.com/ruebot/bagit-profiles)
utility into a single, easy to use software package.

Enhanced bag support includes:

* Update-in-place functionality for existing bags.
* Automatic archiving and extraction of bags using ZIP, TAR, and TGZ formats.
* Automatic generation of remote file manifest entries and fetch.txt via configuration file.
* Automatic file retrieval based on the contents of a bag's fetch.txt file with multiple protocol support.
* Built-in profile validation.
* Built-in support for creation of bags with [Bagit/RO profile](https://github.com/ResearchObject/bagit-ro) compatibility.

An experimental Graphical User Interface (GUI) for `bdbag` can be found [here](https://github.com/fair-research/bdbag_gui).

#### Technical Papers

["I'll take that to go: Big data bags and minimal identifiers for exchange of large, complex datasets"](https://zenodo.org/record/820878) explains the motivation for BDBags and the related Minid construct, provides details on design and implementation, and gives examples of use. 

["Reproducible big data science: A case study in continuous FAIRness"](https://www.biorxiv.org/content/early/2018/02/27/268755) presents a data analysis use case in which BDBags and Minids are used to capture a transcription factor binding site analysis.

### Dependencies

* [Python 2.7](https://www.python.org/downloads/release/python-27/) is the minimum Python version required.
* The code and dependencies are also compatible with Python 3, versions 3.3 through 3.6.

### Installation
The latest `bdbag` release is available on PyPi and can be installed using `pip`:

```sh
pip install bdbag
```

Note that the above command will install `bdbag` with only the minimal dependencies required to run.
If you wish to install `bdbag` with the extra fetch transport handler support provided by `boto` (for AWS S3)
and `globus` (for Globus Transfer) packages, use the following command:
```sh
pip install bdbag[boto,globus]
```

### Installation from Source
You can use `pip` to install `bdbag` directly from GitHub:

```sh
sudo pip install git+https://github.com/fair-research/bdbag
```
or:
```sh
pip install --user git+https://github.com/fair-research/bdbag
```

You can also [download](https://github.com/fair-research/bdbag/archive/master.zip) the current `bdbag` source code from GitHub or
alternatively clone the source from GitHub if you have *git* installed:

```sh
git clone https://github.com/fair-research/bdbag
```
From the root of the `bdbag` source code directory execute the following command:
```sh
sudo pip install .
```
or:
```sh
pip install --user .
```
Note that if you want to install the extra dependencies from a local source directory you would use the following command:
```sh
pip install .[boto,globus]
```

### Testing
The unit tests can be run by invoking the following command from the root of the `bdbag` source code directory:
```sh
python setup.py test
```

### Usage

This software can be used from the command-line environment by running the `bdbag` script.  For detailed usage
instructions, see the [CLI Guide](./doc/cli.md).

### Configuration

Some components of the `bdbag` software can be configured via JSON-formatted configuration files.
See the [Configuration Guide](./doc/config.md) for further details.

### Application Programming Interface

It is also possible to use `bdbag` from within other Python programs via an API.
See the [API Guide](./doc/api.md) for further details.

### Utilities

A CLI utility module is provided for various ancillary tasks commonly involved with authoring **bdbags**.
See the [Utility Guide](./doc/utils.md) for further details.

### Change Log

The change log is located [here](CHANGELOG.md).
