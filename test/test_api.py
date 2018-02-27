import os
import sys
import logging
import unittest
import bdbag
import bdbag.bdbagit as bdbagit
import bdbag.bdbagit_profile as bdbagit_profile
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

    def test_update_bag_change_metadata(self):
        logger.info(self.getTestHeader('update bag change metadata'))
        try:
            bag = bdb.make_bag(self.test_bag_dir,
                               update=True,
                               metadata={"Contact-Name": "nobody"},
                               metadata_file=(ospj(self.test_config_dir, 'test-metadata.json')))
            output = self.stream.getvalue()
            self.assertIsInstance(bag, bdbagit.BDBag)
            self.assertExpectedMessages(['Reading bag metadata from file', 'test-metadata.json'], output)
        except Exception as e:
            self.fail(bdbag.get_typed_exception(e))

    def test_update_bag_change_metadata_only(self):
        logger.info(self.getTestHeader('update bag change metadata only - do not save manifests'))
        try:
            bag = bdb.make_bag(self.test_bag_dir,
                               update=True,
                               save_manifests=False,
                               metadata={"Contact-Name": "nobody"},
                               metadata_file=(ospj(self.test_config_dir, 'test-metadata.json')))
            output = self.stream.getvalue()
            self.assertIsInstance(bag, bdbagit.BDBag)
            self.assertExpectedMessages(['Reading bag metadata from file', 'test-metadata.json'], output)
            self.assertUnexpectedMessages(['updating manifest-sha1.txt',
                                           'updating manifest-sha256.txt',
                                           'updating manifest-sha512.txt',
                                           'updating manifest-md5.txt'], output)
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
                "^Bag validation failed:.*(minid_v0[.]1_Nov_2015[.]pdf:|bdbag-profile[.]json)",
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
