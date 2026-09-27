#!/usr/bin/env bash
# Installs the jev-seo skill for Claude Code (and Codex, if present) by symlinking.
set -euo pipefail
SRC="$(cd "$(dirname "$0")" && pwd)/skills/jev-seo"
for dir in "$HOME/.claude/skills" "$HOME/.codex/skills"; do
  [ -d "$(dirname "$dir")" ] || continue
  mkdir -p "$dir"
  ln -sfn "$SRC" "$dir/jev-seo"
  echo "linked $dir/jev-seo -> $SRC"
done
command -v uv >/dev/null || echo "Install uv: curl -LsSf https://astral.sh/uv/install.sh | sh"
[ -n "${TYPESAFE_API_KEY:-}" ] || echo "Set TYPESAFE_API_KEY (get one at https://console.typesafe.ai/)"
echo "Done. Restart Claude Code, then ask: 'use jev-seo to classify intent for keywords.csv'"
