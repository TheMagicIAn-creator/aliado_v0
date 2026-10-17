"""Frases de exemplo do roteador local (lote 31): o que cada tipo de mensagem costuma dizer.

A mensagem do usuário é comparada com estas frases pelo modelo local de busca. Trocar ou acrescentar
frases muda a rota sem mexer no código; `tests/test_routing.py` confere as rotas de mensagens reais."""

# O que a mensagem pede.
INTENTS: dict[str, tuple[str, ...]] = {
    "conversa": (
        "Oi, tudo bem?", "Bom dia, Aliado.", "Obrigado, era isso.", "Quais foram nossas últimas conversas?",
        "Você lembra da nossa conversa de mais cedo?", "O que eu te disse ontem sobre isso?",
        "O que você sabe sobre mim?", "Como você funciona?", "Pode repetir de forma mais curta?",
        "Reescreva a resposta anterior em um parágrafo.", "Traduza a sua última resposta para o inglês.",
        "Não entendi, explique de outro jeito.", "Qual é o seu modelo?", "Me ajude a organizar o meu dia.",
        # Lote 33: conversa solta das mensagens reais.
        "Fale comigo, meu jovem!", "Cara, como você sabe tanto?", "Haha, você está esperto hoje.",
        "Muito obrigado pela ajuda de hoje.",
    ),
    "tarefa": (
        "Escreva um código em Python para ler um arquivo.", "Corrija este erro do meu programa.",
        "Faça uma busca na web sobre este assunto.", "Escreva um e-mail para o meu orientador.",
        "Monte uma planilha com estes dados.", "Coloque a seção de código com ícone de copiar.",
        "Me fale sobre a última notícia pública dessa empresa.", "Você reconhece este repositório do GitHub?",
        "Traduza este texto para o inglês.", "Quero só conversar sobre a vida.", "Meu trabalho está corrido esta semana.",
        "Estou morando fora da cidade onde eu queria estar.", "Sugira um roteiro de estudos para a semana.",
    ),
    "fato": (
        "Qual é a taxa de falha dos ventiladores segundo o artigo?", "Qual o tempo de reparo de um transformador?",
        "Em que ano o FMEA surgiu?", "Qual intervalo de manutenção foi obtido para o rolamento?",
        "Quantas horas de operação por ano o estudo adota?", "Qual o valor do MTBF do inversor?",
        "What repair time does the standard give for the transformer?", "Qual a confiabilidade estimada do regulador?",
        "Qual é o limite usado para o NPR?", "Quem propôs esse método?",
    ),
    "sintese": (
        "Com citação direta, me diga, com base na literatura, o que são autoencoders.",
        "Trazendo de ao menos duas fontes, qual é a definição de manutenção centrada na confiabilidade?",
        "Compare o que os autores dizem sobre a curva da banheira.", "Explique como funciona o rastreamento do ponto de máxima potência.",
        "Como se calcula a confiabilidade de um sistema em série e em paralelo?", "Resuma o que a literatura diz sobre falhas em inversores.",
        "Quais são os princípios da manutenção centrada na confiabilidade?", "Discuta as vantagens e os limites do FMEA.",
        "What causes random failures in the bathtub curve?", "Faça uma revisão do que os documentos dizem sobre detecção de anomalias.",
        "Defina disponibilidade e mantenabilidade com base nas fontes.",
    ),
    "visual": (
        "O que mostra a Figura 2 do artigo?", "Quais colunas tem a tabela de taxas de falha?",
        "Como é a árvore de falhas do alarme contra fogo?", "Descreva o diagrama de blocos de confiabilidade.",
        "Quais variáveis têm a maior correlação na matriz de correlação?", "Which failure modes have the highest RPN in the chart?",
        "Qual é a equação da disponibilidade no texto?", "O que aparece no gráfico de Pareto?",
        "Transcreva o quadro de severidade.", "Como é a curva de custo de manutenção na figura?",
    ),
    "resultados": (
        "Qual foi o F1 do autoencoder LSTM nos ensaios?", "Quantos alarmes falsos o detector denso deu?",
        "Como ficou a comparação entre o Denso e o LSTM no GPVS?", "Qual limiar foi fixado para os detectores?",
        "Quais falhas do GPVS não foram detectadas?", "Mostre os resultados da avaliação oficial.",
        "Qual é o NPR do capacitor na nossa FMECA?", "Qual a disponibilidade do inversor nos nossos cenários?",
        "Quando cada falha começa a aparecer nos nossos dados?", "Resuma os resultados do meu experimento.",
        # Lote 33: resultados sem a palavra "resultados".
        "Qual foi a especificidade do autoencoder denso?", "Quantos ensaios com falha cada modelo detectou?",
        "Qual o atraso mediano até o alarme?", "Qual componente ficou mais crítico na nossa análise?",
        "O que eu já consegui na pesquisa até agora?",
    ),
    "metodo": (
        "Resuma o protocolo de partição e calibração dos detectores.", "Quais taxas de falha foram decididas para a FMECA?",
        "Por que o limiar é o percentil 99 dos dados saudáveis?", "Qual foi a decisão sobre a separação entre treino e teste?",
        "Como devo justificar a escolha do autoencoder na dissertação?", "Revise a metodologia do meu experimento.",
        "Quais hipóteses a pesquisa assume?", "O que as diretrizes aprovadas dizem sobre o conjunto de teste?",
        "Como rodo de novo o pipeline do GPVS?", "Que critério usamos para comparar os modelos?",
    ),
}

# A especialização que combina com a mensagem; "nenhuma" é a conversa geral.
SKILLS: dict[str, tuple[str, ...]] = {
    "pesquisa-inversores": (
        "Detecção de falhas em inversores fotovoltaicos com autoencoders.", "Resultados do GPVS com os modelos Denso e LSTM.",
        "Literatura do mestrado sobre confiabilidade de sistemas fotovoltaicos.", "FMECA do inversor e taxas de falha dos componentes.",
        "Protocolo de calibração, limiar e avaliação dos detectores.", "O que os artigos dizem sobre falhas em usinas solares?",
        "Definição de manutenção centrada na confiabilidade com base na literatura.", "Fault detection in photovoltaic inverters.",
    ),
    "confiabilidade": (
        "Converter uma taxa de falha por hora em probabilidade em 20 anos.", "Calcular a disponibilidade com MTBF e MTTR.",
        "Montar um cenário de confiabilidade com Weibull.", "Qual a confiabilidade de três componentes em série?",
        "Interpretar o resultado do cálculo de mantenabilidade.", "Calcular o MTBF a partir da taxa de falha.",
    ),
    "engenharia": (
        "Escreva um script em Python para ler estes arquivos.", "Como estruturar este projeto de software?",
        "Revise este código e aponte os erros.", "Preciso automatizar uma planilha.", "Qual arquitetura usar para esta aplicação?",
        "Projete um circuito de medição para esta bancada.", "Me ajude a depurar este erro de programação.",
    ),
    "nenhuma": (
        "Oi, tudo bem?", "Me conte uma curiosidade.", "Obrigado pela ajuda.", "Quais foram nossas últimas conversas?",
        "Escreva um e-mail curto para o meu orientador.", "Que dia é hoje?",
    ),
}
