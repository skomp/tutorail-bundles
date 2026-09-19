---
id: 01-reading-the-network
title: Reading the network
design_refs: [address-plan, interface-roles]
validators: [board-reachable]
---

## Purpose

Learn to read the board's live network state as concrete, inspectable tables before you
change any of it.

## Prerequisites

Lesson `00-find-the-board` is complete: the board is powered and on the wired network, you
can open an SSH session to it, and `board.env` holds a working `BOARD_HOST` and
`BOARD_USER`. Everything in this lesson is run on the board, in that SSH session.

## Learning objectives

- Read the interface list and tell an interface, an address and a link state apart
- Read the routing table and predict which interface and next hop the kernel picks for a
  given destination
- Read the neighbour table and say what it records and what it does not
- Point at the exact interface, address and route that carry your own SSH session
- Identify your upstream Ethernet interface — whose name varies by board and image
  (`eth0`, `end0`, `enp1s0`, …) — along with its DHCP-assigned address and the default
  route, and record the interface name as `WAN_IF` for the rest of the course

## Theory

The board's networking is not a mystery the `ip` command performs; it is a set of tables the
kernel already holds. The `ip` command is a client. It speaks to the kernel over an interface
called netlink, asks a question ("what interfaces exist?", "what routes are installed?"), and
prints the answer. Nothing you run in this lesson sends a single packet onto the wire. You are
reading state, not making it. Keeping that distinction clear is the whole point of the lesson:
when something is broken later, you will want to know whether the tables are wrong or the wire
is, and these are the tables.

There are three tables to read.

The **interface list** is what you see with `ip addr` (or `ip link` for just the links). An
*interface* is the kernel's handle on one way of sending and receiving packets: `lo` is the
loopback that never leaves the board, and one of the others is the wired Ethernet port you
arrived on. Its name depends on the board and the image — it may be `eth0`, `end0`, `enp1s0`
or similar — which is exactly why you read it here rather than assume it; more interfaces
appear in later lessons. An *address* is an IP address bound to an interface, written with its prefix length, for
example `192.168.1.50/24`. One interface can carry several addresses, or none. A *link state*
is separate from any address: `ip link` shows flags like `UP` (the interface is administratively
enabled) and a `state` such as `UP` or `DOWN` that reflects *carrier* — whether the driver sees
a live connection, for Ethernet a cable plugged into something live at the other end. An interface
can be administratively `UP` yet have no carrier, and it can have carrier yet no address. Read
those three facts — does it exist, does it have carrier, does it have an address — as three
separate questions.

The **routing table** is what `ip route` prints, and it is how the kernel decides where a packet
goes. Given a destination address, the kernel finds the most specific matching route — the one
with the longest prefix that contains the destination — and that route names the outgoing
interface and, when the destination is not directly attached, the *next hop* (a `via` address) to
hand the packet to. A route with no `via`, marked something like `192.168.1.0/24 dev <iface>`, is a
*directly-connected* route: those destinations are on the same link, reachable without a
gateway. The **default route**, written `default via <gateway> dev <iface>`, is the least
specific route of all; it matches every destination that nothing more specific matched, and it is
how the board reaches the wider internet. Routes also often carry a `src` field: that is the
source address the kernel will stamp on packets it originates out of that route, chosen from the
outgoing interface's addresses. `src` is about packets the board itself sends; it is not a filter
on what may arrive.

