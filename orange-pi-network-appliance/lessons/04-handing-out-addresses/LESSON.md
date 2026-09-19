---
id: 04-handing-out-addresses
title: Handing out addresses
design_refs: [address-plan, platform]
validators: [lease-issued]
supplies:
  - from: lessons/04-handing-out-addresses/checks/04-lease.sh
    to: checks/04-lease.sh
    describe: "Check for this lesson: dnsmasq issued a lease on the AP subnet"
---

## Purpose

In lesson 03 a client can associate to the AP, but it gets no address, so it is useless — a
link with nothing to say over it. This lesson gives the appliance a **DHCP server** so a
joining client is handed an address, a gateway, and a DNS resolver automatically, and a **DNS
service** so the names that client looks up get answered. You run `dnsmasq` in the foreground
first and watch a real client take a lease, then persist the configuration into the `etc/`
repo. At the end a Wi-Fi client can get on the AP subnet and resolve a name — but it still
cannot reach the internet, because forwarding and NAT are lessons 05 and 06.

## Prerequisites

The AP from lesson `03-bring-up-an-ap` working: `wlan0` in AP mode carrying `192.168.4.1/24`,
hostapd beaconing, and a client that can associate (and currently sits at "connected, no
internet"). Your SSH session and `board.env` (lesson `00-find-the-board`), and the Bluetooth
serial lifeline from lesson `02-the-lifeline` — nothing here should cut your access, but a
misconfigured resolver on the board is exactly the kind of thing that can, so keep the
lifeline available. The ability to read links and addresses (`ip addr`, lesson
`01-reading-the-network`), where you also discovered and recorded the board's upstream Ethernet
interface as `WAN_IF` (its actual name varies — `eth0`, `end0`, `enp1s0`, …); it is exported in
your board session, so later references here use `$WAN_IF`. The `dnsmasq` package on the board; install it if it is absent
(`apt install dnsmasq`, or the installer the tutor recorded — the package manager is the one
prerequisite that adapts, `#platform`). A second device with Wi-Fi to join the AP and, on it,
a way to run a DNS query (`dig`, `nslookup`, or the phone simply loading a name).

## Learning objectives

- Explain what a DHCP server hands out — an address from a **range**, a **lease time**, and
  **options** (the default gateway and the DNS server) — and why each matters to the client
- Follow the **DORA** exchange (Discover, Offer, Request, Acknowledge) well enough to read it
  happening in a foreground `dnsmasq -d` log
- Distinguish a DNS **resolver** from a DNS **forwarder**, and explain that dnsmasq here is a
  forwarder that relays client queries to the upstream resolver the board learned by DHCP on
  the upstream interface (`$WAN_IF`) (`#address-plan`)
- Write a minimal dnsmasq configuration that serves DHCP and DNS on `wlan0` only, with the
  gateway and DNS options pointing at `192.168.4.1`
- Read the lease file (`/var/lib/misc/dnsmasq.leases`) and explain every field of a live lease
- Resolve the common `:53` conflict with a stub resolver, so dnsmasq can bind the DNS port
- Recognise the instructive failures — an overlapping range, a lease with no gateway/DNS
  option, a forwarder pointed at nothing — and know what each looks like from the client
- Persist the working configuration into the `etc/` repo and deploy it, knowing that clients
  still have no internet until lessons 05–06

## Theory

A client that has just associated has a working link and nothing else. It does not know its own
address, it does not know where to send traffic that is not on its own wire, and it does not
know who to ask to turn a name into an address. **DHCP** — the Dynamic Host Configuration
Protocol — is how it learns all three, automatically, from a server on the network. On this
appliance that server is `dnsmasq`, running on the board and listening on `wlan0`.

A DHCP server hands out three kinds of thing. First, an **address**, taken from a configured
**range** (also called a pool) — a contiguous band of addresses inside the subnet that the
server is allowed to give away, for example `192.168.4.50` through `192.168.4.150` inside
`192.168.4.0/24`. Second, a **lease time**: an address is not given forever, it is *leased*
for a period (an hour, a day), after which the client must renew or lose it. This lets the
server reclaim addresses from devices that have left. Third, a set of **options** — extra facts
the client needs to actually use the network. The two that matter here are the **default
gateway** (option 3, "router": where to send traffic bound for anywhere off this subnet) and
the **DNS server** (option 6: who to ask to resolve names). On this appliance both of those are
the appliance itself, `192.168.4.1` — it is the client's gateway *and* its resolver.

The exchange that delivers all this is four messages, remembered as **DORA**:

- **Discover** — the client, with no address yet, broadcasts "is there a DHCP server here?"
- **Offer** — the server replies "yes, you can have `192.168.4.<n>`, here are the options"
- **Request** — the client broadcasts "I'll take that one" (broadcast, so any other server
  that also offered knows it was not chosen)
- **Acknowledge** — the server confirms, records the lease, and the client configures itself

When you run `dnsmasq -d` in the foreground and a client joins, you will see these four steps
logged in order, with the client's MAC and the offered address. Reading them go by is the proof
the DHCP side works — and if it stops after Discover with no Offer, the log tells you the server
heard the client but had nothing valid to give.

The **DNS** side is separate, and the distinction to hold onto is **resolver versus forwarder**.
A full resolver walks the DNS hierarchy itself, from the root servers down, to answer a query. A
**forwarder** does no such walking — it simply passes the client's query to another resolver and
relays the answer back. dnsmasq here is a **forwarder**. When a client asks it for `example.com`,
dnsmasq forwards that query to the upstream resolver that the board learned when the upstream
interface (`$WAN_IF`) got its address by DHCP from the upstream network (`#address-plan`: the
upstream interface is the DHCP-client upstream, and its learned resolver is what the appliance
forwards to). The client asks the appliance; the
appliance asks upstream; the answer comes back the same path. This is why the DNS option you
hand clients is `192.168.4.1` and not the upstream resolver directly — clients only ever talk to
the appliance, and the appliance decides where the real query goes.

Every lease dnsmasq grants is written to **`/var/lib/misc/dnsmasq.leases`**, one line per lease.
The fields are: the lease expiry (a Unix timestamp), the client's **MAC address**, the leased
**IP**, the client's **hostname** (if it announced one), and the client identifier. Reading this
file is how you confirm, on the board, exactly which client holds which address and until when —
independently of what the client claims about itself.

One platform wrinkle to expect: DNS lives on **UDP/TCP port 53**, and on a Debian/Armbian system
something may already be listening there — a stub resolver such as `systemd-resolved` bound to
`127.0.0.53`. dnsmasq wants to bind `:53` on `wlan0` to answer clients, and if a stub resolver is
occupying the port dnsmasq will fail to start with an "address already in use" error. You resolve
this before persisting — either by stopping/disabling the stub resolver, or by confining each to
its own interface so they do not collide. The foreground run will surface the conflict loudly,
which is the point of running foreground first.

## Concepts to teach

DHCP as the mechanism by which a client with only a link learns its address, gateway, and
resolver; the three things a DHCP server hands out — an address from a **range/pool**, a **lease
time**, and **options**; specifically the gateway option (router, = `192.168.4.1`) and the DNS
option (= `192.168.4.1`) and why both point at the appliance; the **DORA** four-message exchange
and how to read it in a foreground `dnsmasq -d` log; DNS **resolver versus forwarder**, and that
dnsmasq is a forwarder relaying to the upstream resolver the board learned by DHCP on the
upstream interface (`$WAN_IF`) (`#address-plan`); the lease file `/var/lib/misc/dnsmasq.leases`
and every field of a lease line; binding dnsmasq to `wlan0` only and never serving DHCP on the
upstream interface (`$WAN_IF`); the `:53` stub-resolver
conflict and how to clear it; and the deliberate limit that a client can get an address and
resolve a name yet still not reach the internet, because forwarding (lesson 05) and NAT (lesson
06) do not exist yet.

## Constraints

- You write the dnsmasq configuration yourself, every directive of it. The tutor states what the
  configuration must contain and checks the result; it does not write your configuration.
- dnsmasq serves **only** `wlan0`. Bind it to the AP interface and do **not** serve DHCP on
  the upstream interface (`$WAN_IF`) — handing addresses to the network the board is a *client* of
  is a serious misconfiguration. Use the directives that pin dnsmasq to `wlan0` (an
  `interface=`/`bind-interfaces` pairing, or `except-interface=`), not a bare listen-everywhere.
- The DHCP **range** must lie inside `192.168.4.0/24` and must **not** include `192.168.4.1` —
  that address belongs to the appliance itself and must never be leased to a client
  (`#address-plan`).
- The gateway option and the DNS option you hand clients are both `192.168.4.1`. An address with
  neither is useless; get both right.
- IPv4 only (`#address-plan`). Do not configure DHCPv6 or serve IPv6 addresses.
- Do **not** add forwarding, NAT, or a client default route to the internet in this lesson. A
  client that has an address and can resolve a name but cannot reach the internet is the correct
  end state here.
- Persist into the `etc/` repo and deploy with `make deploy`. The live setup must be reproducible
  from the repo, not live only in your shell history. Enabling dnsmasq at boot and ordering it
  against networkd/hostapd is finalized in lesson `09-making-it-survive-a-reboot`; here, aim for a
  configuration in the repo that deploys and runs.

## Suggested progression

Do it live in the foreground first, watch a real client take a lease, then persist.

Start by clearing the port. Check what, if anything, is already on `:53`: `ss -lunp | grep :53`
(and `ss -ltnp | grep :53` for TCP) shows the listeners. If a stub resolver such as
`systemd-resolved` holds it, decide how to clear it — stop and disable it, or confine it — and
note that a running stub resolver is also what populates `/etc/resolv.conf`, so be deliberate
about what the board itself uses for DNS after you change this. Confirm `wlan0` still carries
`192.168.4.1/24` from lesson 03 (`ip addr show wlan0`); dnsmasq needs the interface addressed on
the subnet it will serve.

Now write a minimal dnsmasq configuration in a scratch file on the board (not yet in the repo —
you are testing it). It needs: a binding to `wlan0` only; a `dhcp-range=` inside
`192.168.4.0/24` that excludes `192.168.4.1`, with a lease time; the **gateway** option pointing
at `192.168.4.1`; and the **DNS** option pointing at `192.168.4.1`. Run it in the **foreground
with debug**: `dnsmasq -d -C /path/to/your.conf`. Read the startup lines — dnsmasq prints the
interface it is serving, the DHCP range it will offer from, and where it is forwarding DNS to. If
it exits with "address already in use", the `:53` conflict is not cleared; go back and clear it.

With dnsmasq beaconing its readiness, join the AP from your client (it already associates from
lesson 03) and watch the foreground log. You should see **DHCPDISCOVER**, **DHCPOFFER**,
**DHCPREQUEST**, **DHCPACK** in order, with the client's MAC and the offered address — the DORA
exchange, live. On the client, confirm it configured itself: it now has an address in your range,
a default gateway of `192.168.4.1`, and `192.168.4.1` as its resolver.

Read the lease from the board: `tail /var/lib/misc/dnsmasq.leases` (or `cat` it). Identify every
field on the client's line — expiry timestamp, MAC, leased IP, hostname, client-id — and check the
IP matches what the client reports and what the log offered.

Now test DNS from the client. Query a name explicitly against the appliance: `dig @192.168.4.1
example.com` or `nslookup example.com 192.168.4.1`. You should get an answer — the client asked
the appliance, the appliance forwarded to the upstream resolver it learned on the upstream interface (`$WAN_IF`), and the
address came back. Note carefully what still does *not* work: try to actually reach that address
(`ping`, a browser) and it fails, because there is no forwarding and no NAT yet. Name resolves,
packet goes nowhere. That gap is lessons 05 and 06, and it is the correct state to end on.

Provoke the instructive failures at least once, so you recognise them for real:

- **Overlapping range.** Set the `dhcp-range` to start at `192.168.4.1` (colliding with the
  appliance's own address) and restart. Watch what dnsmasq says, and reason about the address
  conflict that would cause on the wire. Restore the range to exclude `.1`.
- **Address but no options.** Remove the gateway and DNS options, leaving only the range, and
  rejoin. The client *gets an address* and looks connected, yet it has no route off-subnet and
  no resolver — "connected" but nothing works. This is the most confusing real failure; see it
  deliberately so you diagnose it in seconds later. Restore the options.
- **Forwarding to nowhere.** Point dnsmasq's upstream server at an address that does not answer
  (a `server=` to a dead IP, or with the board's own upstream DNS unavailable) and query again —
  the client gets an address fine but name lookups time out. This isolates "DNS is broken" from
  "DHCP is broken", which look nothing alike once you have seen both. Restore the upstream.

Then stop the foreground dnsmasq (Ctrl-C) and persist. Author the working configuration into the
repo — `etc/dnsmasq.conf`, or `etc/dnsmasq.d/appliance.conf` if you prefer the drop-in form — the
same directives you proved live: bound to `wlan0`, the range, the lease time, the gateway and DNS
options at `192.168.4.1`, and whatever `:53`-conflict resolution your board needed. Deploy with
`make deploy` and confirm dnsmasq comes up against the deployed config and a client still leases.
Getting dnsmasq reliably enabled and correctly ordered against networkd and hostapd for an
unattended boot is finalized in lesson `09-making-it-survive-a-reboot`; here, aim for a config in
the repo that deploys and serves.

## Completion conditions

- dnsmasq is running against your configuration, bound to `wlan0`, and **not** offering DHCP on
  the upstream interface (`$WAN_IF`).
- A Wi-Fi client that joins the AP **obtains an address inside `192.168.4.0/24`** (in your
  configured range, and never `192.168.4.1`), with default gateway `192.168.4.1` and DNS server
  `192.168.4.1`.
- The lease is visible by hand in `/var/lib/misc/dnsmasq.leases` — you can point to the client's
  line and read off its MAC, leased IP, and expiry.
- The client **resolves a name** through the appliance — `dig @192.168.4.1 example.com` (or
  `nslookup example.com 192.168.4.1`) returns an answer.
- The client still has **no internet** — a `ping` or browser to a resolved address fails —
  because forwarding and NAT do not exist yet. This is expected; confirm you did not add them.
- You can explain, out loud, the options handed out and why the gateway and DNS both point at
  `192.168.4.1`.
- `etc/dnsmasq.conf` (or `etc/dnsmasq.d/appliance.conf`) exists in the repo with the directives
  you proved live, and `make deploy` applies it.
- `bash checks/04-lease.sh` passes — it SSHes to the board and confirms dnsmasq is running and a
  lease has been issued on the AP subnet. **Associate a client to the AP first**, so there is a
  lease for the check to find, then run it.

## On completion, persist

Record in the instance's `STATE.md` (and `DESIGN.md` where it is a durable decision):

- DHCP and DNS now serve the AP subnet: a client joining `wlan0` is handed an address, a gateway,
  and a resolver, and its name lookups are answered.
- The **DHCP range** chosen (its start and end inside `192.168.4.0/24`) and the **lease time**,
  so later lessons and any debugging know exactly what the pool is.
- That the gateway option and DNS option handed to clients are both `192.168.4.1`, and that
  dnsmasq forwards DNS to the upstream resolver learned by DHCP on the upstream interface
  (`$WAN_IF`) (`#address-plan`).
- How the `:53`/stub-resolver conflict was resolved on this board, so it is not rediscovered from
  scratch next time.
- That **clients still have no internet** — they have an address and can resolve names, but
  forwarding (`05-routing-between-two-links`) and NAT (`06-nat-with-nftables`) do not exist yet,
  and those are the next lessons.

## Optional deeper paths

- Add a **static lease** (`dhcp-host=` mapping a MAC to a fixed address) so a chosen device always
  gets the same IP, and watch it take that address instead of one from the pool.
- Explore dnsmasq's **local DNS**: give clients names for each other or for the appliance
  (`/etc/hosts` entries dnsmasq serves, or `dhcp-fqdn`/`domain=`), so `ping appliance` resolves
  on the AP subnet without any upstream involvement.
- Watch DHCP on the wire with `tcpdump -i wlan0 port 67 or port 68` while a client joins, and line
  the captured Discover/Offer/Request/Ack packets up against the dnsmasq log — the same DORA, seen
  from the network instead of the server.
- Look at how dnsmasq learns its upstream servers — from `/etc/resolv.conf`, or pinned explicitly
  with `server=` / `--no-resolv` — and reason about what should happen to client DNS when the
  upstream interface (`$WAN_IF`) changes, which is the problem lesson `10-upstream-detection` returns to.
