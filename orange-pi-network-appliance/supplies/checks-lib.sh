# Sourced by every check script. Provides board.env values and SSH helpers.
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

# Run a command on the board over SSH, non-interactively (key-based; see require_board).
bssh() { ssh -o BatchMode=yes -o ConnectTimeout=8 "${BOARD_USER}@${BOARD_HOST}" "$@"; }

# Run a command on a Wi-Fi client host, if one is configured (some checks use it).
cssh() {
  : "${CLIENT_HOST:?set CLIENT_HOST in board.env to run this check}"
  : "${CLIENT_USER:?set CLIENT_USER in board.env to run this check}"
  ssh -o BatchMode=yes -o ConnectTimeout=8 "${CLIENT_USER}@${CLIENT_HOST}" "$@"
}

pass() { echo "PASS: $*"; exit 0; }
fail() { echo "FAIL: $*" >&2; exit 1; }

# Confirm a non-interactive (key-based) SSH session opens to the board, and if it does
# not, show SSH's OWN error and say what actually causes it. The checks connect with
# BatchMode, which never prompts, so key auth (set up in lesson 00) must already work.
require_board() {
  local err
  if err="$(ssh -o BatchMode=yes -o ConnectTimeout=8 "${BOARD_USER}@${BOARD_HOST}" true 2>&1)"; then
    return 0
  fi
  echo "FAIL: cannot open a non-interactive SSH session to ${BOARD_USER}@${BOARD_HOST}." >&2
  echo "  ssh said: ${err}" >&2
  case "$err" in
    *"Permission denied"*|*"Too many authentication failures"*|*"publickey"*)
      echo "  cause: key-based SSH is not set up. The checks use BatchMode and cannot type a" >&2
      echo "         password; lesson 00 installs your public key on the board (ssh-copy-id)." >&2 ;;
    *"Host key verification failed"*|*"REMOTE HOST IDENTIFICATION"*|*"known_hosts"*|*"host key"*)
      echo "  cause: the host key for '${BOARD_HOST}' is not accepted. Connect once interactively" >&2
      echo "         to this EXACT BOARD_HOST value, accept the key, then re-run." >&2 ;;
    *"Connection refused"*|*"timed out"*|*"No route to host"*|*"Could not resolve"*|*"Name or service not known"*)
      echo "  cause: the board is not reachable at this host. Re-check BOARD_HOST/BOARD_USER." >&2 ;;
  esac
  exit 1
}
