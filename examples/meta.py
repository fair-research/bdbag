#
# Program to create a big data bag (BDBag) containing a supplied set of (descriptive string, Minid) pairs,
# each of which is assumed to reference a single BDBag. This BDBag contains:
# -- A data/README file listing the files referenced by the Minids
# -- A metadata/manifest.json with a Research Object describing the BDBag's contents
# -- A fetch.txt file with the info required to fetch the sub-bags into "data" (standard BDBag stuff)
#
# Usage: python meta.py -m MINIDS -b BAGNAME [-r REMOTE_FILE_MANIFEST] [-V]
#   MINIDS = name of file in which each line is a comma-separated <descriptive string>, <minid> pair
#   BAGNAME = name of directory for new BDBag
#   REMOTE_FILE_MANIFEST = name of file in which to place remote file manifest. By default, "t.json"
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
import re
import datetime

debug = 1

def run_command(command):
    if debug > 0:
        print('Run: %s'%' '.join(command))
    result = subprocess.check_output(command, stderr=subprocess.STDOUT)
    return( result.decode('utf-8') )

def get_minid_fields(minid):
    json_string = run_command(['minid', '--quiet', '--json', minid])

    minid_json = json.loads(json_string)
    locations = minid_json['locations']
    link = locations[0]['link']
    filename = os.path.basename(link)
    return( (minid_json['checksum'], link, filename) )

def get_size(link):
    run_command(['wget', link])
    file = os.path.basename(link)
    size_string = run_command(['wc', '-c', file])  
    s = re.sub('^ +', '', str(size_string))
    size = s.split(' ')[0]
    run_command(['rm', file])
    return(size) 

def process_minid(line, writer):
    (minid, _, _, filename, checksum, size) = line
    json_minid = {
        'url'      : minid,
        'filename' : filename,
        'length'   : size,
        'sha256'   : checksum
    }
    writer.write(json.dumps(json_minid, indent=2))

def prepare_minid(description, minid):
    (checksum, link, filename) = get_minid_fields(minid)
    size = get_size(link)
    filename = description.replace(' ', '_') + '_' + filename
    return( (minid, description, link, filename, checksum, size) )

def extract_fields(minids):
    results = []
    for line in minids:
        (description, minid) = line.split(',')
        minid = minid.strip()
        entry = prepare_minid(description, minid)
        results += [entry]
    return(results)

def generate_json(minid_fields, filename):
    with open(filename, 'wt') as e_writer:
        e_writer.write('[')
        for index, entry in enumerate(minid_fields):
            process_minid(entry, e_writer)
            if index+1 < len(minid_fields):
                e_writer.write(',')
            e_writer.write('\n')
        e_writer.write(']\n')
    if debug > 0:
        print('Remote file manifest created:')
        with open(filename) as json_data:
            parsed = json.load(json_data)
            print(json.dumps(parsed, indent=4, sort_keys=True))


def prepare_bdbag(bagname):
    try:
        run_command(['mkdir', bagname])
    except:
        print('Bag directory cannot already exist')
        exit(1)

def generate_bdbag(filename, bagname):
    run_command(['bdbag', '--remote-file-manifest', filename, bagname])

def validate_bdbag(bagname):
    run_command(['bdbag', '--resolve-fetch', 'all', bagname])
    run_command(['bdbag', '--validate', 'full', bagname])

def write_ro_metadata(filename, minid_fields):
    os.mkdir(os.path.dirname(filename))
    with open(filename, 'wt') as e_writer:
        e_writer.write('{\n  "@context": ["https://w3id.org/bundle/context"],\n')
        e_writer.write('  "@id": "../",\n')
        date = datetime.datetime.utcnow().replace(microsecond=0).isoformat() + 'Z' 
        e_writer.write('  "createdOn": "' + date + '",\n')
        e_writer.write('  "createdBy": { "name": "meta.py" },\n')

        e_writer.write('  "conformsTo": [\n')
        e_writer.write('    "https://tools.ietf.org/html/draft-kunze-bagit-14",\n')
        e_writer.write('    "https://w3id.org/ro/bagit/profile"\n')
        e_writer.write('  ],\n\n')

        e_writer.write('  "aggregates": [\n')
        count = 0
        for index, elem in enumerate(minid_fields):
            (_, _, _, filename, _, _) = elem
            e_writer.write('    {\n      "mediatype": "application/zip",\n')
            e_writer.write('      "uri": "../data/' + filename + '"\n    }')
            if index+1 < len(minid_fields):
                e_writer.write(',')
            e_writer.write('\n')
        e_writer.write('  ],\n\n')
        e_writer.write('  "annotations": [\n    {\n')
        e_writer.write('      "content": "../data/README.md",\n')
        e_writer.write('      "oa:motivatedBy": "oa:describing",\n')
        e_writer.write('      "about": [\n')
        for index, elem in enumerate(minid_fields):
            (_, _, _, filename, _, _) = elem
            e_writer.write('          "../data/' + filename + '"')
            if index+1 < len(minid_fields):
                e_writer.write(',')
            e_writer.write('\n')
        e_writer.write('      ]\n    }\n  ]\n}\n')


def write_readme(filename, minid_fields):
    with open(filename, 'wt') as e_writer:
        e_writer.write('This is a Big Data bag (BDBag: https://github.com/ini-bdds/bdbag)\n')
        e_writer.write('that itself contains ' + str(len(minid_fields)) + ' Minid-referenced BDBags, as follows:\n\n')
        for entry in minid_fields:
            (minid, description, link, filename, checksum, size) = entry
            e_writer.write(minid + ' (' + description + '): ' + link + '\n')

#----------------------------------------------------------------------------------------------------------------
def main(argv):
    parser = argparse.ArgumentParser(description='Program to create a BDBag containing a set of Minids for remote content')
    parser.add_argument('-m', '--minids', help='File listing Minids for new bag', required=True)
    parser.add_argument('-r', '--remote-file-manifest', help='Temporary file in which to place the remote file manifest', required=False)
    parser.add_argument('-b', '--bagname', help='Name of directory for new bag.', required=True)
    parser.add_argument('-V', '--verify', action='store_true', help='Validate bag after building it.', required=False)
    parser.add_argument('-d', '--debug', help='Debug level', required=False, type=int, choices=[0, 1, 2])
    args = parser.parse_args()

    # Default debug level is 1: set -d 0 for no info at all, -d 2 for verbose info
    if args.debug != None:
        global debug
        debug = args.debug

    if args.remote_file_manifest == None:
        filename = 't.json'
    else:
        filename = args.remote_file_manifest
    
    prepare_bdbag(args.bagname)

    with open(args.minids) as f:
        minids = f.readlines()
        minids = [x.strip() for x in minids] 

    minid_fields = extract_fields(minids)
    generate_json(minid_fields, filename)
    # Note that README is created at top level; gets moved to "data" when bag is created.
    write_readme(args.bagname + '/README', minid_fields)
    generate_bdbag(filename, args.bagname)
    write_ro_metadata(args.bagname + '/metadata/manifest.json', minid_fields)
    if args.verify:
        validate_bdbag(args.bagname)

#----------------------------------------------------------------------------------------------------------------
if __name__ == '__main__':
   main(sys.argv[1:])
