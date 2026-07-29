# Estado atual do projeto

Este documento é um retrato do projeto para dar contexto a sessões futuras
(humanas ou de agentes de IA). Ele descreve o que existe hoje, onde estamos na
trilha de aprendizado e o que fazer a seguir. Não é fonte de requisitos — os
requisitos canônicos ficam nos demais documentos de [`docs/`](../index.md).

Ao retomar a trilha, leia também o
[`learning-path-workflow.md`](learning-path-workflow.md), que define como cada
item deve ser explicado, aprovado, implementado, verificado, documentado e
commitado, e o [`learning-path-progress.md`](../learning-path-progress.md), que
preserva exemplos e aprendizados dos itens concluídos.

Atualizado em: 2026-07-29.

## Visão geral

O produto é um sistema de **reembolso de despesas com comprovante**. São dois
repositórios Git irmãos e independentes, cada um com seu remote. O `Refund-api`
está na `main` (`ef7c60f`); o `Refund-FrontEnd` está na branch
`feat/frontend-contract-and-receipt` (`39e0683`), **ainda sem merge** — ver
pendências:

- **`Refund-api`** — backend Python + FastAPI, Clean Architecture pragmática.
- **`Refund-FrontEnd`** — frontend React 19 + TypeScript + Vite.

Ambos vivem dentro do diretório de trabalho `ToBeBetter/`, que **não** é um
repositório Git. Na raiz desse diretório (fora do controle de versão) estão três
documentos que guiam a evolução do projeto:

- `learning_path.md` — a trilha da situação atual até a arquitetura-alvo.
- `arquitetura_ideal_adaptada.md` — o blueprint arquitetural de destino.
- `desenvolvimento_com_ia.md` — a metodologia doc-first de trabalho com IA.

Visão, usuários e escopo estão em [`docs/vision.md`](../vision.md).

## Como rodar

- Backend: ver [`README.md`](../../README.md) do `Refund-api` (sobe em
  `localhost:3333`; PostgreSQL no Neon via `DATABASE_URL`).
- Frontend: ver `README.md` do `Refund-FrontEnd` (Vite em `localhost:5173`;
  espera a API em `localhost:3333`).

## Arquitetura (resumo)

### Backend — fluxo em camadas

```
rota FastAPI -> HttpRequest interno -> composer (injeção de dependência)
  -> view (try/except + error_handler) -> validator -> controller (regra + autorização)
  -> repository/driver (por interface) -> HttpResponse
```

A autorização mora no controller (não no repository). Decisões de segurança
notáveis: 404 tanto para "não existe" quanto para "não é seu" (evita enumerar
IDs); mensagem genérica no login; validação de comprovante por extensão, não pelo
`Content-Type` do cliente. Cada camada tem seu `_test.py` ao lado.

### Frontend — design system shadcn/ui + feature module

`src/components/ui` é o design system: componentes **copiados do registry do
shadcn/ui** (`npx shadcn@latest add <componente>`) e versionados aqui, escritos
com `cva` + `clsx` sobre o helper `cn()` de `src/lib/utils.ts`. Os tokens de cor
ficam em `src/index.css`, no vocabulário do shadcn (`--background`,
`--foreground`, `--primary`, `--border`, `--sidebar-*`…), com dark mode via
`@custom-variant dark (&:is([data-theme="dark"] *))` — o `data-theme` continua
sendo escrito pelo `ThemeEffect` a partir da store Zustand (Item 12).
`src/components/core` guarda a composição do shell (MainLayout, Sidebar,
Topbar). Ícones são só do `lucide-react`; o único SVG local é o `Receipt.svg`
da marca.

Ao redor: `pages/` (prefixo `Page`), `features/refunds/` com fachada pública
(Item 8), `stores/` (Zustand), `hooks/`, `context/` (Auth via Context +
`localStorage`), `lib/` (Axios com interceptors) e `schemas/` (Zod). Server
state via TanStack Query; formulário e responses consumidos validados com Zod. O
React Router usa Data Mode com loaders, páginas lazy e erro de rota; busca e
paginação da Home vivem em search params validados. As camadas
(`app`/`feature`/`ui`/`shared`) são verificadas pelo `eslint-plugin-boundaries`
(Item 9).

`src/components/{atoms,molecules}` **não existem mais** — foram substituídos por
`src/components/ui` no ciclo do restyle.

## Trilha de aprendizado — onde estamos

### Método acordado

Percorrer o `learning_path.md` **item por item, na ordem das fases**, com
**aprendizado acima de velocidade**. Para cada item, antes de implementar:
(1) explicar o conceito e por que é interessante; (2) comparar com o estado atual
do código; (3) mostrar o custo de não fazer; (4) implementar explicando os
conceitos novos. Um item por vez, com comparação visual, aprovação antes da
implementação e verificação, documentação e commits antes de avançar. O processo
completo e obrigatório está em
[`learning-path-workflow.md`](learning-path-workflow.md).

### Progresso

- **Fase 1, Item 1 — Server state vs client state: CONCLUÍDO.**
  Commit `refactor: centralize refund query keys/options and tune query client`
  no repo `Refund-FrontEnd`. O que mudou:
  - `src/lib/query-client.ts` (novo): `QueryClient` com defaults conscientes
    (`staleTime` 30s, `retry` 1, `refetchOnWindowFocus` false).
  - `src/hooks/refundQueries.ts` (novo): fábrica `refundKeys` (fonte única das
    chaves de cache, hierárquicas sob `["refunds"]`) + `refundListQuery` /
    `refundDetailQuery` (`queryOptions` reutilizáveis) com `AbortSignal`.
  - `useRefunds`/`useRefund` consomem os `queryOptions`; `useCreateRefund`/
    `useDeleteRefund` invalidam via `refundKeys.all`.
  - Verificação: `npx tsc -b --noEmit` passou (exit 0). Runtime ainda **não**
    validado contra a API (depende de subir backend + banco).

- **Fase 1, Item 2 — Schemas como fronteira: CONCLUÍDO.**
  - `src/schemas/auth.ts`: `loginResponseSchema` e tipo derivado.
  - `src/schemas/refund.ts`: schemas de `Refund`, listagem, detalhe e criação;
    tipos derivados substituem `src/types/refund.ts`, que foi removido.
  - Login, listagem, detalhe e criação recebem o response Axios como `unknown` e
    executam `schema.parse` antes de usar, armazenar ou colocar dados no cache.
  - O contrato da criação reflete que a API não retorna `created_at`.
  - Verificação: `npx tsc -b --noEmit` e `npm run build` passaram; runtime contra
    a API real ainda não foi validado.

- **Fase 1, Item 3 — React Router data APIs e estado na URL: CONCLUÍDO.**
  - `src/router.tsx`: `createBrowserRouter`, layouts preservados, páginas lazy e
    `PageRouteError` como erro de rota.
  - `src/router-loaders.ts`: loaders da Home e detalhe verificam a sessão e usam
    `queryClient.ensureQueryData` com os `queryOptions` do Item 1.
  - `src/schemas/refund.ts`: `page` e `name` validados/coagidos; URLs inválidas
    são normalizadas antes da consulta.
  - `PageHome` usa loader data e search params; busca debounced reinicia página,
    paginação atualiza o histórico e valores padrão são omitidos da URL.
  - Verificação: typecheck e build passaram; chunks separados foram gerados.
    HTTP local respondeu corretamente, mas o fluxo visual/autenticado ficou
    pendente porque não havia navegador conectado.

