---
id: 03-bring-up-an-ap
title: Bring up an access point
design_refs: [interface-roles, address-plan, platform]
validators: [ap-beaconing]
supplies:
  - from: lessons/03-bring-up-an-ap/checks/03-ap.sh
    to: checks/03-ap.sh
    describe: "Check for this lesson: hostapd is beaconing and wlan0 is in AP mode"
---

## Purpose

The appliance is a Wi-Fi router, so before it can route anything it has to be a Wi-Fi
network — a radio that names itself, that a phone can find and join. In this lesson you turn
`wlan0` into an access point and watch a station associate to it, and you stop exactly there:
the client joins and gets *no address and no internet*, on purpose, because addresses are the
next lesson's job. This lesson is only the radio and the join.

## Prerequisites

An SSH session on the board and a working `board.env` (lesson `00-find-the-board`). You can
read the board's links with `ip link` and `iw dev` (lesson `01-reading-the-network`), which
is how you will confirm `wlan0` exists and what mode it is in. The Bluetooth serial console
from lesson `02-the-lifeline` working, because bringing `wlan0` up as an AP can disturb any
Wi-Fi you were relying on for access — from here on, the lifeline is your safety net, not a
nicety. A `wlan0` interface present on the board (`iw dev` lists it) and its radio not blocked
by `rfkill`. The `hostapd` package on the board; install it if it is absent
(`apt install hostapd`, or the installer the tutor recorded — the package manager is the one
prerequisite that adapts, `#platform`). A second device to join the network: a phone or a
laptop with Wi-Fi.

## Learning objectives

- Explain what an 802.11 access point advertises — SSID, band and channel — and how a beacon
  frame makes the network discoverable
- Distinguish *authentication* from *association*, and read both happening in the hostapd log
- Explain what the Wi-Fi regulatory domain / country code controls, and why hostapd refuses
  to start when it is unset or wrong
- Write a minimal WPA2 `hostapd.conf` from its essential keys and run hostapd in the
  foreground to watch beacons go out and a station join
- Give `wlan0` its access-point address `192.168.4.1/24` live, and explain why a joined client
  still has no address until DHCP exists (lesson 04)
- Persist the AP by authoring `etc/hostapd/hostapd.conf` and deploying it, and know which part
  of making it start unattended is deferred to lesson 09

## Theory

An **access point** is a station that advertises a network and lets others join it. It does
this by broadcasting **beacon frames**: small management frames sent many times a second that
carry the network's name and how to talk to it. The name is the **SSID** — the human-readable
string a phone shows in its Wi-Fi list. When you switch `wlan0` from an ordinary client
(*managed* mode) into **AP mode**, the radio stops looking for networks to join and starts
being one, emitting those beacons itself.

Every 802.11 network lives on a **band** and a **channel**. The band is the frequency range —
2.4 GHz or 5 GHz — and in hostapd it is chosen by `hw_mode` (`g` selects 2.4 GHz, `a` selects
5 GHz). Within a band the spectrum is divided into numbered **channels**; `channel` picks one.
Not every channel is legal on every band, and not every band is legal in every country, which
is where the next concept comes in.

Radio spectrum is regulated per country: which channels may be used, at what power, and
whether a band is allowed at all differs by jurisdiction. Linux enforces this through a
**regulatory domain**, selected by a two-letter **country code** (`DE`, `GB`, `US`, …). This
is not paperwork you can skip. hostapd **refuses to start** if the country is unset or if the
`channel`/`hw_mode` you asked for is not permitted in that country — it would rather emit
nothing than transmit illegally. The Armbian first-boot overlay usually sets a country, but
"usually" is not "always", and a wrong or missing one is the single most common reason an
otherwise-correct AP config never comes up. You will check it deliberately in this lesson.

When a device joins, two distinct steps happen, in order, and hostapd logs each one.
**Authentication** comes first: the station and the AP establish that they are willing to talk
at the 802.11 level (with WPA2 this is the low-level handshake, before the passphrase is even
proven). **Association** comes second: the station formally attaches to this AP — the AP
allocates it a slot and, from that point, the two exchange data frames. Authentication is
"we can speak"; association is "you are now my client". Watching an `AP-STA-CONNECTED` line
(preceded by authenticated/associated messages) in the hostapd log is the proof this lesson is
after — it means the radio layer worked end to end.

