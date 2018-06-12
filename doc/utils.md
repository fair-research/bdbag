# *bdbag*: *`bdbag-utils`*  reference

## Summary

The *bdbag-utils* command-line program is designed to make some of the more repetitive and
programmable tasks associated with creating and maintaining bags easier. In particular, various methods
for programmatically generating [`remote-file-manifests`](config.md#remote-file-manifest) are provided.


## Usage
The `bdbag-utils` CLI functions are invoked as sub-commands.

```
usage: bdbag-utils [-h] [--quiet] [--debug]
                   {create-rfm-from-filesystem,create-rfm-from-file,create-rfm-from-url-list}
                   ...
```

## Arguments:

##### `--quiet`
Suppress logging output.

----
##### `--debug`
Enable debug logging output.

----
##### `-h, --help`
Print a detailed help message and exit.

----

### `create-rfm-from-filesystem`
Create a `remote-file-manifest` by recursively scanning a directory from a mounted filesystem.
```
usage: bdbag-utils create-rfm-from-filesystem [-h] --checksum
                                              {md5,sha1,sha256,sha512,all}
                                              [--base-payload-path <url>]
                                              --base-url <url>
                                              [--filter <column><operator><value>]
                                              [--url-formatter {none,append-path,append-filename}]
                                              [--streaming-json]
                                              <input path> <output file>
```

----
##### `--checksum {md5,sha1,sha256,sha512,all}`
*Required*

Checksum algorithm to use: can be specified multiple times with different values.
If `all` is specified, every supported checksum will be generated.


----
##### `--base-payload-path <url>`
*Optional*

An optional path prefix to prepend to each relative file path found while walking
the input directory tree. All files will be rooted under this base directory path
in any bag created from this manifest.

----
##### `--base-url <url>`
*Required*

A URL root to prepend to each file listed in the manifest.
Used to generate fetch URL fields dynamically.

----
##### `--filter <column><operator><value>`
*Optional*

A simple expression of the form `<column><operator><value>` where:
* `<column>` is the name of a column in the generated remote file manifest entry to be filtered on.
* `<operator>` is one of the following tokens:
    * `==` (equal)
    * `!=` (not equal)
    * `=*` (wildcard substring equal)
    * `!*` (wildcard substring not equal)
    * `^*` (wildcard starts with)
    * `$*` (wildcard ends with)
    * `>`, `>=`, `<`, `<=`
* `<value>` is a string pattern or integer to be filtered against.

----
##### `--url-formatter {none,append-path,append-filename}`
*Optional*

Format function for generating remote file URLs.
* If `append-path` is specified, the existing relative path including the filename
will be appended to the `--base-url` argument.
* If `append-filename` is specified, only the filename will be appended.
* If `none` is specified, the `--base-url` argument will be used as-is.
The default setting is "append-path".

----
##### `--streaming-json`
*Optional*

If `streaming-json` is specified, one JSON tuple object per line will be written to the output file.
Enable this option if the default behavior produces a file that is prohibitively large for `bdbag` to parse
entirely into system memory.

----
##### `<input path>`
*Required*

A path to an input directory that will be recursively scanned for files. Each file found will have its checksum
calculated and get added as an entry in the output `remote-file-manifest`.

----
##### `<output file>`
*Required*

Path of the filename where the remote file manifest will be written.

----
### `create-rfm-from-file`
Create a `remote-file-manifest` from a CSV or JSON file with records containing
column data that can be mapped to the required fields in the `remote-file-manifest`.

Note: even though the various checksum column-mapping arguments are technically _optional_ from
the perspective of the command-line parser, at least one _must_ be specified.
```
usage: bdbag-utils create-rfm-from-file [-h] [--input-format {csv,json}]
                                        [--filter <column><operator><value>]
                                        --url-col <url column>
                                        --length-col <length column>
                                        --filename-col <filename column>
                                        [--md5-col <md5 column>]
                                        [--sha1-col <sha1 column>]
                                        [--sha256-col <sha256 column>]
                                        [--sha512-col <sha512 column>]
                                        <input file> <output file>
```

----
##### `--input-format {csv,json}`
*Required*

The input file format specified by keyword, either `csv` or `json`.
Various flavors of CSV are supported, e.g., tab-delimited, quoted, etc.

----
##### `--filter <column><operator><value>`
*Optional*

A simple expression of the form `<column><operator><value>` where:
* `<column>` is the name of a column in the input file to be filtered on.
* `<operator>` is one of the following tokens:
    * `==` (equal)
    * `!=` (not equal)
    * `=*` (wildcard substring equal)
    * `!*` (wildcard substring not equal)
    * `^*` (wildcard starts with)
    * `$*` (wildcard ends with)
    * `>`, `>=`, `<`, `<=`
* `<value>` is a string pattern or integer to be filtered against.

----
##### `--url-col <url column>`
*Required*

The column or key name in the input file which will be mapped to the `url` attribute of the output manifest.

----
##### `--length-col <length column>`
*Required*

The column or key name in the input file which will be mapped to the `length` attribute of the output manifest.

----
##### `--filename-col <filename column>`
*Required*

The column or key name in the input file which will be mapped to the `filename` attribute of the output manifest.

----
##### `--md5-col <md5 column>`
*Optional*

The column or key name in the input file which will be mapped to the `md5` attribute of the output manifest.

----
##### `--sha1-col <sha1 column>`
*Optional*

The column or key name in the input file which will be mapped to the `sha1` attribute of the output manifest.

----
##### `--sha256-col <sha256 column>`
*Optional*

The column or key name in the input file which will be mapped to the `sha256` attribute of the output manifest.

----
##### `--sha512-col <sha512 column`
*Optional*

The column or key name in the input file which will be mapped to the `sha512` attribute of the output manifest.

----
##### `<input file>`
*Required*

Path to a CSV or JSON formatted input file.

----
##### `<output file>`
*Required*

Path of the filename where the remote file manifest will be written.

----
### `create-rfm-from-url-list`
Create a remote file manifest from a list of HTTP(S) URLs by issuing HTTP HEAD
requests for the Content-Length, Content-Disposition, and Content-MD5, Content-SHA256
(or equivalent checksum type) headers for each URL.

Note: only `md5` and `sha256` hash algorithms are supported with this function.
```
usage: bdbag-utils create-rfm-from-url-list [-h] [--keychain-file <file>]
                                            [--base-payload-path <url>]
                                            [--md5-header <md5 header name>]
                                            [--sha256-header <sha256 header name>]
                                            [--filter <column><operator><value>]
                                            [--disable-hash-decode-base64]
                                            [--preserve-url-path]
                                            [--streaming-json]
                                            <input file> <output file>
```

----
##### `--keychain-file <file>`
*Optional*

Optional path to a [`keychain`](config.md#keychain.json) file. If this argument is not specified, the keychain file
defaults to: `~/.bdbag/keychain.json`.

----
##### `--base-payload-path <url>`
*Optional*

An optional path prefix to prepend to each relative file path found while querying each URL
for metadata. All files will be rooted under this base directory path in any bag created
from this manifest.

----
##### `--md5-header <md5 header name>`
*Optional*

The name of the response header that contains the MD5 hash value. Defaults to `Content-MD5`.
Other examples: `x-amz-meta-md5chksum` (AWS S3), `x-goog-hash: md5` (GCS).

----
##### `--sha256-header <sha256 header name>`
*Optional*

The name of the response header that contains the SHA256 hash value. Defaults to `Content-SHA256`.

----
##### `--filter <column><operator><value>`
*Optional*

A simple expression of the form `<column><operator><value>` where:
* `<column>` is the name of a header in the result headers to be filtered on.
* `<operator>` is one of the following tokens:
    * `==` (equal)
    * `!=` (not equal)
    * `=*` (wildcard substring equal)
    * `!*` (wildcard substring not equal)
    * `^*` (wildcard starts with)
    * `$*` (wildcard ends with)
    * `>`, `>=`, `<`, `<=`
* `<value>` is a string pattern or integer to be filtered against.

----
##### `--disable-hash-decode-base64`
*Optional*

Content hashes found in headers are assumed to be `base64` encoded.
Use this option to disable the automatic `base64` decoding (and subsequent hex encoding)
of the hash header and use the result value unchanged.

----
##### `--preserve-url-path`
*Optional*

Preserve the URL file path in the local payload. This is used for mirroring the path
hierarchy from the source in the bag payload directory.

----
##### `--streaming-json`
*Optional*

If `streaming-json` is specified, one JSON tuple object per line will be written to the output file.
Enable this option if the default behavior produces a file that is prohibitively large for `bdbag` to parse
entirely into system memory.

----
##### `<input file>`
*Required*

Path to a file containing a newline delimited list of URLs to query for header metadata.

----
##### `<output file>`
*Required*

Path of the filename where the remote file manifest will be written.