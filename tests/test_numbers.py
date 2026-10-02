"""Lote 26: conferência dos números de uma resposta contra os blocos de resultados citados."""

from __future__ import annotations

from decimal import Decimal

import pytest

from aliado.numbers import check_numbers, numbers_in, split_grouped

BLOCKS = {
    "R1": ("Avaliação oficial de 27/09/2026: os 14 ensaios.\n| Denso | 10 de 14 | 2,04 s | 0,402 | 2.611 janelas | 63,7e-6/h |\n"
           "| AE-LSTM | 8 de 14 | 1,7 s | 0,386 |\n| IC 95%: 0% a 1,9% | 1,83% a 2,68% | -0,0714 |"),
    "R2": "| AE-LSTM | 8 | 1,7 s | 99,09% | S 7, O 4, D 6, NPR 168 |",
}
NOTES = "MCC: de −1 a 1; 0,5 equivale a sortear."


def written(text, **kwargs):
    return [token for token, _ in numbers_in(text, **kwargs)]


def unverified(answer, blocks=BLOCKS, shared=""):
    return check_numbers(split_grouped(answer), blocks, shared)["unverified"]


def test_dates_references_marks_and_names_are_not_numbers():
    text = "Em 27/09/2026 e 2026-09-30, o F1L e o F7M tiveram F1 de 0,458 [R1][K12ab][W3], com p99."
    assert written(text) == ["0,458"]
    assert written("Na avaliação de 27 de setembro de 2026 e em setembro de 2026, 10 ensaios") == ["10"]
    assert written("Baschel et al. (2018), Tab. 1, p. 5; Sarquis et al., 2020, Tabela III; IEEE Std 493-2007, Fig. 7: 26 h") == ["26"]
    # Referência entre parênteses, com o autor por extenso: o ano não é um número da resposta (lote 27).
    assert written("segundo a NASA (National Aeronautics and Space Administration, 2008) e (Lafraia, 2001; IEEE, Inc., 2007)") == []
    assert written("foram 2026 janelas, 2020 delas (acima de 2000)") == ["2026", "2020", "2000"]
    # As formas que as respostas por documento usam: título com a referência, ano e página, item e norma militar.
    assert written("### 1. Lafraia, 2001") == [] and written("Rahman (2017, p. 2) e o item 2.2.1 da MIL-STD-1629A") == []
    assert written("Institute of Electrical and Electronics Engineers, Inc., 2007, foram 3 casos") == ["3"]
    # Só nome próprio antes da vírgula é referência: um rótulo em minúscula não esconde o número.
    assert written("com alarme (todas oficiais, 2041); sem alarme, 1987; total") == ["2041", "1987"]
    assert written("Engineers, Inc., 2007 (IEEE Std 493)") == [] and written("são 14 itens 11 e os itens 2.2.1") == ["14", "11"]
    # Título com a referência seguida de itálico, e os números de referência do próprio texto citado.
    assert written("### 4. National Aeronautics and Space Administration, 2008 *(documento em estado parcial)*") == []
    assert written('"measured in months or hours [72]. It is the inverse of the failure rate [73, 74]", com 3 casos') == ["3"]
    # No trecho fechado por uma marca de resultado, "Nome, ano" só é referência entre parênteses.
    counts = {"R1": "| Denso | 2.050 |\n| LSTM | 1.990 |"}
    assert check_numbers("Janelas com alarme: Denso, 2041; LSTM, 1987 [R1].", counts)["unverified"] == ["2041", "1987"]
    assert check_numbers("Resultados [R1]:\n- Denso, 2041", counts)["unverified"] == ["2041"]
    assert check_numbers("Como em (Lafraia, 2001; IEEE, Inc., 2007), o Denso teve 2.050 janelas [R1].", counts)["unverified"] == []
    assert check_numbers("Resultados [R1]:\n### 1. Lafraia, 2001", counts)["unverified"] == []
    assert written("1. Primeiro item com 3 janelas") == ["3"] and written("- 10 de 14 ensaios") == ["10", "14"]
    # dia/mês sem ano só é data quando vem de uma data conhecida; senão, são dois números
    assert written("10/14 ensaios") == ["10", "14"] and written("em 27/09", short_dates=frozenset({"27/09"})) == []
    assert written("S/O/D = 9/9/6") == ["9", "9", "6"] and written("2,04/1,7 s") == ["2,04", "1,7"]


def test_formulas_and_powers_of_ten_are_read_as_numbers():
    assert written(r"$\lambda = 99{,}9 \times 10^{-6}$/h e $R(t)=e^{-2t}$ com $x_{1}$") == ["99,9e-6"]
    same = {Decimal("0.0000637")}
    for text in ("63,7e-6", "6,37e-5", "63,7 × 10⁻⁶", "63,7×10^-6", r"$63{,}7 \times 10^{-6}$", "63,7 x 10^{-6}"):
        assert numbers_in(text)[0][1] == same, text
    assert written("×10⁻⁶ por hora e 10^-6") == []  # potência de 10 solta é escala de unidade
    assert written("A sensibilidade é $0,45$") == ["0,45"]


def test_only_the_writing_may_differ():
    assert numbers_in("2.041")[0][1] == {Decimal("2041"), Decimal("2.041")}
    assert Decimal("0.402") in numbers_in("0,402")[0][1] and Decimal("0.402") in numbers_in("0.402")[0][1]
    assert numbers_in("1.817.016")[0][1] == {Decimal("1817016")} and numbers_in("2.041,4")[0][1] == {Decimal("2041.4")}
    assert numbers_in("−0,0714")[0][1] == numbers_in("-0,0714")[0][1]
    assert numbers_in("0,50")[0][1] & numbers_in("0,5")[0][1]
    # o traço depois de % ou de ) é de intervalo, não sinal de menos
    assert written("0%–1,9% e 1,83%-2,68% e (0)−5") == ["0", "1,9", "1,83", "2,68", "0", "5"]
    assert written("-0,0714 (−0,214 a 0); MCC=-0,044; 0–53,4") == ["-0,0714", "−0,214", "0", "-0,044", "0", "53,4"]


