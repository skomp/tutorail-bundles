---
id: 07-the-management-network
title: The management network
design_refs: [interface-roles, address-plan, recovery-invariant, platform]
validators: [mgmt-reachable]
supplies:
  - from: lessons/07-the-management-network/checks/07-mgmt.sh
    to: checks/07-mgmt.sh
    describe: "Check for this lesson: the Bluetooth management network is up and not NATed"
---

## Purpose

The appliance now serves clients, but you still administer it over the paths clients use or
over the SSH-on-Ethernet you started with — so in this lesson you build a separate management
network over Bluetooth PAN, a third L3 interface (`bnep0` on `192.168.44.0/24`) that is
deliberately kept off the client network: not NATed, and (in lesson 08) trusted. The lesson is
the contrast between a client interface and a management interface.

## Prerequisites

An SSH session on the board and a working `board.env` (lesson `00-find-the-board`). The
Bluetooth serial console from lesson `02-the-lifeline` working, because this lesson changes
Bluetooth configuration and you want the IP-independent way back available while you do it. A
client-facing Wi-Fi network that works end to end: `wlan0` on `192.168.4.1/24` (lesson
`03-bring-up-an-ap`), DHCP and DNS for clients (lesson `04-handing-out-addresses`), forwarding
between links (lesson `05-routing-between-two-links`), and NAT so clients reach the internet
(lesson `06-nat-with-nftables`). You need the lesson-06 masquerade rule in front of you,
because part of this lesson is proving the management subnet is *not* in it. The `bluez` stack
with PAN/NAP support on the board — the `bluetooth`/`bluez` service and a way to serve the NAP
role (`bt-network`, or the equivalent your `bluez` version exposes); install it if it is absent
(`apt install bluez`, plus whatever your image ships PAN in — the package manager is the one
prerequisite that adapts, `#platform`). A Bluetooth host to administer from — your laptop —
with a Bluetooth PAN client (a NAP consumer) available on it.

## Learning objectives

- Distinguish Bluetooth **PAN** (a network link carrying Ethernet frames, giving you `bnep0`)
  from **SPP/RFCOMM** (the serial byte stream of the lesson-02 lifeline), and explain why they
  are different profiles for different jobs
- Explain the **NAP** (Network Access Point) role in PAN and what serving it does on the board
- Treat `bnep0` as an ordinary L3 interface — address it and reason about it exactly as you do
  `wlan0` or the Ethernet link
- Bring up the PAN NAP live, give `bnep0` its management address `192.168.44.1/24`, connect
  your admin host, and SSH to the appliance over PAN
- Explain why the management subnet must **not** be masqueraded — it is not a client of the
  internet, it is how you reach the box — and confirm it is absent from the lesson-06 rule
- Explain why administration belongs on its own interface with its own trust level, separate
  from the client interface
- State precisely why PAN is **convenience** management and **not** the lifeline: `bnep0` is an
  IP interface, so it depends on the very IP stack the serial console is designed to outlive
- Persist the management network so it returns on boot

## Theory

You already met Bluetooth **profiles** in lesson 02: one radio, many agreed link shapes. Two of
them matter for this appliance and they do completely different things. The **Serial Port
Profile (SPP)** carries an undifferentiated byte stream and appears on Linux as an RFCOMM
character device (`/dev/rfcomm0`); that is the lifeline console, and it never touches IP.
**PAN** (Personal Area Network) is the other one, and it is what this lesson uses. PAN carries
**Ethernet frames** over Bluetooth and presents them as a network interface — `bnep0`
("Bluetooth Network Encapsulation Protocol") — that you give an IP address, route through, and
firewall like any other L3 interface. SPP gives you a serial line; PAN gives you a network. Do
not blur them: they solve different problems, and only one of them is the recovery path.

