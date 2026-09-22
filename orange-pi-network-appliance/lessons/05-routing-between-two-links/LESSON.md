---
id: 05-routing-between-two-links
title: Routing between two links
design_refs: [interface-roles]
validators: [forwarding-on]
supplies:
  - from: lessons/05-routing-between-two-links/checks/05-forward.sh
    to: checks/05-forward.sh
    describe: "Check for this lesson: IPv4 forwarding is enabled"
---

## Purpose

Your clients have addresses now but still cannot reach the internet, because by default a
Linux host does not forward packets between its interfaces — it is an endpoint, not a router,
so a packet arriving on `wlan0` bound for the internet is simply dropped. In this lesson you
turn the board into a router by enabling IP forwarding, watch a client's packet actually leave
on the upstream interface (`$WAN_IF`), and then discover that forwarding alone still does not work: the reply never comes
back. That failure is the point of the lesson, and it is what NAT fixes in lesson 06.

## Prerequisites

An SSH session on the board and a working `board.env` (lesson `00-find-the-board`), and the
Bluetooth serial lifeline from lesson `02-the-lifeline` available, because this lesson changes
how the kernel handles traffic between your two links. The access point up and beaconing
(lesson `03-bring-up-an-ap`) and a DHCP server handing out addresses on `192.168.4.0/24`
(lesson `04-handing-out-addresses`), so you have a real client with a real `192.168.4.x` address
that can already reach the board but nothing beyond it. The upstream interface (`$WAN_IF`)
plugged into your upstream network and holding an address on it — a dynamic upstream address is
fine and expected (`#interface-roles`, `#address-plan`). You can read links, addresses and the
routing table by hand (lesson `01-reading-the-network`), which is how you will confirm what
forwarding does. Lesson `01-reading-the-network` established the upstream interface's name (it
varies by board and image — `eth0`, `end0`, `enp1s0`, …) and recorded it in `board.env` as
`WAN_IF`; this lesson assumes you have `export WAN_IF=<name>` (and `AP_IF`, usually `wlan0`) set
in your board shell, so the commands below can refer to it as `"$WAN_IF"`. The `tcpdump` package
on the board; install it if it is absent (`apt install tcpdump`).

## Learning objectives

- Explain the difference between a **host** (an endpoint that accepts or originates traffic for
  itself) and a **router** (a host that forwards traffic between interfaces on behalf of
  others), and why a stock Linux box is the former
- Explain what `net.ipv4.ip_forward` controls and precisely what changes the moment it is `1`
- Enable forwarding live with `sysctl -w` and confirm it took effect
- Trace, using the routing table, how a packet from a `192.168.4.x` client to an internet
  address is matched against the default route and sent out the upstream interface (`$WAN_IF`)
- Use `tcpdump` on the upstream interface (`$WAN_IF`) to observe that a client's forwarded packet leaves the board carrying
  its **private** `192.168.4.x` source address, and that no reply returns
- Explain, in your own words, *why* the reply does not come back — a private source address is
  not routable on the internet, so the far end has nowhere to send its answer — and name NAT
  (lesson 06) as the fix
- Persist forwarding through a file in `/etc/sysctl.d/` so it survives a reboot

## Theory

A freshly installed Linux machine is a **host**: it sends packets that it originates and
receives packets addressed to itself, and that is all. When a packet arrives on one interface
whose destination address is *not* the machine's own, the kernel's default answer is to drop
it. This is the safe default — most machines are not routers and should not silently relay
other people's traffic — but it is exactly what stands between your clients and the internet.
A **router** is a host that has been told to do the opposite: when a packet arrives that is not
for it, look up where that destination lives, and forward the packet out toward it.

The switch that turns one into the other is a single kernel setting: **`net.ipv4.ip_forward`**.
It is a boolean, `0` by default. While it is `0`, the packet that arrives on `wlan0` from a
client, addressed to some internet host, is discarded at the point where the kernel realises
the destination is not local — it never even consults the routing table on that packet's
behalf. Set it to `1` and the kernel begins doing the forwarding step: for a packet that is not
addressed to the board, it looks the destination up in the **routing table** and, if a route
exists, sends the packet on out of the matching interface. Nothing else about the machine
changes — no addresses move, no config is rewritten — you have simply granted the kernel
permission to relay.

So follow one packet. A client on `wlan0` with address `192.168.4.50` wants to reach, say,
`1.1.1.1`. Its own routing table sends anything off its local subnet to its default gateway,
which is the board at `192.168.4.1` — so the packet arrives on the board's `wlan0`, with
**source `192.168.4.50`** and **destination `1.1.1.1`**. The destination is not the board, so
with forwarding on the kernel consults *the board's* routing table. There is no specific route
to `1.1.1.1`, so it matches the **default route** — the one pointing at your upstream gateway
via the upstream interface (`$WAN_IF`) — and the packet is forwarded out the upstream toward the internet. Forwarding is working.
The packet really leaves.

