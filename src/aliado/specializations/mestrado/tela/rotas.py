"""Rotas da aba Ciência do mestrado (lotes 20, 23, 24 e 36): a rodada atual do experimento e os exploradores.

Saíram de `interfaces/web/science.py`, que ficou com o que vale para qualquer pesquisa: FMECA, confiabilidade por
componente e cenários. As visões da rodada atual (resumo, métricas, escores e início das falhas) só leem
arquivos; os exploradores carregam os modelos da rodada atual no primeiro uso."""

from __future__ import annotations

import uuid

from starlette.concurrency import run_in_threadpool
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route

from aliado.interfaces.web.science import compute, error


def science_routes(settings, worker, lock) -> tuple[list[Route], object]:
    """As rotas e o estado dos exploradores, que o núcleo junta ao de /api/ciencia."""
    created = {}

    def explorer():
        """Criado no primeiro uso da aba (numpy e PyTorch não pesam na abertura do servidor) e de novo
        quando a rodada atual muda: os modelos e os erros são os da rodada que a aba mostra."""
        from aliado.specializations.mestrado.exploradores.explorador import Explorer
        from aliado.specializations.mestrado.resultados.rodada_atual import current

        if created.get("explorer") is None or created["explorer"].run != current(settings.results_dir):
            created["explorer"] = Explorer(settings.results_dir, settings.dataset_dir, settings.data_dir / "ciencia")
        return created["explorer"]

    def state() -> dict:
        try:
            found = explorer()
            return {"exploradores": found.status() | {"opcoes": found.choices()}, "rodada": found.run.id}
        except ImportError:
            return {"exploradores": {"disponivel": False, "pronto": False, "faltando": ["o extra 'ml' (numpy e PyTorch)"]},
                    "rodada": None}

    async def prepare(request: Request):
        job = uuid.uuid4().hex
        with lock:
            settings.jobs[job] = {"estado": "processando", "etapa": "preparando", "atual": 0, "total": 4}

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

    async def threshold(request: Request):
        return await compute(request, explorer().threshold, "modelo", "semente", "k", "percentil",
                             optional={"janela": "window"})

    async def alarms(request: Request):
        return await compute(request, explorer().alarms, "modelo", "semente", "k", "percentil", "confirmacoes",
                             optional={"ensaio": "trial"})

    async def view(function: str, *arguments):
        """A rodada atual (lotes 23 e 34): só leitura, sem carregar os modelos."""
        try:
            from aliado.specializations.mestrado.resultados import paineis

            return JSONResponse(await run_in_threadpool(getattr(paineis, function), *arguments))
        except FileNotFoundError as exc:
            return error(str(exc), 404)
        except ImportError:
            return error("Falta o extra 'ml' (numpy) para ver os resultados.", 404)
        except (KeyError, ValueError, StopIteration):
            return error("Os resultados da rodada estão incompletos.", 404)

    async def overview(request: Request):
        return await view("overview", settings.results_dir)

    async def per_fault(request: Request):
        return await view("per_fault", settings.results_dir)

    async def score_panels(request: Request):
        return await view("score_panels", settings.results_dir, settings.dataset_dir)

    async def onsets(request: Request):
        return await view("onsets", settings.results_dir)

    return [
        Route("/api/ciencia/resumo", overview),
        Route("/api/ciencia/metricas", per_fault),
        Route("/api/ciencia/escores", score_panels),
        Route("/api/ciencia/inicio", onsets),
        Route("/api/ciencia/preparar", prepare, methods=["POST"]),
        Route("/api/ciencia/limiar", threshold, methods=["POST"]),
        Route("/api/ciencia/alarme", alarms, methods=["POST"]),
    ], state
