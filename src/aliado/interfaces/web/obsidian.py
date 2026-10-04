"""Espelho do AL-IAdo para o Obsidian (lote 28).

Gera, numa pasta própria, notas em Markdown com `[[links]]`: uma por conversa, uma por documento da
biblioteca e uma de anotações por fonte (documento ou conversa). O sentido é um só, do AL-IAdo para o
Obsidian: as notas geradas são refeitas a cada mudança, e o que for escrito nelas é substituído. Arquivos que
o AL-IAdo não escreveu e a pasta `.obsidian/` nunca são tocados (só a configuração do grafo é criada, e
apenas quando ainda não existe).

Regras de segurança do texto:
- os campos saem por lista do que pode sair: caminhos de pasta, trechos e passagens recuperados ficam de fora;
- o texto das respostas é limpo do que o Obsidian executaria ou buscaria na rede (HTML cru, imagens, links
  que não são http, blocos de linguagens que ele executa) e do que viraria link entre notas, etiqueta ou
  comentário por acidente;
- o resultado é conferido por um analisador de Markdown, que também procura as marcas próprias do Obsidian
  no que ele lê como texto: se sobrar algo vivo, o texto sai numa forma sem nenhuma marcação interpretada
  (código e fórmulas inclusive).
"""

from __future__ import annotations

import ctypes
import json
import os
import re
import sqlite3
import sys
import threading
import time
import unicodedata
import uuid
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import datetime, timezone, tzinfo
from pathlib import Path, PurePosixPath, PureWindowsPath

from markdown_it import MarkdownIt

from aliado.interfaces.web.rendering import _CITATION, _RESULT, _WEB

FOLDERS = ("Conversas", "Documentos", "Anotações")
ABOUT = "Sobre esta pasta"
OTHERS = "Outras anotações"
MANIFEST = ".aliado-exportacao.json"
FAILURE = "Aviso: a pasta do Obsidian não foi atualizada agora; ela será atualizada na próxima resposta."
UNSAFE_TEXT = "*(Este texto não pôde ser levado para a nota com segurança; ele continua no AL-IAdo.)*"

# Os mesmos rótulos da aba Memória (app.js).
KIND_SECTIONS = (("perfil", "Perfil"), ("preferencia", "Preferências"), ("decisao", "Decisões"),
                 ("correcao", "Correções"), ("fato", "Fatos"))
ORIGIN_LABELS = {"feedback": "sua", "comando": "sua", "inferido": "inferida"}
OLD_STATUS = {"superada": "superada", "revogada": "revogada"}
DOCUMENT_STATUS = {"ready": "lido por inteiro", "partial": "lido em parte"}
BLOCKED = {"invalid_citations", "invalid_result_refs"}
# Linguagens de bloco de código que só mudam as cores. Qualquer outra (query, mermaid, dataview…) pode ser
# executada pelo Obsidian ou por um plugin, e o bloco vai como texto.
PLAIN_LANGUAGES = {
    "python", "py", "json", "yaml", "yml", "bash", "sh", "shell", "powershell", "ps1", "text", "txt", "plaintext",
    "sql", "javascript", "js", "typescript", "ts", "c", "cpp", "c++", "csharp", "cs", "java", "matlab", "octave",
    "latex", "tex", "r", "julia", "csv", "ini", "toml", "xml", "html", "css", "diff", "markdown", "md", "rust", "go",
    "fortran", "vhdl", "verilog"}
# Cores do grafo por pasta, criadas só quando o cofre ainda não tem configuração do grafo.
GRAPH = {
    "collapse-filter": False, "search": "", "showTags": False, "showAttachments": False, "hideUnresolved": True,
    "showOrphans": True, "collapse-color-groups": False,
    "colorGroups": [{"query": "path:Conversas", "color": {"a": 1, "rgb": 0x4C78A8}},
                    {"query": "path:Documentos", "color": {"a": 1, "rgb": 0x54A24B}},
                    {"query": "path:Anotações", "color": {"a": 1, "rgb": 0xF58518}}],
    "collapse-display": False, "showArrow": True, "textFadeMultiplier": 0, "nodeSizeMultiplier": 1,
    "lineSizeMultiplier": 1, "collapse-forces": True, "centerStrength": 0.5, "repelStrength": 10,
    "linkStrength": 1, "linkDistance": 250, "scale": 1, "close": False,
}

# Delimitam os pedaços já prontos (código, fórmulas e links gerados) enquanto o resto do texto é limpo.
_OPEN, _CLOSE = chr(0xE000), chr(0xE001)
_PLACEHOLDER = re.compile(f"{_OPEN}(\\d+){_CLOSE}")
_INVISIBLE = chr(0x200B)  # espaço de largura zero
# Proibidos no Windows ou com sentido num link do Obsidian (a crase abriria um trecho de código no meio dele).
_FORBIDDEN = re.compile(r'[\x00-\x1f\x7f\[\]#^|\\/:*?"<>`' + _OPEN + _CLOSE + "]")
_RESERVED = {"CON", "PRN", "AUX", "NUL", *(f"COM{n}" for n in range(1, 10)), *(f"LPT{n}" for n in range(1, 10))}
_INLINE_CODE = re.compile(r"(?<![`\\])(`+)(?!`)([^\n]{0,2000}?)(?<!`)\1(?!`)")
# Fórmulas, com tamanho limitado: $$…$$ e \[…\] sem linha em branco no meio; \(…\) e $…$ numa linha só.
_MATH = re.compile(r"(?<!\\)\$\$(?:(?!\n[ \t]*\n)[^$]){1,4000}?\$\$|(?<!\\)\\\[(?:(?!\n[ \t]*\n)[^$]){1,4000}?\\\]"
                   r"|(?<!\\)\\\([^\n$]{1,2000}?\\\)"
                   r"|(?<![\\\w$])\$(?=\S)[^\n$]{1,2000}?(?<=\S)(?<!\\)\$(?![\d$])", re.DOTALL)