And here is the wall. That packet left the upstream interface (`$WAN_IF`) still carrying its original source address,
`192.168.4.50`. The `192.168.0.0/16` range (which includes `192.168.4.0/24`) is one of the
**private address ranges** (RFC 1918): addresses reserved for use inside local networks and
deliberately **not routable on the public internet**. Every router between you and `1.1.1.1`
either has no route back to `192.168.4.50` or is required to drop traffic to it. Suppose the
packet even reaches `1.1.1.1` and it tries to reply — the reply is addressed *to*
`192.168.4.50`, an address that means nothing out there, so the reply has nowhere to go and
never comes back. From the client's point of view, its request vanished into silence.

Nothing you can do to the *routing* table fixes this, because routing is not the problem — the
packet was routed correctly, out the correct interface. The problem is the **source address**.
The fix is to rewrite it: as each client packet leaves the upstream interface (`$WAN_IF`), replace its private source with
the board's own routable upstream address, and remember the mapping so that when the reply
comes back to the board it can be rewritten again and delivered to the right client. That
rewrite-and-remember is **NAT** (network address translation), and the kernel machinery that
holds those mappings is **connection tracking**. That is lesson `06-nat-with-nftables`. In this
lesson you deliberately stop at the broken state and make sure you can explain it, because a
router that forwards but does not translate is a specific, common, and confusing failure, and
recognising it by its signature — packets leaving with a private source, no replies — is worth
more than being handed the working answer.

## Concepts to teach

Host versus router, and why the stock Linux default is to be a host that drops transit traffic;
`net.ipv4.ip_forward` as the single boolean that switches this, what `0` and `1` each mean, and
that at `0` a non-local packet is dropped before the routing table is even consulted for it;
how, with forwarding on, a forwarded packet is matched against the board's own routing table
and the **default route** sends an internet-bound packet out the upstream interface (`$WAN_IF`); the anatomy of the client
packet — source `192.168.4.x`, destination on the internet — as it arrives on `wlan0` and as it
leaves on the upstream interface (`$WAN_IF`) unchanged; **private (RFC 1918) address ranges** and what "not routable on the
public internet" means concretely; the precise reason the reply fails — the source is private,
so the far end's answer has nowhere to return to — and that this is a source-address problem,
not a routing problem, so no route fixes it; NAT and connection tracking named (not configured)
as the lesson-06 fix that rewrites the source and remembers the mapping for the return trip;
and the difference between a **live** `sysctl -w` change (gone on reboot) and a **persisted**
one in `/etc/sysctl.d/`.

## Constraints

- You write the sysctl configuration yourself, both the live command and the file in
  `/etc/sysctl.d/`. The tutor states what must be true and checks it; it does not write your
  config.
- IPv4 only (`#address-plan`). This lesson is about `net.ipv4.ip_forward`; do not enable IPv6
  forwarding.
- Do **not** add NAT, masquerading, or any nftables rule in this lesson. A client whose packets
  leave the upstream interface (`$WAN_IF`) but get no reply is the correct end state here — that is the observation the
  lesson is built around, and lesson `06-nat-with-nftables` is where it gets fixed.
- Do not change addresses or routes to try to make the reply come back. Routing is already
  correct; changing it will only hide the real cause.
- Persist through `/etc/sysctl.d/` (and deploy from the `etc/` repo with `make deploy`), not by
  editing `/etc/sysctl.conf` in place — the live setup must be reproducible from the repo, not
  live only in your shell.

## Suggested progression

Enable it live, watch what crosses and what does not, then make it permanent.

First, confirm the starting state and prove the default. Read the current value with
`sysctl net.ipv4.ip_forward` (or `cat /proc/sys/net/ipv4/ip_forward`) — it should be `0`. From
a joined client, try to reach an internet address by IP (`ping 1.1.1.1`, avoiding DNS for now)
and confirm it fails. This is forwarding off: the client's packet reaches the board and is
dropped there.