PAN defines roles. The **NAP** (Network Access Point) is the node that offers network access to
others — it is the "server" end of a PAN. Your appliance serves the NAP role, your laptop is
the PAN client (a PANU) that connects to it, and when it does, both ends get a `bnep0`
interface bridging the two. On the board, serving NAP is what `bt-network` (or your `bluez`
version's equivalent) does once the controller is powered, paired and trusted with the admin
host.

The important idea is that `bnep0` is **nothing special** at layer 3. It is an interface with a
MAC and, once you give it one, an IP address; you can `ip addr` it, ping across it, route to it,
and match on it in nftables exactly as you would `wlan0`. From the plan (`#address-plan`,
`#interface-roles`) it takes the **management** subnet: `bnep0` is `192.168.44.1/24`, entirely
separate from the client subnet `192.168.4.0/24` on `wlan0`. Two subnets, two interfaces, two
jobs.

And here is the whole point of the lesson — the **contrast in roles**. `wlan0` is the *client*
interface: the devices on it are consumers of the internet, so their traffic is masqueraded out
the upstream (lesson 06) and, in lesson 08, they are treated as untrusted — box-input from them
is limited. `bnep0` is the *management* interface: it exists so *you* can reach the box, not so
the box can reach the internet on its behalf. That flips both decisions. It must **not** be
masqueraded — masquerading rewrites the source address of traffic *going out to the internet*,
and the management host is not going to the internet, it is going to the appliance itself; a
management subnet in the masquerade rule is a category error, not merely a redundant line. And
in lesson 08 it is the *trusted* interface: administration (SSH to the box) is allowed from
`bnep0` and limited from `wlan0`. Different interface, different trust level, on purpose. That
is why you build administration on its own link instead of sharing the client's.

Now the distinction you must not get wrong. It is tempting to think of this Bluetooth PAN link
as "the way back in when the network breaks" — but it is **not the lifeline**, and mistaking it
for one is dangerous. `bnep0` is an IP interface. Reaching the appliance over PAN needs the IP
stack up, `bnep0` addressed, the route present, and (after lesson 08) the firewall allowing it —
exactly the things a bad route or a wrong rule can take away. The real lifeline is the lesson-02
**serial** console (SPP/RFCOMM), whose chain radio → SPP → RFCOMM → getty → shell consults no
address, route, interface or firewall rule at all. PAN is **convenience** management — a
comfortable network path for day-to-day administration when the IP stack is healthy. When it is
not, PAN goes down with it, and the serial console is what you fall back to. Keep the two
Bluetooth links straight: same radio, two profiles, and only the serial one is the recovery
invariant (`#recovery-invariant`).

## Concepts to teach

Bluetooth PAN as a profile that carries Ethernet frames and yields the `bnep0` network
interface, versus SPP/RFCOMM as the serial byte stream of the lesson-02 lifeline — two profiles,
two jobs, on one radio; the NAP (Network Access Point) role as the node serving network access,
and PANU as the client that connects to it; `bnep0` as an ordinary L3 interface you address and
route like `wlan0` or Ethernet; the management subnet `192.168.44.0/24` and `bnep0` at
`192.168.44.1/24` from the plan, distinct from the client subnet; the client-versus-management
role contrast (`#interface-roles`) — `wlan0` client/NATed/untrusted, `bnep0`
management/not-NATed/trusted; what masquerading actually does (rewrites source on internet-bound
traffic) and therefore why the management subnet must never be in the masquerade rule; why
administration belongs on its own interface at its own trust level; and the sharp distinction
that PAN is IP-dependent convenience management, **not** the recovery path — the serial console
of lesson 02 is the lifeline because it is IP-independent (`#recovery-invariant`).

## Constraints

- You write every command and every config yourself. The tutor states objectives and checks; it
  does not write your configuration.
- The management subnet `192.168.44.0/24` is **not NATed**. It must not appear in any masquerade
  or source-NAT rule (`#interface-roles`). You will confirm this against the lesson-06 ruleset,
  not assume it.
- `bnep0` gets exactly `192.168.44.1/24`, and `wlan0` keeps `192.168.4.1/24` — the values the
  course depends on (`#address-plan`). Two separate subnets; do not overlap or renumber them.
- IPv4 only (`#address-plan`). Do not configure IPv6 on `bnep0`.
- The client and management roles stay separate: a Wi-Fi client must not be able to reach the
  appliance's administration. (The firewall that enforces this fully is lesson 08; here you
  build the separate interface it will act on and confirm the separation as it stands.)
- Do **not** treat PAN as the lifeline or let it replace the serial console
  (`#recovery-invariant`). Keep the lesson-02 console working; PAN is convenience only.
- Persist into the `etc/` repo and deploy with `make deploy`. The management network must be
  reproducible from the repo and survive a reboot, not live only in your shell history.

## Suggested progression

Do it live first, watch it work, then persist it. Keep the lesson-02 serial console available
throughout — you are changing Bluetooth, and it is your safety net if you disturb it.

Confirm the ground. `rfkill list` shows Bluetooth unblocked; in `bluetoothctl`, `show` reports
the controller present and powered. Confirm the controller is paired and trusted with your admin
laptop (from lesson 02 it may already be) — `paired-devices` and `info <MAC>` — and if not,
pair and `trust <MAC>` it so it can reconnect without a fresh agent confirmation each time.

Serve the NAP role on the board, live. Bring up PAN as a Network Access Point with `bt-network`
(for example `bt-network -s nap <bridge-or-config>`, or the NAP mechanism your `bluez` version
exposes) so the appliance offers network access over Bluetooth. From your laptop, connect to it
as a PAN client. When it connects, a `bnep0` interface appears on the board — confirm with
`ip link show bnep0`. If no `bnep0` appears, the NAP is not actually being served or the client
did not connect as PANU; read the `bluez` logs before going further.

Address `bnep0` from the plan: `ip addr add 192.168.44.1/24 dev bnep0`, then `ip link set bnep0
up`, and confirm with `ip addr show bnep0`. Give the admin end of the link an address in the
same subnet (statically on the laptop, or however your PAN client is set up) and prove L3 works
across it: ping `192.168.44.1` from the laptop.