_TAG_START = r"(?=[A-Za-z/!?%])"  # "<%" é o comando de um plugin de modelos
# HTML cru; ficam os links automáticos <https://…> e <mailto:…> e as marcas de texto sem atributos (br, sub, sup).
_HTML = re.compile(r"<(?!(?:https?://|mailto:)[^\s<>]*>)(?!/?(?:br|sub|sup)\s*/?>)" + _TAG_START, re.IGNORECASE)
_PLAIN_TAG = re.compile(r"</?(?:br|sub|sup)\s*/?>", re.IGNORECASE)
_ANY_TAG = re.compile(r"<" + _TAG_START)
_DOLLAR = re.compile(r"(?<!\\)((?:\\\\)*)\$")  # um cifrão que ainda não está escapado
# Etiqueta: "#" seguido de texto, menos no meio de uma palavra, de um endereço ou de um código como "&#60;".
_ANY_HASH = r"(?<![^\W_])(?<![/#&])#(?=[^\s#])"
_TAG = re.compile(r"(?<!\\)" + _ANY_HASH)  # o que já veio escapado fica como está
_STRICT_TAG = re.compile(_ANY_HASH)
# Começo de uma linha dentro de citações e itens de lista; depois dele vêm o título ou a definição de link.
_MARKER = re.compile(r"(?:>|[-*+](?=[ \t])|\d{1,9}[.)](?=[ \t]))[ \t]*")
_ATX = re.compile(r"#{1,6}(?=\s)")
_RULE = re.compile(r"(?:=+|-+)[ \t]*")  # a linha que faria da anterior um título
_SAFE_LINK = re.compile(r"(?:https?://|mailto:)", re.IGNORECASE)
# Link cujo destino não é http(s) nem e-mail (obsidian://, file://, outra nota, caminho): vira texto.
_OTHER_LINK = re.compile(r"\]\((?!\s*<?(?:https?://|mailto:))", re.IGNORECASE)
# Definição de link por referência cujo destino não é http(s) nem e-mail.
_DEFINED = re.compile(r"\[[^\]\n]{0,1000}\]:(?![ \t]*<?(?:https?://|mailto:))", re.IGNORECASE)
# O que só o Obsidian interpreta: link e incorporação de nota, comentário e etiqueta.
_OBSIDIAN = re.compile(r"\[\[|%%|" + _ANY_HASH)
_HTTP = re.compile(r"https?://[^\s<>]+")
_DOI = re.compile(r"10\.\d{4,9}/[-._;()/:A-Za-z0-9]+")
_OURS = re.compile(r'\A---\ntipo: "(?:conversa|documento|anotações)"\n')
_TEMPORARY = re.compile(r"\.~[0-9a-f]{32}\.tmp")
_SENTINEL, _MARK = "ALIADOFIMDOTEXTO", "ALIADOMARCA"
# Com HTML ligado, aceitando qualquer destino de link e sem juntar o texto escapado ao resto: tudo o que
# poderia estar vivo vira um pedaço que a conferência consegue julgar.
_PARSER = MarkdownIt("commonmark").enable(["table", "strikethrough"]).disable("text_join")
_PARSER.validateLink = lambda url: True


@dataclass(frozen=True)
class Note:
    text: str
    created: datetime | None  # vira a data de criação do arquivo: a linha do tempo do grafo usa essa data


def note_name(text: object, fallback: str, limit: int = 100) -> str:
    """Nome de nota válido no Windows e num `[[link]]`; sem ponto ou espaço no fim."""
    def clean(value: object) -> str:
        name = " ".join(_FORBIDDEN.sub(" ", unicodedata.normalize("NFC", str(value or ""))).split()).lstrip(". ")
        name = re.sub(r"%{2,}", "%", name)  # "%%" abriria um comentário no título da nota
        if len(name) > limit:
            cut = name[:limit]
            name = cut[:cut.rfind(" ")] if cut.rfind(" ") >= limit // 2 else cut
        return name.rstrip(". ")

    name = clean(text) or clean(fallback) or "Nota"
    if name.split(".")[0].strip().upper() in _RESERVED:
        name += " (nota)"
    return name


def _key(name: str) -> str:
    return unicodedata.normalize("NFC", name).casefold()


class _Names:
    """Nomes únicos no cofre inteiro, sem diferenciar maiúsculas: o Obsidian resolve o link pelo nome."""

    def __init__(self):
        self._taken: set[str] = set()

    def take(self, name: str) -> str:
        candidate, number = name, 1
        while _key(candidate) in self._taken:
            number += 1
            candidate = f"{name} ({number})"
        self._taken.add(_key(candidate))
        return candidate


def _clean(text: object) -> str:
    return str(text or "").replace(_OPEN, "").replace(_CLOSE, "")


def _word(value: object) -> str:
    """Um campo que deveria ser texto; qualquer outra coisa vale como vazio."""
    return value if isinstance(value, str) else ""


def _inert(text: str) -> str:
    """Nenhuma marcação sobrevive: nem HTML, nem link, nem imagem, nem código, nem fórmula."""
    text = text.replace("\\", "\\\\").replace("<", "&lt;")  # a barra já escrita não pode desfazer as de baixo
    text = re.sub(r"([\[\]`~$|])", r"\\\1", text).replace("%%", "\\%\\%")
    return _STRICT_TAG.sub("\\#", text)


def _plain(text: object) -> str:
    """Texto de uma linha (título, referência, anotação), sem nada que o Obsidian interprete."""
    # No começo da linha, "# x" seria um título e "> x" uma citação.
    return re.sub(r"^(#+(?=\s|$)|>)", r"\\\1", _inert(" ".join(_clean(text).split())))


def _lines(text: str, *, definitions: bool) -> str:
    """O que depende do começo da linha, numa passada só: os títulos descem dois níveis, para ficar abaixo de
    "### Resposta"; a linha de = ou - que faria um título da anterior ganha uma linha em branco antes; e a
    definição de link por referência vira texto."""
    ready: list[str] = []
    blank = True
    for line in text.split("\n"):
        at = len(line) - len(line.lstrip(" \t"))
        marked = at
        while (marker := _MARKER.match(line, marked)) is not None:
            marked = marker.end()
        if at <= 3 or marked > at:  # com mais recuo e sem citação nem lista, é código recuado
            rest = line[marked:]
            heading = _ATX.match(rest)
            if heading:
                line = line[:marked] + "#" * min(6, len(heading.group(0)) + 2) + rest[heading.end():]
            elif definitions and _DEFINED.match(rest):
                line = line[:marked] + "\\" + rest
            elif definitions and _PLAIN_TAG.fullmatch(rest.strip()):
                # Sozinha na linha, até uma marca simples abriria um bloco de HTML, onde nada mais é interpretado.
                line = line[:marked] + rest.replace("<", "&lt;", 1)
            elif not blank and rest and _RULE.fullmatch(rest):
                ready.append("")
        ready.append(line)
        blank = not line[marked:].strip()
    return "\n".join(ready)


def _escape(text: str) -> str:
    """Limpa um trecho de prosa, fora de código e de fórmulas."""
    # Primeiro o "[[", depois o "![": imagem e incorporação viram texto, e nenhum dos dois reaparece.
    text = text.replace("[[", "\\[\\[").replace("![", "!\\[")
    text = _DOLLAR.sub(r"\1\\$", text).replace("%%", "\\%\\%")
    text = _OTHER_LINK.sub("]\\(", _HTML.sub("&lt;", text))
    return _lines(_TAG.sub("\\#", text), definitions=True)


def _math(fragment: str) -> str | None:
    """A fórmula pronta, ou None se o trecho não deve ser tratado como fórmula."""
    if fragment.startswith(("\\(", "\\[")):
        inside = fragment[2:-2]
        if not inside.strip():
            return None  # "\( \)" viraria um "$$" solto, que engoliria o texto seguinte
        # O Obsidian só desenha fórmulas com cifrões.
        fragment = f"${inside.strip()}$" if fragment.startswith("\\(") else f"$${inside}$$"
    # Se o Obsidian não ler este trecho como fórmula, nada nele pode virar HTML, imagem, link, definição de
    # link, comentário ou etiqueta: um espaço separa cada par, e a conta continua a mesma.
    fragment = _ANY_TAG.sub("< ", fragment).replace("![", "! [").replace("](", "] (").replace("]:", "] :")
    fragment = re.sub(r"\[(?=\[)", "[ ", re.sub(r"%(?=%)", "% ", fragment))
    return _TAG.sub("\\#", fragment)


