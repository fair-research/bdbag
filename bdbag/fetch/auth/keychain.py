import os
import logging
import json
import collections
import stat

from bdbag import DEFAULT_CONFIG_PATH as DEFAULT_KEYCHAIN_PATH

logger = logging.getLogger(__name__)

DEFAULT_KEYCHAIN_FILE = os.path.join(DEFAULT_KEYCHAIN_PATH, 'keychain.cfg')
DEFAULT_KEYCHAIN = [
    {
        "uri": "https://",
        "auth_uri": "",
        "auth_type": "form",
        "auth_method": "post",
        "auth_params": {
            "username": "",
            "password": "",
            "username_field": "username",
            "password_field": "password"
        }
    },
    {
        "uri": "globus://",
        "auth_uri": "https://nexus.api.globusonline.org/goauth/token?grant_type=client_credentials",
        "auth_params": {
            "username": "",
            "password": "",
            "local_endpoint": ""
        }
    }
]


def create_default_keychain():
    if not os.path.isdir(DEFAULT_KEYCHAIN_PATH):
        os.makedirs(DEFAULT_KEYCHAIN_PATH)
    with open(DEFAULT_KEYCHAIN_FILE, 'w') as kf:
        kf.write(json.dumps(DEFAULT_KEYCHAIN, sort_keys=True, indent=4, separators=(',', ': ')))
    os.chmod(DEFAULT_KEYCHAIN_FILE, stat.S_IRUSR | stat.S_IWUSR)


def read_config(keychain_file):
    if keychain_file == DEFAULT_KEYCHAIN_FILE and not os.path.isfile(keychain_file):
        logger.info("No default keychain file found, creating one")
        create_default_keychain()
    with open(keychain_file) as kf:
        config = kf.read()
    return json.loads(config, object_hook=lambda d: collections.namedtuple('Auth', d.keys())(*d.values()))


def has_auth_attr(auth, attr, quiet=False):
    if getattr(auth, attr, None) is None:
        if not quiet:
            logger.warn("Unable to locate attribute [%s] in keychain entry for uri: %s" %
                        (attr, getattr(auth, 'uri', '')))
        return False
    return True

