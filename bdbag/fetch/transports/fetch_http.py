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
import datetime
import logging
import certifi
import requests
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry
from bdbag import urlsplit, stob, get_typed_exception
from bdbag.bdbag_config import DEFAULT_CONFIG, DEFAULT_FETCH_CONFIG, FETCH_CONFIG_TAG, \
    FETCH_HTTP_REDIRECT_STATUS_CODES_TAG, DEFAULT_FETCH_HTTP_REDIRECT_STATUS_CODES
from bdbag.fetch import Megabyte, get_transfer_summary, ensure_valid_output_path
import bdbag.fetch.auth.keychain as keychain

logger = logging.getLogger(__name__)

CHUNK_SIZE = 10 * Megabyte
SESSIONS = dict()
HEADERS = {'Connection': 'keep-alive'}


def validate_auth_config(auth):
    if not keychain.has_auth_attr(auth, 'auth_type'):
        return False
    if not keychain.has_auth_attr(auth, 'auth_params'):
        return False

    return True


def get_auth(url, auth_config):
    for auth in keychain.get_auth_entries(url, auth_config):
        if validate_auth_config(auth):
            return auth
    return None


def get_session(url, auth_config, config):

    session = None
    response = None

    for auth in keychain.get_auth_entries(url, auth_config):
        try:
            if not validate_auth_config(auth):
                continue

            uri = auth.get("uri")
            if uri in SESSIONS:
                session = SESSIONS[uri]
                break
            else:
                session = init_new_session(config["session_config"])

            auth_type = auth.get("auth_type")
            auth_params = auth.get("auth_params", {})

            if auth_type == 'cookie':
                if auth_params:
                    cookies = auth_params.get("cookies", [])
                    if cookies:
                        for cookie in cookies:
                            name, value = cookie.split('=', 1)
                            session.cookies.set(name, value, domain=urlsplit(uri).hostname, path='/')
                    session.headers.update(auth_params.get("additional_request_headers", {}))
                    SESSIONS[uri] = session
                    break

            if auth_type == 'bearer-token':
                token = auth_params.get("token")
                if token:
                    session.headers.update({"Authorization": "Bearer " + token})
                    session.headers.update(auth_params.get("additional_request_headers", {}))
                    SESSIONS[uri] = session
                    break
                else:
                    logging.warning("Missing required parameters [token] for auth_type [%s] for keychain entry [%s]" %
                                    (auth_type, uri))

            # if we get here the assumption is that the auth_type is either http-basic or http-form and that an
            # actual session "login" request is necessary
            auth_uri = auth.get("auth_uri", uri)
            username = auth_params.get("username")
            password = auth_params.get("password")
            if not (username and password):
                logging.warning(
                    "Missing required parameters [username, password] for auth_type [%s] for keychain entry [%s]" %
                    (auth_type, uri))
                continue

            session.headers.update(auth_params.get("additional_request_headers", {}))

            auth_method = auth_params.get("auth_method", "post")
            if auth_type == 'http-basic':
                session.auth = (username, password)
                if auth_method:
                    auth_method = auth_method.lower()
                if auth_method == 'post':
                    response = session.post(auth_uri, auth=session.auth)
                elif auth_method == 'get':
                    response = session.get(auth_uri, auth=session.auth)
                else:
                    logging.warning("Unsupported auth_method [%s] for auth_type [%s] for keychain entry [%s]" %
                                    (auth_method, auth_type, uri))
            elif auth_type == 'http-form':
                username_field = auth_params.get("username_field", "username")
                password_field = auth_params.get("password_field", "password")
                response = session.post(auth_uri, {username_field: username, password_field: password})
            if response.status_code > 203:
                logger.warning(
                    'Authentication failed with Status Code: %s %s\n' % (response.status_code, response.text))
            else:
                logger.info("Session established: %s", uri)
                SESSIONS[uri] = session
                break

        except Exception as e:
            logger.warning("Unhandled exception during HTTP(S) authentication: %s" % get_typed_exception(e))

    if not session:
        url_parts = urlsplit(url)
        base_url = str("%s://%s" % (url_parts.scheme, url_parts.netloc))
        session = SESSIONS.get(base_url, None)
        if not session:
            session = init_new_session(config["session_config"])
            SESSIONS[base_url] = session

    return session


