import os
import logging
import urlparse
from transports import *

logger = logging.getLogger(__name__)

UNIMPLEMENTED = "Transfer protocol \"%s\" is not supported by this implementation"

SCHEME_HTTP = 'http'
SCHEME_HTTPS = 'https'
SCHEME_GLOBUS = 'globus'
SCHEME_FTP = 'ftp'
SCHEME_SFTP = 'sftp'
SCHEME_ARK = 'ark'


def fetch_bag_files(bag):

    for url, size, path in bag.fetch_entries():
        scheme = urlparse.urlsplit(url, True).scheme.lower()
        output_path = os.path.normpath(os.path.join(bag.path, path))
        logger.info("Transferring file %s to %s" % (url, output_path))
        if SCHEME_HTTP == scheme or SCHEME_HTTPS == scheme:
            fetch_http.get_file(url, output_path)
        elif SCHEME_GLOBUS == scheme:
            fetch_globus.get_file(url, output_path)
        else:
            logger.warn(UNIMPLEMENTED % scheme)
