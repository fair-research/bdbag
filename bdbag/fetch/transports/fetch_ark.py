import sys
import json
import logging
import requests
import bdbag
from collections import OrderedDict

if sys.version_info > (3,):
    from urllib.parse import urlsplit
else:
    from urlparse import urlsplit

logger = logging.getLogger(__name__)

RESOLVER_URL = "http://n2t.net"


def resolve(ark):

    if ark is None:
        return None

    urls = []
    resolver_url = ''.join((RESOLVER_URL, '/', ark))
    logger.info("Attempting to resolve %s into a valid set of URLs." % ark)
    r = requests.get(resolver_url, headers={'accept': 'application/json', 'Connection': 'keep-alive'})
    if r.status_code != 200:
        logger.error('HTTP GET Failed for: %s' % r.url)
        logger.error("Host %s responded:\n\n%s" % (urlsplit(r.url).netloc, r.text))
    else:
        info = {}
        try:
            info = json.loads(r.text, object_pairs_hook=OrderedDict)
        except Exception as e:
            logger.warning("Unable to parse ARK resolution result, a MINID or other supported JSON metadata structure "
                           "was not found. Exception: %s" % bdbag.get_typed_exception(e))
        # need a better way to validate minid response structure
        locations = info.get('locations', list())
        for location in locations:
            uri = location.get('uri', None)
            if uri:
                urls.append(uri)

    if urls:
        logger.info("The identifier %s resolved into the following locations: %s" % (ark, urls))
    else:
        logger.warning("No file locations were found for identifier %s" % ark)

    return urls

