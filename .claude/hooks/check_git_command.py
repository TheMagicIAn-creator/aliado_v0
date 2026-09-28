"""Guard conservador de comandos Git literais, exclusivo do Claude Code.

Nao e um interpretador nem uma sandbox: aliases, scripts externos e execucao
dinamica exigem revisao pelo assistente. Nunca executa ou imprime o payload.
"""

from __future__ import annotations

import json
import re
import shlex
import sys

VALUE_OPTIONS = {"-C", "-c", "--git-dir", "--work-tree", "--namespace", "--config-env"}
FLAG_OPTIONS = {
    "--no-pager", "--paginate", "-P", "-p", "--bare", "--no-replace-objects",
    "--literal-pathspecs", "--glob-pathspecs", "--noglob-pathspecs",
    "--icase-pathspecs", "--no-optional-locks", "--no-lazy-fetch",
}
ASSIGNMENT = re.compile(r"[A-Za-z_][A-Za-z0-9_]*=")
SEPARATORS = frozenset(";&|()<>")


def git_blocked(args: list[str]) -> bool:
    """Separa opcoes globais da operacao; uma opcao desconhecida bloqueia."""
    index = 0
    while index < len(args):
        arg = args[index]
        if arg in {"--help", "--version"}:
            return False
        if arg in VALUE_OPTIONS:
            if index + 1 >= len(args):
                return True
            index += 2
        elif arg in FLAG_OPTIONS or any(
            arg.startswith(option + "=") for option in VALUE_OPTIONS if option.startswith("--")
        ) or (arg.startswith(("-C", "-c")) and len(arg) > 2):
            index += 1
        elif arg.startswith("-"):
            return True
        else:
            break
    if index == len(args):
        return False
    operation, tail = args[index], args[index + 1:]
    # Depois de -- os nomes de arquivos nao sao opcoes.
    options = tail[:tail.index("--")] if "--" in tail else tail
    short = [arg[1:] for arg in options if arg.startswith("-") and not arg.startswith("--")]
    if operation in {"push", "restore", "checkout"}:
        return True
    if operation == "reset":
        return "--hard" in options
    if operation == "clean":
        return not ("--dry-run" in options or any("n" in arg for arg in short))
    if operation == "branch":
        return "--delete" in options or any("d" in arg or "D" in arg for arg in short)
    return False


def segment_blocked(tokens: list[str], depth: int) -> bool:
    while tokens and (tokens[0] in {"command", "exec", "env", "--", "then", "do", "else"}
                      or ASSIGNMENT.match(tokens[0])):
        tokens = tokens[1:]
    if not tokens:
        return False
    executable = tokens[0].replace("\\", "/").rsplit("/", 1)[-1].lower()
    if executable in {"git", "git.exe"}:
        return git_blocked(tokens[1:])
    shells = {"bash", "sh", "zsh", "dash", "powershell", "pwsh", "cmd"}
    if executable.removesuffix(".exe") in shells:
        for index, token in enumerate(tokens[1:], 1):
            flag = token.lower()
            if flag in {"-command", "/c"} or (
                flag.startswith("-") and not flag.startswith("--") and "c" in flag[1:]
                and executable.removesuffix(".exe") in {"bash", "sh", "zsh", "dash"}
            ):
                if index + 1 == len(tokens):
                    return True
                script = tokens[index + 1]
                if executable.removesuffix(".exe") in {"powershell", "pwsh", "cmd"} and index + 2 < len(tokens):
                    script = shlex.join(tokens[index + 1:])
                return command_blocked(script, depth + 1)
    return False


def command_blocked(command: str, depth: int = 0) -> bool:
    if depth > 8:
        return True
    command = re.sub(r"(?:\\|`)\r?\n", "", command)
    # Aspas que atravessam linhas e sintaxe nao analisavel bloqueiam na duvida.
    # Separar linhas tambem preserva a fronteira apos comentarios de shell.
    for line in command.splitlines():
        lexer = shlex.shlex(line, posix=True, punctuation_chars=";&|()<>")
        lexer.whitespace_split = True
        segment: list[str] = []
        for token in lexer:
            if token and all(char in SEPARATORS for char in token):
                if segment_blocked(segment, depth):
                    return True
                segment = []
            else:
                segment.append(token)
        if segment_blocked(segment, depth):
            return True
    return False


def main() -> int:
    try:
        payload = json.load(sys.stdin)
        command = payload["tool_input"]["command"]
        if not isinstance(command, str) or not command.strip():
            raise ValueError("missing command")
        # Sem menção a git, nada a proteger: evita bloquear leituras de sintaxe complexa.
        blocked = "git" in command.lower() and command_blocked(command)
    except (ValueError, TypeError, KeyError, RecursionError):
        blocked = True
    if blocked:
        print("BLOCKED: Git guard rejected this command or could not validate its syntax. "
              "Review the operation with the researcher.", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
