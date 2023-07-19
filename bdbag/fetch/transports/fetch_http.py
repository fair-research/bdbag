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
from requests.utils import default_user_agent
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry
from bdbag import urlsplit, stob, get_typed_exception, VERSION
from bdbag.bdbag_config import DEFAULT_CONFIG, DEFAULT_FETCH_CONFIG, FETCH_CONFIG_TAG, \
    FETCH_HTTP_REDIRECT_STATUS_CODES_TAG, DEFAULT_FETCH_HTTP_SESSION_CONFIG, DEFAULT_FETCH_HTTP_REDIRECT_STATUS_CODES
from bdbag.fetch import *
from bdbag.fetch.transports.base_transport import BaseFetchTransport
from bdbag.fetch.auth.cookies import get_request_cookies
import bdbag.fetch.auth.keychain as kc

logger = logging.getLogger(__name__)

CHUNK_SIZE = 10 * Megabyte
HEADERS = {"User-Agent": "bdbag/%s (%s)" % (VERSION, default_user_agent())}


class HTTPFetchTransport(BaseFetchTransport):

    def __init__(self, config, keychain, **kwargs):
        super(HTTPFetchTransport, self).__init__(config, keychain, **kwargs)
        self.config = config or DEFAULT_FETCH_CONFIG[SCHEME_HTTP]
        self.cookies = get_request_cookies(self.config) if kwargs.get("cookie_scan", True) else None
        self.sessions = dict()

    @staticmethod
    def validate_auth_config(auth):
        if not kc.has_auth_attr(auth, "auth_type"):
            return False
        if not kc.has_auth_attr(auth, "auth_params"):
            return False

        return True

    def get_auth(self, url):
        for auth in kc.get_auth_entries(url, self.keychain):
            if self.validate_auth_config(auth):
                return auth
        return None

    def bypass_cert_verify(self, url):
        bypass = self.config.get("bypass_ssl_cert_verification", False)
        if isinstance(bypass, bool) and bypass:
            logger.warning("Bypassing SSL certificate verification due to global configuration setting. "
                           "Disabling all SSL certificate verification in this way is NOT recommended.")
            return True
        elif isinstance(bypass, list):
            for uri in bypass:
                if uri in url:
                    logger.warning(
                        "Bypassing SSL certificate validation for URL %s due to matching whitelist entry: [%s]" %
                        (url, uri))
                    return True
        return False

    @staticmethod
    def init_new_session(session_config):
        session = requests.session()
        retries = Retry(connect=session_config["retry_connect"],
                        read=session_config["retry_read"],
                        backoff_factor=session_config["retry_backoff_factor"],
                        status_forcelist=session_config["retry_status_forcelist"])
        session.mount("http://", HTTPAdapter(max_retries=retries))
        session.mount("https://", HTTPAdapter(max_retries=retries))

        return session

    def get_session(self, url):
        session = None
        response = None

        for auth in kc.get_auth_entries(url, self.keychain):
            try:
                if not self.validate_auth_config(auth):
                    continue

                uri = auth.get("uri")
                if uri in self.sessions:
                    session = self.sessions[uri]
                    break
                else:
                    session = self.init_new_session(
                        self.config.get("session_config", DEFAULT_FETCH_HTTP_SESSION_CONFIG))

                auth_type = auth.get("auth_type")
                auth_params = auth.get("auth_params", {})

                if auth_type == "cookie":
                    if auth_params:
                        cookies = auth_params.get("cookies", [])
                        if cookies:
                            for cookie in cookies:
                                name, value = cookie.split("=", 1)
                                session.cookies.set(name, value, domain=urlsplit(uri).hostname, path="/")
                        session.headers.update(auth_params.get("additional_request_headers", {}))
                        self.sessions[uri] = session
                        break

                if auth_type == "bearer-token":
                    token = auth_params.get("token")
                    if token:
                        session.headers.update({"Authorization": "Bearer " + token})
                        session.headers.update(auth_params.get("additional_request_headers", {}))
                        self.sessions[uri] = session
                        break
                    else:
                        logger.warning("Missing required parameters [token] for auth_type [%s] for keychain entry [%s]"
                                       % (auth_type, uri))

                # if we get here the assumption is that the auth_type is either http-basic or http-form and that an
                # actual session "login" request is necessary
                auth_uri = auth.get("auth_uri", uri)
                username = auth_params.get("username")
                password = auth_params.get("password")
                if not (username and password):
                    logger.warning(
                        "Missing required parameters [username, password] for auth_type [%s] for keychain entry [%s]" %
                        (auth_type, uri))
                    continue

                session.headers.update(auth_params.get("additional_request_headers", {}))

                auth_method = auth_params.get("auth_method", "post")
                if auth_type == "http-basic":
                    session.auth = (username, password)
                    if auth_method:
                        auth_method = auth_method.lower()
                    if auth_method == "post":
                        response = session.post(auth_uri, auth=session.auth)
                    elif auth_method == "get":
                        response = session.get(auth_uri, auth=session.auth)
                    else:
                        logger.warning("Unsupported auth_method [%s] for auth_type [%s] for keychain entry [%s]" %
                                       (auth_method, auth_type, uri))
                elif auth_type == "http-form":
                    username_field = auth_params.get("username_field", "username")
                    password_field = auth_params.get("password_field", "password")
                    response = session.post(auth_uri, {username_field: username, password_field: password})
                if response.status_code > 203:
                    logger.warning(
                        "Authentication failed with Status Code: %s %s\n" % (response.status_code, response.text))
                else:
                    logger.info("Session established: %s", uri)
                    self.sessions[uri] = session
                    break

            except Exception as e:  # pragma: no cover
                logger.warning("Unhandled exception during HTTP(S) authentication: %s" % get_typed_exception(e))

        if not session:
            url_parts = urlsplit(url)
            base_url = str("%s://%s" % (url_parts.scheme, url_parts.netloc))
            session = self.sessions.get(base_url, None)
            if not session:
                session = self.init_new_session(self.config.get("session_config", DEFAULT_FETCH_HTTP_SESSION_CONFIG))
                self.sessions[base_url] = session

        return session

    def fetch(self, url, output_path, **kwargs):
        try:
            headers = kwargs.get("headers", {"Connection": "keep-alive"})
            headers.update(HEADERS)
            redirect_status_codes = self.config.get(
                FETCH_HTTP_REDIRECT_STATUS_CODES_TAG, DEFAULT_FETCH_HTTP_REDIRECT_STATUS_CODES)

            session = self.get_session(url)
            output_path = ensure_valid_output_path(url, output_path)
            allow_redirects = stob(self.config.get("allow_redirects", True))
            allow_redirects_with_token = False
            authorization = None
            auth = self.get_auth(url) or {}
            auth_type = auth.get("auth_type")
            auth_params = auth.get("auth_params")
            if auth_type == "bearer-token":
                allow_redirects = False
                # Force setting the "X-Requested-With": "XMLHttpRequest" header is a workaround for some OIDC servers
                # which on an unauthenticated request redirect to a login flow instead of responding with a 401.
                headers.update({"X-Requested-With": "XMLHttpRequest"})
                if auth_params:
                    allow_redirects_with_token = stob(auth_params.get("allow_redirects_with_token", False))

            while True:
                logger.info("Attempting GET from URL: %s" % url)
                r = session.get(url,
                                stream=True,
                                headers=headers,
                                allow_redirects=allow_redirects,
                                verify=False if self.bypass_cert_verify(url) else certifi.where(),
                                cookies=self.cookies)
                if r.status_code in redirect_status_codes:
                    url = r.headers["Location"]
                    logger.info("Server responded with redirect to: %s" % url)
                    if auth_type == "bearer-token":
                        if allow_redirects_with_token:
                            authorization = session.headers.get("Authorization")
                            if authorization:
                                headers.update({"Authorization": authorization})
                            else:
                                logger.warning(
                                    "Unable to locate Authorization header in requests session headers after redirect")
                        else:
                            logger.warning("Authorization bearer token propagation on redirect is disabled for "
                                           "security reasons. If necessary, you can enable token propagation for this "
                                           "URL in keychain.json.")
                            if session.headers.get("Authorization"):
                                del session.headers["Authorization"]
                    elif not allow_redirects:
                        logger.warning("Redirects for this scheme have been disabled via the configuration file.")
                        break
                else:
                    break

            # restore the bearer-token auth header back to the session if it exists got stripped due to redirect
            if auth_type == "bearer-token" and authorization is not None and not session.headers.get("Authorization"):
                session.headers.update({"Authorization": authorization})

            if r.status_code != 200:
                logger.error("HTTP GET Failed for URL: %s" % url)
                logger.error("Host %s responded:\n\n%s" % (urlsplit(url).netloc,  r.text))
                logger.warning("File transfer failed: [%s]" % output_path)
            else:
                total = 0
                start = datetime.datetime.now()
                logger.debug("Transferring file %s to %s" % (url, output_path))
                with open(output_path, "wb") as data_file:
                    for chunk in r.iter_content(chunk_size=CHUNK_SIZE):
                        data_file.write(chunk)
                        total += len(chunk)
                elapsed_time = datetime.datetime.now() - start
                check_transfer_size_mismatch(output_path, kwargs.get("size"), total)
                logger.info("File [%s] transfer complete. %s" %
                            (output_path, get_transfer_summary(total, elapsed_time)))
                return output_path

        except requests.exceptions.RequestException as e:
            logger.error("HTTP Request Exception: %s" % (get_typed_exception(e)))

        return None

    def cleanup(self):
        for session in self.sessions.values():
            session.close()
        self.sessions.clear()
