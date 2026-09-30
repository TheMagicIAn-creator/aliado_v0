"""Aba Ciência da interface (lote 20): resultados, exploradores, confiabilidade e FMECA.

Os cálculos são do serviço científico; o navegador só desenha. Salvar um cenário ou rodar a
FMECA grava sempre numa pasta nova de `data/resultados`, sem sobrescrever outra. O GPVS pela
interface (preparar, treinar e avaliar) fica para o lote 21.
"""

from __future__ import annotations

import csv
import json
import re
import unicodedata
import uuid
from datetime import datetime
from pathlib import Path

from starlette.concurrency import run_in_threadpool
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route

from aliado.interfaces.web.rendering import render_markdown

# Arquivo que identifica o tipo de cada pasta de resultado.
RESULT_KINDS = (
    ("resultado.json", "cenario", "Cenário de confiabilidade"),
    ("fmeca.json", "fmeca", "FMECA"),
    ("escores.npz", "gpvs-avaliacao", "GPVS: avaliação"),
    ("escores_calibracao.npz", "gpvs-modelos", "GPVS: modelos e limiar"),
    ("avaliacao-busca.json", "busca", "Medição da busca"),
    ("normalizacao.npz", "gpvs-preparo", "GPVS: preparo"),  # modelos também têm; vêm antes na ordem
    ("relatorio.json", "relatorio", "Relatório"),
)
REPORTS = ("relatorio.md", "fmeca.md")


def _error(message: str, status: int = 400) -> JSONResponse:
    return JSONResponse({"erro": message}, status)


def _kind(folder: Path) -> tuple[str, str] | None:
    for name, kind, label in RESULT_KINDS:
        if (folder / name).is_file():
            return kind, label
    return None


def _title(folder: Path, kind: str) -> str:
    try:
        if kind == "cenario":
            return json.loads((folder / "resultado.json").read_text(encoding="utf-8"))["name"]
        if kind == "fmeca":
            return json.loads((folder / "fmeca.json").read_text(encoding="utf-8"))["nome"]
    except (OSError, ValueError, KeyError):
        pass
    return folder.name


def list_results(root: Path) -> list[dict]:
    """Pastas de resultado, com um nível de agrupamento (ex.: lote-07/igbt-operacao)."""
    if not root.is_dir():
        return []
    items = []
    for folder in sorted(root.iterdir()):
        if not folder.is_dir():
            continue
        found = _kind(folder)
        candidates = [(folder, found)] if found else [
            (sub, _kind(sub)) for sub in sorted(folder.iterdir()) if sub.is_dir() and _kind(sub)]
        for path, (kind, label) in candidates:
            items.append({"id": path.relative_to(root).as_posix(), "tipo": kind, "rotulo": label,
                          "titulo": _title(path, kind),
                          "modificado": datetime.fromtimestamp(path.stat().st_mtime).isoformat(timespec="minutes")})
    return items


