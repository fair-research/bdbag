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
import datetime
from collections import namedtuple
from bdbag import urlsplit, filter_dict
from bdbag.bdbag_config import *
from bdbag.fetch.transports import *
from bdbag.fetch.auth.keychain import *
from bdbag.fetch.auth.cookies import *
from bdbag.fetch.resolvers import resolve

logger = logging.getLogger(__name__)

UNIMPLEMENTED = "Transfer protocol \"%s\" is not supported by this implementation"

SCHEME_HTTP = 'http'
SCHEME_HTTPS = 'https'
SCHEME_S3 = 's3'
SCHEME_GS = 'gs'
SCHEME_GLOBUS = 'globus'
SCHEME_FTP = 'ftp'
SCHEME_SFTP = 'sftp'
SCHEME_TAG = 'tag'

FetchEntry = namedtuple("FetchEntry", ["url", "length", "filename"])


def fetch_bag_files(bag,
                    keychain_file=DEFAULT_KEYCHAIN_FILE,
                    config_file=DEFAULT_CONFIG_FILE,
                    force=False,
                    callback=None,
                    filter_expr=None,
                    **kwargs):

    auth = read_keychain(keychain_file)
    config = read_config(config_file)
    cookies = get_request_cookies(config) if kwargs.get("cookie_scan", True) else None

    success = True
    current = 0
    total = 0 if not callback else len(set(bag.files_to_be_fetched()))
    start = datetime.datetime.now()
    for entry in map(FetchEntry._make, bag.fetch_entries()):
        if filter_expr:
            if not filter_dict(filter_expr, entry._asdict()):
                continue
        output_path = os.path.normpath(os.path.join(bag.path, entry.filename))
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
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug("Not fetching already present file: %s" % output_path)
            pass
        else:
            result_path = fetch_file(entry.url,
                                     output_path,
                                     auth,
                                     size=entry.length,
                                     config=config,
                                     cookies=cookies,
                                     **kwargs)
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
    cleanup_transports()
    return success


def fetch_file(url, path, auth, **kwargs):

    scheme = urlsplit(url).scheme.lower()
    if SCHEME_HTTP == scheme or SCHEME_HTTPS == scheme:
        return fetch_http.get_file(url, path, auth, **kwargs)
    if SCHEME_FTP == scheme:
        return fetch_ftp.get_file(url, path, auth, **kwargs)
    if SCHEME_S3 == scheme or SCHEME_GS == scheme:
        return fetch_boto3.get_file(url, path, auth, **kwargs)
    if SCHEME_GLOBUS == scheme:
        return fetch_globus.get_file(url, path, auth, **kwargs)
    if SCHEME_TAG == scheme:  # pragma: no cover
        logger.info("The fetch entry for file %s specifies the tag URI %s. Tag URIs may represent objects that "
                    "cannot be directly resolved as network resources and therefore cannot be automatically fetched. "
                    "Such files must be acquired outside of the context of this software." % (path, url))
        return path

    # if we get here, assume the url is an identifier and try to resolve it
    config = kwargs.get("config")
    resolver_config = config.get(RESOLVER_CONFIG_TAG, DEFAULT_RESOLVER_CONFIG) if config else DEFAULT_RESOLVER_CONFIG
    supported_resolvers = resolver_config.keys()
    if scheme in supported_resolvers:
        for entry in resolve(url, resolver_config):
            url = entry.get("url")
            if url:
                output_path = fetch_file(url, path, auth, **kwargs)
                if output_path:
                    return output_path
        return None

    logger.warning(UNIMPLEMENTED % scheme)
    return None


def fetch_single_file(url,
                      output_path=None,
                      config_file=DEFAULT_CONFIG_FILE,
                      keychain_file=DEFAULT_KEYCHAIN_FILE,
                      **kwargs):

    auth = read_keychain(keychain_file)
    config = read_config(config_file)
    cookies = get_request_cookies(config) if kwargs.get("cookie_scan", True) else None
    result_path = fetch_file(url, output_path, auth, config=config, cookies=cookies, **kwargs)
    cleanup_transports()

    return result_path


def get_request_cookies(config):
    fetch_config = config.get(FETCH_CONFIG_TAG, DEFAULT_FETCH_CONFIG)
    http_fetch_config = fetch_config.get("http", dict())
    cookie_jar_config = http_fetch_config.get(COOKIE_JAR_TAG, DEFAULT_COOKIE_JAR_SEARCH_CONFIG)
    cookies = load_and_merge_cookie_jars(find_cookie_jars(cookie_jar_config)) if \
        cookie_jar_config.get(COOKIE_JAR_SEARCH_TAG, True) else None
    return cookies


def cleanup_transports():
    fetch_http.cleanup()
    fetch_ftp.cleanup()
