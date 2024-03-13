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
import io
import errno
import logging
import json
import shutil
import stat
import time
import tempfile
import tarfile
import gzip
from zipfile import ZipFile, ZipInfo, ZIP_DEFLATED, ZIP_STORED, is_zipfile
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


def configure_logging(level=logging.INFO, logpath=None, filemode='a', log_format=DEFAULT_LOG_FORMAT, force=False):
    logging.captureWarnings(True)
    if logpath:
        if sys.version_info > (3, 8):
            logging.basicConfig(filename=logpath, filemode=filemode, level=level, format=log_format, force=force)
        else:
            logging.basicConfig(filename=logpath, filemode=filemode, level=level, format=log_format)
    else:
        if sys.version_info > (3, 8):
            logging.basicConfig(level=level, format=log_format, force=force)
        else:
            logging.basicConfig(level=level, format=log_format)


def read_metadata(metadata_file):
    if not metadata_file:
        return dict()
    else:
        metadata_file = os.path.abspath(metadata_file)

    logger.info("Reading bag metadata from file: %s" % metadata_file)
    with io.open(metadata_file, encoding='utf-8') as mf:
        metadata = mf.read()
        mf.close()
        return json.loads(metadata, object_pairs_hook=OrderedDict)


def cleanup_bag(bag_path, save=False):
    logger.info("Cleaning up bag dir: %s" % bag_path)
    if save:
        return safe_move(bag_path)
    else:
        shutil.rmtree(bag_path)
        return None


def ensure_bag_path_exists(bag_path, save=True):
    saved_bag_path = None
    if os.path.exists(bag_path):
        saved_bag_path = cleanup_bag(bag_path, save)
    if not os.path.exists(bag_path):
        logger.info("Creating bag directory: %s" % bag_path)
        os.makedirs(bag_path)

    return saved_bag_path


def revert_bag(bag_path):
    if not is_bag(bag_path):
        logger.warning("Cannot revert the bag %s because it is not a bag directory!" % bag_path)
        return

    for path in os.listdir(bag_path):
        if os.path.basename(os.path.abspath(path)) != 'data':
            if path.startswith(("bag-info", "bagit", "fetch", "manifest-", "tagmanifest-")):
                os.remove(os.path.join(bag_path, path))

    data_path = os.path.join(bag_path, 'data')
    if os.path.isdir(data_path):
        for path in os.listdir(data_path):
            old_path = os.path.join(data_path, path)
            new_path = os.path.join(bag_path, path)
            logger.debug("Bag revert: moving payload file %s to %s", old_path, new_path)
            os.rename(old_path, new_path)
        os.rmdir(data_path)
    else:
        logger.warning("Bag directory %s does not contain a \"data\" directory to revert." % bag_path)
    logger.info("Bag directory %s has been reverted back to a normal directory." % bag_path)


def prune_bag_manifests(bag):
    manifests_pruned = False
    manifests = list(bag.manifest_files())
    manifests += list(bag.tagmanifest_files())
    for manifest in manifests:
        if manifest.find("tagmanifest-") != -1:
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
        if os.path.isdir(bag_path):
            bag = bdbagit.BDBag(bag_path)
    except (bdbagit.BagError, bdbagit.BagValidationError) as e:  # pragma: no cover
        logger.warning("Exception while checking if directory %s is a bag: %s" % (bag_path, e))
    return True if bag else False


def check_payload_consistency(bag, skip_remote=False, quiet=False):
    logger.info("Checking payload consistency. This can take some time for large bags with many payload files...")

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
        unresolved_fetch_files = list(set(bag.files_to_be_fetched()) - set(bag.payload_files()))
        if unresolved_fetch_files:
            payload_consistent = False
            if not quiet:
                logger.warning("The bag contains remote file references in fetch.txt that have not been resolved: [%s]"
                               % (", ".join(unresolved_fetch_files) if len(unresolved_fetch_files) > 1 else
                                  unresolved_fetch_files[0]))

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
             config_file=None,
             ro_metadata=None,
             ro_metadata_file=None,
             idempotent=None):
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
    idempotent_config = bag_config.get(BAG_ARCHIVE_IDEMPOTENT, False)
    idempotent = idempotent_config if (idempotent_config and idempotent is None) else \
        False if idempotent is None else idempotent

    if idempotent and (ro_metadata or ro_metadata_file):
        logger.warning("Bag idempotency cannot be guaranteed when ro-metadata is present.")

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

    if idempotent:
        if 'Bagging-Date' in bag_metadata:
            logger.warning(
                "Bagging-Date metadata is not compatible with Bag idempotency. Removing Bagging-Date attribute.")
            del bag_metadata["Bagging-Date"]
        if 'Bagging-Time' in bag_metadata:
            logger.warning(
                "Bagging-Time metadata is not compatible with Bag idempotency. Removing Bagging-Time attribute.")
            del bag_metadata["Bagging-Time"]
    else:
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


