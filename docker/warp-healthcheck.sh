#!/bin/bash
# Health check for Cloudflare WARP running in proxy mode.
#
# The image's built-in check only verifies that the WARP daemon started, which
# is not enough to catch a dead tunnel. This one makes a real request through
# the SOCKS5 listener and requires Cloudflare to report the tunnel as active.
#
# Mounted at /healthcheck/connected-to-warp.sh; the container restarts itself
# after three consecutive failures.
curl -fsS --socks5-hostname 127.0.0.1:1080 "https://cloudflare.com/cdn-cgi/trace" \
  | grep -qE "warp=(plus|on)" || exit 1
exit 0