def test_marked_spans_are_checked_against_the_cited_blocks():
    answer = ("O Denso detectou 10 de 14 ensaios, com atraso de 2,04 s [R1].\n"
              "| AE-LSTM | 8 | 1,7 s | [R2] |\n"
              "Intervalo: 0%–1,9% e 1,83%-2,68%, diferença de −0,0714 [R1], na avaliação de 27/09 de 2026 [R1].")
    assert check_numbers(answer, BLOCKS) == {"used": ["R1", "R2"], "invalid": [], "unverified": [], "unmarked": 0}
    assert unverified("Sensibilidade de 0,40 e atraso de 2040 ms [R1]; depois 0,45 [R1].\n"
                      "A taxa é 6,37e-5/h e são 2611 janelas [R1].") == ["0,40", "2040", "0,45"]
    assert unverified("O Denso detectou 11/14 ensaios [R1] e S/O/D = 9/9/6 [R2].") == ["11", "9"]
    assert unverified("O Denso detectou 10/14 ensaios [R1] e S/O/D = 7/4/6 [R2].") == []
    assert unverified(r"A taxa é $99{,}9 \times 10^{-6}$/h [R1].") == ["99,9e-6"]
    assert unverified("O Denso detectou 27 de 14 ensaios [R1].") == ["27"]
    # um número de outro bloco não vale para a linha que cita só o primeiro
    assert unverified("O AE-LSTM tem 99,09% [R1].") == ["99,09"] and unverified("O AE-LSTM tem 99,09% [R1][R2].") == []
    # as notas enviadas valem em qualquer linha marcada
    assert unverified("O MCC vai de −1 a 1; 0,5 equivale a sortear [R1].") == ["−1", "1", "0,5"]
    assert unverified("O MCC vai de −1 a 1; 0,5 equivale a sortear [R1].", shared=NOTES) == []


def test_spans_that_end_in_a_document_or_web_mark_belong_to_that_source():
    assert unverified("Baschel et al. (2018) relatam 98,5% [Kabc]; nos seus resultados, 99,09% [R2].") == []
    assert unverified("Na web, a taxa citada é de 50e-6/h [W1], contra 63,7e-6/h [R1].") == []
    assert unverified("| IGBT | 11,4e-6/h [Kabc] | 63,7e-6/h [R1] |") == []
    assert unverified("A sensibilidade é 0,40 [R1] e o artigo diz 0,95 [Kabc].") == ["0,40"]
    assert unverified("São 99,09% [R2, Kabc] e 0,999 [Kabc; R1].") == ["0,999"]


def test_tables_and_lists_inherit_the_marks_of_the_line_that_opens_them():
    table = ("Na avaliação oficial [R1], os resultados foram:\n\n| Indicador | Denso | AE-LSTM |\n|---|---|---|\n"
             "| Ensaios detectados | 13 de 14 | 8 de 14 |\n| Sensibilidade | 0,402 | 0,88 |")
    assert unverified(table) == ["13", "0,88"]
    assert unverified("Segundo a avaliação oficial [R1]:\n- Denso: 10 de 14 ensaios\n- AE-LSTM: 12 de 14 ensaios") == ["12"]
    report = check_numbers("O Denso detectou 10 de 14 ensaios [R1].\nA sensibilidade foi de 0,95 e o atraso, de 0,3 s.\n"
                           "- item solto com 7", BLOCKS)
    assert report["unverified"] == [] and report["unmarked"] == 2  # sem herança; o 7 está num bloco e não conta
    assert check_numbers("Baschel relata 98,5% [Kabc].", BLOCKS)["unmarked"] == 0  # número de documento não é "sem marca"
    # A tradução de uma citação direta vem na linha seguinte, sem marca própria: é da mesma fonte (lote 27).
    quoted = '"The MTBF ranges from 30 to 50 years" [Kabc].\n*(Tradução: O MTBF vai de 30 a 50 anos.)*\n- Tradução: de 30 a 50 anos.'
    assert check_numbers(quoted, BLOCKS)["unmarked"] == 0
    assert check_numbers("A sensibilidade é 0,40 [R1].\nTradução: são 0,95 [R1].", BLOCKS)["unverified"] == ["0,40", "0,95"]


@pytest.mark.parametrize("text,expected", [
    ("Veja [R1, R2] e [R3; R4].", "Veja [R1][R2] e [R3][R4]."),
    ("Veja [R1 e R4] e [R1-R3] e [R2–R3].", "Veja [R1][R4] e [R1][R2][R3] e [R2][R3]."),
    ("Veja [R1, Kabc], [Kabc,R1] e [W1; R2].", "Veja [R1][Kabc], [Kabc][R1] e [W1][R2]."),
    ("Sem grupo: [R1] (R2) [a, b] [R1 ou R2].", "Sem grupo: [R1] (R2) [a, b] [R1 ou R2]."),
])
def test_grouped_marks_are_split(text, expected):
    assert split_grouped(text) == expected


def test_unknown_marks_and_answers_without_marks():
    report = check_numbers("São 10 [R1] e 5 [R9].", BLOCKS)
    assert report["used"] == ["R1", "R9"] and report["invalid"] == ["R9"]
    assert check_numbers("Sem marcas, 123 e 4,5.", BLOCKS) == {"used": [], "invalid": [], "unverified": [], "unmarked": 2}
