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
import os
import json
import copy
import uuid
from collections import OrderedDict
from bdbag import guess_mime_type, add_mime_types, escape_uri, VERSION, BAGIT_VERSION
from datetime import datetime
from tzlocal import get_localzone
import logging

logger = logging.getLogger(__name__)

BAG_CREATOR_NAME = "BDBag version: %s (Bagit version: %s)" % (VERSION, BAGIT_VERSION)
BAG_CREATOR_URI = "https://github.com/fair-research/bdbag"
BAG_CONFORMS_TO = ['https://tools.ietf.org/html/draft-kunze-bagit-14',
                   'https://w3id.org/ro/bagit/profile']
ORCID_BASE_URL = "http://orcid.org"

DEFAULT_RO_MANIFEST = {
    "@context": ["https://w3id.org/bundle/context"],
    "@id": "../",
    "aggregates": [],
    "annotations": []
}


def check_input(obj):
    if not isinstance(obj, dict):
        raise ValueError(
            "bdbag_ro: invalid input object type (%s), expected (dict)" % type(obj).__name__)


def read_bag_ro_metadata(bag_path, metadata_path="manifest.json"):
    bag_ro_metadata_path = os.path.abspath(os.path.join(bag_path, "metadata", metadata_path))

    with open(bag_ro_metadata_path) as mf:
        metadata = mf.read()

    return json.loads(metadata, object_pairs_hook=OrderedDict)


def write_bag_ro_metadata(obj, bag_path, metadata_path="manifest.json"):

    check_input(obj)

    bag_ro_metadata_path = os.path.abspath(os.path.join(bag_path, "metadata"))
    ro_metadata_path = os.path.join(bag_ro_metadata_path, metadata_path)
    ro_metadata_path_dir = os.path.dirname(ro_metadata_path)

    if not os.path.exists(ro_metadata_path_dir):
        os.makedirs(ro_metadata_path_dir)

    with open(os.path.abspath(ro_metadata_path.strip()), 'w') as ro_metadata:
        json.dump(obj, ro_metadata, sort_keys=True, indent=4)


def serialize_bag_ro_metadata(obj, bag_path):
    logging.info("Serializing ro-metadata to: %s" % os.path.abspath(os.path.join(bag_path, "metadata")))
    check_input(obj)
    for k, v in obj.items():
        write_bag_ro_metadata(v, bag_path, k)


def init_ro_manifest(creator_name=None,
                     creator_uri=None,
                     creator_orcid=None,
                     author_name=None,
                     author_uri=None,
                     author_orcid=None):
    manifest = copy.deepcopy(DEFAULT_RO_MANIFEST)
    authored_by = None
    if author_name:
        if author_orcid and not author_orcid.startswith("http"):
            author_orcid = "/".join([ORCID_BASE_URL, author_orcid])
        authored_by = make_authored_by(author_name, uri=author_uri, orcid=author_orcid)

    if creator_name:
        if creator_orcid and not creator_orcid.startswith("http"):
            creator_orcid = "/".join([ORCID_BASE_URL, creator_orcid])
        created_by = make_created_by(creator_name, uri=creator_uri, orcid=creator_orcid)
    else:
        created_by = make_created_by(name=BAG_CREATOR_NAME, uri=BAG_CREATOR_URI)

    add_provenance(manifest,
                   created_on=make_created_on(),
                   created_by=created_by,
                   authored_on=make_authored_on(),
                   authored_by=authored_by)

    return manifest


def add_file_metadata(manifest,
                      source_url=None,
                      local_path=None,
                      media_type=None,
                      retrieved_on=None,
                      retrieved_by=None,
                      created_on=None,
                      created_by=None,
                      authored_on=None,
                      authored_by=None,
                      conforms_to=None,
                      bundled_as=None,
                      update_existing=False):

    check_input(manifest)

    if not source_url and not local_path:
        raise ValueError("Error while adding file metadata to RO manifest. "
                         "At least one of the parameters \"source_url\" or \"local_path\" must be specified")

    path = source_url
    if local_path:
        path = local_path
    elif bundled_as:
        filename = bundled_as.get("filename")
        path = filename

    if not conforms_to:
        file_ext = os.path.splitext(path)[1][1:]
        file_ext = file_ext.lstrip(".") if file_ext else None
        conforms_to = FILETYPE_ONTOLOGY_MAP.get(file_ext, None)

    if not media_type:
        media_type = guess_mime_type(path)

    uri = source_url = escape_uri(source_url)
    retrieved_from = None

    if local_path:
        uri = escape_uri(ensure_payload_path_prefix(local_path))
        if source_url:
            retrieved_from = dict(retrievedFrom=source_url)

    add_provenance(
        add_aggregate(manifest,
                      uri=uri,
                      mediatype=media_type,
                      conforms_to=conforms_to,
                      bundled_as=bundled_as,
                      update_existing=update_existing),
        retrieved_from=retrieved_from,
        retrieved_on=retrieved_on,
        retrieved_by=retrieved_by,
        created_on=created_on,
        created_by=created_by,
        authored_on=authored_on,
        authored_by=authored_by)


