---
id: 09-making-it-survive-a-reboot
title: Making it survive a reboot
design_refs: [control-plane, recovery-invariant, platform]
validators: [reboot-survives]
supplies:
  - from: lessons/09-making-it-survive-a-reboot/checks/09-persist.sh
    to: checks/09-persist.sh
    describe: "Check for this lesson: the appliance units are enabled and will survive a reboot"
---

## Purpose

Turn the pile of live, hand-run configuration into an appliance that boots itself
back to a working state after a power cut, with nobody logged in.

Everything you have built works right now — the access point beacons, clients get
leases, traffic is NATed to the internet, the firewall drops what it should, the
management network is up, and the serial lifeline answers. But almost all of it
lives in the running kernel and in processes you started by hand. Pull the power
and it is gone: the addresses, the forwarding sysctl, the nftables ruleset, the
hostapd and dnsmasq processes. This lesson is where the appliance earns its name.
You will declare the links to `systemd-networkd`, turn hostapd, dnsmasq and
nftables into enabled systemd units, order them so they come up in the right
sequence without help, deploy the whole configuration with `make deploy`, then
reboot the board and prove it all returns on its own. This is milestone M3: after
this lesson the box behaves like an appliance, not like a session you are holding
open.

## Prerequisites

- Lessons 03 through 08 complete and working live: the AP (`03-bring-up-an-ap`),
  DHCP and DNS (`04-handing-out-addresses`), IP forwarding
  (`05-routing-between-two-links`), NAT (`06-nat-with-nftables`), the management
  network (`07-the-management-network`) and the firewall
  (`08-a-firewall-with-intent`). This lesson persists what those lessons taught;
  it does not teach new networking.
- Lesson 02 (`02-the-lifeline`) complete, with the serial console already
  persisted as a systemd unit. That unit is your safety net for this lesson: if a
  reboot comes up with the IP network broken, the Bluetooth serial console is how
  you get back in to fix it.
- The `etc/` config repo, `board.env`, the `checks/` scripts and the `Makefile`
  with a working `make deploy` (it copies `etc/` to the board and reloads the
  units). You have used `make deploy` in earlier lessons to persist single pieces;
  here you use it for the whole configuration.
- A way to reboot the board and reach it again afterwards — SSH over the network,
  the `bnep0` management address, or the serial lifeline.

## Learning objectives

- Explain what a *control plane* is in this context, and why the appliance must
  have exactly one — `systemd-networkd` — rather than mixing it with
  NetworkManager or `ifupdown`.
- Describe the intermittent, start-order failure mode that mixing control planes
  produces, and why an *intermittent* failure is worse than a consistent one.
- Write `systemd-networkd` `.network` files that realise the address plan: `eth0`
  as a DHCP client, `wlan0` with the static AP address `192.168.4.1/24`, and
  `bnep0` with the static management address `192.168.44.1/24`.
- Explain when a `.netdev` file is needed (virtual interfaces you create) and why
  this appliance's interfaces mostly do not need one.
- Order the units with `After=`, `Wants=`, `Requires=` and `BindsTo=` so nothing
  starts before what it depends on — dnsmasq not before `wlan0` has its address,
  the nftables ruleset loaded before forwarding carries traffic.
- Distinguish "running now" from "enabled to start at boot", and enable every unit
  the appliance needs.
- Verify the whole appliance returns after a real reboot, the serial lifeline
  included.

## Theory

**One control plane.** A *control plane* is whatever software owns the network
interfaces — decides which links come up, what addresses they carry, what routes
exist. Linux ships several that can do this job: `systemd-networkd`,
NetworkManager, the older `ifupdown` (`/etc/network/interfaces`), and interfaces
brought up by ad-hoc scripts. Any one of them, alone, works. The danger is having
more than one active at once, each believing it owns an interface. This appliance
picks **`systemd-networkd`** and only that. It is already present on Armbian, it
is declarative (you describe the desired state in files, not a sequence of
commands), and it integrates cleanly with the rest of systemd's ordering, which is
exactly what you need for unattended boot.

