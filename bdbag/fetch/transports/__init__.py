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

import sys
import logging
from importlib import import_module

from bdbag import stob
from bdbag.fetch import *
from bdbag.fetch.transports.fetch_http import HTTPFetchTransport
from bdbag.fetch.transports.fetch_ftp import FTPFetchTransport
from bdbag.fetch.transports.fetch_globus import GlobusTransferFetchTransport
from bdbag.fetch.transports.fetch_boto3 import BOTO3FetchTransport
from bdbag.fetch.transports.fetch_gcs import GCSFetchTransport
from bdbag.fetch.transports.fetch_tag import TAGFetchTransport

logger = logging.getLogger(__name__)

DEFAULT_FETCH_TRANSPORTS = {
    SCHEME_HTTP: HTTPFetchTransport,
    SCHEME_HTTPS: HTTPFetchTransport,
    SCHEME_FTP: FTPFetchTransport,
    SCHEME_S3: BOTO3FetchTransport,
    SCHEME_GS: GCSFetchTransport,
    SCHEME_GLOBUS: GlobusTransferFetchTransport,
    SCHEME_TAG: TAGFetchTransport
}

DEFAULT_SUPPORTED_SCHEMES = [DEFAULT_FETCH_TRANSPORTS.keys()]


def find_fetcher(scheme, fetch_config, keychain, **kwargs):
    clazz = None
    config = fetch_config.get(scheme, fetch_config.get(scheme.lower(), fetch_config.get(scheme.upper()))) or {}
    handler = config.get("handler")
    if not handler:
        clazz = DEFAULT_FETCH_TRANSPORTS.get(scheme.lower())
        if not clazz:
            return None

    if not clazz:
        try:
            module_name, class_name = handler.rsplit(".", 1)
            try:
                module = sys.modules[module_name]
            except KeyError:
                module = import_module(module_name)
            clazz = getattr(module, class_name) if module else None
        except (ImportError, AttributeError, ValueError):
            pass
        if not clazz:
            raise RuntimeError("Unable to import specified fetch handler class: [%s]" % handler)

        if not stob(config.get("allow_keychain", False)):
            keychain = None
            logger.debug("Keychain will not be passed to fetch handler class [%s]. Set \"allow_keychain\":\"True\" in "
                         "fetch config to enable keychain propagation." % handler)

    return clazz(config, keychain, **kwargs)

