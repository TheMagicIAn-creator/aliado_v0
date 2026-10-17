"""Gera os mapas documentais em SVG editável e PNG; não acessa dados do usuário."""

from __future__ import annotations

import html
import math
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

OUT = Path(__file__).resolve().parent
SCALE = 1.5
COLORS = {
    "ui": ("#eaf2ff", "#2f65c8"),
    "local": ("#e7f5f3", "#17786e"),
    "ml": ("#f0eafd", "#7552b3"),
    "cloud": ("#fff0df", "#b76718"),
    "data": ("#eef1f6", "#596b85"),
    "science": ("#eaf4e5", "#527c32"),
}
INK, MUTED, LINE = "#172b43", "#52647b", "#8b9cb0"


class Map:
    def __init__(self, number, name, title, subtitle, height=1420):
        self.name, self.height = name, height
        self.im = Image.new("RGB", (2700, int(height * SCALE)), "#f8fafc")
        self.draw = ImageDraw.Draw(self.im)
        self.svg = [f'<svg xmlns="http://www.w3.org/2000/svg" width="1800" height="{height}" viewBox="0 0 1800 {height}">',
                    '<rect width="100%" height="100%" fill="#f8fafc"/>',
                    f'<title>{html.escape(title)}</title><desc>{html.escape(subtitle)}</desc>']
        self.text(55, 27, f"AL-IAdo  /  MAPA {number:02d}", 18, "#17786e", True)
        self.text(55, 65, title, 43, INK, True)
        self.text(55, 128, subtitle, 21, MUTED)
        x = 55
        for key, label in [("ui", "Interface"), ("local", "Código local"), ("ml", "Modelo local"),
                           ("cloud", "API paga"), ("data", "Persistência"), ("science", "Ciência")]:
            self.rect(x, 176, 13, 13, COLORS[key][1], COLORS[key][1], 3)
            self.text(x + 23, 169, label, 17, MUTED)
            x += 200
        self.text(55, height - 48, "Código local em 05/10/2026 · v0.5.0 + lote 32 · setas = fluxo ou dependência; não são serviços separados", 16, MUTED)
        self.text(1580, height - 48, f"MAPA {number:02d} / 05", 16, MUTED, True)

    def font(self, size, bold=False):
        return ImageFont.truetype("C:/Windows/Fonts/segoeuib.ttf" if bold else "C:/Windows/Fonts/segoeui.ttf", round(size * SCALE))

    def text(self, x, y, value, size=21, color=INK, bold=False):
        self.draw.text((x * SCALE, y * SCALE), value, font=self.font(size, bold), fill=color)
        self.svg.append(f'<text x="{x}" y="{y}" dominant-baseline="text-before-edge" font-family="Segoe UI, Arial, sans-serif" font-size="{size}" font-weight="{700 if bold else 400}" fill="{color}">{html.escape(value)}</text>')

    def rect(self, x, y, w, h, fill, stroke, radius=15, width=1):
        self.draw.rounded_rectangle(tuple(round(v * SCALE) for v in (x, y, x + w, y + h)), round(radius * SCALE), fill, stroke, round(width * SCALE))
        self.svg.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{radius}" fill="{fill}" stroke="{stroke}" stroke-width="{width}"/>')

    def paragraph(self, x, y, text, width, size=21, color=INK, bold=False):
        cursor = y
        for para in text.split("\n"):
            line = ""
            for word in para.split():
                proposed = f"{line} {word}".strip()
                if self.draw.textlength(proposed, font=self.font(size, bold)) > width * SCALE and line:
                    self.text(x, cursor, line, size, color, bold)
                    cursor += size * 1.42
                    line = word
                else:
                    line = proposed
            self.text(x, cursor, line, size, color, bold)
            cursor += size * 1.42
        return cursor

    def card(self, x, y, w, h, title, body, kind="local", foot=None, new=False, size=21):
        fill, accent = COLORS[kind]
        self.rect(x, y, w, h, fill, accent, width=1.4)
        self.rect(x + 1, y + 18, 5, h - 36, accent, accent, 2)
        if new:
            self.rect(x + w - 136, y - 14, 120, 29, "#17786e", "#17786e", 8)
            self.text(x + w - 123, y - 11, "NOVO · LOTE 32", 13, "#ffffff", True)
        cursor = self.paragraph(x + 22, y + 16, title, w - 44, 25, INK, True)
        cursor = self.paragraph(x + 22, cursor + 8, body, w - 44, size, INK)
        bottom = y + h - (39 if foot else 15)
        if cursor > bottom + 5:
            raise ValueError(f"Texto excede cartão: {title}: {cursor} > {bottom}")
        if foot:
            self.text(x + 22, y + h - 33, foot, 15, MUTED)

    def area(self, x, y, w, h, label, kind="local"):
        self.rect(x, y, w, h, "#ffffff", "#cad5e2", 19)
        self.text(x + 22, y + 13, label, 18, COLORS[kind][1], True)

    def arrow(self, points, label=None, label_at=None, color=LINE, dashed=False):
        scaled = [(x * SCALE, y * SCALE) for x, y in points]
        if dashed:
            for a, b in zip(scaled, scaled[1:]):
                dist = math.dist(a, b)
                for start in range(0, int(dist), 15):
                    end = min(start + 8, dist)
                    self.draw.line([(a[0] + (b[0] - a[0]) * p / dist, a[1] + (b[1] - a[1]) * p / dist) for p in (start, end)], fill=color, width=3)
        else:
            self.draw.line(scaled, fill=color, width=3)
        x, y = points[-1]
        a, b = points[-2]
        angle = math.atan2(y - b, x - a)
        head = [(x, y), (x - 11 * math.cos(angle - .45), y - 11 * math.sin(angle - .45)),
                (x - 11 * math.cos(angle + .45), y - 11 * math.sin(angle + .45))]
        self.draw.polygon([(a * SCALE, b * SCALE) for a, b in head], fill=color)
        coords = " ".join(f"{a},{b}" for a, b in points)
        dash = ' stroke-dasharray="6 5"' if dashed else ""
        self.svg.append(f'<polyline points="{coords}" fill="none" stroke="{color}" stroke-width="2"{dash}/><polygon points="{" ".join(f"{a},{b}" for a,b in head)}" fill="{color}"/>')
        if label:
            self.text(*label_at, label, 16, MUTED)

    def save(self):
        self.im.save(OUT / f"{self.name}.png", optimize=True)
        (OUT / f"{self.name}.svg").write_text("\n".join(self.svg + ["</svg>"]), encoding="utf-8")
        print(f"OK {self.name} ({self.im.width} x {self.im.height})")


