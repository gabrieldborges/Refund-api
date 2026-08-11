# Ciclo de feature — Diretório do time (backend e frontend)

Data: 2026-08-11.
Repositórios afetados: **os dois**, `Refund-api` (endpoints, contrato e
documentação canônica) e `Refund-FrontEnd` (feature e telas novas).

É o **Ciclo 1** do
[panorama das três telas](../../plans/2026-08-11-tres-telas-panorama.md), que
travou as decisões de Time, Dashboard e Calendário e fixou a ordem
**Time → Dashboard → Calendário**. Este ciclo não depende de nenhuma branch
pendente.

## Motivação

**A entrada "Time" da sidebar está desabilitada desde que a sidebar existe.** Ela
aparece com o selo "em breve" ao lado de Dashboard e Calendário
(`nav-items.tsx`), sem rota e sem página. É uma promessa visível na interface e
não cumprida.

**Não existe forma de saber quem usa o sistema.** O admin revisa e paga
solicitações de pessoas cujo cadastro ele nunca vê. Não há tela, e também não há
API: `UsersRepository` expõe apenas `insert_user`, `select_user_by_email`,
`select_user_by_id` e `update_avatar` — nenhuma busca, nenhuma paginação, nem na
interface. **Nada aqui é "só ligar a tela".**

**O histórico de uma pessoa só é alcançável por dentro de uma revisão.** O
`RequesterPanel` já mostra exatamente o que se quer saber de alguém — contagens
por status e as solicitações dela — mas só existe embutido na tela de revisão de
uma solicitação específica. Para ver o histórico de uma pessoa, o admin precisa
abrir uma solicitação dela.

## Decisões tomadas no brainstorming

| Decisão | Escolha | Razão |
|---|---|---|
| Quem acessa | Só admin, nas duas telas | O diretório é informação sobre terceiros; um usuário padrão não tem o que fazer com ela |
| Cargo na empresa | **Fora.** A lista mostra o papel (`role`) | `users` não tem o campo e nada o preencheria — a coluna mostraria "—" para todos. Registrado como ideia no roadmap |
| Escrita | Nenhuma. Ciclo somente leitura | Promover a admin depende do `role` do JWT e só valeria no próximo login; uma UI que promete efeito imediato mentiria |
| Ordenação da lista | Fixa: `name ASC`, sem parâmetro `sort` | Sem coluna ordenável não há lista branca a expressar, e portanto **nenhum validator novo** — ver §1 |
| Busca | Por nome, `ILIKE`, com debounce de 400 ms na URL | Mesmo mecanismo da Home; nenhum padrão novo |
| Reuso do painel | **Extrair o núcleo** compartilhado do `RequesterPanel` | Ver §5: o reuso direto não era possível, e as alternativas eram props de modo ou duplicar a regra |
| Onde vive o spec | `Refund-api` | Convenção do ciclo cross-repo anterior (`2026-08-10-first-deploy-railway-design.md`) |

Alternativas descartadas, registradas:

- **`GET /users` com `sort`/`order` como o de refunds.** Não há caso de uso hoje;
  quando houver, ligar é a mesma dupla de barreiras já provada (lista branca no
  validator, `SORTABLE_COLUMNS` no repositório).
- **Tornar `currentRefundId` e o cabeçalho opcionais no `RequesterPanel`.** Menor
  em linhas, mas cria um componente de dois modos, e uma prop booleana de
  aparência é o começo clássico de um componente que faz coisas demais.
- **Página do membro com consultas próprias.** Duplicaria a montagem dos
  contadores por status em duas telas.

## Escopo, em ordem de risco

### 1. `GET /users` — listagem paginada e buscável (fundação)

A fatia completa do projeto, na forma que `GET /refunds` já usa: rota → composer
→ view → controller → repositório.

- **Repositório** (`models/repositories/users_repository.py` e sua interface):
  `select_users(page, per_page, name)` e a contagem total. Busca por
  `name.ilike(f"%{name}%")`, como `refunds_repository.py:47`. Ordenação
  `name ASC` **com desempate por `id`** — o mesmo motivo do `Refunds.c.id.desc()`
  em `RefundsRepository.__order_by`: sem desempate, `LIMIT/OFFSET` não é
  determinístico e uma linha pode aparecer em duas páginas.
