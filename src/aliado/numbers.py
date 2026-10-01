"""Conferência de números de uma resposta contra os blocos de resultados citados (lote 26).

O modelo recebe os resultados da pesquisa em blocos [R1], [R2]… e deve repetir os números como
estão. Aqui, cada trecho da resposta fechado por uma marca [Rn] tem os números comparados aos que
estão impressos nos blocos citados na mesma linha (e nas notas enviadas com eles). Só a escrita
pode diferir (2.041 e 2041; 0,402 e 0.402; 63,7e-6 e 63,7 × 10⁻⁶): arredondar, converter ou
inventar é apontado.

Regras da conferência:
- o trecho que termina numa marca de documento [K…] ou da web [Wn] pertence a essa fonte e fica fora;
- linha de tabela ou item de lista sem marca herda as marcas da linha marcada que os abre;
- datas, referências (autor e ano, tabela, página, norma) e nomes de ensaio não contam como número;
- número em parágrafo sem marca não é conferido; os que também não estão em nenhum bloco são contados à parte.
Só usa a biblioteca padrão.
"""

from __future__ import annotations

import re
from decimal import Decimal, InvalidOperation

RESULT_MARK = re.compile(r"\[(R\d+)\]")
_ANY_MARK = re.compile(r"\[([KWR][^\]\s]*)\]")
# [R1, R4], [R1; R4], [R1 e R4] e o intervalo [R1-R3].
_ONE = r"(?:K[0-9A-Za-z]+|[RW]\d+)"
_GROUP = re.compile(r"\[(" + _ONE + r"(?:\s*(?:[,;]|\be\b|[-–])\s*" + _ONE + r")+)\]")
_MONTH = r"(?:janeiro|fevereiro|mar[cç]o|abril|maio|junho|julho|agosto|setembro|outubro|novembro|dezembro)"
_DATE_WITH_YEAR = re.compile(r"(?<![\d.,/])(\d{1,2}/\d{1,2})/(\d{2,4})(?![\d/]|[.,]\d)")
# Não contam como número: datas, referências e nomes de ensaio ou de métrica (F1, F7M, p99).
_IGNORED = re.compile(
    r"(?<![\d.,/])\d{1,2}/\d{1,2}/\d{2,4}(?![\d/]|[.,]\d)|\b\d{4}-\d{2}-\d{2}\b"            # datas com ano
    rf"|\b\d{{1,2}}º?\s+de\s+{_MONTH}(?:\s+de\s+\d{{4}})?\b|\b{_MONTH}\s+de\s+\d{{4}}\b"      # datas por extenso
    r"|\((?:19|20)\d{2}[a-z]?\)|\bet\s+al\.?,?\s*\(?(?:19|20)\d{2}[a-z]?\)?"                 # autor e ano
    r"|\b(?:pp?|pág|págs|Tab|Tabela|Fig|Figura|Eq|Equação|Seção|Cap|Capítulo)\.?\s*(?:\d+(?:[-–.]\d+)*|[IVXLC]+\b)"  # localizadores
    r"|\b(?:IEEE|IEC|ISO|NBR|ABNT)(?:\s+Std)?\.?\s*\d+(?:[-:–]\d+)*"                        # normas
    r"|\b[A-Za-zÀ-ÿ_]+\d+[A-Za-z]?\b",                                                       # F1, F7M, p99
    re.IGNORECASE)
