# *bdbag*: Command-line Interface (CLI)

## Summary

The *bdbag* command-line program is designed to operate on either bag directories or single file archives of bags in a
supported format, such as ZIP, TAR, or TGZ. Different functions are available based on the context of the input bag
path.  Therefore, when invoking *bdbag*, some command-line arguments may either be incompatible with other specified
arguments, or may be invalid in the context of the bag path specified.  In such cases, the program will notify the user
with an error message indicating the incompatibility.

----

## Usage
The only mandatory argument is a valid path to a local bag directory, a local bag archive file, or a URL/URI resolving to a remote bag archive file. All other arguments are optional.

### Basic arguments:
```
usage: bdbag
[--version]
[--update]
[--revert]
[--archiver {zip,tar,tgz}]
[--checksum {md5,sha1,sha256,sha512,all}]
[--skip-manifests]
[--prune-manifests]
[--materialize]
[--resolve-fetch {all,missing}]
[--fetch-filter <column><operator><value>]
[--validate {fast,full,structure,completeness}]
[--validate-profile {profile-only,full}]
[--profile-path <file>]
[--config-file <file>]
[--keychain-file <file>]
[--metadata-file <file>]
[--ro-metadata-file <file>]
[--ro-manifest-generate {overwrite, update}]
[--remote-file-manifest <file>]
[--quiet]
[--debug]
[--help]
[--output-path]
<path>
```

### Extended arguments:
These extended arguments are mapped directly to metadata fields in bag-info.txt:
```
[--bag-count BAG_COUNT]
[--bag-group-identifier BAG_GROUP_IDENTIFIER]
[--bag-size BAG_SIZE]
[--bagit-profile-identifier BAGIT_PROFILE_IDENTIFIER]
[--contact-email CONTACT_EMAIL]
[--contact-name CONTACT_NAME]
[--contact-orcid CONTACT_ORCID]
[--contact-phone CONTACT_PHONE]
[--external-description EXTERNAL_DESCRIPTION]
[--external-identifier EXTERNAL_IDENTIFIER]
[--internal-sender-description INTERNAL_SENDER_DESCRIPTION]
[--internal-sender-identifier INTERNAL_SENDER_IDENTIFIER]
[--organization-address ORGANIZATION_ADDRESS]
[--source-organization SOURCE_ORGANIZATION]
```
----

### Argument descriptions:

----
#### `<path>`
Mandatory path parameter. The path should represent either a local bag directory or local bag archive file, _or_ an actionable URL/URI referencing a serialized bag archive.
In this context, an actionable URL/URI is defined as either content referenced directly by URL that can be retrieved with a supported
fetch transport handler, or a URI whose scheme can be interpreted as an identifier scheme that can be handled by the currently installed identifier resolvers.

* If the target path is a directory and no bag structure exists in that path, a bag structure will be created "in-place".
In order for a bag to be created in-place, the calling user must have write permissions for the specified directory.
* If the target path is an archive file and no other conflicting arguments are specified, the archive file will be extracted.
* If the target path is an actionable URL/URI, the target of the URL (or resolved URI, if the URI represents a supported identifier scheme) will be downloaded to the current directory.

#### `--output-path`
Optional output path parameter. Functions that may produce extracted directory output (such as `materialize`, `extract`, or `validate` when 
operating on bag _archive_ files) can be configured to write such output to the specified `output-path`.

----
#### `--update`
Update an existing bag dir, recalculating tag-manifest checksums and regenerating manifests and fetch.txt if necessary.

----
#### `--revert`
Revert an existing bag directory back to a normal directory, deleting all bag metadata files. Payload files in the `data` directory will be moved back to the directory root, and the `data` directory will be deleted.

----
#### `--archiver {zip,tar,tgz}`
Archive a bag using the specified format.

----
#### `--checksum {md5,sha1,sha256,sha512,all}`
Checksum algorithm(s) to use: can be specified multiple times with different values. If `all` is specified,
every supported checksum will be generated.

----
#### `--skip-manifests`
If specified in conjunction with `--update`, only tagfile manifests will be regenerated, with payload manifests and
fetch.txt (if any) left as is. This argument should be used as an optimization (to avoid recalculating payload file
checksums) when only the bag metadata has been changed.

----
#### `--prune-manifests`
If specified, any existing checksum manifests not explicitly configured (either by the `--checksum` argument or in
`bdbag.json`) will be deleted from the bag during an update.

----
#### `--materialize`
The `materialize` function is a bag bootstrapper. When invoked,
it will attempt to fully _reconstitute_ a bag by performing multiple
possible actions depending on the context of the `<path>` argument.
1. If `<path>` is a URL or a URI of a resolvable identifier scheme, the file
referenced by this value will first be downloaded to the current directory _or_ the directory specified by the optional 
`--output-path` argument.
2. If the `<path>` (or previously downloaded file) represents a
local path to a supported archive format, the archive will be extracted
to the directory containing the bag archive _or_ the directory specified by the optional `--output-path` argument.
3. If the `<path>` (or previously extracted file) represents a valid
bag directory, any remote file references contained within the bag's
`fetch.txt` file will attempt to be resolved.
4. Full validation will be run on the materialized bag. If any one of
these steps fail, an error is raised.