def _language(info: str) -> str:
    return (info.split() or [""])[0].lower()


def _live(text: str) -> bool:
    """O texto pronto, lido como Markdown: sobrou HTML, imagem, link que não é http, marca própria do Obsidian
    em texto corrido, bloco de código numa linguagem que ele executa, consulta de plugin em código na linha,
    comando de plugin de modelos, ou um bloco aberto no fim?"""
    if "<%" in text:
        return True
    tokens = _PARSER.parse(f"{text}\n\n{_SENTINEL}\n")
    for token in tokens:
        if token.type == "fence" and _language(token.info) not in PLAIN_LANGUAGES | {""}:
            return True
        if token.type == "html_block":
            return True  # num bloco de HTML nada mais é interpretado, nem os links gerados
        for child in token.children or ():
            if child.type == "image" or (child.type == "html_inline" and not _PLAIN_TAG.fullmatch(child.content)):
                return True
            if child.type == "link_open" and not _SAFE_LINK.match(str(child.attrGet("href") or "")):
                return True
            if child.type == "code_inline" and child.content.lstrip().startswith(("=", "$=")):
                return True
            if child.type == "text" and _OBSIDIAN.search(child.content):
                return True
    # O que vier depois do texto tem de começar um parágrafo novo, fora de qualquer bloco.
    return not (len(tokens) >= 3 and tokens[-3].type == "paragraph_open" and tokens[-3].level == 0
                and tokens[-2].content == _SENTINEL)


def _restore(text: str, kept: list[tuple[str, str]], *, check: bool = False) -> str:
    """Devolve os pedaços guardados. Na versão da conferência, só o link gerado vira uma palavra (ele é seguro
    por construção, e "[[nota]]" é justamente o que a conferência procura); o resto é o texto que vai à nota."""
    def piece(match: re.Match) -> str:
        index = int(match.group(1))
        if index >= len(kept):
            return ""
        kind, fragment = kept[index]
        return _MARK if check and kind == "marca" else fragment

    for _ in range(4):  # uma fórmula pode guardar um pedaço de código já protegido
        if not _PLACEHOLDER.search(text):
            break
        text = _PLACEHOLDER.sub(piece, text)
    return text


def _fences(text: str) -> str:
    """Nos blocos de código cercados do texto pronto, a linguagem só fica se for uma das que apenas mudam as
    cores, e o comando de plugin de modelos é desfeito por um caractere invisível."""
    lines = text.split("\n")
    for token in _PARSER.parse(text):
        if token.type != "fence" or not token.map:
            continue
        start, end = token.map
        first = lines[start]
        at = first.find(token.markup)
        language = _language(token.info)
        if at >= 0 and language:
            lines[start] = first[:at] + token.markup + (language if language in PLAIN_LANGUAGES else "text")
        for index in range(start + 1, min(end, len(lines))):
            lines[index] = lines[index].replace("<%", f"<{_INVISIBLE}%")
    return "\n".join(lines)


def _closed(text: str) -> str:
    """Um bloco de código sem fim é fechado, para o resto da nota não virar código."""
    last = next((token for token in reversed(_PARSER.parse(text)) if token.level == 0), None)
    if last is None or last.type != "fence" or not last.map:
        return ""
    bare = text.split("\n")[last.map[1] - 1].strip()
    closed = (last.map[1] - last.map[0] > 1 and bare and set(bare) == {last.markup[0]}
              and len(bare) >= len(last.markup))
    return "" if closed else "\n" + last.markup


def _render(text: str, mark: Callable[[str, str], str | None] | None, *, strict: bool) -> tuple[str, str]:
    """O texto pronto e a versão dele que a conferência lê (a mesma, com os links gerados trocados por uma
    palavra)."""
    kept: list[tuple[str, str]] = []

    def keep(kind: str, fragment: str) -> str:
        kept.append((kind, fragment))
        return f"{_OPEN}{len(kept) - 1}{_CLOSE}"

    def marks(piece: str) -> str:
        def swap(kind: str, match: re.Match) -> str:
            ready = mark(kind, match.group(1))
            if ready is None:
                return match.group(0)
            # A marca vinha colada ao texto ou a outra marca; o link por extenso pede um espaço antes.
            glued = match.start() > 0 and match.string[match.start() - 1] not in " \t\n(["
            return (" " if glued else "") + keep("marca", _clean(ready))

        if mark is not None:
            for pattern, kind in ((_CITATION, "K"), (_WEB, "W"), (_RESULT, "R")):
                piece = pattern.sub(lambda match, kind=kind: swap(kind, match), piece)
        return piece

    if strict:
        ready = _lines(_inert(marks(text)), definitions=False)
        return _restore(ready, kept), _restore(ready, kept, check=True)

    def code(match: re.Match) -> str:
        ticks, inside = match.group(1), match.group(2).replace("<%", f"<{_INVISIBLE}%")
        # "`= …`" e "`$= …`" são consultas de um plugin comum: um caractere invisível desfaz o prefixo.
        return keep("codigo", f"{ticks}{_INVISIBLE if inside.lstrip().startswith(('=', '$=')) else ''}{inside}{ticks}")

    def formula(match: re.Match) -> str:
        ready = _math(match.group(0))
        return match.group(0) if ready is None else keep("formula", ready)

    def prose(piece: str) -> str:
        return _escape(marks(_MATH.sub(formula, _INLINE_CODE.sub(code, piece))))

    # Os blocos de código cercados, onde quer que estejam (também em listas e citações), ficam como vieram.
    lines = text.split("\n")
    parts: list[str] = []
    cursor = 0
    for token in _PARSER.parse(text):
        if token.type != "fence" or not token.map or token.map[0] < cursor:
            continue
        start, end = token.map
        if start > cursor:
            parts.append(prose("\n".join(lines[cursor:start])))
        parts.append("\n".join(lines[start:end]))
        cursor = end
    if cursor < len(lines):
        parts.append(prose("\n".join(lines[cursor:])))
    result = "\n".join(parts)
    # As duas versões passam pelos mesmos acertos, decididos sobre o texto que a conferência lê.
    ready, check = _fences(_restore(result, kept)), _fences(_restore(result, kept, check=True))
    closing = _closed(check)
    return ready.rstrip("\n") + closing if closing else ready, check.rstrip("\n") + closing if closing else check


def obsidian_text(text: object, mark: Callable[[str, str], str | None] | None = None) -> str:
    """Texto de pergunta ou resposta pronto para uma nota.

    Código e fórmulas ficam como estão. `mark(tipo, valor)` troca as marcas `[K…]`, `[Wn]` e `[Rn]` pelo
    texto pronto, ou devolve None para deixar a marca como veio. O resultado é conferido: se ainda houver
    algo que o Obsidian executaria, buscaria ou ligaria por conta própria, o texto sai sem nenhuma marcação
    interpretada.
    """
    text = _clean(text).replace("\r\n", "\n").replace("\r", "\n")
    for strict in (False, True):
        ready, check = _render(text, mark, strict=strict)
        if not _live(check.strip("\n")):
            return ready.strip("\n")
    return UNSAFE_TEXT


