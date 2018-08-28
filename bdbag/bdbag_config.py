import os
import errno
import logging
import json
import shutil
from collections import OrderedDict
from bdbag import get_typed_exception, BAG_PROFILE_TAG, BDBAG_PROFILE_ID, VERSION


logger = logging.getLogger(__name__)

ID_RESOLVER_TAG = 'identifier_resolvers'
DEFAULT_ID_RESOLVERS = ['n2t.net', 'identifiers.org']

COOKIE_JAR_TAG = "http_cookies"
COOKIE_JAR_SEARCH_TAG = "scan_for_cookie_files"
COOKIE_JAR_FILE_TAG = "file_names"
COOKIE_JAR_PATHS_TAG = "search_paths"
COOKIE_JAR_PATH_FILTER_TAG = "search_paths_filter"
DEFAULT_COOKIE_JAR_FILE_NAMES = ["*cookies.txt"]
DEFAULT_COOKIE_JAR_SEARCH_PATHS = [os.path.normpath(os.path.join(os.path.expanduser('~')))]
DEFAULT_COOKIE_JAR_SEARCH_PATH_FILTER = ".bdbag"

BAG_CONFIG_TAG = "bag_config"
BAG_SPEC_VERSION_TAG = "bagit_spec_version"
BAG_ALGORITHMS_TAG = "bag_algorithms"
BAG_PROCESSES_TAG = "bag_processes"
BAG_METADATA_TAG = "bag_metadata"
CONFIG_VERSION_TAG = "bdbag_config_version"
DEFAULT_BAG_SPEC_VERSION = "0.97"
DEFAULT_CONFIG_PATH = os.path.join(os.path.expanduser('~'), '.bdbag')
DEFAULT_CONFIG_FILE = os.path.join(DEFAULT_CONFIG_PATH, 'bdbag.json')
DEFAULT_BAG_ALGORITHMS = ['md5', 'sha256']

DEFAULT_CONFIG = {
    CONFIG_VERSION_TAG: VERSION,
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
    ID_RESOLVER_TAG: DEFAULT_ID_RESOLVERS,
    COOKIE_JAR_TAG:
    {
        COOKIE_JAR_SEARCH_TAG: True,
        COOKIE_JAR_FILE_TAG: DEFAULT_COOKIE_JAR_FILE_NAMES,
        COOKIE_JAR_PATHS_TAG: DEFAULT_COOKIE_JAR_SEARCH_PATHS,
        COOKIE_JAR_PATH_FILTER_TAG: DEFAULT_COOKIE_JAR_SEARCH_PATH_FILTER
    }
}


def create_default_config():
    try:
        if not os.path.isdir(DEFAULT_CONFIG_PATH):
            try:
                os.makedirs(DEFAULT_CONFIG_PATH, mode=0o750)
            except OSError as error:
                if error.errno != errno.EEXIST:
                    raise
        with open(DEFAULT_CONFIG_FILE, 'w') as cf:
            cf.write(json.dumps(DEFAULT_CONFIG, indent=2))
            cf.close()
            print("Created default configuration file in: %s" % DEFAULT_CONFIG_FILE)
    except Exception as e:
        logger.debug("Unable to create default configuration file %s. %s" %
                     (DEFAULT_CONFIG_FILE, get_typed_exception(e)))


def read_config(config_file, create_default=True):
    if config_file == DEFAULT_CONFIG_FILE and not os.path.isfile(config_file) and create_default:
        create_default_config()
    if os.path.isfile(config_file):
        with open(config_file) as cf:
            config = cf.read()
    else:
        config = json.dumps(DEFAULT_CONFIG)
        logger.warning("Unable to read configuration file: [%s]. Using internal defaults." % DEFAULT_CONFIG_FILE)

    return json.loads(config, object_pairs_hook=OrderedDict)


if os.access(
        os.path.expanduser('~'), os.F_OK | os.R_OK | os.W_OK | os.X_OK) and not os.path.isfile(DEFAULT_CONFIG_FILE):
    create_default_config()

