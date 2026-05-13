#!/bin/zsh
set -euo pipefail

ROOT_DIR="$HOME/Documents/cards_on_tap"
VENV_ACTIVATE="$ROOT_DIR/.venv/bin/activate"
LAUNCHER_APP="$ROOT_DIR/launcher_app.py"
LAUNCHER_PORT="8500"

if [[ ! -f "$VENV_ACTIVATE" ]]; then
  echo "Virtualenv not found at: $VENV_ACTIVATE"
  read -r "?Press Enter to close..."
  exit 1
fi

if [[ ! -f "$LAUNCHER_APP" ]]; then
  echo "Launcher app not found at: $LAUNCHER_APP"
  read -r "?Press Enter to close..."
  exit 1
fi

cd "$ROOT_DIR"
source "$VENV_ACTIVATE"
exec streamlit run "$LAUNCHER_APP" --server.port "$LAUNCHER_PORT"
