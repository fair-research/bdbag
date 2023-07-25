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
import shutil
from datetime import datetime
from distutils.util import strtobool
from importlib_metadata import distribution, PackageNotFoundError

logger = logging.getLogger(__name__)

__version__ = "1.7.0"
__bagit_version__ = "1.8.1"
__bagit_profile_version__ = "1.3.1"

if sys.version_info > (3,):  # pragma: no cover
    from urllib.parse import quote as urlquote, unquote as urlunquote, urlsplit, urlunsplit, urlparse
    from urllib.request import urlretrieve, urlopen, urlcleanup
else:  # pragma: no cover
    from urllib import quote as urlquote, unquote as urlunquote, urlretrieve, urlopen, urlcleanup
    from urlparse import urlsplit, urlunsplit, urlparse

try:
    version = distribution("bdbag").version
    VERSION = version + '' if not getattr(sys, 'frozen', False) else version + '-frozen'
except PackageNotFoundError:  # pragma: no cover
    VERSION = __version__ + '-dev' if not getattr(sys, 'frozen', False) else __version__ + '-frozen'
PROJECT_URL = 'https://github.com/fair-research/bdbag'

try:
    version = distribution("bagit").version
    BAGIT_VERSION = version + '' if not getattr(sys, 'frozen', False) else version + '-frozen'
except PackageNotFoundError:  # pragma: no cover
    BAGIT_VERSION = 'unknown' if not getattr(sys, 'frozen', False) else __bagit_version__ + '-frozen'

try:
    version = distribution("bagit_profile").version
    BAGIT_PROFILE_VERSION = version + '' if not getattr(sys, 'frozen', False) else version + '-frozen'
except PackageNotFoundError:  # pragma: no cover
    BAGIT_PROFILE_VERSION = 'unknown' if not getattr(sys, 'frozen', False) else __bagit_profile_version__ + '-frozen'

BAG_PROFILE_TAG = 'BagIt-Profile-Identifier'
BDBAG_PROFILE_ID = 'https://raw.githubusercontent.com/fair-research/bdbag/master/profiles/bdbag-profile.json'
BDBAG_RO_PROFILE_ID = 'https://raw.githubusercontent.com/fair-research/bdbag/master/profiles/bdbag-ro-profile.json'

CONTENT_DISP_REGEX = re.compile(r"^filename[*]=UTF-8''(?P<name>[-_.~A-Za-z0-9%]+)$")
FILTER_REGEX = re.compile(r"(?P<column>^.*)(?P<operator>==|!=|=\*|!\*|=~|\^\*|\$\*|>=|>|<=|<)(?P<value>.*$)")
FILTER_DOCSTRING = "\"==\" (equal), " \
                   "\"!=\" (not equal), " \
                   "\"=*\" (wildcard substring equal), " \
                   "\"!*\" (wildcard substring not equal), " \
                   "\"=~\" (matches regular expression), " \
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
    mtype = mimetypes.guess_type(file_path, strict=False)
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


# Per the bagit spec, we just want to replace (%,\r,\n,\t, ) for storage in fetch.txt, but this is also applicable
# to URI/IRI storage in ro-metadata as well
def escape_uri(uri, encode_whitespace=True):
    if not uri:
        return uri

    uri = uri.replace("%", "%25").replace("\n", "%0A").replace("\r", "%0D")
    if encode_whitespace:
        uri = uri.replace(" ", "%20").replace("\t", "%09")

    return uri


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

    filter_neg = filter_substring = filter_re = filter_relation = filter_startswith = filter_endswith = False
    if "==" == operator:
        pass
    elif "!=" == operator:
        filter_neg = True
    elif "=*" == operator:
        filter_substring = True
    elif "=~" == operator:
        filter_re = True
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
            elif filter_re:
                result = re.search(filter_val, str(value)) is not None
            elif filter_startswith:
                result = str(value).startswith(filter_val)
            elif filter_endswith:
                result = str(value).endswith(filter_val)
            elif filter_relation:
                try:
                    statement = "%d%s%d" % (int(value), operator, int(filter_val))
                    result = eval(statement)
                except Exception as e:
                    logger.warning("Unable to evaluate filter expression [%s]: %s" %
                                   (expr, get_typed_exception(e)))
            else:
                result = filter_val == value
    if not result:
        logger.debug(
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


def safe_move(old_path, new_path=None):
    old_path = os.path.realpath(old_path)
    if new_path:
        new_path = os.path.realpath(new_path)
    if os.path.dirname(old_path) == old_path:
        logger.debug("Ignore move of root filesystem path: %s" % old_path)
        return old_path

    path_qualifier = '-' + datetime.strftime(datetime.now(), "%Y-%m-%d_%H.%M.%S")
    if os.path.exists(old_path):
        if not new_path:
            new_path = ''.join([old_path, path_qualifier])
            logger.info("Target path %s already exists, moving it to %s" %
                        (old_path, new_path))
        elif new_path and os.path.exists(new_path):
            override_path = ''.join([new_path, path_qualifier])
            logger.info("Requested target path %s already exists, moving it to %s" % (new_path, override_path))
            new_path = override_path
        shutil.move(old_path, new_path)
        return new_path
    return old_path


def bag_parent_dir_from_archive(file_list):
    root_paths = set()
    parent_paths = set()
    child_paths = set()
    if not isinstance(file_list, list):
        return None
    for path in file_list:
        root = path.partition("/")
        root_paths.add(root[0])
        if root[1]:
            parent_paths.add(root[0])
        if "/" in root[2]:
            child_paths.add(root[2].partition("/")[0])

    if len(parent_paths - child_paths) > 1:
        logger.warning("Unable to determine bag parent directory from archive file list. "
                       "Expecting single bag parent dir but got: %s" % parent_paths)
        return None
    if len(root_paths - parent_paths) > 0:
        logger.warning("Unable to determine bag parent directory from archive file list. "
                       "Expecting single bag parent dir in archive but found files in the archive root")
        return None
    return parent_paths.pop()
