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
import sys
import json
import shutil
import logging
import mock
import unittest
from os.path import join as ospj
from os.path import exists as ospe
from os.path import isfile as ospif
from bdbag import bdbag_api as bdb, bdbag_config as bdbcfg, bdbag_ro as bdbro, bdbagit as bdbagit, filter_dict, \
    get_typed_exception
from bdbag.fetch.auth import keychain
from test.test_common import BaseTest

if sys.version_info > (3,):
    from io import StringIO
else:
    from StringIO import StringIO

logger = logging.getLogger()


class TestAPI(BaseTest):

    def setUp(self):
        super(TestAPI, self).setUp()
        self.stream = StringIO()
        self.handler = logging.StreamHandler(self.stream)
        logger.addHandler(self.handler)

    def tearDown(self):
        self.stream.close()
        logger.removeHandler(self.handler)
        super(TestAPI, self).tearDown()

    def test_create_config(self):
        logger.info(self.getTestHeader('create config'))
        try:
            config_file = ospj(self.test_config_dir, ".bdbag", 'bdbag.json')
            bdbcfg.write_config(config_file=config_file)
        except Exception as e:
            self.fail(get_typed_exception(e))

    def test_read_with_create_default_config(self):
        logger.info(self.getTestHeader('read config with create default if missing'))
        try:
            config_file = ospj(self.test_config_dir, ".bdbag", 'bdbag.json')
            bdbcfg.read_config(config_file=config_file)
        except Exception as e:
            self.fail(get_typed_exception(e))

    def test_read_with_update_base_config(self):
        logger.info(self.getTestHeader('read config with auto-upgrade version'))
        try:
            config_file = ospj(self.test_config_dir, 'base-config.json')
            bdbcfg.read_config(config_file=config_file, auto_upgrade=True)
        except Exception as e:
            self.fail(get_typed_exception(e))

    def test_create_keychain(self):
        logger.info(self.getTestHeader('create keychain'))
        try:
            keychain_file = ospj(self.test_config_dir, ".bdbag", 'keychain.json')
            keychain.write_keychain(keychain_file=keychain_file)
        except Exception as e:
            self.fail(get_typed_exception(e))

    def test_read_with_create_default_keychain(self):
        logger.info(self.getTestHeader('read keychain with create default if missing'))
        try:
            keychain_file = ospj(self.test_config_dir, ".bdbag", 'keychain.json')
            keychain.read_keychain(keychain_file=keychain_file)
        except Exception as e:
            self.fail(get_typed_exception(e))

    def test_read_with_create_default_keychain_location(self):
        logger.info(self.getTestHeader('test read keychain with create default location'))
        try:
            default_keychain_path = ospj(self.test_config_dir, ".bdbag")
            default_keychain_file = ospj(default_keychain_path, 'keychain.json')
            patched_default_config = mock.patch.multiple(
                "bdbag.fetch.auth.keychain",
                DEFAULT_KEYCHAIN_FILE=default_keychain_file)

            patched_default_config.start()
            keychain.read_keychain(keychain_file=default_keychain_file)
            patched_default_config.stop()
        except Exception as e:
            self.fail(get_typed_exception(e))

    def test_bootstrap_config(self):
        logger.info(self.getTestHeader('test bootstrap config'))
        try:
            config_file = ospj(self.test_config_dir, ".bdbag", 'bdbag.json')
            keychain_file = ospj(self.test_config_dir, ".bdbag", 'keychain.json')
            bdbcfg.bootstrap_config(config_file=config_file, keychain_file=keychain_file, base_dir=self.test_config_dir)
        except Exception as e:
            self.fail(get_typed_exception(e))

    def test_bootstrap_config_with_upgrade(self):
        logger.info(self.getTestHeader('test bootstrap config with upgrade'))
        try:
            config_file = ospj(self.test_config_dir, 'base-config.json')
            keychain_file = ospj(self.test_config_dir, ".bdbag", 'keychain.json')
            bdbcfg.bootstrap_config(config_file=config_file, keychain_file=keychain_file, base_dir=self.test_config_dir)
        except Exception as e:
            self.fail(get_typed_exception(e))

    def test_create_bag(self):
        logger.info(self.getTestHeader('create bag'))
        try:
            bag = bdb.make_bag(self.test_data_dir)
            self.assertIsInstance(bag, bdbagit.BDBag)
        except Exception as e:
            self.fail(get_typed_exception(e))

    def test_cleanup_bag(self):
        logger.info(self.getTestHeader('cleanup bag'))
        try:
            bdb.cleanup_bag(self.test_bag_dir)
            self.assertFalse(ospe(self.test_bag_dir), "Failed to cleanup bag directory")
        except Exception as e:
            self.fail(get_typed_exception(e))

    def test_ensure_bag_path_exists(self):
        logger.info(self.getTestHeader('ensure bag path exists, save existing'))
        try:
            saved_bag_path = bdb.ensure_bag_path_exists(self.test_bag_dir)
            self.assertTrue(ospe(self.test_bag_dir), "Bag directory does not exist")
            self.assertTrue(ospe(saved_bag_path), "Saved bag path does not exist")
        except Exception as e:
            self.fail(get_typed_exception(e))

    def test_ensure_bag_path_exists_delete_existing(self):
        logger.info(self.getTestHeader('ensure bag path exists, delete existing'))
        try:
            bdb.ensure_bag_path_exists(self.test_bag_dir, save=False)
            self.assertTrue(ospe(self.test_bag_dir), "Bag directory does not exist")
        except Exception as e:
            self.fail(get_typed_exception(e))

    def test_create_bag_with_config(self):
        logger.info(self.getTestHeader('create bag with config'))
        try:
            bag = bdb.make_bag(self.test_data_dir,
                               config_file=(ospj(self.test_config_dir, 'test-config.json')))
            self.assertIsInstance(bag, bdbagit.BDBag)
            self.assertFalse(ospif(ospj(self.test_data_dir, 'manifest-sha1.txt')))
            self.assertFalse(ospif(ospj(self.test_data_dir, 'manifest-sha256.txt')))
            self.assertFalse(ospif(ospj(self.test_data_dir, 'manifest-sha512.txt')))
            self.assertFalse(ospif(ospj(self.test_data_dir, 'tagmanifest-sha1.txt')))
            self.assertFalse(ospif(ospj(self.test_data_dir, 'tagmanifest-sha256.txt')))
            self.assertFalse(ospif(ospj(self.test_data_dir, 'tagmanifest-sha512.txt')))
            baginfo = ospj(self.test_data_dir, 'bag-info.txt')
            with open(baginfo) as bi:
                baginfo_txt = bi.read()
            self.assertIn('Contact-Name: bdbag test', baginfo_txt)
        except Exception as e:
            self.fail(get_typed_exception(e))

    def test_revert_bag(self):
        logger.info(self.getTestHeader('revert bag'))
        try:
            bdb.revert_bag(self.test_bag_dir)
            self.assertFalse(ospif(ospj(self.test_bag_dir, 'bag-info.txt')))
            self.assertFalse(ospif(ospj(self.test_bag_dir, 'bagit.txt')))
            self.assertFalse(ospif(ospj(self.test_bag_dir, 'manifest-sha1.txt')))
            self.assertFalse(ospif(ospj(self.test_bag_dir, 'manifest-md5.txt')))
            self.assertFalse(ospif(ospj(self.test_bag_dir, 'manifest-sha1.txt')))
            self.assertFalse(ospif(ospj(self.test_bag_dir, 'manifest-sha256.txt')))
            self.assertFalse(ospif(ospj(self.test_bag_dir, 'manifest-sha512.txt')))
            self.assertFalse(ospif(ospj(self.test_bag_dir, 'tagmanifest-md5.txt')))
            self.assertFalse(ospif(ospj(self.test_bag_dir, 'tagmanifest-sha1.txt')))
            self.assertFalse(ospif(ospj(self.test_bag_dir, 'tagmanifest-sha256.txt')))
            self.assertFalse(ospif(ospj(self.test_bag_dir, 'tagmanifest-sha512.txt')))
            self.assertTrue(ospif(ospj(self.test_bag_dir, 'README.txt')))
            self.assertTrue(ospif(ospj(self.test_bag_dir, ospj('test1', 'test1.txt'))))
            self.assertTrue(ospif(ospj(self.test_bag_dir, ospj('test2', 'test2.txt'))))
            self.assertFalse(ospe(ospj(self.test_bag_dir, 'data')))
        except Exception as e:
            self.fail(get_typed_exception(e))

    def test_revert_non_bag(self):
        logger.info(self.getTestHeader('revert bag'))
        try:
            bdb.revert_bag(self.test_data_dir)
            output = self.stream.getvalue()
            self.assertExpectedMessages(["Cannot revert the bag %s because it is not a bag directory!"], output)
        except Exception as e:
            self.fail(get_typed_exception(e))

    def test_update_bag_add_file(self):
        logger.info(self.getTestHeader('update bag add file'))
        try:
            with open(ospj(self.test_bag_dir, 'data', 'NEWFILE.txt'), 'w') as nf:
                nf.write('Additional file added via unit test.')
            bag = bdb.make_bag(self.test_bag_dir, update=True)
            output = self.stream.getvalue()
            self.assertIsInstance(bag, bdbagit.BDBag)
            self.assertExpectedMessages(['NEWFILE.txt'], output)
        except Exception as e:
            self.fail(get_typed_exception(e))

    def test_update_bag_remove_file(self):
        logger.info(self.getTestHeader('update bag remove file'))
        try:
            os.remove(ospj(self.test_bag_dir, 'data', 'test1', 'test1.txt'))
            bag = bdb.make_bag(self.test_bag_dir, update=True)
            output = self.stream.getvalue()
            self.assertIsInstance(bag, bdbagit.BDBag)
            self.assertUnexpectedMessages(['test1.txt'], output)
        except Exception as e:
            self.fail(get_typed_exception(e))

    def test_update_bag_change_file(self):
        logger.info(self.getTestHeader('update bag change file'))
        try:
            with open(ospj(self.test_bag_dir, 'data', 'README.txt'), 'a') as f:
                f.writelines('Additional data added via unit test.')
            bag = bdb.make_bag(self.test_bag_dir, update=True)
            output = self.stream.getvalue()
            self.assertIsInstance(bag, bdbagit.BDBag)
            self.assertExpectedMessages(['README.txt'], output)
        except Exception as e:
            self.fail(get_typed_exception(e))

    def test_update_bag_change_file_with_skip_override(self):
        logger.info(self.getTestHeader('update bag change file with no save manifest attempt'))
        try:
            bag = bdb.make_bag(self.test_bag_dir, algs=["md5"], update=True, prune_manifests=True, save_manifests=False)
            output = self.stream.getvalue()
            self.assertIsInstance(bag, bdbagit.BDBag)
            self.assertExpectedMessages(['Manifests must be updated due to bag payload change'], output)
        except Exception as e:
            self.fail(get_typed_exception(e))

    def _test_create_or_update_bag_with_metadata(
            self, update=False, override_file_metadata=False, no_file_metadata=False):
        try:
            metadata_param = None if not override_file_metadata else {"Contact-Name": "nobody"}
            ro_metadata_param = None if not override_file_metadata else {
                "manifest.json": {
                    "@context": ["https://w3id.org/bundle/context"],
                    "@id": "../"
                }
            }
            bag_dir = self.test_bag_dir if update else self.test_data_dir
            bag = bdb.make_bag(bag_dir,
                               update=update,
                               metadata=metadata_param,
                               metadata_file=None if no_file_metadata else
                               ospj(self.test_config_dir, 'test-metadata.json'),
                               ro_metadata=ro_metadata_param,
                               ro_metadata_file=None if no_file_metadata else
                               ospj(self.test_config_dir, 'test-ro-metadata.json'))
            output = self.stream.getvalue()
            self.assertIsInstance(bag, bdbagit.BDBag)
            bag_info_txt = self.slurp_text_file(ospj(bag_dir, 'bag-info.txt')).splitlines()
            if override_file_metadata:
                self.assertIn('Contact-Name: nobody', bag_info_txt)
            if not no_file_metadata:
                self.assertExpectedMessages(['Reading bag metadata from file', 'test-metadata.json'], output)
                self.assertExpectedMessages(['Reading bag metadata from file', 'test-ro-metadata.json'], output)
                self.assertIn('External-Description: Simple bdbag test', bag_info_txt)
                ro_manifest_file = ospj(bag_dir, 'metadata', 'manifest.json')
                self.assertTrue(os.path.isfile(ro_manifest_file))
                ro_manifest_txt = self.slurp_text_file(ro_manifest_file)
                ro_test_line = '"uri": "../data/test2/test2.txt"'
                if override_file_metadata:
                    self.assertNotIn(ro_test_line, ro_manifest_txt)
                else:
                    self.assertIn(ro_test_line, ro_manifest_txt)

        except Exception as e:
            self.fail(get_typed_exception(e))

    def test_create_bag_with_file_metadata_only(self):
        logger.info(self.getTestHeader('create bag with file metadata only'))
        self._test_create_or_update_bag_with_metadata()

    def test_create_bag_with_parameterized_metadata_only(self):
        logger.info(self.getTestHeader('create bag with parameterized metadata only'))
        self._test_create_or_update_bag_with_metadata(no_file_metadata=True)

    def test_create_bag_with_parameterized_metadata_and_file_metadata(self):
        logger.info(self.getTestHeader('create bag with parameterized metadata and file metadata'))
        self._test_create_or_update_bag_with_metadata(override_file_metadata=True)

    def test_update_bag_with_file_metadata_only(self):
        logger.info(self.getTestHeader('update bag with file metadata only'))
        self._test_create_or_update_bag_with_metadata(update=True)

    def test_update_bag_change_parameterized_metadata_only(self):
        logger.info(self.getTestHeader('update bag change parameterized metadata, no file metadata'))
        self._test_create_or_update_bag_with_metadata(update=True, no_file_metadata=True)

    def test_update_bag_change_parameterized_metadata_and_file_metadata(self):
        logger.info(self.getTestHeader('update bag change metadata with parameterized override of file metadata'))
        self._test_create_or_update_bag_with_metadata(update=True, override_file_metadata=True)

    def test_update_bag_change_metadata_only(self):
        logger.info(self.getTestHeader('update bag change metadata only - do not save manifests'))
        try:
            bag = bdb.make_bag(self.test_bag_dir,
                               update=True,
                               save_manifests=False,
                               metadata={"Contact-Name": "nobody"},
                               metadata_file=ospj(self.test_config_dir, 'test-metadata.json'),
                               ro_metadata_file=ospj(self.test_config_dir, 'test-ro-metadata.json'))
            output = self.stream.getvalue()
            self.assertIsInstance(bag, bdbagit.BDBag)
            self.assertExpectedMessages(['Reading bag metadata from file', 'test-metadata.json'], output)
            bag_info_txt = self.slurp_text_file(ospj(self.test_bag_dir, 'bag-info.txt')).splitlines()
            self.assertIn('Contact-Name: nobody', bag_info_txt)
            self.assertIn('External-Description: Simple bdbag test', bag_info_txt)
            self.assertTrue(os.path.isfile(ospj(self.test_bag_dir, 'metadata', 'manifest.json')))
            self.assertUnexpectedMessages(['updating manifest-sha1.txt',
                                           'updating manifest-sha256.txt',
                                           'updating manifest-sha512.txt',
                                           'updating manifest-md5.txt'], output)
        except Exception as e:
            self.fail(get_typed_exception(e))

    def test_update_bag_change_metadata_nested_dict(self):
        logger.info(self.getTestHeader('update bag change metadata with nested dict'))
        try:
            bag = bdb.make_bag(self.test_bag_dir,
                               update=True,
                               save_manifests=False,
                               metadata_file=ospj(self.test_config_dir, 'test-ro-metadata.json'))
            output = self.stream.getvalue()
            self.assertIsInstance(bag, bdbagit.BDBag)
            self.assertExpectedMessages(['Reading bag metadata from file', 'test-ro-metadata.json'], output)
            self.assertExpectedMessages(["Nested dictionary content not supported in tag file: [bag-info.txt]"], output)
        except Exception as e:
            self.fail(get_typed_exception(e))

    def test_update_bag_prune(self):
        logger.info(self.getTestHeader('update bag prune manifests'))
        try:
            bag = bdb.make_bag(self.test_bag_dir, algs=['md5'], update=True, prune_manifests=True)
            self.assertIsInstance(bag, bdbagit.BDBag)
            self.assertFalse(ospif(ospj(self.test_bag_dir, 'manifest-sha1.txt')))
            self.assertFalse(ospif(ospj(self.test_bag_dir, 'manifest-sha256.txt')))
            self.assertFalse(ospif(ospj(self.test_bag_dir, 'manifest-sha512.txt')))
            self.assertFalse(ospif(ospj(self.test_bag_dir, 'tagmanifest-sha1.txt')))
            self.assertFalse(ospif(ospj(self.test_bag_dir, 'tagmanifest-sha256.txt')))
            self.assertFalse(ospif(ospj(self.test_bag_dir, 'tagmanifest-sha512.txt')))
        except Exception as e:
            self.fail(get_typed_exception(e))

    def test_update_bag_duplicate_manifest_entry_from_remote(self):
        logger.info(self.getTestHeader('update bag with fetch.txt entry for local file'))
        try:
            with self.assertRaises(bdbagit.BagManifestConflict) as ar:
                bdb.make_bag(self.test_bag_invalid_state_duplicate_manifest_fetch_dir, update=True)
            logger.error(get_typed_exception(ar.exception))
        except Exception as e:
            self.fail(get_typed_exception(e))

    def test_create_bag_duplicate_manifest_entry_from_remote(self):
        logger.info(self.getTestHeader('create bag with fetch.txt entry for local file'))
        try:
            duplicate_file = "test-fetch-http.txt"
            shutil.copy(ospj(self.test_http_dir, duplicate_file), ospj(self.test_data_dir, duplicate_file))
            with self.assertRaises(bdbagit.BagManifestConflict) as ar:
                bdb.make_bag(self.test_data_dir,
                             remote_file_manifest=ospj(self.test_config_dir, 'test-fetch-manifest.json'))
            logger.error(get_typed_exception(ar.exception))
        except Exception as e:
            self.fail(get_typed_exception(e))

    def test_update_bag_invalid_fetch_entry(self):
        logger.info(self.getTestHeader('update bag with invalid fetch.txt entry with missing length'))
        try:
            bdb.validate_bag_structure(self.test_bag_update_invalid_fetch_dir)
            fetch = ospj(self.test_bag_update_invalid_fetch_dir, 'fetch.txt')
            with open(fetch, "w") as ff:
                ff.write('https://raw.githubusercontent.com/fair-research/bdbag/master/test/test-data/test-http/'
                         'test-fetch-http.txt\t-\tdata/test-fetch-http.txt\n')
            with self.assertRaises(ValueError) as ar:
                bdb.make_bag(self.test_bag_update_invalid_fetch_dir, update=True)
            logger.error(get_typed_exception(ar.exception))
        except Exception as e:
            self.fail(get_typed_exception(e))

    def test_create_bag_invalid_fetch_entry_length(self):
        logger.info(self.getTestHeader('create bag with invalid fetch.txt entry with missing length'))
        try:
            with self.assertRaises(ValueError) as ar:
                bdb.make_bag(self.test_data_dir,
                             remote_file_manifest=ospj(self.test_config_dir, 'test-invalid-fetch-manifest-1.json'))
            logger.error(get_typed_exception(ar.exception))
        except Exception as e:
            self.fail(get_typed_exception(e))

    def test_create_bag_invalid_fetch_entry_missing_checksum(self):
        logger.info(self.getTestHeader('create bag with invalid fetch.txt entry with missing checksum(s)'))
        try:
            with self.assertRaises(ValueError) as ar:
                bdb.make_bag(self.test_data_dir,
                             remote_file_manifest=ospj(self.test_config_dir, 'test-invalid-fetch-manifest-2.json'))
            logger.error(get_typed_exception(ar.exception))
        except Exception as e:
            self.fail(get_typed_exception(e))

    def test_create_bag_mixed_checksums_allowed(self):
        logger.info(self.getTestHeader('allow create bag with non-uniform checksum(s) per file'))
        try:
            bdb.make_bag(self.test_data_dir,
                         remote_file_manifest=ospj(self.test_config_dir,
                                                   'test-fetch-manifest-mixed-checksums.json'))
            bdb.validate_bag(self.test_bag_dir, fast=True)
        except Exception as e:
            self.fail(get_typed_exception(e))

    def test_create_bag_mixed_checksums_disallowed(self):
        logger.info(self.getTestHeader('disallow create bag with non-uniform checksum(s) per file'))
        try:
            with self.assertRaises(RuntimeError) as ar:
                bdb.make_bag(self.test_data_dir,
                             remote_file_manifest=ospj(self.test_config_dir,
                                                       'test-fetch-manifest-mixed-checksums.json'),
                             config_file=(ospj(self.test_config_dir, 'test-config-2.json')))
            self.assertExpectedMessages([str(ar.exception)], "Expected the same number of files for each checksum")
            logger.error(get_typed_exception(ar.exception))
        except Exception as e:
            self.fail(get_typed_exception(e))

    def test_archive_bag_zip(self):
        logger.info(self.getTestHeader('archive bag zip format'))
        try:
            archive_file = bdb.archive_bag(self.test_bag_dir, 'zip')
            self.assertTrue(ospif(archive_file))
        except Exception as e:
            self.fail(get_typed_exception(e))

    def test_archive_bag_tgz(self):
        logger.info(self.getTestHeader('archive bag tgz format'))
        try:
            archive_file = bdb.archive_bag(self.test_bag_dir, 'tgz')
            self.assertTrue(ospif(archive_file))
        except Exception as e:
            self.fail(get_typed_exception(e))

    def test_archive_bag_tar(self):
        logger.info(self.getTestHeader('archive bag tar format'))
        try:
            archive_file = bdb.archive_bag(self.test_bag_dir, 'tar')
            self.assertTrue(ospif(archive_file))
        except Exception as e:
            self.fail(get_typed_exception(e))

    def test_archive_bag_incomplete_structure(self):
        logger.info(self.getTestHeader('archive incomplete bag zip format'))
        try:
            self.assertRaises(bdbagit.BagValidationError,
                              bdb.archive_bag,
                              self.test_bag_invalid_structure_manifest_dir, 'zip')
        except Exception as e:
            self.fail(get_typed_exception(e))

    def test_extract_bag_archive_zip(self):
        logger.info(self.getTestHeader('extract bag zip format'))
        try:
            bag_path = bdb.extract_bag(ospj(self.test_archive_dir, 'test-bag.zip'), temp=True)
            self.assertTrue(ospe(bag_path))
            self.assertTrue(bdb.is_bag(bag_path))
            bdb.cleanup_bag(os.path.dirname(bag_path))
        except Exception as e:
            self.fail(get_typed_exception(e))

    def test_extract_bag_archive_zip_with_relocate_existing(self):
        logger.info(self.getTestHeader('extract bag zip format, relocate existing'))
        try:
            bag_path = bdb.extract_bag(ospj(self.test_archive_dir, 'test-bag.zip'), temp=False)
            self.assertTrue(ospe(bag_path))
            self.assertTrue(bdb.is_bag(bag_path))
            bag_path = bdb.extract_bag(ospj(self.test_archive_dir, 'test-bag.zip'), temp=False)
            self.assertTrue(ospe(bag_path))
            self.assertTrue(bdb.is_bag(bag_path))
            bdb.cleanup_bag(os.path.dirname(bag_path))
            output = self.stream.getvalue()
            self.assertExpectedMessages(["moving existing directory"], output)
        except Exception as e:
            self.fail(get_typed_exception(e))

    def test_extract_bag_archive_tgz(self):
        logger.info(self.getTestHeader('extract bag tgz format'))
        try:
            bag_path = bdb.extract_bag(ospj(self.test_archive_dir, 'test-bag.tgz'), temp=True)
            self.assertTrue(ospe(bag_path))
            self.assertTrue(bdb.is_bag(bag_path))
            bdb.cleanup_bag(os.path.dirname(bag_path))
        except Exception as e:
            self.fail(get_typed_exception(e))

    def test_extract_bag_archive_tar(self):
        logger.info(self.getTestHeader('extract bag tar format'))
        try:
            bag_path = bdb.extract_bag(ospj(self.test_archive_dir, 'test-bag.tar'), temp=True)
            self.assertTrue(ospe(bag_path))
            self.assertTrue(bdb.is_bag(bag_path))
            bdb.cleanup_bag(os.path.dirname(bag_path))
        except Exception as e:
            self.fail(get_typed_exception(e))

    def test_validate_complete_bag_full(self):
        logger.info(self.getTestHeader('test full validation complete bag'))
        try:
            bdb.validate_bag(self.test_bag_dir, fast=False)
        except Exception as e:
            self.fail(get_typed_exception(e))

    def test_validate_complete_bag_full_with_callback_and_cancel(self):
        logger.info(self.getTestHeader('test full validation complete bag with callback and cancel'))
        try:
            def callback(current, total):
                if current < total - 1:
                    return True
                else:
                    return False

            self.assertRaises(bdbagit.BaggingInterruptedError,
                              bdb.validate_bag,
                              self.test_bag_dir,
                              fast=False,
                              callback=callback)
        except Exception as e:
            self.fail(get_typed_exception(e))

    def test_validate_complete_bag_fast(self):
        logger.info(self.getTestHeader('test fast validation complete bag'))
        try:
            bdb.validate_bag(self.test_bag_dir, fast=True)
        except Exception as e:
            self.fail(get_typed_exception(e))

    def test_validate_complete_bag_structure(self):
        logger.info(self.getTestHeader('test structure validation complete bag'))
        try:
            bdb.validate_bag_structure(self.test_bag_dir)
        except Exception as e:
            self.fail(get_typed_exception(e))

    def test_validate_incomplete_bag_full(self):
        logger.info(self.getTestHeader('test full validation incomplete bag'))
        try:
            self.assertRaisesRegex(
                bdbagit.BagValidationError,
                "^Bag validation failed:.*(test-fetch-identifier[.]txt:|test-fetch-http[.]txt)",
                bdb.validate_bag,
                self.test_bag_incomplete_dir, fast=False)
        except Exception as e:
            self.fail(get_typed_exception(e))

    def test_validate_incomplete_bag_fast(self):
        logger.info(self.getTestHeader('test fast validation incomplete bag'))
        try:
            self.assertRaises(bdbagit.BagValidationError, bdb.validate_bag, self.test_bag_incomplete_dir, fast=True)
        except Exception as e:
            self.fail(get_typed_exception(e))

    def test_validate_incomplete_bag_structure(self):
        logger.info(self.getTestHeader('test structure validation incomplete bag'))
        try:
            bdb.validate_bag_structure(self.test_bag_incomplete_dir)
        except Exception as e:
            self.fail(get_typed_exception(e))

    def test_validate_invalid_bag_structure_manifest(self):
        logger.info(self.getTestHeader('test structure validation invalid bag manifest'))
        try:
            self.assertRaises(bdbagit.BagValidationError,
                              bdb.validate_bag_structure,
                              self.test_bag_invalid_structure_manifest_dir)
        except Exception as e:
            self.fail(get_typed_exception(e))

    def test_validate_invalid_bag_structure_filesystem(self):
        logger.info(self.getTestHeader('test structure validation invalid bag filesystem'))
        try:
            self.assertRaises(bdbagit.BagValidationError,
                              bdb.validate_bag_structure,
                              self.test_bag_invalid_structure_filesystem_dir)
        except Exception as e:
            self.fail(get_typed_exception(e))

    def test_validate_invalid_bag_structure_fetch(self):
        logger.info(self.getTestHeader('test structure validation invalid bag fetch.txt'))
        try:
            self.assertRaises(bdbagit.BagValidationError,
                              bdb.validate_bag_structure,
                              self.test_bag_invalid_structure_fetch_dir)
        except Exception as e:
            self.fail(get_typed_exception(e))

    def test_validate_invalid_bag_state_manifest_fetch(self):
        logger.info(self.getTestHeader('test bag state validation invalid bag manifest with missing fetch.txt'))
        try:
            self.assertRaises(bdbagit.BagValidationError,
                              bdb.validate_bag_structure,
                              self.test_bag_invalid_state_manifest_fetch_dir,
                              skip_remote=False)
        except Exception as e:
            self.fail(get_typed_exception(e))

    def test_validate_invalid_bag_state_fetch_filesize(self):
        logger.info(self.getTestHeader('test bag state validation invalid local file size of fetch.txt file ref'))
        try:
            self.assertRaises(bdbagit.BagValidationError,
                              bdb.validate_bag_structure,
                              self.test_bag_invalid_state_fetch_filesize_dir,
                              skip_remote=False)
        except Exception as e:
            self.fail(get_typed_exception(e))

    def test_filter_dict(self):
        logger.info(self.getTestHeader('test filter function'))

        msg = "evaluating filter expression: %s"
        test_url = "http://example.com/files/examples/README.txt"
        test_length = 250624
        test_filename = "data/examples/README.txt"
        test_entry = {"url": test_url,
                      "length": test_length,
                      "filename": test_filename}
        pos_exprs = ["url==%s" % test_url,
                     "url!=http://foo",
                     "url=*/files/",
                     "filename!*/files/",
                     "filename^*data/",
                     "filename$*.txt",
                     "length>250623",
                     "length>=250624",
                     "length<250625",
                     "length<=250624"]
        neg_exprs = ["url!=%s" % test_url,
                     "url==http://foo",
                     "url=*/fils/",
                     "filename!*/examples/",
                     "filename^*dat/",
                     "filename$*.tx",
                     "length>250624",
                     "length>=250625",
                     "length<250624",
                     "length<=250623",
                     "length<=-"]
        bad_exprs = ["url*=http://foo", "url=http://foo"]
        try:
            for expr in pos_exprs:
                result = filter_dict(expr, test_entry)
                self.assertTrue(result, msg % expr)
            for expr in neg_exprs:
                result = filter_dict(expr, test_entry)
                self.assertFalse(result, msg % expr)
            for expr in bad_exprs:
                self.assertRaises(ValueError, filter_dict, expr, test_entry)
        except Exception as e:
            self.fail(get_typed_exception(e))

    ro_test_aggregates = [
        {
            "bundledAs": {
                "filename": "test-fetch-http.txt",
                "folder": "../data/",
            },
            "mediatype": "text/plain",
            "uri": "https://raw.githubusercontent.com/fair-research/bdbag/master/test/test-data/test-http/test-fetch-http.txt"
        },
        {
            "bundledAs": {
                "filename": "test-fetch-identifier.txt",
                "folder": "../data/",
            },
            "mediatype": "text/plain",
            "uri": "http://n2t.net/ark:/57799/b9dd5t"
        },
        {
            "mediatype": "text/plain",
            "uri": "../data/README.txt"
        },
        {
            "mediatype": "text/plain",
            "uri": "../data/test1/test1.txt"
        },
        {
            "mediatype": "text/plain",
            "uri": "../data/test2/test2.txt"
        }
    ]

    def test_generate_ro_manifest_update(self):
        logger.info(self.getTestHeader('create bag with auto-generation of RO manifest in update mode'))
        try:
            bdb.make_bag(self.test_data_dir, algs=['md5', 'sha1', 'sha256', 'sha512'],
                         remote_file_manifest=ospj(self.test_config_dir, 'test-fetch-manifest.json'))
            bdb.generate_ro_manifest(self.test_data_dir, overwrite=True)
            ro = bdbro.read_bag_ro_metadata(self.test_data_dir)
            old_agg_dict = dict()
            for entry in ro.get("aggregates", []):
                old_agg_dict[entry["uri"]] = entry
            bdbro.add_file_metadata(ro, local_path="../data/FAKE.txt", bundled_as=bdbro.make_bundled_as())
            bdbro.write_bag_ro_metadata(ro, self.test_data_dir)

            bdb.generate_ro_manifest(self.test_data_dir, overwrite=False)
            ro = bdbro.read_bag_ro_metadata(self.test_data_dir)
            for entry in ro.get("aggregates", []):
                if entry["uri"] in old_agg_dict:
                    self.assertTrue(entry["bundledAs"]["uri"] == old_agg_dict[entry["uri"]]["bundledAs"]["uri"])

        except Exception as e:
            self.fail(get_typed_exception(e))

    def test_generate_ro_manifest_overwrite(self):
        logger.info(self.getTestHeader('create bag with auto-generation of RO manifest in overwrite mode'))
        try:
            bdb.make_bag(self.test_data_dir, algs=['md5', 'sha1', 'sha256', 'sha512'],
                         remote_file_manifest=ospj(self.test_config_dir, 'test-fetch-manifest.json'))
            bdb.generate_ro_manifest(self.test_data_dir, overwrite=True)
            ro = bdbro.read_bag_ro_metadata(self.test_data_dir)
            agg_dict = dict()
            for entry in ro.get("aggregates", []):
                agg_dict[entry["uri"]] = entry
            for test_entry in self.ro_test_aggregates:
                self.assertTrue(test_entry["uri"] in agg_dict)
                entry = agg_dict[test_entry["uri"]]
                bundled_as = entry.get("bundledAs")
                if bundled_as:
                    if "filename" in bundled_as:
                        self.assertTrue(test_entry["bundledAs"]["filename"] == bundled_as["filename"])
                    if "folder" in bundled_as:
                        self.assertTrue(test_entry["bundledAs"]["folder"] == bundled_as["folder"])

        except Exception as e:
            self.fail(get_typed_exception(e))


if __name__ == '__main__':
    unittest.main()
