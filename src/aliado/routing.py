"""Roteador local (lote 31): decide, sem chamar provedor, o que cada mensagem precisa.

Antes de gastar tokens, a mensagem passa por regras rápidas e por um classificador sobre o modelo local de
busca. O resultado diz a escada de leitura (nada, trechos, páginas, documento), a skill, o modelo e quanto
raciocínio pedir, com o motivo em palavras. Na dúvida, vale o caminho barato."""

from __future__ import annotations

import math
import re
from dataclasses import asdict, dataclass
from functools import cache

from aliado.knowledge.metadata import named_documents
from aliado.knowledge.stopwords import STOPWORDS, plain
from aliado.routing_examples import INTENTS, SKILLS

# Degraus da escada de leitura.
NONE, PASSAGES, PAGES, DOCUMENT, WIDE = 0, 1, 2, 3, 4
RUNG_NAMES = {NONE: "sem a biblioteca", PASSAGES: "trechos", PAGES: "páginas inteiras", DOCUMENT: "documento inteiro",
              WIDE: "leitura ampla"}
CHEAP, STRONG = "flash_lite", "flash"
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
_RESULTS = re.compile(r"\b(noss[oa]s? (resultados?|dados|avaliac\w+|fmeca|experimentos?|modelos?)|meus? (resultados?|"
                      r"experimentos?|modelos?|dados)|alarmes? falsos?|ensaios?|reanalise|aba ciencia)\b")
# Resultados da pesquisa sem as palavras acima (lote 33). Os nomes dos modelos, dos ensaios e das métricas vêm do
# resumo dos resultados que o servidor monta para o chat (`results_vocabulary`); sem ele, valem estes. Um modelo ou
# um ensaio da pesquisa basta. Uma métrica precisa de um objeto da pesquisa ou de um sinal de valor obtido; um
# objeto, de um verbo no passado. Pedido de fonte ou de conceito ("o que é", "como funciona") não é resultado.
RESULT_MODELS = frozenset({"denso", "ae-lstm"})
RESULT_METRICS = frozenset({"sensibilidade", "especificidade", "precisao", "recall", "atraso", "atraso mediano",
                            "ensaios detectados", "alarme", "alarmes", "mcc", "f1", "taxa de deteccao", "criticidade",
                            "npr", "disponibilidade", "confiabilidade", "limiar"})
_TRIAL = re.compile(r"\bf\d{1,2}[lm]?\b")
_STUDY = re.compile(r"\b(detector(es)?|modelos?|autoencoders?|lstm|recorrente|componentes?|grupos?|cenarios?|ensaios?)\b")
_DONE = re.compile(r"\b(detect(ou|aram)|teve|tiveram|deu|deram|ficou|ficaram|obtive|obtivemos|consegui|conseguimos|"
                   r"errou|erraram|acertou|acertaram|funcionou|funcionaram|gerou|geraram|disparou|dispararam|"
                   r"alcancou|alcancaram|atingiu|atingiram|perdeu|perderam)\b")
_RANK = re.compile(r"\b(maior|menor|melhor|pior|mais alt[oa]|mais baix[oa])\b")
_PROGRESS = re.compile(r"\bo que (eu )?(ja )?(consegui|obtive|alcancei|produzi)\b|\bmeu progresso\b")
# "Como se calcula a confiabilidade de um sistema com componentes..." é conceito, não resultado (lote 47, a P7).
_CONCEPT = re.compile(r"^(o que (e|sao)|defina|como funciona|qual (e )?a definicao|como (se )?calcul\w*)\b")
# Depois de uma resposta com a biblioteca (lote 33): conversa solta não volta à biblioteca; reclamação lê mais fundo.
_CHAT = re.compile(r"\b(k{3,}\w*|kak\w*|(ha){2,}|rs+|valeu|obrigad[oa]s?|legal|show|massa|nossa|relaxa|tranquil\w*|"
                   r"beleza|otim[oa]|excelente|perfeit[oa]|incrivel|sabido|esperto|cansad[oa]|informal|descontraid[oa])\b")
