# *bdbag*: Configuration Guide

Some components of the `bdbag` software are configured via JSON-formatted configuration files.

There are two global configuration files: [bdbag.json](#bdbag.json) and [keychain.json](#keychain.json). Skeleton versions of
these files with simple default values are automatically created in the current user's home directory the first time a bag is created or opened.

Additionally, three JSON-formatted configuration files can be passed as arguments to *bdbag* in order to supply input
for certain bag creation and update functions.  These files are known as [metadata](#metadata), [ro metadata](#ro_metadata) and
[remote-file-manifest](#remote-file-manifest) configurations.

<a name="bdbag.json"></a>
## `bdbag.json`

The file `bdbag.json` is a global configuration file that allows the user to specify a set of parameters to be used as
defaults when performing various bag manipulation functions.

The format of `bdbag.json` is a single JSON object containing a set of JSON child objects (used as
configuration sub-sections) which control various default behaviors of the software.

##### Object: `root`
This is the parent object for the entire configuration.

| Parameter | Description
| --- | --- |
|`bdbag_config_version`|The version number of the configuration file. In general, it matches the release version number of `bdbag`
|`bag_config`|This object contains all bag-related configuration parameters.
|`fetch_config`|This object contains all fetch-related configuration parameters.
|`resolver_config`|This object contains all implementation-specific resolver configuration parameters.
|`identifier_resolvers`|This is a global list of identifier "meta" resolvers. It can be overridden on a per-resolver basis via the individual configuration blocks for each resolver in `resolver_config`.

##### Object: `bag_config`
This object contains all bag-related configuration parameters.

| Parameter | Description
| --- | --- |
|`bag_algorithms`|This is an array of strings representing the default checksum algorithms to use for bag manifests, if not otherwise specified.  Valid values are "md5", "sha1", "sha256", and "sha512".
|`bag_archiver`|This is a string representing the default archiving format to use if not otherwise specified.  Valid values are "zip", "tar", and "tgz".
|`bag_metadata`|This is a list of simple JSON key-value pairs that will be written as-is to bag-info.txt.
|`bag_processes`|This is a numeric value representing the default number of concurrent processes to use when calculating checksums.
|`bagit_spec_version`|The version of the `bagit` specification that created bags will conform to. Valid values are "0.97" or "1.0".

##### Object: `fetch_config`
The `fetch_config` object contains a set of child objects each keyed by the scheme of the transport protocol that the object contains configuration parameters for.
Currently, only the `http` and `s3` transports have configuration objects that control their behavior.

| Parameter | Description
| --- | --- |
|`http`|Configuration for the `http` fetch handler.
|`s3`|Configuration for the `s3` fetch handler.

##### Object: `fetch_config:http`
This object contains configuration parameters for the `http` fetch handler.

| Parameter | Description
| --- | --- |
|`session_config`|Session configuration parameters for the `requests` HTTP client library. The parameters mainly control retry logic.
|`http_cookies`|Configuration parameters for automatic loading and merging of HTTP cookie files.
|`allow_redirects`|A boolean indicating that redirects should automatically be followed, or not.
|`redirect_status_codes`|An array of integers representing the HTTP status codes used for determining redirection. Defaults to `[301, 302, 303, 307, 308]`.

##### Object: `fetch_config:http:session_config`
Session configuration parameters for the `requests` HTTP client library. The parameters mainly control retry logic. The retry logic is provided via the `urllib3` library, wrapped by `requests`.
For more infomation, see this external [documentation](https://urllib3.readthedocs.io/en/latest/reference/urllib3.util.html#module-urllib3.util.retry).

| Parameter | Description
| --- | --- |
|`retry_backoff_factor`|The exponential backoff factor for all retry attempts. Defaults to `1.0`.
|`retry_connect`|The number of connect attempts to retry. Defaults to `5`.
|`retry_read`| The number of read attempts to retry. Defaults to `5`.
|`retry_status_forcelist`|A list of HTTP response codes that will force and automatic retry. Defaults to: `[500,502,503,504]`.

##### Object: `fetch_config:http:http_cookies`
Configuration parameters for automatic loading and merging of HTTP cookie files.
These cookie files must follow the Mozilla/Netscape/CURL/WGET format as described [here](https://unix.stackexchange.com/questions/36531/format-of-cookies-when-using-wget).

| Parameter | Description
| --- | --- |
|`scan_for_cookie_files`|A boolean value that enables/disables the cookie scan feature globally. Defaults to `True` (enabled).
|`search_paths`|An array of base directory paths from which to recursively search with `search_paths_filter` for `file_names` to use as input. Defaults to the system-dependent expansion of `~`.
|`search_paths_filter`|An [`fnmatch.filter`](https://docs.python.org/3.5/library/fnmatch.html) pattern that can be used to filter specific subdirectories of each path specified in `search_paths`. Defaults to `.bdbag`.
|`file_names`|An array of input cookie filenames or [`fnmatch.filter`](https://docs.python.org/3.5/library/fnmatch.html) patterns to match cookie filenames against. Defaults to `[*cookies.txt]`.

##### Object: `fetch_config:s3`
This object contains configuration parameters for the `s3` fetch handler.

| Parameter | Description
| --- | --- |
|`max_read_retries`| Maximum number of socket read retries. Defaults to `5`.
|`read_chunk_size`| Number of bytes to consume per read attempt. Defaults to `10485760` bytes (10MB).
|`read_timeout_seconds`|Timeout in seconds per read attempt. Defaults to `120`.

##### Object: `resolver_config`
This object contains all implementation-specific resolver configuration parameters, keyed by resolver scheme. The current default handlers schemes are: `[ark, minid, doi, and ga4ghdos`].
Each scheme can have multiple resolver configuration blocks in an array, where each block can be mapped to a different resolver namespace prefix.

| Parameter | Description
| --- | --- |
|`handler`|This is the fully-qualified Python class name of a class derived from `bdbag.fetch.resolvers.base_resolver.BaseResolverHandler` and implementing the required functions. The `bdbag` resolver code will attempt to locate and instantiate this class at runtime.
|`prefix`|This is an optional parameter that maps the handler resolution to only instances that contain the specific `prefix` found in the identifier.
|`identifier_resolvers`|This is the same parameter as the global `identifier_resolvers` array. If found at this level, it will override the global setting for this scheme/prefix combination.


Below is a sample `bdbag.json` file:
```json
{
  "bag_config": {
    "bag_algorithms": [
      "md5",
      "sha256"
    ],
    "bag_metadata": {
      "BagIt-Profile-Identifier": "https://raw.githubusercontent.com/fair-research/bdbag/master/profiles/bdbag-profile.json",
      "Contact-Name": "mdarcy",
      "Contact-Orcid": "0000-0003-2280-917X"
    },
    "bag_processes": 1,
    "bagit_spec_version": "0.97"
  },
  "bdbag_config_version": "1.5.0",
  "fetch_config": {
    "http": {
      "session_config": {
        "retry_backoff_factor": 1.0,
        "retry_connect": 5,
        "retry_read": 5,
        "retry_status_forcelist": [
          500,
          502,
          503,
          504
        ]
      },
      "http_cookies": {
        "file_names": [
            "*cookies.txt"
        ],
        "scan_for_cookie_files": true,
        "search_paths": [
            "/home/mdarcy"
        ],
        "search_paths_filter": ".bdbag"
      },
    },
    "s3": {
      "max_read_retries": 5,
      "read_chunk_size": 10485760,
      "read_timeout_seconds": 120
    }
  },
  "identifier_resolvers": [
    "n2t.net",
    "identifiers.org"
  ],
  "resolver_config": {
    "ark": [
      {
        "identifier_resolvers": [
          "n2t.net",
          "identifiers.org"
        ],
        "prefix": null
      },
      {
        "handler": "bdbag.fetch.resolvers.ark_resolver.MinidResolverHandler",
        "identifier_resolvers": [
          "n2t.net",
          "identifiers.org"
        ],
        "prefix": "57799"
      },
      {
        "handler": "bdbag.fetch.resolvers.ark_resolver.MinidResolverHandler",
        "identifier_resolvers": [
          "n2t.net",
          "identifiers.org"
        ],
        "prefix": "99999/fk4"
      }
    ],
    "doi": [
      {
        "handler": "bdbag.fetch.resolvers.doi_resolver.DOIResolverHandler",
        "identifier_resolvers": [
          "n2t.net",
          "identifiers.org"
        ],
        "prefix": "10.23725/"
      }
    ],
    "ga4ghdos": [
      {
        "handler": "bdbag.fetch.resolvers.dataguid_resolver.DataGUIDResolverHandler",
        "identifier_resolvers": [
          "n2t.net"
        ],
        "prefix": "dg.4503/"
      }
    ],
    "minid": [
      {
        "handler": "bdbag.fetch.resolvers.ark_resolver.MinidResolverHandler",
        "identifier_resolvers": [
          "n2t.net",
          "identifiers.org"
        ]
      }
    ]
  }
}
```

<a name="keychain.json"></a>
## `keychain.json`
The file `keychain.json` is used to specify the authentication mechanisms and credentials for the various URLs that might
be encountered while trying to resolve (download) the files listed in a bag's fetch.txt file.

The format of `keychain.json` is a JSON array containing a list of JSON objects, each of which specify a set of parameters used to
configure the authentication method and credentials to use for a specifed base URL.

##### Parameters
| Parameter | Description |
| --- | --- |
|`uri`|This is the base URI used to specify when authentication should be used.  When a URI reference is encountered in fetch.txt, an attempt will be made to match it against all base URIs specified in `keychain.json` and if a match is found, the request will be authenticated before file retrieval is attempted.
|`auth_uri`|This is the authentication URI used to establish an authenticated session for the specified `uri`.  This is currently assumed to be an HTTP(s) protocol URL.
|`auth_type`|This is the authentication type used by the server specified by `uri` or `auth_uri` (if present).
|`auth_params`|This is a child object containing authentication-type specific parameters used in session establishment.  It will generally contain credential information such as a username and password, a cookie value, or client certificate parameters. It can also contain other parameters required for authentication with the given `auth_type` mechanism; for example the HTTP method (i.e., `GET` or `POST`) to use with HTTP Basic Auth.

Below is a sample `keychain.json` file:
```json
[
    {
        "uri": "https://some.host.com/somefiles/",
        "auth_uri": "https://some.host.com/authenticate",
        "auth_type": "http-form",
        "auth_params": {
            "username": "me",
            "password": "mypassword",
            "username_field": "username",
            "password_field": "password"
        }
    },
    {
        "uri": "https://some.host.com/somefiles/",
        "auth_uri": "https://some.host.com/authenticate",
        "auth_type": "http-basic",
        "auth_params": {
            "auth_method":"POST",
            "username": "me",
            "password": "mypassword"
        }
    },
    {
        "uri": "https://some.host.com/somefiles/",
        "auth_type": "cookie",
        "auth_params": {
            "cookies": [ "a_cookie_name=zxyfw1231_secret"]
        }
    },
    {
        "uri": "https://some.host.com/somefiles/",
        "auth_type": "bearer-token",
        "auth_params": {
            "token": "<token>",
            "allow_redirects_with_token": "True"
        }
    },
    {
        "uri": "ftp://some.host.com/somefiles/",
        "auth_type": "ftp-basic",
        "auth_params": {
            "username": "anonymous",
            "password": "bdbag@users.noreply.github.com"
        }
    },
    {
        "uri": "s3://mybucket",
        "auth_type": "aws-credentials",
        "auth_params": {
            "key": "foo",
            "secret": "bar"
        }
    },
    {
        "uri": "globus://my_endpoint/my_files/",
        "auth_type": "globus_transfer",
        "auth_params": {
            "local_endpoint": "b06c5a10-0b17-11e7-a73f-22000bf2d559",
            "transfer_token": "AQBXNMizAAAAAAADPIg9SoyPk_dm0BOFcWT7pe-52fQKv2Je6zi-hEvJ5xkfXw8rLaL9mVg8RtOY-vy4qrQd"
        }
    }
]
```

<a name="remote-file-manifest"></a>
## `remote-file-manifest`
A `remote-file-manifest` configuration file is used by `bdbag` during bag creation and update as a way
to include files in a bag that are not necesarily present on the local system, and therefore cannot be hashed.
The file is processed by `bdbag` and the data used to generate both payload manifest entries and `fetch.txt`
entries in the result bag.

The `remote-file-manifest` is structured as a JSON array containing a list of JSON objects that have the following attributes:

* `url`: The url where the file can be located or dereferenced from. This value MUST be present.
* `length`: The length of the file in bytes. This value MUST be present.
* `filename`: The filename (or path), relative to the bag 'data' directory as it will be referenced in the bag
manifest(s) and fetch.txt files. This value MUST be present.
* AT LEAST one (and ONLY one of each) of the following `algorithm:checksum` key-value pairs:
  * `md5`:`<md5 hex value>`
  * `sha1`:`<sha1 hex value>`
  * `sha256`:`<sha256 hex value>`
  * `sha512`:`<sha512 hex value>`
* Other legal JSON keys and values of arbitrary complexity MAY be included, as long as the basic
requirements of the structure (as described above) are fulfilled.

Below is a sample `remote-file-manifest` configuration file:
```json
[
    {
        "url":"https://raw.githubusercontent.com/fair-research/bdbag/master/profiles/bdbag-profile.json",
        "length":699,
        "filename":"bdbag-profile.json",
        "sha256":"eb42cbc9682e953a03fe83c5297093d95eec045e814517a4e891437b9b993139"
    },
    {
        "url":"ark:/88120/r8059v",
        "length": 632860,
        "filename": "minid_v0.1_Nov_2015.pdf",
        "sha256": "cacc1abf711425d3c554277a5989df269cefaa906d27f1aaa72205d30224ed5f"
    }
]
```

<a name="metadata"></a>
## *`bag-info` metadata*
A `bag-info` metadata configuration file consists of a single JSON object containing a set of JSON key-value pairs that will be
written as-is to the bag's `bag-info.txt` file.  NOTE: per the `bagit` specification, strings are the only supported value type in `bag-info.txt`.

Below is a sample `bag-info` *metadata* configuration file:
```json
{
    "BagIt-Profile-Identifier": "https://raw.githubusercontent.com/fair-research/bdbag/master/profiles/bdbag-profile.json",
    "External-Description": "Simple bdbag test",
    "Arbitrary-Metadata-Field": "This is completely arbitrary"
}
```

<a name="ro_metadata"></a>
## *`ro` metadata*
A Research Object metadata configuration file consists of a single JSON object containing a set of JSON key-object pairs where
the `key` is a `/` delimited relative file path and the `object` is any aribitratily complex JSON content. This format allows
`bdbag` to process all RO metadata as an aggregation which can then be serialized into individual JSON file components relative
to the bag's `metadata` directory.

NOTE: while this documentation refers to this configuration file as a `ro` metadata file,
the contents of this configuration file only have to conform to the [`bagit-ro`](https://github.com/ResearchObject/bagit-ro)
conventions if `bagit-ro` compatibility is the goal. Otherwise, this mechanism can be used as a generic way to create any number of
arbitrary JSON (or JSON-LD) metadata files as `bagit` tagfiles.

Below is a sample *ro metadata* configuration file:
```json
{
  "manifest.json": {
    "@context": [ "https://w3id.org/bundle/context" ],
    "@id": "../",
    "createdOn": "2018-02-08T12:23:00Z",
    "aggregates": [
      { "uri": "../data/CTD_chem_gene_ixn_types.csv",
        "mediatype": "text/csv"
      },
      { "uri": "../data/CTD_chemicals.csv",
        "mediatype": "text/csv"
      },
      { "uri": "../data/CTD_pathways.csv",
        "mediatype": "text/csv"
      }
    ],
    "annotations": [
      { "about": "../data/CTD_chem_gene_ixn_types.csv",
        "content": "annotations/CTD_chem_gene_ixn_types.csv.jsonld"
      }
    ]
  },
  "annotations/CTD_chem_gene_ixn_types.csv.jsonld": {
    "@context": {
      "schema": "http://schema.org/",
      "object": "schema:object",
      "TypeName": {
        "@type": "schema:name",
        "@id": "schema:name"
      },
      "Code": {
        "@type": "schema:code",
        "@id": "schema:code"
      },
      "Description": {
        "@type": "schema:description",
        "@id": "schema:description"
      },
      "ParentCode": {
        "@type": "schema:code",
        "@id": "schema:parentItem"
      },
      "results": {
        "@id": "schema:object",
        "@type": "schema:object",
        "@container": "@set"
      }
    }
  }
}
```
