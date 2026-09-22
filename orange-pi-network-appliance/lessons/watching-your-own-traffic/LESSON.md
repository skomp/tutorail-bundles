---
id: watching-your-own-traffic
title: Watching your own traffic
design_refs: [interface-roles, platform]
validators: [capture-works]
optional: true
supplies:
  - from: lessons/watching-your-own-traffic/checks/opt-capture.sh
    to: checks/opt-capture.sh
    describe: "Check for this optional lesson: tcpdump captures traffic on wlan0"
---

## Purpose

Watch, on the wire, the packets your appliance forwards — and see the same client
flow with its private source on `wlan0` and rewritten to the upstream interface's
address on the upstream side, so the NAT translation from lesson 06 stops being a
rule you trust and becomes a thing you observed.

By lesson 06 a Wi-Fi client reaches the internet through the box, and you read a
`conntrack` entry that recorded the translation. That entry is the kernel's
bookkeeping. This lesson lets you look at the actual packets on each side of the
box and confirm the story yourself: leaving `wlan0` a packet carries source
`192.168.4.x`; the same connection leaving the upstream interface (`$WAN_IF`)
carries that interface's upstream address instead. Two captures, one flow, the
translation visible in both. This is an observation lesson — you change nothing
about how the appliance runs.

## Prerequisites

This lesson stands alone; it assumes only the finished NAT appliance, not that
you arrived here from any particular step.

- Lesson 01 established the upstream interface's name and recorded it as `WAN_IF`
  (in `board.env`, and `export`ed in your board session — `AP_IF`, usually
  `wlan0`, is the client-facing side). This lesson uses `"$WAN_IF"` in commands
  and "the upstream interface" in prose; make sure `WAN_IF` is exported in the
  shell you capture from.
- A working NATed access point: lesson 06 (`06-nat-with-nftables`) complete.
  Client traffic from `192.168.4.0/24` is source-NATed (`masquerade`) out the
  upstream interface (`$WAN_IF`), and a Wi-Fi client can reach the internet
  through the box.
- The interface roles from the design: `wlan0` faces the clients, the upstream
  interface (`$WAN_IF`) faces the internet. All captures in this lesson name those
  two interfaces.
- At least one Wi-Fi client associated to the AP and generating traffic you can
  point at — a phone loading pages, a laptop running `ping` or `curl`. Without
  live traffic there is nothing to capture.
- A shell on the box (over SSH or the Bluetooth lifeline from lesson 02) with
  privilege to capture: `tcpdump` needs root or the appropriate capability.
- `tcpdump` installed on the box. Installing it is your work:
  `apt install tcpdump` (your tutor may substitute the package manager for your
  image).

## Learning objectives

- Capture live traffic on a chosen interface with `tcpdump`, and explain why the
  interface you pick determines whether you see the pre-NAT or post-NAT view.
- Capture one client's flow on `wlan0` (private source `192.168.4.x`) and the same
  flow on the upstream interface (source rewritten to that interface's address),
  and point to the single translation that connects the two.
- Write BPF capture filters (`host`, `port`, `net`) to narrow a capture to the one
  conversation you care about, and explain why an unfiltered capture on a busy
  interface hides the signal.
- Read a `tcpdump` line well enough to name source, destination, protocol and port,
  and tell the client-facing side of a flow from the internet-facing side.
- Tie the two views back to `conntrack` and `masquerade` from lesson 06: the wire
  captures are the two ends of the flow whose translation conntrack records.

## Theory

**What `tcpdump` does.** `tcpdump` puts an interface into a mode where the kernel
copies every packet crossing it up to your terminal, decoded into one line each.
You choose which interface with `-i` (for example `tcpdump -i wlan0`), and that
choice is the whole game in this lesson: the box sits between two networks, and
each interface shows the traffic at a *different point in its journey through the
box*.

**Why the interface picks the side of the translation.** A client packet enters
the box on `wlan0` still carrying its real private source, `192.168.4.x`. It is
routed, and on the way out the upstream interface (`$WAN_IF`) the `masquerade`
rule rewrites that source to that interface's own upstream address (this is
exactly the postrouting rewrite from lesson 06). So:

