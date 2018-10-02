import os
from bdbag import urlsplit

Kilobyte = 1024
Megabyte = Kilobyte ** 2


def get_transfer_summary(total_bytes, elapsed_time):
    total_secs = elapsed_time.total_seconds()
    transferred = \
        float(total_bytes) / float(Kilobyte) if total_bytes < Megabyte else float(total_bytes) / float(Megabyte)
    throughput = str(" at %.2f MB/second" % (transferred / total_secs)) if (total_secs >= 1) else ""
    elapsed = str("Elapsed time: %s." % elapsed_time) if (total_secs > 0) else ""
    summary = "%.3f %s transferred%s. %s" % \
              (transferred, "KB" if total_bytes < Megabyte else "MB", throughput, elapsed)
    return summary


def ensure_valid_output_path(url, output_path=None):
    if not output_path:
        upr = urlsplit(url, allow_fragments=False)
        output_path = os.path.join(os.curdir, os.path.basename(upr.path))
    output_path = os.path.abspath(output_path)
    output_dir = os.path.dirname(output_path)
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    return output_path
