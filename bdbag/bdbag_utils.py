import base64
import sys
import os
import argparse
import hashlib
import logging
import json
import binascii
from bdbag import bdbag_api as bdb, parse_content_disposition, urlsplit
from bdbag import get_typed_exception as gte
from bdbag.fetch.transports.fetch_http import get_session
from bdbag.fetch.auth.keychain import read_keychain, DEFAULT_KEYCHAIN_FILE

logger = logging.getLogger(__name__)


def create_remote_file_manifest(args):
    with open(args.output_file, 'w') as rfm_file:
        rfm = list()
        for dirpath, dirnames, filenames in os.walk(args.input_path):
            subdirs_count = dirnames.__len__()
            if subdirs_count:
                logger.info("%s subdirectories found in input directory %s %s" %
                            (subdirs_count, args.input_path, dirnames))
            filenames.sort()
            for fn in filenames:
                rfm_entry = dict()
                input_file = os.path.join(dirpath, fn)
                logger.debug("Processing input file %s" % input_file)
                input_rel_path = input_file.replace(args.input_path, '')
                filepath = args.base_payload_path if args.base_payload_path else ""
                filepath = "".join([filepath, input_rel_path])
                rfm_entry["filename"] = filepath.replace("\\", "/").lstrip("/")
                rfm_entry["url"] = url_format(args.url_formatter,
                                              base_url=args.base_url,
                                              filepath=input_rel_path.replace("\\", "/").lstrip("/"),
                                              filename=fn)
                rfm_entry["length"] = os.path.getsize(input_file)
                rfm_entry.update(calculate_file_hashes(input_file, args.checksum))
                rfm_entry.update({"metadata": {"title": os.path.basename(rfm_entry["filename"])}})
                if args.streaming_json:
                    rfm_file.writelines(''.join([json.dumps(rfm_entry), '\n']))
                else:
                    rfm.append(rfm_entry)
        if not args.streaming_json:
            rfm_file.write(json.dumps(rfm, indent=4))
        logger.info("Successfully created remote file manifest: %s" % args.output_file)


def generate_remote_file_manifest(args):
    keychain_file = args.keychain_file if args.keychain_file else DEFAULT_KEYCHAIN_FILE
    auth = read_keychain(keychain_file)
    with open(args.output_file, 'w') as rfm_file, open(args.input_file, 'r') as input_file:
        rfm = list()
        for url in input_file.readlines():
            rfm_entry = dict()
            logger.debug("Processing input URL %s" % url)
            try:
                headers = headForHeaders(url, auth, raise_for_status=True)
            except Exception as e:
                logging.warning("HEAD request failed for URL [%s]: %s" % (url, gte(e)))
                continue
            length = headers.get("Content-Length")
            content_type = headers.get("Content-Type")
            content_disposition = headers.get("Content-Disposition")
            md5 = headers.get("Content-MD5")
            if md5:
                md5 = decodeBase64toHex(md5)
            sha256 = headers.get("Content-SHA256")
            if sha256:
                sha256 = decodeBase64toHex(sha256)

            # if content length or both hash values are missing, there is a problem
            if not length:
                logging.warning("Could not determine Content-Length for %s" % url)
            if not (md5 or sha256):
                logging.warning("Could not locate an MD5 or SHA256 hash for %s" % url)

            # try to construct filename using content_disposition, if available, else fallback to the URL path fragment
            filepath = urlsplit(url).path
            filename = os.path.basename(filepath).split(":")[0] if not content_disposition else \
                parse_content_disposition(content_disposition)
            subdir = args.base_payload_path if args.base_payload_path else ""
            output_path = ''.join([subdir, os.path.dirname(filepath), "/", filename])

            rfm_entry['url'] = url
            rfm_entry['length'] = length
            rfm_entry['filename'] = output_path
            if md5:
                rfm_entry['md5'] = md5
            if sha256:
                rfm_entry['sha256'] = sha256
            if content_type:
                rfm_entry["content_type"] = content_type
            rfm_entry.update({"metadata": {"title": os.path.basename(rfm_entry["filename"])}})

            if args.streaming_json:
                rfm_file.writelines(''.join([json.dumps(rfm_entry), '\n']))
            else:
                rfm.append(rfm_entry)
        if not args.streaming_json:
            rfm_file.write(json.dumps(rfm, indent=4))
        logger.info("Successfully generated remote file manifest: %s" % args.output_file)


