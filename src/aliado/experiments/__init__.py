"""Experimentos (spec 0034): a rodada atual, os resultados em JSON e Markdown e o PDF por pedido.

Cada experimento vem de uma especialização (atributo `EXPERIMENTS`) e roda por inteiro, num processo
só, com o próprio código (`run`). O núcleo cuida do resto, igual para todos:
- cada rodada fica numa pasta nova, `<resultados>/<chave>/rodada-NNN/`, que nunca é reaproveitada;
- `resultado.json` é gravado por último e de uma vez: sem ele a rodada está incompleta e não aparece;
- a rodada atual é a completa mais nova; sem nenhuma, a que o experimento já tinha (`legacy`);
- rodar de novo com os mesmos parâmetros da rodada atual é recusado: o resultado seria o mesmo.
"""

from __future__ import annotations

import json
import os
import re
from pathlib import Path

RESULT = "resultado.json"
REPORT = "resultado.md"
FORMAT = 1
_RUN = re.compile(r"rodada-(\d{3,})")


def available() -> list:
    """Os experimentos de todas as especializações instaladas."""
    from aliado import specializations

    return [experiment for group in specializations.gather("EXPERIMENTS") for experiment in group]


def find(key: str):
    for experiment in available():
        if experiment.KEY == key:
            return experiment
    raise ValueError("Experimento não encontrado.")


def _integer(value, label: str, low: int, high: int) -> int:
    text = str(value).strip()
    if isinstance(value, bool) or not re.fullmatch(r"-?\d+(\.0)?", text):
        raise ValueError(f"{label}: informe um número inteiro.")
    number = int(float(text))
    if not low <= number <= high:
        raise ValueError(f"{label}: use um inteiro entre {low} e {high}.")
    return number


def normalize(experiment, values: dict) -> dict:
    """Os parâmetros do pedido conferidos pela declaração do experimento; o que faltar fica no padrão."""
    if not isinstance(values, dict):
        raise ValueError("Parâmetros inválidos.")
    unknown = set(values) - {item["nome"] for item in experiment.PARAMETERS}
    if unknown:
        raise ValueError("Parâmetro desconhecido: " + ", ".join(sorted(unknown)) + ".")
    chosen = {}
    for item in experiment.PARAMETERS:
        value = values.get(item["nome"], item["padrao"])
        low, high = item.get("minimo", 0), item.get("maximo", 2**31 - 1)
        if item["tipo"] == "inteiro":
            chosen[item["nome"]] = _integer(value, item["rotulo"], low, high)
            continue
        parts = value.split(",") if isinstance(value, str) else list(value) if isinstance(value, (list, tuple)) else None
        if parts is None:
            raise ValueError(f"{item['rotulo']}: informe números inteiros separados por vírgula.")
        numbers = [_integer(part, item["rotulo"], low, high) for part in parts if str(part).strip()]
        if not numbers or len(set(numbers)) != len(numbers):
            raise ValueError(f"{item['rotulo']}: informe uma lista de inteiros distintos.")
        chosen[item["nome"]] = sorted(numbers) if item.get("ordenar") else numbers
    return chosen


def same_parameters(experiment, wanted: dict, result: dict | None) -> bool:
    """Se o pedido repete os parâmetros do resultado (os dois já conferidos)."""
    if not result:
        return False
    try:
        return normalize(experiment, wanted) == normalize(experiment, result.get("parametros") or {})
    except ValueError:
        return False


def runs_dir(results_dir: str | Path, key: str) -> Path:
    return Path(results_dir) / key


def _numbered(parent: Path) -> list[tuple[int, Path]]:
    if not parent.is_dir():
        return []
    return sorted((int(match.group(1)), path) for path in parent.iterdir()
                  if path.is_dir() and (match := _RUN.fullmatch(path.name)))


def next_folder(results_dir: str | Path, key: str) -> Path:
    """Próximo número livre (rodada-003); nunca reaproveita uma pasta, nem a de uma rodada incompleta."""
    parent = runs_dir(results_dir, key)
    return parent / f"rodada-{max((number for number, _ in _numbered(parent)), default=0) + 1:03d}"


