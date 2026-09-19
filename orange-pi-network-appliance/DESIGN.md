# Design

Durable decisions about the appliance that later lessons depend on. This is
subject knowledge for the tutor, not learner progress. It is seeded here and the
tutor appends to it as the learner makes decisions during the course.

## Address plan {#address-plan}

The appliance uses three interfaces with fixed roles on fixed subnets:

- **the upstream Ethernet interface** — a DHCP *client* of whatever LAN it is
  plugged into, so its address is not known in advance and must not be assumed. Its
  **name is not assumed either**: it varies by board and image (`eth0`, `end0`,
  `enp1s0`, …). The learner discovers it in lesson 01 by reading the default route,
  records it as `WAN_IF` in `board.env`, and exports `WAN_IF` in the board shell;
  lessons and check scripts refer to `$WAN_IF`, never a literal name.
- **the access-point interface**, `192.168.4.1/24` — usually `wlan0` (recorded as
  `AP_IF`). Clients on `192.168.4.0/24` receive addresses by DHCP.
- `bnep0` — the **Bluetooth management network**, `192.168.44.1/24`. Admin hosts
  on `192.168.44.0/24` reach the appliance here.

Interface **names** are discovered and recorded, never assumed; the subnets and
roles below are fixed.

The main path is IPv4 only. IPv6 is **deliberately deferred** to the optional
`route-ipv6` lesson; nothing on the main path routes or NATs IPv6.

**What breaks if a lesson contradicts this:** if the AP subnet is chosen to
overlap the upstream LAN — both `192.168.1.0/24`, say — then NAT in lesson 06
fails in a way that looks like a firewall bug, a DNS bug, anything but the
addressing collision it is. Keep the AP and management subnets in ranges an
ordinary home LAN does not use. *Resolved.*

## Interface roles and trust {#interface-roles}

Each interface has one trust level, and the firewall is built entirely around it:

- the **upstream interface** (`$WAN_IF`) — **untrusted / upstream**. The internet
  is on the other side of it.
- the **AP interface** (`$AP_IF`, usually `wlan0`) — **client**. Traffic is NATed
  out through `$WAN_IF`; input *to the appliance itself* from the AP is limited to
  what a client needs (DHCP, DNS).
- `bnep0` — **management / trusted**. Not NATed. Input to the appliance is
  allowed here, because this is where administration happens.
- `lo` — local.

**What breaks if a lesson contradicts this:** the management network (lesson 07)
and the firewall (lesson 08) have no coherent policy without these roles — they
are the spine both are built on. NATing the management link, or allowing a Wi-Fi
client to reach administration, collapses the distinction the whole design rests
on. *Resolved.*

## The recovery invariant {#recovery-invariant}

The lifeline — the RFCOMM Bluetooth serial console from lesson 02 — **must never
depend on IP configuration.** It is a serial getty over a Bluetooth profile, not
a network path, and it keeps working when the routing table is wrong and when the
firewall is dropping everything.

**What breaks if a lesson contradicts this:** if the way back into the board were
an IP path, then a wrong route or a default-drop firewall policy (lesson 08)
would lock the learner out of their own appliance with no recovery. This is the
reason lesson 02 comes before everything routed, and the reason the firewall
lesson can safely teach default-drop. *Resolved.*

## Control plane {#control-plane}

systemd-networkd owns the links; hostapd, dnsmasq and nftables run as their own
systemd units, ordered so the appliance comes up unattended after a reboot. The
control plane is networkd — **not** NetworkManager, and **not** ifupdown.

**What breaks if a lesson contradicts this:** the persistence lesson (09) and the
upstream-detection lesson (10) both assume one control plane owns the interfaces.
Mixing NetworkManager or ifupdown in produces start-order races that persist
intermittently — the appliance comes up correctly most of the time, which is the
worst way for it to fail. *Resolved.*

## Platform and package manager {#platform}

The appliance runs a Debian-based Armbian image (Bookworm or later) on an Orange
Pi Zero 3, with systemd. The networking stack is fixed: systemd-networkd,
nftables, dnsmasq, hostapd, bluez (see also `#control-plane`). Lessons that
install software assume these packages and no others.

**The package manager is the single adaptable prerequisite.** The default is apt,
and install steps are written `apt install <pkg>`. If the learner is on another
Debian derivative, the tutor asks once, records the choice in the instance's
`STATE.md` under "Decisions made in discussion", and substitutes the install
command from then on. Nothing else adapts, because the tools the course drives
(`systemctl`, `networkctl`, `nft`, `iw`, `hostapd`, `bluetoothctl`) are the same
whichever installer placed them.

Admin access to the board is **key-based SSH**, established in lesson 00. Every check
script connects non-interactively (`ssh -o BatchMode=yes`), so a password prompt, a key
passphrase prompt or an unaccepted host key all make a check fail rather than pause — which
is why key setup and a single consistent `BOARD_HOST` value are part of lesson 00 and not an
unstated assumption.

**What breaks if a lesson contradicts this:** a lesson that assumes NetworkManager,
netplan, ifupdown or iptables is teaching a different stack from every other
lesson, and the check scripts — which read `networkctl` and `nft` — will not see
what it produced. Installing a package is the learner's work (it needs the
network); a lesson is right to ask for it, and wrong to assume a stack other than
this one. *Resolved, except the package-manager value, which the learner sets.*

## DNS policy {#dns-policy}

**Deliberately unresolved.** On the main path, dnsmasq simply forwards client
queries to the upstream resolver the appliance learned by DHCP on the upstream
interface (`$WAN_IF`).
Anything beyond that — caching policy, blocklists, split-horizon answers for the
management network — is left open and is a candidate for a later offered lesson.
A learner who wants to go further here is not contradicting the design; they are
resolving a decision the course left open on purpose. *Open.*