def archive_bag(bag_path, bag_archiver, config_file=None, idempotent=None):
    bag_archiver = bag_archiver.lower()
    bag_path = bag_path.rstrip(os.path.sep)

    config = read_config(config_file)
    idempotent_config = config[BAG_CONFIG_TAG].get(BAG_ARCHIVE_IDEMPOTENT, False)
    idempotent = idempotent_config if (idempotent_config and idempotent is None) else \
        False if idempotent is None else idempotent

    try:
        validate_bag_structure(bag_path, skip_remote=True)
    except Exception as e:
        logger.error("Error while archiving bag: %s", e)
        raise e

    logger.info("Archiving bag (%s): %s" % (bag_archiver, bag_path))
    if idempotent:
        logger.debug("Creating idempotent (reproducible) %s formatted bag archive." % bag_archiver)
    tarmode = None
    archive = None
    fn = '.'.join([os.path.basename(bag_path), bag_archiver])
    if bag_archiver == 'tar':
        tarmode = 'w'
    elif bag_archiver == 'tgz':
        tarmode = 'w:gz'
    elif bag_archiver == 'bz2':
        tarmode = 'w:bz2'
    elif bag_archiver == 'xz' and sys.version_info >= (3, 3):
        tarmode = 'w:xz'
    elif bag_archiver == 'zip':
        zfp = os.path.join(os.path.dirname(bag_path), fn)
        archive = zip_bag_dir(bag_path, zfp, idempotent)
    else:
        raise RuntimeError("Archive format not supported for bag file: %s \n "
                           "Supported archive formats are ZIP or TAR/GZ/BZ2%s" %
                           (bag_path,  ("/XZ" if sys.version_info >= (3, 3) else "")))

    if tarmode:
        archive = tar_bag_dir(bag_path, fn, tarmode, idempotent)

    logger.info('Created bag archive: %s' % archive)

    return archive


def tar_bag_dir(bag_path, tar_file_path, tarmode, idempotent=False):

    def filter_mtime(tarinfo):
        # a fixed mtime is a core requirement for a reproducible archive
        tarinfo.mtime = 0
        return tarinfo

    is_idempotent_tgz = False
    if idempotent and tarmode == 'w:gz':
        is_idempotent_tgz = True
        tarmode = 'w'
        tar_file_path = '.'.join([os.path.basename(bag_path), "tar"])

    tfp = os.path.join(os.path.dirname(bag_path), tar_file_path)
    t = tarfile.open(tfp, tarmode)
    t.add(bag_path,
          os.path.relpath(bag_path, os.path.dirname(bag_path)),
          recursive=True,
          filter=filter_mtime if idempotent else None)
    t.close()
    archive = t.name

    # TGZ is a special case which we have to GZIP separately because we can't pass through the needed mtime=0 argument
    # via the tarfile API - this is obviously less efficient than performing a tar|gzip in a single pass but oh well.
    if is_idempotent_tgz:
        archive = os.path.splitext(t.name)[0] + ".tgz"
        with io.open(t.name, 'rb') as f_in, io.open(archive, 'wb') as f_out:
            with gzip.GzipFile(filename=t.name, mode='wb', fileobj=f_out, mtime=0) as gzf:
                while True:
                    chunk = f_in.read(io.DEFAULT_BUFFER_SIZE)
                    if not chunk:
                        break
                    gzf.write(chunk)
                gzf.flush()
        os.remove(t.name)

    return archive


