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
import json
import logging
import requests
from collections import OrderedDict
from bdbag import urlsplit, get_typed_exception
from bdbag.fetch.resolvers.base_resolver import BaseResolverHandler

logger = logging.getLogger(__name__)


class DataGUIDResolverHandler(BaseResolverHandler):

    def __init__(self, identifier_resolvers, args):
        super(DataGUIDResolverHandler, self).__init__(identifier_resolvers, args)

    def resolve(self, identifier, headers=None):
        if not headers:
            headers = {'Accept': 'application/json', 'Connection': 'close'}
        return super(DataGUIDResolverHandler, self).resolve(identifier, headers)

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
        data_object = content.get("data_object", {})
        length = data_object.get("size")
        if length:
            base_entry["length"] = length
        checksums = data_object.get("checksums", [])
        for checksum in checksums:
            base_entry[checksum["type"]] = checksum["checksum"]
        locations = data_object.get('urls', [])
        for location in locations:
            url = location.get("url")
            if url:
                entry = dict(base_entry)
                entry["url"] = url
                entries.append(entry)

        return entries
