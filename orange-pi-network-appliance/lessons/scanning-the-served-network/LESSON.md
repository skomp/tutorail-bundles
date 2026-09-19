---
id: scanning-the-served-network
title: Scanning the served network
design_refs: [address-plan, interface-roles, platform]
validators: [scan-runs]
optional: true
supplies:
  - from: lessons/scanning-the-served-network/checks/opt-scan.sh
    to: checks/opt-scan.sh
    describe: "Check for this optional lesson: a scan finds hosts on the served network"
---

## Purpose

You built a network for other machines to use; this lesson turns the appliance's
eye inward and shows you how to see who is actually on it — an operator's-eye
view of your own clients.

Until now every client on `192.168.4.0/24` has been an abstraction: DHCP hands
out a lease, NAT sends the traffic on its way, the firewall gives each packet a
verdict, and you never had to know a single client apart from the others. An
operator does need to know. Which hosts are live right now? Is that the phone you
expected, or something you did not put there? What does a given client expose to
the rest of the subnet? These are questions you answer by *discovering* the
hosts, not by reading a config file — because the config says who *may* connect,
and discovery tells you who *has*. This lesson teaches how host discovery works
and lets you run it against the one network you are entitled to probe: your own.

## Prerequisites

This lesson stands alone; you do not need to have arrived here straight from
lesson 08. Before you start, make sure the following are true:

- **A working AP with at least one associated client** (lessons 03-06). The
  appliance serves `wlan0` on `192.168.4.0/24`, and at least one client must be
  associated and hold a DHCP lease — a scan of an empty subnet finds nothing and
  teaches nothing. Associate a phone or laptop before you begin.
- **The firewall from lesson 08 in place.** The `input`/`forward` policy is what
  makes some of the results below read as *filtered* rather than *closed*; the
  lesson leans on that distinction.
- **A shell on the appliance**, over SSH or the lesson-02 serial console. You run
  the scans *from the appliance*, which sits on the served segment.
- **The `nmap` and/or `arp-scan` packages installed.** Installing them is your
  work: `sudo apt update && sudo apt install nmap arp-scan`. `arp-scan` needs to
  be run as root.

## Scope — read this first

**Scan only the network you operate.** That means your own served subnet,
`192.168.4.0/24`, reached through `wlan0`. Do **not** point a scan at the
upstream interface (`$WAN_IF`), at whatever LAN the appliance is plugged into, or at any
host or range you do not own. You operate the AP subnet; you do not operate the
upstream. This is a defensive exercise on your own appliance — keep it there.

## Learning objectives

- Enumerate the live hosts on the served subnet from the appliance, and read the
  result well enough to say which addresses are real clients.
- Explain the difference between **active** and **passive** discovery, and
  between the two active methods you use here: ARP-based discovery on the local
  segment and ICMP/TCP host discovery.
- Explain why ARP discovery finds hosts only on the same layer-2 segment and
  cannot reach beyond it.
- Distinguish a **closed** port (the host answered and refused) from a
  **filtered** port (nothing answered, e.g. a firewall dropped the probe) for at
  least one host, and say what each tells you.
- State, and stay inside, the scope limit: your own served subnet only.

## Theory

**Active vs passive discovery.** *Active* discovery sends packets and watches for
answers — you provoke the network into revealing its hosts. *Passive* discovery
sends nothing; it only listens to traffic that is already flowing and notes which
addresses appear. Active is faster and more complete but it is visible — every
host you probe could log the probe. Passive is invisible but only ever sees hosts
that happen to talk while you watch. This lesson is active; passive is an optional
path at the end.

**ARP-based discovery, and why it stops at the segment.** On a shared local
network, one host reaches another by its hardware (MAC) address, and it learns
that address by broadcasting an ARP request: "who has `192.168.4.37`? tell me."
The host that owns the address answers with its MAC. `arp-scan` weaponises this:
it sends an ARP request for every address in the range and lists whoever answers.
Because it works at the hardware layer, it is fast, hard for a host to hide from
(a host that ignores ping still needs ARP to use the network at all), and it
reports the MAC, which often names the vendor.

