# bdbag

#### BDDS Big Data Bag Utilities

The *bdbag* utilities are a collection of software programs for working with Bagit packages that conform the BDDS Bagit
and BDDS Bagit/RO profiles.

These utilities combine various other components such as the BDDS forks of the
[Bagit-Python](https://github.com/ini-bdds/bagit-python) bag creation utility and the BDDS
[Bagit-Profiles-Validator](https://github.com/ini-bdds/bagit-profiles-validator)
utility into a single, easy to use software package.

Enhanced bag support includes:

* Update-in-place functionality for existing bags.
* Automatic archiving and extraction of bags using ZIP, TAR, and TGZ formats.
* Automatic generation of remote file manifest entries and fetch.txt via configuration file.
* Automatic file retrieval based on the contents of a bag's fetch.txt file with multiple protocol support.
* Built-in profile validation.
* Built-in support for creation of bags with [Bagit/RO profile](https://github.com/ResearchObject/bagit-ro) compatibility.

### Dependencies

* [Python 2.7](https://www.python.org/downloads/release/python-2711/)


### Installation
Download the current [bdbag](https://github.com/ini-bdds/bdbag/archive/master.zip) source code from GitHub or
alternatively clone the source from GitHub if you have *git* installed:

```sh
git clone https://github.com/ini-bdds/bdbag
```
From the root of the **bdbag** source code directory execute the following command:
```sh
python setup.py install
```

Note that you may want to run this command as **root** or using **sudo** if you are on a Unix-based system and want to
make **bdbag** available to all users.

### Configuration

See the [Configuration guide](./doc/config.md).

### Usage

This software can be used from the command-line environment by running the **bdbag** script.  For detailed usage
instructions, see the [CLI guide](./doc/cli.md).

### Application Programming Interface

It is also possible to use **bdbag** from within other Python programs via an API.
See the [API guide](./doc/api.md) for further details.