_LIBRARY_ASK = re.compile(r"\b(traga|traz|trazer|mostre|cite|citacao|fontes?|explique|compare|liste|resuma|detalhe|defina|"
                          r"tabelas?|figuras?|paginas?|primeir[oa]|segund[oa]|outr[oa]|isso|disso|nisso|mas e)\b|"
                          r"(?:^|[.,;!?]\s*)e (?:o|a|os|as|sobre)\b")  # "Nossa, que bom. E a FMECA?"
_COMPLAINT = re.compile(r"\b(voce|vc)\b.{0,30}\b(nao (conseguiu|trouxe|respondeu|achou|encontrou|citou)|esqueceu|errou)\b|"
                        r"\b(faltou|faltaram|ficou faltando)\b|\bnao (era|e|foi) isso\b|"
                        r"\b(resposta|isso) (esta |ficou )?(incomplet[oa]|errad[oa])\b")
_METHOD = re.compile(r"\b(protocolo|particao|calibrac\w+|metodologia|hipoteses?|diretriz(es)?|decis(ao|oes)|criterios?|"
                     r"pipeline|dissertacao)\b")
_SOURCES = re.compile(r"\b(literatura|fontes?|citac\w+|definic\w+|conceitos?|referencias?|artigos?|documentos?|autor(es)?|"
                      r"normas?|livros?|papers?|resumo|abstract|teses?|thesis|theses|tcc|monografias?)\b")
# A obra de outro autor é material da biblioteca, não resultado desta pesquisa (lote 47, a E3).
_WORKS = re.compile(r"\b(teses?|thesis|theses|tcc|monografias?)\b")
_TASK = re.compile(r"\b(traceback|python|codigo|script|planilha|e-?mail|https?|na web|noticias?|programa\w*)\b")
_CODE = re.compile(r"\b(traceback|python|codigo|script|programa\w*)\b")
# Lote 70: tradução, explicação para leigo ou curta e lista pedem só o modelo; sem pedido de fonte, a biblioteca só atrasa.
_DIRECT = re.compile(r"^(traduza|traduzir|translate)\b|\bpara (um |uma )?leig[oa]s?\b|"
                     r"\bem (uma|duas|tres|ate (duas|tres|\d+)|\d+) (frases?|linhas?)\b|\bem poucas palavras\b|^liste\b")
_SYNTHESIS = re.compile(r"\b(compare|comparar|explique|discuta|resuma|o que (e|sao)|como funciona|por que)\b")
_INSTITUTION_NOISE = {"inc", "ltd", "and", "of", "for", "the"}
# Pedidos escritos (lote 35): o que antes era um seletor ou uma chave da tela. Valem só no começo ou no fim de uma
# oração ("Use o modelo maior. O que é MCC?", "Explique MCC usando o modelo maior"), para uma pergunta comum
# ("o modelo maior detectou mais?") não virar pedido. O texto é comparado sem acento e em minúsculas.
_USE = r"(?:use|usa|usar|usando|utilize|utilizando|responda com|responda usando|pelo|via)"
_DIRECTIVES = (
    ("modelo", STRONG, rf"{_USE} (?:o )?modelo (?:maior|mais forte|mais potente|mais capaz|completo|grande)"),
    ("modelo", CHEAP, rf"{_USE} (?:o )?modelo (?:menor|mais barato|mais rapido|mais leve|pequeno)"),
    ("biblioteca", False, r"sem (?:usar |consultar )?(?:a )?biblioteca|sem (?:usar |consultar )?(?:os )?(?:meus )?documentos|"
                          r"nao (?:use|consulte|abra) (?:a biblioteca|os documentos)"),
    ("leitura", WIDE, r"(?:faca |use |usando |com )?(?:a )?leitura ampla|(?:leia|ler|lendo) (?:todos )?os documentos inteiros"),
    ("leitura", DOCUMENT, r"(?:leia|ler|lendo) (?:o|este|esse) (?:documento|artigo|livro|pdf|arquivo) (?:inteiro|todo|completo)"),
    ("leitura", PAGES, r"(?:leia|ler|lendo|use|usando|com) (?:as )?paginas inteiras"),
    ("leitura", PASSAGES, r"(?:responda |use |usando |leia |com )?(?:so|somente|apenas) (?:com )?(?:os )?trechos"),
    ("web", True, r"(?:busque|buscar|pesquise|pesquisar|procure|procurar|consulte|consultar)(?: isso| isto)? "
                  r"(?:na web|na internet|online|no google)"),
    ("web", False, r"sem (?:buscar |busca |pesquisar |pesquisa |consultar )?(?:na |a )?(?:web|internet)"),
    ("resultados", True, r"(?:use|usa|usando|considere|inclua|incluindo) (?:os )?(?:nossos |meus )?resultados(?: da pesquisa)?"),
    ("resultados", False, r"sem (?:os )?(?:nossos |meus )?resultados(?: da pesquisa)?"),
    ("skill", "nenhuma", r"sem (?:skill|especializacao)"),
    ("skill", None, r"(?:use|usa|usando|com) a skill (?:de |da )?(?P<name>[a-z0-9-]+)"),
    ("apoio", None, r"com (?:o )?apoio (?:da |de )?(?:skill )?(?:de |da )?(?P<name>[a-z0-9-]+)"),
)
_PLEASE = r"(?:(?:por favor|pf),?\s*)?"
# Uma oração termina num ponto, ponto e vírgula, dois-pontos, exclamação, interrogação, quebra de linha ou numa
# vírgula seguida de espaço (a de "0,5" não separa).
_CLAUSE = re.compile(r"[.;:!?\n]+|,(?=\s)")
CHOICE_NAMES = {"modelo": {STRONG: "o modelo maior", CHEAP: "o modelo menor"}, "biblioteca": {False: "sem a biblioteca"},
                "web": {True: "com busca na web", False: "sem a web"},
                "resultados": {True: "com os resultados da pesquisa", False: "sem os resultados da pesquisa"}}
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
    # A mensagem reclama da resposta anterior (lote 33): a pergunta anterior volta com uma leitura mais funda.
    complaint: bool = False

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