- **Serializador** (`controllers/user_serializer.py`) — **o ponto crítico deste
  ciclo**: `{id, name, email, role, has_avatar, created_at}`, e nunca `password`.
  Módulo próprio pelo mesmo motivo de `refund_serializer.py`: uma forma, um
  lugar, um teste. `has_avatar` é `bool(avatar_filename)`, como o refund já faz —
  o nome do arquivo não é dado do cliente.
- **Controller** (`controllers/user_lister_controller.py`): `if role != "admin":
  raise HttpForbiddenError(...)` **antes de qualquer acesso ao banco**, que é o
  idioma anti-enumeração de `refund_reviewer_controller.py:30`.
- **View + composer + rota**, registrada em `main/routes/user_routes.py` com
  `page: int = Query(1, ge=1)` e `per_page: int = Query(10, ge=1, le=100)`,
  idênticos aos de `list_refunds`.

**Nenhum validator novo, e isso é uma decisão, não um esquecimento.** Os limites
de `page` e `per_page` são impostos pelo `Query(ge=..., le=...)` do FastAPI na
própria rota. O `refund_lister_validator` existe apenas para as listas brancas de
`status`, `sort` e `order`, que o FastAPI só expressaria com o envelope de erro
nativo dele em vez do `{"detail": "..."}` deste projeto. Como esta rota não tem
lista branca a expressar, um validator vazio seria cópia de forma sem conteúdo.

### 2. `GET /users/{user_id}` — um usuário

Reaproveita `select_user_by_id`, que já existe. Controller novo respondendo
**404 e não 403** para quem não é admin, seguindo
`refund_stats_finder_controller.py:19` — a mesma escolha de não confirmar a
existência de um id a quem não pode vê-lo.

**Atenção à ordem das rotas**: o `user_routes` já tem `/{user_id}/avatar` e
`/{user_id}/refund-stats`, e `POST|DELETE /me/avatar`. A rota nova é
`GET /users/{user_id}` com `user_id: int`, então não colide — mas o teste deve
provar isso em vez de assumir.

### 3. Contrato (ADR-007)

`contract/users.json`, o **terceiro** arquivo de contrato, espelhado em
`Refund-FrontEnd/src/features/team/contract/users.json`. O destino segue a regra
já registrada no `contract_test.py`: cada metade cai onde os schemas que a
validam vivem, porque o `eslint-plugin-boundaries` proíbe uma feature ler um
arquivo da camada `app`.

Captura em `src/test_integration/contract_test.py`, com duas particularidades:

- **Precisa da fixture `admin_headers`**, não da `authenticated`: as duas rotas
  são admin-only, e `admin_headers` promove por `UPDATE` direto porque o cadastro
  sempre cria `standard` (BR-003) e não há endpoint que conceda o papel.
- Com as duas fixtures ativas existem dois usuários ("Ana" e "Chefe"), o que dá
  uma lista de verdade para o snapshot em vez de uma de um item.

Lembrar do que o próprio `contract_test.py` avisa: ele pega "a API mudou e o
contrato não foi regerado", mas **não** pega "o contrato foi regerado e a cópia
do frontend não". A cópia é manual.

### 4. Documentação canônica

- `docs/use-cases/UC-015-list-users.md` e `UC-016-view-user.md`, com as entradas
  em `docs/index.md`.
- **BR-025** em `docs/business-rules.md` (a última é a BR-024): o diretório é
  restrito a administradores, com 403 na listagem e 404 na consulta individual, e
  a razão da diferença — a listagem não revela nada sobre um id específico, então
  pode ser honesta sobre a falta de permissão; a consulta individual, se
  respondesse 403, confirmaria que aquele id existe.

### 5. Extrair o núcleo do `RequesterPanel`

O panorama registrou que a página do membro reaproveitaria o `RequesterPanel`
direto. **Ao ler o componente, não era possível**: ele exige
`currentRefundId: number` — âncora do destaque da linha e das setas de navegação,
dois conceitos que só existem numa revisão — e desenha o nome da pessoa no
próprio `CardHeader`, que na página do membro apareceria duas vezes, já que o
cartão de identidade mostra o nome.

