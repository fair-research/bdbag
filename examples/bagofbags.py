#
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
# Many limitations
# -- Essentially no error checking.
# -- manifest.json is a Research Object, but doesn't include provenance info
#

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

logger = logging.getLogger(__name__)

BAG_CONFORMS_TO = [ 'https://tools.ietf.org/html/draft-kunze-bagit-14',
                    'https://w3id.org/ro/bagit/profile' ]
NAME2THING = 'http://n2t.net/'
MINID_SERVER = 'http://minid.bd2k.org/minid'


def configure_logging(level=logging.INFO, logpath=None):
    logging.captureWarnings(True)
    log_format = "%(asctime)s - %(levelname)s - %(message)s"
    if logpath:
        logging.basicConfig(filename=logpath, level=level, format=log_format)
    else:
        logging.basicConfig(level=level, format=log_format)


def init_ro_manifest(creator_name=None, creator_uri=None, creator_orcid=None):
    manifest = copy.deepcopy(ro.DEFAULT_RO_MANIFEST)
    created_on = ro.make_created_on()
    created_by = None
    if creator_name:
        if creator_orcid and not creator_orcid.startswith('http'):
            creator_orcid = '/'.join(['http://orcid.org', creator_orcid])
        created_by = ro.make_created_by(creator_name, uri=creator_uri, orcid=creator_orcid)
    ro.add_provenance(manifest, created_on=created_on, created_by=created_by)
    manifest.update({ 'conformsTo' : BAG_CONFORMS_TO })
    return manifest


#It could make sense to aggregate the nested bags by their global
#URI in the RO manifest instead of the (potentially not resolved) local
#.zip files. The 'bundledAs' can be used to link it together with the ZIP
#file:
#
#'aggregates': [
#  { 'uri': 'http://n2t.net/ark:/57799/b91w9r',
#    'conformsTo': [ 
#       'https://tools.ietf.org/html/draft-kunze-bagit-14',
#       'https://w3id.org/ro/bagit/profile'
#    ],
#    'bundledAs': {
#      'uri': '../data/adrenal_gland_912c17b6-b2bf-461b-9753-49e7e01ac536.zip',
#      'folder': 'data/'
#      'filename': 'adrenal_gland_912c17b6-b2bf-461b-9753-49e7e01ac536.zip'
#    }
# }
#]


def add_remote_file_manifest(entries, ro_manifest):
    for (minid, _, _, uri, _, _) in entries:
         bundled_as = { 'uri'      : '../data/' + uri,
                        'folder'   : 'data/',
                        'filename' : uri }
         ro.add_aggregate(ro_manifest, NAME2THING+minid, mediatype=None,
                          conforms_to=BAG_CONFORMS_TO, bundled_as=bundled_as)
    ro.add_annotation(ro_manifest, '../', content=''.join(['../data/', 'README']))
    # Following is a bit of a hack: should really modify ro.add_annotation to accept a motivatedBy
    [annotation] = ro_manifest.get('annotations', list())
    annotation['oa:motivatedBy'] = 'oa:describing'
    ro_manifest['annotations'] = [annotation]


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


# Fetch the sub-bag file into a temporary directory and determine its size
def get_size(link):
    response = requests.get(link)
    size = len(response.content)
    return(size) 


def extract_fields(minids):
    results = []
    for minid in minids:
        minid = minid.strip()
        (checksum, title, link, filename) = get_minid_fields(minid)
        size = get_size(link)
        results += [(minid, title, link, filename, checksum, size)]
    return(results)


DEFAULT_RO_MANIFEST = {
    '@context': ['https://w3id.org/bundle/context'],
    '@id': '../',
    'aggregates': [],
    'annotations': []
}


def write_ro_manifest(obj, path):
    with open(os.path.abspath(path), 'w') as ro_manifest:
        json.dump(obj, ro_manifest, sort_keys=True, indent=4)


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


def ensure_bag_path_exists(bag_path, overwrite=False):
    if os.path.exists(bag_path):
        if overwrite:
            shutil.rmtree(bag_path)
        else:
            saved_bag_path = ''.join([bag_path, '_', time.strftime('%Y-%m-%d_%H.%M.%S')])
            logger.warn('Specified bag directory already exists -- moving it to %s' % saved_bag_path)
            shutil.move(bag_path, saved_bag_path)
    if not os.path.exists(bag_path):
        os.makedirs(bag_path)


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
    parser.add_argument('-m', '--minids', help='File listing Minids for new bag', required=True)
    parser.add_argument('-b', '--bagname', help='Name of directory for new bag.', required=True)
    parser.add_argument('-V', '--verify', action='store_true', help='Validate bag after building it.', required=False)
    parser.add_argument('-q', '--quiet', action="store_true", help="Suppress logging output.")
    parser.add_argument('-d', '--debug', action="store_true", help="Enable debug logging output.")
    args = parser.parse_args()
   
    configure_logging(level=logging.ERROR if args.quiet else (logging.DEBUG if args.debug else logging.INFO))

    # Create the directory that will hold the new BDBag
    ensure_bag_path_exists(args.bagname)

    # Read list of sub-bag Minids
    with open(args.minids) as f:
        minids = f.readlines()
        minids = [x.strip() for x in minids] 

    # Fetch each sub-bag to determine its properties
    minid_fields = extract_fields(minids)

    # Create 'README' file in the newly created bag directory. (moved to 'data' when bag is created)
    write_readme(args.bagname, minid_fields)

    # Create remote_file_manifest_file, to be used by make_bag
    working_dir = temp_path = tempfile.mkdtemp(prefix='encode2bag_')
    remote_file_manifest_file = osp.abspath(osp.join(working_dir, 'remote-file-manifest.json'))
    generate_remote_manifest_file(minid_fields, remote_file_manifest_file)

    # Create the new bag based on the supplied remote manifest file
    bag = bdb.make_bag(args.bagname,
                       algs=['md5', 'sha256'],
                       #metadata=bag_metadata,
                       remote_file_manifest=remote_file_manifest_file)

    # Create metadata/manifest.json file with Research Object JSON object
    ro_manifest = init_ro_manifest(creator_name='bagofbags.py', creator_uri='https://github.com/ini-bdds/bdbag/examples/bagofbags.py')
    add_remote_file_manifest(minid_fields, ro_manifest)
    bag_metadata_dir = os.path.abspath(os.path.join(args.bagname, 'metadata'))
    if not os.path.exists(bag_metadata_dir):
        os.mkdir(bag_metadata_dir)
    ro_manifest_path = osp.join(bag_metadata_dir, 'manifest.json')
    write_ro_manifest(ro_manifest, ro_manifest_path)

    # Run make_bag again to include manifest.json in the checksums etc.
    bdb.make_bag(args.bagname, update=True)

    if args.verify:
        bdb.resolve_fetch(args.bagname, force=True) 
        bdb.validate_bag(args.bagname, fast=False, callback=None)


#----------------------------------------------------------------------------------------------------------------
if __name__ == '__main__':
   main(sys.argv[1:])
