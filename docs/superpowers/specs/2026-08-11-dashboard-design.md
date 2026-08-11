# Ciclo de feature — Dashboard (backend e frontend)

Data: 2026-08-11.
Repositórios afetados: **os dois**, `Refund-api` (agregado, contrato e
documentação canônica) e `Refund-FrontEnd` (gráficos e tela nova).

É o **Ciclo 2** do
[panorama das três telas](../../plans/2026-08-11-tres-telas-panorama.md). Sucede o
[Ciclo 1 — Diretório do time](2026-08-11-team-directory-design.md), já mesclado na
`main` dos dois repositórios.

## Motivação

**A entrada "Dashboard" está desabilitada desde que a sidebar existe**, com o selo
"em breve" ao lado de Calendário. É a segunda das três telas prometidas na
interface e não entregues.

**Não existe nenhum agregado que cruze usuários.** `GET /users/{id}/refund-stats`
é por usuário e, de propósito, não tem total entre status (UC-014). A
consequência já está registrada no [roadmap](../../roadmap.md): o card de dinheiro
da Home mostra, para o admin, o total *solicitado* em vez de aprovado + pago,
porque não há de onde tirar o número certo.

**Nada no produto responde "como isso evoluiu".** Todas as telas mostram o estado
atual — uma lista, um detalhe, contadores. Não há nenhuma leitura ao longo do
tempo, e é a pergunta que um gestor faz primeiro.

## Decisões tomadas no brainstorming

| Decisão | Escolha | Razão |
|---|---|---|
| Quem acessa | Todos, com dados no escopo do papel | Admin vê a empresa; padrão vê as próprias solicitações. Mesmo idioma de escopo do `refund_lister_controller.py:31` |
| Requisições | **Uma só**, `GET /refunds/summary` | Serve os quatro gráficos e os indicadores; quatro endpoints produziriam cascata numa tela que abre tudo de uma vez |
| Janela | `months`, default 6, máximo 12 | Um teto evita uma varredura sem limite; 6 meses cabem num eixo legível |
| Meses vazios | Preenchidos com zero | Um mês ausente abriria buraco no eixo de tempo e a linha mentiria sobre a inclinação |
| Categorias vazias | Preenchidas com zero | Mesma razão de UC-014 preencher os quatro status: a barra ausente some, e "zero" não é "não existe" |
| Barras empilhadas | **Dentro**, com mitigação | Ver "A paleta" — é o gráfico com a falha de cor conhecida |
| Cor das barras por categoria | **Uma cor só** | A categoria já está no eixo; colorir cada barra seria codificação redundante |
| Eixos | **Um por gráfico, sempre** | Dois eixos y é o erro nº 1 em gráficos; valor e contagem viram dois gráficos, nunca um |
| Fuso da agregação por mês | UTC, documentado | Converter exigiria decidir de quem é o fuso; ver "Limitação conhecida" |

Alternativas descartadas, registradas:

- **Quatro endpoints, um por gráfico.** Cascata de requisições numa tela que
  precisa de tudo ao abrir, e quatro varreduras da mesma tabela.
- **Um gráfico de valor E contagem no mesmo eixo do tempo.** Seria eixo duplo.
- **Colorir as cinco categorias.** Além de redundante, a paleta tem quatro slots e
  ciclar cores categóricas é proibido — a quinta barra repetiria a primeira.
- **Trocar a paleta pelas cores validadas.** Recusado neste ciclo: mudaria a cor
  da rosca já entregue na tela de revisão. Ver abaixo.

## A paleta: uma falha conhecida, medida e aceita

A paleta atual (`donutPalette.ts`) foi submetida ao validador de paletas. Ela
**falha 4 das 6 checagens**, nos dois modos:

| Checagem | Resultado |
|---|---|
| Faixa de luminosidade | FALHA — `#1D3557` escuro demais (0,328); `#A8DADC` e `#F1FAEE` claros demais (0,854 e 0,975) |
| Piso de croma | FALHA — as quatro leem como cinza |
| Separação para daltonismo | PASSA — pior par ΔE 10,7 (protan) |
| **Piso de visão normal** | **FALHA DURA** — `#F1FAEE` ↔ `#A8DADC` ΔE **12,9**, abaixo do piso 15 |
| Contraste contra a superfície | AVISO — `#A8DADC` 1,49:1 e `#F1FAEE` 1,04:1 no claro |

A rosca escapa hoje porque cada fatia tem leader line com rótulo e percentual, mais
contorno de 1,5px — identidade nunca depende só da cor ali.

