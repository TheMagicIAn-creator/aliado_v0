"""A declaração do experimento AE Denso × AE-LSTM: o nome, a base, a descrição, os parâmetros da tela, as etapas e a
avaliação oficial. Só constantes e a biblioteca padrão, para quem precisa delas não importar a rodada inteira."""

from __future__ import annotations

from aliado.science.deteccao.registro import consultas as registry
from aliado.specializations.mestrado.base.ensaios import DATA_DIR

KEY = "ae-denso-lstm"
TITLE = "AE Denso × AE-LSTM"
DATASET = "GPVS"
DATASET_DIR = DATA_DIR
CONFIRMATION = registry.PHRASE
DESCRIPTION = ("Compara dois detectores de falhas não supervisionados na base GPVS: um autoencoder denso, que olha "
               "cada janela de 20 ms sozinha, e um autoencoder LSTM, que olha sequências de janelas. Os dois seguem o "
               "mesmo protocolo: divisão do tempo em blocos, limiar no percentil 99 da calibração, alarme com janelas "
               "seguidas acima do limiar e avaliação nos 14 ensaios com falha e no teste saudável.")
DURATION = "cerca de 2 minutos"
LEGACY_EVALUATION = "gpvs-avaliacao-001"
LEGACY_ID = "avaliacao-oficial"
STAGES = {"preparo": "preparo", "modelos": "modelos", "avaliacao": "avaliacao", "inicio": "inicio"}
PARAMETERS = (
    {"nome": "separacao", "rotulo": "Separação entre blocos", "tipo": "inteiro", "padrao": 11, "minimo": 0,
     "maximo": 200, "unidade": "janelas",
     "nota": "Janelas descartadas entre os blocos de treino, validação, calibração e teste, para um bloco não "
             "vazar no outro. 11 é a decisão de 27/09/2026."},
    {"nome": "sementes", "rotulo": "Repetições do treino", "tipo": "inteiros", "padrao": [13, 29, 42, 71, 101],
     "minimo": 0, "ordenar": True,
     "nota": "Um número por repetição do treino, separados por vírgula: cada um fixa o ponto de partida aleatório. "
             "Os números mostrados são os da repetição de referência (42, se estiver na lista), e a faixa vai do "
             "menor ao maior valor das repetições."},
    {"nome": "teto_epocas", "rotulo": "Teto de épocas", "tipo": "inteiro", "padrao": 2000, "minimo": 1,
     "maximo": 100_000,
     "nota": "Limite de segurança do treino; quem o encerra é a perda na validação. 150 repete a pesquisa de origem."},
)
METRICS = (("sensibilidade", "Sensibilidade"), ("especificidade", "Especificidade"), ("precisao", "Precisão"),
           ("f1", "F1"), ("mcc", "MCC"), ("auc_roc", "AUC-ROC"), ("auc_pr", "AUC-PR"))