Nasce `components/RefundStatsPanel.tsx` com o que as duas telas querem: a rosca
de contagens por status e a primeira página das solicitações daquela pessoa.
Props:

| Prop | Tipo | Papel |
|---|---|---|
| `userId` | `number` | De quem são as estatísticas e a lista |
| `userName` | `string` | Só para o link "ver todas na Home" |
| `viewer` | `RefundViewer \| null` | Destino de cada linha via `getRefundHref` |
| `currentRefundId` | `number \| undefined` | Qual linha destacar; ausente = nenhuma |
| `headerActions` | `ReactNode \| undefined` | Slot à direita do título da lista |

**Por que um slot `ReactNode` e não um `showArrows` booleano.** Os dois eliminam
o `if` do componente, mas fazem coisas diferentes: um booleano de aparência
mantém a decisão *dentro* do componente e cresce em número a cada tela nova; um
slot devolve a decisão ao chamador, que passa o que quiser ali — inclusive nada.
É composição em vez de configuração. `currentRefundId` continua sendo um dado, e
opcional porque "nenhuma linha destacada" é um estado legítimo, não um modo.

O `RefundStatsPanel` **não renderiza `Card` nem título**: quem monta decide o
invólucro. Isso é o que resolve o nome duplicado.

`RequesterPanel` fica sendo o invólucro fino da tela de revisão: `Card` +
`CardHeader` com o nome + `RefundStatsPanel` recebendo `currentRefundId` e as
duas setas no `headerActions`. `NavigationArrow` vai com ele — é navegação de
revisão, não de estatísticas.

A importação `lazy(() => import("./RefundDonutChart"))` migra para o
`RefundStatsPanel`, e a razão dela precisa migrar junto: o donut **não pode** ser
reexportado pela fachada, senão os 74,2 kB gzip do chunk voltam para o bundle de
entrada sem erro nenhum (ver [`performance-budget.md`](../../performance-budget.md)).
Quem passa a ser exportado pela fachada é o `RefundStatsPanel`, que faz o
`import()` dinâmico por dentro — exatamente o arranjo que já mantém a divisão de
pé hoje.

**Dívida adjacente que este corte obriga a pagar**: o `RequesterPanel` tem quatro
strings em português cru, fora do i18n — o título "Solicitações", o vazio
"Nenhuma solicitação encontrada.", a mensagem de erro da lista e o link "Ver
todas as solicitações de … na Home". Extrair o núcleo levaria texto não traduzido
para uma segunda tela, e há teste de paridade entre catálogos
(`src/locales/catalogues.test.ts`). As quatro entram nos **dois** catálogos; a do
link tem interpolação de nome.

### 6. Feature `team` no frontend

Feature nova `src/features/team/`, atrás da fachada `index.ts`, espelhando
`features/refunds`:

- `api/userQueries.ts` — `userKeys` hierárquico, `userListQuery` e
  `userDetailQuery` como `queryOptions`, com `signal` repassado ao axios e Zod na
  fronteira. Mesmo arranjo de `refundQueries.ts`, para o loader e o hook
  compartilharem a mesma entrada de cache.
- `schemas/user.ts` — `userSchema`, resposta de lista e
  `userListSearchParamsSchema` com `.catch()` por campo, para um parâmetro de URL
  digitado errado cair no padrão em vez de pôr a página em `isError`.
- `constants/pagination.ts` — `USERS_PER_PAGE = 10`, importado pelo hook **e**
  pelo loader, para não divergirem.
- `hooks/useUsers.ts`, `hooks/useUser.ts`.
- `components/UsersTable.tsx` — TanStack Table com `getCoreRowModel` apenas.
  Colunas: nome, e-mail, papel (`Badge`) e membro desde. Nenhum cabeçalho
  clicável, porque a API não aceita ordenação — um cabeçalho que parecesse
  clicável ou não faria nada, ou ordenaria as 10 linhas da página.
- `contract.test.ts` validando `userSchema` contra o snapshot.

A feature `team` **não pode** importar `features/refunds` (irmãs são proibidas
pelo `eslint.config.js:39-62`). Quem compõe as duas é a página, camada `app`.

### 7. Páginas, rotas e a guarda de admin

