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
            bdb.resolve_fetch(self.test_bag_fetch_http_dir, cookie_scan=False)
            bdb.validate_bag(self.test_bag_fetch_http_dir, fast=True)
            bdb.validate_bag(self.test_bag_fetch_http_dir, fast=False)
            output = self.stream.getvalue()
        except Exception as e:
            self.fail(bdbag.get_typed_exception(e))

    def _test_resolve_fetch_http_with_filter(self, expr, files):
        logger.info(self.getTestHeader('test resolve fetch http with filter expression "%s"' % expr))
        try:
            bdb.resolve_fetch(self.test_bag_fetch_http_dir, filter_expr=expr, cookie_scan=False)
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
            bdb.resolve_fetch(self.test_bag_fetch_http_dir,
                              keychain_file=ospj(self.test_config_dir, 'test-keychain-1.json'), cookie_scan=False)
            bdb.validate_bag(self.test_bag_fetch_http_dir, fast=True)
            bdb.validate_bag(self.test_bag_fetch_http_dir, fast=False)
            output = self.stream.getvalue()
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
            bdb.resolve_fetch(self.test_bag_fetch_http_dir,
                              keychain_file=ospj(self.test_config_dir, keychain_file), cookie_scan=False)
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
                              keychain_file=ospj(self.test_config_dir, 'test-keychain-4.json'), cookie_scan=False)
            bdb.validate_bag(self.test_bag_fetch_http_dir, fast=True)
            bdb.validate_bag(self.test_bag_fetch_http_dir, fast=False)
            output = self.stream.getvalue()
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
            bdb.resolve_fetch(self.test_bag_fetch_http_dir,
                              keychain_file=ospj(self.test_config_dir, 'test-keychain-6.json'), cookie_scan=False)
            bdb.validate_bag(self.test_bag_fetch_http_dir, fast=True)
            bdb.validate_bag(self.test_bag_fetch_http_dir, fast=False)
            output = self.stream.getvalue()
        except Exception as e:
            self.fail(bdbag.get_typed_exception(e))

    def test_resolve_fetch_ark(self):
        logger.info(self.getTestHeader('test resolve fetch ark'))
        try:
            bdb.resolve_fetch(self.test_bag_fetch_ark_dir, cookie_scan=False)
            bdb.validate_bag(self.test_bag_fetch_ark_dir, fast=True)
            bdb.validate_bag(self.test_bag_fetch_ark_dir, fast=False)
            output = self.stream.getvalue()
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
                    "https://raw.githubusercontent.com/fair-research/bdbag/master/test/test-data/test-http/test-fetch-identifier.txt"
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

            bdb.resolve_fetch(self.test_bag_fetch_ark2_dir, cookie_scan=False)
            bdb.validate_bag(self.test_bag_fetch_ark2_dir, fast=True)
            bdb.validate_bag(self.test_bag_fetch_ark2_dir, fast=False)
            output = self.stream.getvalue()
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
                    "https://raw.githubusercontent.com/fair-research/bdbag/master/test/test-data/test-http/test-fetch-identifier.txt"
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

            bdb.resolve_fetch(self.test_bag_fetch_doi_dir, cookie_scan=False)
            bdb.validate_bag(self.test_bag_fetch_doi_dir, fast=True)
            bdb.validate_bag(self.test_bag_fetch_doi_dir, fast=False)
            output = self.stream.getvalue()
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

            bdb.resolve_fetch(self.test_bag_fetch_dataguid_dir, cookie_scan=False)
            bdb.validate_bag(self.test_bag_fetch_dataguid_dir, fast=True)
            bdb.validate_bag(self.test_bag_fetch_dataguid_dir, fast=False)
            output = self.stream.getvalue()
        except Exception as e:
            self.fail(bdbag.get_typed_exception(e))

    def test_resolve_fetch_minid(self):
        logger.info(self.getTestHeader('test resolve fetch minid'))
        try:
            bdb.resolve_fetch(self.test_bag_fetch_minid_dir, cookie_scan=False)
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

    @unittest.skipIf(sys.version_info[:3] > (2, 7, 10), "https://bugs.python.org/issue27973")
    def test_resolve_fetch_ftp_auth(self):
        logger.info(self.getTestHeader('test resolve fetch ftp with auth'))
        try:
            bdb.resolve_fetch(self.test_bag_fetch_auth_dir,
                              keychain_file=ospj(self.test_config_dir, 'test-keychain-5.json'))
            bdb.validate_bag(self.test_bag_fetch_auth_dir, fast=True)
            bdb.validate_bag(self.test_bag_fetch_auth_dir, fast=False)
            output = self.stream.getvalue()
        except Exception as e:
            self.fail(bdbag.get_typed_exception(e))

#    def test_resolve_fetch_globus(self):
#        # TODO
#        pass


if __name__ == '__main__':
    unittest.main()