The **neighbour table** is what `ip neigh` shows, and it answers a different question again. To
put a packet onto a shared link like Ethernet, the kernel needs the *link-layer* (MAC) address of
the next machine on that link — the next hop from the route, or the destination itself if it is
directly connected. It learns those MAC addresses with ARP (for IPv4) and caches them here, each
entry an IP paired with a MAC and a state such as `REACHABLE`, `STALE` or `FAILED`. The neighbour
table is a cache of who is physically next to you on a link. It does not decide where packets go;
the routing table does that, and only then does the neighbour table supply the MAC for the hop the
route already chose. Confusing the two is the classic beginner error, so keep them apart: route
first (which interface, which next hop), neighbour second (what is that next hop's MAC).

Now make it concrete with the session you are sitting in. Your SSH connection arrived on some
interface and the board's replies leave by some route. You can read both off these tables rather
than guessing.

## Concepts to teach

Interface, address (with prefix length), link state versus carrier, administrative up versus
operational up. Routing table / FIB, longest-prefix match, directly-connected route, default
route, next hop (`via`), `src` address. Neighbour / ARP table, MAC address, neighbour state.
`ip` as a netlink client that reads kernel state rather than being the network itself. The
address plan in this course (see `#address-plan`): the upstream Ethernet interface is the
untrusted upstream and takes its address by DHCP, so neither its address nor its **name** is
known in advance — both must be read, not assumed. The upstream interface's name is recorded
as `WAN_IF`, and the access-point interface (usually `wlan0`) as `AP_IF`.

## Constraints

This is a read-only lesson. Inspect; do not configure, bring interfaces up or down, add or
delete routes, or flush the neighbour table. Nothing is persisted to `etc/` because nothing is
configured — there is no config to author yet. Every command runs on the board over your SSH
session.

## Suggested progression

Run `ip addr` and read off every interface, its carrier/link state, and any addresses. Then
`ip link` alone to see the state flags without the address noise. Run `ip route` and locate the
default route: its `dev` names your **upstream Ethernet interface**, and that is the name the
rest of the course needs. Confirm it two ways — it is the interface `ip route show default`
points at, and it is the one carrying your SSH session (below) — because on a headless box you
should not guess it. Note both its **name** (for example `end0`) and its DHCP-assigned address,
and read off the directly-connected route for its subnet and the `src` address. Predict, before
running anything else, which interface a packet to a public address (say `1.1.1.1`) would leave
by, and which it would take to another host on the upstream subnet; confirm with
`ip route get 1.1.1.1` and `ip route get <a neighbour on the subnet>`. Now tie it to your own
session: your SSH client's address is the destination for the board's replies — run
`ip route get <your client's address>` to see the interface and route that carry your session,
and check that it matches where you connected from and matches the default route's `dev`.
Finally run `ip neigh` and identify the entry for your next hop (the default gateway, or your SSH
client if it is on the same link), noting its MAC and state.

Now record what you found, because every later lesson refers to the upstream by name. Set
`WAN_IF` to your interface's name in `board.env` (for example `WAN_IF=end0`) — that is what the
check scripts and the deploy Makefile read — and leave `AP_IF=wlan0` unless your Wi-Fi adapter
is named differently. Then, in this board session, `export WAN_IF=<name>` so the commands in
later lessons that use `$WAN_IF` work as written (re-export it whenever you open a new session on
the board, or add it to your shell profile). Re-confirm the board is still reachable with
`bash checks/00-reach.sh`; since this lesson changes no board state, this only re-checks that
SSH still works.

## Completion conditions

From the live tables, and without guessing, the learner can:

- Name the interface and route (`ip route get <client-address>`) that carry their own SSH
  session, and explain why that interface is the one, in terms of the matching route rather than
  merely "it has an address".
- Name their upstream Ethernet interface — found as the `dev` of the default route and
  confirmed as the one carrying their SSH session — state its current IPv4 address and prefix,
  say both name and address were not knowable in advance (the address came from DHCP), and
  confirm they have recorded the name as `WAN_IF` in `board.env` (and exported it in the board
  session).
- Point at the default route (`default via … dev …`) and distinguish it from a
  directly-connected route.
- Explain what the neighbour table records (IP-to-MAC for hosts on a shared link, with a state)
  and why it is consulted only after the routing table has chosen a next hop.
- Confirm `bash checks/00-reach.sh` still passes, understanding it merely re-confirms SSH because
  this lesson changed no state.

## On completion, persist

Nothing is written to `etc/`. Record in the instance's `STATE.md` that the learner can read the
interface, routing and neighbour tables, that they have identified the upstream Ethernet
interface and recorded its name as `WAN_IF` (note the name, e.g. `end0`), its DHCP-assigned
address and prefix (note the value, marking that it may change on the next lease) and the board's
default route, and that they can name the interface and route carrying their SSH session. Record
the chosen `WAN_IF` (and `AP_IF` if it is not `wlan0`) as a decision.

## Optional deeper paths

Add `-s` to `ip -s link` to see per-interface packet and error counters. Read the other routing
tables with `ip route show table all`, and see how the kernel chooses among tables with
`ip rule`. Watch the neighbour table change: `ip neigh` before and after reaching a new host on
the subnet, and observe entries age from `REACHABLE` to `STALE`. Compare `ip route get` for a
directly-connected destination (no `via`) against a remote one (via the gateway) and read the
difference in the output.