def init_new_session(session_config):
    session = requests.session()
    retries = Retry(connect=session_config['retry_connect'],
                    read=session_config['retry_read'],
                    backoff_factor=session_config['retry_backoff_factor'],
                    status_forcelist=session_config['retry_status_forcelist'])
    session.mount('http://', HTTPAdapter(max_retries=retries))
    session.mount('https://', HTTPAdapter(max_retries=retries))

    return session


def get_file(url, output_path, auth_config, **kwargs):

    try:
        headers = kwargs.get("headers", HEADERS)
        bdbag_config = kwargs.get("config", DEFAULT_CONFIG)
        fetch_config = bdbag_config.get(FETCH_CONFIG_TAG, DEFAULT_FETCH_CONFIG)
        config = fetch_config.get("http", DEFAULT_FETCH_CONFIG["http"])
        redirect_status_codes = config.get(
            FETCH_HTTP_REDIRECT_STATUS_CODES_TAG, DEFAULT_FETCH_HTTP_REDIRECT_STATUS_CODES)

        session = get_session(url, auth_config, config)
        output_path = ensure_valid_output_path(url, output_path)

        allow_redirects = config.get("allow_redirects", False)
        allow_redirects_with_token = False
        auth = get_auth(url, auth_config) or {}
        auth_type = auth.get("auth_type")
        auth_params = auth.get("auth_params")
        if auth_type == 'bearer-token':
            allow_redirects = False
            # Force setting the "X-Requested-With": "XMLHttpRequest" header is a workaround for some OIDC servers that
            # on an unauthenticated request redirect to a login flow instead of responding with a 401 Unauthorized.
            headers.update({"X-Requested-With": "XMLHttpRequest"})
            if auth_params:
                allow_redirects_with_token = stob(auth_params.get("allow_redirects_with_token", False))

        while True:
            logger.info("Attempting GET from URL: %s" % url)
            r = session.get(url,
                            stream=True,
                            headers=headers,
                            allow_redirects=allow_redirects,
                            verify=certifi.where(),
                            cookies=kwargs.get("cookies"))
            if r.status_code in redirect_status_codes:
                url = r.headers['Location']
                logger.info("Server responded with redirect to: %s" % url)
                if auth_type == 'bearer-token':
                    if allow_redirects_with_token:
                        authorization = session.headers.get("Authorization")
                        if authorization:
                            headers.update({"Authorization": authorization})
                        else:
                            logger.warning(
                                "Unable to locate Authorization header in requests session headers after redirect")
                    else:
                        logger.warning("Authorization bearer token propagation on redirect is disabled for security "
                                       "purposes. Enable token propagation for this URL in keychain.json")
                        if session.headers.get("Authorization"):
                            del session.headers["Authorization"]
                continue
            else:
                break

        if r.status_code != 200:
            logger.error('HTTP GET Failed for URL: %s' % url)
            logger.error("Host %s responded:\n\n%s" % (urlsplit(url).netloc,  r.text))
            logger.warning('File transfer failed: [%s]' % output_path)
        else:
            total = 0
            start = datetime.datetime.now()
            logger.debug("Transferring file %s to %s" % (url, output_path))
            with open(output_path, 'wb') as data_file:
                for chunk in r.iter_content(chunk_size=CHUNK_SIZE):
                    data_file.write(chunk)
                    total += len(chunk)
            elapsed_time = datetime.datetime.now() - start
            summary = get_transfer_summary(total, elapsed_time)
            logger.info('File [%s] transfer successful. %s' % (output_path, summary))
            return output_path

    except requests.exceptions.RequestException as e:
        logger.error('HTTP Request Exception: %s' % (get_typed_exception(e)))

    return None


def cleanup():
    for session in SESSIONS.values():
        session.close()
    SESSIONS.clear()
