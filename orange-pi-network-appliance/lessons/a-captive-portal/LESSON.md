---
id: a-captive-portal
title: A captive portal
design_refs: [interface-roles, platform]
validators: [portal-redirects]
optional: true
supplies:
  - from: lessons/a-captive-portal/checks/opt-portal.sh
    to: checks/opt-portal.sh
    describe: "Check for this optional lesson: client port 80 is redirected to a splash responder"
---

## Purpose

Make the appliance intercept a client's first web request and answer it with a
splash page of your own — the mechanism behind every hotel and airport login
screen — and learn first-hand why the same trick fails against HTTPS.

Until now the box has treated a client's traffic as something to forward and NAT,
never something to answer on the client's behalf. A captive portal inverts that
for one narrow case: when a new client asks for `http://example.com`, the box
quietly redirects that request to a small web server running on the appliance
itself, which serves a page it never asked for. You have already met the two
netfilter hooks that make this possible — you masquerade in `postrouting` and you
filter in `input` and `forward`. The missing piece is the third: rewriting a
packet's *destination* on the way in. That is the whole lesson, plus an honest
look at the wall you hit the moment the client speaks TLS.

## Prerequisites

This lesson stands alone and is offered, never required. Before you start, the
following must already be true:

- **Lessons 03-06:** a working access point that NATs its clients. A phone or
  laptop associates to `wlan0`, gets a `192.168.4.0/24` lease, and reaches the
  internet through the upstream interface (`$WAN_IF`). If a client cannot browse
  the web, fix that first —
  a portal has nothing to intercept otherwise.
- **Lesson 08:** the `inet filter` firewall with default-drop `input` and
  `forward` chains. You need it here because redirected traffic still has to
  survive the firewall, and a default-drop `input` chain will silently swallow
  the redirected connection unless you allow it.
- **Lesson 02 (recommended):** the Bluetooth serial console. Redirect rules act
  on client traffic, not on your admin path, so the risk is lower than lesson 08
  — but a misplaced rule can still surprise you, and the serial lifeline costs
  nothing to keep open.

You also need a minimal HTTP responder available on the box. Anything that binds
a TCP port and returns a page will do — `python3 -m http.server` from a directory
holding an `index.html`, `busybox httpd`, a two-line `nc` loop, or a small
`socat` listener. Installing it, if it is not already present, is your work.

## Learning objectives

- Explain the difference between source NAT (`postrouting`) and destination NAT
  (`prerouting`), and say which one a captive portal uses and why.
- Write an `nftables` rule that redirects new client TCP connections on port 80
  to a responder listening on the appliance.
- Run a minimal HTTP responder that serves a splash page, and confirm an
  unauthenticated client lands on it.
- Allow the redirected traffic through the lesson-08 firewall, and explain why it
  is dropped without that rule.
- Demonstrate that an HTTPS request is *not* silently intercepted, and explain
  why redirecting a TLS connection produces a certificate error rather than a
  covert splash page.

## Theory

**A third hook: rewriting the destination.** In lesson 06 you rewrote the
*source* address of outgoing packets in the `postrouting` hook, so replies could
find their way back. A captive portal rewrites the *destination* instead, and it
does so as early as possible — in the **`prerouting`** hook, before the kernel
decides where the packet should go. That ordering is the point. If you rewrote
the destination after routing, the kernel would already have chosen to send the
packet out the upstream interface (`$WAN_IF`) toward the real internet. By
changing the destination in
`prerouting`, you change the routing decision itself: a packet the client
addressed to a far-off web server is re-addressed to the box, and the kernel
routes it to a local socket instead of forwarding it.

**`redirect` is destination NAT to the box itself.** `nftables` gives you two
ways to rewrite a destination. `dnat to <address>:<port>` sends the packet to
some specific host. `redirect to :<port>` is the special case that means "to this
box, on this port" — it uses whichever local address the packet arrived toward,
so you do not have to name the appliance's IP. For a captive portal, `redirect`
is exactly right: you want the client's request to land on a server here, on this
machine. The table and chain look like this:

    table ip nat {
        chain prerouting {
            type nat hook prerouting priority dstnat; policy accept;
            iifname "wlan0" tcp dport 80 redirect to :8080
        }
    }

Read the rule literally: a packet arriving on `wlan0`, TCP, destined for port 80,
has its destination rewritten to port 8080 on the box. Everything else falls
through untouched and is routed and NATed as usual. This lives alongside the
`postrouting`/`masquerade` rule from lesson 06 — both are `nat`-family chains,
each on its own hook, and they do not conflict. (Whether you add the `prerouting`
chain to your existing `nat` table or keep a separate one is a style choice; keep
the masquerade rule intact either way.)