@cache
def _specialized() -> dict:
    """O que as especializações acrescentam ao roteador (lote 36): frases de exemplo, termos que levam aos
    resultados e a skill padrão. Lido na primeira mensagem, nunca ao importar este módulo."""
    from aliado import specializations

    intents = {name: list(examples) for name, examples in INTENTS.items()}
    skills, terms = {}, []
    for extra in specializations.gather("ROUTING"):
        for name, examples in extra.get("intents", {}).items():
            intents.setdefault(name, []).extend(examples)
        skills |= extra.get("skills", {})
        terms += extra.get("results_terms", ())
    return {"intents": {name: tuple(examples) for name, examples in intents.items()}, "skills": skills | SKILLS,
            "results": re.compile(r"\b(" + "|".join(map(re.escape, terms)) + r")\b") if terms else None,
            "default": specializations.first("DEFAULT_SKILL")}


def _skill(encoder, text: str, intent: str, current: str | None, available: set[str]) -> tuple[str | None, str | None]:
    """A skill da mensagem e o motivo; a da conversa só troca quando outra ganha com folga."""
    default = _specialized()["default"]
    if intent in {"resultados", "metodo"} and default in available:
        return default, None
    if intent == "conversa":
        return None, None
    base = current if current in available else (default if default in available else None)
    if intent == "tarefa":
        base = None  # fora da biblioteca, a skill só entra se o assunto pedir
    elif len(text.split()) < SKILL_WORDS:
        return base, None  # "E o pertile?" não diz de que assunto se trata: vale a skill da conversa
    scores = {name: value for name, value in _scores(encoder, "skills", _specialized()["skills"], text).items()
              if name == "nenhuma" or name in available}
    best, value, _ = _best(scores)
    if best is None or value < MIN_SIMILARITY:
        return base, None
    chosen = None if best == "nenhuma" else best
    if chosen != base and value - scores.get(base or "nenhuma", 0.0) < SKILL_MARGIN:
        return base, None
    return chosen, (f"o assunto combina com a skill {chosen}" if chosen and chosen != base else None)


def _table_rows(text: str) -> list[list[str]]:
    """As linhas de uma tabela em Markdown, célula por célula, sem a linha de separação."""
    rows = []
    for line in str(text or "").splitlines():
        if line.strip().startswith("|") and not re.fullmatch(r"[\s|:-]+", line):
            rows.append([cell.strip() for cell in line.strip().strip("|").split("|")])
    return rows


