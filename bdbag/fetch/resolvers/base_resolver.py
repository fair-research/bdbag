import logging
import requests
from bdbag import urlsplit, stob, get_typed_exception
from bdbag.bdbag_config import DEFAULT_ID_RESOLVERS

logger = logging.getLogger(__name__)


class BaseResolverHandler(object):
    def __init__(self, identifier_resolvers, args):
        self.identifier_resolvers = identifier_resolvers
        self.args = args

    @staticmethod
    def get_resolver_url(identifier, resolver):
        resolver_scheme = "http://" if not (
                resolver.startswith("http://") or resolver.startswith("https://")) else ''
        return ''.join((resolver_scheme, resolver, '/', identifier))

    @classmethod
    def handle_response(cls, response):
        raise NotImplementedError("Must be implemented by subclass")

    def resolve(self, identifier, headers=None):
        if identifier is None:
            return []

        if stob(self.args.get("simple", False)):
            urls = list()
            for identifier_resolver in self.identifier_resolvers:
                urls.append({"url": self.get_resolver_url(identifier, identifier_resolver)})
            return urls

        session = requests.session()
        if headers:
            session.headers = headers
        for resolver in self.identifier_resolvers:
            resolver_url = self.get_resolver_url(identifier, resolver)
            logger.info("Attempting to resolve %s into a valid set of URLs." % identifier)
            r = session.get(resolver_url)
            if r.status_code != 200:
                logger.error('HTTP GET Failed for %s with code: %s' % (r.url, r.status_code))
                logger.error("Host %s responded:\n\n%s" % (urlsplit(r.url).netloc, r.text))
                continue
            else:
                urls = self.handle_response(r)

            if urls:
                logger.info(
                    "The identifier %s resolved into the following locations: [%s]" %
                    (identifier, ', '.join([url["url"] for url in urls])))
            else:
                logger.warning("No file locations were found for identifier %s" % identifier)

            return urls
