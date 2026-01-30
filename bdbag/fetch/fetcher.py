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
import signal
import datetime
import logging
import threading
import concurrent.futures
from collections import namedtuple
from bdbag import urlsplit, urlunquote, filter_dict
from bdbag.bdbag_config import read_config, DEFAULT_CONFIG, DEFAULT_CONFIG_FILE, DEFAULT_KEYCHAIN_FILE, \
    FETCH_CONFIG_TAG, DEFAULT_FETCH_CONFIG, RESOLVER_CONFIG_TAG, DEFAULT_RESOLVER_CONFIG, \
    FETCH_CONCURRENCY_TAG, DEFAULT_FETCH_CONCURRENCY, \
    FETCH_CONCURRENCY_EXCLUDE_TAG, DEFAULT_FETCH_CONCURRENCY_EXCLUDE
from bdbag.fetch.auth.keychain import read_keychain, DEFAULT_KEYCHAIN_FILE
from bdbag.fetch.auth.cookies import get_request_cookies
from bdbag.fetch.resolvers import resolve
from bdbag.fetch.transports import find_fetcher
from bdbag.fetch.transports.base_transport import BaseFetchTransport

logger = logging.getLogger(__name__)

UNIMPLEMENTED = "Transfer protocol \"%s\" is not supported."

FetchEntry = namedtuple("FetchEntry", ["url", "length", "filename"])

_fetcher_creation_lock = threading.Lock()


def fetch_bag_files(bag,
                    keychain_file=DEFAULT_KEYCHAIN_FILE,
                    config_file=None,
                    force=False,
                    callback=None,
                    filter_expr=None,
                    fetch_concurrency=None,
                    **kwargs):

    keychain = read_keychain(keychain_file)
    config = read_config(config_file)
    fetchers = kwargs.get("fetchers") or dict()
    success = True
    current = 0
    total = 0 if not callback else len(set(bag.files_to_be_fetched()))
    start = datetime.datetime.now()

    # Determine effective concurrency
    max_concurrent = config.get(FETCH_CONCURRENCY_TAG, DEFAULT_FETCH_CONCURRENCY)
    requested = fetch_concurrency if fetch_concurrency else 1
    max_workers = min(requested, max_concurrent)

    # Collect entries to fetch
    entries_to_fetch = []
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
            entries_to_fetch.append((entry, output_path, remote_size))

    # Get the list of schemes excluded from parallel fetching
    exclude_schemes = config.get(FETCH_CONCURRENCY_EXCLUDE_TAG, DEFAULT_FETCH_CONCURRENCY_EXCLUDE)

    interrupted = False
    try:
        if max_workers <= 1:
            # Serial path — original behavior
            for entry, output_path, remote_size in entries_to_fetch:
                result_path = fetch_file(
                    entry.url, output_path, config, keychain, fetchers, size=remote_size, **kwargs)
                if not result_path:
                    success = False

                if callback:
                    current += 1
                    if not callback(current, total):
                        logger.warning("Fetch cancelled by user...")
                        success = False
                        break
        else:
            # Partition entries into serial (excluded schemes) and parallel
            serial_entries = []
            parallel_entries = []
            for item in entries_to_fetch:
                scheme = urlsplit(item[0].url).scheme.lower()
                if scheme in exclude_schemes:
                    serial_entries.append(item)
                else:
                    parallel_entries.append(item)

            # Parallel path
            cancelled = False
            if parallel_entries:
                logger.info("Using concurrent fetching with %d workers" % max_workers)

                # Pre-populate fetchers for known schemes to avoid races
                fetch_config = config.get(FETCH_CONFIG_TAG) or DEFAULT_FETCH_CONFIG
                _prepopulate_fetchers(parallel_entries, fetch_config, keychain, fetchers, **kwargs)

                cancel_event = threading.Event()
                callback_lock = threading.Lock()

                def _do_fetch(entry, output_path, remote_size):
                    if cancel_event.is_set():
                        return None
                    return fetch_file(
                        entry.url, output_path, config, keychain, fetchers, size=remote_size, **kwargs)

                # Install a SIGINT handler that sets the cancel event so worker threads abort promptly
                original_sigint = signal.getsignal(signal.SIGINT)
                sigint_received = threading.Event()

                def _sigint_handler(signum, frame):
                    sigint_received.set()
                    cancel_event.set()
                    logger.warning("Fetch interrupted by user (Ctrl+C)...")

                signal.signal(signal.SIGINT, _sigint_handler)
                try:
                    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
                        future_to_entry = {}
                        for entry, output_path, remote_size in parallel_entries:
                            future = executor.submit(_do_fetch, entry, output_path, remote_size)
                            future_to_entry[future] = (entry, output_path)

                        for future in concurrent.futures.as_completed(future_to_entry):
                            if cancel_event.is_set():
                                # Drain remaining futures without blocking
                                for f in future_to_entry:
                                    f.cancel()
                                success = False
                                cancelled = True
                                break

                            entry, output_path = future_to_entry[future]
                            try:
                                result_path = future.result()
                                if not result_path:
                                    success = False
                            except Exception as e:
                                logger.error("Exception fetching %s: %s" % (output_path, e))
                                success = False

                            if callback:
                                with callback_lock:
                                    current += 1
                                    if not callback(current, total):
                                        logger.warning("Fetch cancelled by user...")
                                        success = False
                                        cancel_event.set()
                                        cancelled = True
                                        for f in future_to_entry:
                                            f.cancel()
                                        break
                finally:
                    signal.signal(signal.SIGINT, original_sigint)
                    if sigint_received.is_set():
                        interrupted = True

            # Serial path for excluded schemes
            if serial_entries and not cancelled:
                if parallel_entries:
                    logger.info(
                        "Fetching %d entries serially (excluded from parallel fetching)" % len(serial_entries))
                for entry, output_path, remote_size in serial_entries:
                    result_path = fetch_file(
                        entry.url, output_path, config, keychain, fetchers, size=remote_size, **kwargs)
                    if not result_path:
                        success = False

                    if callback:
                        current += 1
                        if not callback(current, total):
                            logger.warning("Fetch cancelled by user...")
                            success = False
                            break

    except KeyboardInterrupt:
        logger.warning("Fetch interrupted by user (Ctrl+C)...")
        success = False
        interrupted = True

    elapsed = datetime.datetime.now() - start
    logger.info("Fetch complete. Elapsed time: %s" % elapsed)
    cleanup_fetchers(fetchers)

    if interrupted:
        raise KeyboardInterrupt

    return success


def _prepopulate_fetchers(entries, fetch_config, keychain, fetchers, **kwargs):
    """Pre-create fetcher instances for all schemes in the entry list."""
    schemes = set()
    for entry, _, _ in entries:
        scheme = urlsplit(entry.url).scheme.lower()
        schemes.add(scheme)
    for scheme in schemes:
        if scheme not in fetchers:
            fetcher = find_fetcher(scheme, fetch_config, keychain, **kwargs)
            if fetcher:
                fetchers[scheme] = fetcher


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
        with _fetcher_creation_lock:
            # Double-checked locking
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