def results_vocabulary(digest: dict | None) -> dict[str, frozenset[str]]:
    """Os modelos, os ensaios e as métricas que aparecem no resumo dos resultados (lote 33), sem acento.

    Modelos: as colunas de uma tabela de indicadores, a primeira coluna de uma tabela de modelos e o prefixo de
    colunas como "Denso: sensibilidade". Ensaios: a primeira coluna de uma tabela de ensaios. Métricas: os nomes
    das notas de cada indicador. Somam-se aos de sempre, para valer também sem o resumo."""
    models, trials, metrics = set(RESULT_MODELS), set(), set(RESULT_METRICS)
    for block in (digest or {}).get("blocos") or ():
        for note in block.get("notas") or ():
            name = plain(note.get("nome") or "").strip()
            if 2 <= len(name) <= 40:
                metrics.add(name)
        for table in re.split(r"\n\s*\n", str(block.get("texto") or "")):
            rows = _table_rows(table)
            if not rows:
                continue
            header = [plain(cell) for cell in rows[0]]
            models |= {cell.split(":")[0].strip() for cell in header if ":" in cell}
            if header[0] == "indicador":
                models |= {cell for cell in header[1:] if cell and ":" not in cell}
            first = {plain(row[0]) for row in rows[1:] if row and row[0]}
            if header[0] == "modelo":
                models |= first
            elif header[0] == "ensaio":
                trials |= first
    clean = lambda values: frozenset(value for value in values if 2 <= len(value) <= 40)  # noqa: E731
    # Um nome de modelo é curto e sem números nem vírgulas ("Denso", "AE-LSTM"); o resto é título de coluna.
    names = {value for value in models if re.fullmatch(r"[a-z][a-z-]*( [a-z-]+)?", value)}
    return {"modelos": clean(names), "ensaios": clean(trials), "metricas": clean(metrics)}


def _has(text: str, phrase: str) -> bool:
    return bool(re.search(rf"(?<![\w-]){re.escape(phrase)}(?![\w-])", text))


def _about_results(text: str, vocabulary: dict | None) -> bool:
    """A mensagem pergunta pelos resultados da pesquisa, mesmo sem dizer "resultados" (lote 33)."""
    terms = _specialized()["results"]
    if _RESULTS.search(text) or _PROGRESS.search(text) or (terms is not None and terms.search(text)):
        return True
    if _SOURCES.search(text) or _CONCEPT.search(text):
        return False
    vocabulary = vocabulary or results_vocabulary(None)
    if _TRIAL.search(text) or any(_has(text, name) for name in vocabulary["ensaios"]):
        return True
    # "Denso" também é adjetivo ("o capítulo é denso"): um modelo só conta junto de uma métrica, de uma palavra da
    # pesquisa ou de outro modelo.
    models = sum(_has(text, name) for name in vocabulary["modelos"])
    metric = any(_has(text, name) for name in vocabulary["metricas"])
    study = bool(_STUDY.search(text))
    return bool((models and (metric or study or models > 1))
                or (metric and (study or _DONE.search(text) or _RANK.search(text))) or (study and _DONE.search(text)))


