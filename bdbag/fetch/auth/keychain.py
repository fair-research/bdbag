import os
import errno
import logging
import json
import collections
import stat
import bdbag
from bdbag import DEFAULT_CONFIG_PATH as DEFAULT_KEYCHAIN_PATH

logger = logging.getLogger(__name__)

DEFAULT_KEYCHAIN_FILE = os.path.join(DEFAULT_KEYCHAIN_PATH, 'keychain.json')
DEFAULT_KEYCHAIN = [
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
        "uri": "globus://<endpoint>/<path>",
        "auth_type": "token",
        "auth_params": {
            "local_endpoint": "",
            "transfer_token": ""
        }
    }
]


def create_default_keychain():
    if not os.path.isdir(DEFAULT_KEYCHAIN_PATH):
        try:
            os.makedirs(DEFAULT_KEYCHAIN_PATH)
        except OSError as error:
            if error.errno != errno.EEXIST:
                raise
    with open(DEFAULT_KEYCHAIN_FILE, 'w') as kf:
        kf.write(json.dumps(DEFAULT_KEYCHAIN, sort_keys=True, indent=4, separators=(',', ': ')))
    os.chmod(DEFAULT_KEYCHAIN_FILE, stat.S_IRUSR | stat.S_IWUSR)


def read_keychain(keychain_file, create_default=True):
    keychain = json.dumps(DEFAULT_KEYCHAIN)
    if keychain_file == DEFAULT_KEYCHAIN_FILE and not os.path.isfile(keychain_file) and create_default:
        logger.debug("No keychain file specified and no default keychain file found, attempting to create one.")
        try:
            create_default_keychain()
        except Exception as e:
            logger.warning(
                "Unable to create default keychain file. A keychain file is required for authentication when "
                "retrieving files from protected remote resources. Either ensure that the default keychain "
                "file %s can be created or provide an a different path to a valid keychain file. Error: %s" %
                (DEFAULT_KEYCHAIN_FILE, bdbag.get_typed_exception(e)))
    if os.path.isfile(keychain_file):
        with open(keychain_file) as kf:
            keychain = kf.read()

    return json.loads(keychain, object_hook=lambda d: collections.namedtuple('Auth', d.keys())(*d.values()))


def has_auth_attr(auth, attr, quiet=False):
    if getattr(auth, attr) is None:
        if not quiet:
            logger.warning("Unable to locate attribute [%s] in keychain entry for uri: %s" %
                           (attr, getattr(auth, 'uri', '')))
        return False
    return True

