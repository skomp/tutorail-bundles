# Build a Linux Network Appliance on the Orange Pi Zero 3

**Bundle id:** `orange-pi-network-appliance`
**Scale:** long
**Status:** approved
**Date:** 2026-09-19

## The learner

For someone who is comfortable in Linux — a shell, editing files, reading `journalctl` and
a systemd unit — but has never configured a network by hand and does not yet know what a
routing table, a NAT translation or a DHCP lease really *is*. `level: intermediate`.

At the end they have a headless Orange Pi Zero 3 that plugs into any Ethernet, takes its
upstream from that link automatically, serves a routed and NATed Wi-Fi access point to
clients, and stays reachable for administration over a separate Bluetooth link that is
deliberately not part of the client network — and they can explain, mechanism by
mechanism, why each of those works and where it breaks. They learn the Linux networking
stack, not a file to paste.

**One sentence:** plug in the box, its Wi-Fi clients reach the internet, and you can still
get in to fix it when the config you just wrote is wrong.

## The arc

Each mechanism is done **live and impermanently first** (watch it work, watch it vanish on
reboot), then authored into an `etc/` config repo and deployed to the board. The
instructive failure column is the reason each row is a lesson and not a handover.

### Main path

| # | slug | purpose | objective | instructive failure | completion | design_refs | validators |
|---|---|---|---|---|---|---|---|
| 00 | `find-the-board` | find a headless board on a LAN you do not control | DHCP, ARP, mDNS from the client side | wrong subnet, stale ARP cache vs. a live sweep, mDNS blocked on the LAN | learner SSHes in and can say how they found it | `#address-plan` | `board-reachable` |
| 01 | `reading-the-network` | `ip addr`/`ip route`/`ip neigh` as objects, not incantations | routing tables & the FIB; `ip` as a netlink client | misreading which route carried the session; confusing the neighbour table with the routing table | learner names the link and route that carried their SSH session | `#address-plan`, `#interface-roles` | `board-reachable` |
| 02 | `the-lifeline` | an out-of-band way back in that does not depend on IP | Bluetooth SPP/RFCOMM; getty over a serial line | forgetting the SPP profile is off by default; assuming the lifeline needs an address | learner drops Ethernet and still gets a shell over Bluetooth | `#recovery-invariant` | `lifeline-up` |
| 03 | `bring-up-an-ap` | hostapd in the foreground, a station associates (no IP yet) | 802.11 AP basics: SSID, channel, regulatory domain, association | wrong/blank reg domain so hostapd refuses to start; expecting internet before there is an address | a phone shows "connected, no internet" and the association is in the log | `#interface-roles`, `#address-plan` | `ap-beaconing` |
| 04 | `handing-out-addresses` | dnsmasq as DHCP + DNS for the AP subnet, live | DHCP server side; DNS resolving vs forwarding | a DHCP range that overlaps the interface address; serving DNS that forwards nowhere | a client gets a lease and resolves a name; learner reads both | `#address-plan` | `lease-issued` |
| 05 | `routing-between-two-links` | why a packet from the AP does not reach the upstream yet | `ip_forward`; forward vs input; the host as a router | leaving forwarding off; expecting a reply without NAT and not seeing why | learner shows one packet forwarded and one dropped for want of NAT | `#interface-roles` | `forwarding-on` |
| 06 | `nat-with-nftables` | masquerade and the conntrack idea; clients reach the internet | NAT and connection tracking; nftables NAT hooks | masquerade on the wrong chain/hook; forgetting the return path is conntrack's job | a client pings `1.1.1.1` through the box; learner explains the translation | `#address-plan`, `#interface-roles` | `nat-live` |
| 07 | `the-management-network` | Bluetooth PAN → `bnep0`, a third L3 interface, deliberately not NATed | Bluetooth PAN/NAP; a management interface vs a client interface | NATing the mgmt link like a client; letting a Wi-Fi client reach admin | learner reaches admin over `bnep0` that a Wi-Fi client provably cannot | `#interface-roles`, `#address-plan`, `#recovery-invariant` | `mgmt-reachable` |
| 08 | `a-firewall-with-intent` | nftables policy: forward vs input, per-interface trust, default drop | netfilter tables/chains/hooks; the forward-vs-input distinction | a default-drop that locks out the IP admin path (but not the lifeline — by design) | stated policy enforced; learner predicts each verdict before testing | `#interface-roles`, `#recovery-invariant` | `firewall-policy` |
| 09 | `making-it-survive-a-reboot` | persist the lot into systemd-networkd + hostapd/dnsmasq/nftables units | systemd-networkd; unit ordering & dependencies | a `.network` that fights a leftover live config; unit start-order races | reboot and the AP, NAT and lifeline all come back unattended | `#control-plane`, `#recovery-invariant` | `reboot-survives` |
| 10 | `upstream-detection` | detect Ethernet carrier and switch upstream automatically | link-carrier detection & hotplug; event-driven reconfiguration | acting on the wrong event; not re-NATing after the upstream changes | unplug/replug the upstream link, upstream follows, clients keep working | `#control-plane`, `#interface-roles` | `upstream-follows` |

