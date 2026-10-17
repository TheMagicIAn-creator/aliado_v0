"""PDF formal de um resultado (spec 0034): capa, sumário, seções numeradas e tabelas, com o JSON anexo.

Só texto e tabelas, desenhados pelo matplotlib (sem pyplot) e medidos antes de desenhar. Cada página
é diagramada primeiro e desenhada depois; assim o sumário e o "página n de N" saem numa passada só.
O pypdf anexa o `resultado.json` e põe um marcador por seção. Os números chegam já formatados pelo
experimento, que monta os blocos (`report`): seções, parágrafos, listas, tabelas e linhas de comando.
"""

from __future__ import annotations

import io
import json
import math
import threading
from dataclasses import dataclass, field
from datetime import datetime
from functools import cache

PAGE_W, PAGE_H = 595.28, 841.89  # A4, em pontos
LEFT = RIGHT = 62.0
TOP, BOTTOM = 76.0, 70.0
WIDTH = PAGE_W - LEFT - RIGHT
INK, MUTED, ACCENT = "#1b1b1b", "#5f6368", "#1f3a5f"
SERIF, SANS, MONO = "DejaVu Serif", "DejaVu Sans", "DejaVu Sans Mono"
# estilo: (família, tamanho, negrito, itálico, entrelinha, cor)
STYLES = {
    "corpo": (SERIF, 10.2, False, False, 14.6, INK),
    "secao": (SANS, 13.0, True, False, 19.0, ACCENT),
    "legenda": (SANS, 8.8, True, False, 12.2, INK),
    "celula": (SANS, 8.3, False, False, 11.2, INK),
    "cabecalho": (SANS, 8.3, True, False, 11.2, INK),
    "nota": (SANS, 7.6, False, True, 10.4, MUTED),
    "codigo": (MONO, 8.0, False, False, 11.4, INK),
    "sumario": (SERIF, 10.5, False, False, 18.0, INK),
    "margem": (SANS, 7.6, False, False, 10.0, MUTED),
    "capa_selo": (SANS, 9.0, True, False, 13.0, ACCENT),
    "capa_titulo": (SANS, 25.0, True, False, 31.0, INK),
    "capa_sub": (SERIF, 13.0, False, False, 18.0, MUTED),
    "capa_rotulo": (SERIF, 11.0, False, False, 15.5, INK),
}
PAD, ROW_PAD = 4.5, 2.4
_lock = threading.Lock()


@cache
def _font(style: str):
    from matplotlib.font_manager import FontProperties

    family, size, bold, italic = STYLES[style][:4]
    return FontProperties(family=family, size=size, weight="bold" if bold else "normal",
                          style="italic" if italic else "normal")


@cache
def _measurer():
    from matplotlib.textpath import TextToPath

    return TextToPath()


@cache
def width(text: str, style: str) -> float:
    """Largura em pontos, sem as dicas de pixel: um pouco folgada, para nenhuma linha passar da margem."""
    return _measurer().get_text_width_height_descent(text, _font(style), ismath=False)[0] if text else 0.0


def wrap(text: str, style: str, limit: float) -> list[str]:
    """Quebra por palavra; uma palavra maior que a linha (um hash, um caminho) é quebrada por letra."""
    lines = []
    for paragraph in str(text).split("\n"):
        line = ""
        for word in paragraph.split(" "):
            candidate = f"{line} {word}" if line else word
            if width(candidate, style) <= limit:
                line = candidate
                continue
            if line:
                lines.append(line)
            while width(word, style) > limit:
                cut = next((i for i in range(len(word), 0, -1) if width(word[:i], style) <= limit), 1)
                lines.append(word[:cut])
                word = word[cut:]
            line = word
        lines.append(line)
    return lines


