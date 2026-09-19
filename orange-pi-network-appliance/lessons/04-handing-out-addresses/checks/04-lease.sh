#!/usr/bin/env bash
# lease-issued: dnsmasq is running and has handed out a lease on the AP subnet.
. "$(dirname "$0")/_lib.sh"
bssh 'systemctl is-active --quiet dnsmasq || pgrep -x dnsmasq >/dev/null' || fail "dnsmasq is not running"
leases="$(bssh 'grep -c "192\.168\.4\." /var/lib/misc/dnsmasq.leases 2>/dev/null' || echo 0)"
[ "${leases:-0}" -ge 1 ] || fail "no DHCP lease on 192.168.4.0/24 yet — associate a client, then re-run"
pass "dnsmasq has issued ${leases} lease(s) on the AP subnet"
