"""Markdown do modelo em HTML seguro, com fórmulas preservadas e citações numeradas."""

from __future__ import annotations

import html
import re

from markdown_it import MarkdownIt

# HTML bruto do modelo nunca é aceito: texto vindo de PDFs não pode injetar código na página.
_MARKDOWN = MarkdownIt("commonmark", {"html": False, "linkify": False, "typographer": False}).enable(
    ["table", "strikethrough"])
MAX_RENDER_CHARS = 60_000
# $...$ exige conteúdo colado aos cifrões, para não tratar "R$ 5,00 e R$ 10" como fórmula.
_MATH = re.compile(r"\$\$.+?\$\$|\\\[.+?\\\]|\\\(.+?\\\)|(?<![\\\w])\$(?=\S)[^\n$]+?(?<=\S)\$", re.DOTALL)
_CITATION = re.compile(r"\[(K[^\]\s]*)\]")
_WEB = re.compile(r"\[W(\d+)\]")
_RESULT = re.compile(r"\[(R\d+)\]")


def render_markdown(text: str, sources: list[dict] | tuple = (), web_sources: list[dict] | tuple = (),
                    result_sources: list[dict] | tuple = ()) -> str:
    """Converte a resposta; `[Kid]` vira o número da fonte, `[Wn]`, o da fonte na web, e `[Rn]`, o
    bloco de resultados da pesquisa (lote 26), quando ele foi mesmo citado."""
    text = str(text or "")[:MAX_RENDER_CHARS]
    numbers = {source["citation_id"]: index for index, source in enumerate(sources, 1)}
    protected: list[str] = []

    def keep(fragment: str) -> str:
        protected.append(fragment)
        return f"ALIADOPH{len(protected) - 1}X"

    text = _MATH.sub(lambda match: keep(html.escape(match.group(0))), text)

    def cite(match: re.Match) -> str:
        number = numbers.get(match.group(1))
        if number is None:
            return match.group(0)
        return keep(f'<button type="button" class="cite" data-cite="{number}" '
                    f'aria-label="Fonte {number}">{number}</button>')

    text = _CITATION.sub(cite, text)

    def web(match: re.Match) -> str:
        number = int(match.group(1))
        if not 1 <= number <= len(web_sources):
            return match.group(0)
        return keep(f'<button type="button" class="cite cite-web" data-web="{number}" '
                    f'aria-label="Fonte na web {number}">{number}</button>')

    text = _WEB.sub(web, text)
    results = {source["citation_id"] for source in result_sources}

    def result(match: re.Match) -> str:
        mark = match.group(1)
        if mark not in results:
            return match.group(0)
        return keep(f'<button type="button" class="cite cite-result" data-result="{mark}" '
                    f'aria-label="Resultado da pesquisa {mark}">{mark}</button>')

    text = _RESULT.sub(result, text)
    rendered = _MARKDOWN.render(text)
    return re.sub(r"ALIADOPH(\d+)X", lambda match: protected[int(match.group(1))], rendered)