**Onde a falha morde de verdade é nas barras empilhadas:** "aprovada" e "paga"
seriam segmentos vizinhos, sem leader line.

**Decisão: manter a paleta e mitigar.** Gap de 2px entre segmentos, legenda
sempre presente, tooltip por segmento e rótulo direto nos maiores. E fica
registrado com honestidade: **o piso de visão normal é a única checagem que
codificação secundária não desculpa.** Isto é uma falha conhecida, não resolvida.
Trocar a paleta mudaria a cor da rosca já entregue e validada na tela de revisão,
e essa troca é um ciclo próprio — anotada no roadmap.

Consequência que não é negociável: **as cores de status são as mesmas na rosca e
no empilhado.** Cor segue a entidade, nunca o ranking nem o gráfico.

## Escopo, em ordem de risco

### 1. `GET /refunds/summary` (fundação)

Uma chamada de repositório com **três** `GROUP BY`, e o escopo aplicado no
controller como em `refund_lister_controller.py:31`
(`filter_user_id = filter_user_id if role == "admin" else user_id`):

```
{ "type": "RefundSummary",
  "scope": "all" | "user",
  "months": 6,
  "by_status":   { "pending": {"count": 0, "amount_in_cents": 0}, "approved": {…},
                   "paid": {…}, "rejected": {…} },
  "by_category": { "food": {…}, "lodging": {…}, "transport": {…},
                   "service": {…}, "others": {…} },
  "by_month":    [ { "month": "2026-03", "count": 0, "amount_in_cents": 0,
                     "by_status": { "pending": {…}, "approved": {…},
                                    "paid": {…}, "rejected": {…} } }, … ] }
```

- **As quatro chaves de status e as cinco de categoria sempre presentes**, com
  zeros — o mesmo contrato de UC-014, pela mesma razão. As listas canônicas são
  `ALL_STATUSES` (`refund_stats_finder_controller.py:9`) e `ALLOWED_CATEGORIES`
  (`refund_creator_validator.py:6`).
- **`by_month` traz todos os meses da janela**, do mais antigo ao mais recente,
  inclusive os sem nenhuma solicitação. O preenchimento é do controller, não do
  SQL: o banco só devolve os meses que existem.
- `by_month[].by_status` é o que alimenta o empilhado — e é por isso que uma
  requisição basta.
- Validator novo **é** necessário aqui, ao contrário do Ciclo 1: `months` tem teto
  e é a única forma de limitar a varredura. Fica em
  `validators/refund_summary_validator.py`.
- Repositório: `summarize_refunds(user_id, months)`, com `date_trunc('month',
  created_at)` no terceiro agrupamento. `user_id` nulo = todos, como
  `select_refunds` já trata.

### 2. Contrato e documentação

`contract/refunds.json` ganha a chave `refundSummary` — **não** um arquivo novo:
é resposta de reembolso, e os schemas que a validam vivem em
`features/refunds`. Capturada com `authenticated` (o escopo de usuário) **e** com
`admin_headers` (o escopo global), duas chaves, porque as duas formas diferem em
`scope` e é isso que o frontend precisa saber.

UC-017 em `docs/use-cases/`, entrada em `docs/index.md`. Nenhuma BR nova: o
escopo por papel é o da BR já registrada para a listagem.

### 3. Os quatro gráficos

Entram `@nivo/bar` e `@nivo/line`. `@nivo/core` e `@react-spring/web` já estão.

| Gráfico | Forma | Séries | Cor | Legenda |
|---|---|---|---|---|
| Por status | rosca (reuso do `RefundDonutChart`) | 4 | paleta de status | leader lines |
| Por categoria | barras horizontais | **1** | **uma cor** | nenhuma — o título nomeia |
| Valor por mês | linha | **1** | uma cor | nenhuma |
| Status por mês | barras empilhadas | 4 | **as mesmas cores da rosca** | sempre presente |

**Barras horizontais para categoria, não verticais**: são cinco rótulos de texto
("Alimentação", "Hospedagem"…), e na horizontal eles ficam legíveis sem rotação.

**Uma cor só nas barras por categoria** porque a categoria já está no eixo. Cinco
cores seriam codificação redundante — e a paleta não tem cinco slots.

**Um eixo por gráfico.** A linha mostra **valor**; contagem por mês já está no
empilhado. Dois eixos y no mesmo gráfico está fora de questão.

Cada gráfico novo repete as cinco lições de `RefundDonutChart.tsx`, que não são
estilo — cada uma corrige um defeito real:

1. cromo em hexadecimal por tema (`CHROME`): o Nivo pinta por atributo SVG, onde
   `var(--token)` não resolve;
