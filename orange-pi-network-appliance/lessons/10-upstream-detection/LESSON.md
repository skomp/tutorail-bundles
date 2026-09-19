---
id: 10-upstream-detection
title: Upstream detection
design_refs: [control-plane, interface-roles, platform]
validators: [upstream-follows]
supplies:
  - from: lessons/10-upstream-detection/checks/10-upstream.sh
    to: checks/10-upstream.sh
    describe: "Check for this lesson: eth0 is a networkd DHCP client and carrier changes are reacted to"
---

## Purpose

Make the appliance follow its Ethernet automatically — unplug `eth0` and replug
it into a different network, and the upstream re-establishes itself while Wi-Fi
clients keep reaching the internet, with no login and no manual step.

After lesson 09 the appliance is complete and survives a reboot, but the upstream
it uses is still whatever was plugged in when it booted. Move it to a different
LAN, or pull the cable and put it back, and nothing reacts on its own: the new
DHCP lease may arrive, but the pieces that depend on the old lease do not
re-align by themselves, and a client can be left stranded until you intervene.
This lesson closes that gap. You will watch the kernel's link-carrier events as
they happen, then author a small reactor that fires on them and re-establishes
routing and NAT for the new upstream. This is the headline feature of the
appliance, and it comes last because it only means anything once there is a
working routed box to keep working.

## Prerequisites

- Lesson 09 (`09-making-it-survive-a-reboot`) complete: the whole appliance is
  persisted under `systemd-networkd` and comes back after a reboot on its own.
  `networkd` owns the links; this lesson reacts to `networkd`'s view of them and
  must not undo that persistence.
- Lesson 06 (`06-nat-with-nftables`) complete: client traffic from
  `192.168.4.0/24` is source-NATed out `eth0` with `masquerade`. You will lean on
  the fact that `masquerade` follows `eth0`'s current address, and you will handle
  the one thing it does not clean up on its own.
- Lesson 05 (`05-routing-between-two-links`) complete: forwarding is on and the
  default route toward the internet is learned from `eth0`'s DHCP lease.
- Lesson 02 (`02-the-lifeline`) available: you have the Bluetooth serial way onto
  the box that does not depend on its networking. You will deliberately unplug the
  upstream in this lesson; keep the lifeline within reach.
- `eth0` is a `systemd-networkd`-managed DHCP client with a working upstream, and
  a Wi-Fi client currently reaches the internet through the box.

## Learning objectives

- Distinguish a link's *carrier* (does the wire have a live physical connection)
  from its *operational state* (`operstate`: `down`, `no-carrier`, `dormant`,
  `up`) and from its *administrative* state (whether it is set up at all).
- Explain what a hotplug / link event is: the kernel noticing carrier appearing
  or disappearing and telling userspace, versus polling for it.
- Observe those events live with `ip monitor link`, `ip -4 monitor address`, and
  `networkctl` / `networkctl status eth0`, and read the state transitions during
  an unplug and a replug.
- Explain why a change of upstream needs action even though `networkd` re-runs
  DHCP: the default route follows the new lease, `masquerade` follows the new
  `eth0` address on its own, but connection-tracking entries created against the
  *old* upstream survive and can leave clients briefly broken until flushed.
- Choose and describe an event-driven reactor built on `networkd` — either a
  `networkd-dispatcher` hook keyed on the `routable` and `off` states, or a small
  `systemd` unit triggered by the link event — and say why this is not a polling
  loop and not NetworkManager.
- Identify the correct event to act on (carrier / routable, not merely an address
  change) and explain the instructive failures of acting on the wrong one.
- Author the reactor into `etc/`, deploy it, and prove the upstream follows a real
  unplug-and-replug.

## Theory