def read_result(folder: Path) -> dict | None:
    try:
        data = json.loads((Path(folder) / RESULT).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return data if isinstance(data, dict) else None


def latest(results_dir: str | Path, key: str) -> tuple[Path, dict] | None:
    """A rodada completa mais nova; as incompletas ou ilegíveis ficam de fora."""
    for _, folder in reversed(_numbered(runs_dir(results_dir, key))):
        result = read_result(folder)
        if result is not None and result.get("experimento") == key:
            return folder, result
    return None


def current(results_dir: str | Path, experiment) -> dict | None:
    """O resultado da rodada atual; sem rodada completa, o que o experimento já tinha (ou None)."""
    found = latest(results_dir, experiment.KEY)
    if found:
        return found[1]
    legacy = getattr(experiment, "legacy", None)
    return legacy(Path(results_dir)) if legacy else None


def markdown(result: dict) -> str:
    """O resumo em Markdown, igual para todos os experimentos: parâmetros e indicadores, com as notas."""
    lines = [f"# {result['titulo']}", "", f"{result['rotulo']}. Base de dados: {result['base']}.", "",
             "## Parâmetros", "", "| Parâmetro | Valor |", "|---|---|"]
    lines += [f"| {item['rotulo']} | {item['texto']} |" for item in result.get("parametros_texto", ())]
    lines += ["", "## Indicadores", "", "| Indicador | Valor | O que é |", "|---|---:|---|"]
    lines += [f"| {item['rotulo']} | {item['texto']} | {item.get('nota', '')} |"
              for item in (result.get("numeros") or {}).values()]
    if result.get("comando"):
        lines += ["", "## Para reproduzir", "", f"`{result['comando']}`"]
    return "\n".join(lines) + "\n"


def write_result(folder: str | Path, result: dict) -> Path:
    """O Markdown e, por último e de uma vez, o JSON que marca a rodada como completa."""
    folder = Path(folder)
    (folder / REPORT).write_text(markdown(result), encoding="utf-8")
    partial = folder / f".{RESULT}.parcial"
    partial.write_text(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    os.replace(partial, folder / RESULT)
    return folder / RESULT


def saved_result(name: str, data: bytes) -> dict:
    """O resultado guardado: o `resultado.json` anexo a um PDF exportado, ou o próprio JSON."""
    suffix = Path(name).suffix.lower()
    if suffix == ".pdf":
        from io import BytesIO

        from pypdf import PdfReader

        try:
            attached = PdfReader(BytesIO(data)).attachments.get(RESULT) or []
        except Exception as exc:  # arquivo de fora: qualquer falha do leitor vira um aviso, nunca um erro do servidor
            raise ValueError("Não foi possível ler o PDF.") from exc
        if not attached:
            raise ValueError("O PDF não traz o resultado.json anexado; envie um PDF exportado pela aba Ciência.")
        data = attached[0]
    elif suffix != ".json":
        raise ValueError("Envie o PDF exportado pela aba Ciência ou o resultado.json.")
    try:
        result = json.loads(data.decode("utf-8-sig"))
    except (UnicodeDecodeError, ValueError) as exc:
        raise ValueError("O arquivo não é um resultado.json legível.") from exc
    if not isinstance(result, dict):
        raise ValueError("O arquivo não é um resultado.json legível.")
    return result


def compare(saved: dict, now: dict) -> dict:
    """Guardado × atual, indicador por indicador; a diferença é atual − guardado."""
    if not isinstance(saved, dict) or not isinstance(saved.get("numeros"), dict):
        raise ValueError("O arquivo não traz os indicadores de uma rodada.")
    if saved.get("experimento") != now.get("experimento"):
        raise ValueError("O resultado guardado é de outro experimento.")
    rows = []
    current_numbers = now.get("numeros") or {}
    for key in dict.fromkeys([*saved["numeros"], *current_numbers]):
        before, after = saved["numeros"].get(key), current_numbers.get(key)
        before = before if isinstance(before, dict) else {}
        after = after if isinstance(after, dict) else {}
        old, new = before.get("valor"), after.get("valor")
        numeric = all(isinstance(value, (int, float)) and not isinstance(value, bool) for value in (old, new))
        rows.append({"chave": key, "rotulo": after.get("rotulo") or before.get("rotulo") or key,
                     "nota": after.get("nota") or before.get("nota") or "",
                     "guardado": before.get("texto", "—"), "atual": after.get("texto", "—"),
                     "diferenca": new - old if numeric else None, "igual": old == new and bool(before) and bool(after)})
    return {"guardado": {key: saved.get(key) for key in ("rodada", "rotulo", "executado_em", "parametros")},
            "atual": {key: now.get(key) for key in ("rodada", "rotulo", "executado_em", "parametros")},
            "linhas": rows, "iguais": sum(row["igual"] for row in rows), "total": len(rows)}
