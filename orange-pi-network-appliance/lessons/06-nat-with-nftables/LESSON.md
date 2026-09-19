---
id: 06-nat-with-nftables
title: NAT with nftables
design_refs: [address-plan, interface-roles, platform]
validators: [nat-live]
supplies:
  - from: lessons/06-nat-with-nftables/checks/06-nat.sh
    to: checks/06-nat.sh
    describe: "Check for this lesson: masquerade is loaded and a client reaches the internet"
---

## Purpose

Turn on source NAT so a Wi-Fi client finally reaches the internet through the
box — the payoff the whole appliance has been building toward.

In lesson 05 you enabled forwarding and watched a client's packet leave `eth0`
toward the internet, then never get a reply. The packet went out carrying a
source address from `192.168.4.0/24` — a private range that no host on the wider
internet knows how to route back to. The reply had nowhere to return to. This
lesson closes that gap. You will rewrite the source address of each outgoing
client packet to the box's own upstream address, so replies come back to the box,
and let the kernel put them on the return path to the right client. When you
finish, a phone on your access point can browse the web.

## Prerequisites

- Lesson 05 (`05-routing-between-two-links`) complete: `net.ipv4.ip_forward` is
  on and the box forwards client packets out `eth0`. You confirmed the outbound
  packet leaves but no reply returns — that unanswered packet is the problem this
  lesson solves.
- Lesson 04 (`04-handing-out-addresses`) complete: a client associates to the AP
  and gets a `192.168.4.0/24` lease with the box as its gateway and resolver.
- Lesson 02 (`02-the-lifeline`) available: you have a way onto the
  box that does not depend on its networking. Editing packet-mangling rules can
  cut your own path in; keep the Bluetooth lifeline within reach.
- `eth0` has a working upstream lease and the box itself can reach the internet
  (for example `ping -c1 1.1.1.1` from the box succeeds).

## Learning objectives

- Explain why private client addresses cannot receive replies from the internet,
  and how source NAT solves it.
- Explain why this appliance uses `masquerade` rather than a static source-NAT
  rule, in terms of the dynamic upstream address from the address plan.
- Describe connection tracking (conntrack) and its role: the kernel remembers
  each outbound flow so the reply is matched and un-translated automatically,
  with no reverse rule of your own.
- Place a NAT rule correctly: a table of family `ip`, a chain of type `nat` with
  hook `postrouting`, and understand why postrouting is the right hook for
  masquerade.
- Scope the rule to client traffic only (the `192.168.4.0/24` subnet leaving
  `eth0`), leaving the future management network un-NATed.
- Add the rule live, prove a client reaches the internet, then persist it into
  `etc/` and deploy.

## Theory

**Why the reply never came back.** Every packet carries a source and a
destination address. Your client's packet left with source `192.168.4.x`. That
range is one of the private ranges reserved for local networks (RFC 1918); it is
not globally unique and no router on the internet has a route to it. The
destination host answered, but its reply was addressed to `192.168.4.x`, which
dies at the first real router. The fix is to make outgoing packets appear to come
from an address the internet *can* route back to: the box's own upstream address
on `eth0`.

**Source NAT.** Network Address Translation rewrites addresses in packet headers
as they pass through the box. *Source* NAT rewrites the source address of packets
going out. You take the client packet, replace its source `192.168.4.x` with the
box's `eth0` address, and send it on. Now the far host replies to the box, which
is globally reachable. Source NAT is what lets many private clients share one
public-facing address.

**Why masquerade, not a fixed rule.** Plain source NAT (`snat`) rewrites to an
address *you name in the rule*. That only works if you know the upstream address
in advance and it never changes. Per the address plan, `eth0` gets its address
dynamically by DHCP from whatever network you plug into — it can change on a new
lease. `masquerade` is the variant of source NAT that rewrites to *whatever
address `eth0` currently has* at the moment the packet leaves, looked up per
packet. It costs slightly more than a static rule and it is exactly what a
dynamic upstream needs. That is why this appliance masquerades.

**How the reply gets home: connection tracking.** You might expect to need a
second rule to translate replies back. You do not. The kernel's *connection
tracking* subsystem (conntrack) records every flow that passes through the box —
the original source/destination/ports, and the translation it applied. When a
reply arrives for a tracked flow, conntrack recognises it, reverses the
translation automatically, and forwards it to the original client. You write one
rule for the outbound direction; conntrack handles the return. Writing a reverse
rule yourself is a common mistake and is unnecessary — worse, it fights the
machinery that already works.

**Where the rule lives in nftables.** nftables organises rules into *tables*
(scoped to an address family, here `ip` for IPv4), which contain *chains*, which
hold rules. A chain that does address translation must be declared with type
`nat`. Chains also attach to a *hook* — a point in the kernel's packet path — and
a *priority*. For rewriting the source of forwarded traffic, the right hook is
`postrouting`: it runs after the kernel has decided the packet is leaving and
chosen the outgoing interface, which is the last moment before the packet goes on
the wire and the only place masquerade can know the final `eth0` address. A
common instructive failure is to attach the masquerade to `prerouting` (the hook
for *destination* NAT, before routing) — there, nothing gets translated and
clients still fail. This lesson gives you only enough nftables structure to place
this one rule; the full filtering firewall, with its `filter` table and dropped
traffic, is lesson 08.

**Scope it to clients.** The masquerade must apply to client traffic only:
packets from `192.168.4.0/24` leaving `eth0`. A rule that masquerades
*everything* would also rewrite the management network you add in lesson 07,
which is deliberately *not* NATed — its traffic must keep its real source
address. Match on the client source subnet, the outgoing interface `eth0`, or
both; do not write a bare `masquerade` with no match.

## Concepts to teach

