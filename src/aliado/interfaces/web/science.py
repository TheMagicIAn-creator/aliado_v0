"""Aba Ciência da interface (lotes 20, 23, 24, 34 e 36): confiabilidade, FMECA e cenários, e o que as
especializações acrescentam.

Os cálculos são do serviço científico; o navegador só desenha. Salvar um cenário ou rodar a
FMECA grava sempre numa pasta nova de `data/resultados`, sem sobrescrever outra. A rodada atual de um
experimento e os exploradores vêm da especialização dele (`science_routes`), com o glossário da aba (`NOTES`).
Rodar o experimento de novo fica em `experiments.py`; a aba não lista as pastas de resultados.
"""

from __future__ import annotations

import json
import re
import unicodedata
from datetime import datetime
from pathlib import Path

from starlette.concurrency import run_in_threadpool
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route

from aliado import specializations


def error(message: str, status: int = 400) -> JSONResponse:
    return JSONResponse({"erro": message}, status)


async def read_body(request: Request) -> dict:
    data = await request.json()
    if not isinstance(data, dict):
        raise ValueError("Pedido inválido.")
    return data


async def compute(request: Request, function, *names: str, optional: dict | None = None):
    """Chama a função com os campos pedidos; `optional` mapeia campo do pedido -> argumento."""
    try:
        data = await read_body(request)
        arguments = [data[name] for name in names]
        extras = {argument: data[name] for name, argument in (optional or {}).items()
                  if data.get(name) not in (None, "")}
        result = await run_in_threadpool(function, *arguments, **extras)
    except (KeyError, TypeError):
        return error("Parâmetros incompletos.")
    except ValueError as exc:
        return error(str(exc))
    return JSONResponse(result)


def _slug(text: str) -> str:
    ascii_text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    slug = re.sub(r"[^a-z0-9]+", "-", ascii_text.lower()).strip("-")
    if len(slug) > 40:
        slug = slug[:41].rsplit("-", 1)[0]  # corta numa fronteira de palavra
    return slug or "cenario"


def _shown(path: Path) -> str:
    """Caminho para mostrar ao usuário: relativo à pasta do projeto quando possível."""
    try:
        return path.resolve().relative_to(Path.cwd().resolve()).as_posix()
    except ValueError:
        return str(path)


def _new_folder(root: Path, prefix: str) -> Path:
    """Pasta nova e inexistente; nunca reaproveita a de outro resultado."""
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    for suffix in ("", *[f"-{n}" for n in range(2, 100)]):
        folder = root / f"{prefix}-{stamp}{suffix}"
        if not folder.exists():
            return folder
    raise ValueError("Não foi possível escolher uma pasta nova para o resultado.")


def science_routes(settings, worker, lock) -> list[Route]:
    """Rotas da aba Ciência; `settings` traz results_dir, dataset_dir, reference_dir e data_dir."""
    fmeca_table = settings.reference_dir / "fmeca.json"
    scenarios_dir = settings.reference_dir / "cenarios"
    parts = [make(settings, worker, lock) for make in specializations.gather("science_routes")]
    notes = {}
    for extra in specializations.gather("NOTES"):
        notes |= extra

    async def state(request: Request):
        data = {"fmeca": fmeca_table.is_file(), "cenarios": scenarios_dir.is_dir(),
                "resultados": settings.results_dir.is_dir(), "notas": notes}
        for _, extra in parts:  # a rodada atual e os exploradores, de cada especialização
            data |= await run_in_threadpool(extra)
        return JSONResponse(data)

    async def reliability(request: Request):
        from aliado.science.ram import reliability as curve

        return await compute(request, curve, "taxa", "horas_por_ano", "base", "horizonte")

    async def presets(request: Request):
        def load():
            items = []
            for path in sorted(scenarios_dir.glob("*.json")) if scenarios_dir.is_dir() else []:
                data = json.loads(path.read_text(encoding="utf-8"))
                items.append({"arquivo": path.name, "cenario": data})
            return items
        return JSONResponse(await run_in_threadpool(load))

    async def run_scenario(request: Request):
        from aliado.science import evaluate_scenario

        return await compute(request, evaluate_scenario, "cenario")

    async def save_scenario(request: Request):
        from aliado.science import evaluate_scenario, export_result
        from aliado.science.ram import EXPLORATION_SOURCE

        try:
            scenario = (await read_body(request)).get("cenario")
            if not isinstance(scenario, dict):
                raise ValueError("Envie o cenário.")
            sources = [str(item).strip() for item in scenario.get("sources") or [] if str(item).strip()]
            if not sources or EXPLORATION_SOURCE in sources or not scenario.get("assumptions"):
                raise ValueError("Para salvar, informe a fonte e as hipóteses do cenário.")

            def save():
                result = evaluate_scenario(scenario)
                folder = _new_folder(settings.results_dir, f"cenario-{_slug(result['name'])}")
                export_result(result, folder)
                return {"pasta": folder.relative_to(settings.results_dir).as_posix(), "caminho": _shown(folder)}
            saved = await run_in_threadpool(save)
        except ValueError as exc:
            return error(str(exc))
        return JSONResponse(saved, 201)

    async def fmeca(request: Request):
        from aliado.science.fmeca import evaluate_fmeca, export_fmeca, load_table

        if not fmeca_table.is_file():
            return error("Tabela da FMECA não encontrada.", 404)
        try:
            if request.method == "GET":
                return JSONResponse(await run_in_threadpool(lambda: evaluate_fmeca(*load_table(fmeca_table))))

            def run():
                folder = _new_folder(settings.results_dir, "fmeca")
                export_fmeca(evaluate_fmeca(*load_table(fmeca_table)), folder)
                return {"pasta": folder.relative_to(settings.results_dir).as_posix(), "caminho": _shown(folder)}
            return JSONResponse(await run_in_threadpool(run), 201)
        except ValueError as exc:
            return error(str(exc))

    async def components(request: Request):
        """Confiabilidade e disponibilidade de cada grupo da FMECA (lote 25); não grava nada."""
        from aliado.science.components import component_view, load_repairs
        from aliado.science.fmeca import load_table

        repairs = settings.reference_dir / "reparos.json"
        if not fmeca_table.is_file() or not repairs.is_file():
            return error("Faltam a tabela da FMECA ou os tempos de reparo (reparos.json).", 404)
        try:
            return JSONResponse(await run_in_threadpool(
                lambda: component_view(*load_table(fmeca_table), load_repairs(repairs))))
        except (ValueError, KeyError, OSError) as exc:
            return error(str(exc))

    async def job_status(request: Request):
        with lock:
            job = settings.jobs.get(request.path_params["job"])
        return JSONResponse(job) if job else error("Tarefa não encontrada.", 404)

    return [
        Route("/api/ciencia", state),
        *[route for routes, _ in parts for route in routes],
        Route("/api/ciencia/tarefas/{job}", job_status),
        Route("/api/ciencia/confiabilidade", reliability, methods=["POST"]),
        Route("/api/ciencia/componentes", components),
        Route("/api/ciencia/cenarios", presets),
        Route("/api/ciencia/cenarios/rodar", run_scenario, methods=["POST"]),
        Route("/api/ciencia/cenarios/salvar", save_scenario, methods=["POST"]),
        Route("/api/ciencia/fmeca", fmeca, methods=["GET", "POST"]),
    ]
