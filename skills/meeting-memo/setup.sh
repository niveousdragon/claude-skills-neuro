#!/usr/bin/env bash
# Sets up everything meeting-memo needs on a clean macOS or Linux machine:
# Python 3, pandoc, faster-whisper and the speech model. Safe to run again.
#
# Run:  bash setup.sh
set -euo pipefail
here="$(cd "$(dirname "$0")" && pwd)"

install_pkg() {  # $1 = brew name, $2 = apt name
    if command -v brew >/dev/null; then brew install "$1"
    elif command -v apt-get >/dev/null; then sudo apt-get update && sudo apt-get install -y "$2"
    else echo "[FAILED] no brew or apt-get: install $1 by hand, then rerun"; exit 1
    fi
}

command -v python3 >/dev/null || install_pkg python python3-pip
echo "[OK] $(python3 --version)"

command -v pandoc >/dev/null || install_pkg pandoc pandoc
echo "[OK] $(pandoc --version | head -1)"

echo "[..] installing faster-whisper"
# --user avoids touching the system Python; newer distros refuse a global install.
python3 -m pip install --user --upgrade --quiet faster-whisper \
  || python3 -m pip install --user --upgrade --quiet --break-system-packages faster-whisper
echo "[OK] faster-whisper installed"

echo "[..] downloading the speech model on first run (about 1.6 GB), then a self-test"
# If huggingface.co is unreachable, export HF_ENDPOINT=<mirror> and rerun.
python3 "$here/transcribe.py" --check
echo "[OK] meeting-memo is ready"
