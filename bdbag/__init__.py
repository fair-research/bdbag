import os
import re
import sys
import mimetypes
from pkg_resources import get_distribution, DistributionNotFound

if not mimetypes.inited:
    mimetypes.init()

try:
    VERSION = get_distribution("bdbag").version
except DistributionNotFound:
    VERSION = '0.0.dev0'
PROJECT_URL = 'https://github.com/fair-research/bdbag'

try:
    BAGIT_VERSION = get_distribution("bagit").version
except DistributionNotFound:
    BAGIT_VERSION = '0.0.dev0'

BAG_PROFILE_TAG = 'BagIt-Profile-Identifier'
BDBAG_PROFILE_ID = 'https://raw.githubusercontent.com/fair-research/bdbag/master/profiles/bdbag-profile.json'
BDBAG_RO_PROFILE_ID = 'https://raw.githubusercontent.com/fair-research/bdbag/master/profiles/bdbag-ro-profile.json'

ID_RESOLVER_TAG = 'identifier_resolvers'
DEFAULT_ID_RESOLVERS = ['n2t.net', 'identifiers.org']

DEFAULT_CONFIG_PATH = os.path.join(os.path.expanduser('~'), '.bdbag')
DEFAULT_CONFIG_FILE = os.path.join(DEFAULT_CONFIG_PATH, 'bdbag.json')
DEFAULT_CONFIG = {
    'bag_config':
    {
        'bag_algorithms': ['md5', 'sha256'],
        'bag_processes': 1,
        'bag_metadata':
        {
            BAG_PROFILE_TAG: BDBAG_PROFILE_ID
        }
    },
    ID_RESOLVER_TAG: DEFAULT_ID_RESOLVERS
}

if sys.version_info > (3,):
    from urllib.parse import quote as urlquote, unquote as urlunquote, urlsplit, urlunsplit
    from urllib.request import urlretrieve, urlopen
else:
    from urllib import quote as urlquote, unquote as urlunquote, urlretrieve, urlopen
    from urlparse import urlsplit, urlunsplit


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


def parse_content_disposition(value):
    m = re.match("^filename[*]=UTF-8''(?P<name>[-_.~A-Za-z0-9%]+)$", value)
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


def escape_url_path(url, safe='/'):
    urlparts = urlsplit(url)
    path = urlquote(urlunquote(urlparts.path), safe=safe)
    query = urlquote(urlunquote(urlparts.query))
    fragment = urlquote(urlunquote(urlparts.fragment))
    return urlunsplit((urlparts.scheme, urlparts.netloc, path, query, fragment))