- **Capture on `wlan0`** and you see the *pre-NAT* view: source `192.168.4.x`,
  destination the far internet host. This is the client's packet as it really is.
- **Capture on the upstream interface** (`tcpdump -i "$WAN_IF"`) and you see the
  *post-NAT* view of the same packet: source is now that interface's address,
  destination unchanged. The client's private address has disappeared from the
  header.

The same reasoning runs in reverse for replies: on the upstream interface the
reply is addressed to that interface's address; by the time it leaves `wlan0`
conntrack has un-translated it back to `192.168.4.x`. Watching both interfaces is
watching both ends of the
translation that `conntrack` recorded for you in lesson 06 — the wire confirms the
bookkeeping.

**Capture filters (BPF).** An interface on a working appliance is busy, and an
unfiltered `tcpdump` scrolls faster than you can read — the packet you want is
buried. A *capture filter* (Berkeley Packet Filter) tells the kernel to hand you
only matching packets. The three you need here:

- `host 192.168.4.23` — only traffic to or from that address.
- `port 443` or `port 53` — only that TCP/UDP port (443 is HTTPS, 53 is DNS).
- `net 192.168.4.0/24` — only traffic to or from the client subnet.

Combine them with `and`, `or`, `not`: `tcpdump -i wlan0 host 192.168.4.23 and
port 443`. Narrow the filter until you see one conversation, not the whole box.

**Reading a line without drowning.** A `tcpdump` line reads left to right:
timestamp, protocol, `source > destination`, then flags and length. `-n` stops it
turning addresses into hostnames (which is slow and hides the numbers you came to
read); on a fast link that alone makes the output legible. Read the `source` field
first — that is the field NAT rewrites, and comparing it between the two captures
is the entire exercise.

**Instructive failures to expect.** Capture on the wrong interface and you see
traffic, but not the side of the translation you meant — for example you look for
the upstream interface's address on `wlan0`, where it never appears. Read the two captures
backwards and you will call the pre-NAT source the post-NAT one; the fix is to
remember that the private `192.168.4.x` address only lives on the `wlan0` side. And
an over-broad filter (or none) drowns the one flow in the box's own chatter — DNS,
ARP, SSH, the reply traffic — until you narrow it to one host and port.

## Concepts to teach

- `tcpdump` basics: choosing an interface with `-i`, that it shows live packets one
  line each, and that it needs root/capability to capture.
- The interface choice selects the side of NAT: `wlan0` shows the pre-NAT private
  source, the upstream interface (`$WAN_IF`) shows the same flow with the source
  rewritten to that interface's address.
- The reverse direction: replies arrive on the upstream interface for that
  interface's address and leave `wlan0` un-translated back to the client — the
  mirror of the outbound rewrite.
- BPF capture filters: `host`, `port`, `net`, combined with `and`/`or`/`not`, and
  why filtering is what makes a capture on a live interface readable.
- Reading a `tcpdump` line: timestamp, protocol, `source > destination`, port; the
  role of `-n`; reading the source field to spot the translation.
- The tie back to lesson 06: these two captures are the two ends of the flow whose
  translation `conntrack` records, and `masquerade` performs.

## Constraints

- The learner runs every `tcpdump` command themselves, on their own appliance,
  against their own traffic. The tutor explains and points; it does not run the
  capture for them.
- Capture is limited to the learner's own box and their own client's traffic. This
  is defensive, educational observation of your own network — not capture of
  anyone else's traffic.
- Nothing under `etc/` changes and nothing is deployed. This lesson observes; it
  must not alter how the appliance runs.
- The learner must capture the *same* flow on both `wlan0` and the upstream
  interface (`$WAN_IF`) — one capture on one interface does not show the
  translation. Both sides are required to see it.
- Filters must be narrow enough to isolate one client conversation; an unfiltered
  capture that the learner cannot read back is not a completed capture.

## Suggested progression

