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
import argparse
import os
import sys
import logging
import bagit
from bdbag import bdbag_api as bdb, inspect_path, get_typed_exception, FILTER_DOCSTRING, VERSION, BAGIT_VERSION
from bdbag.bdbag_config import bootstrap_config, DEFAULT_CONFIG_FILE
from bdbag.fetch import fetcher
from bdbag.fetch.auth.keychain import DEFAULT_KEYCHAIN_FILE

BAG_METADATA = dict()

ASYNC_TRANSFER_VALIDATION_WARNING = \
    "Warning: combining full validation and fetch resolution may result in validation " \
    "errors or other unexpected issues with asynchronous transfers (such as Globus), " \
    "as checksums may be recalculated on files that are currently being written to. " \
    "If the fetch resolution for this bag does not initiate any asynchronous transfers, " \
    "you can safely ignore this warning.\n\n"


class VersionAction(argparse.Action):

    def __init__(self,
                 option_strings,
                 dest=argparse.SUPPRESS,
                 default=argparse.SUPPRESS,
                 help="show program's version number and exit"):
        super(VersionAction, self).__init__(
            option_strings=option_strings,
            dest=dest,
            default=default,
            nargs=0,
            help=help)

    def __call__(self, parser, namespace, values, option_string=None):
        print("BDBag %s (Bagit %s)" % (VERSION, BAGIT_VERSION))
        bootstrap_config()
        parser.exit()


class AddMetadataAction(argparse.Action):

    def __init__(self, option_strings, dest, nargs=None, **kwargs):
        if nargs is not None:
            raise ValueError("nargs not allowed")
        super(AddMetadataAction, self).__init__(option_strings, dest, **kwargs)

    def __call__(self, parser, namespace, values, option_string=None):
        opt = option_string.lstrip('--')
        opt_caps = '-'.join([o.capitalize() for o in opt.split('-')])
        BAG_METADATA[opt_caps] = values


