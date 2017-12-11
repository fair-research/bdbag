import os
from pkg_resources import get_distribution, DistributionNotFound

try:
    VERSION = get_distribution("bdbag").version
except DistributionNotFound:
    VERSION = '0.0.dev0'

try:
    BAGIT_VERSION = get_distribution("bagit").version
except DistributionNotFound:
    BAGIT_VERSION = '0.0.dev0'

BAG_PROFILE_TAG = 'BagIt-Profile-Identifier'
BDBAG_PROFILE_ID = 'https://raw.githubusercontent.com/ini-bdds/bdbag/master/profiles/bdbag-profile.json'
BDBAG_RO_PROFILE_ID = 'https://raw.githubusercontent.com/ini-bdds/bdbag/master/profiles/bdbag-ro-profile.json'

DEFAULT_CONFIG_PATH = os.path.join(os.path.expanduser('~'), '.bdbag')
DEFAULT_CONFIG_FILE = os.path.join(DEFAULT_CONFIG_PATH, 'bdbag.json')
DEFAULT_CONFIG = {
    'bag_config':
    {
        'bag_algorithms': ['md5', 'sha256'],
        'bag_processes': 1,
        'bag_metadata':
        {
            BAG_PROFILE_TAG: BDBAG_PROFILE_ID
        }
    }
}


def get_typed_exception(e):
    exc = "".join(("[", type(e).__name__, "] "))
    return "".join((exc, str(e)))
