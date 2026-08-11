# Panorama — as três telas "em breve": Time, Dashboard e Calendário

Data: 2026-08-11.
Repositórios afetados: **`Refund-api` e `Refund-FrontEnd`**, os três ciclos tocam
os dois.

Este documento **não é um spec**. Ele trava as decisões das três telas e a ordem
de construção, para que cada ciclo depois vire um spec+plan próprio, no formato
de `docs/superpowers/specs/` do repositório afetado. Requisitos canônicos
continuam nos demais documentos de [`docs/`](../index.md) — este é um plano, como
o [`current-state.md`](current-state.md).

## O ponto de partida

O `Refund-FrontEnd` tem três entradas de menu marcadas como "em breve" em
`src/components/core/nav-items.tsx`, com `enabled: false`: Dashboard, Time e
Calendário. Não existem rotas nem páginas para elas — só o item desabilitado, que
`Sidebar.tsx` renderiza como botão inerte com um `SidebarMenuBadge`.

A intenção é preencher as três. O planejamento veio antes da construção porque
elas compartilham fundação (agregação no backend, escopo por papel, gráficos), e
decidir isso três vezes separadamente produziria três respostas diferentes.

## O que a exploração desmentiu

Quatro premissas caíram ao ler o código. Ficam registradas porque cada uma
mudaria o escopo de um ciclo se fosse descoberta durante a implementação.

1. **Não é trabalho só de frontend.** Não existe endpoint que liste usuários:
   `UsersRepository` (`src/models/repositories/users_repository.py`) expõe apenas
   `insert_user`, `select_user_by_email`, `select_user_by_id` e `update_avatar` —
   nada de busca ou paginação, nem na interface. E não existe agregado global:
   `GET /users/{id}/refund-stats` é por usuário e **deliberadamente não tem total
   entre status** (UC-014). Cada uma das três telas exige backend novo.
2. **A biblioteca de gráficos é o Nivo, não o recharts.** `@nivo/core` e
   `@nivo/pie` já estão no `package.json` do frontend, com `@react-spring/web`,
   que é a animação do Nivo. A suposição inicial era recharts, e estava errada.
3. **O gráfico de rosca já existe, pronto e testado**, em
   `src/features/refunds/components/RefundDonutChart.tsx` com
   `src/features/refunds/lib/donutPalette.ts`. Ele já resolve paleta com cor
   semântica, cromo por tema, `prefers-reduced-motion`, rótulo acessível e
   carregamento sob demanda. O Dashboard **reaproveita**; reescrever seria perder
   cinco lições já pagas (listadas no Ciclo 2).
4. **`GET /refunds` não filtra por data.** O calendário depende de um parâmetro
   que ainda não existe.

### Dependência de branch — resolvida em 2026-08-11

Quando a primeira versão deste panorama foi escrita, o donut, a paleta e o hook
`usePrefersReducedMotion` **ainda não estavam commitados**: eram arquivos não
rastreados na branch `feat/serve-static` do frontend. O Ciclo 2 dependia dela.

**A branch foi mesclada no mesmo dia e a dependência caiu.** Os três arquivos
estão rastreados na `main` do frontend, e o Ciclo 2 pode começar sem espera.

Ainda assim, este documento cita as partes internas desses arquivos **por
identificador** (`CHROME`, `sliceColor`, o ramo `isError`) em vez de por número de
linha. É a mesma lição que o [`current-state.md`](current-state.md) registra sobre
os SHAs: a forma que não envelhece descreve *como encontrar* o estado, não afirma
qual é. Confira com:

```bash
cd Refund-FrontEnd && git log --oneline -1 && git status --short
grep -n "CHROME\|isError\|role=\"img\"" src/features/refunds/components/RefundDonutChart.tsx
```

## Decisões travadas

