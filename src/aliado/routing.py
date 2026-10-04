"""Roteador local (lote 31): decide, sem chamar provedor, o que cada mensagem precisa.

Antes de gastar tokens, a mensagem passa por regras rápidas e por um classificador sobre o modelo local de
busca. O resultado diz a escada de leitura (nada, trechos, páginas, documento), a skill, o modelo e quanto
raciocínio pedir, com o motivo em palavras. Na dúvida, vale o caminho barato."""

from __future__ import annotations

import math
import re
from dataclasses import asdict, dataclass

from aliado.knowledge.metadata import named_documents
from aliado.knowledge.stopwords import STOPWORDS, plain
from aliado.routing_examples import INTENTS, SKILLS

# Degraus da escada de leitura.
NONE, PASSAGES, PAGES, DOCUMENT, WIDE = 0, 1, 2, 3, 4
RUNG_NAMES = {NONE: "sem a biblioteca", PASSAGES: "trechos", PAGES: "páginas inteiras", DOCUMENT: "documento inteiro",
              WIDE: "leitura ampla"}
CHEAP, STRONG = "flash_lite", "flash"
DEFAULT_SKILL = "pesquisa-inversores"
# Semelhança mínima com uma frase de exemplo, e a folga sobre o segundo tipo, para o classificador valer.
MIN_SIMILARITY, MIN_MARGIN = 0.45, 0.02
# A skill da conversa só troca quando outra ganha com esta folga.
SKILL_MARGIN = 0.08
# Sem sinal claro, a mensagem só vai à biblioteca se parecer com o título de algum documento. Nas mensagens
# reais de 04/10/2026, as perguntas de referência ficaram em 0,31 ou mais, e a conversa solta, em 0,33 ou menos.
MIN_TOPIC = 0.35
# Uma mensagem curta depois de uma resposta com a biblioteca continua o assunto ("Traga outra fonte.").
FOLLOW_UP_WORDS = 8
# Com menos palavras que isto, a mensagem não troca a skill da conversa.
SKILL_WORDS = 5

_DEEPER = re.compile(r"\b(leia|ler|olhe|veja|verifique|confira|procure)\b.{0,40}\b(mais fundo|a fundo|inteir[oa]s?|tudo|"
                     r"nele|nela|neles|no documento|no original|no artigo|no livro|no pdf)\b|\baprofund")
_MEMORY = re.compile(r"\b(nossas? (ultimas? )?conversas?|conversamos|falamos|voce lembra|lembra d[aeo]|te (disse|falei)|"
                     r"eu (disse|falei)|mais cedo|sobre mim|ultima vez que)\b")
_GREETING = re.compile(r"^(oi+|ola|opa|bom dia|boa tarde|boa noite|obrigad[oa]|valeu|tudo bem|beleza|ok|certo|entendi|"
                       r"perfeito|show)\b")
_COLLECTION = re.compile(r"\b(quais|quantos|que|liste|listar) (sao )?(os |as )?(documentos|artigos|fontes|livros|referencias|"
                         r"autores|normas|arquivos)\b|\b(ha|tem|existe|temos) (algum|alguma|alguns|algumas) (literatura|"
                         r"artigo|fonte|documento|referencia|livro|norma|autor)|\b(no acervo|na biblioteca)\b|"
                         r"\bwhich (documents|papers)\b")
_VISUAL = re.compile(r"\b(figuras?|fig|tabelas?|quadros?|graficos?|diagramas?|arvores? de falhas?|equac(ao|oes)|formulas?|"
                     r"curvas?|esquemas?|fluxogramas?|matriz(es)?|formularios?|figures?|tables?|charts?|diagrams?|"
                     r"fault trees?|plots?|curves?)\b")
_RESULTS = re.compile(r"\b(gpvs|noss[oa]s? (resultados?|dados|avaliac\w+|fmeca|experimentos?|modelos?)|meus? (resultados?|"
                      r"experimentos?|modelos?|dados)|alarmes? falsos?|ensaios?|reanalise|aba ciencia)\b")