def _intent(text: str, question: str, words: list[str], named: tuple, encoder, cards, after_library: bool,
            after_results: bool = False, vocabulary: dict | None = None) -> tuple[str, str]:
    """O tipo da mensagem e o motivo: regras rápidas primeiro; depois, as frases de exemplo."""
    if after_library and _COMPLAINT.search(text):
        return "reclamacao", "a mensagem diz que a resposta anterior não bastou: leitura mais funda"
    if _DEEPER.search(text) and len(words) <= 14:
        return "aprofundar", "a mensagem pede uma leitura mais funda"
    if named:
        names = ", ".join((cards[title].get("referencia") or title) for title in named)
        return "documento", f"a mensagem cita {names}"
    # "Valeu! E a segunda fonte?" agradece e pede: depois de uma resposta com a biblioteca, vale o pedido.
    if _MEMORY.search(text) or (len(words) <= 5 and _GREETING.search(text)
                                and not (after_library and _LIBRARY_ASK.search(text))):
        return "conversa", "é conversa ou memória, sem consulta aos documentos"
    if _COLLECTION.search(text):
        return "acervo", "a pergunta é sobre o que há na biblioteca"
    if _VISUAL.search(text):
        return "visual", "a pergunta fala de figura, tabela, gráfico ou fórmula"
    if _about_results(text, vocabulary):
        return "resultados", "a pergunta é sobre os resultados da pesquisa"
    if _TASK.search(text):
        return "tarefa", "é uma tarefa de código, de escrita ou de busca fora da biblioteca"
    if after_library and len(words) <= FOLLOW_UP_WORDS and _CHAT.search(text) and not _LIBRARY_ASK.search(text):
        return "conversa", "conversa solta depois de uma resposta com a biblioteca"
    if after_library and len(words) <= FOLLOW_UP_WORDS:
        return "continuacao", "mensagem curta que continua a pergunta anterior"
    if after_results and len(words) <= FOLLOW_UP_WORDS and not _GREETING.search(text):
        return "resultados", "mensagem curta que continua a pergunta sobre os resultados"
    sources = bool(_SOURCES.search(text))
    if _DIRECT.search(text) and not sources:
        return "tarefa", "pede tradução, explicação curta ou lista, sem pedir fontes: responde direto"
    label, value, margin = _best(_scores(encoder, "intents", _specialized()["intents"], question))
    if (label is not None and value >= MIN_SIMILARITY and margin >= MIN_MARGIN
            and not (label in {"conversa", "tarefa"} and sources) and not (label == "resultados" and _WORKS.search(text))):
        return label, f"parece uma mensagem do tipo «{label}»"
    if _METHOD.search(text):
        return "metodo", "a pergunta é de método ou de decisões da pesquisa"
    if sources:
        return "sintese", "a pergunta pede o que os documentos dizem"
    if encoder is None or _topic(encoder, cards, question) >= MIN_TOPIC:
        return ("sintese" if _SYNTHESIS.search(text) else "consulta"), "o assunto parece com o de um documento da biblioteca"
    return "conversa", "não parece com nenhum documento da biblioteca"


@dataclass(frozen=True)
class Written:
    """A mensagem sem os pedidos escritos e o que eles pedem, campo por campo."""

    text: str
    choices: dict


def _folded(text: str) -> tuple[str, list[int]]:
    """O texto sem acento e em minúsculas, com a posição de cada letra dele no original."""
    letters, where = [], []
    for index, char in enumerate(text):
        for letter in plain(char):
            letters.append(letter)
            where.append(index)
    return "".join(letters), where


def _value(field: str, value, match, skills: set[str]):
    if value is not None:
        return value
    name = match.group("name")
    return name if name in skills else None


def _clause(clause: str, skills: set[str], choices: dict) -> list[tuple[int, int]]:
    """Os trechos de uma oração que são pedidos, no começo ou no fim dela; registra o que cada um pede.

    O pedido do documento inteiro fica no texto: "Leia o artigo inteiro do Pertile" diz qual é o documento. Seguido
    de "de/do/da", não é pedido: "Sem a biblioteca de componentes, ..." fala de outra biblioteca."""
    spans, start, end = [], 0, len(clause)
    while True:
        segment = clause[start:end]
        for field, value, pattern in _DIRECTIVES:
            keep = field == "leitura" and value == DOCUMENT
            other = "" if keep else r"(?!\s+d[aeo]s?\b)"
            head = re.match(rf"\s*{_PLEASE}(?:{pattern})(?![\w-]){other}(?:\s*,?\s+e(?=\s))?", segment)
            if head and (got := _value(field, value, head, skills)) is not None:
                choices[field] = got
                spans += [] if keep else [(start, start + head.end())]
                start += head.end()
                break
            tail = re.search(rf"(?:^|\s)(?:e\s+)?(?:{pattern}),?\s*(?:por favor)?\s*$", segment)
            if tail and (got := _value(field, value, tail, skills)) is not None:
                choices[field] = got
                spans += [] if keep else [(start + tail.start(), end)]
                end = start + tail.start()
                break
        else:
            return spans


