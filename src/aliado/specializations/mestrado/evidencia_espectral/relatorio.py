"""O texto da evidência espectral para o chat e para o PDF: as linhas das duas tabelas, em linguagem simples e com os
números no formato da tela. Só a biblioteca padrão."""

from __future__ import annotations

from aliado.science.resumo_citavel.formato import num, pct

MODELS = (("denso", "Denso"), ("lstm", "AE-LSTM"))
INDICATOR_NAMES = {"dc": "Nível DC / fundamental", "fundamental": "Fundamental / comissionamento", "thd": "THD",
                   "h2": "2ª harmônica / fundamental", "h3": "3ª harmônica / fundamental",
                   "h5": "5ª harmônica / fundamental"}
SHORT_NAMES = {"dc": "nível DC", "fundamental": "fundamental", "thd": "THD", "h2": "2ª harmônica", "h3": "3ª harmônica",
               "h5": "5ª harmônica"}
ALARM_HEADERS = ["Ensaio", "Modelo", "Janela do alarme", "Fase com maior erro", "Maior erro geral",
                 *INDICATOR_NAMES.values()]
CHANGE_HEADERS = ["Ensaio", "Falha", "Mais muda", "Em segundo lugar", "Janelas antes da mudança observada"]
ALARM_TEXT = ("Cada linha é a janela de 20 ms em que o modelo confirmou o primeiro alarme depois do início nominal da "
              "falha, contada do começo do registro. A fase é a do maior erro do modelo entre as 6 de corrente e tensão, "
              "com a posição desse erro entre os 24 da janela. O nível DC, a THD e as harmônicas estão em porcentagem da "
              "fundamental: o primeiro número é o da janela do alarme, e o entre parênteses, a mediana no "
              "comissionamento do mesmo ensaio. A evidência descreve o sinal; não diz qual é a falha.")
CHANGE_TEXT = ("A mudança compara a mediana depois do início nominal da falha com a do comissionamento, em amplitudes "
               "interquartis (IQR) do comissionamento; o sinal diz se o indicador subiu ou desceu. As janelas antes da "
               "mudança observada só aparecem nos ensaios de mudança clara.")
_SIGNALS = {"median": "mediana de {}", "iqr": "variação de {}", "rms": "RMS de {}", "thd": "THD de {}"}
_OTHERS = {"i_rms_unbalance": "desequilíbrio das correntes", "v_rms_unbalance": "desequilíbrio das tensões",
           "p_ac_mean": "potência CA média", "p_ac_std": "oscilação da potência CA", "p_dc_median": "potência CC",
           "p_dc_iqr": "variação da potência CC"}


def feature_name(feature: str) -> str:
    """O nome em palavras de uma das 24 variáveis (`ia_thd` vira "THD de ia")."""
    if feature in _OTHERS:
        return _OTHERS[feature]
    signal, kind = feature.rsplit("_", 1)
    return _SIGNALS[kind].format(signal)


def _value(key: str, value: float) -> str:
    """A fundamental relativa como razão; o nível DC, a THD e as harmônicas em porcentagem da fundamental."""
    return num(value, 2) if key == "fundamental" else pct(value, 2)


def _cell(item: dict, key: str) -> str:
    # A fundamental do comissionamento é a própria referência (1): o parêntese não diria nada.
    if key == "fundamental":
        return _value(key, item["indicadores"][key])
    return f"{_value(key, item['indicadores'][key])} ({_value(key, item['comissionamento'][key])})"


def alarm_rows(evidence: dict) -> list[list[str]]:
    rows = []
    for name in evidence["alarmes"]["denso"]:
        for kind, model in MODELS:
            item = evidence["alarmes"][kind][name]
            if item["alarme"] is None:
                rows.append([name, model, "sem alarme", *["—"] * (len(ALARM_HEADERS) - 3)])
                continue
            rows.append([name, model, f"{item['alarme']}" + (" (passo irregular)" if item["passo_irregular"] else ""),
                         f"{item['fase']} ({item['posicao_da_fase']}º)", feature_name(item["maior_atributo"]),
                         *[_cell(item, key) for key in INDICATOR_NAMES]])
    return rows


def _change(entry: dict) -> str:
    key = entry["indicador"]
    return (f"{SHORT_NAMES[key]} de {entry['fase']}, de {_value(key, entry['comissionamento'])} para "
            f"{_value(key, entry['depois'])} ({num(entry['mudanca'], 2)} IQR)")


def change_rows(evidence: dict, fault_names: dict[str, str]) -> list[list[str]]:
    """`fault_names`: o nome curto de cada falha pelo código dela (F1, F2…)."""
    late = evidence["janelas_antes_da_mudanca"]
    return [[name, fault_names.get(name[:2], name[:2]), *[_change(entry) for entry in entries],
             "—" if late.get(name) is None else str(late[name])]
            for name, entries in evidence["mais_mudam"].items()]