The same mechanism is exactly why ARP discovery **cannot see past your own
segment.** ARP is a broadcast, and broadcasts do not cross a router — the
appliance itself, doing its routing job, stops them. So `arp-scan` on `wlan0`
sees the `192.168.4.0/24` clients and nothing else: not the upstream LAN, not the
internet. That limit is a feature here. It is also the first instructive failure
below: if you expect ARP discovery to reach the upstream, you will get an empty
or nonsensical result and misread it as "nothing there" when the real answer is
"wrong tool for a different segment."

**ICMP/TCP host discovery.** `nmap -sn` (a "ping scan" — discovery only, no port
scan) finds live hosts by a mix of probes: an ARP request when the target is on
the local segment, and ICMP echo plus a couple of TCP probes otherwise. On your
own segment `nmap -sn` and `arp-scan` will largely agree, because both fall back
to ARP; the value of `nmap` is that it also does the layer-3 probing you would
need to reason about hosts that are *not* on your segment — which, per the scope
rule, you are not going to probe here, but which is why the two tools exist
separately.

**Closed vs filtered — the distinction worth owning.** When you go past discovery
and ask about a *port* on a live host (`nmap` without `-sn`), each port comes back
in one of a few states. Two of them look similar and mean opposite things:

- **closed** — the host received your probe and actively answered "nothing is
  listening here" (for TCP, a RST). You learn two facts: the host is alive and
  reachable, and that port has no service.
- **filtered** — *nothing came back at all.* A firewall silently dropped the
  probe, so `nmap` cannot tell whether a service is behind it. You learn that
  something is refusing to answer — often the firewall you built in lesson 08, or
  the client's own firewall.

The difference is who stayed silent. Closed is a host saying "no"; filtered is a
host (or a firewall in front of it) saying nothing. Reading `filtered` as `closed`
will make you conclude a service is absent when in fact a firewall is hiding it —
the second instructive failure. Point a port scan at the appliance's own
`wlan0` address and you can watch your lesson-08 policy turn ports `filtered`.

## Concepts to teach

- Active vs passive discovery: what each sends, what each can and cannot see.
- ARP request/reply as the local-segment discovery mechanism, and MAC/vendor as
  what it reveals.
- Why ARP (a broadcast) does not cross the router, so ARP discovery is
  segment-local by construction — and why that matches the scope rule.
- `nmap -sn` as host discovery vs a port scan, and how it overlaps with
  `arp-scan` on the local segment.
- Port states, specifically **closed** (host answered, refused) vs **filtered**
  (no answer, dropped) — who is silent and what you may and may not conclude.
- The scope limit as an operator principle: you probe the network you run, not
  the one you are attached to.

## Constraints

- **You run every command.** The tutor does not run scans for you and does not
  hand you a finished invocation to paste blindly — you choose the tool, the
  range, and the interface, and you say why.
- **Target only `192.168.4.0/24`, via `wlan0`.** Never scan the upstream
  interface (`$WAN_IF`), the LAN behind it, or any host you do not own. If a command's target is not
  inside your served subnet, do not run it.
- **No configuration changes.** This lesson observes; it does not alter `etc/`,
  the firewall, or any service. Nothing you do here needs `make deploy`.
- Do not run destructive or aggressive `nmap` options (no `-sS` flood tuning
  games, no scripts against third parties). Discovery and a plain port state read
  on your own hosts are the whole exercise.

## Suggested progression

Run each step live and read the output before moving on. The goal is not to
collect scans but to be able to explain every line one produces.

1. **Confirm you have a client to find.** Check the DHCP leases or the AP's
   associated-station list and note at least one client address on
   `192.168.4.0/24`. If there is none, associate a device now — the rest of the
   lesson has nothing to discover without it.

2. **Install the tools.** `sudo apt update && sudo apt install nmap arp-scan` if
   they are not already present.