**Why mixing control planes is the worst kind of bug.** If two control planes both
try to configure `eth0`, the result depends on which one wins the race at boot —
and that race is not deterministic. One boot, `systemd-networkd` sets the DHCP
lease first and everything works; the next boot, a leftover NetworkManager or
`ifupdown` config brings the link up its own way, or tears down the address the
other just set, and the appliance comes up subtly wrong. Because it depends on
timing, it happens *sometimes*. An intermittent failure is worse than a consistent
one: a consistent failure you find immediately and fix; an intermittent one passes
your test, ships, and falls over in the field weeks later with no obvious cause.
The cure is not to debug the race — it is to make sure only one control plane is
ever active. That means finding and removing (or masking) any competing
configuration: NetworkManager managing these interfaces, `/etc/network/interfaces`
stanzas, or scripts from earlier lessons that brought interfaces up by hand.

**Declaring the links: `.network` files.** `systemd-networkd` reads unit files
from `/etc/systemd/network/`. A `.network` file matches one or more interfaces (by
name, MAC, type) and declares their layer-3 configuration. The address plan maps
onto three of them:

- `eth0` — the upstream. A `.network` that matches `eth0` and sets `DHCP=yes`, so
  the board is a DHCP *client* on whatever network you plug it into and learns its
  address, gateway and DNS from upstream.
- `wlan0` — the AP side. A `.network` that matches `wlan0` and assigns the static
  `Address=192.168.4.1/24`. `systemd-networkd` owns the address; hostapd owns the
  radio and the BSS. They are complementary: one runs the access point, the other
  gives the interface the gateway address your DHCP clients are told to use.
- `bnep0` — the management network from lesson 07. A `.network` that matches
  `bnep0` and assigns the static `Address=192.168.44.1/24`. `bnep0` is created by
  BlueZ when a PAN peer connects, so the file does not create the interface — it
  configures it the moment it appears.

**When you need a `.netdev`.** A `.network` *configures* an interface that exists;
a `.netdev` *creates* a virtual one — a bridge, a VLAN, a WireGuard tunnel. This
appliance's interfaces are all created elsewhere: `eth0` and `wlan0` by their
kernel drivers, `bnep0` by BlueZ. So the core of your work here is `.network`
files, and you likely need no `.netdev` at all. Know the distinction so you reach
for the right one if a later lesson adds a virtual interface.

**Ordering: units that wait for what they need.** Enabling a unit makes it start at
boot, but "at boot" is not an instant — units start in parallel, and a unit that
depends on something else must say so or it will start too early. systemd
expresses this with a few directives you should understand rather than copy:

- `After=` / `Before=` set *ordering* only: "start me after that unit has started".
  They say nothing about whether the other unit is even wanted.
- `Wants=` is a *weak* dependency: pull that unit in too, but if it fails, start me
  anyway.
- `Requires=` is a *strong* dependency: if that unit fails, do not start me.
- `BindsTo=` is stronger still: tie my life to that unit — if it stops later, stop
  me too. Useful for a service that is meaningless without a specific interface.

For this appliance the orderings that matter:

- **dnsmasq after the AP address exists.** dnsmasq listens on `192.168.4.1` and
  hands out leases on `wlan0`. If it starts before `systemd-networkd` has put the
  address on `wlan0`, it either fails to bind or binds to the wrong thing. Order
  dnsmasq after the network is configured (for example after
  `systemd-networkd-wait-online` or the relevant interface being up), so the
  address is there first.
- **nftables loaded before traffic is forwarded.** The firewall and NAT ruleset
  must be in place *before* the box starts forwarding client packets, or there is a
  window at boot where traffic flows unfiltered and un-NATed. Order the nftables
  unit early, before forwarding is carrying traffic, so the ruleset is never
  briefly absent.
- **hostapd needs `wlan0` present.** Order hostapd after the interface exists so it
  is not racing the driver.

**"Running" is not "enabled".** `systemctl start` runs a unit now;
`systemctl enable` marks it to start at every boot. They are independent, and this
is the single most common way persistence silently fails: a unit you started by
hand works perfectly all through testing, then never comes back after the reboot
because you never enabled it. Every unit the appliance needs —
`systemd-networkd`, hostapd, dnsmasq, and the nftables loader — must be *enabled*,
not merely running. `systemctl is-enabled <unit>` tells you the truth for each.