def add_provenance(obj, created_on=None, created_by=None, authored_on=None, authored_by=None,
                   retrieved_from=None, retrieved_on=None, retrieved_by=None):

    check_input(obj)

    if created_on:
        obj.update(created_on)
    if created_by:
        obj.update(created_by)
    if authored_on:
        obj.update(authored_on)
    if authored_by:
        obj.update(authored_by)
    if retrieved_from:
        obj.update(retrieved_from)
    if retrieved_on:
        obj.update(retrieved_on)
    if retrieved_by:
        obj.update(retrieved_by)

    return obj


def add_aggregate(obj, uri, mediatype=None, conforms_to=None, bundled_as=None, update_existing=False):

    check_input(obj)

    aggregates = obj.get('aggregates', list())
    aggregate = dict()
    aggregate['uri'] = uri.replace("\\", "/")
    if mediatype:
        aggregate['mediatype'] = mediatype
    if conforms_to:
        aggregate['conformsTo'] = conforms_to
    if bundled_as:
        aggregate['bundledAs'] = bundled_as

    exists = False
    if update_existing:
        for i, item in enumerate(aggregates):
            if aggregate['uri'] == item['uri']:
                ba = item.get('bundledAs')
                ba_uri = ba.get('uri') if ba else None
                if ba_uri:
                    aggregate['bundledAs']['uri'] = ba_uri
                aggregates[i] = aggregate
                exists = True
                break

    if not exists:
        aggregates.append(aggregate)
    obj['aggregates'] = aggregates

    return aggregate


def add_annotation(obj, about, uri=None, content=None, motivatedBy=None, update_existing=False):

    check_input(obj)

    annotations = obj.get('annotations', list())
    annotation = dict()
    annotation['about'] = about
    if uri:
        annotation['uri'] = uri if uri else uuid.uuid4().urn
    if content:
        annotation['content'] = content
    if motivatedBy:
        annotation['oa:motivatedBy'] = motivatedBy

    exists = false
    if update_existing:
        for i, item in enumerate(annotations):
            if annotation['about'] == item["about"]:
                annotation['uri'] = item.get('uri', uri)
                annotations[i] = annotation
                exists = True
                break
    if not exists:
        annotations.append(annotation)
    obj['annotations'] = annotations

    return annotation


def make_bundled_as(uri=None, folder=None, filename=None):

    if filename and folder is None:
        raise ValueError("When specifying a \"filename\" attribute for a bundledAs object, the \"folder\" attribute "
                         "must also be specified.")

    bundled_as = dict()
    bundled_as['uri'] = uri if uri else uuid.uuid4().urn
    if filename:
        bundled_as['filename'] = filename
    if folder is not None:
        bundled_as['folder'] = ensure_payload_path_prefix(folder)

    return bundled_as


def make_created_by(name, uri=None, orcid=None):
    created_by = dict()
    created_by['createdBy'] = _make_user_ref(name, uri, orcid)

    return created_by


def make_created_on(date=None):
    created_on = dict()
    created_on['createdOn'] = _make_isoformat_date(date)

    return created_on


def make_authored_by(name, uri=None, orcid=None):
    authored_by = dict()
    authored_by['authoredBy'] = _make_user_ref(name, uri, orcid)

    return authored_by


def make_authored_on(date=None):
    authored_on = dict()
    authored_on['authoredOn'] = _make_isoformat_date(date)

    return authored_on


def make_retrieved_by(name, uri=None, orcid=None):
    retrieved_by = dict()
    retrieved_by['retrievedBy'] = _make_user_ref(name, uri, orcid)

    return retrieved_by


def make_retrieved_on(date=None):
    retrieved_on = dict()
    retrieved_on['retrievedOn'] = _make_isoformat_date(date)

    return retrieved_on