def overview():
    d = Map(1, "01-visao-geral", "Arquitetura geral: setores e fronteiras", "Aplicação Python local e modular · servidor Starlette/Uvicorn · interface no navegador · Gemini na nuvem")
    d.area(45, 225, 1270, 1015, "COMPUTADOR DO PESQUISADOR · 127.0.0.1:8765")
    d.area(1360, 225, 395, 1015, "SERVIÇOS EXTERNOS", "cloud")
    d.card(75, 285, 785, 160, "1  Interface web", "Chat e fontes · envio de documentos · Memória · Ciência\nHTML, CSS e JavaScript; gráficos D3 e fórmulas KaTeX.", "ui", "interfaces/web/static/")
    d.card(900, 285, 385, 160, "2  Terminal", "Comandos para conversar, preparar a biblioteca e executar ciência.", "ui", "cli.py")
    d.arrow([(450, 445), (450, 500)])
    d.arrow([(1092, 445), (1092, 500)])
    d.card(75, 500, 1210, 180, "3  Coordenação e regras da conversa", "Servidor web + Agent: roteamento local, contexto, leitura, estimativas, chamada ao modelo e conferência.\nSkills do AL-IAdo: engenharia, confiabilidade e pesquisa de inversores; carregadas conforme a tarefa.", "local", "interfaces/web/app.py · agent.py · routing.py · skills/builtin/")
    for x in (260, 680, 1100):
        d.arrow([(x, 680), (x, 745)])
    d.card(75, 745, 370, 240, "4  Biblioteca", "Originais, extração, busca por texto e significado.\nCache + reordenação local das páginas (lote 32).", "ml", "knowledge/ · veja mapa 03")
    d.card(495, 745, 370, 240, "5  Memória", "Perfil, preferências, correções e conversas.\nFiltro local da revisão paga (lote 32).", "local", "memory/ · veja mapa 04")
    d.card(915, 745, 370, 240, "6  Ciência", "Cálculos, autoencoders e avaliações por comando.\nResultados estruturados disponíveis ao chat.", "science", "science/ · veja mapa 05")
    for x in (260, 680, 1100):
        d.arrow([(x, 985), (x, 1050)])
    d.card(75, 1050, 1210, 150, "7  Dados e rastreabilidade no disco", "SQLite + arquivos: biblioteca, memória, conversas, pesos locais, resultados e registro de uso.\nEspelho de saída para o Obsidian. Os dados de trabalho ficam em data/, fora do Git.", "data")
    d.arrow([(1285, 585), (1385, 585)], "API", (1323, 551), COLORS["cloud"][1])
    d.card(1385, 350, 345, 485, "8  Google / Gemini", "Gateway de provedores faz a ligação.\n\nResposta ao chat e busca web opcional.\n\nAuxiliares: reformular busca, fichas, revisão de memória e figuras solicitadas.\n\nPDFs selecionados podem seguir ao serviço de arquivos.", "cloud", "llm/providers/gemini.py", size=20)
    d.card(1385, 890, 345, 310, "OpenAI (opcional)", "Um adaptador local permite integrar esse provedor.\n\nO chat web atual seleciona modelos Google; não há troca automática entre provedores.", "data", "Integração local disponível", size=20)
    d.paragraph(65, 1268, "Leitura do mapa: os setores locais são módulos do mesmo projeto. As tarefas científicas longas usam subprocessos.\nMiniLM e o reordenador executam inferência local; os autoencoders científicos são treinados em um fluxo separado.", 1640, 21)
    d.save()


