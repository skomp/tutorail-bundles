---
id: 08-a-firewall-with-intent
title: A firewall with intent
design_refs: [interface-roles, recovery-invariant, platform]
validators: [firewall-policy]
supplies:
  - from: lessons/08-a-firewall-with-intent/checks/08-firewall.sh
    to: checks/08-firewall.sh
    describe: "Check for this lesson: default-drop firewall with established/related accepted"
---

## Purpose

The appliance routes and NATs, but it still accepts and forwards far more than
it should — this lesson replaces that accidental openness with a firewall whose
every verdict you can predict before you test it.

Up to now the box has been permissive by default. Anything that arrives at the
upstream interface (`$WAN_IF`) addressed to the appliance is processed; any
packet that can be forwarded is forwarded. That was the right thing while you
were building the data path, because a permissive box never gets in the way of
the feature you are testing. It is the wrong thing now. The upstream interface is
untrusted, and the box offers services — SSH, DNS, DHCP — that have no business
answering the whole world.

A firewall with intent is not a list of blocks. It is a policy derived from what
each interface *is*. You decide, once, what each role is allowed to do, and then
every packet's fate follows from its interfaces. You write the ruleset; the
tutor does not write it for you.

## Prerequisites

- Lesson 01: the discovered interface names, recorded in `board.env` — the
  upstream (WAN) interface as `WAN_IF` and the AP interface as `AP_IF` (usually
  `wlan0`). This lesson assumes `export WAN_IF=<name>` is in your board session,
  so `$WAN_IF` expands to your board's actual upstream (e.g. `end0`) in every
  live `nft` command below.
- Lesson 00: SSH access to the board.
- Lesson 02: the Bluetooth **serial** console. This is the recovery path for
  this lesson and it must work before you touch the firewall. It is
  IP-independent — it does not care whether any firewall rule locks out SSH.
- Lesson 06: NAT with `nftables`, including conntrack. The connection-tracking
  state you met there is what makes a default-drop firewall usable.
- Lesson 07: the `bnep0` management network. That interface is the trusted
  administrative path and the policy treats it as such.
- A working data path: a wlan0 client can reach the internet through the upstream
  interface (`$WAN_IF`).

## Learning objectives

- Explain the difference between the netfilter `input` and `forward` hooks, and
  decide for any packet which of the two questions applies to it.
- Author an `nftables` filter table with `input` and `forward` chains whose
  policy is `drop`, plus explicit accepts.
- Encode the interface roles (untrusted upstream `$WAN_IF`, client wlan0, trusted
  bnep0, local lo) into per-interface `iifname`/`oifname` rules.
- Use a `ct state established,related accept` rule to let replies and existing
  connections through, and explain why the policy is unusable without it.
- Predict the verdict for a given packet before running it, and confirm the
  prediction live.
- Recover an IP lockout through the serial console.

## Theory

**Two questions, two hooks.** A router firewall answers two separate questions,
and netfilter gives you a separate hook for each. Traffic *addressed to the
appliance itself* — an SSH session to the box, a DNS query a client sends to the
box's resolver, a stray probe to the upstream interface (`$WAN_IF`) — passes
through the **`input`** hook.
Traffic *passing through the box* between two interfaces — a client packet on its
way out to the internet — passes through the **`forward`** hook. A packet hits
exactly one of these. Nothing a client sends *to the internet* is ever seen by
`input`; nothing sent *to the box* is ever seen by `forward`. Keeping these two
straight is the whole discipline of the lesson: you protect the box in `input`
and you police transit in `forward`, and the rules for one are not the rules for
the other.

**Default-drop with explicit accepts.** A chain has a *policy* — the verdict for
any packet that reaches the end of the chain without matching a rule. You will
set both chains to `policy drop`. That inverts the mindset: instead of listing
what to block, you list what to *allow*, and everything else falls off the end
and dies. This is the only honest way to reason about a firewall, because the set
of things you forgot to block is unbounded, but the set of things you meant to
allow is small and you can name every member of it.

**Why default-drop is safe to teach here.** Default-drop is exactly where people
lock themselves out — one wrong `input` chain and your SSH session freezes
mid-command. On a remote box that is a site visit. On *this* box it is not,
because your lifeline from lesson 02 is the Bluetooth **serial** console, and a
serial console carries no IP. No `input` rule, no `forward` rule, no policy you
can possibly write touches it. You can drop every IP path to the box, realise
your mistake, open the serial console, and fix the ruleset. That safety net is
what makes it reasonable to experiment with default-drop live rather than
theorising about it — build the console habit before you start.

