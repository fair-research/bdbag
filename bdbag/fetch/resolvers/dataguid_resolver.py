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

    def handle_response(self, response):
        entries = list()
        try:
            content = response.json()
        except Exception as e:
            logger.warning(
                "Unable to parse identifier resolution result, a supported JSON metadata "
                "structure was not found. Exception: %s" % get_typed_exception(e))
            return entries

        entry = dict()
        data_object = content.get("data_object", {})
        locations = data_object.get('urls')
        if locations:
            length = data_object.get("size")
            if length:
                entry["length"] = length
            checksums = data_object.get("checksums", [])
            for checksum in checksums:
                entry[checksum["type"]] = checksum["checksum"]
            for location in locations:
                url = location.get("url")
                if url:
                    entry["url"] = url
                    entries.append(entry)

        return entries
