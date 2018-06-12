# *bdbag*: Configuration Guide

Some components of the **bdbag** software are configured via JSON-formatted configuration files.

There are two global configuration files: [bdbag.json](#bdbag.json) and [keychain.json](#keychain.json). Skeleton versions of
these files with simple default values are automatically created in
the current user's home directory the first time a bag is created or opened.

Additionally, three JSON-formatted configuration files can be passed as arguments to *bdbag* in order to supply input
for certain bag creation and update functions.  These files are known as [metadata](#metadata), [ro metadata](#ro_metadata) and
[remote-file-manifest](#remote-file-manifest) configurations.

<a name="bdbag.json"></a>
## *bdbag.json*

The file `bdbag.json` is a global configuration file that allows the user to specify a set of parameters to be used as
defaults when performing various bag manipulation functions.

The format of *bdbag.json* is a single JSON object containing a set of JSON child objects (used as
configuration sub-sections) which control various default behaviors of the software. Currently, only the sub-section `bag_config` is supported.

##### Parameters
| Parameter | Description | Parent Object|
| --- | --- | --- |
|*bag_config*|This is the parent object for all bag-related defaults.| Object root
|*bag_algorithms*|This is an array of strings representing the default checksum algorithms to use for bag manifests, if not otherwise specified.  Valid values are "md5", "sha1", "sha256", and "sha512".| *bag_config*
|*bag_archiver*|This is a string representing the default archiving format to use if not otherwise specified.  Valid values are "zip", "tar", and "tgz".|*bag_config*
|*bag_metadata*|This is a list of simple JSON key-value pairs that will be written as-is to bag-info.txt.|*bag_config*
|*bag_processes*|This is a numeric value representing the default number of concurrent processes to use when calculating checksums.|*bag_config*
|||

Below is a sample *bdbag.json* file:
```json
{
    "bag_config": {
        "bag_algorithms": [
            "md5",
            "sha256"
        ],
        "bag_metadata": {
            "BagIt-Profile-Identifier": "https://raw.githubusercontent.com/fair-research/bdbag/master/profiles/bdbag-profile.json",
            "Contact-Name": "Mike D'Arcy"
        },
        "bag_processes": 1
    }
}
```

<a name="keychain.json"></a>
## *keychain.json*
The file `keychain.json` is used to specify the authentication mechanisms and credentials for the various URLs that might
be encountered while trying to resolve (download) the files listed in a bag's fetch.txt file.

The format of `keychain.json` is a JSON array containing a list of JSON objects, each of which specify a set of parameters used to
configure the authentication method and credentials to use for a specifed base URL.

##### Parameters
| Parameter | Description |
| --- | --- |
|*uri*|This is the base URI used to specify when authentication should be used.  When a URI reference is encountered in fetch.txt, an attempt will be made to match it against all base URIs specified in *keychain.json* and if a match is found, the request will be authenticated before file retrieval is attempted.
|*auth_uri*|This is the authentication URI used to establish an authenticated session for the specified *uri*.  This is currently assumed to be an HTTP(s) protocol URL.
|*auth_type*|This is the authentication type used by the server specified by *auth_uri*.  Currently, only the values "http-basic", "http-form" and "cookie" are supported when using the HTTP(S) protocol, and "token" when using Globus Transfer protocol.
|*auth_params*|This is a child object containing authentication-type specific parameters used in session establishment.  It will generally contain credential information such as a username and password, a cookie value, or client certificate parameters. It can also contain other parameters required for authentication with the given *auth_type* mechanism; for example the HTTP method (i.e., `GET` or `POST`) to use with HTTP Basic Auth.
|||

Below is a sample *keychain.json* file:
```json
[
    {
        "uri":"https://some.host.com/somefiles",
        "auth_uri":"https://some.host.com/authenticate",
        "auth_type": "http-form",
        "auth_params": {
            "username": "me",
            "password": "mypassword",
            "username_field": "username",
            "password_field": "password"
        }
    },
    {
        "uri":"https://another.host.com/somefiles",
        "auth_uri":"https://another.host.com/authenticate",
        "auth_type": "http-basic",
        "auth_params": {
            "auth_method":"POST",
            "username": "me",
            "password": "mypassword"
        }
    },
    {
        "uri":"https://yet-another.host.com/",
        "auth_type": "cookie",
        "auth_params": {
            "cookies": [ "a_cookie_name=zxyfw1231_secret"]
        }
    },
    {
        "uri": "ftp://ftp.ftp-host.net/",
        "auth_type": "ftp-basic",
        "auth_params": {
            "username": "anonymous",
            "password": "bdbag@users.noreply.github.com"
        }
    },       
    {
        "uri":"globus://",
        "auth_type": "token",
        "auth_params": {
            "local_endpoint": "b06c5a10-0b17-11e7-a73f-22000bf2d559",
            "transfer_token": "AQBXNMizAAAAAAADPIg9SoyPk_dm0BOFcWT7pe-52fQKv2Je6zi-hEvJ5xkfXw8rLaL9mVg8RtOY-vy4qrQd"
        }
    }
]
```

<a name="remote-file-manifest"></a>
## *remote-file-manifest*
A *remote-file-manifest* configuration file is used by `bdbag` during bag creation and update as a way
to include files in a bag that are not necesarily present on the local system, and therefore cannot be hashed.
The file is processed by `bdbag` and the data used to generate both payload manifest entries and `fetch.txt`
entries in the result bag.

The `remote-file-manifest` is structured as a JSON array containing a list of JSON objects that have the following attributes:

* `url`: The url where the file can be located or dereferenced from. This value MUST be present.
* `length`: The length of the file in bytes. This value MUST be present.
* `filename`: The filename (or path), relative to the bag 'data' directory as it will be referenced in the bag
manifest(s) and fetch.txt files. This value MUST be present.
* AT LEAST ONE or more (and ONLY ONE of each) of the following `algorithm:checksum` key-value pairs:
  * `md5`:`<md5 hex value>`
  * `sha1`:`<sha1 hex value>`
  * `sha256`:`<sha256 hex value>`
  * `sha512`:`<sha512 hex value>`
* Other legal JSON keys and values of arbitrary complexity MAY be included, as long as the basic
requirements of the structure (as described above) are fulfilled.

Below is a sample *remote-file-manifest* configuration file:
```json
[
    {
        "url":"https://raw.githubusercontent.com/fair-research/bdbag/master/profiles/bdbag-profile.json",
        "length":699,
        "filename":"bdbag-profile.json",
        "md5":"9faccdb6f9a47a10d9a00bd2b13f7ab3",
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
