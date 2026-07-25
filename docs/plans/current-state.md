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

Atualizado em: 2026-07-25.

## Visão geral

O produto é um sistema de **reembolso de despesas com comprovante**. São dois
repositórios Git irmãos e independentes (cada um com seu remote, ambos na branch
`main`):

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

### Frontend — Atomic Design

`src/components/{atoms,molecules,organisms,core}` para UI; `pages/` (prefixo
`Page`), `hooks/`, `context/` (Auth via Context + `localStorage`), `lib/`
(Axios com interceptors), `schemas/` (Zod) e `constants/`. Server state via
TanStack Query; formulário e responses consumidos validados com Zod. O React
Router usa Data Mode com loaders, páginas lazy e erro de rota; busca e paginação
da Home vivem em search params validados.

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

- **Próximo — Fase 2, Item 7 — Acessibilidade prática:** testar por role/nome
  acessível, associar labels (`htmlFor`/`id`), `aria-invalid`/`aria-describedby`,
  foco no primeiro erro e auditoria com axe. As lacunas já mapeadas alimentam o
  item: label do `InputText` não associada e o spinner do `Button` sem `role`/nome.

## Pendências e riscos conhecidos

- **Runtime do Item 1 parcialmente validado.** A **exclusão** foi exercitada no
  navegador (revelou e motivou as correções de runtime acima). Ainda falta
  conferir lista, busca, paginação, criação, detalhe, e que voltar à Home dentro
  de 30s não dispara refetch.
- **Runtime do Item 2 contra a API real ainda pendente.** Os schemas já têm
  testes automatizados: o `refundCreateSchema` no Item 4
  (`src/schemas/refund.test.ts`, via `.shape`) e os schemas de **response** no
  Item 5, exercitados contra o MSW (`src/hooks/refundQueries.test.tsx` prova que
  um response malformado vira `isError` em vez de entrar no cache). Falta apenas
  a validação manual contra o backend real de verdade (não mockado).
- **`localStorage` ainda usa type assertion.** `JSON.parse(raw) as AuthUser` não
  valida uma sessão persistida; ficou fora do Item 2, restrito a responses HTTP.
- **Runtime visual do Item 3 não validado.** Falta verificar em navegador login,
  URL direta, reload, busca, paginação, back/forward, detalhe, normalização de
  parâmetros e a página de erro. Os serviços locais e respostas HTTP foram
  verificados, mas não havia navegador conectado à sessão.
- **Lint do frontend já vermelho antes da trilha.** 18 erros
  `react-refresh/only-export-components` em arquivos de componentes
  (`Icon`, `Text`, `Button`, `Dialog`, etc.). Não faz parte da trilha; candidato
  a um item futuro de higiene. O Item 4 não alterou essa contagem (0 erros novos).

- **Acessibilidade: labels não associadas ao input.** O `InputText` não liga
  `<label>`/`htmlFor` ao `<input>`, então o teste de login seleciona campos por
  placeholder. É o Item 7 (acessibilidade prática).

- **Campo `file` do `refundCreateSchema` sem teste.** Exige um `FileList`, que o
  jsdom não constrói de forma limpa; ficará coberto pelo teste de upload do
  `RefundFormDialog` (upload real com `user-event`) em item futuro.
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
- **Backend retorna 500 (não 404) via 500 genérico?** Verificado que NÃO: o fluxo
  de "não encontrado" já levanta `HttpNotFoundError` → 404. Os 500 vistos no log
  vinham do bug de concorrência (agora corrigido), não do caminho de not-found.