- `src/pages/PageTeam.tsx` — busca, tabela e paginação. A busca reaproveita
  `src/hooks/useDebouncedValue.ts` (400 ms) e o padrão URL-como-estado do
  `RefundSearch` (`PageHome.tsx:40-73`), inclusive o `key={name ?? ""}` que
  remonta o input quando a URL muda por fora.
- `src/pages/PageTeamMember.tsx` — cartão de identidade (nome, e-mail, papel,
  membro desde) e, abaixo, `RefundStatsPanel` no seu próprio `Card`.
- `src/router.tsx` — `/team` e `/team/:id`, lazy, com `handle: { titleKey }`.
- `src/router-loaders.ts` — `teamLoader` (normaliza `page` e `name`, redireciona
  para omitir da URL o que é o padrão, `ensureQueryData`) e `teamMemberLoader`.
- **`requireAdmin()` extraído**: hoje a única checagem de papel em loader está
  embutida no `reviewLoader` (`router-loaders.ts:126`). Duas rotas novas
  precisando dela é o momento de virar função. Não-admin recebe
  `throw redirect("/")`. Continua sendo guarda **de interface**: a autorização
  real é a de §1 e §2, e é ela que os testes de backend provam.
- `nav-items.tsx` — item de Time com `enabled: true` e campo novo
  `adminOnly?: boolean`; `Sidebar.tsx` filtra por papel.
- ⚠️ `Sidebar.test.tsx` afirma `getAllByText("em breve")` com **3**; passa a
  **2**.

## Arquitetura

Backend, `Refund-api/src/`:

- `models/repositories/users_repository.py` (+ interface) — `select_users` e a contagem
- `controllers/user_serializer.py` — novo, a forma pública do usuário
- `controllers/user_lister_controller.py` (+ interface) — 403 antes do banco
- `controllers/user_finder_controller.py` (+ interface) — 404 para não-admin
- `views/user_lister_view.py`, `views/user_finder_view.py` — novas
- `main/composer/user_lister_composer.py`, `user_finder_composer.py` — novas
- `main/routes/user_routes.py` — duas rotas novas
- `test_integration/contract_test.py` — captura de `users.json`

Frontend, dentro da feature `src/features/team/`: `api/userQueries.ts`,
`schemas/user.ts`, `constants/pagination.ts`, `hooks/useUsers.ts`,
`hooks/useUser.ts`, `components/UsersTable.tsx`, `contract/users.json`.

Dentro de `src/features/refunds/`: `components/RefundStatsPanel.tsx` (novo, o
núcleo extraído) e `components/RequesterPanel.tsx` (reduzido a invólucro). A
fachada troca a exportação de `RequesterPanel` por **as duas** — a tela de
revisão continua usando a primeira, a página do membro usa a segunda. O donut
segue **não** exportado.

Fora das features: `src/pages/PageTeam.tsx`, `src/pages/PageTeamMember.tsx`,
`src/router.tsx`, `src/router-loaders.ts` (`requireAdmin`),
`src/components/core/nav-items.tsx`, `src/components/core/Sidebar.tsx`, e os dois
catálogos de locale.

## Testes

Suíte atual: **frontend 318 testes em 55 arquivos**; **backend 341 testes**
(mais 72 desmarcados, os de integração). Ambas verdes antes de abrir a branch.

Backend:

- `user_serializer` — **`password` ausente da saída**. É o teste mais importante
  do ciclo: um campo sensível numa lista de usuários é o pior defeito possível
  aqui, e o serializador único é o que torna isso provável de uma vez.
- `select_users` — paginação, busca por nome parcial e case-insensitive, e o
  desempate por `id` produzindo ordem estável entre páginas.
- `user_lister_controller` — admin recebe a lista; **não-admin recebe 403 sem que
  o repositório seja chamado** (asserção no mock, não só no status).
- `user_finder_controller` — admin recebe; não-admin recebe **404**; id
  inexistente recebe 404. Os dois últimos indistinguíveis, que é o objetivo.
- Rotas, por HTTP: as duas novas, e uma prova de que `GET /users/{id}` não
  captura `/users/{id}/avatar` nem `/users/{id}/refund-stats`.
- Integração: o contrato de `users.json`.

