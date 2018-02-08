# bdbag
[![Build Status](https://travis-ci.org/ini-bdds/bdbag.svg)](https://travis-ci.org/ini-bdds/bdbag)

#### BDDS Big Data Bag Utilities

The *bdbag* utilities are a collection of software programs for working with
[BagIt](https://datatracker.ietf.org/doc/draft-kunze-bagit/) packages that conform the BDDS Bagit and BDDS Bagit/RO profiles.

The *bdbag* [profiles](https://github.com/ini-bdds/bdbag/tree/master/profiles) specify the use of the fetch.txt file, require serialization, and specify what manifests must be provided with a *bdbag*.

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

An experimental Graphical User Interface (GUI) for *bdbag* can be found [here](https://github.com/ini-bdds/bdbag_gui).

### Dependencies

* [Python 2.7](https://www.python.org/downloads/release/python-2711/) is the minimum Python version required.
* The code and dependencies are also compatible with Python 3, versions 3.3 through 3.6.

### Installation
The latest *bdbag* release is available on PyPi and can be installed using `pip`:

```sh
pip install bdbag
```

### Installation from Source
Download the current [bdbag](https://github.com/ini-bdds/bdbag/archive/master.zip) source code from GitHub or
alternatively clone the source from GitHub if you have *git* installed:

```sh
git clone https://github.com/ini-bdds/bdbag
```
From the root of the **bdbag** source code directory execute the following command:
```sh
python setup.py install --user
```

Note that if you want to make **bdbag** available to all users on the system, you should run the following command:
```sh
python setup.py install
```
If you are on a Unix-based system (including MacOSX) you should execute the above command as **root** or use **sudo**.

### Testing
The unit tests can be run by invoking the following command from the root of the **bdbag** source code directory:
```sh
python setup.py test
```

### Configuration

See the [Configuration guide](./doc/config.md).

### Usage

This software can be used from the command-line environment by running the **bdbag** script.  For detailed usage
instructions, see the [CLI guide](./doc/cli.md).

### Application Programming Interface

It is also possible to use **bdbag** from within other Python programs via an API.
See the [API guide](./doc/api.md) for further details.
