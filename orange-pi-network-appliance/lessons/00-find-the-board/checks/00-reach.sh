#!/usr/bin/env bash
# board-reachable: a non-interactive (key-based) SSH session opens to the board.
. "$(dirname "$0")/_lib.sh"
require_board
pass "${BOARD_USER}@${BOARD_HOST} is reachable over key-based SSH"
