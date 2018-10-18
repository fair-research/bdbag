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
import errno
import logging
import json
import shutil
import tempfile
import tarfile
import zipfile
import bdbag.bdbagit as bdbagit
import bdbag.bdbagit_profile as bdbp
import bdbag.bdbag_ro as bdbro
from datetime import date, datetime
from tzlocal import get_localzone
from collections import OrderedDict
from bdbag import *
from bdbag.bdbag_config import *
from bdbag.fetch.fetcher import fetch_bag_files, fetch_single_file
from bdbag.fetch.auth.keychain import DEFAULT_KEYCHAIN_FILE

logger = logging.getLogger(__name__)


def configure_logging(level=logging.INFO, logpath=None, filemode='a', log_format=DEFAULT_LOG_FORMAT):
    logging.captureWarnings(True)
    if logpath:
        logging.basicConfig(filename=logpath, filemode=filemode, level=level, format=log_format)
    else:
        logging.basicConfig(level=level, format=log_format)


def read_metadata(metadata_file):
    if not metadata_file:
        return dict()
    else:
        metadata_file = os.path.abspath(metadata_file)

    logger.info("Reading bag metadata from file: %s" % metadata_file)
    with open(metadata_file) as mf:
        metadata = mf.read()
        mf.close()
        return json.loads(metadata, object_pairs_hook=OrderedDict)


def cleanup_bag(bag_path, save=False):
    logger.info("Cleaning up bag dir: %s" % bag_path)
    if save:
        saved_bag_path = ''.join([bag_path, '_', datetime.strftime(datetime.now(), "%Y-%m-%d_%H.%M.%S")])
        logger.info("Moving bag %s to %s" % (bag_path, saved_bag_path))
        shutil.move(bag_path, saved_bag_path)
        return saved_bag_path
    else:
        shutil.rmtree(bag_path)
        return None


def ensure_bag_path_exists(bag_path, save=True):
    saved_bag_path = None
    if os.path.exists(bag_path):
        saved_bag_path = cleanup_bag(bag_path, save)
    if not os.path.exists(bag_path):
        logging.info("Creating bag directory: %s" % bag_path)
        os.makedirs(bag_path)

    return saved_bag_path


def revert_bag(bag_path):
    if not is_bag(bag_path):
        logger.warning("Cannot revert the bag %s because it is not a bag directory!")
        return

    for path in os.listdir(bag_path):
        if os.path.basename(os.path.abspath(path)) != 'data':
            if path.startswith(("bag-info", "bagit", "fetch", "manifest-", "tagmanifest-")):
                os.remove(os.path.join(bag_path, path))

    data_path = os.path.join(bag_path, 'data')
    for path in os.listdir(data_path):
        old_path = os.path.join(data_path, path)
        new_path = os.path.join(bag_path, path)
        logger.debug("Bag revert: moving payload file %s to %s", old_path, new_path)
        os.rename(old_path, new_path)
    os.rmdir(data_path)
    logging.info("Bag directory %s has been reverted back to a normal directory." % bag_path)


def prune_bag_manifests(bag):
    manifests_pruned = False
    manifests = list(bag.manifest_files())
    manifests += list(bag.tagmanifest_files())
    for manifest in manifests:
        if not manifest.find("tagmanifest-") is -1:
            search = "tagmanifest-"
        else:
            search = "manifest-"
        alg = os.path.basename(manifest).replace(search, "").replace(".txt", "")
        if alg not in bag.algorithms:
            logger.info("Removing unused manifest from bag: %s" % manifest)
            os.remove(manifest)
            manifests_pruned = True

    return manifests_pruned


def is_bag(bag_path):
    bag = None
    try:
        bag = bdbagit.BDBag(bag_path)
    except (bdbagit.BagError, bdbagit.BagValidationError):  # pragma: no cover
        pass
    return True if bag else False


