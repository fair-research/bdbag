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
import gc
import sys
import shutil
import tempfile
import unittest
import logging
import bagit
from bdbag.bdbag_api import configure_logging

configure_logging(logpath='test.log', filemode='w', level=logging.DEBUG)


class BaseTest(unittest.TestCase):

    def setUp(self):

        if sys.version_info < (3,):
            self.assertRaisesRegex = self.assertRaisesRegexp

        self.tmpdir = tempfile.mkdtemp(prefix="bdbag_test_")
        shutil.copytree(os.path.abspath(os.path.join('test', 'test-data')), os.path.join(self.tmpdir, 'test-data'))

        self.test_data_dir = os.path.join(self.tmpdir, 'test-data', 'test-dir')
        self.assertTrue(os.path.isdir(self.test_data_dir))
        self.test_archive_dir = os.path.join(self.tmpdir, 'test-data', 'test-archives')
        self.assertTrue(os.path.isdir(self.test_archive_dir))
        self.test_config_dir = os.path.join(self.tmpdir, 'test-data', 'test-config')
        self.assertTrue(os.path.isdir(self.test_config_dir))
        self.test_http_dir = os.path.join(self.tmpdir, 'test-data', 'test-http')
        self.assertTrue(os.path.isdir(self.test_http_dir))

        self.test_bag_dir = os.path.join(self.tmpdir, 'test-data', 'test-bag')
        self.assertTrue(os.path.isdir(self.test_bag_dir))
        self.test_bag_incomplete_dir = os.path.join(self.tmpdir, 'test-data', 'test-bag-incomplete')
        self.assertTrue(os.path.isdir(self.test_bag_incomplete_dir))
        self.test_bag_incomplete_fetch_dir = os.path.join(self.tmpdir, 'test-data', 'test-bag-incomplete-fetch')
        self.assertTrue(os.path.isdir(self.test_bag_incomplete_fetch_dir))
        self.test_bag_fetch_http_dir = os.path.join(self.tmpdir, 'test-data', 'test-bag-fetch-http')
        self.assertTrue(os.path.isdir(self.test_bag_fetch_http_dir))
        self.test_bag_fetch_http_bad_dir = os.path.join(self.tmpdir, 'test-data', 'test-bag-fetch-http-bad')
        self.assertTrue(os.path.isdir(self.test_bag_fetch_http_bad_dir))
        self.test_bag_fetch_ark_dir = os.path.join(self.tmpdir, 'test-data', 'test-bag-fetch-ark')
        self.assertTrue(os.path.isdir(self.test_bag_fetch_ark_dir))
        self.test_bag_fetch_ark2_dir = os.path.join(self.tmpdir, 'test-data', 'test-bag-fetch-ark2')
        self.assertTrue(os.path.isdir(self.test_bag_fetch_ark2_dir))
        self.test_bag_fetch_doi_dir = os.path.join(self.tmpdir, 'test-data', 'test-bag-fetch-doi')
        self.assertTrue(os.path.isdir(self.test_bag_fetch_doi_dir))
        self.test_bag_fetch_dataguid_dir = os.path.join(self.tmpdir, 'test-data', 'test-bag-fetch-dataguid')
        self.assertTrue(os.path.isdir(self.test_bag_fetch_dataguid_dir))
        self.test_bag_fetch_minid_dir = os.path.join(self.tmpdir, 'test-data', 'test-bag-fetch-minid')
        self.assertTrue(os.path.isdir(self.test_bag_fetch_minid_dir))
        self.test_bag_fetch_ftp_dir = os.path.join(self.tmpdir, 'test-data', 'test-bag-fetch-ftp')
        self.assertTrue(os.path.isdir(self.test_bag_fetch_ftp_dir))
        self.test_bag_fetch_auth_dir = os.path.join(self.tmpdir, 'test-data', 'test-bag-fetch-ftp-auth')
        self.assertTrue(os.path.isdir(self.test_bag_fetch_auth_dir))
        self.test_bag_invalid_structure_manifest_dir = os.path.join(
            self.tmpdir, 'test-data', 'test-bag-invalid-structure-manifest')
        self.assertTrue(os.path.isdir(self.test_bag_invalid_structure_manifest_dir))
        self.test_bag_invalid_structure_filesystem_dir = os.path.join(
            self.tmpdir, 'test-data', 'test-bag-invalid-structure-filesystem')
        self.assertTrue(os.path.isdir(self.test_bag_invalid_structure_filesystem_dir))
        self.test_bag_invalid_structure_fetch_dir = os.path.join(
            self.tmpdir, 'test-data', 'test-bag-invalid-structure-fetch')
        self.assertTrue(os.path.isdir(self.test_bag_invalid_structure_fetch_dir))
        self.test_bag_invalid_state_manifest_fetch_dir = os.path.join(
            self.tmpdir, 'test-data', 'test-bag-invalid-state-manifest-fetch')
        self.assertTrue(os.path.isdir(self.test_bag_invalid_state_manifest_fetch_dir))
        self.test_bag_invalid_state_fetch_filesize_dir = os.path.join(
            self.tmpdir, 'test-data', 'test-bag-invalid-state-fetch-filesize')
        self.assertTrue(os.path.isdir(self.test_bag_invalid_state_fetch_filesize_dir))
        self.test_bag_update_invalid_fetch_dir = os.path.join(
            self.tmpdir, 'test-data', 'test-bag-update-invalid-fetch')
        self.assertTrue(os.path.isdir(self.test_bag_update_invalid_fetch_dir))
        self.test_bag_invalid_state_duplicate_manifest_fetch_dir = os.path.join(
            self.tmpdir, 'test-data', 'test-bag-invalid-state-duplicate-manifest-fetch')
        self.assertTrue(os.path.isdir(self.test_bag_invalid_state_duplicate_manifest_fetch_dir))

    def tearDown(self):
        if os.path.isdir(self.tmpdir):
            shutil.rmtree(self.tmpdir)
        gc.collect()

    def assertExpectedMessages(self, messages, output):
        for expected in messages:
            self.assertIn(expected, output, "Expected \'%s\' in output string." % expected)

    def assertUnexpectedMessages(self, messages, output):
        for unexpected in messages:
            self.assertNotIn(unexpected, output, "Unexpected \'%s\' in output string." % unexpected)

    def getTestHeader(self, desc, args=None):
        return str('\n\n[%s: %s]\n%s') % (self.__class__.__name__, desc, (' '.join(args) + '\n') if args else "")

    @staticmethod
    def slurp_text_file(filename):
        with bagit.open_text_file(filename) as f:
            return f.read()

    class MockResponse:
        def __init__(self, json_data, status_code, headers={}):
            self.json_data = json_data
            self.status_code = status_code
            self.headers = headers

        def json(self):
            return self.json_data