And here is the deliberate gap. Association is an 802.11 event; it has nothing to do with IP.
A device that has associated has a working *link* to the board and still has **no IP address**,
because nothing on the board is handing addresses out yet. On a phone this shows as "connected,
no internet". That is not a fault — it is exactly where this lesson stops. `wlan0` itself does
get an address here — the access-point address `192.168.4.1/24` from the plan (`#address-plan`,
`#interface-roles`: `wlan0` is the client-facing interface) — but that is the *board's* address
on its own network, not something a client receives. The DHCP server that gives clients
addresses is lesson `04-handing-out-addresses`.

The essential `hostapd.conf` is short. `interface=wlan0` names the radio to run on;
`ssid=` names the network; `hw_mode=` and `channel=` choose band and channel; `country_code=`
sets the regulatory domain. For WPA2, a small block turns on encryption:
`wpa=2`, `wpa_key_mgmt=WPA-PSK`, a `wpa_passphrase=` of at least eight characters, and
`rsn_pairwise=CCMP`. That is enough to beacon a protected network a phone will join.

## Concepts to teach

Access point versus managed/client mode, and what switching `wlan0` to AP mode changes; the
SSID as the advertised network name and the beacon frame as the periodic broadcast that
carries it; band and channel, and how `hw_mode` selects the band and `channel` the channel
within it; the regulatory domain and country code, what they constrain, and specifically that
hostapd refuses to start on an unset country or an out-of-band/illegal channel; the two-step
join — authentication then association — and how to read each in the hostapd log; the
essential `hostapd.conf` keys and the minimal WPA2 block; the distinction between the *link*
(association, an 802.11 fact) and *addressing* (IP, which does not exist yet), so the learner
expects "connected, no internet" and reads it as success; `wlan0`'s own AP address
`192.168.4.1/24` as the board's address, not the client's; and that exactly one thing may own
`wlan0` — hostapd here — so any other manager of that interface must be out of the way.

## Constraints

- You write `hostapd.conf` yourself, every key of it. The tutor states the required keys and
  checks the result; it does not write your configuration.
- IPv4 only (`#address-plan`). Do not configure IPv6 on `wlan0`.
- `wlan0` gets exactly the address `192.168.4.1/24` — the value the whole course depends on
  (`#address-plan`). Not a different subnet, not a different host.
- Do **not** give clients an address in this lesson, and do not add a DHCP server, a default
  route for clients, or NAT. A joined client having no internet is the correct end state here.
- Exactly one thing may manage `wlan0`. Before you start, make sure no other process owns it —
  no NetworkManager, no `wpa_supplicant` holding it in client mode, no second hostapd. The
  control plane for this appliance is systemd-networkd (`#control-plane`), and the full unit
  ordering is finalized in lesson 09; here you only need `wlan0` free for hostapd to claim.
- Persist into the `etc/` repo and deploy with `make deploy`. The live setup must be
  reproducible from the repo, not live only in your shell history.

## Suggested progression

Do it live first, watch it work, then persist it.

Begin by confirming the ground. `iw dev` shows `wlan0` and its current type; `rfkill list`
shows the Wi-Fi radio unblocked (unblock it with `rfkill unblock wifi` if it is soft-blocked).
Check that nothing else is holding the interface — stop or mask any NetworkManager or
`wpa_supplicant` instance that has claimed `wlan0`, so hostapd can take it.

