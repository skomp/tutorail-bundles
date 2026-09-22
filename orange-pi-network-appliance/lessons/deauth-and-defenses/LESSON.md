---
id: deauth-and-defenses
title: Deauthentication and defences
design_refs: [interface-roles, platform]
validators: [deauth-observed]
optional: true
supplies:
  - from: lessons/deauth-and-defenses/checks/opt-deauth.sh
    to: checks/opt-deauth.sh
    describe: "Check for this optional lesson: hostapd has protected management frames enabled"
---

## Purpose

A plain WPA2 access point can be knocked off the air by anyone with a nearby radio, and no
firewall you have built can stop it — because the attack happens a layer below IP. In this
lesson you learn why, on your own AP, and you turn on the one hostapd feature that actually
defends against it: Protected Management Frames.

## Prerequisites

A working, persisted access point run by hostapd — lesson `03-bring-up-an-ap` for the radio
and lesson `09-making-it-survive-a-reboot` for the persisted `etc/hostapd/hostapd.conf` that
survives a reboot. You edit that same config here, so it must already exist in the repo and
deploy cleanly with `make deploy`. An SSH session on the board, or the serial lifeline from
lesson `02-the-lifeline`, so that if a Wi-Fi change disturbs your own connection you are not
locked out.

To *observe* the attack you need a **second Wi-Fi radio that supports monitor mode** — a
USB Wi-Fi adapter with a driver capable of monitor mode, on the board or on a nearby laptop.
This is a real hardware requirement, and many cheap adapters cannot do it. The observation is
optional: **the defence can be enabled, deployed, and checked without any second radio**, and
that is the required part of the lesson. If you have no monitor-mode radio, skip the
observation steps and do the defence.

This is a defensive lesson on **your own access point only**. You disrupt a network you
control, to understand a weakness in it, so you can close it. Nothing here is a procedure for
interfering with anyone else's network.

## Learning objectives

- Explain that 802.11 has three frame classes — management, control, and data — and that
  beacons, association, and *deauthentication* are all management frames
- Explain why, in the original 802.11 standard, deauthentication frames are **unauthenticated**:
  any radio can forge a frame that claims to be the AP (or the client) and orders a
  disconnect, and the receiver obeys it
- Locate the attack at the **802.11 link layer**, and explain why nothing in your nftables
  ruleset or any IP-layer control can see or stop it — it disconnects the client before IP is
  ever involved
- Explain what **Protected Management Frames (PMF, 802.11w)** do: they authenticate management
  frames so that a forged deauth is rejected instead of obeyed
- Enable PMF in hostapd with `ieee80211w`, and explain the difference between `ieee80211w=1`
  (optional/capable) and `ieee80211w=2` (required)
- State honestly what PMF does and does not do: it protects against the deauth/disassociation
  attack specifically, it requires client support, and `=2` will refuse clients that lack it

## Theory

An 802.11 network carries three kinds of frames. **Data frames** carry the actual payload —
the packets your IP stack sees. **Control frames** are tiny coordination frames (acknowledgements
and the like). **Management frames** run the membership of the network itself: beacons that
advertise it, probe requests and responses, authentication and association when a client joins,
and — the one this lesson is about — **deauthentication** and disassociation when a client
leaves. A deauthentication frame is a management frame that says, in effect, "this station is
no longer authenticated; drop the connection."

Here is the flaw. In the original standard, management frames are sent **in the clear and
unauthenticated**, even on a WPA2 network whose *data* is fully encrypted. Encryption protects
what you send once you are joined; it does not protect the join-and-leave signalling. A
deauthentication frame carries a source address, a destination address, and a reason code, and
that is all a receiver checks. It does not verify that the frame genuinely came from the AP or
the client it claims to be from. So any nearby radio can **forge** a deauth frame — put the
AP's address in the "from" field and a client's address in the "to" field — and send it. The
client receives what looks like a lawful order from its own access point and disconnects. Send
these frames repeatedly and the client cannot stay associated: the network is, for that client,
knocked off the air. The AP is still beaconing perfectly; the client just keeps being told to
leave.

