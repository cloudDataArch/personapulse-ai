# PersonaPulse Banco

Pacote versionado do banco de dados do PersonaPulse AI.

Este diretorio guarda os artefatos iniciais do banco, sem credenciais e sem URLs privadas:

- `00_personapulse_banco_schema.sql`: DDL consolidado do PostgreSQL.
- `01_personapulse_banco_seed_demo.sql`: DML com carga demonstrativa do CRM.
- `02_consultas_dba.sql`: consultas em portugues para validacao e analise.

## Base demonstrativa incluida

- Clientes: 120
- Pedidos: 307
- Eventos: 535
- Campanhas: 0

## Como usar

1. Crie ou selecione um banco PostgreSQL.
2. Execute `00_personapulse_banco_schema.sql`.
3. Execute `01_personapulse_banco_seed_demo.sql`.
4. Valide com `02_consultas_dba.sql`.

## Padrao adotado

As tabelas internas usam UUID para proteger integracoes entre CSV, CRM, Ads e Power BI.
Para leitura humana, as views `dba.*` exibem IDs sequenciais iniciando em zero, nomes de colunas em portugues e campos de contato como WhatsApp, e-mail, Instagram, TikTok, LinkedIn e Facebook.

Proxima evolucao prevista: separar DDL, DML, funcoes, procedures, indices e documentacao operacional em arquivos proprios.