def question():
    d = Map(2, "02-caminho-da-pergunta", "O caminho de uma pergunta", "A rota automática escolhe o contexto e a profundidade; o pesquisador pode ajustar as opções", 1550)
    rows = [(235, 155), (450, 170), (680, 190), (930, 180), (1170, 200)]
    titles = ["1  Entrada e roteamento local", "2  Montagem do contexto", "3  Estimativa e confirmação", "4  Gateway → Gemini → resposta", "5  Conferência e persistência"]
    bodies = ["Pergunta + histórico recente + opções.\nRegras e similaridade escolhem skill, modelo e leitura.",
              "Documentos e memória relevantes, referências da skill e resultados científicos, quando cabem na tarefa.",
              "Estima o custo da leitura escolhida.\nNas leituras acima de trechos, verifica os limites e a confirmação necessária.",
              "Envia regras e contexto ao modelo escolhido. A resposta chega aos poucos à interface; uso é registrado.",
              "Confere referências, trechos citados e números de resultados. Guarda a conversa; quando elegível, memória e trilhas de páginas."]
    for i, ((y, h), title, body) in enumerate(zip(rows, titles, bodies)):
        d.card(55, y, 625, h, title, body, "cloud" if i == 3 else "local")
        if i < 4:
            d.arrow([(365, y + h), (365, rows[i + 1][0])])
    d.card(790, 235, 955, 155, "A escolha de modelo também é local", "Roteador: regras + exemplos comparados com MiniLM, sem chamada paga.\nDefine intenção, skill, alias de modelo e profundidade. Histórico ajuda em continuações.", "ml", "routing.py · routing_examples.py")
    d.arrow([(680, 310), (790, 310)])
    d.card(790, 450, 955, 235, "Escada de leitura", "0  Sem biblioteca: conversa, tarefas e resultados.\n1  Trechos: consulta textual comum.\n2  Páginas completas: seleção local, geralmente até 10 páginas.\n3  Documento citado ou fixado; documentos grandes podem cair para páginas.\n4  Leitura ampla: somente por escolha explícita na interface.", "local", size=20)
    d.arrow([(680, 535), (790, 535)])
    d.card(790, 740, 955, 200, "Como os limites estão aplicados no código", "Acima de 30 mil tokens estimados: confirmação para leitura ampliada.\nApós 300 mil tokens no dia: toda leitura acima dos trechos pede confirmação.\nA reformulação paga da busca acontece antes dessa verificação.", "cloud", "interfaces/web/app.py · limites preservados")
    d.arrow([(680, 780), (790, 780)])
    d.card(790, 995, 955, 190, "Duas condições que mudam o percurso", "Busca web habilitada mantém a biblioteca em trechos.\nUma resposta automática sem citações pode provocar uma nova tentativa com páginas, dentro do orçamento restante e do limite diário.", "local", "agent.py · interfaces/web/app.py")
    d.arrow([(680, 1020), (735, 1020), (735, 1065), (790, 1065)], dashed=True)
    d.card(790, 1225, 955, 145, "Saídas e limites da conferência", "Fontes, avisos, uso e memória ficam disponíveis na interface. A conferência verifica vínculos e valores; não certifica a verdade científica da resposta.", "data")
    d.arrow([(680, 1280), (790, 1280)])
    d.paragraph(55, 1410, "A trilha de uma conversa pode reaproveitar páginas já citadas. Ela orienta a leitura, mas a resposta é gerada novamente.\nO filtro do lote 32 só decide se haverá uma revisão adicional de memória; ele não impede salvar a conversa.", 1680, 21)
    d.save()