Now watch the drop from the board's side before you change anything. On the board, run
`tcpdump` on `wlan0` filtered to the client — `tcpdump -ni wlan0 host 192.168.4.50` (use your
client's actual address) — and, in another session, `tcpdump -ni "$WAN_IF" host 192.168.4.50`.
Re-run the client's ping. You will see the request arrive on `wlan0` and **nothing** appear on
the upstream interface (`$WAN_IF`): the packet is not being forwarded. That is the endpoint behaviour you are about to
change.

Enable forwarding live: `sysctl -w net.ipv4.ip_forward=1`, and confirm it reads back as `1`.
Nothing else — no addresses, no routes, no firewall. Look at the board's routing table
(`ip route`) and find the **default route** via the upstream interface (`$WAN_IF`); that is the route your client's
internet-bound packets will now match.

Re-run the two `tcpdump` captures and the client's ping. This time the story changes on the upstream interface (`$WAN_IF`):
you will see the client's ICMP echo request **leave the upstream (`$WAN_IF`)**, and — read the addresses in the
capture carefully — it leaves with **source `192.168.4.50`**, the client's private address,
unchanged. Forwarding is working; the packet is really going out. Now watch for the reply.
None comes back. Sit with that: the request left the building, and nothing answered.

This is the moment the lesson is built around, so make sure you can explain it rather than just
observe it. State it in your own words: the packet left the upstream interface (`$WAN_IF`) with a private `192.168.4.x`
source; that address is not routable on the public internet (RFC 1918); so even if it reaches
its destination, the reply is addressed to somewhere that does not exist out there and can
never find its way back. Confirm to yourself that this is a *source-address* problem — try
nothing with routes, because the routing was correct. Name the fix: rewrite the source to the
board's routable upstream (`$WAN_IF`) address on the way out and remember the mapping to reverse it on the
way back — NAT and connection tracking — which is lesson `06-nat-with-nftables`.

Then persist what you enabled. A `sysctl -w` change is gone on the next reboot, so author a
file in `/etc/sysctl.d/` (for example `/etc/sysctl.d/30-ipforward.conf`) containing the line
`net.ipv4.ip_forward=1`, keep it in the `etc/` repo, and `make deploy`. Apply and verify it
without rebooting the whole board — `sysctl --system` reloads the `sysctl.d` files — then
confirm the value is still `1`. If you want the full proof, reboot the board and check that
forwarding comes back up on its own.

## Completion conditions

- `net.ipv4.ip_forward` reads `1` live (`sysctl net.ipv4.ip_forward`), enabled by you with
  `sysctl -w` during the lesson.
- With `tcpdump` on the upstream interface (`$WAN_IF`), you have **seen** a client's forwarded packet leave the upstream (`$WAN_IF`) carrying
  its private `192.168.4.x` source address — not merely inferred it. You can point to the
  request on the upstream interface (`$WAN_IF`) and to the absence of any reply.
- You can explain, in your own words, why the reply does not return: the source is a private
  (RFC 1918) `192.168.4.x` address, not routable on the internet, so the far end has nowhere to
  send its answer — and you can name NAT / connection tracking (lesson 06) as the fix, and say
  why no change to the routing table would help.
- A file under `/etc/sysctl.d/` sets `net.ipv4.ip_forward=1`, it lives in the `etc/` repo, and
  `make deploy` applies it; the setting survives `sysctl --system` (and a reboot).
- You added **no** NAT, no nftables rule, and changed no address or route to force the reply
  back. The client still has no internet — that is the expected end state.
- The `forwarding-on` validator passes — it confirms `net.ipv4.ip_forward` is `1` on the board.

## On completion, persist

Record in the instance's `STATE.md` (and `DESIGN.md` where it is a durable decision):

- IP forwarding is **enabled and persisted**: `net.ipv4.ip_forward=1` live and set in a
  `/etc/sysctl.d/` file deployed from the repo, so the board comes up as a router after a
  reboot.
- That forwarding **alone is not enough** for clients to reach the internet: their packets
  leave the upstream interface (`$WAN_IF`) with a private `192.168.4.x` source and no reply can return.
- That **NAT is still required** for return traffic, and that it is lesson
  `06-nat-with-nftables`, which is next — this is a deliberate cliffhanger, not an unfinished
  bug.

## Optional deeper paths

- Read `/proc/sys/net/ipv4/ip_forward` directly and compare it with `sysctl` output — they are
  two views of the same kernel knob — and browse `/proc/sys/net/ipv4/conf/*/forwarding` to see
  that forwarding also exists per interface, not only globally.
- Look at `net.ipv4.conf.all.rp_filter` (reverse-path filtering) and reason about how it would
  interact with asymmetric routing on a two-link box — a setting worth understanding before it
  ever surprises you.
- Watch the same forwarded packet on both interfaces at once and note that its TTL is
  decremented by one as the board forwards it — the visible fingerprint of a real router hop.
- Read the RFC 1918 private ranges (`10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16`) and
  confirm which one `192.168.4.0/24` falls in and why the course chose it (`#address-plan`).
