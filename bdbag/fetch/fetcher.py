import os
import sys
import logging
from bdbag.fetch.transports import *

if sys.version_info > (3,):
    from urllib.parse import urlsplit
else:
    from urlparse import urlsplit

logger = logging.getLogger(__name__)

UNIMPLEMENTED = "Transfer protocol \"%s\" is not supported by this implementation"

SCHEME_HTTP = 'http'
SCHEME_HTTPS = 'https'
SCHEME_GLOBUS = 'globus'
SCHEME_FTP = 'ftp'
SCHEME_SFTP = 'sftp'
SCHEME_ARK = 'ark'


def fetch_bag_files(bag):

    success = True
    for url, size, path in bag.fetch_entries():
        output_path = os.path.normpath(os.path.join(bag.path, path))
        success = fetch_file(url, size, output_path)
    return success


def fetch_file(url, size, path):

    scheme = urlsplit(url, allow_fragments=True).scheme.lower()
    if SCHEME_HTTP == scheme or SCHEME_HTTPS == scheme:
        return fetch_http.get_file(url, path)
    elif SCHEME_GLOBUS == scheme:
        return fetch_globus.get_file(url, path)
    elif SCHEME_ARK == scheme:
        for url in fetch_ark.resolve(url):
            if fetch_file(url, size, path):
                return True
        return False
    else:
        logger.warn(UNIMPLEMENTED % scheme)
        return False