| Decisão | Escolha | Razão |
|---|---|---|
| Visibilidade | Time só admin. Dashboard e Calendário para todos, com dados no escopo do papel | O admin vê a empresa; o usuário padrão vê as próprias solicitações |
| Cargo na empresa | **Não adicionar coluna.** A lista de Time mostra o papel (`role`: Administrador / Padrão) | Sem ninguém que preencha, `job_title` nasceria sempre nula e a coluna mostraria "—" para todos. Evita migration e endpoint de escrita |
| Página do usuário | Somente leitura | Promoção a admin continua sendo `init/promote_admin.py`. Mantém a superfície de risco pequena |
| Fatiamento | Este panorama + um spec+plan por ciclo, escrito no início do ciclo | Os specs anteriores têm 223–404 linhas cada; um spec único das três viraria um plan de 40+ tarefas, difícil de executar e de revisar |
| Ordem | **Time → Dashboard → Calendário** | Time é o único com fundação nova de verdade e não depende de nada. O Calendário fica por último e reaproveita o filtro de data e os gráficos |
| Gráficos | Quatro: rosca por status, barras por categoria, linha por mês, barras empilhadas status × mês | Cobre proporção, comparação, tempo e composição — quatro arquétipos, não quatro variações do mesmo |
| Grade do mês | `npx shadcn@latest add calendar` (react-day-picker v9) | Segue a regra do `AGENTS.md` do frontend: componente novo vem do registry. Teclado e ARIA de grid já resolvidos, que é justamente onde uma grade feita à mão falha |

Alternativas descartadas, registradas:

- **Coluna `job_title` preenchida pelo admin.** Era a opção mais completa, mas
  exigia migration mais `PATCH` novo para um dado que a tela só exibe. Fica como
  ideia no [`roadmap.md`](../roadmap.md).
- **`PATCH /users/{id}/role` na interface.** Descartada por um motivo concreto: o
  `role` vem do JWT e `get_current_user` nunca consulta o banco, então quem é
  promovido só vira admin de fato no próximo login. Uma UI que promete efeito
  imediato mentiria.
- **Grade de mês escrita à mão com `Intl` e `Date`.** Zero dependência nova, mas
  fuso horário e semana de virada de mês são exatamente onde esse código erra.
- **Uma feature `dashboard` separada no frontend.** Impossível: ver "Fronteiras"
  abaixo.

## Fronteiras que ditam o desenho do frontend

O `eslint-plugin-boundaries` (`eslint.config.js:39-62`) classifica o código em
`app`, `feature`, `ui` e `shared`, com `default: 'disallow'`. Duas consequências
não negociáveis:

- **Uma feature não pode importar outra.** Por isso os gráficos do Dashboard
  ficam dentro de `features/refunds` (junto do `RefundDonutChart`) e não numa
  feature `dashboard`: eles consomem dados de reembolso.
- **Uma feature não pode importar `app`** (onde vive `src/context`). Por isso o
  espectador é passado por prop — o `RefundViewer` de
  `features/refunds/lib/getRefundHref.ts` é uma interface mínima local, não o
  `AuthUser`. A página do membro do time compõe duas features **na camada
  `app`**, que é a única com permissão para isso.

## Ciclo 1 — Time (admin) — **CONCLUÍDO em 2026-08-11**

Spec: [`2026-08-11-team-directory-design.md`](../superpowers/specs/2026-08-11-team-directory-design.md).
Plan: [`2026-08-11-team-directory.md`](../superpowers/plans/2026-08-11-team-directory.md).

**Duas coisas que este panorama errou, descobertas ao ler o código na hora de
construir.** Ficam registradas porque as duas eram afirmações plausíveis:

1. **O ciclo não precisava de `user_lister_validator`.** Os limites de `page` e
   `per_page` são impostos pelo `Query(ge=..., le=...)` do FastAPI na rota. O
   `refund_lister_validator` existe só para as listas brancas de `status`, `sort`
   e `order`, que o FastAPI expressaria com o envelope de erro dele em vez do
   `{"detail": "..."}` do projeto. Sem lista branca, um validator seria forma
   copiada sem conteúdo.
2. **O reuso do `RequesterPanel` não era direto.** Ele exige `currentRefundId` —
   âncora do destaque e das setas — e desenha o nome no próprio `CardHeader`, que
   duplicaria o nome na página do membro. O núcleo foi extraído para
   `RefundStatsPanel`, com um id opcional e um slot `ReactNode` para as ações do
   cabeçalho.

