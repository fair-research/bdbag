# Bag of Bags

#### BDDS Big Data Bag Examples

#### [bagofbags](bagofbags.py): Create a BDBag containing 1+ other BDBags

This program creates a new big data bag (BDBag) containing a supplied set of Minids,
each of which is assumed to reference a single BDBag.  That is, a "bag of bags." This BDBag contains, among other things:
* `data/README` providing some description of the new BDBag's contents
* `metadata/manifest.json` with a Research Object describing the new BDBag's contents
* `fetch.txt` with the info required to fetch the sub-bags into "data" (standard BDBag stuff)

```sh
python bagofbags.py -m MINIDS -b BAGNAME [-V] [-h] [-q] [-d]
```
* `MINIDS` : Name of input file listing the Minids to be included, one per line.
* `BAGNAME` : Name of the directory that is to be created for the new BDBag
* `-V` : If provided, then once bag is created, fetch bag contents and validate it.

In the following image, we show a request to create a new BDBag, `MYBAG`, that is to contain
the bags listed in the file `MYMINIDS`. The new BDBag contains the usual files that are to be
found in a BDBag, with the `fetch.txt` file containing the Minids that can be used to fetch
their contents and the `data/manifest.json` containing descriptive metadata. The `data/README` file
contains background information.

![Image of the whole thing](images/MetaBags.png)

`
