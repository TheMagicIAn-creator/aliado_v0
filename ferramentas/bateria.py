"""Bateria do AL-IAdo (lote 49): os testes em processos separados, com tempo, treinos de rede e pico de memória.

- Cada subpasta de `tests/` com `__init__.py` e testes (hoje `science` e `mestrado`) roda num processo só, para as
  fixtures de sessão valerem para a pasta inteira. Os outros `tests/test_*.py` rodam um por processo, como antes.
- `--rapida` deixa de fora os testes que treinam redes ou leem os dados reais (`-m "not treina and not dados_reais"`);
  sobram as specs, o isolamento, os contratos, o gateway, o provedor local e o resto do que é rápido.
- A saída de cada processo vai para `<saida>/<grupo>.log`, e o resumo, para `<saida>/pytest.json`.

Uso: `.venv\\Scripts\\python.exe ferramentas/bateria.py [--rapida] [--saida tmp/bateria] [grupo ...]`.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TESTS = ROOT / "tests"
FAST = "not treina and not dados_reais"
# Só estes grupos importam o PyTorch; nos outros, contar os treinos custaria a importação dele.
TRAINING_HINTS = ("torch", "origin_gpvs_runs", "rodada_sintetica")


def groups() -> list[tuple[str, Path]]:
    found = []
    for path in sorted(TESTS.iterdir()):
        if path.is_dir() and (path / "__init__.py").is_file() and any(path.rglob("test_*.py")):
            found.append((path.name, path))
        elif path.is_file() and path.name.startswith("test_") and path.suffix == ".py":
            found.append((path.stem, path))
    return found


def _count(word: str, text: str) -> int:
    found = re.search(rf"(\d+) {word}", text)
    return int(found[1]) if found else 0


def _trains(path: Path) -> bool:
    files = path.rglob("*.py") if path.is_dir() else [path]
    return any(hint in file.read_text(encoding="utf-8") for file in files for hint in TRAINING_HINTS)


def run(name: str, path: Path, output: Path, fast: bool) -> dict:
    measure = output / f"{name}.medicao.json"
    env = os.environ | {"ALIADO_MEDICAO": str(measure), "PYTHONPATH": str(ROOT / "ferramentas")}
    if _trains(path):
        env["ALIADO_CONTAR_TREINOS"] = "1"
    command = [sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider", "-p", "medicao",
               str(path.relative_to(ROOT))] + (["-m", FAST] if fast else [])
    begin = time.perf_counter()
    done = subprocess.run(command, cwd=ROOT, env=env, capture_output=True, text=True, encoding="utf-8",
                          errors="replace")
    text = done.stdout + done.stderr
    (output / f"{name}.log").write_text(text, encoding="utf-8")
    tail = text.strip().splitlines()[-1] if text.strip() else ""
    measured = json.loads(measure.read_text(encoding="utf-8")) if measure.is_file() else {}
    measure.unlink(missing_ok=True)
    # Sem nenhum teste escolhido (só os lentos no grupo), o pytest sai com 5: não é falha.
    exit_code = 0 if done.returncode == 5 and fast else done.returncode
    return {"grupo": name, "exit_code": exit_code, "passed": _count("passed", tail), "failed": _count("failed", tail),
            "skipped": _count("skipped", tail), "deselected": _count("deselected", tail),
            "errors": _count("errors?", tail), "seconds": round(time.perf_counter() - begin, 2),
            "treinos": measured.get("treinos"), "pico_memoria_mib": measured.get("pico_memoria_mib")}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--rapida", action="store_true", help="sem os testes que treinam ou leem os dados reais")
    parser.add_argument("--saida", default="tmp/bateria", help="pasta dos registros (padrão: tmp/bateria)")
    parser.add_argument("grupos", nargs="*", help="só estes grupos (nomes de subpasta ou de arquivo, sem .py)")
    args = parser.parse_args(argv)
    output = (ROOT / args.saida).resolve()
    output.mkdir(parents=True, exist_ok=True)
    chosen = [(name, path) for name, path in groups() if not args.grupos or name in args.grupos]
    started, results = time.perf_counter(), []
    for name, path in chosen:
        results.append(run(name, path, output, args.rapida))
        print(results[-1], flush=True)
    summary = {"rapida": args.rapida, "grupos": len(results),
               **{key: sum(item[key] for item in results)
                  for key in ("passed", "failed", "skipped", "deselected", "errors")},
               "treinos": sum(item["treinos"] or 0 for item in results),
               "pico_memoria_mib": max((item["pico_memoria_mib"] or 0 for item in results), default=0),
               "grupos_com_falha": [item["grupo"] for item in results if item["exit_code"] != 0],
               "seconds": round(time.perf_counter() - started, 2), "resultados": results}
    (output / "pytest.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print({key: summary[key] for key in ("grupos", "passed", "failed", "skipped", "deselected", "treinos",
                                         "pico_memoria_mib", "grupos_com_falha", "seconds")})
    return 1 if summary["grupos_com_falha"] else 0


if __name__ == "__main__":
    sys.exit(main())