_LIST_MARKER = re.compile(r"^\s*(?:#+\s*)?(?:\d+[.)]|[-*+])\s+")  # itens de lista e títulos numerados
# O traço depois de %, ) ou ° é de intervalo, não sinal de menos.
_NUMBER = re.compile(r"(?<![\w.,])(?:(?<![%)°])[-−–])?\d(?:[\d.,]*\d)?(?:[eE][-+−]?\d+)?")
_SUPERSCRIPT = str.maketrans("⁰¹²³⁴⁵⁶⁷⁸⁹⁻⁺", "0123456789-+")
_SUPERSCRIPTS = re.compile(r"[⁰¹²³⁴⁵⁶⁷⁸⁹⁻⁺]+")
# a × 10^-n, a·10⁻ⁿ, a \times 10^{-n}: a mesma grandeza em notação científica.
_POWER_OF_TEN = re.compile(r"(\d[\d.,]*)\s*(?:×|\\times|\\cdot|·|\*|x)\s*10\s*\^\s*\{?\s*([-−+]?\d+)\s*\}?")
_BARE_POWER = re.compile(r"(?<![\d.,])10\s*\^\s*\{?\s*[-−+]?\d+\s*\}?")
_SCRIPT = re.compile(r"(?<=[A-Za-z}\)])[_^](?:\{[^{}]*\}|[-−+]?\w+)")


def _normalize(text: str) -> str:
    """Escritas equivalentes viram a mesma: vírgula de LaTeX, potências de 10 e fórmulas sem os cifrões."""
    text = text.replace("{,}", ",")
    text = _SUPERSCRIPTS.sub(lambda m: "^" + m.group(0).translate(_SUPERSCRIPT), text)
    text = _POWER_OF_TEN.sub(lambda m: f"{m.group(1)}e{m.group(2).replace('−', '-')}", text)
    text = _BARE_POWER.sub(" ", text)  # 10^-6 solto é escala de unidade, não número
    text = _SCRIPT.sub("", text)  # índices e expoentes de símbolos: x_{1}, e^{-2t}
    return re.sub(r"\$\$?|\\[()\[\]]", " ", text)


def _candidates(token: str) -> set[Decimal]:
    """Valores possíveis de um número escrito com vírgula ou ponto; '2.041' pode ser 2041 ou 2,041."""
    text = token.replace("−", "-").replace("–", "-")
    mantissa, _, exponent = re.sub(r"[eE]", "e", text).partition("e")
    options = set()
    if "," in mantissa and "." in mantissa:
        decimal = max(mantissa.rfind(","), mantissa.rfind("."))
        options.add(re.sub(r"[.,]", "", mantissa[:decimal]) + "." + mantissa[decimal + 1:])
    elif "," in mantissa or "." in mantissa:
        separator = "," if "," in mantissa else "."
        if mantissa.count(separator) == 1:
            options.add(mantissa.replace(separator, "."))
        if re.fullmatch(rf"-?\d{{1,3}}(?:\{separator}\d{{3}})+", mantissa):
            options.add(mantissa.replace(separator, ""))
        if not options:
            options.add(mantissa.replace(separator, ""))
    else:
        options.add(mantissa)
    values = set()
    for option in options:
        try:
            values.add(Decimal(option + (f"e{exponent}" if exponent else "")).normalize())
        except InvalidOperation:
            continue
    return values


def numbers_in(text: str, *, short_dates: frozenset[str] = frozenset()) -> list[tuple[str, set[Decimal]]]:
    """Os números de um texto, como escritos, com os valores possíveis de cada um.

    `short_dates` são os dia/mês de datas conhecidas (27/09): só esses contam como data sem o ano.
    """
    clean = _ANY_MARK.sub(" ", _LIST_MARKER.sub("", text))
    clean = _IGNORED.sub(" ", _normalize(clean))
    for date in short_dates:
        clean = re.sub(rf"(?<![\d.,/]){re.escape(date)}(?![\d/]|[.,]\d)", " ", clean)
    found = []
    for match in _NUMBER.finditer(clean):
        values = _candidates(match.group(0))
        if values:
            found.append((match.group(0), values))
    return found


