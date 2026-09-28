# Validação do lote 09

Verificação local em **26/09/2026**, Windows/Python 3.12, `google-genai` 1.75.0.
Nenhum commit, push ou PR; pela decisão do pesquisador, os commits ficam para a v0 concluída.

## Resultado

| Verificação | Resultado |
|---|---|
| Lista de modelos da chave (sem cobrança) | 44 modelos com `generateContent`; escolhidos `gemini-3.8-flash` e `gemini-3.5-flash-lite`. |
| `.env` | Duas linhas de modelo preenchidas; chave não exibida. Cópia anterior em `tmp/lote-09-env-antes.bak`, fora do Git. |
| `.venv/Scripts/python.exe -m pytest -q` | **223 testes passaram** (220 anteriores + 3 novos). |
| `.venv/Scripts/python.exe -m ruff check .` | Sem problemas. |
| Testes sem rede | Os testes não gravaram em `data/uso/`. |

## Chamadas reais

| Modelo | Skill | Entrada | Saída | Raciocínio | Total |
|---|---|---:|---:|---:|---:|
| `gemini-3.5-flash-lite` | nenhuma | 391 | 58 | — | 449 |
| `gemini-3.8-flash` | `pesquisa-inversores` | 3.173 | 262 | 541 | 3.976 |

A primeira resposta distinguiu corretamente taxa de falha e probabilidade de falha.
A segunda reproduziu as decisões do lote 07: IGBT 8,9×10⁻⁶/h (Baschel et al., 2018),
contatores CA/CC como um item com 8,31×10⁻⁶/h (Gallardo-Saavedra via Sarquis Filho,
Tab. III), bases de 4.015 e 8.760 h/ano, e a ressalva de reconferência nos PDFs.
O registro `data/uso/chamadas.jsonl` guardou só data, modelo e tokens.

## Ajustes após a revisão do pesquisador

- **Próximo passo:** a instrução geral em `src/aliado/agent.py` deixou de exigir a
  pergunta ao fim de toda resposta. O agente consulta o usuário quando ele pede
  planejamento ou quando uma decisão dele é necessária, e usa o próprio julgamento
  nos demais casos. As mensagens fixas de "evidência insuficiente" continuam
  perguntando, porque exigem uma indicação do usuário.
- **Trava Git:** `.claude/hooks/check_git_command.py` libera, sem análise, comandos
  que não mencionam `git`, para eliminar os bloqueios de leituras com sintaxe complexa.
  Comandos com `git` continuam analisados e bloqueados na dúvida. Por decisão do
  pesquisador, a trava será retirada se voltar a causar atrasos.
- Resultado: **227 testes passaram** (4 novos casos da trava) e Ruff sem problemas.

## Observações para revisão

- As duas respostas terminam com "Qual será o próximo passo?", vindo das instruções
  gerais aprovadas. Em perguntas curtas, pode soar repetitivo.
- As instruções da skill de pesquisa somam cerca de 3 mil tokens de entrada por
  pergunta; a memória e a busca na web aumentarão esse contexto.
- A trava Git revisada no lote 08 bloqueou um comando de leitura sem Git, por não
  conseguir analisar sua sintaxe. O bloqueio é conservador e foi contornado com as
  ferramentas de leitura.
