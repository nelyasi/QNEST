#!/usr/bin/env bash
set -euo pipefail

MODEL="${1:-qwen3:8b}"
ENDPOINT="${QNEST_OLLAMA_ENDPOINT:-http://127.0.0.1:11434}"

printf '\nQNEST local AI setup\n====================\n'
printf 'Model: %s\n' "$MODEL"
printf 'Endpoint: %s\n\n' "$ENDPOINT"

if ! command -v ollama >/dev/null 2>&1; then
  cat <<'EOF'
Ollama is not installed.

Install Ollama from its official installer, then run this script again.
macOS users can also install it with Homebrew if they already use Homebrew:

  brew install --cask ollama

QNEST does not auto-install or upload anything on your behalf.
EOF
  exit 1
fi

if ! curl -fsS "$ENDPOINT/api/tags" >/dev/null 2>&1; then
  echo "Starting Ollama in the background..."
  nohup ollama serve >"${TMPDIR:-/tmp}/qnest_ollama.log" 2>&1 &
  sleep 2
fi

echo "Pulling $MODEL (this can take a while the first time)..."
ollama pull "$MODEL"

echo
if curl -fsS "$ENDPOINT/api/tags" >/dev/null 2>&1; then
  echo "✓ Ollama is reachable at $ENDPOINT"
  echo "✓ QNEST can use model: $MODEL"
  echo
  echo "Open QNEST → Settings → AI Assistant → Test connection."
else
  echo "Ollama was installed but QNEST could not reach $ENDPOINT."
  echo "Try running: ollama serve"
  exit 2
fi
