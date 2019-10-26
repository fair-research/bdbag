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
import os
import datetime
import logging
from collections import namedtuple
from bdbag import urlsplit, urlunquote, filter_dict
from bdbag.bdbag_config import read_config, DEFAULT_CONFIG, DEFAULT_CONFIG_FILE, DEFAULT_KEYCHAIN_FILE, \
    FETCH_CONFIG_TAG, DEFAULT_FETCH_CONFIG, RESOLVER_CONFIG_TAG, DEFAULT_RESOLVER_CONFIG
from bdbag.fetch.auth.keychain import read_keychain, DEFAULT_KEYCHAIN_FILE
from bdbag.fetch.auth.cookies import get_request_cookies
from bdbag.fetch.resolvers import resolve
from bdbag.fetch.transports import find_fetcher
from bdbag.fetch.transports.base_transport import BaseFetchTransport

logger = logging.getLogger(__name__)

UNIMPLEMENTED = "Transfer protocol \"%s\" is not supported."

FetchEntry = namedtuple("FetchEntry", ["url", "length", "filename"])


def fetch_bag_files(bag,
                    keychain_file=DEFAULT_KEYCHAIN_FILE,
                    config_file=None,
                    force=False,
                    callback=None,
                    filter_expr=None,
                    **kwargs):

    keychain = read_keychain(keychain_file)
    config = read_config(config_file)
    fetchers = kwargs.get("fetchers") or dict()
    success = True
    current = 0
    total = 0 if not callback else len(set(bag.files_to_be_fetched()))
    start = datetime.datetime.now()

    for entry in map(FetchEntry._make, bag.fetch_entries()):
        filename = urlunquote(entry.filename)
        if filter_expr:
            if not filter_dict(filter_expr, entry._asdict()):
                continue
        output_path = os.path.normpath(os.path.join(bag.path, filename))
        local_size = os.path.getsize(output_path) if os.path.exists(output_path) else None
        try:
            remote_size = int(entry.length)
        except ValueError:
            remote_size = None
        missing = True
        if local_size is not None:
            if local_size == remote_size or remote_size is None:
                missing = False

        if not force and not missing:
            logger.debug("Not fetching already present file: %s" % output_path)
        else:
            result_path = fetch_file(entry.url, output_path, config, keychain, fetchers, size=remote_size, **kwargs)
            if not result_path:
                success = False

        if callback:
            current += 1
            if not callback(current, total):
                logger.warning("Fetch cancelled by user...")
                success = False
                break
    elapsed = datetime.datetime.now() - start
    logger.info("Fetch complete. Elapsed time: %s" % elapsed)
    cleanup_fetchers(fetchers)
    return success


def fetch_single_file(url,
                      output_path=None,
                      config_file=None,
                      keychain_file=DEFAULT_KEYCHAIN_FILE,
                      **kwargs):

    keychain = read_keychain(keychain_file)
    config = read_config(config_file)
    fetchers = kwargs.get("fetchers") or dict()
    result_path = fetch_file(url, output_path, config, keychain, fetchers, **kwargs)
    cleanup_fetchers(fetchers)

    return result_path


def fetch_file(url, output_path, config, keychain, fetchers, **kwargs):
    scheme = urlsplit(url).scheme.lower()
    fetch_config = config.get(FETCH_CONFIG_TAG) or DEFAULT_FETCH_CONFIG
    fetcher = fetchers.get(scheme)
    if not fetcher:
        fetcher = find_fetcher(scheme, fetch_config, keychain, **kwargs)
        if fetcher:
            fetchers[scheme] = fetcher
    if fetcher:
        return fetcher.fetch(url, output_path, **kwargs)

    # if we get here, assume the url contains an identifier scheme and try to resolve it as such
    resolver_config = config.get(RESOLVER_CONFIG_TAG, DEFAULT_RESOLVER_CONFIG) if config else DEFAULT_RESOLVER_CONFIG
    supported_resolvers = resolver_config.keys()
    if scheme in supported_resolvers:
        for entry in resolve(url, resolver_config):
            url = entry.get("url")
            if url:
                result_path = fetch_file(url, output_path, config, keychain, fetchers, **kwargs)
                if result_path:
                    return result_path
        return None

    logger.warning(UNIMPLEMENTED % scheme)
    return None


def cleanup_fetchers(fetchers):
    for fetcher in fetchers.values():
        if isinstance(fetcher, BaseFetchTransport):
            fetcher.cleanup()