E duas que os testes pegaram: o `CardTitle` do shadcn é uma `div` sem `asChild`,
então o nome nunca era um heading enquanto o painel abaixo tinha um `h3`; e os
testes de estado de erro exerciam um caminho inalcançável, porque o
`ensureQueryData` do loader rejeita antes de o componente renderizar.

### O plano original do Ciclo 1, para referência

### Backend

A fatia completa, replicando o slice de `GET /refunds`:

- `models/repositories/users_repository.py` e sua interface: `select_users(page,
  per_page, name)` e `count_users(name)`. Busca por `ILIKE '%name%'`, como
  `refunds_repository.py:47`. `ORDER BY name ASC` **com desempate por `id`**,
  pelo mesmo motivo do `id DESC` em `RefundsRepository.__order_by`: sem
  desempate, a paginação não é determinística e uma linha pode aparecer em duas
  páginas.
- `validators/user_lister_validator.py`: limites de `page` e `per_page`,
  espelhando `refund_lister_validator.py`.
- `controllers/user_serializer.py` — **o ponto crítico**: a resposta é
  `{id, name, email, role, has_avatar, created_at}`. Nunca `password`. Módulo
  próprio pelo mesmo motivo de `refund_serializer.py`: uma forma, um lugar. Um
  campo sensível vazado numa lista de usuários é o pior defeito possível neste
  ciclo, e um serializador único é o que torna isso testável de uma vez.
- `controllers/user_lister_controller.py`: `if role != "admin"` levantando
  `HttpForbiddenError` **antes de qualquer acesso ao banco**, que é o idioma
  anti-enumeração de `refund_reviewer_controller.py:30`.
- `controllers/user_finder_controller.py`, para `GET /users/{id}`: admin-only,
  respondendo **404** e não 403, seguindo `refund_stats_finder_controller.py:19`.
- Views, composers e registro em `main/routes/user_routes.py`.
- Contrato (ADR-007): snapshot novo `contract/users.json`, espelhado em
  `Refund-FrontEnd/src/features/team/contract/users.json`.
- Documentação: UC-015 (listar usuários) e UC-016 (consultar usuário) em
  `docs/use-cases/`, entradas em [`docs/index.md`](../index.md), e a regra de
  acesso admin-only em [`business-rules.md`](../business-rules.md).

### Frontend

Feature nova `src/features/team/`, espelhando `features/refunds`, com fachada
`index.ts` — o resto da aplicação só importa por ela:

- `api/userQueries.ts`: `userKeys` hierárquico, `userListQuery` e
  `userDetailQuery` como `queryOptions`, com `signal` repassado ao axios e Zod na
  fronteira. Cópia fiel de `features/refunds/api/refundQueries.ts`, para o
  loader e o hook compartilharem a mesma entrada de cache.
- `schemas/user.ts`: `userSchema`, resposta de lista e `userListSearchParamsSchema`
  com `.catch()` por campo, como o de refunds.
- `constants/pagination.ts`: `USERS_PER_PAGE = 10`, importado pelo hook **e** pelo
  loader, para não divergirem.
- `hooks/useUsers.ts`, `hooks/useUser.ts`.
- `components/UsersTable.tsx`: TanStack Table só com `getCoreRowModel` —
  ordenação é server-side, o componente não ordena nada. Colunas nome, e-mail,
  papel (`Badge`) e membro desde.
- `contract.test.ts` validando o schema contra o snapshot.

Páginas e rotas, na camada `app`:

- `src/pages/PageTeam.tsx`: busca por nome, tabela e paginação. A busca
  **reaproveita** `src/hooks/useDebouncedValue.ts` (400 ms) e o padrão
  URL-como-estado do sub-componente `RefundSearch` (`PageHome.tsx:40-73`),
  inclusive o `key={name ?? ""}` que remonta o input quando a URL muda por fora.
- `src/pages/PageTeamMember.tsx`: cartão de identidade (nome, e-mail, papel,
  membro desde) **mais o reuso de `RequesterPanel`**, que a fachada de refunds já
  exporta. Ele já é exatamente "nome, contadores por status e as solicitações
  daquela pessoa" — é a tela pedida, e duplicá-la seria criar uma segunda
  verdade. Verificar as props e estender minimamente se preciso.
