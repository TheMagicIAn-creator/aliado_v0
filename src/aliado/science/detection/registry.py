"""Registro das consultas ao teste de um experimento de detecção, só acrescentado (lotes 21 e 34).

Cada avaliação pontua o teste saudável e os ensaios com falha, e isso é uma consulta ao teste. A
primeira, a oficial, é lida da própria pasta da avaliação (`canonical`, informada pelo experimento).
Uma nova exige a frase de confirmação, recebe o próximo número e fica marcada como não oficial. Uma
reanálise dos escores já gravados também entra, com o tipo "reanalise". O arquivo nunca é reescrito:
cada mudança de estado é um evento novo.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

REGISTRY = "registro-consultas-teste.jsonl"
PHRASE = "consultar o teste"
FINAL_STATES = ("concluida", "falhou", "cancelada")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _path(results_dir: str | Path) -> Path:
    return Path(results_dir) / REGISTRY


def events(results_dir: str | Path) -> list[dict]:
    path = _path(results_dir)
    if not path.is_file():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _append(results_dir: str | Path, event: dict) -> None:
    path = _path(results_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(event, ensure_ascii=False) + "\n")


def _seed(results_dir: str | Path, canonical: str | None) -> dict | None:
    """A consulta oficial, lida da própria pasta da avaliação."""
    if not canonical:
        return None
    config_path = Path(results_dir) / canonical / "configuracao.json"
    if not config_path.is_file():
        return None
    config = json.loads(config_path.read_text(encoding="utf-8"))
    return {"numero": 1, "estado": "concluida", "canonica": True, "data": config.get("executado_em"),
            "treino": {"pasta": Path(config["treino"]["pasta"]).name,
                       "sha256": config["treino"]["configuracao_sha256"]},
            "saida": canonical, "origem": "semeado a partir da avaliação canônica, feita pelo terminal"}


def ensure_seeded(results_dir: str | Path, canonical: str | None) -> None:
    """Na primeira gravação, o arquivo começa pela consulta oficial."""
    seed = _seed(results_dir, canonical)
    if seed and not events(results_dir):
        _append(results_dir, seed | {"registrado_em": _now()})


def start(results_dir: str | Path, *, training: str, training_sha: str, output: str, phrase: str,
          canonical: str | None = None, origin: str = "interface") -> int:
    """Abre uma consulta não oficial; recusa sem a frase exata. Devolve o número."""
    if str(phrase or "").strip().lower() != PHRASE:
        raise ValueError(f'Para avaliar, digite a frase "{PHRASE}".')
    ensure_seeded(results_dir, canonical)
    number = max((event["numero"] for event in events(results_dir)), default=0) + 1
    _append(results_dir, {
        "numero": number, "estado": "iniciada", "canonica": False, "data": datetime.now().date().isoformat(),
        "treino": {"pasta": training, "sha256": training_sha}, "saida": output, "frase_confirmada": True,
        "registrado_em": _now(), "origem": origin,
    })
    return number


def record_reanalysis(results_dir: str | Path, *, source: str, output: str, training: str, training_sha: str,
                      config_sha: str, canonical: str | None = None) -> int:
    """Reanálise dos escores já gravados de uma avaliação (lote 24): não pontua o teste de novo, mas
    volta a olhar para ele, então entra no registro, concluída e não oficial. Devolve o número."""
    ensure_seeded(results_dir, canonical)
    number = max((event["numero"] for event in events(results_dir)), default=0) + 1
    _append(results_dir, {
        "numero": number, "estado": "concluida", "canonica": False, "tipo": "reanalise",
        "data": datetime.now().date().isoformat(), "treino": {"pasta": training, "sha256": training_sha},
        "reusa": source, "saida": output, "configuracao_sha256": config_sha, "registrado_em": _now(),
        "origem": "terminal",
    })
    return number


def finish(results_dir: str | Path, number: int, state: str) -> None:
    if state not in FINAL_STATES:
        raise ValueError("Estado final inválido para a consulta.")
    _append(results_dir, {"numero": int(number), "estado": state, "registrado_em": _now()})


def consultations(results_dir: str | Path, canonical: str | None = None) -> list[dict]:
    """Uma linha por consulta, com o estado mais recente; o histórico fica no arquivo.

    Sem arquivo, mostra a consulta oficial sem gravar nada.
    """
    recorded = events(results_dir)
    if not recorded:
        seed = _seed(results_dir, canonical)
        return [seed] if seed else []
    merged: dict[int, dict] = {}
    for event in recorded:
        merged.setdefault(event["numero"], {}).update(event)
    return [merged[number] for number in sorted(merged)]


def close_open(results_dir: str | Path, output: str, state: str) -> list[int]:
    """Fecha as consultas que ficaram abertas para a pasta `output`: o processo parou antes de fechá-las."""
    closed = [item["numero"] for item in consultations(results_dir)
              if item.get("saida") == output and item.get("estado") == "iniciada"]
    for number in closed:
        finish(results_dir, number, state)
    return closed
