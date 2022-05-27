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
import io
import os
import errno
import logging
import json
import collections
import stat
import bdbag
from bdbag import DEFAULT_CONFIG_PATH
from bdbag.bdbagit import force_unicode

logger = logging.getLogger(__name__)

DEFAULT_KEYCHAIN_FILE = os.path.join(DEFAULT_CONFIG_PATH, 'keychain.json')
DEFAULT_KEYCHAIN = []
KEYCHAIN_EXAMPLE = [
    {
        "uri": "https://<hostname>/<path>",
        "auth_uri": "",
        "auth_type": "http-form",
        "auth_params": {
            "auth_method": "post",
            "username": "",
            "password": "",
            "username_field": "username",
            "password_field": "password",
            "cookies": []
        }
    },
    {
        "uri": "ftp://<hostname>/<path>",
        "auth_type": "ftp-basic",
        "auth_params": {
            "username": "",
            "password": ""
        }
    },
    {
        "uri": "https://<hostname>/<path>",
        "auth_type": "bearer-token",
        "auth_params": {
            "token": "<token>",
            "allow_redirects_with_token": "True"
        }
    },
    {
        "uri": "s3://<bucket_name>",
        "auth_type": "aws-credentials",
        "auth_params": {
            "key": "foo",
            "secret": "bar"
        }
    },
    {
        "uri": "globus://<endpoint>/<path>",
        "auth_type": "globus_transfer",
        "auth_params": {
            "local_endpoint": "",
            "transfer_token": ""
        }
    }
]


def write_keychain(keychain=DEFAULT_KEYCHAIN, keychain_file=DEFAULT_KEYCHAIN_FILE):
    keychain_path = os.path.dirname(keychain_file)
    if not os.path.isdir(keychain_path):
        try:
            os.makedirs(keychain_path)
        except OSError as error:  # pragma: no cover
            if error.errno != errno.EEXIST:
                raise
    with io.open(keychain_file, 'w', encoding='utf-8') as kf:
        kf.write(force_unicode(json.dumps(keychain if keychain is not None else list(),
                                          ensure_ascii=False, sort_keys=True, indent=4, separators=(',', ': '))))
    os.chmod(keychain_file, stat.S_IRUSR | stat.S_IWUSR)


def read_keychain(keychain_file=DEFAULT_KEYCHAIN_FILE, create_default=True):
    keychain = json.dumps(DEFAULT_KEYCHAIN)
    if keychain_file == DEFAULT_KEYCHAIN_FILE and not os.path.isfile(keychain_file) and create_default:
        logger.debug("No keychain file specified and no default keychain file found, attempting to create one.")
        try:
            write_keychain(keychain_file=keychain_file)
        except Exception as e:  # pragma: no cover
            logger.warning(
                "Unable to create default keychain file. A keychain file is required for authentication when "
                "retrieving files from protected remote resources. Either ensure that the default keychain "
                "file %s can be created or provide a different path to a valid keychain file. Error: %s" %
                (keychain_file, bdbag.get_typed_exception(e)))
    if os.path.isfile(keychain_file):
        with io.open(keychain_file, encoding='utf-8') as kf:
            keychain = kf.read()

    return json.loads(keychain, object_hook=collections.OrderedDict)


def update_keychain(keychain_entries, keychain_file=None, delete=False):
    assert keychain_entries
    if not isinstance(keychain_entries, list):
        keychain_entries = [keychain_entries]
    keychain_file = keychain_file or DEFAULT_KEYCHAIN_FILE
    if not os.path.isfile(keychain_file):
        keychain = list()
    else:
        keychain = read_keychain(keychain_file, create_default=False)
    updated_keychain = list()

    # copy all existing entries except those we are updating
    for entry in keychain:
        skip = False
        for update_entry in keychain_entries:
            update_uri = update_entry.get("uri")
            update_auth_type = update_entry.get("auth_type")
            update_tag = update_entry.get("tag")
            if not ((update_uri and update_auth_type) or update_tag):
                logger.warning("BDBag keychain entry update requires either a pair of valid \"uri\" and \"auth_type\" "
                               "parameters or a \"tag\" parameter to match keychain entries against.")
                continue
            update_uri = update_uri.lower().strip() if update_uri else None
            uri = entry.get("uri", "").lower().strip()
            update_auth_type = update_auth_type.lower().strip() if update_auth_type else None
            auth_type = entry.get("auth_type", "").lower().strip()
            tag = entry.get("tag")
            if (uri == update_uri) and (auth_type == update_auth_type) or \
                    ((tag is not None and update_tag is not None) and tag == update_tag):
                skip = True
                continue
        if not skip:
            updated_keychain.append(entry)

    if not delete:
        updated_keychain.extend(keychain_entries)

    write_keychain(updated_keychain, keychain_file)

    return updated_keychain


def has_auth_attr(auth, attr, quiet=False):
    if auth.get(attr) is None:
        if not quiet:  # pragma: no cover
            logger.warning("Unable to locate attribute [%s] in keychain entry for uri: %s" %
                           (attr, auth.get("uri", "")))
        return False
    return True


def get_auth_entries(url, auth):
    entries = list()
    for entry in auth:
        uri = entry.get("uri", "").lower().strip()
        if uri in url.lower():
            entries.append(entry)
    return entries