- **Fase 2, Item 4 — Vitest, Testing Library e user-event: CONCLUÍDO.**
  Primeira infraestrutura de testes do frontend (Vitest + jsdom + Testing
  Library + user-event), no repo `Refund-FrontEnd`. O que mudou:
  - `vite.config.ts`: `defineConfig` do `vitest/config` + bloco `test`
    (`environment: "jsdom"`, `setupFiles`).
  - `src/test/setup.ts` (novo): matchers do jest-dom + `afterEach(cleanup)`
    (necessário por rodarmos com imports explícitos, sem `globals`).
  - `package.json`: scripts `test`/`test:watch` e devDeps de teste.
  - Testes colocados: `src/lib/format.test.ts`, `src/schemas/refund.test.ts`,
    `src/components/core/ProtectedRoute.test.tsx`, `src/pages/PageLogin.test.tsx`.
  - Verificação: `npm run test` (15 testes verdes), `npx tsc -b --noEmit`
    (exit 0) e `npm run lint` (18 erros preexistentes, 0 novos).

- **Fase 2, Item 5 — MSW (Mock Service Worker): CONCLUÍDO.**
  Mock de rede para testes (node server), no repo `Refund-FrontEnd`. O que mudou:
  - `src/test/msw/handlers.ts` + `server.ts`: handlers *happy-path* de login,
    lista, detalhe, criação e exclusão, com caminhos `*` (independentes do host).
  - `src/test/setup.ts`: ciclo `listen`/`resetHandlers`/`close` +
    `localStorage.clear` no `afterEach`.
  - `src/test/utils.tsx`: `QueryWrapper` para `renderHook`.
  - Testes de integração: `src/hooks/refundQueries.test.tsx` (fecha a dívida dos
    schemas de response do Item 2), `src/pages/PageLogin.integration.test.tsx`
    (login real + token + 401) e `src/hooks/useCreateRefund.test.tsx` (criação +
    422 via `server.use`).
  - `@vitest/ui` integrado (script `test:ui` → `vitest --ui`).
  - Verificação: `npm run test` (23 testes verdes), `npx tsc -b --noEmit`
    (exit 0), `npm run lint` (18 preexistentes, 0 novos).

- **Correções de runtime (2026-07-25).** A validação do app no navegador (backend
  + banco reais) revelou dois bugs na exclusão de reembolso, ambos corrigidos com
  teste (detalhes no [diário](../learning-path-progress.md)):
  - **Frontend:** `invalidateQueries` não refazia a lista **inativa** (some por
    até `staleTime`) e ainda rebuscava o detalhe do item deletado. Ajuste: nova
    `refundKeys.lists()` + `refetchType: "all"` em `useDeleteRefund`/
    `useCreateRefund`. Teste: `src/hooks/useDeleteRefund.test.tsx`.
  - **Backend:** `DatabaseConnectionHandler` era um singleton com sessão mutável
    compartilhada (`self.session`), causando 500 e vazamento de conexão sob
    concorrência. Ajuste: sessão por-operação via `@asynccontextmanager connect()`.
    Teste: `src/models/settings/database_connection_handler_test.py`.

- **Fase 2, Item 6 — Pirâmide de testes frontend: CONCLUÍDO.**
  Testes de componente isolados para o design system, no repo `Refund-FrontEnd`:
  - `src/components/molecules/Button.test.tsx`, `Dialog.test.tsx`,
    `InputText.test.tsx` — comportamento acessível (role, nome, clique, abrir/
    fechar, digitação, erro), não classes.
  - Mapa da suíte por nível registrado no [diário](../learning-path-progress.md);
    **E2E adiado** (só documentado, com fluxo candidato nomeado).
  - Verificação: `npm run test` (32 testes verdes), `npx tsc -b --noEmit`
    (exit 0), `npm run lint` (18 preexistentes, 0 novos).

- **Fase 2, Item 7 — Acessibilidade prática: CONCLUÍDO.**
  Melhorias de a11y nos formulários, no repo `Refund-FrontEnd`:
  - `InputText` com label associada (`htmlFor`/`id`) + `aria-invalid`/
    `aria-describedby`; `Button` com `aria-busy` e ícone `aria-hidden`.
  - `PopOverMenu`: trigger virou botão operável por teclado (bug achado pelo axe).
  - `vitest-axe` + auditorias (`PageRegister`, `RefundFormDialog`); foco no
    primeiro erro verificado e testado.
  - Verificação: `npm run test` (38 testes verdes), `npx tsc -b --noEmit`
    (exit 0), `npm run lint` (18 preexistentes, 0 novos).

- **Fase 3, Item 8 — Feature-based architecture: CONCLUÍDO.**
  Commit `1594d0f` (`refactor: colocate refunds into a feature module with a
  public façade`) no repo `Refund-FrontEnd`. Migrou **apenas** a feature de
  reembolsos para `src/features/refunds/` (`api`, `hooks`, `schemas`,
  `components`, `constants`) com uma **fachada pública** `index.ts` — o resto do
  app importa da fachada, nunca do interior. Páginas ficaram **fora** (shells que
  consomem a feature), seguindo bulletproof-react / FSD; `router.tsx` intocado.
  Design system, `lib`, auth e `hooks/useDebouncedValue` seguem neutros. Sem
  mudança de comportamento (38 testes só relocados). Verificação: `npm run test`
  (38 verdes), `npx tsc -b --noEmit` (exit 0), `npm run lint` (18 preexistentes,
  0 novos) + grep de sanidade (ninguém importa o interior; feature não depende de
  `pages/`).

- **Fase 3, Item 9 — Boundaries verificáveis pelo ESLint: CONCLUÍDO.**
  Commit `4bab16e` (`feat: enforce feature boundaries with @/ aliases and
  eslint-plugin-boundaries`) no repo `Refund-FrontEnd`. O que mudou:
  - **Alias `@/`**: `tsconfig.app.json` (`paths`, sem `baseUrl` deprecado) e
    `vite.config.ts` (`resolve.alias`, herdado pelo Vitest). Os `../../../` da
    feature viraram `@/...` — paga a dívida do Item 8.
  - **`eslint-plugin-boundaries` (v7)**: `eslint.config.js` classifica pastas em
    camadas (`feature`, `ui`, `shared`, `app`) e a regra `boundaries/dependencies`
    proíbe `ui/shared → feature`, imports entre features (`relationship` diferente
    de `internal`) e furar a fachada (`app → feature` só via
    `fileInternalPath: index`). Resolver `@/` no lint via
    `eslint-import-resolver-typescript`.
  - Decisão registrada: `components/core` é camada **app** (não se aplicou o
    `core → ui` literal do `learning_path.md`, que era exemplo genérico).
  - Verificação: `npx tsc -b --noEmit` (exit 0), `npm run test` (38 verdes),
    `npm run build` (ok), `npm run lint` (18 preexistentes, 0 de boundaries,
    0 warnings) + 2 violações temporárias capturadas pela regra e revertidas.