def headForHeaders(url, auth=None, raise_for_status=False):
    session = get_session(url, auth)
    r = session.head(url, headers={'Connection': 'keep-alive'})
    if raise_for_status:
        r.raise_for_status()
    headers = r.headers

    return headers


def url_format(formatter, base_url, filepath=None, filename=None):
    url = None
    urlpath = None
    if formatter == "none":
        return base_url
    elif formatter == "append-path":
        urlpath = "/".join([filepath])
    elif formatter == "append-filename":
        urlpath = "/".join([filename])
    else:
        raise RuntimeError("Unknown URL formatter: %s" % formatter)
    if base_url.endswith("/"):
        url = "".join([base_url, urlpath])
    else:
        url = "/".join([base_url, urlpath])
    return url.replace('\\', '/')


# this function was "borrowed" from bagit-python/bagit.py since it has private scope in that module.
def calculate_file_hashes(full_path, hashes):
    f_hashers = dict()
    for alg in hashes:
        try:
            f_hashers[alg] = hashlib.new(alg)
        except ValueError:
            logger.warning("Unable to validate file contents using unknown %s hash algorithm", alg)

    logger.info("Calculating %s checksum(s) for file %s" % (set(f_hashers.keys()), full_path))
    if not os.path.exists(full_path):
        logger.warning("%s does not exist" % full_path)
        return

    try:
        with open(full_path, 'rb') as f:
            while True:
                block = f.read(1048576)
                if not block:
                    break
                for i in f_hashers.values():
                    i.update(block)
    except (IOError, OSError) as e:
        logger.warning("Could not read %s: %s" % (full_path, str(e)))
        raise

    return dict((alg, h.hexdigest()) for alg, h in f_hashers.items())


def decodeBase64toHex(base64str):
    result = binascii.hexlify(base64.standard_b64decode(base64str))
    if isinstance(result, bytes):
        result = result.decode('ascii')

    return result


def parse_cli():
    description = 'Utility routines for working with BDBags'

    parser = argparse.ArgumentParser(
        description=description, epilog="For more information see: http://github.com/fair-research/bdbag")

    parser.add_argument(
        '--quiet', action="store_true", help="Suppress logging output.")

    parser.add_argument(
        '--debug', action="store_true", help="Enable debug logging output.")

    subparsers = parser.add_subparsers(dest="subparser", help="sub-command help")

    parser_crfm = \
        subparsers.add_parser('create-rfm',
                              description="Create a remote file manifest by recursively scanning a directory.",
                              help='create-rfm help')

    parser_crfm.add_argument(
        'input_path', metavar="<input path>",
        help="Path to a directory tree which will be traversed for input files.")

    parser_crfm.add_argument(
        'output_file', metavar="<output file>",
        help="Path of the filename where the remote file manifest will be written.")

    checksum_arg = "--checksum"
    parser_crfm.add_argument(
        checksum_arg, action='append', required=True, choices=['md5', 'sha1', 'sha256', 'sha512', 'all'],
        help="Checksum algorithm to use: can be specified multiple times with different values. "
             "If \'all\' is specified, every supported checksum will be generated")

    base_payload_path_arg = '--base-payload-path'
    parser_crfm.add_argument(
        base_payload_path_arg, metavar="<url>",
        help="An optional path prefix to prepend to each relative file path found while walking the input directory "
             "tree. All files will be rooted under this base directory path in any bag created from this manifest.")

    base_url_arg = "--base-url"
    parser_crfm.add_argument(
        base_url_arg, metavar="<url>", required=True,
        help="A URL root to prepend to each file listed in the manifest. Can be used to generate fetch URL "
             "fields dynamically.")

