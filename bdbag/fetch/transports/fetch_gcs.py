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
GSA = None


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
        global GSA
        if GSA is None:
            gsa_module = "google.oauth2.service_account"
            try:
                GSA = import_module(gsa_module)
            except ImportError as e:
                raise RuntimeError(
                    "Unable to find required module. Ensure that the Python module "
                    "\"%s\" is installed." % gsa_module, e)

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

    def fetch(self, url, output_path, **kwargs):
        success = False
        output_path = ensure_valid_output_path(url, output_path)

        self.import_gcs()
        try:
            credentials = self.get_credentials(url) or {}
            project_id = credentials.get("project_id") or self.config.get("default_project_id") or None
            service_account_creds_file = credentials.get("service_account_credentials_file")
            storage_credentials = GSA.Credentials.from_service_account_file(service_account_creds_file) \
                if (service_account_creds_file and os.path.isfile(service_account_creds_file)) else None
            try:
                gcs_client = GCS.Client(project=project_id, credentials=storage_credentials)
            except Exception as e:
                raise RuntimeError("Unable to create GCS storage client: %s" % get_typed_exception(e))

            upr = urlsplit(url, allow_fragments=False)
            allow_requester_pays = credentials.get("allow_requester_pays", False)
            bucket = gcs_client.bucket(upr.netloc, user_project=project_id if allow_requester_pays else None)
            logger.info("Attempting GET from URL: %s with project_id=%s and allow_requester_pays=%s%s" %
                        (url, project_id, allow_requester_pays,
                         ". Using service account credentials from file %s" % service_account_creds_file if
                         service_account_creds_file else ""))
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
