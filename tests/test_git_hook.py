"""Envia textos ao hook; nenhum comando Git dos casos é executado."""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def bash():
    executable = shutil.which("bash")
    git = shutil.which("git")
    if not executable and git:
        candidate = Path(git).resolve().parent.parent / "bin/bash.exe"
        if candidate.is_file():
            executable = str(candidate)
    if not executable:
        pytest.skip("Bash indisponível; necessário para testar o launcher do Claude.")
    return executable


def invoke(bash, payload):
    return subprocess.run(
        [bash, str(ROOT / ".claude/hooks/block-dangerous-git.sh")],
        input=payload, capture_output=True, encoding="utf-8", cwd=ROOT, timeout=15,
    )


@pytest.mark.parametrize("command", [
    "git push origin master", "git -C . push origin master",
    "git --no-pager push origin master", "git -c core.autocrlf=false -C . push",
    "git --git-dir=.git push", "git --work-tree . push",
    "git clean -df", "git clean -fdx", "git clean --force -d",
    "git reset HEAD --hard", "git -C . reset --hard HEAD",
    "git restore src/aliado/agent.py", "git checkout -- README.md",
    "git branch -D branch", "git branch -d branch",
    "git status && git -C . push", "git status\ngit push",
    "git status # leitura\ngit push",
    "command -- git push", "env LANG=C git push",
    "bash -c 'git -C . push'", 'powershell -Command "git clean -df"',
    "pwsh -Command git -C . push", "cmd /c git clean -df",
    '& "C:\\Program Files\\Git\\bin\\git.exe" -C . push',
    "git \\\n push", "git `\n push", "echo $(git push)",
])
def test_hook_blocks_direct_and_wrapped_destructive_commands(bash, command):
    result = invoke(bash, json.dumps({"tool_input": {"command": command}}))
    assert result.returncode == 2, (command, result.stderr)


@pytest.mark.parametrize("command", [
    "git status", "git -C . status --short", "git diff --stat",
    "git log -3", "git branch --list", "git clean -nd", "git clean --dry-run",
    "git --help", "git --version", "python -m pytest",
    'echo "git push"', "printf '%s' 'git clean -df'",
    "git log --grep='git push'", "git status # git push",
])
def test_hook_allows_read_only_commands_and_quoted_documentation(bash, command):
    result = invoke(bash, json.dumps({"tool_input": {"command": command}}))
    assert result.returncode == 0, (command, result.stderr)


@pytest.mark.parametrize("command", [
    "echo 'aspas sem fechamento", "sed -n '/## Lote 08/,/^## [^L]/p' README.md | head -30",
    "python -c \"print('ok')\"; grep -n \"| 08|Gemini\" README.md",
])
def test_hook_allows_unparseable_commands_without_git(bash, command):
    result = invoke(bash, json.dumps({"tool_input": {"command": command}}))
    assert result.returncode == 0, (command, result.stderr)


def test_hook_still_blocks_unparseable_commands_mentioning_git(bash):
    result = invoke(bash, json.dumps({"tool_input": {"command": "git push 'aspas sem fechamento"}}))
    assert result.returncode == 2


@pytest.mark.parametrize("payload", ["not json", "{}", '{"tool_input":{"command":null}}'])
def test_invalid_input_is_blocked_without_printing_payload(bash, payload):
    result = invoke(bash, payload)
    assert result.returncode == 2
    assert payload not in result.stderr


def test_hook_does_not_echo_secrets_when_blocking(bash):
    result = invoke(bash, json.dumps({"tool_input": {"command": "git push https://secret-token@example.test/r"}}))
    assert result.returncode == 2
    assert "secret-token" not in result.stdout + result.stderr
