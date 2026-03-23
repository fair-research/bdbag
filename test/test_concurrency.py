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
import logging
import threading
import unittest
import mock
import bdbag.bdbagit as bdbagit
from bdbag.fetch.fetcher import fetch_bag_files
from bdbag.fetch.transports.fetch_http import HTTPFetchTransport
from test.test_common import BaseTest

logger = logging.getLogger()

PATCHED_REQUESTS_GET = "bdbag.fetch.transports.fetch_http.requests.Session.get"


def mock_fetch_response(url, stream=True, headers=None, allow_redirects=True, verify=True, cookies=None):
    return mock.Mock(status_code=200,
                     iter_content=lambda chunk_size: [b"fake data"],
                     headers={})


class TestConcurrentFetch(BaseTest):

    def setUp(self):
        super(TestConcurrentFetch, self).setUp()

    def tearDown(self):
        super(TestConcurrentFetch, self).tearDown()

    @mock.patch(PATCHED_REQUESTS_GET, side_effect=mock_fetch_response)
    def test_serial_fetch_concurrency_1(self, mock_get):
        """fetch_concurrency=1 should use the serial path and complete all fetches."""
        logger.info(self.getTestHeader('test serial fetch with concurrency=1'))
        bag = bdbagit.BDBag(self.test_bag_fetch_http_dir)
        result = fetch_bag_files(bag, force=True, fetch_concurrency=1, cookie_scan=False)
        self.assertTrue(result)

    @mock.patch(PATCHED_REQUESTS_GET, side_effect=mock_fetch_response)
    def test_parallel_fetch_concurrency_gt1(self, mock_get):
        """fetch_concurrency>1 should use the parallel path and complete all fetches."""
        logger.info(self.getTestHeader('test parallel fetch with concurrency=4'))
        bag = bdbagit.BDBag(self.test_bag_fetch_http_dir)
        result = fetch_bag_files(bag, force=True, fetch_concurrency=4, cookie_scan=False)
        self.assertTrue(result)

    @mock.patch(PATCHED_REQUESTS_GET, side_effect=mock_fetch_response)
    def test_callback_cancellation_parallel(self, mock_get):
        """Callback returning False should cancel parallel fetching."""
        logger.info(self.getTestHeader('test callback cancellation in parallel mode'))
        bag = bdbagit.BDBag(self.test_bag_fetch_http_dir)

        def cancel_callback(current, total):
            return False

        result = fetch_bag_files(bag, force=True, fetch_concurrency=4, callback=cancel_callback, cookie_scan=False)
        self.assertFalse(result)

    @mock.patch(PATCHED_REQUESTS_GET)
    def test_one_failed_fetch_doesnt_block_others_parallel(self, mock_get):
        """One failed fetch should not block others in parallel mode."""
        logger.info(self.getTestHeader('test one failed fetch in parallel mode'))

        call_count = [0]
        lock = threading.Lock()

        def side_effect(url, stream=True, headers=None, allow_redirects=True, verify=True, cookies=None):
            with lock:
                call_count[0] += 1
                count = call_count[0]
            if count == 1:
                return mock.Mock(status_code=500,
                                 text="Internal Server Error",
                                 headers={})
            return mock.Mock(status_code=200,
                             iter_content=lambda chunk_size: [b"fake data"],
                             headers={})

        mock_get.side_effect = side_effect
        bag = bdbagit.BDBag(self.test_bag_fetch_http_dir)
        result = fetch_bag_files(bag, force=True, fetch_concurrency=4, cookie_scan=False)
        # Result should be False because one fetch failed, but all should have been attempted
        self.assertFalse(result)
        self.assertGreater(call_count[0], 1)

    def test_get_session_returns_per_thread_sessions(self):
        """Each thread must receive its own requests.Session, not a shared one."""
        transport = HTTPFetchTransport(config=None, keychain=None, cookie_scan=False)
        sessions = {}
        lock = threading.Lock()

        def capture(url):
            session = transport.get_session(url)
            with lock:
                sessions[threading.current_thread().ident] = session

        threads = [
            threading.Thread(target=capture, args=("https://example.com/file%d" % i,))
            for i in range(4)
        ]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        transport.cleanup()

        self.assertEqual(len(sessions), 4)
        # All four session objects must be distinct instances
        self.assertEqual(len(set(id(s) for s in sessions.values())), 4)


if __name__ == '__main__':
    unittest.main()
