# Deploy the appliance configuration you author under etc/ to the board.
# Reads BOARD_HOST / BOARD_USER from board.env.
include board.env

BOARD = $(BOARD_USER)@$(BOARD_HOST)

.PHONY: deploy diff restart
## deploy: copy etc/ to the board's /etc and reload the affected units
deploy:
	rsync -a --rsync-path="sudo rsync" etc/ $(BOARD):/etc/
	ssh $(BOARD) 'sudo systemctl daemon-reload && \
	  sudo systemctl reload-or-restart systemd-networkd 2>/dev/null || true; \
	  for u in hostapd dnsmasq nftables; do \
	    sudo systemctl reload-or-restart $$u 2>/dev/null || true; \
	  done'

## diff: show what deploy would change, without changing anything
diff:
	rsync -a --dry-run --itemize-changes --rsync-path="sudo rsync" etc/ $(BOARD):/etc/

## restart: reload the appliance units without copying files
restart:
	ssh $(BOARD) 'sudo systemctl daemon-reload && \
	  for u in systemd-networkd hostapd dnsmasq nftables; do \
	    sudo systemctl reload-or-restart $$u 2>/dev/null || true; \
	  done'
