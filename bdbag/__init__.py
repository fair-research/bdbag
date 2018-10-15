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
import re
import sys
import json
import logging
import mimetypes
from requests.utils import requote_uri
from distutils.util import strtobool
from pkg_resources import get_distribution, DistributionNotFound

__version__ = "1.5.0"

if sys.version_info > (3,):  # pragma: no cover
    from urllib.parse import quote as urlquote, unquote as urlunquote, urlsplit, urlunsplit
    from urllib.request import urlretrieve, urlopen, urlcleanup
else:  # pragma: no cover
    from urllib import quote as urlquote, unquote as urlunquote, urlretrieve, urlopen, urlcleanup
    from urlparse import urlsplit, urlunsplit

try:
    VERSION = get_distribution("bdbag").version
except DistributionNotFound:  # pragma: no cover
    VERSION = __version__ + '-dev'
PROJECT_URL = 'https://github.com/fair-research/bdbag'

try:
    BAGIT_VERSION = get_distribution("bagit").version
except DistributionNotFound:  # pragma: no cover
    BAGIT_VERSION = 'unknown'

BAG_PROFILE_TAG = 'BagIt-Profile-Identifier'
BDBAG_PROFILE_ID = 'https://raw.githubusercontent.com/fair-research/bdbag/master/profiles/bdbag-profile.json'
BDBAG_RO_PROFILE_ID = 'https://raw.githubusercontent.com/fair-research/bdbag/master/profiles/bdbag-ro-profile.json'

CONTENT_DISP_REGEX = re.compile(r"^filename[*]=UTF-8''(?P<name>[-_.~A-Za-z0-9%]+)$")
FILTER_REGEX = re.compile(r"(?P<column>^.*)(?P<operator>==|!=|=\*|!\*|\^\*|\$\*|>=|>|<=|<)(?P<value>.*$)")
FILTER_DOCSTRING = "\"==\" (equal), " \
                   "\"!=\" (not equal), " \
                   "\"=*\" (wildcard substring equal), " \
                   "\"!*\" (wildcard substring not equal), " \
                   "\"^*\" (wildcard starts with), " \
                   "\"$*\" (wildcard ends with), " \
                   "or \">\", \">=\", \"<\", \"<=\""

DEFAULT_LOG_FORMAT = "%(asctime)s - %(levelname)s - %(message)s"
DEFAULT_CONFIG_PATH = os.path.join(os.path.expanduser('~'), '.bdbag')

if not mimetypes.inited:
    mimetypes.init()


def stob(string):
    return bool(strtobool(str(string)))


def get_typed_exception(e):
    exc = "".join(("[", type(e).__name__, "] "))
    return "".join((exc, str(e)))


def add_mime_types(types):
    if not types:
        return
    for t in types.keys():
        for e in types[t]:
            mimetypes.add_type(type=t, ext=e if e.startswith(".") else "".join([".", e]))


def guess_mime_type(file_path):
    mtype = mimetypes.guess_type(file_path)
    content_type = 'application/octet-stream'
    if mtype[0] is not None and mtype[1] is not None:
        content_type = "+".join([mtype[0], mtype[1]])
    elif mtype[0] is not None:
        content_type = mtype[0]
    elif mtype[1] is not None:
        content_type = mtype[1]

    return content_type


def parse_content_disposition(value):  # pragma: no cover
    m = CONTENT_DISP_REGEX.match(value)
    if not m:
        raise ValueError('Cannot parse content-disposition "%s".' % value)

    n = m.groupdict()['name']

    try:
        n = urlunquote(str(n))
    except Exception as e:
        raise ValueError('Invalid URL encoding of content-disposition filename component. %s.' % e)

    try:
        if sys.version_info < (3,):
            n = n.decode('utf8')
    except Exception as e:
        raise ValueError('Invalid UTF-8 encoding of content-disposition filename component. %s.' % e)

    return n


def escape_uri(uri, illegal_only=True, safe="/"):  # pragma: no cover
    if not uri:
        return uri

    if illegal_only:
        return requote_uri(uri)
    else:
        urlparts = urlsplit(uri)
        path = urlquote(urlunquote(urlparts.path), safe=safe)
        query = urlquote(urlunquote(urlparts.query), safe=safe)
        fragment = urlquote(urlunquote(urlparts.fragment), safe=safe)
        return urlunsplit((urlparts.scheme, urlparts.netloc, path, query, fragment))


def filter_dict(expr, entry):
    if not expr:
        return True
    match = FILTER_REGEX.search(expr)
    if not match:
        raise ValueError("Unable to parse expression: %s" % expr)

    expr_dict = match.groupdict()
    filter_col = expr_dict["column"]
    filter_val = expr_dict["value"]
    operator = expr_dict["operator"]

    filter_neg = filter_substring = filter_relation = filter_startswith = filter_endswith = False
    if "==" == operator:
        pass
    elif "!=" == operator:
        filter_neg = True
    elif "=*" == operator:
        filter_substring = True
    elif "^*" == operator:
        filter_startswith = True
    elif "$*" == operator:
        filter_endswith = True
    elif "!*" == operator:
        filter_substring = True
        filter_neg = True
    elif (">" == operator) or (">=" == operator) or ("<" == operator) or ("<=" == operator):
        filter_relation = True
    else:
        raise ValueError("Unsupported operator type in filter expression: %s" % expr)

    result = False
    filter_val = filter_val.strip()
    filter_col = filter_col.strip()
    if filter_col in set(entry.keys()):
        value = entry[filter_col]
        if filter_neg:
            if filter_substring:
                result = filter_val not in str(value)
            else:
                result = filter_val != value
        else:
            if filter_substring:
                result = filter_val in str(value)
            elif filter_startswith:
                result = str(value).startswith(filter_val)
            elif filter_endswith:
                result = str(value).endswith(filter_val)
            elif filter_relation:
                try:
                    statement = "%d%s%d" % (int(value), operator, int(filter_val))
                    result = eval(statement)
                except Exception as e:
                    logging.warning("Unable to evaluate filter expression [%s]: %s" %
                                    (expr, get_typed_exception(e)))
            else:
                result = filter_val == value
    if not result:
        logging.debug(
            "Excluding %s because it does not match the filter expression: [%s]." %
            (json.dumps(entry), expr))

    return result


def inspect_path(path):
    abs_path = os.path.abspath(path)
    exists = os.path.exists(abs_path)
    is_uri = is_file = is_dir = False
    if not exists:
        upr = urlsplit(path)
        drive, tail = os.path.splitdrive(path)
        if upr.scheme and upr.scheme.lower() != drive.rstrip(":").lower():
            is_uri = True
    if not is_uri:
        is_file = os.path.isfile(abs_path)
        is_dir = os.path.isdir(abs_path)

    return is_file, is_dir, is_uri
