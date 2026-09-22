---
id: route-ipv6
title: Routing IPv6
design_refs: [address-plan, platform]
validators: [v6-routes]
optional: true
supplies:
  - from: lessons/route-ipv6/checks/opt-ipv6.sh
    to: checks/opt-ipv6.sh
    describe: "Check for this optional lesson: IPv6 is routed, not NATed, with router advertisements"
---

## Purpose

Give your Wi-Fi clients real, globally routable IPv6 by *routing* a delegated
prefix to them — and see why the NAT reflex you built in lesson 06 is exactly the
wrong instinct on IPv6.

The main path of this course is IPv4 only, and it ends with NAT: many private
clients hiding behind one upstream address (lesson 06). That habit is so strong it
feels like "how networking works". IPv6 works differently on purpose. There are
enough addresses that every host can hold a globally unique, routable one, so
there is nothing to hide behind a translator and nothing to translate. Instead of
masquerading clients, you ask the upstream for a block of addresses, hand a slice
of that block to the `wlan0` side, and *route* between the two. This optional
lesson is where IPv6 is taught, deliberately deferred from the main path so the
IPv4 model lands first.

## Prerequisites

This lesson stands alone but assumes a finished IPv4 appliance. Before you start:

- Lesson 01 established your upstream interface name (it varies by board and image
  — `eth0`, `end0`, `enp1s0`, …) and recorded it as `WAN_IF` in `board.env`, with
  the AP interface recorded as `AP_IF` (usually `wlan0`). Your board session has
  `WAN_IF` exported (`export WAN_IF=<name>`), so the interactive commands below use
  `"$WAN_IF"` for the upstream, and config files you author use the actual recorded
  name in place of the `<WAN_IF>` placeholder.
- Lesson 06 (`06-nat-with-nftables`) complete: Wi-Fi clients on
  `192.168.4.0/24` reach the internet, NATed out the upstream interface
  (`$WAN_IF`). That working IPv4 box is the thing you are extending, and its NAT
  model is the foil for everything here.
- Lesson 02 (`02-the-lifeline`) available: a way onto the box that does not depend
  on its networking. IPv6 forwarding and RA changes can disturb client
  connectivity; keep the Bluetooth lifeline within reach.
- The control plane is `systemd-networkd` (per `#control-plane`), and the address
  plan (`#address-plan`) defers IPv6 to this lesson — there is no IPv6 configured
  yet.
- **An upstream that actually provides IPv6.** This is the hard prerequisite, and
  it is not yours to control. Ideally the upstream offers *prefix delegation*
  (DHCPv6-PD), which hands you a block you can sub-divide. If the upstream gives
  you only a single address on the upstream interface (`$WAN_IF`) and no delegated
  prefix, you can bring IPv6
  up *on the box* but you cannot cleanly route a globally routable prefix to
  clients — read the theory, do what your upstream allows, and stop where it
  stops. If the upstream has no IPv6 at all, you can complete the reading and the
  forwarding step but not the end-to-end client test; that is an honest outcome,
  not a failure of your work. Confirm what you have early (see progression step 1)
  before building on an assumption.

## Learning objectives

- Explain why IPv6 hosts get globally routable addresses and why that removes the
  need for NAT — and why NAT66 is usually a mistake, not a translation of your
  IPv4 setup.
- Describe how an upstream hands you address space with DHCPv6 Prefix Delegation
  (DHCPv6-PD), and how that differs from a single upstream address.
- Explain Router Advertisements (RA) and SLAAC: how a client on `wlan0` learns a
  prefix and configures its own global address from your advertisements, with no
  central lease table.
- Enable IPv6 forwarding, and explain why it is a separate switch from the IPv4
  forwarding you turned on in lesson 05.