**The recovery invariant still holds.** The serial lifeline from lesson 02 is a
getty over a Bluetooth serial (SPP/RFCOMM) link — it carries bytes, not IP, and it
does not depend on `systemd-networkd`, the addresses, or the firewall. That is
exactly why it is your safety net for this lesson. But a safety net you never test
is a guess: the reboot in this lesson is also where you confirm the lifeline unit
comes back on its own and still lets you in with the whole IP network stripped
away. If the reboot brings the appliance up broken, the lifeline is how you get in
to read the logs and fix it — so verify it survives too, not just the AP and NAT.

## Concepts to teach

- The control plane: the software that owns the interfaces, and why the appliance
  commits to exactly one (`systemd-networkd`), not NetworkManager or `ifupdown`.
- The start-order race that mixing control planes causes, and why an intermittent,
  timing-dependent failure is the worst failure mode to ship.
- `systemd-networkd` `.network` files realising the address plan: `eth0` DHCP
  client, `wlan0` static `192.168.4.1/24`, `bnep0` static `192.168.44.1/24`.
- `.network` (configure an existing interface) versus `.netdev` (create a virtual
  one), and why this appliance needs mostly the former.
- Unit ordering and dependency semantics: `After=`/`Before=` (ordering only),
  `Wants=` (weak), `Requires=` (strong), `BindsTo=` (bound lifetime) — and the two
  concrete orderings that matter (dnsmasq after the AP address; nftables before
  forwarding).
- `systemctl enable` versus `systemctl start`: start now versus come back at boot,
  and that forgetting to enable is how persistence silently fails.
- The recovery invariant: the serial lifeline is IP-independent and must survive
  the reboot too; verify it, do not assume it.

## Constraints

- The learner writes every `.network` file and every unit change themselves. The
  tutor explains the semantics, points at what is missing, and reviews — but does
  not write the networkd files or hand over finished unit files to paste.
- `systemd-networkd` is the sole control plane. Any competing configuration —
  NetworkManager managing these interfaces, `/etc/network/interfaces` stanzas,
  ad-hoc bring-up scripts from earlier lessons — must be found and removed or
  masked before completion. A `.network` file fighting a leftover live/manual
  configuration for the same interface is a defect to fix, not to leave.
- The three interfaces must follow the address plan exactly: `eth0` DHCP client,
  `wlan0` `192.168.4.1/24`, `bnep0` `192.168.44.1/24`. No hard-coded upstream
  address on `eth0`.
- Every unit the appliance needs must be *enabled*, not just running:
  `systemd-networkd`, hostapd, dnsmasq, nftables, and the lifeline getty.
- The persisted configuration is deployed through `etc/` and `make deploy`. Do not
  hand-edit files directly on the board and call it done — the repo is the source
  of truth, and a reboot must reproduce it from what `make deploy` installed.
- The serial lifeline must come up after reboot and remain IP-independent. Verify
  it; do not assume it survived.
- IPv4 only.

## Suggested progression

1. Frame the milestone: right now everything is live and would die on a power cut.
   The goal is an unattended boot to a fully working appliance. Name the pieces
   that are currently only live — addresses, `ip_forward`, the nftables ruleset,
   the hostapd/dnsmasq processes.
2. Audit the current control plane. Have the learner find what is managing the
   interfaces today: `networkctl list` and `networkctl status <iface>`, whether
   NetworkManager is installed and active, whether `/etc/network/interfaces` has
   stanzas, and which earlier-lesson steps brought interfaces up by hand. Decide
   what must be removed or masked so only `systemd-networkd` remains.
3. Author the `.network` files under `etc/` (mirroring `/etc/systemd/network/`):
   `eth0` with `DHCP=yes`; `wlan0` with static `192.168.4.1/24`; `bnep0` with
   static `192.168.44.1/24`. Have the learner tie each back to the address plan
   and explain why `eth0` is a client while the other two are static.
4. Make hostapd, dnsmasq and nftables into managed, enabled units, folding in the
   configuration authored live in lessons 03, 04, 06 and 08. Have the learner add
   the ordering: dnsmasq after the AP address is configured, nftables loaded
   before forwarding carries traffic, hostapd after `wlan0` exists — reasoning
   aloud about `After=` versus `Requires=` versus `BindsTo=` for each.
5. Persist the forwarding sysctl properly (a `sysctl.d` drop-in under `etc/`) so
   `ip_forward` is on at boot rather than set by hand.
