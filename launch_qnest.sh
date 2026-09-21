#!/usr/bin/env bash
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_NAME="${QNEST_CONDA_ENV:-qoala}"

find_env_python() {
  local candidates=()

  if [[ -n "${QNEST_PYTHON:-}" ]]; then
    candidates+=("${QNEST_PYTHON}")
  fi

  if [[ "${CONDA_DEFAULT_ENV:-}" == "$ENV_NAME" ]] && command -v python >/dev/null 2>&1; then
    candidates+=("$(command -v python)")
  fi

  candidates+=(
    "$HOME/miniforge3/envs/$ENV_NAME/bin/python"
    "$HOME/mambaforge/envs/$ENV_NAME/bin/python"
    "$HOME/miniconda3/envs/$ENV_NAME/bin/python"
    "$HOME/anaconda3/envs/$ENV_NAME/bin/python"
  )

  if [[ -n "${CONDA_EXE:-}" && -x "${CONDA_EXE}" ]]; then
    local base
    base="$(dirname "$(dirname "${CONDA_EXE}")")"
    candidates+=("$base/envs/$ENV_NAME/bin/python")
  fi

  local p
  for p in "${candidates[@]}"; do
    if [[ -n "$p" && -x "$p" ]]; then
      printf '%s\n' "$p"
      return 0
    fi
  done
  return 1
}

PYTHON_BIN=""
if PYTHON_BIN="$(find_env_python)"; then
  :
elif command -v conda >/dev/null 2>&1; then

  echo "QNEST: using Conda environment '$ENV_NAME'..."
  cd "$HERE"
  exec conda run --no-capture-output -n "$ENV_NAME" python app_gui.py
else
  cat >&2 <<EOF
QNEST could not locate the '$ENV_NAME' Python environment.

Expected one of these locations, for example:
  $HOME/miniforge3/envs/$ENV_NAME/bin/python

Your QNEST installation itself is fine; only the launcher could not find its Python.
You can either:
  1. set QNEST_PYTHON=/full/path/to/python, or
  2. initialise Conda/Miniforge in your shell.
EOF
  exit 1
fi

cd "$HERE"
echo "QNEST: launching with $PYTHON_BIN"
exec "$PYTHON_BIN" app_gui.py