- Advertise a prefix on `wlan0` (with `radvd`, or with dnsmasq's RA support) and
  *route* the delegated sub-prefix to clients rather than masquerading it.
- Contrast each step with the IPv4 equivalent you already built: DHCP lease versus
  SLAAC, private subnet versus delegated global prefix, masquerade versus route.

## Theory

**Enough addresses to stop hiding.** IPv4 has about four billion addresses, far
too few for every device, which is why lesson 06 put your clients on a private
`192.168.4.0/24` range and NATed them behind one upstream address. IPv6 addresses
are 128 bits wide — the space is effectively unlimited at any human scale. A
single delegated prefix typically gives you far more addresses than there are
devices on Earth. Because addresses are plentiful and globally unique, every host,
including a phone on your AP, can hold an address the whole internet can route to.
There is no scarcity to work around, so there is nothing to translate.

**Why NAT66 is the wrong reflex.** After lesson 06 the instinct is to reach for
`masquerade` again — a "NAT66" rule that hides clients behind the box's IPv6
address. Resist it. NAT exists on IPv4 to *stretch a scarce address space*; that
problem does not exist on IPv6, so NAT66 buys you nothing and costs you plenty. It
breaks end-to-end addressing (the property IPv6 is designed to restore), confuses
connection tracking, and complicates the return path — all to solve a scarcity
problem you do not have. The IPv6 way is to give clients real addresses and
*route* their packets. If you catch yourself writing a masquerade rule in this
lesson, that is the mistake this lesson is built to prevent.

**How you get address space: prefix delegation.** On IPv4 your upstream interface
(`$WAN_IF`) got one address from the upstream by DHCP. On IPv6 the upstream can do better: with
*DHCPv6 Prefix Delegation* (DHCPv6-PD) it delegates a whole *prefix* — a block of
addresses, for example a `/56` or `/60` — for you to use and sub-divide. Think of
it as being handed a range you own, not a single address. `systemd-networkd`
requests a delegated prefix on the upstream link and then assigns a slice of it to
your downstream link. You take one `/64` out of the delegated block for `wlan0`;
that `/64` is what your clients will draw their addresses from. Contrast with
IPv4: there you *invented* a private subnet (`192.168.4.0/24`) because you could
not get routable space; here the routable space is *given* to you to divide.

**How clients configure themselves: RA and SLAAC.** On IPv4 you ran a DHCP server
(dnsmasq, lesson 04) that handed each client an address from a lease table. IPv6's
usual mechanism is different and does not need a central table. The router — your
box — periodically sends *Router Advertisements* (RAs) onto `wlan0`. An RA
announces "this `/64` prefix is on this link, and I am a router you can use". A
client that hears the RA performs *SLAAC* (Stateless Address Autoconfiguration):
it forms its own address by combining the advertised prefix with an
interface-derived or randomised suffix, checks the address is unused, and starts
using it — no request to a server, no lease. The RA also tells the client to use
your box as its default IPv6 gateway. This is the step that most surprises someone
coming from IPv4: you do not "hand out" IPv6 addresses the way you handed out
leases; you *advertise a prefix* and clients build their own. (DHCPv6 can also
assign addresses statefully, but on a simple AP RA/SLAAC is the normal path;
expecting DHCPv6 to behave like IPv4 DHCP is a common wrong turn.)

**Turning on forwarding — again, separately.** In lesson 05 you set
`net.ipv4.ip_forward` so the kernel would forward IPv4 between links. IPv6 has its
own independent switch: `net.ipv6.conf.all.forwarding` (and it interacts with how
the kernel treats RAs on an interface that is itself forwarding). Enabling IPv4
forwarding did *not* enable IPv6 forwarding; this is a separate, easy-to-forget
step, and without it packets from clients will not cross the box no matter how
correct the addressing is.

**Advertising the prefix on `wlan0`.** Something on the box must actually emit the
RAs for the `/64` you took from the delegated prefix. Two common choices: `radvd`
(the dedicated Router Advertisement Daemon) or dnsmasq's built-in RA support (the
same dnsmasq you already run for IPv4 on `wlan0`, extended to advertise IPv6). Pick
one. With either, you configure it to advertise your downstream `/64` on `wlan0`
and to signal that clients should SLAAC. `systemd-networkd` can also send RAs
itself via `IPv6SendRA=`; whichever you choose, exactly one thing should own RAs on
`wlan0` — two RA sources on one link fight.

**Route, do not translate.** Put it together and the shape is: the upstream
delegates a prefix; you assign one `/64` of it to `wlan0`; you advertise that
`/64` so clients SLAAC global addresses; you enable IPv6 forwarding; the box
*routes* client packets out the upstream interface (`$WAN_IF`) with their real
source addresses intact, and
replies come straight back to those globally routable addresses. No masquerade, no
conntrack-driven un-translation, no reverse anything. The upstream already routes
the delegated prefix back toward your box because it delegated it to you — that is
what delegation means. This is the whole point: on IPv6 you route a prefix you were
given, where on IPv4 you masqueraded a private range you invented.

**Install what you use.** If you advertise with `radvd`, install it
(`apt install radvd`); if you extend dnsmasq instead, no new package is needed.
Installing packages is your job, not the tutor's.

## Concepts to teach

- IPv6's address abundance: hosts get globally routable addresses, so the NAT
  rationale from lesson 06 (scarcity) does not apply.