### Optional track (offered, not sequenced)

Each is written in full and offered by the tutor after the main-path lesson that earns it.
None is a prerequisite for any main-path lesson.

| slug | purpose | objective | instructive failure | completion | offer after | design_refs | validators |
|---|---|---|---|---|---|---|---|
| `watching-your-own-traffic` | see the packets you are routing | `tcpdump`, interface selection, BPF filters | capturing on the wrong interface; reading NAT'd vs pre-NAT addresses backwards | learner captures a client flow and shows both sides of the translation | 06 | `#interface-roles` | `capture-works` |
| `scanning-the-served-network` | discover what is on the network you serve | active vs passive discovery; nmap/arp-scan | scanning upstream by mistake; reading closed vs filtered wrong | learner enumerates a client from the box and explains each result | 08 | `#address-plan`, `#interface-roles` | `scan-runs` |
| `a-captive-portal` | redirect and intercept client HTTP | DNAT redirect, a splash responder, why HTTPS resists it | redirecting all traffic not just port 80; expecting to intercept TLS | an unauthenticated client is redirected to the splash page | 08 | `#interface-roles` | `portal-redirects` |
| `deauth-and-defenses` | 802.11 deauth as an attack, and what hostapd can and cannot do | management-frame attacks; PMF/802.11w | treating deauth as an IP-layer problem; expecting hostapd to stop it without PMF | learner observes a deauth and enables the defence that actually helps | 09 | `#interface-roles` | `deauth-observed` |
| `route-ipv6` | route (not NAT) IPv6 to clients | RA/prefix delegation; why NAT66 is usually wrong | trying to masquerade v6; expecting DHCPv6 to behave like v4 | a client gets a routable v6 address and reaches a v6 host | 06 | `#address-plan` | `v6-routes` |

## Chapters and milestones

- **M1 — I can reach the board and cannot be locked out of it** (00–02)
- **M2 — clients on my Wi-Fi reach the internet** (03–07)
- **M3 — it survives a reboot and behaves like an appliance** (08–10)
- **M4 — it can see and shape the network it serves** (optional track)

## Teaching stance

The learner's "artifact" is often running kernel and daemon state, not a file, so work is
checked by scripts that inspect **live** state on the board over SSH — a written ruleset
that is never loaded must not pass.

**Validators are the tutor's to run, never the learner's** (runner-protocol §14;
`advance_on: validated-evidence-only`). So a lesson body names the *validator* — `board-reachable`,
`nat-live` — and **never a runnable command string** like `bash checks/00-reach.sh`: a
copy-pasteable command invites the tutor to hand the run to the learner, whose result is an
assertion, not evidence, and a validator name resolves only through the `validators` map, which
is the tutor's step. The lesson still says *what* is verified. By-hand learner tests — the
unplugged-Ethernet login, associating a client, the reboot, the unplug/replug — stay imperative;
only the validator invocation is withheld. *(Added 2026-09-22 after a live run — see `#16`.)*

```yaml
workspace_kind: new-repository        # an appliance-config repo the learner builds up
ownership_policy: tutor-must-not-edit-learner-owned
solution_code: on-request-only
one_task_at_a_time: true
advance_on: validators                # all of a lesson's validators pass
                                      # (exact token confirmed against bundle-format at build)

learner_owned:                        # the config the learner authors, and their board.env
  - "etc/**"
  - "board.env"
tutor_owned:                          # supplied plumbing and checks
  - "checks/**"
  - "Makefile"
  - "FLASH.md"
  - "README.md"
  - "boot-overlay/**"

validators:
  # each is a command-kind check run against the live board via checks/<n>-*.sh
  board-reachable:   { kind: command, run: "checks/00-reach.sh" }
  lifeline-up:       { kind: command, run: "checks/02-lifeline.sh" }
  ap-beaconing:      { kind: command, run: "checks/03-ap.sh" }
  lease-issued:      { kind: command, run: "checks/04-lease.sh" }
  forwarding-on:     { kind: command, run: "checks/05-forward.sh" }
  nat-live:          { kind: command, run: "checks/06-nat.sh" }
  mgmt-reachable:    { kind: command, run: "checks/07-mgmt.sh" }
  firewall-policy:   { kind: command, run: "checks/08-firewall.sh" }
  reboot-survives:   { kind: command, run: "checks/09-persist.sh" }
  upstream-follows:  { kind: command, run: "checks/10-upstream.sh" }
  capture-works:     { kind: command, run: "checks/opt-capture.sh" }
  scan-runs:         { kind: command, run: "checks/opt-scan.sh" }
  portal-redirects:  { kind: command, run: "checks/opt-portal.sh" }
  deauth-observed:   { kind: command, run: "checks/opt-deauth.sh" }
  v6-routes:         { kind: command, run: "checks/opt-ipv6.sh" }
```