----
#### `--resolve-fetch {missing,all}`
Download remote files listed in the bag's fetch.txt file. 
* The `missing` option only attempts to fetch files that do not
already exist in the bag payload directory. Additionally, files that do exist but have a different size in bytes than the file size as declared by the `length` field in `fetch.txt` are considered as _incomplete_ and will be fetched when using the `missing` argument. 
* The `all` option causes all fetch files to be re-acquired, even if they
already exist in the bag payload directory.

----
#### `--fetch-filter <column><operator><value>`
Selectively fetch files where entries in `fetch.txt` match the filter expression `<column><operator><value>` where:
*  `column` is one of the following literal values corresponding to the field names in `fetch.txt`: `url`, `length`, or `filename`
* `<operator>` is one of the following predefined tokens:

	| Operator | Description |
	| --- | --- |
	|==| equal |
	|!=| not equal |
	|=*| wildcard substring equal |
	|!*| wildcard substring not equal |
	|^*| wildcard starts with |
	|$*| wildcard ends with |
	|=~| regexpression matches |
	|>| greater than |
	|>=| greater than or equal to |
	|<| less than |
	|<=| less than or equal to |

* `value` is a string or integer

With this mechanism you can do various string-based pattern matching on `filename` and `url`. Using `missing` as the mode for `--resolve-fetch`,  you can invoke the command multiple times with a different filter to perform a effective disjunction. For example:

* `bdbag --resolve-fetch missing --fetch-filter 'filename$*.txt' ./my-bag`
* `bdbag --resolve-fetch missing --fetch-filter 'filename^*README' ./my-bag`
* `bdbag --resolve-fetch missing --fetch-filter 'filename==data/change.log' ./my-bag`
* `bdbag --resolve-fetch missing --fetch-filter 'filename=~(?!foo).*\.json$' ./my-bag`
* `bdbag --resolve-fetch missing --fetch-filter 'url=*/requirements/' ./my-bag`

The above commands will get all files ending with ".txt", all files beginning with "README", the exact file "data/change.log", files ending with ".json" but do not contain "foo" on their path, and all urls containing "/requirements/" in the url path, respectively.

You can also use `length` and the integer relation operators to easily limit the size of the files retrieved, for example:

* `bdbag --resolve-fetch all --fetch-filter length<=1000000`

###### Important Note: enclosing the `fetch-filter` expression in single quotes
For those users of Unix or MacOS systems whose shell environment expands certain characters like `*` and `$`, the `--fetch-filter` expression should be enclosed in single quotation (`'`) marks.

----
#### `--validate {fast,full,structure}`
Validate a bag directory or bag archive.
* If `fast` is specified, the `Payload-Oxum` metadata field (if present) will be
used to check that the payload files are present and accounted for.
* If `full` is specified, all checksums will be regenerated and compared to the corresponding entries in the manifest.
* If `structure` is specified, the bag will be checked for structural validity only.
* If `completeness` is specified, the bag will be checked for both structural validity and completeness (presence) of files listed in all manifests.

----
#### `--validate-profile {bag-only, full}`
Validate a bag against the profile specified by the bag's `BagIt-Profile-Identifier` metadata field, if present. The 
`bag-only` argument keyword can be used to bypass the otherwise automatic bag serialization validation 
(implied by the default value, `full`), and therefore is suitable for use on bag directories.