#    url_map_arg = parser_crfm.add_argument(
#        '--url-map-file', metavar="<path>",
#        help="Path to a JSON formatted file that maps file relative paths to URLs.")

    url_formatter_arg = "--url-formatter"
    parser_crfm.add_argument(
        url_formatter_arg , choices=['none', 'append-path', 'append-filename'], default='none',
        help="Format function for generating remote file URLs. "
             "If \'append-path\' is specified, the existing relative path including the filename will be appended to"
             " the %s argument. If \'append-path\' is specified, only the filename will be appended. If \"none\" is "
             "specified, the %s argument will be used as-is." %
             (base_url_arg, base_url_arg))

    streaming_json_arg = "--streaming-json"
    parser_crfm.add_argument(
        streaming_json_arg, action='store_true', default=False,
        help=str("If \'streaming-json\' is specified, one JSON tuple object per line will be output to the output file."
                 "Enable this option if the default behavior produces a file that is prohibitively large to parse "
                 "entirely into system memory."))

    parser_crfm.set_defaults(func=create_remote_file_manifest)

    parser_grfm = \
        subparsers.add_parser('generate-rfm',
                              description="Generate a remote file manifest by from a list of HTTP(S) URLs by issuing "
                                          "HTTP HEAD requests for Content-Length, Content-Disposition, and Content-MD5 "
                                          "headers for each URL",
                              help='generate-rfm help')

    parser_grfm.add_argument(
        'input_file', metavar="<input file>",
        help="Path to a newline delimited list of URLs that will be used to generate the remote file manifest.")

    parser_grfm.add_argument(
        'output_file', metavar="<output file>",
        help="Path of the filename where the remote file manifest will be written.")

    parser_grfm.add_argument(
        '--keychain-file', default=DEFAULT_KEYCHAIN_FILE, metavar='<file>',
        help="Optional path to a keychain file. If this argument is not specified, the keychain file "
             "defaults to: %s " % DEFAULT_KEYCHAIN_FILE)

    grfm_base_payload_path_arg = "--base-payload-path"
    parser_grfm.add_argument(
        grfm_base_payload_path_arg, metavar="<url>",
        help="An optional path prefix to prepend to each relative file path found while querying each URL for metadata."
             " All files will be rooted under this base directory path in any bag created from this manifest.")

#    grfm_url_map_arg = "--url-map-file"
#     parser_grfm.add_argument(
#        grfm_url_map_arg, metavar="<path>",
#        help="Path to a JSON formatted file that maps file relative paths to URLs.")

    preserve_url_path_arg = "--preserve-url-path"
    parser_grfm.add_argument(
        preserve_url_path_arg, default=False, action="store_true",
        help="Preserve the URL file path in the local payload.")

    grfm_streaming_json_arg = "--streaming-json"
    parser_grfm.add_argument(
        grfm_streaming_json_arg, action='store_true', default=False,
        help=str("If \'streaming-json\' is specified, one JSON tuple object per line will be output to the output file."
                 "Enable this option if the default behavior produces a file that is prohibitively large to parse "
                 "entirely into system memory."))

    parser_grfm.set_defaults(func=generate_remote_file_manifest)

    args = parser.parse_args()

    bdb.configure_logging(level=logging.ERROR if args.quiet else (logging.DEBUG if args.debug else logging.INFO))

    return args, parser


def main():

    args, parser = parse_cli()
    error = None
    result = 0

    if not args.quiet:
        sys.stderr.write('\n')

    try:
        if args.subparser is None:
            parser.print_usage()
        else:
            args.func(args)
    except Exception as e:
        result = 1
        error = "Error: %s" % gte(e)

    finally:
        if result != 0:
            sys.stderr.write("\n%s" % error)

    if not args.quiet:
        sys.stderr.write('\n')

    return result


if __name__ == '__main__':
    sys.exit(main())


