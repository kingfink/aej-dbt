#!/usr/bin/env bash
set -euo pipefail

export PATH="$HOME/.local/bin:$PATH"
mkdir -p "$HOME/.local/bin"

if ! command -v rg >/dev/null 2>&1; then
  sudo apt-get update \
    -o Dir::Etc::sourcelist="sources.list.d/debian.sources" \
    -o Dir::Etc::sourceparts="-"
  sudo apt-get install -y ripgrep
fi

if ! command -v uv >/dev/null 2>&1; then
  curl -LsSf https://astral.sh/uv/install.sh | sh
fi

if ! command -v dbt >/dev/null 2>&1; then
  bash scripts/install-dbt-fusion "$HOME/.local/bin"
fi

if ! command -v wizard >/dev/null 2>&1; then
  bash scripts/install-dbt-wizard "$HOME/.local/bin"
fi

uv sync --locked

bash scripts/dbt-deps
bash scripts/dbt-parse
