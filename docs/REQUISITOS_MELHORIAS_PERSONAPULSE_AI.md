# PersonaPulse AI - Requisitos de melhorias

## Objetivo

Evoluir o PersonaPulse AI para uma plataforma de inteligencia comercial, campanhas e dados de clientes mais eficiente que ferramentas focadas apenas em gestao de redes sociais.

O posicionamento recomendado e:

```text
mLabs ajuda a agendar, aprovar e medir posts.
PersonaPulse AI ajuda a decidir para quem vender, o que falar, por qual canal agir e como medir retorno real.
```

## Referencia competitiva

Ferramentas como mLabs sao fortes em:

- agendamento de publicacoes;
- calendario editorial;
- relatorios de redes sociais;
- fluxo de criacao e aprovacao de posts;
- colaboracao entre equipe e cliente;
- analise de concorrentes;
- inbox/chat social;
- integracao com criacao visual e IA para conteudo.

O PersonaPulse AI deve competir por outro eixo: decisao comercial baseada em dados proprios, CRM, Ads, Power BI, segmentacao e recomendacoes acionaveis.

## Principios do produto

- Nao exibir funcionalidade incompleta como se estivesse pronta.
- Priorizar dado real, fonte declarada e auditoria.
- Transformar dados em acao, nao apenas em graficos.
- Reduzir trabalho operacional do gestor de marketing.
- Explicar recomendacoes em linguagem executiva.
- Manter a interface simples, rapida e confiavel.

## Fora de escopo atual

- Precificador automatico de produtos.
- Buscape, DataForSEO e Google Custom Search JSON API para ticket medio.
- Agendamento direto de posts em redes sociais sem APIs oficiais.
- Automacoes que publiquem campanhas sem aprovacao explicita do usuario.

## Prioridade 1 - Base executiva e confiabilidade

### RQ-001 Dashboard executivo aprimorado

Criar uma visao executiva com indicadores de negocio, nao apenas dados operacionais.

Requisitos:

- mostrar receita atribuida;
- mostrar gasto de midia;
- mostrar ROI;
- mostrar conversoes;
- mostrar leads;
- mostrar ticket medio vindo de pedidos reais do CRM;
- mostrar clientes analisados;
- mostrar campanhas ativas;
- comparar desempenho por canal;
- destacar alertas quando uma fonte estiver sem dados.

Criterio de aceite:

- o usuario entende em menos de 30 segundos se as campanhas estao gerando retorno;
- nenhum card deve exibir dado simulado como se fosse dado real.

### RQ-002 Estado real das fontes de dados

Exibir claramente quais fontes estao conectadas, pendentes, simuladas ou com erro.

Requisitos:

- status por fonte: ativo, pendente, erro, planejado;
- data da ultima sincronizacao;
- quantidade de registros importados;
- erro resumido quando a sincronizacao falhar;
- botao de nova tentativa quando aplicavel.

Criterio de aceite:

- o usuario sabe exatamente se esta olhando dados reais ou dados demo.

### RQ-003 Remocao de funcionalidades incompletas da experiencia principal

Revisar a interface e esconder recursos que ainda nao entregam valor real.

Requisitos:

- remover abas sem fluxo completo;
- trocar botoes falsos por estados "planejado" apenas em area tecnica ou roadmap;
- manter logs e docs sobre recursos removidos quando necessario.

Criterio de aceite:

- a interface nao deve prometer uma acao que nao executa.

## Prioridade 2 - Campanhas como fluxo de trabalho

### RQ-004 Pipeline de campanhas

Transformar campanhas em objetos com ciclo de vida.

Estados:

- rascunho;
- em revisao;
- aprovada;
- ativa;
- pausada;
- finalizada;
- arquivada.

Requisitos:

- cada campanha deve ter publico, canal, objetivo, mensagem e status;
- historico de alteracoes;
- data de inicio e fim;
- responsavel;
- resultado consolidado.

Criterio de aceite:

- o usuario consegue acompanhar campanhas do planejamento ao resultado.

### RQ-005 Calendario de campanhas

Criar calendario comercial multicanal.

Requisitos:

- visao mensal e semanal;
- campanhas por data;
- filtro por canal;
- filtro por status;
- alertas de campanha sem aprovacao;
- destaque de datas comerciais.

Criterio de aceite:

- o usuario consegue planejar o mes de campanhas dentro do PersonaPulse.

### RQ-006 Aprovacao de campanhas

Criar fluxo simples de aprovacao.

Requisitos:

- enviar campanha para revisao;
- aprovar;
- solicitar ajuste;
- comentar;
- registrar aprovador e data;
- bloquear ativacao sem aprovacao quando configurado.

Criterio de aceite:

- agencia, gestor e cliente conseguem colaborar sem perder historico.

## Prioridade 3 - Recomendacoes acionaveis com IA

### RQ-007 Central de recomendacoes executivas

Transformar recomendacoes em acoes priorizadas.

Tipos iniciais:

- reativacao de clientes;
- pausa de campanha ruim;
- ampliacao de campanha boa;
- criacao de campanha para segmento com alta intencao;
- melhoria de copy;
- ajuste de canal;
- alerta de queda de conversao.

Requisitos:

