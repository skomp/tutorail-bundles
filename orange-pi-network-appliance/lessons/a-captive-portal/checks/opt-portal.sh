#!/usr/bin/env bash
# portal-redirects: client port 80 is redirected and a splash responder is listening.
. "$(dirname "$0")/_lib.sh"
rs="$(bssh 'sudo nft list ruleset 2>/dev/null' || true)"
grep -Eiq 'redirect|dnat' <<<"$rs" || fail "no redirect/dnat rule for the captive portal"
grep -q  'tcp dport 80'   <<<"$rs" || fail "nothing redirects client port 80"
bssh 'sudo ss -ltn 2>/dev/null | grep -Eq ":(80|8080)\b"' || fail "no splash responder listening on port 80 or 8080"
pass "client port 80 is redirected and a splash responder is listening"
echo "Confirm by hand: an HTTP request from a client lands on the splash page, and an HTTPS one does not."
