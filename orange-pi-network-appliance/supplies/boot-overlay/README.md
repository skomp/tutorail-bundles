# First-boot overlay

Copy the files in this directory onto the boot partition of the freshly flashed
microSD card (the small FAT volume that mounts when you re-insert the card after
flashing). They take effect on the board's first boot.

- `armbian_first_run.txt.example` — rename to `armbian_first_run.txt` on the boot
  partition and edit it. Armbian reads this file once, on first boot, then
  deletes it. It sets the hostname and the Wi-Fi regulatory country, and leaves
  SSH enabled.

Setting the Wi-Fi country here matters: `hostapd` refuses to start with an unset
or wrong regulatory domain, and that failure is confusing when you meet it in
lesson 03. Setting it now means the access-point lesson is about the access
point, not about a reg-domain error.

Nothing here configures routing, NAT, the firewall or Bluetooth. Those are the
course, and you build them yourself.
