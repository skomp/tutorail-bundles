# Flashing and first boot — a checklist, not a lesson

You do this once, before lesson 00. Nothing here teaches networking, so the
course does not spend a lesson on it; it is a checklist you follow and tick off.
If any step fails, that is a flashing problem, not a course exercise.

## What you need

- An Orange Pi Zero 3 and a microSD card (8 GB or larger).
- A USB-C power supply that can deliver enough current (a phone charger is often
  not enough; a 5 V / 2–3 A supply is safe).
- An Ethernet cable into a network that hands out addresses by DHCP.
- A card reader on your own machine.

## Steps

1. **Download an Armbian image** for the Orange Pi Zero 3 (a current stable
   "minimal" or "server" build is ideal — you do not need a desktop).
2. **Flash it** to the microSD card with a tool you trust (balenaEtcher,
   Raspberry Pi Imager, or `dd` if you know the device node). Verify after write.
3. **Apply the first-boot overlay.** After flashing, the boot partition mounts as
   a small FAT volume. Copy the contents of the `boot-overlay/` directory from
   this workspace onto it, following `boot-overlay/README.md`. This is what
   enables SSH on first boot and sets the Wi-Fi regulatory country early, so the
   access-point lessons work later.
4. **Insert the card, connect Ethernet, apply power.** The first boot takes
   longer than later ones (it expands the filesystem). Give it two minutes.
5. **Do not look for it yet.** Finding the board on the network is lesson 00, and
   it is the first thing the course actually teaches. Come back here only if the
   board never appears at all after several minutes — that is a flashing problem.

## If the board never appears

- Re-seat the card and re-flash; a bad write is the usual cause.
- Try a different power supply; an under-powered board boots erratically.
- Confirm the Ethernet link light is on at both ends.