Check the regulatory country *before* you write any config, because it gates everything after
it. `iw reg get` shows the current domain; if it reads `country 00` (the world/unset domain)
or the wrong country, set it — live with `iw reg set <CC>`, and durably however your Armbian
image records it (the first-boot overlay's setting, or the `crda`/`wireless-regdb` mechanism).
Pick the country you are actually in and a `channel`/`hw_mode` that is legal there — for
2.4 GHz, `hw_mode=g` with a channel in 1–11 is safe almost everywhere.

Now write a minimal `hostapd.conf` in a scratch location on the board (not yet in the repo —
you are testing it). Include `interface=wlan0`, an `ssid` you will recognise, `hw_mode`,
`channel`, `country_code`, and the WPA2 block (`wpa=2`, `wpa_key_mgmt=WPA-PSK`,
`wpa_passphrase=…`, `rsn_pairwise=CCMP`). Run it in the **foreground with debug**:
`hostapd -d /path/to/hostapd.conf`. Read the output — you should see it set the interface to
AP mode, select the channel, and begin sending beacons. If it exits instead, read *why*: a
country/channel complaint means the regulatory domain and your `channel`/`hw_mode` disagree;
a "could not configure driver mode" or "resource busy" means something else still owns
`wlan0`.

With hostapd beaconing, join from your phone or laptop: the SSID appears in its Wi-Fi list;
select it and enter the passphrase. Watch the hostapd log — you should see the station
authenticate, then associate, then an `AP-STA-CONNECTED` line with the client's MAC. The
client will report "connected, no internet". That is the target state; do not try to fix it.

While hostapd is still running, give `wlan0` its own address so the interface matches the plan:
`ip addr add 192.168.4.1/24 dev wlan0` and confirm with `ip addr show wlan0`. Note that the
client still gets nothing from this — it is the board's address, and the client has no way to
learn an address of its own until lesson 04.

Provoke the instructive failures at least once, so you recognise them later. Stop hostapd,
set the country to `00` or an obviously wrong one, and start again — watch it refuse. Restore
the country, then set `channel` to one not allowed in your band/country (a 5 GHz channel with
`hw_mode=g`, say) and watch it refuse differently. Fix both. These two are the failures you
will hit for real, and they look like "hostapd is broken" until you learn to read them.

Then stop the foreground hostapd (Ctrl-C) and persist. Author the working configuration into
`etc/hostapd/hostapd.conf` in the repo — the same keys you proved live — and add whatever your
setup needs for `wlan0` to carry `192.168.4.1/24` and for hostapd to find its config. Deploy
with `make deploy`. Getting hostapd fully enabled and correctly ordered against networkd for
an unattended boot is finalized in lesson `09-making-it-survive-a-reboot`; here, aim for a config
in the repo that deploys and runs, and a `wlan0` that comes up on `192.168.4.1/24`.

## Completion conditions

- `iw dev` (or `iw dev wlan0 info`) shows `wlan0` in **AP** mode.
- hostapd is running against your configuration and beaconing the SSID — the SSID is visible
  in the Wi-Fi list of a nearby device.
- A phone or laptop **associates** to the network with the passphrase, and the association is
  visible by hand in the hostapd log (an `AP-STA-CONNECTED` line for that client's MAC,
  preceded by the authenticate/associate messages). The client shows "connected, no internet",
  which is expected.
- `ip addr show wlan0` shows `192.168.4.1/24` on `wlan0`.
- The client has **no** IP address of its own — confirm you did not add DHCP, NAT, or a client
  route.
- `etc/hostapd/hostapd.conf` exists in the repo with the keys you proved live, and
  `make deploy` applies it.
- `bash checks/03-ap.sh` passes — it SSHes to the board and confirms hostapd is running and
  `wlan0` is in AP mode. Run it, and confirm the association separately by hand, because the
  check verifies the radio, not that a real client joined.

## On completion, persist

Record in the instance's `STATE.md` (and `DESIGN.md` where it is a durable decision):

- The AP is up: `wlan0` beacons and stations can associate over Wi-Fi.
- The chosen **SSID**, **channel**, **band** (`hw_mode`), and **regulatory country code** —
  later lessons and any debugging need to know exactly what was chosen.
- That `wlan0` carries `192.168.4.1/24` (per `#address-plan`).
- That **clients still receive no address** — a joined client has a link but no IP and no
  internet — and that handing out addresses is lesson `04-handing-out-addresses`, which is next.
- Any regulatory-domain fix you had to make (the country was unset/wrong and how you set it),
  so it is not rediscovered from scratch on the next board.

## Optional deeper paths

- Inspect the beacons from another machine with `iw dev <if> scan` or a monitor-mode capture,
  and find the SSID, channel, and advertised capabilities in the frames themselves.
- Read the difference between `hw_mode=g` and 802.11n/`ieee80211n=1`, and what an `ht_capab`
  line would add — higher throughput, still the same association you already have.
- Hide the SSID (`ignore_broadcast_ssid`) and observe that "hidden" only suppresses the name
  in beacons; it is not security, and the network is trivially discoverable when a client is
  connected.
- Look at `hostapd_cli` as a live control channel to a running hostapd — listing associated
  stations, watching events — without reading the raw log.
