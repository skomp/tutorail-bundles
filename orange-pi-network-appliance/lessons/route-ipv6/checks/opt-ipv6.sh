#!/usr/bin/env bash
# v6-routes: IPv6 is forwarded (not masqueraded) and router advertisements are configured.
. "$(dirname "$0")/_lib.sh"
v="$(bssh 'cat /proc/sys/net/ipv6/conf/all/forwarding' 2>/dev/null || echo 0)"
[ "$v" = "1" ] || fail "IPv6 forwarding is off"
if bssh 'sudo nft list ruleset 2>/dev/null | grep -A3 ip6 | grep -q masquerade'; then
  fail "IPv6 is being masqueraded — route the delegated prefix instead of NATing it"
fi
bssh 'systemctl is-active --quiet radvd || (pgrep -x dnsmasq >/dev/null && grep -qs enable-ra /etc/dnsmasq.conf /etc/dnsmasq.d/* 2>/dev/null)' || fail "no router advertisements (radvd or dnsmasq enable-ra)"
pass "IPv6 is forwarded, not masqueraded, and router advertisements are configured"
if [ -n "${CLIENT_HOST:-}" ]; then
  cssh 'ip -6 addr show scope global 2>/dev/null | grep -q inet6' && echo "Client ${CLIENT_HOST} has a global IPv6 address." || echo "Note: client ${CLIENT_HOST} has no global IPv6 address yet."
fi
