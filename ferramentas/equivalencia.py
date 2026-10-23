"""Equivalência da ciência (lote 49): o experimento inteiro no GPVS sintético, comparado com uma referência.

Serve para provar que mudar arquivos de lugar não mudou nenhum número.
- `gravar <pasta>`: gera o GPVS sintético (72 mil linhas por ensaio), roda `aliado experimento rodar` e guarda a
  rodada em <pasta>.
- `comparar <referencia> [--rodada <pasta>]`: roda de novo (ou usa uma rodada já feita) e compara arquivo por arquivo.
  - Os JSON e o Markdown são comparados sem as datas e os horários da própria execução, `duracao_s`, `versao` e a
    versão do código.
  - Os `.npz` e os `.pt`, matriz por matriz; o resto, byte a byte.
  - Arquivos e chaves novos aparecem à parte das diferenças: um lote que acrescenta saídas não muda as antigas.
- `autoteste`: duas execuções iguais não podem mostrar diferença, e uma alterada tem de mostrar.

Parâmetros fixos: separação 2, sementes 42 e 13, teto de 3 épocas, a frase de consulta ao teste.
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tests"))
WORK = ROOT / "tmp" / "equivalencia" / "trabalho"
ROWS = 72_000
PARAMETERS = ("separacao=2", "sementes=42,13", "teto_epocas=3")
MASKED_KEYS = frozenset({"duracao_s", "versao", "codigo"})
# Lote 60: também a data curta entre parênteses, como "meio (22/10)" no relatório do início, que só difere quando a
# comparação é feita em outro dia; dia e mês válidos, para não esconder uma fração como "(13/16)".
DATES = re.compile(r"\d{4}-\d{2}-\d{2}(?:[T ]\d{2}:\d{2}(?::\d{2}(?:\.\d+)?)?(?:[+-]\d{2}:\d{2}|Z)?)?|\d{2}/\d{2}/\d{4}"
                   r"(?:,? (?:às )?\d{2}:\d{2}(?::\d{2})?)?|\((?:0[1-9]|[12]\d|3[01])/(?:0[1-9]|1[0-2])\)")


def run_experiment(work: Path) -> Path:
    """Gera a base sintética em <work>/base e roda o experimento em <work>/resultados; devolve a pasta da rodada."""
    from apoio.gpvs_sintetico import write_synthetic

    base, results = work / "base", work / "resultados"
    write_synthetic(base, rows=ROWS, provenance=True)
    args = ["experimento", "rodar", "ae-denso-lstm", "--resultados", str(results), "--base", str(base),
            *[item for value in PARAMETERS for item in ("--parametro", value)], "--frase", "consultar o teste"]
    code = "import sys; from aliado.cli import main; sys.exit(main(sys.argv[1:]))"
    done = subprocess.run([sys.executable, "-c", code, *args], cwd=ROOT, capture_output=True, text=True,
                          encoding="utf-8", errors="replace")
    if done.returncode != 0:
        raise SystemExit(f"O experimento falhou ({done.returncode}):\n{done.stdout}\n{done.stderr}")
    return results / "ae-denso-lstm" / "rodada-001"


def _mask(value):
    if isinstance(value, dict):
        return {key: "<mascarado>" if key in MASKED_KEYS else _mask(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_mask(item) for item in value]
    if isinstance(value, str):
        return DATES.sub("<data>", value)
    return value


def _keys(value, prefix: str = "") -> set[str]:
    if isinstance(value, dict):
        found = set()
        for key, item in value.items():
            path = f"{prefix}.{key}" if prefix else key
            found |= {path} | _keys(item, path)
        return found
    if isinstance(value, list):
        return set().union(*(_keys(item, f"{prefix}[{index}]") for index, item in enumerate(value))) if value else set()
    return set()


def _without(value, extra: set[str], prefix: str = ""):
    """O JSON novo sem as chaves que a referência não tem, para que só o que já existia seja comparado."""
    if isinstance(value, dict):
        kept = {}
        for key, item in value.items():
            path = f"{prefix}.{key}" if prefix else key
            if path not in extra:
                kept[key] = _without(item, extra, path)
        return kept
    if isinstance(value, list):
        return [_without(item, extra, f"{prefix}[{index}]") for index, item in enumerate(value)]
    return value


def _same_npz(old: Path, new: Path) -> bool:
    import numpy as np

    with np.load(old, allow_pickle=False) as a, np.load(new, allow_pickle=False) as b:
        if set(a.files) != set(b.files):
            return False
        for name in a.files:
            if a[name].dtype.kind == "U" and name == "meta":
                if _mask(json.loads(str(a[name]))) != _mask(json.loads(str(b[name]))):
                    return False
            elif a[name].dtype != b[name].dtype or not np.array_equal(a[name], b[name]):
                return False
    return True


def _same_weights(old: Path, new: Path) -> bool:
    import torch

    a, b = (torch.load(path, map_location="cpu", weights_only=True) for path in (old, new))
    if set(a) != set(b) or any(a[key] != b[key] for key in a if key != "state_dict"):
        return False
    return set(a["state_dict"]) == set(b["state_dict"]) and all(
        torch.equal(a["state_dict"][key], b["state_dict"][key]) for key in a["state_dict"])


def compare(reference: Path, run: Path) -> dict:
    """Diferenças no que já existia, mais os arquivos e as chaves novos, listados à parte."""
    old = {path.relative_to(reference).as_posix() for path in reference.rglob("*") if path.is_file()}
    new = {path.relative_to(run).as_posix() for path in run.rglob("*") if path.is_file()}
    result = {"iguais": 0, "diferentes": [], "faltando": sorted(old - new), "arquivos_novos": sorted(new - old),
              "chaves_novas": {}}
    for name in sorted(old & new):
        a, b = reference / name, run / name
        if a.read_bytes() == b.read_bytes():
            same = True
        elif a.suffix == ".json":
            before, after = json.loads(a.read_text(encoding="utf-8")), json.loads(b.read_text(encoding="utf-8"))
            extra = _keys(after) - _keys(before)
            if extra:
                result["chaves_novas"][name] = sorted(extra)
            same = _mask(before) == _mask(_without(after, extra))
        elif a.suffix == ".md":
            normal = [DATES.sub("<data>", path.read_text(encoding="utf-8").replace("\r\n", "\n")) for path in (a, b)]
            same = normal[0] == normal[1]
        elif a.suffix == ".npz":
            same = _same_npz(a, b)
        elif a.suffix == ".pt":
            same = _same_weights(a, b)
        else:
            same = a.read_bytes().replace(b"\r\n", b"\n") == b.read_bytes().replace(b"\r\n", b"\n")
        if same:
            result["iguais"] += 1
        else:
            result["diferentes"].append(name)
    result["equivalente"] = not result["diferentes"] and not result["faltando"]
    return result


def _fresh_run() -> Path:
    # Sempre a mesma pasta: a avaliação grava o caminho do treino, que não pode mudar de uma execução para outra.
    if WORK.exists():
        shutil.rmtree(WORK)
    return run_experiment(WORK)


def _record(target: Path) -> None:
    run = _fresh_run()
    if target.exists():
        shutil.rmtree(target)
    shutil.copytree(run, target)
    shutil.rmtree(WORK)
    print(f"Referência gravada em {target}")


def _compare(reference: Path, existing: Path | None) -> dict:
    if existing is not None:
        return compare(reference, existing)
    result = compare(reference, _fresh_run())
    shutil.rmtree(WORK)
    return result


def _selftest(folder: Path) -> int:
    first, second = folder / "a", folder / "b"
    _record(first)
    _record(second)
    same = compare(first, second)
    altered = folder / "b-alterada"
    if altered.exists():
        shutil.rmtree(altered)
    shutil.copytree(second, altered)
    result = json.loads((altered / "resultado.json").read_text(encoding="utf-8"))
    key = sorted(result["numeros"])[0]
    result["numeros"][key]["valor"] = (result["numeros"][key]["valor"] or 0) + 1
    (altered / "resultado.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    changed = compare(first, altered)
    report = {"iguais_sem_diferenca": same["equivalente"], "arquivos_comparados": same["iguais"],
              "alterada_com_diferenca": not changed["equivalente"], "diferencas_na_alterada": changed["diferentes"]}
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["iguais_sem_diferenca"] and report["alterada_com_diferenca"] else 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    commands = parser.add_subparsers(dest="comando", required=True)
    commands.add_parser("gravar").add_argument("pasta")
    compare_parser = commands.add_parser("comparar")
    compare_parser.add_argument("referencia")
    compare_parser.add_argument("--rodada", help="compara com esta rodada, sem rodar de novo")
    commands.add_parser("autoteste").add_argument("pasta")
    args = parser.parse_args(argv)
    if args.comando == "gravar":
        _record((ROOT / args.pasta).resolve())
        return 0
    if args.comando == "autoteste":
        return _selftest((ROOT / args.pasta).resolve())
    result = _compare((ROOT / args.referencia).resolve(), (ROOT / args.rodada).resolve() if args.rodada else None)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["equivalente"] else 1


if __name__ == "__main__":
    sys.exit(main())