def check_payload_consistency(bag, skip_remote=False, quiet=False):

    only_in_manifests, only_on_fs, only_in_fetch = bag.compare_manifests_with_fs_and_fetch()
    payload_consistent = not only_on_fs

    if not skip_remote:
        # check for changes to remote entries vs. known fetch.txt entries
        updated_remote_files = sorted(bag.remote_entries.keys())
        existing_remote_files = sorted(list(bag.files_to_be_fetched(False)))
        modified_remote_files = list(set(updated_remote_files) - set(existing_remote_files))
        if modified_remote_files:
            payload_consistent = False
            if not quiet:
                logger.warning("The bag manifests require updating to reflect changes to remote file references.")

        # check if there are files flagged as only_in_manifests that have not had remote entries created for them
        normalized_updated_remote_files = set()
        for filename in updated_remote_files:
            normalized_updated_remote_files.add(os.path.normpath(filename))
        unresolved_manifest_files = list(set(only_in_manifests) - normalized_updated_remote_files)
        if unresolved_manifest_files:
            payload_consistent = False

        # check for fetch files that are simply missing from the payload
        unresolved_fetch_files = set(bag.files_to_be_fetched()) - set(bag.payload_files())
        if unresolved_fetch_files:
            payload_consistent = False
            if not quiet:
                logger.warning("The bag contains remote file references in fetch.txt that have not been resolved.")

        # check for size mismatches of local files that may have been fetched already
        for url, size, path in bag.fetch_entries():
            output_path = os.path.normpath(os.path.join(bag.path, path))
            if os.path.exists(output_path):
                local_size = os.path.getsize(output_path)
                try:
                    remote_size = int(size)
                except ValueError:
                    remote_size = -1
                if local_size != remote_size:
                    payload_consistent = False
                    if not quiet:
                        logger.warning("The size of the local file %s (%d bytes) does not match the size of the file "
                                       "(%s bytes) specified in fetch.txt." % (output_path, local_size, size))
    elif payload_consistent:
        payload_consistent = not (only_in_manifests or only_in_fetch)

    for path in only_in_manifests:
        e = bdbagit.FileMissing(path)
        if not quiet:
            logger.warning(
                "%s. Resolve this file reference by either 1) adding the missing file to the bag or 2) if the file is "
                "a payload file, adding a remote file reference in fetch.txt. or 3) re-run with the  \"update\" "
                "argument in order to remove this file from the bag manifest." % get_typed_exception(e))
    for path in only_on_fs:
        e = bdbagit.UnexpectedFile(path)
        if not quiet:
            logger.warning(
                "%s. Re-run with the \"update\" argument in order to add this file to the manifest."
                % get_typed_exception(e))
    for path in only_in_fetch:
        e = bdbagit.UnexpectedRemoteFile(path)
        if not quiet:
            logger.warning(
                "%s. Ensure that any remote file references from fetch.txt are also present in the manifest and "
                "re-run with the \"update\" argument in order to apply this change." % get_typed_exception(e))

    return payload_consistent


def should_update_manifests(bag, bag_algorithms, prune_manifests, remote_file_manifest):
    save_manifests = False

    if not prune_manifests:
        save_manifests = not all(x in bag.algorithms for x in bag_algorithms)
        if save_manifests:
            bag.algorithms = list(set(bag.algorithms).union(bag_algorithms))
    else:
        bag.algorithms = bag_algorithms
    if remote_file_manifest:
        bag.remote_entries.update(
            generate_remote_files_from_manifest(remote_file_manifest, bag.algorithms))
    skip_remote = True if not remote_file_manifest else False
    if prune_manifests:
        save_manifests = prune_bag_manifests(bag)
    if not save_manifests:
        save_manifests = not check_payload_consistency(bag, skip_remote, quiet=True)

    return save_manifests


