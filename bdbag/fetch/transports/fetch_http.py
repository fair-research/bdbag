import os
import logging
import requests
import certifi
import urlparse
import bdbag
import bdbag.fetch.auth.keychain as keychain

logger = logging.getLogger(__name__)

CHUNK_SIZE = 1024 * 1024
SESSIONS = dict()
KEYCHAIN = keychain.read_config(keychain.DEFAULT_KEYCHAIN_FILE)


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


def get_session(url):

    session = None
    response = None

    for auth in list((entry for entry in KEYCHAIN if hasattr(entry, 'uri') and (entry.uri.lower() in url.lower()))):

        try:
            if not validate_auth_config(auth):
                continue

            if not auth.auth_uri:
                continue

            if auth.uri in SESSIONS:
                session = SESSIONS[auth.uri]
                break
            else:
                session = requests.session()

            if auth.auth_type == 'basic':
                session.auth = (auth.auth_params.username, auth.auth_params.password)
                auth_method = auth.auth_method.lower()
                if auth_method == 'post':
                    response = session.post(auth.auth_uri, auth=session.auth)
                elif auth_method == 'get':
                    response = session.get(auth.auth_uri, auth=session.auth)
            elif auth.auth_type == 'form':
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

    return session if session else requests.session()


def get_file(url, output_path=None, headers=None, session=None):

    try:
        if not session:
            session = get_session(url)
        output_dir = os.path.dirname(os.path.abspath(output_path))
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        r = session.get(url, headers=headers, stream=True, verify=certifi.where())
        if r.status_code == 401:
            session = get_session(url)
            r = session.get(url, headers=headers, stream=True, verify=certifi.where())
        if r.status_code != 200:
            logger.error('HTTP GET Failed for url: %s' % url)
            logger.error("Host %s responded:\n\n%s" % (urlparse.urlsplit(url).netloc,  r.text))
            logger.warn('File [%s] transfer failed. ' % output_path)
        else:
            with open(output_path, 'wb') as data_file:
                for chunk in r.iter_content(CHUNK_SIZE):
                    data_file.write(chunk)
                data_file.flush()
            logger.info('File [%s] transfer successful.' % output_path)
            return True

    except requests.exceptions.RequestException as e:
        logger.error('HTTP Request Exception: %s %s' % (e.errno, e.message))

    return False
