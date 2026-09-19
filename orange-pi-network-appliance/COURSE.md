# Build a Linux Network Appliance on the Orange Pi Zero 3

## The goal

You will build a headless Orange Pi Zero 3 that you can plug into any Ethernet
network and that immediately becomes a small router: it takes its upstream from
the Ethernet link, serves a Wi-Fi access point whose clients reach the internet
through it, and stays reachable for administration over a separate Bluetooth link
that is deliberately kept off the client network. When the Ethernet link changes,
the appliance follows it without being touched.

The point is not the finished box. It is that by the end you can explain, one
mechanism at a time, why each part works and where it breaks — a routing table, a
NAT translation, a DHCP lease, an 802.11 beacon, an nftables verdict, a
systemd-networkd unit — instead of pasting a configuration you do not understand.

## How this course teaches

Every mechanism is done twice. First **live and impermanently** on the board:
you run `ip`, `nft`, `hostapd` and `dnsmasq` by hand, watch the thing work, and
watch it vanish on the next reboot. Only then do you **persist** it — author the
configuration into an `etc/` repository on your own machine and deploy it to the
board. Doing it live first is what turns "it works" into "I know why it works",
and it is what gives each lesson something you can get wrong in a way that teaches
you something.

You write and run everything yourself. The tutor reads your board's real state
back through small check scripts — a live `nft` ruleset, an actual ping through
the box, a lease that was really issued — and never advances on "trust me".

A word on the recovery path, because it shapes the order of the course: the
Bluetooth serial console (lesson 02) comes before anything that touches routing
or the firewall. It is your lifeline, and it works when the IP stack is broken.
That is what makes the later lessons safe to get wrong.

## What this course assumes you have

The course is pinned to one platform, on purpose. Half of it is about how Linux
*specifically* expresses networking — systemd-networkd units, nftables rulesets —
so it teaches one stack well rather than several badly.

- **Hardware:** an Orange Pi Zero 3.
- **Operating system:** a current Debian-based Armbian image (Bookworm or later)
  with **systemd**. The image is flashed and first-booted before lesson 00 — see
  `FLASH.md`.
- **Networking stack:** **systemd-networkd** as the control plane, **nftables**
  for filtering and NAT, **dnsmasq** for DHCP and DNS, **hostapd** for the access
  point, **bluez** for Bluetooth. These are the subject; they are not swappable.
- **A shell** on your own machine with `ssh`, `rsync` and `make`, to reach and
  deploy to the board.

**The one thing that adapts: the package manager.** The course assumes **apt** and
writes install steps as `apt install …`. If your image uses a different Debian
derivative, tell the tutor at the start and it will substitute your package
manager in the install steps — nothing else changes, because the tools the course
drives are the same. Installing packages needs the network, so it stays your work:
the course cannot ship the packages, and a lesson that asks you to install one is
asking for real work, not toil.

Everything past the package manager is fixed. A different init system, control
plane or firewall is a different course.

## The chapters, in order

- **00 — Find the board.** Locate a headless board on a network you do not
  control, and get a shell on it.
- **01 — Reading the network.** The interface, the routing table and the
  neighbour table as objects you can inspect.
- **02 — The lifeline.** An out-of-band Bluetooth serial console that does not
  depend on the IP configuration.
- **03 — Bring up an access point.** hostapd in the foreground; a station
  associates, with no address yet.
- **04 — Handing out addresses.** dnsmasq as DHCP and DNS for the AP subnet.
- **05 — Routing between two links.** Why a packet from the AP does not reach the
  upstream yet, and what forwarding does.
- **06 — NAT with nftables.** Masquerade and connection tracking; clients reach
  the internet.
- **07 — The management network.** Bluetooth PAN as a third interface, kept off
  NAT and filtered as management.
- **08 — A firewall with intent.** An nftables policy that treats input and
  forward, and each interface, as separate questions.
- **09 — Making it survive a reboot.** Persist everything into systemd-networkd
  and its companion units.
- **10 — Upstream detection.** React to the Ethernet carrier and choose the
  upstream automatically.

## Milestones

- **M1 — I can reach the board and cannot be locked out of it.** (00–02)
- **M2 — Clients on my Wi-Fi reach the internet.** (03–07)
- **M3 — It survives a reboot and behaves like an appliance.** (08–10)
- **M4 — It can see and shape the network it serves.** (the optional lessons)

## Optional lessons

These are offered by the tutor at the right moment and are never required. The
course is complete without any of them.

- **Watching your own traffic** — capture and read the packets you are routing.
  Offered after lesson 06.
- **Scanning the served network** — discover what is on the network you serve.
  Offered after lesson 08.
- **A captive portal** — redirect and intercept client HTTP, and see why HTTPS
  resists it. Offered after lesson 08.
- **Deauthentication and defences** — 802.11 deauth as an attack, and what
  hostapd can and cannot do about it. Offered after lesson 09.
- **Routing IPv6** — route, rather than NAT, IPv6 to clients. Offered after
  lesson 06.

## Topics this course must cover

- routing tables and the FIB (ip-routing, ip-forwarding)
- NAT and connection tracking (nat, conntrack, masquerade)
- DHCP, both client and server sides (dhcp, leases)
- DNS resolving versus forwarding
- 802.11 AP basics: SSID, channel, regulatory domain, association (hostapd, access-point, 802.11-ap)
- nftables tables, chains and hooks, and the netfilter hook points (nftables, netfilter, firewall)
- the forward-versus-input distinction: the host as a router versus as an endpoint
- systemd-networkd and unit ordering (networkd, persistent-networking)
- `ip` as a netlink client (routing-table, fib)
- Bluetooth SPP/RFCOMM versus PAN/NAP (rfcomm, bluetooth-pan, bnep)
- link-carrier detection and hotplug (link-carrier, hotplug, upstream-detection)

## Topics this course deliberately does not cover

- WPA3 and enterprise authentication internals
- VLANs and multi-AP bridging
- kernel-module or U-Boot / bootloader work
- IPv6 on the main path — it is offered as an optional lesson instead