_METHOD = re.compile(r"\b(protocolo|particao|calibrac\w+|metodologia|hipoteses?|diretriz(es)?|decis(ao|oes)|criterios?|"
                     r"pipeline|dissertacao)\b")
_SOURCES = re.compile(r"\b(literatura|fontes?|citac\w+|definic\w+|conceitos?|referencias?|artigos?|documentos?|autor(es)?|"
                      r"normas?|livros?|papers?|resumo|abstract)\b")
_TASK = re.compile(r"\b(traceback|python|codigo|script|planilha|e-?mail|https?|na web|noticias?|programa\w*)\b")
_CODE = re.compile(r"\b(traceback|python|codigo|script|programa\w*)\b")
_SYNTHESIS = re.compile(r"\b(compare|comparar|explique|discuta|resuma|o que (e|sao)|como funciona|por que)\b")
_INSTITUTION_NOISE = {"inc", "ltd", "and", "of", "for", "the"}
# Palavras que falam do acervo ou do pedido, e não do assunto: ficam fora da contagem exata de termos.
_GENERIC = set("""literatura literaturas fonte fontes artigo artigos documento documentos livro livros referencia
    referencias autor autores norma normas biblioteca acervo arquivo arquivos algum alguma alguns algumas explica
    explicam explique fala falam trata tratam existe existem quais qual quantos quantas temos cita citam citacao
    menciona mencionam mencao define definem definicao conceito traga mostre liste listar diga segundo acordo
    explicitamente diretamente tema assunto termo palavra sobre papers paper which documents saber gostaria queria
    pode poderia favor aparece aparecem""".split())


@dataclass(frozen=True)
class Route:
    """O que a mensagem pede e como responder gastando o mínimo."""

    intent: str
    rung: int
    skill: str | None
    model: str
    reasoning: str | None = None
    catalog: bool = False
    references: bool = False
    results: bool = False
    deeper: bool = False
    named: tuple[str, ...] = ()
    reasons: tuple[str, ...] = ()

    def view(self) -> dict:
        """A rota para guardar com a resposta e mostrar na tela."""
        return asdict(self) | {"named": list(self.named), "reasons": list(self.reasons), "leitura": RUNG_NAMES[self.rung]}


_CACHE: dict[tuple, dict[str, list[list[float]]]] = {}


def _unit(vector) -> list[float]:
    norm = math.sqrt(sum(value * value for value in vector))
    return [value / norm for value in vector] if norm else []


def _examples(encoder, name: str, groups: dict[str, tuple[str, ...]]) -> dict[str, list[list[float]]]:
    """Os vetores das frases de exemplo, calculados uma vez por modelo local."""
    key = (id(encoder), getattr(encoder, "fingerprint", ""), name)
    if key not in _CACHE:
        _CACHE[key] = {label: [_unit(vector) for vector in encoder.encode(list(sentences))]
                       for label, sentences in groups.items()}
    return _CACHE[key]


def _scores(encoder, name: str, groups, text: str) -> dict[str, float]:
    """A maior semelhança da mensagem com as frases de cada tipo; vazio sem o modelo local."""
    if encoder is None or not text.strip():
        return {}
    try:
        parts = encoder.split(text) if hasattr(encoder, "split") else [text]
        vectors = encoder.encode(parts or [text])
        query = _unit([sum(values) for values in zip(*vectors)])
        examples = _examples(encoder, name, groups)
    except (ValueError, OSError, RuntimeError, ImportError, IndexError):
        return {}  # sem o modelo local, valem só as regras
    return {label: max((sum(a * b for a, b in zip(query, vector)) for vector in vectors_ if len(vector) == len(query)),
                       default=0.0) for label, vectors_ in examples.items()}


