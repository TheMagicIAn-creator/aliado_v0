"""Limpeza das páginas e trechos por frase (lote 29).

O texto guardado de cada página não muda. Aqui se decide o que dele vira trecho de busca:
- as linhas de cabeçalho e de rodapé que se repetem nas páginas saem;
- o sumário e a lista de referências ficam marcados como partes de apoio, fora da busca comum;
- o restante é dividido em frases inteiras, juntadas até o limite de tokens do encoder.
Cada trecho continua sendo uma fatia exata do texto da página.
"""

from __future__ import annotations

import math
import re
import statistics
from bisect import bisect_left

from aliado.knowledge.metadata import GLYPHS
from aliado.knowledge.stopwords import plain

LIMIT = 110
# Partes de apoio: cheias de palavras-chave e vazias de conteúdo. A marca vai no local do trecho.
SUMMARY, REFERENCES = "sumário", "referências"
_MARKS = tuple(f" · {kind}" for kind in (SUMMARY, REFERENCES))
# Pergunta que pede o sumário ou as referências: as partes de apoio entram na busca.
SUPPORT_WORDS = frozenset(
    "sumario capitulo capitulos referencia referencias bibliografia bibliografica bibliograficas cita citam "
    "citado citada citados citadas citacao citacoes contents chapter chapters reference references "
    "bibliography cite cites cited citation citations".split())
# Cabeçalho e rodapé: linhas das bordas da página que se repetem, com os números trocados.
EDGE_LINES = 3
EDGE_SHARE = 0.30
MIN_PAGES = 4
# Linha de borda com o número da página: basta aparecer em 5 páginas, se o número acompanhar a página em
# 60% das vezes entre ocorrências próximas (até 4 páginas de distância).
TRACK_PAGES, TRACK_GAP, TRACK_SHARE = 5, 4, 0.60
# Legenda de figura ou tabela no pé da página não é rodapé.
_CAPTION = re.compile(r"(?:fig(?:ure|ura)?s?\.?|tab(?:le|ela)?s?\.?|quadro|gr[áa]fico)\s*#")
# Sumário: página em que boa parte das linhas tem pontilhado.
_LEADER = re.compile(r"(?:\.[ \t]?){6,}|…{3,}")
SUMMARY_LINES, SUMMARY_SHARE = 5, 0.40
# Lista de referências: começa num título próprio e segue enquanto aparecem começos de entrada.
_HEADING = re.compile(
    r"(?:\d{1,2}(?:\.\d{1,2})*\.?\s+|[ivxlc]{1,5}\.\s+)?"
    r"(?:references?|refer[êe]ncias(?:\s+bibliogr[áa]ficas)?|bibliography|bibliografia|works\s+cited|literature\s+cited)"
    r"\s*:?", re.IGNORECASE)
_NUMBERED = re.compile(r"\s*(?:\[(\d{1,3})\]\s*|\((\d{1,3})\)\s*|(\d{1,3})\.\s+)\S")
# "Baschel, S.", "Sarquis Filho, E. A." ou, na ABNT, "LAFRAIA, João".
_AUTHOR = re.compile(
    r"\s*(?:[A-ZÀ-Ý][\w'’\-]*(?:\s+(?:[A-ZÀ-Ý][\w'’\-]*|d[aeo]s?|v[ao]n|der|del|di|la|le)){0,3},\s*[A-ZÀ-Ý]\."
    r"|[A-ZÀ-Ý]{2,}(?:\s+[A-ZÀ-Ý]{2,}){0,3},\s*[A-ZÀ-Ý])")
_FEATURE = re.compile(r"\b(?:19|20)\d{2}[a-z]?\b|\bdoi\b|https?://|\bet\s+al\b|\bpp?\.\s*\d|\bvol\.|\bIn:", re.IGNORECASE)
MAX_GAP, MIN_ENTRIES, MAX_HEADING, MAX_ENTRY = 8, 3, 48, 4
# Fim de frase: pontuação final, espaço e começo com maiúscula ou número; ou uma linha em branco.
_BOUNDARY = re.compile(r"(?<=[.!?…])[\"'”’»)\]]*\s+(?=[\"'“‘«(\[]?[A-ZÀ-Ý0-9])|\n[ \t]*\n\s*")
_ABBREVIATIONS = frozenset(
    "al fig figs eq eqs tab ref refs sec no nº vol pp p pág pag cf vs etc dr dra sr sra prof eng ex approx aprox "
    "ed eds art cap inc ltd co jr st ca i.e e.g".split())
