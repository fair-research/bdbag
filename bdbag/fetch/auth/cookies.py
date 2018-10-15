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
import fnmatch
import logging
from requests.cookies import RequestsCookieJar
from bdbag import stob, get_typed_exception
from bdbag.bdbag_config import *

if sys.version_info > (3,):
    from http.cookiejar import MozillaCookieJar
else:
    from cookielib import MozillaCookieJar


def find_cookie_jars(cookie_jar_config=None):
    found = list()
    if cookie_jar_config:
        search = stob(cookie_jar_config.get(COOKIE_JAR_SEARCH_TAG, True))
        if search:
            paths = cookie_jar_config.get(COOKIE_JAR_PATHS_TAG, [])
            for path in paths:
                for root, dirs, files in os.walk(path, topdown=True):
                    dirs[:] = [d for d in fnmatch.filter(
                        dirs, cookie_jar_config.get(COOKIE_JAR_PATH_FILTER_TAG, DEFAULT_COOKIE_JAR_SEARCH_PATH_FILTER))]
                    patterns = cookie_jar_config.get(COOKIE_JAR_FILE_TAG, DEFAULT_COOKIE_JAR_FILE_NAMES)
                    if dirs:
                        logging.debug("Scanning directories %s in %s for cookie files named: %s" %
                                      (dirs, root, patterns))
                    for pattern in patterns:
                        for f in fnmatch.filter(files, pattern):
                            found.append(os.path.join(root, f))
    return found


def load_and_merge_cookie_jars(cookie_jar_paths):
    cookie_jar = RequestsCookieJar()
    if not cookie_jar_paths:
        return cookie_jar

    logging.debug("Attempting to load and merge the following cookie files: %s" % cookie_jar_paths)
    for f in cookie_jar_paths:
        if os.path.isfile(f):
            try:
                cookies = MozillaCookieJar(f)
                cookies.load(ignore_expires=True, ignore_discard=True)
                cookie_jar.update(cookies)
            except Exception as e:
                logging.warning("Unable to load cookie file [%s]: %s" % (f, get_typed_exception(e)))

    # Do not preserve expire values from cookies with expires=0 from the file, or requests will not use the cookie
    for cookie in iter(cookie_jar):
        if not cookie.expires:
            cookie.expires = None

    return cookie_jar
