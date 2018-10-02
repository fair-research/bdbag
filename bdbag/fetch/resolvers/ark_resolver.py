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

        base_entry = dict()
        locations = content.get('locations')
        if locations:
            checksum_function = content.get("checksum_function", "sha256")
            checksum = content.get("checksum")
            base_entry[checksum_function] = checksum
            for location in locations:
                uri = location.get('uri', None)
                if uri:
                    entry = dict(base_entry)
                    entry["url"] = uri
                    entries.append(entry)
        else:  # newer response format
            metadata = content.get("metadata", {})
            length = metadata.get("contentSize")
            if length:
                base_entry["length"] = length
            checksums = content.get("checksums", [])
            for checksum in checksums:
                base_entry[checksum["function"]] = checksum["value"]
            locations = content.get('location', [])
            for location in locations:
                entry = dict(base_entry)
                entry["url"] = location
                entries.append(entry)

        return entries
