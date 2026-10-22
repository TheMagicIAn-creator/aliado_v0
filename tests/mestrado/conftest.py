"""Fixtures de sessão do mestrado (lote 49): cada dado sintético e cada treino é feito uma vez por bateria.

As saídas compartilhadas são só de leitura; quem grava numa pasta de resultados recebe uma cópia
(`rodada_sintetica_copia`), para um teste não alterar o outro."""

import shutil
from types import SimpleNamespace

import pytest
from apoio.gpvs_sintetico import SHORT_PURGE, write_synthetic


@pytest.fixture(scope="session")
def gpvs_sintetico(tmp_path_factory):
    """O GPVS sintético (16 ensaios de 16 mil linhas), gerado uma vez. Quem altera um CSV copia a pasta antes."""
    folder = tmp_path_factory.mktemp("gpvs-sintetico")
    write_synthetic(folder)
    return folder


@pytest.fixture(scope="session")
def preparado_sintetico(gpvs_sintetico):
    """O GPVS sintético preparado com a separação da origem (2 janelas), sem cache."""
    from aliado.specializations.mestrado.preparo import preparacao

    return preparacao.prepare(gpvs_sintetico, purge=SHORT_PURGE)


@pytest.fixture(scope="session")
def rodada_sintetica(gpvs_sintetico, preparado_sintetico, tmp_path_factory):
    """Os 4 detectores sintéticos (denso e AE-LSTM, sementes 3 e 4, 3 épocas, p90), treinados e exportados uma vez,
    com a avaliação, nas pastas com os nomes reais (`gpvs-modelos-002` e `gpvs-avaliacao-001`)."""
    pytest.importorskip("torch")
    from aliado.science.deteccao.redes.autoencoders import Hyperparameters
    from aliado.specializations.mestrado import reanalysis
    from aliado.specializations.mestrado.evaluation import (
        EvaluationConfig,
        export_evaluation,
        load_training,
        score_all,
    )
    from aliado.specializations.mestrado.treino.artefatos import export_training
    from aliado.specializations.mestrado.treino.configuracao import ExperimentConfig
    from aliado.specializations.mestrado.treino.detectores import train_detectors, training_blocks

    data = preparado_sintetico
    # 20 janelas de calibração sintéticas não sustentam p99; p90 exige só 11.
    config = ExperimentConfig(purge=SHORT_PURGE, seeds=(3, 4), reference_seed=3, percentile=90.0,
                              hyperparameters=Hyperparameters(max_epochs=3))
    runs = train_detectors(data.scaled, training_blocks(data), config)
    results = tmp_path_factory.mktemp("resultados-sinteticos")
    export_training(runs, data, config, results / "gpvs-modelos-002")
    detectors = load_training(results / "gpvs-modelos-002")
    export_evaluation(score_all(detectors, data), detectors, data, EvaluationConfig(resamples=200),
                      results / reanalysis.EVALUATION)
    return SimpleNamespace(dados=gpvs_sintetico, preparado=data, config=config, runs=runs, resultados=results,
                           treino=results / "gpvs-modelos-002", avaliacao=results / reanalysis.EVALUATION)


@pytest.fixture
def rodada_sintetica_copia(rodada_sintetica, tmp_path):
    """A rodada sintética numa cópia, para os testes que gravam na pasta de resultados (reanálise e registro)."""
    results = tmp_path / "resultados"
    shutil.copytree(rodada_sintetica.resultados, results)
    return SimpleNamespace(**vars(rodada_sintetica) | {"resultados": results, "treino": results / "gpvs-modelos-002",
                                                        "avaliacao": results / rodada_sintetica.avaliacao.name})


@pytest.fixture(scope="session")
def origin_gpvs_runs(base_real):
    """Semente 42 com a separação e o teto de épocas da origem, treinada uma vez para as conferências reais."""
    pytest.importorskip("torch")
    from aliado.science.deteccao.redes.autoencoders import Hyperparameters
    from aliado.specializations.mestrado.atributos.cache import features_cache
    from aliado.specializations.mestrado.preparo import preparacao
    from aliado.specializations.mestrado.treino.configuracao import ExperimentConfig
    from aliado.specializations.mestrado.treino.detectores import train_detectors, training_blocks

    config = ExperimentConfig(purge=2, seeds=(42,), hyperparameters=Hyperparameters(max_epochs=150))
    data = preparacao.prepare(base_real, cache=features_cache(base_real), purge=config.purge)
    return config, data, train_detectors(data.scaled, training_blocks(data), config)