**conntrack makes it usable — the established/related accept.** In lesson 06 you
watched conntrack record every forwarded flow so that return packets could be
matched and un-NATed. That same table answers a firewall question: *is this
packet part of a conversation the box already decided to allow?* The rule

    ct state established,related accept

accepts any packet belonging to a flow that is already established, plus the
`related` traffic a flow spawns (an ICMP error about an accepted flow, for
example). Put this rule first in each chain and you only ever have to write
accept rules for the *first* packet of a new conversation — the direction you
actually care about. Omit it and the results are baffling: your SSH session dies
the instant you load the ruleset, because the reply packets of your *existing*
connection now match nothing and hit the drop policy. Nearly every "my firewall
broke everything" story is a missing established/related rule.

**Per-interface matching encodes trust.** `iifname` matches the interface a
packet arrived on; `oifname` matches the interface it is leaving by. These are
how the interface roles become rules. `iifname "bnep0" accept` in the `input`
chain says "the management network is trusted to talk to the box".
`iifname "wlan0" oifname "$WAN_IF" accept` in the `forward` chain says "clients
may reach the upstream". Because the default is drop, you never have to write the
inverse — "wlan0 may not reach bnep0" is true simply because you never wrote a
rule allowing it.

**The filter table structure.** You need one table and two chains:

    table inet filter {
        chain input {
            type filter hook input priority 0; policy drop;
            # accepts go here
        }
        chain forward {
            type filter hook forward priority 0; policy drop;
            # accepts go here
        }
    }

`type filter` with `hook input`/`hook forward` attaches the chain to the two
hooks above; `policy drop` sets the fall-through verdict. (You can use family
`inet` or `ip`; this lesson is IPv4 only, so either works — be consistent.) This
is a different table from the `nat` table you wrote in lesson 06; the two
coexist, each on its own hooks, and you keep NAT where it is.

## Concepts to teach

- The `input` hook vs the `forward` hook: traffic *to* the box vs traffic
  *through* it, and why a packet hits exactly one.
- Chain policy, and default-drop as an allow-list discipline.
- The `ct state established,related accept` rule and its tie-back to conntrack in
  lesson 06 — what breaks without it (existing SSH, all replies).
- `iifname`/`oifname` per-interface matching as the encoding of interface roles.
- The interface roles themselves as the source of the whole policy: the upstream
  interface (`$WAN_IF`) untrusted, wlan0 client (NATed out, allowed to send the
  box only what a client needs), bnep0 trusted/management, lo local.
- Why loopback must be accepted explicitly (local services talk to themselves
  over lo; drop it and things quietly break).
- The serial console as the recovery invariant that makes default-drop safe.
- That `input` and `forward` are independent problems — a fix in one is not a fix
  in the other.

## Constraints

- **You write the ruleset. The tutor does not write it for you** and will not
  hand you a finished `nftables.conf` to paste.
- The policy of both the `input` and `forward` chains must be `drop`. No
  `policy accept` with a list of blocks.
- Every accept must be justified by an interface role. If you cannot say which
  role a rule serves, it does not belong.
- Accept `ct state established,related` and loopback before anything else.
- IPv4 only. Do not add IPv6 rules; do not rely on IPv6 behaviour.
- Keep the lesson-06 `nat` table intact. This lesson adds a `filter` table; it
  does not replace NAT.
- Have the serial console open before you set `policy drop` the first time.

## Suggested progression

Build the ruleset live and incrementally, testing each rule's effect before
moving on. Do not author the file first and load it blind.

1. **Open the lifeline.** Connect the lesson-02 Bluetooth serial console and
   confirm you have a shell over it. Leave it open for the rest of the lesson.
   Everything below is safe only because this is running.

2. **See what "no firewall" means.** Before adding anything, look at the current
   ruleset (`nft list ruleset`) and confirm there is no filtering — the box
   accepts and forwards everything. This is the state you are replacing.

3. **Create the filter table and chains with a permissive start.** Add the
   `inet filter` table with `input` and `forward` chains, but begin with
   `policy accept` while you build. This lets you add accept rules and watch them
   match (`nft list ruleset` shows per-rule counters) without risking a lockout
   yet.

4. **Add the two universal accepts to `input`.** First
   `ct state established,related accept`, then accept on `iifname "lo"`. Confirm
   your SSH session and existing connections are unaffected.

