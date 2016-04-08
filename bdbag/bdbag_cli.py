import argparse
import os
import sys
import logging
import bagit
import bdbag

BAG_METADATA = dict()


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
    description = 'BD2K BDBag utility for working with Bagit/RO archives'

    parser = argparse.ArgumentParser(description=description)
    standard_args = parser.add_argument_group('Standard arguments')

    update_arg = standard_args.add_argument(
        '--update', action="store_true", help="Update (regenerate manifests) an existing bag dir.")

    standard_args.add_argument(
        "--archiver", choices=['zip', 'tar', 'tgz'], help="Archive a bag using the specified format.")

    checksum_arg = standard_args.add_argument(
        "--checksum", action='append', choices=['md5', 'sha1', 'sha256', 'sha512', 'all'],
        help="Checksum algorithm to use: can be specified multiple times with different values. "
             "If \'all\' is specified, every supported checksum will be generated")

    standard_args.add_argument(
        '--resolve-fetch', action="store_true", help="Download remote files listed in the bag's fetch.txt file.")

    standard_args.add_argument(
        '--validate', choices=['fast', 'full'],
        help="Validate a bag directory or bag archive. If \"fast\" is specified, Payload-Oxum (if present) will be "
             "used to check that the payload files are present and accounted for. Otherwise if \"full\" is specified, "
             "all checksums will be regenerated and compared to the corresponding entries in the manifest")

    standard_args.add_argument(
        '--validate-profile', action="store_true",
        help="Validate a bag against the profile specified by the bag's "
             "\"BagIt-Profile-Identifier\" metadata field, if present.")

    standard_args.add_argument(
        '--config-file', default=bdbag.DEFAULT_CONFIG_FILE, metavar='<file>',
        help="Optional path to a configuration file. If this argument is not specified, the configuration file "
             "defaults to: %s " % bdbag.DEFAULT_CONFIG_FILE)

    metadata_file_arg = standard_args.add_argument(
        '--metadata-file', metavar='<file>', help="Optional path to a JSON formatted metadata file")

    standard_args.add_argument(
        '--remote-manifest-file', metavar='<file>',
        help="Remote manifest configuration file used to generate fetch.txt.")

    standard_args.add_argument(
        '--quiet', action="store_true", help="Suppress logging output.")

    standard_args.add_argument(
        '--debug', action="store_true", help="Enable debug logging output.")

    standard_args.add_argument(
        'path', nargs="?", help="Path to a bag directory or bag archive file.")

    metadata_args = parser.add_argument_group('Bag metadata arguments')
    for header in bagit.STANDARD_BAG_INFO_HEADERS:
        metadata_args.add_argument('--%s' % header.lower(), action=AddMetadataAction)

    args = parser.parse_args()

    if not args.path:
        sys.stderr.write("Error: A path to a bag directory or bag archive file is required.")
        sys.exit(-1)

    path = os.path.abspath(args.path)

    if args.archiver and os.path.isfile(path):
        sys.stderr.write("Error: A bag archive cannot be created from an existing bag archive.")
        sys.exit(-1)

    if args.checksum and os.path.isfile(path):
        sys.stderr.write("Error: A checksum manifest cannot be added to an existing bag archive. "
                         "The bag must be extracted, updated, and re-archived.")
        sys.exit(-1)

    if args.update and os.path.isfile(path):
        sys.stderr.write("Error: An existing bag archive cannot be updated in-place. "
                         "The bag must first be extracted and then updated.")
        sys.exit(-1)

    if args.checksum and not args.update and bdbag.is_bag(path):
        sys.stderr.write("Error: Specifying %s for an existing bag requires the %s argument in order "
                         "to apply the changes." % (checksum_arg.option_strings, update_arg.option_strings))
        sys.exit(-1)

    if args.metadata_file and not args.update and bdbag.is_bag(path):
        sys.stderr.write("Error: Specifying %s for an existing bag requires the %s argument in order "
                         "to apply the changes." % (metadata_file_arg.option_strings, update_arg.option_strings))
        sys.exit(-1)

    if BAG_METADATA and not args.update and bdbag.is_bag(path):
        sys.stderr.write("Error: Specifying additional metadata %s for an existing bag requires the %s argument "
                         "in order to apply the change." % (BAG_METADATA, update_arg.option_strings))
        sys.exit(-1)

    return args


def main():

    args = parse_cli()

    archive = None
    temp_path = None
    error = None
    result = 0

    bdbag.configure_logging(level=logging.ERROR if args.quiet else (logging.DEBUG if args.debug else logging.INFO))

    try:
        path = os.path.abspath(args.path)
        if not os.path.isfile(path):
            # do not try to create or update the bag if the user just wants to validate an existing bag
            if not ((args.validate or args.validate_profile) and not args.update and bdbag.is_bag(path)):
                if args.checksum and 'all' in args.checksum:
                    args.checksum = ['md5', 'sha1', 'sha256', 'sha512']
                bdbag.make_bag(path,
                               args.update,
                               args.checksum,
                               BAG_METADATA if BAG_METADATA else None,
                               args.metadata_file,
                               args.config_file)

        if args.validate:
            if os.path.isfile(path):
                temp_path = bdbag.extract_temp_bag(path)
            bdbag.validate_bag(temp_path if temp_path else path,
                               True if args.validate == 'fast' else False,
                               args.config_file)

        if args.archiver:
            archive = bdbag.archive_bag(path, args.archiver)

        if archive is None and os.path.isfile(path):
            archive = path

        if args.validate_profile:
            if os.path.isfile(path):
                if not temp_path:
                    temp_path = bdbag.extract_temp_bag(path)
            profile = bdbag.validate_bag_profile(temp_path if temp_path else path)
            bdbag.validate_bag_serialization(archive if archive else path, profile)

        result = 0

    except Exception as e:
        result = -1
        error = "Error: %s" % bdbag.get_named_exception(e)

    finally:
        if temp_path:
            bdbag.cleanup_bag(temp_path)
        if result != 0:
            sys.stderr.write(error)

    sys.exit(result)
