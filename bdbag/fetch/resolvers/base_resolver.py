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
import requests
from bdbag import urlsplit, stob, get_typed_exception
from bdbag.bdbag_config import DEFAULT_ID_RESOLVERS

logger = logging.getLogger(__name__)


class BaseResolverHandler(object):
    def __init__(self, identifier_resolvers, args):
        self.identifier_resolvers = identifier_resolvers
        self.args = args or dict()

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

        urls = list()
        if stob(self.args.get("simple", False)):
            for identifier_resolver in self.identifier_resolvers:
                urls.append({"url": self.get_resolver_url(identifier, identifier_resolver)})
            return urls

        session = requests.session()
        for resolver in self.identifier_resolvers:
            resolver_url = self.get_resolver_url(identifier, resolver)
            logger.info("Attempting to resolve %s into a valid set of URLs." % resolver_url)
            if not stob(self.args.get("allow_automatic_redirects", True)):
                url = resolver_url
                while True:
                    r = session.head(url, allow_redirects=False)
                    if r.is_redirect:
                        url = r.headers.get("location")
                    else:
                        resolver_url = url
                        break
            r = session.get(resolver_url, headers=headers)
            if r.status_code != 200:
                logger.error('HTTP GET Failed for %s with code: %s' % (resolver_url, r.status_code))
                logger.error("Host %s responded:\n\n%s" % (urlsplit(resolver_url).netloc, r.text))
                continue
            else:
                urls = self.handle_response(r)

            if urls:
                logger.info(
                    "The identifier %s resolved into the following locations: [%s]" %
                    (identifier, ', '.join([url["url"] for url in urls])))
                break
            else:
                logger.warning("No file locations were found for identifier: [%s]" % identifier)

        session.close()
        return urls