- cada recomendacao deve ter prioridade;
- impacto esperado;
- motivo da recomendacao;
- dados usados;
- botao para gerar campanha a partir da recomendacao;
- status: nova, em andamento, aplicada, ignorada.

Criterio de aceite:

- o usuario sai da tela sabendo exatamente qual acao tomar.

### RQ-008 Score de oportunidade

Criar score por cliente e por segmento.

Fatores sugeridos:

- recencia de compra;
- frequencia de compra;
- valor gasto;
- engajamento;
- canal preferido;
- origem do lead;
- resposta a campanhas;
- consentimento de marketing.

Criterio de aceite:

- clientes e segmentos aparecem ordenados por potencial de acao.

## Prioridade 4 - CRM, inbox e oportunidades

### RQ-009 Central de oportunidades

Criar uma tela comercial para leads e clientes com maior chance de conversao.

Requisitos:

- lista de oportunidades;
- score;
- produto/interesse associado;
- ultima interacao;
- canal recomendado;
- proxima acao sugerida;
- status da oportunidade.

Criterio de aceite:

- o usuario consegue priorizar atendimento e campanha sem abrir planilhas.

### RQ-010 Historico do cliente

Exibir linha do tempo do cliente.

Eventos:

- compra;
- lead;
- clique;
- abertura;
- campanha recebida;
- interacao CRM;
- alteracao de consentimento.

Criterio de aceite:

- ao abrir um cliente, o usuario entende contexto, valor e proxima acao.

## Prioridade 5 - Relatorios e Power BI

### RQ-011 Relatorio executivo automatico

Criar exportacao de resumo semanal/mensal.

Conteudo:

- principais indicadores;
- campanhas vencedoras;
- campanhas ruins;
- segmentos de maior potencial;
- recomendacoes da IA;
- proximas acoes.

Formatos:

- PDF;
- JSON para Power BI;
- CSV quando aplicavel.

Criterio de aceite:

- o usuario consegue gerar um relatorio de reuniao em poucos cliques.

### RQ-012 Endpoints Power BI mais completos

Evoluir endpoints atuais.

Requisitos:

- endpoint de segmentos;
- endpoint de recomendacoes;
- endpoint de oportunidades;
- endpoint de campanhas com metricas;
- schemas estaveis mesmo sem dados.

Criterio de aceite:

- Power BI nao quebra quando uma fonte esta vazia.

## Prioridade 6 - Performance e confiabilidade tecnica

### RQ-013 Otimizacao do carregamento inicial

Reduzir tempo de abertura do app.

Requisitos:

- carregar dashboard primeiro;
- buscar dados secundarios sob demanda;
- evitar chamadas duplicadas;
- cache local controlado;
- estados de loading e erro por painel.

Criterio de aceite:

- primeira tela utilizavel em ate 2 segundos em ambiente VPS.

### RQ-014 Separacao de frontend em modulos

O arquivo `index.html` concentra HTML, CSS e JavaScript. Separar gradualmente.

Estrutura sugerida:

```text
static/personapulse/
  index.html
  styles.css
  app.js
  modules/
    dashboard.js
    customers.js
    campaigns.js
    integrations.js
    recommendations.js
```

Criterio de aceite:

- novas telas podem ser alteradas sem mexer em um arquivo gigante.

### RQ-015 Observabilidade basica

Criar diagnostico operacional simples.

Requisitos:

- endpoint `/health` com banco e versao;
- endpoint `/api/system/status` com fontes, banco e ultima sync;
- logs de erro sem expor secrets;
- auditoria de importacoes e sincronizacoes.

Criterio de aceite:

- problema de ambiente pode ser diagnosticado em menos de 5 minutos.

## Roadmap recomendado

### Sprint 1 - Produto confiavel

- RQ-001 Dashboard executivo aprimorado.
- RQ-002 Estado real das fontes.
- RQ-003 Remover promessas incompletas.
- RQ-015 Observabilidade basica.

Status inicial:

- primeira entrega implementa novos KPIs executivos, painel de saude das fontes e endpoint `/api/system/status`;
- proximas entregas devem aprofundar alertas, loading por painel e estados vazios por modulo.

### Sprint 2 - Campanhas de verdade

- RQ-004 Pipeline de campanhas.
- RQ-005 Calendario de campanhas.
- RQ-006 Aprovacao.

### Sprint 3 - IA acionavel

- RQ-007 Central de recomendacoes.
- RQ-008 Score de oportunidade.
- RQ-009 Central de oportunidades.

### Sprint 4 - Relatorios e escala

- RQ-010 Historico do cliente.
- RQ-011 Relatorio executivo automatico.
- RQ-012 Power BI ampliado.
- RQ-013 Otimizacao de carregamento.
- RQ-014 Modularizacao do frontend.

## Metricas de sucesso

- Tempo ate primeira tela util.
- Quantidade de campanhas criadas por semana.
- Percentual de recomendacoes aplicadas.
- Receita atribuida a campanhas.
- ROI por canal.
- Tempo economizado em relatorios.
- Numero de fontes conectadas com dados reais.

## Proxima decisao

Comecar pela Sprint 1, com foco em tornar o PersonaPulse AI mais confiavel, rapido e executivo antes de adicionar novas superficies grandes como calendario e inbox.