**Match narrowly or break everything.** The single most destructive mistake here
is redirecting too much. A rule that omits `tcp dport 80` — or worse, redirects
all of a client's traffic — sends DNS, HTTPS, NTP, every protocol the client
uses, into a web server that speaks none of them. The client's name lookups
fail, its clock will not sync, nothing loads, and the failure looks nothing like
"the portal works." The redirect must be scoped to exactly the plaintext HTTP you
intend to intercept: arriving on the client interface, TCP, destination port 80,
new connections only.

**The responder.** The redirect only moves packets; something has to answer them.
Run a small HTTP server bound to the redirect port (`8080` above) that returns
your splash page for any request. A one-line server is fine —
`python3 -m http.server 8080` from a directory containing `index.html` serves
that file to every client. The responder does not need to understand which URL
the client originally wanted; for this lesson it answers everything with the same
page. (Real portals do parse the request and often issue an HTTP redirect of
their own to a login URL — a deeper path below.)

**The firewall will drop it unless you let it through.** After lesson 08, the
box's `input` chain is default-drop. A redirected packet is now destined *to the
box* on port 8080, so it is an `input`-chain packet — and there is no rule
allowing it, so it dies. This is the confusing failure: the redirect is correct,
the responder is running, and the client still times out, because the firewall
ate the redirected connection. You must add an `input` accept for new connections
from the client interface to the responder port, for example
`iifname "wlan0" tcp dport 8080 ct state new accept`. This is a deliberate
loosening of the lesson-08 policy, scoped to exactly the portal port, and you
should be able to say why it is safe.

**Why HTTPS defeats you — the honest part.** Try the same thing with
`https://example.com` and it does not work, and it *cannot* be made to work
transparently. The reason is TLS. When a client opens an HTTPS connection it
performs a handshake in which the server must present a certificate proving it is
the site the client asked for — `example.com`. Your responder has no such
certificate. If you redirect the TLS connection to your box (by also redirecting
`tcp dport 443`), your server either cannot complete the handshake at all or
presents a certificate for the wrong name, and the client aborts with a
certificate error. There is no way around this that does not involve the client
*already trusting* a certificate authority you control — which is to say, the
client must have been configured, in advance and with the user's knowledge, to
trust you. That is why real captive portals only ever intercept plaintext HTTP,
and why modern operating systems deliberately probe over HTTP (not HTTPS) to
discover a portal exists. The certificate error is not a bug in your setup; it is
TLS doing exactly its job — refusing to let a machine in the middle impersonate a
site it cannot authenticate as. This is the security property the lesson is
really about.

## Concepts to teach

- Destination NAT vs source NAT: `prerouting`/`dstnat` (change where a packet is
  going) vs `postrouting`/`masquerade` (change where it came from), and why a
  portal must act in `prerouting`, before the routing decision.
- `redirect to :<port>` as the "to this box" special case of `dnat`, and why it
  spares you from naming the appliance's own address.
- Scoping the redirect to `iifname "wlan0" tcp dport 80` — and the wreckage that
  follows from redirecting more than that.
- That a redirected packet becomes an `input`-chain packet to the box, so the
  lesson-08 default-drop firewall must explicitly accept the responder port.
- The role of the HTTP responder: it answers the moved connections; it need not
  know the original URL to serve a splash page.
- Why HTTPS cannot be transparently intercepted: TLS requires the server to prove
  it is the requested host, and you hold no certificate for a host you are not.
- That OS portal-detection probes are HTTP by design, precisely because HTTP is
  the only thing a portal can honestly intercept.

## Constraints

- **You write every rule and run every command. The tutor does not write your
  ruleset or your responder for you.**
- The redirect must match narrowly: client interface, TCP, destination port 80,
  new connections. Do not redirect all traffic; do not redirect UDP; do not
  redirect DNS.
- Keep the lesson-06 `masquerade` rule and the lesson-08 `filter` policy intact.
  This lesson adds a `prerouting` redirect and one scoped `input` accept; it does
  not replace NAT or open the firewall wholesale.
- The `input` accept you add must be scoped to the responder port, not a blanket
  accept of the client interface.
- Do **not** attempt to defeat HTTPS by installing a certificate on client
  devices or redirecting port 443 to fake a site. The lesson's point is that you
  cannot transparently intercept TLS; demonstrate that limit, do not paper over
  it.
- This is your own appliance and your own clients. Intercepting traffic is only
  legitimate on a network you operate; do not carry the technique elsewhere.

## Suggested progression

Build the redirect live and watch each stage take effect before persisting.