MIN_SENTENCE = 20
# Linha que começa uma legenda: "Fig. 3. Fault tree…", "Table 7-2— Failure modes", "Figura 4.3 – Formulário".
# A menção no meio do texto ("Figure 5 explains…") segue com letra minúscula e não conta.
_CAPTION_LINE = re.compile(
    r"^[ \t]*(?i:fig(?:ure|ura)?s?\.?|tab(?:le|ela)?s?\.?|quadro|gr[áa]fico)[ \t]*\d+(?:[.\-]\d+)*[ \t]*"
    r"(?:[.:—–|\-][ \t]*)?[A-ZÀ-Ý“\"]", re.MULTILINE)
# Numa frase maior que o limite, a linha bem mais curta que as outras fecha um bloco (título, fórmula, fim
# de parágrafo), e a que termina em pontuação também.
SHORT_LINE = 0.6
_CLOSING = (".", "!", "?", ":", ";")
# Na descrição de uma figura, o corte é procurado a partir de 60% do tamanho ideal do trecho, e o fim de
# frase ou de item que serve de corte é o ponto, a exclamação, a interrogação ou o ponto e vírgula.
FILL_FLOOR = 0.6
_FILL_STOPS = (".", "!", "?", ";")


def scheme(encoder) -> str | None:
    """Nome do esquema de trechos por frase deste encoder; None se ele só tem a própria divisão."""
    if getattr(encoder, "token_spans", None) is None:
        return None
    return f"frases{getattr(encoder, 'chunk_tokens', LIMIT)}-v1"


def marked(locator: str, kind: str | None) -> str:
    return f"{locator} · {kind}" if kind else locator


def support(locator: str) -> bool:
    """O local é de sumário ou de lista de referências."""
    return locator.endswith(_MARKS)


def asks_support(query: str) -> bool:
    return bool({plain(word) for word in re.findall(r"[^\W\d_]+", query)} & SUPPORT_WORDS)


def _lines(text: str, start: int = 0, end: int | None = None) -> list[tuple[int, int]]:
    spans, position, block = [], start, text[start:end]
    for whole, line in zip(block.splitlines(keepends=True), block.splitlines()):
        spans.append((position, position + len(line)))
        position += len(whole)
    return spans


def _pattern(line: str) -> str:
    return re.sub(r"\d+", "#", " ".join(line.lower().split()))


def _tracks_pages(found: list[tuple[int, tuple[int, ...]]]) -> bool:
    """Um dos números da linha acompanha a página: de uma ocorrência à seguinte, cresce o mesmo que ela.

    É o caso do cabeçalho de capítulo com o número da página ("106 3 Control Technology…"), que se repete
    em poucas páginas do livro. A legenda de figura e o título de tabela continuada não acompanham."""
    by_page: dict[int, tuple[int, ...]] = {}
    for page, digits in found:
        by_page.setdefault(page, digits)
    ordered = sorted(by_page.items())
    width = len(ordered[0][1])
    if len(ordered) < TRACK_PAGES or not width:
        return False
    pairs, hits = 0, [0] * width
    for (page, digits), (following, others) in zip(ordered, ordered[1:]):
        if following - page > TRACK_GAP or len(digits) != width or len(others) != width:
            continue
        pairs += 1
        for position in range(width):
            hits[position] += others[position] - digits[position] == following - page
    return pairs >= TRACK_PAGES - 1 and max(hits) >= TRACK_SHARE * pairs


def _edges(pages: list[str], numbers: list[int]) -> set[str]:
    """Os padrões de cabeçalho e rodapé: linhas das bordas, com os números trocados por #, que se repetem
    em boa parte das páginas ou que trazem o número da página."""
    if len(pages) < MIN_PAGES:
        return set()
    seen: dict[str, list[tuple[int, tuple[int, ...]]]] = {}
    for number, text in zip(numbers, pages):
        filled = [text[a:b] for a, b in _lines(text) if text[a:b].strip()]
        for line in dict.fromkeys(filled[:EDGE_LINES] + filled[-EDGE_LINES:]):
            pattern = _pattern(line)
            # Legenda não é rodapé, e uma linha só de números (a de uma tabela) só conta com 1 ou 2 números.
            if not _CAPTION.match(pattern) and (re.search(r"[^\W\d_]", pattern) or pattern.count("#") <= 2):
                seen.setdefault(pattern, []).append((number, tuple(int(digits) for digits in re.findall(r"\d+", line))))
    floor = max(3, math.ceil(EDGE_SHARE * len(pages)))
    return {pattern for pattern, found in seen.items()
            if len({page for page, _ in found}) >= floor or _tracks_pages(found)}


