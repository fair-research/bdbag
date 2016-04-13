import os
import getpass

DEFAULT_CONFIG_PATH = os.path.join(os.path.expanduser('~'), '.bdbag')
DEFAULT_CONFIG_FILE = os.path.join(DEFAULT_CONFIG_PATH, 'bdbag.cfg')
DEFAULT_CONFIG = {
    'bag_config':
    {
        'bag_algorithms': ['md5', 'sha256'],
        'bag_archiver': 'zip',
        'bag_processes': 1,
        'bag_metadata':
        {
            'Contact-Name': getpass.getuser(),
            'BagIt-Profile-Identifier':
                'https://raw.githubusercontent.com/ini-bdds/bdbag/master/profiles/bdbag-profile.json'
        }
    }
}


def get_named_exception(e):
    exc = "".join(("[", type(e).__name__, "] "))
    return "".join((exc, str(e)))
