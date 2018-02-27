import os
import platform
import logging
from bdbag import urlsplit, get_typed_exception
import bdbag.fetch.auth.keychain as keychain
import globus_sdk

logger = logging.getLogger(__name__)


def validate_auth_config(auth):
    if not keychain.has_auth_attr(auth, 'auth_type'):
        return False
    if not keychain.has_auth_attr(auth, 'auth_params'):
        return False
    if not keychain.has_auth_attr(auth.auth_params, 'transfer_token'):
        return False
    if not keychain.has_auth_attr(auth.auth_params, 'local_endpoint'):
        return False

    return True


def authenticate(url, auth_config):

    for auth in list((entry for entry in auth_config if hasattr(entry, 'uri') and (entry.uri.lower() in url.lower()))):
        try:
            if not validate_auth_config(auth):
                continue
            if auth.auth_type == 'token':
                return auth.auth_params.transfer_token, auth.auth_params.local_endpoint
        except Exception as e:
            logger.warn("Unhandled exception getting Globus token: %s" % get_typed_exception(e))

    return None, None


def get_file(url, output_path, auth_config, token=None, dest_endpoint=None):

    try:
        src_endpoint = urlsplit(url).hostname
        src_path = urlsplit(url).path
        if platform.system() == "Windows":
            dest_path = ''.join(('/', output_path.replace('\\', '/').replace(':', '')))
        else:
            dest_path = os.path.abspath(output_path)

        if not token:
            token, dest_endpoint = authenticate(url, auth_config)
        if token is None:
            logger.warn("A valid Globus access token is required to create transfers. "
                        "Check keychain.json for valid parameters.")
            return False

        if dest_endpoint is None:
            logger.warn("A valid Globus destination endpoint must be specified. "
                        "Check keychain.json for valid parameters.")
            return False

        # initialize transfer client
        authorizer = globus_sdk.AccessTokenAuthorizer(token)
        client = globus_sdk.TransferClient(authorizer=authorizer)

        # Activate source endpoint
        logger.debug("Activating source endpoint: %s" % src_endpoint)
        data = client.endpoint_autoactivate(src_endpoint, if_expires_in=600)

        # Activate destination endpoint
        logger.debug("Activating destination endpoint: %s" % dest_endpoint)
        data = client.endpoint_autoactivate(dest_endpoint, if_expires_in=600)

        filename = src_path.rsplit('/', 1)[-1]
        label = "".join(("BDBag Fetch -- ", filename.replace('.', '_')))

        # get a unique ID for this transfer
        tdata = globus_sdk.TransferData(client,
                                        src_endpoint,
                                        dest_endpoint,
                                        label=label)

        tdata.add_item(src_path, dest_path, recursive=False)

        # start the transfer
        data = client.submit_transfer(tdata)
        task_id = data["task_id"]

        logger.info("Globus transfer started with ID %s" % task_id)
        logger.debug("Transferring file %s to %s" % (url, output_path))
        return True

    except Exception as e:
        logger.error('Globus transfer request exception: %s' % get_typed_exception(e))

    return False
