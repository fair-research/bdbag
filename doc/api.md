# *bdbag*: Application Programming Interface (API)

## Summary
Most of the *bdbag* functional logic is available via an API.  Developers who wish to incorporate *bdbag* into their own code can do so by importing the *bdbag* module and make use of the functions contained within **bdbag_api.py**.

The command-line interface is built upon the API in this manner and can be used as a reference implementation.

## API Documentation

* [bdbag_api.py](#bdbag_api)
    * [configure_logging(level=logging.INFO, logpath=None)](#configure_logging)
    * [create_default_config()](#create_default_config)
    * [read_config(config_file)](#read_config)
    * [read_metadata(metadata_file)](#read_metadata)
    * [is_bag(bag_path)](#is_bag)
    * [cleanup_bag(bag_path)](#cleanup_bag)
    * [revert_bag(bag_path)](#revert_bag)
    * [prune_bag_manifests(bag)](#prune_bag_manifests)
    * [check_payload_consistency(bag, skip_remote=False, quiet=False)](#check_payload_consistency)
    * [make_bag(bag_path, update=False, algs=None, prune_manifests=False, metadata=None, metadata_file=None, remote_file_manifest=None, config_file=bdbag.DEFAULT_CONFIG_FILE, ro_metadata=None, ro_metadata_file=None)](#make_bag)
    * [resolve_fetch(bag_path, force=False, keychain_file=DEFAULT_KEYCHAIN_FILE)](#resolve_fetch)
    * [generate_ro_manifest(bag_path, overwrite=False)](#generate_ro_manifest)
    * [archive_bag(bag_path, bag_archiver)](#archive_bag)
    * [extract_bag(bag_path, output_path=None, temp=False)](#extract_bag)
    * [validate_bag(bag_path, fast=False, config_file=bdbag.DEFAULT_CONFIG_FILE)](#validate_bag)
    * [validate_bag_profile(bag_path, profile_path=None)](#validate_bag_profile)
    * [validate_bag_serialization(bag_path, bag_profile)](#validate_bag_serialization)
    * [validate_bag_structure(bag_path, skip_remote=True)](#validate_bag_structure)

<a name="bdbag_api"></a>
### bdbag_api.py
The primary Python file which contains the *bdbag* API functions.  After installing bdbag, append the following to the top of your script.

```python
from bdbag import bdbag_api
```

-----

<a name="configure_logging"></a>
#### configure_logging(level=logging.INFO, logpath=None)
Set the logging level and optional output path for log statements.

| Param | Type | Description |
| --- | --- | --- |
|level|[Python logging module level constant](https://docs.python.org/2/library/logging.html#logging-levels)|The logging event filter level.
|logpath|`string`|A path to a file to redirect logging statements to. Default is **stdout**.

-----

<a name="create_default_config"></a>
#### create_default_config()
Creates the default configuration file `bdbag.json` if it does not already exist.

-----

<a name="read_config"></a>
#### read_config(config_file) ⇒ `dict`
Reads the configuration file specified by `config_file` into a dictionary object. If the file path specified is
the default configuration file location `~/.bdbag/bdbag.json`, and that file does not already exist, it is created.

| Param | Type | Description |
| --- | --- | --- |
|config_file|`string`|A normalized, absolute path to a configuration file.

**Returns**: `dict` - The configuration data.

-----

<a name="read_metadata"></a>
#### read_metadata(metadata_file) ⇒ `dict`
Reads the configuration file specified by `metadata_file` into a dictionary object.  The format of `metadata_file` is
described [here](./config.md#metadata).

| Param | Type | Description |
| --- | --- | --- |
|metadata_file|`string`|A normalized, absolute path to a metadata file.

**Returns**: `dict` - The metadata.

-----

<a name="is_bag"></a>
#### is_bag(bag_path) ⇒ `boolean`
Checks if the path denoted by `bag_path` is a directory that contains a valid bag structure.

| Param | Type | Description |
| --- | --- | --- |
|bag_path|`string`|A normalized, absolute path to the bag location.

**Returns**: `boolean` - Whether the path specified by `bag_path` contains a valid bag structure.

-----

<a name="cleanup_bag"></a>
#### cleanup_bag(bag_path)
Deletes the directory tree denoted by `bag_path`.

| Param | Type | Description |
| --- | --- | --- |
|bag_path|`string`|A normalized, absolute path to a bag directory.

-----

<a name="revert_bag"></a>
#### revert_bag(bag_path)
Revert an existing bag directory back to a normal directory, deleting all bag metadata files. Payload files in the `data` directory will be moved back to the directory root, and the `data` directory will be deleted.

| Param | Type | Description |
| --- | --- | --- |
|bag_path|`string`|A normalized, absolute path to a bag directory.

-----

<a name="prune_bag_manifests"></a>
#### prune_bag_manifests(bag) ⇒ `boolean`
For the given `bag` object, removes any file and tagfile manifests for checksums that are not listed in that object's
`algs` member variable.

| Param | Type | Description |
| --- | --- | --- |
|bag|`bag`|a `bag` object such as that returned by `make_bag`

**Returns**: `boolean` - If any manifests were pruned or not.

-----

<a name="check_payload_consistency"></a>
#### check_payload_consistency(bag, skip_remote=False, quiet=False)  ⇒ `boolean`
Checks if the payload files in the bag's `data` directory are consistent with the bag's file manifests and the bag's
`fetch.txt` file, if any.

| Param | Type | Description |
| --- | --- | --- |
|bag|`bag`|a `bag` object such as that returned by `make_bag`
|skip_remote|`boolean`|do not include any of the bag's remote file entries or `fetch.txt` entries in the check
|quiet|`boolean`|do not emit any logging messages if inconsistencies are encountered

**Returns**: `boolean` - If all payload files can be accounted for either locally or as remote entries in `fetch.txt`,
and that there are no additional files present that are not listed in either `fetch.txt` or the bag's file manifests.

-----

<a name="make_bag"></a>
#### make_bag(bag_path, update=False, algs=None, prune_manifests=False, metadata=None, metadata_file=None, remote_file_manifest=None, config_file=bdbag.DEFAULT_CONFIG_FILE, ro_metadata=None, ro_metadata_file=None)  ⇒ `bag`
Creates or updates the bag denoted by the `bag_path` argument.

| Param | Type | Description |
| --- | --- | --- |
|bag_path|`string`|A normalized, absolute path to a bag directory.
|algs|`list`|A list of checksum algorithms to use for calculating file fixities. When creating a bag, only the checksums present in this variable will be used. When updating a bag, this function will take the union of any existing bag algorithms and what is specified by this parameter, ***except*** when the `prune_manifests` parameter is specified, in which case then only the algorithms specifed by this parameter will be used.
|update|`boolean`|If `bag_path` represents an existing bag, update it. If this parameter is not specified when invoking this function on an existing bag, the function is essentially a NOOP and will emit a logging message to that effect.
|save_manifests|`boolean`|Defaults to `True`. If true, saves all manifests, recalculating  all checksums and regenerating `fetch.txt`. If false, only tagfile manifest checksums are recalculated.  Use this flag as an optimization (to avoid recalculating payload file checksums) when only the bag metadata has been changed. This parameter is only meaningful during update operations, otherwise it is ignored.
|prune_manifests|`boolean`|Removes any file and tagfile manifests for checksums that are not listed in the `algs` variable.  This parameter is only meaningful during update operations, otherwise it is ignored.
|metadata|`dict`|A dictionary of key-value pairs that will be written directly to the bag's 'bag-info.txt' file.
|metadata_file|`string`|A JSON file representation of metadata that will be written directly to the bag's 'bag-info.txt' file. The format of this metadata is described [here](./config.md#metadata).
|remote_file_manifest|`string`|A path to a JSON file representation of remote file entries that will be used to add remote files to the bag file manifest(s) and used to create the bag's `fetch.txt`. The format of this file is described [here](./config.md/#remote-file-manifest).
|config_file|`string`|A JSON file representation of configuration data that is used during bag creation and update. The format of this file is described [here](./config.md#bdbag.json).
|ro_metadata|`dict`|A dictionary that will be used to serialize data into one or more JSON files into the bag's `metadata` directory. The format of this metadata is described [here](./config.md#ro_metadata).
|ro_metadata_file|`string`|A path to a JSON file representation of RO metadata that will be used to serialize data into one or more JSON files into the bag's `metadata` directory. The format of this metadata is described [here](./config.md#ro_metadata).

**Returns**: `bag` - An instantiated [bagit-python](https://github.com/LibraryOfCongress/bagit-python/blob/master/bagit.py) `bag` compatible class object.

-----

<a name="resolve_fetch"></a>
#### resolve_fetch(bag_path, force=False, keychain_file=DEFAULT_KEYCHAIN_FILE) ⇒ `boolean`
Attempt to download files listed in the bag's `fetch.txt` file.  The method of transfer is dependent on the protocol
scheme of the URL field in `fetch.txt`.  Note that not all file transfer protocols are supported at this time.

Additionally, some URLs may require authentication in order to retrieve protected files.  In this case, the
`keychain.json` configuration file must be configured with the appropriate authentication mechanism and credentials to
use for a given base URL. The documentation for `keychain.json` can be found [here](./config.md#keychain.json).

| Param | Type | Description |
| --- | --- | --- |
|bag_path|`string`|A normalized, absolute path to a bag directory.
|force|`boolean`|A `boolean` value indicating whether to retrieve all listed files in `fetch.txt` or only those which are not currently found in the bag payload directory.
|keychain_file|`string`|A normalized, absolute path to a `keychain.json` file, or if not specified, the default location will be used: `~/.bdbag/keychain.json`

**Returns**: `boolean` - If all remote files were resolved successfully or not. Also returns `True` if the function invocation resulted in a NOOP.

-----

<a name="generate_ro_manifest"></a>
#### generate_ro_manifest(bag_path, overwrite=False)
Automatically create a RO `manifest.json` file in the `metadata` tagfile directory.
The bag will be introspected and metadata from `bag-info.txt`, along with lists of local payload files and files in `fetch.txt`, will be used to generate the RO manifest.

Note: the contents of the `manifest.json` file output by this method are limited to what can be automatically generated by introspecting the bag structure and it's metadata.
Currently, this includes only provenance members of the top-level RO object, and the list of aggregated resources (`aggregates`) contained within the bag.

| Param | Type | Description |
| --- | --- | --- |
|bag_path|`string`|A normalized, absolute path to a bag directory.
|overwrite|`boolean`|A `boolean` value indicating whether to overwrite or update to any existing RO `metadata/manifest.json` file.

-----

<a name="archive_bag"></a>
#### archive_bag(bag_path, bag_archiver) ⇒ `string`
Creates a single, serialized bag archive file from the directory specified by `bag_path` using the format specified by
`bag_archiver`. The resulting archive file is BagIt spec
compliant, i.e., complies with the rules of **"Section 4: Serialization"** of the
[BagIt Specification](https://datatracker.ietf.org/doc/draft-kunze-bagit/).

| Param | Type | Description |
| --- | --- | --- |
|bag_path|`string`|A normalized, absolute path to a bag directory.
|bag_archiver|`string`|One of the following case-insensitive string values: `zip`, `tar`, or `tgz`.

**Returns**: `string` - The normalized, absolute path of the directory of the created archive file.

-----

<a name="extract_bag"></a>
#### extract_bag(bag_path, output_path=None, temp=False) ⇒ `string`
Extracts the bag specified by `bag_path` to the based directory specified by `output_path`, or, if the `temp` parameter is specified, an operating system dependent temporary path.

| Param | Type | Description |
| --- | --- | --- |
|bag_path|`string`|A normalized, absolute path to a bag directory.
|output_path|`string`|A normalized, absolute path to a base directory where the bag should be extracted.
|temp|`boolean`|A `boolean` value indicating whether to extract this bag to a temporary directory or not. If `True`, overrides the `output_path` variable, if specified.

**Returns**: `string` - The normalized, absolute path of the directory where the bag was extracted.

-----
<a name="validate_bag"></a>
#### validate_bag(bag_path, fast=False, config_file=bdbag.DEFAULT_CONFIG_FILE) ⇒ `boolean`
Validates a bag archive or bag directory.  If a bag archive is specified, it is first extracted to a temporary directory
before validation and then the temporary directory is deleted after validation completes.

If `fast` is `True`, then only the total count of payload files and the total byte count of all files are compared to the bag's
`Payload-Oxum` metadata field, if present.  Otherwise, checksums will be recalculated for every file present in the bag
payload directory and compared against the checksum values in the file manifest(s).

| Param | Type | Description |
| --- | --- | --- |
|bag_path|`string`|A normalized, absolute path to a bag directory or bag archive file.
|fast|`boolean`|If `True` only check payload contents against `Payload-Oxum`, otherwise re-calculate checksums for all payload files.
|config_file|`string`|A normalized, absolute path to a *bdbag* configuration file. Uses the default configuration file if  not specified.

**Returns**: `boolean` - If the bag passed validation or not.

-----
<a name="validate_bag_profile"></a>
#### validate_bag_profile(bag_path, profile_path=None) ⇒ `boolean`
Validates a bag archive or bag directory against a bag profile. If a bag archive is specified, it is first extracted to a temporary directory
before profile validation and then the temporary directory is deleted after profile validation completes.

If a `profile_path` is specified, the bag is validated against that profile. Otherwise, this function checks the bag's `bag-info.txt` for a valid `BagIt-Profile-Identifier` metadata field and attemps to resolve that field's value as a URL link to the profile.

| Param | Type | Description |
| --- | --- | --- |
|bag_path|`string`|A normalized, absolute path to a bag directory or bag archive file.
|bag_profile|`string`|A normalized, absolute path to a [BagIt-Profile](https://github.com/ruebot/bagit-profiles) file.

**Returns**: `boolean` - If the bag passed profile validation or not.

-----
<a name="validate_bag_serialization"></a>
#### validate_bag_serialization(bag_path, bag_profile) ⇒ `boolean`
Validates a bag archive's serialization format against a bag profile's `Serialization` and `Accept-Serialization`
constraints, if any.

| Param | Type | Description |
| --- | --- | --- |
|bag_path|`string`|A normalized, absolute path to a bag archive file.
|bag_profile|`string`|A normalized, absolute path to a [BagIt-Profile](https://github.com/ruebot/bagit-profiles) file.

**Returns**: `boolean` - If the bag passed profile serialization validation or not.

-----
<a name="validate_bag_structure"></a>
#### validate_bag_structure(bag_path, check_remote=False)
Checks a bag's structural conformance as well as payload consistency between file manifests, the filesystem, and fetch.txt.

| Param | Type | Description |
| --- | --- | --- |
|bag_path|`string`|A normalized, absolute path to a bag directory or bag archive file.
|check_remote|`boolean`|A boolean value indicating if remote files should be included in the the consistency check.

**Throws**: `BagValidationError` - If the bag structure could not be validated.