def _moment(value: object, tz: tzinfo | None) -> datetime | None:
    try:
        moment = datetime.fromisoformat(str(value))
        if moment.tzinfo is None:
            moment = moment.replace(tzinfo=timezone.utc)
        return moment.astimezone(tz)
    except (ValueError, OverflowError, OSError):  # data ilegível ou fora do que o sistema representa
        return None


def _day(moment: datetime | None) -> str:
    return moment.strftime("%d/%m/%Y") if moment else "data não registrada"


def _front(pairs: list[tuple[str, object]]) -> str:
    """Propriedades da nota; os textos saem como JSON, que também é YAML válido."""
    def inert(value: object) -> object:
        # Numa propriedade, "[[x]]" seria um link entre notas e "<%" um comando de plugin de modelos.
        if isinstance(value, list):
            return [inert(item) for item in value]
        return _clean(value).replace("[[", "[ [").replace("]]", "] ]").replace("<%", "< %")

    lines = ["---"]
    for key, value in pairs:
        if value is None:
            continue
        if isinstance(value, datetime):
            written = value.strftime("%Y-%m-%dT%H:%M")
        elif isinstance(value, int):
            written = str(value)
        else:
            written = json.dumps(inert(value), ensure_ascii=False)
        lines.append(f"{key}: {written}")
    return "\n".join([*lines, "---"])


def _web_link(source: dict) -> str:
    title = _plain(source.get("title") or source.get("domain") or "fonte na web")
    uri = str(source.get("uri") or source.get("url") or "")
    if not _HTTP.fullmatch(uri) or _OPEN in uri or _CLOSE in uri:
        return title
    return f"[{title}](<{uri.replace('|', '%7C')}>)"  # a barra vertical quebraria a linha de uma tabela


def _about() -> str:
    return "\n".join([
        f"# {ABOUT}", "",
        "Esta pasta é um espelho do AL-IAdo para o Obsidian. Ela existe para você ver, no grafo, como as "
        "conversas, os documentos da biblioteca e as anotações da memória se ligam e crescem.", "",
        "## O que há aqui", "",
        "- **Conversas:** uma nota por conversa, com as perguntas e as respostas. Cada documento citado numa "
        "resposta vira um link para a nota dele.",
        "- **Documentos:** uma nota por documento da biblioteca, com a ficha (título, autores, ano e DOI).",
        "- **Anotações:** as anotações da memória, agrupadas pela fonte: uma nota para cada documento e uma "
        "para cada conversa de onde saíram anotações.", "",
        "No grafo, as conversas aparecem em azul, os documentos em verde e as anotações em laranja. Essas "
        "cores são criadas só na primeira vez; se você mudar as cores do grafo, as suas ficam.", "",
        "## Como a pasta é atualizada", "",
        "- O AL-IAdo refaz estas notas sozinho depois de cada resposta e sempre que a biblioteca ou a memória "
        "mudam.",
        "- O caminho é um só, do AL-IAdo para o Obsidian: o que você escrever numa nota gerada é substituído "
        "na próxima atualização, e nada do que você fizer aqui muda o AL-IAdo.",
        "- Notas suas, criadas por você nesta pasta, não são tocadas. Para não se misturarem, crie-as fora das "
        "pastas Conversas, Documentos e Anotações.",
        "- Uma conversa ou um documento apagado no AL-IAdo sai daqui também.", "",
        "## Como o texto das respostas aparece", "",
        "- Blocos de código só mantêm a linguagem quando ela serve apenas para colorir; os de diagramas e de "
        "consultas aparecem como texto, sem serem desenhados nem executados.",
        "- Imagens e links que não levam a um site (http) aparecem como texto.",
        "- Se uma resposta trouxer algo que o Obsidian executaria ou buscaria por conta própria, ela aparece "
        "inteira como texto simples, sem negrito, fórmulas desenhadas ou links.", "",
        "## Linha do tempo", "",
        "No grafo, o botão de animação mostra as notas na ordem em que surgiram. O AL-IAdo grava em cada "
        "arquivo a data do registro (o começo da conversa, a chegada do documento, a primeira anotação), para a "
        "animação mostrar o crescimento real.", "",
        "## O que significa cada propriedade", "",
        "- **tipo:** conversa, documento ou anotações.",
        "- **criada** e **atualizada:** quando a conversa começou e quando recebeu a última mensagem.",
        "- **perguntas:** quantas perguntas você fez na conversa.",
        "- **arquivo:** o nome do arquivo enviado à biblioteca.",
        "- **versão:** quantas vezes o mesmo arquivo foi enviado com conteúdo diferente; a nota mostra a mais "
        "recente.",
        "- **situação:** \"lido por inteiro\" quando todo o texto foi aproveitado; \"lido em parte\" quando "
        "alguma página ficou sem texto utilizável (as pendências aparecem na nota).",
        "- **adicionado:** quando o documento entrou na biblioteca.",
        "- **referência:** a forma curta de citar o documento, tirada da ficha (autor e ano).",
        "- **fonte:** de onde saíram as anotações da nota: de um documento, de uma conversa ou de outra origem.",
        "- **em vigor:** quantas anotações da nota estão valendo hoje. Não entram as que estão em conflito, as "
        "superadas e as revogadas.", "",
        "## O que significa cada marca nas anotações", "",
        "- **p. 10:** a página do documento de onde a anotação saiu.",
        "- **sua:** você disse ou corrigiu; vale desde o momento em que foi dita.",
        "- **inferida:** o AL-IAdo deduziu de um documento ou de uma conversa; confira antes de se apoiar nela.",
        "- **em conflito:** uma anotação inferida que contradiz uma sua. A sua continua valendo até você "
        "decidir, na aba Memória.",
        "- **diverge da skill:** uma decisão sua diferente do que a especialização em uso recomenda.",
        "- **superada:** foi trocada por uma versão mais nova.",
        "- **revogada:** foi retirada, por você ou porque o documento saiu da biblioteca; fica só como "
        "histórico.", "",
    ])


def _source(memory: dict) -> dict:
    return memory.get("source") if isinstance(memory.get("source"), dict) else {}


def _memory_line(memory: dict, talk_names: dict[str, str], *, link_talk: bool, gone_document: bool) -> str:
    source = _source(memory)
    details = []
    if source.get("page") is not None:
        details.append(f"p. {_plain(source['page'])}")
    elif source.get("locator"):
        details.append(_plain(source["locator"]))
    if _word(memory.get("origin")) in ORIGIN_LABELS:
        details.append(ORIGIN_LABELS[memory["origin"]])
    if memory.get("status") == "conflito":
        details.append("em conflito")
    if memory.get("diverges_skill"):
        details.append("diverge da skill")
    if source.get("url"):
        details.append(_web_link({"title": source.get("title"), "uri": source.get("url")}))
    if link_talk and str(source.get("conversation_id") or "") in talk_names:
        details.append(f"da conversa [[{talk_names[str(source['conversation_id'])]}]]")
    if gone_document:
        details.append("de um documento que saiu da biblioteca")
    return f"{_plain(memory.get('text'))} — {' · '.join(details)}" if details else _plain(memory.get("text"))


