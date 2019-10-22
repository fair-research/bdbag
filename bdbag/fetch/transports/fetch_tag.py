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
import logging
from bdbag.fetch.transports.base_transport import BaseFetchTransport

logger = logging.getLogger(__name__)


class TAGFetchTransport(BaseFetchTransport):

    def __init__(self, config, keychain, **kwargs):
        super(TAGFetchTransport, self).__init__(config, keychain, **kwargs)

    @staticmethod
    def fetch(url, output_path, **kwargs):
        logger.info("The fetch entry for file %s specifies the tag URI %s. Tag URIs may represent objects that "
                    "cannot be directly resolved as network resources and therefore cannot be automatically fetched. "
                    "Such files must be acquired outside of the context of this software." % (output_path, url))
        return output_path

    def cleanup(self):  # pragma: no cover
        pass
