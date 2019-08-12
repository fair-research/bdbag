# *bdbag*: Application Programming Interface (API)

## Summary
Most of the *bdbag* functional logic is available via an API.  Developers who wish to incorporate *bdbag* into their own code can do so by importing the *bdbag* module and make use of the functions contained within **bdbag_api.py**.

The command-line interface is built upon the API in this manner and can be used as a reference implementation.

## API Documentation

* [bdbag_api.py](#bdbag_api)
    * [archive_bag](#archive_bag)
    * [check_payload_consistency](#check_payload_consistency)
    * [cleanup_bag](#cleanup_bag)
    * [configure_logging](#configure_logging)
    * [extract_bag](#extract_bag)
    * [generate_ro_manifest](#generate_ro_manifest)
    * [is_bag](#is_bag)
    * [make_bag](#make_bag)
    * [materialize](#materialize)
    * [prune_bag_manifests](#prune_bag_manifests)
    * [read_metadata](#read_metadata)
    * [resolve_fetch](#resolve_fetch)
    * [revert_bag](#revert_bag)
    * [validate_bag](#validate_bag)
    * [validate_bag_profile](#validate_bag_profile)
    * [validate_bag_serialization](#validate_bag_serialization)
    * [validate_bag_structure](#validate_bag_structure)

* [bdbag_config.py](bdbag_config)
    * [bootstrap_config](#bootstrap_config)
    * [read_config](#read_config)
    * [upgrade_config](#upgrade_config)
    * [write_config](#write_config)

* [bdbag](#bdbag_module)
    * [filter_dict](#filter_dict)
    * [inspect_path](#inspect_path)
<a name="bdbag_api"></a>
## bdbag_api.py
The primary Python file which contains the *bdbag* API functions.  After installing bdbag, append the following to the top of your script.
```python
from bdbag import bdbag_api
```

<a name="archive_bag"></a>
## archive_bag
```python
archive_bag(bag_path, bag_archiver)
```
Creates a single, serialized bag archive file from the directory specified by `bag_path` using the format specified by
`bag_archiver`. The resulting archive file is BagIt spec
compliant, i.e., complies with the rules of **"Section 4: Serialization"** of the
[BagIt Specification](https://datatracker.ietf.org/doc/draft-kunze-bagit/).

##### Parameters
| Param | Type | Description |
| --- | --- | --- |
|bag_path|`string`|A normalized, absolute path to a bag directory.
|bag_archiver|`string`|One of the following case-insensitive string values: `zip`, `tar`, or `tgz`.

**Returns**: `string` - The normalized, absolute path of the directory of the created archive file.

-----
<a name="check_payload_consistency"></a>
## check_payload_consistency
```python
check_payload_consistency(bag, skip_remote=False, quiet=False)
```
Checks if the payload files in the bag's `data` directory are consistent with the bag's file manifests and the bag's
`fetch.txt` file, if any.

##### Parameters
| Param | Type | Description |
| --- | --- | --- |
|bag|`bag`|a `bag` object such as that returned by `make_bag`
|skip_remote|`boolean`|do not include any of the bag's remote file entries or `fetch.txt` entries in the check
|quiet|`boolean`|do not emit any logging messages if inconsistencies are encountered

**Returns**: `boolean` - If all payload files can be accounted for either locally or as remote entries in `fetch.txt`,
and that there are no additional files present that are not listed in either `fetch.txt` or the bag's file manifests.

-----
<a name="cleanup_bag"></a>
## cleanup_bag
```python
cleanup_bag(bag_path)
```
Deletes the directory tree denoted by `bag_path`.

##### Parameters
| Param | Type | Description |
| --- | --- | --- |
|bag_path|`string`|A normalized, absolute path to a bag directory.

-----
<a name="configure_logging"></a>
## configure_logging
```python
configure_logging(level=logging.INFO, logpath=None)
```
Set the logging level and optional file output path for log statements.

##### Parameters
| Param | Type | Description |
| --- | --- | --- |
|level|[Python logging module level constant](https://docs.python.org/2/library/logging.html#logging-levels)|The logging event filter level.
|logpath|`string`|A path to a file to redirect logging statements to. Default is **stdout**.

-----
<a name="extract_bag"></a>
## extract_bag
```python
extract_bag(bag_path, output_path=None, temp=False)
```
Extracts the bag specified by `bag_path` to the based directory specified by `output_path`, or, if the `temp` parameter is specified, an operating system dependent temporary path.

##### Parameters
| Param | Type | Description |
| --- | --- | --- |
|bag_path|`string`|A normalized, absolute path to a bag directory.
|output_path|`string`|A normalized, absolute path to a base directory where the bag should be extracted.
|temp|`boolean`|A `boolean` value indicating whether to extract this bag to a temporary directory or not. If `True`, overrides the `output_path` variable, if specified.

**Returns**: `string` - The normalized, absolute path of the directory where the bag was extracted.

-----
<a name="generate_ro_manifest"></a>
## generate_ro_manifest
```python
generate_ro_manifest(bag_path, overwrite=False)
```
Automatically create a RO `manifest.json` file in the `metadata` tagfile directory.
The bag will be introspected and metadata from `bag-info.txt`, along with lists of local payload files and files in `fetch.txt`, will be used to generate the RO manifest.

Note: the contents of the `manifest.json` file output by this method are limited to what can be automatically generated by introspecting the bag structure and it's metadata.
Currently, this includes only provenance members of the top-level RO object, and the list of aggregated resources (`aggregates`) contained within the bag.

##### Parameters
| Param | Type | Description |
| --- | --- | --- |
|bag_path|`string`|A normalized, absolute path to a bag directory.
|overwrite|`boolean`|A `boolean` value indicating whether to overwrite or update to any existing RO `metadata/manifest.json` file.

-----
<a name="is_bag"></a>
## is_bag
```python
is_bag(bag_path)
```
Checks if the path denoted by `bag_path` is a directory that contains a valid bag structure.

##### Parameters
| Param | Type | Description |
| --- | --- | --- |
|bag_path|`string`|A normalized, absolute path to the bag location.

**Returns**: `boolean` - Whether the path specified by `bag_path` contains a valid bag structure.

-----
<a name="prune_bag_manifests"></a>
## prune_bag_manifests
```python
prune_bag_manifests(bag)
```
For the given `bag` object, removes any file and tagfile manifests for checksums that are not listed in that object's
`algs` member variable.

##### Parameters
| Param | Type | Description |
| --- | --- | --- |
|bag|`bag`|a `bag` object such as that returned by `make_bag`

**Returns**: `boolean` - If any manifests were pruned or not.

-----
<a name="make_bag"></a>
## make_bag
```python
make_bag(bag_path,
         update=False,
         algs=None,
         prune_manifests=False,
         metadata=None,
         metadata_file=None,
         remote_file_manifest=None,
         config_file=bdbag.DEFAULT_CONFIG_FILE,
         ro_metadata=None,
         ro_metadata_file=None)
```
Creates or updates the bag denoted by the `bag_path` argument.

##### Parameters
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
<a name="materialize"></a>
## materialize
```python
materialize(input_path,
            output_path=None,
            fetch_callback=None,
            validation_callback=None,
            keychain_file=DEFAULT_KEYCHAIN_FILE,
            config_file=DEFAULT_CONFIG_FILE,
            filter_expr=None,
            force=False,
            **kwargs)
```
The `materialize` function is a bag bootstrapper. When invoked,
it will attempt to fully _reconstitute_ a bag by performing multiple
possible actions depending on the context of the `input_path` parameter.
1. If `input_path` is a URL or a URI of a resolvable identifier scheme, the file
referenced by this value will first be downloaded to the current directory.
2. If the `input_path` (or previously downloaded file) represents a
local path to a supported archive format, the archive will be extracted
to the current directory.
3. If the `input_path` (or previously extracted file) represents a valid
bag directory, any remote file references contained within the bag's
`fetch.txt` file will attempt to be resolved. If the `input_path` does 
not represent a valid bag directory, the function will terminate without 
errors and emit a log message stating this fact.
4. Full validation will be run on the materialized bag. If any one of
these steps fail, an error is raised.

##### Parameters
| Param | Type | Description |
| --- | --- | --- |
|input_path|`string`|An input path that must evaluate to either a local file path, local directory path, or an actionable URL/URI.
|output_path|`string`|The base output path for staging the materialization. Defaults to the current working directory.
|fetch_callback|`function(current, total)`|A callback function where the `current` parameter is the current item being _fetched_ out of the `total` number of items to be _fetched_. The callback function should return a `boolean` indicating whether the calling function should continue processing or interrupt.
|validation_callback|`function(current, total)`|A callback function where the `current` parameter is the current item being _validated_ out of the `total` number of items to be _validated_. The callback function should return a `boolean` indicating whether the calling function should continue processing or interrupt.
|keychain_file|`string`|A normalized, absolute path to a keychain file. Defaults to the expansion of `~/.bdbag/keychain.json`.
|config_file|`string`|A normalized, absolute path to a configuration file. Defaults to the expansion of `~/.bdbag/bdbag.json`.
|filter_expr|`string`|A [selective fetch filter](#resolve_fetch_filter). NOTE: if a selective fetch filter is used to materialize an incomplete bag, a `BagValidationException` will be thrown during validation. This may be an acceptable error in some cases.
|force|`boolean`|A boolean indicating that _all_ files listed in `fetch.txt` should be retrieved, regardless of whether they already exist in the payload directory or not. Otherwise, only missing or incomplete files will be retrieved.
|**kwargs|`dict`|Unpacked keyword arguments in dictionary format.

**Raises**: `BagValidationError`, `RuntimeError` if the bag could not be materialized and validated successfully.

**Returns**: `string` - The normalized, absolute path to the directory of the materialized bag.

-----
<a name="read_metadata"></a>
## read_metadata
```python
read_metadata(metadata_file)
```
Reads the configuration file specified by `metadata_file` into a dictionary object.  The format of `metadata_file` is
described [here](./config.md#metadata).

##### Parameters
| Param | Type | Description |
| --- | --- | --- |
|metadata_file|`string`|A normalized, absolute path to a metadata file.

**Returns**: `dict` - The metadata.

-----
<a name="resolve_fetch"></a>
## resolve_fetch
```python
resolve_fetch(bag_path,
              force=False,
              callback=None,
              keychain_file=DEFAULT_KEYCHAIN_FILE,
              config_file=DEFAULT_CONFIG_FILE,
              filter_expr=None,
              **kwargs)
```
Attempt to download files listed in the bag's `fetch.txt` file.  The method of transfer is dependent on the protocol
scheme of the URL field in `fetch.txt`.  Note that not all file transfer protocols are supported at this time.

Additionally, some URLs may require authentication in order to retrieve protected files.  In this case, the
`keychain.json` configuration file must be configured with the appropriate authentication mechanism and credentials to
use for a given base URL. The documentation for `keychain.json` can be found [here](./config.md#keychain.json).

<a name="resolve_fetch_filter"></a>
##### Filter Expressions (Selective Fetch)
The argument `filter_expr` takes a string of the form: `<column><operator><value>` where:
*  `column` is one of the following literal values corresponding to the field names in `fetch.txt`: `url`, `length`, or `filename`
* `<operator>` is a predefined token. See syntax [below](#filter_dict_syntax).
* `value` is a string or integer

With this mechanism you can do various string-based pattern matching on `filename` and `url`. For example:

* `filter_expr="filename$*.txt"`
* `filter_expr="filename^*README"`
* `filter_expr="filename==data/change.log"`
* `filter_expr="url=*/requirements/"`

The above commands will get all files ending with ".txt", all files beginning with "README", the exact file "data/change.log", and all urls containing "/requirements/" in the url path.

You can also use `length` and the integer relation operators to easily limit the size of the files retrieved, for example:

* `filter_expr="length<=1000000"`

##### Parameters
| Param | Type | Description |
| --- | --- | --- |
|bag_path|`string`|A normalized, absolute path to a bag directory.
|force|`boolean`|A `boolean` value indicating whether to retrieve all listed files in `fetch.txt` or only those which are not currently found in the bag payload directory.
|callback|`function(current, total)`|A callback function where the `current` parameter is the current item being _fetched_ out of the `total` number of items to be _fetched_. The callback function should return a `boolean` indicating whether the calling function should continue processing or interrupt.
|keychain_file|`string`|A normalized, absolute path to a keychain file. Defaults to the expansion of `~/.bdbag/keychain.json`.
|config_file|`string`|A normalized, absolute path to a configuration file. Defaults to the expansion of `~/.bdbag/bdbag.json`.
|filter_expr|`string`|A string of the form: `<column><operator><value>`. See syntax [below](#filter_dict_syntax).

**Returns**: `boolean` - If all remote files were resolved successfully or not. Also returns `True` if the function invocation resulted in a NOOP.

-----
<a name="revert_bag"></a>
## revert_bag
```python
revert_bag(bag_path)
```
Revert an existing bag directory back to a normal directory, deleting all bag metadata files. Payload files in the `data` directory will be moved back to the directory root, and the `data` directory will be deleted.

##### Parameters
| Param | Type | Description |
| --- | --- | --- |
|bag_path|`string`|A normalized, absolute path to a bag directory.

-----
<a name="validate_bag"></a>
## validate_bag
```python
validate_bag(bag_path, fast=False, config_file=bdbag.DEFAULT_CONFIG_FILE)
```
Validates a bag archive or bag directory.  If a bag archive is specified, it is first extracted to a temporary directory
before validation and then the temporary directory is deleted after validation completes.

If `fast` is `True`, then only the total count of payload files and the total byte count of all files are compared to the bag's
`Payload-Oxum` metadata field, if present.  Otherwise, checksums will be recalculated for every file present in the bag
payload directory and compared against the checksum values in the file manifest(s).

##### Parameters
| Param | Type | Description |
| --- | --- | --- |
|bag_path|`string`|A normalized, absolute path to a bag directory or bag archive file.
|fast|`boolean`|If `True` only check payload contents against `Payload-Oxum`, otherwise re-calculate checksums for all payload files.
|config_file|`string`|A normalized, absolute path to a *bdbag* configuration file. Uses the default configuration file if  not specified.

**Raises**: `BagValidationError`, `BaggingInterruptedError`, or `RuntimeError` if the bag fails to validate successfully.

-----
<a name="validate_bag_profile"></a>
## validate_bag_profile
```python
validate_bag_profile(bag_path, profile_path=None)
```
Validates a bag archive or bag directory against a bag profile. If a bag archive is specified, it is first extracted to a temporary directory
before profile validation and then the temporary directory is deleted after profile validation completes.

If a `profile_path` is specified, the bag is validated against that profile. Otherwise, this function checks the bag's `bag-info.txt` for a valid `BagIt-Profile-Identifier` metadata field and attemps to resolve that field's value as a URL link to the profile.

##### Parameters
| Param | Type | Description |
| --- | --- | --- |
|bag_path|`string`|A normalized, absolute path to a bag directory or bag archive file.
|bag_profile|`string`|A normalized, absolute path to a [BagIt-Profile](https://github.com/ruebot/bagit-profiles) file.

**Raises**: `ProfileValidationError`

**Returns**: `Profile` - The `Profile` object, if the bag passed profile validation.

-----
<a name="validate_bag_serialization"></a>
## validate_bag_serialization
```python
validate_bag_serialization(bag_path, bag_profile)
```
Validates a bag archive's serialization format against a bag profile's `Serialization` and `Accept-Serialization`
constraints, if any.

##### Parameters
| Param | Type | Description |
| --- | --- | --- |
|bag_path|`string`|A normalized, absolute path to a bag archive file.
|bag_profile|`string`|A normalized, absolute path to a [BagIt-Profile](https://github.com/ruebot/bagit-profiles) file.

**Raises**: `ProfileValidationError`

-----
<a name="validate_bag_structure"></a>
## validate_bag_structure
```python
validate_bag_structure(bag_path, check_remote=False)
```
Checks a bag's structural conformance as well as payload consistency between file manifests, the filesystem, and fetch.txt.

##### Parameters
| Param | Type | Description |
| --- | --- | --- |
|bag_path|`string`|A normalized, absolute path to a bag directory or bag archive file.
|check_remote|`boolean`|A boolean value indicating if remote files should be included in the the consistency check.

**Throws**: `BagValidationError` - If the bag structure could not be validated.

-----
<a name="bdbag_config_module"></a>
## bdbag_config.py
Utility functions for the `bdbag.json` configuration file.
To make use of these functions, after installing bdbag append the following to the top of your script.
```python
from bdbag.bdbag_config import <function name>
```

<a name="bootstrap_config"></a>
## bootstrap_config
```python
bootstrap_config(config_file=DEFAULT_CONFIG_FILE, keychain_file=DEFAULT_KEYCHAIN_FILE, base_dir=None)
```
Attempts to create the default configuration file at the location specified by `config_file` and the default keychain file at the location specified by `keychain_file`.
If the `base_dir` argument is specified, it will be checked to ensure the directory exists and the caller has read/write/execute permissions.
If explicit locations via the declared parameters are not provided, the `base_dir` will be assumed to be the system dependent expansion of `~`,
and `config_file` will be set to `~/.bdbag/bdbag.json` and `keychain_file` will be set to `~/.bdbag/keychain.json`.
##### Parameters
| Param | Type | Description |
| --- | --- | --- |
|config_file|`string`|A normalized, absolute path to a configuration file. Defaults to the expansion of `~/.bdbag/bdbag.json`.
|keychain_file|`string`|A normalized, absolute path to a configuration file. Defaults to the expansion of `~/.bdbag/keychain.json`
|base_dir|`string`|A directory path, assumed to be the base path where the files will be written. This path will be checked for access before attempting to write the files. If it is not specified, it defaults to the system-dependent expansion of `~`.

-----
<a name="read_config"></a>
## read_config
```python
read_config(config_file, create_default=True, auto_upgrade=False)
```
Reads the configuration file specified by `config_file` into a dictionary object. If the file path specified is
the default configuration file location `~/.bdbag/bdbag.json`, and that file does not already exist, it is created unless `create_default=False`.
If `auto_upgrade=True` and an existing configuration file is found and is of an unknown or lesser version number than the current configuration file format, it will be upgraded to the latest version.
Any existing settings found that are forward-compatible with the current version will be preserved during the upgrade process.
##### Parameters
| Param | Type | Description |
| --- | --- | --- |
|config_file|`string`|A normalized, absolute path to a configuration file.
|create_default|`boolean`|Automatically create the file specified by `config_file` if it does not already exist.
|auto_upgrade|`boolean`|Automatically upgrade the file specified by `config_file` if it already exists and is not the current version.

**Returns**: `dict` - The configuration data.

-----
<a name="write_config"></a>
## write_config
```python
write_config(config=DEFAULT_CONFIG, config_file=DEFAULT_CONFIG_FILE)
```
Writes the configuration specified by `config` to the location specified by `config_file`.
Without arguments, creates the default configuration file `bdbag.json` with the default configuration template, if it does not already exist.
##### Parameters
| Param | Type | Description |
| --- | --- | --- |
|config_file|`string`|A normalized, absolute path to a configuration file.

-----
<a name="upgrade_config"></a>
## upgrade_config
```python
upgrade_config(config_file)
```
Upgrade an existing configuration file to the current format. If an existing configuration file is found and is of an unknown or lesser version number than the current configuration file format, it will be upgraded to the latest version.
Any existing settings found that are forward-compatible with the current version will be preserved during the upgrade process.
##### Parameters
| Param | Type | Description |
| --- | --- | --- |
|config_file|`string`|A normalized, absolute path to a configuration file.

-----
<a name="bdbag_module"></a>
## bdbag (`__init__.py`)
Some shared utility functions exist at the `bdbag` module level in `__init__.py`.
To make use of these functions, after installing bdbag append the following to the top of your script.
```python
from bdbag import <function name>
```
<a name="inspect_path"></a>
## inspect_path
```python
inspect_path(path)
```
Attempts to determine if the string specified by `path` is a local file, local directory, or a actionable URL/URI.

**Returns**: `is_file, is_dir, is_uri` - A 3-tuple of boolean values indicating if the path is a file, directory, or URL/URI, respectively.

-----
<a name="filter_dict"></a>
## filter_dict
```python
filter_dict(expr, entry)
```
Evaluates the dictionary variable `entry` against the filter expression `expr`,
where `expr` is a string of the form: `<column><operator><value>`.
The set of operators is syntactically limited. See syntax [below](#filter_dict_syntax).

##### Parameters
| Param | Type | Description |
| --- | --- | --- |
|expr|`string`|A string of the form: `<column><operator><value>`. See syntax [below](#filter_dict_syntax).
|entry|`dict`|A dictionary containing the data to be filtered.

<a name="filter_dict_syntax"></a>
##### Filter Expression Syntax
* `column` is a name of a key in the input dictionary.
* `<operator>` is one of the following predefined tokens:

	| Operator | Description |
	| --- | --- |
	|==| equal
	|!=| not equal
	|=*| wildcard substring equal
	|!*| wildcard substring not equal
	|^*| wildcard starts with
	|$*| wildcard ends with
	|>| greater than
	|>=| greater than or equal to
	|<| less than
	|<=| less than or equal to
* `value` is a string or integer

**Returns**: `boolean` - A boolean value indicating whether the target `dict` contained a key-value pair that matched the input `expr`, or not.