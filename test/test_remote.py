# encoding: utf-8

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
import sys
import logging
import mock
import json
import unittest
import requests
import tempfile
import bdbag
import bdbag.bdbagit as bdbagit
import bdbag.bdbagit_profile as bdbagit_profile
from os.path import join as ospj
from os.path import exists as ospe
from os.path import isfile as ospif
from bdbag import bdbag_api as bdb, bdbag_config as bdbcfg
from bdbag.fetch import fetcher
from bdbag.fetch.transports.fetch_http import BaseFetchTransport, HTTPFetchTransport
from bdbag.fetch.auth import cookies
from bdbag.fetch.auth.keychain import read_keychain, update_keychain, get_auth_entries
from test.test_common import BaseTest

if sys.version_info > (3,):
    from io import StringIO
else:
    from StringIO import StringIO

logger = logging.getLogger()


class CustomTestFetchTransport(HTTPFetchTransport):

    def __init__(self, config, keychain, **kwargs):
        super(CustomTestFetchTransport, self).__init__(config, keychain, **kwargs)
        if self.keychain:
            logger.debug("Got propagated keychain: %s" % json.dumps(self.keychain))

    def fetch(self, url, output_path, **kwargs):
        return super(CustomTestFetchTransport, self).fetch(url, output_path, **kwargs)

    def cleanup(self):
        super(CustomTestFetchTransport, self).cleanup()


class BadCustomTestFetchTransport(BaseFetchTransport):

    def __init__(self, config, keychain, **kwargs):
        super(BadCustomTestFetchTransport, self).__init__(config, keychain, **kwargs)


