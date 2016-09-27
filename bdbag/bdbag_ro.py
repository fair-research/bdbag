import os
import json
from datetime import datetime
from tzlocal import get_localzone
import logging

logger = logging.getLogger(__name__)

DEFAULT_RO_MANIFEST = {
    "@context": ["https://w3id.org/bundle/context"],
    "@id": "../",
    "aggregates": [],
    "annotations": []
}


def write_ro_manifest(obj, path):
    with open(os.path.abspath(path), 'w') as ro_manifest:
        json.dump(obj, ro_manifest, sort_keys=True, indent=4)


def add_provenance(obj, created_on=None, created_by=None, authored_on=None, authored_by=None,
                   retrieved_from=None, retrieved_on=None, retrieved_by=None):

    if not isinstance(obj, dict):
        return

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


def add_aggregate(obj, uri, mediatype=None, conforms_to=None, bundled_as=None):

    if not isinstance(obj, dict):
        return

    aggregates = obj.get('aggregates', list())
    aggregate = dict()
    aggregate['uri'] = uri
    if mediatype:
        aggregate['mediatype'] = mediatype
    if conforms_to:
        aggregate['conformsTo'] = conforms_to
    if bundled_as:
        aggregate['bundledAs'] = bundled_as

    aggregates.append(aggregate)
    obj['aggregates'] = aggregates

    return aggregate


def add_annotation(obj, about, uri=None, content=None):

    if not isinstance(obj, dict):
        return

    annotations = obj.get('annotations', list())
    annotation = dict()
    annotation['about'] = about
    if uri:
        annotation['uri'] = uri
    if content:
        annotation['content'] = content

    annotations.append(annotation)
    obj['annotations'] = annotations

    return annotation


def make_bundled_as(obj, uri, folder=None, filename=None):

    if not isinstance(obj, dict):
        return

    if filename and not folder:
        logger.warn("When specifying a \"filename\" attribute for a bundledAs object, the \"folder\" attribute must"
                    " also be specified.")

    bundled_as = dict()
    bundled_as['uri'] = uri
    if filename:
        bundled_as['filename'] = filename
    if folder:
        bundled_as['folder'] = folder

    obj['bundledAs'] = bundled_as

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