def _group_note(heading: str, source_kind: str, source_line: str, memories: list[dict], *, title: str | None,
                talk_names: dict[str, str], gone: set[str], tz: tzinfo | None) -> Note:
    def order(memory: dict):
        page = _source(memory).get("page")
        return (page is None, page if isinstance(page, int) else 0, str(memory.get("created_at") or ""),
                str(memory.get("id") or ""))

    def summary(memory: dict) -> str | None:
        source, text = _source(memory), str(memory.get("text") or "")
        if not (source.get("ficha") and source.get("page") is None and text.startswith("Resumo de ")):
            return None
        prefix = f"Resumo de {title}: "
        return text[len(prefix):] if title and text.startswith(prefix) else text.partition(": ")[2] or text

    active = sorted((m for m in memories if _word(m.get("status")) not in OLD_STATUS), key=order)
    old = sorted((m for m in memories if _word(m.get("status")) in OLD_STATUS), key=order)
    link_talk = source_kind != "conversa"
    lines = [_front([("tipo", "anotações"), ("fonte", source_kind),
                     ("em vigor", sum(1 for m in active if m.get("status") == "ativa"))]),
             f"# {_plain(heading)}", "", source_line, ""]
    summaries = [text for text in map(summary, active) if text]
    if summaries:
        lines += ["## Resumo", "", *(f"{_plain(text)}\n" for text in summaries)]
    rest = [m for m in active if summary(m) is None]
    known = {kind for kind, _ in KIND_SECTIONS}
    for kind, label in (*KIND_SECTIONS, (None, "Outras")):
        chosen = [m for m in rest if (m.get("kind") == kind if kind else _word(m.get("kind")) not in known)]
        if chosen:
            lines += [f"## {label}", "", *(
                "- " + _memory_line(m, talk_names, link_talk=link_talk, gone_document=str(m.get("id")) in gone)
                for m in chosen), ""]
    if old:
        lines += ["> [!note]- Anotações antigas", *(
            f"> - ({OLD_STATUS[m['status']]}) "
            + _memory_line(m, talk_names, link_talk=link_talk, gone_document=str(m.get("id")) in gone)
            for m in old), ""]
    moments = [moment for moment in (_moment(m.get("created_at"), tz) for m in memories) if moment]
    return Note("\n".join(lines).rstrip("\n") + "\n", min(moments) if moments else None)


def _document_note(entry: dict, group: str | None, tz: tzinfo | None) -> Note:
    latest = entry["latest"]
    card = latest.get("ficha") if isinstance(latest.get("ficha"), dict) else {}
    reference = latest.get("referencia")
    added = _moment(entry["first"], tz)
    aliases = [entry["title"]]
    if reference and str(reference) != entry["name"]:
        aliases.append(str(reference))
    version = latest.get("version")
    lines = [_front([("tipo", "documento"), ("arquivo", entry["title"]),
                     ("versão", version if isinstance(version, int) else None),
                     ("situação", DOCUMENT_STATUS.get(_word(latest.get("status")))), ("adicionado", added),
                     ("referência", str(reference) if reference else None), ("aliases", aliases)]),
             f"# {_plain(card.get('titulo') or entry['title'])}", "", "## Ficha do documento", ""]
    if card:
        authors = card.get("autores") if isinstance(card.get("autores"), list) else []
        doi = _clean(card.get("doi"))
        lines += [f"- **Autores:** {_plain('; '.join(str(author) for author in authors)) or '—'}",
                  f"- **Ano:** {_plain(card.get('ano')) or '—'}",
                  "- **DOI:** " + (f"[{_plain(doi)}](<https://doi.org/{doi}>)" if _DOI.fullmatch(doi)
                                   else _plain(doi) or "—"),
                  "- **Ficha:** " + ("sua (editada por você)" if latest.get("ficha_origem") == "sua"
                                     else "inferida — confira no original")]
    else:
        lines.append("Este documento ainda não tem ficha.")
    issues = latest.get("issues") if isinstance(latest.get("issues"), list) else []
    if any(issues):
        lines += ["", "## Pendências da leitura", "", *(f"- {_plain(issue)}" for issue in issues if issue)]
    if len(entry["versions"]) > 1:
        lines += ["", "## Versões", ""]
        for item in entry["versions"]:
            unread = " (não pôde ser lida)" if item.get("status") == "failed" else ""
            lines.append(f"- versão {_plain(item.get('version'))}, adicionada em "
                         f"{_day(_moment(item.get('created_at'), tz))}{unread}")
    if group:
        lines += ["", f"Anotações tiradas deste documento: [[{group}]]"]
    return Note("\n".join(lines) + "\n", added)


def _talk_note(talk: dict, documents: dict[str, dict], memory_notes: dict[str, str], talk_names: dict[str, str],
               tz: tzinfo | None) -> Note:
    created, updated = _moment(talk.get("created_at"), tz), _moment(talk.get("updated_at"), tz)
    messages = talk["messages"]
    lines = [_front([("tipo", "conversa"), ("criada", created), ("atualizada", updated),
                     ("perguntas", sum(1 for message in messages if message["role"] == "user"))]),
             f"# {_plain(talk.get('title') or 'Conversa')}", ""]
    question = 0
    for message in messages:
        content = _word(message.get("content"))
        if message["role"] == "user":
            question += 1
            sent = _moment(message.get("created_at"), tz)
            lines += [f"## Pergunta {question}", ""]
            if sent:
                lines += [f"*{sent.strftime('%d/%m/%Y %H:%M')}*", ""]
            lines += [obsidian_text(content), ""]
            continue
        lines += ["### Resposta", "", obsidian_text(content, _marker(message, documents)), ""]
        notices = _notices(message)
        if notices:
            lines += [f"*{' '.join(notices)}*", ""]
        extras = _extras(message, documents, memory_notes, talk_names)
        if extras:
            lines += ["> [!info]- Fontes e memória", *(f"> {line}" for line in extras), ""]
    return Note("\n".join(lines).rstrip("\n") + "\n", created)


def _items(message: dict, key: str) -> list[dict]:
    value = message.get(key)
    return [item for item in value if isinstance(item, dict)] if isinstance(value, list) else []


def _cited(source: dict, documents: dict[str, dict], *, locator: bool = True) -> str:
    entry = documents.get(str(source.get("document_id")))
    where = f" ({_plain(source['locator'])})" if locator and source.get("locator") else ""
    if entry:
        return f"[[{entry['name']}]]{where}"
    return _plain(source.get("referencia") or source.get("title") or "documento") + where


def _marker(message: dict, documents: dict[str, dict]) -> Callable[[str, str], str | None]:
    sources = {str(source.get("citation_id")): source for source in _items(message, "sources")}
    results = {str(block.get("citation_id")): block for block in _items(message, "result_sources")}
    web = message.get("web_sources") if isinstance(message.get("web_sources"), list) else []

    def mark(kind: str, value: str) -> str | None:
        if kind == "K":
            return _cited(sources[value], documents) if value in sources else None
        if kind == "W":
            number = int(value) if len(value) <= 6 else 0  # um número absurdo não é uma fonte
            if not 1 <= number <= len(web) or not isinstance(web[number - 1], dict):
                return None
            return _web_link(web[number - 1])
        block = results.get(value)
        return f"(resultado da pesquisa: {_plain(block.get('titulo') or value)})" if block else None

    return mark


