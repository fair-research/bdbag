import os
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


def get_named_exception(e):
    exc = "".join(("[", type(e).__name__, "] "))
    return "".join((exc, str(e)))