5. **Add the role-based `input` accepts.** Accept all input from
   `iifname "bnep0"` (trusted management). From `iifname "wlan0"`, accept only
   what a client legitimately sends the box: DHCP (`udp dport { 67, 68 }`) and
   DNS (`udp dport 53`, and `tcp dport 53` if your resolver serves TCP). Do *not*
   add a blanket wlan0 accept.

6. **Build the `forward` accepts.** `ct state established,related accept` first,
   then `iifname "wlan0" oifname "$WAN_IF" accept` for clients reaching the
   internet. Nothing else — wlan0->bnep0 and every other cross-interface flow has
   no reason to exist and will fall through.

7. **Predict, then flip to drop.** Before you change the policy, write down the
   verdict you expect for each of these, and *why*:
   - a wlan0 client opening a web connection to the internet (forward: accept —
     new wlan0->`$WAN_IF`);
   - a wlan0 client trying to reach a bnep0 admin address (forward: drop — no
     rule);
   - the bnep0 admin host SSHing to the box (input: accept — trusted iifname);
   - a new connection from the upstream interface (`$WAN_IF`) to the box (input:
     drop — no rule, falls to policy).
   Then set both chains to `policy drop`.

8. **Test each prediction live.** From a wlan0 client, confirm internet works and
   the admin address does not answer. From the bnep0 host, confirm SSH to the box
   works. From the upstream side (`$WAN_IF`), confirm a new connection to the box
   is refused.
   Where a verdict surprises you, read the per-rule counters to find which rule
   did or did not match — that is the debugging loop.

9. **Deliberately break it, then recover (optional but recommended).** Remove the
   established/related accept from `input` and reload. Watch your SSH session
   freeze. Recover through the serial console and put the rule back. You now know
   the safety net holds.

10. **Author and deploy.** Only once the live ruleset behaves exactly as
    predicted, write the complete `etc/nftables.conf` to match it, and run
    `make deploy`. That file is loaded by `nftables`, not by a shell, so `$WAN_IF`
    will **not** expand there — write your actual recorded upstream name in place
    of the `<WAN_IF>` placeholder (e.g. `end0`) directly into the `iifname`/
    `oifname` rules. Then re-run your predictions against the deployed box to
    confirm the persisted file and the live ruleset agree.

## Completion conditions

- The `inet filter` table exists with an `input` chain and a `forward` chain,
  both with `policy drop`.
- Both chains accept `ct state established,related` before any other rule, and
  `input` accepts loopback.
- The role-based accepts hold and nothing broader is present: `input` accepts all
  of bnep0 and, from wlan0, only DHCP and DNS to the box; `forward` accepts only
  new wlan0->`$WAN_IF`.
- No new connection from the upstream interface (`$WAN_IF`) to the box is
  accepted; wlan0->bnep0 forwarding is dropped.
- You can state, before testing, the correct verdict and its reason for each of:
  client->internet (accept), client->admin (drop), admin->box (accept), new
  `$WAN_IF`->box (drop) — and the live tests match.
- The lesson-06 `nat` table is still present and NAT still works.
- The policy is persisted in `etc/nftables.conf` and applied with `make deploy`,
  and the deployed ruleset matches what you tested live.
- `bash checks/08-firewall.sh` passes. It confirms both `input` and `forward` are
  default-drop with `established,related` accepted.

## On completion, persist

Record in the instance's DESIGN.md:

- The firewall policy stated in terms of the interface roles, not as a rule dump:
  the upstream interface (`$WAN_IF`) untrusted (no new input, no blanket forward);
  wlan0 client (NATed out via
  forward, allowed to send the box only DHCP and DNS); bnep0 trusted management
  (full input to the box); lo local (accepted). Both chains default-drop with
  established/related accepted first.
- That the recovery path for a firewall lockout is the **lesson-02 Bluetooth
  serial console**, which is IP-independent and therefore unaffected by any
  filter rule — this is why default-drop is safe on this box.
- Note in STATE.md that the policy is now persisted in `etc/nftables.conf` and
  deployed.

## Optional deeper paths

With a firewall that gives every packet a deliberate verdict, two directions open
up. You could turn the appliance's eye outward and inspect the network it serves
— who is connected on wlan0, what they are doing — now that you have a policy to
measure that traffic against. Or you could make the box assert itself to a client
before letting it out, redirecting a new client's first request to a page of your
own. Both build directly on the role-based rules you just wrote; neither is
required to consider the appliance done.