def _best(scores: dict[str, float]) -> tuple[str | None, float, float]:
    ranked = sorted(scores.items(), key=lambda item: -item[1])
    if not ranked:
        return None, 0.0, 0.0
    return ranked[0][0], ranked[0][1], ranked[0][1] - (ranked[1][1] if len(ranked) > 1 else 0.0)


def _acronyms(cards: dict) -> dict[str, str]:
    """Siglas de autores institucionais ("NASA", "IEEE"), para reconhecer "o documento da nasa"."""
    found = {}
    for title, entry in cards.items():
        for author in (entry.get("ficha") or {}).get("autores", []):
            words = [word for word in re.findall(r"[^\W\d_]+", author)
                     if word[0].isupper() and plain(word) not in _INSTITUTION_NOISE]
            if len(words) >= 3:
                found["".join(word[0] for word in words).lower()] = title
    return found


def _topic(encoder, cards: dict | None, text: str) -> float:
    """A maior semelhança da mensagem com o título de um documento da biblioteca."""
    titles = tuple(sorted({(entry.get("ficha") or {}).get("titulo") or "" for entry in (cards or {}).values()} - {""}))
    if not titles:
        return 0.0
    return max(_scores(encoder, f"titulos:{hash(titles)}", {"titulos": titles}, text).values(), default=0.0)


def _skill(encoder, text: str, intent: str, current: str | None, available: set[str]) -> tuple[str | None, str | None]:
    """A skill da mensagem e o motivo; a da conversa só troca quando outra ganha com folga."""
    if intent in {"resultados", "metodo"} and DEFAULT_SKILL in available:
        return DEFAULT_SKILL, None
    if intent == "conversa":
        return None, None
    base = current if current in available else (DEFAULT_SKILL if DEFAULT_SKILL in available else None)
    if intent == "tarefa":
        base = None  # fora da biblioteca, a skill só entra se o assunto pedir
    elif len(text.split()) < SKILL_WORDS:
        return base, None  # "E o pertile?" não diz de que assunto se trata: vale a skill da conversa
    scores = {name: value for name, value in _scores(encoder, "skills", SKILLS, text).items()
              if name == "nenhuma" or name in available}
    best, value, _ = _best(scores)
    if best is None or value < MIN_SIMILARITY:
        return base, None
    chosen = None if best == "nenhuma" else best
    if chosen != base and value - scores.get(base or "nenhuma", 0.0) < SKILL_MARGIN:
        return base, None
    return chosen, (f"o assunto combina com a skill {chosen}" if chosen and chosen != base else None)


def _intent(text: str, question: str, words: list[str], named: tuple, encoder, cards, after_library: bool,
            after_results: bool = False) -> tuple[str, str]:
    """O tipo da mensagem e o motivo: regras rápidas primeiro; depois, as frases de exemplo."""
    if _DEEPER.search(text) and len(words) <= 14:
        return "aprofundar", "a mensagem pede uma leitura mais funda"
    if named:
        names = ", ".join((cards[title].get("referencia") or title) for title in named)
        return "documento", f"a mensagem cita {names}"
    if _MEMORY.search(text) or (len(words) <= 5 and _GREETING.search(text)):
        return "conversa", "é conversa ou memória, sem consulta aos documentos"
    if _COLLECTION.search(text):
        return "acervo", "a pergunta é sobre o que há na biblioteca"
    if _VISUAL.search(text):
        return "visual", "a pergunta fala de figura, tabela, gráfico ou fórmula"
    if _RESULTS.search(text):
        return "resultados", "a pergunta é sobre os resultados da pesquisa"
    if _TASK.search(text):
        return "tarefa", "é uma tarefa de código, de escrita ou de busca fora da biblioteca"
    if after_library and len(words) <= FOLLOW_UP_WORDS:
        return "continuacao", "mensagem curta que continua a pergunta anterior"
    if after_results and len(words) <= FOLLOW_UP_WORDS and not _GREETING.search(text):
        return "resultados", "mensagem curta que continua a pergunta sobre os resultados"
    label, value, margin = _best(_scores(encoder, "intents", INTENTS, question))
    sources = bool(_SOURCES.search(text))
    if (label is not None and value >= MIN_SIMILARITY and margin >= MIN_MARGIN
            and not (label in {"conversa", "tarefa"} and sources)):
        return label, f"parece uma mensagem do tipo «{label}»"
    if _METHOD.search(text):
        return "metodo", "a pergunta é de método ou de decisões da pesquisa"
    if sources:
        return "sintese", "a pergunta pede o que os documentos dizem"
    if encoder is None or _topic(encoder, cards, question) >= MIN_TOPIC:
        return ("sintese" if _SYNTHESIS.search(text) else "consulta"), "o assunto parece com o de um documento da biblioteca"
    return "conversa", "não parece com nenhum documento da biblioteca"