def _body(text: str, common: set[str]) -> tuple[int, int, int]:
    """A página sem o cabeçalho e o rodapé: início, fim e quantas linhas saíram.

    Só saem linhas seguidas a partir da borda, até 3 de cada lado: o que fica é uma fatia só do texto."""
    spans = [(a, b) for a, b in _lines(text) if text[a:b].strip()]
    repeated = [_pattern(text[a:b]) in common for a, b in spans]
    first, last = 0, len(spans)
    while first < min(EDGE_LINES, last) and repeated[first]:
        first += 1
    while last > first and len(spans) - last < EDGE_LINES and repeated[last - 1]:
        last -= 1
    if first >= last:
        return 0, 0, len(spans)
    return spans[first][0], spans[last - 1][1], first + len(spans) - last


def _is_summary(lines: list[str]) -> bool:
    filled = [line for line in lines if line.strip()]
    hits = sum(1 for line in filled if _LEADER.search(line))
    return hits >= SUMMARY_LINES and hits >= SUMMARY_SHARE * len(filled)


def _references(pages: list[str], bodies: list[tuple[int, int]], skip: set[int]) -> dict[int, list[tuple[int, int]]]:
    """As fatias de lista de referências, por página.

    A lista começa numa linha de título ("References", "Referências", "Bibliografia") e segue enquanto
    aparecem começos de entrada: a numeração seguida ou "Sobrenome, I.". Para depois de 8 linhas sem
    entrada ou quando a numeração recomeça do 1, e só vale com 3 entradas ou mais. Assim, um livro com
    referências por capítulo não perde o capítulo seguinte, e um título solto no meio do texto não conta.
    """
    regions: dict[int, list[tuple[int, int]]] = {}

    def close(state: dict) -> None:
        if state["entries"] < MIN_ENTRIES:
            return
        (first, a), (last, b) = state["start"], state["keep"]
        for index in range(first, last + 1):
            if index in skip:
                continue
            start, end = bodies[index]
            span = (a if index == first else start, b if index == last else end)
            if span[1] > span[0]:
                regions.setdefault(index, []).append(span)

    state = final = None
    for index, (text, (start, end)) in enumerate(zip(pages, bodies)):
        if index in skip:
            continue
        for a, b in _lines(text, start, end):
            line = text[a:b]
            if not line.strip():
                continue
            final = (index, b)
            if state is None:
                if len(line.strip()) <= MAX_HEADING and _HEADING.fullmatch(line.strip()):
                    state = {"start": (index, a), "keep": (index, b), "entries": 0, "gap": 0, "number": None}
                continue
            numbered = _NUMBERED.match(line)
            number = int(next(group for group in numbered.groups() if group)) if numbered else None
            if number == 1 and (state["number"] or 0) >= MIN_ENTRIES:
                close(state)  # outra lista numerada começa: a de referências acabou
                state = None
                continue
            if number is not None:
                entry = number <= 3 if state["number"] is None else 0 < number - state["number"] <= 3
            else:
                entry = bool(_AUTHOR.match(line))
            if entry:
                state.update(entries=state["entries"] + 1, gap=0, keep=(index, b),
                             number=number if number is not None else state["number"])
                continue
            state["gap"] += 1
            if state["gap"] >= MAX_GAP:
                close(state)
                state = None
            elif state["entries"] and state["gap"] <= MAX_ENTRY and _FEATURE.search(line):
                state["keep"] = (index, b)  # continuação da entrada, com o ano ou as páginas
    if state is not None:  # a lista vai até o fim do documento
        state["keep"] = final
        close(state)
    return regions