- Why NAT66 / masquerade is the wrong instinct on IPv6, and what it breaks
  (end-to-end addressing) versus what it was ever for on IPv4 (scarcity).
- DHCPv6 Prefix Delegation (DHCPv6-PD): the upstream delegates a *prefix* you
  sub-divide, contrasted with the single upstream-interface (`$WAN_IF`) address
  IPv4 got by DHCP.
- Router Advertisements (RA) and SLAAC: clients learn the prefix and build their
  own global address from your advertisements, contrasted with the IPv4 DHCP
  lease table from lesson 04.
- IPv6 forwarding as an independent switch from IPv4 forwarding
  (`net.ipv6.conf.all.forwarding`), and that enabling one does not enable the
  other.
- Choosing and configuring an RA source on `wlan0` (radvd or dnsmasq RA), with
  exactly one owner of RAs on the link.
- Routing the delegated `/64` to clients versus masquerading it — the central
  contrast with lesson 06.
- Honest dependence on the upstream: without IPv6 upstream, and especially without
  prefix delegation, how far you can and cannot get.

## Constraints

- The learner writes and runs every command and every persisted config. The tutor
  explains, points, and reviews, but never writes a config file or hands over a
  finished ruleset to paste.
- IPv6 must be **routed**, not translated. No `masquerade`/NAT66 rule for IPv6 may
  be present. If the learner writes one out of IPv4 habit, treat it as the central
  teaching moment and have them remove it and route the prefix instead.
- Client global addresses must come from the *delegated* prefix (or the closest
  the upstream allows), advertised on `wlan0` — not from a made-up or
  documentation prefix, and not a ULA standing in for the global one on the main
  path.
