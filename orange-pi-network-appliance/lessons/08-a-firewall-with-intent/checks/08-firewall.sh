#!/usr/bin/env bash
# firewall-policy: input and forward are default-drop, with established/related accepted.
. "$(dirname "$0")/_lib.sh"
rs="$(bssh 'sudo nft list ruleset 2>/dev/null' || true)"
[ -n "$rs" ] || fail "the nftables ruleset is empty"
grep -Eq 'hook input .*policy drop'   <<<"$rs" || fail "the input chain is not default-drop"
grep -Eq 'hook forward .*policy drop' <<<"$rs" || fail "the forward chain is not default-drop"
grep -q  'ct state established'        <<<"$rs" || fail "established/related is not accepted — existing connections will break"
pass "firewall has default-drop input and forward, with established/related accepted"
echo "Confirm by hand: predict each verdict (client->internet, client->admin, admin->box) before testing it."
