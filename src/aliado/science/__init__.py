"""Ciência geral do AL-IAdo: métodos que valem para qualquer base de dados, sem parâmetros físicos nem execução
automática (lote 50). Cada pasta tem uma etapa e só ela:

- `deteccao/`: a detecção de falhas por reconstrução, da partição dos dados ao alarme e às métricas;
- `confiabilidade/`: os cenários de confiabilidade, mantenabilidade e disponibilidade;
- `fmeca/`: a tabela da FMECA, o NPR e a leitura pelas taxas;
- `componentes/`: os reparos e a disponibilidade por componente;
- `resumo_citavel/`: os números como na tela e o texto dos blocos citáveis do chat.

Nada é importado aqui: cada uso importa o arquivo da pasta, e `import aliado.science` não carrega numpy nem PyTorch.
"""
