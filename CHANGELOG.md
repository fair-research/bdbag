# CHANGE LOG

## 1.7.0
* PR: [#54](https://github.com/fair-research/bdbag/pull/54): Add support for passing a local profile path for profile validation. Thanks to [Bernhard Hampel-Waffenthal](https://github.com/prettybits) for the contribution.
* [#40](https://github.com/fair-research/bdbag/issues/40): Replace deprecated use of `pkg_resources` with `importlib-metadata` and `packaging`.
* Fix issue with HTTP fetch transport where bearer-token auth gets stripped from the session on a legitimate redirect but not restored for any potential new request on that same URL-bound session.
* Unpin `tzlocal` unless Python<3.
* Support for Python 3.5 and 3.6 has been dropped. Python 3.7 compatibility is deprecated but still officially supported in this release.

## 1.6.4

### Added Google Cloud Storage fetch handler for handling `gs://` URLs in _fetch.txt_. 
Note that this is a soft dependency and you must install the [gcloud CLI](https://cloud.google.com/sdk/docs/install) on the system where you will be running 
`bdbag` in order for this handler to function.

### Enabling "requester pays":
This handler supports the _requester pays_ usage pattern by allowing the billable `project_id` to be specified in the `auth_params` object for
a corresponding `keychain.json` entry for a matching `gs://` URI pattern. 

For example, to configure (and allow) _requester pays_ for a GS bucket, you would add a `keychain.json` entry similar 
to the following:

```json
{
    "uri": "gs://gcs-bdbag-integration-testing/",
    "auth_type": "gcs-credentials",
    "auth_params": {
        "project_id": "bdbag-204999",
        "allow_requester_pays": true
    }
}
```
You can also explicitly disallow _requester pays_ at the client-side in the following ways:
* Set `allow_requester_pays` to `false`
* Omit the `allow_requester_pays` field.
* Omit the `project_id` field.
* Omit the `auth_params` object entirely.

Note that if you do any of the above, data retrieval requests to buckets which have _requester pays_ enabled will fail. 
The use case for this configuration option is to ensure that you __don't__ pay for requests when _requester pays_
is disabled on the bucket. Per the following GCS [documentation](https://cloud.google.com/storage/docs/requester-pays):

```json
Important: Buckets that have Requester Pays disabled still accept requests that include a billing project, 
and charges are applied to the billing project supplied in the request. 
Consider any billing implications prior to including a billing project in all of your requests.
```

IMPORTANT NOTE: 

At the time of this writing, when using `gcloud-CLI` from `Google Cloud SDK 416.0.0` and previous, it is
possible to still be billed for bucket usage _even if_ you've disallowed _requester pays_ for a given bucket in 
`keychain.json`. This is because the `gcloud init` process requires that you specify a default `project_id` and this 
project id is subsequently stored in the `application_default_credentials.json` file used by the GCS APIs 
(which the `bdbag` fetch handler uses) as `quota_project_id`. If this value is present it will be passed on all GCS API
calls as a fallback regardless even if explicitly not passed to the API call. 
This can be worked around by removing the `quota_project_id` from `application_default_credentials.json`.

### Using service account credentials:

It is also possible to specify a `service_account_credentials_file` which is a file path referencing a service account 
credentials JSON file provided by Google Cloud Storage. For example:
```json
{
    "uri": "gs://bdbag-dev/",
    "auth_type": "gcs-credentials",
    "auth_params": {
        "project_id": "bdbag-204400",
        "service_account_credentials_file": "/home/bdbag/bdbag-204400-41babdd46e24.json"
    }
}
```

## 1.6.3
* Fix bug in `bdbag_api.validate()` where underlying `BagError` exceptions were not being propagated correctly.
* Add an environment marker to `setup.py` for the `python-requests` dependency. This marker specifies that no greater 
than `requests-2.25.1` be used with `Python3.5` environments, due to underlying incompatibilities with `requests` dependency 
chain and `Python3.5` after `requests-2.26.0`. Reported in issue [#47](https://github.com/fair-research/bdbag/issues/47).
Note that `bdbag` support for `Python3.5` is planned to be dropped in the `1.7.0` release.

## 1.6.2
* Set "User-Agent" header for HTTP fetch handler (via `python-requests`) to `"bdbag/{version} (requests/{version})"`.
* Added `sha1` support for `bdbag_utils` function `create-rfm-from-url-list`. See PR [#46](https://github.com/fair-research/bdbag/pull/46).
* Fix issues with unicode handling in `fetch.txt`, RO `metadata.json`, `keychain.json`, and `remote-file-manifest` JSON files.
* Fix issues with over-escaping (urlencoding) of filenames and urls in `fetch.txt` and RO `metadata.json`. 
  Per the spec, *only* CR,LF, whitespace, and literal percent should be encoded.

## 1.6.1
* [#41](https://github.com/fair-research/bdbag/issues/41): Add support for regex patterns in `filter_dict`. 
  See PR [#42](https://github.com/fair-research/bdbag/pull/42).
* Add `-frozen` qualifier suffix (when applicable) to version strings returned by get_distribution.
* Pinned `setuptools_scm<6.0` due to it dropping support for Python 2.7/3.5 which we will still support for a little while longer.

## 1.6.0
* Implement [#37](https://github.com/fair-research/bdbag/issues/37): Support external fetch transports via plug-in 
  architecture.
* Added `--output-path` CLI (and corresponding API) argument for specifying output path for extracted archives.
* Added a `bypass_ssl_cert_verification` configuration option for the `https` fetch handler so that SSL certificate verification could be disabled 
  either globally (not recommended) or on a whitelisted set of URL paths used in simple substring matches against 
  a bag's `fetch.txt` URLs.
* Update the `--validate-profile` CLI argument so that it can take an optional keyword argument, `bag-only`, which 
  can be used to bypass the otherwise automatic profile serialization validation, and therefore is suitable to use 
  on extracted bag directories.
* Fixed issue with `archive_bag` API function not including empty directories when creating `zip` format archives.
* Modified `extract_bag` API function to accurately include the bag root directory path of the extracted bag 
  archive in the return value. Previously, this value could have wound up being different from the file archive base 
  name; for example if the archive file was renamed or was created in such a way that the base file name never matched 
  the archived bag directory root. 
* Refactored `bagit-profile` support. This module is no longer "vendored" internally and is now a proper external 
  dependency intended to be pulled from PyPi.  The `Profile` class is patched internally, as needed. This dependency 
  is currently pinned to `1.3.1`.
* Updated `bdbag-profile.json` and `bdbag-ro-profile.json` to leverage newer features of `bagit-profile` version 
  `1.3`. Loosened "Manifests-Required" to only require `md5` for both profiles.
* Pinned `bagit-python` dependency version to `1.8.1`.
* Added Python 3.8 and 3.9 support to `setup.py` metadata and travis builds.
* Dropped Python 3.4 support.

## 1.5.6
* Fix [#34](https://github.com/fair-research/bdbag/issues/34): New file hashes for existing manifest entries generated 
  from remote-file-manifests don't get updated in bags.
* Fix [#36](https://github.com/fair-research/bdbag/issues/36): Directory paths with a slash at the end during 
  "archive_bag" result in a malformed archive name.
* Added `update_keychain` API function in `auth/keychain.py` for add/update/delete of keychain entries.
* Added Python 3.7 support to `setup.py` metadata and travis builds.

## 1.5.5

* Ensure tag file manifest entries for additional tag files uses 
denormalized path separator (unix-style `/`) similar to payload file 
manifest entries.
* Return result bag path from the `materialize()` function.
* Don't use strict mode when guessing mime types to allow for user-extended types.
* Dropped Python 3.3 support.

## 1.5.4

* Fix #31: Missing import of `ensure_valid_output_path` in `fetch_globus.py`.
* Fix e745f98: Undefined `false` in `bdbag_ro.py` .

## 1.5.3
* Added a monkeypatch for `hashlib.algorithms_guaranteed` prior to the
import of any `bagit` code so that `bagit-1.7.0` (which assumes
`algorithms_guaranteed` is present, but in reality only _consistently_
exists on Python 2.7.9 or greater) can still be used by `bdbag` on
systems that only have Python 2.7.0 to 2.7.8 installed.
Lifted the strict pin on Python>=2.7.9. Note that this won't make
standalone `bagit` installations work on these systems, but it will
allow `bdbag` to successfully import and use `bagit` as a library.
Additional notes
[here](https://github.com/fair-research/bdbag/commit/86517b9ba89524c3e1328eea7f4537552f0af82e#commitcomment-31548879).

* Added code to properly url encode whitespace and other illegal
characters in the `filename` field of `fetch.txt`, per the `bagit` spec.
This will automatically be encoded when `bdbag` generates a bag from a
`remote-file-manifest`, and will automatically decoded when attempting
to resolve files via fetch. Added a corresponding unit test.
* Added a new CLI validate option: `--completeness`. This is in parity
with `bagit` CLI options and is useful primarily for determining which
files in `fetch.txt` have not yet been retrieved. Added a corresponding
unit test.
* Added code in the CLIs to print stack traces in when `--debug` is
specified.

## 1.5.1

* Fixed bug with `bdbagit.save()` and "strict mode" version check logic
that prohibited mixing of checksum types for payload files when the
`bagit` specification version of the bag being updated was < `1.0`.
Added a unit test that would have caught it.

## 1.5.0

__Milestone feature release__

* Added `materialize` CLI and API function. The materialize function is
basically a bag bootstrapper. When invoked, it will attempt to fully
_reconstitute_ a bag by performing multiple actions depending on the
context of the input `path` parameter. If `path` is a URL or a URI of a
resolvable identifier scheme, the file referenced by this value will
first be downloaded to the current directory. Next, if the `path` value
(or previously downloaded file) is a local path to a supported archive
format, the archive will be extracted to the current directory. Then,
if the `path` value (or previously extracted file) is a valid bag
directory, any remote file references contained within the bag's
`fetch.txt` file will attempt to be resolved. Finally, full validation
will be run on the materialized bag. If any one of these steps fail,
an error is raised.

* Refactored identifier resolution into a modular plug-in system. Added
support for DOI and DataGUID identifier schemes in addition to existing
ARK/Minid schemes. Additional schemes can be supported by creating a
compliant "plug-in" resolver class and configuring it via the
`bdbag.json` configuration file.

* Bagit specification version compliance is now configurable. The
default specification version used is `0.97` which permits heterogeneous
mixing of checksums in bag payload manifests. Addresses
[#27](https://github.com/fair-research/bdbag/issues/27) and reverts the
restriction introduced in release `1.3.0`.

* Implement cloud storage fetch transports for access to secured Amazon
S3 and Google Cloud Store via `boto3` library. GCS bucket and object
access via `boto3` is only supported when the target GCS bucket is set
to "interoperability mode". The `boto3` library is an optional runtime
dependency and need only be installed if support for automatic download
of `S3` or `GS` URLs from `fetch.txt` entries is desired. Various
parameters relating to the operation of this fetch handler are exposed
via the `bdbag.json` configuration file and can be tuned accordingly.
Addresses [#25](https://github.com/fair-research/bdbag/issues/25).

* Numerous improvements to HTTP fetch handler:

    * Support for "Authorization" header based authentication via
    the `keychain.json` configuration file. This authentication mode
    allows for Bearer Token authentication scenarios such as those
    used in OAuth 2.0 authorization flows.
    * Improved handling for cookie-based authentication. Added a
    configurable mechanism that scans for multiple
    Mozilla/Netscape/CURL/WGET compatible cookie files, merges them, and
    automatically uses them in outbound HTTP fetch requests.
    * Exposed some of the `requests` module's session parameters in the
    `bdbag.json` configuration file. This allows for tuning such values
    as connect/read retry count, backoff factor, and the status code
    retry forcelist, along with the option of disabling automatic
    redirect following.

* Refactored `bdbag.json` configuration file processing into a separate
module and significantly increased the scope of the configuration file.
Added a basic mechanism for versioning the configuration file and
upgrading existing config files to newer versions while preserving
backward-compatible configuration settings, when possible.

* Improved unit test coverage.

* Updated documentation.

## 1.4.1

* Fix bug when no expr passed to filter_dict(), missed from code refactor.

## 1.4.0

* Add partial (selective) fetch functionality to API and CLI per
[#20](https://github.com/fair-research/bdbag/issues/20).
* Add an API and CLI function to automatically generate a basic RO
manifest via bag introspection.
* Add 'Bagging-Time' as a default bag-info metadata element.
* Allow 'url' field in remote file manifest to be an array as well as a
string, but only read array[0] when generating fetch.txt.
* Add logic to allow an RO manifest object to be "updated" without
generating new unique URNs for existing nodes.
* Fixed some issues with keychain handling and HTTP fetch handler.
* Changed `globus-sdk` to a run-time dependency.
* Numerous functional changes to bdbag-utils. New create-rfm-from-file
function that can create an RFM by parsing a CSV file.
Added documentation [here](https://github.com/fair-research/bdbag/blob/master/doc/utils.md).
* Added additional unit tests
(copied over from https://github.com/LibraryOfCongress/bagit-python/blob/master/test.py,
with modifications) for additional coverage of bdbagit.py.
* Improved unit test coverage.
* Update docs.

## 1.3.0

* Enhanced RO/JSON-LD tagfile metadata support. Additions to the CLI and
API now support the creation of the RO tagfile metadata directory and
any associated JSON-LD files from a single JSON "meta-manifest".
Coupling this with `remote-file-manifest`-based bag creation allows for
entirely remote payloads but with local RO/JSON-LD metadata using only
two metadata input files.
* Refactored the overridden manifest saving functions in `bdbagit.py` to
be more inline with the current `bagit` approach and upcoming `bagit`
1.0 spec changes.

    IMPORTANT NOTES:
    * Due to this change, it will no longer be possible to create/update
     bags using multiple checksum manifests unless _every_ file in the
     payload is listed in _every_ payload manifest.  In other words, it
     now is an error condition to specify more than one checksum
     algorithm (e.g., both `md5` and `sha256`) and not be able to
     calculate or provide all specified checksum types for each payload
     file, including those listed in `fetch.txt`.
    * The primary impact of this change is the creation of bags via
    `remote-file-manifest`, since the checksums for these files must be
    known _a priori_ and therefore _all_ remote file references must
    provide the same checksum algorithm type(s) uniformly across the
    entire set of payload files.

* Allow the `bag-info.txt` metadata value `Contact-Orcid` to be
specified when using the CLI via the argument `--contact-orcid`.
* Fixed an issue with the handling of the `metadata` and `metadata_file`
arguments of `make_bag` that allowed for arbitrarily complex JSON
content as `bag-info.txt` lines. Per the `bagit` spec, only string
values are supported.
* Ensure URL escaping (of whitespace only) in generated `fetch.txt`
URLs, per `bagit` spec.
* Build universal (Python 2 and 3 compat.) wheels by default.
Fixes [#19](https://github.com/fair-research/bdbag/issues/19)

## 1.2.4

* Handle "-" when found as length field in fetch.txt, per bagit spec.
BDBag can read and resolve files in bags which have unspecified content
lengths, but will not allow them to be created via remote-file-manifests
(because Payload-0xum cannot be reliably determined without byte counts
for all referenced files), and will throw an exception during the
creating/updating of a bag where an unspecified length is encountered.
* Fix duplicate manifest entry issue when creating/updating bags that
have remote file references for payload files that are already present
in the bag. It is now a conflict for a bag to have both a file in the
local payload and in fetch.txt during create/update, and an exception
will be thrown when this condition is detected.
* Ensure URL escaping in fetch.txt, per bagit spec.
* Don't emit blank lines when CLI is in quiet mode.

## 1.2.3

* Fix issue with bag extraction and directory nesting.

## 1.2.1

* Improvements to identifier handling in fetch.txt. Minid CURIs of the
form minid:xxyyzz are now supported as fetch URLs.
Multiple identifier resolver service URLs are now supported, and the
defaults can be overridden in the bdbag.json config file.
* Improvements to RO helper API.
* Improvements to utility module: added a utility routine for generating
a remote-file-manifest by executing HEAD requests against a list of URLs.
* Added bagofbags example contribution from @ianfoster.
* Updated to use upstream bagit-1.6.4.

## 1.1.4

* Fix issue with incorrect Payload-0xum being generated by the
bdbagit.update_manifests_from_remote() function.

## 1.1.3

* Fix minor issue with default keychain file entry examples.

## 1.1.2

* Fix issue with creating a bag directly from a remote file manifest.
Fixes [#15](https://github.com/fair-research/bdbag/issues/15)
* Sync with bagit-1.6.3 release. Also fixes [#15](https://github.com/fair-research/bdbag/issues/15).
* Upstream version is currently pegged at bagit-1.6.3 for bdbag-1.1.2.

## 1.1.1

__Initial public release__

* Uploaded to PyPi.  Fixes [#8](https://github.com/fair-research/bdbag/issues/8)
* Refactored _bagit_ dependency to directly use upstream from
https://github.com/LibraryOfCongress/bagit-python rather than a forked copy.
Upstream version is currently pegged at `bagit-1.6.2` for `bdbag-1.1.1`.
Fixes [#10](https://github.com/fair-research/bdbag/issues/10),
[#8](https://github.com/fair-research/bdbag/issues/8)
* Added FTP fetch handler. Fixes [#3](https://github.com/fair-research/bdbag/issues/3)
* Fixed issue with Globus fetch handler with current version of Globus SDK.
Updated dependency and pegged `globus-sdk==1.3.0` for `bdbag-1.1.1`.
Fixes [#14](https://github.com/fair-research/bdbag/issues/14)
* Added `revert_bag` function to API and CLI to revert a bag directory
back to a normal directory.
Fixes [#9](https://github.com/fair-research/bdbag/issues/9).
* Removed  `--bag-path` as a required flag argument in the CLI in favor
of the bag path being the only required positional argument.
