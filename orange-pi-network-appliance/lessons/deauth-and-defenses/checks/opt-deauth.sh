#!/usr/bin/env bash
# deauth-observed: hostapd has protected management frames enabled (the deauth defence).
. "$(dirname "$0")/_lib.sh"
require_board
cfg="$(bssh 'cat /etc/hostapd/hostapd.conf 2>/dev/null' || true)"
grep -Eq '^[[:space:]]*ieee80211w=(1|2)' <<<"$cfg" || fail "hostapd has no ieee80211w — protected management frames are not enabled"
pass "hostapd has protected management frames enabled (ieee80211w)"
echo "The attack itself is observed by hand with a second radio; this check confirms the defence is in place."