def _notices(message: dict) -> list[str]:
    notices = []
    status = _word(message.get("validation_status"))
    if status in BLOCKED:
        notices.append("Resposta barrada pela conferência das citações: o texto acima é o aviso que apareceu no "
                       "lugar dela.")
    elif message.get("provider") == "local" or status == "insufficient_evidence":
        notices.append("Aviso do próprio AL-IAdo, sem resposta do modelo.")
    if message.get("cortada"):
        notices.append("Resposta cortada pelo limite de tamanho.")
    if message.get("results_status") == "numeros_nao_conferidos":
        notices.append("Há números que não conferem com os resultados citados.")
    if message.get("in_context") is False:
        notices.append("Ficou fora do histórico da conversa.")
    return notices


def _grouped(ids: list[str], memory_notes: dict[str, str]) -> str:
    counts: dict[str, int] = {}
    missing = 0
    for memory_id in ids:
        if memory_id in memory_notes:
            counts[memory_notes[memory_id]] = counts.get(memory_notes[memory_id], 0) + 1
        else:
            missing += 1
    pieces = [f"[[{name}]] ({count})" for name, count in counts.items()]
    if missing:
        pieces.append(f"{missing} de um documento que saiu da biblioteca")
    return "; ".join(pieces)


def _extras(message: dict, documents: dict[str, dict], memory_notes: dict[str, str],
            talk_names: dict[str, str]) -> list[str]:
    lines = []
    cited: dict[str, list[str]] = {}
    for source in _items(message, "sources"):
        places = cited.setdefault(_cited(source, documents, locator=False), [])
        place = _plain(source.get("locator") or "")
        if place and place not in places:
            places.append(place)
    if cited:
        lines.append("**Documentos citados:** " + "; ".join(
            label + (f" ({', '.join(places)})" if places else "") for label, places in cited.items()))
    web = [_web_link(source) for source in _items(message, "web_sources")]
    if web:
        lines.append("**Fontes da web:** " + "; ".join(dict.fromkeys(web)))
    results = [_plain(block.get("titulo") or block.get("citation_id")) for block in _items(message, "result_sources")]
    if results:
        lines.append("**Resultados da pesquisa:** " + "; ".join(dict.fromkeys(results)))
    for key, label in (("memorias_usadas", "Anotações usadas"), ("memorias_criadas", "Anotações criadas")):
        grouped = _grouped([str(item.get("id")) for item in _items(message, key)], memory_notes)
        if grouped:
            lines.append(f"**{label}:** {grouped}")
    recalled = list(dict.fromkeys(str(item.get("conversation_id")) for item in _items(message, "conversas_lembradas")))
    if recalled:
        known = [f"[[{talk_names[cid]}]]" for cid in recalled if cid in talk_names]
        gone = len(recalled) - len(known)
        if gone:
            known.append("uma conversa apagada" if gone == 1 else f"{gone} conversas apagadas")
        lines.append("**Conversas lembradas:** " + "; ".join(known))
    return lines


def build_notes(conversations: list[dict], documents: list[dict], memories: list[dict], *,
                tz: tzinfo | None = None) -> dict[str, Note]:
    """As notas do cofre, por caminho relativo. O resultado só depende das entradas: sem data de exportação,
    uma segunda rodada com os mesmos dados não grava nada. `tz` é o fuso das datas (padrão: o do computador)."""
    names = _Names()
    names.take(ABOUT)
    notes: dict[str, Note] = {f"{ABOUT}.md": Note(_about(), None)}

    # Documentos: um por título, na versão mais recente que pôde ser lida.
    by_title: dict[str, list[dict]] = {}
    for document in documents:
        if isinstance(document, dict) and document.get("title"):
            by_title.setdefault(str(document["title"]), []).append(document)
    library: list[dict] = []
    document_of: dict[str, dict] = {}  # id de qualquer versão -> documento
    for title, versions in by_title.items():
        versions = sorted(versions, key=lambda item: (
            item.get("version") if isinstance(item.get("version"), int) else 0, str(item.get("id") or "")))
        readable = [item for item in versions if item.get("status") != "failed"]
        if not readable:
            continue
        entry = {"title": title, "latest": readable[-1], "versions": versions,
                 "first": min(str(item.get("created_at") or "") for item in versions)}
        library.append(entry)
        document_of.update({str(item.get("id")): entry for item in versions})
    library.sort(key=lambda entry: (entry["first"], entry["title"]))

    # Conversas com mensagens, da mais antiga à mais nova.
    talks = []
    for conversation in conversations:
        if not isinstance(conversation, dict):
            continue
        listed = conversation.get("messages") if isinstance(conversation.get("messages"), list) else []
        messages = [m for m in listed if isinstance(m, dict) and _word(m.get("role")) in {"user", "assistant"}]
        if messages:
            talks.append(conversation | {"messages": messages})
    talks.sort(key=lambda talk: (str(talk.get("created_at") or ""), str(talk.get("id") or "")))
    talk_ids = {str(talk.get("id")) for talk in talks}

    # Anotações por fonte: o documento, a anotação corrigida, a conversa ou "outras".
    by_id = {str(memory.get("id")): memory for memory in memories if isinstance(memory, dict)}
    gone: set[str] = set()  # em vigor, de um documento que saiu da biblioteca

    def group_of(memory: dict, seen: tuple[str, ...] = ()) -> tuple[str, str] | None:
        source = _source(memory)
        if source.get("document_id") is not None:
            entry = document_of.get(str(source["document_id"]))
            if entry:
                return ("documento", entry["title"])
            if _word(memory.get("status")) in OLD_STATUS:
                return None  # o documento saiu da biblioteca, e a anotação já não vale
            gone.add(str(memory.get("id")))
            return ("outras", "")
        seen = (*seen, str(memory.get("id")))
        corrected = str(source.get("conferida_de") or "")
        if corrected in by_id and corrected not in seen:
            # A correção fica junto do que ela corrige; se a anotação corrigida saiu do cofre, segue a regra geral.
            target = group_of(by_id[corrected], seen)
            if target is not None:
                return target
        if source.get("conversation_id"):
            return ("conversa", str(source["conversation_id"]))
        return ("outras", "")

    groups: dict[tuple[str, str], list[dict]] = {}
    for memory in sorted(by_id.values(), key=lambda m: (str(m.get("created_at") or ""), str(m.get("id") or ""))):
        key = group_of(memory)
        if key is not None:
            groups.setdefault(key, []).append(memory)

    # Nomes, sempre na mesma ordem: o que chegou antes fica com o nome; o repetido que chega depois ganha "(2)".
    for entry in library:
        stem = Path(entry["title"]).stem
        entry["name"] = names.take(note_name(entry["latest"].get("referencia") or stem, stem or "Documento"))
    group_names: dict[tuple[str, str], str] = {}
    for entry in library:
        if ("documento", entry["title"]) in groups:
            group_names[("documento", entry["title"])] = names.take(
                note_name(f"Anotações – {entry['name']}", "Anotações", limit=120))
    talk_names: dict[str, str] = {}
    for talk in talks:
        created = _moment(talk.get("created_at"), tz)
        day = created.strftime("%Y-%m-%d ") if created else ""
        talk_names[str(talk.get("id"))] = names.take(note_name(f"{day}{talk.get('title') or ''}", "Conversa"))
    lost_titles: dict[str, str] = {}
    for key in sorted((key for key in groups if key[0] == "conversa"),
                      key=lambda key: (key[1] not in talk_ids, talk_names.get(key[1], ""), key[1])):
        if key[1] in talk_ids:
            label = talk_names[key[1]]
        else:
            titles = [str(_source(m).get("conversation_title") or "") for m in groups[key]]
            label = lost_titles[key[1]] = next((title for title in titles if title.strip()), "conversa apagada")
        group_names[key] = names.take(note_name(f"Anotações – {label}", "Anotações", limit=120))
    if ("outras", "") in groups:
        group_names[("outras", "")] = names.take(OTHERS)
    memory_notes = {str(memory.get("id")): group_names[key] for key, members in groups.items() for memory in members}

    for entry in library:
        notes[f"Documentos/{entry['name']}.md"] = _document_note(
            entry, group_names.get(("documento", entry["title"])), tz)
    for talk in talks:
        notes[f"Conversas/{talk_names[str(talk.get('id'))]}.md"] = _talk_note(
            talk, document_of, memory_notes, talk_names, tz)
    for key, members in groups.items():
        name = group_names[key]
        if key[0] == "documento":
            entry = next(entry for entry in library if entry["title"] == key[1])
            line, title = f"Tiradas do documento [[{entry['name']}]].", key[1]
        elif key[0] == "conversa":
            line = (f"Criadas na conversa [[{talk_names[key[1]]}]]." if key[1] in talk_ids
                    else f"Criadas na conversa “{_plain(lost_titles[key[1]])}” (conversa apagada).")
            title = None
        else:
            line, title = "Anotações sem documento nem conversa de origem.", None
        notes[f"Anotações/{name}.md"] = _group_note(name, key[0], line, members, title=title,
                                                    talk_names=talk_names, gone=gone, tz=tz)
    return notes


