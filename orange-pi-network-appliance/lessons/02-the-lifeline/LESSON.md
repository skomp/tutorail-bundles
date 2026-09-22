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
- Bind an rfcomm device, discover why `serial-getty@rfcomm0` will not start against it, and
  activate the getty with a udev rule — distinguishing a `/dev` node from a systemd device
  unit — then connect and log in from the controller
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

But pointing a getty at `/dev/rfcomm0` is not as simple as starting `serial-getty@rfcomm0`,
and meeting the failure is the point of the exercise. `serial-getty@.service` declares
`BindsTo=dev-%i.device`: it starts only once systemd has a *device unit* for that tty, and
stops when the device goes away. The trap is that a `/dev` node is **not** a systemd device
unit. systemd creates a `dev-….device` unit only for a udev device tagged `systemd`, and the
stock rules tag `ttyS*`, `ttyAMA*` and `ttyUSB*` — never `rfcomm*`. So `/dev/rfcomm0` can
exist and be perfectly usable while `dev-rfcomm0.device` never activates, and
`systemctl start serial-getty@rfcomm0` times out on that dependency.

The fix is a **udev rule**, and since this course does not assume you have written one, here
is what a rule is. *udev* is the daemon that reacts to the kernel's device events: whenever a
device appears, changes or goes away, the kernel emits an event (`add`, `change`, `move`,
`remove`) and udev runs its rules against it. A rule is one line of comma-separated *keys*.
Keys written with `==` are **match** conditions — the rule fires only if every one of them
matches the event's device; keys written with `=`, `+=` or `:=` are **assignments** that take
effect when it does. Four keys carry this job: `SUBSYSTEM` and `KERNEL` match *which* device
this is; `TAG+="systemd"` tells systemd to mind the device, which is the assignment that makes
the `.device` unit exist at all; and `ENV{SYSTEMD_WANTS}="…"` names a unit for systemd to
start when the device appears. Rules live in files under `/etc/udev/rules.d/`, read in
filename order (a numeric prefix like `99-` decides when yours runs), and udev re-reads them
after `udevadm control --reload`. Two tools let you write a rule by looking rather than
guessing: `udevadm monitor` prints events live as you connect, and `udevadm info /dev/rfcomm0`
(add `--attribute-walk` for the full set) prints the exact `SUBSYSTEM`, `KERNEL` and
attributes you can match on. You will use both to build the rule yourself.

With such a rule tagging the rfcomm device `systemd` and wanting the getty, `BindsTo=` finally
works *for* you: the getty starts the moment the node appears and stops cleanly on hangup.

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
systemd template; why a `/dev` node is not a systemd `.device` unit and how `serial-getty@`'s
`BindsTo=` depends on the latter; udev as the device-event daemon and the anatomy of a udev
rule (match keys with `==`, assignments with `+=`, `TAG+="systemd"`, `ENV{SYSTEMD_WANTS}`),
placed under `/etc/udev/rules.d/` and reloaded with `udevadm control --reload`, with
`udevadm monitor` and `udevadm info` to write it by looking; binding a getty to an rfcomm
device this way to get a shell over Bluetooth; and the
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

Now try to run a getty the obvious way, and watch it fail: `systemctl start
serial-getty@rfcomm0` returns `Timed out waiting for device dev-rfcomm0.device` and fails with
result `dependency`, even though `/dev/rfcomm0` is present and openable. Diagnose it against
the theory above before fixing it — no `systemd` tag on the rfcomm device means no
`dev-rfcomm0.device` unit, and the getty's `BindsTo=` has nothing to bind to.

Now write the udev rule that fixes it, and build it by looking rather than by pasting. Run
`udevadm monitor` and open the link so you see the event: `add /devices/virtual/tty/rfcomm0
(tty)`, followed a moment later by a `move` as the device is re-parented — so match on stable
keys, not that transient path. Read the device's match keys with `udevadm info /dev/rfcomm0`.
Then compose a rule in a `99-`-prefixed file under `/etc/udev/rules.d/`: match the rfcomm tty
by its `SUBSYSTEM` and `KERNEL`, tag it with `TAG+="systemd"`, and start its getty with
`ENV{SYSTEMD_WANTS}="serial-getty@%k.service"` (`%k` expands to the kernel name, `rfcomm0`).
Reload with `udevadm control --reload`, reconnect from the controller, and confirm the getty
now starts on its own as the node appears. Check the tag actually took with
`udevadm info /dev/rfcomm0 | grep -i systemd`. Then open the paired serial port and confirm
the login prompt and, after logging in, a shell.

With it working live, persist it into `etc/`. Two pieces plus the udev rule you just wrote:
the rule itself (under `etc/udev/rules.d/`), and a small service that makes the rfcomm node
exist on boot in the first place — power the controller as needed, re-advertise SPP, and
`rfcomm listen`/bind `/dev/rfcomm0` (an `rfcomm-bind` service, or the equivalent in your unit).
You do **not** statically enable `serial-getty@rfcomm0`: the udev rule activates it whenever
the node appears, which is exactly the behaviour you want. Order the bind service so it does
**not** wait on any network target — the lifeline must come up whether or not the IP stack
does. Deploy with `make deploy` and reboot the board to prove the console returns on its own.

## Completion conditions

With **Ethernet unplugged**, you open a serial terminal from your paired controller and get a
login prompt on the board, log in, and run a command in the resulting shell. This by-hand
test with the cable out is the real proof — it demonstrates the path needs no IP.

The `lifeline-up` validator passes. It SSHes to the board and confirms two things: a serial getty is bound to an rfcomm device (a
running `serial-getty@rfcommN` or an rfcomm-bind service), and the Bluetooth controller is
powered. Treat a green check as necessary but not sufficient: it confirms the unit is up, and
the unplugged-Ethernet login confirms the unit does what it is for.

The console survives a reboot: after `make deploy` and a power cycle, the udev rule and the
bind service are in place, and reconnecting from the controller brings up the login prompt on
its own — the getty is activated by the rule when the rfcomm node appears, with nothing
re-issued by hand. You can state, in one sentence, why this path keeps working when a route is
wrong or the firewall drops all input; and you can explain why `systemctl start
serial-getty@rfcomm0` failed before the rule and works through it after.

## On completion, persist

Record in the instance state (`STATE.md`) that the lifeline is up: the controller's MAC that
is paired and trusted, the rfcomm device, the udev rule that activates the getty, the bind
service in use, and that the console has been verified with Ethernet unplugged and confirmed
to survive a reboot.

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