def parse_cli():
    description = 'BDBag utility for working with Bagit/RO archives'

    parser = argparse.ArgumentParser(
        description=description, epilog="For more information see: http://github.com/fair-research/bdbag")

    parser.add_argument('--version', action=VersionAction)

    standard_args = parser.add_argument_group('Bag arguments')

    update_arg = "--update"
    standard_args.add_argument(
        update_arg, action="store_true",
        help="Update an existing bag dir, regenerating manifests and fetch.txt if necessary.")

    revert_arg = "--revert"
    standard_args.add_argument(
        revert_arg, action="store_true",
        help="Revert an existing bag directory back to a normal directory, deleting all bag metadata files. "
             "Payload files in the \'data\' directory will be moved back to the directory root, and the \'data\' "
             "directory will be deleted.")

    archiver_arg = "--archiver"
    standard_args.add_argument(
        archiver_arg, choices=['zip', 'tar', 'tgz'], help="Archive a bag using the specified format.")

    checksum_arg = "--checksum"
    standard_args.add_argument(
        checksum_arg, action='append', choices=['md5', 'sha1', 'sha256', 'sha512', 'all'],
        help="Checksum algorithm to use: can be specified multiple times with different values. "
             "If \'all\' is specified, every supported checksum will be generated")

    skip_manifests_arg = "--skip-manifests"
    standard_args.add_argument(
        skip_manifests_arg, action='store_true',
        help=str("If \'skip-manifests\' is specified in conjunction with %s, only tagfile manifests will be "
                 "regenerated, with payload manifests and fetch.txt (if any) left as is. This argument should be used "
                 "when only bag metadata has changed." % update_arg))

    prune_manifests_arg = "--prune-manifests"
    standard_args.add_argument(
        prune_manifests_arg, action='store_true',
        help="If specified, any existing checksum manifests not explicitly configured via either"
             " the \"checksum\" argument(s) or configuration file will be deleted from the bag during an update.")

    materialize_arg = "--materialize"
    standard_args.add_argument(
        materialize_arg, action="store_true",
        help="Attempt to fully materialize a bag by performing multiple actions depending on the context of the input "
             "<path>. If <path> is a URL or a URI of a resolvable identifier scheme, the file referenced by this value "
             "will first be downloaded to the current directory. Next, if the <path> value (or previously downloaded "
             "file) is a local path to a supported archive format, the archive will be extracted to the current "
             "directory. Then, if the <path> value (or previously extracted file) is a valid bag directory, any remote "
             "file references contained within the bag's \"fetch.txt\" file will attempt to be resolved. Finally, "
             "full validation will be run on the materialized bag. If any one of these steps fail, a non-zero error is "
             "returned.")

    fetch_arg = "--resolve-fetch"
    standard_args.add_argument(
        fetch_arg, "--fetch", choices=['all', 'missing'],
        help="Download remote files listed in the bag's fetch.txt file. "
             "The \"missing\" option only attempts to fetch files that do not "
             "already exist in the bag payload directory. "
             "The \"all\" option causes all fetch files to be re-acquired,"
             " even if they already exist in the bag payload directory.")

    fetch_filter_arg = "--fetch-filter"
    standard_args.add_argument(
        fetch_filter_arg, metavar="<column><operator><value>",
        help="A simple expression of the form <column><operator><value> where: <column> is the name of a column in "
             "the bag's fetch.txt to be filtered on, <operator> is one of the following tokens; %s, and <value> is a "
             "string pattern or integer to be filtered against." % FILTER_DOCSTRING)

    validate_arg = "--validate"
    standard_args.add_argument(
        validate_arg, choices=['fast', 'full', 'structure'],
        help="Validate a bag directory or bag archive. If \"fast\" is specified, Payload-Oxum (if present) will be "
             "used to check that the payload files are present and accounted for. If \"full\" is specified, "
             "all checksums will be regenerated and compared to the corresponding entries in the manifest. " 
             "If \"structure\" is specified, the bag will be checked for structural validity only.")

    validate_profile_arg = "--validate-profile"
    standard_args.add_argument(
        validate_profile_arg, action="store_true",
        help="Validate a bag against the profile specified by the bag's "
             "\"BagIt-Profile-Identifier\" metadata field, if present.")

    config_file_arg = "--config-file"
    standard_args.add_argument(
        config_file_arg, default=DEFAULT_CONFIG_FILE, metavar='<file>',
        help="Optional path to a configuration file. If this argument is not specified, the configuration file "
             "defaults to: %s " % DEFAULT_CONFIG_FILE)

    keychain_file_arg = "--keychain-file"
    standard_args.add_argument(
        keychain_file_arg, default=DEFAULT_KEYCHAIN_FILE, metavar='<file>',
        help="Optional path to a keychain file. If this argument is not specified, the keychain file "
             "defaults to: %s " % DEFAULT_KEYCHAIN_FILE)

    metadata_file_arg = "--metadata-file"
    standard_args.add_argument(
        metadata_file_arg, metavar='<file>', help="Optional path to a JSON formatted metadata file")

    ro_metadata_file_arg = "--ro-metadata-file"
    standard_args.add_argument(
        ro_metadata_file_arg, metavar='<file>', help="Optional path to a JSON formatted RO metadata file")

    ro_manifest_generate_arg = "--ro-manifest-generate"
    standard_args.add_argument(
        ro_manifest_generate_arg, choices=['overwrite', 'update'],
        help="Automatically generate a basic RO metadata manifest.json file by introspecting a bag's metadata and "
             "structure.")

    remote_file_manifest_arg = "--remote-file-manifest"
    standard_args.add_argument(
        remote_file_manifest_arg, metavar='<file>',
        help="Optional path to a JSON formatted remote file manifest configuration file used to add remote file entries"
             " to the bag manifest(s) and create the bag fetch.txt file.")

    standard_args.add_argument(
        '--quiet', action="store_true", help="Suppress logging output.")

    standard_args.add_argument(
        '--debug', action="store_true", help="Enable debug logging output.")

    standard_args.add_argument(
        'path', metavar="<path>", help="Path to a bag directory or bag archive file.")

    metadata_args = parser.add_argument_group('Bag metadata arguments')
    headers = list(bagit.STANDARD_BAG_INFO_HEADERS)
    headers.append("Contact-Orcid")
    for header in sorted(headers):
        metadata_args.add_argument('--%s' % header.lower(), action=AddMetadataAction)

    args = parser.parse_args()

    bdb.configure_logging(level=logging.ERROR if args.quiet else (logging.DEBUG if args.debug else logging.INFO))

    is_file, is_dir, is_uri = inspect_path(args.path)
    if not is_file and not is_dir and not is_uri:
        sys.stderr.write("Error: file or directory not found: %s\n\n" % args.path)
        sys.exit(2)
    elif is_uri:
        path = args.path
    else:
        path = os.path.abspath(args.path)

    if args.archiver and not is_dir:
        sys.stderr.write("Error: A bag archive can only be created on directories.\n\n")
        sys.exit(2)

    if args.checksum and not is_dir:
        sys.stderr.write("Error: A checksum manifest can only be added to a bag directory.\n\n")
        sys.exit(2)

    if args.update and not is_dir:
        sys.stderr.write("Error: Only existing bag directories can be updated.\n\n")
        sys.exit(2)

    if args.revert and not is_dir:
        sys.stderr.write("Error: Only existing bag directories can be reverted.\n\n")
        sys.exit(2)

    if args.fetch_filter and not args.resolve_fetch:
        sys.stderr.write("Error: The %s argument can only be used with the %s argument.\n\n" %
                         (fetch_filter_arg, fetch_arg))
        sys.exit(2)

    if args.resolve_fetch and not is_dir:
        sys.stderr.write("Error: Resolving remote files using %s can only target bag directories.\n\n" %
                         fetch_arg)
        sys.exit(2)

    if args.update and args.resolve_fetch:
        sys.stderr.write("Error: The %s argument is not compatible with the %s argument.\n\n" %
                         (update_arg, fetch_arg))
        sys.exit(2)

    if args.remote_file_manifest and args.resolve_fetch:
        sys.stderr.write("Error: The %s argument is not compatible with the %s argument.\n\n" %
                         (remote_file_manifest_arg, fetch_arg))
        sys.exit(2)

    is_bag = bdb.is_bag(path)
    if args.checksum and not args.update and is_bag:
        sys.stderr.write("Error: Specifying %s for an existing bag requires the %s argument in order "
                         "to apply any changes.\n\n" % (checksum_arg, update_arg))
        sys.exit(2)

    if args.remote_file_manifest and not args.update and is_bag:
        sys.stderr.write("Error: Specifying %s for an existing bag requires the %s argument in order "
                         "to apply any changes.\n\n" % (remote_file_manifest_arg, update_arg))
        sys.exit(2)

    if args.metadata_file and not args.update and is_bag:
        sys.stderr.write("Error: Specifying %s for an existing bag requires the %s argument in order "
                         "to apply any changes.\n\n" % (metadata_file_arg, update_arg))
        sys.exit(2)

    if args.ro_metadata_file and not args.update and is_bag:
        sys.stderr.write("Error: Specifying %s for an existing bag requires the %s argument in order "
                         "to apply any changes.\n\n" % (ro_metadata_file_arg, update_arg))
        sys.exit(2)

    if args.prune_manifests and not args.update and is_bag:
        sys.stderr.write("Error: Specifying %s for an existing bag requires the %s argument in order "
                         "to apply any changes.\n\n" % (prune_manifests_arg, update_arg))
        sys.exit(2)

    if args.skip_manifests and not args.update and is_bag:
        sys.stderr.write("Error: Specifying %s requires the %s argument.\n\n" %
                         (skip_manifests_arg, update_arg))
        sys.exit(2)

    if BAG_METADATA and not args.update and is_bag:
        sys.stderr.write("Error: Adding or modifying metadata %s for an existing bag requires the %s argument "
                         "in order to apply any changes.\n\n" % (BAG_METADATA, update_arg))
        sys.exit(2)

    if args.revert and not is_bag:
        sys.stderr.write("Error: The directory %s is not a bag and therefore cannot be reverted.\n\n" % path)
        sys.exit(2)

    if args.revert and args.update and is_bag:
        sys.stderr.write("Error: The %s argument is not compatible with the %s argument.\n\n" %
                         (revert_arg, update_arg))
        sys.exit(2)

    return args, path, is_bag, is_file, is_uri


