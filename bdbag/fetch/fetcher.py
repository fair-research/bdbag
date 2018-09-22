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


def fetch_bag_files(bag, keychain_file, force=False, callback=None, config=DEFAULT_CONFIG, filter_expr=None, **kwargs):

    success = True
    auth = read_keychain(keychain_file)
    resolver_config = config.get(RESOLVER_CONFIG_TAG, DEFAULT_RESOLVER_CONFIG) if config else DEFAULT_RESOLVER_CONFIG
    cookies = load_and_merge_cookie_jars(find_cookie_jars(
        config.get(COOKIE_JAR_TAG, DEFAULT_CONFIG[COOKIE_JAR_TAG]))) if kwargs.get("cookie_scan", True) else None
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
            success = fetch_file(entry.url,
                                 entry.length,
                                 output_path,
                                 auth,
                                 config = config,
                                 resolver_config=resolver_config,
                                 cookies=cookies,
                                 **kwargs)
        if callback:
            current += 1
            if not callback(current, total):
                logger.warning("Fetch cancelled by user...")
                break
    elapsed = datetime.datetime.now() - start
    logger.info("Fetch complete. Elapsed time: %s" % elapsed)
    cleanup_transports()
    return success


def fetch_file(url, size, path, auth, **kwargs):

    scheme = urlsplit(url, allow_fragments=True).scheme.lower()
    if SCHEME_HTTP == scheme or SCHEME_HTTPS == scheme:
        return fetch_http.get_file(url, path, auth, **kwargs)
    if SCHEME_FTP == scheme:
        return fetch_ftp.get_file(url, path, auth, **kwargs)
    if SCHEME_S3 == scheme or SCHEME_GS == scheme:
        return fetch_boto3.get_file(url, path, auth, **kwargs)
    if SCHEME_GLOBUS == scheme:
        return fetch_globus.get_file(url, path, auth, **kwargs)
    if SCHEME_TAG == scheme:
        logger.info("The fetch entry for file %s specifies the tag URI %s. Tag URIs may represent objects that "
                    "cannot be directly resolved as network resources and therefore cannot be automatically fetched. "
                    "Such files must be acquired outside of the context of this software." % (path, url))
        return True

    # if we get here, assume the url is an identifier and try to resolve it
    resolver_config = kwargs.get("resolver_config", {})
    supported_resolvers = resolver_config.keys()
    if scheme in supported_resolvers:
        for entry in resolve(url, resolver_config):
            url = entry.get("url")
            if url:
                if fetch_file(url, size, path, auth, **kwargs):
                    return True
        return False

    logger.warning(UNIMPLEMENTED % scheme)
    return False


def cleanup_transports():
    fetch_http.cleanup()
