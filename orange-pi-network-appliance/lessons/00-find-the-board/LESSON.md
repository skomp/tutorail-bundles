---
id: 00-find-the-board
title: Find the board
design_refs: [address-plan]
validators: [board-reachable]
supplies:
  - from: lessons/00-find-the-board/checks/00-reach.sh
    to: checks/00-reach.sh
    describe: "Check for this lesson: the board answers over SSH"
---

## Purpose

The board is flashed, booted and plugged into Ethernet, but it is headless and you do not
know what address it received, so your first task is to find it on a network you do not
control and open an SSH session to it.

## Prerequisites

A flashed board, powered and connected to your LAN by Ethernet (done before this lesson; no
earlier lesson). Your own machine on the same LAN, with a shell. You will install a scanning
tool on your machine; `arp-scan` and `avahi-utils` are the examples used here, but any
equivalent is fine.

## Learning objectives

- Describe how a freshly booted host gets an IPv4 address from a DHCP server it did not
  choose
- Locate an unknown host on a local subnet three independent ways: a DHCP lease list, an
  ARP or neighbour sweep, and mDNS name resolution
- Explain which method found the board and why the others did or did not work
- Open an SSH session to the board and record how to reach it
- Install key-based SSH so the board answers without a password, because every later
  check connects non-interactively and cannot type one

## Theory

The board did not have an address baked in. On boot its DHCP client broadcast a request onto
the Ethernet segment, and the DHCP server on that LAN (usually your router) offered a lease:
an address, a subnet mask, a default gateway and a lifetime. The board now holds that address
until the lease expires or it reboots. Nothing told you which address, so you must discover it
from your own machine using facts the network already exposes.

Three facts are exposed, and each is a different layer. First, the DHCP server keeps a list of
the leases it handed out; a home router shows this in its admin page, and it names the board
directly. Second, every host that talks on the subnet must map an IP address to a hardware
(MAC) address, and it does this with ARP: a broadcast asking "who has this IP?", answered by
the host that owns it. A sweep that ARPs every address in the subnet makes each live host
reveal its MAC, and the board's MAC has an Allwinner or vendor prefix you can recognise.
Third, mDNS (multicast DNS, the zeroconf `.local` system) lets a host answer to its own name
on the link with no DNS server: the first-boot overlay set the board's hostname to
`orangepizero3`, so `orangepizero3.local` should resolve if mDNS reaches it.

These are independent. When one is blocked or stale, another still works, and knowing which
layer each uses tells you why.

Finding the board is only half of it; you also need a way in that the rest of the course can
use without you. SSH offers two ways to prove who you are: a password, typed each time, and a
key pair, where you install your public key on the board once and authenticate with your
private key from then on. The checks in this course connect **non-interactively** — they
never stop to ask for a password — so key authentication is not a nicety here, it is what
makes every later check able to run at all. There is one more prompt to know about: the first
time you reach a host, SSH shows its host key and asks you to accept it, and it records that
key in `known_hosts` against the exact host string you used. Reach the board once as
`orangepizero3` and once as its address and those are two different strings with two
different records — so pick one value for `BOARD_HOST` and use it everywhere. The address is
usually the steadier choice, because mDNS names can come and go.

## Concepts to teach

DHCP lease (address, mask, gateway, lifetime) and the client broadcast that obtains it; the
local subnet and how to know which one you are on; ARP as layer-2 address resolution and the
neighbour/ARP cache versus a live sweep; MAC address and vendor prefix; mDNS/zeroconf and the
`.local` name; the difference between a name not resolving and a host not answering. SSH
password versus public-key authentication and why non-interactive checks need a key; the host
key, `known_hosts`, and why the record is tied to the exact host string used.

## Constraints

- You must locate the board yourself; you will not be given its address.
- Use tools on your own machine, not on the board (you cannot log in yet).
- You must be able to state which of the three methods found it and why.
- Do not change any setting on the LAN's router beyond reading its lease list.

## Suggested progression

Find your own machine's address and subnet first (`ip addr`), so you sweep the right range;
looking in the wrong subnet is the most common early mistake and it teaches what "local
subnet" means. Then try the three methods and notice how they differ. Read the router's lease
list if you can reach it. Run an ARP sweep of your subnet (`arp-scan --localnet`, or a
ping-sweep followed by `ip neigh`) and pick out the board by its vendor MAC prefix; if you
only inspect `ip neigh` without sweeping first, you may be reading a stale cache, so sweep
live. Try mDNS (`avahi-browse -at`, or `ping orangepizero3.local`); if `.local` fails, that
LAN may filter multicast, which is itself the lesson: fall back to a sweep. Once you have a
candidate address, SSH to it — accepting its host key when asked — and confirm it is the
board. Decide now which value you will use for `BOARD_HOST` (the address is the steadier
choice) and use only that from here on, so the host-key record matches. Fill in `board.env`
with `BOARD_HOST` and `BOARD_USER`.

Now make that access non-interactive. If you do not already have a key pair, generate one
(`ssh-keygen`), then install your public key on the board — `ssh-copy-id <BOARD_USER>@<BOARD_HOST>`
does it in one step, asking for your password this one last time. Confirm it worked by opening
a fresh session: `ssh <BOARD_USER>@<BOARD_HOST>` should now let you in with no password
prompt. That is the state every check depends on. If `ssh-copy-id` is not available, append
the contents of your `~/.ssh/id_*.pub` to the board's `~/.ssh/authorized_keys` by hand and
fix its permissions (`700` on `~/.ssh`, `600` on the file).

## Completion conditions

You can open an SSH session to the board **without being asked for a password** — key
authentication is installed — using the exact `BOARD_HOST` and `BOARD_USER` now in
`board.env`. The `board-reachable` validator passes: it opens a non-interactive
(key-based) session — the same mechanism every later check uses — and confirms the board answers. If it fails it now prints
SSH's own error and names the cause — a password prompt means the key is not installed; a
host-key error means you must accept the key for this exact `BOARD_HOST`; a connection error
points back at `board.env`. You can also name which discovery method found the board (lease
list, ARP/neighbour sweep, or mDNS) and say in one sentence why it worked and, if relevant,
why another failed.

## On completion, persist

Record in the instance state that the board is reachable over key-based SSH, the `BOARD_HOST`
and `BOARD_USER` values now in `board.env`, which of the three discovery methods worked, and
the package manager in use if the tutor substituted one other than `apt`. Do not record any
password or private key.

## Optional deeper paths

Read a DHCP exchange on the wire (DISCOVER, OFFER, REQUEST, ACK) if the learner wants to see
the lease being obtained. Explain why a MAC vendor prefix (OUI) identifies the maker, and why
a randomised or virtualised MAC would not. Discuss why some networks isolate clients so ARP
sweeps and mDNS both fail, and what remains (the lease list, or a direct link) when they do.
