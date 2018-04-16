import os
import logging
import datetime
from bdbag import urlsplit, get_typed_exception
import bdbag.fetch.auth.keychain as keychain

logger = logging.getLogger(__name__)

CHUNK_SIZE = 1024 * 10240
SESSIONS = dict()


def validate_auth_config(auth):
    if not keychain.has_auth_attr(auth, 'auth_type'):
        return False
    if not keychain.has_auth_attr(auth, 'auth_params'):
        return False
    if not keychain.has_auth_attr(auth.auth_params, 'username'):
        return False
    if not keychain.has_auth_attr(auth.auth_params, 'password'):
        return False

    return True


def authenticate(url, auth_config):

    for auth in list((entry for entry in auth_config if hasattr(entry, 'uri') and (entry.uri.lower() in url.lower()))):
        try:
            if not validate_auth_config(auth):
                continue
            if auth.auth_type == 'irods-password':
                return auth.auth_params.username, auth.auth_params.password
        except AttributeError as e:
            logger.warn("Exception getting iRODS authentication parameters: %s" % get_typed_exception(e))

    logger.warning("Could not locate a suitable keychain entry for: %s" % url)
    return None, None


def get_session(url, auth_config):

    url_parts = urlsplit(url)
    base_url = str("%s://%s" % (url_parts.scheme, url_parts.netloc))
    session = SESSIONS.get(base_url, None)
    if not session:
        session = get_new_session(url, auth_config)
        SESSIONS[base_url] = session

    return session


def get_new_session(url, auth_config):
    url_parts = urlsplit(url)
    port = url_parts.port
    username, password = authenticate(url, auth_config)
    if username is None or password is None:
        raise ValueError("Missing required username or password parameter in keychain")

    from irods.session import iRODSSession
    session = iRODSSession(irods_host=url_parts.hostname,
                           irods_port=port if port else 1247,
                           irods_zone_name=url_parts.path.split("/")[1],
                           irods_user_name=str(username),
                           password=str(password))

    return session


def get_file(url, output_path, auth_config, headers=None, session=None):

    try:
        if not session:
            session = get_session(url, auth_config)
        output_dir = os.path.dirname(os.path.abspath(output_path))
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        logger.info("Attempting iRODS GET from URL: %s" % url)
        url_parts = urlsplit(url)
        obj = session.data_objects.get(url_parts.path)
        total = 0
        start = datetime.datetime.now()
        logger.debug("Transferring file %s to %s" % (url, output_path))
        with open(output_path, 'wb') as data_file, obj.open('r+') as input_path:
            while True:
                data = input_path.read(CHUNK_SIZE)
                if not data:
                    break
                data_file.write(data)
                total += len(data)
        elapsed = datetime.datetime.now() - start
        totalSecs = elapsed.total_seconds()
        totalMBs = float(total) / float((1024 * 1024))
        throughput = str("%.3f MB/second" % (totalMBs / totalSecs if totalSecs > 0 else 0.001))
        logger.info('File [%s] transfer successful. %.3f MB transferred at %s. Elapsed time: %s. ' %
                    (output_path, totalMBs, throughput, elapsed))
        return True

    except Exception as e:
        logger.error('iRODS Request Exception: %s' % (get_typed_exception(e)))

    return False


def cleanup():
    for session in SESSIONS.values():
        session.cleanup()
    SESSIONS.clear()
