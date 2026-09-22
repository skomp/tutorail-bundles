---
id: 02-the-lifeline
title: The lifeline
design_refs: [recovery-invariant, platform]
validators: [lifeline-up]
supplies:
  - from: lessons/02-the-lifeline/checks/02-lifeline.sh
    to: checks/02-lifeline.sh
    describe: "Check for this lesson: the Bluetooth serial console is up"
---

## Purpose

Everything you build from lesson 03 on can break the IP network — a wrong route, a link that
never comes up, a firewall that drops all input — so before you touch any of it you build a
way back into the board that does not use IP at all: a login shell over a Bluetooth serial
console.

## Prerequisites

An SSH session on the board and a working `board.env` (lesson `00-find-the-board`). You can
read the board's links and routes (lesson `01-reading-the-network`), which is how you will
prove the console is independent of them. The board's Bluetooth radio present and not blocked
by `rfkill`. A Bluetooth controller you will pair from — your laptop or your phone — with a
serial-terminal application on it. The `bluez` stack and its command-line tools
(`bluetoothctl`, `rfcomm`) on the board; install them if they are absent
(`apt install bluez`, or the installer the tutor recorded).

## Learning objectives

- Explain what a Bluetooth *profile* is, and distinguish SPP/RFCOMM (a serial link) from PAN
  (a network link, built later in lesson 07)
- Explain what a serial getty is, and how binding one to an rfcomm device yields a login
  shell over Bluetooth
- Pair a controller with the board over `bluetoothctl` and advertise the Serial Port Profile
- Bind an rfcomm device on the board and run a getty on it, live, then connect to it and log
  in from the controller
- Persist the console as a systemd unit so it survives a reboot
- Justify why this recovery path keeps working when the routing table is wrong and the
  firewall is dropping everything

## Theory

Bluetooth does not define one connection; it defines many, one per *profile*. A profile is an
agreed shape for a particular kind of link — audio, a keyboard, a file transfer — layered on
the same radio. Two profiles matter for this appliance and they do completely different
things. The **Serial Port Profile (SPP)** emulates a plain serial cable: it carries an
undifferentiated stream of bytes between two devices, exactly as an old RS-232 wire did. On
Linux the local end of an SPP link appears as an **RFCOMM** device, a character device such
as `/dev/rfcomm0`. The other profile, **PAN** (Personal Area Network), carries *Ethernet
frames* and gives you a network interface (`bnep0`) with an IP address; that is a different
tool for a different job, and you build it in lesson 07. This lesson uses SPP only, and it
deliberately never gives the console an IP address — the whole point is a path that has none.

A **getty** ("get tty") is the small program that owns a terminal device, prints the login
prompt, and hands a successful login to `login`, which starts your shell. It is what greets
you on a physical serial console or a virtual console. systemd ships it as a templated unit,
`serial-getty@.service`: the part after the `@` names the device, so `serial-getty@ttyS0`
runs a login prompt on `/dev/ttyS0`. Point the same mechanism at an rfcomm device — run a
getty on `/dev/rfcomm0` — and anything that opens that RFCOMM link over Bluetooth gets a
login prompt and, after authenticating, a real shell on the board.

Now the reason this is the *recovery* path and not just another way in. The chain is radio →
SPP → RFCOMM character device → getty → `login` → shell. Not one link in that chain consults
an IP address, a route, an interface, or the firewall. When lesson 06 gives you a wrong route
and the board can no longer reach or be reached over Ethernet or Wi-Fi, this console is
unaffected. When lesson 08 installs a default-drop firewall that blocks every packet arriving
at the board, this console is unaffected, because no packet is involved. That independence is
the invariant the rest of the course leans on (`#recovery-invariant`): you build the lifeline
first so that every routed lesson after it is safe to get wrong. If the way back in were an IP
path, one bad rule would lock you out of your own board with no recovery.

## Concepts to teach

Bluetooth profile as a per-purpose link shape on a shared radio; SPP/RFCOMM as a serial byte
stream and `/dev/rfcommN` as its local device; the contrast with PAN/`bnep0` as a network
link carrying Ethernet frames (named here, built in lesson 07) so the two never blur;
pairing, trust and bonding in `bluetoothctl` (discoverable, pairable, paired, trusted);
the SDP service record and why SPP must be *advertised* before a controller can find it to
connect; getty as the owner of a terminal device and `serial-getty@.service` as its
systemd template; binding a getty to an rfcomm device to get a shell over Bluetooth; and the
independence of this whole chain from the IP stack, routes and the firewall.