3. **ARP-discover the served segment.** Run `arp-scan` against `wlan0` — for
   example `sudo arp-scan --interface=wlan0 192.168.4.0/24` (or
   `sudo arp-scan --interface=wlan0 --localnet`). Read the list: the appliance's
   own `192.168.4.1`, plus each associated client, each with a MAC and often a
   vendor name. Identify which line is which device.

4. **Cross-check with `nmap` host discovery.** Run `nmap -sn 192.168.4.0/24` from
   the appliance. Confirm it reports the same live hosts. Note that on this
   segment it, too, is using ARP under the hood — the results should agree with
   step 3.

5. **See the segment boundary for yourself.** Predict what `arp-scan` would find
   if aimed at the upstream, then reason about why you will *not* run that
   (scope) and why it could not work anyway (ARP does not cross the router). If
   you want to see the empty-result failure safely, aim `arp-scan` at an unused
   *in-scope* range within `192.168.4.0/24` and watch it find nothing — that is
   what "no host answered" looks like, distinct from "wrong segment."

6. **Read closed vs filtered on a host you own.** Pick one live client and run a
   small port scan against it, e.g. `nmap 192.168.4.37`. Then run the same
   against the appliance's own AP address, `nmap 192.168.4.1`. Compare the port
   states. Find at least one port reported **closed** and one reported
   **filtered**, and say for each which side stayed silent and what you may
   conclude. If your lesson-08 firewall is dropping probes to the box, expect
   `filtered` there.

7. **Explain your results.** For the hosts you found, state which are live and
   name the device behind each. For one port, state whether it is closed or
   filtered and what that means. If a result surprised you, find out why before
   you call the lesson done.

8. **Run the check.** `bash checks/opt-scan.sh`.

## Completion conditions

- You have enumerated the live hosts on `192.168.4.0/24` from the appliance,
  using `arp-scan` and/or `nmap -sn`, and can name the device behind each
  discovered address (including the appliance's own `192.168.4.1`).
- You can explain, in your own words, why ARP-based discovery finds those hosts
  and only those — that ARP is a local broadcast the router does not forward — so
  it cannot reach the upstream segment.
- For at least one port on one host, you can say whether it is **closed** or
  **filtered**, which side stayed silent, and what you may and may not conclude
  from each — and you have seen a `filtered` result produced by a dropping
  firewall (yours from lesson 08 counts).
- Every scan you ran targeted `192.168.4.0/24` only; you did not scan the
  upstream interface (`$WAN_IF`) or any host you do not own, and you can state why that limit holds.
- `bash checks/opt-scan.sh` passes. It confirms a scan run from the appliance
  discovers a host on the AP subnet — so associate a client first, or the check
  has nothing to find.

## On completion, persist

Record in the instance's DESIGN.md or STATE.md:

- That you can discover and interpret the hosts on the served network
  (`192.168.4.0/24`) from the appliance, using ARP-based discovery and
  `nmap` host discovery, and can read a live-host list.
- That you understand **closed** vs **filtered** port states — host-refused vs
  silently-dropped — and have seen the firewall from lesson 08 produce a
  `filtered` result.
- The scope limit as a standing operator rule: discovery runs against the served
  subnet only, never the upstream or any network you do not operate.

No `etc/` change is needed; this lesson observes and does not alter the
appliance.

## Optional deeper paths

If you want to go further, three directions build on what you just did:

- **Service and version detection.** Beyond "the port is open," `nmap -sV`
  interrogates a service to name it and guess its version, and `-A` adds OS
  detection and more. Run these only against your own clients, and notice how
  much more intrusive — and more visible in a target's logs — they are than plain
  discovery.
- **Passive discovery.** Instead of probing, watch the traffic already flowing
  through the appliance and let hosts reveal themselves by talking (the companion
  optional lesson on watching your own traffic goes here). Compare what passive
  observation finds against what an active scan found: the overlap and the gaps
  are the lesson.
- **Why an operator scans their own network.** Discovery is how you notice a
  device you did not authorise, an unexpected open port on a client, or a host
  that vanished. Think about how you would run this regularly and diff the result
  against a known-good baseline — the beginning of turning a one-off scan into
  monitoring.