def directives(question: str, skills=()) -> Written:
    """Os pedidos escritos da mensagem (lote 35) e a mensagem sem eles, para o roteador, a busca e o modelo.

    Valem só no começo ou no fim de uma oração; um pedido que ocupa a oração inteira some com a pontuação dela.
    `skills` são os nomes das skills que existem: "use a skill X" só vale para uma delas."""
    folded, where = _folded(question)
    names = set(skills)
    choices: dict = {}
    removed: list[tuple[int, int]] = []
    position, before = 0, None
    for separator in [*_CLAUSE.finditer(folded), None]:
        start, end = position, separator.start() if separator else len(folded)
        position = separator.end() if separator else len(folded)
        spans = _clause(folded[start:end], names, choices)
        comma = before is not None and folded[before.start():before.end()].strip() == ","
        previous, before = before, separator
        if not spans:
            continue
        rest = folded[start:end]
        for a, b in sorted(spans, reverse=True):
            rest = rest[:a] + rest[b:]
        if not re.fullmatch(r"\s*(?:e|por favor|pf)?\s*", rest):
            removed += [(start + a, start + b) for a, b in spans]
        elif comma:
            removed.append((previous.start(), end))  # ", só com trechos?": sai com a vírgula, e o "?" fica
        else:
            removed.append((start, position))  # a oração era só o pedido: sai com a pontuação dela
    if not removed:
        return Written(question.strip(), choices)
    drop = set()
    for a, b in removed:
        if b > a:
            drop.update(range(where[a], where[b - 1] + 1))
    text = "".join(char for index, char in enumerate(question) if index not in drop)
    text = re.sub(r"\s+([.,;:!?])", r"\1", re.sub(r"\s+", " ", text)).strip()
    # Sem o pedido, um "por favor" solto não é pergunta.
    text = re.sub(r"^(?:[.,;:!?]+\s*|e\s+|(?:por favor|pf)\s*[.,;:!]?\s*)+", "", text, flags=re.IGNORECASE)
    text = re.sub(r"[,;]\s*(?:por favor|pf)\s*([.!?]?)$", r"\1", text, flags=re.IGNORECASE)
    return Written(text[:1].upper() + text[1:] if text else "", choices)


def describe(choices: dict) -> list[str]:
    """Os pedidos escritos em palavras, para a linha da rota sob a resposta."""
    said = []
    for field, value in choices.items():
        if field == "leitura":
            said.append(RUNG_NAMES[value] if value == WIDE else f"leitura: {RUNG_NAMES[value]}")
        elif field == "skill":
            said.append("sem skill" if value == "nenhuma" else f"skill {value}")
        elif field == "apoio":
            said.append(f"apoio da skill {value}")
        else:
            said.append(CHOICE_NAMES[field][value])
    return said


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
          library: bool = True, results: bool = False, previous: dict | None = None,
          vocabulary: dict | None = None) -> Route:
    """A rota de uma mensagem. `library` e `results` dizem o que está ligado na tela; `cards` são as fichas dos
    documentos, para reconhecer um autor citado; `skills` são as disponíveis, e `current_skill`, a da conversa;
    `previous` é a rota da resposta anterior, para a mensagem curta que continua o assunto; `vocabulary`, os nomes
    tirados dos resultados (`results_vocabulary`)."""
    text = plain(question)
    words = text.split()
    cards = cards or {}
    named = set(named_documents(question, cards))
    named |= {title for acronym, title in _acronyms(cards).items() if re.search(rf"\b{re.escape(acronym)}\b", text)}
    named = tuple(sorted(named))
    before = int((previous or {}).get("rung") or 0)
    intent, why = _intent(text, question, words, named, encoder, cards, before >= PASSAGES,
                          bool((previous or {}).get("results")) and results, vocabulary)
    complaint = intent == "reclamacao"
    if complaint:
        intent = "aprofundar"
    reasons = [why]
    skill, skill_why = _skill(encoder, question, intent, current_skill, set(skills))
    if skill_why:
        reasons.append(skill_why)
    rung = {"conversa": NONE, "tarefa": NONE, "resultados": NONE, "acervo": PASSAGES, "fato": PASSAGES,
            "sintese": PASSAGES, "metodo": PASSAGES, "consulta": PASSAGES, "visual": PAGES, "documento": DOCUMENT,
            "aprofundar": max(before, PAGES if complaint else PASSAGES), "continuacao": max(before, PASSAGES)}[intent]
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
        reasons=tuple(reasons), complaint=complaint)