- `src/router.tsx`: rotas `/team` e `/team/:id`, lazy, com `handle: { titleKey }`.
- `src/router-loaders.ts`: `teamLoader` (normaliza `page` e `name`, redireciona
  para retirar defaults, `ensureQueryData`) e `teamMemberLoader`. **Extrair um
  `requireAdmin()` reutilizável** da checagem hoje embutida em
  `router-loaders.ts:126` — não existe `AdminRoute` nem helper de papel. A guarda
  de rota é de interface: a autorização real é do backend.
- `nav-items.tsx`: `enabled: true` no item de Time e campo novo
  `adminOnly?: boolean`; `Sidebar.tsx` passa a filtrar por papel.
- i18n: chaves em `pt-BR.json` **e** `en-US.json` — `src/locales/catalogues.test.ts`
  testa paridade entre os catálogos.
- `src/components/core/Sidebar.test.tsx` afirma `getAllByText("em breve")`
  com length **3**; passa a **2**.

## Ciclo 2 — Dashboard (todos, com escopo por papel) — **CONCLUÍDO em 2026-08-11**

Spec: [`2026-08-11-dashboard-design.md`](../superpowers/specs/2026-08-11-dashboard-design.md).
Plan: [`2026-08-11-dashboard.md`](../superpowers/plans/2026-08-11-dashboard.md).

**O que a skill de visualização mudou neste panorama.** A paleta foi submetida ao
validador e **falha 4 das 6 checagens** nos dois modos, incluindo uma falha dura:
`#A8DADC` (aprovada) e `#F1FAEE` (paga) têm ΔE 12,9 em visão normal, abaixo do piso
de 15. A rosca escapa porque tem leader line com rótulo em cada fatia; o empilhado
não teria. Decisão: **manter a paleta e mitigar** (gap de 2px, legenda com
quadrados, tooltip por segmento), registrando como falha conhecida — o piso de
visão normal é a única checagem que codificação secundária não desculpa. Trocar a
paleta muda a cor da rosca já entregue, e é ciclo próprio.

Duas decisões de forma vieram da análise, não do gosto: as barras por categoria são
**uma série com uma cor** (a categoria já está no eixo, e a paleta tem 4 slots para
5 categorias — ciclar repetiria a primeira sem erro), e a linha mostra **só valor**
(contagem já está no empilhado; juntar seria eixo duplo).

Custo medido: os gráficos foram de 74,2 para **≈120,7 kB gzip**; a entrada subiu
**0,9 kB**, de 173,1 para 174,1 — a divisão continua de pé.

**Ajuste de 2026-08-11, depois do uso.** O resumo passou de janela deslizante de
`months` para **ano-calendário** com `year`, mais `available_years`. O motivo é de
leitura: o eixo X carrega **só o mês** e o ano vive no **título do card** — o ano é
o mesmo para as doze marcas, e no eixo gastaria a largura que falta em 390px com a
única informação que não varia. Isso só lê corretamente se cada resposta cobrir
janeiro a dezembro de um ano; uma janela deslizante colocaria dois anos num eixo de
nomes de mês sem ano.

**Regra de rótulo, para o Ciclo 3 herdar.** O período vai no título, a unidade do
eixo vai acima do gráfico, e o eixo carrega só o que varia entre as marcas:

| Granularidade | Título do card | Eixo X |
|---|---|---|
| Mensal (Dashboard) | o **ano** | só o **mês** |
| Diária (Calendário, Ciclo 3) | o **mês e o ano** | só o **dia** |

O `ChartCard` já recebe o período por prop (`period`), então o Calendário passa
"agosto de 2026" sem tocar no componente.

**Escala de valor.** O eixo mostra inteiros e a unidade é nomeada uma vez acima do
gráfico ("em reais", "em milhares de reais", "em milhões de reais"), escolhida pelo
**maior valor da série**. Fixar em milhares funciona com números grandes e mente com
pequenos: com os volumes atuais do projeto o eixo leria 2, e categorias abaixo de
R$ 500 leriam 0 — indistinguível de categoria sem nenhuma solicitação. O corte para
milhares é em dez mil, não mil, porque entre os dois a divisão produz 1, 2, 3: perda
de resolução sem ganho de legibilidade.