The reason your firewall is useless against this is worth stating plainly, because the instinct
is exactly wrong. Everything you built in lessons 06 and 08 — NAT, the intent-based nftables
ruleset — operates on **IP packets**, at layer 3 and above. A deauth attack never produces an
IP packet. It operates at the **802.11 link layer** (layer 2), and it takes the client down
*before* any IP traffic exists to be filtered. There is no packet for nftables to drop, no
address for a rule to match. This is not a gap in your ruleset; it is the wrong layer entirely.
The defence has to live where the attack lives — in the 802.11 protocol, in hostapd.

That defence is **Protected Management Frames (PMF)**, standardised as **802.11w** and enabled
in hostapd with the key **`ieee80211w`**. PMF adds cryptographic protection to the
management frames that matter — in particular, deauthentication and disassociation — using keys
established during the WPA handshake. With PMF in effect, a deauth frame that was not produced
by the genuine peer fails its integrity check and is **discarded** rather than obeyed. The
forged flood becomes noise. hostapd accepts three values: `ieee80211w=0` disables it,
`ieee80211w=1` makes it **optional** (clients that support PMF use it; clients that do not still
connect, unprotected), and `ieee80211w=2` makes it **required** (every client must support PMF
or it is refused association).

Be honest about the limits, because overselling PMF is its own instructive failure. PMF closes
the **deauthentication/disassociation** attack; it does not make Wi-Fi immune to every radio-layer
disruption — an attacker can still jam the raw spectrum, which is a different, cruder problem no
protocol setting fixes. PMF also requires **client support**: PMF has been widespread since
around 2018, but an old phone, laptop, or IoT device may not implement it. Choose `=1` and you
protect the clients that can while still admitting the ones that cannot; choose `=2` and you get
the strongest guarantee at the cost of shutting out any client that lacks PMF — which, on an
appliance serving a mix of devices, may lock something out silently. This is why WPA3 exists in
part: **WPA3 mandates PMF**, removing the choice, which is the direction the standard is moving.

## Concepts to teach

The three 802.11 frame classes (management, control, data) and where deauthentication sits —
a management frame, in the same family as beacons and association; the fact that WPA2 encrypts
**data** but leaves **management frames unauthenticated** in the original standard, so a full
WPA2 passphrase does nothing to stop a forged deauth; how a deauth attack works conceptually —
a spoofed source address and a reason code the receiver obeys without verifying origin — and
that it disrupts the client, not the AP, which keeps beaconing; the crucial layering point,
that this is a **layer-2 / 802.11** attack and therefore **invisible and unreachable to
nftables and every IP-layer control**, so the firewall genuinely cannot help; Protected
Management Frames / 802.11w as the defence, and the hostapd key `ieee80211w`; the meaning of
`ieee80211w=1` (optional) versus `=2` (required) and the trade-off between coverage and
compatibility; and the honest limits — PMF addresses deauth/disassociation specifically, needs
client support, does not stop raw jamming, and is mandatory under WPA3.

## Constraints

- Everything you do here is on **your own AP**. The observation, if you do it, is of *your*
  network being disrupted by *you*. Do not point any of this at a network you do not own.
- You edit the **persisted** hostapd config — `etc/hostapd/hostapd.conf` in the repo — and
  deploy it with `make deploy`. Do not leave PMF as a live-only tweak that a reboot loses; the
  whole point is a persisted defence.
- The tutor states the key and checks the result; **you** write the `ieee80211w` line into the
  config yourself. The tutor never writes your configuration.
- Do not try to defend against deauth with nftables, a route, or any IP-layer control. If you
  find yourself reaching for the firewall, that is the wrong-layer failure this lesson is about
  — stop and name it.
- The AP must keep working for your real clients after the change. If you choose
  `ieee80211w=2`, confirm the devices you actually rely on can still associate before you treat
  the lesson as done; a defence that locks out your own phone is not finished.
- Any monitor-mode observation uses a **second** radio. Do not tear `wlan0` out of AP mode to
  observe — that would take your own AP down and defeats the exercise.

## Suggested progression

Understand the layer first, then observe if you can, then persist the defence.

Start by locating the attack. With the tutor, walk the frame classes and confirm for yourself
where deauthentication sits and why WPA2's data encryption does not touch it. Then answer the
question the lesson turns on: could anything in your nftables ruleset stop a deauth? Reason it
through — a deauth produces no IP packet, so there is nothing to match — until you can say
plainly that this is a layer-2 problem and the firewall is the wrong tool. That conclusion is
the point of the lesson; do not move on until it is yours.

