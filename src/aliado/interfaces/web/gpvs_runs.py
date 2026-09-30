"""GPVS pela interface (lote 21): preparar, treinar e avaliar pelos próprios comandos do terminal.

Cada etapa roda num subprocesso de `aliado ciencia …`, o mesmo caminho de código do terminal:
os resultados são idênticos, um erro não derruba o servidor e Cancelar encerra o processo. Só
uma etapa por vez, num executor separado do envio de documentos. Uma nova avaliação consulta o
teste de novo (M14): exige a frase de confirmação, entra no registro e fica não canônica.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

from starlette.concurrency import run_in_threadpool
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route

from aliado.interfaces.web.science import _error, _shown
from aliado.science.detection import registry

# Etapa -> (subcomando do terminal, prefixo da pasta nova).
STEPS = {"preparar": ("preparar-gpvs", "gpvs-preparo"), "treinar": ("treinar-gpvs", "gpvs-modelos"),
         "avaliar": ("avaliar-gpvs", "gpvs-avaliacao")}
# Configuração canônica de 27/09, usada só se a rodada canônica não estiver no computador.
FALLBACK = {"separacao": 11, "sementes": [13, 29, 42, 71, 101], "teto_epocas": 2000}
MAX_LINES = 40
FINAL = {"concluido": "concluida", "falhou": "falhou", "cancelado": "cancelada"}


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


def _read(path: Path) -> dict | None:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def canonical(results_dir: Path) -> dict:
    """Configuração do treino citado na avaliação canônica, com o hash; senão, os valores de 27/09."""
    evaluation = _read(results_dir / registry.CANONICAL / "configuracao.json")
    if evaluation:
        training = Path(evaluation["treino"]["pasta"]).name
        frozen = _read(results_dir / training / "configuracao.json")
        if frozen:
            config = frozen["configuracao"]
            return {"treino": training, "sha256": evaluation["treino"]["configuracao_sha256"],
                    "separacao": config["purge"], "sementes": config["seeds"],
                    "teto_epocas": config["hyperparameters"]["max_epochs"]}
    return FALLBACK | {"treino": None, "sha256": None}


def trainings(results_dir: Path) -> list[dict]:
    reference = canonical(results_dir)["sha256"]
    items = []
    for folder in sorted(results_dir.glob("gpvs-modelos-*")) if results_dir.is_dir() else []:
        frozen = _read(folder / "configuracao.json")
        if frozen and (folder / "escores_calibracao.npz").is_file():
            items.append({"pasta": folder.name, "sha256": frozen["sha256"], "canonica": frozen["sha256"] == reference})
    return items


def next_folder(results_dir: Path, prefix: str) -> Path:
    """Próximo número livre (gpvs-modelos-003); nunca reaproveita uma pasta."""
    numbers = [int(path.name.rsplit("-", 1)[1]) for path in results_dir.glob(f"{prefix}-*")
               if path.name.rsplit("-", 1)[1].isdigit()] if results_dir.is_dir() else []
    return results_dir / f"{prefix}-{max(numbers, default=0) + 1:03d}"


class GpvsRunner:
    """Uma etapa por vez; o estado vai para `settings.jobs`, como as tarefas da biblioteca."""

    def __init__(self, settings, lock):
        self.settings, self.lock = settings, lock
        self.executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="aliado-gpvs")
        self.command = settings.gpvs_command or run_subprocess
        self.job, self.process, self.cancelled = None, None, False

    def busy(self) -> bool:
        return self.job is not None and self.settings.jobs[self.job]["estado"] == "processando"

    def current(self) -> dict | None:
        with self.lock:
            return {"id": self.job} | self.settings.jobs[self.job] if self.job else None

    def submit(self, step: str, args: list[str], output: Path, *, consultation: int | None = None) -> str:
        job = uuid.uuid4().hex
        with self.lock:
            if self.busy():
                raise RuntimeError("Já há uma etapa do GPVS em andamento; espere terminar ou cancele.")
            self.settings.jobs[job] = {"estado": "processando", "etapa": step, "pasta": output.name, "linhas": [],
                                       "iniciado_em": _now(), "inicio": time.time(), "consulta": consultation}
            self.job, self.cancelled = job, False
        self.executor.submit(self._run, job, step, args, output, consultation)
        return job

    def cancel(self) -> None:
        with self.lock:
            if not self.busy():
                raise RuntimeError("Nenhuma etapa do GPVS em andamento.")
            self.cancelled = True
            process = self.process
        if process is not None:
            process.terminate()

    def _run(self, job: str, step: str, args: list[str], output: Path, consultation: int | None) -> None:
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
        results_dir = self.settings.results_dir
        record = {"origem": "interface", "etapa": step, "comando": ["aliado", *args], "iniciado_em": started,
                  "terminado_em": _now(), "estado": state, "consulta": consultation}
        if step == "treinar":
            frozen = _read(output / "configuracao.json")
            record["configuracao_canonica"] = bool(frozen) and frozen["sha256"] == canonical(results_dir)["sha256"]
        if output.is_dir():
            (output / "execucao.json").write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n",
                                                  encoding="utf-8")
            if consultation is not None:
                (output / "consulta.json").write_text(json.dumps(
                    {"numero": consultation, "canonica": False, "data": datetime.now().date().isoformat(),
                     "frase_confirmada": True, "registro": registry.REGISTRY}, ensure_ascii=False, indent=2) + "\n",
                    encoding="utf-8")
        if consultation is not None:
            registry.finish(results_dir, consultation, FINAL[state])
        with self.lock:
            self.settings.jobs[job].update({"estado": state, "erro": error, "decorrido_s": round(elapsed, 1),
                                            "resultado": {"pasta": output.name} if state == "concluido" else None})


def _integer(value, label: str, low: int, high: int) -> int:
    try:
        number = int(value)
    except (TypeError, ValueError):
        raise ValueError(f"{label}: informe um número inteiro.") from None
    if isinstance(value, bool) or not low <= number <= high or str(value).strip() not in {str(number), f"{number}.0"}:
        raise ValueError(f"{label}: use um inteiro entre {low} e {high}.")
    return number


def _seeds(value) -> list[int]:
    items = value.split(",") if isinstance(value, str) else list(value or [])
    seeds = [_integer(str(item).strip(), "Sementes", 0, 2**31 - 1) for item in items if str(item).strip()]
    if not seeds or len(set(seeds)) != len(seeds):
        raise ValueError("Sementes: informe uma lista de inteiros distintos.")
    return seeds


def gpvs_routes(settings, lock) -> list[Route]:
    runner = GpvsRunner(settings, lock)

    def data_args() -> list[str]:
        return ["--dados", _shown(settings.gpvs_dir), "--cache", _shown(settings.gpvs_dir / "processado" / "variaveis.npz")]

    def available() -> list[str]:
        return [] if (settings.gpvs_dir / "proveniencia.json").is_file() else [f"os dados do GPVS em {_shown(settings.gpvs_dir)}"]

    async def state(request: Request):
        def build():
            return {"disponivel": not available(), "faltando": available(), "canonica": canonical(settings.results_dir),
                    "treinos": trainings(settings.results_dir), "tarefa": runner.current(),
                    "consultas": registry.consultations(settings.results_dir), "frase": registry.PHRASE}
        return JSONResponse(await run_in_threadpool(build))

    async def body(request: Request) -> dict:
        data = await request.json()
        if not isinstance(data, dict):
            raise ValueError("Pedido inválido.")
        return data

    def start(step: str, args: list[str], output: Path, consultation=None) -> JSONResponse:
        job = runner.submit(step, args, output, consultation=consultation)
        return JSONResponse({"tarefa": job, "pasta": output.name, "consulta": consultation}, 202)

    async def prepare(request: Request):
        try:
            if available():
                raise ValueError("Faltam " + "; ".join(available()) + ".")
            data = await body(request)
            purge = _integer(data.get("separacao", FALLBACK["separacao"]), "Separação", 0, 200)
            output = next_folder(settings.results_dir, STEPS["preparar"][1])
            return start("preparar", ["ciencia", STEPS["preparar"][0], *data_args(), "--saida", _shown(output),
                                      "--separacao", str(purge)], output)
        except ValueError as exc:
            return _error(str(exc))
        except RuntimeError as exc:
            return _error(str(exc), 409)

    async def train(request: Request):
        try:
            if available():
                raise ValueError("Faltam " + "; ".join(available()) + ".")
            data = await body(request)
            purge = _integer(data.get("separacao"), "Separação", 0, 200)
            seeds = _seeds(data.get("sementes"))
            epochs = _integer(data.get("teto_epocas"), "Teto de épocas", 1, 100_000)
            output = next_folder(settings.results_dir, STEPS["treinar"][1])
            return start("treinar", ["ciencia", STEPS["treinar"][0], *data_args(), "--saida", _shown(output),
                                     "--separacao", str(purge), "--sementes", ",".join(map(str, seeds)),
                                     "--teto-epocas", str(epochs)], output)
        except ValueError as exc:
            return _error(str(exc))
        except RuntimeError as exc:
            return _error(str(exc), 409)

    async def evaluate(request: Request):
        try:
            if available():
                raise ValueError("Faltam " + "; ".join(available()) + ".")
            data = await body(request)
            if str(data.get("frase") or "").strip().lower() != registry.PHRASE:
                raise ValueError(f'Para avaliar, digite a frase "{registry.PHRASE}".')
            chosen = next((item for item in trainings(settings.results_dir) if item["pasta"] == data.get("treino")), None)
            if chosen is None:
                raise ValueError("Escolha uma rodada de treino existente.")
            if runner.busy():
                raise RuntimeError("Já há uma etapa do GPVS em andamento; espere terminar ou cancele.")
            output = next_folder(settings.results_dir, STEPS["avaliar"][1])
            number = registry.start(settings.results_dir, training=chosen["pasta"], training_sha=chosen["sha256"],
                                    output=output.name, phrase=data.get("frase"))
            try:
                return start("avaliar", ["ciencia", STEPS["avaliar"][0], *data_args(), "--modelos",
                                         _shown(settings.results_dir / chosen["pasta"]), "--saida", _shown(output)],
                             output, number)
            except RuntimeError:
                registry.finish(settings.results_dir, number, "falhou")
                raise
        except ValueError as exc:
            return _error(str(exc))
        except RuntimeError as exc:
            return _error(str(exc), 409)

    async def cancel(request: Request):
        try:
            runner.cancel()
        except RuntimeError as exc:
            return _error(str(exc), 409)
        return JSONResponse({"cancelando": True})

    return [
        Route("/api/ciencia/gpvs", state),
        Route("/api/ciencia/gpvs/preparar", prepare, methods=["POST"]),
        Route("/api/ciencia/gpvs/treinar", train, methods=["POST"]),
        Route("/api/ciencia/gpvs/avaliar", evaluate, methods=["POST"]),
        Route("/api/ciencia/gpvs/cancelar", cancel, methods=["POST"]),
    ]