### O plano original do Ciclo 2, para referência

### Backend

Um endpoint que serve os quatro gráficos e os indicadores, para a tela inteira
custar uma requisição e não haver cascata:

`GET /refunds/summary?months=6` (default 6, máximo 12), com escopo pelo idioma já
existente em `refund_lister_controller.py:31`
(`filter_user_id = filter_user_id if role == "admin" else user_id`):

```
{ type: "RefundSummary", scope: "all" | "user",
  by_status:   { pending: {count, amount_in_cents}, approved: {...},
                 paid: {...}, rejected: {...} },
  by_category: [ { category, count, amount_in_cents } ],
  by_month:    [ { month: "2026-08", count, amount_in_cents,
                   by_status: { pending: {...}, approved: {...},
                                paid: {...}, rejected: {...} } } ] }
```

Três `GROUP BY` numa única chamada de repositório: por `status`, por `category` e
por `date_trunc('month', created_at)` cruzado com `status`. O
`by_month[].by_status` é o que alimenta as barras empilhadas. UC novo e snapshot
de contrato. Atende a ideia **"agregado por status cruzando usuários"** do
[`roadmap.md`](../roadmap.md).

### Frontend

- `npm i @nivo/bar @nivo/line` — mesma família já adotada; `@nivo/core` e
  `@react-spring/web` já estão presentes.
- **Rosca por status: reuso direto** de `RefundDonutChart`. As props `slices` e
  `metric: "count" | "currency"` já atendem, e sobreviveram intactas ao merge de
  2026-08-11.
  - **Armadilha, verificada na assinatura atual**: a chave passada em
    `unitLabelKey` **precisa ter as variantes de plural do i18next**
    (`_one` / `_other`). O total é interpolado como `count`, e sem elas uma
    solicitação só aparece rotulada como "1 solicitações". Vale para cada rótulo
    de unidade novo que o Dashboard introduzir, nos **dois** catálogos.
- Novos `RefundBarChart.tsx` (barras horizontais por categoria),
  `RefundLineChart.tsx` (valor por mês) e `RefundStackedBarChart.tsx`
  (status × mês), **dentro de `features/refunds`**.

#### A restrição que decide o desenho: os gráficos não podem ser reexportados pela fachada

O [orçamento de performance](../performance-budget.md), medido em 2026-08-11,
registra que o chunk do donut é de **74,2 kB gzip — um terço de tudo o mais que a
aplicação entrega** — e que uma **reexportação estática** de `RefundDonutChart`
pela fachada (`features/refunds/index.ts`) traz esse chunk inteiro de volta para o
bundle de entrada **sem erro nenhum**, só com um `index` mais gordo.

Isso colide com a regra de fronteira: a camada `app` só pode alcançar a feature
pelo `index.ts`. As duas convivem porque o que a fachada exporta é um
**contêiner** que faz o `import()` dinâmico por dentro — é o que
`RequesterPanel` já faz com o donut. O `lazy()` é o que cria o chunk; o
`export { default as X } from './X'` é o que o destrói.

Portanto, para o Dashboard: a fachada exporta **um contêiner de gráficos** que
carrega os quatro sob demanda, e **nenhum arquivo de gráfico é reexportado
diretamente**. Um único ponto de `import()` dinâmico também é melhor que quatro,
porque os quatro gráficos compartilham `@nivo/core` e os pacotes `d3-*`.

Duas consequências para o spec do Ciclo 2:

- **Medir o bundle depois de adicionar `@nivo/bar` e `@nivo/line`.** Eles trazem
  mais pacotes `d3-*`, então o chunk vai passar de 74 kB — o número atual é a
  linha de base, não o teto. Atualizar o orçamento com o valor medido.
- **A verificação é uma linha do `npm run build`**: enquanto houver um chunk
  separado para os gráficos, a divisão está de pé. Se o `index` engordar ~74 kB
  ou mais, alguém reexportou estaticamente.