def terms(question: str, *, limit: int = 6) -> list[str]:
    """As palavras do assunto de uma pergunta, para a contagem exata na biblioteca: sem as palavras vazias e
    sem as que falam do acervo ("literatura", "fonte", "explica")."""
    kept = []
    for word in re.findall(r"[^\W\d_]+(?:-[^\W\d_]+)*", question, re.UNICODE):
        key = plain(word)
        if len(key) >= 4 and key not in STOPWORDS and key not in _GENERIC and key not in {plain(k) for k in kept}:
            kept.append(word)
    return kept[:limit]


def route(question: str, *, encoder=None, cards: dict | None = None, skills=(), current_skill: str | None = None,
          library: bool = True, results: bool = False, previous: dict | None = None) -> Route:
    """A rota de uma mensagem. `library` e `results` dizem o que está ligado na tela; `cards` são as fichas dos
    documentos, para reconhecer um autor citado; `skills` são as disponíveis, e `current_skill`, a da conversa;
    `previous` é a rota da resposta anterior, para a mensagem curta que continua o assunto."""
    text = plain(question)
    words = text.split()
    cards = cards or {}
    named = set(named_documents(question, cards))
    named |= {title for acronym, title in _acronyms(cards).items() if re.search(rf"\b{re.escape(acronym)}\b", text)}
    named = tuple(sorted(named))
    before = int((previous or {}).get("rung") or 0)
    intent, why = _intent(text, question, words, named, encoder, cards, before >= PASSAGES,
                          bool((previous or {}).get("results")) and results)
    reasons = [why]
    skill, skill_why = _skill(encoder, question, intent, current_skill, set(skills))
    if skill_why:
        reasons.append(skill_why)
    rung = {"conversa": NONE, "tarefa": NONE, "resultados": NONE, "acervo": PASSAGES, "fato": PASSAGES,
            "sintese": PASSAGES, "metodo": PASSAGES, "consulta": PASSAGES, "visual": PAGES, "documento": DOCUMENT,
            "aprofundar": max(before, PASSAGES), "continuacao": max(before, PASSAGES)}[intent]
    if intent == "resultados" and _SOURCES.search(text):
        rung = PASSAGES  # "compare os nossos resultados com a literatura" pede os dois
    if not library:
        rung = NONE
    # O modelo menor para conversa, acervo, fato pontual e tarefa sem código; o maior para o resto.
    cheap = intent in {"conversa", "acervo", "fato"} or (intent == "tarefa" and skill != "engenharia"
                                                          and not _CODE.search(text))
    return Route(
        intent=intent, rung=rung, skill=skill, model=CHEAP if cheap else STRONG,
        reasoning="low" if cheap else None, catalog=intent == "acervo" and library,
        references=intent in {"resultados", "metodo", "consulta", "aprofundar", "continuacao"},
        results=results and intent in {"resultados", "metodo"}, deeper=intent == "aprofundar", named=named,
        reasons=tuple(reasons))