@dataclass
class _Layout:
    pages: list[list[tuple]] = field(default_factory=list)
    sections: list[tuple[str, str, int]] = field(default_factory=list)  # número, título, índice da página
    y: float = TOP
    tables: int = 0

    def new_page(self) -> None:
        self.pages.append([])
        self.y = TOP

    def room(self) -> float:
        return PAGE_H - BOTTOM - self.y

    def need(self, height: float) -> None:
        if height > self.room() + 0.01:
            self.new_page()

    def text(self, x: float, text: str, style: str, *, align: str = "left", color: str | None = None) -> None:
        """Uma linha na posição atual; a linha de base fica a 3/4 da entrelinha."""
        self.pages[-1].append(("texto", x, self.y + STYLES[style][4] * 0.74, text, style, align, color))

    def rule(self, x0: float, x1: float, y: float, thickness: float, color: str = INK) -> None:
        self.pages[-1].append(("linha", x0, x1, y, thickness, color))

    def lines(self, lines: list[str], style: str, *, indent: float = 0.0, first: str | None = None) -> None:
        leading = STYLES[style][4]
        for index, line in enumerate(lines):
            # Nem a primeira linha sozinha no pé da página, nem a última sozinha no alto da seguinte.
            alone = (index == 0 and len(lines) > 1) or (index > 0 and len(lines) - index == 2)
            self.need(2 * leading if alone else leading)
            if index == 0 and first:
                self.text(LEFT, first, style)
            self.text(LEFT + indent, line, style)
            self.y += leading


def _section(layout: _Layout, number: str, title: str) -> None:
    # O título nunca fica sozinho no pé da página: vai junto com duas linhas do que vem depois.
    layout.need(STYLES["secao"][4] + 10 + 2 * STYLES["corpo"][4])
    if layout.y > TOP:
        layout.y += 8
    layout.sections.append((number, title, len(layout.pages) - 1))
    layout.text(LEFT, f"{number}   {title}", "secao")
    layout.y += STYLES["secao"][4] + 4


def _columns(columns: list[str], rows: list[list[str]], numeric: list[bool]) -> list[float]:
    """Larguras: a natural de cada coluna; sobra vai para as de texto, e falta é tirada delas."""
    natural = [max([width(str(name), "cabecalho")] + [width(str(row[i]), "celula") for row in rows]) + 2 * PAD
               for i, name in enumerate(columns)]
    textual = [i for i, flag in enumerate(numeric) if not flag] or list(range(len(columns)))
    total = sum(natural)
    if total <= WIDTH:
        extra = (WIDTH - total) / len(textual)
        return [value + (extra if i in textual else 0.0) for i, value in enumerate(natural)]
    # Colunas de texto curtas ficam inteiras; só as longas quebram linha.
    long = [i for i in textual if natural[i] > WIDTH * 0.3] or textual
    fixed = sum(value for i, value in enumerate(natural) if i not in long)
    room = max(WIDTH - fixed, 50.0 * len(long))
    scale = room / sum(natural[i] for i in long)
    widths = [max(50.0, value * scale) if i in long else value for i, value in enumerate(natural)]
    if sum(widths) > WIDTH:  # até as colunas de números precisam encolher
        widths = [value * WIDTH / sum(widths) for value in widths]
    return widths


def _row(cells: list[str], widths: list[float], style: str) -> tuple[float, list[list[str]]]:
    wrapped = [wrap(str(cell), style, w - 2 * PAD) for cell, w in zip(cells, widths)]
    return max(len(lines) for lines in wrapped) * STYLES[style][4] + 2 * ROW_PAD, wrapped


def _draw_row(layout: _Layout, wrapped: list[list[str]], widths: list[float], numeric: list[bool], style: str) -> None:
    leading, x = STYLES[style][4], LEFT
    top = layout.y
    for lines, w, right in zip(wrapped, widths, numeric):
        layout.y = top + ROW_PAD
        for line in lines:
            if right:
                layout.text(x + w - PAD, line, style, align="right")
            else:
                layout.text(x + PAD, line, style)
            layout.y += leading
        x += w
    layout.y = top + max(len(lines) for lines in wrapped) * leading + 2 * ROW_PAD


def _table(layout: _Layout, block: dict) -> None:
    columns, rows = [str(c) for c in block["colunas"]], [[str(c) for c in row] for row in block["linhas"]]
    numeric = list(block.get("numericas") or [False] * len(columns))
    widths = _columns(columns, rows, numeric)
    numbered = block.get("numerada", True)
    layout.tables += numbered
    title = f"Tabela {layout.tables} — {block['legenda']}" if numbered else block["legenda"]
    caption = wrap(title, "legenda", WIDTH)
    head_height, head = _row(columns, widths, "cabecalho")
    measured = [_row(row, widths, "celula") for row in rows]

    def start(continued: bool) -> None:
        layout.lines(caption if not continued else wrap(f"{title} (continuação)", "legenda", WIDTH), "legenda")
        layout.y += 3
        layout.rule(LEFT, LEFT + WIDTH, layout.y, 0.8)
        _draw_row(layout, head, widths, numeric, "cabecalho")
        layout.rule(LEFT, LEFT + WIDTH, layout.y, 0.5)

    first = sum(height for height, _ in measured[:2])
    layout.need(len(caption) * STYLES["legenda"][4] + 3 + head_height + first + 4)
    if layout.y > TOP:
        layout.y += 4
    start(False)
    for height, wrapped in measured:
        if height > layout.room() - 2:
            layout.rule(LEFT, LEFT + WIDTH, layout.y, 0.5)
            layout.new_page()
            start(True)
        _draw_row(layout, wrapped, widths, numeric, "celula")
    layout.rule(LEFT, LEFT + WIDTH, layout.y, 0.8)
    layout.y += 5
    for note in block.get("notas") or ():
        layout.lines(wrap(note, "nota", WIDTH), "nota")
    layout.y += 8