def library():
    d = Map(3, "03-biblioteca-e-busca", "Biblioteca: entrada, busca e leitura", "A biblioteca preserva os documentos; a busca local escolhe o material que pode chegar ao modelo", 1480)
    d.area(40, 225, 1720, 385, "A · ENTRADA E INDEXAÇÃO DOS DOCUMENTOS")
    boxes = [(65, "1  Receber", "PDF, Markdown ou JSON.\nPreserva original e hash do conteúdo.", "data", "library.py"),
             (490, "2  Extrair", "Texto nativo do PDF; OCR quando necessário. Figuras e tabelas localizadas.", "local", "extraction.py · figures.py"),
             (915, "3  Preparar", "Divide texto em trechos. MiniLM gera vetores locais; catálogo reúne metadados.", "ml", "chunking.py · embeddings.py"),
             (1340, "4  Armazenar", "SQLite: documentos, trechos, busca textual, fichas e figuras. Extrações em arquivos.", "data", "catalog.sqlite3")]
    for x, title, body, kind, foot in boxes:
        d.card(x, 285, 390, 210, title, body, kind, foot)
    for x in (455, 880, 1305):
        d.arrow([(x, 380), (x + 35, 380)])
    d.paragraph(65, 530, "Auxiliares via Gemini: fichas bibliográficas e de leitura. Descrições de figuras enviam páginas como imagem somente por pedido explícito.\nOs arquivos originais e as extrações continuam locais; enviar um documento à biblioteca não equivale a enviar todo o acervo ao modelo.", 1650, 20)
    d.area(40, 640, 1720, 555, "B · CONSULTA QUANDO A BIBLIOTECA É USADA")
    d.card(65, 705, 390, 210, "5  Reformular consulta", "Gemini auxiliar usa pergunta e histórico. Se falhar, a busca segue com a própria pergunta.", "cloud", "rewrite.py")
    d.card(490, 705, 390, 210, "6  Buscar candidatos", "Busca textual (FTS) + vetores MiniLM + documento nomeado. Diversidade entre documentos.", "ml", "library.py")
    d.card(915, 705, 390, 210, "7  Reordenar páginas", "Cross-encoder local compara pergunta e trechos; até 60 candidatos. Só no modo de páginas.", "ml", "reranking.py", new=True)
    d.card(1340, 705, 390, 210, "8  Montar leitura", "Trechos, páginas ou documento, conforme a rota. Confere integridade e prepara citações.", "local", "reading.py · agent.py")
    for x in (455, 880, 1305):
        d.arrow([(x, 800), (x + 35, 800)])
    d.arrow([(810, 915), (810, 955), (1535, 955), (1535, 915)], "trechos / documento: sem reordenar", (885, 929), dashed=True)
    d.card(490, 990, 815, 165, "Cache da busca na memória RAM", "Reutiliza textos e matriz de vetores. Mudanças no SQLite invalidam o cache; o catálogo persistido continua sendo a referência.", "data", "library.py · PRAGMA data_version", new=True)
    d.arrow([(685, 990), (685, 915)])
    d.card(65, 990, 390, 165, "Pesquisa literal", "Contagem de palavras e menções também usa consulta local exata.", "local")
    d.card(1340, 990, 390, 165, "Se faltar reordenador", "Mantém a seleção anterior e informa o estado. Sem download automático.", "local", size=20)
    d.arrow([(1305, 855), (1325, 855), (1325, 1070), (1340, 1070)], dashed=True)
    d.card(55, 1240, 805, 150, "Entrega à resposta", "Apenas o contexto selecionado segue ao Gemini. PDFs enviados pelo modo de leitura podem ficar no serviço de arquivos por até 48 horas.", "cloud")
    d.card(900, 1240, 845, 150, "Modelos locais com funções diferentes", "MiniLM cria vetores para encontrar textos parecidos. O cross-encoder dá uma nova ordem aos candidatos; seu escore não é uma probabilidade.", "ml")
    d.save()