**Carrier, operstate, and why "the cable is in" is a kernel-level fact.** Every
network link has a *carrier*: the physical-layer signal that says a live peer is
on the other end of the wire. When you unplug `eth0`, the NIC loses carrier and
the kernel marks the link `NO-CARRIER`; plug it back and carrier returns. The
kernel also keeps an *operational state* for the link, `operstate`, which you can
read at `/sys/class/net/eth0/operstate` and see in `ip link` — it moves through
values like `down`, `no-carrier`, `dormant`, and `up`. This is distinct from the
*administrative* state (whether anything has brought the interface up at all): a
link can be administratively up but have no carrier because nothing is plugged in.
Upstream detection is, at bottom, reacting to carrier transitions on `eth0`.

**Link events: the kernel tells you, you do not poll.** Rather than checking
`operstate` in a loop, you can subscribe to the kernel's netlink notifications: it
emits an event the instant a link's carrier or state changes. `ip monitor link`
prints those link events as they arrive; `ip -4 monitor address` prints
address-add and address-remove events; `networkctl` shows `networkd`'s
interpretation of the same underlying state. Watching these while you physically
unplug and replug the cable is the whole point of the live phase: you see
`NO-CARRIER` appear on unplug, then on replug carrier return, DHCP re-run, a new
address arrive, and `networkd` move `eth0` back to `routable`.

**Why `networkd` owns this, and what it does for you automatically.** Per the
control-plane design, `systemd-networkd` owns the links; you build the reactor on
top of it rather than reaching for NetworkManager. When carrier returns on `eth0`,
`networkd` re-runs the DHCP client on its own, obtains a fresh lease, and installs
the new address and the new default route that came with it. So the *default
route* follows the new upstream without your help. And because lesson 06 used
`masquerade` rather than a static SNAT, the NAT rule rewrites to *whatever address
`eth0` has right now* — so NAT also follows the new address without a rule change.
Two of the three moving parts realign themselves.

**The part that does not fix itself: stale conntrack.** The third part is
connection tracking. When the old upstream was live, the kernel recorded a
conntrack entry for each client flow, remembering the translation it applied
against the *old* `eth0` address. When the upstream flips to a new network with a
new address, those old entries are now wrong: replies for them will never come
back, and until each stale entry expires on its own, a client's existing
connections can hang. The fix is to *flush* the relevant conntrack entries when
the upstream changes, so clients rebuild fresh flows against the new upstream —
for example `conntrack -F` to flush the table, or a more targeted flush of the
entries tied to the old address if you want to be surgical. Deciding to flush, and
doing it at the right moment, is the substantive work of the reactor.

**Building the reactor: two shapes, same job.** You need something that runs the
moment `eth0`'s upstream is (re-)established and does the re-alignment step
(principally the conntrack flush, plus any re-assertion your setup needs). Two
idiomatic shapes sit on top of `networkd`:

- *`networkd-dispatcher`.* This daemon watches `networkd` and runs your executable
  scripts from state-named directories — a hook in `routable.d/` runs when a link
  becomes routable, a hook in `off.d/` runs when it goes down. You drop a small
  script keyed on `eth0` reaching `routable`, and it does the flush. This is the
  most direct fit and is `networkd`-native.
- *A small `systemd` unit triggered by the link event.* Alternatively, wire a
  oneshot unit that runs the re-alignment, triggered when `eth0` comes up — for
  example `BindsTo=`/`After=` the `sys-subsystem-net-devices-eth0.device` unit, or
  driven from a networkd hook. Same outcome, more moving parts, useful if you want
  the action expressed as a first-class unit with its own logs and status.

Either way the reactor is event-driven — it sleeps until the kernel says the link
changed — not a timer polling `operstate`.

**Act on the right event.** The most common instructive failure here is reacting
to the wrong signal. If you fire only on an *address-change* event you can miss
cases, or fire before `networkd` has finished bringing the link to `routable`; if
you fire on carrier-up too early, DHCP may not have a lease yet and there is
nothing coherent to realign. Keying on `networkd`'s `routable` state (the link is
up *and* has a usable address and route) is the reliable trigger for
re-establishing the upstream, and `off` for tearing down. Two further failures to
watch for: not doing the re-alignment at all, so the default route and NAT are
fine but old client connections hang on stale conntrack until they time out; and a
reactor that itself perturbs `networkd`'s ownership of the link (bringing
interfaces up or down by hand) and fights the persistence you built in lesson 09.

