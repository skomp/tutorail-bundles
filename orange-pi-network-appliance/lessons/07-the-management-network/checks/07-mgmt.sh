#!/usr/bin/env bash
# mgmt-reachable: bnep0 is up on the management subnet, and that subnet is not NATed.
. "$(dirname "$0")/_lib.sh"
require_board
bssh 'ip -4 addr show bnep0 2>/dev/null | grep -q "192\.168\.44\.1"' || fail "bnep0 has no 192.168.44.1 — the management network is not up"
if bssh 'sudo nft list ruleset 2>/dev/null | grep masquerade | grep -q "192\.168\.44"'; then
  fail "the management subnet appears in a masquerade rule — it must not be NATed"
fi
pass "bnep0 is up on 192.168.44.1 and the management subnet is not NATed"
echo "Confirm by hand: you can reach admin over Bluetooth PAN, and a Wi-Fi client cannot."
