import json
import logging
import requests
from bdbag import urlsplit, get_typed_exception, DEFAULT_ID_RESOLVERS
from collections import OrderedDict

logger = logging.getLogger(__name__)


def resolve(identifier, resolvers=DEFAULT_ID_RESOLVERS):
    urls = []
    if identifier is None:
        return urls

    for resolver in resolvers:
        resolver_scheme = "http://" if not (resolver.startswith("http://") or resolver.startswith("https://")) else ''
        resolver_url = ''.join((resolver_scheme, resolver, '/', identifier))
        logger.info("Attempting to resolve %s into a valid set of URLs." % identifier)
        r = requests.get(resolver_url, headers={'accept': 'application/json', 'Connection': 'keep-alive'})
        if r.status_code != 200:
            logger.error('HTTP GET Failed for: %s' % r.url)
            logger.error("Host %s responded:\n\n%s" % (urlsplit(r.url).netloc, r.text))
            continue
        else:
            info = {}
            try:
                info = json.loads(r.text, object_pairs_hook=OrderedDict)
            except Exception as e:
                logger.warning("Unable to parse identifier resolution result, a MINID or other supported JSON metadata "
                               "structure was not found. Exception: %s" % get_typed_exception(e))
            # need a better way to validate minid response structure
            locations = info.get('locations', list())
            for location in locations:
                uri = location.get('uri', None)
                if uri:
                    urls.append(uri)

        if urls:
            logger.info("The identifier %s resolved into the following locations: %s" % (identifier, urls))
        else:
            logger.warning("No file locations were found for identifier %s" % identifier)

        return urls