6. Enable everything: walk `systemctl is-enabled` across `systemd-networkd`,
   hostapd, dnsmasq, nftables and the lifeline getty, and enable any that are only
   running. This is the step most likely to be missed.
7. Deploy the whole configuration with `make deploy` and reconcile the running
   system without rebooting yet: `networkctl status` for the addresses,
   `systemctl status` for the units, a client still reaching the internet.
8. Run `bash checks/09-persist.sh` to confirm the units are enabled and the
   `.network` files are present — the pre-flight before the real test.
9. Instructive failures to surface if they have not appeared: a `.network` file
   fighting a leftover manual address on the same interface; dnsmasq ordered
   before the AP address and failing to bind; the nftables ruleset absent for a
   window at boot; a unit that works now but was never enabled.
10. The real test: reboot the board with nobody intervening. When it returns,
    re-run checks 03, 04 and 06 to prove the AP beacons, DHCP hands out leases and
    NAT works — from a cold boot, not from your live session. Then confirm the
    serial lifeline came back by connecting over it.

## Completion conditions

- `bash checks/09-persist.sh` passes: `systemd-networkd`, hostapd, dnsmasq and
  nftables are all *enabled* (not merely running), and `.network` files are present
  under `/etc/systemd/network/` on the board.
- `systemd-networkd` is the only active control plane; no NetworkManager,
  `ifupdown`, or ad-hoc script is also configuring `eth0`, `wlan0` or `bnep0`. The
  learner can point at what they removed or masked.
- The `.network` files realise the address plan: `eth0` is a DHCP client, `wlan0`
  carries `192.168.4.1/24`, `bnep0` carries `192.168.44.1/24` — confirmable with
  `networkctl status <iface>`.
- The configuration was deployed through `etc/` with `make deploy`; the working
  state on the board is what the repo installs, not a hand-edit.
- After an **actual reboot** with no intervention, the appliance returns fully:
  re-running `bash checks/03-ap.sh`, `bash checks/04-lease.sh` and
  `bash checks/06-nat.sh` all pass — the AP beacons, a client gets a
  `192.168.4.0/24` lease with the box as gateway/resolver, and a client reaches
  the internet through NAT.
- After the same reboot, the serial lifeline is up on its own and you can log in
  over it, proving the recovery path is IP-independent and persisted.
- The learner can explain, in their own words, why one control plane matters and
  what start-order race mixing them would cause.

## On completion, persist

Record in the instance's `DESIGN.md`/`STATE.md`:

- The appliance is fully persisted under `systemd-networkd` as the single control
  plane: `eth0` DHCP client, `wlan0` static `192.168.4.1/24`, `bnep0` static
  `192.168.44.1/24`, all declared in `.network` files under `etc/`.
- hostapd, dnsmasq and nftables run as enabled systemd units, with `ip_forward`
  persisted via a `sysctl.d` drop-in.
- The unit ordering decisions made and why: dnsmasq after `wlan0` has its address
  (so it can bind `192.168.4.1`), the nftables ruleset loaded before forwarding
  carries traffic (so there is no unfiltered/un-NATed window at boot), hostapd
  after `wlan0` exists — and which `After=`/`Requires=`/`BindsTo=` was used for
  each.
- Any competing control-plane configuration that was removed or masked
  (NetworkManager, `ifupdown`, earlier bring-up scripts), so a future session does
  not reintroduce the race.
- A cold reboot brings the whole appliance back unattended — AP, DHCP/DNS, NAT and
  firewall — and the serial lifeline returns with it and remains IP-independent.
  This is milestone M3: the box behaves like an appliance.

## Optional deeper paths

- Read the boot ordering the units actually produced:
  `systemd-analyze critical-chain` and `systemd-analyze plot > boot.svg` show what
  started when and where the waits were, turning your `After=`/`Wants=` choices
  into a picture.
- Watch `systemd-networkd-wait-online` and `networkctl` decide when a link counts
  as "online", and consider what "online" should mean for an appliance whose
  upstream may be absent at boot — a direct lead into lesson 10, upstream
  detection.
- Consider what still would not survive a failure short of a clean reboot: an
  interface that flaps, a DHCP lease that never renews, a unit that crashes and is
  not set to restart. Look at `Restart=` and watchdog options as the next level of
  robustness beyond "comes back after a reboot".