def zip_bag_dir(bag_path, zip_file_path, idempotent=False):
    # The majority of this code came from https://fekir.info/post/reproducible-zip-archives/ with the exception of the
    # buffered writing of file entries (instead of ZipFile.writestr) which was added for scalability reasons.
    zipfile = ZipFile(zip_file_path, 'w', ZIP_DEFLATED, allowZip64=True)
    entries = []
    for root, dirs, files in os.walk(bag_path):
        for d in dirs:
            entries.append(os.path.relpath(os.path.join(root, d), os.path.dirname(bag_path)) + os.path.sep)
        for f in files:
            entries.append(os.path.relpath(os.path.join(root, f), os.path.dirname(bag_path)))
    entries.sort()
    for e in entries:
        filepath = os.path.join(os.path.dirname(bag_path), e)
        if sys.version_info < (3,):
            zipfile.write(filepath, e)
        else:
            if idempotent:
                # a fixed mtime is a core requirement for a reproducible archive
                date_time = (1980, 1, 1, 0, 0, 0)
            else:
                st = os.stat(filepath)
                mtime = time.localtime(st.st_mtime)
                date_time = mtime[0:6]
            info = ZipInfo(
                filename=e,
                date_time=date_time
            )
            info.create_system = 3  # unix
            if e.endswith(os.path.sep):
                info.external_attr = 0o40755 << 16 | 0x010
                info.compress_type = ZIP_STORED
                info.CRC = 0  # unclear why necessary, maybe a bug?
                zipfile.writestr(info, b'')
            else:
                info.external_attr = 0o100644 << 16
                info.compress_type = ZIP_DEFLATED
                with io.open(filepath, 'rb') as data, zipfile.open(info, 'w') as out:
                    while True:
                        chunk = data.read(io.DEFAULT_BUFFER_SIZE)
                        if not chunk:
                            break
                        out.write(chunk)
                    out.flush()
    zipfile.close()
    return zipfile.filename


def extract_bag(bag_path, output_path=None, temp=False, config_file=None):
    if not os.path.exists(bag_path):
        raise RuntimeError("Specified bag path not found: %s" % bag_path)

    # check for unfiltered TAR extraction override
    config = read_config(config_file)
    allow_unfiltered_tar_extraction = config.get(ENABLE_UNFILTERED_TAR_EXTRACTION_TAG, False)

    # determine output path for extraction
    base_path = extracted_path = None
    bag_dir = os.path.splitext(os.path.basename(bag_path))[0]
    if os.path.isfile(bag_path):
        if temp:
            base_path = tempfile.mkdtemp(prefix='bag_')
        elif output_path:
            base_path = os.path.realpath(output_path)
        elif not output_path:
            base_path = os.path.dirname(os.path.splitext(bag_path)[0])

        # extraction preflight
        if is_zipfile(bag_path):
            logger.info("Extracting ZIP archived file: %s" % bag_path)
            archive = ZipFile(bag_path)
            files = archive.namelist()
        elif tarfile.is_tarfile(bag_path):
            logger.info("Extracting TAR/GZ/BZ2%s archived file: %s" %
                        (bag_path,  ("/XZ" if sys.version_info >= (3, 3) else "")))
            archive = tarfile.open(bag_path)
            files = archive.getnames()
        else:
            raise RuntimeError("Archive format not supported for file: %s\n"
                               "Supported archive formats are ZIP or TAR/GZ/BZ2%s" %
                               (bag_path,  ("/XZ" if sys.version_info >= (3, 3) else "")))
        archived_bag_dir = bag_parent_dir_from_archive(files)
        extracted_path = os.path.join(base_path, archived_bag_dir or bag_dir)
        output_path = os.path.join(output_path, extracted_path or bag_dir) if output_path else None
        safe_move(extracted_path, output_path)

        # Perform the extraction - use "data" filter with tarfile, if available. See https://peps.python.org/pep-0706.
        # If data filter not available, abort execution unless "allow_unfiltered_tar_extraction" is enabled in config.
        try:
            if isinstance(archive, tarfile.TarFile):
                if hasattr(tarfile, 'data_filter'):
                    # customize tarfile 'data' filter: if we encounter a tarinfo entry with a mtime of 0 (epoch), then
                    # set mtime to None which will cause tarfile to suppress preserving the mtime for the extracted file
                    def tar_data_filter(entry, path):
                        if entry.mtime == 0:
                            entry.mtime = None
                        return tarfile.data_filter(entry, path)
                    archive.extractall(base_path, filter=tar_data_filter)
                else:
                    if isinstance(archive, tarfile.TarFile):
                        logger.warning('SECURITY WARNING: TAR extraction may be unsafe; consider updating Python to a '
                                       'version which has been patched to address this vulnerability. '
                                       'See: https://nvd.nist.gov/vuln/detail/CVE-2007-4559')
                        if allow_unfiltered_tar_extraction:
                            archive.extractall(base_path)
                        else:
                            raise RuntimeError(
                                "TAR archive extraction has been disabled because the TAR 'extraction filters' feature "
                                "is not present in the current Python version. Python versions 3.8 through 3.11 "
                                "require an update that contains a back-port of this feature: the minimum versions are "
                                "3.8.17, 3.9.17, 3.10.12, and 3.11.4. Python versions 3.12 and above contain this "
                                "feature by default. Earlier Python versions (3.7 and prior) are unsupported. To "
                                "disable this security policy enforcement (not recommended), set "
                                "'allow_unfiltered_tar_extraction: true' in your 'bdbag.json' configuration file. "
                                "Please consider upgrading your Python to a newer version containing a back-port of "
                                "this important security fix.")
            else:
                # zipfile - which already sanitizes path names and doesn't have the same vulnerabilities as tar
                archive.extractall(base_path)
        finally:
            archive.close()

    logger.info("File %s was successfully extracted to directory %s" % (bag_path, extracted_path))

    return extracted_path