## Supplied files

The board setup is toil or plumbing, never a lesson: the bundle ships what it can, and the
instructive gotchas inside setup (the Wi-Fi regulatory domain, the Bluetooth SPP profile)
are folded into lessons 03 and 02 where they actually bite.

| from | to | describe | scope |
|---|---|---|---|
| `supplies/FLASH.md` | `FLASH.md` | how to flash the image and first-boot the board — a checklist, not a lesson | `tutorial.yaml` |
| `supplies/boot-overlay/` | `boot-overlay/` | first-boot config to copy onto the SD card: enable SSH, set the Wi-Fi country, turn on the Bluetooth SPP profile | `tutorial.yaml` |
| `supplies/board.env.template` | `board.env` | fill in how the check scripts reach your board (host, user); you found these in lesson 00 | `tutorial.yaml` |
| `supplies/Makefile` | `Makefile` | `make deploy` rsyncs `etc/` to the board and restarts the affected services | `tutorial.yaml` |
| `supplies/README.md` | `README.md` | what this config repo is and how to deploy it | `tutorial.yaml` |
| `lessons/00-find-the-board/checks/` | `checks/` | the check script for this lesson | `00-find-the-board` |
| `lessons/01-reading-the-network/checks/` | `checks/` | the check script for this lesson | `01-reading-the-network` |
| `lessons/02-the-lifeline/checks/` | `checks/` | the check script for this lesson | `02-the-lifeline` |
| `lessons/03-bring-up-an-ap/checks/` | `checks/` | the check script for this lesson | `03-bring-up-an-ap` |
| `lessons/04-handing-out-addresses/checks/` | `checks/` | the check script for this lesson | `04-handing-out-addresses` |
| `lessons/05-routing-between-two-links/checks/` | `checks/` | the check script for this lesson | `05-routing-between-two-links` |
| `lessons/06-nat-with-nftables/checks/` | `checks/` | the check script for this lesson | `06-nat-with-nftables` |
| `lessons/07-the-management-network/checks/` | `checks/` | the check script for this lesson | `07-the-management-network` |
| `lessons/08-a-firewall-with-intent/checks/` | `checks/` | the check script for this lesson | `08-a-firewall-with-intent` |
| `lessons/09-making-it-survive-a-reboot/checks/` | `checks/` | the check script for this lesson | `09-making-it-survive-a-reboot` |
| `lessons/10-upstream-detection/checks/` | `checks/` | the check script for this lesson | `10-upstream-detection` |
| *(each optional lesson)* | `checks/` | the check script for that optional lesson | *(that lesson id)* |

> Note on scope: lesson-scope supplies must live inside `lessons/<lesson>/`, so each check
> script ships in its own lesson folder. The five workspace-root files are placed once, at
> materialization. The check scripts inspect state; they do not carry the answer config,
> which stays the learner's to write.

## Durable decisions

### `#address-plan`
AP on `192.168.4.0/24` (`wlan0` = `.1`), Bluetooth PAN/management on `192.168.44.0/24`
(`bnep0` = `.1`), and the upstream Ethernet interface is a DHCP client of whatever upstream LAN
it is plugged into. IPv4 only on the main path. **Interface names are discovered, not assumed:**
the upstream name varies by board/image (`eth0`, `end0`, `enp1s0`, …), so the learner reads it
from the default route in lesson 01 and records it as `WAN_IF` in `board.env` (AP interface as
`AP_IF`, default `wlan0`); lessons and checks refer to `$WAN_IF`, never a literal. **Breaks if
contradicted:** an AP subnet that collides with the upstream LAN makes NAT in lesson 06 fail in
a way that looks like anything but an addressing bug; and a lesson that hardcodes an interface
name breaks on any board whose name differs. *Resolved.* IPv6 is **deliberately deferred** to
the optional `route-ipv6` lesson. *(Interface-name discovery added 2026-09-19 after a real
board reported `end0`, not `eth0`.)*

