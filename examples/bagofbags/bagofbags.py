# BagOfBags.py -- Ian Foster
#
# Program to create a big data bag (BDBag) containing a supplied set of (descriptive string, Minid) pairs,
# each of which is assumed to reference a single BDBag. This BDBag contains:
# -- A data/README file listing the files referenced by the Minids
# -- A metadata/manifest.json with a Research Object describing the BDBag's contents
# -- A fetch.txt file with the info required to fetch the sub-bags into 'data' (standard BDBag stuff)
#
# Usage: python bagofbags.py -m MINIDS -b BAGNAME [-V] [-q] [-d]
#   MINIDS = name of file containing a set of Minids, one per line
#   BAGNAME = name of directory for new BDBag
#   -V : If provided, then once bag is created, fetch bag contents and validate it.
#
# Runs with >Python 2.7, AFAIK
#
# Limitations
# -- Limited error checking.
# -- manifest.json is a Research Object, but doesn't include provenance info

import operator
import json
import sys
import argparse
import subprocess
import os
import logging
import os.path as osp
import re
import requests
import datetime
import time
import copy
import shutil
import tempfile
from bdbag import bdbag_api as bdb
from bdbag import bdbag_ro as ro
import minid_client.minid_client_api as mn
from bdbag import VERSION, BAGIT_VERSION

NAME2THING      = 'http://n2t.net/'
MINID_SERVER    = 'http://minid.bd2k.org/minid'


def add_remote_file_manifest(entries, ro_manifest):
    for (minid, _, _, uri, _, _) in entries:
         ro.add_aggregate(ro_manifest, NAME2THING+minid,
                          mediatype=None,
                          conforms_to=ro.BAG_CONFORMS_TO,
                          bundled_as=ro.make_bundled_as(None, '', uri))
    ro.add_annotation(ro_manifest,
                      '../',
                      '../data/README',
                      motivatedBy={"@id": "oa:describing"})


def get_minid_fields(minid):
    r = mn.get_entities(MINID_SERVER, minid, False)
    minid_json = r[minid]
    locations = minid_json['locations']
    link = locations[0]['link']
    filename = os.path.basename(link)
    try:
        title = str(minid_json['titles'][0]['title'])
    except:
        title = ''
    return( (minid_json['checksum'], title, link, filename) )


# Determine the size of the sub-bag file
def get_size(link):
    r = requests.head(link)
    r.raise_for_status()
    if r.ok:
        size = r.headers['Content-Length']
    return(size) 


# Read Minids from file and, for each, determine title, URI, filename, checksum, size
def extract_fields(minidfile):
    with open(minidfile) as f:
        minids = f.readlines()
        minids = [x.strip() for x in minids] 
    results = []
    for minid in minids:
        (checksum, title, link, filename) = get_minid_fields(minid)
        size = get_size(link)
        results += [(minid, title, link, filename, checksum, size)]
    return(results)


def generate_remote_manifest_file(minid_fields, remote_manifest_filepath):
    with open(remote_manifest_filepath, 'w') as writer:
        entries = list()
        for (minid, _, _, filename, checksum, size) in minid_fields:
            entry = {
                'url'      : minid,
                'filename' : filename,
                'length'   : size,
                'sha256'   : checksum
            }
            entries.append(entry)
        json.dump(entries, writer, sort_keys=True, indent=4)


def write_readme(filename, minid_fields):
    with open(filename + '/README', 'wt') as e_writer:
        e_writer.write('This is a Big Data bag (BDBag: https://github.com/ini-bdds/bdbag)\n')
        e_writer.write('that itself contains ' + str(len(minid_fields)) + ' Minid-referenced BDBags, as follows:\n\n')
        for entry in minid_fields:
            (minid, title, link, filename, checksum, size) = entry
            e_writer.write(minid + ' (' + title + '): ' + link + '\n')


#----------------------------------------------------------------------------------------------------------------
def main(argv):
    parser = argparse.ArgumentParser(description='Program to create a BDBag containing a set of Minids for remote content')
    parser.add_argument('-m', '--minids', metavar='<minid file>',
                        help='File listing Minids for new bag', required=True)
    parser.add_argument('-b', '--bagname', metavar='<bag name>',
                        help='Name of directory for new bag.', required=True)
    parser.add_argument('-v', '--verify', action='store_true',
                        help='Validate bag after building it.', required=False)
    parser.add_argument('-q', '--quiet', action="store_true", help="Suppress logging output.")
    parser.add_argument('-d', '--debug', action="store_true", help="Enable debug logging output.")
    parser.add_argument('-n', '--author-name', metavar="<person or entity name>",
        help="Optional name of the person or entity responsible for the creation of this bag, "
             "for inclusion in the bag metadata.")
    parser.add_argument('-o', '--author-orcid', metavar="<orcid>",
        help="Optional ORCID identifier of the bag creator, for inclusion in the bag metadata.")
    args = parser.parse_args()
   
    bdb.configure_logging(level=logging.ERROR if args.quiet else (logging.DEBUG if args.debug else logging.INFO))

    # Create the directory that will hold the new BDBag
    bdb.ensure_bag_path_exists(args.bagname)

    # For each supplied minid, fetch sub-bag to determine its properties
    minid_fields = extract_fields(args.minids)

    # Create 'README' file in the newly created bag directory. (moved to 'data' when bag is created)
    write_readme(args.bagname, minid_fields)

    # Create remote_file_manifest_file, to be used by make_bag
    working_dir = temp_path = tempfile.mkdtemp(prefix='encode2bag_')
    remote_file_manifest_file = osp.abspath(osp.join(working_dir, 'remote-file-manifest.json'))
    generate_remote_manifest_file(minid_fields, remote_file_manifest_file)

    # Create the new bag based on the supplied remote manifest file
    bag = bdb.make_bag(args.bagname,
                       algs=['md5', 'sha256'],
                       remote_file_manifest=remote_file_manifest_file)

    # Create metadata/manifest.json file with Research Object JSON object
    ro_manifest = ro.init_ro_manifest(author_name=args.author_name, author_orcid=args.author_orcid,
        creator_name = 'bagofbags using BDBag version: %s (Bagit version: %s)' % (VERSION, BAGIT_VERSION),
        creator_uri='https://github.com/ini-bdds/bdbag/examples/bagofbags/')
    add_remote_file_manifest(minid_fields, ro_manifest)
    bag_metadata_dir = os.path.abspath(os.path.join(args.bagname, 'metadata'))
    if not os.path.exists(bag_metadata_dir):
        os.mkdir(bag_metadata_dir)
    ro.write_ro_manifest(ro_manifest, osp.join(bag_metadata_dir, 'manifest.json'))

    # Run make_bag again to include manifest.json in the checksums etc.
    bdb.make_bag(args.bagname, update=True)

    if args.verify:
        bdb.resolve_fetch(args.bagname, force=True) 
        bdb.validate_bag(args.bagname, fast=False, callback=None)

#----------------------------------------------------------------------------------------------------------------
if __name__ == '__main__':
   main(sys.argv[1:])
