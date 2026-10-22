"""A execução da rodada: o que falta no computador, as consultas ao teste e o experimento inteiro num processo só,
do preparo ao resumo. Só a biblioteca padrão no topo: numpy e PyTorch entram dentro das funções."""

from __future__ import annotations

import time
from datetime import datetime
from importlib.util import find_spec
from pathlib import Path

from aliado.science.deteccao.registro import consultas as registry
from aliado.science.identidade.codigo import code_version
from aliado.science.identidade.contrato import CONTRACT
from aliado.science.identidade.hashes import arrays_digest
from aliado.specializations.mestrado.atributos.cache import features_cache
from aliado.specializations.mestrado.rodada.consolidacao import collect
from aliado.specializations.mestrado.rodada.declaracao import DATASET, LEGACY_EVALUATION, STAGES


def missing(dataset_dir: str | Path) -> list[str]:
    """O que falta neste computador para rodar, sem importar numpy nem PyTorch."""
    absent = [] if (Path(dataset_dir) / "proveniencia.json").is_file() else [f"a base de dados {DATASET} em {dataset_dir}"]
    return absent + [f"o {name} (extra 'ml')" for module, name in (("numpy", "numpy"), ("torch", "PyTorch"))
                     if find_spec(module) is None]


def consultations(results_dir: str | Path) -> int:
    """Quantas vezes os dados de teste já foram usados, pelo registro de consultas."""
    return len(registry.consultations(results_dir, LEGACY_EVALUATION))


def interrupted(results_dir: str | Path, folder: str | Path, state: str) -> None:
    """O processo parou antes de fechar a consulta (cancelado ou com erro): ela é fechada aqui."""
    output = Path(folder).resolve().relative_to(Path(results_dir).resolve()).as_posix()
    registry.close_open(results_dir, output, "cancelada" if state == "cancelado" else "falhou")


def run(params: dict, folder: str | Path, *, results_dir: str | Path, dataset_dir: str | Path, phrase: str,
        progress=print) -> dict:
    """O experimento inteiro, numa pasta nova, com os parâmetros já conferidos; devolve o resultado."""
    from aliado.science.deteccao.redes.autoencoders import Hyperparameters
    from aliado.specializations.mestrado.avaliacao.artefatos import (
        ERRORS,
        export_evaluation,
        load_errors,
    )
    from aliado.specializations.mestrado.avaliacao.configuracao import EvaluationConfig
    from aliado.specializations.mestrado.avaliacao.pontuacao import score_all
    from aliado.specializations.mestrado.avaliacao.treino_congelado import load_training
    from aliado.specializations.mestrado.preparo import artefatos as artefatos_do_preparo
    from aliado.specializations.mestrado.preparo import preparacao
    from aliado.specializations.mestrado.preparo import resumo as resumo_do_preparo
    from aliado.specializations.mestrado.reanalise import reanalise
    from aliado.specializations.mestrado.resultados import rodada_atual
    from aliado.specializations.mestrado.treino.artefatos import export_training
    from aliado.specializations.mestrado.treino.configuracao import ExperimentConfig
    from aliado.specializations.mestrado.treino.detectores import train_detectors, training_blocks

    started = time.monotonic()
    code = code_version()  # antes de preparar os dados: a versão que de fato roda
    folder, results_dir, dataset_dir = Path(folder), Path(results_dir), Path(dataset_dir)
    output = folder.resolve().relative_to(results_dir.resolve()).as_posix()
    cache = features_cache(dataset_dir)
    seeds = tuple(params["sementes"])
    config = ExperimentConfig(purge=params["separacao"], seeds=seeds, reference_seed=42 if 42 in seeds else seeds[0],
                              hyperparameters=Hyperparameters(max_epochs=params["teto_epocas"]))
    progress(f"Preparando a base de dados, com {config.purge} janelas entre os blocos…")
    prepared = preparacao.prepare(dataset_dir, cache=cache, purge=config.purge, fractions=config.fractions)
    artefatos_do_preparo.export_preparation(prepared, resumo_do_preparo.report(prepared), folder / STAGES["preparo"])
    progress(f"Treinando os dois modelos em {len(seeds)} repetições…")
    runs = train_detectors(prepared.scaled, training_blocks(prepared), config, progress=progress)
    export_training(runs, prepared, config, folder / STAGES["modelos"])
    trained = load_training(folder / STAGES["modelos"])  # confere os hashes do que acabou de ser gravado
    number = registry.start(results_dir, training=f"{output}/{STAGES['modelos']}", training_sha=trained.frozen["sha256"],
                            output=output, phrase=phrase, canonical=LEGACY_EVALUATION, origin="experimento")
    progress(f"Pontuando os ensaios de teste: é a {number}ª vez que os dados de teste são usados…")
    try:
        export_evaluation(score_all(trained, prepared), trained, prepared, EvaluationConfig(), folder / STAGES["avaliacao"])
        progress("Procurando quando cada falha aparece nos sinais…")
        reanalise.run(folder / STAGES["avaliacao"], folder / STAGES["modelos"], dataset_dir, folder / STAGES["inicio"],
                       cache=cache)
    except BaseException:
        registry.finish(results_dir, number, "falhou")
        raise
    registry.finish(results_dir, number, "concluida")
    progress("Montando o resumo…")
    meta, errors = load_errors(folder / STAGES["avaliacao"] / ERRORS)
    identity = {"contrato": CONTRACT, "codigo": code, "pesos": meta["pesos"], "variaveis": meta["variaveis"],
                "janela": meta["janela"], "erros_sha256": arrays_digest(errors)}
    return collect(rodada_atual.Run(folder / STAGES["avaliacao"], folder / STAGES["inicio"], False, folder.name, number),
                   params, executed=datetime.now().astimezone().isoformat(timespec="seconds"), identity=identity,
                   duration=time.monotonic() - started)