## Concepts to teach

- Carrier versus `operstate` versus administrative state — three different
  questions about one link, and which one "the cable was unplugged" changes.
- Link (hotplug) events as kernel netlink notifications, and event-driven reaction
  versus polling `operstate` in a loop.
- Observing events live: `ip monitor link`, `ip -4 monitor address`, and
  `networkctl` / `networkctl status eth0`, and reading the transitions during an
  unplug/replug.
- `systemd-networkd` re-running DHCP on carrier return: the new address and the
  new default route arrive on their own — control-plane ownership in action, and
  why this is not NetworkManager.
- Why `masquerade` (lesson 06) needs no change when the upstream address changes,
  and, in contrast, why stale conntrack entries against the old upstream do need
  flushing.
- The reactor mechanism: a `networkd-dispatcher` hook on `routable`/`off`, or a
  small link-triggered `systemd` unit, and the trade-off between them.
- Choosing the correct trigger (`routable`, not a bare address-change or an early
  carrier-up), and the failures of choosing wrong.

## Constraints

- The learner writes the reactor — the dispatcher hook script or the `systemd`
  unit, and the conntrack-flush command inside it. The tutor explains, points at
  events and state, and reviews, but does not write the hook or hand over a
  finished script to paste.
- Build on `systemd-networkd` plus an event mechanism (`networkd-dispatcher` or a
  link-triggered unit). Do not introduce NetworkManager, and do not replace
  `networkd`'s ownership of the links.
- Must not break the reboot persistence from lesson 09. The reactor is added
  *alongside* the persisted configuration; after this lesson the box must still
  come back correctly on a cold boot.
- The reactor must not itself bring `eth0` up or down or otherwise fight
  `networkd`; it reacts to link state, it does not drive it.
- Trigger on the upstream becoming routable (and going off), not on a bare
  address-change event or a premature carrier-up.
- Prove it with a real physical unplug/replug (or a move to a different LAN), not
  only by reading configuration.
- IPv4 only. IPv6 upstream handling is out of scope (an optional path covers
  routing IPv6).

## Suggested progression

1. Frame the gap in one line: the appliance survives a reboot, but its upstream is
   still frozen to whatever was plugged in at boot. This lesson makes it follow
   the cable.
2. Read the current state before touching anything: `networkctl status eth0`,
   `ip link show eth0` (note `operstate`), `cat /sys/class/net/eth0/operstate`,
   the current `eth0` address and default route (`ip -4 addr show eth0`,
   `ip route show default`). Confirm a Wi-Fi client currently reaches the
   internet.
3. Live, watch the events. In one session run `ip monitor link` (and, in another,
   `ip -4 monitor address` and/or `networkctl` / `journalctl -fu
   systemd-networkd`). Physically unplug `eth0` and read the `NO-CARRIER` /
   `off` transition; replug it and read carrier return, DHCP re-running, a new
   address arriving, and `networkd` reaching `routable`. Have the learner narrate
   which line is which.
4. During that replug, expose the problem: check whether a client's *existing*
   connections hang while its *new* connections work, and inspect conntrack
   (`conntrack -L`) to find entries still referencing the old upstream address.
   Establish that the default route and `masquerade` realigned themselves but
   stale conntrack did not.
5. Decide the trigger. Reason about why `routable` (link up with address and
   route) is the right moment and why an early carrier-up or a bare
   address-change is not. Reach the choice of mechanism: a `networkd-dispatcher`
   hook, or a link-triggered `systemd` unit.
6. Author the reactor live (or in a scratch location first): a small script/unit
   that, when `eth0` becomes routable, flushes the stale conntrack entries
   (`conntrack -F`, or a targeted flush) and re-asserts anything the setup needs.
   Keep it idempotent and scoped to `eth0`.
