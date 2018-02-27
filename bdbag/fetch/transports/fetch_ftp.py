import os
import datetime
import logging
from bdbag import urlsplit, urlunsplit, urlretrieve, get_typed_exception
import bdbag.fetch.auth.keychain as keychain

logger = logging.getLogger(__name__)


def validate_auth_config(auth):
    if not keychain.has_auth_attr(auth, 'uri'):
        return False
    if not keychain.has_auth_attr(auth, 'auth_type'):
        return False
    if not keychain.has_auth_attr(auth, 'auth_params'):
        return False

    return True


def get_credentials(url, auth_config):

    credentials = (None, None)
    for auth in list((entry for entry in auth_config if hasattr(entry, 'uri') and (entry.uri.lower() in url.lower()))):

        if not validate_auth_config(auth):
            continue

        if auth.auth_type == 'ftp-basic':
            credentials = (auth.auth_params.username, auth.auth_params.password)
            break

    return credentials


def get_file(url, output_path, auth_config, credentials=None):

    try:
        if not credentials:
            credentials = get_credentials(url, auth_config)
        output_dir = os.path.dirname(os.path.abspath(output_path))
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        logger.info("Attempting FTP retrieve from URL: %s" % url)
        creds = "%s:%s@" % (credentials[0] or "anonymous", credentials[1] or "bdbag@users.noreply.github.com")
        url_parts = urlsplit(url)
        full_url = urlunsplit(
            (url_parts.scheme, "%s%s" % (creds, url_parts.netloc), url_parts.path, url_parts.query, url_parts.fragment))
        start = datetime.datetime.now()
        logger.debug("Transferring file %s to %s" % (url, output_path))
        urlretrieve(full_url, output_path)
        elapsed = datetime.datetime.now() - start
        total = os.path.getsize(output_path)
        totalSecs = elapsed.total_seconds()
        totalMBs = float(total) / float((1024 * 1024))
        throughput = str("%.3f MB/second" % (totalMBs / totalSecs if totalSecs > 0 else 0.001))
        logger.info('File [%s] transfer successful. %.3f MB transferred at %s. Elapsed time: %s. ' %
                    (output_path, totalMBs, throughput, elapsed))
        return True

    except Exception as e:
        logger.error('FTP Request Exception: %s' % (get_typed_exception(e)))
        logger.warning('File transfer failed: [%s]' % output_path)

    return False

