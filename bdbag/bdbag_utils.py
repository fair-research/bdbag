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
import base64
import sys
import os
import argparse
import hashlib
import logging
import json
import binascii
from collections import namedtuple
from csv import DictReader, Sniffer
from bdbag import bdbag_api as bdb, parse_content_disposition, urlsplit, filter_dict, FILTER_DOCSTRING
from bdbag import get_typed_exception as gte
from bdbag.fetch.transports.fetch_http import get_session
from bdbag.fetch.auth.keychain import read_keychain, DEFAULT_KEYCHAIN_FILE

logger = logging.getLogger(__name__)


def create_rfm_from_filesystem(args):
    with open(args.output_file, 'w') as rfm_file:
        rfm = list()
        if not os.path.isdir(args.input_path):
            raise ValueError("The following path does not exist or is not a directory: [%s]" % args.input_path)
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
                rfm_entry.update(compute_file_hashes(input_file, args.checksum))

                if not filter_dict(args.filter, rfm_entry):
                    continue

                if args.streaming_json:
                    rfm_file.writelines(''.join([json.dumps(rfm_entry, sort_keys=True), '\n']))
                else:
                    rfm.append(rfm_entry)
        if not args.streaming_json:
            rfm_file.write(json.dumps(rfm, sort_keys=True, indent=2))
        logger.info("Successfully created remote file manifest: %s" % args.output_file)


def create_rfm_from_url_list(args):
    keychain_file = args.keychain_file if args.keychain_file else DEFAULT_KEYCHAIN_FILE
    auth = read_keychain(keychain_file)
    with open(args.output_file, 'w') as rfm_file, open(args.input_file, 'r') as input_file:
        rfm = list()
        for url in input_file.readlines():
            rfm_entry = dict()
            url = url.strip()
            logger.debug("Processing input URL %s" % url)
            try:
                headers = head_for_headers(url, auth, raise_for_status=True)
            except Exception as e:
                logging.warning("HEAD request failed for URL [%s]: %s" % (url, gte(e)))
                continue
            logger.debug("Result headers: %s" % headers)
            length = headers.get("Content-Length")
            content_type = headers.get("Content-Type")
            content_disposition = headers.get("Content-Disposition")
            md5_header = args.md5_header if args.md5_header else "Content-MD5"
            md5 = headers.get(md5_header)
            md5 = get_checksum_from_string_list("md5", md5)
            if md5 and not args.disable_hash_decode_base64:
                rfm_entry["md5_base64"] = md5
                md5 = decode_base64_to_hex(md5)
                rfm_entry["md5"] = md5
            sha256_header = args.sha256_header if args.sha256_header else "Content-SHA256"
            sha256 = headers.get(sha256_header)
            sha256 = get_checksum_from_string_list("sha256", sha256)
            if sha256 and not args.disable_hash_decode_base64:
                rfm_entry["sha256_base64"] = sha256
                sha256 = decode_base64_to_hex(sha256)
                rfm_entry["sha256"] = sha256

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
            rfm_entry['filename'] = output_path.lstrip("/")
            if content_type:
                rfm_entry["content_type"] = content_type

            if not filter_dict(args.filter, rfm_entry):
                continue

            if args.streaming_json:
                rfm_file.writelines(''.join([json.dumps(rfm_entry, sort_keys=True), '\n']))
            else:
                rfm.append(rfm_entry)
        if not args.streaming_json:
            rfm_file.write(json.dumps(deduplicate_rfm_entries(rfm), sort_keys=True, indent=2))
        logger.info("Successfully created remote file manifest: %s" % args.output_file)


