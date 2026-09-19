#!/usr/bin/env bash
# scan-runs: nmap or arp-scan is present and finds at least one host on the AP subnet.
. "$(dirname "$0")/_lib.sh"
require_board
bssh 'command -v nmap >/dev/null || command -v arp-scan >/dev/null' || fail "neither nmap nor arp-scan is installed on the board"
scan_cmd='if command -v arp-scan >/dev/null; then sudo arp-scan --interface='"$AP_IF"' 192.168.4.0/24 2>/dev/null | grep -c "192\.168\.4\."; else sudo nmap -sn 192.168.4.0/24 2>/dev/null | grep -c "Nmap scan report"; fi'
found="$(bssh "$scan_cmd" || echo 0)"
[ "${found:-0}" -ge 1 ] || fail "the scan found no hosts on the AP subnet — associate a client first"
pass "the scan of the served network found ${found} host(s)"