### `#interface-roles`
The upstream interface (`$WAN_IF`) untrusted/upstream; the AP interface (`$AP_IF`, usually
`wlan0`) client (NAT yes, box-input limited to DHCP/DNS); `bnep0` management/trusted (no NAT,
box-input allowed); `lo` local. **Breaks if contradicted:** the firewall in lesson 08 and the
mgmt network in lesson 07 have no coherent policy without this — it is their spine. *Resolved.*

### `#recovery-invariant`
The lifeline — the RFCOMM serial console — must **never** depend on IP configuration.
**Breaks if contradicted:** if the way back in were an IP path, a wrong routing table or a
default-drop firewall (lesson 08) would lock the learner out of their own board. This is
why lesson 02 precedes everything routed. *Resolved.*

### `#control-plane`
systemd-networkd owns the links; hostapd, dnsmasq and nftables are their own units loaded
in a defined order. Not NetworkManager, not ifupdown. **Breaks if contradicted:** the
persistence and auto-switch lessons (09–10) assume one control plane; mixing them produces
races that persist intermittently. *Resolved.*

### `#platform`
The platform stack is pinned: Debian-based Armbian (Bookworm+) on the Orange Pi
Zero 3, systemd, systemd-networkd, nftables, dnsmasq, hostapd, bluez. The **one**
adaptable prerequisite is the package manager: apt by default, and the tutor
substitutes another Debian-derivative's installer once, recording the choice in
the instance. **Breaks if contradicted:** a lesson assuming NetworkManager,
netplan, ifupdown or iptables teaches a different stack from the rest and the
check scripts (which read `networkctl`/`nft`) miss its output. Installing packages
is the learner's work — it needs the network — so a lesson may ask for it.
*Resolved (added 2026-09-19 after the author asked how prerequisites are stated);
package-manager value set by the learner.*

Admin access is **key-based SSH**, established in lesson 00: the check scripts connect
non-interactively (`ssh -o BatchMode=yes`), so a password prompt, a passphrase prompt or an
unaccepted host key make a check fail rather than pause. Lesson 00 therefore installs the
learner's public key (`ssh-copy-id`) and has them settle on one consistent `BOARD_HOST`, and
`require_board()` in `checks/_lib.sh` surfaces SSH's real error instead of misblaming
`board.env`. *Resolved (added 2026-09-19 after a live run hit it — see `#14`).*

### `#dns-policy` (open)
Beyond "dnsmasq forwards to the upstream resolver", DNS policy — caching, blocklists,
split-horizon — is **deliberately unresolved** and a candidate for a later offered lesson.

## Coverage

**The course owes the learner:** routing tables & the FIB · NAT and connection tracking
(conntrack) · DHCP, client and server sides · DNS resolving vs forwarding · 802.11 AP
basics (SSID, channel, regulatory domain, association) · nftables tables/chains/hooks and
the netfilter hook points · the forward-vs-input distinction (host as router vs host as
endpoint) · systemd-networkd and unit ordering · `ip` as a netlink client · Bluetooth
SPP/RFCOMM vs PAN/NAP · link-carrier detection & hotplug.

**The course deliberately does not teach:** WPA3 / enterprise auth internals · VLANs &
multi-AP bridging · kernel-module or U-Boot / bootloader work · IPv6 on the main path
(offered separately).

## Proposed manifest fields

```yaml
bundle_format: 1
id: orange-pi-network-appliance
title: "Build a Linux Network Appliance on the Orange Pi Zero 3"
subjects: [linux-networking, routing, nat, wifi, bluetooth, systemd, embedded-linux]
aliases: ["network appliance", "linux router", "wifi access point", "orange pi",
          "nat", "headless router", "travel router"]
level: intermediate
style: project-driven
description: >
  Build a headless Orange Pi Zero 3 that routes and NATs a Wi-Fi access point from its
  Ethernet upstream, stays reachable over Bluetooth, and teaches the Linux networking
  mechanisms behind each step.
```

## Open questions

- `#dns-policy` is intentionally left open (recorded above) — not a blocker for approval.
- Exact `advance_on` token is confirmed against the runner's `bundle-format.md` at build
  time; the intent ("advance when all of a lesson's validators pass") is fixed.
