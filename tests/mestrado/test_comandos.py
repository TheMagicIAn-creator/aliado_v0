"""Os comandos `aliado ciencia preparar-gpvs`, `treinar-gpvs` e `avaliar-gpvs`: gravam numa pasta nova e nunca
sobrescrevem."""

from __future__ import annotations

import json

import numpy as np
from apoio.gpvs_sintetico import SHORT_PURGE


def test_cli_prepares_report_without_overwriting(gpvs_sintetico, tmp_path, capsys):
    from aliado.cli import main

    output = tmp_path / "preparo"
    args = ["ciencia", "preparar-gpvs", "--dados", str(gpvs_sintetico), "--saida", str(output),
            "--cache", str(tmp_path / "cache.npz"), "--separacao", str(SHORT_PURGE)]
    assert main(args) == 0
    report = json.loads((output / "relatorio.json").read_text(encoding="utf-8"))
    assert report["saudavel"]["papeis"]["train"] == 80
    assert "Verificação do M14" in (output / "relatorio.md").read_text(encoding="utf-8")
    with np.load(output / "normalizacao.npz") as stored:
        assert stored["papel_train"].shape == (80,) and stored["piso_iqr"].shape == (24,)
    assert main(args) == 2 and "já existe" in capsys.readouterr().err


def test_cli_refuses_degenerate_threshold_before_training_and_existing_folder(gpvs_sintetico, tmp_path, capsys):
    from aliado.cli import main

    folder = gpvs_sintetico
    output = tmp_path / "treino"
    args = ["ciencia", "treinar-gpvs", "--dados", str(folder), "--saida", str(output),
            "--cache", str(tmp_path / "cache.npz"), "--separacao", str(SHORT_PURGE), "--sementes", "7"]
    assert main(args) == 2
    assert "exige ao menos 101 janelas" in capsys.readouterr().err and not output.exists()
    output.mkdir()
    assert main(args) == 2 and "já existe" in capsys.readouterr().err


def test_cli_evaluates_and_refuses_existing_folder(rodada_sintetica, tmp_path, capsys):
    from aliado.cli import main

    folder, output = rodada_sintetica.dados, rodada_sintetica.treino
    args = ["ciencia", "avaliar-gpvs", "--modelos", str(output), "--saida", str(tmp_path / "avaliacao"),
            "--dados", str(folder), "--cache", str(tmp_path / "cache.npz")]
    assert main(args) == 0 and (tmp_path / "avaliacao" / "relatorio.md").is_file()
    capsys.readouterr()
    assert main(args) == 2 and "já existe" in capsys.readouterr().err
