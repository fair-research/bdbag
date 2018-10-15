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
import json
from collections import OrderedDict
import bagit
from bagit import *
from bagit import _, _can_read, _can_bag, _make_tagmanifest_file, _encode_filename, _decode_filename, _calc_hashes,_walk
from bdbag import escape_uri, VERSION, BAGIT_VERSION, PROJECT_URL

LOGGER = logging.getLogger(__name__)

SUPPORTED_BAGIT_SPECS = ["0.97", "1.0"]


def parse_version(version):
    try:
        return tuple(int(i) for i in version.split(".", 1))
    except ValueError:
        raise BagError(
            _("Bag version numbers must be MAJOR.MINOR numbers, not %s") % version
        )


def make_bag(bag_dir,
             bag_info=None,
             processes=1,
             checksums=None,
             encoding='utf-8',
             remote_entries=None,
             spec_version="0.97"):
    """
    Convert a given directory into a bag. You can pass in arbitrary
    key/value pairs to put into the bag-info.txt metadata file as
    the bag_info dictionary.
    """

    if spec_version not in SUPPORTED_BAGIT_SPECS:
        raise RuntimeError(_("Unsupported BagIt specfication version: %s" % spec_version))
    bag_version = parse_version(spec_version)

    if checksums is None:
        checksums = DEFAULT_CHECKSUMS

    bag_dir = os.path.abspath(bag_dir)
    cwd = os.path.abspath(os.path.curdir)

    if cwd.startswith(bag_dir) and cwd != bag_dir:
        raise RuntimeError(_('Bagging a parent of the current directory is not supported'))

    LOGGER.info(_("Creating bag for directory %s"), bag_dir)

    if not os.path.isdir(bag_dir):
        LOGGER.error(_("Bag directory %s does not exist"), bag_dir)
        raise RuntimeError(_("Bag directory %s does not exist") % bag_dir)

    # FIXME: we should do the permissions checks before changing directories
    old_dir = os.path.abspath(os.path.curdir)

    try:
        # TODO: These two checks are currently redundant since an unreadable directory will also
        #       often be unwritable, and this code will require review when we add the option to
        #       bag to a destination other than the source. It would be nice if we could avoid
        #       walking the directory tree more than once even if most filesystems will cache it

        unbaggable = _can_bag(bag_dir)

        if unbaggable:
            LOGGER.error(_("Unable to write to the following directories and files:\n%s"), unbaggable)
            raise BagError(_("Missing permissions to move all files and directories"))

        unreadable_dirs, unreadable_files = _can_read(bag_dir)

        if unreadable_dirs or unreadable_files:
            if unreadable_dirs:
                LOGGER.error(_("The following directories do not have read permissions:\n%s"),
                             unreadable_dirs)
            if unreadable_files:
                LOGGER.error(_("The following files do not have read permissions:\n%s"),
                             unreadable_files)
            raise BagError(_("Read permissions are required to calculate file fixities"))
        else:
            LOGGER.info(_("Creating data directory"))

            # FIXME: if we calculate full paths we won't need to deal with changing directories
            os.chdir(bag_dir)
            cwd = os.getcwd()
            temp_data = tempfile.mkdtemp(dir=cwd)

            for f in os.listdir('.'):
                if os.path.abspath(f) == temp_data:
                    continue
                new_f = os.path.join(temp_data, f)
                LOGGER.info(_('Moving %(source)s to %(destination)s'), {'source': f, 'destination': new_f})
                os.rename(f, new_f)

            LOGGER.info(_('Moving %(source)s to %(destination)s'), {'source': temp_data, 'destination': 'data'})
            os.rename(temp_data, 'data')

            # permissions for the payload directory should match those of the
            # original directory
            os.chmod('data', os.stat(cwd).st_mode)

            strict = True if bag_version >= (1, 0) else False
            validate_remote_entries(remote_entries, bag_dir)
            total_bytes, total_files = make_manifests(
                'data', processes, algorithms=checksums, encoding=encoding, remote=remote_entries, strict=strict)

            _make_fetch_file(bag_dir, remote_entries)

            LOGGER.info(_("Creating bagit.txt"))
            txt = """BagIt-Version: %s\nTag-File-Character-Encoding: UTF-8\n""" % spec_version
            with open_text_file('bagit.txt', 'w') as bagit_file:
                bagit_file.write(txt)

            LOGGER.info(_("Creating bag-info.txt"))
            if bag_info is None:
                bag_info = {}

            # allow 'Bagging-Date' and 'Bag-Software-Agent' to be overidden
            if 'Bagging-Date' not in bag_info:
                bag_info['Bagging-Date'] = date.strftime(date.today(), "%Y-%m-%d")
            if 'Bag-Software-Agent' not in bag_info:
                bag_info['Bag-Software-Agent'] = \
                    'BDBag version: %s (Bagit version: %s) <%s>' % (VERSION, BAGIT_VERSION, PROJECT_URL)
            bag_info['Payload-Oxum'] = "%s.%s" % (total_bytes, total_files)
            _make_tag_file('bag-info.txt', bag_info)

            for c in checksums:
                _make_tagmanifest_file(c, bag_dir, encoding='utf-8')
    except Exception:
        LOGGER.error(_("An error occurred creating a bag in %s"), bag_dir)
        raise
    finally:
        os.chdir(old_dir)

    return BDBag(bag_dir)


