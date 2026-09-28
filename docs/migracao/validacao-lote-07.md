# Validação do lote 07

Verificação local em **25–26/09/2026**, Windows/Python 3.12. Implementação autorizada
na conversa; nenhum commit, push, PR ou publicação feito pelo assistente.

## Resultado

| Verificação | Resultado |
|---|---|
| `.venv/Scripts/python.exe -m pytest -q` | **174 testes passaram** (160 anteriores + 14 novos). |
| `.venv/Scripts/python.exe -m ruff check .` | Sem problemas. |
| Conversão `time_base` | 4.015 e 8.760 h/ano comparadas com 1−exp(−λ·h·t); recusa de 10 configurações inválidas; saída sem `time_base` inalterada. |
| Isolamento das taxas | Os quatro λ aparecem só no contexto de `pesquisa-inversores`, nunca no núcleo, em `engenharia` ou em `confiabilidade`. |
| Oito cenários | Executados pelo CLI em `data/resultados/lote-07/`; dois valores conferidos à mão. |
| Skills copiadas | Quatro arquivos em `.claude/skills/` com SHA-256 idêntico ao de `.agents/skills/`. |
| Hook Git | Teste direto: push, reset --hard, clean e push --force saem com código 2; status, ls e pytest saem com 0. Ao vivo, na sessão, um comando inofensivo com o texto "git push" foi bloqueado. |

## Resultados dos cenários

Probabilidade de falha F(t), com o componente analisado isoladamente e taxa constante.

| Grupo | λ (1/h) | Base | F(1 ano) | F(10 anos) | F(20 anos) |
|---|---:|---|---:|---:|---:|
| CCB | 63,7e-6 | operação | 0,2257 | 0,9225 | 0,9940 |
| CCB | 63,7e-6 | calendário | 0,4277 | 0,9962 | 0,99999 |
| Contatores CA/CC | 8,31e-6 | operação | 0,0328 | 0,2837 | 0,4869 |
| Contatores CA/CC | 8,31e-6 | calendário | 0,0702 | 0,5171 | 0,7668 |
| IGBT | 8,9e-6 | operação | 0,0351 | 0,3005 | 0,5106 |
| IGBT | 8,9e-6 | calendário | 0,0750 | 0,5414 | 0,7897 |
| Ventiladores | 26,7e-6 | operação | 0,1017 | 0,6577 | 0,8828 |
| Ventiladores | 26,7e-6 | calendário | 0,2086 | 0,9036 | 0,9907 |

Conferência à mão: CCB em operação, F(1) = 1−exp(−63,7e-6·4015) = 0,22567; IGBT em
calendário, R(20) = exp(−8,9e-6·8760·20) = 0,21029. Os dois conferem com o serviço.

## Limites

As taxas vêm do registro de 13/09 e não foram reconferidas nos artigos neste lote;
duas são valores secundários, via Sarquis Filho et al. (2020). Não se sabe se as
taxas bibliográficas se referem a horas de operação ou de calendário, por isso há
duas bases. A taxa constante ignora mortalidade infantil e desgaste. Os valores
elevados em 20 anos, como os da CCB, decorrem dessas hipóteses e não são previsões
de campo. Não há topologia de sistema, reparo, disponibilidade ou NPR revisado.

O hook bloqueia na dúvida: um comando que apenas mencione um padrão bloqueado
também é barrado. Nesses casos, o assistente usa as ferramentas de edição de arquivos.
O hook restringe só o assistente. Nenhum wheel novo foi gerado neste lote.

## Preservação

Os manifestos anteriores e o registro de 14/09 em `skills-desenvolvimento.json`
não foram alterados; a instalação para o Claude Code consta do
[manifesto do lote 07](lote-07.json). A referência de 22/09 e o registro de 13/09
continuam intactos. O README e o JSON privados do lote 05 foram copiados para
`tmp/lote-07/baseline-memory-review/` antes da atualização. Nenhuma memória foi
ativada, e o repositório de origem não foi acessado.