----
#### `--profile-path <file>`
Optional path to a `Bagit-Profiles-Specification` JSON file. The file format is described
[here](https://bagit-profiles.github.io/bagit-profiles-specification/).
If this argument is not specified, the profile specified by the bag's `BagIt-Profile-Identifier` metadata field will be used.

----
#### `--config-file <file>`
Optional path to a *bdbag* configuration file. The configuration file format is described
[here](./config.md#bdbag.json).
If this argument is not specified, the configuration file will be set to the value of the environment variable `BDBAG_CONFIG_FILE` (if present) or otherwise default to `~/.bdbag/bdbag.json`.

----
#### `--keychain-file <file>`
Optional path to a *keychain* configuration file. The configuration file format is described
[here](./config.md#keychain.json).
If this argument is not specified, the configuration file defaults to: `~/.bdbag/keychain.json`

----
#### `--metadata-file <file>`
Optional path to a JSON formatted metadata file. The configuration file format is described
[here](./config.md#metadata).

----
#### `--ro-metadata-file <file>`
Optional path to a JSON formatted Research Object metadata configuration file. The configuration file format is described
[here](./config.md#ro_metadata).

----
#### `--remote-file-manifest <file>`
Optional path to a JSON formatted remote file manifest. The configuration file format is described
[here](./config.md#remote-file-manifest).
This configuration file is used to add remote file entries to the bag manifest(s) and create the bag fetch.txt file.

----
#### `--ro-manifest-generate {overwrite, update}`
If specified, a RO `manifest.json` file will automatically be created in the `metadata` tagfile directory.
The bag will be introspected and metadata from `bag-info.txt` along with lists of local payload files and files in `fetch.txt` will be used to generate the RO manifest.

----
#### `--quiet`
Suppress logging output.

----
#### `--debug`
Enable debug logging output.

----
#### `-h, --help`
Print a detailed help message and exit.

----
### Argument compatibility
This following table enumerates the various arguments and compatibility modes.

|                 Argument |                           Context                           | Description                                                                                                                                                                                                                                   |
|-------------------------:|:-----------------------------------------------------------:|-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
|                 `<path>` |                             all                             | Required argument. When no other options are specified, creates a bag from the target path if that path is a directory and not already a bag; otherwise, if the path represents an archive file in a supported format, the file is extracted. |
|          `--output-path` |                      bag archive only                       | For a certain set of functions that may extract bag archive files (currently only `materialize`, `extract`, or `validate`), this argument dictates the directory where the output results of the extraction should be placed.                 |
|               `--update` |                        bag dir only                         | An existing bag archive cannot be updated in-place. The bag must first be extracted and then updated.                                                                                                                                         |
|               `--revert` |                        bag dir only                         | Only a bag directory may be reverted to a non-bag directory.                                                                                                                                                                                  |
|             `--archiver` |                        bag dir only                         | A bag archive cannot be created from an existing bag archive.                                                                                                                                                                                 |
|             `--checksum` |                        bag dir only                         | A checksum manifest cannot be added to an existing bag archive. The bag must be extracted, updated, and re-archived.                                                                                                                          |
|      `--prune-manifests` |                  bag dir only, update only                  | Unused manifests may only be pruned from an existing bag during an update operation.                                                                                                                                                          |
|       `--skip-manifests` |                  bag dir only, update only                  | Skipping the recalculation of payload checksums may only be performed on an existing bag during an update operation.                                                                                                                          |
|          `--materialize` |       bag archive, bag dir, or actionable bag URL/URI       | The `--materialze` argument cannot be combined with any other arguments except for `--config-file`, `--keychain-file`, and `--fetch-filter`.                                                                                                  |
|        `--resolve-fetch` |              bag dir only, no create or update              | The resolution (download) of files listed in fetch.txt cannot be executed when creating or updating a bag.                                                                                                                                    |
|         `--fetch-filter` |                  bag dir only, fetch only                   | A fetch filter is only relevant during a `--resolve-fetch`.                                                                                                                                                                                   |
|             `--validate` |                             all                             | A bag directory or a bag archive can be validated.  If a bag archive is to be validated, it is first extracted from the archive to a temporary directory and validated, then the temporary directory is removed.                              |
|     `--validate-profile` |                             all                             | A bag directory or a bag archive can have its profile validated.  If a bag archive is to have its profile validated, it is first extracted from the archive to a temporary directory and validated, then the temporary directory is removed.  |
|         `--profile-path` | bag dir or bag archive, only used with `--validate-profile` | A local profile path is only valid in the context of a `--validate-profile` operation.                                                                                                                                                        |
|          `--config-file` |             bag dir only, create or update only             | A config-file override can be specified whenever a bag is created or updated.                                                                                                                                                                 |
|        `--keychain-file` | bag dir only, used only when `--resolve-fetch` is specified | This argument is only meaningful in the context of remote file resolution.                                                                                                                                                                    |
|        `--metadata-file` |             bag dir only, create or update only             | A metadata config file can be specified whenever a bag is created or updated.                                                                                                                                                                 |
|     `--ro-metadata-file` |             bag dir only, create or update only             | A Research Object metadata config file can be specified whenever a bag is created or updated.                                                                                                                                                 |
| `--remote-file-manifest` |             bag dir only, create or update only             | A remote-file-manifest can be specified whenever a bag is created or updated.                                                                                                                                                                 |
| `--ro-manifest-generate` |                        bag dir only                         | An RO manifest may be auto-generated on any valid bag directory.                                                                                                                                                                              |
|    any extended argument |             bag dir only, create or update only             | Any of the standard bag metadata extended arguments, e.g., `--source-organization` or `--contact-email` may be specified during create or update of a bag directory, but not a bag archive.                                                   |

----
### Examples

----
##### 1. Creating a bag:
The simplest invocation of *bdbag* is to create a bag in-place by specifying an input directory. For example, given a
directory like this:
```
[mdarcy@dev ~]$ ls -lagR test_bag/
test_bag/:
total 12
drwxrwxr-x.  2 mdarcy   38 Apr 20 19:54 .
drwxr-xr-x. 24 mdarcy 4096 Apr 20 19:53 ..
-rw-rw-r--.  1 mdarcy   45 Apr 20 19:53 test1.txt
-rw-rw-r--.  1 mdarcy   56 Apr 20 19:53 test2.txt
```

Executing `bdbag ./test_bag` generates the following output:
```

[mdarcy@dev ~]$ bdbag ./test_bag/

2016-04-20 20:02:14,711 - INFO - creating bag for directory /home/mdarcy/test_bag
2016-04-20 20:02:14,712 - INFO - creating data dir
2016-04-20 20:02:14,712 - INFO - moving test1.txt to /home/mdarcy/test_bag/tmp0ttnWM/test1.txt
2016-04-20 20:02:14,712 - INFO - moving test2.txt to /home/mdarcy/test_bag/tmp0ttnWM/test2.txt
2016-04-20 20:02:14,712 - INFO - moving /home/mdarcy/test_bag/tmp0ttnWM to data
2016-04-20 20:02:14,712 - INFO - writing manifest-sha256.txt
2016-04-20 20:02:14,713 - INFO - writing manifest with 1 processes
2016-04-20 20:02:14,713 - INFO - Generating checksum for file data/test1.txt
2016-04-20 20:02:14,713 - INFO - Generating checksum for file data/test2.txt
2016-04-20 20:02:14,713 - INFO - writing manifest-md5.txt
2016-04-20 20:02:14,713 - INFO - writing manifest with 1 processes
2016-04-20 20:02:14,713 - INFO - Generating checksum for file data/test1.txt
2016-04-20 20:02:14,714 - INFO - Generating checksum for file data/test2.txt
2016-04-20 20:02:14,714 - INFO - writing bagit.txt
2016-04-20 20:02:14,714 - INFO - writing bag-info.txt
2016-04-20 20:02:14,714 - INFO - writing /home/mdarcy/test_bag/tagmanifest-sha256.txt
2016-04-20 20:02:14,715 - INFO - writing /home/mdarcy/test_bag/tagmanifest-md5.txt
2016-04-20 20:02:14,716 - INFO - Created bag: /home/mdarcy/test_bag
```

The resulting bag directory now looks like the following:
```
[mdarcy@dev ~]$ ls -lagR test_bag/
test_bag/:
total 32
drwxrwxr-x.  3 mdarcy 4096 Apr 20 20:02 .
drwxr-xr-x. 24 mdarcy 4096 Apr 20 19:53 ..
-rw-rw-r--.  1 mdarcy  240 Apr 20 20:02 bag-info.txt
-rw-rw-r--.  1 mdarcy   55 Apr 20 20:02 bagit.txt
drwxrwxr-x.  2 mdarcy   38 Apr 20 20:02 data
-rw-rw-r--.  1 mdarcy   98 Apr 20 20:02 manifest-md5.txt
-rw-rw-r--.  1 mdarcy  162 Apr 20 20:02 manifest-sha256.txt
-rw-rw-r--.  1 mdarcy  192 Apr 20 20:02 tagmanifest-md5.txt
-rw-rw-r--.  1 mdarcy  320 Apr 20 20:02 tagmanifest-sha256.txt

test_bag/data:
total 12
drwxrwxr-x. 2 mdarcy   38 Apr 20 20:02 .
drwxrwxr-x. 3 mdarcy 4096 Apr 20 20:02 ..
-rw-rw-r--. 1 mdarcy   45 Apr 20 19:53 test1.txt
-rw-rw-r--. 1 mdarcy   56 Apr 20 19:53 test2.txt
```

We could now run other commands on the newly created bag such as `--validate`, `--validate-profile`, and `--archive` in
order to validate and package the bag up for transport and publication.  However, these operations can all be combined
together into a single invocation when creating or updating a bag, and it is generally more efficient to do so.

Here's how that would be done using the same starting bag directory:
```
[mdarcy@dev ~]$ bdbag ./test_bag/ --validate fast --validate-profile --archive tgz

2016-04-20 20:19:18,869 - INFO - creating bag for directory /home/mdarcy/test_bag
2016-04-20 20:19:18,869 - INFO - creating data dir
2016-04-20 20:19:18,869 - INFO - moving test1.txt to /home/mdarcy/test_bag/tmp39hQy6/test1.txt
2016-04-20 20:19:18,869 - INFO - moving test2.txt to /home/mdarcy/test_bag/tmp39hQy6/test2.txt
2016-04-20 20:19:18,870 - INFO - moving /home/mdarcy/test_bag/tmp39hQy6 to data
2016-04-20 20:19:18,870 - INFO - writing manifest-sha256.txt
2016-04-20 20:19:18,870 - INFO - writing manifest with 1 processes
2016-04-20 20:19:18,870 - INFO - Generating checksum for file data/test1.txt
2016-04-20 20:19:18,870 - INFO - Generating checksum for file data/test2.txt
2016-04-20 20:19:18,870 - INFO - writing manifest-md5.txt
2016-04-20 20:19:18,871 - INFO - writing manifest with 1 processes
2016-04-20 20:19:18,871 - INFO - Generating checksum for file data/test1.txt
2016-04-20 20:19:18,871 - INFO - Generating checksum for file data/test2.txt
2016-04-20 20:19:18,871 - INFO - writing fetch.txt
2016-04-20 20:19:18,871 - INFO - writing bagit.txt
2016-04-20 20:19:18,871 - INFO - writing bag-info.txt
2016-04-20 20:19:18,872 - INFO - writing /home/mdarcy/test_bag/tagmanifest-sha256.txt
2016-04-20 20:19:18,873 - INFO - writing /home/mdarcy/test_bag/tagmanifest-md5.txt
2016-04-20 20:19:18,873 - INFO - Created bag: /home/mdarcy/test_bag
2016-04-20 20:19:18,874 - INFO - Validating bag: /home/mdarcy/test_bag
2016-04-20 20:19:18,874 - INFO - Bag /home/mdarcy/test_bag is valid
2016-04-20 20:19:18,875 - INFO - Verifying bag structure: /home/mdarcy/test_bag
2016-04-20 20:19:18,875 - INFO - Archiving bag (tgz): /home/mdarcy/test_bag
2016-04-20 20:19:18,880 - INFO - Created bag archive: /home/mdarcy/test_bag.tgz
2016-04-20 20:19:18,880 - INFO - Validating bag profile: /home/mdarcy/test_bag
2016-04-20 20:19:18,881 - INFO - Retrieving profile: https://raw.githubusercontent.com/fair-research/bdbag/master/profiles/bdbag-profile.json
2016-04-20 20:19:18,990 - INFO - Bag structure conforms to specified profile
2016-04-20 20:19:18,991 - INFO - Validating bag serialization: /home/mdarcy/test_bag.tgz
2016-04-20 20:19:18,997 - INFO - Bag serialization conforms to specified profile
```
----
##### 2. Updating a bag:
Updating a bag is a similar process.  For example, perhaps we want to add and additional file to an existing bag.
Maybe we would also like to change the checksum algorithms being used.  Finally, we may also want to change the archive
encoding to ZIP format.  While it is possible to perform all of these operations  individually with multiple invocations of `--update`, they can also be combined together into a single command.

First, add or remove files from the bag data directory as desired. In this example we'll just add a file called `test3.txt`:
```

[mdarcy@dev ~]$ ls -lagR test_bag/
test_bag/:
total 32
drwxrwxr-x.  3 mdarcy 4096 Apr 20 20:19 .
drwxr-xr-x. 24 mdarcy 4096 Apr 20 21:03 ..
-rw-rw-r--.  1 mdarcy  240 Apr 20 20:19 bag-info.txt
-rw-rw-r--.  1 mdarcy   55 Apr 20 20:19 bagit.txt
drwxrwxr-x.  2 mdarcy   54 Apr 20 21:03 data
-rw-rw-r--.  1 mdarcy   98 Apr 20 20:19 manifest-md5.txt
-rw-rw-r--.  1 mdarcy  162 Apr 20 20:19 manifest-sha256.txt
-rw-rw-r--.  1 mdarcy  192 Apr 20 20:19 tagmanifest-md5.txt
-rw-rw-r--.  1 mdarcy  320 Apr 20 20:19 tagmanifest-sha256.txt

test_bag/data:
total 16
drwxrwxr-x. 2 mdarcy   54 Apr 20 21:03 .
drwxrwxr-x. 3 mdarcy 4096 Apr 20 20:19 ..
-rw-rw-r--. 1 mdarcy   45 Apr 20 19:53 test1.txt
-rw-rw-r--. 1 mdarcy   56 Apr 20 19:53 test2.txt
-rw-rw-r--. 1 mdarcy   43 Apr 20 21:03 test3.txt
```
Now we can execute an `--update` command to pick up the additional file.  We can also add a new checksum manifest with `--checksum sha1` and change the archive encoding to ZIP format:
```
[mdarcy@dev ~]$ bdbag ./test_bag/ --update --checksum sha1 --archive zip

2016-04-21 15:55:09,880 - INFO - Updating bag: /home/mdarcy/test_bag
2016-04-21 15:55:09,881 - INFO - updating manifest-sha256.txt
2016-04-21 15:55:09,881 - INFO - writing manifest with 1 processes
2016-04-21 15:55:09,881 - INFO - Generating checksum for file data/test1.txt
2016-04-21 15:55:09,881 - INFO - Generating checksum for file data/test2.txt
2016-04-21 15:55:09,881 - INFO - Generating checksum for file data/test3.txt
2016-04-21 15:55:09,882 - INFO - updating manifest-md5.txt
2016-04-21 15:55:09,882 - INFO - writing manifest with 1 processes
2016-04-21 15:55:09,882 - INFO - Generating checksum for file data/test1.txt
2016-04-21 15:55:09,882 - INFO - Generating checksum for file data/test2.txt
2016-04-21 15:55:09,882 - INFO - Generating checksum for file data/test3.txt
2016-04-21 15:55:09,882 - INFO - updating manifest-sha1.txt
2016-04-21 15:55:09,882 - INFO - writing manifest with 1 processes
2016-04-21 15:55:09,883 - INFO - Generating checksum for file data/test1.txt
2016-04-21 15:55:09,883 - INFO - Generating checksum for file data/test2.txt
2016-04-21 15:55:09,883 - INFO - Generating checksum for file data/test3.txt
2016-04-21 15:55:09,883 - INFO - updating bag-info.txt
2016-04-21 15:55:09,883 - INFO - writing /home/mdarcy/test_bag/tagmanifest-sha256.txt
2016-04-21 15:55:09,886 - INFO - writing /home/mdarcy/test_bag/tagmanifest-md5.txt
2016-04-21 15:55:09,887 - INFO - writing /home/mdarcy/test_bag/tagmanifest-sha1.txt
2016-04-21 15:55:09,888 - INFO - Verifying bag structure: /home/mdarcy/test_bag
2016-04-21 15:55:09,889 - INFO - Archiving bag (zip): /home/mdarcy/test_bag
2016-04-21 15:55:09,891 - INFO - Created bag archive: /home/mdarcy/test_bag.zip
```
----
##### 3. Adding additional metadata:
Arbitrary metadata can be added to `bag-info.txt` by specifying a metadata configuration file to the `--metadata-file`
argument. The format of the metadata file is described [here](./config.md#metadata). Metadata files can be specified
when creating or updating a bag.

For example, given the contents of the following metadata file called "test-metadata.json":

```json
{
    "BagIt-Profile-Identifier": "https://raw.githubusercontent.com/fair-research/bdbag/master/profiles/bdbag-profile.json",
    "External-Description": "Simple bdbag test",
    "Source-Organization": "Fair-Research Team",
    "Contact-Name": "mdarcy",
    "Arbitrary-Metadata-Value": "Some arbitrary value"
}
```
Creating a bag that includes this metadata would be executed like this:
```
[mdarcy@dev ~]$ bdbag ./test_bag/ --metadata-file ./test-metadata.json

2016-04-22 11:54:19,705 - INFO - Reading bag metadata from file /home/mdarcy/test-metadata.json
2016-04-22 11:54:19,706 - INFO - creating bag for directory /home/mdarcy/test_bag
2016-04-22 11:54:19,706 - INFO - creating data dir
2016-04-22 11:54:19,706 - INFO - moving test1.txt to /home/mdarcy/test_bag/tmpsS29hK/test1.txt
2016-04-22 11:54:19,706 - INFO - moving test2.txt to /home/mdarcy/test_bag/tmpsS29hK/test2.txt
2016-04-22 11:54:19,706 - INFO - moving /home/mdarcy/test_bag/tmpsS29hK to data
2016-04-22 11:54:19,707 - INFO - writing manifest-sha256.txt
2016-04-22 11:54:19,707 - INFO - writing manifest with 1 processes
2016-04-22 11:54:19,707 - INFO - Generating checksum for file data/test1.txt
2016-04-22 11:54:19,707 - INFO - Generating checksum for file data/test2.txt
2016-04-22 11:54:19,707 - INFO - writing manifest-md5.txt
2016-04-22 11:54:19,707 - INFO - writing manifest with 1 processes
2016-04-22 11:54:19,708 - INFO - Generating checksum for file data/test1.txt
2016-04-22 11:54:19,708 - INFO - Generating checksum for file data/test2.txt
2016-04-22 11:54:19,708 - INFO - writing bagit.txt
2016-04-22 11:54:19,708 - INFO - writing bag-info.txt
2016-04-22 11:54:19,709 - INFO - writing /home/mdarcy/test_bag/tagmanifest-sha256.txt
2016-04-22 11:54:19,709 - INFO - writing /home/mdarcy/test_bag/tagmanifest-md5.txt
2016-04-22 11:54:19,710 - INFO - Created bag: /home/mdarcy/test_bag
```
The resulting `bag-info.txt` will now contain the metadata from the `test-metadata.json` file, in addition to the
required metadata that is automatically added by the bagging software:
```
[mdarcy@dev ~]$ cat test_bag/bag-info.txt

Arbitrary-Metadata-Value: Some arbitrary value
Bag-Software-Agent: bdbag.py <http://github.com/fair-research/bdbag>
BagIt-Profile-Identifier: https://raw.githubusercontent.com/fair-research/bdbag/master/profiles/bdbag-profile.json
Bagging-Date: 2016-04-22
Contact-Name: mdarcy
External-Description: Simple bdbag test
Payload-Oxum: 101.2
Source-Organization: Fair-Research Team
```
----

##### 4. Adding remote file references:
Remote file references are used to create bags which do not necessarily contain all files listed in the payload
manifests, but instead defer the retrieval of these files until the consumer of the bag is ready to download them.
The locations of remote files are listed in a bag's `fetch.txt` file.

Adding remote file references is similar to adding metadata. The `--remote-file-manifest` argument is used to specify
the file that will be used by *bdbag* to generate the manifest entries for the remote files, in addition to generating
the `fetch.txt` file that lists the location information for these files.  The format of the `remote-file-manifest` is
described [here](./config.md#remote-file-manifest).

Here's an example of what a `remote-file-manifest` looks like:
```json
[
  {
    "url":"https://raw.githubusercontent.com/fair-research/bdbag/master/profiles/bdbag-profile.json",
    "length":747,
    "filename":"bdbag-profile.json",
    "sha256":"3275665cda7f4e8e1919f34f22320e4c0eb14004afcbb90ca625bd877efb44f7"
  },
  {
    "url":"ark:/57799/b9dd5t",
    "length": 223,
    "filename": "test-fetch-identifier.txt",
    "sha256": "59e6e0b91b51d49a5fb0e1068980d2e7d2b2001a6d11c59c64156d32e197a626"
  }
]
```
Updating our previously created bag to add these remote files would be done like this:
```
[mdarcy@dev ~]$ bdbag ./test_bag/ --update --remote-file-manifest ./test-fetch-manifest.json

2016-04-22 12:16:30,412 - INFO - Updating bag: /home/mdarcy/test_bag
2016-04-22 12:16:30,412 - INFO - Generating remote file references from ./test-fetch-manifest.json
2016-04-22 12:16:30,413 - INFO - updating manifest-sha256.txt
2016-04-22 12:16:30,413 - INFO - writing manifest with 1 processes
2016-04-22 12:16:30,413 - INFO - Generating checksum for file data/test1.txt
2016-04-22 12:16:30,413 - INFO - Generating checksum for file data/test2.txt
2016-04-22 12:16:30,414 - INFO - updating manifest-md5.txt
2016-04-22 12:16:30,414 - INFO - writing manifest with 1 processes
2016-04-22 12:16:30,414 - INFO - Generating checksum for file data/test1.txt
2016-04-22 12:16:30,414 - INFO - Generating checksum for file data/test2.txt
2016-04-22 12:16:30,414 - INFO - writing fetch.txt
2016-04-22 12:16:30,414 - INFO - updating bag-info.txt
2016-04-22 12:16:30,415 - INFO - writing /home/mdarcy/test_bag/tagmanifest-sha256.txt
2016-04-22 12:16:30,416 - INFO - writing /home/mdarcy/test_bag/tagmanifest-md5.txt
```
The result of this command is a `fetch.txt` file in our bag directory, along with manifest entries for the remote files:
```
[mdarcy@dev ~]$ ls -lagR test_bag/
test_bag/:
total 32
drwxrwxr-x.  3 mdarcy  180 Sep 19 20:25 .
drwxr-xr-x. 11 mdarcy 4096 Sep 19 20:27 ..
-rw-rw-r--.  1 mdarcy  349 Sep 18 19:13 bag-info.txt
-rw-rw-r--.  1 mdarcy   55 Sep 12 19:18 bagit.txt
drwxrwxr-x.  2 mdarcy   40 Sep 19 20:25 data
-rw-rw-r--.  1 mdarcy  170 Sep 18 19:13 fetch.txt
-rw-rw-r--.  1 mdarcy   98 Sep 18 19:13 manifest-md5.txt
-rw-rw-r--.  1 mdarcy  349 Sep 18 19:13 manifest-sha256.txt
-rw-rw-r--.  1 mdarcy  235 Sep 18 19:13 tagmanifest-md5.txt
-rw-rw-r--.  1 mdarcy  395 Sep 18 19:13 tagmanifest-sha256.txt

test_bag/data:
total 8
drwxrwxr-x. 2 mdarcy  40 Sep 19 20:25 .
drwxrwxr-x. 3 mdarcy 180 Sep 19 20:25 ..
-rw-rw-r--. 1 mdarcy  30 Sep 12 19:17 test1.txt
-rw-rw-r--. 1 mdarcy  38 Sep 12 19:17 test2.txt

[mdarcy@dev ~]$ cat test_bag/fetch.txt

https://raw.githubusercontent.com/fair-research/bdbag/master/profiles/bdbag-profile.json        747     data/bdbag-profile.json
ark:/57799/b9dd5t       223     data/test-fetch-identifier.txt

[mdarcy@dev ~]$  cat test_bag/manifest-md5.txt

dad6891eb4148dfed2d162370983d06f  data/test1.txt
11069c18ee13a990265cf944359dbca5  data/test2.txt

[mdarcy@dev ~]$  cat test_bag/manifest-sha256.txt

2d874441132225aa2d63754efb7af0aa2c22bd63c5225dba73e3f49d360e9e63  data/test1.txt
46e94d2bc7804ae2c92674e0d16e8a8b26dc1f7eba90b1d225c88b67d566761d  data/test2.txt
3275665cda7f4e8e1919f34f22320e4c0eb14004afcbb90ca625bd877efb44f7  data/bdbag-profile.json
59e6e0b91b51d49a5fb0e1068980d2e7d2b2001a6d11c59c64156d32e197a626  data/test-fetch-identifier.txt
```

----
##### 5. Resolving remote file references:
Remote files can be resolved (downloaded) using *bdbag* by specifying the `--resolve-fetch` argument.  The
`--resolve-fetch` argument requires one of the following keyword options to be specified: `all` or `missing`.
The `missing` option only attempts to fetch files that do not already exist in the bag payload directory.
The `all` option causes all fetch files to be re-acquired, even if they already exist in the bag payload directory.

For any given bag, it is important to establish the bag's validity before making use of the
contents. If one were to receive, for example, the bag containing remote file references from the previous sample and
attempt to validate it, the following output would be produced:
```
[mdarcy@dev ~]$ bdbag ./test_bag/ --validate fast

2019-09-19 20:30:00,750 - INFO - Validating bag: /home/mdarcy/test_bag
2019-09-19 20:30:00,753 - WARNING - BagValidationError: A BagValidationError may be transient if the bag contains unresolved remote file references from a fetch.txt file. In this case the bag is incomplete but not necessarily invalid. Resolve remote file references (if any) and re-validate.

Error: [BagValidationError] Payload-Oxum validation failed. Expected 4 files and 1038 bytes but found 2 files and 68 bytes
```
Resolving remote references on the example bag would yield:
```
[mdarcy@dev ~]$ bdbag ./test_bag/ --resolve-fetch all

2019-09-19 20:31:01,790 - INFO - Attempting to resolve remote file references from /home/mdarcy/test_bag/fetch.txt.
2019-09-19 20:31:01,793 - INFO - Attempting GET from URL: https://raw.githubusercontent.com/fair-research/bdbag/master/profiles/bdbag-profile.json
2019-09-19 20:31:01,983 - INFO - File [/home/mdarcy/test_bag/data/bdbag-profile.json] transfer successful. 0.729 KB transferred. Elapsed time: 0:00:00.007388.
2019-09-19 20:31:01,985 - INFO - Attempting to resolve http://n2t.net/ark:/57799/b9dd5t into a valid set of URLs.
2019-09-19 20:31:02,508 - INFO - The identifier ark:/57799/b9dd5t resolved into the following locations: [https://raw.githubusercontent.com/fair-research/bdbag/master/test/test-data/test-http/test-fetch-identifier.txt]
2019-09-19 20:31:02,509 - INFO - Attempting GET from URL: https://raw.githubusercontent.com/fair-research/bdbag/master/test/test-data/test-http/test-fetch-identifier.txt
2019-09-19 20:31:02,650 - INFO - File [/home/mdarcy/test_bag/data/test-fetch-identifier.txt] transfer successful. 0.218 KB transferred. Elapsed time: 0:00:00.006668.
2019-09-19 20:31:02,650 - INFO - Fetch complete. Elapsed time: 0:00:00.857709

```
The bag directory would now contain the following files:
```
[mdarcy@dev ~]$ ls -lagR test_bag/
test_bag/:
total 32
drwxrwxr-x.  3 mdarcy  180 Sep 19 20:25 .
drwxr-xr-x. 12 mdarcy 4096 Sep 19 20:30 ..
-rw-rw-r--.  1 mdarcy  349 Sep 18 19:13 bag-info.txt
-rw-rw-r--.  1 mdarcy   55 Sep 12 19:18 bagit.txt
drwxrwxr-x.  2 mdarcy   99 Sep 19 20:31 data
-rw-rw-r--.  1 mdarcy  170 Sep 18 19:13 fetch.txt
-rw-rw-r--.  1 mdarcy   98 Sep 18 19:13 manifest-md5.txt
-rw-rw-r--.  1 mdarcy  349 Sep 18 19:13 manifest-sha256.txt
-rw-rw-r--.  1 mdarcy  235 Sep 18 19:13 tagmanifest-md5.txt
-rw-rw-r--.  1 mdarcy  395 Sep 18 19:13 tagmanifest-sha256.txt

test_bag/data:
total 16
drwxrwxr-x. 2 mdarcy  99 Sep 19 20:31 .
drwxrwxr-x. 3 mdarcy 180 Sep 19 20:25 ..
-rw-rw-r--. 1 mdarcy 747 Sep 19 20:31 bdbag-profile.json
-rw-rw-r--. 1 mdarcy  30 Sep 12 19:17 test1.txt
-rw-rw-r--. 1 mdarcy  38 Sep 12 19:17 test2.txt
-rw-rw-r--. 1 mdarcy 223 Sep 19 20:31 test-fetch-identifier.txt

```
Finally, we can run `--validate full` on the bag in order to verify that the bag is now both complete and valid:
```
[mdarcy@dev ~]$ bdbag ./test_bag/ --validate full

2019-09-19 20:32:11,145 - INFO - Validating bag: /home/mdarcy/test_bag
2019-09-19 20:32:11,148 - INFO - Verifying checksum for file /home/mdarcy/test_bag/data/test1.txt
2019-09-19 20:32:11,149 - INFO - Verifying checksum for file /home/mdarcy/test_bag/data/test2.txt
2019-09-19 20:32:11,149 - INFO - Verifying checksum for file /home/mdarcy/test_bag/data/bdbag-profile.json
2019-09-19 20:32:11,149 - INFO - Verifying checksum for file /home/mdarcy/test_bag/data/test-fetch-identifier.txt
2019-09-19 20:32:11,149 - INFO - Verifying checksum for file /home/mdarcy/test_bag/bag-info.txt
2019-09-19 20:32:11,150 - INFO - Verifying checksum for file /home/mdarcy/test_bag/bagit.txt
2019-09-19 20:32:11,150 - INFO - Verifying checksum for file /home/mdarcy/test_bag/fetch.txt
2019-09-19 20:32:11,150 - INFO - Verifying checksum for file /home/mdarcy/test_bag/manifest-md5.txt
2019-09-19 20:32:11,150 - INFO - Verifying checksum for file /home/mdarcy/test_bag/manifest-sha256.txt
2019-09-19 20:32:11,150 - INFO - Bag /home/mdarcy/test_bag is valid
```

----