def create_rfm_from_file(args):
    if not (args.md5_col or args.sha1_col or args.sha256_col or args.sha512_col):
        raise ValueError("At least one checksum algorithm column mapping must be specified.")

    with open(args.output_file, 'w') as rfm_file, open(args.input_file, 'r') as input_file:
        rfm = list()
        if not args.input_format == 'json':
            dialect = Sniffer().sniff(input_file.read(4096))
            input_file.seek(0)
            rows = DictReader(input_file, dialect=dialect)
        else:
            rows = json.load(input_file)

        for row in rows:
            if not filter_dict(args.filter, row):
                continue
            rfm_entry = dict()
            rfm_entry["url"] = row[args.url_col]
            rfm_entry["length"] = int(row[args.length_col])
            rfm_entry["filename"] = urlsplit(row[args.filename_col]).path.lstrip("/")
            if args.md5_col:
                rfm_entry["md5"] = row[args.md5_col]
                rfm_entry["md5_base64"] = encode_hex_to_base64(rfm_entry["md5"])
            if args.sha1_col:
                rfm_entry["sha1"] = row[args.sha1_col]
                rfm_entry["sha1_base64"] = encode_hex_to_base64(rfm_entry["sha1"])
            if args.sha256_col:
                rfm_entry["sha256"] = row[args.sha256_col]
                rfm_entry["sha256_base64"] = encode_hex_to_base64(rfm_entry["sha256"])
            if args.sha512_col:
                rfm_entry["sha512"] = row[args.sha512_col]
                rfm_entry["sha512_base64"] = encode_hex_to_base64(rfm_entry["sha512"])
            rfm.append(rfm_entry)

        entries = deduplicate_rfm_entries(rfm)
        logger.info("Writing %d entries to remote file manifest" % len(entries))
        rfm_file.write(json.dumps(entries, sort_keys=True, indent=2))
        logger.info("Successfully created remote file manifest: %s" % args.output_file)


def deduplicate_rfm_entries(rfm):
    if not rfm:
        return rfm

    entry = namedtuple('entry', sorted(rfm[0].keys()))
    unique = set()
    for item in rfm:
        current = entry(**item)
        if current not in unique:
            unique.add(current)
    if len(unique) < len(rfm):
        logger.info("Remove %d duplicate entries from generated remote file manifest." % (len(rfm) - len(unique)))

    del rfm
    result = [d._asdict() for d in unique]
    return result


def head_for_headers(url, auth=None, raise_for_status=False):
    session = get_session(url, auth)
    r = session.head(url, headers={'Connection': 'keep-alive'})
    if raise_for_status:
        r.raise_for_status()
    headers = r.headers

    return headers


def url_format(formatter, base_url, filepath=None, filename=None):
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


def compute_hashes(obj, hashes=frozenset(['md5'])):
    """
       Digests input data read from file-like object fd or passed directly as bytes-like object.
       Compute hashes for multiple algorithms. Default is MD5.
       Returns a tuple of a hex-encoded digest string and a base64-encoded value suitable for an HTTP header.
    """
    if not (hasattr(obj, 'read') or isinstance(obj, bytes)):
        raise ValueError("Cannot compute hash for given input: a file-like object or bytes-like object is required")

    hashers = dict()
    for alg in hashes:
        try:
            hashers[alg] = hashlib.new(alg.lower())
        except ValueError:
            logging.warning("Unable to validate file contents using unknown hash algorithm: %s", alg)

    while True:
        if hasattr(obj, 'read'):
            block = obj.read(1024 ** 2)
        else:
            block = obj
            obj = None
        if not block:
            break
        for i in hashers.values():
            i.update(block)

    hashes = dict()
    for alg, h in hashers.items():
        digest = h.hexdigest()
        base64digest = base64.b64encode(h.digest())
        # base64.b64encode returns str on python 2.7 and bytes on 3.x, so deal with that and always return a str
        if not isinstance(base64digest, str) and isinstance(base64digest, bytes):
            base64digest = base64digest.decode('ascii')
        hashes[alg] = digest
        hashes[alg + "_base64"] = base64digest

    return hashes