- **Ciclo de feature — Shell do app (sidebar + topbar + tema): CONCLUÍDO.**
  Primeiro ciclo de feature interligado à trilha (brainstorming → spec → plano →
  execução; artefatos em `Refund-FrontEnd/docs/superpowers/`). Mesclado na `main`
  do `Refund-FrontEnd` (branch `feat/app-shell`, fast-forward; HEAD `957c5b1`).
  Cobriu **Item 12 (Zustand)** — store `src/stores/ui.ts` persistida (tema +
  sidebar) — e o **Item 10 (Pattern layer) reinterpretado** — integrar/tematizar
  `react-pro-sidebar` em vez de construir um pattern. O que mudou: `MainLayout`
  virou Sidebar + Topbar + Outlet; tema por **variáveis CSS** (tokens semânticos
  claro/escuro em `index.css`, migração dos 16 arquivos que usavam a paleta fixa);
  `@mui/icons-material`; `Header`/`NavLink` removidos; fix dos ícones svgr
  (`fill="black"` → `currentColor` via `replaceAttrValues`). Perfil é frontend-only
  (iniciais + username do e-mail). Verificação: `npx tsc -b --noEmit` (0),
  `npm run test` (59 verdes), `npm run build` (ok), `npm run lint` (18
  preexistentes, 0 de boundaries). Detalhes no [diário](../learning-path-progress.md).

- **Ciclo de feature — Restyle com shadcn/ui: CONCLUÍDO.**
  Segundo ciclo de feature interligado à trilha (brainstorming → spec → plano →
  execução em 10 tasks com revisão por task; artefatos em
  `Refund-FrontEnd/docs/superpowers/`). **Mesclado nos dois repos:**
  `Refund-FrontEnd` na `main` (o `feat/shadcn-restyle`, `957c5b1..b66aa16`,
  14 commits) e `Refund-api` na `main` (o `feat/refund-list-sum`, `5fae554` + a
  documentação). Depois do merge vieram ajustes manuais de layout do Gabriel
  direto na `main` do frontend (`3929a37`, `f336ae1`, `2d07a8d` e `6326606`).
  Cobriu o **Item 10 (Pattern layer) em segunda passagem** — o
  ciclo do shell integrou uma lib pronta (`react-pro-sidebar`); este **possui o
  código** (o shadcn é um registry, não uma dependência). O que mudou:
  - `src/components/{atoms,molecules}` deletados; nasce `src/components/ui` com
    15 componentes do registry (692 → 2033 linhas de código de componente).
  - `src/index.css` trocou a paleta própria pelos tokens do shadcn; o seletor de
    dark mode continua `data-theme`, via um `@custom-variant`.
  - Shell reescrito sobre `ui/sidebar` + `ui/sheet`; `react-pro-sidebar`,
    `@mui/*`, `@emotion/*`, `tailwind-variants` e `classnames` removidos;
    entraram `lucide-react`, `class-variance-authority` e `clsx`.
  - As 7 telas restiladas; `PageHome` virou layout de painel com faixa de resumo
    (Solicitações + Total), preparando o ciclo do TanStack Table.
  - **Backend:** `select_refunds` devolve `sum_amount_in_cents` calculado na
    **mesma query** do `count`, respeitando filtros e autorização;
    `UC-004` atualizado.
  - Verificação: `npm run test` (75 verdes em 24 arquivos), `npx tsc -b
    --noEmit` (exit 0), `npm run build` (ok, sem o aviso de chunk > 500 kB),
    `npm run lint` (**0 erros, 0 warnings** — primeira vez na trilha),
    `pytest` (73 verdes), `pylint src` (10.00/10).
  - **Estes dois últimos números do frontend ficaram obsoletos depois do merge**,
    e a correção só apareceu no ciclo de 2026-07-29:
    - O commit manual `2d07a8d` deixou um import de `Separator` não usado em
      `src/components/core/Topbar.tsx`. Isso quebrava `npx tsc -b --noEmit`
      (exit 2), `npm run lint` (1 erro) **e** `npm run build` na `main` do
      frontend. Corrigido pelo commit `4e53be4` da branch
      `feat/frontend-contract-and-receipt`.
    - O aviso de chunk > 500 kB **voltou** em algum ponto depois do restyle: o
      bundle principal já estava em **503,57 kB** no ponto de partida do ciclo
      seguinte. Não foi causado por ele.
  - **Validado em navegador em 2026-07-28**, pelo Gabriel, contra um checklist
    derivado das pendências (mantido no Notion, em `Work → ToBeBetter`). Fechou
    contraste claro/escuro, emenda sidebar↔topbar, colapso da sidebar, drawer
    no mobile, faixa de resumo e os runtimes dos Itens 1 e 3. Ficaram **4 itens
    abertos** — ver pendências. Detalhes no
    [diário](../learning-path-progress.md).
  - **Ordem de merge/deploy: o backend precisa ir para produção antes do
    frontend.** `src/features/refunds/schemas/refund.ts` do frontend valida a
    resposta de `GET /refunds` com Zod e declara `sum_amount_in_cents` como
    campo **obrigatório**. Se o `feat/shadcn-restyle` for mesclado e implantado
    antes do `feat/refund-list-sum`, o backend em produção ainda responde sem
    esse campo, o `.parse` do Zod falha em toda listagem, `useRefunds` cai em
    `isError` e a Home passa a mostrar "Não foi possível carregar as
    solicitações" para todo usuário — a tela principal do produto fica
    inutilizável até o backend ser implantado. O caminho inverso é seguro: um
    frontend antigo simplesmente ignora o campo novo, pois o Zod descarta
    chaves desconhecidas por padrão. O merge já aconteceu nos dois repos, então
    a restrição vale agora para o **deploy**: implantar **primeiro** o
    `Refund-api`, **depois** o `Refund-FrontEnd`.

- **Ciclo de feature — Workflow de aprovação (backend): CONCLUÍDO.**
  Terceiro ciclo de feature e o primeiro inteiramente de backend, na branch
  `feat/refund-approval-workflow` do `Refund-api` (`5b50c0f..f083d0b`, 20
  commits). **Mesclado na `main`** pelo merge `177f929` (correção: até
  2026-07-29 este documento afirmava que não estava). Artefatos em
  `docs/superpowers/`
  ([spec](../superpowers/specs/2026-07-28-refund-approval-workflow-design.md),
  [plano](../superpowers/plans/2026-07-28-refund-approval-workflow.md)).
  Cobriu **Item 18 (Alembic)** e **Item 20 (Unit of Work)**. O que mudou:
  - **Schema sob migrations.** `metadata.create_all` saiu do lifespan; o schema é
    governado por `alembic/versions/` e `alembic upgrade head`. Baseline escrito à
    mão (o `autogenerate` sai vazio contra um banco que já bate) e conferido por
    uma migration descartável que precisa sair vazia. `ADR-002` amendada.
  - **`refunds.status`** (`pending`/`approved`/`rejected`, `server_default` fazendo
    o backfill das 41 linhas) e a tabela **`refund_reviews`** com o histórico das
    decisões.
  - **`PATCH /refunds/{id}/status`** — só admin, e nunca a própria solicitação
    (BR-016). Transições reversíveis entre decisões, nunca de volta a `pending`
    (BR-017); rejeição exige justificativa (BR-018). A **ordem das checagens** é
    decisão de segurança: o papel é verificado antes de qualquer consulta ao banco.
  - **`UnitOfWork`** (`src/models/settings/unit_of_work.py`) delimita uma transação
    por caso de uso, com dois repositories sessão-injetada que não commitam. Os
    CRUDs existentes **não** foram refatorados — um write só não precisa de UoW.
  - **Exclusão restrita a pendentes** (BR-015 alterada), com o `DELETE`
    condicional ao status para fechar a corrida com uma aprovação concorrente.
  - `UC-007` novo; `UC-004`/`UC-005`/`UC-006` amendados; `init/promote_admin.py`
    para criar o primeiro admin (o cadastro público só cria `standard`).
  - Verificação: `pytest` (**105 verdes**, partiu de 73), `pylint src`
    (**10.00/10**), ciclo `upgrade`/`downgrade` executado contra o banco real, e
    **10/10 cenários ponta a ponta** contra a API real com os status HTTP
    conferidos um a um. Detalhes no [diário](../learning-path-progress.md).