def clean_pages(pages: list[str], numbers: list[int] | None = None) -> tuple[list[list[tuple[int, int, str | None]]], dict]:
    """Para cada página, as fatias do texto que viram trechos: (início, fim, parte de apoio ou None).

    `numbers` são os números das páginas no arquivo. Devolve também o registro do que saiu, com as páginas
    pela posição na lista."""
    common = _edges(pages, numbers or list(range(1, len(pages) + 1)))
    bodies, removed = [], 0
    for text in pages:
        start, end, dropped = _body(text, common)
        bodies.append((start, end))
        removed += dropped
    summaries = {index for index, (text, (start, end)) in enumerate(zip(pages, bodies))
                 if _is_summary([text[a:b] for a, b in _lines(text, start, end)])}
    regions = _references(pages, bodies, summaries)
    parts, glyphs = [], 0
    for index, (text, (start, end)) in enumerate(zip(pages, bodies)):
        if index in summaries:
            spans = [(start, end, SUMMARY)]
        else:
            spans, position = [], start
            for a, b in regions.get(index, ()):
                spans += [(position, a, None), (a, b, REFERENCES)]
                position = b
            spans.append((position, end, None))
        cut = []
        for a, b, kind in spans:
            position = a
            for match in GLYPHS.finditer(text, a, b):  # códigos de glifo sem texto
                glyphs += 1
                cut.append((position, match.start(), kind))
                position = match.end()
            cut.append((position, b, kind))
        parts.append([(a, b, kind) for a, b, kind in cut if text[a:b].strip()])
    record = {"linhas_de_borda": removed, "padroes_de_borda": sorted(common), "sumario": sorted(summaries),
              "referencias": sorted(regions), "glifos": glyphs}
    return parts, record


def sentences(text: str, start: int = 0, end: int | None = None) -> list[tuple[int, int]]:
    """Fatias de frases inteiras, na ordem, entre `start` e `end`."""
    end = len(text) if end is None else end
    spans, position = [], start
    for match in _BOUNDARY.finditer(text, start, end):
        gap = match.group()
        stop = match.start() + len(gap) - len(gap.lstrip("\"'”’»)]"))
        if text[match.start() - 1] == ".":
            words = text[position:match.start()].split()
            word = words[-1].rstrip(".").lstrip("([\"'“‘«").lower() if words else ""
            if word in _ABBREVIATIONS or (len(word) == 1 and word.isalpha()):
                continue  # "et al.", "Fig.", iniciais de um nome: a frase continua
        spans.append((position, stop))
        position = match.end()
    if position < end:
        spans.append((position, end))
    merged, carry = [], None
    for a, b in spans:  # um pedaço curto demais ("1.", "Sim.") segue com a frase seguinte
        a = carry if carry is not None else a
        carry = None
        if len(text[a:b].strip()) < MIN_SENTENCE:
            carry = a
            continue
        merged.append((a, b))
    if carry is not None:
        merged = merged[:-1] + [(merged[-1][0], spans[-1][1])] if merged else [(carry, spans[-1][1])]
    return merged


def pack(text: str, start: int, end: int, tokens: list[tuple[int, int]], limit: int = LIMIT) -> list[tuple[int, int]]:
    """Os trechos de uma fatia do texto: frases inteiras, com até `limit` tokens, sem sobreposição.

    A legenda de figura ou de tabela começa sempre um trecho novo. Junta ao parágrafo de cima, ela se
    perdia na busca: a pergunta sobre a figura deixava de achar a página."""
    cuts = [start] + [match.start() for match in _CAPTION_LINE.finditer(text, start, end) if match.start() > start] + [end]
    return [span for a, b in zip(cuts, cuts[1:]) for span in _pack(text, a, b, tokens, limit)]