def make_manifests(data_dir, processes, algorithms=DEFAULT_CHECKSUMS, encoding='utf-8', remote=None, strict=False):
    LOGGER.info(_('Using %(process_count)d processes to generate manifests: %(algorithms)s'),
                {'process_count': processes, 'algorithms': ', '.join(algorithms)})

    manifest_line_generator = partial(generate_manifest_lines, algorithms=algorithms)

    if processes > 1:
        pool = multiprocessing.Pool(processes=processes)
        checksums = pool.map(manifest_line_generator, _walk(data_dir))
        pool.close()
        pool.join()
    else:
        checksums = [manifest_line_generator(i) for i in _walk(data_dir)]

    # At this point we have a list of tuples which start with the algorithm name:
    manifest_data = {}
    for batch in checksums:
        for entry in batch:
            manifest_data.setdefault(entry[0], []).append(entry[1:])

    # These will be keyed on the algorithm name so we can perform sanity checks
    # below to catch failures in the hashing process:
    num_files = defaultdict(lambda: 0)
    total_bytes = defaultdict(lambda: 0)

    remote_entries = []
    if remote:
        LOGGER.info(_('Generating manifest lines for remote files'))
        sorted_remote_entries = OrderedDict(sorted(remote.items(), key=lambda t: t[0]))
        for filename, values in sorted_remote_entries.items():
            checksums = []
            remote_size = int(values['length'])
            for alg in CHECKSUM_ALGOS:
                if alg in values.keys():
                    checksums.append(
                        (alg, values[alg], _denormalize_filename(_decode_filename(filename)), remote_size))
            remote_entries.append(checksums)

    for batch in remote_entries:
        for entry in batch:
            manifest_data.setdefault(entry[0], []).append(entry[1:])

    file_entries = {}
    for algorithm, values in manifest_data.items():
        manifest_filename = 'manifest-%s.txt' % algorithm

        with open_text_file(manifest_filename, 'w', encoding=encoding) as manifest:
            for digest, filename, byte_count in values:
                manifest.write("%s  %s\n" % (digest, _encode_filename(filename)))
                num_files[algorithm] += 1
                total_bytes[algorithm] += byte_count
                file_entries[filename] = byte_count

    # We'll use sets of the values for the error checks and eventually return the payload oxum values:
    byte_value_set = set(total_bytes.values())
    file_count_set = set(num_files.values())

    # allow a bag with an empty payload
    if not byte_value_set and not file_count_set:
        return 0, 0

    if strict:
        if len(file_count_set) != 1:
            raise RuntimeError(_('Expected the same number of files for each checksum'))

        if len(byte_value_set) != 1:
            raise RuntimeError(_('Expected the same number of bytes for each checksum'))

        return byte_value_set.pop(), file_count_set.pop()

    byte_total = file_total = 0
    for file_size in file_entries.values():
        file_total += 1
        byte_total += file_size

    return byte_total, file_total


