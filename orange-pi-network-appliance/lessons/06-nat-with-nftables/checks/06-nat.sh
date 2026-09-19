#!/usr/bin/env bash
# nat-live: a masquerade rule is loaded, and (if a client is configured) a client reaches the internet.
. "$(dirname "$0")/_lib.sh"
require_board
bssh 'sudo nft list ruleset 2>/dev/null | grep -q masquerade' || fail "no masquerade rule in the nftables ruleset"
if [ -n "${CLIENT_HOST:-}" ]; then
  cssh 'ping -c1 -W3 1.1.1.1 >/dev/null 2>&1' || fail "client ${CLIENT_HOST} cannot reach 1.1.1.1 through the box"
  pass "masquerade is loaded and client ${CLIENT_HOST} reached 1.1.1.1 through the appliance"
else
  pass "masquerade is loaded (set CLIENT_HOST in board.env to also prove a client reaches the internet)"
fi
