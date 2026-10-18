"""O que o mestrado acrescenta ao roteador local (lote 36): as frases de exemplo que nomeiam o domínio e o
nome da base como termo de resultados. O núcleo junta isto às frases dele na primeira mensagem."""

ROUTING = {
    # Somadas às frases do mesmo tipo em `aliado.routing_examples.INTENTS`.
    "intents": {
        "fato": ("Qual o valor do MTBF do inversor?",),
        "sintese": ("Resuma o que a literatura diz sobre falhas em inversores.",),
        "resultados": ("Como ficou a comparação entre o Denso e o LSTM no GPVS?", "Quais falhas do GPVS não foram detectadas?",
                       "Qual a disponibilidade do inversor nos nossos cenários?"),
        "metodo": ("Como rodo de novo o pipeline do GPVS?",),
    },
    # A skill do mestrado, ao lado das do núcleo em `aliado.routing_examples.SKILLS`.
    "skills": {
        "pesquisa-inversores": (
            "Detecção de falhas em inversores fotovoltaicos com autoencoders.", "Resultados do GPVS com os modelos Denso e LSTM.",
            "Literatura do mestrado sobre confiabilidade de sistemas fotovoltaicos.", "FMECA do inversor e taxas de falha dos componentes.",
            "Protocolo de calibração, limiar e avaliação dos detectores.", "O que os artigos dizem sobre falhas em usinas solares?",
            "Definição de manutenção centrada na confiabilidade com base na literatura.", "Fault detection in photovoltaic inverters.",
        ),
    },
    # Palavras que, sozinhas, levam a mensagem aos resultados da pesquisa (sem acento, em minúsculas).
    "results_terms": ("gpvs",),
}
