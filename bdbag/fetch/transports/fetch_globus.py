import os
import platform
import logging
import json
import urlparse
import requests
import bdbag
import bdbag.fetch.auth.keychain as keychain
from globusonline.transfer.api_client import TransferAPIClient, Transfer

logger = logging.getLogger(__name__)

TOKENS = dict()
KEYCHAIN = keychain.read_config(keychain.DEFAULT_KEYCHAIN_FILE)


def validate_auth_config(auth):
    if not keychain.has_auth_attr(auth, 'auth_uri'):
        return False
    if not keychain.has_auth_attr(auth, 'auth_params'):
        return False
    if not keychain.has_auth_attr(auth.auth_params, 'username'):
        return False
    if not keychain.has_auth_attr(auth.auth_params, 'password'):
        return False
    if not keychain.has_auth_attr(auth.auth_params, 'local_endpoint'):
        return False

    return True


def authenticate(url):

    response = None
    session = requests.session()

    for auth in list((entry for entry in KEYCHAIN if hasattr(entry, 'uri') and (entry.uri.lower() in url.lower()))):

        try:
            if not validate_auth_config(auth):
                continue

            auth_type = auth.auth_type if keychain.has_auth_attr(auth, 'auth_type', quiet=True) else 'basic'
            auth_method = auth.auth_method.lower() if keychain.has_auth_attr(auth, 'auth_type', quiet=True) else 'get'

            if auth_type == 'basic':
                if auth.auth_params.password in TOKENS:
                    token, endpoint = TOKENS[auth.auth_params.password]
                    return token, endpoint
                session.auth = (auth.auth_params.username, auth.auth_params.password)
                if auth_method == 'post':
                    response = session.post(auth.auth_uri, auth=session.auth)
                elif auth_method == 'get':
                    response = session.get(auth.auth_uri, auth=session.auth)
                if response.status_code > 203:
                    logger.warn('Globus authentication failed with Status Code: %s %s' %
                                (response.status_code, response.text))
                else:
                    logger.info("Globus authentication successful: %s", auth.auth_uri)
                    token = json.loads(response.text)
                    access_token = token['access_token']
                    TOKENS[auth.auth_params.password] = access_token, auth.auth_params.local_endpoint
                    return access_token, auth.auth_params.local_endpoint
            else:
                continue

        except Exception as e:
            logger.warn("Unhandled exception during Globus authentication: %s" % bdbag.get_named_exception(e))

    return None, None


def get_file(url, output_path, token=None, dest_endpoint=None):

    try:
        src_endpoint = urlparse.urlsplit(url).hostname
        src_path = urlparse.urlsplit(url).path
        if platform.system() == "Windows":
            dest_path = ''.join(('/', output_path.replace('\\', '/').replace(':', '')))
        else:
            dest_path = os.path.abspath(output_path)

        if not token:
            token, dest_endpoint = authenticate(url)
        if token is None:
            logger.warn("A valid Globus access token is required to create transfers. "
                        "Check keychain.cfg for valid parameters.")
            return False
        if dest_endpoint is None:
            logger.warn("A valid Globus destination endpoint must be specified. "
                        "Check keychain.cfg for valid parameters.")
            return False

        # initialize transfer client
        client = TransferAPIClient(None, goauth=token.strip())

        # Activate source endpoint
        logger.debug("Activating source endpoint: %s" % src_endpoint)
        code, reason, data = client.endpoint_autoactivate(src_endpoint, if_expires_in=600)
        logger.debug("Activation expires: %s" % data["expire_time"])

        # Activate destination endpoint
        logger.debug("Activating destination endpoint: %s" % dest_endpoint)
        code, reason, data = client.endpoint_autoactivate(dest_endpoint, if_expires_in=600)
        logger.debug("Activation expires: %s" % data["expire_time"])

        # get a unique ID for this transfer
        code, message, data = client.transfer_submission_id()
        submission_id = data["value"]

        # start the transfer
        filename = src_path.rsplit('/', 1)[-1]
        label = "".join(("BDBag Fetch -- ", filename.replace('.', '_')))
        transfer = Transfer(submission_id, src_endpoint, dest_endpoint, label=label)
        transfer.add_item(src_path, dest_path)
        code, reason, data = client.transfer(transfer)
        task_id = data["task_id"]

        logger.info("Globus transfer started with ID %s" % task_id)
        logger.debug("Transferring file %s to %s" % (url, output_path))
        return True

    except Exception as e:
        logger.error('Globus transfer request exception: %s' % bdbag.get_named_exception(e))

    return False