7. Prove it live: with the reactor active, unplug and replug `eth0` (or move it to
   a different LAN with a different subnet) and confirm the upstream
   re-establishes and a Wi-Fi client keeps reaching the internet across the flip,
   including existing-connection recovery, not just new connections.
8. Optional instructive probe: temporarily key the reactor on the wrong event (an
   early carrier-up, or address-change only), see it misfire or miss, then restore
   the `routable` trigger.
9. Persist: author the dispatcher hook or the `systemd` unit into `etc/` and
   `make deploy`, so the reactor is part of the box's configuration and survives a
   reboot. Re-verify after deploy.

## Completion conditions

- With the reactor in place, a real unplug-and-replug of `eth0` (or a move to a
  different LAN, ideally on a different subnet) results in the upstream
  re-establishing automatically: `eth0` obtains a fresh lease, the default route
  follows it, and a Wi-Fi client keeps reaching the internet across the flip —
  including connections that were open before the flip, once stale conntrack is
  flushed.
- `eth0` remains a `systemd-networkd`-managed DHCP client; `networkd` still owns
  the link and no NetworkManager was introduced.
- A carrier-reacting mechanism is present and enabled — either `networkd-dispatcher`
  with a hook keyed on `eth0` reaching `routable` (and going `off`), or a
  link-triggered `systemd` unit — and it is triggered by the upstream becoming
  routable, not by a bare address-change or a premature carrier-up.
- The reactor flushes stale conntrack entries on upstream change (e.g.
  `conntrack -F` or a targeted flush), and the learner can explain why the default
  route and `masquerade` realign on their own but conntrack does not.
- The reactor does not bring `eth0` up or down itself and does not undo lesson
  09's persistence; the box still comes back correctly on a cold boot.
- The reactor is persisted into `etc/` and deployed with `make deploy`, and the
  upstream still follows a replug after the deploy.
- `bash checks/10-upstream.sh` passes. It confirms `eth0` is a `networkd` DHCP
  client and that a carrier-reacting mechanism — `networkd-dispatcher` or a custom
  upstream unit — is present. The check cannot pull a cable for you, so after it
  passes, prove it for real by physically unplugging and replugging `eth0` and
  watching a client stay online.

## On completion, persist

Record in the instance's `DESIGN.md`/`STATE.md`:

- Upstream detection is in place: `eth0`'s upstream now follows the cable
  automatically, keyed on `networkd`'s `routable`/`off` states.
- The mechanism chosen — `networkd-dispatcher` hook, or a link-triggered `systemd`
  unit — and where its script/unit lives in `etc/`.
- The conntrack-flush handling on upstream change (which flush, and why it is
  needed while the default route and `masquerade` realign on their own).
- That the reactor is additive to lesson 09's persistence and does not drive the
  link itself, so cold-boot behaviour is unchanged.
- That the appliance is now complete: it routes and NATs a Wi-Fi AP from its
  Ethernet upstream, is reachable over Bluetooth, survives a reboot, and follows
  its upstream automatically — the headline feature is met.

## Optional deeper paths

- Make the flush surgical: instead of `conntrack -F` (which drops every tracked
  flow), target only entries bound to the old upstream address, and reason about
  the trade-off between a clean sweep and disrupting unrelated flows.
- Handle the `off` transition explicitly: have the reactor react when `eth0` goes
  down (log it, or take a defined action) rather than only on `routable`, and
  consider what the appliance should present to clients while there is no
  upstream at all.
- Watch the reactor work in production: follow `journalctl -fu
  networkd-dispatcher` (or your unit) across a flip to confirm it fired exactly
  once and at the right moment, distinguishing "hook present" from "hook working".
- Consider multiple or changing upstream media — for example an alternative
  upstream link — and how the `routable`/`off` logic would generalise to choosing
  between upstreams, as groundwork for a more capable appliance.
- Consider what IPv6 upstream detection would add: prefixes learned by SLAAC/DHCPv6
  on carrier return behave differently from a single IPv4 lease — motivation for
  the optional IPv6 path.