- **Ciclo de feature — Consulta da listagem e foto de perfil (backend):
  CONCLUÍDO.** Quarto ciclo, na branch `feat/refund-query-and-avatar` do
  `Refund-api` (`3fa42b2..2c2081c`, 19 commits). **Mesclado na `main`** em
  2026-07-29, junto da pilha que estava por cima (ver ciclo seguinte).
  Artefatos em `docs/superpowers/`
  ([spec](../superpowers/specs/2026-07-29-refund-query-and-avatar-design.md),
  [plano](../superpowers/plans/2026-07-29-refund-query-and-avatar.md)).
  Feito antes do frontend de propósito. O que mudou:
  - **`GET /refunds` ganhou `status`, `sort` e `order`**, com listas brancas e 422
    fora delas, e ordenação estável (`id DESC` como desempate). `total` e
    `sum_amount_in_cents` respeitam o filtro.
  - **Objeto `user` aninhado** em toda resposta de reembolso; `user_id` saiu do
    topo. `POST /refunds` passou a reler a linha gravada, unificando as três
    formas.
  - **Foto de perfil:** `users.avatar_filename`, `POST`/`DELETE
    /users/me/avatar`, servida em `/avatars/{filename}`.
  - `ReceiptStorage` virou **`FileStorage`** parametrizado pelo diretório.
  - Dívida de storage: uploads ignorados pelo git, 7 órfãos removidos.
  - Verificação: `pytest` (**154 verdes**, partiu de 105), `pylint src`
    (**10.00/10**), ciclo `upgrade`/`downgrade` real, e **19/19 cenários ponta a
    ponta** contra a API real. Detalhes no [diário](../learning-path-progress.md).
  - **Backend e frontend TÊM de ir para produção juntos** — ver pendências.

- **Ciclo de feature — Servir arquivos com autenticação (backend): CONCLUÍDO.**
  Quinto ciclo, na branch `feat/authenticated-file-serving` (`55be4d4..ba51c4b`,
  8 commits de código), **empilhada sobre `feat/refund-query-and-avatar`**. A
  pilha inteira **foi mesclada na `main`** no início do ciclo do frontend, por
  **fast-forward** (`3fa42b2..ef7c60f`, 33 commits): a `main` do `Refund-api`
  está hoje em `ef7c60f`, com `pytest` 178/178 e `pylint src` 10.00/10 depois do
  merge. Artefatos em `docs/superpowers/`
  ([spec](../superpowers/specs/2026-07-29-authenticated-file-serving-design.md),
  [plano](../superpowers/plans/2026-07-29-authenticated-file-serving.md)).
  Nasceu de uma verificação de rotina que achou `GET /receipts/<uuid>`
  respondendo 200 sem token. O que mudou:
  - **Os dois mounts estáticos saíram.** `FileStorage` ganhou `read() -> bytes`
    (não um caminho — a interface sobrevive ao Item 22).
  - **`GET /refunds/{id}/receipt`** — dono ou admin; "não existe", "não é seu" e
    "arquivo sumiu" respondem 404 **idênticos**, inclusive na mensagem.
  - **`GET /users/{id}/avatar`** — qualquer autenticado; não há decisão de
    autorização a tomar.
  - **`filename` saiu das respostas** e `user.avatar_filename` virou
    `user.has_avatar`, através de um `refund_serializer.py` compartilhado pelos
    três casos de uso de leitura. O repositório continua devolvendo `filename`,
    porque a exclusão o lê para apagar o arquivo.
  - **O login passou a devolver `id`** — sem ele o cliente não tinha como buscar
    a própria foto.
  - Verificação: `pytest` (**178 verdes**), `pylint src` (**10.00/10**), e
    **14/14 cenários ponta a ponta**, incluindo `ls uploads/receipts/` antes e
    depois provando que a exclusão ainda apaga o arquivo.

- **Ciclo de feature — Contrato novo e comprovante autenticado (frontend):
  IMPLEMENTAÇÃO CONCLUÍDA, `main` do frontend AINDA NÃO MESCLADA E NADA VALIDADO
  EM NAVEGADOR.** Sexto ciclo e o primeiro de frontend desde o restyle, na branch
  `feat/frontend-contract-and-receipt` do `Refund-FrontEnd`
  (`6326606..39e0683`, 17 commits), executado em 11 tasks com revisão por task
  mais uma revisão da branch inteira. Artefatos em
  `Refund-FrontEnd/docs/superpowers/`
  ([spec](../../../Refund-FrontEnd/docs/superpowers/specs/2026-07-29-frontend-contract-and-receipt-design.md),
  [plano](../../../Refund-FrontEnd/docs/superpowers/plans/2026-07-29-frontend-contract-and-receipt.md)).
  Não abre item novo: **fecha a lacuna do Item 2** (a sessão persistida em
  `localStorage`, que estava fora daquele item). O **Item 11 (error boundaries)**
  foi considerado e deixado de fora de propósito. O que mudou:
  - **Contrato absorvido.** `src/features/refunds/schemas/refund.ts` passou a
    exigir `user` aninhado e `status`; `user_id` e `filename` saíram.
    `refundBaseSchema` e `refundCreateResponseSchema` foram **removidos** —
    aquele contrato separado existia só porque a criação não devolvia
    `created_at`, e o backend passou a reler a linha gravada.
    `refundDetailResponseSchema` virou `refundResponseSchema`, servindo detalhe
    **e** criação. `loginResponseSchema` ganhou `id`, e `AuthUser` também.
  - **Sessão persistida validada.** `storedUserSchema` + `safeParse` no lugar de
    `JSON.parse(raw) as AuthUser`. **Efeito no deploy: todo usuário logado é
    deslogado uma vez** (as sessões salvas não têm `id`).
  - **Comprovante autenticado.** `getReceiptUrl` removido de `src/lib/api.ts`;
    entram `receiptQuery` (cacheia o **Blob**, sem Zod — a resposta é binária),
    `useReceipt`, o hook compartilhado `src/hooks/useObjectUrl.ts` (cria e
    **revoga** a object URL) e `ReceiptPreview` (imagem ou `<object>` de PDF
    decidido por `blob.type`, com diálogo de tela cheia).
  - **Badge de status somente leitura** na linha da Home e no card de detalhe,
    com variantes já existentes do `ui/badge`.
  - **Ajustes pequenos:** `REFUNDS_PER_PAGE = 10` com fonte única em
    `features/refunds/constants/pagination.ts`, exportada pela fachada; a
    asserção vazia do `PageHome.test.tsx` fechada; import de `Separator` não
    usado removido do `Topbar` (era o que quebrava `tsc`, `eslint` e `build` na
    `main`).
  - Verificação: `npm run test` (**103 verdes em 31 arquivos**, suíte rodada 3×),
    `npx tsc -b --noEmit` (exit 0), `npm run lint` (**0 erros, 0 warnings**),
    `npm run build` (ok; bundle **503,57 → 506,00 kB**, +2,43 kB — o aviso de
    > 500 kB é **pré-existente**), `pytest` (178 verdes) e `pylint src`
    (10.00/10) no `Refund-api` depois do fast-forward.
  - **Validado em navegador em 2026-07-29**, pelo Gabriel, contra o checklist
    derivado da Task 11 do plano: contrato sem erro de parse do Zod, logout
    forçado da sessão antiga, preview do comprovante em imagem e em PDF
    (incluindo tela cheia), badge nos três status e o 404 do comprovante alheio.
    Sem ressalvas. Detalhes no [diário](../learning-path-progress.md).