def _pack(text: str, start: int, end: int, tokens: list[tuple[int, int]], limit: int) -> list[tuple[int, int]]:
    """Trechos de frases inteiras com até `limit` tokens e tamanhos equilibrados.

    Uma frase que sozinha passa do limite (tabela, fórmula, lista sem pontuação) é cortada nas quebras de
    linha, de preferência depois de uma linha curta ou terminada em pontuação, que fecha um bloco; uma linha
    que ainda passa, a cada `limit` tokens."""
    starts = [a for a, _ in tokens]

    def count(a: int, b: int) -> int:
        return bisect_left(starts, b) - bisect_left(starts, a)

    lengths = [len(text[a:b].strip()) for a, b in _lines(text, start, end) if text[a:b].strip()]
    short = SHORT_LINE * statistics.median(lengths) if lengths else 0
    units = []
    for a, b in sentences(text, start, end):
        if count(a, b) <= limit:
            units.append((a, b))
            continue
        blocks, begin, last_end = [], None, a
        for line_start, line_end in _lines(text, a, b):
            line = text[line_start:line_end].strip()
            if not line:
                continue
            begin, last_end = line_start if begin is None else begin, line_end
            if len(line) < short or line.endswith(_CLOSING):
                blocks.append((begin, line_end))
                begin = None
        if begin is not None:
            blocks.append((begin, last_end))
        for block_start, block_end in blocks:
            if count(block_start, block_end) <= limit:
                units.append((block_start, block_end))
                continue
            for line_start, line_end in _lines(text, block_start, block_end):
                if count(line_start, line_end) <= limit:
                    units.append((line_start, line_end))
                    continue
                index, last = bisect_left(starts, line_start), bisect_left(starts, line_end)
                while index < last:
                    stop = min(index + limit, last)
                    # O corte recua até o começo de uma palavra, para não parti-la ao meio.
                    while (stop < last and stop - index > limit // 2
                           and not (text[tokens[stop][0]].isspace() or text[tokens[stop][0] - 1].isspace())):
                        stop -= 1
                    units.append((tokens[index][0], tokens[stop - 1][1]))
                    index = stop
    sized = [(a, b, count(a, b)) for a, b in units]
    sized = [unit for unit in sized if unit[2]]
    total = sum(size for _, _, size in sized)
    target = total / max(1, math.ceil(total / limit))
    chunks, current, filled = [], None, 0
    for a, b, size in sized:
        if current is not None and (filled + size > limit or filled >= target):
            chunks.append(current)
            current, filled = None, 0
        current = (a, b) if current is None else (current[0], b)
        filled += size
    if current is not None:
        chunks.append(current)
    trimmed = []
    for a, b in chunks:
        piece = text[a:b]
        a, b = a + len(piece) - len(piece.lstrip()), b - (len(piece) - len(piece.rstrip()))
        if b > a:
            trimmed.append((a, b))
    return trimmed


def filled(text: str, encoder, head: int = 0) -> list[str] | None:
    """Trechos de tamanho parecido, até o limite de tokens, para um texto que é uma coisa só (a descrição de
    uma figura).

    O que falta é repartido por igual entre os trechos que ainda cabem, e o corte fica no ponto mais próximo
    desse tamanho, entre 60% dele e o limite: de preferência no fim de uma linha; senão no fim de uma frase
    ou de um item (ponto, ponto e vírgula); senão no começo de uma palavra. Nenhum trecho fica só com a sobra.
    O primeiro vai pelo menos até a posição `head` do texto, quando ela cabe no limite: é o que garante a
    legenda junto com o começo da descrição. None se o encoder só tem a própria divisão."""
    spans = getattr(encoder, "token_spans", None)
    if spans is None:
        return None
    tokens, limit = spans(text), getattr(encoder, "chunk_tokens", LIMIT)
    chunks, index, last = [], 0, len(tokens)
    while index < last:
        size = math.ceil((last - index) / math.ceil((last - index) / limit))
        stop = index + size
        if stop < last:
            lines, stops, words = [], [], []
            floor, hard = index + max(1, int(FILL_FLOOR * size)), min(index + limit, last - 1)
            if index == 0 and head:
                reach = bisect_left([a for a, _ in tokens], head)
                floor = max(floor, reach) if reach <= hard else floor
            for cut in range(floor, hard + 1):
                gap = text[tokens[cut - 1][1]:tokens[cut][0]]
                if "\n" in gap:
                    lines.append(cut)
                elif text[tokens[cut - 1][0]:tokens[cut - 1][1]].rstrip().endswith(_FILL_STOPS):
                    stops.append(cut)
                elif gap or text[tokens[cut][0]:tokens[cut][0] + 1].isspace():
                    words.append(cut)
            stop = min(lines or stops or words or [stop], key=lambda cut: (abs(cut - stop), -cut))
        piece = text[tokens[index][0]:tokens[stop - 1][1]].strip()
        if piece:
            chunks.append(piece)
        index = stop
    return chunks


def pieces(text: str, parts: list[tuple[int, int, str | None]], encoder) -> list[tuple[str, str | None]] | None:
    """Os trechos de um texto, cada um com a sua parte de apoio; None se o encoder só tem a própria divisão."""
    spans = getattr(encoder, "token_spans", None)
    if spans is None:
        return None
    tokens, limit = spans(text), getattr(encoder, "chunk_tokens", LIMIT)
    return [(text[a:b], kind) for start, end, kind in parts for a, b in pack(text, start, end, tokens, limit)]