def _cover(layout: _Layout, result: dict) -> None:
    layout.new_page()
    layout.rule(LEFT, LEFT + WIDTH, TOP - 20, 2.6, ACCENT)
    layout.y = TOP + 10
    layout.text(LEFT, "RELATÓRIO DE EXPERIMENTO", "capa_selo")
    layout.y += 40
    for line in wrap(result["titulo"], "capa_titulo", WIDTH):
        layout.text(LEFT, line, "capa_titulo")
        layout.y += STYLES["capa_titulo"][4]
    layout.y += 6
    layout.text(LEFT, f"Base de dados: {result['base']}", "capa_sub")
    layout.y += STYLES["capa_sub"][4] + 18
    for line in wrap(result["rotulo"], "capa_rotulo", WIDTH):
        layout.text(LEFT, line, "capa_rotulo")
        layout.y += STYLES["capa_rotulo"][4]
    layout.y += 30
    rows = [[item["rotulo"], item["texto"]] for item in result.get("parametros_texto", ())]
    rows += [["Rodada", result.get("rodada") or "—"], ["Executada em", _when(result.get("executado_em"))],
             ["Relatório gerado em", _when(datetime.now().astimezone().isoformat(timespec="minutes"))],
             ["Versão do AL-IAdo", result.get("versao") or "—"]]
    _table(layout, {"legenda": "Identificação da rodada", "colunas": ["Item", "Valor"], "linhas": rows,
                    "numericas": [False, False], "numerada": False})
    layout.y = PAGE_H - BOTTOM - 40
    for line in wrap("O resultado.json desta rodada vai anexado a este PDF. Na aba Ciência, \"Comparar com "
                     "resultado salvo\" lê esse anexo e mostra a rodada guardada ao lado da atual.", "nota", WIDTH):
        layout.text(LEFT, line, "nota")
        layout.y += STYLES["nota"][4]
    layout.rule(LEFT, LEFT + WIDTH, PAGE_H - BOTTOM + 8, 0.6, ACCENT)


def _when(iso: str | None) -> str:
    if not iso:
        return "—"
    text = str(iso)
    day = "/".join(reversed(text[:10].split("-")))
    return f"{day} {text[11:16]}" if len(text) >= 16 and text[10] == "T" else day


def _content(layout: _Layout, blocks: list[dict]) -> None:
    layout.new_page()
    number = 0
    for block in blocks:
        kind = block["tipo"]
        if kind == "secao":
            number += 1
            _section(layout, str(number), block["titulo"])
        elif kind == "paragrafo":
            layout.lines(wrap(block["texto"], "corpo", WIDTH), "corpo")
            layout.y += 6
        elif kind == "lista":
            for item in block["itens"]:
                layout.lines(wrap(item, "corpo", WIDTH - 14), "corpo", indent=14, first="•")
                layout.y += 2
            layout.y += 4
        elif kind == "codigo":
            layout.lines(wrap(block["texto"], "codigo", WIDTH - 12), "codigo", indent=12)
            layout.y += 8
        elif kind == "tabela":
            _table(layout, block)
        else:
            raise ValueError(f"Bloco desconhecido no relatório: {kind}")