2. `usePrefersReducedMotion()` alimentando `animate`: a animação é JavaScript via
   react-spring, e o `@media` do `index.css` não a alcança;
3. `theme.text.fontSize` em **string rem**, não número — número o Nivo trata como
   pixel e o gráfico sai da escala tipográfica;
4. `role="img"` no contêiner com `aria-label` **contendo os números**, para nenhum
   valor existir só em pixel;
5. carregamento sob demanda, para a árvore do Nivo não entrar no bundle inicial.

E duas exigências novas, que a rosca não tem:

- **Tooltip por marca**, em todos os três gráficos novos. A rosca é
  `isInteractive={false}` porque tem os valores nas leader lines; os novos não
  têm, então o hover é como se lê um valor exato.
- **Gap de 2px** entre segmentos empilhados e entre barras vizinhas.

### 4. `chartPalette.ts`

`lib/donutPalette.ts` → `lib/chartPalette.ts`, preservando `PALETTE`,
`NEGATIVE_COLOR`, `sliceColor` e `readableTextOn`. O módulo tem teste próprio;
atualizar o import.

**`sliceColor` não serve para as categorias.** Ela indexa por posição na lista, e
para 5 itens com 4 cores o `% PALETTE.length` repetiria a primeira — ciclar cor
categórica é proibido. Como as barras de categoria são série única com uma cor,
`sliceColor` continua sendo só para status, que tem exatamente 4 valores. Registrar
isso como comentário no módulo, senão o próximo gráfico a chamar `sliceColor` com
5 itens produz duas barras da mesma cor sem erro nenhum.

### 5. Indicadores e a tela

Faixa de indicadores acima dos gráficos, reusando o idioma de `Card` /
`Skeleton` / `<p role="alert">` de `PageHome.tsx:259-329`: total de solicitações,
valor aprovado + pago, pendentes.

**O valor é aprovado + pago, não a soma dos quatro status.** Somar os quatro
juntaria previsão, passivo, despesa liquidada e nada — é a decisão registrada em
UC-014, e este endpoint finalmente dá ao admin o número que a Home não tinha.

`src/pages/PageDashboard.tsx`, rota `/dashboard` com `dashboardLoader` fazendo
`ensureQueryData`. Sem `requireAdmin`: a tela é para todos, e o escopo é do
servidor.

**Escopo do usuário padrão**: com poucas solicitações os gráficos ficam quase
vazios. Valem para todos o estado vazio (`chart.empty`) e, sobretudo, a regra de
**nunca tratar erro como zero** — um gráfico zerado por falha de rede é
indistinguível de quem de fato não tem nada.

`nav-items.tsx`: Dashboard `enabled: true`, sem `adminOnly`. Os selos "em breve"
vão de 2 para **1**.

### 6. A fachada e o chunk

O que a fachada exporta é **um contêiner** que carrega os quatro gráficos sob
demanda por dentro — nunca os gráficos direto. Uma reexportação estática de
qualquer um deles traz o chunk inteiro do Nivo de volta ao bundle de entrada
**sem erro nenhum**, só com um `index` mais gordo
([orçamento](../../performance-budget.md)).

Um ponto de `import()` para os quatro, e não quatro, porque eles compartilham
`@nivo/core` e os pacotes `d3-*`.

**Medir e registrar o chunk depois de adicionar `@nivo/bar` e `@nivo/line`.** Os
74,2 kB atuais são a linha de base, não o teto: os dois trazem mais pacotes
`d3-*`. Atualizar o orçamento com o número medido.

## Arquitetura

Backend, `Refund-api/src/`:

- `models/repositories/refunds_repository.py` — `summarize_refunds`, três `GROUP BY`
- `validators/refund_summary_validator.py` — teto de `months`
- `controllers/refund_summary_controller.py` (+ interface) — escopo, e o
  preenchimento de zeros e de meses ausentes
- `views/refund_summary_view.py`, `main/composer/refund_summary_composer.py`
- `main/routes/refund_routes.py` — a rota nova, **antes** de `/{refund_id}`
- `test_integration/contract_test.py` — `refundSummary` nas duas formas

Frontend, dentro de `src/features/refunds/`:

- `api/summaryQueries.ts` — `refundSummaryQuery(months)`
- `schemas/summary.ts` — a resposta, com as chaves fixas
- `hooks/useRefundSummary.ts`
- `lib/chartPalette.ts` — renomeado
- `components/RefundBarChart.tsx`, `RefundLineChart.tsx`,
  `RefundStackedBarChart.tsx` — novos
- `components/DashboardCharts.tsx` — o contêiner que a fachada exporta

