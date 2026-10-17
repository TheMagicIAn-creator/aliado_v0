# Lote 32 — busca em memória, reordenação de páginas e revisor seletivo

Autorizado pelo pesquisador em 04/10/2026, ao pedir a continuação do trabalho interrompido
("Prossigamos daqui" e "Retome"). Parte da 0.5.0 e preserva a alteração iniciada em
`src/aliado/knowledge/library.py`.

## Escopo

1. Manter os trechos e vetores normalizados em memória e refazer esse retrato quando o catálogo
   mudar, inclusive numa atualização feita por outra conexão. Preservar a busca por palavras,
   a diversidade de documentos, as referências e a conferência dos originais.
2. No degrau de páginas inteiras, reordenar até 60 candidatos com uma segunda rede local.
   Usar `cross-encoder/mmarco-mMiniLMv2-L12-H384-v1`, ONNX quantizado para CPU, revisão e
   hashes fixos. O preparo baixa somente os artefatos públicos do modelo; a inferência não usa rede.
   Documento citado, páginas fixadas e trilhas conservam sua prioridade. Se o modelo estiver
   ausente ou falhar, continuar pela busca anterior e registrar o motivo no resumo da leitura.
3. Poupar o revisor pago em cumprimentos e consultas informativas. Revisar pedidos explícitos,
   preferências, correções, decisões, informações pessoais e declarações ambíguas. A memória de
   conversas continua guardando as trocas aceitas; as fichas dos documentos continuam fornecendo
   fatos com fonte. Consultas comuns não geram uma revisão adicional só por terem citações.

## Arquivos

- `knowledge/library.py`, novo `knowledge/reranking.py` e `agent.py`: busca e seleção de páginas.
- `memory/reviewer.py` e `interfaces/web/app.py`: filtro local e integração.
- `cli.py`, `.env.example` e `README.md`: preparo e configuração do modelo local.
- Testes específicos, roteiro, changelog e novo registro em `docs/migracao/`.

## Validação e limites

- Testes sem rede: reutilização e atualização do cache, concorrência, corrupção, seleção de
  páginas, modelo ausente, hash inválido e preservação dos pedidos de memória.
- Medição local com documentos sintéticos, incluindo perguntas em português e textos em inglês.
  Relatar separadamente primeira busca, buscas seguintes e custo de reordenação. Não presumir
  ganho de qualidade ou economia de tokens sem medi-los.
- Suíte completa e Ruff; nenhum teste pago, leitura integral ou reindexação do acervo real.
- Os limites de 30 mil por leitura e aviso em 300 mil por dia não mudam. A reescrita de consultas,
  roteamento entre provedores e mudanças nas trilhas ficam fora deste lote.
- Sem commit, push, publicação ou alteração dos manifestos anteriores.
