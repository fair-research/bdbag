#
# Copyright 2016 University of Southern California
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
import os
import importlib
import logging
import platform
from bdbag import urlsplit, get_typed_exception
from bdbag.fetch import *
from bdbag.fetch.transports.base_transport import BaseFetchTransport
import bdbag.fetch.auth.keychain as kc

logger = logging.getLogger(__name__)
globus_sdk = None
globus_sdk_name = "globus_sdk"


class GlobusTransferFetchTransport(BaseFetchTransport):

    def __init__(self, config, keychain, **kwargs):
        super(GlobusTransferFetchTransport, self).__init__(config, keychain, **kwargs)

    @staticmethod
    def validate_auth_config(auth):
        if not kc.has_auth_attr(auth, "auth_type"):
            return False
        if not kc.has_auth_attr(auth, "auth_params"):
            return False
        if not kc.has_auth_attr(auth["auth_params"], "transfer_token"):
            return False
        if not kc.has_auth_attr(auth["auth_params"], "local_endpoint"):
            return False

        return True

    def get_credentials(self, url):
        credentials = (None, None)
        for auth in kc.get_auth_entries(url, self.keychain):
            if not self.validate_auth_config(auth):
                continue
            auth_type = auth.get("auth_type")
            auth_params = auth.get("auth_params", {})
            if auth_type == "globus_transfer":
                transfer_token = auth_params.get("transfer_token")
                local_endpoint = auth_params.get("local_endpoint")
                credentials = (transfer_token, local_endpoint)
                break

        return credentials

    def fetch(self, url, output_path, **kwargs):

        # locate library
        global globus_sdk
        if globus_sdk is None:
            try:
                globus_sdk = importlib.import_module(globus_sdk_name)
            except ImportError:
                pass
        if globus_sdk is None:
            raise RuntimeError("Cannot fetch file using Globus Transfer: unable to find the Globus SDK. "
                               "Ensure that the Python module \"%s\" is installed." % globus_sdk_name)

        try:
            src_endpoint = urlsplit(url).hostname
            src_path = urlsplit(url).path
            output_path = ensure_valid_output_path(url, output_path)
            if platform.system() == "Windows":
                dest_path = "".join(("/", output_path.replace("\\", "/").replace(":", "")))
            else:
                dest_path = os.path.abspath(output_path)

            token, dest_endpoint = self.get_credentials(url)
            if token is None:
                logger.warning("A valid Globus Transfer access token is required to create transfers. "
                               "Check keychain.json for invalid parameters.")
                return None

            if dest_endpoint is None:
                logger.warning("A valid Globus Transfer destination endpoint must be specified. "
                               "Check keychain.json for invalid parameters.")
                return None

            # initialize transfer client
            authorizer = globus_sdk.AccessTokenAuthorizer(token)
            client = globus_sdk.TransferClient(authorizer=authorizer)

            # Activate source endpoint
            logger.debug("Activating source endpoint: %s" % src_endpoint)
            data = client.endpoint_autoactivate(src_endpoint, if_expires_in=600)

            # Activate destination endpoint
            logger.debug("Activating destination endpoint: %s" % dest_endpoint)
            data = client.endpoint_autoactivate(dest_endpoint, if_expires_in=600)

            filename = src_path.rsplit("/", 1)[-1]
            label = "".join(("BDBag Fetch -- ", filename.replace(".", "_")))

            # get a unique ID for this transfer
            tdata = globus_sdk.TransferData(client,
                                            src_endpoint,
                                            dest_endpoint,
                                            label=label)

            tdata.add_item(src_path, dest_path, recursive=False)

            # start the transfer
            data = client.submit_transfer(tdata)
            task_id = data["task_id"]

            logger.info("Globus Transfer started with ID %s" % task_id)
            logger.debug("Transferring file %s to %s" % (url, output_path))
            return output_path

        except Exception as e:
            logger.error("Globus Transfer request exception: %s" % get_typed_exception(e))

        return None

    def cleanup(self):
        pass
