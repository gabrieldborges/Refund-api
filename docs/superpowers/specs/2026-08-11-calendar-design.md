# Ciclo de feature — Calendário (backend e frontend)

Data: 2026-08-11.
Repositórios afetados: **os dois**, `Refund-api` (filtro por data, contagem diária,
contrato e documentação) e `Refund-FrontEnd` (grade do mês e tela nova).

É o **Ciclo 3** e último do
[panorama das três telas](../../plans/2026-08-11-tres-telas-panorama.md). Sucede o
[Ciclo 2 — Dashboard](2026-08-11-dashboard-design.md), já mesclado na `main` dos
dois repositórios.

## Motivação

**"Calendário" é a última entrada desabilitada da sidebar.** Com ela, os três selos
"em breve" desaparecem e a navegação para de prometer o que não existe.

**Não existe como perguntar "o que aconteceu naquele dia".** `GET /refunds` filtra
por nome, status e solicitante, e ordena por data — mas **não filtra por data**. Para
achar as solicitações de um dia, hoje se pagina a lista e se lê a coluna.

**O Dashboard mostra o mês como um ponto.** Ele responde "quanto em julho", não
"quando dentro de julho". A distribuição dentro do mês — se as solicitações vêm
espalhadas ou concentradas no fechamento — não é visível em lugar nenhum.

## Decisões tomadas no brainstorming

| Decisão | Escolha | Razão |
|---|---|---|
| Quem acessa | Todos, com dados no escopo do papel | Mesmo idioma do Dashboard e da listagem |
| Filtro por data | **Aditivo** em `GET /refunds` (`created_from` / `created_to`) | A listagem já é o endpoint de "quais solicitações"; um endpoint novo duplicaria paginação, busca e ordenação |
| Contagem por dia | Endpoint próprio, `GET /refunds/daily-counts?month=` | Granularidade e parâmetro diferentes do resumo anual; enfiar no `summary` faria um endpoint responder duas perguntas |
| Grade do mês | `npx shadcn@latest add calendar` (react-day-picker v9) | Regra do `AGENTS.md`: componente novo vem do registry. Teclado e ARIA de grid já resolvidos |
| Métrica do gráfico | **Contagem** por dia, não valor | A pergunta do mês é "quando", e a resposta é quantas — valor por dia já existe agregado por mês no Dashboard |
| Navegação de mês | Livre, sem teto | Um calendário navega; um mês vazio mostra zeros, que é resposta. Diferente do seletor de ano, que é uma lista e não pode oferecer opção morta |
| Dias sem solicitação | Sem badge, não com "0" | Num calendário a ausência de marca já lê como zero; 31 zeros seriam ruído |
| Fuso | UTC, documentado | Mesma limitação e mesma razão do agrupamento por mês (UC-017) |

Alternativas descartadas, registradas:

- **Um endpoint só, devolvendo contagem e as solicitações do dia.** Acoplaria duas
  perguntas de ciclos de vida diferentes: a contagem muda ao navegar o mês, a lista
  muda ao escolher o dia.
- **Grade própria com `Intl` e `Date`.** Já descartada no panorama: fuso e semana de
  virada de mês são onde esse código erra, e teclado de grid seria escrito à mão.
- **Valor por dia no gráfico.** Fora da pergunta: a distribuição pedida é de
  quantidade.

## Escopo, em ordem de risco

### 1. Filtro por data em `GET /refunds` (aditivo)

`created_from` e `created_to`, ambos data ISO (`YYYY-MM-DD`), ambos opcionais.

- **Semiaberto por construção:** `created_from` entra como `created_at >= from` e
  `created_to` como `created_at < to + 1 dia`. Assim `created_from=created_to=` um
  mesmo dia devolve aquele dia inteiro, que é exatamente o que a tela pede — e
  ninguém precisa nomear `23:59:59`, que descarta o último segundo.
- Validator: formato e ordem (`from` não pode ser depois de `to`). Recusa com `422`
  no envelope do projeto, como as listas brancas de `status` e `sort`.
- Repositório: dois filtros a mais em `select_refunds`, que já monta a lista de
  filtros.

**Aditivo, então o contrato não quebra:** nenhum cliente existente passa esses
parâmetros, e ausentes eles não filtram nada.

### 2. `GET /refunds/daily-counts?month=YYYY-MM`

```
{ "type": "RefundDailyCounts",
  "scope": "all" | "user",
  "month": "2026-08",
  "days": [ { "date": "2026-08-01", "count": 0 }, … ] }
```

- **Todos os dias do mês, inclusive os vazios**, do dia 1 ao último. O
  preenchimento é do controller, como o dos meses em UC-017: o banco só devolve os
  dias que existem.
