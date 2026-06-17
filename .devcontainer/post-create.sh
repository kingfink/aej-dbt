#!/usr/bin/env bash
set -euo pipefail

export PATH="$HOME/.local/bin:$PATH"
mkdir -p "$HOME/.local/bin"

if ! command -v uv >/dev/null 2>&1 ||
  ! command -v dbt >/dev/null 2>&1 ||
  ! command -v wizard >/dev/null 2>&1 ||
  ! command -v rg >/dev/null 2>&1 ||
  [[ ! -x .venv/bin/python ]]; then
  bash .devcontainer/update-content.sh
fi

bash scripts/configure-dbt-wizard "$PWD"