def set_created(path: Path, when: datetime) -> bool:
    """Grava a data de criação do arquivo (só no Windows): a animação do grafo segue essa data."""
    if os.name != "nt":
        return False
    from ctypes import wintypes

    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.CreateFileW.argtypes = (wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD, wintypes.LPVOID,
                                   wintypes.DWORD, wintypes.DWORD, wintypes.HANDLE)
    kernel.CreateFileW.restype = wintypes.HANDLE  # sem isto, o identificador de 64 bits sairia cortado
    kernel.SetFileTime.argtypes = (wintypes.HANDLE, ctypes.POINTER(wintypes.FILETIME), ctypes.c_void_p,
                                   ctypes.c_void_p)
    kernel.SetFileTime.restype = wintypes.BOOL
    kernel.CloseHandle.argtypes = (wintypes.HANDLE,)
    ticks = int((when.timestamp() + 11_644_473_600) * 10_000_000)  # centenas de nanossegundos desde 1601
    if ticks <= 0:
        return False
    moment = wintypes.FILETIME(ticks & 0xFFFFFFFF, ticks >> 32)
    # Só os atributos, compartilhando leitura, escrita e exclusão; a data de modificação fica como está.
    handle = kernel.CreateFileW(str(path), 0x0100, 0x7, None, 3, 0x80, None)
    if handle in (None, ctypes.c_void_p(-1).value):
        return False
    try:
        return bool(kernel.SetFileTime(handle, ctypes.byref(moment), None, None))
    finally:
        kernel.CloseHandle(handle)


def _drifted(path: Path, when: datetime) -> bool:
    born = getattr(path.stat(), "st_birthtime", None)
    return born is not None and abs(born - when.timestamp()) > 2


def _replace(temporary: Path, target: Path) -> None:
    for attempt in range(1, 6):
        try:
            os.replace(temporary, target)
            return
        except PermissionError:  # o Obsidian ou o antivírus com o arquivo aberto por um instante
            if attempt == 5:
                raise
            time.sleep(0.1 * attempt)


def _atomic(target: Path, data: bytes) -> None:
    temporary = target.with_name(f".~{uuid.uuid4().hex}.tmp")  # começa com ponto: o Obsidian não o mostra
    temporary.write_bytes(data)
    try:
        _replace(temporary, target)
    except OSError:
        temporary.unlink(missing_ok=True)
        raise


def _listed(manifest: Path) -> set[str]:
    """O que o AL-IAdo escreveu aqui. Sem o registro, nada é apagado; com ele ocupado, a rodada espera."""
    try:
        data = json.loads(manifest.read_text(encoding="utf-8"))
        return {item for item in data["arquivos"] if isinstance(item, str)}
    except FileNotFoundError:
        return set()
    except (ValueError, KeyError, TypeError):
        return set()  # registro ilegível: recomeça, e só as notas com a cara das geradas voltam a ele


def _shaped(relative: str, *, about: bool) -> bool:
    """O caminho tem a forma de uma nota gerada: um nome simples numa das três pastas, ou a apresentação."""
    if about and relative == f"{ABOUT}.md":
        return True
    parts = relative.split("/")
    if len(parts) != 2 or parts[0] not in FOLDERS:
        return False
    name = parts[1]
    # No Windows, "..\\x" e "a:b" também mudam de pasta: o nome tem de ser só um nome.
    return (name.endswith(".md") and name != ".md" and name == PureWindowsPath(name).name
            and name == PurePosixPath(name).name and ":" not in name)


def _generated(target: Path, relative: str) -> bool:
    """O arquivo tem a cara de uma nota gerada? Serve para não cobrir uma nota do pesquisador com o mesmo nome."""
    with target.open("rb") as handle:
        head = handle.read(160).decode("utf-8", "ignore").replace("\r\n", "\n")
    return head.startswith(f"# {ABOUT}\n") if relative == f"{ABOUT}.md" else bool(_OURS.match(head))


def _identity(path: Path) -> tuple[int, int] | None:
    """O arquivo em si, qualquer que seja a grafia do nome pelo qual o sistema o encontra."""
    try:
        status = path.stat()
    except OSError:
        return None
    return (status.st_dev, status.st_ino)