- O **número de dias vem do calendário**, não de uma constante: fevereiro tem 28 ou
  29, e errar isso é o defeito clássico deste endpoint. Um teste cobre ano bissexto.
- Sem `amount_in_cents`: a métrica é contagem. Publicar valor aqui seria criar um
  campo sem consumidor.
- Escopo pelo idioma de `refund_lister_controller.py:31`.
- Validator: `month` no formato `YYYY-MM`, com o ano na mesma faixa de UC-017.
- Rota declarada **antes** de `/{refund_id}`, pelo mesmo motivo de
  `/refunds/summary` — e com o mesmo teste, que afirma qual composer rodou.

### 3. Contrato e documentação

`contract/refunds.json` ganha `refundDailyCounts` e `refundListByDay` (a listagem
com o filtro novo). Capturados nos dois escopos onde o escopo muda a resposta.

**Normalização:** `date` é derivado do mês corrente, então entra na normalização
como `month` já entrou — substituindo só o ano, para os dias seguirem distintos.

UC-018 (contagem diária) e a atualização de UC-004 com os dois parâmetros novos.
Entradas em `docs/index.md`.

### 4. `RefundLineChart` deixa de conhecer dinheiro

Hoje ele recebe `months: { month, cents }[]` e converte centavos por dentro. O
Calendário precisa dele com **contagem por dia**.

Em vez de um `metric` que ramifica, o componente passa a receber pontos já em
unidade de exibição:

```ts
interface RefundLineChartProps {
  points: { label: string; value: number; exact: string }[];
  titleKey: string;
  // Rótulo da unidade acima do gráfico. Ausente = sem rótulo (contagem não tem
  // unidade a declarar).
  unitLabelKey?: string;
  visibleLabels?: string[];
  isLoading?: boolean;
  isError?: boolean;
}
```

`value` é o que o eixo desenha, `exact` é o que o tooltip mostra. Quem sabe se
aquilo é dinheiro é **o chamador**: o Dashboard aplica `valueScaleFor` e passa
`formatCentsToBRL` no `exact`; o Calendário passa a contagem crua e o inteiro
formatado. O gráfico fica com uma responsabilidade só — desenhar uma série num
eixo.

### 5. A tela

`npx shadcn@latest add calendar` → `src/components/ui/calendar.tsx` e
react-day-picker v9.

- `src/pages/PageCalendar.tsx`, com **mês e dia na URL**
  (`?month=YYYY-MM&day=YYYY-MM-DD`), seguindo a convenção URL-como-estado;
  `calendarLoader` normaliza e faz prefetch.
- `DayButton` customizado com a contagem do dia. **Sem badge nos dias zerados:**
  num calendário a ausência de marca já lê como zero.
- Clicar num dia abre o painel com as solicitações daquele dia, via
  `useRefunds({ createdFrom: dia, createdTo: dia })`, com as linhas apontando por
  `getRefundHref(refund, viewer)` — reuso obrigatório, é a implementação única da
  BR-016.
- **O painel mostra a primeira página.** Quando `total` passa do que veio, ele diz
  "mostrando N de M": um dia com mais de dez solicitações é implausível neste
  produto, e paginar dentro do painel seria construir para um caso que não ocorre —
  mas silenciar a diferença seria mentir.
- Gráfico do mês: `RefundLineChart` com contagem por dia. **Título carrega mês e
  ano; eixo X carrega só o dia** — a regra registrada no panorama para
  granularidade diária. No mobile os rótulos rareiam, como no Dashboard: 31 dias
  não cabem em 390px.
- `nav-items.tsx`: Calendário `enabled: true`, sem `adminOnly`.

### 6. O teste da sidebar precisa ser reescrito, não ajustado

Com o Calendário ativo os selos "em breve" chegam a **zero**, e
`getAllByText` **lança exceção** quando não encontra nada — não devolve lista vazia.
Os dois casos que contam selos saem, e no lugar entra o que agora é a afirmação
útil: **todos os itens são links**, e o item admin-only continua sumindo para
usuário padrão.

O campo `enabled` da interface `NavItem` fica: ele é a máquina do selo, e o próximo
item futuro vai usá-lo. Mas nenhum item o usa como `false` hoje, e isso precisa
estar dito no arquivo — senão o mecanismo parece morto e alguém o remove.

## Arquitetura

Backend, `Refund-api/src/`:

- `validators/refund_lister_validator.py` — formato e ordem das datas
- `validators/refund_daily_counts_validator.py` — formato de `month`
- `models/repositories/refunds_repository.py` — datas em `select_refunds`;
  `count_by_day` novo
- `controllers/refund_daily_counts_controller.py` (+ interface) — escopo e
  preenchimento dos dias
- `views/refund_daily_counts_view.py`, `main/composer/refund_daily_counts_composer.py`
- `main/routes/refund_routes.py` — parâmetros novos na listagem; rota nova **antes**
  de `/{refund_id}`

