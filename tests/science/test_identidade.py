"""A identidade de uma rodada (lote 54): os hashes, o contrato dos arquivos e a versão do código, sem domínio."""

from __future__ import annotations

import hashlib
import shutil
import subprocess

import pytest

from aliado.science.identidade import codigo
from aliado.science.identidade.codigo import code_version
from aliado.science.identidade.contrato import (
    CONTRACT,
    ContractViolationError,
    check_version,
    require,
)
from aliado.science.identidade.hashes import arrays_digest, config_digest, sha256_file


def test_file_and_config_hashes_match_hashlib(tmp_path):
    """EXP-13: o hash de arquivo lê em blocos e dá o mesmo valor do SHA-256 do conteúdo inteiro."""
    data = bytes(range(256)) * (5 * 1024 + 7)  # mais de 1 MiB, sem caber num bloco só
    path = tmp_path / "grande.bin"
    path.write_bytes(data)
    assert len(data) > 1024 * 1024 and sha256_file(path) == hashlib.sha256(data).hexdigest()
    config = {"b": [2, 3], "a": 1}
    assert config_digest(config) == hashlib.sha256(b'{"a": 1, "b": [2, 3]}').hexdigest() == config_digest(dict(sorted(config.items())))


def test_the_arrays_digest_follows_the_content_not_the_file(tmp_path):
    """EXP-13: o código da matriz vem do conteúdo; regravada, ela dá o mesmo valor, e qualquer mudança o altera."""
    np = pytest.importorskip("numpy")
    arrays = {"b": np.arange(6, dtype=np.float32).reshape(2, 3), "a": np.ones(4, dtype=np.float32)}
    first, second = tmp_path / "um.npz", tmp_path / "dois.npz"
    np.savez_compressed(first, **arrays)
    np.savez_compressed(second, **dict(reversed(arrays.items())))
    with np.load(first) as one, np.load(second) as two:
        assert arrays_digest(dict(one)) == arrays_digest(dict(two)) == arrays_digest(arrays)
    changed = arrays | {"a": np.array([1, 1, 1, 1.0000001], dtype=np.float32)}
    assert arrays_digest(changed) != arrays_digest(arrays)
    assert arrays_digest(arrays | {"a": arrays["a"].astype(np.float64)}) != arrays_digest(arrays)
    assert arrays_digest(arrays | {"b": arrays["b"].reshape(3, 2)}) != arrays_digest(arrays)


def test_the_contract_requires_every_field_and_a_known_version():
    """EXP-13: sem valor padrão silencioso; o erro diz o que falta e continua sendo um ValueError."""
    with pytest.raises(ContractViolationError, match="faltam os campos do contrato pesos, janela"):
        require({"contrato": 1, "variaveis": []}, ("contrato", "pesos", "variaveis", "janela"), "erros.npz")
    require({"contrato": 1}, ("contrato",), "erros.npz")
    assert check_version({}, "x") is None and check_version({"contrato": None}, "x") is None
    assert check_version({"contrato": CONTRACT}, "x") == CONTRACT
    with pytest.raises(ContractViolationError, match="versão 2"):
        check_version({"contrato": 2}, "x")
    assert issubclass(ContractViolationError, ValueError)


def _git(cwd, *args) -> str:
    return subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True, check=True).stdout.strip()


def test_the_code_version_is_always_an_explicit_state(tmp_path, monkeypatch):
    """EXP-13: o commit e as alterações locais só existem no estado "registrado"; os outros estados não supõem nada."""
    if shutil.which("git") is None:
        pytest.skip("Sem o git neste computador.")
    monkeypatch.setenv("GIT_CEILING_DIRECTORIES", str(tmp_path))  # a busca do repositório não sobe além da pasta do teste
    blank = {"commit": None, "alteracoes_locais": None}
    loose = tmp_path / "solta" / "src" / "aliado"
    loose.mkdir(parents=True)
    assert code_version(loose) == {"estado": "fora de repositório", **blank}

    repo = tmp_path / "repo"
    package = repo / "src" / "aliado"
    package.mkdir(parents=True)
    (package / "x.py").write_text("x = 1\n", encoding="utf-8")
    _git(repo, "init", "-q")
    _git(repo, "add", "src")
    _git(repo, "-c", "user.name=teste", "-c", "user.email=teste@exemplo", "commit", "-q", "-m", "inicio")
    head = _git(repo, "rev-parse", "HEAD")
    (repo / "notas.txt").write_text("fora de src e do pyproject\n", encoding="utf-8")
    assert code_version(package) == {"estado": "registrado", "commit": head, "alteracoes_locais": False}
    (package / "x.py").write_text("x = 2\n", encoding="utf-8")
    assert code_version(package) == {"estado": "registrado", "commit": head, "alteracoes_locais": True}

    installed = repo / ".venv" / "Lib" / "site-packages" / "aliado"
    installed.mkdir(parents=True)
    assert code_version(installed) == {"estado": "pacote fora do repositório", **blank}

    def missing(*args, **kwargs):
        raise FileNotFoundError("git")

    monkeypatch.setattr(codigo.subprocess, "run", missing)
    assert code_version(package) == {"estado": "git ausente", **blank}

    def slow(*args, **kwargs):
        raise subprocess.TimeoutExpired("git", 10)

    monkeypatch.setattr(codigo.subprocess, "run", slow)
    assert code_version(package) == {"estado": "erro", **blank}
