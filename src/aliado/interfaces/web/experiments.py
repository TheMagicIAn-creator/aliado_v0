"""Experimentos pela interface (spec 0034): rodar do zero, acompanhar, cancelar, baixar o PDF e comparar.

A rodada é um subprocesso de `aliado experimento rodar`, o mesmo caminho de código do terminal: um erro
não derruba o servidor, e Cancelar encerra o processo. Uma rodada por vez, num executor próprio. Rodar
com os parâmetros da rodada atual é recusado (o resultado seria o mesmo), e uma rodada que usa os dados
de teste exige a frase de confirmação. O PDF é montado só quando pedido; nada dele fica gravado.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

from starlette.concurrency import run_in_threadpool
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.routing import Route

from aliado import experiments
from aliado.interfaces.web.science import _error, _shown

MAX_LINES = 40
MAX_SAVED_BYTES = 5 * 1024 * 1024


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def run_subprocess(args: list[str], on_line, on_process) -> tuple[int, str]:
    """Roda `python -m aliado <args>`; as linhas de stderr são o progresso, o stdout é o resumo."""
    env = os.environ | {"PYTHONUNBUFFERED": "1", "PYTHONIOENCODING": "utf-8"}
    process = subprocess.Popen([sys.executable, "-m", "aliado", *args], cwd=Path.cwd(), stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE, text=True, encoding="utf-8", errors="replace", env=env)
    on_process(process)
    try:
        for line in process.stderr:
            on_line(line.rstrip())
        output = process.stdout.read()
        return process.wait(), output
    finally:
        on_process(None)


class Runner:
    """Uma rodada por vez; o estado vai para `settings.jobs`, como as tarefas da biblioteca."""

    def __init__(self, settings, lock):
        self.settings, self.lock = settings, lock
        self.executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="aliado-experimento")
        self.command = settings.experiment_command or run_subprocess
        self.job, self.process, self.cancelled = None, None, False

    def busy(self) -> bool:
        return self.job is not None and self.settings.jobs[self.job]["estado"] == "processando"

    def current(self) -> dict | None:
        with self.lock:
            return {"id": self.job} | self.settings.jobs[self.job] if self.job else None

    def submit(self, experiment, args: list[str], folder: Path) -> str:
        job = uuid.uuid4().hex
        with self.lock:
            if self.busy():
                raise RuntimeError("Já há uma rodada em andamento; espere terminar ou cancele.")
            self.settings.jobs[job] = {"estado": "processando", "etapa": experiment.TITLE, "experimento": experiment.KEY,
                                       "pasta": folder.name, "linhas": [], "iniciado_em": _now(), "inicio": time.time()}
            self.job, self.cancelled = job, False
        self.executor.submit(self._run, job, experiment, args, folder)
        return job

    def cancel(self) -> None:
        with self.lock:
            if not self.busy():
                raise RuntimeError("Nenhuma rodada em andamento.")
            self.cancelled = True
            process = self.process
        if process is not None:
            process.terminate()

    def _run(self, job: str, experiment, args: list[str], folder: Path) -> None:
        def on_line(text: str) -> None:
            if text:
                with self.lock:
                    lines = self.settings.jobs[job]["linhas"]
                    lines.append(text)
                    del lines[:-MAX_LINES]

        def on_process(process) -> None:
            self.process = process
            if process is not None and self.cancelled:
                process.terminate()  # cancelado antes de o processo começar

        error = None
        try:
            code, _ = self.command(args, on_line, on_process)
            state = "cancelado" if self.cancelled else ("concluido" if code == 0 else "falhou")
        except (OSError, ValueError, RuntimeError) as exc:
            state, error = "falhou", str(exc)
        with self.lock:
            lines = list(self.settings.jobs[job]["linhas"])
            started = self.settings.jobs[job]["iniciado_em"]
            elapsed = time.time() - self.settings.jobs[job]["inicio"]
        if state == "falhou" and error is None:
            error = lines[-1] if lines else "O comando terminou com erro."
        if state != "concluido" and hasattr(experiment, "interrupted"):
            experiment.interrupted(self.settings.results_dir, folder, state)  # fecha o que o processo deixou aberto
        if folder.is_dir():
            record = {"origem": "interface", "comando": ["aliado", *args], "iniciado_em": started,
                      "terminado_em": _now(), "estado": state}
            (folder / "execucao.json").write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n",
                                                  encoding="utf-8")
        with self.lock:
            self.settings.jobs[job].update({"estado": state, "erro": error, "decorrido_s": round(elapsed, 1),
                                            "resultado": {"pasta": folder.name} if state == "concluido" else None})


def _slug(text: str) -> str:
    return re.sub(r"[^A-Za-z0-9]+", "-", text.replace("×", "x")).strip("-")


def experiment_routes(settings, lock) -> list[Route]:
    runner = Runner(settings, lock)

    def dataset(experiment) -> Path:
        return Path(settings.dataset_dir or experiment.DATASET_DIR)

    def describe(experiment) -> dict:
        try:
            result = experiments.current(settings.results_dir, experiment)
        except ImportError:
            result = None  # sem numpy, a rodada de antes não é lida; o que falta aparece em "faltando"
        consultations = getattr(experiment, "consultations", None)
        return {"chave": experiment.KEY, "titulo": experiment.TITLE, "base": experiment.DATASET,
                "descricao": experiment.DESCRIPTION, "duracao": getattr(experiment, "DURATION", None),
                "parametros": list(experiment.PARAMETERS),
                "atual": None if result is None else {key: result.get(key) for key in (
                    "rodada", "rotulo", "oficial", "consulta", "executado_em", "parametros", "parametros_texto")},
                "faltando": experiment.missing(dataset(experiment)),
                "consultas": consultations(settings.results_dir) if consultations else None,
                "frase": getattr(experiment, "CONFIRMATION", None)}

    async def listing(request: Request):
        items = await run_in_threadpool(lambda: [describe(item) for item in experiments.available()])
        return JSONResponse({"experimentos": items, "tarefa": runner.current()})

    def chosen(request: Request):
        return experiments.find(request.path_params["key"])

    async def start(request: Request):
        try:
            experiment = chosen(request)
            data = await request.json()
            if not isinstance(data, dict):
                raise ValueError("Pedido inválido.")
            params = experiments.normalize(experiment, data.get("parametros") or {})
            absent = experiment.missing(dataset(experiment))
            if absent:
                raise ValueError("Faltam " + "; ".join(absent) + ".")
            if runner.busy():
                raise RuntimeError("Já há uma rodada em andamento; espere terminar ou cancele.")
            result = await run_in_threadpool(experiments.current, settings.results_dir, experiment)
            if experiments.same_parameters(experiment, params, result):
                raise RuntimeError("A rodada mostrada já tem estes parâmetros: o resultado seria o mesmo. "
                                   "Mude um parâmetro para rodar de novo.")
            phrase = getattr(experiment, "CONFIRMATION", None)
            if phrase and str(data.get("frase") or "").strip().lower() != phrase:
                raise ValueError(f'Para rodar, digite a frase "{phrase}".')
            folder = experiments.next_folder(settings.results_dir, experiment.KEY)
            args = ["experimento", "rodar", experiment.KEY, "--resultados", _shown(settings.results_dir),
                    "--base", _shown(dataset(experiment)), "--saida", _shown(folder),
                    *[part for name, value in params.items() for part in
                      ("--parametro", f"{name}={','.join(map(str, value)) if isinstance(value, list) else value}")],
                    *(["--frase", phrase] if phrase else [])]
            job = runner.submit(experiment, args, folder)
        except ValueError as exc:
            return _error(str(exc))
        except RuntimeError as exc:
            return _error(str(exc), 409)
        return JSONResponse({"tarefa": job, "pasta": folder.name}, 202)

    async def cancel(request: Request):
        try:
            runner.cancel()
        except RuntimeError as exc:
            return _error(str(exc), 409)
        return JSONResponse({"cancelando": True})

    async def report(request: Request):
        from aliado.experiments.pdf import render

        try:
            experiment = chosen(request)

            def build():
                result = experiments.current(settings.results_dir, experiment)
                if result is None:
                    raise ValueError("Ainda não há resultado deste experimento.")
                return result, render(result, experiment.report(result))
            result, data = await run_in_threadpool(build)
        except ValueError as exc:
            return _error(str(exc), 404)
        except ImportError:
            return _error("Faltam o matplotlib e o pypdf (extra 'science') para montar o PDF.", 404)
        name = f"AL-IAdo_{_slug(experiment.TITLE)}_{result.get('rodada') or 'rodada'}.pdf"
        return Response(data, media_type="application/pdf",
                        headers={"Content-Disposition": f'attachment; filename="{name}"'})

    async def compare(request: Request):
        try:
            experiment = chosen(request)
            form = await request.form(max_files=1, max_fields=2)
            upload = form.get("arquivo")
            if upload is None or not getattr(upload, "filename", None):
                raise ValueError("Envie o PDF exportado pela aba Ciência ou o resultado.json.")
            data = await upload.read(MAX_SAVED_BYTES + 1)
            if len(data) > MAX_SAVED_BYTES:
                return _error("Arquivo acima de 5 MB.", 413)

            def build():
                now = experiments.current(settings.results_dir, experiment)
                if now is None:
                    raise ValueError("Ainda não há resultado deste experimento para comparar.")
                saved = experiments.saved_result(upload.filename, data)
                comparison = experiments.compare(saved, now)
                try:
                    comparison["guardado"]["parametros"] = experiments.normalize(experiment, saved.get("parametros") or {})
                except ValueError:
                    comparison["guardado"]["parametros"] = None  # sem parâmetros válidos, não há o que reaplicar
                return comparison
            return JSONResponse(await run_in_threadpool(build))
        except ValueError as exc:
            return _error(str(exc))

    return [
        Route("/api/experimentos", listing),
        Route("/api/experimentos/cancelar", cancel, methods=["POST"]),
        Route("/api/experimentos/{key}/rodar", start, methods=["POST"]),
        Route("/api/experimentos/{key}/pdf", report),
        Route("/api/experimentos/{key}/comparar", compare, methods=["POST"]),
    ]
