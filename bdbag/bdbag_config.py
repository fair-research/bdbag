#
# Copyright 2016 University of Southern California
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
import os
import errno
import logging
import json
from collections import OrderedDict
from packaging.version import parse as parse_version
from importlib_metadata import distribution, PackageNotFoundError
from bdbag import get_typed_exception, safe_move, \
    DEFAULT_CONFIG_PATH, BAG_PROFILE_TAG, BDBAG_PROFILE_ID, VERSION, __version__
from bdbag.fetch import Megabyte
from bdbag.fetch.auth.keychain import DEFAULT_KEYCHAIN_FILE, write_keychain

logger = logging.getLogger(__name__)

BAG_CONFIG_TAG = "bag_config"
BAG_SPEC_VERSION_TAG = "bagit_spec_version"
BAG_ALGORITHMS_TAG = "bag_algorithms"
BAG_PROCESSES_TAG = "bag_processes"
BAG_METADATA_TAG = "bag_metadata"
CONFIG_VERSION_TAG = "bdbag_config_version"
DEFAULT_BAG_SPEC_VERSION = "0.97"
DEFAULT_CONFIG_FILE_ENVAR = "BDBAG_CONFIG_FILE"
DEFAULT_CONFIG_FILE = os.path.join(DEFAULT_CONFIG_PATH, 'bdbag.json')
DEFAULT_BAG_ALGORITHMS = ['md5', 'sha256']

COOKIE_JAR_TAG = "http_cookies"
COOKIE_JAR_SEARCH_TAG = "scan_for_cookie_files"
COOKIE_JAR_FILE_TAG = "file_names"
COOKIE_JAR_PATHS_TAG = "search_paths"
COOKIE_JAR_PATH_FILTER_TAG = "search_paths_filter"
DEFAULT_COOKIE_JAR_FILE_NAMES = ["*cookies.txt"]
DEFAULT_COOKIE_JAR_SEARCH_PATHS = [os.path.normpath(os.path.join(os.path.expanduser('~')))]
DEFAULT_COOKIE_JAR_SEARCH_PATH_FILTER = ".bdbag"
DEFAULT_COOKIE_JAR_SEARCH_CONFIG = {
    COOKIE_JAR_SEARCH_TAG: True,
    COOKIE_JAR_FILE_TAG: DEFAULT_COOKIE_JAR_FILE_NAMES,
    COOKIE_JAR_PATHS_TAG: DEFAULT_COOKIE_JAR_SEARCH_PATHS,
    COOKIE_JAR_PATH_FILTER_TAG: DEFAULT_COOKIE_JAR_SEARCH_PATH_FILTER
}

FETCH_CONFIG_TAG = "fetch_config"
FETCH_HTTP_REDIRECT_STATUS_CODES_TAG = "redirect_status_codes"
DEFAULT_FETCH_HTTP_REDIRECT_STATUS_CODES = [301, 302, 303, 307, 308]
DEFAULT_FETCH_HTTP_SESSION_CONFIG = {
    "retry_connect": 2,
    "retry_read": 4,
    "retry_backoff_factor": 1.0,
    "retry_status_forcelist": [500, 502, 503, 504]
}
DEFAULT_FETCH_CONFIG = {
    "http": {
        "session_config": DEFAULT_FETCH_HTTP_SESSION_CONFIG,
        "allow_redirects": True,
        "redirect_status_codes": DEFAULT_FETCH_HTTP_REDIRECT_STATUS_CODES,
        COOKIE_JAR_TAG: DEFAULT_COOKIE_JAR_SEARCH_CONFIG

    },
    "https": {
        "session_config": DEFAULT_FETCH_HTTP_SESSION_CONFIG,
        "allow_redirects": True,
        "bypass_ssl_cert_verification": False,
        "redirect_status_codes": DEFAULT_FETCH_HTTP_REDIRECT_STATUS_CODES,
        COOKIE_JAR_TAG: DEFAULT_COOKIE_JAR_SEARCH_CONFIG

    },
    "s3": {
        "read_chunk_size": 10 * Megabyte,
        "read_timeout_seconds": 60,
        "max_read_retries": 3
    },
    "gs": {
        "default_project_id": None
    }
}

ID_RESOLVER_TAG = "identifier_resolvers"
DEFAULT_ID_RESOLVERS = ['identifiers.org', 'n2t.net']
RESOLVER_CONFIG_TAG = "resolver_config"
DEFAULT_RESOLVER_CONFIG = {
    "ark": [
        {
            ID_RESOLVER_TAG: DEFAULT_ID_RESOLVERS
        },
        {
            "prefix": "57799",
            "handler": "bdbag.fetch.resolvers.ark_resolver.MinidResolverHandler",
            "args": {"allow_automatic_redirects": False},
            ID_RESOLVER_TAG: DEFAULT_ID_RESOLVERS
        },
        {
            "prefix": "99999/fk4",  # we cannot assume every identifier in this test ARK shoulder references a MINID
            "handler": "bdbag.fetch.resolvers.ark_resolver.MinidResolverHandler",
            "args": {"allow_automatic_redirects": False},
            ID_RESOLVER_TAG: DEFAULT_ID_RESOLVERS
        }
    ],
    "minid": [
        {
            "handler": "bdbag.fetch.resolvers.ark_resolver.MinidResolverHandler",
            "args": {"allow_automatic_redirects": False},
            ID_RESOLVER_TAG: DEFAULT_ID_RESOLVERS
        }
    ],
    "doi": [
        {
            "prefix": "10.23725/",
            "handler": "bdbag.fetch.resolvers.doi_resolver.DOIResolverHandler",
            ID_RESOLVER_TAG: DEFAULT_ID_RESOLVERS
        }
    ],
    "ga4ghdos": [
        {
            "prefix": "dg.4503/",
            "handler": "bdbag.fetch.resolvers.dataguid_resolver.DataGUIDResolverHandler",
            ID_RESOLVER_TAG: ["n2t.net"]
        }
    ]
}