class TestRemoteAPI(BaseTest):

    def setUp(self):
        super(TestRemoteAPI, self).setUp()
        self.stream = StringIO()
        self.handler = logging.StreamHandler(self.stream)
        logger.addHandler(self.handler)
        logger.setLevel(logging.DEBUG)

    def tearDown(self):
        self.stream.close()
        logger.removeHandler(self.handler)
        super(TestRemoteAPI, self).tearDown()

    def _test_bag_with_remote_file_manifest(self, update=False, use_json_stream=False):
        try:
            bag_dir = self.test_data_dir if not update else self.test_bag_dir
            filename = 'test-fetch-manifest.json' if not use_json_stream else 'test-fetch-manifest-2.json'
            bag = bdb.make_bag(bag_dir,
                               algs=["md5", "sha1", "sha256", "sha512"],
                               update=update,
                               remote_file_manifest=ospj(self.test_config_dir, filename))
            output = self.stream.getvalue()
            self.assertIsInstance(bag, bdbagit.BDBag)
            self.assertExpectedMessages(['Generating remote file references from', filename], output)
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

    def test_create_bag_from_remote_file_manifest_json_stream(self):
        logger.info(self.getTestHeader('create bag add remote file manifest with json stream format'))
        self._test_bag_with_remote_file_manifest(use_json_stream=True)

    def test_bag_with_unencoded_utf8_remote_file_manifest(self):
        try:
            bag_dir = self.test_data_dir
            filename = 'test-fetch-manifest-encoding.json'
            bag = bdb.make_bag(bag_dir,
                               algs=["md5", "sha1", "sha256", "sha512"],
                               remote_file_manifest=ospj(self.test_config_dir, filename))
            output = self.stream.getvalue()
            self.assertIsInstance(bag, bdbagit.BDBag)
            self.assertExpectedMessages(['Generating remote file references from', filename], output)
            fetch_file = ospj(bag_dir, 'fetch.txt')
            self.assertTrue(ospif(fetch_file))
            with io.open(fetch_file, encoding='utf-8') as ff:
                fetch_txt = ff.read()
            self.assertIn(
                u'https://raw.githubusercontent.com/fair-research/bdbag/master/test/test-data/test-http-encoded/'
                u'test%09fetch%25http®.txt\t201\tdata/test%0Afetch%0Ahttp®.txt', fetch_txt)
            self.assertIn(
                u'https://raw.githubusercontent.com/fair-research/bdbag/master/test/test-data/test-http-encoded/'
                u'test%20fetch%25http®.txt\t201\tdata/test fetch http®.txt', fetch_txt)
            self.assertIn(
                u'https://raw.githubusercontent.com/fair-research/bdbag/master/test/test-data/test-http-encoded/'
                u'test%20fetch%25http®.txt\t201\tdata/test%25fetch http®%0D%0A.txt', fetch_txt)
            bdb.validate_bag_structure(bag_dir, True)
        except Exception as e:
            self.fail(bdbag.get_typed_exception(e))

    def test_validate_profile(self):
        logger.info(self.getTestHeader('validate profile'))
        try:
            profile = bdb.validate_bag_profile(self.test_bag_profile_dir)
            self.assertIsInstance(profile, bdbagit_profile.Profile)
        except Exception as e:
            self.fail(bdbag.get_typed_exception(e))

    def test_validate_profile_serialization_zip(self):
        logger.info(self.getTestHeader('validate profile serialization zip'))
        try:
            bag_path = ospj(self.test_archive_dir, 'test-bag.zip')
            bdb.validate_bag_serialization(
                bag_path,
                bag_profile_path=
                'https://raw.githubusercontent.com/fair-research/bdbag/master/profiles/bdbag-profile.json')
        except Exception as e:
            self.fail(bdbag.get_typed_exception(e))

    def test_validate_profile_serialization_tar(self):
        logger.info(self.getTestHeader('validate profile serialization tar'))
        try:
            bag_path = ospj(self.test_archive_dir, 'test-bag.tar')
            bdb.validate_bag_serialization(
                bag_path,
                bag_profile_path=
                'https://raw.githubusercontent.com/fair-research/bdbag/master/profiles/bdbag-profile.json')
        except Exception as e:
            self.fail(bdbag.get_typed_exception(e))

    def test_validate_profile_serialization_tgz(self):
        logger.info(self.getTestHeader('validate profile serialization tgz'))
        try:
            bag_path = ospj(self.test_archive_dir, 'test-bag.tgz')
            bdb.validate_bag_serialization(
                bag_path,
                bag_profile_path=
                'https://raw.githubusercontent.com/fair-research/bdbag/master/profiles/bdbag-profile.json')
        except Exception as e:
            self.fail(bdbag.get_typed_exception(e))

    def test_validate_invalid_profile_serialization_bag_dir(self):
        logger.info(self.getTestHeader('validate invalid profile serialization on a bag dir'))
        try:
            bag_path = ospj(self.test_bag_dir)
            self.assertRaises(bdbagit_profile.ProfileValidationError,
                              bdb.validate_bag_serialization,
                              bag_path,
                              bag_profile_path=
                              'https://raw.githubusercontent.com/fair-research/bdbag/master/profiles/'
                              'bdbag-profile.json')
        except Exception as e:
            self.fail(bdbag.get_typed_exception(e))

    def test_validate_invalid_profile_serialization_unsupported_format(self):
        logger.info(self.getTestHeader('validate invalid profile serialization on an unsupported archive format'))
        try:
            bag_path = ospj(self.test_archive_dir, 'test-bag.7z')
            self.assertRaises(bdbagit_profile.ProfileValidationError,
                              bdb.validate_bag_serialization,
                              bag_path,
                              bag_profile_path=
                              'https://raw.githubusercontent.com/fair-research/bdbag/master/profiles/'
                              'bdbag-profile.json')
        except Exception as e:
            self.fail(bdbag.get_typed_exception(e))

    def test_validate_remote_bag_from_rfm(self):
        logger.info(self.getTestHeader('create, resolve, and validate bag from remote file manifest'))
        try:
            self._test_bag_with_remote_file_manifest()
            self.assertTrue(bdb.resolve_fetch(self.test_data_dir), "Fetch incomplete")
            bdb.validate_bag(self.test_data_dir, fast=True)
            bdb.validate_bag(self.test_data_dir, fast=False)
        except Exception as e:
            self.fail(bdbag.get_typed_exception(e))

    def test_resolve_fetch_http(self):
        logger.info(self.getTestHeader('test resolve fetch http'))
        try:
            self.assertTrue(bdb.resolve_fetch(self.test_bag_fetch_http_dir, cookie_scan=False), "Fetch incomplete")
            bdb.validate_bag(self.test_bag_fetch_http_dir, fast=True)
            bdb.validate_bag(self.test_bag_fetch_http_dir, fast=False)
        except Exception as e:
            self.fail(bdbag.get_typed_exception(e))

    def test_resolve_fetch_http_no_redirects(self):
        logger.info(self.getTestHeader('test resolve fetch http no redirects'))
        try:
            self.assertFalse(bdb.resolve_fetch(self.test_bag_fetch_http_no_redirect_dir,
                                               config_file=ospj(self.test_config_dir, 'test-config-6.json'),
                                               cookie_scan=False), "Fetch complete")
        except Exception as e:
            self.fail(bdbag.get_typed_exception(e))

    def test_resolve_fetch_http_unexpected_filesize(self):
        logger.info(self.getTestHeader('test resolve fetch http unexpected filesize warning'))
        try:
            self.assertTrue(bdb.resolve_fetch(self.test_bag_fetch_http_unexpected_filesize_dir, cookie_scan=False),
                            "Fetch incomplete")
            output = self.stream.getvalue()
            self.assertExpectedMessages(["transfer size mismatch. Expected 200 bytes but received 201 bytes"], output)
        except Exception as e:
            self.fail(bdbag.get_typed_exception(e))

    def test_resolve_fetch_http_encoded_filename(self):
        logger.info(self.getTestHeader('test resolve fetch http with encoded filename'))
        try:
            self.assertTrue(bdb.resolve_fetch(self.test_bag_fetch_http_encoded_filename_dir, cookie_scan=False),
                            "Fetch incomplete")
            bdb.validate_bag(self.test_bag_fetch_http_encoded_filename_dir, fast=True)
            bdb.validate_bag(self.test_bag_fetch_http_encoded_filename_dir, fast=False)
        except Exception as e:
            self.fail(bdbag.get_typed_exception(e))

    def test_resolve_fetch_http_with_callback_cancel(self):
        logger.info(self.getTestHeader('test resolve fetch http'))
        try:
            def callback(current, total):
                if current < total - 1:
                    return True
                else:
                    return False

            self.assertFalse(bdb.resolve_fetch(self.test_bag_fetch_http_dir, callback=callback, cookie_scan=False))
        except Exception as e:
            self.fail(bdbag.get_typed_exception(e))

    def test_resolve_fetch_http_bad_request(self):
        logger.info(self.getTestHeader('test resolve fetch http bad url path'))
        try:
            self.assertFalse(bdb.resolve_fetch(self.test_bag_fetch_http_bad_dir,
                                               config_file=ospj(self.test_config_dir, 'test-config-3.json'),
                                               cookie_scan=False))
            output = self.stream.getvalue()
            self.assertExpectedMessages(["HTTP GET Failed for URL",
                                         "HTTP Request Exception",
                                         "Transfer protocol",
                                         "is not supported"],
                                        output)
        except Exception as e:
            self.fail(bdbag.get_typed_exception(e))

    def test_resolve_fetch_http_bypass_ssl_cert_verify_global(self):
        logger.info(self.getTestHeader('test resolve fetch http bypass ssl cert verify global'))
        try:
            self.assertTrue(bdb.resolve_fetch(self.test_bag_fetch_http_dir,
                                              config_file=ospj(self.test_config_dir, 'test-config-11.json'),
                                              cookie_scan=False))
            output = self.stream.getvalue()
            self.assertExpectedMessages(["Bypassing SSL certificate verification due to global configuration setting."],
                                        output)
        except Exception as e:
            self.fail(bdbag.get_typed_exception(e))

    def test_resolve_fetch_http_bypass_ssl_cert_verify_whitelisted_uri(self):
        logger.info(self.getTestHeader('test resolve fetch http bypass ssl cert verify whitelisted uri'))
        try:
            self.assertTrue(bdb.resolve_fetch(self.test_bag_fetch_http_dir,
                                              config_file=ospj(self.test_config_dir, 'test-config-12.json'),
                                              cookie_scan=False))
            output = self.stream.getvalue()
            self.assertExpectedMessages(["Bypassing SSL certificate validation for URL",
                                         "due to matching whitelist entry"],
                                        output)
        except Exception as e:
            self.fail(bdbag.get_typed_exception(e))

    def test_resolve_fetch_incomplete(self):
        logger.info(self.getTestHeader('test resolve fetch incomplete'))
        try:
            self.assertTrue(bdb.resolve_fetch(self.test_bag_incomplete_fetch_dir,
                                              force=False, cookie_scan=False, quiet=False),
                            "Fetch incomplete")
            bdb.validate_bag(self.test_bag_incomplete_fetch_dir, fast=True)
            bdb.validate_bag(self.test_bag_incomplete_fetch_dir, fast=False)
        except Exception as e:
            self.fail(bdbag.get_typed_exception(e))

    def _test_resolve_fetch_http_with_filter(self, expr, files):
        logger.info(self.getTestHeader('test resolve fetch http with filter expression "%s"' % expr))
        try:
            self.assertTrue(bdb.resolve_fetch(self.test_bag_fetch_http_dir,
                                              filter_expr=expr,
                                              cookie_scan=False),
                            "Fetch incomplete")
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
            patched_requests_get = None

            def mocked_request_auth_get_success(*args, **kwargs):
                args[0].auth = None
                patched_requests_get.stop()
                return BaseTest.MockResponse({}, 200)

            patched_requests_get = mock.patch.multiple("bdbag.fetch.transports.fetch_http.requests.Session",
                                                       get=mocked_request_auth_get_success,
                                                       auth=None,
                                                       create=True)

            patched_requests_get.start()
            self.assertTrue(bdb.resolve_fetch(self.test_bag_fetch_http_dir,
                                              keychain_file=ospj(self.test_config_dir, 'test-keychain-1.json'),
                                              cookie_scan=False), "Fetch incomplete")
            bdb.validate_bag(self.test_bag_fetch_http_dir, fast=True)
            bdb.validate_bag(self.test_bag_fetch_http_dir, fast=False)
        except Exception as e:
            self.fail(bdbag.get_typed_exception(e))

    def test_resolve_fetch_http_basic_auth_get_bad_key(self):
        logger.info(self.getTestHeader('test resolve fetch http basic auth GET with bad key'))
        try:
            self.assertTrue(bdb.resolve_fetch(self.test_bag_fetch_http_dir,
                                              keychain_file=ospj(self.test_config_dir, 'test-keychain-bad-1.json'),
                                              cookie_scan=False))
            output = self.stream.getvalue()
            self.assertExpectedMessages(["Missing required parameters [username, password]"], output)
        except Exception as e:
            self.fail(bdbag.get_typed_exception(e))

    def _test_resolve_fetch_http_auth_post(self, keychain_file):
        try:
            def mocked_request_auth_post_success(*args, **kwargs):
                args[0].auth = None
                patched_requests_post.stop()
                return BaseTest.MockResponse({}, 201)

            patched_requests_post = mock.patch.multiple("bdbag.fetch.transports.fetch_http.requests.Session",
                                                        post=mocked_request_auth_post_success,
                                                        auth=None,
                                                        create=True)
            patched_requests_post.start()
            self.assertTrue(bdb.resolve_fetch(self.test_bag_fetch_http_dir,
                                              keychain_file=ospj(self.test_config_dir, keychain_file),
                                              cookie_scan=False),
                            "Fetch incomplete")
            bdb.validate_bag(self.test_bag_fetch_http_dir, fast=True)
            bdb.validate_bag(self.test_bag_fetch_http_dir, fast=False)
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
            self.assertTrue(bdb.resolve_fetch(self.test_bag_fetch_http_dir,
                                              keychain_file=ospj(self.test_config_dir, 'test-keychain-4.json'),
                                              cookie_scan=False), "Fetch incomplete")
            bdb.validate_bag(self.test_bag_fetch_http_dir, fast=True)
            bdb.validate_bag(self.test_bag_fetch_http_dir, fast=False)
        except Exception as e:
            self.fail(bdbag.get_typed_exception(e))

    def test_resolve_fetch_http_auth_token_get(self):
        logger.info(self.getTestHeader('test resolve fetch http token auth'))
        try:
            patched_requests_get_auth = None

            def mocked_request_auth_token_get_success(*args, **kwargs):
                args[0].auth = None
                args[0].headers = {}
                patched_requests_get_auth.stop()
                return args[0].get(args[1], **kwargs)

            patched_requests_get_auth = mock.patch.multiple("bdbag.fetch.transports.fetch_http.requests.Session",
                                                            get=mocked_request_auth_token_get_success,
                                                            auth=None,
                                                            create=True)

            patched_requests_get_auth.start()
            self.assertTrue(bdb.resolve_fetch(self.test_bag_fetch_http_dir,
                            keychain_file=ospj(self.test_config_dir, 'test-keychain-6.json'),
                            cookie_scan=False), "Fetch incomplete")
            bdb.validate_bag(self.test_bag_fetch_http_dir, fast=True)
            bdb.validate_bag(self.test_bag_fetch_http_dir, fast=False)
        except Exception as e:
            self.fail(bdbag.get_typed_exception(e))

    def test_resolve_fetch_http_auth_token_get_with_allowed_redirects(self):
        logger.info(self.getTestHeader('test resolve fetch http token auth with allowed redirect'))
        try:
            patched_requests_get_auth = None

            def mocked_request_auth_token_get_success(*args, **kwargs):
                headers = args[0].headers or {}
                headers.update({"Location": args[1]})
                args[0].auth = None
                args[0].headers = {}
                patched_requests_get_auth.stop()
                return BaseTest.MockResponse({}, 302, headers=headers)

            patched_requests_get_auth = mock.patch.multiple("bdbag.fetch.transports.fetch_http.requests.Session",
                                                            get=mocked_request_auth_token_get_success,
                                                            auth=None,
                                                            create=True)

            patched_requests_get_auth.start()
            self.assertTrue(bdb.resolve_fetch(self.test_bag_fetch_http_dir,
                            keychain_file=ospj(self.test_config_dir, 'test-keychain-6.json'),
                                              cookie_scan=False), "Fetch incomplete")
            bdb.validate_bag(self.test_bag_fetch_http_dir, fast=True)
            bdb.validate_bag(self.test_bag_fetch_http_dir, fast=False)
        except Exception as e:
            self.fail(bdbag.get_typed_exception(e))

    def test_resolve_fetch_http_auth_token_get_with_disallowed_redirects(self):
        logger.info(self.getTestHeader('test resolve fetch http token auth with disallowed redirect'))
        try:
            patched_requests_get_auth = None

            def mocked_request_auth_token_get_success(*args, **kwargs):
                headers = args[0].headers or {}
                headers.update({"Location": args[1]})
                args[0].auth = None
                args[0].headers = {}
                patched_requests_get_auth.stop()
                return BaseTest.MockResponse({}, 302, headers=headers)

            patched_requests_get_auth = mock.patch.multiple("bdbag.fetch.transports.fetch_http.requests.Session",
                                                            get=mocked_request_auth_token_get_success,
                                                            auth=None,
                                                            create=True)

            patched_requests_get_auth.start()
            self.assertTrue(bdb.resolve_fetch(self.test_bag_fetch_http_dir,
                                              keychain_file=ospj(self.test_config_dir, 'test-keychain-7.json'),
                                              cookie_scan=False),
                            "Fetch incomplete")
            bdb.validate_bag(self.test_bag_fetch_http_dir, fast=True)
            bdb.validate_bag(self.test_bag_fetch_http_dir, fast=False)
            output = self.stream.getvalue()
            self.assertExpectedMessages(["Authorization bearer token propagation on redirect is disabled"], output)
        except Exception as e:
            self.fail(bdbag.get_typed_exception(e))

    def test_resolve_fetch_ark(self):
        logger.info(self.getTestHeader('test resolve fetch ark'))
        try:
            self.assertTrue(bdb.resolve_fetch(self.test_bag_fetch_ark_dir, cookie_scan=False), "Fetch incomplete")
            bdb.validate_bag(self.test_bag_fetch_ark_dir, fast=True)
            bdb.validate_bag(self.test_bag_fetch_ark_dir, fast=False)
        except Exception as e:
            self.fail(bdbag.get_typed_exception(e))

    def test_resolve_fetch_ark2(self):
        logger.info(self.getTestHeader('test resolve fetch ark2'))
        try:
            mock_response = {
                "admins": [
                    "urn:globus:auth:identity:7b315147-d8f6-4a80-853d-78b65826d734",
                    "urn:globus:groups:id:23acce4c-733f-11e8-a40d-0e847f194132",
                    "urn:globus:auth:identity:b2541312-d274-11e5-9131-bbb9500ff459",
                    "urn:globus:auth:identity:88204dba-e812-432a-abcd-ec631583a98c",
                    "urn:globus:auth:identity:58b31676-ef95-11e5-8ff7-5783aaa8fce7"
                ],
                "checksums": [
                    {
                        "function": "sha256",
                        "value": "59e6e0b91b51d49a5fb0e1068980d2e7d2b2001a6d11c59c64156d32e197a626"
                    }
                ],
                "identifier": "ark:/57799/b91FmdtR3Pf4Ct7",
                "landing_page": "https://identifiers.globus.org/ark:/57799/b91FmdtR3Pf4Ct7/landingpage",
                "location": [
                    "https://raw.githubusercontent.com/fair-research/bdbag/master/test/test-data/test-http/test-fetch-identifier.txt",
                    "http://raw.githubusercontent.com/fair-research/bdbag/master/test/test-data/test-http/test-fetch-identifier.txt"
                ],
                "metadata": {
                    "title": "BDBag identifier unit test file"
                },
                "visible_to": [
                    "public"
                ]
            }

            patched_resolve_ark_get = None

            def mocked_request_resolver_ark_get_success(*args, **kwargs):
                args[0].auth = None
                patched_resolve_ark_get.stop()
                return BaseTest.MockResponse(mock_response, 200)

            patched_resolve_ark_get = mock.patch.multiple("bdbag.fetch.resolvers.base_resolver.requests.Session",
                                                          get=mocked_request_resolver_ark_get_success,
                                                          auth=None,
                                                          create=True)
            patched_resolve_ark_get.start()

            self.assertTrue(bdb.resolve_fetch(self.test_bag_fetch_ark2_dir, cookie_scan=False), "Fetch incomplete")
            bdb.validate_bag(self.test_bag_fetch_ark2_dir, fast=True)
            bdb.validate_bag(self.test_bag_fetch_ark2_dir, fast=False)
        except Exception as e:
            self.fail(bdbag.get_typed_exception(e))

    def test_resolve_fetch_bad_ark(self):
        logger.info(self.getTestHeader('test resolve fetch bad ark'))
        try:
            self.assertFalse(bdb.resolve_fetch(self.test_bag_fetch_ark_bad_dir,
                                               config_file=ospj(self.test_config_dir, 'test-config-3.json'),
                                               cookie_scan=False))
            output = self.stream.getvalue()
            self.assertExpectedMessages(["No file locations were found for identifier"], output)
        except Exception as e:
            self.fail(bdbag.get_typed_exception(e))

    def test_resolve_fetch_ark_bad_response(self):
        logger.info(self.getTestHeader('test resolve fetch ark bad response'))
        try:
            self.assertFalse(bdb.resolve_fetch(self.test_bag_fetch_ark2_dir,
                                               config_file=ospj(self.test_config_dir, 'test-config-3.json'),
                                               cookie_scan=False), "Fetch complete")
        except Exception as e:
            self.fail(bdbag.get_typed_exception(e))

    def test_resolve_fetch_doi(self):
        logger.info(self.getTestHeader('test resolve fetch doi'))
        try:
            mock_response = {
                "@context": "http://schema.org",
                "@type": "Dataset",
                "@id": "https://doi.org/10.23725/9999-9999",  # fake DOI
                "identifier": [
                    {
                        "@type": "PropertyValue",
                        "propertyID": "doi",
                        "value": "https://doi.org/10.23725/9999-9999"  # fake DOI
                    },
                    {
                        "@type": "PropertyValue",
                        "propertyID": "minid",
                        "value": "ark:/57799/b91FmdtR3Pf4Ct7"
                    },
                    {
                        "@type": "PropertyValue",
                        "propertyID": "sha256",
                        "value": "59e6e0b91b51d49a5fb0e1068980d2e7d2b2001a6d11c59c64156d32e197a626"
                    }
                ],
                "url": "https://ors.datacite.org/doi:/10.23725/9999-9999",  # fake DOI
                "additionalType": "BDBAG Test file",
                "name": "test-fetch-identifier.txt",
                "author": {
                    "name": "BDBag"
                },
                "description": "BDBag identifier unit test file",
                "keywords": "bdbag, unit test",
                "datePublished": "2018-09-20",
                "contentUrl": [
                    "https://raw.githubusercontent.com/fair-research/bdbag/master/test/test-data/test-http/test-fetch-identifier.txt",
                    "http://raw.githubusercontent.com/fair-research/bdbag/master/test/test-data/test-http/test-fetch-identifier.txt"
                ],
                "schemaVersion": "http://datacite.org/schema/kernel-4",
                "publisher": {
                    "@type": "Organization",
                    "name": "fair-research.org"
                },
                "fileFormat": [
                    "text/plain "
                ]
            }
            patched_resolve_doi_get = None

            def mocked_request_resolver_doi_get_success(*args, **kwargs):
                args[0].auth = None
                patched_resolve_doi_get.stop()
                return BaseTest.MockResponse(mock_response, 200)

            patched_resolve_doi_get = mock.patch.multiple("bdbag.fetch.resolvers.base_resolver.requests.Session",
                                                          get=mocked_request_resolver_doi_get_success,
                                                          auth=None,
                                                          create=True)
            patched_resolve_doi_get.start()

            self.assertTrue(bdb.resolve_fetch(self.test_bag_fetch_doi_dir, cookie_scan=False), "Fetch incomplete")
            bdb.validate_bag(self.test_bag_fetch_doi_dir, fast=True)
            bdb.validate_bag(self.test_bag_fetch_doi_dir, fast=False)
        except Exception as e:
            self.fail(bdbag.get_typed_exception(e))

    def test_resolve_fetch_dataguid(self):
        logger.info(self.getTestHeader('test resolve fetch dataguid'))
        try:
            mock_response = {
                "data_object": {
                    "checksums": [
                        {
                            "checksum": "59e6e0b91b51d49a5fb0e1068980d2e7d2b2001a6d11c59c64156d32e197a626",
                            "type": "sha256"
                        }
                    ],
                    "created": "2018-09-20T17:00:21.428857",
                    "description": "BDBag identifier unit test file",
                    "id": "dg.4503/a5d79375-1ba8-418f-9dda-eb981375e599",  # fake DataGUID
                    "mime_type": "text/plain",
                    "name": "test-fetch-identifier.txt",
                    "size": 223,
                    "updated": "2018-09-20T17:00:21.428866",
                    "urls": [
                        {
                            "url": "https://raw.githubusercontent.com/fair-research/bdbag/master/test/test-data/test-http/test-fetch-identifier.txt"
                        },
                        {
                            "url": "http://raw.githubusercontent.com/fair-research/bdbag/master/test/test-data/test-http/test-fetch-identifier.txt"
                        }
                    ],
                    "version": "0d318219"
                }
            }
            patched_resolve_dataguid_get = None

            def mocked_request_resolver_dataguid_get_success(*args, **kwargs):
                args[0].auth = None
                patched_resolve_dataguid_get.stop()
                return BaseTest.MockResponse(mock_response, 200)

            patched_resolve_dataguid_get = mock.patch.multiple("bdbag.fetch.resolvers.base_resolver.requests.Session",
                                                               get=mocked_request_resolver_dataguid_get_success,
                                                               auth=None,
                                                               create=True)
            patched_resolve_dataguid_get.start()

            self.assertTrue(bdb.resolve_fetch(self.test_bag_fetch_dataguid_dir, cookie_scan=False), "Fetch incomplete")
            bdb.validate_bag(self.test_bag_fetch_dataguid_dir, fast=True)
            bdb.validate_bag(self.test_bag_fetch_dataguid_dir, fast=False)
        except Exception as e:
            self.fail(bdbag.get_typed_exception(e))

    def test_resolve_fetch_minid(self):
        logger.info(self.getTestHeader('test resolve fetch minid'))
        try:
            self.assertTrue(bdb.resolve_fetch(self.test_bag_fetch_minid_dir, cookie_scan=False), "Fetch incomplete")
            bdb.validate_bag(self.test_bag_fetch_minid_dir, fast=True)
            bdb.validate_bag(self.test_bag_fetch_minid_dir, fast=False)
        except Exception as e:
            self.fail(bdbag.get_typed_exception(e))

    def test_resolve_fetch_resolver_handler_not_found(self):
        logger.info(self.getTestHeader('test resolve fetch with resolver handler not found'))
        try:
            self.assertFalse(bdb.resolve_fetch(self.test_bag_fetch_minid_dir,
                                               config_file=ospj(self.test_config_dir, 'test-config-4.json'),
                                               cookie_scan=False), "Fetch complete")
        except Exception as e:
            self.fail(bdbag.get_typed_exception(e))

    def test_resolve_fetch_resolver_handler_unspecified(self):
        logger.info(self.getTestHeader('test resolve fetch with resolver handler unspecified'))
        try:
            self.assertTrue(bdb.resolve_fetch(self.test_bag_fetch_minid_dir,
                                              config_file=ospj(self.test_config_dir, 'test-config-5.json'),
                                              cookie_scan=False), "Fetch incomplete")
        except Exception as e:
            self.fail(bdbag.get_typed_exception(e))

    def test_resolve_fetch_resolver_scheme_not_supported(self):
        logger.info(self.getTestHeader('test resolve fetch with resolver scheme not supported'))
        try:
            self.assertFalse(bdb.resolve_fetch(self.test_bag_fetch_minid_dir,
                                               config_file=ospj(self.test_config_dir, 'test-config-6.json'),
                                               cookie_scan=False), "Fetch complete")
        except Exception as e:
            self.fail(bdbag.get_typed_exception(e))

    def test_resolve_fetch_ftp_no_auth(self):
        logger.info(self.getTestHeader('test resolve fetch ftp'))
        try:
            patched_urlretrieve = None

            def mocked_urlretrieve_success(*args, **kwargs):
                patched_urlretrieve.stop()
                return

            patched_urlretrieve = mock.patch.multiple("bdbag.fetch.transports.fetch_ftp",
                                                      urlretrieve=mocked_urlretrieve_success)
            patched_urlretrieve.start()

            self.assertTrue(bdb.resolve_fetch(self.test_bag_fetch_ftp_dir, force=True), "Fetch incomplete")
            bdb.validate_bag(self.test_bag_fetch_ftp_dir, fast=True)
            bdb.validate_bag(self.test_bag_fetch_ftp_dir, fast=False)
        except Exception as e:
            self.fail(bdbag.get_typed_exception(e))

    def test_resolve_fetch_ftp_auth(self):
        logger.info(self.getTestHeader('test resolve fetch ftp with auth'))
        try:
            patched_urlretrieve = None

            def mocked_urlretrieve_success(*args, **kwargs):
                patched_urlretrieve.stop()
                return

            patched_urlretrieve = mock.patch.multiple("bdbag.fetch.transports.fetch_ftp",
                                                      urlretrieve=mocked_urlretrieve_success)
            patched_urlretrieve.start()

            self.assertTrue(bdb.resolve_fetch(self.test_bag_fetch_auth_dir, force=True,
                            keychain_file=ospj(self.test_config_dir, 'test-keychain-5.json')), "Fetch incomplete")
            bdb.validate_bag(self.test_bag_fetch_auth_dir, fast=True)
            bdb.validate_bag(self.test_bag_fetch_auth_dir, fast=False)
        except Exception as e:
            self.fail(bdbag.get_typed_exception(e))

    def test_resolve_fetch_ftp_bad_request(self):
        logger.info(self.getTestHeader('test resolve fetch ftp bad requests'))
        try:
            patched_urlretrieve = None

            def mocked_urlretrieve_success(*args, **kwargs):
                patched_urlretrieve.stop()
                raise Exception("Mocked FTP urlretrieve error")

            patched_urlretrieve = mock.patch.multiple("bdbag.fetch.transports.fetch_ftp",
                                                      urlretrieve=mocked_urlretrieve_success)
            patched_urlretrieve.start()

            self.assertFalse(bdb.resolve_fetch(self.test_bag_fetch_ftp_dir, force=True), "Fetch complete")
        except Exception as e:
            self.fail(bdbag.get_typed_exception(e))

    def test_resolve_fetch_tag(self):
        logger.info(self.getTestHeader('test resolve fetch tag'))
        try:
            self.assertTrue(bdb.resolve_fetch(self.test_bag_fetch_tag_dir, cookie_scan=False), "Fetch incomplete")
            output = self.stream.getvalue()
            self.assertExpectedMessages(["The fetch entry for file", "specifies the tag URI"], output)
        except Exception as e:
            self.fail(bdbag.get_typed_exception(e))

    def test_fetch_single(self):
        logger.info(self.getTestHeader('test fetch single file'))
        try:
            output_path = ospj(self.test_bag_fetch_http_dir, "test-fetch-http.txt")
            fetcher.fetch_single_file(
                "https://raw.githubusercontent.com/fair-research/bdbag/master/test/test-data/test-http/"
                "test-fetch-http.txt",
                output_path)
            self.assertTrue(os.path.exists(output_path))
        except Exception as e:
            self.fail(bdbag.get_typed_exception(e))

    def test_materialize_non_bag(self):
        logger.info(self.getTestHeader('test materialize non-bag'))
        curdir = os.getcwd()
        os.chdir(self.tmpdir)
        try:
            bag_path = bdb.materialize(self.test_data_dir)
            self.assertFalse(bdb.is_bag(bag_path))
        except Exception as e:
            self.fail(bdbag.get_typed_exception(e))
        finally:
            os.chdir(curdir)

    def test_materialize_from_dir(self):
        logger.info(self.getTestHeader('test materialize from dir'))
        curdir = os.getcwd()
        os.chdir(self.tmpdir)
        try:
            bag_path = bdb.materialize(self.test_bag_fetch_http_dir)
            self.assertTrue(bdb.is_bag(bag_path))
        except Exception as e:
            self.fail(bdbag.get_typed_exception(e))
        finally:
            os.chdir(curdir)

    def test_materialize_from_file(self):
        logger.info(self.getTestHeader('test materialize from file'))
        curdir = os.getcwd()
        os.chdir(self.tmpdir)
        try:
            bag_path = bdb.materialize(ospj(self.test_archive_dir, 'test-bag-fetch-http.zip'))
            self.assertTrue(bdb.is_bag(bag_path))
        except Exception as e:
            self.fail(bdbag.get_typed_exception(e))
        finally:
            os.chdir(curdir)

    def test_materialize_from_file_to_target_dir(self):
        logger.info(self.getTestHeader('test materialize from file to target dir'))
        try:
            bag_path = bdb.materialize(ospj(self.test_archive_dir, 'test-bag-fetch-http.zip'), self.tmpdir)
            self.assertTrue(bdb.is_bag(bag_path))
        except Exception as e:
            self.fail(bdbag.get_typed_exception(e))

    def test_materialize_from_url(self):
        logger.info(self.getTestHeader('test materialize from URL'))
        curdir = os.getcwd()
        os.chdir(self.tmpdir)
        try:
            bag_path = bdb.materialize("https://github.com/fair-research/bdbag/raw/master/test/test-data/test-archives/"
                                       "test-bag.zip")
            self.assertTrue(bdb.is_bag(bag_path))
        except Exception as e:
            self.fail(bdbag.get_typed_exception(e))
        finally:
            os.chdir(curdir)

    def test_materialize_from_url_to_target_dir(self):
        logger.info(self.getTestHeader('test materialize from URL to target dir'))
        try:
            bag_path = bdb.materialize("https://github.com/fair-research/bdbag/raw/master/test/test-data/test-archives/"
                                       "test-bag.zip", self.tmpdir)
            self.assertTrue(bdb.is_bag(bag_path))
        except Exception as e:
            self.fail(bdbag.get_typed_exception(e))

    def test_cookie_load_and_merge(self):
        logger.info(self.getTestHeader('test cookie load and merge'))
        try:
            cookie_jar_paths = [ospj(self.test_config_dir, "test-cookies-1.txt"),
                                ospj(self.test_config_dir, "test-cookies-2.txt")]
            cookies.load_and_merge_cookie_jars(cookie_jar_paths)
        except Exception as e:
            self.fail(bdbag.get_typed_exception(e))

    def test_cookie_load_and_merge_failure(self):
        logger.info(self.getTestHeader('test cookie load and merge'))
        try:
            cookie_jar_paths = [ospj(self.test_config_dir, "test-cookies-bad.txt"),
                                ospj(self.test_config_dir, "test-cookies-2.txt")]
            cookies.load_and_merge_cookie_jars(cookie_jar_paths)
            output = self.stream.getvalue()
            self.assertExpectedMessages(["Unable to load cookie file"], output)
        except Exception as e:
            self.fail(bdbag.get_typed_exception(e))

    def test_materialize_from_identifier(self):
        logger.info(self.getTestHeader('test materialize from identifier'))
        curdir = os.getcwd()
        os.chdir(self.tmpdir)
        try:
            bdb.materialize("minid:b91H6JHBS1u2FTG")
        except Exception as e:
            self.fail(bdbag.get_typed_exception(e))
        finally:
            os.chdir(curdir)

    def test_update_keychain_single(self):
        logger.info(self.getTestHeader('test update keychain single'))
        keychain_file = ospj(self.test_config_dir, 'test-keychain-8.json')
        updated_entry = {
            "uri": "https://raw.githubusercontent.com/",
            "auth_type": "http-basic",
            "auth_params": {
              "auth_method": "get",
              "username": "foo",
              "password": "bar!"
            }
          }
        try:
            updated_keychain = update_keychain(updated_entry, keychain_file=keychain_file)
            logger.info("Updated keychain: %s" % json.dumps(updated_keychain))
            entries = get_auth_entries("https://raw.githubusercontent.com/", updated_keychain)
            found = False
            for entry in entries:
                if entry["auth_type"] == "http-basic":
                    if entry["auth_params"]["username"] == "foo" and entry["auth_params"]["password"] == "bar!":
                        found = True
                        break
            self.assertTrue(found)
        except Exception as e:
            self.fail(bdbag.get_typed_exception(e))

    def test_update_keychain_multi(self):
        logger.info(self.getTestHeader('test update keychain multi'))
        keychain_file = ospj(self.test_config_dir, 'test-keychain-8.json')
        updated_entries = [
            {
                "uri": "https://raw.githubusercontent.com/",
                "auth_type": "http-basic",
                "auth_params": {
                  "auth_method": "get",
                  "username": "fake",
                  "password": "bar!"
                }
            },
            {
                "uri": "https://raw.githubusercontent.com/",
                "auth_type": "bearer-token",
                "auth_params": {
                    "token": "bar",
                    "allow_redirects_with_token": "True",
                    "additional_request_headers": {
                        "X-Requested-With": "XMLHttpRequest"
                    }
                }
            }
        ]
        try:
            updated_keychain = update_keychain(updated_entries, keychain_file=keychain_file)
            logger.info("Updated keychain: %s" % json.dumps(updated_keychain))
            entries = get_auth_entries("https://raw.githubusercontent.com/", updated_keychain)
            found1 = found2 = False
            for entry in entries:
                if entry["auth_type"] == "http-basic":
                    if entry["auth_params"]["password"] == "bar!":
                        found1 = True
                if entry["auth_type"] == "bearer-token":
                    if entry["auth_params"]["allow_redirects_with_token"] == "True":
                        found2 = True
            self.assertTrue(found1 and found2)
        except Exception as e:
            self.fail(bdbag.get_typed_exception(e))

    def test_update_keychain_add_single(self):
        logger.info(self.getTestHeader('test update keychain add single'))
        keychain_file = ospj(self.test_config_dir, 'test-keychain-8.json')
        added_entry = {
            "uri": "https://foo.bar.com/",
            "auth_type": "http-basic",
            "auth_params": {
              "auth_method": "get",
              "username": "foo",
              "password": "bar!"
            }
          }
        try:
            keychain = read_keychain(keychain_file, create_default=False)
            entries = get_auth_entries("https://foo.bar.com/", keychain)
            self.assertFalse(entries)
            updated_keychain = update_keychain(added_entry, keychain_file=keychain_file)
            logger.info("Updated keychain: %s" % json.dumps(updated_keychain))
            entries = get_auth_entries("https://foo.bar.com/", updated_keychain)
            self.assertTrue(len(entries) == 1)
        except Exception as e:
            self.fail(bdbag.get_typed_exception(e))

    def test_update_keychain_add_multi(self):
        logger.info(self.getTestHeader('test update keychain add multi'))
        keychain_file = ospj(self.test_config_dir, 'test-keychain-8.json')
        added_entries = [
            {
                "uri": "https://foo.bar.com/",
                "auth_type": "http-basic",
                "auth_params": {
                  "auth_method": "get",
                  "username": "fake",
                  "password": "bar!"
                }
            },
            {
                "uri": "https://foo.bar.com/",
                "auth_type": "bearer-token",
                "auth_params": {
                    "token": "bar",
                    "allow_redirects_with_token": "True",
                    "additional_request_headers": {
                        "X-Requested-With": "XMLHttpRequest"
                    }
                }
            }
        ]
        try:
            keychain = read_keychain(keychain_file, create_default=False)
            entries = get_auth_entries("https://foo.bar.com/", keychain)
            self.assertFalse(entries)
            updated_keychain = update_keychain(added_entries, keychain_file=keychain_file)
            logger.info("Updated keychain: %s" % json.dumps(updated_keychain))
            entries = get_auth_entries("https://foo.bar.com/", updated_keychain)
            self.assertTrue(len(entries) == 2)
        except Exception as e:
            self.fail(bdbag.get_typed_exception(e))

    def test_update_keychain_del_single(self):
        logger.info(self.getTestHeader('test update keychain del single'))
        keychain_file = ospj(self.test_config_dir, 'test-keychain-8.json')
        deleted_entry = {
            "uri": "ftp://ftp.nist.gov/",
            "auth_type": "ftp-basic"
        }
        try:
            keychain = read_keychain(keychain_file, create_default=False)
            entries = get_auth_entries("ftp://ftp.nist.gov/", keychain)
            self.assertTrue(len(entries) == 1)
            updated_keychain = update_keychain(deleted_entry, keychain_file=keychain_file, delete=True)
            logger.info("Updated keychain: %s" % json.dumps(updated_keychain))
            entries = get_auth_entries("ftp://ftp.nist.gov/", updated_keychain)
            self.assertFalse(entries)
        except Exception as e:
            self.fail(bdbag.get_typed_exception(e))

    def test_update_keychain_del_multi(self):
        logger.info(self.getTestHeader('test update keychain del multi'))
        keychain_file = ospj(self.test_config_dir, 'test-keychain-8.json')
        deleted_entries = [
            {
                "uri": "https://raw.githubusercontent.com/",
                "auth_type": "http-basic"
            },
            {
                "uri": "https://raw.githubusercontent.com/",
                "auth_type": "bearer-token"
            }
        ]
        try:
            keychain = read_keychain(keychain_file, create_default=False)
            entries = get_auth_entries("https://raw.githubusercontent.com/", keychain)
            self.assertTrue(entries)
            updated_keychain = update_keychain(deleted_entries, keychain_file=keychain_file, delete=True)
            logger.info("Updated keychain: %s" % json.dumps(updated_keychain))
            entries = get_auth_entries("https://raw.githubusercontent.com/", updated_keychain)
            self.assertFalse(entries)
        except Exception as e:
            self.fail(bdbag.get_typed_exception(e))

    def test_update_keychain_del_by_tag(self):
        logger.info(self.getTestHeader('test update keychain del by tag'))
        keychain_file = ospj(self.test_config_dir, 'test-keychain-8.json')
        deleted_entries = {"tag": "unit test"}
        try:
            keychain = read_keychain(keychain_file, create_default=False)
            entries = get_auth_entries("https://raw.githubusercontent.com/", keychain)
            self.assertTrue(entries)
            updated_keychain = update_keychain(deleted_entries, keychain_file=keychain_file, delete=True)
            logger.info("Updated keychain: %s" % json.dumps(updated_keychain))
            entries = get_auth_entries("https://raw.githubusercontent.com/", updated_keychain)
            self.assertFalse(entries)
        except Exception as e:
            self.fail(bdbag.get_typed_exception(e))

    def test_update_keychain_invalid_params(self):
        logger.info(self.getTestHeader('test update keychain invalid params'))
        keychain_file = ospj(self.test_config_dir, 'test-keychain-8.json')
        deleted_entries = [
            {
                "uri": "https://raw.githubusercontent.com/",
            },
            {
                "auth_type": "bearer-token"
            },
            {
                "uri": "ftp://ftp.nist.gov/",
                "tag": "invalid"
            }
        ]
        try:
            keychain = read_keychain(keychain_file, create_default=False)
            entries = get_auth_entries("https://raw.githubusercontent.com/", keychain)
            self.assertTrue(entries)
            updated_keychain = update_keychain(deleted_entries, keychain_file=keychain_file, delete=True)
            logger.info("Updated keychain: %s" % json.dumps(updated_keychain))
            self.assertTrue(len(updated_keychain) == 3)
        except Exception as e:
            self.fail(bdbag.get_typed_exception(e))

    def test_resolve_fetch_custom_handler_no_keychain(self):
        logger.info(self.getTestHeader('test resolve fetch custom handler no keychain'))
        try:
            self.assertTrue(bdb.resolve_fetch(self.test_bag_fetch_http_dir,
                                              config_file=ospj(self.test_config_dir, 'test-config-7.json'),
                                              cookie_scan=False),
                            "Fetch incomplete")
            output = self.stream.getvalue()
            self.assertExpectedMessages(["Keychain will not be passed to fetch handler class"], output)
            bdb.validate_bag(self.test_bag_fetch_http_dir, fast=True)
            bdb.validate_bag(self.test_bag_fetch_http_dir, fast=False)
        except Exception as e:
            self.fail(bdbag.get_typed_exception(e))

    def test_resolve_fetch_custom_handler_with_keychain(self):
        logger.info(self.getTestHeader('test resolve fetch custom handler with keychain'))
        try:
            self.assertTrue(bdb.resolve_fetch(self.test_bag_fetch_http_dir,
                                              config_file=ospj(self.test_config_dir, 'test-config-8.json'),
                                              keychain_file=ospj(self.test_config_dir, 'test-keychain-9.json'),
                                              cookie_scan=False),
                            "Fetch incomplete")
            output = self.stream.getvalue()
            self.assertExpectedMessages(["Got propagated keychain: ", "ftp://ftp.nist.gov/"], output)
            bdb.validate_bag(self.test_bag_fetch_http_dir, fast=True)
            bdb.validate_bag(self.test_bag_fetch_http_dir, fast=False)
        except Exception as e:
            self.fail(bdbag.get_typed_exception(e))

    def test_resolve_fetch_bad_custom_handler(self):
        logger.info(self.getTestHeader('test resolve fetch bad custom handler'))
        try:
            self.assertRaisesRegex(NotImplementedError,
                                   "Method must be implemented by subclass",
                                   bdb.resolve_fetch,
                                   self.test_bag_fetch_http_dir,
                                   config_file=ospj(self.test_config_dir, 'test-config-9.json'),
                                   cookie_scan=False)
        except Exception as e:
            self.fail(bdbag.get_typed_exception(e))

    def test_resolve_fetch_invalid_custom_handler(self):
        logger.info(self.getTestHeader('test resolve fetch invalid custom handler'))
        try:
            self.assertRaisesRegex(RuntimeError,
                                   "Unable to import specified fetch handler class: \\[foo\\.bar\\.InvalidHandler\\]",
                                   bdb.resolve_fetch,
                                   self.test_bag_fetch_http_dir,
                                   config_file=ospj(self.test_config_dir, 'test-config-10.json'),
                                   cookie_scan=False)
        except Exception as e:
            self.fail(bdbag.get_typed_exception(e))

    @unittest.skip("Not implemented")
    def test_resolve_fetch_globus(self):
        # TODO
        pass


if __name__ == '__main__':
    unittest.main()
