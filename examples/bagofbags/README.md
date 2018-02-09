# BagOfBags: Create a BDBag containing references to other BDBags

This program uses functions from the `bdbag_api`, `bdbag_ro`, and `minid_client_api` packages
to create a big data bag containing a supplied set of Minids,
each of which is assumed to reference a single BDBag.  That is, a "bag of bags."
In brief, it:
* Reads the Minids for the sub-bags from a supplied file
* Uses `minid_client_api.get_entities` to fetch metadata about each sub-bag
* Uses `bdbag_api.make_bag` to create the new bag containing references to the sub-bags
* Uses several `bdbag_ro` functions to create the Research Object describing the new bag

It also creates a `README` file containing a list of sub-bag titles.

For example, the following creates a bag called `MYBAG` containing the bags listed in
the file `MYMINIDS`, with specified author name and ORCID.

```sh
python bagofbags.py -m MYMINIDS -b MYBAG -n "Josiah Carberry" -o "0000-0002-1825-0097"
```

As shown below, the resulting BDBag contains the usual files that are to be
found in a BDBag, with the `fetch.txt` file containing the Minids that can be used to fetch
their contents and the `data/manifest.json` containing descriptive metadata.
In addition, the `data/README` file contains background information.

![Image of the whole thing](images/MetaBags.png)

If you want to validate a newly created bag of bags, then the `-v` option will also:
* Use `bdbag_api.resolve_fetch` to download the sub-bags
* Use `bdbag_api.validate_bag` to validate the complete bag of bags