- Private (RFC 1918) addresses are not internet-routable, so replies to them
  cannot return — the concrete reason lesson 05's packet vanished.
- Source NAT: rewriting the source address of outgoing packets so many private
  clients share the box's upstream-facing address.
- `masquerade` versus static `snat`, tied explicitly to the dynamic `eth0`
  address from the address plan.
- Connection tracking (conntrack): the kernel remembers each flow and reverses
  the translation for replies automatically — no reverse rule needed.
- nftables NAT structure: an `ip` table, a chain of type `nat`, the `postrouting`
  hook and priority, and why postrouting (not prerouting) is correct for
  masquerade.
- Scoping NAT to the client subnet/interface, and why the management network must
  stay un-NATed.

## Constraints

- The learner writes every `nft` command and the persisted ruleset. The tutor
  explains, points, and reviews, but does not write the rules or hand over a
  finished ruleset to paste.
- The masquerade must be scoped to client traffic — source `192.168.4.0/24`,
  interface `eth0`, or both. A rule that would NAT the future management network
  is wrong and must be corrected before completion.
- Use `masquerade`, not a static `snat` to a hard-coded address, because the
  upstream address is dynamic.
- Do not add a reverse/return rule; conntrack handles replies. If the learner
  writes one, treat it as a teaching moment and have them remove it.
- IPv4 only. IPv6 is out of scope for this lesson (an optional path later covers
  routing IPv6).
- Add the rule live first and prove it works before persisting anything.

## Suggested progression

1. Restate the failure from lesson 05 in one line: the outbound packet left but
   no reply returned, because its source was a private `192.168.4.x` address.
   Establish that this lesson makes replies routable.
2. From the box, confirm the box itself reaches the internet (`ping -c1
   1.1.1.1`) and read the current `eth0` address (`ip -4 addr show eth0`). Note
   that this address was learned by DHCP and can change — motivate masquerade.
3. Live: create an `ip` NAT table and a `postrouting` chain of type `nat`, then
   add one `masquerade` rule matched to client traffic (source
   `192.168.4.0/24` and/or `oifname "eth0"`). Have the learner reason aloud about
   why `postrouting` and why the scope.
4. From a Wi-Fi client, prove it: `ping -c3 1.1.1.1` (raw connectivity), then a
   name-based test such as browsing or `curl` (proves DNS from lesson 04 plus NAT
   together). It should now work where it failed at the end of lesson 05.
5. Inspect conntrack on the box (`conntrack -L`, or read `/proc/net/nf_conntrack`
   if the `conntrack` tool is absent) and find the client's flow. Point out the
   recorded original and translated addresses — this is the state that returns the
   reply, and the reason no reverse rule is needed.
6. Optional teaching probe: temporarily reason about (or try) attaching the same
   rule to `prerouting`, or dropping the scope match, to see it fail or
   over-reach; then restore the correct rule.
7. Persist: author the NAT table and rule into an nftables ruleset file under
   `etc/`, then `make deploy`. (The complete ruleset and its enable-on-boot wiring
   are finalised alongside the firewall in lessons 08 and 09; here you are adding
   the NAT portion.)
8. Re-verify after deploy that a client still reaches the internet, so the
   persisted rule — not just the live one — is what is working.

## Completion conditions

- A Wi-Fi client reaches the internet through the box: `ping -c3 1.1.1.1`
  succeeds from the client, and a name-based request (browsing a page, or `curl`
  to a hostname) succeeds. This is the failure from lesson 05 now fixed.
- A `masquerade` rule is loaded in an `ip` NAT table on a `postrouting` chain of
  type `nat`, and it is scoped to client traffic (source `192.168.4.0/24` and/or
  `oifname "eth0"`) — not a blanket masquerade of all traffic.
- The rule uses `masquerade`, not a static `snat` to a hard-coded address.
- No self-authored reverse/return NAT rule exists; the learner can explain that
  conntrack returns the replies.
- The learner can explain, in their own words, what the source address is
  rewritten to and why, and what conntrack does for the reply.
- The rule is persisted into `etc/` and deployed with `make deploy`, and a client
  still reaches the internet after the deploy.
- `bash checks/06-nat.sh` passes. It confirms the masquerade rule is loaded on the
  box; and if `CLIENT_HOST` (and `CLIENT_USER`) are set in `board.env`, it also
  drives a real client to prove it reaches `1.1.1.1` end to end. Set
  `CLIENT_HOST`/`CLIENT_USER` in `board.env` to get that full client-side test
  rather than the rule-only check.

## On completion, persist

Record in the instance's `DESIGN.md`/`STATE.md`:

- NAT is live and persisted: client traffic from `192.168.4.0/24` is
  source-NATed out `eth0` with `masquerade`, on an `ip` table's `postrouting`
  chain (type `nat`).
- The masquerade is scoped to the client subnet/interface on purpose; the
  management network (lesson 07) is intentionally left un-NATed and must stay
  that way.
- The upstream `eth0` address is dynamic (DHCP); `masquerade` tracks it, which is
  why no static SNAT address is recorded.
- Clients now reach the internet end to end — milestone M2 is met. Note that the
  full nftables ruleset and its boot-time enabling are completed in lessons 08
  and 09; what is persisted here is the NAT portion.

## Optional deeper paths

- Watch conntrack live as a client generates traffic — `conntrack -E` for the
  event stream, or repeated `conntrack -L` — and see flows created, counted and
  expired. Good grounding for a later optional lesson on watching your own
  traffic.
- Inspect NAT rule counters (`nft list table ip <name>` with counters) to confirm
  packets are actually hitting the masquerade rule, a quick way to tell "rule
  present" from "rule working".
- Consider what IPv6 would need: clients with globally routable addresses would
  not be masqueraded at all, but routed and firewalled instead — motivation for
  the optional IPv6 path offered later.