def compute_file_hashes(file_path, hashes=frozenset(['md5'])):
    """
       Digests data read from file denoted by file_path.
    """
    if not os.path.exists(file_path):
        logging.warning("%s does not exist" % file_path)
        return
    else:
        logging.debug("Computing [%s] hashes for file [%s]" % (','.join(hashes), file_path))

    try:
        with open(file_path, 'rb') as fd:
            return compute_hashes(fd, hashes)
    except (IOError, OSError) as e:
        logging.warning("Error while calculating digest(s) for file %s: %s" % (file_path, str(e)))
        raise


def decode_base64_to_hex(base64str):
    result = binascii.hexlify(base64.standard_b64decode(base64str))
    if isinstance(result, bytes):
        result = result.decode('ascii')

    return result


def encode_hex_to_base64(hexstr):
    result = binascii.unhexlify(hexstr)
    if isinstance(result, bytes):
        result = base64.standard_b64encode(result)

    if not isinstance(result, str) and isinstance(result, bytes):
        result = result.decode('ascii')

    return result


def get_checksum_from_string_list(alg, input_str, delim=",", sep="="):
    if input_str:
        if delim in input_str:
            checksums = input_str.split(delim)
            for checksum in checksums:
                if checksum.strip().startswith(alg.lower() + sep) or checksum.strip().startswith(alg.upper() + sep):
                    result = checksum.split(sep, 1)[1]
                    return result
    return input_str


def create_crfm_fs_subparser(subparsers):
    parser_crfm_fs = \
        subparsers.add_parser(
            'create-rfm-from-filesystem',
            description="Create a remote file manifest by recursively scanning a directory from a mounted filesystem.",
            help='create-rfm-from-filesystem help')

    parser_crfm_fs.add_argument(
        'input_path', metavar="<input path>",
        help="Path to a directory tree which will be traversed for input files.")

    parser_crfm_fs.add_argument(
        'output_file', metavar="<output file>",
        help="Path of the filename where the remote file manifest will be written.")

    checksum_arg = "--checksum"
    parser_crfm_fs.add_argument(
        checksum_arg, action='append', required=True, choices=['md5', 'sha1', 'sha256', 'sha512', 'all'],
        help="Checksum algorithm to use: can be specified multiple times with different values. "
             "If \'all\' is specified, every supported checksum will be generated")

    base_payload_path_arg = '--base-payload-path'
    parser_crfm_fs.add_argument(
        base_payload_path_arg, metavar="<url>",
        help="An optional path prefix to prepend to each relative file path found while walking the input directory "
             "tree. All files will be rooted under this base directory path in any bag created from this manifest.")

    base_url_arg = "--base-url"
    parser_crfm_fs.add_argument(
        base_url_arg, metavar="<url>", required=True,
        help="A URL root to prepend to each file listed in the manifest. Can be used to generate fetch URL "
             "fields dynamically.")

    crfm_fs_input_filter_arg = "--filter"
    parser_crfm_fs.add_argument(
        crfm_fs_input_filter_arg, metavar="<column><operator><value>",
        help="A simple expression of the form <column><operator><value> where: <column> is the name of a column in "
             "the generated remote file manifest entry to be filtered on, <operator> is one of the following tokens; "
             "%s, and <value> is a string pattern or integer to be filtered against." % FILTER_DOCSTRING)

    url_formatter_arg = "--url-formatter"
    parser_crfm_fs.add_argument(
        url_formatter_arg, choices=['none', 'append-path', 'append-filename'], default='append-path',
        help="Format function for generating remote file URLs. "
             "If \'append-path\' is specified, the existing relative path including the filename will be appended to"
             " the %s argument. If \'append-filename\' is specified, only the filename will be appended. If \"none\" "
             "is specified, the %s argument will be used as-is. The default setting is \"append-path\"" %
             (base_url_arg, base_url_arg))

    streaming_json_arg = "--streaming-json"
    parser_crfm_fs.add_argument(
        streaming_json_arg, action='store_true', default=False,
        help=str("If \'streaming-json\' is specified, one JSON tuple object per line will be output to the output file."
                 "Enable this option if the default behavior produces a file that is prohibitively large to parse "
                 "entirely into system memory."))

    parser_crfm_fs.set_defaults(func=create_rfm_from_filesystem)


