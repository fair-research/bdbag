import os
import datetime
import logging
from bdbag import urlsplit, urlunsplit, urlretrieve, get_typed_exception
from bdbag.fetch import get_transfer_summary, ensure_valid_output_path
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
    for auth in list((entry for entry in auth_config if (entry.get("uri", "").lower() in url.lower()))):

        if not validate_auth_config(auth):
            continue

        auth_type = auth.get("auth_type")
        auth_params = auth.get("auth_params", {})
        username = auth_params.get("username")
        password = auth_params.get("password")
        if auth_type == 'ftp-basic':
            credentials = (username, password)
            break

    return credentials


def get_file(url, output_path, auth_config, **kwargs):

    try:
        credentials = kwargs.get("credentials")
        if not credentials:
            credentials = get_credentials(url, auth_config)
        output_path = ensure_valid_output_path(url, output_path)
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
        summary = get_transfer_summary(total, elapsed)
        logger.info('File [%s] transfer successful. %s' % (output_path, summary))
        return True

    except Exception as e:
        logger.error('FTP Request Exception: %s' % (get_typed_exception(e)))
        logger.warning('File transfer failed: [%s]' % output_path)

    return False