1. Restate the goal in one line: you already trust that NAT works (lesson 06); now
   you will *see* the translation, by capturing the same flow on each side of the
   box.
2. Install `tcpdump` on the box if it is not present (`apt install tcpdump`), and
   confirm it runs (`tcpdump --version`).
3. Pick a target client and start generating traffic from it — for example a
   sustained `ping 1.1.1.1`, or `curl` in a loop to a known host — so there is a
   steady flow to capture. Note the client's `192.168.4.x` address.
4. Capture the pre-NAT view: on the box, `tcpdump -n -i wlan0 host <client-ip>`
   (add `and port 443` or `and icmp` to narrow to the flow you started). Read the
   `source > destination` field and confirm the source is `192.168.4.x`.
5. Read the current upstream address (`ip -4 addr show "$WAN_IF"`) so you know what
   to look for on the other side.
6. Capture the post-NAT view of the *same* flow: `tcpdump -n -i "$WAN_IF"` filtered
   to the same destination or port (for example `host <far-host> and port 443`, or
   `icmp`). Confirm the source is now the upstream interface's address and the
   private `192.168.4.x` no longer appears.
7. Put the two side by side and name the translation: same destination, same
   protocol/port, source `192.168.4.x` on `wlan0` becomes the upstream interface's
   address on the upstream side. Have the learner say aloud which capture is
   pre-NAT and which is post, and why.
8. Tie it back: this is the flow whose translation you read in `conntrack` in
   lesson 06 — the wire and the conntrack entry describe the same masquerade.
9. Instructive probes: capture on the wrong interface (look for the upstream
   interface's address on `wlan0`) and see it never appear; run an unfiltered
   `tcpdump -i "$WAN_IF"` briefly to feel the noise, then re-apply the filter and
   watch the signal return.

## Completion conditions

- `tcpdump` is installed on the box and the learner runs it themselves.
- The learner captures one client's flow on `wlan0` and shows the source is the
  client's private `192.168.4.x` address (the pre-NAT view).
- The learner captures the *same* flow on the upstream interface (`$WAN_IF`) and
  shows the source is now that interface's upstream address, with `192.168.4.x`
  absent from the header (the post-NAT view).
- The learner points to the single translation connecting the two captures —
  same destination and protocol/port, source rewritten — and states correctly
  which capture is pre-NAT and which is post-NAT.
- The learner uses at least one narrowing capture filter (`host`, `port`, or
  `net`) so the captured flow is readable rather than buried, and can explain what
  the filter selected.
- The learner connects the two captures back to `conntrack`/`masquerade` from
  lesson 06: these are the two ends of the flow conntrack tracks.
- The `capture-works` validator passes. It confirms `tcpdump` captures traffic on
  `wlan0` on the box.
- Nothing under `etc/` was changed and nothing was deployed.

## On completion, persist

Record in the instance's `DESIGN.md`/`STATE.md`:

- The learner can capture and read forwarded traffic on the appliance with
  `tcpdump`, choosing the interface deliberately and narrowing with BPF filters.
- The learner has observed the NAT translation on the wire: the same client flow
  with a private `192.168.4.x` source on `wlan0` and the upstream interface's
  address on the upstream side, and has connected this to the
  `conntrack`/`masquerade` behaviour from lesson 06.
- No `etc/` change was made — this is an observation lesson and the running
  appliance is unchanged.

## Optional deeper paths

- Write a capture to a file with `tcpdump -w flow.pcap …`, copy it off the box,
  and open it in Wireshark for a graphical, per-field view of the same packets —
  including following a whole conversation as a stream.
- Tighten to a single client and single conversation: combine `host <client-ip>
  and host <far-host> and port 443` on `wlan0`, then the post-NAT equivalent on
  the upstream interface (`$WAN_IF`), to watch exactly one flow cross the box with
  nothing else in the way.
- Watch a DNS exchange: capture `port 53` on `wlan0` to see a client's query to
  the box's resolver, then on the upstream interface to see the box's own upstream
  lookup — a
  second, different shape of the same "client-side versus upstream-side" split
  you saw with NAT.