- **Próximo — o workflow de aprovação na UI.** Depende de mesclar e implantar o
  ciclo acima primeiro (deploy conjunto). O backlog remanescente está na seção
  abaixo.

## Backlog do frontend — o que ainda falta

O ciclo de 2026-07-29 (`feat/frontend-contract-and-receipt`) absorveu o contrato
novo, o comprovante autenticado, o badge de status e os ajustes pequenos. **Essa
branch ainda não foi mesclada** — enquanto isso, a `main` do `Refund-FrontEnd`
continua incapaz de consumir a API atual.

O que resta, em ciclos próprios (um por vez, na ordem do roadmap):

### 1. Workflow de aprovação na UI

Rota de revisão **só para admin**, com o clique do admin indo para lá em vez do
detalhe; aprovar/rejeitar com **motivo obrigatório na rejeição**; **terceiro card
na faixa de resumo** (Pendente/Aprovado), adiado desde o restyle. O badge de
status já existe e é somente leitura. **Decidido:** a tela **não** consome o
corpo do `PATCH` — ela invalida a query e refaz o `GET`, porque aquela resposta
tem forma divergente (ver `UC-007` e as pendências).

### 2. Lista de reembolsos com TanStack Table (Item 13)

Toolbar com filtro por `status` e ordenação por `sort`/`order` **server-side**.
Agora é honesto: a API tem os três parâmetros. **Sem isso, um toolbar
client-side filtraria só as linhas da página** — o erro que originou o ciclo de
consulta da listagem.

### 3. Foto de perfil (upload e exibição)

`POST`/`DELETE /users/me/avatar`, gradiente como padrão, `has_avatar` decidindo
entre foto e gradiente, e exibição no Sidebar e na lista. Os schemas já absorvem
`user.has_avatar`, mas **nenhuma tela renderiza avatar** — exibir antes de
existir upload custaria N requisições autenticadas por página, sem cache do
browser. O `src/hooks/useObjectUrl.ts` foi posto na camada compartilhada
justamente para este ciclo poder reusá-lo sem esbarrar no
`eslint-plugin-boundaries`. Aqui também se decide o
`avatar_filename` cru nas respostas de login/upload/remoção (ver pendências).

As armadilhas do frontend que continuam valendo (`ui/sidebar.tsx` editado à mão,
a altura `h-17.5`, o diretório `./@/` do CLI do shadcn, os polyfills de jsdom em
`src/test/setup.ts`) estão descritas na seção de pendências abaixo.

## Pendências e riscos conhecidos

- ~~**Nenhum arquivo será servido sem autenticação.**~~ RESOLVIDO em 2026-07-29,
  no ciclo próprio: os dois mounts foram removidos e substituídos por
  `GET /refunds/{id}/receipt` (dono ou admin) e `GET /users/{id}/avatar`
  (qualquer autenticado). `GET /receipts/<uuid>` sem token passou de **200** para
  **404**. **Alternativa não escolhida, registrada:** URL assinada de vida curta
  preservaria a privacidade sem custar N fetches por página — é território do
  Item 22.
- **A resposta do login ainda devolve `avatar_filename` cru.** O mesmo vale para
  `POST` e `DELETE /users/me/avatar`. Depois da remoção do mount esse nome não
  resolve para URL nenhuma — o cliente usa `GET /users/{id}/avatar`. As respostas
  de reembolso já convertem para `has_avatar`; estas três não, porque a spec
  daquele ciclo restringiu a conversão de propósito. Não é quebra (o campo é
  ignorável), é inconsistência. **Decisão em aberto** — o ciclo de 2026-07-29
  deixou `avatar_filename` deliberadamente **fora** do `loginResponseSchema` (o
  Zod descarta chaves desconhecidas e não há consumidor sem avatar na tela), de
  modo que a decisão continua adiada para o ciclo da foto de perfil.
- **DECIDIDO em 2026-07-29: a tela de revisão NÃO consome o corpo do PATCH.**
  Em vez de alinhar a forma da resposta de `PATCH /refunds/{id}/status` (que
  exigiria mexer no `select_for_update`, compartilhado com a transação da
  aprovação), o frontend invalida a query e refaz o `GET`. Nenhuma mudança de
  backend. Isso mantém viva a pendência da forma divergente logo abaixo, agora
  como algo deliberado e sem consumidor.

- **DEPLOY CONJUNTO OBRIGATÓRIO — esta quebra não tem lado seguro, e continua
  valendo.** O ciclo de 2026-07-29 tirou `user_id` do topo das respostas de
  reembolso e o moveu para `user.id`. O Zod do frontend na `main` declara
  `user_id` como **obrigatório**: um backend novo com frontend velho falha o
  `.parse` em toda listagem. E o inverso falha igual, porque o frontend da
  branch `feat/frontend-contract-and-receipt` exige `user`. Diferente do
  `sum_amount_in_cents` do ciclo anterior — que tinha uma ordem segura — **aqui
  não existe nenhuma**. Os dois têm de ser implantados no mesmo momento. Se isso
  não for viável, a alternativa é uma versão de transição devolvendo `user_id`
  **e** `user`, removendo `user_id` só depois.
  **Situação em 2026-07-29:** o backend já está na `main` (`ef7c60f`); o frontend
  **não** — a branch com o contrato novo segue sem merge. Implantar o backend
  isoladamente hoje quebraria a Home de todo usuário.
- **Efeito colateral esperado do deploy do frontend: todo usuário logado é
  deslogado uma vez.** O `AuthContext` passou a validar a sessão do
  `localStorage` com `storedUserSchema`, que exige `id` — campo que as sessões
  salvas hoje não têm. Não é bug; é a consequência correta de exigir um campo
  novo. Vale avisar antes de implantar, para não virar chamado de suporte.
