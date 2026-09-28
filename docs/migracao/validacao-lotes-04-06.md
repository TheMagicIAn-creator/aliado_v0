# Validação dos lotes 04–06

Verificação local em **25/09/2026**, Windows/Python 3.12. Implementação autorizada
na conversa; nenhum commit, push, PR ou publicação realizado pelo assistente.

## Resultado

| Verificação | Resultado |
|---|---|
| `.venv/Scripts/python.exe -m pytest -q` | **160 testes passaram**, incluindo o encoder local preparado. |
| `.venv/Scripts/python.exe -m ruff check .` | Sem problemas. |
| `.venv/Scripts/python.exe -m pip check` | Sem conflitos de dependências. |
| Validador `skill-creator` | Skills `confiabilidade` e `pesquisa-inversores` válidas. |
| Wheel | Build concluído; 28 arquivos de código/skills conferidos byte a byte com a fonte. |
| Execução do wheel fora do checkout | Importação e preparo de pedido passaram com bloqueio de rede, subprocessos, escrita e leitura de `.env`/revisão privada. |
| OCR real e busca semântica | PDF sintético lido por Tesseract por+eng; trecho recuperado com página 1 e método OCR; catálogo íntegro. |
| Encoder real | 384 dimensões; exemplo bilíngue relacionado superou o texto sem relação; trechos longos sem truncamento silencioso. |
| Memórias | 30 hashes conferidos; 16 decisões existentes aprovadas; 3 refinamentos propostos; 0 memórias ativas. |

## O que mudou

**Lote 04:** `.env` privado preserva byte a byte a configuração fornecida antes
no exemplo. O exemplo público foi sanitizado. Os adapters rejeitam texto vazio,
JSON `null` e valores estruturados que não sejam objetos. Há biblioteca local
versionada, extração PDF/MD/JSON, OCR, encoder fixado, SQLite/FTS5, busca híbrida,
verificação de integridade e integração opcional com o agente/CLI.

**Lote 05:** o inventário privado recebeu uma revisão semântica derivada, em
Markdown/JSON. Os originais e a revisão anterior permanecem preservados.
As novas propostas refinam grandezas/unidades, evidência de correções e autoria
de registros automáticos. Não foram ativadas nem incluídas em RAG ou treinamento.

**Lote 06:** modelos gerais exponencial/Weibull, série/paralelo independentes,
mantenabilidade e disponibilidade inerente, com parâmetros/fontes/hipóteses
explícitos; exportação JSON/CSV/Markdown/PNG em pasta nova; skill geral reutilizada
pela pesquisa. Testes cobrem resultados analíticos, limites e recusa de sobrescrita.

O README, a arquitetura, as specs e o guia científico refletem essas capacidades.
Manifestos anteriores e o registro histórico de 13/09 permanecem intactos.
O HEAD e o estado limpo da origem conferem com o baseline da retomada.

## Evidências e limitações

O [manifesto](lotes-04-06.json) registra arquivos e hashes desta entrega. Evidências
auxiliares ficam em `tmp/lotes-04-06/`: baseline, teste dos componentes reais,
verificação do wheel e exportação científica sintética. Instalação local e hashes
do encoder/OCR ficam em `tmp/lote-04/setup/`; binários/modelos ficam em `data/`.
São arquivos ignorados pelo Git, não dependências distribuídas no wheel.

O instalador Windows de OCR não concluiu; os arquivos de execução foram extraídos
para a pasta local e o executável/idiomas foram verificados. Não é necessário
registrar um serviço ou alterar o PATH do sistema.

Não houve consulta paga aos provedores, teste de qualidade científica de respostas,
ingestão de literatura real ou execução do experimento do mestrado. As chaves
estão configuradas localmente, mas os identificadores reais dos modelos ainda
precisam ser preenchidos pelo pesquisador antes da primeira consulta à API.

Testes de citações verificam os IDs recuperados; não comprovam fidelidade semântica
do texto gerado. OCR, fórmulas e tabelas exigem conferência. Busca exaustiva e
heurísticas de recuperação precisam ser avaliadas no acervo escolhido. Bibliotecas
separadas por diretório não substituem autenticação multiusuário.

## Participação seguinte

Revisar as três propostas em `data/memory-review/lote-05/README.md`; escolher os
modelos de API e fornecer o novo acervo quando desejar. Taxas, tempos de reparo e
topologia dos inversores serão decididos em perguntas e respostas. Interface web
com upload pelo chat e integração MCP v1 permanecem etapas posteriores.
Os commits ficam a cargo do pesquisador; um commit histórico artificial não é
pré-requisito para continuar.
