#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
if [ -z "${SDL_VIDEODRIVER:-}" ] && [ -z "${DISPLAY:-}" ] && [ -z "${WAYLAND_DISPLAY:-}" ]; then
  export SDL_VIDEODRIVER=kmsdrm
fi
export SDL_AUDIODRIVER="${SDL_AUDIODRIVER:-alsa}"
if [ -x .venv/bin/python ]; then
  exec .venv/bin/python -m handy.main
fi
exec python3 -m handy.main
