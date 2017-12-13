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

    def _test_bag_remote(self, update=False):
        try:
            bag_dir = self.test_data_dir if not update else self.test_bag_dir
            bag = bdb.make_bag(bag_dir,
                               update=update,
                               remote_file_manifest=ospj(self.test_config_dir, 'test-fetch-manifest.json'))
            output = self.stream.getvalue()
            self.assertIsInstance(bag, bdbagit.BDBag)
            self.assertExpectedMessages(['Generating remote file references from', 'test-fetch-manifest.json'], output)
            fetch_file = ospj(bag_dir, 'fetch.txt')
            self.assertTrue(ospif(fetch_file))
            with open(fetch_file) as ff:
                fetch_txt = ff.read()
            self.assertIn(
                'https://raw.githubusercontent.com/ini-bdds/bdbag/master/profiles/bdbag-profile.json'
                '\t723\tdata/bdbag-profile.json', fetch_txt)
            self.assertIn(
                'ark:/88120/r8059v\t632860\tdata/minid_v0.1_Nov_2015.pdf', fetch_txt)
        except Exception as e:
            self.fail(bdbag.get_typed_exception(e))

    def test_create_bag_remote(self):
        logger.info(self.getTestHeader('create bag add remote file manifest'))
        self._test_bag_remote()

    def test_update_bag_remote(self):
        logger.info(self.getTestHeader('update bag add remote file manifest'))
        self._test_bag_remote(True)

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

    def test_validate_profile(self):
        logger.info(self.getTestHeader('validate profile'))
        try:
            profile = bdb.validate_bag_profile(self.test_bag_dir)
            self.assertIsInstance(profile, bdbagit_profile.Profile)
        except Exception as e:
            self.fail(bdbag.get_typed_exception(e))

    def test_validate_profile_serialization(self):
        logger.info(self.getTestHeader('validate profile serialization'))
        try:
            bag_path = ospj(self.test_archive_dir, 'test-bag.zip')
            bdb.validate_bag_serialization(
                bag_path,
                bag_profile_path='https://raw.githubusercontent.com/ini-bdds/bdbag/master/profiles/bdbag-profile.json')
        except Exception as e:
            self.fail(bdbag.get_typed_exception(e))

    def test_resolve_fetch_http(self):
        logger.info(self.getTestHeader('test resolve fetch http'))
        try:
            bdb.resolve_fetch(self.test_bag_fetch_http_dir)
            bdb.validate_bag(self.test_bag_fetch_http_dir, fast=False)
            output = self.stream.getvalue()
        except Exception as e:
            self.fail(bdbag.get_typed_exception(e))

#    def test_resolve_fetch_http_auth(self):
#        # TODO
#        pass

    def test_resolve_fetch_ark(self):
        logger.info(self.getTestHeader('test resolve fetch ark'))
        try:
            bdb.resolve_fetch(self.test_bag_fetch_ark_dir)
            bdb.validate_bag(self.test_bag_fetch_ark_dir, fast=False)
            output = self.stream.getvalue()
        except Exception as e:
            self.fail(bdbag.get_typed_exception(e))

    def test_resolve_fetch_ftp(self):
        logger.info(self.getTestHeader('test resolve fetch ftp'))
        try:
            bdb.resolve_fetch(self.test_bag_fetch_ftp_dir)
            bdb.validate_bag(self.test_bag_fetch_ftp_dir, fast=False)
            output = self.stream.getvalue()
        except Exception as e:
            self.fail(bdbag.get_typed_exception(e))

#    def test_resolve_fetch_globus(self):
#        # TODO
#        pass


if __name__ == '__main__':
    unittest.main()
