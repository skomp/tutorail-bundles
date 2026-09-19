# Design

Durable decisions about the appliance that later lessons depend on. This is
subject knowledge for the tutor, not learner progress. It is seeded here and the
tutor appends to it as the learner makes decisions during the course.

## Address plan {#address-plan}

The appliance uses three interfaces with fixed roles on fixed subnets:

- `eth0` — the **upstream**. It is a DHCP *client* of whatever LAN it is plugged
  into, so its address is not known in advance and must not be assumed.
- `wlan0` — the **access point**, `192.168.4.1/24`. Clients on
  `192.168.4.0/24` receive addresses by DHCP.
- `bnep0` — the **Bluetooth management network**, `192.168.44.1/24`. Admin hosts
  on `192.168.44.0/24` reach the appliance here.

The main path is IPv4 only. IPv6 is **deliberately deferred** to the optional
`route-ipv6` lesson; nothing on the main path routes or NATs IPv6.

**What breaks if a lesson contradicts this:** if the AP subnet is chosen to
overlap the upstream LAN — both `192.168.1.0/24`, say — then NAT in lesson 06
fails in a way that looks like a firewall bug, a DNS bug, anything but the
addressing collision it is. Keep the AP and management subnets in ranges an
ordinary home LAN does not use. *Resolved.*

## Interface roles and trust {#interface-roles}

Each interface has one trust level, and the firewall is built entirely around it:

- `eth0` — **untrusted / upstream**. The internet is on the other side of it.
- `wlan0` — **client**. Traffic is NATed out through `eth0`; input *to the
  appliance itself* from `wlan0` is limited to what a client needs (DHCP, DNS).
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

## DNS policy {#dns-policy}

**Deliberately unresolved.** On the main path, dnsmasq simply forwards client
queries to the upstream resolver the appliance learned by DHCP on `eth0`.
Anything beyond that — caching policy, blocklists, split-horizon answers for the
management network — is left open and is a candidate for a later offered lesson.
A learner who wants to go further here is not contradicting the design; they are
resolving a decision the course left open on purpose. *Open.*
