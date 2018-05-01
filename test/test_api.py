import os
import sys
import shutil
import logging
import unittest
import bdbag
import bdbag.bdbagit as bdbagit
from os.path import join as ospj
from os.path import exists as ospe
from os.path import isfile as ospif
from bdbag import bdbag_api as bdb
from test.test_common import BaseTest

if sys.version_info > (3,):
    from io import StringIO
else:
    from StringIO import StringIO

logging.basicConfig(filename='test_api.log', filemode='w', level=logging.DEBUG)
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

    def test_create_bag(self):
        logger.info(self.getTestHeader('create bag'))
        try:
            bag = bdb.make_bag(self.test_data_dir)
            self.assertIsInstance(bag, bdbagit.BDBag)
        except Exception as e:
            self.fail(bdbag.get_typed_exception(e))

    def test_cleanup_bag(self):
        logger.info(self.getTestHeader('cleanup bag'))
        try:
            bdb.cleanup_bag(self.test_bag_dir)
            self.assertFalse(ospe(self.test_bag_dir), "Failed to cleanup bag directory")
        except Exception as e:
            self.fail(bdbag.get_typed_exception(e))

    def test_ensure_bag_path_exists(self):
        logger.info(self.getTestHeader('ensure bag path exists, save existing'))
        try:
            saved_bag_path = bdb.ensure_bag_path_exists(self.test_bag_dir)
            self.assertTrue(ospe(self.test_bag_dir), "Bag directory does not exist")
            self.assertTrue(ospe(saved_bag_path), "Saved bag path does not exist")
        except Exception as e:
            self.fail(bdbag.get_typed_exception(e))

    def test_ensure_bag_path_exists_delete_existing(self):
        logger.info(self.getTestHeader('ensure bag path exists, delete existing'))
        try:
            bdb.ensure_bag_path_exists(self.test_bag_dir, save=False)
            self.assertTrue(ospe(self.test_bag_dir), "Bag directory does not exist")
        except Exception as e:
            self.fail(bdbag.get_typed_exception(e))

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
            self.fail(bdbag.get_typed_exception(e))

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
            self.fail(bdbag.get_typed_exception(e))

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
            self.fail(bdbag.get_typed_exception(e))

    def test_update_bag_remove_file(self):
        logger.info(self.getTestHeader('update bag remove file'))
        try:
            os.remove(ospj(self.test_bag_dir, 'data', 'test1', 'test1.txt'))
            bag = bdb.make_bag(self.test_bag_dir, update=True)
            output = self.stream.getvalue()
            self.assertIsInstance(bag, bdbagit.BDBag)
            self.assertUnexpectedMessages(['test1.txt'], output)
        except Exception as e:
            self.fail(bdbag.get_typed_exception(e))

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
            self.fail(bdbag.get_typed_exception(e))

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
            self.fail(bdbag.get_typed_exception(e))

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
            self.fail(bdbag.get_typed_exception(e))

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
            self.fail(bdbag.get_typed_exception(e))

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
            self.fail(bdbag.get_typed_exception(e))

    def test_update_bag_duplicate_manifest_entry_from_remote(self):
        logger.info(self.getTestHeader('update bag with fetch.txt entry for local file'))
        try:
            with self.assertRaises(bdbagit.BagManifestConflict) as ar:
                bdb.make_bag(self.test_bag_invalid_state_duplicate_manifest_fetch_dir, update=True)
            logger.error(bdbag.get_typed_exception(ar.exception))
        except Exception as e:
            self.fail(bdbag.get_typed_exception(e))

    def test_create_bag_duplicate_manifest_entry_from_remote(self):
        logger.info(self.getTestHeader('create bag with fetch.txt entry for local file'))
        try:
            duplicate_file = "test-fetch-http.txt"
            shutil.copy(ospj(self.test_http_dir, duplicate_file), ospj(self.test_data_dir, duplicate_file))
            with self.assertRaises(bdbagit.BagManifestConflict) as ar:
                bdb.make_bag(self.test_data_dir,
                             remote_file_manifest=ospj(self.test_config_dir, 'test-fetch-manifest.json'))
            logger.error(bdbag.get_typed_exception(ar.exception))
        except Exception as e:
            self.fail(bdbag.get_typed_exception(e))

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
            logger.error(bdbag.get_typed_exception(ar.exception))
        except Exception as e:
            self.fail(bdbag.get_typed_exception(e))

    def test_create_bag_invalid_fetch_entry(self):
        logger.info(self.getTestHeader('create bag with invalid fetch.txt entry with missing length'))
        try:
            with self.assertRaises(ValueError) as ar:
                bdb.make_bag(self.test_data_dir,
                             remote_file_manifest=ospj(self.test_config_dir, 'test-invalid-fetch-manifest.json'))
            logger.error(bdbag.get_typed_exception(ar.exception))
        except Exception as e:
            self.fail(bdbag.get_typed_exception(e))

    def test_archive_bag_zip(self):
        logger.info(self.getTestHeader('archive bag zip format'))
        try:
            archive_file = bdb.archive_bag(self.test_bag_dir, 'zip')
            self.assertTrue(ospif(archive_file))
        except Exception as e:
            self.fail(bdbag.get_typed_exception(e))

    def test_archive_bag_tgz(self):
        logger.info(self.getTestHeader('archive bag tgz format'))
        try:
            archive_file = bdb.archive_bag(self.test_bag_dir, 'tgz')
            self.assertTrue(ospif(archive_file))
        except Exception as e:
            self.fail(bdbag.get_typed_exception(e))

    def test_archive_bag_tar(self):
        logger.info(self.getTestHeader('archive bag tar format'))
        try:
            archive_file = bdb.archive_bag(self.test_bag_dir, 'tar')
            self.assertTrue(ospif(archive_file))
        except Exception as e:
            self.fail(bdbag.get_typed_exception(e))

    def test_extract_bag_archive_zip(self):
        logger.info(self.getTestHeader('extract bag zip format'))
        try:
            bag_path = bdb.extract_bag(ospj(self.test_archive_dir, 'test-bag.zip'), temp=True)
            self.assertTrue(ospe(bag_path))
            self.assertTrue(bdb.is_bag(bag_path))
            bdb.cleanup_bag(os.path.dirname(bag_path))
        except Exception as e:
            self.fail(bdbag.get_typed_exception(e))

    def test_extract_bag_archive_tgz(self):
        logger.info(self.getTestHeader('extract bag tgz format'))
        try:
            bag_path = bdb.extract_bag(ospj(self.test_archive_dir, 'test-bag.tgz'), temp=True)
            self.assertTrue(ospe(bag_path))
            self.assertTrue(bdb.is_bag(bag_path))
            bdb.cleanup_bag(os.path.dirname(bag_path))
        except Exception as e:
            self.fail(bdbag.get_typed_exception(e))

    def test_extract_bag_archive_tar(self):
        logger.info(self.getTestHeader('extract bag tar format'))
        try:
            bag_path = bdb.extract_bag(ospj(self.test_archive_dir, 'test-bag.tar'), temp=True)
            self.assertTrue(ospe(bag_path))
            self.assertTrue(bdb.is_bag(bag_path))
            bdb.cleanup_bag(os.path.dirname(bag_path))
        except Exception as e:
            self.fail(bdbag.get_typed_exception(e))

    def test_validate_complete_bag_full(self):
        logger.info(self.getTestHeader('test full validation complete bag'))
        try:
            bdb.validate_bag(self.test_bag_dir, fast=False)
        except Exception as e:
            self.fail(bdbag.get_typed_exception(e))

    def test_validate_complete_bag_fast(self):
        logger.info(self.getTestHeader('test fast validation complete bag'))
        try:
            bdb.validate_bag(self.test_bag_dir, fast=True)
        except Exception as e:
            self.fail(bdbag.get_typed_exception(e))

    def test_validate_complete_bag_structure(self):
        logger.info(self.getTestHeader('test structure validation complete bag'))
        try:
            bdb.validate_bag_structure(self.test_bag_dir)
        except Exception as e:
            self.fail(bdbag.get_typed_exception(e))

    def test_validate_incomplete_bag_full(self):
        logger.info(self.getTestHeader('test full validation incomplete bag'))
        try:
            self.assertRaisesRegex(
                bdbagit.BagValidationError,
                "^Bag validation failed:.*(test-fetch-identifier[.]txt:|test-fetch-http[.]txt)",
                bdb.validate_bag,
                self.test_bag_incomplete_dir, fast=False)
        except Exception as e:
            self.fail(bdbag.get_typed_exception(e))

    def test_validate_incomplete_bag_fast(self):
        logger.info(self.getTestHeader('test fast validation incomplete bag'))
        try:
            self.assertRaises(bdbagit.BagValidationError,  bdb.validate_bag, self.test_bag_incomplete_dir, fast=True)
        except Exception as e:
            self.fail(bdbag.get_typed_exception(e))

    def test_validate_incomplete_bag_structure(self):
        logger.info(self.getTestHeader('test structure validation incomplete bag'))
        try:
            bdb.validate_bag_structure(self.test_bag_incomplete_dir)
        except Exception as e:
            self.fail(bdbag.get_typed_exception(e))

    def test_validate_invalid_bag_structure_manifest(self):
        logger.info(self.getTestHeader('test structure validation invalid bag manifest'))
        try:
            self.assertRaises(bdbagit.BagValidationError,
                              bdb.validate_bag_structure,
                              self.test_bag_invalid_structure_manifest_dir)
        except Exception as e:
            self.fail(bdbag.get_typed_exception(e))

    def test_validate_invalid_bag_structure_filesystem(self):
        logger.info(self.getTestHeader('test structure validation invalid bag filesystem'))
        try:
            self.assertRaises(bdbagit.BagValidationError,
                              bdb.validate_bag_structure,
                              self.test_bag_invalid_structure_filesystem_dir)
        except Exception as e:
            self.fail(bdbag.get_typed_exception(e))

    def test_validate_invalid_bag_structure_fetch(self):
        logger.info(self.getTestHeader('test structure validation invalid bag fetch.txt'))
        try:
            self.assertRaises(bdbagit.BagValidationError,
                              bdb.validate_bag_structure,
                              self.test_bag_invalid_structure_fetch_dir)
        except Exception as e:
            self.fail(bdbag.get_typed_exception(e))

    def test_validate_invalid_bag_state_manifest_fetch(self):
        logger.info(self.getTestHeader('test bag state validation invalid bag manifest with missing fetch.txt'))
        try:
            self.assertRaises(bdbagit.BagValidationError,
                              bdb.validate_bag_structure,
                              self.test_bag_invalid_state_manifest_fetch_dir,
                              skip_remote=False)
        except Exception as e:
            self.fail(bdbag.get_typed_exception(e))

    def test_validate_invalid_bag_state_fetch_filesize(self):
        logger.info(self.getTestHeader('test bag state validation invalid local file size of fetch.txt file ref'))
        try:
            self.assertRaises(bdbagit.BagValidationError,
                              bdb.validate_bag_structure,
                              self.test_bag_invalid_state_fetch_filesize_dir,
                              skip_remote=False)
        except Exception as e:
            self.fail(bdbag.get_typed_exception(e))


if __name__ == '__main__':
    unittest.main()
