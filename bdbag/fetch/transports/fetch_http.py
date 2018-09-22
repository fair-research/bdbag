import os
import datetime
import logging
import certifi
import requests
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry
from bdbag import urlsplit, get_typed_exception
from bdbag.bdbag_config import DEFAULT_CONFIG, DEFAULT_FETCH_CONFIG, FETCH_CONFIG_TAG
from bdbag.fetch import Megabyte, get_transfer_summary
import bdbag.fetch.auth.keychain as keychain

logger = logging.getLogger(__name__)

CHUNK_SIZE = 10 * Megabyte
SESSIONS = dict()
HEADERS = {'Connection': 'keep-alive'}


def validate_auth_config(auth):
    if not keychain.has_auth_attr(auth, 'auth_type'):
        return False
    if not keychain.has_auth_attr(auth, 'auth_params'):
        return False

    return True


def get_session(url, auth_config, config):

    session = None
    response = None

    for auth in list((entry for entry in auth_config if hasattr(entry, 'uri') and (entry.uri.lower() in url.lower()))):

        try:
            if not validate_auth_config(auth):
                continue

            if auth.uri in SESSIONS:
                session = SESSIONS[auth.uri]
                break
            else:
                session = init_new_session(config["session_config"])

            if auth.auth_type == 'cookie':
                if auth.auth_params and hasattr(auth.auth_params, 'cookies'):
                    cookies = auth.auth_params.cookies
                    for cookie in cookies:
                        name, value = cookie.split('=', 1)
                        session.cookies.set(name, value, domain=urlsplit(auth.uri).hostname, path='/')
                    SESSIONS[auth.uri] = session
                    break

            if auth.auth_type == 'bearer-token':
                if auth.auth_params and hasattr(auth.auth_params, 'token'):
                    session.headers.update({"Authorization": "Bearer " + auth.auth_params.token})
                    SESSIONS[auth.uri] = session
                    break
                else:
                    logging.warning("Missing required parameters [token] for auth_type [%s] for keychain entry [%s]" %
                                    (auth.auth_type, auth.uri))

            # if we get here the assumption is that the auth_type is either http-basic or http-form and that an
            # actual session "login" request is necessary
            auth_uri = auth.uri
            if keychain.has_auth_attr(auth, 'auth_uri'):
                auth_uri = auth.auth_uri

            if not (keychain.has_auth_attr(auth.auth_params, 'username') and
                    keychain.has_auth_attr(auth.auth_params, 'password')):
                logging.warning(
                    "Missing required parameters [username, password] for auth_type [%s] for keychain entry [%s]" %
                    (auth.auth_type, auth.uri))
                continue

            if auth.auth_type == 'http-basic':
                session.auth = (auth.auth_params.username, auth.auth_params.password)
                auth_method = "post"
                if keychain.has_auth_attr(auth.auth_params, 'auth_method'):
                    auth_method = auth.auth_params.auth_method.lower()
                if auth_method == 'post':
                    response = session.post(auth_uri, auth=session.auth)
                elif auth_method == 'get':
                    response = session.get(auth_uri, auth=session.auth)
                else:
                    logging.warning("Unsupported auth_method [%s] for auth_type [%s] for keychain entry [%s]" %
                                    (auth_method, auth.auth_type, auth.uri))
            elif auth.auth_type == 'http-form':
                response = session.post(auth_uri,
                                        {auth.auth_params.username_field or "username": auth.auth_params.username,
                                         auth.auth_params.password_field or "password": auth.auth_params.password})
            if response.status_code > 203:
                logger.warning(
                    'Authentication failed with Status Code: %s %s\n' % (response.status_code, response.text))
            else:
                logger.info("Session established: %s", auth.uri)
                SESSIONS[auth.uri] = session
                break

        except Exception as e:
            logger.warning("Unhandled exception during HTTP(S) authentication: %s" % get_typed_exception(e))

    if not session:
        url_parts = urlsplit(url)
        base_url = str("%s://%s" % (url_parts.scheme, url_parts.netloc))
        session = SESSIONS.get(base_url, None)
        if not session:
            session = init_new_session(config["session_config"])
            SESSIONS[base_url] = session

    return session


def init_new_session(session_config):
    session = requests.session()
    retries = Retry(connect=session_config['retry_connect'],
                    read=session_config['retry_read'],
                    backoff_factor=session_config['retry_backoff_factor'],
                    status_forcelist=session_config['retry_status_forcelist'])
    session.mount('http://', HTTPAdapter(max_retries=retries))
    session.mount('https://', HTTPAdapter(max_retries=retries))

    return session


def get_file(url, output_path, auth_config, **kwargs):

    try:
        bdbag_config = kwargs.get("config", DEFAULT_CONFIG)
        fetch_config = bdbag_config.get(FETCH_CONFIG_TAG, DEFAULT_FETCH_CONFIG)
        config = fetch_config.get("http", DEFAULT_FETCH_CONFIG["http"])

        session = get_session(url, auth_config, config)
        output_dir = os.path.dirname(os.path.abspath(output_path))
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        headers = kwargs.get("headers")
        if not headers:
            headers = HEADERS
        else:
            headers.update(HEADERS)
        logger.info("Attempting GET from URL: %s" % url)
        r = session.get(url,
                        headers=headers,
                        stream=True,
                        allow_redirects=config.get("allow_redirects", True),
                        verify=certifi.where(),
                        cookies=kwargs.get("cookies"))
        if r.status_code == 401:
            session = get_session(url, auth_config, config)
            r = session.get(url,
                            headers=headers,
                            stream=True,
                            allow_redirects=config.get("allow_redirects", True),
                            verify=certifi.where())
        if r.status_code != 200:
            logger.error('HTTP GET Failed for URL: %s' % url)
            logger.error("Host %s responded:\n\n%s" % (urlsplit(url).netloc,  r.text))
            logger.warning('File transfer failed: [%s]' % output_path)
        else:
            total = 0
            start = datetime.datetime.now()
            logger.debug("Transferring file %s to %s" % (url, output_path))
            with open(output_path, 'wb') as data_file:
                for chunk in r.iter_content(chunk_size=CHUNK_SIZE):
                    data_file.write(chunk)
                    total += len(chunk)
            elapsed_time = datetime.datetime.now() - start
            summary = get_transfer_summary(total, elapsed_time)
            logger.info('File [%s] transfer successful. %s' % (output_path, summary))
            return True

    except requests.exceptions.RequestException as e:
        logger.error('HTTP Request Exception: %s' % (get_typed_exception(e)))

    return False


def cleanup():
    for session in SESSIONS.values():
        session.close()
    SESSIONS.clear()