1. **Confirm the starting point.** From a wlan0 client, load a plain
   `http://` site (many test sites still serve HTTP, e.g.
   `http://neverssl.com`) and confirm it loads normally through the box. This is
   the traffic you are about to intercept.

2. **Start the responder.** On the box, create a directory with an `index.html`
   splash page and start a server on a spare port, e.g.
   `python3 -m http.server 8080`. Confirm it works locally with
   `curl -s http://127.0.0.1:8080/` on the box itself.

3. **Add the redirect rule.** In a `nat` `prerouting` chain (hook priority
   `dstnat`), add `iifname "wlan0" tcp dport 80 redirect to :8080`. Check it is
   loaded with `nft list ruleset`.

4. **Watch it fail on the firewall (instructive).** From the client, request the
   HTTP site again. It will most likely hang or time out — the redirected packet
   is now addressed to the box on 8080 and the lesson-08 `input` policy drops it.
   Confirm the diagnosis by watching the drop: the connection never reaches the
   responder.

5. **Open the responder port in the firewall.** Add
   `iifname "wlan0" tcp dport 8080 ct state new accept` to the `input` chain.
   Request the HTTP site once more — now the client's request lands on your
   splash page regardless of the site it asked for.

6. **Prove HTTPS is not intercepted.** From the client, request an `https://`
   site. Observe that it does *not* silently show your splash page: either it
   loads the real site normally (because you only redirected port 80) or, if you
   experiment with redirecting 443, it fails with a certificate error. Write down
   which you saw and why. Do not pursue a working HTTPS intercept — confirm the
   limit and move on.

7. **Persist and redeploy.** Once the live behaviour is exactly right, write the
   redirect rule into `etc/` (alongside your existing nftables config) and, if
   you want the splash server to come back on boot, add a small responder unit
   there too. Run `make deploy`, then re-test from a client to confirm the
   deployed box behaves like the live one.

## Completion conditions

- A `nat` `prerouting` chain contains a redirect matching exactly
  `iifname "wlan0" tcp dport 80` to your responder port, and nothing broader.
- A minimal HTTP responder is listening on that port on the box and returns your
  splash page.
- The lesson-08 `input` chain has one scoped accept for new connections to the
  responder port, and the rest of the default-drop policy is unchanged.
- From an unauthenticated wlan0 client, an `http://` request to *any* site lands
  on the splash page.
- From the same client, an `https://` request is **not** silently intercepted —
  it either reaches the real site or fails with a visible certificate error, and
  you can explain why TLS makes transparent interception impossible.
- The lesson-06 `masquerade` rule and normal client internet access still work
  for everything you did not redirect.
- The redirect (and optionally the responder unit) is persisted under `etc/` and
  applied with `make deploy`, and the deployed box behaves like your live tests.
- `bash checks/opt-portal.sh` passes. It confirms the client's port 80 is
  redirected and a splash responder is listening.

## On completion, persist

Record in the instance's DESIGN.md:

- The portal mechanism in terms of the hooks: a `prerouting` `redirect` of
  `wlan0` TCP port 80 to a local responder, distinct from the `postrouting`
  masquerade, plus the one scoped `input` accept that lets the redirected traffic
  through the firewall.
- The responder you chose and the port it binds, and where its splash page lives.
- The HTTP-vs-HTTPS finding, stated as a property, not a defeat: plaintext HTTP
  can be transparently intercepted; HTTPS cannot, because TLS requires the server
  to authenticate as the requested host and you hold no certificate for it — this
  is why real portals intercept only HTTP and why OS portal probes use HTTP.

Note in STATE.md that the redirect rule (and any responder unit) is now persisted
under `etc/` and deployed.

## Optional deeper paths

If you want to go further, none of these is required:

- **DNS-based portal detection.** Investigate how phones and laptops discover a
  portal before you ever open a browser — Android fetches
  `connectivitycheck.gstatic.com/generate_204`, Apple devices fetch
  `captive.apple.com`, and a portal is inferred when the expected response does
  not come back. Notice these probes are HTTP, and think about what your redirect
  does to them.
- **Real portals allow, then re-allow.** A production portal does not serve the
  same page forever. It keeps an allowlist and, once a client authenticates,
  changes the ruleset to stop redirecting that client's traffic — often keyed on
  the client's MAC or IP. Sketch how you would add and later remove a per-client
  bypass rule, and where that state would live.
- **The ethics and the law.** Interception is a capability, and the reason it is
  acceptable here is that you own the appliance and the network. Read up on why
  the same technique is off-limits on networks you do not operate, and let that
  boundary — not the technical possibility — decide where you use it.
