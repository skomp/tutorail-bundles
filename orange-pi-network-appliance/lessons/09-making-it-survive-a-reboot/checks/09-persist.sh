#!/usr/bin/env bash
# reboot-survives: the appliance units are enabled and networkd config is in place.
. "$(dirname "$0")/_lib.sh"
for u in systemd-networkd hostapd dnsmasq nftables; do
  bssh "systemctl is-enabled --quiet $u" || fail "$u is not enabled — it will not come back after a reboot"
done
bssh 'ls /etc/systemd/network/*.network >/dev/null 2>&1' || fail "no systemd-networkd .network files under /etc/systemd/network"
pass "networkd, hostapd, dnsmasq and nftables are enabled and networkd config is present"
echo "Then prove it for real: reboot the board and re-run checks 03, 04 and 06."