def make_bag(bag_path,
             algs=None,
             update=False,
             save_manifests=True,
             prune_manifests=False,
             metadata=None,
             metadata_file=None,
             remote_file_manifest=None,
             config_file=DEFAULT_CONFIG_FILE,
             ro_metadata=None,
             ro_metadata_file=None):
    bag = None
    try:
        bag = bdbagit.BDBag(bag_path)
    except (bdbagit.BagError, bdbagit.BagValidationError):
        pass

    config = read_config(config_file)
    bag_config = config[BAG_CONFIG_TAG]
    bag_version = bag_config.get(BAG_SPEC_VERSION_TAG, DEFAULT_BAG_SPEC_VERSION)
    bag_algorithms = algs if algs else bag_config.get(BAG_ALGORITHMS_TAG, ['md5', 'sha256'])
    bag_processes = bag_config.get(BAG_PROCESSES_TAG, 1)

    # bag metadata merge order: config(if new, else if update use existing)->metadata_file->metadata
    if not update or (update and not os.path.isfile(os.path.join(bag_path, "bag-info.txt"))):
        # config metadata
        bag_metadata = bag_config.get(BAG_METADATA_TAG, {}).copy()
    else:
        bag_metadata = bag.info

    # file metadata
    bag_metadata.update(read_metadata(metadata_file))
    bag_ro_metadata = read_metadata(ro_metadata_file)

    # parameterized metadata
    if metadata:
        bag_metadata.update(metadata)
    if ro_metadata:
        bag_ro_metadata.update(ro_metadata)
    if bag_ro_metadata:
        bag_metadata.update({BAG_PROFILE_TAG: BDBAG_RO_PROFILE_ID})

    if 'Bagging-Date' not in bag_metadata:
        bag_metadata['Bagging-Date'] = date.strftime(date.today(), "%Y-%m-%d")

    if 'Bagging-Time' not in bag_metadata:
        bag_metadata['Bagging-Time'] = datetime.strftime(datetime.now(tz=get_localzone()), "%H:%M:%S %Z")

    if 'Bag-Software-Agent' not in bag_metadata:
        bag_metadata['Bag-Software-Agent'] = \
            'BDBag version: %s (Bagit version: %s) <%s>' % (VERSION, BAGIT_VERSION, PROJECT_URL)

    if bag:
        if update:
            try:
                logger.info("Updating bag: %s" % bag_path)
                bag.info.update(bag_metadata)
                manifests_update = should_update_manifests(bag, bag_algorithms, prune_manifests, remote_file_manifest)
                if manifests_update and not save_manifests:
                    logger.warning(
                        "Manifests must be updated due to bag payload change or checksum configuration change.")
                    save_manifests = True
                if bag_ro_metadata:
                    bdbro.serialize_bag_ro_metadata(bag_ro_metadata, bag_path)
                bag.save(bag_processes, manifests=save_manifests)
            except Exception as e:
                logger.error("Exception while updating bag manifests: %s", e)
                raise e
        else:
            logger.info("The directory %s is already a bag." % bag_path)
    # otherwise, create
    else:
        remote_files = None
        if remote_file_manifest:
            remote_files = generate_remote_files_from_manifest(remote_file_manifest, bag_algorithms)
        bag = bdbagit.make_bag(bag_path,
                               bag_info=bag_metadata,
                               processes=bag_processes,
                               checksums=bag_algorithms,
                               remote_entries=remote_files,
                               spec_version=bag_version)
        logger.info('Created bag: %s' % bag_path)
        if bag_ro_metadata:
            bdbro.serialize_bag_ro_metadata(bag_ro_metadata, bag_path)
            bag.save(bag_processes)
    return bag


