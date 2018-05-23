import datetime
from bdbag import ID_RESOLVER_TAG, DEFAULT_ID_RESOLVERS, DEFAULT_CONFIG, urlsplit
from bdbag.fetch.transports import *
from bdbag.fetch.auth.keychain import *

logger = logging.getLogger(__name__)

UNIMPLEMENTED = "Transfer protocol \"%s\" is not supported by this implementation"

SCHEME_HTTP = 'http'
SCHEME_HTTPS = 'https'
SCHEME_GLOBUS = 'globus'
SCHEME_FTP = 'ftp'
SCHEME_SFTP = 'sftp'
SCHEME_ARK = 'ark'
SCHEME_MINID = 'minid'
SCHEME_TAG = 'tag'


def fetch_bag_files(bag, keychain_file, force=False, callback=None, config=DEFAULT_CONFIG):

    success = True
    auth = read_keychain(keychain_file)
    resolvers = config.get(ID_RESOLVER_TAG, DEFAULT_ID_RESOLVERS) if config else DEFAULT_ID_RESOLVERS
    current = 0
    total = 0 if not callback else len(set(bag.files_to_be_fetched()))
    start = datetime.datetime.now()
    for url, size, path in bag.fetch_entries():
        output_path = os.path.normpath(os.path.join(bag.path, path))
        local_size = os.path.getsize(output_path) if os.path.exists(output_path) else None
        try:
            remote_size = int(size)
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
            success = fetch_file(url, size, output_path, auth, resolvers=resolvers)
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
        return fetch_http.get_file(url, path, auth)
    if SCHEME_FTP == scheme:
        return fetch_ftp.get_file(url, path, auth)
    elif SCHEME_GLOBUS == scheme:
        return fetch_globus.get_file(url, path, auth)
    elif SCHEME_ARK == scheme or SCHEME_MINID == scheme:
        resolvers = kwargs.get("resolvers")
        for url in fetch_identifier.resolve(url, resolvers):
            if fetch_file(url, size, path, auth):
                return True
        return False
    elif SCHEME_TAG == scheme:
        logger.info("The fetch entry for file %s specifies the tag URI %s. Tag URIs may represent objects that "
                    "cannot be directly resolvable as network resources and therefore cannot be automatically "
                    "fetched. Such files must be acquired outside of the context of this software." % (path, url))
        return True
    else:
        logger.warning(UNIMPLEMENTED % scheme)
        return False


def cleanup_transports():
    fetch_http.cleanup()
