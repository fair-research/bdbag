import sys
import bdbag.fetch.transports.fetch_http
import bdbag.fetch.transports.fetch_ark

if sys.version_info < (3,):
    import bdbag.fetch.transports.fetch_globus