def create_crfm_file_subparser(subparsers):
    parser_crfm_file = \
        subparsers.add_parser(
            'create-rfm-from-file',
            description="Create a remote file manifest from a CSV or JSON file with records containing column data "
                        "that can be mapped to the required RFM fields.",
            help='create-rfm-from-file help')

    parser_crfm_file.add_argument(
        'input_file', metavar="<input file>",
        help="Path to a CSV, or JSON input file.")

    parser_crfm_file.add_argument(
        'output_file', metavar="<output file>",
        help="Path of the filename where the remote file manifest will be written.")

    crfm_file_input_format_arg = "--input-format"
    parser_crfm_file.add_argument(
        crfm_file_input_format_arg, choices=['csv', 'json'], default='csv',
        help="The input file format.")

    crfm_file_input_filter_arg = "--filter"
    parser_crfm_file.add_argument(
        crfm_file_input_filter_arg, metavar="<column><operator><value>",
        help="A simple expression of the form <column><operator><value> where: <column> is the name of a column in "
             "the input file to be filtered on, <operator> is one of the following tokes; %s, and <value> is a string "
             "pattern or integer to be filtered against." % FILTER_DOCSTRING)

    crfm_file_input_url_arg = "--url-col"
    parser_crfm_file.add_argument(
        crfm_file_input_url_arg, metavar="<url column>", required=True,
        help="The column or attribute in the input file which will be mapped to the \"url\" attribute of the RFM.")

    crfm_file_input_length_arg = "--length-col"
    parser_crfm_file.add_argument(
        crfm_file_input_length_arg, metavar="<length column>", required=True,
        help="The column or attribute in the input file which will be mapped to the \"length\" attribute of the RFM.")

    crfm_file_input_filename_arg = "--filename-col"
    parser_crfm_file.add_argument(
        crfm_file_input_filename_arg, metavar="<filename column>", required=True,
        help="The column or attribute in the input file which will be mapped to the \"filename\" attribute of the RFM.")

    crfm_file_input_md5_arg = "--md5-col"
    parser_crfm_file.add_argument(
        crfm_file_input_md5_arg, metavar="<md5 column>",
        help="The column or attribute in the input file which will be mapped to the \"md5\" attribute of the RFM.")

    crfm_file_input_sha1_arg = "--sha1-col"
    parser_crfm_file.add_argument(
        crfm_file_input_sha1_arg, metavar="<sha1 column>",
        help="The column or attribute in the input file which will be mapped to the \"sha1\" attribute of the RFM.")

    crfm_file_input_sha256_arg = "--sha256-col"
    parser_crfm_file.add_argument(
        crfm_file_input_sha256_arg, metavar="<sha256 column>",
        help="The column or attribute in the input file which will be mapped to the \"sha256\" attribute of the RFM.")

    crfm_file_input_sha512_arg = "--sha512-col"
    parser_crfm_file.add_argument(
        crfm_file_input_sha512_arg, metavar="<sha512 column>",
        help="The column or attribute in the input file which will be mapped to the \"sha512\" attribute of the RFM.")

    parser_crfm_file.set_defaults(func=create_rfm_from_file)