def split_grouped(text: str) -> str:
    """[R1, R4], [R1 e R4], [R1-R3] e grupos mistos como [R1, Kabc] viram marcas separadas, para cada
    uma ser conferida e exibida."""
    def expand(match: re.Match) -> str:
        inside = match.group(1)
        span = re.fullmatch(r"R(\d+)\s*[-–]\s*R(\d+)", inside)
        if span and int(span.group(1)) < int(span.group(2)) <= int(span.group(1)) + 20:
            return "".join(f"[R{n}]" for n in range(int(span.group(1)), int(span.group(2)) + 1))
        return "".join(f"[{mark}]" for mark in re.findall(_ONE, inside))

    return _GROUP.sub(expand, text)


def _dates_of(text: str) -> tuple[set[str], set[Decimal]]:
    """Dia/mês e ano das datas impressas num bloco: 27/09 e 2026 podem aparecer sozinhos na resposta."""
    short, years = set(), set()
    for day_month, year in _DATE_WITH_YEAR.findall(text):
        short.add(day_month)
        years.add(Decimal(year))
    for year in re.findall(r"\b(\d{4})-\d{2}-\d{2}\b", text):
        years.add(Decimal(year))
    return short, years


def _spans(line: str) -> list[tuple[str, list[str]]]:
    """Trechos da linha, cada um com as marcas que o fecham; o resto depois da última marca vem sem marcas."""
    spans, start, position = [], 0, 0
    matches = list(_ANY_MARK.finditer(line))
    while position < len(matches):
        group = [matches[position]]
        while position + 1 < len(matches) and not line[group[-1].end():matches[position + 1].start()].strip(" ,;e"):
            position += 1
            group.append(matches[position])
        spans.append((line[start:group[0].start()], [m.group(1) for m in group]))
        start = group[-1].end()
        position += 1
    spans.append((line[start:], []))
    return spans


def check_numbers(answer: str, blocks: dict[str, str], shared: str = "") -> dict:
    """Marcas usadas, marcas que não existem, números que não conferem e quantos ficaram sem marca.

    `blocks` leva de cada id ao texto inteiro do bloco (título, fonte e tabela); `shared` é o texto
    que vale para qualquer bloco (as notas dos indicadores).
    """
    used = list(dict.fromkeys(RESULT_MARK.findall(answer)))
    invalid = [mark for mark in used if mark not in blocks]
    shared_values = set().union(*(values for _, values in numbers_in(shared)), set())
    allowed_by_block, dates_by_block = {}, {}
    for mark, text in blocks.items():
        short, years = _dates_of(text)
        dates_by_block[mark] = short
        allowed_by_block[mark] = set().union(*(values for _, values in numbers_in(text)), years, shared_values)
    everything = set().union(*allowed_by_block.values(), shared_values)
    known_dates = frozenset().union(*dates_by_block.values())
    unverified, unmarked, inherited = [], 0, []
    for line in answer.splitlines():
        if not line.strip():
            continue
        own = [mark for mark in RESULT_MARK.findall(line) if mark in blocks]
        structured = line.lstrip().startswith("|") or bool(_LIST_MARKER.match(line))
        if own:
            inherited = own
        elif not structured:
            inherited = []  # um parágrafo sem marca encerra a herança
        line_marks = own or (inherited if structured else [])
        # Fica fora o trecho que termina numa marca de documento [K…] ou da web [Wn]: é dessa fonte.
        texts = [text for text, marks in _spans(line) if not marks or any(mark.startswith("R") for mark in marks)]
        if not line_marks:
            # Sem marca, só conta o número que também não está em nenhum resultado enviado.
            unmarked += sum(1 for text in texts for _, values in numbers_in(text, short_dates=known_dates)
                            if not values & everything)
            continue
        allowed = set().union(*(allowed_by_block[mark] for mark in line_marks))
        short_dates = frozenset().union(*(dates_by_block[mark] for mark in line_marks))
        for text in texts:
            for written, values in numbers_in(text, short_dates=short_dates):
                if not values & allowed and written not in unverified:
                    unverified.append(written)
    return {"used": used, "invalid": invalid, "unverified": unverified, "unmarked": unmarked}