- ~~**NADA DO CICLO DO CONTRATO NOVO FOI VALIDADO EM NAVEGADOR.**~~ RESOLVIDO em
  2026-07-29: o Gabriel percorreu no navegador, contra a API real, o checklist da
  Task 11 — login/listagem/detalhe/criação sem erro de parse do Zod, o logout
  forçado da sessão antiga, o preview do comprovante em imagem e em PDF
  (incluindo a tela cheia), o badge nos três status e o 404 do comprovante de
  outro usuário. Tudo passou, sem ressalvas.
- **O endpoint de revisão devolve uma forma diferente das outras.**
  `PATCH /refunds/{id}/status` monta a resposta a partir de
  `RefundStatusRepository.select_for_update`, que continua devolvendo o formato
  achatado com `user_id` no topo — enquanto criação, listagem e detalhe devolvem
  `user` aninhado. Está documentado no `UC-007` e **não** foi corrigido de
  propósito: mudar aquele repositório rippla no workflow de aprovação. Resolver
  quando a tela de revisão for construída.
- **Duas repositories sobre a tabela `refunds`, com formas diferentes.**
  `RefundsRepository.select_refund_by_id` devolve `user` aninhado;
  `RefundStatusRepository.select_for_update` devolve `user_id` achatado. Ambas
  são tipadas `-> Optional[dict]`. Há um comentário na segunda alertando, mas a
  regra que vale é: **um call site segue a forma do método específico que
  consome**, não a "forma da tabela". Essa divergência já quase virou um bug
  durante a correção deste ciclo.

- **`select_for_update` segura uma conexão do pool enquanto espera.** Achado na
  revisão final do ciclo de aprovação e **deliberadamente não corrigido**. O lock
  é tomado dentro da transação do `UnitOfWork` e não há `NOWAIT` nem
  `lock_timeout`. Cenário: três revisões concorrentes da mesma solicitação — A
  segura o lock, B bloqueia ocupando a segunda conexão, e C (qualquer endpoint,
  até um login) espera o `pool_timeout` de 30s e recebe 500. Antes deste ciclo
  nenhum caminho segurava lock durante uma espera, então contenção não conseguia
  esgotar o pool. Conserto: subir o `pool_size` ou definir um `lock_timeout`
  curto nos `connect_args`. Conecta com a pendência do pool pequeno logo abaixo —
  as duas devem ser resolvidas juntas, num item de backend próprio.
- **O ciclo `upgrade`/`downgrade` das migrations é verificado à mão.**
  Automatizá-lo exige um PostgreSQL descartável, que é o **Item 19**. Testar
  migrations em SQLite seria pior que não testar: esconderia justamente as
  diferenças que o Item 19 existe para expor. Limitação aceita e registrada.
- **Existe um admin de teste no banco.** `admin.validacao@example.com` foi criado
  e promovido durante a verificação ponta a ponta do ciclo de aprovação, junto de
  `validacao.visual@example.com` e seus reembolsos de teste. São descartáveis.

- ~~**Uma asserção vazia no teste do `RefundSearch`.**~~ RESOLVIDO em 2026-07-29,
  no ciclo do contrato novo: `src/pages/PageHome.test.tsx` passou a iniciar o
  router em `?page=2` e a afirmar que o parâmetro `page` some depois da busca —
  o ramo de `updateListLocation` em `PageHome.tsx` finalmente tem cobertura real.
  **A prova não foi "o teste passa": foi quebrar o ramo de propósito e ver o
  teste falhar** (a falha lê `"?page=1&name=Ana"`, porque o debounce sempre chama
  `updateListLocation` com `nextPage=1` e a atribuição incondicional sobrescreve
  o `page` no lugar). `PageHome.tsx` ficou byte a byte igual.
- ~~**O restyle inteiro não foi validado em navegador.**~~ RESOLVIDO em
  2026-07-28: o Gabriel percorreu no navegador o checklist derivado destas
  pendências (Notion, `Work → ToBeBetter`). Fecharam contraste no claro e no
  escuro, alinhamento das telas restiladas, a emenda sidebar↔topbar, o colapso
  da sidebar em modo trilho, estado ativo e hover da navegação, o drawer no
  mobile (overlay, Esc, scroll), a Home em tela estreita, a persistência de tema
  e de estado da sidebar, e a faixa de resumo (incluindo o total respeitando o
  filtro, não mudando entre páginas, e o plural de "1 solicitação").
  Daqueles 4 itens abertos, **restam 3** — o primeiro foi fechado em 2026-07-29.
- ~~**Aberto 1/4 — schemas contra a API real (Item 2) segue sem marcação.**~~
  RESOLVIDO em 2026-07-29, na validação do ciclo do contrato novo: login,
  listagem, detalhe e criação foram exercitados no navegador contra a API real
  sem nenhum erro de parse do Zod. O item vinha desde o restyle com evidência
  apenas indireta (os blocos de cache e da faixa de resumo só passavam se o Zod
  tivesse aceitado o payload), e agora tem confirmação direta. Vale registrar o
  que fechou o item: não foi um teste novo, foi alguém abrir o navegador — a
  suíte roda contra o MSW, que por definição devolve o payload que nós mesmos
  escrevemos.
- **Aberto 2/4 — contraste nunca foi auditado com ferramenta.** O checklist
  distingue "contraste parece legível" (marcado, olho humano) de "contraste
  auditado no DevTools/Lighthouse" (não marcado). Só a segunda forma produz
  número de razão de contraste; a primeira não substitui a auditoria e não é
  auditável em teste automatizado (o jsdom não calcula cor).
- **Aberto 3/4 — rejeição de comprovante por tamanho/extensão em runtime.** O
  upload real (`.jpg`/`.png`/`.pdf`) foi validado, mas o caminho de rejeição não.
  Existe teste automatizado para ele (`RefundFormDialog.test.tsx` cobre a
  rejeição por tamanho), então é conferir a mensagem no navegador, não implementar.
- **Aberto 4/4 — o "Choose File / No file chosen" do input nativo.** Marcado como
  *verificado*, não como *resolvido*: o item pedia "decidir se estiliza". O
  `<input type="file">` continua exibindo o texto nativo do browser, em inglês,
  dentro de uma UI toda em português. Decisão ainda em aberto.
- **`src/test/setup.ts` tem um polyfill de jsdom para o Radix Select.** O jsdom
  não implementa a Pointer Capture API nem `scrollIntoView`; sem os no-ops
  (guardados por `if (!…)`, espelhando o polyfill de `matchMedia` que já
  existia), qualquer teste que abra um `ui/select` estoura com
  `TypeError: target.hasPointerCapture is not a function`. Não remova ao ver que
  "nada usa". Nota de processo: o `AGENTS.md` do frontend pede alinhar
  infraestrutura transversal de teste **antes** de introduzi-la, e esta foi
  sinalizada depois do fato. **O ciclo de 2026-07-29 acertou o processo** — o
  stub de `URL.createObjectURL`/`revokeObjectURL` foi sinalizado na spec antes de
  existir — mas produziu uma curiosidade que vale conhecer: **esse stub é um
  no-op neste ambiente.** O `window.URL` do jsdom 29.1.1 realmente não tem os
  dois métodos, só que o `URL` **global** sob o Vitest é o do Node, que os
  implementa (a saída dos testes traz `blob:nodedata:<uuid>`, não o
  `blob:mock/N` do stub). A guarda `if (!URL.createObjectURL)` nunca dispara.
  Fica como rede de segurança para ambientes que não os tenham — e a unicidade
  de que os testes dependem vem da plataforma, não do stub.
