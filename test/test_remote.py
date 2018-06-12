import os
import sys
import logging
import mock
import unittest
import requests
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

PATCHED_REQUESTS_GET = None
PATCH_REQUESTS_POST = None


def mocked_request_auth_get_success(*args, **kwargs):
    args[0].auth = None
    PATCHED_REQUESTS_GET.stop()
    return BaseTest.MockResponse({}, 200)


def mocked_request_auth_post_success(*args, **kwargs):
    args[0].auth = None
    PATCHED_REQUESTS_POST.stop()
    return BaseTest.MockResponse({}, 201)


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

    def _test_bag_with_remote_file_manifest(self, update=False):
        try:
            bag_dir = self.test_data_dir if not update else self.test_bag_dir
            bag = bdb.make_bag(bag_dir,
                               algs=["md5", "sha1", "sha256", "sha512"],
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
                'https://raw.githubusercontent.com/fair-research/bdbag/master/test/test-data/test-http/'
                'test-fetch-http.txt\t201\tdata/test-fetch-http.txt', fetch_txt)
            self.assertIn(
                'ark:/57799/b9dd5t\t223\tdata/test-fetch-identifier.txt', fetch_txt)
            bdb.validate_bag_structure(bag_dir, True)
        except Exception as e:
            self.fail(bdbag.get_typed_exception(e))

    def test_create_bag_from_remote_file_manifest(self):
        logger.info(self.getTestHeader('create bag add remote file manifest'))
        self._test_bag_with_remote_file_manifest()

    def test_update_bag_from_remote_file_manifest(self):
        logger.info(self.getTestHeader('update bag add remote file manifest'))
        self._test_bag_with_remote_file_manifest(True)

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
                bag_profile_path=
                'https://raw.githubusercontent.com/fair-research/bdbag/master/profiles/bdbag-profile.json')
        except Exception as e:
            self.fail(bdbag.get_typed_exception(e))

    def test_validate_remote_bag_from_rfm(self):
        logger.info(self.getTestHeader('create, resolve, and validate bag from remote file manifest'))
        self._test_bag_with_remote_file_manifest()
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

    def _test_resolve_fetch_http_with_filter(self, expr, files=list(frozenset())):
        logger.info(self.getTestHeader('test resolve fetch http with filter expression "%s"' % expr))
        try:
            bdb.resolve_fetch(self.test_bag_fetch_http_dir, filter_expr=expr)
            for test_file in files:
                self.assertTrue(ospif(ospj(self.test_bag_fetch_http_dir, test_file)))
        except Exception as e:
            self.fail(bdbag.get_typed_exception(e))

    def test_resolve_fetch_http_with_filter1(self):
        self._test_resolve_fetch_http_with_filter("length<500", ["data/test-fetch-http.txt"])

    def test_resolve_fetch_http_with_filter2(self):
        self._test_resolve_fetch_http_with_filter("filename==data/test-fetch-http.txt", ["data/test-fetch-http.txt"])

    def test_resolve_fetch_http_with_filter3(self):
        self._test_resolve_fetch_http_with_filter("url=*/test-data/test-http/",
                                                  ["data/test-fetch-http.txt", "data/test-fetch-identifier.txt"])

    def test_resolve_fetch_http_basic_auth_get(self):
        logger.info(self.getTestHeader('test resolve fetch http basic auth GET'))
        try:
            global PATCHED_REQUESTS_GET
            PATCHED_REQUESTS_GET = mock.patch.multiple("bdbag.fetch.transports.fetch_http.requests.Session",
                                                       get=mocked_request_auth_get_success,
                                                       auth=None,
                                                       create=True)

            PATCHED_REQUESTS_GET.start()
            bdb.resolve_fetch(self.test_bag_fetch_http_dir,
                              keychain_file=ospj(self.test_config_dir, 'test-keychain-1.json'))
            bdb.validate_bag(self.test_bag_fetch_http_dir, fast=True)
            bdb.validate_bag(self.test_bag_fetch_http_dir, fast=False)
            output = self.stream.getvalue()
        except Exception as e:
            self.fail(bdbag.get_typed_exception(e))

    def _test_resolve_fetch_http_auth_post(self, keychain_file):
        try:
            global PATCHED_REQUESTS_POST
            PATCHED_REQUESTS_POST = mock.patch.multiple("bdbag.fetch.transports.fetch_http.requests.Session",
                                                        post=mocked_request_auth_post_success,
                                                        auth=None,
                                                        create=True)
            PATCHED_REQUESTS_POST.start()
            bdb.resolve_fetch(self.test_bag_fetch_http_dir,
                              keychain_file=ospj(self.test_config_dir, keychain_file))
            bdb.validate_bag(self.test_bag_fetch_http_dir, fast=True)
            bdb.validate_bag(self.test_bag_fetch_http_dir, fast=False)
            output = self.stream.getvalue()
        except Exception as e:
            self.fail(bdbag.get_typed_exception(e))

    def test_resolve_fetch_http_basic_auth_post(self):
        logger.info(self.getTestHeader('test resolve fetch http basic auth POST'))
        self._test_resolve_fetch_http_auth_post("test-keychain-2.json")

    def test_resolve_fetch_http_form_auth_post(self):
        logger.info(self.getTestHeader('test resolve fetch http form auth POST'))
        self._test_resolve_fetch_http_auth_post("test-keychain-3.json")

    def test_resolve_fetch_http_cookie_auth(self):
        logger.info(self.getTestHeader('test resolve fetch http cookie auth'))
        try:
            bdb.resolve_fetch(self.test_bag_fetch_http_dir,
                              keychain_file=ospj(self.test_config_dir, 'test-keychain-4.json'))
            bdb.validate_bag(self.test_bag_fetch_http_dir, fast=True)
            bdb.validate_bag(self.test_bag_fetch_http_dir, fast=False)
            output = self.stream.getvalue()
        except Exception as e:
            self.fail(bdbag.get_typed_exception(e))

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