def archive_bag(bag_path, bag_archiver):
    bag_archiver = bag_archiver.lower()

    try:
        validate_bag_structure(bag_path, skip_remote=True)
    except Exception as e:
        logger.error("Error while archiving bag: %s", e)
        raise e

    logger.info("Archiving bag (%s): %s" % (bag_archiver, bag_path))
    tarmode = None
    archive = None
    fn = '.'.join([os.path.basename(bag_path), bag_archiver])
    if bag_archiver == 'tar':
        tarmode = 'w'
    elif bag_archiver == 'tgz':
        tarmode = 'w:gz'
    elif bag_archiver == 'bz2':
        tarmode = 'w:bz2'
    elif bag_archiver == 'zip':
        zfp = os.path.join(os.path.dirname(bag_path), fn)
        zf = zipfile.ZipFile(zfp, 'w', compression=zipfile.ZIP_DEFLATED, allowZip64=True)
        for dirpath, dirnames, filenames in os.walk(bag_path):
            for name in filenames:
                filepath = os.path.normpath(os.path.join(dirpath, name))
                relpath = os.path.relpath(filepath, os.path.dirname(bag_path))
                if os.path.isfile(filepath):
                    zf.write(filepath, relpath)
        zf.close()
        archive = zf.filename
    else:
        raise RuntimeError("Archive format not supported for bag file: %s \n "
                           "Supported archive formats are ZIP or TAR/GZ/BZ2" % bag_path)

    if tarmode:
        tfp = os.path.join(os.path.dirname(bag_path), fn)
        t = tarfile.open(tfp, tarmode)
        t.add(bag_path, os.path.relpath(bag_path, os.path.dirname(bag_path)), recursive=True)
        t.close()
        archive = t.name

    logger.info('Created bag archive: %s' % archive)

    return archive


def extract_bag(bag_path, output_path=None, temp=False):
    if not os.path.exists(bag_path):
        raise RuntimeError("Specified bag path not found: %s" % bag_path)

    bag_dir = os.path.splitext(os.path.basename(bag_path))[0]
    if os.path.isfile(bag_path):
        if temp:
            output_path = tempfile.mkdtemp(prefix='bag_')
        elif not output_path:
            output_path = os.path.splitext(bag_path)[0]
            if os.path.exists(output_path):
                newpath = ''.join([output_path, '-', datetime.strftime(datetime.now(), "%Y-%m-%d_%H.%M.%S")])
                logger.info("Specified output path %s already exists, moving existing directory to %s" %
                            (output_path, newpath))
                shutil.move(output_path, newpath)
            output_path = os.path.dirname(bag_path)
        if zipfile.is_zipfile(bag_path):
            logger.info("Extracting ZIP archived bag file: %s" % bag_path)
            with open(bag_path, 'rb') as bag_file:
                zipped = zipfile.ZipFile(bag_file)
                zipped.extractall(output_path)
                zipped.close()
        elif tarfile.is_tarfile(bag_path):
            logger.info("Extracting TAR/GZ/BZ2 archived bag file: %s" % bag_path)
            tarred = tarfile.open(bag_path)
            tarred.extractall(output_path)
            tarred.close()
        else:
            raise RuntimeError("Archive format not supported for bag file: %s"
                               "\nSupported archive formats are ZIP or TAR/GZ/BZ2" % bag_path)

    extracted_path = os.path.join(output_path, bag_dir)
    logger.info("File %s was successfully extracted to directory %s" % (bag_path, extracted_path))

    return extracted_path


def validate_bag(bag_path, fast=False, callback=None, config_file=DEFAULT_CONFIG_FILE):
    config = read_config(config_file)
    bag_config = config['bag_config']
    bag_processes = bag_config.get('bag_processes', 1)

    try:
        logger.info("Validating bag: %s" % bag_path)
        bag = bdbagit.BDBag(bag_path)
        bag.validate(bag_processes if not callback else 1, fast=fast, callback=callback)
        logger.info("Bag %s is valid" % bag_path)
    except bdbagit.BagValidationError as e:
        logger.warning("BagValidationError: A BagValidationError may be transient if the bag contains unresolved "
                       "remote file references from a fetch.txt file. In this case the bag is incomplete but not "
                       "necessarily invalid. Resolve remote file references (if any) and re-validate.")
        raise e
    except bdbagit.BaggingInterruptedError as e:
        logger.warning(get_typed_exception(e))
        raise e
    except Exception as e:
        raise RuntimeError("Unhandled exception while validating bag: %s" % e)