def memory():
    d = Map(4, "04-memoria-e-dados", "Memória: o que é guardado e reutilizado", "Conversas, anotações duráveis, trilhas de leitura e cache têm funções distintas", 1500)
    d.card(55, 235, 800, 170, "1  Histórico completo da conversa", "Pergunta, resposta, fontes, rota e uso são guardados após a resposta. O histórico recente volta ao contexto da pergunta seguinte.", "data", "interfaces/web/conversations.py · data/conversas/*.json")
    d.card(925, 235, 820, 170, "2  Memória de conversas e trilhas", "Trocas elegíveis recebem representação para busca. Páginas citadas e verificadas podem ser lembradas para orientar outra leitura.", "ml", "memory/store.py · data/memoria/memoria.sqlite3")
    d.arrow([(855, 315), (925, 315)])
    d.arrow([(455, 405), (455, 470)])
    d.card(55, 470, 800, 200, "3  Filtro local: precisa revisar esta mensagem?", "Reconhece preferências, correções, decisões e pedidos para lembrar. Perguntas informativas comuns dispensam uma revisão paga adicional.", "local", "memory/reviewer.py · needs_review", new=True)
    d.card(925, 470, 820, 200, "4  Revisor de memória via Gemini", "Quando indicado, propõe anotações estruturadas. Verificações locais de origem, conflito e validade condicionam a gravação.", "cloud", "memory/reviewer.py · review_exchange")
    d.arrow([(855, 565), (925, 565)], "sim", (877, 530))
    d.arrow([(455, 670), (455, 730)], "não: já salvou o histórico", (475, 687))
    d.card(55, 730, 800, 165, "Histórico continua disponível", "Dispensar a revisão não apaga a conversa e não impede o armazenamento de trocas e trilhas elegíveis. Não há novo treinamento do modelo.", "local")
    d.arrow([(1335, 670), (1335, 730)])
    d.card(925, 730, 820, 165, "5  Anotações duráveis", "Perfil, preferências, correções, fatos e decisões, com origem e versões. Comandos e correções explícitas têm precedência sobre inferências.", "data", "memory/store.py · registros separados das trocas")
    d.arrow([(1335, 895), (1335, 955)])
    d.card(925, 955, 820, 165, "6  Próxima pergunta: recuperar o que é relevante", "A busca local seleciona memórias e conversas pertinentes. O Agent inclui esse contexto na nova chamada ao modelo.", "ml", "memory/store.py · agent.py")
    d.card(55, 955, 800, 165, "Controle pelo pesquisador", "A interface oferece consulta e edição da memória. Pedidos explícitos para lembrar e fichas de leitura seguem seus próprios caminhos de registro.", "ui", "interfaces/web/app.py")
    d.arrow([(855, 1035), (925, 1035)], dashed=True)
    d.area(40, 1170, 1720, 225, "OUTRAS FORMAS DE PERSISTÊNCIA · FORA DA MEMÓRIA DURÁVEL")
    d.card(65, 1225, 515, 155, "Obsidian", "Espelho de mão única: notas e ligações. Não volta como fonte de instruções.", "data", "data/obsidian/", size=19)
    d.card(625, 1225, 515, 155, "Registros de uso", "Modelo e consumo por chamada; controle dos arquivos enviados ao Google.", "data", "data/uso/", size=19)
    d.card(1185, 1225, 545, 155, "Cache e pesos locais", "Aceleram a busca e a inferência. Não são preferências nem fatos do usuário.", "ml", "RAM + data/models/", size=19)
    d.save()