def create_crfm_urls_subparser(subparsers):
    parser_crfm_urls = \
        subparsers.add_parser(
            'create-rfm-from-url-list',
            description="Create a remote file manifest from a list of HTTP(S) URLs by issuing HTTP HEAD requests "
                        "for the Content-Length, Content-Disposition, and Content-MD5 headers for each URL",
            help='create-rfm-from-url-list help')

    parser_crfm_urls.add_argument(
        'input_file', metavar="<input file>",
        help="Path to a file containing a newline delimited list of URLs used to generate the remote file manifest.")

    parser_crfm_urls.add_argument(
        'output_file', metavar="<output file>",
        help="Path of the filename where the remote file manifest will be written.")

    parser_crfm_urls.add_argument(
        '--keychain-file', default=DEFAULT_KEYCHAIN_FILE, metavar='<file>',
        help="Optional path to a keychain file. If this argument is not specified, the keychain file "
             "defaults to: %s " % DEFAULT_KEYCHAIN_FILE)

    crfm_urls_base_payload_path_arg = "--base-payload-path"
    parser_crfm_urls.add_argument(
        crfm_urls_base_payload_path_arg, metavar="<url>",
        help="An optional path prefix to prepend to each relative file path found while querying each URL for metadata."
             " All files will be rooted under this base directory path in any bag created from this manifest.")

    crfm_urls_md5_header_arg = "--md5-header"
    parser_crfm_urls.add_argument(
        crfm_urls_md5_header_arg, metavar="<md5 header name>", default="Content-MD5",
        help="The name of the response header that contains the MD5 hash value. Defaults to \"Content-MD5\". "
             "Other examples: \"x-amz-meta-md5chksum\" (AWS S3), \"x-goog-hash: md5\" (GCS)")

    crfm_urls_sha256_header_arg = "--sha256-header"
    parser_crfm_urls.add_argument(
        crfm_urls_sha256_header_arg, metavar="<sha256 header name>", default="Content-SHA256",
        help="The name of the response header that contains the SHA256 hash value. Defaults to \"Content-SHA256\". ")

    crfm_urls_input_filter_arg = "--filter"
    parser_crfm_urls.add_argument(
        crfm_urls_input_filter_arg, metavar="<column><operator><value>",
        help="A simple expression of the form <column><operator><value> where: <column> is the name of a header in "
             "the result headers to be filtered on, <operator> is one of the following tokens; %s, and <value> is a "
             "string pattern or integer to be filtered against." % FILTER_DOCSTRING)

    disable_hash_decode_base64_arg = "--disable-hash-decode-base64"
    parser_crfm_urls.add_argument(
        disable_hash_decode_base64_arg, default=False, action="store_true",
        help="Content hashes found in headers are assumed to be base64 encoded. Use this option to disable the "
             "automatic base64 decoding of the hash header and use the return value unchanged.")

    #    crfm_urls_url_map_arg = "--url-map-file"
    #     parser_crfm_urls.add_argument(
    #        crfm_urls_url_map_arg, metavar="<path>",
    #        help="Path to a JSON formatted file that maps file relative paths to URLs.")

    preserve_url_path_arg = "--preserve-url-path"
    parser_crfm_urls.add_argument(
        preserve_url_path_arg, default=False, action="store_true",
        help="Preserve the URL file path in the local payload.")

    crfm_urls_streaming_json_arg = "--streaming-json"
    parser_crfm_urls.add_argument(
        crfm_urls_streaming_json_arg, action='store_true', default=False,
        help=str("If \'streaming-json\' is specified, one JSON tuple object per line will be output to the output file."
                 "Enable this option if the default behavior produces a file that is prohibitively large to parse "
                 "entirely into system memory."))

    parser_crfm_urls.set_defaults(func=create_rfm_from_url_list)


def parse_cli():
    description = 'Utility routines for working with BDBags'

    parser = argparse.ArgumentParser(
        description=description, epilog="For more information see: http://github.com/fair-research/bdbag")

    parser.add_argument(
        '--quiet', action="store_true", help="Suppress logging output.")

    parser.add_argument(
        '--debug', action="store_true", help="Enable debug logging output.")

    subparsers = parser.add_subparsers(dest="subparser", help="sub-command help")
    create_crfm_fs_subparser(subparsers)
    create_crfm_file_subparser(subparsers)
    create_crfm_urls_subparser(subparsers)

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