If you have a monitor-mode radio, observe your own AP under stress (optional). Put the second
radio into monitor mode and watch the management frames around your AP — you will see beacons
going out and, when a client joins, the authentication and association exchange. This is the
observational half: seeing that management frames are ordinary, visible, spoofable frames, not
some protected inner channel. Keep this conceptual and on your own network. If you have no such
radio, skip straight to the defence — it is the required work.

Now enable the defence. Open the running hostapd config you persisted in lesson 09 and add
`ieee80211w`. Decide `=1` or `=2` deliberately: `=1` protects PMF-capable clients while still
admitting older ones, `=2` requires PMF of everyone. For an appliance that may serve mixed
devices, `=1` is the safe default; choose `=2` only if you know every client supports it.
Note that some WPA setups pair PMF with SAE/WPA3 keying, but on a WPA2-PSK network
`ieee80211w=1` on top of your existing `wpa=2` block is the change you need. Test it live first
if you like — restart hostapd against the edited config and reconnect a client to confirm it
still associates — but the durable step is to keep the line in `etc/hostapd/hostapd.conf`.

Persist and deploy. With the `ieee80211w` line in the repo copy of the config, run `make
deploy`, then restart hostapd on the board so the running instance picks up the change. Confirm
a real client — your phone, your laptop — still joins and reaches the internet through the
appliance; if you chose `=2`, confirm *every* client you care about still joins.

Surface the instructive failures at least once, so you recognise them. First, the wrong-layer
reflex: before enabling PMF, note that no firewall rule you could write would help — say why.
Second, the false sense of safety: a plain WPA2 AP *without* `ieee80211w` resists a forged
deauth not at all, however strong its passphrase — PMF is a separate switch, and encryption is
not it. Third, the compatibility trap: if you reach for `=2`, name the risk that an old client
will be refused silently, and check for it rather than discovering it as a mystery outage later.

## Completion conditions

- The `deauth-observed` validator passes — it confirms the deployed hostapd configuration has
  `ieee80211w` enabled (PMF is on).
- `etc/hostapd/hostapd.conf` in the repo contains the `ieee80211w` key you added (`1` or `2`),
  and the value on the board matches, applied through `make deploy` — not a live-only edit.
- hostapd is running against that configuration, and a real client still **associates** to the
  AP and reaches the internet through the appliance after the change. If you chose
  `ieee80211w=2`, every client you rely on still joins.
- You can explain, in your own words, why a deauthentication attack is a **link-layer** problem
  and why **no nftables rule** could stop it — the wrong-layer point, stated correctly.
- You can state what PMF does (protects management frames so forged deauths are rejected) and
  what it does not do (it needs client support, it does not stop raw jamming, `=2` refuses
  non-PMF clients).
- (Optional, only with a monitor-mode radio) You observed your own AP's management frames and
  can describe what a deauth frame is at the frame level.

## On completion, persist

Record in the instance's `DESIGN.md`/`STATE.md`:

- Protected Management Frames are enabled on the AP: `ieee80211w=<1 or 2>` is present in the
  persisted `etc/hostapd/hostapd.conf` and deployed, and **which** value was chosen and why
  (optional for mixed clients, required if all clients support PMF).
- That deauthentication is an **802.11 link-layer (layer-2) attack**, invisible and unreachable
  to nftables and every IP-layer control — so the defence is a hostapd/802.11w setting, not a
  firewall rule. This is the fact most worth not rediscovering.
- Any client that could not associate under `ieee80211w=2` (if you tried it), so a future
  session does not treat a PMF compatibility refusal as a random failure.

## Optional deeper paths

- Read how 802.11w actually protects a frame: the SA Query mechanism and the management-frame
  integrity/encryption keys (IGTK) derived in the handshake, and how a spoofed deauth fails
  the integrity check.
- Follow the PMF **negotiation**: how a client and AP advertise PMF capability in the RSN
  information element, and how `ieee80211w=1` lets a capable client opt in while a legacy client
  falls back to no protection.
- Look at why **WPA3 mandates PMF** — the transition from WPA2-PSK to WPA3-SAE, and what
  `wpa_key_mgmt=SAE` alongside `ieee80211w=2` would change on this same AP.
- Compare the deauth attack to raw **jamming**: why PMF closes the former and nothing at the
  protocol layer closes the latter, and what that says about the limits of a link-layer defence.