Fora da feature: `src/pages/PageDashboard.tsx`, `src/router.tsx`,
`src/router-loaders.ts`, `src/components/core/nav-items.tsx`, os dois catálogos.

## Testes

Suíte atual: **backend 371** (mais 72 de integração); **frontend 372 em 63
arquivos**. Ambas verdes na `main`.

Backend:

- `summarize_refunds` — os três agrupamentos; o filtro de `user_id` presente nos
  três; a janela de meses no `WHERE`.
- Controller — escopo: admin sem `user_id` agrega todos, padrão agrega só os
  próprios **mesmo passando `user_id` de outro**; as quatro chaves de status e as
  cinco de categoria presentes com zeros; **um mês sem solicitação aparece
  zerado**; `by_month` em ordem cronológica.
- Validator — `months` acima do teto e abaixo de 1 recusados.
- Rota — a nova não é capturada por `/{refund_id}`.
- Integração — o contrato nas duas formas de escopo.

Frontend:

- `chartPalette` — os testes existentes, com o import novo.
- Cada gráfico novo — o `aria-label` com os números; o estado vazio; e **erro que
  não vira zero**. Não asserte caminhos SVG: o jsdom não tem layout engine, o Nivo
  mede o contêiner como 0×0 e não desenha marca nenhuma. A lição está nos
  comentários de `RefundDonutChart.test.tsx` e `RequesterPanel.test.tsx`.
- Empilhado — legenda presente com os quatro status; as cores **iguais** às da
  rosca (asserção sobre `sliceColor`, não sobre o SVG).
- Barras por categoria — cinco barras, **uma cor**, nenhuma legenda.
- `PageDashboard` — indicadores; valor = aprovado + pago, **não** a soma dos
  quatro; carregando, erro e vazio.
- `dashboardLoader` — normaliza `months`, e **não** redireciona usuário padrão.
- `Sidebar` — selos "em breve" em 1.
- Um `.a11y.test.tsx` para `PageDashboard`.
- Handlers do MSW para `/refunds/summary` nas duas formas de escopo.

## Verificação

Backend: `pytest`, `pylint src; echo $?` — **o código de saída, não a nota**, e
**não** através de um pipe para `tail`, que reporta o status do `tail`. Como toca
repositório: `docker compose up -d` e `pytest -m integration`.

Frontend, na ordem do CI: `npm run typecheck`, `npm run lint` (0 erros **e** 0
avisos), `npx vitest run`, `npm run build`.

**Ler a saída do `npm run build`.** O chunk dos gráficos vai crescer além dos 74,2
kB; registrar o número. Se o `index` engordar nessa ordem de grandeza, algum
gráfico foi importado estaticamente.

Navegador, com a API em `localhost:3333`:

- Com **admin** e com **padrão**: os números e os gráficos precisam ser
  **diferentes** entre os dois.
- Claro e escuro — o cromo do Nivo depende do tema.
- 390 × 844, medindo overflow por `scrollWidth` contra `clientWidth`.
- Tooltip funcionando nos três gráficos novos.
- Um mês sem solicitação aparecendo como zero na linha, e não como buraco.

## Consequências e pendências

- **A falha de paleta segue aberta**, mitigada e documentada: `#A8DADC` ↔
  `#F1FAEE` com ΔE 12,9 em visão normal, abaixo do piso 15, no gráfico empilhado.
  Codificação secundária não desculpa esta checagem. Trocar a paleta é ciclo
  próprio, e muda a cor da rosca já entregue.
- **A agregação por mês é em UTC.** Uma solicitação criada às 22h de Brasília cai
  no mês seguinte na virada. Converter exigiria decidir de quem é o fuso.
- **Duas dependências novas** (`@nivo/bar`, `@nivo/line`) e o chunk maior.
- **`sliceColor` continua com 4 slots.** Chamá-la com 5 itens repete a primeira cor
  sem erro; o comentário no módulo é a única barreira.
- **O card de dinheiro da Home continua mostrando o total solicitado.** Este ciclo
  cria o endpoint que o corrige, mas mudar a Home é fora de escopo aqui.

## Fora de escopo

- **Trocar a paleta pelas cores validadas** — ciclo próprio, registrado no roadmap.
- **Calendário** — Ciclo 3 do panorama.
- **Intervalo de datas customizado** e **exportar o dashboard** (PDF/CSV).
- **Corrigir o card de dinheiro da Home** com o agregado novo.
- **Gráficos na página do membro do time** — a página tem a rosca via
  `RefundStatsPanel` e isso basta.
- **E2E** — adiado desde o Item 6.