def _make_user_ref(name, uri=None, orcid=None):
    user_ref = dict()
    user_ref['name'] = name
    if uri:
        user_ref['uri'] = uri
    if orcid:
        user_ref['orcid'] = orcid

    return user_ref


def _make_isoformat_date(date=None):
    if date:
        date = date.replace(microsecond=0)
        return date.isoformat()
    else:
        now = datetime.now(tz=get_localzone())
        now = now.replace(microsecond=0)
        return now.isoformat()


def ensure_payload_path_prefix(input_path):
    input_path = input_path.replace("\\", "/")
    if input_path.startswith("/"):
        input_path = input_path.lstrip("/")
    if input_path == "data":
        output_path = "../data/"
    elif input_path.startswith("data/"):
        output_path = ''.join(["../", input_path])
    elif input_path.startswith("../data/"):
        output_path = input_path
    else:
        output_path = ''.join(["../data/", input_path])

    return output_path


FILETYPE_ONTOLOGY_MAP = {
    "bam": "http://edamontology.org/format_2572",
    "bed bed12": "http://edamontology.org/format_3586",
    "bed bed3": "http://edamontology.org/format_3003",
    "bed bed3+": "http://edamontology.org/format_3003",
    "bed bed6+": "http://edamontology.org/format_3003",
    "bed bed9": "http://edamontology.org/format_3003",
    "bed bedExonScore": "http://edamontology.org/format_3003",
    "bed bedGraph": "http://edamontology.org/format_3583",
    "bed bedLogR": "http://edamontology.org/format_3003",
    "bed bedMethyl": "http://edamontology.org/format_3003",
    "bed bedRnaElements": "http://edamontology.org/format_3003",
    "bed broadPeak": "http://edamontology.org/format_3614",
    "bed idr_peak": "http://edamontology.org/format_3003",
    "bed modPepMap": "http://edamontology.org/format_3003",
    "bed narrowPeak": "http://edamontology.org/format_3613",
    "bed pepMap": "http://edamontology.org/format_3003",
    "bed peptideMapping": "http://edamontology.org/format_3003",
    "bed tss_peak": "http://edamontology.org/format_3003",
    "bigBed bed12": "http://edamontology.org/format_3004",
    "bigBed bed3": "http://edamontology.org/format_3004",
    "bigBed bed3+": "http://edamontology.org/format_3004",
    "bigBed bed6+": "http://edamontology.org/format_3004",
    "bigBed bed9": "http://edamontology.org/format_3004",
    "bigBed bedExonScore": "http://edamontology.org/format_3004",
    "bigBed bedLogR": "http://edamontology.org/format_3004",
    "bigBed bedMethyl": "http://edamontology.org/format_3004",
    "bigBed bedRnaElements": "http://edamontology.org/format_3004",
    "bigBed broadPeak": "http://edamontology.org/format_3004",
    "bigBed idr_peak": "http://edamontology.org/format_3004",
    "bigBed modPepMap": "http://edamontology.org/format_3004",
    "bigBed narrowPeak": "http://edamontology.org/format_3004",
    "bigBed pepMap": "http://edamontology.org/format_3004",
    "bigBed peptideMapping": "http://edamontology.org/format_3004",
    "bigBed tss_peak": "http://edamontology.org/format_3004",
    "bigWig": "http://edamontology.org/format_3006",
    "CEL": "http://edamontology.org/format_1638",
    "csfasta": "http://edamontology.org/format_3589",
    "csqual": "",
    "csv": "http://edamontology.org/format_3475",
    "dcm": "http://edamontology.org/format_3548",
    "dicom": "http://edamontology.org/format_3548",
    "json": "http://edamontology.org/format_3464",
    "fasta": "http://edamontology.org/format_1929",
    "fastq": "http://edamontology.org/format_1930",
    "gff gff3": "http://edamontology.org/format_1975",
    "gtf": "http://edamontology.org/format_2306",
    "idat": "http://edamontology.org/format_3578",
    "nii": "http://edamontology.org/format_3549",
    "rcc": "http://edamontology.org/format_3580",
    "sam": "http://edamontology.org/format_2573",
    "tagAlign": "",
    "tar": "http://purl.obolibrary.org/obo/WSIO_compression_019",
    "tsv": "http://edamontology.org/format_3475",
    "wig": "http://edamontology.org/format_3005"
}

MIMETYPE_EXTENSION_MAP = {
    "application/dicom": ["dcm", "dicom"],
    "application/x-nifti": ["nii"],
    "application/fasta": ["fasta"]
}
add_mime_types(MIMETYPE_EXTENSION_MAP)