def validate_bag_structure(bag_path, skip_remote=True):
    try:
        logger.info("Validating bag structure: %s" % bag_path)
        bag = bdbagit.BDBag(bag_path)
        if not check_payload_consistency(bag, skip_remote=skip_remote):
            raise bdbagit.BagValidationError("Inconsistent payload state. See log warnings for additional information.")
        logger.info("The directory %s is a valid bag structure" % bag_path)
    except Exception as e:
        logger.error("Error while validating bag structure: %s", e)
        raise e


def validate_bag_profile(bag_path, profile_path=None):

    logger.info("Validating bag profile: %s" % bag_path)
    bag = bdbagit.BDBag(bag_path)

    # Instantiate a profile, supplying its URI.
    if not profile_path:
        profile_path = bag.info.get(BAG_PROFILE_TAG, None)
        if not profile_path:
            raise bdbp.ProfileValidationError("Bag does not contain a BagIt-Profile-Identifier")

    logger.info("Retrieving profile: %s" % profile_path)
    profile = bdbp.Profile(profile_path)

    # Validate the profile.
    if profile.validate(bag):
        logger.info("Bag structure conforms to specified profile")
    else:
        raise bdbp.ProfileValidationError("Bag structure does not conform to specified profile")

    return profile


def validate_bag_serialization(bag_path, bag_profile=None, bag_profile_path=None):

    if not bag_profile:
        if not bag_profile_path:
            raise bdbp.ProfileValidationError(
                "Unable to instantiate profile, no bag profile or profile path found")
        logger.info("Retrieving profile: %s" % bag_profile_path)
        bag_profile = bdbp.Profile(bag_profile_path)

    # Validate 'Serialization' and 'Accept-Serialization'.
    logger.info("Validating bag serialization: %s" % bag_path)
    try:
        bag_profile.validate_serialization(bag_path)
        logger.info("Bag serialization conforms to specified profile")
    except Exception as e:
        logger.error("Bag serialization does not conform to specified profile. Error: %s" % e)
        raise e


def generate_remote_files_from_manifest(remote_file_manifest, algs, strict=False):
    logger.info("Generating remote file references from %s" % remote_file_manifest)
    remote_files = dict()
    with open(remote_file_manifest, "r") as rfm_in:
        line = rfm_in.readline().lstrip()
        rfm_in.seek(0)
        is_json_stream = False
        if line.startswith('{'):
            fetch = rfm_in
            is_json_stream = True
        else:
            fetch = json.load(rfm_in, object_pairs_hook=OrderedDict)
        try:
            for entry in fetch:
                if is_json_stream:
                    entry = json.loads(entry, object_pairs_hook=OrderedDict)

                filename = ''.join(['data', '/', entry['filename']])
                url = entry['url'][0] if isinstance(entry['url'], list) else entry['url']
                hash_provided = (bdbagit.CHECKSUM_ALGOS - set(entry.keys())) != bdbagit.CHECKSUM_ALGOS
                if not hash_provided:
                    raise ValueError("A remote file manifest entry did not provide a required hash value: %s" %
                                     json.dumps(entry))
                add = True
                for alg in bdbagit.CHECKSUM_ALGOS:
                    if alg in entry:
                        if strict and alg not in algs:
                            add = False
                        if add:
                            bdbagit.make_remote_file_entry(
                                remote_files, filename, url, entry['length'], alg, entry[alg])
        finally:
            rfm_in.close()

    return remote_files


