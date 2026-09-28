#!/bin/bash
# Guard local de desenvolvimento; nao executa o comando recebido.
ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd) || exit 2
CHECKER="$ROOT/.claude/hooks/check_git_command.py"

for PYTHON in "$ROOT/.venv/Scripts/python.exe" "$ROOT/.venv/bin/python"; do
  if [ -x "$PYTHON" ]; then
    exec "$PYTHON" -I "$CHECKER"
  fi
done
for PYTHON in python3 python; do
  if command -v "$PYTHON" >/dev/null 2>&1; then
    exec "$PYTHON" -I "$CHECKER"
  fi
done
echo "BLOCKED: Python is required to validate this command." >&2
exit 2