Now the payoff: SSH to the appliance over PAN. From the laptop, `ssh <user>@192.168.44.1` and
confirm you get a shell on the board over Bluetooth, with Ethernet and Wi-Fi playing no part in
that path. This is the convenience management link working.

Confirm the management subnet is **excluded from NAT**. Read the live ruleset —
`nft list ruleset` — and find the lesson-06 masquerade rule. It should masquerade the *client*
subnet `192.168.4.0/24` out the upstream and say nothing about `192.168.44.0/24`. If the
management subnet is caught by the rule (an over-broad match on the upstream interface, or a
missing source qualifier), fix the rule so it only masquerades client traffic — the management
subnet is not a client of the internet and must not be rewritten. Verify by hand: traffic from
the management host to the box is not source-NATed.

Prove the roles are separate. From a Wi-Fi client on `192.168.4.0/24`, confirm it cannot reach
the appliance's administration on the management subnet — it has no route to `192.168.44.0/24`
and, as lesson 08 will make airtight, must not be allowed to reach admin there. Note plainly
that full enforcement is the firewall's job in lesson 08; here you are confirming the separation
that the separate interface already gives you.

Say out loud, or write down, why this PAN link is **not** the lifeline: it needs IP up, `bnep0`
addressed, the route present, and (soon) the firewall permitting it — all the things the serial
console deliberately does without. If you are unsure, drop the serial console mentally into the
same failure and see which survives.

With it working live, persist it. Author into `etc/` whatever your setup needs to serve the NAP
role, bring `bnep0` up, and give it `192.168.44.1/24` on boot — a small service that starts the
NAP, and `bnep0`'s address configured through systemd-networkd (`#platform`, and the full
ordering is finalized in lesson `09-making-it-survive-a-reboot`). Make sure your persisted NAT
config still excludes `192.168.44.0/24`. Deploy with `make deploy` and reconnect from the laptop
to prove the management network returns.

## Completion conditions

- You reach the appliance's administration over `bnep0` (Bluetooth PAN): from your admin host
  you SSH to `192.168.44.1` and get a shell on the board, over Bluetooth, with no Ethernet or
  Wi-Fi in that path. This by-hand test is the proof the management link works.
- `ip addr show bnep0` shows `192.168.44.1/24` on `bnep0`, and `wlan0` still carries
  `192.168.4.1/24`.
- The management subnet `192.168.44.0/24` does **not** appear in any masquerade or source-NAT
  rule — confirm by reading `nft list ruleset` and checking the lesson-06 masquerade matches
  only the client subnet.
- A Wi-Fi client on `192.168.4.0/24` provably cannot reach the appliance's administration on the
  management subnet — confirm by hand from a real client (no route to `192.168.44.0/24`, no
  admin access there).
- You can state, in one sentence, why PAN is convenience management and the lesson-02 serial
  console is the lifeline — and the serial console still works.
- `bash checks/07-mgmt.sh` passes — it SSHes to the board and confirms `bnep0` has
  `192.168.44.1` and that the management subnet is not NATed. Run it, and confirm the two
  by-hand facts separately (SSH over PAN reaches admin; a Wi-Fi client cannot), because the
  script checks the interface and the ruleset, not that the roles behave for a real client.
- The management network survives a reboot: after `make deploy` and a power cycle, the NAP is
  served, `bnep0` comes up on `192.168.44.1/24`, and the laptop can reconnect without you
  re-issuing commands by hand.

## On completion, persist

Record in the instance's `STATE.md` (and `DESIGN.md` where it is a durable decision):

- The management network is up: `bnep0` on `192.168.44.0/24`, address `192.168.44.1/24`, served
  as a Bluetooth PAN NAP, reachable over PAN from the admin host (note its MAC/address).
- That the management subnet is **not NATed** — it is excluded from the lesson-06 masquerade,
  and why (it is how you reach the box, not a client of the internet).
- That `bnep0` is the **management/trusted** interface and `wlan0` the **client/untrusted** one
  (`#interface-roles`), and that lesson 08's firewall relies on this split.
- The critical distinction, stated plainly (`#recovery-invariant`): the **lifeline is the
  IP-independent serial console** of lesson 02; the PAN link here is **convenience management
  only** and goes down with the IP stack, so it is never the recovery path.

## Optional deeper paths

- Compare the two Bluetooth profiles concretely on the running board: read the serial console's
  RFCOMM device and the PAN's `bnep0` side by side, and confirm one is a character device and
  the other a network interface on the same radio.
- Look at how the NAP end is wired — whether your `bluez` serves it over a bridge and what that
  bridge would let you do (multiple PAN clients on one management segment) — without changing
  the single-admin setup.
- Add a nftables counter or a `nft monitor` trace to watch management traffic arrive on `bnep0`
  and confirm, live, that it is never source-NATed the way client traffic on `wlan0` is.
- Think through the failure matrix ahead of lesson 08: for a wrong route, a default-drop
  firewall, and Ethernet unplugged, mark which of {serial console, PAN, SSH-over-Ethernet}
  survives each — and confirm only the serial console survives all three.
