import argparse
import os
import sys
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

    standard_args.add_argument(
        "--archiver", choices=['zip', 'tar', 'tgz', 'bz2'], help="archive format to use")

    checksum_arg = standard_args.add_argument(
        "--checksum", action='append', choices=['md5', 'sha1', 'sha256', 'sha512'],
        help="checksum to use, can be specified multiple times with different values")

    standard_args.add_argument(
        '--config-file', default=bdbag.DEFAULT_CONFIG_FILE)

    metadata_arg = standard_args.add_argument(
        '--metadata-file', help="JSON formatted metadata file")

    no_update_arg = standard_args.add_argument(
        '--no-update', action="store_true", help="do not update (regenerate manifests) an existing bag dir")

    standard_args.add_argument(
        '--quiet', action="store_true", help="suppress logging output")

    remote_manifest_arg = standard_args.add_argument(
        '--remote-manifest-file', help="remote manifest configuration file used to generate fetch.txt")

    standard_args.add_argument(
        '--resolve-fetch', action="store_true", help="download remote files listed in the bag's fetch.txt file")

    standard_args.add_argument(
        '--validate', action="store_true", help="validate a bag directory or bag archive")

    standard_args.add_argument(
        '--validate-profile', action="store_true", help="validate a bag against it's profile")

    standard_args.add_argument(
        'path', nargs="?", help="path to a bag directory or bag archive file")

    metadata_args = parser.add_argument_group('Bag metadata arguments')
    for header in bagit.STANDARD_BAG_INFO_HEADERS:
        metadata_args.add_argument('--%s' % header.lower(), action=AddMetadataAction)

    args = parser.parse_args()

    if not args.path:
        print "Error: A path to a bag directory or bag archive file is required."
#        parser.print_help()
        sys.exit(-1)

    if args.archiver and os.path.isfile(os.path.abspath(args.path)):
        print("Error: A bag archive cannot be created from an existing bag archive.")
#        parser.print_help()
        sys.exit(-1)

    if args.checksum and os.path.isfile(os.path.abspath(args.path)):
        print("Error: A checksum update cannot be added to an existing bag archive. "
              "The bag must be extracted, updated, and re-archived.")
#        parser.print_help()
        sys.exit(-1)

    if args.no_update and (args.checksum or args.metadata_file or args.remote_manifest_file):
        update_args = list()
        if args.checksum:
            update_args.append(checksum_arg.option_strings)
        if args.metadata_file:
            update_args.append(metadata_arg.option_strings)
        if args.remote_manifest_file:
            update_args.append(remote_manifest_arg.option_strings)
        print "Error: The argument %s is not compatible with the following arguments: %s" % \
              (no_update_arg.option_strings, update_args)
        sys.exit(-1)

    return args


def main():

    args = parse_cli()

    archive = None
    temp_path = None
    path = os.path.abspath(args.path)

    if not args.quiet:
        bdbag.configure_logging()

    try:
        if not os.path.isfile(path):
            bdbag.make_bag(path,
                           args.no_update,
                           args.checksum,
                           BAG_METADATA,
                           args.metadata_file,
                           args.config_file)

        if args.validate:
            if os.path.isfile(path):
                temp_path = bdbag.extract_temp_bag(path)
            bdbag.validate_bag(temp_path if temp_path else path, args.config_file)

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

    except Exception as e:
        print "Error: %s" % e
        sys.exit(-1)

    finally:
        if temp_path:
            bdbag.cleanup_bag(temp_path)
