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
import datetime
import logging
from importlib import import_module
from bdbag import urlsplit, urlunsplit, stob, get_typed_exception
from bdbag.bdbag_config import DEFAULT_CONFIG, DEFAULT_FETCH_CONFIG, FETCH_CONFIG_TAG
from bdbag.fetch import *
from bdbag.fetch.transports.base_transport import BaseFetchTransport
from bdbag.fetch.auth import keychain as kc

logger = logging.getLogger(__name__)

GCS = None


class GCSFetchTransport(BaseFetchTransport):

    def __init__(self, config, keychain, **kwargs):
        super(GCSFetchTransport, self).__init__(config, keychain, **kwargs)
        self.config = config or DEFAULT_FETCH_CONFIG[SCHEME_GS]

    @staticmethod
    def import_gcs():
        # locate library
        global GCS
        if GCS is None:
            gcs_module = "google.cloud.storage"
            try:
                GCS = import_module(gcs_module)
            except ImportError as e:
                raise RuntimeError(
                    "Unable to find required module. Ensure that the Python module "
                    "\"%s\" is installed." % gcs_module, e)

    @staticmethod
    def validate_auth_config(auth):
        if not kc.has_auth_attr(auth, "auth_type"):
            return False

        return True

    def get_credentials(self, url):
        credentials = None
        for auth in kc.get_auth_entries(url, self.keychain):
            if not self.validate_auth_config(auth):
                continue
            auth_type = auth.get("auth_type")
            auth_params = auth.get("auth_params")
            if auth_type == "gcs-credentials":
                credentials = auth_params
                break

        return credentials

    @staticmethod
    def get_requester_pays_status(client, bucket_name):
        """Get a bucket's requester pays metadata"""

        bucket = client.get_bucket(bucket_name)
        requester_pays_status = bucket.requester_pays

        if requester_pays_status:
            logger.info(f"Requester Pays is enabled for {bucket_name}")

        return requester_pays_status

    def fetch(self, url, output_path, **kwargs):
        success = False
        output_path = ensure_valid_output_path(url, output_path)

        self.import_gcs()
        try:
            credentials = self.get_credentials(url) or {}
            project_id = credentials.get("project_id") or self.config["default_project_id"]
            try:
                gcs_client = GCS.Client(project=project_id)
            except Exception as e:
                raise RuntimeError("Unable to create GCS storage client: %s" % get_typed_exception(e))

            logger.info("Attempting GET from URL: %s" % url)
            upr = urlsplit(url, allow_fragments=False)
            requester_pays = self.get_requester_pays_status(gcs_client, upr.netloc)
            bucket = gcs_client.bucket(upr.netloc, user_project=project_id if requester_pays else None)

            logger.debug("Transferring file %s to %s" % (url, output_path))
            blob = bucket.blob(upr.path.lstrip("/"))
            start = datetime.datetime.now()
            blob.download_to_filename(output_path)
            elapsed_time = datetime.datetime.now() - start
            total = os.path.getsize(output_path)
            check_transfer_size_mismatch(output_path, kwargs.get("size"), total)
            logger.info("File [%s] transfer complete. %s" % (output_path, get_transfer_summary(total, elapsed_time)))
            success = True
        except Exception as e:
            logger.error(get_typed_exception(e))
        finally:
            if not success:
                logger.error("GCS GET Failed for URL: %s" % url)
                logger.warning("File transfer failed: [%s]" % output_path)

        return output_path if success else None

    def cleanup(self):
        pass