def result_detail(root: Path, result_id: str) -> dict:
    listed = {item["id"]: item for item in list_results(root)}
    if result_id not in listed:
        raise ValueError("Resultado não encontrado.")
    folder = (root / result_id).resolve()
    if not folder.is_relative_to(root.resolve()):
        raise ValueError("Resultado não encontrado.")
    item = listed[result_id]
    report = next((folder / name for name in REPORTS if (folder / name).is_file()), None)
    detail = item | {"caminho": _shown(folder),
                     "html": render_markdown(report.read_text(encoding="utf-8")) if report else None}
    kind = item["tipo"]
    if (folder / "execucao.json").is_file():  # rodada feita pela interface (lote 21)
        detail["execucao"] = json.loads((folder / "execucao.json").read_text(encoding="utf-8"))
    if kind == "gpvs-avaliacao":
        from aliado.science.detection import registry

        consultation = folder / "consulta.json"
        detail["consulta"] = (json.loads(consultation.read_text(encoding="utf-8")) if consultation.is_file()
                              else {"numero": 1, "canonica": True} if folder.name == registry.CANONICAL else None)
    if kind == "gpvs-modelos":
        from aliado.interfaces.web.gpvs_runs import canonical

        frozen = json.loads((folder / "configuracao.json").read_text(encoding="utf-8"))
        detail["configuracao_canonica"] = frozen["sha256"] == canonical(root)["sha256"]
    if kind == "cenario":
        data = json.loads((folder / "resultado.json").read_text(encoding="utf-8"))
        detail["curvas"] = {"unidade": data.get("time_unit"), "linhas": [
            {key: row.get(key) for key in ("time", "reliability", "failure_probability")} for row in data["rows"]
            if "reliability" in row]}
    elif kind == "fmeca":
        detail["fmeca"] = json.loads((folder / "fmeca.json").read_text(encoding="utf-8"))
    elif kind == "gpvs-modelos":
        detail["calibracao"] = _calibration(folder)
    elif kind == "gpvs-avaliacao":
        with (folder / "metricas_por_ensaio.csv").open(encoding="utf-8", newline="") as handle:
            rows = list(csv.DictReader(handle))
        reference = json.loads((folder / "relatorio.json").read_text(encoding="utf-8"))["semente_referencia"]
        detail["ensaios"] = {"semente": reference, "linhas": [
            {key: row[key] for key in ("modelo", "ensaio", "detectado", "atraso_ms", "alarmes_pre_falha")}
            for row in rows if int(row["semente"]) == int(reference)]}
    elif kind == "busca":
        data = json.loads((folder / "avaliacao-busca.json").read_text(encoding="utf-8"))
        detail["busca"] = {key: data.get(key) for key in ("data", "busca", "resumo", "por_grupo")}
    return detail


