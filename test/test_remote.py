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

logging.basicConfig(filename='test_remote.log', filemode='w', level=logging.DEBUG)
logger = logging.getLogger()


class TestRemoteAPI(BaseTest):

    def setUp(self):
        super(TestRemoteAPI, self).setUp()
        self.stream = StringIO()
        self.handler = logging.StreamHandler(self.stream)
        logger.addHandler(self.handler)

    def tearDown(self):
        self.stream.close()
        logger.removeHandler(self.handler)
        super(TestRemoteAPI, self).tearDown()

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

    def test_validate_remote_bag_from_rfm(self):
        logger.info(self.getTestHeader('create, resolve, and validate bag from remote file manifest'))
        self._test_bag_remote()
        bdb.resolve_fetch(self.test_data_dir)
        bdb.validate_bag(self.test_data_dir, fast=True)
        bdb.validate_bag(self.test_data_dir, fast=False)

    def test_resolve_fetch_http(self):
        logger.info(self.getTestHeader('test resolve fetch http'))
        try:
            bdb.resolve_fetch(self.test_bag_fetch_http_dir)
            bdb.validate_bag(self.test_bag_fetch_http_dir, fast=True)
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
            bdb.validate_bag(self.test_bag_fetch_ark_dir, fast=True)
            bdb.validate_bag(self.test_bag_fetch_ark_dir, fast=False)
            output = self.stream.getvalue()
        except Exception as e:
            self.fail(bdbag.get_typed_exception(e))

    def test_resolve_fetch_minid(self):
        logger.info(self.getTestHeader('test resolve fetch minid'))
        try:
            bdb.resolve_fetch(self.test_bag_fetch_minid_dir)
            bdb.validate_bag(self.test_bag_fetch_minid_dir, fast=True)
            bdb.validate_bag(self.test_bag_fetch_minid_dir, fast=False)
            output = self.stream.getvalue()
        except Exception as e:
            self.fail(bdbag.get_typed_exception(e))

    def test_resolve_fetch_ftp(self):
        logger.info(self.getTestHeader('test resolve fetch ftp'))
        try:
            bdb.resolve_fetch(self.test_bag_fetch_ftp_dir)
            bdb.validate_bag(self.test_bag_fetch_ftp_dir, fast=True)
            bdb.validate_bag(self.test_bag_fetch_ftp_dir, fast=False)
            output = self.stream.getvalue()
        except Exception as e:
            self.fail(bdbag.get_typed_exception(e))

#    def test_resolve_fetch_globus(self):
#        # TODO
#        pass


if __name__ == '__main__':
    unittest.main()