Frontend:

- `src/features/refunds/schemas/dailyCounts.ts`, `api/dailyCountsQueries.ts`,
  `hooks/useDailyCounts.ts`
- `src/features/refunds/schemas/refund.ts` — `createdFrom`/`createdTo` nos params da
  listagem
- `src/features/refunds/components/RefundLineChart.tsx` — generalizado (§4)
- `src/features/refunds/components/DashboardCharts.tsx` — adaptado ao novo contrato
  do gráfico
- `src/features/refunds/components/DayRefundsPanel.tsx` — a lista do dia
- `src/components/ui/calendar.tsx` — do registry
- `src/pages/PageCalendar.tsx`, `src/router.tsx`, `src/router-loaders.ts`,
  `nav-items.tsx`, `Sidebar.test.tsx`, os dois catálogos

## Testes

Suíte atual: **backend 405** (mais 72 de integração); **frontend 416 em 68
arquivos**. Ambas verdes na `main`.

Backend:

- `select_refunds` com datas — os dois filtros no `WHERE`; `created_to` virando
  `< to + 1 dia`; ausentes não filtrando.
- Validator da listagem — data mal formada e `from` depois de `to` recusadas.
- `count_by_day` — `GROUP BY` por dia; filtro de usuário; janela do mês.
- Controller — todos os dias do mês presentes com zero; **fevereiro de ano
  bissexto com 29 dias**; escopo por papel com `user_id` ignorado para padrão.
- Rotas — `daily-counts` não lida como `refund_id`; a listagem aceitando as datas.
- Integração — os dois contratos novos.

Frontend:

- `RefundLineChart` — o novo contrato: rótulo de unidade ausente não renderiza
  nada; `exact` aparecendo no tooltip. Os testes do Dashboard **não podem mudar de
  comportamento** — só de forma de chamada.
- `PageCalendar` — dia com solicitações mostrando a contagem; dia sem, **sem
  badge**; clicar num dia escrevendo `day` na URL; o painel listando as
  solicitações daquele dia; "mostrando N de M" quando há mais.
- `calendarLoader` — normaliza `month` e `day` inválidos; **não** redireciona
  usuário padrão.
- `Sidebar` — nenhum selo "em breve"; todos os itens são links; item admin-only
  ausente para padrão.
- Um `.a11y.test.tsx` para `PageCalendar` — a grade é o componente com mais
  semântica de teclado desta aplicação.
- Handlers do MSW para `daily-counts` e para a listagem com datas.

## Verificação

Backend: `pytest`, `pylint src; echo $?` — **o código de saída, não a nota**, e não
por pipe para `tail`. Como toca repositório: `docker compose up -d` e
`pytest -m integration`.

Frontend, na ordem do CI: `npm run typecheck`, `npm run lint` (0 erros **e** 0
avisos), `npx vitest run`, `npm run build`.

**Ler a saída do `npm run build`.** O react-day-picker é dependência nova; registrar
quanto ela custa e onde caiu. Se o `index` crescer muito, a grade também vai para
carregamento sob demanda.

Navegador, com a API em `localhost:3333`:

- Com **admin** e com **padrão**: contagens **diferentes** no mesmo mês.
- Um dia com solicitações mostrando o número; um dia sem, limpo.
- Clicar num dia, recarregar a página e cair no mesmo dia (o estado está na URL).
- Navegar para um mês sem nada: grade limpa e gráfico vazio, não erro.
- **Teclado**: chegar à grade por Tab e andar pelos dias com as setas.
- Claro e escuro; 390 × 844 com `scrollWidth` contra `clientWidth`.

## Consequências e pendências

- **A contagem por dia é em UTC.** Uma solicitação criada às 22h de Brasília aparece
  no dia seguinte. Mesma limitação de UC-017, e a mais visível das três telas:
  aqui o dia é a unidade.
- **O painel do dia mostra a primeira página**, com "N de M" quando há mais.
- **Dependência nova** (react-day-picker) e o bundle maior.
- **`NavItem.enabled` fica sem nenhum item `false`.** O mecanismo do selo continua,
  documentado no arquivo para não parecer morto.
- **`RefundLineChart` mudou de contrato.** Quem o usar precisa converter antes de
  passar — o que é a intenção: o gráfico não decide mais o que é dinheiro.

## Fora de escopo

- **Criar solicitação a partir de um dia** do calendário.
- **Semana ou intervalo arbitrário** — a grade é mensal.
- **Filtro por status dentro do calendário.**
- **Fuso horário configurável** — decisão adiada em UC-017, mantida.
- **Trocar a paleta** — dívida registrada no roadmap.
- **E2E** — adiado desde o Item 6.