- Exactly one thing advertises RAs on `wlan0` (radvd *or* dnsmasq *or*
  networkd's `IPv6SendRA=`), never two at once.
- IPv6 forwarding must be explicitly enabled; do not assume lesson 05's IPv4
  forwarding covers it.
- Do it live first and prove a client gets a global address and reaches an IPv6
  host, then persist into `etc/` and `make deploy`.
- If the upstream provides no IPv6, or no prefix delegation, do not fake it. Bring
  up what the upstream genuinely allows, state plainly where you had to stop, and
  do not fabricate a global prefix to make a test pass.

## Suggested progression

1. **Find out what the upstream gives you** before building anything. From the
   box, check whether the upstream interface (`$WAN_IF`) has a global IPv6 address
   and whether a prefix was delegated (`ip -6 addr show "$WAN_IF"`, `ip -6 route`,
   and networkd's lease/PD state via `networkctl status "$WAN_IF"`). Decide
   honestly: full PD, single address only,
   or no IPv6. This decides how far the lesson can go.
2. Restate the contrast in one line: on IPv4 (lesson 06) you masqueraded a private
   range; on IPv6 you will route a delegated global prefix. Name the reflex to
   resist — no NAT66.
3. **Request/observe the delegated prefix** and assign a `/64` from it to `wlan0`
   in `systemd-networkd` (request PD on the upstream `<WAN_IF>` `.network` — use
   your actual recorded interface name in the filename and its `[Match]` — hand a
   sub-prefix
   to the `wlan0` `.network`). Confirm `wlan0` gains a global `/64` address from
   the delegated block (`ip -6 addr show wlan0`).
4. **Enable IPv6 forwarding** live (`sysctl -w net.ipv6.conf.all.forwarding=1`)
   and note explicitly that this is separate from lesson 05's IPv4 switch.
5. **Advertise the prefix on `wlan0`**: configure radvd (install with
   `apt install radvd`) or dnsmasq's RA support to advertise your downstream `/64`
   and signal SLAAC. Start it and confirm RAs are going out (`radvdump`, or watch
   with `ip -6 monitor` / `tcpdump -i wlan0 icmp6`).
6. **Prove it from a client**: a Wi-Fi client should form a global IPv6 address by
   SLAAC (`ip -6 addr` on the client shows a global address in your `/64`, not
   only link-local/ULA) and reach an IPv6 host — for example
   `ping -6 -c3 2606:4700:4700::1111` or `curl -6` to an IPv6-capable name. Verify
   the client's default IPv6 route points at the box.
7. **Show it is routed, not NATed**: on the box, confirm no IPv6 masquerade rule
   exists (`nft list ruleset` shows no NAT66) and that the client's traffic leaves
   with its own global source address (a quick `tcpdump -i "$WAN_IF" ip6` while the
   client pings shows the client's real address as source, not the box's).
8. **Persist**: move the forwarding sysctl, the networkd PD/prefix assignment, and
   the RA configuration into `etc/`, then `make deploy`. Re-verify after deploy
   that a client still gets a global address and reaches an IPv6 host from the
   persisted config, not just the live state.
9. If the upstream lacked PD or IPv6, stop at the furthest honest point and record
   in the persist step exactly where and why.

## Completion conditions

- A Wi-Fi client obtains a **global** IPv6 address by SLAAC, drawn from the prefix
  advertised on `wlan0` (`ip -6 addr` on the client shows a global address in that
  `/64`, not merely link-local or a ULA), and reaches an IPv6 host through the box
  (for example `ping -6` or `curl -6` to an IPv6 destination succeeds).
- IPv6 is **routed, not masqueraded**: IPv6 forwarding is enabled on the box, and
  there is **no** IPv6 masquerade/NAT66 rule. The client's packets leave the
  upstream interface (`$WAN_IF`) carrying the client's own global source address.
- RAs are advertised on `wlan0` by exactly one source (radvd, dnsmasq, or
  networkd), announcing the downstream `/64` with SLAAC, and the client's default
  IPv6 route points at the box.
- The learner can explain, in their own words, why IPv6 routes a delegated prefix
  instead of NATing, and how RA/SLAAC differs from the IPv4 DHCP lease from lesson
  04.
- The forwarding sysctl, the networkd prefix-delegation/assignment, and the RA
  config are persisted into `etc/` and deployed with `make deploy`, and a client
  still gets a global address and reaches an IPv6 host after the deploy.
- The `v6-routes` validator passes. It confirms IPv6 forwarding is on, that no IPv6
  masquerade rule is present, and that RAs are configured on `wlan0`; and if
  `CLIENT_HOST` (and `CLIENT_USER`) are set in `board.env`, it also drives a real
  client to confirm it has a global IPv6 address and reaches an IPv6 host. Set
  `CLIENT_HOST`/`CLIENT_USER` in `board.env` to get that full client-side test
  rather than the box-only check.
- If the upstream provides no IPv6 or no prefix delegation, the box-side steps
  (forwarding enabled, no NAT66, RA configuration written) are done and the
  limitation is recorded honestly in the persist step; the end-to-end client test
  is not expected to pass, and faking a global prefix to force it does not count as
  completion.

## On completion, persist

Record in the instance's `DESIGN.md`/`STATE.md`:

- IPv6 is **routed** to clients: the upstream delegates a prefix (DHCPv6-PD), a
  `/64` of it is assigned to `wlan0`, and clients form global addresses by SLAAC
  from RAs. Note the delegated prefix and the downstream `/64` actually in use.
- The RA mechanism chosen (radvd, dnsmasq RA, or networkd `IPv6SendRA=`) and which
  interface owns RAs — so a later reader knows where to look and does not add a
  second RA source.
- IPv6 forwarding is enabled and persisted (separate from the IPv4 forwarding set
  in lesson 05).
- **NAT66 was deliberately avoided**: IPv6 client traffic is routed with real
  global source addresses and must stay that way; do not add an IPv6 masquerade.
- If the upstream limited how far this went (single address only, or no IPv6),
  record exactly what was achieved and what the missing upstream capability blocks,
  so the next session does not mistake it for unfinished work.

## Optional deeper paths

- **Firewalling IPv6.** On IPv4, NAT incidentally hid clients from unsolicited
  inbound traffic. IPv6 clients are globally reachable, so there is no NAT to hide
  behind and a stateful IPv6 `filter` (an `ip6` table, or the `inet` family
  covering both) matters *more*, not less. Explore an IPv6 counterpart to the
  lesson 08 firewall: allow established/related and solicited traffic, drop
  unsolicited inbound, while still permitting the ICMPv6 that IPv6 needs to
  function (RA/NA, path MTU) — dropping all ICMPv6 breaks IPv6.
- **ULAs versus global addresses.** Unique Local Addresses (`fc00::/7`) are IPv6's
  private-ish range. Discuss when a ULA is appropriate (stable internal addressing
  independent of a changing delegated prefix) and why it is *not* a substitute for
  the global prefix on the main path — a ULA alone does not reach the internet.
- **Dual-stack behaviour on clients.** With both IPv4 (lesson 06) and IPv6 now
  working, clients use Happy Eyeballs to race A and AAAA connections and prefer the
  one that answers first. Observe a client picking IPv6 for a dual-stack host, and
  what happens when one stack is degraded — useful for reasoning about failures
  that "only happen on some sites".