- Cada gráfico novo precisa repetir as **cinco lições já pagas** em
  `RefundDonutChart.tsx`. Elas não são estilo; cada uma corrige um defeito real:
  1. cor de cromo em hexadecimal por tema (a constante `CHROME`) — o Nivo pinta
     por atributo SVG, onde `var(--token)` não é resolvido pelo navegador;
  2. `usePrefersReducedMotion()` alimentando `animate` — a animação do Nivo é
     JavaScript via react-spring, e o `@media (prefers-reduced-motion)` do
     `index.css` não a alcança;
  3. `theme.text.fontSize` como **string em rem**, não número — número o Nivo
     trata como pixel, e o gráfico deixa de acompanhar a escala tipográfica;
  4. `role="img"` no contêiner com `aria-label` **contendo os números**, para que
     nenhum valor exista somente em pixel;
  5. `React.lazy`, como no `RequesterPanel.tsx`, para a árvore do Nivo não
     entrar no bundle inicial.
- Generalizar `lib/donutPalette.ts` para `lib/chartPalette.ts`, preservando
  `PALETTE`, `NEGATIVE_COLOR`, `sliceColor` e `readableTextOn` (esta última
  chegou no merge de 2026-08-11), de modo que os quatro gráficos
  compartilhem a paleta e `rejected` continue vermelho em todos — cor com
  significado não pode depender da posição no ranking. O módulo tem teste
  próprio; atualizar o import.
- `src/pages/PageDashboard.tsx`: faixa de indicadores e os quatro gráficos,
  reusando o idioma de `Card` / `Skeleton` / `<p role="alert">` de
  `PageHome.tsx:253-318`. Rota `/dashboard` com `dashboardLoader` fazendo
  `ensureQueryData`.
- Escopo do usuário padrão: com poucas solicitações os gráficos ficam quase
  vazios. Valem para todos o estado vazio de `RefundDonutChart`
  (o ramo `total === 0`, com a chave `chart.empty`) e, sobretudo, a regra de
  **nunca tratar erro como zero** (o ramo `isError`, com `chart.error`, que vem
  antes): uma rosca vazia por falha de rede é indistinguível de
  uma pessoa que não tem nada.
- Testes: o jsdom não tem layout engine, então o Nivo mede o contêiner como 0×0 e
  não desenha marca nenhuma. Asserte o rótulo acessível e a transformação dos
  dados, não caminhos SVG. A lição já está escrita em
  `RefundDonutChart.test.tsx` e `RequesterPanel.test.tsx`, nos comentários que
  começam em "jsdom has no layout engine".
- `nav-items.tsx`: Dashboard `enabled: true` — os badges "em breve" vão de 2 para 1.

## Ciclo 3 — Calendário (todos, com escopo por papel) — **CONCLUÍDO em 2026-08-11**

Spec: [`2026-08-11-calendar-design.md`](../superpowers/specs/2026-08-11-calendar-design.md).

**As três telas estão entregues, e nenhum item da sidebar tem selo "em breve".**

Duas coisas do plano original mudaram:

1. **A regra de rótulo foi aplicada como registrado acima**: o eixo X carrega só o
   **dia**, e o mês e o ano vivem no título do card. Isso obrigou o
   `RefundLineChart` a parar de conhecer dinheiro — ele recebe pontos já em unidade
   de exibição mais o valor exato para o tooltip, e quem converte é o chamador.
2. **Nenhum badge nos dias zerados.** Num calendário a ausência de marca já lê como
   zero; 29 zeros seriam ruído.

Custo medido: o `react-day-picker` são **21,95 kB gzip**, e caíram no chunk lazy de
`/calendar` — a entrada subiu 1,13 kB. Quem nunca abre o calendário não baixa a grade.

**`NavItem.enabled` fica sem nenhum item `false`.** O mecanismo do selo continua, com
um comentário no arquivo dizendo por quê: sem ele o mecanismo parece morto e alguém o
remove, junto do lugar onde a próxima promessa seria feita.

### O plano original do Ciclo 3, para referência

### Backend