- **`src/components/ui/sidebar.tsx` foi editado à mão.** O `SidebarProvider` do
  shadcn escrevia `document.cookie` incondicionalmente, mesmo controlado por
  fora. A escrita e as duas constantes de cookie foram removidas, com um
  comentário no lugar: a store Zustand (`src/stores/ui.ts`) é a fonte única do
  estado de UI (Item 12). **Regerar esse arquivo pelo CLI reintroduz o cookie.**
  Consequência mais ampla: "vendorizado" não é sinônimo de "isento" — arquivos
  de `components/ui` são código do projeto, editáveis e revisáveis como qualquer
  outro.
- **A topbar e o cabeçalho da sidebar têm altura fixa igual de propósito.** Os
  dois carregam `h-17.5` e `border-b` (`src/components/core/Topbar.tsx` e
  `src/components/core/Sidebar.tsx`) para que as bordas de baixo caiam na mesma
  linha horizontal e a emenda entre sidebar e conteúdo fique contínua. **A
  origem é uma tunagem manual do próprio Gabriel**, encontrada não commitada na
  árvore de trabalho durante o ciclo do restyle, guardada como patch e levada
  como requisito para a reescrita do shell — hoje ela está expressa de forma
  diferente da que ele escreveu (o `SidebarHeader` do shadcn precisa também de
  `flex-row`/`p-4` sobrescrevendo os padrões, e do bloco
  `group-data-[collapsible=icon]:*` para o modo trilho). Os tokens `--border` e
  `--sidebar-border` resolvem para o mesmo valor nos dois temas, então a emenda
  é realmente contínua. **Não é ajuste acidental:** quem reformatar o shell
  precisa preservar a igualdade de altura, ou desfaz uma decisão visual
  deliberada sem perceber.
- **Ajuste manual do Gabriel no modal de nova solicitação** (commit `6326606`,
  `fix : category input label width and input icon position on modal`), feito
  durante a validação visual. Duas mudanças com intenção:
  - `RefundFormDialog.tsx`: o `SelectTrigger` da Categoria ganhou `w-full`. O
    `SelectTrigger` do shadcn tem largura por conteúdo, então dentro de um
    `FormItem className="flex-1"` ele ficava estreito e desalinhado do campo
    Valor ao lado. Com `w-full` os dois campos da linha passam a ter a mesma
    largura.
  - `input-file.tsx`: o wrapper ganhou `relative` e o ícone `CloudUpload` virou
    `absolute right-0 mr-4`. Antes o ícone era um irmão em `flex`, ocupando
    espaço *fora* do campo; agora fica sobreposto **dentro** da borda do input,
    à direita.
  - **Ao contrário do `sidebar.tsx`, este arquivo não tem risco de regeneração:**
    `input-file.tsx` é componente **autoral do projeto** (não existe no registry
    do shadcn), então `npx shadcn@latest add` nunca vai sobrescrevê-lo. Vale
    saber que `src/components/ui` mistura as duas origens — arquivos copiados do
    registry e arquivos escritos aqui — e que só os primeiros correm o risco
    descrito no item anterior. O resto do diff do commit é espaço em branco.
- **O CLI do shadcn escreve num diretório literal `./@/` na raiz.** Causa: o
  `tsconfig.json` raiz não tem `paths` (eles vivem no `tsconfig.app.json`, via
  project references) e o CLI só lê o da raiz. Aconteceu nas quatro tasks que
  rodaram o CLI. Depois de cada `npx shadcn@latest add`, mover os arquivos para
  `src/components/ui`, apagar o `./@` e conferir `git diff src/index.css` — o
  CLI também já acrescentou um bloco `.dark { … }` (seletor errado para este
  projeto) sem avisar.
- ~~**Runtime do Item 1 parcialmente validado.**~~ RESOLVIDO em 2026-07-28:
  lista, busca, paginação, criação e detalhe conferidos no navegador, e o
  `staleTime` de 30s verificado na aba Network (voltar à Home dentro da janela
  **não** dispara refetch). A exclusão já tinha sido validada antes, no episódio
  que motivou as correções de runtime acima.
- **Runtime do Item 2 contra a API real ainda pendente.** Os schemas já têm
  testes automatizados: o `refundCreateSchema` no Item 4
  (`src/schemas/refund.test.ts`, via `.shape`) e os schemas de **response** no
  Item 5, exercitados contra o MSW (hoje em
  `src/features/refunds/api/refundQueries.test.tsx`, movido no Item 8 — prova que
  um response malformado vira `isError` em vez de entrar no cache; o ciclo do
  restyle reexerceu isso ao adicionar `sum_amount_in_cents`). Falta apenas a
  validação manual contra o backend real de verdade (não mockado). **Segue
  pendente em 2026-07-29:** o ciclo do contrato novo reescreveu esses schemas
  inteiros (e passou a exercitá-los contra handlers MSW com a forma nova), mas a
  passada no navegador contra a API real continua sem acontecer.
- ~~**`localStorage` ainda usa type assertion.**~~ RESOLVIDO em 2026-07-29:
  `src/schemas/auth.ts` ganhou `storedUserSchema` e o `AuthContext` passou a usar
  `safeParse` (não `parse` — uma sessão inválida deve derrubar a sessão, não a
  aplicação no primeiro render). Fecha a metade do Item 2 que ficara de fora.
  **O `src/router-loaders.ts` lia o mesmo dado e ficou para trás**, com uma
  checagem de presença crua; a divergência foi achada só na revisão da branch
  inteira e corrigida junto (ver a pendência sobre leitores divergentes abaixo).
- ~~**Runtime visual do Item 3 não validado.**~~ RESOLVIDO em 2026-07-28: login,
  URL direta de detalhe, reload, `?name=`, `?page=`, back/forward, normalização
  de parâmetros inválidos, página de erro de rota e omissão dos valores padrão
  da URL — todos conferidos no navegador.
- ~~**Lint do frontend já vermelho antes da trilha.**~~ RESOLVIDO no ciclo do
  restyle: os 18 erros `react-refresh/only-export-components` viviam em
  `atoms/`+`molecules/`, que deixaram de existir. `npm run lint` está em **0
  erros e 0 warnings**. Dois overrides passaram a existir no `eslint.config.js`,
  e a distinção entre eles é deliberada: `react-refresh/only-export-components`
  desligada no diretório `src/components/ui/**` (regra **estrutural** — o
  registry exporta o `cva` ao lado do componente, sem efeito em runtime); e
  `react-hooks/purity` + `react-hooks/set-state-in-effect` desligadas **por
  arquivo, pelo nome** (`src/components/ui/sidebar.tsx` e
  `src/hooks/use-mobile.ts`), porque são regras de **correção** e um componente
  novo que as viole precisa continuar aparecendo no lint.
  **Ressalva (2026-07-29): "0 erros" não é um estado que se conquista uma vez.**
  Entre o merge do restyle e o ciclo do contrato novo, o commit manual `2d07a8d`
  deixou um import não usado no `Topbar` e a `main` do frontend passou a falhar
  em `tsc`, `eslint` **e** `npm run build` — sem ninguém notar, porque nenhum
  ciclo rodou as verificações naquele intervalo. Corrigido pelo `4e53be4`. A
  lição de processo: **medir o ponto de partida antes de abrir uma branch**, ou
  o portão de verificação de todas as tasks seguintes não significa nada.
