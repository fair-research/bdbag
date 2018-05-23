import argparse
import os
import sys
import logging
import bagit
from bdbag import bdbag_api as bdb, get_typed_exception, DEFAULT_CONFIG_FILE, VERSION
from bdbag.fetch.auth.keychain import DEFAULT_KEYCHAIN_FILE

BAG_METADATA = dict()

ASYNC_TRANSFER_VALIDATION_WARNING = \
    "Warning: combining full validation and fetch resolution may result in validation " \
    "errors or other unexpected issues with asynchronous transfers (such as Globus), " \
    "as checksums may be recalculated on files that are currently being written to. " \
    "If the fetch resolution for this bag does not initiate any asynchronous transfers, " \
    "you can safely ignore this warning.\n\n"


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

    parser.add_argument('--version', action='version', version=VERSION)

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

    fetch_arg = "--resolve-fetch"
    standard_args.add_argument(
        fetch_arg, "--fetch", choices=['all', 'missing'],
        help="Download remote files listed in the bag's fetch.txt file. "
             "The \"missing\" option only attempts to fetch files that do not "
             "already exist in the bag payload directory. "
             "The \"all\" option causes all fetch files to be re-acquired,"
             " even if they already exist in the bag payload directory.")

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

    path = os.path.abspath(args.path)
    if not os.path.exists(path):
        sys.stderr.write("Error: file or directory not found: %s\n\n" % path)
        sys.exit(2)

    is_file = os.path.isfile(path)
    if args.archiver and is_file:
        sys.stderr.write("Error: A bag archive cannot be created from an existing bag archive.\n\n")
        sys.exit(2)

    if args.checksum and is_file:
        sys.stderr.write("Error: A checksum manifest cannot be added to an existing bag archive. "
                         "The bag must be extracted, updated, and re-archived.\n\n")
        sys.exit(2)

    if args.update and is_file:
        sys.stderr.write("Error: An existing bag archive cannot be updated in-place. "
                         "The bag must first be extracted and then updated.\n\n")
        sys.exit(2)

    if args.revert and is_file:
        sys.stderr.write("Error: An existing bag archive cannot be reverted in-place. "
                         "The bag must first be extracted and then reverted.\n\n")
        sys.exit(2)

    if args.resolve_fetch and is_file:
        sys.stderr.write("Error: It is not possible to resolve remote files directly into a bag archive. "
                         "The bag must first be extracted before the %s argument can be specified.\n\n" %
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

    return args, is_bag, is_file


def main():

    args, is_bag, is_file = parse_cli()
    path = os.path.abspath(args.path)

    archive = None
    temp_path = None
    error = None
    result = 0

    if not args.quiet:
        sys.stderr.write('\n')

    try:
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
                sys.stderr.write('\n')
            return result

        if args.resolve_fetch:
            if args.validate == 'full':
                sys.stderr.write(ASYNC_TRANSFER_VALIDATION_WARNING)
            bdb.resolve_fetch(path,
                              force=True if args.resolve_fetch == 'all' else False,
                              keychain_file=args.keychain_file,
                              config_file=args.config_file)

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
            sys.stderr.write("\n%s" % error)

    if not args.quiet:
        sys.stderr.write('\n')

    return result


if __name__ == '__main__':
    sys.exit(main())