def science():
    d = Map(5, "05-ciencia-e-autoencoders", "Ciência: cálculo, treino e resultados", "O núcleo geral de engenharia e a especialização em inversores permanecem separados", 1500)
    d.card(55, 235, 1690, 125, "1  O pesquisador inicia uma operação", "Aba Ciência ou CLI → comandos definidos no projeto. Preparação, treino e avaliação GPVS usam subprocessos; o chat não dispara código livre.", "ui", "interfaces/web/gpvs_runs.py · cli.py", size=21)
    d.area(40, 425, 580, 615, "NÚCLEO GERAL · ENGENHARIA", "science")
    d.area(660, 425, 1100, 615, "ESPECIALIZAÇÃO · PESQUISA DE INVERSORES / GPVS", "science")
    d.arrow([(335, 360), (335, 485)])
    d.arrow([(1210, 360), (1210, 468), (935, 468), (935, 485)])
    d.card(65, 485, 530, 235, "2  Modelos de confiabilidade", "Confiabilidade, disponibilidade e manutenção: exponencial, Weibull e sistemas em série ou paralelo.\nCenários e premissas são explícitos.", "science", "science/ram.py")
    d.card(65, 770, 530, 225, "3  Risco e componentes", "FMECA: modos de falha e prioridade de risco.\nTaxas de falha e cenários de reparo têm análise separada das notas de risco.", "science", "science/fmeca.py · components.py")
    d.arrow([(330, 720), (330, 770)])
    d.card(685, 485, 500, 215, "4  Dados e protocolo", "Ensaios GPVS, divisão temporal, normalização e construção de sequências. Separação entre treino, calibração e teste.", "science", "detection/gpvs.py · protocol.py")
    d.card(1235, 485, 500, 215, "5  Autoencoders", "Denso e AE-LSTM aprendem a reconstruir sinais saudáveis. Erro de reconstrução alimenta a detecção de anomalias.", "ml", "detection/models.py · training.py")
    d.arrow([(1185, 590), (1235, 590)])
    d.card(1235, 765, 500, 230, "6  Limiar e avaliação", "Calibração define o limiar. Testes medem detecção, falsos alarmes e atraso.\nConfigurações e consultas ao teste ficam registradas.", "science", "threshold.py · evaluation.py · registry.py")
    d.arrow([(1485, 700), (1485, 765)])
    d.card(685, 765, 500, 230, "7  Reanálise do início", "Detector de mudança nos sinais localiza o início observado da falha. A reanálise é secundária e preserva a avaliação oficial.", "science", "detection/onset.py · reanalysis.py")
    d.arrow([(1235, 885), (1185, 885)])
    d.arrow([(330, 995), (330, 1095)])
    d.arrow([(1485, 995), (1485, 1060), (455, 1060), (455, 1095)])
    d.arrow([(935, 995), (935, 1060)])
    d.card(55, 1095, 800, 165, "8  Resultados e rastreabilidade", "Arquivos de configuração, modelos treinados, escores, métricas e histórico de execuções. Novas rodadas preservam as anteriores.", "data", "data/resultados/ · data/gpvs/")
    d.card(925, 1095, 820, 165, "9  Interface e contexto científico do chat", "Aba Ciência exibe gráficos e tabelas. Um resumo estruturado dos resultados fornece números, fontes e notas para as respostas.", "science", "science/digest.py · interfaces/web/science.py")
    d.arrow([(855, 1175), (925, 1175)])
    d.paragraph(55, 1310, "O Gemini explica resultados já calculados pelo serviço científico. As referências numéricas são conferidas na resposta.\nTreinar autoencoders com sinais de ensaio é diferente de usar MiniLM na busca e de guardar memórias das conversas.\nNenhum dos três novos blocos do lote 32 alterou o método de treinamento ou os resultados científicos de referência.", 1660, 21)
    d.save()


if __name__ == "__main__":
    overview()
    question()
    library()
    memory()
    science()