def _per_page() -> int:
    return int((PAGE_H - TOP - BOTTOM - STYLES["secao"][4] - 14) // STYLES["sumario"][4])


def _contents(layout: _Layout, offset: int) -> list[list[tuple]]:
    """As páginas do sumário, já com os números de página do conteúdo."""
    per_page = _per_page()
    pages = []
    for start in range(0, max(1, len(layout.sections)), per_page):
        page = _Layout()
        page.new_page()
        page.text(LEFT, "Sumário", "secao")
        page.y += STYLES["secao"][4] + 14
        for number, name, index in layout.sections[start:start + per_page]:
            label, target = f"{number}   {name}", str(index + offset + 1)
            page.text(LEFT, label, "sumario")
            page.text(LEFT + WIDTH, target, "sumario", align="right")
            gap = WIDTH - width(label, "sumario") - width(target, "sumario") - 16
            dots = " ." * max(0, int(gap // width(" .", "sumario")))
            page.text(LEFT + WIDTH - width(target, "sumario") - 8, dots, "sumario", align="right", color=MUTED)
            page.y += STYLES["sumario"][4]
        pages.append(page.pages[0])
    return pages


def _frame(ops: list[tuple], title: str, run: str, number: int, total: int) -> list[tuple]:
    """Cabeçalho e rodapé das páginas depois da capa."""
    layout = _Layout(pages=[list(ops)])
    layout.rule(LEFT, LEFT + WIDTH, TOP - 18, 0.5, MUTED)
    layout.y = TOP - 34
    layout.text(LEFT, title, "margem")
    layout.text(LEFT + WIDTH, run, "margem", align="right")
    layout.rule(LEFT, LEFT + WIDTH, PAGE_H - BOTTOM + 20, 0.5, MUTED)
    layout.y = PAGE_H - BOTTOM + 26
    layout.text(LEFT, "AL-IAdo · relatório de experimento", "margem")
    layout.text(LEFT + WIDTH, f"página {number} de {total}", "margem", align="right")
    return layout.pages[0]


def layout(result: dict, blocks: list[dict]) -> tuple[list[list[tuple]], list[tuple[str, str, int]]]:
    """Todas as páginas, prontas para desenhar, e as seções com a página de cada uma (contando a capa)."""
    cover = _Layout()
    _cover(cover, result)
    body = _Layout()
    _content(body, blocks)
    offset = 1 + math.ceil(max(1, len(body.sections)) / _per_page())
    toc = _contents(body, offset)
    pages = cover.pages + toc + body.pages
    total = len(pages)
    run = result.get("rodada") or ""
    framed = [pages[0]] + [_frame(ops, result["titulo"], run, index + 1, total) for index, ops in enumerate(pages[1:], 1)]
    return framed, [(number, name, index + offset) for number, name, index in body.sections]


def _draw(ops: list[tuple]):
    from matplotlib.figure import Figure
    from matplotlib.lines import Line2D

    figure = Figure(figsize=(PAGE_W / 72, PAGE_H / 72), dpi=72)
    for op in ops:
        if op[0] == "linha":
            _, x0, x1, y, thickness, color = op
            figure.add_artist(Line2D([x0 / PAGE_W, x1 / PAGE_W], [1 - y / PAGE_H] * 2, transform=figure.transFigure,
                                     linewidth=thickness, color=color, solid_capstyle="butt"))
        else:
            _, x, y, text, style, align, color = op
            figure.text(x / PAGE_W, 1 - y / PAGE_H, text, fontproperties=_font(style), color=color or STYLES[style][5],
                        ha=align, va="baseline", parse_math=False)
    return figure


def render(result: dict, blocks: list[dict]) -> bytes:
    """O PDF pronto, com o `resultado.json` anexo e um marcador por seção."""
    from matplotlib import rc_context
    from matplotlib.backends.backend_pdf import PdfPages
    from pypdf import PdfReader, PdfWriter

    with _lock, rc_context({"pdf.fonttype": 42}):
        pages, sections = layout(result, blocks)
        buffer = io.BytesIO()
        with PdfPages(buffer, metadata={"Title": f"{result['titulo']} · {result.get('rodada') or ''}",
                                        "Author": "AL-IAdo", "Subject": result.get("rotulo") or "",
                                        "Creator": "AL-IAdo"}) as pdf:
            for ops in pages:
                pdf.savefig(_draw(ops))
    writer = PdfWriter(clone_from=PdfReader(io.BytesIO(buffer.getvalue())))
    writer.add_attachment("resultado.json", json.dumps(result, ensure_ascii=False, indent=2).encode("utf-8"))
    for number, name, index in sections:
        writer.add_outline_item(f"{number} {name}", index)
    writer.page_mode = "/UseOutlines"
    output = io.BytesIO()
    writer.write(output)
    return output.getvalue()
