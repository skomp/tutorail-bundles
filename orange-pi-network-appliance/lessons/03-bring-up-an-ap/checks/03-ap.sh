#!/usr/bin/env bash
# ap-beaconing: hostapd is running and wlan0 is in AP mode.
. "$(dirname "$0")/_lib.sh"
bssh 'systemctl is-active --quiet hostapd || pgrep -x hostapd >/dev/null' || fail "hostapd is not running"
mode="$(bssh 'iw dev wlan0 info 2>/dev/null | awk "/type/{print \$2}"' || true)"
[ "$mode" = "AP" ] || fail "wlan0 is not in AP mode (iw reports type=${mode:-none})"
pass "hostapd is running and wlan0 is in AP mode"
echo "Confirm by hand: your phone sees the SSID and can associate (no internet yet)."
