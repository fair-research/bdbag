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
from bdbag import get_typed_exception
from bdbag.fetch.resolvers.base_resolver import BaseResolverHandler
from bagit import CHECKSUM_ALGOS

logger = logging.getLogger(__name__)


class DOIResolverHandler(BaseResolverHandler):

    def __init__(self, identifier_resolvers, args):
        super(DOIResolverHandler, self).__init__(identifier_resolvers, args)

    def resolve(self, identifier, headers=None):
        if not headers:
            headers = {'Accept': 'application/json', 'Connection': 'close'}
        return super(DOIResolverHandler, self).resolve(identifier, headers)

    def handle_response(self, response):
        entries = list()
        try:
            content = response.json()
        except Exception as e:
            logger.warning(
                "Unable to parse identifier resolution result, a supported JSON metadata "
                "structure was not found. Exception: %s" % get_typed_exception(e))
            return entries

        base_entry = dict()
        locations = content.get('contentUrl')
        if locations:
            length = content.get("contentSize")
            if length:
                base_entry["length"] = length
            identifier_props = content.get("identifier", [])
            for prop in identifier_props:
                name = prop.get("propertyID")
                value = prop.get("value")
                if name and value:
                    name = name.replace('-', '')
                    if name.lower() in CHECKSUM_ALGOS:
                        base_entry[name] = value
            if isinstance(locations, str):
                entry = dict(base_entry)
                entry["url"] = locations
                entries.append(entry)
            else:
                for location in locations:
                    entry = dict(base_entry)
                    entry["url"] = location
                    entries.append(entry)

        return entries

