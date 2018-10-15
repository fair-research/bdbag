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
import sys
import logging
from importlib import import_module
from bdbag import urlsplit, get_typed_exception
from bdbag.bdbag_config import DEFAULT_RESOLVER_CONFIG, DEFAULT_ID_RESOLVERS, ID_RESOLVER_TAG

logger = logging.getLogger(__name__)


def find_resolver(identifier, resolver_config):

    upr = urlsplit(identifier, allow_fragments=True)
    scheme = upr.scheme.lower()
    path = upr.path

    resolver = None
    resolvers = resolver_config.get(scheme, [])
    for resolver in resolvers:
        prefix = resolver.get("prefix")
        if prefix and prefix in path.lstrip("/"):
            break

    if not resolver:
        raise RuntimeError("Unable to locate resolver for identifier scheme: %s" % scheme)

    resolver_args = resolver.get("args", {})
    resolver_class = resolver.get("handler")
    if not resolver_class:
        resolver_class = "bdbag.fetch.resolvers.base_resolver.BaseResolverHandler"
        resolver_args.update({"simple": True})

    clazz = None
    try:
        module_name, class_name = resolver_class.rsplit(".", 1)
        try:
            module = sys.modules[module_name]
        except KeyError:
            module = import_module(module_name)
        clazz = getattr(module, class_name) if module else None
    except (ImportError, AttributeError):
        pass
    if not clazz:
        raise RuntimeError("Unable to import specified resolver class %s" % resolver_class)

    return clazz(resolver.get(ID_RESOLVER_TAG, DEFAULT_ID_RESOLVERS), resolver_args)


def resolve(identifier, resolver_config=DEFAULT_RESOLVER_CONFIG):
    try:
        resolver = find_resolver(identifier, resolver_config)
    except Exception as e:
        logger.error(get_typed_exception(e))
        return []

    return resolver.resolve(identifier)