Frontend:

- `userListSearchParamsSchema` — válidos, e inválidos caindo no padrão.
- `teamLoader` — parâmetro igual ao padrão sumindo da URL; `requireAdmin`
  redirecionando o usuário padrão.
- `UsersTable` — as quatro colunas; papel renderizado como badge; nenhum
  cabeçalho é botão.
- `PageTeam` — busca com debounce escrevendo na URL e resetando `page`; estados
  de carregando, erro e vazio.
- `PageTeamMember` — identidade renderizada; o painel presente; o nome **não**
  duplicado.
- `RefundStatsPanel` — sem `currentRefundId`, nenhuma linha tem
  `aria-current="page"`; sem `headerActions`, nenhuma seta; com os dois, ambos.
- `RequesterPanel` — **os testes existentes devem passar sem alteração de
  comportamento**. Se algum precisar mudar, a extração mudou a tela de revisão,
  o que não é o objetivo.
- `Sidebar` — item de Time visível para admin, **ausente** para usuário padrão; e
  a contagem de "em breve" em 2.
- Handlers do MSW para `GET /users` e `GET /users/{id}`, honrando `name` e
  `page` — um handler que ignora a busca provaria só que o componente renderiza
  uma lista.

Um teste de acessibilidade (`.a11y.test.tsx`) para `PageTeam`, seguindo os que já
existem para `PageHome` e `PageRegister`.

## Verificação

Backend: `pytest` e `pylint src; echo $?` — **o código de saída, não a nota**.
Como o ciclo toca repositórios, também `docker compose up -d` e
`pytest -m integration`, que é o único caminho que gera `users.json`.

Frontend, na ordem do CI: `npm run typecheck`, `npm run lint` (0 erros e 0
warnings, com o ponto de partida medido **antes** de abrir a branch),
`npx vitest run`, `npm run build`.

**Ler a saída do `npm run build`, não só o código de saída.** A extração de §5
mexe justamente no arranjo que mantém o donut num chunk separado: enquanto houver
uma linha `dist/assets/RefundDonutChart-*.js`, a divisão está de pé. Se o `index`
engordar ~74 kB, o `RefundStatsPanel` foi importado estaticamente em algum lugar.

Navegador, contra a API real em `localhost:3333`, com checklist item a item:

- Com **admin**: Time aparece na sidebar; a lista pagina e busca; clicar numa
  pessoa abre a página dela; o nome aparece **uma** vez.
- Com **usuário padrão**: Time **não** aparece na sidebar, e `/team` digitado na
  barra de endereço redireciona.
- Tela de revisão **inalterada**: destaque da linha atual e as duas setas
  funcionando como antes da extração.
- Claro e escuro (o cromo do donut depende do tema) e 390 × 844, medindo overflow
  por `scrollWidth` contra `clientWidth`.

## Consequências e pendências

- **`GET /users` não ordena.** Ordenação por e-mail, papel ou data de cadastro
  fica para quando houver caso de uso.
- **A lista não mostra foto.** `has_avatar` continua sem consumidor; iniciais,
  como a sidebar.
- **Sem cargo na empresa.** A coluna mostra o papel; o cargo depende de coluna
  nova e de um caminho de escrita.
- **A cópia de `users.json` no frontend é manual**, com a mesma lacuna que o
  `contract_test.py` já registra para os outros dois.
- **O `role` do JWT não é reconsultado no banco.** Um usuário promovido enquanto
  está logado continua vendo a interface de padrão até sair e entrar. Vale para
  todo o sistema; a tela de Time só torna isso visível.
- **`RequesterPanel` encolhe e a fachada cresce em um item.** Se a página do
  membro nunca precisar divergir da tela de revisão, a extração terá sido custo
  sem retorno — registrado como aposta, não como certeza.

## Fora de escopo

- **Promover ou rebaixar admin** e **desativar usuário** — cada um é produto
  novo, com ciclo próprio.
- **Dashboard e Calendário** — Ciclos 2 e 3 do panorama.
- **Foto de perfil** — segue como a pendência de produto já registrada.
- **Convidar ou cadastrar usuário pelo admin** — o cadastro segue público.
- **E2E** — adiado desde o Item 6.
