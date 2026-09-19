#!/usr/bin/env bash
# board-reachable: the board answers a shell over SSH using board.env.
. "$(dirname "$0")/_lib.sh"
out="$(bssh 'echo ok' 2>/dev/null || true)"
[ "$out" = "ok" ] || fail "no SSH shell on ${BOARD_USER}@${BOARD_HOST} — is the host/user in board.env right?"
pass "${BOARD_USER}@${BOARD_HOST} answered over SSH"
