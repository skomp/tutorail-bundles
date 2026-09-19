# Appliance configuration

This repository holds the configuration for a headless Orange Pi Zero 3 network
appliance, built up lesson by lesson.

- `etc/` — the configuration you author. It mirrors the board's `/etc`, so
  `etc/systemd/network/…`, `etc/hostapd/…`, `etc/nftables.conf` and so on.
- `board.env` — how tools reach your board (host and user). Not committed with
  real values if you would rather keep them local.
- `checks/` — the check scripts a lesson runs to confirm the board is in the
  state the lesson asked for. You run them; they inspect the board's live state.
- `Makefile` — `make deploy` copies `etc/` to the board and reloads the affected
  units. `make diff` shows what a deploy would change first.
- `FLASH.md` — how the board was flashed and first-booted, for reference.

The workflow every lesson uses: do the mechanism live on the board first, watch
it work, then author it into `etc/` here and `make deploy` it so it survives a
reboot.