def validate_remote_entries(remote_entries, bag_path="."):
    if remote_entries:
        sorted_remote_entries = OrderedDict(sorted(remote_entries.items(), key=lambda t: t[0]))
        for filename, values in sorted_remote_entries.items():
            file_path = os.path.abspath(os.path.join(bag_path, filename))
            if os.path.isfile(file_path):
                error = \
                    "A remote file entry [%s] with metadata %s already exists in the bag payload directory at [%s]. " \
                    "Either remove the local file from the bag payload or remove the remote file entry and " \
                    "regenerate or update the bag." % (filename, json.dumps(remote_entries[filename]), file_path)
                raise BagManifestConflict(error)
            try:
                remote_size = int(values['length'])
            except Exception:
                raise ValueError(
                    "A specified remote file [%s] with metadata %s contains a non-integer file size: \"%s\". " % (
                        filename, json.dumps(remote_entries[filename]), values['length']))


def make_remote_file_entry(remote_entries, filename, url, length, alg, digest):
    entry = remote_entries.get(filename, None)
    if not entry:
        remote_entries[filename] = {'url': url, 'length': length}
    remote_entries[filename][alg] = digest


def _denormalize_filename(filename):
    if os.path.sep != '/':
        parts = filename.split(os.path.sep)
        filename = '/'.join(parts)
    return filename


def _make_fetch_file(path, remote_entries):
    fetch_file_path = os.path.join(path, "fetch.txt")
    if not remote_entries:
        if os.path.isfile(fetch_file_path):
            os.remove(fetch_file_path)
        return

    LOGGER.info('Writing fetch.txt')

    with open_text_file(fetch_file_path, 'w') as fetch_file:
        for filename in sorted(remote_entries.keys()):
            fetch_file.write("%s\t%s\t%s\n" %
                             (escape_uri(remote_entries[filename]['url']),
                              remote_entries[filename]['length'],
                              _denormalize_filename(filename)))


def _find_tag_files(bag_dir):
    for dir in os.listdir(bag_dir):
        if dir != 'data':
            if os.path.isfile(dir) and not dir.startswith('tagmanifest-'):
                yield dir
            for dir_name, _, filenames in os.walk(dir):
                for filename in filenames:
                    if filename.startswith('tagmanifest-'):
                        continue
                    # remove everything up to the bag_dir directory
                    p = os.path.join(dir_name, filename)
                    yield p


# monkeypatch bagit._find_tag_files with our version
bagit._find_tag_files = _find_tag_files


def _make_tag_file(bag_info_path, bag_info):
    headers = sorted(bag_info.keys())
    with open_text_file(bag_info_path, 'w') as f:
        for h in headers:
            values = bag_info[h]
            if not isinstance(values, list):
                values = [values]
            for txt in values:
                if isinstance(txt, dict):
                    LOGGER.warning(_("Nested dictionary content not supported in tag file: [%s]. "
                                     "Skipping element \"%s\" with value %s." %
                                     (bag_info_path, h, json.dumps(txt))))
                    continue
                # strip CR, LF and CRLF so they don't mess up the tag file
                txt = re.sub(r'\n|\r|(\r\n)', '', force_unicode(txt))
                f.write("%s: %s\n" % (h, txt))


# monkeypatch bagit._make_tag_file with our version
bagit._make_tag_file = _make_tag_file


class BaggingInterruptedError(RuntimeError):
    pass


class BagManifestConflict(BagError):
    pass


class UnexpectedRemoteFile(ManifestErrorDetail):
    def __str__(self):
        return _("%s exists in fetch.txt but is not in manifest") % self.path