DEFAULT_CONFIG = {
    CONFIG_VERSION_TAG: __version__,
    BAG_CONFIG_TAG:
        {
            BAG_SPEC_VERSION_TAG: DEFAULT_BAG_SPEC_VERSION,
            BAG_ALGORITHMS_TAG: DEFAULT_BAG_ALGORITHMS,
            BAG_PROCESSES_TAG: 1,
            BAG_METADATA_TAG:
                {
                    BAG_PROFILE_TAG: BDBAG_PROFILE_ID
                }
        },
    FETCH_CONFIG_TAG: DEFAULT_FETCH_CONFIG,
    ID_RESOLVER_TAG: DEFAULT_ID_RESOLVERS,
    RESOLVER_CONFIG_TAG: DEFAULT_RESOLVER_CONFIG
}


def get_updated_config_keys(config):
    updated_config_keys = list()
    if parse_version(config.get(CONFIG_VERSION_TAG, "0")) < parse_version("1.6.0"):
        updated_config_keys.append([FETCH_CONFIG_TAG, ID_RESOLVER_TAG, RESOLVER_CONFIG_TAG])

    return updated_config_keys


def get_deprecated_config_keys(config):
    deprecated_config_keys = list()

    return deprecated_config_keys


def write_config(config=DEFAULT_CONFIG, config_file=DEFAULT_CONFIG_FILE):
    try:
        config_path = os.path.dirname(config_file)
        if not os.path.isdir(config_path):
            try:
                os.makedirs(config_path, mode=0o750)
            except OSError as error:  # pragma: no cover
                if error.errno != errno.EEXIST:
                    raise
        with open(config_file, 'w') as cf:
            cf.write(json.dumps(config if config is not None else DEFAULT_CONFIG, indent=4, sort_keys=True))
            cf.close()
            logger.info("Wrote configuration file: %s" % config_file)
    except Exception as e:
        logger.warning("Unable to create configuration file %s. %s" % (config_file, get_typed_exception(e)))


def read_config(config_file=None, create_default=True, auto_upgrade=False):
    if not config_file:
        config_file = os.getenv(DEFAULT_CONFIG_FILE_ENVAR, DEFAULT_CONFIG_FILE)
        if not os.path.isfile(config_file) and (config_file != DEFAULT_CONFIG_FILE) and not create_default:
            logger.warning("Invalid configuration file path specified using environment variable %s: [%s]. "
                           "Falling back to default configuration file path: [%s]" %
                           (DEFAULT_CONFIG_FILE_ENVAR, config_file, DEFAULT_CONFIG_FILE))
            config_file = DEFAULT_CONFIG_FILE

    if not os.path.isfile(config_file) and create_default:
        write_config(config_file=config_file)

    if os.path.isfile(config_file) and auto_upgrade:
        upgrade_config(config_file)

    if os.path.isfile(config_file):
        logger.debug("Loading configuration file from: %s" % config_file)
        with open(config_file) as cf:
            config = cf.read()
    else:
        config = json.dumps(DEFAULT_CONFIG)
        logger.warning("Unable to read configuration file: [%s]. Using internal defaults." % config_file)

    return json.loads(config, object_pairs_hook=OrderedDict)


def upgrade_config(config_file):
    if config_file and not os.path.isfile(config_file):
        return

    updated = False
    with open(config_file) as cf:
        config = json.loads(cf.read(), object_pairs_hook=OrderedDict)

    new_config = None
    try:
        version = distribution("bdbag").version
    except PackageNotFoundError:  # pragma: no cover
        version = __version__
    if parse_version(version) > parse_version(config.get(CONFIG_VERSION_TAG, "0")):
        new_config = DEFAULT_CONFIG.copy()
        config_items = [BAG_CONFIG_TAG, FETCH_CONFIG_TAG, RESOLVER_CONFIG_TAG, ID_RESOLVER_TAG]
        copy_config_items(config, new_config, config_items)
        updated = True

    if updated and new_config:
        safe_move(config_file)
        write_config(new_config, config_file)
        print("Updated configuration file [%s] to current version format: %s" % (config_file, str(version)))


def copy_config_items(old_config, new_config, key_names):
    for key_name in key_names:
        if key_name in get_deprecated_config_keys(old_config):
            continue
        item = old_config.get(key_name)
        if (item is None) or (key_name in get_updated_config_keys(old_config)):
            new_config[key_name] = DEFAULT_CONFIG[key_name]
        elif isinstance(item, dict):
            for k, v in item.items():
                if k not in get_deprecated_config_keys(old_config):
                    new_config[key_name][k] = v
        else:
            new_config[key_name] = item

    return new_config


def bootstrap_config(config_file=DEFAULT_CONFIG_FILE, keychain_file=DEFAULT_KEYCHAIN_FILE, base_dir=None):
    if not base_dir:
        base_dir = os.path.expanduser('~')
    if os.path.isdir(base_dir) and os.access(base_dir, os.F_OK | os.R_OK | os.W_OK | os.X_OK):
        if not os.path.isfile(config_file):
            write_config(config_file=config_file)
            print("Created default configuration file: %s" % config_file)
        else:
            upgrade_config(config_file)
        if not os.path.isfile(keychain_file):
            write_keychain(keychain_file=keychain_file)
            print("Created default keychain file: %s" % keychain_file)