def write_vault(root: Path, notes: dict[str, Note]) -> dict:
    """Grava as notas que mudaram e apaga as que o AL-IAdo escreveu antes e deixaram de existir.

    O registro `.aliado-exportacao.json` lista o que foi escrito aqui: nada fora dele é apagado, e um arquivo
    do pesquisador com o nome de uma nota gerada não é coberto. Quem diz se dois nomes são o mesmo arquivo é
    o sistema de arquivos. Uma nota que não puder ser lida, gravada ou apagada agora não impede as outras; a
    falha é avisada no fim, e a próxima rodada tenta de novo.
    """
    for relative in notes:
        if not _shaped(relative, about=True):
            raise ValueError("Nota fora da pasta do Obsidian.")
    root = Path(root)
    root.mkdir(parents=True, exist_ok=True)
    base = root.resolve()
    manifest = base / MANIFEST
    previous = _listed(manifest)
    failure: OSError | None = None
    # Uma pasta que aponta para outro lugar fica de fora: nada é gravado nem apagado através dela.
    folders = {name: base / name for name in FOLDERS}
    reachable = {name for name, folder in folders.items() if folder.resolve() == folder}
    if len(reachable) < len(FOLDERS):
        failure = OSError("Uma das pastas do cofre aponta para fora dele.")

    def path_of(relative: str) -> Path | None:
        if relative == f"{ABOUT}.md":
            return base / relative
        folder, name = relative.split("/")
        return folders[folder] / name if folder in reachable else None

    for folder in (base, *(folders[name] for name in reachable)):
        if folder.is_dir():
            for entry in os.scandir(folder):
                if _TEMPORARY.fullmatch(entry.name):
                    try:
                        os.unlink(entry.path)  # sobra de uma rodada interrompida
                    except OSError:
                        pass

    # Primeiro só se decide: o que gravar, o que já está igual e o que é do pesquisador.
    earlier = {relative: _identity(target) for relative in previous
               if _shaped(relative, about=True) and (target := path_of(relative)) is not None}
    spellings = {folder: set(os.listdir(folder)) if folder.is_dir() else set()
                 for folder in (base, *(folders[name] for name in reachable))}
    plan: list[tuple[str, Path, bytes, bool, bool]] = []
    # O que está numa pasta fora de alcance continua no registro, para ser cuidado quando ela voltar.
    listed: set[str] = {relative for relative in previous
                        if _shaped(relative, about=False) and relative.split("/")[0] not in reachable}
    for relative, note in sorted(notes.items()):
        target, data = path_of(relative), note.text.encode("utf-8")
        if target is None:
            continue
        try:
            found = _identity(target)
            if found is None:
                plan.append((relative, target, data, False, False))
                continue
            # Nosso se está no registro com este nome, ou com outra grafia do mesmo arquivo, ou se tem a cara
            # de uma nota gerada (o registro pode ter se perdido).
            ours = relative in previous or any(
                identity == found for other, identity in earlier.items() if _key(other) == _key(relative))
            if not ours and not _generated(target, relative):
                continue  # um arquivo seu com esse nome: fica como está e não entra no registro
            spelled = target.name in spellings[target.parent]
            if spelled and target.read_bytes() == data:
                listed.add(relative)
                if note.created and _drifted(target, note.created):
                    set_created(target, note.created)
                continue
            plan.append((relative, target, data, True, not spelled))
        except OSError as exc:
            failure = failure or exc  # as outras notas seguem; esta fica para a próxima rodada
            if relative in previous:
                listed.add(relative)
    written, unwritten = 0, set()
    for relative, target, data, existed, respell in plan:
        try:
            target.parent.mkdir(exist_ok=True)
            _atomic(target, data)  # sobre o mesmo arquivo com outra grafia, a troca já adota o nome novo
            if respell and target.name not in os.listdir(target.parent):
                mine = _identity(target)
                wrong = next((name for name in os.listdir(target.parent)
                              if _identity(target.with_name(name)) == mine), None)
                if wrong is not None:
                    os.rename(target.with_name(wrong), target)
            if notes[relative].created:
                set_created(target, notes[relative].created)
            listed.add(relative)
            written += 1
        except OSError as exc:
            failure = failure or exc
            unwritten.add(_key(relative))
            if existed:
                listed.add(relative)  # a versão anterior continua lá, e continua sendo nossa
    current = {identity for relative in listed if (target := path_of(relative)) is not None
               and (identity := _identity(target)) is not None}
    removed, stuck = 0, []
    for relative in sorted(previous - listed):
        target = path_of(relative) if _shaped(relative, about=False) else None
        if target is None or not target.is_file():
            continue
        if _identity(target) in current:
            continue  # é uma nota atual: o nome só mudou nas maiúsculas
        if _key(relative) in unwritten:
            stuck.append(relative)  # a nota com o nome novo não pôde ser gravada: a antiga fica até a próxima rodada
            continue
        try:
            target.unlink()
            removed += 1
        except OSError as exc:
            stuck.append(relative)  # fica no registro, e a próxima rodada tenta de novo
            failure = failure or exc
    settings = base / ".obsidian"
    graph = settings / "graph.json"
    if settings.resolve() == settings and not graph.exists():
        try:
            settings.mkdir(exist_ok=True)
            graph.write_text(json.dumps(GRAPH, ensure_ascii=False, indent=2), encoding="utf-8")
        except OSError:
            pass  # as cores são um acabamento: sem elas, o cofre funciona do mesmo jeito
    final = json.dumps({"versao": 1, "arquivos": sorted(listed | set(stuck))}, ensure_ascii=False, indent=1).encode("utf-8")
    if not manifest.is_file() or manifest.read_bytes() != final:
        _atomic(manifest, final)
    if failure is not None:
        raise failure
    return {"notas": len(notes), "escritas": written, "removidas": removed}


class ObsidianSync:
    """Fila própria da exportação: uma rodada por vez, sem atrasar o chat nem os envios de documentos.

    Pedidos que chegam durante uma rodada viram exatamente uma rodada a mais, que relê tudo.
    """

    RETRY = (1.0, 3.0)  # esperas, em segundos, quando um banco ou um arquivo está ocupado

    def __init__(self, export: Callable[[], dict]):
        self._export = export
        self._executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="aliado-obsidian")
        self._lock = threading.Lock()
        self._queued = False
        self._running = False
        self._idle = threading.Event()
        self._idle.set()
        self._state: dict = {"atualizada_em": None, "notas": 0, "escritas": 0, "removidas": 0, "erro": None}

    @property
    def state(self) -> dict:
        with self._lock:
            return dict(self._state)

    def request(self) -> None:
        with self._lock:
            if self._queued:
                return
            self._queued = True
            self._idle.clear()
        try:
            self._executor.submit(self._run)
        except RuntimeError:  # o executor já foi encerrado
            with self._lock:
                self._queued = False
                if not self._running:
                    self._idle.set()

    def flush(self, timeout: float = 10.0) -> bool:
        """Espera as rodadas pedidas terminarem."""
        return self._idle.wait(timeout)

    def _run(self) -> None:
        with self._lock:
            self._queued = False
            self._running = True
        try:
            outcome = self._attempt()
        except Exception:  # nenhuma falha daqui pode chegar ao chat
            with self._lock:
                first = self._state["erro"] is None
                self._state["erro"] = FAILURE
            if first:
                print(FAILURE, file=sys.stderr)
        else:
            with self._lock:
                self._state = {"atualizada_em": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                               "erro": None} | outcome
        finally:
            with self._lock:
                self._running = False
                if not self._queued:
                    self._idle.set()

    def _attempt(self) -> dict:
        for wait in (*self.RETRY, None):
            try:
                return self._export()
            except (sqlite3.OperationalError, PermissionError):
                if wait is None:
                    raise
                time.sleep(wait)
        raise RuntimeError("sem tentativas")  # inalcançável
