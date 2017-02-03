import os
import sys
import datetime
import logging
import requests
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry
import certifi
import bdbag
import bdbag.fetch.auth.keychain as keychain

if sys.version_info > (3,):
    from urllib.parse import urlsplit
else:
    from urlparse import urlsplit

logger = logging.getLogger(__name__)

CHUNK_SIZE = 1024 * 10240
SESSIONS = dict()
HEADERS = {'Connection': 'keep-alive'}


def validate_auth_config(auth):
    if not keychain.has_auth_attr(auth, 'auth_uri'):
        return False
    if not keychain.has_auth_attr(auth, 'auth_type'):
        return False
    if not keychain.has_auth_attr(auth, 'auth_method'):
        return False
    if not keychain.has_auth_attr(auth, 'auth_params'):
        return False
    if not keychain.has_auth_attr(auth.auth_params, 'username'):
        return False
    if not keychain.has_auth_attr(auth.auth_params, 'password'):
        return False
    if not keychain.has_auth_attr(auth.auth_params, 'username_field'):
        return False
    if not keychain.has_auth_attr(auth.auth_params, 'password_field'):
        return False

    return True


def get_session(url, auth_config):

    session = None
    response = None

    for auth in list((entry for entry in auth_config if hasattr(entry, 'uri') and (entry.uri.lower() in url.lower()))):

        try:
            if not validate_auth_config(auth):
                continue

            if not auth.auth_uri:
                continue

            if auth.uri in SESSIONS:
                session = SESSIONS[auth.uri]
                break
            else:
                session = get_new_session()

            if auth.auth_type == 'http-basic':
                session.auth = (auth.auth_params.username, auth.auth_params.password)
                auth_method = auth.auth_method.lower()
                if auth_method == 'post':
                    response = session.post(auth.auth_uri, auth=session.auth)
                elif auth_method == 'get':
                    response = session.get(auth.auth_uri, auth=session.auth)
            elif auth.auth_type == 'http-form':
                response = session.post(auth.auth_uri,
                                        {auth.auth_params.username_field: auth.auth_params.username,
                                         auth.auth_params.password_field: auth.auth_params.password})
            if response.status_code > 203:
                logger.warn('Authentication failed with Status Code: %s %s\n' % (response.status_code, response.text))
            else:
                logger.info("Session established: %s", auth.auth_uri)
                SESSIONS[auth.auth_uri] = session
                break

        except Exception as e:
            logger.warn("Unhandled exception during HTTP(S) authentication: %s" % bdbag.get_named_exception(e))

    if not session:
        url_parts = urlsplit(url)
        base_url = str("%s://%s" % (url_parts.scheme, url_parts.netloc))
        session = SESSIONS.get(base_url, None)
        if not session:
            session = get_new_session()
            SESSIONS[base_url] = session

    return session


def get_new_session():
    session = requests.session()
    retries = Retry(connect=5,
                    read=5,
                    backoff_factor=1.0,
                    status_forcelist=[500, 502, 503, 504])

    session.mount('http://', HTTPAdapter(max_retries=retries))
    session.mount('https://', HTTPAdapter(max_retries=retries))

    return session


def get_file(url, output_path, auth_config, headers=None, session=None):

    try:
        if not session:
            session = get_session(url, auth_config)
        output_dir = os.path.dirname(os.path.abspath(output_path))
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        if not headers:
            headers = HEADERS
        else:
            headers.update(HEADERS)
        logger.info("Attempting GET from URL: %s" % url)
        r = session.get(url, headers=headers, stream=True, verify=certifi.where())
        if r.status_code == 401:
            session = get_session(url, auth_config)
            r = session.get(url, headers=headers, stream=True, verify=certifi.where())
        if r.status_code != 200:
            logger.error('HTTP GET Failed for URL: %s' % url)
            logger.error("Host %s responded:\n\n%s" % (urlsplit(url).netloc,  r.text))
            logger.warn('File transfer failed: [%s]' % output_path)
        else:
            total = 0
            start = datetime.datetime.now()
            logger.debug("Transferring file %s to %s" % (url, output_path))
            with open(output_path, 'wb') as data_file:
                for chunk in r.iter_content(chunk_size=CHUNK_SIZE):
                    data_file.write(chunk)
                    total += len(chunk)
            elapsed = datetime.datetime.now() - start
            totalSecs = elapsed.total_seconds()
            totalMBs = total / (1024 * 1024)
            throughput = str("%.3f MB/second" % (totalMBs / totalSecs if totalSecs > 0 else 0.001))
            logger.info('File [%s] transfer successful. %.3f MB transferred at %s. Elapsed time: %s. ' %
                        (output_path, totalMBs, throughput, elapsed))
            return True

    except requests.exceptions.RequestException as e:
        logger.error('HTTP Request Exception: %s' % (bdbag.get_named_exception(e)))

    return False


def cleanup():
    SESSIONS.clear()