- **Aditivo em `GET /refunds`**: `created_from` e `created_to` (data ISO) no
  validator e no `WHERE created_at >= / <`. Sendo aditivo, não quebra o contrato.
- `GET /refunds/daily-counts?month=YYYY-MM`, com o mesmo escopo por papel,
  retornando `{ month, days: [ { date, count, amount_in_cents } ] }` via
  `GROUP BY date(created_at)`.
- **Fuso horário, a decisão a tomar no spec do ciclo.** `refunds.created_at` é
  `DateTime` com `server_default now()`, e agregar por dia em UTC coloca uma
  solicitação criada às 22h de Brasília no dia seguinte. Duas saídas: agregar em
  UTC e documentar como limitação conhecida, ou converter o fuso na query. A
  primeira é mais simples e honesta; a segunda exige decidir de quem é o fuso.

### Frontend

- `npx shadcn@latest add calendar`, que traz `src/components/ui/calendar.tsx` e
  react-day-picker v9.
- `src/pages/PageCalendar.tsx`, com mês e dia **na URL**
  (`?month=YYYY-MM&day=YYYY-MM-DD`), seguindo a convenção URL-como-estado;
  `calendarLoader` normaliza e faz prefetch.
- `DayButton` customizado com o contador do dia, e `modifiers` marcando os dias
  que tiveram solicitações.
- Clicar num dia abre o painel com as solicitações daquele dia, via
  `useRefunds({ createdFrom, createdTo })`, com as linhas apontando por
  `getRefundHref(refund, viewer)` — reuso obrigatório, é a implementação única da
  BR-016.
- Gráfico do mês: **reuso de `RefundLineChart`** do Ciclo 2, alimentado por
  `daily-counts` (solicitações por dia).
- `nav-items.tsx`: Calendário `enabled: true`. Os badges "em breve" chegam a
  **zero**, e `getAllByText` **lança exceção** quando não encontra nada — o teste
  de `Sidebar.test.tsx` precisa ser **reescrito** neste ciclo, não ter o número
  ajustado. Por exemplo: afirmar que todos os itens são links, e que o item
  admin-only desaparece para o usuário padrão.

## Verificação de cada ciclo

- Frontend, na ordem do CI (`.github/workflows/ci.yml`, do mais barato ao mais
  caro): `npm run typecheck`, `npm run lint`, `npx vitest run`, `npm run build`.
- **Nos ciclos 2 e 3, ler a saída do `npm run build`, não só o código de saída.**
  Os gráficos precisam continuar num chunk próprio; se o `index` engordar ~74 kB
  ou mais, alguém reexportou um gráfico estaticamente pela fachada e a divisão
  caiu em silêncio. Ver [`performance-budget.md`](../performance-budget.md).
- Backend: `pytest` e `pylint src; echo $?` — o código de saída, não a nota. Ao
  tocar repositories ou migrations, também `pytest -m integration` com o banco
  descartável de pé.
- Os testes de contrato acoplam os dois repositórios de propósito: mudar a forma
  de uma resposta quebra a suíte do frontend, que é o aviso desejado.
- Navegador, com a API em `localhost:3333`: tema **claro e escuro** (o cromo do
  Nivo depende do tema) e **390 × 844** (iPhone 12 Pro, a referência do
  `AGENTS.md` do frontend), medindo overflow por `scrollWidth` contra
  `clientWidth` em vez de confiar em captura de tela.
- Com usuário **admin** e usuário **padrão**: Time não pode aparecer na sidebar
  nem responder na rota direta para o padrão, e Dashboard e Calendário devem
  mostrar dados diferentes para cada um.

## Fora de escopo nas três telas

- **Cargo na empresa** (`job_title`): descartado nesta rodada, registrado como
  ideia no [`roadmap.md`](../roadmap.md).
- **Promover ou rebaixar admin pela interface** e **desativar usuário**: cada um
  é produto novo, com ciclo próprio.
- **Foto de perfil**: segue como a pendência de produto já registrada. A lista de
  Time mostra as iniciais, como a sidebar já faz.
- Exportar o dashboard (PDF ou CSV), intervalo de datas customizado no dashboard,
  e gráficos por usuário dentro da página do membro.