## Constraints

- The console must work with **Ethernet unplugged**. If it needs the cable, it is not a
  lifeline. You will test it unplugged, not argue that it should work.
- The console must not depend on any IP address, route, interface or firewall rule on the
  board (`#recovery-invariant`). Do not give the rfcomm path an address; do not order its
  unit after any network target.
- You write every unit and run every command. The tutor states objectives and checks; it
  does not write your configuration.
- Persist into the `etc/` repo and deploy with `make deploy`; the live setup must survive a
  reboot, not live only in your shell history.

## Suggested progression

Do it live first, so you watch it work, then persist it.

Start by confirming the radio is usable: `rfkill list` shows Bluetooth unblocked, and in
`bluetoothctl`, `show` reports the controller present. Power it and make it findable:
`power on`, then `agent on` and `default-agent`, then `discoverable on` and `pairable on`.

Pair from your controller. With `scan on` running on the board (or by initiating from the
controller side), pair the two devices, then `trust <MAC>` the controller so it may
reconnect without a fresh agent confirmation each time. Confirm with `paired-devices` and
`info <MAC>`.

Now enable and advertise SPP — this is the step `bluez` does not do for you, and forgetting
it is the classic failure: the controller pairs fine, then finds nothing to open, because no
serial service is advertised. Register the Serial Port Profile so an SDP record exists for it
(`sdptool add SP`, or the `bluetoothctl` profile registration your `bluez` version exposes),
and bind a device to listen for incoming SPP connections: `rfcomm bind` / `rfcomm listen` to
attach `/dev/rfcomm0`. Check that the device node appears and, where available, that
`sdptool browse local` lists a serial port service.

Run a getty on that device, live: `systemctl start serial-getty@rfcomm0`. From the controller,
open the paired serial port in your terminal application and confirm you are met by the
board's login prompt and, after logging in, a shell. If the connection opens but shows no
prompt, the getty is not actually bound to that device — a link with no login is the second
classic failure, and it looks like success until you notice nothing greets you.

With it working live, persist it. Author the unit(s) into `etc/` so the board recreates this
on boot: enable `serial-getty@rfcomm0`, and add whatever your setup needs to power the
controller, re-advertise SPP and re-bind the rfcomm device before the getty starts (a small
`rfcomm-bind` service, or the equivalent in your unit). Order it so it does **not** wait on
any network target — it must come up whether or not the IP stack does. Deploy with
`make deploy` and reboot the board to prove the console returns on its own.

## Completion conditions

With **Ethernet unplugged**, you open a serial terminal from your paired controller and get a
login prompt on the board, log in, and run a command in the resulting shell. This by-hand
test with the cable out is the real proof — it demonstrates the path needs no IP.

The `lifeline-up` validator passes. It SSHes to the board and confirms two things: a serial getty is bound to an rfcomm device (a
running `serial-getty@rfcommN` or an rfcomm-bind service), and the Bluetooth controller is
powered. Treat a green check as necessary but not sufficient: it confirms the unit is up, and
the unplugged-Ethernet login confirms the unit does what it is for.

The console survives a reboot: after `make deploy` and a power cycle, the getty is running and
the controller can reconnect without you re-issuing anything by hand. You can state, in one
sentence, why this path keeps working when a route is wrong or the firewall drops all input.

## On completion, persist

Record in the instance state (`STATE.md`) that the lifeline is up: the controller's MAC that
is paired and trusted, the rfcomm device and getty unit in use, and that the console has been
verified with Ethernet unplugged and confirmed to survive a reboot.

Add a note to the instance `DESIGN.md` under the recovery-invariant decision: the recovery
path is a Bluetooth *serial* console (SPP/RFCOMM, not PAN) and must stay IP-independent — no
address, no route, no ordering on a network target. Say plainly that the firewall lesson (08)
relies on this, so any later change that makes the console depend on IP breaks the guarantee
that default-drop is safe.

## Optional deeper paths

Read the SDP service record you advertised (`sdptool browse local`) and see how a client
discovers which RFCOMM channel the serial service listens on. Compare SPP with PAN concretely
by looking ahead to lesson 07: same radio, but one gives you a byte stream and the other a
network interface with an IP — and only the byte stream survives a broken IP stack. Inspect
what a getty actually does by reading `serial-getty@.service` and its overrides, and try
setting the port speed or `TERM` for the rfcomm line. Consider what still fails even with the
lifeline up — a wedged kernel, a dead radio, no power — and what a truly last-resort console
(a UART on the board's header) would add beyond this one.
