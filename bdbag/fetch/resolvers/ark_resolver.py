import logging
from bdbag import get_typed_exception
from bdbag.fetch.resolvers.base_resolver import BaseResolverHandler

logger = logging.getLogger(__name__)


class MinidResolverHandler(BaseResolverHandler):

    def __init__(self, identifier_resolvers, args):
        super(MinidResolverHandler, self).__init__(identifier_resolvers, args)

    def handle_response(self, response):
        entries = list()
        try:
            content = response.json()
        except Exception as e:
            logger.warning(
                "Unable to parse identifier resolution result, a MINID or other supported JSON metadata "
                "structure was not found. Exception: %s" % get_typed_exception(e))
            return entries

        entry = dict()
        locations = content.get('locations')
        if locations:
            checksum_function = content.get("checksum_function", "sha256")
            checksum = content.get("checksum")
            entry[checksum_function] = checksum
            for location in locations:
                uri = location.get('uri', None)
                if uri:
                    entry["url"] = uri
                    entries.append(entry)
        else:  # newer response format
            length = content.get("contentSize")
            if length:
                entry["length"] = length
            checksums = content.get("checksums", [])
            for checksum in checksums:
                entry[checksum["function"]] = checksum["value"]
            locations = content.get('location')
            if locations:
                for location in locations:
                    entry["url"] = location
                    entries.append(entry)

        return entries