class BDBag(Bag):

    def __init__(self, path=None):
        Bag.__init__(self, path)
        self.remote_entries = dict()

    def files_to_be_fetched(self, normalize=True):
        for f, size, path in self.fetch_entries():
            if normalize:
                yield os.path.normpath(path)
            else:
                yield path

    def compare_manifests_with_fs_and_fetch(self):
        # We compare the filenames after Unicode normalization so we can
        # reliably detect normalization changes after bag creation:
        files_on_fs = set(normalize_unicode(i) for i in self.payload_files())
        files_in_manifest = set(normalize_unicode(i) for i in self.payload_entries().keys())
        files_in_fetch = set(normalize_unicode(i) for i in self.files_to_be_fetched())

        if self.version_info >= (0, 97):
            files_in_manifest = files_in_manifest | set(self.missing_optional_tagfiles())

        only_on_fs = list()
        only_in_manifest = list()
        only_in_fetch = list(files_in_fetch - files_in_manifest)

        for i in files_in_manifest.difference(files_on_fs):
            if i not in files_in_fetch:
                only_in_manifest.append(self.normalized_manifest_names[i])

        for i in files_on_fs.difference(files_in_manifest):
            only_on_fs.append(self.normalized_filesystem_names[i])

        return only_in_manifest, only_on_fs, only_in_fetch

    def _sync_remote_entries_with_existing_fetch(self):
        payload_entries = self.payload_entries()
        for url, length, filename in self.fetch_entries():
            entry_path = os.path.normpath(filename.lstrip("*"))
            if entry_path in payload_entries:
                for alg in self.algorithms:
                    if payload_entries[entry_path].get(alg, None):
                        self.add_remote_file(filename, url, length, alg, payload_entries[entry_path][alg])

    def add_remote_file(self, filename, url, length, alg, digest):
        if alg not in self.algorithms:
            self.algorithms.append(alg)
        make_remote_file_entry(self.remote_entries, filename, url, length, alg, digest)

    def save(self, processes=1, manifests=False):
        """
        save will persist any changes that have been made to the bag
        metadata (self.info).

        If you have modified the payload of the bag (added, modified,
        removed files in the data directory) and want to regenerate manifests
        set the manifests parameter to True. The default is False since you
        wouldn't want a save to accidentally create a new manifest for
        a corrupted bag.

        If you want to control the number of processes that are used when
        recalculating checksums use the processes parameter.
        """
        # Error checking
        if not self.path:
            raise BagError(_('Bag.save() called before setting the path!'))

        if not os.access(self.path, os.R_OK | os.W_OK | os.X_OK):
            raise BagError(_('Cannot save bag to non-existent or inaccessible directory %s') % self.path)

        unbaggable = _can_bag(self.path)
        if unbaggable:
            LOGGER.error(_("Missing write permissions for the following directories and files:\n%s"),
                         unbaggable)
            raise BagError(_("Missing permissions to move all files and directories"))

        unreadable_dirs, unreadable_files = _can_read(self.path)
        if unreadable_dirs or unreadable_files:
            if unreadable_dirs:
                LOGGER.error(_("The following directories do not have read permissions:\n%s"),
                             unreadable_dirs)
            if unreadable_files:
                LOGGER.error(_("The following files do not have read permissions:\n%s"),
                             unreadable_files)
            raise BagError(_("Read permissions are required to calculate file fixities"))

        # Change working directory to bag directory so helper functions work
        old_dir = os.path.abspath(os.path.curdir)
        try:
            os.chdir(self.path)

            # Generate new manifest files
            if manifests:
                strict = True if (1, 0) >= self.version_info else False
                self._sync_remote_entries_with_existing_fetch()
                validate_remote_entries(self.remote_entries, self.path)
                total_bytes, total_files = make_manifests('data', processes,
                                                          algorithms=self.algorithms,
                                                          encoding=self.encoding,
                                                          remote=self.remote_entries,
                                                          strict=strict)

                # Update fetch.txt
                _make_fetch_file(self.path, self.remote_entries)

                # Update Payload-Oxum
                LOGGER.info(_('Updating Payload-Oxum in %s'), self.tag_file_name)
                self.info['Payload-Oxum'] = '%s.%s' % (total_bytes, total_files)

            _make_tag_file(self.tag_file_name, self.info)

            # Update tag-manifest for changes to manifest & bag-info files
            for alg in self.algorithms:
                _make_tagmanifest_file(alg, self.path, encoding=self.encoding)

            # Reload the manifests
            self._load_manifests()

        except Exception:
            LOGGER.error(_("An error occurred updating bag in %s"), self.path)
            raise

        finally:
            os.chdir(old_dir)

    def validate(self, processes=1, fast=False, completeness_only=False, callback=None):
        """Checks the structure and contents are valid.

        If you supply the parameter fast=True the Payload-Oxum (if present) will
        be used to check that the payload files are present and accounted for,
        instead of re-calculating fixities and comparing them against the
        manifest. By default validate() will re-calculate fixities (fast=False).
        """

        self._validate_structure()
        self._validate_bagittxt()

        self.validate_fetch()

        self._validate_contents(processes=processes, fast=fast, completeness_only=completeness_only, callback=callback)

        return True

    def validate_fetch(self):
        """Validate the fetch.txt file

        Raises `BagError` for errors and otherwise returns no value
        """
        for url, file_size, filename in self.fetch_entries():
            # fetch_entries will raise a BagError for unsafe filenames
            # so at this point we will check only that the URL is minimally
            # well formed:
            parsed_url = urlparse(url)

            # only check for a scheme component since per the spec the URL field is actually a URI per
            # RFC3986 (https://tools.ietf.org/html/rfc3986)
            if not all(parsed_url.scheme):
                raise BagError(_('Malformed URL in fetch.txt: %s') % url)

    def _validate_contents(self, processes=1, fast=False, completeness_only=False, callback=None):
        if fast and not self.has_oxum():
            raise BagValidationError(_('Fast validation requires bag-info.txt to include Payload-Oxum'))

        if fast:
            # Perform the fast file count + size check so we can fail early, but only if fast is specified:
            self._validate_oxum()
            return

        self._validate_completeness()

        if completeness_only:
            return

        self._validate_entries(processes, callback)

    def _validate_completeness(self):
        """
        Verify that the actual file manifests match the files in the data directory
        """
        errors = list()

        # First we'll make sure there's no mismatch between the filesystem
        # and the list of files in the manifest(s)
        only_in_manifests, only_on_fs, only_in_fetch = self.compare_manifests_with_fs_and_fetch()
        for path in only_in_manifests:
            e = FileMissing(path)
            LOGGER.warning(force_unicode(e))
            errors.append(e)
        for path in only_on_fs:
            e = UnexpectedFile(path)
            LOGGER.warning(force_unicode(e))
            errors.append(e)
        for path in only_in_fetch:
            e = UnexpectedRemoteFile(path)
            # this is non-fatal according to spec but the warning is still reasonable
            LOGGER.warning(force_unicode(e))

        if errors:
            raise BagValidationError(_("Bag validation failed"), errors)

    def _validate_entries(self, processes, callback=None):
        """
        Verify that the actual file contents match the recorded hashes stored in the manifest files
        """
        errors = list()

        if os.name == 'posix':
            worker_init = posix_multiprocessing_worker_initializer
        else:
            worker_init = None

        args = ((self.path,
                 self.normalized_filesystem_names.get(rel_path, rel_path),
                 hashes,
                 self.algorithms) for rel_path, hashes in self.entries.items())

        try:
            if processes == 1:
                count = 0
                hash_results = []
                totalHashes = len(self.entries.items())
                for i in args:
                    hash_results.append(_calc_hashes(i))
                    count += 1
                    if callback:
                        if not callback(count, totalHashes):
                            raise BaggingInterruptedError("Bag validation interrupted!")

            else:
                pool = None
                try:
                    pool = multiprocessing.Pool(processes if processes else None, initializer=worker_init)
                    hash_results = pool.map(_calc_hashes, args)
                finally:
                    if pool:
                        pool.terminate()
        except BaggingInterruptedError:
            raise
        # Any unhandled exceptions are probably fatal
        except:
            LOGGER.error(_("Unable to calculate file hashes for %s"), self)
            raise

        for rel_path, f_hashes, hashes in hash_results:
            for alg, computed_hash in f_hashes.items():
                stored_hash = hashes[alg]
                if stored_hash.lower() != computed_hash:
                    e = ChecksumMismatch(rel_path, alg, stored_hash.lower(), computed_hash)
                    LOGGER.warning(force_unicode(e))
                    errors.append(e)

        if errors:
            raise BagValidationError(_("Bag validation failed"), errors)
