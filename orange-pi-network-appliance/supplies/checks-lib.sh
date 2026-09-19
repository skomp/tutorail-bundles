# Sourced by every check script. Provides board.env values and a bssh() helper.
# It is placed at checks/_lib.sh in your workspace; the check scripts sit beside it.
set -euo pipefail

_here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
_root="$(cd "$_here/.." && pwd)"

if [ ! -f "$_root/board.env" ]; then
  echo "FAIL: board.env not found. Copy board.env.template to board.env and fill it in." >&2
  exit 1
fi
# shellcheck source=/dev/null
. "$_root/board.env"

: "${BOARD_HOST:?set BOARD_HOST in board.env}"
: "${BOARD_USER:?set BOARD_USER in board.env}"

# Run a command on the board over SSH, non-interactively.
bssh() { ssh -o BatchMode=yes -o ConnectTimeout=8 "${BOARD_USER}@${BOARD_HOST}" "$@"; }

# Run a command on a Wi-Fi client host, if one is configured (some checks use it).
cssh() {
  : "${CLIENT_HOST:?set CLIENT_HOST in board.env to run this check}"
  : "${CLIENT_USER:?set CLIENT_USER in board.env to run this check}"
  ssh -o BatchMode=yes -o ConnectTimeout=8 "${CLIENT_USER}@${CLIENT_HOST}" "$@"
}

pass() { echo "PASS: $*"; exit 0; }
fail() { echo "FAIL: $*" >&2; exit 1; }