def _calibration(folder: Path) -> dict:
    import numpy as np

    config = json.loads((folder / "configuracao.json").read_text(encoding="utf-8"))["configuracao"]
    report = json.loads((folder / "relatorio.json").read_text(encoding="utf-8"))
    seed, k = report["semente_referencia"], config["top_k"]
    curves = {}
    with np.load(folder / "escores_calibracao.npz") as scores:
        for kind, model in report["modelos"].items():
            key = f"{kind}_s{seed}_k{k}"
            if key in scores:
                curves[kind] = {"escores_ordenados": sorted(float(v) for v in scores[key]),
                                "limiar": float(model["sementes"][str(seed)]["sensibilidade_k"][str(k)])}
    return {"semente": seed, "k": k, "percentil": config["percentile"], "modelos": curves}


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
    """Rotas da aba Ciência; `settings` traz results_dir, gpvs_dir, reference_dir e data_dir."""
    fmeca_table = settings.reference_dir / "fmeca.json"
    scenarios_dir = settings.reference_dir / "cenarios"
    created = {}

    def explorer():
        """Criado no primeiro uso da aba: numpy e PyTorch não pesam na abertura do servidor."""
        if "explorer" not in created:
            from aliado.science.explorer import Explorer

            created["explorer"] = Explorer(settings.results_dir, settings.gpvs_dir, settings.data_dir / "ciencia")
        return created["explorer"]

    async def body(request: Request) -> dict:
        data = await request.json()
        if not isinstance(data, dict):
            raise ValueError("Pedido inválido.")
        return data

    async def state(request: Request):
        try:
            status = await run_in_threadpool(lambda: explorer().status() | {"opcoes": explorer().choices()})
        except ImportError:
            status = {"disponivel": False, "pronto": False, "faltando": ["o extra 'ml' (numpy e PyTorch)"]}
        return JSONResponse({"gpvs": status, "fmeca": fmeca_table.is_file(), "cenarios": scenarios_dir.is_dir(),
                             "resultados": settings.results_dir.is_dir()})

    async def prepare(request: Request):
        job = uuid.uuid4().hex
        with lock:
            settings.jobs[job] = {"estado": "processando", "etapa": "preparando", "atual": 0, "total": 3}

        def progress(stage: str, current: int, total: int) -> None:
            with lock:
                settings.jobs[job].update({"etapa": stage, "atual": current, "total": total})

        def run():
            try:
                explorer().prepare(progress)
                outcome = {"estado": "concluido", "resultado": explorer().choices()}
            except (ValueError, OSError, RuntimeError, ImportError, KeyError) as exc:
                outcome = {"estado": "falhou", "erro": str(exc)}
            with lock:
                settings.jobs[job].update(outcome)

        worker.submit(run)
        return JSONResponse({"tarefa": job}, 202)

    async def compute(request: Request, function, *names: str, optional: dict | None = None):
        """Chama a função com os campos pedidos; `optional` mapeia campo do pedido -> argumento."""
        try:
            data = await body(request)
            arguments = [data[name] for name in names]
            extras = {argument: data[name] for name, argument in (optional or {}).items()
                      if data.get(name) not in (None, "")}
            result = await run_in_threadpool(function, *arguments, **extras)
        except (KeyError, TypeError):
            return _error("Parâmetros incompletos.")
        except ValueError as exc:
            return _error(str(exc))
        return JSONResponse(result)

    async def threshold(request: Request):
        return await compute(request, explorer().threshold, "modelo", "semente", "k", "percentil",
                             optional={"janela": "window"})

    async def alarms(request: Request):
        return await compute(request, explorer().alarms, "modelo", "semente", "k", "percentil", "confirmacoes",
                             optional={"ensaio": "trial"})

    async def reliability(request: Request):
        from aliado.science.explorer import reliability as curve

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
        from aliado.science.explorer import EXPLORATION_SOURCE

        try:
            scenario = (await body(request)).get("cenario")
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
            return _error(str(exc))
        return JSONResponse(saved, 201)

    async def fmeca(request: Request):
        from aliado.science.fmeca import evaluate_fmeca, export_fmeca, load_table

        if not fmeca_table.is_file():
            return _error("Tabela da FMECA não encontrada.", 404)
        try:
            if request.method == "GET":
                return JSONResponse(await run_in_threadpool(lambda: evaluate_fmeca(*load_table(fmeca_table))))

            def run():
                folder = _new_folder(settings.results_dir, "fmeca")
                export_fmeca(evaluate_fmeca(*load_table(fmeca_table)), folder)
                return {"pasta": folder.relative_to(settings.results_dir).as_posix(), "caminho": _shown(folder)}
            return JSONResponse(await run_in_threadpool(run), 201)
        except ValueError as exc:
            return _error(str(exc))

    async def results(request: Request):
        return JSONResponse(await run_in_threadpool(list_results, settings.results_dir))

    async def result(request: Request):
        try:
            detail = await run_in_threadpool(result_detail, settings.results_dir, request.path_params["rid"])
        except ValueError as exc:
            return _error(str(exc), 404)
        return JSONResponse(detail)

    async def job_status(request: Request):
        with lock:
            job = settings.jobs.get(request.path_params["job"])
        return JSONResponse(job) if job else _error("Tarefa não encontrada.", 404)

    return [
        Route("/api/ciencia", state),
        Route("/api/ciencia/preparar", prepare, methods=["POST"]),
        Route("/api/ciencia/tarefas/{job}", job_status),
        Route("/api/ciencia/limiar", threshold, methods=["POST"]),
        Route("/api/ciencia/alarme", alarms, methods=["POST"]),
        Route("/api/ciencia/confiabilidade", reliability, methods=["POST"]),
        Route("/api/ciencia/cenarios", presets),
        Route("/api/ciencia/cenarios/rodar", run_scenario, methods=["POST"]),
        Route("/api/ciencia/cenarios/salvar", save_scenario, methods=["POST"]),
        Route("/api/ciencia/fmeca", fmeca, methods=["GET", "POST"]),
        Route("/api/ciencia/resultados", results),
        Route("/api/ciencia/resultados/{rid:path}", result),
    ]
