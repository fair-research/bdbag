import logging
from bdbag import get_typed_exception
from bdbag.fetch.resolvers.base_resolver import BaseResolverHandler
from bagit import CHECKSUM_ALGOS

logger = logging.getLogger(__name__)


class DOIResolverHandler(BaseResolverHandler):

    def __init__(self, identifier_resolvers, args):
        super(DOIResolverHandler, self).__init__(identifier_resolvers, args)

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
        locations = content.get('contentUrl')
        if locations:
            length = content.get("contentSize")
            if length:
                entry["length"] = length
            identifier_props = content.get("identifier", [])
            for prop in identifier_props:
                name = prop.get("propertyID")
                value = prop.get("value")
                if name and value:
                    name = name.replace('-', '')
                    if name.lower() in CHECKSUM_ALGOS:
                        entry[name] = value
            for location in locations:
                entry["url"] = location
                entries.append(entry)

        return entries

