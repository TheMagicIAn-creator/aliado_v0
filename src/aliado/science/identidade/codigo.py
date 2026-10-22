"""A versão do código que rodou (lote 54): o commit do Git e se havia alterações locais em `src` ou no
`pyproject.toml`. Sempre um estado explícito (registrado, git ausente, fora de repositório, pacote fora do repositório
ou erro); o commit e as alterações só existem no estado "registrado"."""

from __future__ import annotations

import subprocess
from pathlib import Path

PACKAGE = Path(__file__).resolve().parents[2]  # .../src/aliado


def _git(*args: str, cwd: Path) -> subprocess.CompletedProcess:
    return subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True, timeout=10,
                          creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))


def code_version(package: str | Path = PACKAGE) -> dict:
    """{"estado", "commit", "alteracoes_locais"} do código em `package` (a pasta `aliado` que está rodando)."""
    package = Path(package).resolve()
    blank = {"commit": None, "alteracoes_locais": None}
    try:
        top = _git("rev-parse", "--show-toplevel", cwd=package)
        if top.returncode != 0:
            return {"estado": "fora de repositório", **blank}
        root = Path(top.stdout.strip()).resolve()
        # Um pacote instalado num ambiente dentro do repositório não é o código do repositório.
        if root / "src" / "aliado" != package:
            return {"estado": "pacote fora do repositório", **blank}
        head = _git("rev-parse", "HEAD", cwd=root)
        status = _git("status", "--porcelain", "--", "src", "pyproject.toml", cwd=root)
    except FileNotFoundError:
        return {"estado": "git ausente", **blank}
    except (OSError, subprocess.SubprocessError):
        return {"estado": "erro", **blank}
    if head.returncode != 0 or status.returncode != 0:
        return {"estado": "erro", **blank}
    return {"estado": "registrado", "commit": head.stdout.strip(), "alteracoes_locais": bool(status.stdout.strip())}