def generate_ro_manifest(bag_path, overwrite=False, config_file=DEFAULT_CONFIG_FILE):
    bag = bdbagit.BDBag(bag_path)
    bag_ro_metadata_path = os.path.abspath(os.path.join(bag_path, "metadata", "manifest.json"))
    exists = os.path.isfile(bag_ro_metadata_path)
    if exists and not overwrite:
        logger.info("Auto-generating RO manifest: update existing file.")
        ro_metadata = bdbro.read_bag_ro_metadata(bag_path)
    else:
        logger.info("Auto-generating RO manifest: %s." %
                    "creating new file" if not exists else "overwrite existing file")
        ro_metadata = bdbro.init_ro_manifest(author_name=bag.info.get("Contact-Name"),
                                             author_orcid=bag.info.get("Contact-Orcid"),
                                             creator_name=bdbro.BAG_CREATOR_NAME,
                                             creator_uri=bdbro.BAG_CREATOR_URI)

    config = read_config(config_file)
    resolvers = config.get(ID_RESOLVER_TAG, DEFAULT_ID_RESOLVERS) if config else DEFAULT_ID_RESOLVERS
    fetched = bag.fetch_entries()
    local = bag.payload_files()

    for url, length, filename in fetched:
        if url.startswith("minid:") or url.startswith("ark:"):
            url = "".join(["http://", resolvers[0], "/", url])
        bdbro.add_file_metadata(ro_metadata,
                                source_url=url,
                                bundled_as=bdbro.make_bundled_as(
                                    folder=os.path.dirname(filename),
                                    filename=os.path.basename(filename)),
                                update_existing=True)

    for path in local:
        bdbro.add_file_metadata(ro_metadata,
                                local_path=path.replace("\\", "/"),
                                bundled_as=bdbro.make_bundled_as(),
                                update_existing=True)

    bdbro.write_bag_ro_metadata(ro_metadata, bag_path)
    profile = bag.info.get(BAG_PROFILE_TAG)
    if profile == BDBAG_PROFILE_ID:
        bag.info.update({BAG_PROFILE_TAG: BDBAG_RO_PROFILE_ID})
    bag.save()


def resolve_fetch(bag_path,
                  force=False,
                  callback=None,
                  keychain_file=DEFAULT_KEYCHAIN_FILE,
                  config_file=DEFAULT_CONFIG_FILE,
                  filter_expr=None,
                  **kwargs):
    bag = bdbagit.BDBag(bag_path)
    if force or not check_payload_consistency(bag, skip_remote=False, quiet=kwargs.get("quiet", True)):
        logger.info("Attempting to resolve remote file references from %s%s" %
                    (os.path.join(bag_path, "fetch.txt"),
                     "." if not filter_expr else ", using filter expression [%s]." % filter_expr))

        return fetch_bag_files(bag,
                               force=force,
                               keychain_file=keychain_file,
                               config_file=config_file,
                               callback=callback,
                               filter_expr=filter_expr,
                               **kwargs)
    else:
        return True


def materialize(input_path,
                output_path=None,
                fetch_callback=None,
                validation_callback=None,
                keychain_file=DEFAULT_KEYCHAIN_FILE,
                config_file=DEFAULT_CONFIG_FILE,
                filter_expr=None,
                force=False,
                **kwargs):

    configure_logging()
    bag_file = bag_path = None
    is_file, is_dir, is_uri = inspect_path(input_path)
    if is_file:
        bag_file = input_path
    elif is_dir:
        bag_path = input_path
    elif is_uri:
        bag_file = fetch_single_file(input_path,
                                     output_path,
                                     config_file=config_file,
                                     keychain_file=keychain_file,
                                     **kwargs)
        if not bag_file:
            raise RuntimeError("Unable to retrieve bag from: %s" % input_path)

    if bag_file:
        bag_path = extract_bag(bag_file)

    if bag_path:
        if not resolve_fetch(bag_path,
                             force=force,
                             callback=fetch_callback,
                             keychain_file=keychain_file,
                             config_file=config_file,
                             filter_expr=filter_expr,
                             **kwargs):
            logging.warning("One or more bag files were not fetched successfully.")

        validate_bag(bag_path, fast=False, callback=validation_callback, config_file=config_file)