- **Uma diretiva de lint em `src/hooks/useObjectUrl.ts`.**
  `// eslint-disable-next-line react-hooks/set-state-in-effect` sobre o
  `setUrl(null)`. Vale saber como a regra se comporta: ela reporta **no máximo
  uma violação por corpo de efeito**, então a diretiva silencia o efeito
  **inteiro** — um `setState` acrescentado mais abaixo naquele mesmo efeito não
  seria checado. A alternativa proposta na revisão (comparar identidade do blob)
  esbarra na mesma regra, então trocaria correção por correção, não por um lint
  mais limpo. Há também uma **janela de um render** em que o hook devolve a URL
  antiga logo depois de o blob mudar, antes de o efeito rodar; aceita
  conscientemente.

- ~~**Acessibilidade: labels não associadas ao input.**~~ RESOLVIDO no Item 7:
  `InputText` agora associa `<label htmlFor>`/`id` e o erro via `aria-describedby`.
  (Os testes de login ainda usam placeholder, mas `getByLabelText` já funciona.)
- ~~**A11y do `PopOverMenu`: navegação por setas.**~~ RESOLVIDO no ciclo do
  restyle: o `PopOverMenu` (um `Popover` do Radix com uma lista de `div`s) foi
  substituído pelo `src/components/ui/select.tsx`, um listbox de verdade —
  `role="combobox"` no gatilho, `role="option"` nas opções, com o padrão de
  teclado do WAI-ARIA implementado pelo Radix. **Ressalva:** o teste em
  `RefundFormDialog.test.tsx` prova os papéis, mas dirige a seleção por clique;
  nenhum teste automatizado percorre ↑/↓ — a navegação por seta foi conferida
  **à mão** em 2026-07-28 (funciona), o que confirma o comportamento sem fechar
  a lacuna de teste. Contraste segue não auditável no jsdom (precisa de E2E) e a
  auditoria com ferramenta continua pendente.

- ~~**Campo `file` do `refundCreateSchema` sem teste.**~~ RESOLVIDO no ciclo do
  restyle: `src/components/ui/input-file.test.tsx` faz upload real com
  `userEvent.upload`, e `RefundFormDialog.test.tsx` cobre a rejeição por tamanho
  (`aria-invalid` + descrição acessível). Detalhe aprendido: `userEvent.upload`
  **respeita o atributo `accept`** como um seletor de arquivos real — um arquivo
  de extensão errada é descartado antes de chegar ao `FileList`, então testes de
  rejeição por conteúdo precisam usar extensão válida e tamanho inválido.
- **Referência quebrada.** `AGENTS.md` (dos dois repos) aponta para
  `../../CODING_PROFILE.md`, que não existe na árvore. O perfil de
  desenvolvedor equivalente está hoje no `CLAUDE.md` global do usuário.
- **Fragilidade latente banco+arquivo.** Na criação de reembolso, o comprovante
  é salvo em disco **antes** do insert; se o insert falhar, o arquivo fica órfão
  (o mesmo vale na exclusão). É o Item 21 do `learning_path.md` ("consistência
  entre banco e arquivo"); ainda não tratado.
- **Pool de conexões pequeno.** O `engine` usa `pool_size=2, max_overflow=0`.
  Depois do fix de concorrência não há mais vazamento, mas o limite é apertado
  para carga real; é candidato a ajuste/observabilidade num item de backend
  futuro (não é um bug, é tuning).
- **Boundaries não cobre 4 arquivos-raiz do frontend.** No `eslint-plugin-boundaries`
  v7 um elemento é uma **pasta**, então `App.tsx`, `main.tsx`, `router.tsx` e
  `router-loaders.ts` (soltos em `src/`) ficaram **unknown** e não são checados como
  origem de import. São topo da hierarquia (app); mover para uma pasta `app/`
  resolveria, mas seria churn fora do escopo do Item 9. **Confirmado na prática
  em 2026-07-29:** o plano daquele ciclo afirmava que a regra pegaria um import
  ao interior da feature vindo do `router-loaders.ts`. **Não pegaria.** O import
  escrito está correto de qualquer forma (vai pela fachada), mas a rede de
  segurança alegada não existia — e isso é exatamente o risco desta lacuna:
  acreditar numa proteção que não está ligada.
- **Backend retorna 500 (não 404) via 500 genérico?** Verificado que NÃO: o fluxo
  de "não encontrado" já levanta `HttpNotFoundError` → 404. Os 500 vistos no log
  vinham do bug de concorrência (agora corrigido), não do caminho de not-found.

- **Suspeita não confirmada: `ResizeObserver is not defined` em
  `Sidebar.test.tsx`.** Relatado durante a onda de correções finais do ciclo de
  2026-07-29 como um flake **dependente da ordem de execução**, supostamente
  reproduzível também no baseline intocado (`b86d314`). A suíte completa rodou
  **3× na ponta da branch e não reproduziu**. Fica registrado como suspeita —
  nem confirmado nem refutado. Se aparecer, o caminho é um polyfill guardado em
  `src/test/setup.ts`, no mesmo padrão dos que já existem.
- **`per_page: 10` é literal escrito à mão em `src/test/msw/handlers.ts`.** Não
  deriva de `REFUNDS_PER_PAGE`, então pode voltar a divergir num ajuste futuro —
  a mesma classe de problema que o ciclo acabou de fechar no código de produção.
  Parente disso: o loader stub em `src/pages/PageHome.a11y.test.tsx` ainda
  devolve `perPage: 6`; é inerte (nada o assere), mas está obsoleto contra o
  próprio comentário.
- **`ReceiptPreview` com `refundId=""` renderiza Skeleton para sempre.** O
  `useReceipt` desabilita a query, e uma query desabilitada do TanStack reporta
  `isPending: true` indefinidamente. A prop é `string` obrigatória e hoje só a
  página de detalhe a preenche, então não há caminho real até lá — mas é uma
  armadilha para o próximo consumidor.
- **O nome acessível do botão de tela cheia é sem contexto** ("Ver em tela
  cheia"). Só passa a incomodar se o componente for renderizado mais de uma vez
  na mesma página — que é exatamente o que uma lista com comprovantes faria.
- **`AuthContext.test.tsx`: um dos três testes novos já passava antes.** O que
  restaura uma sessão válida não é vazio (guarda o caminho feliz do
  `storedUserSchema`), mas a prova de que o `id` realmente se propaga descansa
  **só** no segundo teste. Vale saber ao mexer nesse arquivo.
- **O `.venv` do `Refund-api` tem shebangs de um caminho antigo**
  (`.../React/Refund-api`). Consequência prática: `pytest` e `pylint` só rodam
  como `.venv/bin/python3 -m pytest` / `-m pylint`, nunca pelos executáveis
  diretos. É problema de ambiente, não de código — **vale recriar o venv**.
- **Sobrou mais um usuário de teste no banco:** `task1-verify@example.com`
  (id 15), criado na verificação do fast-forward do backend. Não existe endpoint
  de exclusão de usuário. Junta-se a `admin.validacao@example.com` e
  `validacao.visual@example.com`; todos descartáveis.