def validate_bag(bag_path, fast=False, callback=None, config_file=None):
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
    except (bdbagit.BagError, bdbagit.BaggingInterruptedError) as e:
        logger.warning(get_typed_exception(e))
        raise e
    except Exception as e:  # pragma: no cover
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
    logger.info("Validating bag profile: %s", bag_path)
    bag = bdbagit.BDBag(bag_path)

    # Instantiate a profile, supplying its URI.
    profile_url = bag.info.get(BAG_PROFILE_TAG, None)
    if not profile_url:
        raise bdbp.ProfileValidationError("Bag does not contain a BagIt-Profile-Identifier")
    logger.info("Loading profile: %s" % (profile_path if profile_path else profile_url))

    profile = None
    if profile_path:
        try:
            with io.open(profile_path, encoding="UTF-8") as profile_file:
                profile = json.loads(profile_file.read())
        except (OSError, IOError, ValueError) as exc:
            raise bdbp.ProfileValidationError("Profile %s could not be read: %s" % (profile_path, exc))

    profile = bdbp.BDBProfile(profile_url, profile)

    # Validate the profile.
    if profile.validate(bag):
        logger.info("Bag structure conforms to specified profile")
    else:
        raise bdbp.ProfileValidationError("Bag structure does not conform to specified profile: %s" % profile.report)

    return profile


def validate_bag_serialization(bag_path, bag_profile=None, bag_profile_path=None):

    if not bag_profile:
        if not bag_profile_path:
            raise bdbp.ProfileValidationError(
                "Unable to instantiate profile, no bag profile or profile path found")
        logger.info("Retrieving profile: %s" % bag_profile_path)
        bag_profile = bdbp.BDBProfile(bag_profile_path)

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
    with io.open(remote_file_manifest, "r", encoding='utf-8') as rfm_in:
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


def generate_ro_manifest(bag_path, overwrite=False, config_file=None):
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
                  config_file=None,
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
                config_file=None,
                filter_expr=None,
                force=False,
                **kwargs):

    bag_file = bag_path = None
    is_file, is_dir, is_uri = inspect_path(input_path)
    if is_file:
        bag_file = input_path
    elif is_dir:
        bag_path = input_path
    elif is_uri:
        output_file_path = os.path.join(output_path,
                                        urlunquote(os.path.basename(
                                            urlsplit(input_path).path))) if output_path else None
        bag_file = fetch_single_file(input_path,
                                     output_file_path,
                                     config_file=config_file,
                                     keychain_file=keychain_file,
                                     **kwargs)
        if not bag_file:
            raise RuntimeError("Unable to retrieve bag from: %s" % input_path)

    if bag_file:
        bag_path = extract_bag(bag_file, output_path)

    if bag_path:
        if not is_bag(bag_path):
            logger.info("The directory [%s] is not a valid bag directory. "
                        "Only a properly structured bag directory can be fully materialized." % bag_path)
            return bag_path

        if not resolve_fetch(bag_path,
                             force=force,
                             callback=fetch_callback,
                             keychain_file=keychain_file,
                             config_file=config_file,
                             filter_expr=filter_expr,
                             **kwargs):
            logger.warning("One or more bag files were not fetched successfully.")

        validate_bag(bag_path, fast=False, callback=validation_callback, config_file=config_file)

    return bag_path