def main():

    args, path, is_bag, is_file, is_uri = parse_cli()

    archive = None
    temp_path = None
    error = None
    result = 0

    if not args.quiet:
        sys.stdout.write('\n')

    try:
        if args.materialize:
            bdb.materialize(path,
                            output_path=None,
                            fetch_callback=None,
                            validation_callback=None,
                            keychain_file=args.keychain_file,
                            config_file=args.config_file,
                            filter_expr=args.fetch_filter)
            return result

        if is_uri:
            # Try to resolve/download the bag
            fetcher.fetch_single_file(path,
                                      config_file=args.config_file,
                                      keychain_file=args.keychain_file)
            if not args.quiet:
                sys.stdout.write('\n')
            return result

        if not is_file:
            # do not try to create or update the bag if the user just wants to validate or complete an existing bag
            if not ((args.validate or args.validate_profile or args.resolve_fetch) and
                    not (args.update and bdb.is_bag(path))):
                if args.checksum and 'all' in args.checksum:
                    args.checksum = ['md5', 'sha1', 'sha256', 'sha512']
                # create or update the bag depending on the input arguments
                bdb.make_bag(path,
                             algs=args.checksum,
                             update=args.update,
                             save_manifests=not args.skip_manifests,
                             prune_manifests=args.prune_manifests,
                             metadata=BAG_METADATA if BAG_METADATA else None,
                             metadata_file=args.metadata_file,
                             remote_file_manifest=args.remote_file_manifest,
                             config_file=args.config_file,
                             ro_metadata_file=args.ro_metadata_file)

        # otherwise just extract the bag if it is an archive and no other conflicting options specified
        elif not (args.validate or args.validate_profile or args.resolve_fetch):
            bdb.extract_bag(path)
            if not args.quiet:
                sys.stdout.write('\n')
            return result

        if args.ro_manifest_generate:
            bdb.generate_ro_manifest(path, True if args.ro_manifest_generate == "overwrite" else False,
                                     config_file=args.config_file)

        if args.resolve_fetch:
            if args.validate == 'full':
                sys.stderr.write(ASYNC_TRANSFER_VALIDATION_WARNING)
            bdb.resolve_fetch(path,
                              force=True if args.resolve_fetch == 'all' else False,
                              keychain_file=args.keychain_file,
                              config_file=args.config_file,
                              filter_expr=args.fetch_filter)

        if args.validate:
            if is_file:
                temp_path = bdb.extract_bag(path, temp=True)
            if args.validate == 'structure':
                bdb.validate_bag_structure(temp_path if temp_path else path)
            else:
                bdb.validate_bag(temp_path if temp_path else path,
                                 fast=True if args.validate == 'fast' else False,
                                 config_file=args.config_file)

        if args.archiver:
            archive = bdb.archive_bag(path, args.archiver)

        if archive is None and is_file:
            archive = path

        if args.validate_profile:
            if is_file:
                if not temp_path:
                    temp_path = bdb.extract_bag(path, temp=True)
            profile = bdb.validate_bag_profile(temp_path if temp_path else path)
            bdb.validate_bag_serialization(archive if archive else path, profile)

        if args.revert:
            bdb.revert_bag(path)

    except Exception as e:
        result = 1
        error = "Error: %s" % get_typed_exception(e)

    finally:
        if temp_path:
            bdb.cleanup_bag(os.path.dirname(temp_path))
        if result != 0:
            sys.stdout.write("\n%s" % error)

    if not args.quiet:
        sys.stdout.write('\n')

    return result


if __name__ == '__main__':
    sys.exit(main())
