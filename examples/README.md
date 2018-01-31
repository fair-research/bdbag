# bdbag examples

#### BDDS Big Data Bag Examples

We provide here what we hope will become a set of examples 
(so far, just one) that illustrate the use the *bdbag* utilities for various purposes.
Some of these examples might eventually become additional utilities, but for now 
they are provided as is, with no commitments as to quality or support. That said,
pleae do notify us of any problems, comments, or suggestions by filing an issue.

### Dependencies

* [Python 2.7](https://www.python.org/downloads/release/python-2711/) is the minimum Python version required.
* The code and dependencies are currently compatible with Python 3.

### The Meta.py example

This program creates a big data bag (BDBag) containing a supplied set of (descriptive string, Minid) pairs,
each of which is assumed to reference a single BDBag. This BDBag contains:
* A *data/README* file listing the files referenced by the Minids
* A *metadata/manifest.json* with a Research Object describing the BDBag's contents
* A *fetch.txt* file with the info required to fetch the sub-bags into "data" (standard BDBag stuff)

```sh
python meta.py -m MINIDS -b BAGNAME [-r REMOTE_FILE_MANIFEST] [-V] [-h]
```
* *MINIDS* : Name of file in which each line is a comma-separated <descriptive string>, <minid> pair
* *BAGNAME* : Name of directory for new BDBag
* *REMOTE_FILE_MANIFEST* : Name of file in which to place remote file manifest. By default, "t.json"
* *-V* : If provided, then once bag is created, fetch bag contents and validate it.

Many limitations
* Essentially no error checking.
* manifest.json is a Research Object, but does not include provenance info
`
