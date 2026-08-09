# Progresso de aprendizado

Este diário preserva o que foi aprendido e alterado em cada item do
[`learning_path.md`](../../learning_path.md). O processo obrigatório para
estudar e encerrar um item está em
[`plans/learning-path-workflow.md`](plans/learning-path-workflow.md).

## Fase 1, Item 1 — Server state versus client state

**Status:** concluído em 2026-07-22.

**Commit da implementação:** `2c28133` —
`refactor: centralize refund query keys/options and tune query client`, no
repositório `Refund-FrontEnd`.

### Por que estudar

Os reembolsos são *server state*: representam uma cópia local de dados que
pertencem à API e podem ficar desatualizados. TanStack Query precisa saber por
quanto tempo essa cópia é considerada fresca, como identificar cada consulta e
como cancelar uma requisição que deixou de ser necessária.

Sem políticas explícitas e uma fonte única para as chaves, cada hook podia
descrever o mesmo recurso de maneira diferente. Isso aumenta o risco de
invalidar apenas parte do cache, repetir requisições e duplicar a configuração
quando os loaders do React Router forem introduzidos.

### Estado anterior

Em `Refund-FrontEnd/src/hooks/useRefunds.ts`, a chave e a função de busca viviam
dentro do hook:

```ts
return useQuery({
  queryKey: ["refunds", { page, perPage, name }],
  queryFn: async () => {
    const { data } = await api.get<RefundsListResponse>("/refunds", {
      params: { page, per_page: perPage, name: name || undefined },
    });
    return data;
  },
});
```

As mutações repetiam uma chave escrita manualmente:

```ts
queryClient.invalidateQueries({ queryKey: ["refunds"] });
```

O `QueryClient` era criado sem políticas próprias em
`Refund-FrontEnd/src/main.tsx`:

```ts
const queryClient = new QueryClient();
```

### Comparação visual

```mermaid
flowchart LR
    subgraph Antes
        H1[Hook de lista] --> K1[Chave escrita no hook]
        H2[Hook de detalhe] --> K2[Outra chave escrita no hook]
        M[Mutação] --> K3[Chave repetida manualmente]
    end

    subgraph Depois
        H3[Hook de lista] --> Q[Query options reutilizáveis]
        H4[Hook de detalhe] --> Q
        Q --> F[Factory central de chaves]
        M2[Mutação] --> F
        R[Loader futuro] -. reutilizará .-> Q
    end
```

### Estado ajustado

`Refund-FrontEnd/src/hooks/refundQueries.ts` passou a ser a fonte única das
chaves e opções de consulta:

```ts
export const refundKeys = {
  all: ["refunds"] as const,
  list: (params: RefundListParams) => [...refundKeys.all, "list", params] as const,
  detail: (id: string) => [...refundKeys.all, "detail", id] as const,
};

export function refundListQuery(params: RefundListParams) {
  return queryOptions({
    queryKey: refundKeys.list(params),
    queryFn: async ({ signal }) => {
      const { data } = await api.get<RefundsListResponse>("/refunds", {
        params: { page: params.page, per_page: params.perPage, name: params.name || undefined },
        signal,
      });
      return data;
    },
  });
}
```

`Refund-FrontEnd/src/lib/query-client.ts` tornou explícitas as políticas gerais:

```ts
export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 30_000,
      retry: 1,
      refetchOnWindowFocus: false,
    },
  },
});
```

Os hooks agora consomem a configuração compartilhada, e as mutações invalidam
`refundKeys.all`. O `AbortSignal` fornecido pelo TanStack Query também é
encaminhado ao Axios.

### Arquivos modificados

- Criados `src/hooks/refundQueries.ts` e `src/lib/query-client.ts`.
- Ajustados `src/hooks/useRefunds.ts`, `src/hooks/useRefund.ts`,
  `src/hooks/useCreateRefund.ts`, `src/hooks/useDeleteRefund.ts` e
  `src/main.tsx`.

### Verificações e limitações

- `npx tsc -b --noEmit`: passou com código de saída 0 na sessão de conclusão.
- A validação em runtime contra a API real ficou pendente: ainda é necessário
  conferir lista, busca, paginação, criação, exclusão, detalhe e o comportamento
  de retorno à Home dentro dos 30 segundos de `staleTime`.
- O lint já possuía 18 erros `react-refresh/only-export-components` anteriores
  ao item e não fez parte dessa mudança.

### O que lembrar

- `useState` guarda estado pertencente à interface; TanStack Query administra
  cópias locais de dados pertencentes ao servidor.
- A `queryKey` é a identidade do dado no cache, não apenas um nome para o hook.
- `staleTime` define frescor; não significa que o dado é removido após 30
  segundos.
- Centralizar chaves e `queryOptions` evita divergência entre hooks, mutações e
  futuros loaders.

## Fase 1, Item 2 — Schemas como fronteira

**Status:** concluído em 2026-07-22.

**Commit da implementação:** `e6b8ea5` —
`feat: validate API responses with Zod schemas`, no repositório
`Refund-FrontEnd`.

### Por que estudar

TypeScript verifica o código durante o desenvolvimento, mas seus tipos não
existem quando a aplicação está executando. Um genérico como
`api.get<RefundsListResponse>()` apenas pede que o compilador confie naquele
formato; ele não inspeciona o JSON recebido.

Uma resposta incompatível podia entrar no cache do TanStack Query ou na sessão
antes de o problema aparecer na UI. O Zod transforma o contrato em código
executável: a aplicação só aceita o dado depois de validá-lo na fronteira HTTP.

### Estado anterior

Em `Refund-FrontEnd/src/hooks/refundQueries.ts`, a listagem confiava no genérico
do Axios e devolvia os dados diretamente:

```ts
const { data } = await api.get<RefundsListResponse>("/refunds", {
  params: { page: params.page, per_page: params.perPage, name: params.name || undefined },
  signal,
});
return data;
```

Em `Refund-FrontEnd/src/context/AuthContext.tsx`, `LoginResponse` era uma
interface manual usada da mesma maneira:

```ts
const { data } = await api.post<LoginResponse>("/auth/login", { email, password });
```

Havia ainda uma divergência escondida em
`Refund-FrontEnd/src/hooks/useCreateRefund.ts`: a chamada afirmava receber um
`Refund` completo, embora a criação da API não devolva `created_at`.

### Comparação visual

```mermaid
flowchart LR
    subgraph Antes
        A1[JSON da API] --> A2[Axios]
        T[Tipo TypeScript] -. afirma o formato .-> A2
        A2 --> A3[Cache ou sessão]
    end

    subgraph Depois
        B1[JSON da API] --> B2[Axios como unknown]
        B2 --> Z[Schema Zod]
        Z -->|válido| B3[Dado tipado]
        B3 --> B4[Cache ou sessão]
        Z -->|inválido| E[Erro na fronteira]
    end
```

### Estado ajustado

`Refund-FrontEnd/src/schemas/refund.ts` passou a conter schemas executáveis e
tipos derivados da mesma fonte:

```ts
export const refundSchema = refundBaseSchema.extend({
  created_at: z.string().nullable(),
});

export const refundsListResponseSchema = z.object({
  type: z.literal("Refund"),
  count: z.number().int().nonnegative(),
  total: z.number().int().nonnegative(),
  page: z.number().int().positive(),
  per_page: z.number().int().min(1).max(100),
  total_pages: z.number().int().nonnegative(),
  attributes: z.array(refundSchema),
});

export type Refund = z.output<typeof refundSchema>;
```

A listagem agora trata a resposta como desconhecida até a validação:

```ts
const { data } = await api.get<unknown>("/refunds", {
  params: { page: params.page, per_page: params.perPage, name: params.name || undefined },
  signal,
});
return refundsListResponseSchema.parse(data);
```

O mesmo padrão foi aplicado ao login, detalhe e criação. A criação recebeu um
schema próprio baseado nos campos realmente devolvidos pela API, sem
`created_at`. O arquivo manual `src/types/refund.ts` deixou de ser necessário.

Neste item não houve coerção nas respostas, portanto `z.input` e `z.output`
seriam iguais. `z.output` foi usado para derivar os tipos validados; a diferença
entre entrada e saída continua demonstrada no formulário, onde
`z.coerce.number()` transforma o valor digitado.

### Arquivos modificados

- Criado `src/schemas/auth.ts`.
- Ampliado `src/schemas/refund.ts`.
- Ajustados `src/context/AuthContext.tsx`, `src/hooks/refundQueries.ts` e
  `src/hooks/useCreateRefund.ts`.
- Removido `src/types/refund.ts`.

### Verificações e limitações

- `npx tsc -b --noEmit`: passou com código de saída 0.
- `npm run build`: passou; o Vite manteve o aviso preexistente de chunk acima de
  500 kB, sem falhar o build.
- Auditoria com `rg`: login, listagem, detalhe e criação usam response
  `unknown` seguido de `schema.parse`.
- Não foi introduzido Vitest porque a infraestrutura de testes frontend é o
  Item 4. Os testes automatizados dos schemas serão acrescentados naquele item.
- A validação dos fluxos contra a API real ainda depende de subir frontend,
  backend e banco.
- O `JSON.parse(raw) as AuthUser` do `localStorage` continua sem validação. Essa
  fronteira não é uma resposta HTTP e ficou fora do escopo aprovado.

### O que lembrar

- Tipos TypeScript não validam dados externos em runtime.
- Dados externos devem ser tratados como `unknown` até atravessarem um schema.
- Derivar tipos com `z.output<typeof schema>` evita manter interface e schema
  manualmente em paralelo.
- Schemas devem representar o contrato real: criação e consulta podem devolver
  formas diferentes do mesmo recurso.
- `parse` devolve o dado validado ou lança `ZodError`; assim, dados inválidos não
  entram silenciosamente no cache ou na sessão.

## Fase 1, Item 3 — React Router Data APIs e estado na URL

**Status:** concluído em 2026-07-22.

**Commit da implementação:** `e62a862` (`feat: add data router loaders and URL
state`), no repositório `Refund-FrontEnd`.

### Por que estudar

A Home guardava busca e página somente em `useState`. A interface conhecia a
posição atual, mas a URL continuava `/`. Recarregar a aplicação perdia os
filtros, compartilhar o endereço não reproduzia a mesma tela e o router não
conseguia preparar a consulta antes de renderizar a página.

Loaders são funções do React Router executadas durante a navegação. Eles não
renderizam componentes nem substituem o TanStack Query: descrevem quais dados a
rota precisa antes de ficar pronta. O `QueryClient` continua responsável pelo
server state e `ensureQueryData` garante a query no cache, buscando na API apenas
quando aquela chave ainda não existe.

### Estado anterior

Em `Refund-FrontEnd/src/pages/PageHome.tsx`, busca e página eram memória local:

```ts
const [search, setSearch] = useState("");
const [page, setPage] = useState(1);
const debouncedSearch = useDebouncedValue(search);

const { data } = useRefunds({ page, name: debouncedSearch });
```

Em `Refund-FrontEnd/src/App.tsx`, `<BrowserRouter><Routes>` apenas renderizava os
componentes. Todas as páginas eram importadas no bundle inicial e não existiam
loaders ou erro de rota.

### Comparação visual

```mermaid
flowchart LR
    subgraph Antes
        A1[URL /] --> A2[Renderiza Home]
        A2 --> A3[useState guarda busca/página]
        A2 --> A4[useQuery chama API]
    end

    subgraph Depois
        B1[URL com name/page] --> Z[Zod valida e normaliza]
        Z --> L[Loader da rota]
        L --> E[ensureQueryData]
        E --> C{Query existe no cache?}
        C -->|não| API[queryFn chama API]
        C -->|sim| R[reutiliza dados]
        API --> R
        R --> B2[Home observa cache com useQuery]
    end
```

O `localStorage` e o cache têm funções diferentes:

```text
localStorage       -> token e usuário; permanece após reload
QueryClient cache  -> responses da API; vive em memória nesta configuração
```

Em um reload, a sessão permanece, mas um novo `QueryClient` começa vazio. O
loader verifica a sessão, `ensureQueryData` não encontra a chave e executa a
`queryFn`. Em uma navegação interna com a chave já armazenada, a consulta é
reutilizada.

### Estado ajustado

`Refund-FrontEnd/src/router-loaders.ts` conecta URL, sessão e cache:

```ts
export async function homeLoader({ request }: LoaderFunctionArgs) {
  requireSession();

  const url = new URL(request.url);
  const { page, name } = refundListSearchParamsSchema.parse({
    page: url.searchParams.get("page") ?? undefined,
    name: url.searchParams.get("name") ?? undefined,
  });
  const queryParams = { page, perPage: 6, name };

  await queryClient.ensureQueryData(refundListQuery(queryParams));
  return queryParams;
}
```

O código real também normaliza a URL: remove `page=1` e busca vazia, converte
página inválida para 1 e remove espaços externos do nome antes de consultar.

`Refund-FrontEnd/src/router.tsx` usa `createBrowserRouter`, mantém os layouts e
carrega as páginas com imports lazy. `App.tsx` passou a renderizar somente o
`AuthProvider` e o `RouterProvider`.

A Home consome os parâmetros validados:

```ts
const { page, perPage, name } = useLoaderData<typeof homeLoader>();
const [, setSearchParams] = useSearchParams();
const { data } = useRefunds({ page, perPage, name });
```

O campo mantém um rascunho local para responder imediatamente à digitação. Após
o debounce, ele atualiza a URL; paginação também altera search params. Uma `key`
baseada no nome recria somente o campo quando back/forward muda a busca, evitando
copiar estado da URL com `setState` dentro de um efeito.

### Arquivos modificados

- Criados `src/router.tsx`, `src/router-loaders.ts` e
  `src/pages/PageRouteError.tsx`.
- Ajustados `src/App.tsx`, `src/pages/PageHome.tsx` e
  `src/schemas/refund.ts`.

### Verificações e limitações

- `npx tsc -b --noEmit`: passou com código de saída 0.
- `npm run build`: passou e gerou chunks separados para Home, Login, Registro,
  Detalhe, Sucesso e Componentes.
- O bundle principal ainda ultrapassa 500 kB; o aviso de performance permanece
  fora deste item.
- `npm run lint`: continua falhando somente nos 18 erros preexistentes de
  `react-refresh/only-export-components`; o erro novo detectado durante a
  implementação foi corrigido antes do encerramento.
- Frontend `/` e `/?name=hotel&page=2` responderam HTTP 200; API `/health`
  respondeu HTTP 200.
- Não havia navegador conectado à sessão. Login, busca, paginação, reload,
  back/forward, detalhe e erros de loader ainda precisam de validação manual.
- Testes automatizados de schemas e router não foram introduzidos porque o
  setup de Vitest é o Item 4.

### O que lembrar

- Loader coordena a preparação da rota; `useQuery` mantém o componente reativo.
- `QueryClient` é a interface programática do mesmo cache acessado pelos hooks.
- `ensureQueryData` reutiliza a query existente ou executa sua `queryFn` quando
  a chave não existe.
- Query keys ficam no cache em memória, não no `localStorage`.
- URL é o lugar apropriado para estado de navegação compartilhável, como busca
  e página.
- `route.lazy` divide código por página; `ErrorBoundary` da rota recebe falhas
  que podem acontecer antes de o componente renderizar.

## Fase 2, Item 4 — Vitest, Testing Library e user-event

**Status:** concluído em 2026-07-24.

**Commit da implementação:** `55f8455` —
`test: set up Vitest + Testing Library and cover format, schema, guard and login`,
no repositório `Refund-FrontEnd`.

### Por que estudar

Os itens 1–3 estavam corretos por tipo (`tsc`), mas nenhum comportamento era
executado por um teste automatizado — as três pendências de runtime existiam
justamente porque não havia infraestrutura de teste no frontend. O `tsc` prova
formato em tempo de compilação; ele não roda `formatCentsToBRL`, não passa uma
entrada inválida pelo `refundCreateSchema` nem confirma que `ProtectedRoute`
redireciona quem não está logado.

Este item introduz a primeira base de testes do frontend (Vitest + jsdom +
Testing Library + user-event) e cobre quatro alvos por nível. É a fundação de que
o MSW (Item 5) e a pirâmide de testes (Item 6) dependem.

### Estado anterior

`package.json` só tinha `dev`, `build`, `lint`, `preview`; nenhuma dependência de
teste e nenhum arquivo `*.test.ts(x)`:

```json
"scripts": { "dev": "vite", "build": "tsc -b && vite build", "lint": "eslint .", "preview": "vite preview" }
```

### Comparação visual

```mermaid
flowchart LR
    subgraph Antes
        A1[tsc -b] --> A2[Os tipos batem]
        A3[Comportamento] -. sem prova executável .-> A4[Confiança manual no navegador]
    end

    subgraph Depois
        B1[tsc -b] --> B2[Os tipos batem]
        B3[vitest run] --> B4[O comportamento está correto]
        B4 --> U[unit: format, schema]
        B4 --> C[componente: ProtectedRoute]
        B4 --> I[integração: fluxo de login]
    end
```

| Alvo                 | Nível      | O que passou a ser provado                              |
|----------------------|------------|---------------------------------------------------------|
| `formatCentsToBRL`   | unitário   | centavos → BRL; zero, milhar e um único centavo         |
| `refundCreateSchema` | unitário   | recusa nome vazio, categoria inválida, valor ≤ 0 e NaN  |
| `ProtectedRoute`     | componente | logado vê o `Outlet`; deslogado vai para `/login`       |
| Fluxo de login       | integração | digitar + submeter chama `login` e navega; erro mostra msg |

### Estado ajustado

`vite.config.ts` passou a usar o `defineConfig` do Vitest e a declarar o ambiente
de teste:

```ts
import { defineConfig } from 'vitest/config'
// ...
  test: {
    environment: 'jsdom',
    setupFiles: './src/test/setup.ts',
  },
```

`src/test/setup.ts` registra os matchers do jest-dom e o `cleanup` entre testes
(necessário porque rodamos com imports explícitos, sem `globals: true`):

```ts
import "@testing-library/jest-dom/vitest";
import { afterEach } from "vitest";
import { cleanup } from "@testing-library/react";

afterEach(() => {
  cleanup();
});
```

O schema é testado campo a campo via `.shape`, evitando construir um `FileList`
no jsdom:

```ts
const result = refundCreateSchema.shape.amount.safeParse("-5");
expect(result.success).toBe(false);
if (!result.success) {
  expect(result.error.issues[0].message).toBe("Valor deve ser maior que zero");
}
```

O fluxo de login roda sem rede: um `AuthContext.Provider` de teste expõe um
`login` espião, e `user-event` dirige a interação.

```ts
const login = vi.fn().mockResolvedValue(undefined);
// render PageLogin dentro de MemoryRouter (/login + / marcada) + AuthContext
await user.type(screen.getByPlaceholderText("voce@exemplo.com"), "ana@exemplo.com");
await user.click(screen.getByRole("button", { name: "Entrar" }));
expect(login).toHaveBeenCalledWith("ana@exemplo.com", "secret123");
expect(await screen.findByText("home page")).toBeInTheDocument();
```

### Arquivos modificados

- Modificados: `package.json` (devDeps + scripts `test`/`test:watch`) e
  `vite.config.ts` (bloco `test`).
- Criados: `src/test/setup.ts`, `src/lib/format.test.ts`,
  `src/schemas/refund.test.ts`, `src/components/core/ProtectedRoute.test.tsx` e
  `src/pages/PageLogin.test.tsx`.
- devDependencies adicionadas: `vitest`, `jsdom`, `@testing-library/react`,
  `@testing-library/dom`, `@testing-library/user-event`,
  `@testing-library/jest-dom`.

### Verificações e limitações

- `npm run test`: 15 testes em 4 arquivos, todos verdes.
- `npx tsc -b --noEmit`: exit 0 (inclui os `*.test.tsx` sob `src`).
- `npm run lint`: 18 erros preexistentes de `react-refresh/only-export-components`,
  **zero** novos. Durante a implementação eu havia introduzido um erro
  (`triple-slash-reference` no `vite.config.ts`); foi detectado pelo lint e
  corrigido antes do encerramento.
- **Campo `file` do schema não testado aqui:** exige um `FileList`, que o jsdom
  não constrói de forma limpa. Fica coberto pelo teste de upload do
  `RefundFormDialog` (item futuro, com `user-event`).
- **Labels não associadas ao input:** o teste de login seleciona os campos por
  placeholder porque o `InputText` não liga `<label>`/`htmlFor` ao `<input>`.
  Essa dívida de acessibilidade é o Item 7.
- Os fluxos contra a API real continuam pendentes de validação manual; este item
  cobre comportamento isolado, não integração ponta a ponta.

### O que lembrar

- `tsc` prova formato; teste prova comportamento. São garantias diferentes.
- `setupFiles` roda uma vez por arquivo de teste — bom lugar para registrar
  matchers e `cleanup`.
- Sem `globals: true`, o Testing Library não limpa o DOM sozinho: registrar
  `afterEach(cleanup)` evita que o DOM de um teste vaze para o próximo.
- `schema.shape.<campo>` permite testar uma regra isolada sem montar o objeto
  inteiro (aqui, sem `FileList`).
- Mockar a **fronteira** (`login` no contexto) em vez da rede mantém o teste
  focado no comportamento da página; a rede fica para o MSW (Item 5).
- Prioridade de queries: prefira `getByRole`/`getByLabelText`; cair para
  `getByPlaceholderText` é aceitável, mas costuma sinalizar uma dívida de
  acessibilidade.

## Fase 2, Item 5 — MSW (Mock Service Worker)

**Status:** concluído em 2026-07-25.

**Commit da implementação:** `7bf7042` —
`test: add MSW network mocking and Vitest UI`, no repositório `Refund-FrontEnd`.

**Escopo:** MSW apenas para testes (node server). O worker de browser para
desenvolvimento (`msw/browser`) foi deliberadamente adiado. Também foi integrado
o Vitest UI (`@vitest/ui`) por pedido do Gabriel.

### Por que estudar

O teste de login do Item 4 mockou a fronteira do `AuthContext` (`login` como
`vi.fn()`), então o `axios` e os schemas de *response* nunca rodavam. Os schemas
do Item 2 (`refundsListResponseSchema`, `refundDetailResponseSchema`,
`refundCreateResponseSchema`) seguiam sem prova executável.

O MSW intercepta HTTP no nível da rede: o `axios` real roda, o `schema.parse`
real roda, e só a *resposta* é falsa. Isso fecha a dívida do Item 2 e cria a base
para os testes de integração da pirâmide (Item 6).

### Estado anterior

`src/test/setup.ts` só registrava jest-dom e `cleanup`; nenhum caminho de rede
(`refundQueries`, `useCreateRefund`, `AuthContext`) tinha teste. O `axios` usa
`baseURL: import.meta.env.VITE_API_URL` (`http://localhost:3333`, carregado do
`.env` também nos testes).

### Comparação visual

```mermaid
flowchart LR
    subgraph Item4[Item 4 — boundary mock]
        A1[PageLogin] --> A2[login = vi.fn]
        A2 -.->|axios e Zod NÃO rodam| A3[asserção]
    end

    subgraph Item5[Item 5 — network mock]
        B1[PageLogin] --> B2[AuthProvider real]
        B2 --> B3[axios real]
        B3 --> B4[MSW intercepta]
        B4 --> B5[loginResponseSchema.parse]
        B5 --> B6[token no localStorage + navegação]
    end
```

| Handler                | Testa                                                    |
|------------------------|---------------------------------------------------------|
| `POST */auth/login`    | login real + `loginResponseSchema` + token persistido   |
| `GET */refunds`        | `useRefunds` + `refundsListResponseSchema`              |
| `GET */refunds/:id`    | `useRefund` + `refundDetailResponseSchema`              |
| `POST */refunds`       | `useCreateRefund` + `refundCreateResponseSchema`        |
| `server.use(401/422)`  | `getApiErrorMessage` nos dois formatos de erro          |

### Estado ajustado

Handlers *happy-path* reutilizáveis, com caminhos `*` para casar qualquer host:

```ts
export const handlers = [
  http.post("*/auth/login", () => HttpResponse.json(loginFixture)),
  http.get("*/refunds", () => HttpResponse.json({ /* lista */ })),
  http.get("*/refunds/:id", ({ params }) => HttpResponse.json({ /* detalhe */ })),
  http.post("*/refunds", () => HttpResponse.json({ /* base */ }, { status: 201 })),
  http.delete("*/refunds/:id", () => new HttpResponse(null, { status: 204 })),
];
```

O ciclo de vida do servidor vive no setup, junto do `cleanup` e da limpeza de
`localStorage` (o `AuthProvider` real persiste token/sessão):

```ts
beforeAll(() => server.listen({ onUnhandledRequest: "error" }));
afterEach(() => { cleanup(); server.resetHandlers(); localStorage.clear(); });
afterAll(() => server.close());
```

Os testes de integração exercitam o caminho real. Response malformado é rejeitado
na fronteira (fecha a promessa do Item 2):

```ts
server.use(http.get("*/refunds", () =>
  HttpResponse.json({ type: "Refund", attributes: "nope" })));
// useRefunds via renderHook -> result.current.isError === true (ZodError)
```

E o override por teste cobre o 422 do FastAPI:

```ts
server.use(http.post("*/refunds", () =>
  HttpResponse.json({ detail: [{ msg: "Arquivo é obrigatório" }] }, { status: 422 })));
// getApiErrorMessage(result.current.error) === "Arquivo é obrigatório"
```

### Arquivos modificados

- Modificados: `package.json` (devDeps `msw`, `@vitest/ui`; script `test:ui`),
  `src/test/setup.ts` (ciclo do servidor MSW + `localStorage.clear`).
- Criados: `src/test/msw/handlers.ts`, `src/test/msw/server.ts`,
  `src/test/utils.tsx` (`QueryWrapper`), `src/hooks/refundQueries.test.tsx`,
  `src/pages/PageLogin.integration.test.tsx`, `src/hooks/useCreateRefund.test.tsx`.

### Verificações e limitações

- `npm run test`: 23 testes em 7 arquivos, todos verdes.
- `npx tsc -b --noEmit`: exit 0.
- `npm run lint`: 18 erros preexistentes, **zero** novos. Durante a implementação
  o `src/test/utils.tsx` chegou a exportar uma função + um componente (1 erro
  novo de `react-refresh`); foi resolvido deixando o arquivo com export único de
  componente, antes do encerramento.
- **Sanidade técnica confirmada:** MSW intercepta o `axios` dentro do jsdom
  (era o risco que eu havia sinalizado no plano).
- **Aviso do jsdom `Not implemented: navigation`:** aparece no teste de 401 do
  login porque o interceptor de `api.ts` faz `window.location.href = "/login"`
  em qualquer 401. Não é falha (o `MemoryRouter` ignora `window.location`); expôs
  um comportamento real do interceptor, candidato a refino futuro.
- **`FileList` continua sem construção real:** o teste de criação passa um
  `[File]` com cast, pois o `mutationFn` só lê `file[0]`.

### O que lembrar

- MSW mocka a **rede**, não a fronteira do código: axios e Zod reais rodam, só a
  resposta é falsa — mais confiança que mockar a função.
- `setupServer` + `listen`/`resetHandlers`/`close` é o ciclo padrão nos testes;
  `onUnhandledRequest: "error"` impede bater na API real por engano.
- `server.use(...)` sobrescreve um handler só para aquele teste; `resetHandlers`
  no `afterEach` desfaz.
- Testar via `renderHook` prova hook + `queryFn` + schema + rede juntos; um
  response malformado precisa virar `isError`, não entrar no cache.
- Um mesmo comportamento pode (e deve) ter testes em níveis diferentes:
  componente (rápido, isolado) e integração (mais caro, mais confiança) —
  antecipa a pirâmide do Item 6.

## Correções de runtime — exclusão de reembolso (2026-07-25)

Ao validar o app no navegador (backend + banco reais), a exclusão de um reembolso
a partir da página de detalhe **não** atualizava a lista da Home, e o log da API
mostrava `GET/DELETE /refunds/{id}` retornando **500** com vazamento de conexão.
A investigação revelou **dois bugs distintos** — um em cada repositório. Não são
itens novos do Learning Path; são correções, mas o aprendizado ficou registrado
aqui por ligar direto aos conceitos dos Itens 1, 3 e (no backend) 20/25.

### Bug 1 — `invalidateQueries` não refaz queries inativas (frontend)

**Commit:** `228ec8d` —
`fix: refresh refund lists after create/delete without refetching detail`, no
repositório `Refund-FrontEnd`.

**Sintoma:** o item excluído continuava na lista após voltar para a Home.

**Causa raiz:** três decisões se combinaram. A exclusão parte do **detalhe**, com
a Home desmontada → a query da lista está **inativa**. `invalidateQueries`, por
padrão (`refetchType: "active"`), **só refaz queries ativas**; a lista inativa era
só marcada como velha. Ao remontar, o `refetchOnMount` decide o refetch **pelo
tempo** (`staleTime` de 30s) e não pela flag de invalidação — como o dado tinha
menos de 30s, era considerado "fresco" e não era refeito. Resultado: item
fantasma por até 30s.

Havia ainda um **segundo efeito**: invalidar o prefixo `["refunds"]` inteiro
também refazia a query de **detalhe do item recém-deletado** (`GET /refunds/{id}`),
que no backend real virava erro — e essa rajada concorrente disparava o Bug 2.

**Comparação visual:**

```text
Antes  invalidateQueries({ queryKey: ["refunds"] })
       -> refaz só ATIVAS  -> lista inativa fica velha (some por até 30s)
       -> atinge o detalhe -> GET /refunds/{id} de item deletado -> erro

Depois invalidateQueries({ queryKey: ["refunds","list"], refetchType: "all" })
       -> refaz TODAS as listas (mesmo inativas), ignorando staleTime
       -> NÃO toca no detalhe -> nenhum GET do item deletado
```

**Estado ajustado:** nova chave `refundKeys.lists()` (prefixo só das listas) e, em
`useDeleteRefund`/`useCreateRefund`:

```ts
queryClient.invalidateQueries({ queryKey: refundKeys.lists(), refetchType: "all" });
```

**Teste:** `src/hooks/useDeleteRefund.test.tsx` — prova que, após excluir com a
lista inativa, o cache da lista vira `["A"]` **e** que o detalhe do item deletado
**não** é rebuscado (`detailCalls` permanece 1).

**O que lembrar:**
- `invalidateQueries` só refaz **queries ativas** por padrão; uma query invalidada
  enquanto inativa depende do `staleTime` na próxima montagem (`refetchOnMount`
  olha o tempo, não a flag). Use `refetchType: "all"` para forçar as inativas.
- Escopo importa: mire só o que precisa (`lists()`), nunca invalide o detalhe de
  algo que acabou de ser apagado.

### Bug 2 — sessão compartilhada no handler de conexão (backend)

**Commit:** `1fc0db0` —
`fix: make the database connection handler concurrency-safe`, no repositório
`Refund-api`.

**Sintoma:** `GET/DELETE /refunds/{id}` retornando 500 e o aviso do garbage
collector sobre conexão asyncpg não devolvida ao pool.

**Causa raiz:** `DatabaseConnectionHandler` era um **singleton de módulo** que
guardava a sessão em `self.session`:

```python
async def __aenter__(self):
    self.session = async_session()   # estado COMPARTILHADO entre requisições
    return self
```

Sob requisições **concorrentes** (que o Bug 1 provocava), a segunda sobrescrevia
o `self.session` da primeira: as duas usavam a mesma sessão asyncpg ao mesmo
tempo (erro de operação concorrente → 500) e a sessão órfã nunca fechava
(vazamento).

**Estado ajustado:** a sessão passou a viver em **variável local** de um
`@asynccontextmanager`, nunca em `self`:

```python
@asynccontextmanager
async def connect(self):
    session = async_session()
    try:
        yield session
    finally:
        await session.close()
```

Os repositórios passaram a usar `async with self.__db_connection.connect() as
session:`. O singleton continua exportado, mas agora é **seguro** mesmo
compartilhado, porque não há mais estado por-operação em `self`.

**Teste:** `src/models/settings/database_connection_handler_test.py` — dois
`connect()` sobrepostos recebem **sessões distintas** e ambas são fechadas.

**O que lembrar:**
- Estado mutável **compartilhado** entre contextos async concorrentes é uma fonte
  clássica de bug. `async def` não serializa acesso; duas requisições realmente se
  intercalam.
- Escope recursos por operação (variável local no context manager), não em `self`
  de um objeto compartilhado. Engine/sessionmaker podem ser singletons; a
  **sessão**, não.

## Fase 2, Item 6 — Pirâmide de testes frontend

**Status:** concluído em 2026-07-25.

**Commit da implementação:** `3736614` —
`test: add isolated component tests for Button, Dialog and InputText`, no
repositório `Refund-FrontEnd`.

**Escopo:** testes de **componente** isolados para as peças do design system
(`Button`, `Dialog`, `InputText`) e o **mapa** da suíte por nível. O topo da
pirâmide (**E2E**) foi deliberadamente **adiado** (só documentado).

### Por que estudar

Cada nível de teste compra uma **confiança diferente** por um **custo diferente**.
A suíte pendia para **integração** (Query + MSW) e quase não tinha teste de
**componente isolado**. Sem esse modelo mental, a tendência é cair em um de dois
extremos: muitos testes de implementação frágeis (quebram a cada refator de CSS)
ou poucos testes integrados (falha difícil de localizar).

### Estado anterior

Não havia teste de componente isolado para `Button`, `Dialog` nem `InputText` —
eles só eram exercitados **indiretamente**, via páginas/integração. Uma regressão
neles (ex.: `disabled` deixar de bloquear o clique, o `Dialog` perder o
`role="dialog"`) só apareceria de forma indireta e difícil de localizar.

### Comparação visual (mapa por nível)

```
      /\        E2E: 0 (adiado; fluxo candidato nomeado abaixo)
     /  \       Integração: PageLogin.integration, refundQueries,
    /----\                   useCreateRefund, useDeleteRefund
   /      \     Componente: Button, Dialog, InputText (novos),
  /--------\                ProtectedRoute, PageLogin (boundary)
 /          \   Unitário: format, refund (schema)
```

Cada nível responde a uma pergunta diferente:

| Nível | Pergunta que responde | Custo |
|-------|-----------------------|-------|
| Unitário | "esta função/schema está correta?" | mínimo |
| Componente | "este componente se comporta (acessível) como o usuário espera?" | baixo |
| Integração | "as peças conversam (Router + Query + Auth + rede)?" | médio |
| E2E | "o sistema real funciona ponta a ponta?" | alto |

### Estado ajustado

Testes de componente que exercitam **comportamento acessível**, não classes:

```tsx
// Button: nome acessível + clique; disabled bloqueia o clique.
await user.click(screen.getByRole("button", { name: "Entrar" }));
expect(onClick).toHaveBeenCalledOnce();

// Dialog: abre pelo trigger com role/nome do título; fecha pelo botão.
await user.click(screen.getByRole("button", { name: "Abrir" }));
await screen.findByRole("dialog", { name: "Excluir solicitação" });
```

### Arquivos modificados

- Criados: `src/components/molecules/Button.test.tsx`, `Dialog.test.tsx` e
  `InputText.test.tsx`.
- Nenhuma infra nova: Testing Library + jsdom já bastavam (o Radix Dialog roda
  no jsdom, com portal e foco).

### Decisão sobre E2E (adiado)

E2E de verdade exige infra pesada (Playwright, subir app + API + banco no teste).
Não foi adicionado agora para manter o incremento focado. **Fluxo candidato**
quando for a hora: login → criar reembolso → vê-lo na lista → excluir → sumir da
lista. É o caminho crítico que atravessa auth, criação, cache e exclusão.

### Verificações e limitações

- `npm run test`: 32 testes em 11 arquivos, todos verdes.
- `npx tsc -b --noEmit`: exit 0.
- `npm run lint`: 18 erros preexistentes, **zero** novos.
- **Lacunas de acessibilidade registradas nos próprios testes** (alimentam o
  Item 7): o spinner do `Button` não tem `role`/nome (detectado pela classe de
  animação); a label do `InputText` não é associada ao `<input>` (query por
  placeholder). O bloqueio de clique do `handling` é via CSS (`pointer-events`),
  que o jsdom não enxerga — por isso não é asserido.

### O que lembrar

- A pirâmide é uma **lente conceitual**, não uma estrutura de pastas: os testes
  seguem colocados ao lado do código; reorganizar em pastas por nível seria churn
  sem ganho.
- Teste de componente é o nível certo para as peças do design system: rápido,
  isolado e localiza a falha. Se o `Button` quebra, o teste do `Button` aponta,
  não "algum lugar do login".
- Testar por **role/nome/comportamento** (não por `className`) deixa o teste
  resistente a refatoração de estilo.
- Escolher o nível é uma decisão de custo/confiança — inclusive **não** escrever
  um E2E agora é uma escolha consciente, não um esquecimento.

## Fase 2, Item 7 — Acessibilidade prática

**Status:** concluído em 2026-07-25.

**Commit da implementação:** `177f40c` —
`feat: improve form accessibility (labels, aria, keyboard, axe)`, no repositório
`Refund-FrontEnd`.

### Por que estudar

Acessibilidade = usável por **teclado e leitor de tela**, não só pelo mouse. O
Radix cobre Dialog/Popover, mas os inputs tinham lacunas concretas: label não
associada (o leitor não anuncia o campo), erro não vinculado (não se sabe qual
campo falhou) e loading mudo. **axe** automatiza a auditoria dessas regras.

### Estado anterior

`InputText` renderizava a label como texto solto, **sem** `htmlFor`/`id`,
`aria-invalid` nem `aria-describedby`. `Button` mostrava o spinner sem anunciar o
estado ocupado. O trigger do `PopOverMenu` era um `<div>` recebendo os atributos
de botão do Radix (`aria-haspopup`/`aria-expanded`) sem `role` e sem teclado.

### Comparação visual

```
ANTES  <span>E-mail</span>  <input placeholder="voce@…">   (label solta)
DEPOIS <label for="id7">E-mail</label>
       <input id="id7" aria-invalid="true" aria-describedby="id7-error">
       <span id="id7-error">E-mail inválido</span>
```

### Estado ajustado

`InputText` gera um id com `useId`, associa a `<label htmlFor>` e vincula o erro:

```tsx
<InputLabelWrapper label={label} htmlFor={inputId}>
  <input id={inputId} aria-invalid={error ? true : undefined}
         aria-describedby={error ? errorId : undefined} {...props} />
</InputLabelWrapper>
{error && <Text as="span" id={errorId} className="text-error">{error}</Text>}
```

`Button` anuncia o processamento e esconde o ícone decorativo:

```tsx
<button aria-busy={handling ? true : undefined} ...>
  ...
  <Icon aria-hidden ... />   {/* spinner/ícone decorativo: fora do nome acessível */}
</button>
```

O trigger do `PopOverMenu` virou um botão operável por teclado:

```tsx
<InputLabelWrapper role="button" tabIndex={0}
  onKeyDown={(e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); e.currentTarget.click(); } }}
  ... />
```

### A auditoria fez o trabalho dela

O `vitest-axe` no `RefundFormDialog` acusou `aria-allowed-attr` — um bug real que
os testes de comportamento não pegariam: o `<div>` do trigger com atributos de
botão sem `role`, e inacessível por teclado. Foi corrigido na origem (acima).

### Foco no primeiro erro (já funcionava)

Ao enviar o formulário vazio, o RHF foca o primeiro campo inválido. Isso já
funcionava por três peças se encaixando — `shouldFocusError` (default), o `ref`
do `register` chegando ao `<input>` (React 19 encaminha `ref` em spread) e o
`aria-invalid`. Foi apenas **verificado** e protegido por teste, sem código novo.

### Arquivos modificados

- Ajustados: `src/components/atoms/Text.tsx` (aceita `htmlFor`/`id`),
  `src/components/molecules/InputLabelWrapper.tsx` (label vira `<label htmlFor>`),
  `src/components/molecules/InputText.tsx` (id + aria), `Button.tsx` (aria-busy +
  ícone `aria-hidden`), `PopOverMenu.tsx` (trigger botão + teclado).
- Criados: `PopOverMenu.test.tsx`, `RefundFormDialog.test.tsx` (foco no erro),
  `PageRegister.a11y.test.tsx`, `RefundFormDialog.a11y.test.tsx` (axe).
- devDep: `vitest-axe`. Testes de `InputText`/`Button` atualizados para asserir
  `getByLabelText`/`aria-*` em vez de placeholder/classe.

### Verificações e limitações

- `npm run test`: 38 testes em 15 arquivos, todos verdes.
- `npx tsc -b --noEmit`: exit 0. `npm run lint`: 18 preexistentes, 0 novos.
- **axe escopado a WCAG A/AA**, rodado no subtree (não no document) e com
  `color-contrast` desabilitado: o jsdom não carrega CSS (contraste) nem tem
  `<title>`/`lang` — essas checagens pertencem a um E2E/navegador.
- **Navegação por ↑/↓ dentro do menu aberto** (padrão listbox completo) ainda não
  existe: o menu abre por teclado, mas percorrer as opções com as setas é um
  aprofundamento maior — follow-up, fora do escopo "prático" deste item.

### O que lembrar

- Associar label ao input (`htmlFor`/`id`) é a base: o leitor anuncia o campo,
  clicar na label o foca, e `getByLabelText` (a query recomendada) passa a funcionar.
- `aria-invalid` + `aria-describedby` ligam a mensagem ao campo — o usuário ouve
  *qual* campo falhou e *por quê*.
- `aria-busy` anuncia processamento; ícone decorativo deve ser `aria-hidden` para
  não poluir o nome acessível do controle.
- Um `<div role="button">` não ganha Enter/Espaço de graça como um `<button>`
  nativo — precisa de `tabIndex` e de um handler de teclado.
- axe pega o que o teste de comportamento não vê (atributo ARIA inválido); um
  teste de comportamento pega o que o axe não vê (o teclado não abrir o menu). São
  complementares.

## Fase 3, Item 8 — Feature-based architecture

**Status:** concluído em 2026-07-25.

**Commit da implementação:** `1594d0f` —
`refactor: colocate refunds into a feature module with a public façade`, no
repositório `Refund-FrontEnd`.

**Escopo aprovado:** migrar **apenas** a feature de reembolsos. As **páginas ficam
fora** da feature (shells que consomem a fachada), seguindo bulletproof-react e
Feature-Sliced Design. Sem path aliases (`@/`) — são o objeto do Item 9.

### Por que estudar

O frontend era organizado **por tipo técnico**: `hooks/`, `schemas/`,
`constants/`, `components/organisms/`. Tudo que era "hook" morava junto, mesmo que
um fosse de reembolso e outro de infraestrutura. Uma mudança de domínio se
espalhava por muitas pastas.

Colocation **por feature** inverte o critério: agrupa tudo que **muda pelo mesmo
motivo**. `features/refunds/` passa a dona da API, hooks, schemas e componentes de
reembolso e expõe uma **fachada pública** (`index.ts`). O resto do app importa de
`features/refunds`, nunca de um caminho interno. Sem essa fronteira o Item 9
(boundaries no ESLint) não teria o que proteger.

### Estado anterior

Os módulos de reembolso viviam espalhados por pasta técnica, e os consumidores
importavam caminhos internos diretos:

```ts
// src/pages/PageRefundDetails.tsx
import { CATEGORIES } from "../constants/categories";
import { useRefund } from "../hooks/useRefund";
import { useDeleteRefund } from "../hooks/useDeleteRefund";
```

Não havia fronteira: qualquer arquivo podia alcançar qualquer parte interna do
domínio.

### Comparação visual

```mermaid
flowchart LR
    subgraph Antes["Antes — por tipo técnico"]
        P1[pages/*] --> H[hooks/useRefund*]
        P1 --> S1[schemas/refund]
        P1 --> C1[constants/categories]
        O1[components/organisms/RefundFormDialog]
    end

    subgraph Depois["Depois — por feature"]
        P2[pages/*] --> F[features/refunds/index.ts\nfachada pública]
        R[router-loaders] --> F
        ML[core/MainLayout] --> F
        F --> IN[api · hooks · schemas\ncomponents · constants\n internos]
    end
```

| Módulo (antes) | É de reembolso? | Destino |
|---|---|---|
| `hooks/refundQueries.ts` | ✅ | `features/refunds/api/` |
| `hooks/useRefund(s)/useCreate/useDelete` | ✅ | `features/refunds/hooks/` |
| `schemas/refund.ts` | ✅ | `features/refunds/schemas/` |
| `components/organisms/RefundFormDialog.tsx` | ✅ | `features/refunds/components/` |
| `constants/categories.ts` | ✅ (domínio de despesa) | `features/refunds/constants/` |
| `lib/*`, design system, `context/`, `router*`, `pages/`, `hooks/useDebouncedValue` | ❌ neutro | ficaram no lugar |

### Estado ajustado

A fachada `src/features/refunds/index.ts` define a superfície pública e mantém o
resto privado:

```ts
export { refundListQuery, refundDetailQuery } from "./api/refundQueries";
export { useRefunds } from "./hooks/useRefunds";
export { useRefund } from "./hooks/useRefund";
export { useCreateRefund } from "./hooks/useCreateRefund";
export { useDeleteRefund } from "./hooks/useDeleteRefund";
export { refundListSearchParamsSchema } from "./schemas/refund";
export { CATEGORIES, CATEGORY_OPTIONS } from "./constants/categories";
export { default as RefundFormDialog } from "./components/RefundFormDialog";
// refundKeys, response schemas e CATEGORY_VALUES são internos — não re-exportados.
```

Os consumidores passaram a importar só da fachada:

```ts
// src/pages/PageRefundDetails.tsx
import { CATEGORIES, useRefund, useDeleteRefund } from "../features/refunds";
```

Sem aliases, os imports **internos** dos arquivos movidos ficaram mais profundos
(o custo consciente deste item): `../lib/api` virou `../../../lib/api`. A distância
**entre subpastas da própria feature** não mudou (`schemas → constants` continua
`../constants/categories`), então vários arquivos não precisaram de ajuste.

### Arquivos modificados

- Movidos (via `git mv`, histórico preservado) para `src/features/refunds/`:
  `api/refundQueries.ts`, `hooks/{useRefunds,useRefund,useCreateRefund,useDeleteRefund}.ts`,
  `schemas/refund.ts`, `components/RefundFormDialog.tsx`, `constants/categories.ts`
  e seus respectivos `*.test.*`.
- Criado: `src/features/refunds/index.ts` (fachada).
- Consumidores ajustados para a fachada: `src/pages/PageHome.tsx`,
  `PageRefundDetails.tsx`, `PageComponents.tsx`, `src/router-loaders.ts`,
  `src/components/core/MainLayout.tsx`.

### Verificações e limitações

- `npm run test`: 38 testes em 15 arquivos, todos verdes (a mesma suíte, só
  relocada — nenhum teste novo, é uma refatoração sem mudança de comportamento).
- `npx tsc -b --noEmit`: exit 0 (pegaria qualquer import quebrado pela mudança de
  caminho).
- `npm run lint`: 18 erros preexistentes, **zero** novos. A fachada mistura
  re-export de componente com funções, mas re-exports não disparam
  `react-refresh/only-export-components`.
- Sanidade por `grep`: nenhum consumidor externo importa o interior da feature; a
  feature não importa de `pages/`; nenhum import órfão para os caminhos antigos.
- **Preserva Atomic Design onde ele importa:** os átomos/moléculas neutros
  continuam no design system; só o organism específico de reembolso
  (`RefundFormDialog`) foi para a feature — a migração é o objeto de estudo
  aprovado, não uma quebra silenciosa da arquitetura.
- **Imports internos mais profundos** (`../../../lib/api`) são a dívida que o
  **Item 9** paga com aliases + boundaries no ESLint.

### O que lembrar

- Organizar **por feature** agrupa o que muda junto; organizar **por tipo** agrupa
  o que se parece. Em escala, "muda junto" reduz o espalhamento por mudança de
  domínio.
- A **fachada** (`index.ts`) é o conceito central: ela torna explícita a diferença
  entre API pública e detalhe interno. Importar `features/refunds` (não um caminho
  interno) é o que o Item 9 vai transformar em regra executável.
- Nem tudo vira feature: design system, `lib`, auth e router são **neutros/app-level**
  e ficam fora. Uma constante de domínio (categorias de despesa), sim, é da feature.
- **Página fica fora da feature** (bulletproof-react / FSD): a rota é ponto de
  composição e assunto do app; a feature não deve conhecer o esquema de URLs.
- `git mv` preserva o histórico do arquivo movido; refatoração de layout não
  precisa apagar a linha do tempo do código.

## Fase 3, Item 9 — Boundaries verificáveis pelo ESLint

**Status:** concluído em 2026-07-26.

**Commit da implementação:** `4bab16e` —
`feat: enforce feature boundaries with @/ aliases and eslint-plugin-boundaries`,
no repositório `Refund-FrontEnd`.

**Escopo aprovado:** (A) alias `@/` e (B) `eslint-plugin-boundaries`. Decisão de
arquitetura tomada antes de implementar: `components/core` é camada **app** (pode
importar `ui`), então a regra literal `core → ui` do `learning_path.md` **não** foi
aplicada — ela era um exemplo genérico, e no código `MainLayout` legitimamente
compõe UI + a fachada da feature.

### Por que estudar

No Item 8 a fachada (`features/refunds/index.ts`) criou a fronteira, mas
*"importe só a fachada"* era só **convenção**: nada impedia
`import { refundKeys } from ".../features/refunds/api/refundQueries"`. O código
compilava e os testes passavam.

O conceito é **architecture fitness function**: uma verificação automatizada que
**falha** quando o código viola uma decisão de arquitetura. A decisão deixa de ser
um comentário no diário e passa a ser parte do `npm run lint`.

### Estado anterior

Sem alias e sem regra de dependência. `eslint.config.js` só tinha `js`,
`typescript-eslint`, `react-hooks` e `react-refresh`. E a dívida do Item 8 estava
concreta — imports internos da feature subindo três níveis:

```ts
// src/features/refunds/api/refundQueries.ts
import { api } from "../../../lib/api";
// src/features/refunds/components/RefundFormDialog.tsx
import Button from "../../../components/molecules/Button";
```

### Comparação visual

Direção permitida (cada camada só enxerga as de baixo); o que estiver fora falha o
lint:

```text
        app          (pages, components/core, organisms, context, schemas)
         │  ↓ pode importar
     feature          (features/refunds — de fora, SÓ pela fachada index.ts)
         │  ↓
         ui           (components/atoms, molecules)
         │  ↓
       shared         (lib, hooks)

REGRAS QUE FALHAM O LINT:
  ✗ ui       → feature        (design system não conhece domínio)
  ✗ shared   → ui / feature    (utilitário neutro)
  ✗ feature  → outra feature   (relationship "sibling", não "internal")
  ✗ app      → interior da feature (só fileInternalPath = index.ts é público)
```

```text
ANTES   import { api } from "../../../lib/api";   // conta os ../, frágil
        convenção "só a fachada" vive no diário

DEPOIS  import { api } from "@/lib/api";           // absoluto, estável
        npm run lint FALHA se alguém furar a fachada ou cruzar camadas
```

### Estado ajustado

**Etapa A — alias `@/`.** `tsconfig.app.json` ganhou `paths` (sem `baseUrl`, que
está deprecado; com `moduleResolution: "bundler"` o `paths` resolve relativo ao
próprio tsconfig). `vite.config.ts` ganhou `resolve.alias` (herdado pelo Vitest).
Os `../../../` da feature viraram `@/...`.

**Etapa B — boundaries.** `eslint.config.js` classifica pastas em camadas e aplica
a regra `boundaries/dependencies` (API v7):

```js
'boundaries/elements': [
  { type: 'feature', pattern: 'src/features/*', capture: ['featureName'] },
  { type: 'ui', pattern: ['src/components/atoms', 'src/components/molecules'] },
  { type: 'shared', pattern: ['src/lib', 'src/hooks'] },
  { type: 'app', pattern: ['src/pages', 'src/components/core', /* ... */] },
],
// política central: app alcança a feature SÓ pela fachada
{
  from: { element: { type: 'app' } },
  allow: { to: { element: { type: 'feature', fileInternalPath: 'index.{ts,tsx}' } } },
},
// feature importa só a si mesma (mesma feature = relationship "internal")
{
  from: { element: { type: 'feature' } },
  allow: { to: { element: { type: 'feature' } },
           dependency: { relationship: { from: 'internal' } } },
},
```

### A prova de que a regra morde

Duas violações temporárias foram criadas e o lint as pegou, depois revertidas:

```text
ui → feature:  "no policy allowing dependencies from type 'ui' to type 'feature'"
app furando a fachada (import a api/refundQueries em vez do index):
               "no policy allowing dependencies from 'app' to 'feature'"
```

### Arquivos modificados

- `tsconfig.app.json` (paths `@/*`), `vite.config.ts` (resolve.alias),
  `eslint.config.js` (elements + regra `boundaries/dependencies`).
- `package.json`: `eslint-plugin-boundaries` e `eslint-import-resolver-typescript`.
- Imports `@/`: os internos da feature (api, hooks, components, constants e seus
  testes) e a fachada nos consumidores (`pages/*`, `components/core/MainLayout`,
  `router-loaders`).

### Verificações e limitações

- `npx tsc -b --noEmit`: exit 0.
- `npm run test`: 38 testes em 15 arquivos, todos verdes (Vitest resolve `@/` pela
  alias do Vite).
- `npm run build`: passou (mantém só o aviso preexistente de chunk >500 kB).
- `npm run lint`: 18 erros preexistentes de `react-refresh`, **0** de boundaries e
  **0 warnings** do plugin.
- **API do plugin migrada:** o `eslint-plugin-boundaries` v7.1 mudou bastante. A
  primeira config usou a API legada (`boundaries/element-types`, `rules`,
  template `${from.featureName}`) e gerou warnings de deprecação; foi migrada para
  a atual (`boundaries/dependencies`, `policies`, elementos por **pasta**,
  `relationship`/`fileInternalPath`) antes do encerramento.
- **Limitação — 4 arquivos-raiz não classificados.** No v7 um elemento é uma
  **pasta**; padrões com nome de arquivo disparam warning. Por isso `App.tsx`,
  `main.tsx`, `router.tsx` e `router-loaders.ts` (soltos em `src/`) ficaram
  **unknown** e não são checados como origem. São topo da hierarquia (app, que
  poderia importar tudo), então as fronteiras que importam seguem cobertas.
  Movê-los para uma pasta `app/` seria churn fora do escopo do item.

### O que lembrar

- **Fitness function**: transforma uma decisão de arquitetura em teste executável.
  Convenção que não é verificada degrada em silêncio no primeiro PR distraído.
- Alias `@/` com `moduleResolution: "bundler"` **não** precisa de `baseUrl` (que
  está deprecado); o `paths` resolve relativo ao tsconfig.
- No `eslint-plugin-boundaries` v7, **elemento = pasta**. Para classificar um
  arquivo isolado seria preciso `boundaries/files` (categoria), não um padrão de
  arquivo no descritor de elemento.
- `relationship: { from: 'internal' }` distingue "mesma feature" de "entre
  features" (`sibling`) sem lógica de captura manual; é como se proíbe import
  entre features.
- `fileInternalPath: 'index.{ts,tsx}'` é o que amarra a fachada: o `app` só entra
  na feature pelo `index`; qualquer caminho interno cai no `disallow`.
- Ao adotar uma lib, conferir se a config bate com a **versão instalada**: warnings
  de deprecação são sinal de estar na API antiga, mesmo que "funcione".

## Ciclo de feature — Shell do app (sidebar + topbar + tema)

**Status:** concluído em 2026-07-27, no repositório `Refund-FrontEnd` (branch
`feat/app-shell`, mesclada na `main` por fast-forward).

**Natureza:** primeiro **ciclo de feature** interligado à trilha (estratégia de usar
features como veículo dos próximos itens, a partir do Item 9). Passou por
brainstorming → spec → plano → execução (skills `brainstorming`, `writing-plans`,
`executing-plans`). Spec e plano em
`Refund-FrontEnd/docs/superpowers/{specs,plans}/2026-07-26-frontend-shell-*`.

**Itens da trilha que este ciclo cobriu:**
- **Item 12 — Zustand e persistência seletiva:** veículo direto. Store
  `src/stores/ui.ts` com `theme` + `sidebarCollapsed`, persistida no `localStorage`
  (middleware `persist`), com assinatura seletiva (`useUiStore(s => s.theme)`).
  Auth **não** foi migrado — segue no Context (decisão registrada anteriormente).
- **Item 10 — Pattern layer: reinterpretado.** Em vez de construir um pattern do
  zero, integramos e tematizamos uma lib pronta (`react-pro-sidebar`) — decisão
  consciente do Gabriel. O aprendizado virou "integrar + tematizar lib de terceiro
  dentro do design system", não "extrair uma composição própria".

### Por que estudar

O produto era direto ao ponto (Header + Outlet). Para escalar para um formato de
painel admin, a **moldura** precisa vir antes das páginas de dados (dashboard,
calendário, time) que virão nos próximos ciclos. E o tema claro/escuro exigia parar
de espalhar cores fixas e adotar uma **fonte única** de cor.

### Estado anterior

`MainLayout` era `Header` (organism) + `Outlet`. As cores viviam hardcoded na paleta
Tailwind (`bg-white`, `text-green-100`, `bg-gray-500`…), sem noção de tema. Não havia
estado global de UI.

### Comparação visual

```text
ANTES  Header + Outlet · cores fixas (bg-white/gray/green) · sem tema · sem store

DEPOIS  Sidebar (react-pro-sidebar) + Topbar de ações + Outlet
        cores = tokens semânticos em variáveis CSS (surface/app/line/content/
        muted/accent/…), que trocam sob [data-theme="dark"]
        Zustand persiste tema + estado da sidebar; um efeito aplica data-theme no <html>
        react-pro-sidebar e utilitários Tailwind leem os MESMOS var(--…) → trocam juntos
```

### Estado ajustado (o que mudou)

- **Tema por variáveis CSS** (`src/index.css`): tokens semânticos em `:root` e
  `:root[data-theme="dark"]`, mapeados no `@theme` do Tailwind 4. Toda a paleta fixa
  do app (16 arquivos) migrou para esses tokens. Modo claro ficou idêntico ao
  anterior (mesmos hex); o dark é novo.
- **Store Zustand** (`src/stores/ui.ts`) + **efeito** (`ThemeEffect`) que escreve
  `data-theme` no `<html>` (resolvendo `"system"` via `matchMedia`).
- **Sidebar** (`react-pro-sidebar`) tematizada via `rootStyles`/`menuItemStyles`
  com `var(--…)`: perfil derivado (iniciais + `@username` do e-mail, em
  `src/lib/profile.ts`), nav com "Solicitações" ativo + Dashboard/Time/Calendário
  "em breve", colapso em icon rail, drawer no mobile, logout no rodapé.
- **Topbar** (`src/components/core/Topbar.tsx`): título por rota (`handle: { title }`
  lido com `useMatches`), toggle de tema e "Nova solicitação".
- **Ícones `@mui/icons-material`** na sidebar/topbar.
- **`Header`/`NavLink` removidos** (código morto após a migração).
- **Fix de tema nos ícones svgr:** os assets tinham `fill="black"` fixo no `<path>`,
  então as classes `fill-*` nunca aplicavam e os ícones ficavam pretos (invisíveis no
  dark). Corrigido repintando `black → currentColor` na importação
  (`vite-plugin-svgr` `replaceAttrValues`) e dirigindo a cor por `text-*`.

### Verificações e limitações

- `npx tsc -b --noEmit` exit 0; `npm run test` 59 testes verdes (22 arquivos);
  `npm run build` OK; `npm run lint` 18 erros preexistentes de `react-refresh`,
  **0 de boundaries**, 0 novos.
- A camada nova respeita o Item 9: `Sidebar`/`Topbar`/`MainLayout` em
  `components/core/` (camada `app`); `src/stores` adicionado à camada `shared` no
  `eslint.config.js`.
- **Perfil frontend-only:** avatar por iniciais e username derivado do e-mail; foto
  e username reais no backend ficam para um ciclo futuro.
- **Ícones sem `fill`** (`Spinner.svg`, `CaretDown.svg`) não são cobertos pelo
  `replaceAttrValues` (não têm valor `black` para trocar) e ainda renderizam pretos;
  o `MagnifyingGlass.svg` foi ajustado manualmente com `fill="currentColor"`.
  Follow-up: `fill="currentColor"` nesses dois ou um `svgProps` global no svgr.
- **Validação visual do dark mode** feita pelo Gabriel no navegador (o jsdom não
  carrega CSS, então essa parte não é coberta por teste automatizado).

### O que lembrar

- **Variáveis CSS são a ponte de tema entre mundos:** Tailwind 4 (`@theme`) e libs
  de terceiro (`react-pro-sidebar`, MUI) podem ler os mesmos `var(--…)`; trocar o
  `data-theme` no `<html>` re-tema tudo de uma vez, sem cola recorrente.
- **Zustand** resolve estado global pequeno de UI com assinatura seletiva e
  `persist`, sem re-render de árvore inteira (Context) nem estado local isolado.
- **`fill` de SVG não cascateia para um `<path>` que tem `fill` próprio.** Para um
  ícone ser temável, o path precisa usar `currentColor` (ou herdar) — aí `text-*`/
  `color` controla, e o mesmo mecanismo serve para svgr e MUI.
- Usar lib pronta (react-pro-sidebar) troca o aprendizado do Item 10 de "construir
  um pattern" para "integrar e tematizar" — decisão de trade-off consciente, não
  padrão quebrado em silêncio.
- Tokens **semânticos** (papéis: surface/content/line…) envelhecem melhor que a
  paleta por nome de cor (gray-100…), porque o mesmo papel troca de valor por tema.

## Ciclo de feature — Restyle com shadcn/ui (Item 10, segunda passagem)

**Status:** concluído em 2026-07-27.

**Repositórios e branches:** `Refund-FrontEnd` (branch `feat/shadcn-restyle`,
commits `957c5b1..b66aa16`) e `Refund-api` (branch `feat/refund-list-sum`,
commit `5fae554` para a soma na listagem, mais o commit de documentação deste
ciclo). **Nenhuma das duas branches foi mesclada** — o merge depende de
autorização.

**Natureza:** segundo ciclo de feature interligado à trilha, no mesmo formato do
ciclo do shell (brainstorming → spec → plano → execução), desta vez executado em
10 tasks com revisão de código a cada task. Spec e plano em
`Refund-FrontEnd/docs/superpowers/{specs,plans}/2026-07-27-shadcn-restyle*`.

**Item da trilha:** **Item 10 — Pattern layer, segunda passagem.** O ciclo do
shell tratou essa camada **integrando uma lib pronta** (`react-pro-sidebar`,
tematizada por variáveis CSS). Este trata a mesma camada pela via oposta:
**posse do código**.

### Por que estudar

O gatilho foi estético — a estilização anterior não agradava. O conteúdo de
aprendizado é outro: **shadcn/ui não é uma dependência, é um _registry_.** O CLI
copia o `.tsx` para dentro do repositório e sai de cena. Não existe
`import { Button } from "shadcn"`; existe `src/components/ui/button.tsx`, um
arquivo versionado no projeto como qualquer outro.

Isso põe frente a frente dois modelos de consumir componente de terceiro, e a
pergunta do item é **quando cada um compensa**: quem versiona o componente, quem
paga o custo do upgrade e o que você ganha e perde em cada escolha.

### Estado anterior

Design system próprio em Atomic Design, `src/components/{atoms,molecules}`, com
`Text`, `Icon`, `Skeleton`, `Button`, `ButtonIcon`, `Dialog`, `InputText`,
`InputFile`, `InputLabelWrapper` e `PopOverMenu` — 10 arquivos, **692 linhas** de
código de componente (sem contar testes), escritos com `tailwind-variants` e
`classnames`:

```tsx
// src/components/molecules/Button.tsx (antes)
import {tv, type VariantProps} from "tailwind-variants";
export const buttonVariants = tv({
  base: "flex items-center justify-center cursor-pointer transition rounded group gap-1",
  variants: {
    variant: { primary: "bg-accent hover:bg-accent-strong" },
    size: { sm: "h-12 w-full py-4 px-5", fit: "h-11 w-fit py-2.5 px-5" },
  },
});
```

E uma paleta própria em `src/index.css`, herdada do ciclo do shell, com uma
linha decisiva:

```css
:root { --surface: #ffffff; --accent: #1F8459; --content: #1F2523; /* … */ }

@theme {
  --color-*: initial;          /* apaga TODAS as cores padrão do Tailwind */
  --color-surface: var(--surface);
  --color-accent:  var(--accent);
}
```

### A limitação encontrada

Colar qualquer componente do registry naquele projeto produzia um elemento
**sem estilo nenhum**. O `button.tsx` do shadcn usa `bg-primary`,
`border-input`, `text-muted-foreground` — nomes que não existiam na paleta do
projeto. E o fallback também não existia: `--color-*: initial` tinha apagado as
cores padrão do Tailwind. Ou seja, o design system era uma **ilha fechada**:
toda tela nova continuaria sendo construída à mão sobre `atoms`/`molecules`.

Havia ainda duas dívidas paradas: `npm run lint` já abria com **18 erros**
preexistentes de `react-refresh/only-export-components`, e a `PageHome` era um
card `max-w-2xl` com `min-h-screen` próprio — escrita antes do shell existir, e
por isso brigando com a sidebar e a topbar que a emolduram hoje.

### Comparação visual

O eixo do item:

| | Dependência (`react-pro-sidebar`) | Copy-in (shadcn) |
|---|---|---|
| Quem versiona o componente | o autor da lib | você |
| Como customizar | props e CSS que ela expôs | edita o arquivo |
| Upgrade | `npm update`, pode quebrar | não existe; você já é o dono |
| Bug no componente | issue no repositório dela | é **seu** bug |
| Custo | superfície pequena, teto de customização baixo | mais código seu para manter |

```text
ANTES   src/components/atoms + molecules  (692 linhas, 10 arquivos, meus)
        tailwind-variants + classnames
        paleta própria: --surface/--app/--accent/--content/--line/…
        @theme { --color-*: initial }   → cores do Tailwind apagadas
        colar um bloco do registry = elemento sem estilo
        lint: 18 erros

DEPOIS  src/components/ui  (2033 linhas, 15 arquivos, copiados do registry —
                            e meus a partir do momento em que foram copiados)
        cva + clsx + cn()
        tokens do shadcn: --background/--foreground/--primary/--border/…
        cores padrão do Tailwind de volta
        colar um bloco do registry = sai certo, sem ajuste
        lint: 0 erros (primeira vez na trilha)
```

### Estado ajustado

**Fundação.** O `components.json` (`baseColor: neutral`, `cssVariables: true`,
`iconLibrary: lucide`) foi escrito à mão, com os aliases apontando para o `@/`
que existe desde o Item 9; o `src/index.css` trocou de vocabulário inteiro; e o
`cn()` entrou em `src/lib/utils.ts`. O ponto que **não** mudou foi o seletor de
tema:

```css
/* src/index.css (depois) — shadcn entrega dark mode como classe `.dark`;
   o projeto já dirige o tema por <html data-theme="…"> desde o Item 12. */
@custom-variant dark (&:is([data-theme="dark"] *));

:root {
  --background: oklch(1 0 0);
  --foreground: oklch(0.145 0 0);
  --primary: oklch(0.205 0 0);
  --border: oklch(0.922 0 0);
  /* … + --card/--popover/--muted/--accent/--destructive/--ring/--sidebar-* */
}
```

Uma linha de `@custom-variant` preservou o `ThemeEffect` e a store Zustand do
Item 12 intactos — nenhum arquivo de tema precisou ser reescrito.

**Estrutura.** `src/components/ui/` nasceu; `atoms/` e `molecules/` deixaram de
existir. No `eslint.config.js` a camada `ui` do Item 9 passou de
`['src/components/atoms', 'src/components/molecules']` para
`['src/components/ui']`; **as políticas de dependência não mudaram** — a fitness
function do Item 9 continuou valendo durante todo o ciclo.

**Mapa da troca:** `Button`+`ButtonIcon` → `ui/button` (`size="icon"`);
`InputText`+`InputLabelWrapper` → `ui/input`+`ui/label`+`ui/form`; `Dialog` →
`ui/dialog`; `PopOverMenu` → `ui/select`; `InputFile` → `ui/input-file`
(wrapper próprio sobre o `input type=file`); `Skeleton` → `ui/skeleton`; `Text`
→ classes Tailwind diretas; `Icon` + 12 SVGs de UI → `lucide-react`;
`react-pro-sidebar` → `ui/sidebar` + `ui/sheet`. Só o `Receipt.svg` ficou, por
ser marca e não ícone de sistema.

**`ui/form` fechou trabalho manual do Item 7.** Ele é nativo de react-hook-form
+ `zodResolver` e emite `aria-invalid`/`aria-describedby` sozinho — exatamente o
que `InputText`/`InputLabelWrapper` faziam à mão. As auditorias `vitest-axe`
existentes foram reexecutadas contra ele e seguem verdes.

**`ui/select` fechou uma pendência de a11y.** O `PopOverMenu` era um `Popover`
do Radix com uma lista de `div`s: abria por teclado (Item 7), mas percorrer as
opções com ↑/↓ exigiria escrever o handler à mão, e isso nunca foi feito. O
`ui/select` é um listbox de verdade — expõe `role="combobox"` no gatilho e
`role="option"` nas opções, com o padrão de teclado do WAI-ARIA já implementado
pelo Radix:

```tsx
// RefundFormDialog.test.tsx
it("lets the user pick a category with the keyboard", async () => {
  await userEvent.click(screen.getByRole("combobox", { name: "Categoria" }));
  await userEvent.click(await screen.findByRole("option", { name: "Alimentação" }));
  expect(screen.getByRole("combobox", { name: "Categoria" }))
    .toHaveTextContent("Alimentação");
});
```

O teste prova os **papéis** (é um combobox com options, não uma pilha de divs);
a navegação por ↑/↓ passa a existir porque o Radix a implementa, mas **nenhum
teste automatizado dirige as setas** — ver "Verificações e limitações".

**`ui/input-file` fechou a pendência do campo `file`.** O `refundCreateSchema`
tinha o campo `file` sem teste porque montar um `FileList` no jsdom é
desagradável. O `userEvent.upload` faz isso:

```tsx
// src/components/ui/input-file.test.tsx
const file = new File(["nota"], "nota-fiscal.pdf", { type: "application/pdf" });
await userEvent.upload(screen.getByLabelText("Comprovante"), file);
expect(screen.getByText("nota-fiscal.pdf")).toBeInTheDocument();
```

Detalhe descoberto no caminho: `userEvent.upload` **respeita o atributo
`accept`** como um seletor de arquivos real. Um `.txt` contra
`accept=".jpg,.jpeg,.png,.pdf"` é silenciosamente descartado e nunca chega ao
`FileList` — o erro observado vira "Anexe o comprovante", não "extensão
inválida". Por isso o teste de rejeição usa um PDF **grande demais** (5 MB), não
um arquivo de extensão errada.

**`PageHome` virou painel.** Saiu o `max-w-2xl`/`min-h-screen`; entraram
cabeçalho de página, faixa de resumo com dois cards (**Solicitações** = `total`,
**Total** = `sum_amount_in_cents`), toolbar de busca (search params e debounce do
Item 3 preservados), lista em painel com `Link` por linha e paginação por
botões-ícone. É a estrutura que o ciclo do TanStack Table (Item 13) vai exigir,
então a Home foi mexida uma vez só.

### Copy-in na prática — os três momentos que ensinaram o conceito

O conceito não ficou abstrato: apareceu três vezes durante a execução, sempre
como uma decisão que **só existe porque o código é nosso**.

**1. Editar o `sidebar.tsx` à mão.** O `SidebarProvider` do shadcn persiste o
estado da sidebar em cookie. Pior: ele escrevia o cookie **incondicionalmente**,
mesmo quando o provider está controlado por fora — que é exatamente o nosso caso
(`open`/`onOpenChange` ligados à store Zustand do Item 12). A revisão da Task 7
pegou isso. A correção foi apagar a escrita e as duas constantes, dentro do
arquivo do registry:

```tsx
// src/components/ui/sidebar.tsx
const setOpen = React.useCallback((value) => {
  const openState = typeof value === "function" ? value(open) : value;
  if (setOpenProp) { setOpenProp(openState); } else { _setOpen(openState); }

  // This project persists sidebar state through the Zustand store
  // (src/stores/ui.ts, localStorage["refund-ui"]) instead of a cookie —
  // the store must stay the single source of truth for UI preferences.
}, [setOpenProp, open]);
```

**Isso não se faz numa dependência do npm.** Com `react-pro-sidebar`, a saída
seria abrir issue, esperar, ou construir uma gambiarra em volta. É o argumento a
favor do copy-in, em uma tela.

**2. "Vendorizado" não é sinônimo de "isento".** Na Task 9, ao zerar o lint, o
override do ESLint ganhou um comentário dizendo que os arquivos de
`components/ui` são "copiados do registry e **não são editados à mão**". A
revisão apontou a contradição: a Task 7 tinha editado o `sidebar.tsx` à mão
naquele mesmo ciclo. O comentário foi reescrito para dizer só o que é verdade.
A lição é que "código de terceiro" deixou de ser uma categoria útil no momento
em que o arquivo entrou no repositório — ele é código do projeto, com as mesmas
obrigações.

**3. Bug de upstream vira bug seu.** Duas regras do React Compiler
(`eslint-plugin-react-hooks` 7) reprovam o código **gerado**, de fábrica:

| Arquivo | Regra | O que há lá |
|---|---|---|
| `src/components/ui/sidebar.tsx:608` | `react-hooks/purity` | `Math.random()` dentro de um `useMemo` (largura do skeleton) |
| `src/hooks/use-mobile.ts:14` | `react-hooks/set-state-in-effect` | `setIsMobile` chamado direto no corpo do `useEffect` |

Nenhum `npm update` conserta isso. A primeira tentativa desligou as duas regras
para `src/components/ui/**` inteiro; a revisão reprovou, com um critério que vale
guardar — **distinguir a natureza da regra**:

```js
// estrutural: cva exportado ao lado do componente. Sem efeito em runtime,
// vale para toda a superfície do registry → desligada no diretório inteiro.
{ files: ['src/components/ui/**/*.{ts,tsx}'],
  rules: { 'react-refresh/only-export-components': 'off' } },

// correção: pegam bug de verdade. Desligadas por arquivo, pelo nome, para que
// um componente novo que as viole continue aparecendo no lint.
{ files: ['src/components/ui/sidebar.tsx', 'src/hooks/use-mobile.ts'],
  rules: { 'react-hooks/purity': 'off',
           'react-hooks/set-state-in-effect': 'off' } },
```

**O preço, dito sem enfeite.** O design system saiu de **692 linhas em 10
arquivos** para **2033 linhas em 15 arquivos** — quase 3× mais código de
componente sob nossa responsabilidade. O `sidebar.tsx` sozinho tem 723 linhas e
define 24 componentes, dos quais o shell usa 11; os outros 13 são superfície que
o projeto carrega sem exercitar, e que ninguém vai notar quebrar. Saíram 7
dependências e entraram 3, o que é bom para o `package.json` — mas o código não
desapareceu: mudou de dono.

### Backend — a soma na mesma query

A faixa de resumo precisa do total em dinheiro de **todo o conjunto filtrado**,
não da página visível — somar `attributes` no frontend daria um número errado
sempre que houvesse mais de uma página. O `select_refunds` já montava `filters` e
rodava um `count`; a soma entrou na **mesma query**, sem segundo round trip:

```python
# src/models/repositories/refunds_repository.py
totals_query = (
    select(func.count(), func.sum(Refunds.c.amount_in_cents))
    .select_from(Refunds)
    .where(*filters)
)
total, total_amount = (await session.execute(totals_query)).one()
# …
return refunds, total, total_amount or 0   # SUM sobre conjunto vazio é NULL
```

A propagação (`tuple[list[dict], int, int]` → interface → controller →
`sum_amount_in_cents` no response) foi feita por TDD, com o RED real registrado:
os 7 testes do controller quebraram com
`ValueError: too many values to unpack (expected 2)` antes da mudança. O teste
do controller prova **encaminhamento, não recálculo** (os itens mockados não têm
campo de valor), e o do repository cobre o caso `NULL → 0`.

No frontend, o `refundsListResponseSchema` ganhou `sum_amount_in_cents` — e isso
produziu a melhor evidência do ciclo de que a fronteira do Item 2 funciona: ao
adicionar o campo ao schema **antes** de atualizar o handler do MSW, a query foi
para `isError` em vez de `isSuccess`, porque o `.parse` rejeitou o response
incompleto. Um response malformado não entra no cache.

### Arquivos modificados

**`Refund-FrontEnd`** (14 commits, `957c5b1..b66aa16`):

- **Fundação:** `components.json` (novo), `src/lib/utils.ts` (novo, `cn()`),
  `src/index.css` (substituído por inteiro), `eslint.config.js` (camada `ui` +
  os dois overrides), `package.json` (entram `lucide-react`,
  `class-variance-authority`, `clsx`; saem `@mui/icons-material`,
  `@mui/material`, `@emotion/react`, `@emotion/styled`, `react-pro-sidebar`,
  `tailwind-variants`, `classnames`).
- **Design system:** `src/components/ui/` com 15 componentes — `button`, `input`,
  `label`, `form`, `card`, `dialog`, `select`, `input-file`, `skeleton`,
  `badge`, `separator`, `sidebar`, `sheet`, `tooltip`, `dropdown-menu` — mais
  `src/hooks/use-mobile.ts`. Testes próprios em `button.test.tsx` e
  `input-file.test.tsx`.
- **Shell:** `src/components/core/{MainLayout,Sidebar,Topbar,nav-items}.tsx`
  reescritos sobre `ui/sidebar`; `src/stores/ui.ts` ganhou
  `setSidebarCollapsed(boolean)`.
- **Telas:** `PageLogin`, `PageRegister`, `PageHome`, `PageRefundDetails`,
  `PageSuccess`, `PageRouteError` e `PageComponents` (reconstruída como galeria
  dos componentes).
- **Feature:** `src/features/refunds/components/RefundFormDialog.tsx`,
  `constants/categories.ts` (ícones SVGR → `LucideIcon`),
  `schemas/refund.ts` (`sum_amount_in_cents`).
- **Testes:** novos `PageHome.test.tsx`, `PageRegister.test.tsx`,
  `PageRefundDetails.test.tsx`, `PageRouteError.test.tsx`;
  `src/test/setup.ts` ganhou um polyfill de jsdom (ver limitações);
  `src/test/msw/handlers.ts` passou a devolver `sum_amount_in_cents`.
- **Removidos:** `src/components/{atoms,molecules}/` inteiros e 12 SVGs de UI.
- **`AGENTS.md`:** saiu "Preserve a organização em Atomic Design"; entrou a
  regra de que componente novo vem do registry para `src/components/ui`.

**`Refund-api`:**

- `src/models/repositories/refunds_repository.py` e sua interface,
  `src/controllers/refund_lister_controller.py`, mais os respectivos `_test.py`.
- `docs/use-cases/UC-004-list-refunds.md` (campo `sum_amount_in_cents` no
  contrato de response).
- Documentação da trilha: este diário e o
  [`current-state.md`](plans/current-state.md).

**Correção de rota do roadmap:** o
[spec do shell](../../Refund-FrontEnd/docs/superpowers/specs/2026-07-26-frontend-shell-sidebar-theme-design.md)
citava `@mui/x-data-grid` para a lista de reembolsos. Trocado por **TanStack
Table**, que é o que o Item 13 do `learning_path.md` e o
`arquitetura_ideal_adaptada.md` sempre disseram — só aquele spec tinha
introduzido o Data Grid.

### Verificações e limitações

Executadas ao fechar o ciclo, com os números observados:

| Comando | Resultado |
|---|---|
| `npm run test` | **75 testes em 24 arquivos**, todos verdes |
| `npx tsc -b --noEmit` | exit 0 |
| `npm run build` | ok — e **sem o aviso de chunk > 500 kB** que aparecia em todas as verificações anteriores (o bundle principal ficou em 491,44 kB depois da saída do MUI) |
| `npm run lint` | **0 erros, 0 warnings** — a primeira vez na trilha |
| `pytest` | **73 testes**, todos verdes |
| `pylint src` | **10.00/10**, exit 0 |

A contagem de testes merece explicação: o ciclo saiu de 59, chegou a **86** e
terminou em **75**. A queda de 11 é exatamente a soma dos testes dos 4 arquivos
de `molecules/` deletados (`Button` 4, `Dialog` 2, `InputText` 3, `PopOverMenu`
2) — o comportamento que eles verificavam passou a ser coberto onde o
componente é usado. Saldo real: **+16 testes** sobre o início do ciclo.

**Pendências e limitações registradas:**

- **O app não foi aberto no navegador neste ciclo.** *Todas* as verificações
  acima são automatizadas. Como o jsdom não carrega CSS, um restyle completo é
  justamente o tipo de mudança que os testes não conseguem validar: contraste,
  alinhamento, dark mode, colapso da sidebar e a faixa de resumo da Home
  continuam **não validados visualmente**. Pelo contrato da trilha, o item
  **não** pode ser apresentado como totalmente validado até que isso aconteça.
- **Navegação por seta do `Select` não tem teste.** O `ui/select` é um listbox de
  verdade e o Radix implementa o padrão de teclado, mas o teste existente usa
  cliques, não ↑/↓. A pendência de a11y do `PopOverMenu` foi fechada pela
  **troca de componente**, não por uma prova automatizada da navegação.
- **Polyfill de jsdom em `src/test/setup.ts`.** O Radix `Select` chama
  `hasPointerCapture`/`setPointerCapture`/`releasePointerCapture` e
  `scrollIntoView`, que o jsdom não implementa; sem os no-ops, qualquer teste
  que abra o Select estoura. Está guardado por `if (!…)` e espelha o polyfill de
  `matchMedia` que já existia. **Mas o `AGENTS.md` do frontend pede alinhar
  infraestrutura transversal de teste _antes_ de introduzi-la**, e aqui ela foi
  sinalizada depois do fato.
- **Bug do CLI do shadcn, recorrente.** `npx shadcn@latest add <componente>`
  escreve num diretório literal `./@/` na raiz do repositório em vez de resolver
  o alias. Causa: o `tsconfig.json` raiz não tem `paths` (eles vivem no
  `tsconfig.app.json`, via project references) e o CLI só lê o da raiz. Aconteceu
  em **todas** as quatro tasks que rodaram o CLI; a correção é mecânica (mover os
  arquivos e apagar o `./@`), mas vai acontecer de novo.
- **O CLI também mexe no `src/index.css` sem avisar.** Numa das execuções ele
  acrescentou um bloco `.dark { --sidebar-*: … }` — seletor errado para este
  projeto, que usa `[data-theme="dark"]`. Revertido com `git checkout`. Conferir
  `git diff src/index.css` depois de cada `add`.
- **Menores adiados** (nenhum bloqueia; ficam registrados para não sumirem):
  - `ui/button.tsx` do registry traz mais tamanhos (`xs`, `icon-xs`, `icon-sm`,
    `icon-lg`) do que os 4 documentados no spec — superfície maior que o
    contrato descrito.
  - `dropdown-menu.tsx` foi gerado e **não é consumido por ninguém**: veio junto
    no `npx shadcn@latest add sidebar sheet tooltip dropdown-menu` da Task 7,
    porque é o padrão de menu de usuário que os dashboards do shadcn costumam
    usar — mas o shell deste projeto não tem esse menu. É o único arquivo de
    `components/ui` sem consumidor.
  - `separator.tsx` **é** consumido (`components/core/Topbar.tsx` e o próprio
    `ui/sidebar.tsx`); o que falta é aparecer na galeria da `PageComponents`,
    que hoje mostra 8 componentes (Button, Input, Select, Dialog, Card, Badge,
    Skeleton, InputFile). Não confundir "não está na vitrine" com "não é usado".
  - No `RefundFormDialog`, o cast do campo `amount` é
    `as string | number | undefined`, mais largo que a realidade (`number` nunca
    ocorre) — `as string | undefined` seria honesto.
  - `PageHome.tsx` manteve alguns imports relativos (`../lib/format`,
    `../hooks/useDebouncedValue`, `../router-loaders`) em vez de `@/`, apesar da
    reescrita completa.
  - Cobertura faltando: ramos de erro/vazio/última página na `PageHome`, e o
    estado intermediário de exclusão ("Excluindo…", Confirmar desabilitado) na
    `PageRefundDetails`.
  - `refunds_repository_test.py` ganhou um `# pylint: disable=duplicate-code` no
    módulo, que também silencia duplicação genuína futura naquele arquivo
    (espelha precedente já existente em `src/views/refund_deleter_view.py`).
  - `PageRegister` (e `PageLogin`, de onde o padrão veio) **perdeu o `required`
    nativo** dos campos; o `type="email"` continua lá. Efeito prático: campo
    vazio não é mais bloqueado pelo navegador — chega ao Zod e a mensagem
    aparece no submit. Foi uma decisão consciente, não um efeito colateral.
- **`src/components/organisms` ainda é citado** no padrão da camada `app` do
  `eslint.config.js`, mas a pasta não existe no disco. É anterior a este ciclo.

### O que lembrar

- **Copy-in vs. dependência é uma troca de _quem paga_, não de _quanto custa_.**
  Dependência: superfície pequena, upgrade grátis, teto de customização baixo.
  Copy-in: customização ilimitada, upgrade inexistente — porque o código já é
  seu, com bug e tudo. Escolha copy-in quando **precisar editar por dentro**;
  escolha dependência quando quiser o problema resolvido por outra pessoa.
- **O momento de decidir é antes de colar o primeiro arquivo.** Depois, o código
  está no repositório e a discussão acabou.
- **"Vendorizado" não é sinônimo de "isento".** Assim que o arquivo entra no
  repositório, ele é código do projeto: passa pelo lint, pela revisão e pela
  responsabilidade de correção como qualquer outro.
- **Ao silenciar uma regra de lint, classifique a regra antes.** Regra
  **estrutural** (padrão do gerador, sem efeito em runtime) pode ser desligada no
  diretório inteiro. Regra de **correção** só se desliga por arquivo, pelo nome —
  senão o próximo componente que introduzir o bug de verdade entra em silêncio.
- **Adotar um design system pronto é adotar o vocabulário dele inteiro.** Não
  existe meio caminho barato: alias sobre os nomes antigos só compensaria se as
  telas antigas fossem ficar — e não iam.
- **Uma linha bem colocada evita reescrever um sistema.** O
  `@custom-variant dark (&:is([data-theme="dark"] *))` preservou o
  `ThemeEffect` e a store do Item 12 sem tocar em nenhum dos dois.
- **Trocar componente por um primitivo acessível fecha dívida de a11y de
  graça** — `ui/form` gerou o `aria-invalid`/`aria-describedby` do Item 7
  sozinho, e `ui/select` trouxe o padrão de listbox que o `PopOverMenu` nunca
  teve. Mas "fechou por construção" não é o mesmo que "está testado".
- **Agregado tem que vir do servidor.** Somar a página no cliente dá um número
  errado a partir da segunda página; a soma foi para a **mesma query** do
  `count`, respeitando os mesmos filtros e a mesma regra de autorização.
- **`SUM` sobre conjunto vazio é `NULL`, não `0`** — precisa de coerção
  explícita, e de um teste para ela.
- **`userEvent.upload` respeita o `accept`** do input, como um seletor de
  arquivos real. Para testar rejeição por conteúdo, use um arquivo de extensão
  válida e tamanho inválido.
- **Item 10 foi visto duas vezes, de propósito:** integrar e tematizar uma lib
  pronta (ciclo do shell) e possuir o código do componente (este ciclo). São as
  duas respostas legítimas para a mesma camada, e o valor de ter visto as duas é
  saber reconhecer qual das duas o próximo problema pede.

## Validação visual do ciclo do restyle (2026-07-28)

Não é um item novo da trilha: é o **fechamento da pendência** que o ciclo do
restyle deixou aberta de propósito — "o app não foi aberto no navegador neste
ciclo". Pelo `learning-path-workflow.md`, o Item 10 (segunda passagem) não podia
ser apresentado como totalmente validado enquanto isso não acontecesse.

### Por que precisou de uma passada manual

Todas as verificações do ciclo foram automatizadas: 75 testes, typecheck, build,
lint, pytest, pylint. Nenhuma delas enxerga cor, posição ou tamanho — o jsdom
não carrega CSS nem faz layout. Um restyle é exatamente a classe de mudança que
uma suíte verde não consegue defender. A pendência não era falta de disciplina;
era o limite da ferramenta.

### Como foi feito

Em vez de sair clicando, as pendências do `current-state.md` foram traduzidas em
um **checklist explícito** (mantido no Notion, em `Work → ToBeBetter`), agrupado
por item da trilha: shell e restyle, responsividade, faixa de resumo, tema
(Item 12), cache (Item 1), estado na URL (Item 3), schemas contra a API real
(Item 2), a11y (Item 7), fluxo de criação e tela de detalhe.

O ganho de escrever o checklist antes: a diferença entre "olhei e pareceu ok" e
"verifiquei o que estava em dúvida" fica registrada por item, e o que **não**
foi verificado sobra visível em vez de sumir no meio de uma impressão geral.

### O que fechou

- Contraste no claro e no escuro (leitura a olho), alinhamento das telas.
- A **emenda sidebar↔topbar** — as duas bordas inferiores na mesma linha, que é
  a razão de existir do `h-17.5` nos dois componentes.
- Colapso da sidebar em modo trilho, estado ativo e hover da navegação.
- Drawer no mobile: overlay, Esc, scroll não vazando, Home empilhando.
- Persistência de tema e de estado da sidebar após reload, sem flash.
- Faixa de resumo: alinhamento, o total respeitando o filtro da busca, o total
  **não** mudando ao trocar de página, e o plural de "1 solicitação".
- **Item 1 completo**: lista, busca, paginação, criação, detalhe e — o item que
  exigia a aba Network — o `staleTime` de 30s impedindo o refetch ao voltar.
- **Item 3 completo**: login, URL direta, reload, `?name=`, `?page=`,
  back/forward, normalização de parâmetro inválido, página de erro e omissão dos
  valores padrão da URL.
- Navegação por ↑/↓ no `Select` de categoria, foco visível no Tab, foco no
  primeiro campo com erro.
- Botão "Excluir" confirmado usando `variant="destructive"` — o vermelho vem do
  token, não sobrou cor fixa da paleta antiga.

### O que ficou aberto, e por quê

- **Schemas contra a API real (Item 2)** — único bloco sem marcação nenhuma.
- **Contraste auditado com ferramenta** — o checklist separou de propósito
  "parece legível" de "auditado no DevTools"; só o segundo dá um número.
- **Rejeição de comprovante por tamanho/extensão** — o upload feliz foi
  validado, o caminho de rejeição não.
- **O "Choose File / No file chosen"** — marcado como *verificado*, não
  *resolvido*: o item pedia uma decisão sobre estilizar o input nativo, e a
  decisão continua em aberto.

### Os ajustes manuais que vieram junto

Quatro commits do Gabriel direto na `main` do frontend durante e depois da
validação (`3929a37`, `f336ae1`, `2d07a8d`, `6326606`). O último tem duas
mudanças com intenção clara, documentadas no `current-state.md`: `w-full` no
`SelectTrigger` da Categoria (que tem largura por conteúdo e ficava estreito
dentro de um `flex-1`) e o ícone `CloudUpload` reposicionado para dentro da
borda do input via `relative` + `absolute right-0`.

### O que lembrar

- **Suíte verde não é o mesmo que aplicação certa.** A cobertura de uma suíte
  termina onde termina a capacidade do ambiente de teste: sem CSS e sem layout,
  o jsdom não tem como falhar por um contraste ruim ou uma borda desalinhada.
  Saber *o que a ferramenta não consegue ver* vale tanto quanto saber usá-la.
- **Transformar pendência em checklist muda o resultado.** Uma pendência em prosa
  ("não foi validado em navegador") vira uma sessão de cliques sem começo nem
  fim. Quebrada em itens verificáveis, ela produz uma resposta por item — e o que
  ficou de fora sobra visível em vez de se dissolver num "está ok".
- **"Verificado" e "resolvido" não são a mesma marcação.** O item do input de
  arquivo foi conferido e a conclusão foi "continua em inglês, falta decidir".
  Marcar isso como fechado perderia a decisão pendente.
- **Confirmar à mão não fecha lacuna de teste.** O reset de página para 1 e a
  navegação por ↑/↓ no `Select` funcionam — foram vistos funcionando. Mas o que
  protege os dois de regredir amanhã é a asserção automatizada, e ela continua
  faltando nos dois casos.
- **`src/components/ui` tem duas origens.** Arquivos copiados do registry
  (`sidebar.tsx`, `select.tsx`…) e arquivos autorais do projeto
  (`input-file.tsx`). Só os primeiros correm o risco de serem sobrescritos por
  um `npx shadcn@latest add`. Editar um arquivo dessa pasta exige saber de qual
  dos dois tipos ele é.

## Ciclo de feature — Workflow de aprovação, backend (Itens 18 e 20)

Terceiro ciclo de feature da trilha, e o primeiro inteiramente de backend.
Cobriu **dois** itens de uma vez, e essa foi a razão de ser o próximo da fila:
nenhum dos dois entrou por completude arquitetural, os dois entraram porque a
feature criou o problema que cada um resolve.

### Por que estudar — e por que só agora

O `learning_path.md` é explícito no Item 20: *"estudar com um caso de uso
realmente multioperação. Não refatorar os CRUDs atuais antes disso."*

Isso quase matou o ciclo antes de começar. Aprovar um reembolso, na forma mais
simples, é **um `UPDATE`** — e Unit of Work coordena commit entre várias
escritas. Com uma só, não há o que coordenar: seria exatamente a abstração
prematura que o próprio item manda evitar.

O que salvou o item foi uma **decisão de produto**, não de arquitetura: guardar
o histórico das decisões numa tabela própria. Aí aprovar vira duas escritas —
`UPDATE refunds` + `INSERT refund_reviews` — que precisam valer juntas. A lição
aqui é anterior ao padrão: **um padrão só se justifica quando o problema dele
existe, e às vezes é o escopo da feature que decide se ele existe.**

O Item 18 foi mais direto: a tabela `refunds` tinha 41 linhas, e
`metadata.create_all` cria tabelas ausentes mas **nunca altera uma existente**.
Adicionar `status` sem migration não é difícil — é impossível.

### Estado anterior

```python
# src/models/repositories/refunds_repository.py
async def insert_refund(self, refund_info: dict) -> int:
    async with self.__db_connection.connect() as session:
        result = await session.execute(insert(Refunds).values(**refund_info))
        await session.commit()          # o repository decide quando confirmar
        return result.inserted_primary_key[0]
```

```python
# src/main/server/server.py
async with engine.begin() as conn:
    await conn.run_sync(metadata.create_all)   # o schema nascia no boot
```

### A limitação encontrada

Com o padrão acima, aprovar seria:

```python
await refunds_repository.update_status(refund_id, "approved")   # commitou
await reviews_repository.insert_review(...)                     # falhou
```

Resultado: **reembolso aprovado sem registro de quem aprovou** — o estado que a
auditoria existe para impedir, e irreversível, porque a primeira sessão já
fechou. Compensar na mão (`try/except` revertendo o status) não resolve: se o
processo morrer entre as duas linhas ninguém compensa, e é reimplementar em
Python, pior, o rollback que o banco dá de graça.

### Comparação visual

| | Antes | Depois |
|---|---|---|
| Dono da transação | o método do repository | o caso de uso, via `UnitOfWork` |
| Escopo do commit | uma escrita | todas as escritas do bloco |
| Falha no meio | primeira escrita persiste | nada persiste |
| Dono do schema | `create_all` no boot | `alembic upgrade head` |
| Alterar tabela com dados | impossível | migration versionada, com `downgrade` |

### Estado ajustado

```python
# src/models/settings/unit_of_work.py
async def __aexit__(self, exc_type, exc_value, traceback) -> None:
    try:
        if exc_type is not None:
            await self.__session.rollback()
    finally:
        await self.__session_ctx.__aexit__(exc_type, exc_value, traceback)
```

```python
# src/controllers/refund_reviewer_controller.py
if role != "admin":                       # ANTES de qualquer acesso ao banco
    raise HttpForbiddenError("Only administrators can review refunds")

async with self.__unit_of_work as unit_of_work:
    refund = await unit_of_work.refunds.select_for_update(refund_id)
    ...
    await unit_of_work.refunds.update_status(refund_id, status)
    await unit_of_work.reviews.insert_review(...)
    await unit_of_work.commit()
```

Os CRUDs existentes **não** foram refatorados. Os dois estilos convivem, e a
diferença entre eles é a lição: um write simples não precisa de UoW; dois writes
que precisam cair juntos, sim.

### Verificações

| Comando | Resultado |
|---|---|
| `pytest` | **105 testes**, todos verdes (partiu de 73) |
| `pylint src` | **10.00/10** ao final de cada uma das 11 tasks |
| Ponta a ponta contra a API real | **10/10 cenários**, status HTTP conferidos um a um |
| `alembic upgrade` / `downgrade` | ciclo completo executado contra o banco real |

O estado do banco após a execução ponta a ponta foi conferido diretamente: duas
linhas em `refund_reviews` com `from_status`/`to_status`/revisor/motivo corretos.

### O que o processo de revisão pegou — e por que isso importa mais que o código

Este ciclo foi executado com um subagente implementador por task e revisão entre
elas. Vale registrar o que a revisão encontrou, porque **três dos achados eram
defeitos do plano**, não da execução:

1. **O baseline vazio do Alembic.** O plano mandava conferir que o `autogenerate`
   traria `create_table`. Contra um banco que já bate com as entidades, ele traz
   **vazio** — e um baseline vazio parece funcionar (o `stamp` reconcilia o banco
   atual) e quebra em qualquer ambiente novo. A saída: escrever o `create_table`
   à mão e **provar que está certo gerando uma migration descartável** — se ela
   sai vazia, o baseline bate com o schema real; qualquer coluna errada
   apareceria como `add_column`.

2. **Vazamento de conexão no `__aexit__` (Critical).** O código do plano fechava a
   sessão *depois* do rollback, sem `try/finally`. Se o rollback falhasse — e ele
   pode, porque a exceção original pode ter quebrado a conexão —, a sessão nunca
   fechava. Com `pool_size=2, max_overflow=0`, dois vazamentos travam a API
   inteira.

3. **Sete testes que não podiam falhar.** O padrão se repetiu em duas tasks. O
   mais instrutivo: um teste chamado `..._the_database_is_never_touched` que só
   verificava que a leitura não aconteceu. Mover a checagem de papel para dentro
   da transação continuaria passando — enquanto toda requisição não autorizada
   consumiria uma conexão. **O nome prometia mais do que a asserção provava.**
   Confirmado por teste de mutação: aplicada a mutação, o teste corrigido falha.

4. **Uma condição de corrida entre os dois estilos de repository**, achada só na
   revisão final da branch. A exclusão lia o status numa sessão e apagava em
   outra; uma aprovação concorrente no meio fazia o `DELETE` bater na FK do
   histórico e virar **500**. Corrigido tornando o `DELETE` condicional
   (`where id = ? and status = 'pending'`) e tratando `rowcount == 0` como 422.

### O que lembrar

- **Um padrão só se justifica quando o problema dele existe.** Unit of Work sobre
  uma escrita só é indireção sem garantia. Antes de adotar, pergunte: *este caso
  de uso tem duas ou mais escritas que precisam valer juntas?*
- **`create_all` opera na granularidade de tabela.** Ele cria o que falta e nunca
  altera o que existe. Não é limitação a contornar: alterar tabela com dados num
  restart é perigoso, e é de propósito que ele se recusa.
- **`autogenerate` é rascunho, não resposta.** Ele compara a metadata com o banco
  **conectado** — então contra um banco já atualizado o diff correto é vazio. E
  ele omite `server_default` com frequência, o que faria o `ALTER TABLE` falhar
  nas linhas existentes.
- **Um `finally` pode ser load-bearing.** Fechar recurso não pode depender do
  passo anterior ter dado certo. A pergunta que revela esse bug: *"e se esta
  linha aqui levantar?"*
- **A ordem das checagens é decisão de segurança.** Verificar o papel antes de
  qualquer consulta não é estilo: uma checagem que não consulta não revela se o
  id existe, então o 403 é idêntico para id real e inventado. É o mesmo raciocínio
  do 404 da BR-013.
- **Teste que não pode falhar é pior que teste ausente**, porque compra confiança
  sem entregar proteção. O jeito de descobrir: para cada asserção, pergunte *"que
  bug faria isto falhar?"* — se não houver resposta, a asserção é decorativa. E
  quando der, prove com mutação em vez de leitura.
- **Duas escritas atômicas não bastam se um terceiro caminho não participa da
  transação.** O `UPDATE`+`INSERT` estava correto desde o início; o furo estava na
  exclusão, que lia e apagava em sessões diferentes. Atomicidade é propriedade do
  sistema, não de um caso de uso.
- **`SELECT ... FOR UPDATE` só é possível porque existe uma transação em volta.**
  Com o padrão antigo, a leitura já teria encerrado a própria sessão antes de
  qualquer decisão ser tomada.

## Ciclo de feature — Consulta da listagem e foto de perfil (2026-07-29)

Quarto ciclo de feature, inteiramente de backend, feito **antes** do frontend de
propósito: construir tela contra uma API que muda em seguida é retrabalho
garantido.

### O que originou o ciclo — uma armadilha, não uma funcionalidade

O plano do frontend inclui o TanStack Table com toolbar de filtro e ordenação.
Mas a API pagina **no servidor**: o frontend pede `per_page=6` e recebe 6 linhas.
O toolbar do TanStack ordena e filtra **o que está na tabela** — ou seja, com 41
reembolsos, um filtro de status olharia 6 deles e uma ordenação por valor
ordenaria a página, não o conjunto.

**Funcionaria visualmente e mentiria.** É pior do que não existir, porque o
usuário confia no que vê.

A lição que dá nome ao ciclo: **ordenação e filtro têm de viver onde vive a
paginação.** Se a paginação é do servidor, filtrar no cliente é filtrar uma
amostra arbitrária.

### O que mudou

- `GET /refunds` ganhou `status`, `sort` e `order`, com listas brancas e 422 fora
  delas. `total` e `sum_amount_in_cents` respeitam o filtro — senão o card de
  resumo diria um número e a lista mostraria outro.
- Toda resposta de reembolso ganhou um objeto `user` aninhado e **perdeu o
  `user_id` do topo**; a tela de revisão do admin precisa do nome de quem pediu,
  não de um id.
- `POST /refunds` passou a reler a linha gravada, para criação, listagem e
  detalhe devolverem **uma** forma.
- Foto de perfil: coluna, `POST`/`DELETE /users/me/avatar`, arquivo servido em
  `/avatars/{filename}`.
- `ReceiptStorage` virou `FileStorage` recebendo o diretório no construtor.
- Dívida de storage: uploads ignorados pelo git e sete arquivos órfãos removidos.

### Duas barreiras contra nome de coluna vindo do cliente

`sort` acaba virando coluna num `ORDER BY`. A defesa tem duas camadas
independentes:

```python
# 1. o validator recusa o que não está na lista branca
SORTABLE_FIELDS = {"created_at", "amount_in_cents", "name", "status"}

# 2. o repositório usa o nome como CHAVE, nunca como texto
SORTABLE_COLUMNS = {"created_at": Refunds.c.created_at, ...}
column = SORTABLE_COLUMNS.get(sort or "created_at", Refunds.c.created_at)
```

A segunda é a que importa: mesmo que a primeira falhasse, um nome desconhecido
não produz coluna nenhuma — cai no padrão. Concatenar string em SQL nunca chega
a ser uma opção.

### Verificações

| Comando | Resultado |
|---|---|
| `pytest` | **154 testes**, todos verdes (partiu de 105) |
| `pylint src` | **10.00/10** ao fim de cada uma das 13 tasks |
| Ponta a ponta contra a API real | **19/19 cenários**, com a ordem realmente conferida |
| `alembic upgrade`/`downgrade` | ciclo completo contra o banco real |

### O que a revisão pegou — e por que a suíte verde não bastava

Foram cinco achados que a execução sozinha não teria encontrado, e **quatro deles
eram defeitos do plano**, não do implementador:

1. **Uma regressão Critical que 147 testes verdes escondiam.** Mover `user_id`
   para dentro de `user` quebrou dois controllers que ainda liam a chave antiga:
   `KeyError` → **500 em `GET /refunds/{id}` e `DELETE` para todo usuário
   comum**. Admin não era afetado, porque a checagem de papel faz curto-circuito
   antes — quebrava exatamente para quem a verificação de propriedade protege.
   A suíte passava porque os mocks daqueles controllers ainda devolviam o formato
   antigo: **testavam um contrato que o repositório havia deixado de cumprir.**
2. **Paginação instável com a ordenação nova.** Ordenar por `status`, `name` ou
   `amount_in_cents` sem critério de desempate: o PostgreSQL não garante ordem
   entre empates, então com `LIMIT/OFFSET` a mesma linha pode sair em duas
   páginas e outra em nenhuma. Antes só existia `created_at`, onde empate é raro;
   as colunas novas tornam empate o caso normal. Conserto: `id DESC` como
   segundo critério.
3. **Testes que não podiam falhar**, de novo e em três formas diferentes:
   asserção sobre `str(statement)` (parâmetros ligados não aparecem no SQL
   renderizado, então `None` e `"abc.jpg"` produzem a mesma string); ausência de
   qualquer teste sobre a **ordem** das três operações do upload; e dados de
   teste com `"name"` e `"user_name"` iguais, que tornariam uma troca entre os
   dois invisível.
4. **Uma armadilha que quase virou bug novo durante a correção:** existe um
   terceiro `["user_id"]`, no controller de revisão, que **não** podia ser
   mudado — ele lê de `RefundStatusRepository.select_for_update`, outra classe,
   que continua devolvendo o formato achatado.

### O que lembrar

- **Ordenação e filtro pertencem à camada que pagina.** Filtrar no cliente uma
  lista paginada no servidor produz uma interface que mente com confiança.
- **`ORDER BY` sem desempate não é ordenação, é sugestão.** Sempre que houver
  `LIMIT/OFFSET`, o critério precisa ser único — ou a paginação duplica e pula
  linhas, e nenhum teste de uma página só enxerga isso.
- **Mock desatualizado é pior que ausência de teste.** Ele afirma que um contrato
  vale quando o outro lado já mudou. Ao alterar a forma que um repositório
  devolve, o trabalho não é atualizar o repositório — é **encontrar todos os
  consumidores**, e a suíte não vai apontá-los.
- **Parâmetro ligado não aparece em `str(statement)`.** Testar SQL por grep na
  string é cego para valores. Asserte sobre `statement.compile().params`.
- **Quando a ordem das operações é a garantia, ela precisa de um teste próprio.**
  Asserções por chamada individual são todas verdadeiras em qualquer sequência;
  `attach_mock` num pai comum põe as chamadas num log ordenado.
- **Dado de teste igual esconde troca de campo.** Se dois campos podem ser
  confundidos, eles têm de ter valores diferentes no fixture, ou o teste passa
  igual invertido.
- **Duas repositories sobre a mesma tabela podem devolver formas diferentes de
  propósito** — e isso é uma armadilha real. Um call site tem de seguir a forma do
  método específico que consome, não a "forma da tabela".

## Ciclo de feature — Servir arquivos com autenticação (2026-07-29)

Quinto ciclo, e o único que nasceu de uma **pergunta**, não de uma funcionalidade
planejada. Ao levantar o que faltava antes do frontend, uma verificação de rotina
devolveu isto:

```
GET /receipts/<uuid-real>   sem token nenhum   ->   200
```

### O conceito: nome imprevisível é controle de acesso, e fraco

Os comprovantes eram servidos por um mount estático do Starlette, fora da
autenticação. A defesa era o nome do arquivo ser um UUIDv4 — imprevisível.

Isso tem nome: **URL-capacidade**. Quem tem o link, tem o acesso. É um padrão
legítimo em alguns contextos (links de compartilhamento), mas tem duas
propriedades que o tornam inadequado para documento financeiro:

- **O acesso não expira e não é revogável.** Quem viu o link uma vez o mantém
  para sempre, inclusive depois de perder acesso ao reembolso.
- **O link vaza por caminhos que ninguém controla** — histórico do navegador,
  `Referer`, logs de proxy, um print compartilhado.

A troca foi por autorização de verdade: o comprovante só é acessível ao dono e a
admins, verificado a cada requisição contra o banco.

### A ordem importou mais que o conteúdo

O ciclo inteiro existiu **antes** do frontend por um motivo específico: o preview
do comprovante é implementado de duas formas incompatíveis conforme a resposta.

| | Mount público | Rota autenticada |
|---|---|---|
| Como a imagem chega | `<img src="/receipts/x.jpg">` | `fetch` com token → `blob URL` |
| Cache do browser | de graça | não existe |
| Limpeza | nenhuma | `revokeObjectURL` no cleanup |

Decidir isso depois significaria reescrever a tela. **Uma decisão de backend que
muda o desenho do frontend precisa vir antes dele** — não porque bloqueia
tecnicamente, mas porque bloqueia o *desenho*.

### A distinção que a mudança forçou

Ao tirar `filename` da resposta, apareceu uma pergunta que o código nunca tinha
precisado responder: **`filename` é dado interno ou é contrato?**

São as duas coisas, para consumidores diferentes:

- O **cliente** o usava para montar `/receipts/{filename}`. Esse uso morreu.
- O **`refund_deleter_controller`** o lê para apagar o arquivo do disco. Esse uso
  está vivo.
- E o **`receipt_finder_controller`**, criado neste mesmo ciclo, também o lê.

Os três liam do mesmo dicionário, porque os serializadores faziam `**refund` —
espalhando a linha do repositório direto na resposta HTTP. Essa cola é o que
fazia dado interno e contrato serem a mesma coisa.

A separação: **o repositório continua devolvendo `filename`; só o serializador
para de emiti-lo.** Um serializador único (`refund_serializer.py`) passou a
produzir a forma de resposta dos três casos de uso de leitura.

### Verificações

| Comando | Resultado |
|---|---|
| `pytest` | **178 testes**, todos verdes |
| `pylint src` | **10.00/10** ao fim de cada uma das 6 tasks |
| Ponta a ponta contra a API real | **14/14 cenários** |
| `GET /receipts/<uuid>` sem token | **200 → 404** |

Esse último número é o ciclo inteiro condensado. E é o tipo de coisa que teste
unitário não prova: um mount é configuração de servidor, não código de aplicação.

### O que a revisão pegou

- **A documentação canônica ainda garantia a vulnerabilidade.** O `UC-008` dizia
  que a foto era servida "publicamente" e citava o mount que este ciclo apagou.
  Todos os outros UCs foram alinhados; esse escapou. Um leitor seguindo a doc
  construiria contra uma URL que agora dá 404 — e a doc insistiria que o mount
  existe.
- **O login não devolvia o `id` do usuário.** Achado só na revisão final, e
  funcional: com `GET /users/{id}/avatar` exigindo um id que só existe dentro do
  JWT, o cliente ficava sem caminho para exibir **a própria** foto. Avatares de
  terceiros funcionavam, porque vêm em `user.id` nas respostas de reembolso. É
  exatamente o tipo de buraco que revisão por task não enxerga: cada peça estava
  correta, e a composição delas não fechava.
- **Testes que não distinguiam mensagem.** Os três caminhos de 404 do comprovante
  precisam ser indistinguíveis — mesma resposta para "não existe", "não é seu" e
  "arquivo sumiu". O código fazia certo, mas os testes verificavam só o *tipo* da
  exceção. A igualdade das mensagens estava garantida apenas por terem sido
  digitadas iguais.

### O que lembrar

- **Um nome imprevisível não é autorização.** É ofuscação com prazo indeterminado:
  não expira, não se revoga, e vaza por caminhos que você não controla.
- **Decisão de backend que muda o desenho do frontend vem antes dele.** O critério
  não é "bloqueia tecnicamente", é "muda como a tela é construída".
- **`**dict` no serializador cola dado interno com contrato.** Enquanto a resposta
  é a linha do banco espalhada, toda coluna nova vira campo público e todo campo
  removido vira quebra em consumidores internos. Um serializador explícito é o que
  separa as duas coisas.
- **Ao remover um campo, o trabalho é achar todos os leitores** — e a suíte não
  vai apontá-los, porque mocks desatualizados continuam afirmando o contrato
  antigo.
- **Indistinguibilidade precisa ser testada como igualdade, não como tipo.** Se
  três caminhos têm de responder a mesma coisa, três asserções independentes com
  o literal repetido provam isso; uma constante compartilhada faria os três
  concordarem por construção e não provaria nada.
- **A composição das peças é onde a revisão final ganha.** Cada task deste ciclo
  passou limpa; o buraco do `id` no login só apareceu quando alguém perguntou
  "como o cliente busca a própria foto?" — uma pergunta que nenhuma task isolada
  tinha motivo para fazer.

## Ciclo de feature — Contrato novo e comprovante autenticado (2026-07-29)

**Status:** implementação concluída em 2026-07-29. **Não validado em navegador**
e **não mesclado** — ver "Verificações e limitações".

**Repositórios e branches:** `Refund-FrontEnd`, branch
`feat/frontend-contract-and-receipt` (`6326606..39e0683`, 17 commits).
No `Refund-api` o ciclo não mudou código: a única ação foi o **fast-forward** de
`feat/authenticated-file-serving` para a `main` (`3fa42b2..ef7c60f`, 33
commits), feito no início para que existisse um contrato único durante todo o
desenvolvimento.

**Natureza:** sexto ciclo de feature e o primeiro de frontend desde o restyle.
Executado em 11 tasks com revisão por task, mais uma **revisão da branch
inteira** no fim. Spec e plano em
`Refund-FrontEnd/docs/superpowers/{specs,plans}/2026-07-29-frontend-contract-and-receipt*`.

**Item da trilha:** o ciclo não abre item novo. Ele **fecha uma lacuna do Item 2
(schemas como fronteira)**: aquele item foi restrito a responses HTTP e deixou
de fora a sessão persistida em `localStorage`, que até aqui era lida com type
assertion. O **Item 11 (error boundaries)** foi considerado e deixado de fora de
propósito — o `ReceiptPreview` trata o próprio erro localmente, e um boundary
sem uma segunda tela de dados para proteger seria abstração prematura.

### Por que estudar

Três ciclos de backend seguidos mudaram o contrato das respostas de reembolso. O
conteúdo de aprendizado deste ciclo não é "atualizar schemas": é **o que
acontece com o frontend quando o backend passa a servir bytes em vez de URLs**.
Um arquivo público é `<img src>` e acabou. Um arquivo autenticado vira
`fetch` → `Blob` → `createObjectURL` → **`revokeObjectURL`**, e essa última
etapa introduz no frontend algo que ele quase nunca tem: um **recurso com dono e
com ciclo de vida**, que precisa ser liberado exatamente uma vez.

Isso colide de frente com a peça que o Item 1 introduziu — um cache que
**descarta entradas quando quer** (`gcTime`) e as compartilha entre componentes.
Cache e recurso descartável, juntos, obrigam a decidir *o que* se cacheia.

### Estado anterior

O contrato que o frontend exigia, em
`Refund-FrontEnd/src/features/refunds/schemas/refund.ts`:

```ts
const refundBaseSchema = z.object({
  id, user_id, name, category, amount_in_cents, filename,
});
export const refundSchema = refundBaseSchema.extend({ created_at });

// A criação não devolve `created_at`, por isso possui um contrato próprio […]
export const refundCreateResponseSchema = z.object({
  type, count: z.literal(1), attributes: refundBaseSchema,
});
```

O comprovante era montado por `getReceiptUrl(filename)` em `src/lib/api.ts` e
consumido por um `<a href target="_blank">` na `PageRefundDetails`. A sessão
persistida era lida assim, em `src/context/AuthContext.tsx`:

```ts
return raw ? (JSON.parse(raw) as AuthUser) : null;
```

E `per_page` estava escrito em **dois** lugares — `src/router-loaders.ts`
(`const REFUNDS_PER_PAGE = 6`) e o default de `useRefunds` — que podiam divergir
em silêncio.

### A limitação encontrada

`user_id` e `filename` eram obrigatórios no Zod e **deixaram de existir** nas
respostas. O `.parse` falharia em **toda** listagem: `useRefunds` cairia em
`isError` e a Home mostraria "Não foi possível carregar as solicitações" para
todo usuário. O mesmo no detalhe e na criação. Não é degradação parcial — é a
tela principal do produto inutilizável.

E não existe ordem de deploy segura: backend novo com frontend velho quebra, e
frontend novo com backend velho quebra igual, porque o frontend novo passa a
exigir `user`. Os dois têm de ir juntos.

### Comparação visual

O contrato:

| Antes | Agora |
|---|---|
| `user_id: 13` no topo | `user: { id, name, has_avatar }` |
| `filename: "abc.jpg"` | não existe — o arquivo vem por rota própria |
| sem `status` | `pending` \| `approved` \| `rejected` |
| criação sem `created_at` | criação com `created_at` (a API relê a linha) |
| login sem `id` | login com `id` |

E o eixo do ciclo — quem guarda o quê:

```text
ERRADO   cache do Query  ->  "blob:…"  (a URL)
         gcTime descarta a entrada com a URL na tela  ->  imagem quebrada
         ou mantém a entrada viva sem revogar         ->  vazamento
         quem revoga? o cache não tem cleanup de componente

CERTO    cache do Query  ->  Blob      (os bytes)
         cada componente que monta: createObjectURL   (a SUA URL)
         cleanup do componente:      revokeObjectURL  (exatamente uma vez)
         bytes reaproveitados pelo cache; ciclo de vida colado ao componente
```

### Estado ajustado

#### O cache guarda os bytes; o componente guarda a URL

Três peças, com responsabilidades separadas de propósito:

```
receiptQuery(id)     features/refunds/api/refundQueries.ts  -> cacheia o Blob
useObjectUrl(blob)   src/hooks/useObjectUrl.ts   (shared)   -> cria/revoga a URL
ReceiptPreview       features/refunds/components/           -> decide a renderização
```

```ts
// src/hooks/useObjectUrl.ts
export function useObjectUrl(blob: Blob | undefined): string | null {
  const [url, setUrl] = useState<string | null>(null);

  useEffect(() => {
    if (!blob) {
      setUrl(null);   // sem isto, o hook devolveria uma URL já revogada
      return;
    }
    const objectUrl = URL.createObjectURL(blob);
    setUrl(objectUrl);
    return () => URL.revokeObjectURL(objectUrl);
  }, [blob]);

  return url;
}
```

A assinatura devolve `null` enquanto não há Blob, para o chamador não precisar
distinguir "carregando" de "sem arquivo" por um valor mágico.

O hook mora em `src/hooks/` (camada *shared*) e **não** dentro de
`features/refunds` por uma razão concreta: o ciclo da foto de perfil vai precisar
do mesmo comportamento, e o `eslint-plugin-boundaries` do Item 9 proíbe uma
feature de importar de outra. Nascendo na feature, o ciclo seguinte esbarraria no
lint. O hook é genérico — só converte `Blob` em URL; a parte autenticada é
responsabilidade da query.

A `receiptQuery` é a **única query do projeto sem Zod**, e isso ficou escrito no
código para não parecer esquecimento: as outras validam JSON; aqui a resposta é
binária e a fronteira já é o `Content-Type`, derivado pelo backend da extensão
armazenada. Não há estrutura a parsear.

O `ReceiptPreview` tira proveito disso: `blob.type` já carrega o `Content-Type`,
então `startsWith("image/")` decide entre `<img>` e `<object type="…pdf">` **sem
nenhum campo novo no contrato**. E ele cria **uma** URL, passando a mesma string
para o diálogo de tela cheia — dois donos de um recurso que precisa ser revogado
uma vez é exatamente como se produz uma imagem quebrada intermitente.

#### Quando o backend remove uma divergência, o frontend remove a compensação

`refundCreateResponseSchema` existia por um motivo documentado: a criação não
devolvia `created_at`. O backend passou a reler a linha gravada e essa razão
evaporou. O schema foi **deletado**, não mantido "por segurança":

```ts
// Um envelope só para detalhe E criação. Até este ciclo a criação tinha
// contrato próprio, porque a API não devolvia `created_at`; ela passou a reler
// a linha gravada e as três respostas ficaram idênticas.
export const refundResponseSchema = z.object({
  type: z.literal("Refund"),
  count: z.literal(1),
  attributes: refundSchema,
});
```

Manter os dois seria carregar para sempre a memória de um problema que não
existe mais — e, pior, dar a impressão de que criação e detalhe ainda divergem.

#### Uma fronteira de schema dispensa fallback lá na frente

O badge de status mapeia os três estados em
`features/refunds/constants/status.ts`, sem criar token de cor novo:

```ts
export const REFUND_STATUS: Record<RefundStatus, { label; variant }> = {
  pending:  { label: "Pendente",  variant: "secondary" },
  approved: { label: "Aprovado",  variant: "default" },
  rejected: { label: "Rejeitado", variant: "destructive" },
};
```

Na revisão veio a pergunta certa: e se a API devolver um quarto status?
`REFUND_STATUS[refund.status]` não tem fallback. A resposta é que **não pode
chegar lá**: `refundStatusSchema` é um `z.enum` e o `refundQueries.ts` usa
`.parse()`, que **joga**. Um status desconhecido termina a query em `isError` e
nunca alcança o render. O fallback defensivo seria código morto — e, pior,
esconderia a quebra de contrato em vez de expô-la.

#### Sessão persistida validada — a metade que faltava do Item 2

```ts
// src/schemas/auth.ts
export const storedUserSchema = z.object({ id, name, email, role });

// src/context/AuthContext.tsx — safeParse, não parse: sessão inválida derruba
// a sessão, não a aplicação no primeiro render.
const result = storedUserSchema.safeParse(JSON.parse(raw));
return result.success ? result.data : null;
```

> **Efeito observável no deploy: todo usuário logado é deslogado uma vez.** As
> sessões salvas hoje não têm `id` e falham no parse. Não é bug — é a
> consequência correta de exigir um campo novo, e é preferível ao comportamento
> anterior, em que um objeto de forma errada passava direto e só quebrava mais
> tarde, longe da causa.

### Arquivos modificados

**`Refund-FrontEnd`** (17 commits, `6326606..39e0683`):

- **Contrato:** `src/features/refunds/schemas/refund.ts` (`user` aninhado,
  `status`, `refundCreateResponseSchema` e `refundBaseSchema` removidos,
  `refundDetailResponseSchema` → `refundResponseSchema`), `src/schemas/auth.ts`
  (`id` no login + `storedUserSchema`), `src/context/auth-context.ts`
  (`AuthUser.id`), `src/features/refunds/hooks/useCreateRefund.ts`.
- **Sessão:** `src/context/AuthContext.tsx` (validação + `queryClient.clear()`
  no logout) e `src/router-loaders.ts` (`requireSession` validando o mesmo
  schema e limpando o `localStorage` ao falhar).
- **Comprovante:** `src/hooks/useObjectUrl.ts` (novo),
  `src/features/refunds/api/refundQueries.ts` (`refundKeys.receipt` +
  `receiptQuery`), `src/features/refunds/hooks/useReceipt.ts` (novo),
  `src/features/refunds/components/ReceiptPreview.tsx` (novo),
  `src/pages/PageRefundDetails.tsx`; `getReceiptUrl` **removido** de
  `src/lib/api.ts`.
- **Badge:** `src/features/refunds/constants/status.ts` (novo),
  `src/pages/PageHome.tsx` e `src/pages/PageRefundDetails.tsx`.
- **Ajustes pequenos:** `src/features/refunds/constants/pagination.ts` (novo,
  `REFUNDS_PER_PAGE = 10`, exportado pela fachada `index.ts`),
  `src/features/refunds/hooks/useRefunds.ts`, `src/router-loaders.ts`;
  `src/components/core/Topbar.tsx` (import `Separator` não usado, removido — ver
  verificações).
- **Testes:** novos `src/context/AuthContext.test.tsx`,
  `src/hooks/useObjectUrl.test.ts`,
  `src/features/refunds/api/receiptQuery.test.tsx`,
  `src/features/refunds/components/ReceiptPreview.test.tsx`,
  `src/features/refunds/constants/status.test.ts`, `src/router-loaders.test.ts`;
  atualizados `src/test/msw/handlers.ts` (contrato novo + handler binário do
  comprovante), `src/test/setup.ts`, `src/pages/PageHome.test.tsx`,
  `src/pages/PageRefundDetails.test.tsx` e os testes do shell.

**`Refund-api`:** nenhuma mudança de código. Este diário e o
[`current-state.md`](plans/current-state.md).

### Verificações e limitações

Na ponta da branch (`39e0683`):

| Comando | Resultado |
|---|---|
| `npm run test` | **103 testes em 31 arquivos**, verdes — a suíte foi rodada **três vezes** |
| `npx tsc -b --noEmit` | exit 0 |
| `npm run lint` | **0 erros, 0 warnings** |
| `npm run build` | ok — bundle principal **503,57 kB → 506,00 kB** (+2,43 kB) |
| `pytest` (`Refund-api`, pós fast-forward) | **178 testes**, verdes |
| `pylint src` (`Refund-api`) | **10.00/10** |

Duas correções ao que o `current-state.md` afirmava sobre o restyle, ambas
descobertas aqui:

- **`npm run build` estava quebrado na `main`.** O commit manual `2d07a8d`
  deixou um import de `Separator` não usado em `src/components/core/Topbar.tsx`,
  o que fazia `tsc -b --noEmit` sair 2, o `eslint .` reportar 1 erro e o
  `npm run build` falhar. Não era regressão deste ciclo — era estado da `main`,
  e teria tornado o portão de verificação de **toda** task deste ciclo sem
  sentido. Corrigido no commit `4e53be4`.
- **O aviso de chunk > 500 kB já existia no ponto de partida.** O bundle estava
  em 503,57 kB antes de qualquer commit deste ciclo. A afirmação de que o
  restyle terminou "sem o aviso" era verdadeira quando escrita (491,44 kB) e
  ficou obsoleta.

**Limitações registradas — o que este ciclo NÃO validou:**

- ~~**Nada foi aberto no navegador.**~~ **Fechado em 2026-07-29**, ainda no mesmo
  dia: o Gabriel percorreu o checklist contra a API real — o logout forçado das
  sessões antigas no primeiro carregamento, o preview do comprovante em imagem
  **e** em PDF (incluindo tela cheia), o badge nos três valores, e o 404 do
  comprovante de outro usuário. Tudo passou, sem ressalvas.
- **Consequência direta: a pendência "Aberto 1/4" foi baixada.** O runtime do
  Item 2 contra a API real dependia dessa passada, e ela aconteceu. Vale guardar
  o motivo de nenhum teste ter fechado esse item antes: a suíte roda contra o
  MSW, que devolve o payload que **nós** escrevemos. Um mock não pode provar que
  o servidor real concorda com o schema — só o servidor real pode.
- **O deploy conjunto continua obrigatório.** A branch do frontend foi mesclada
  na `main` depois da validação; o que resta é implantar os dois juntos.
- **`ResizeObserver` em `Sidebar.test.tsx` (não confirmado).** Durante a onda de
  correções foi relatado um `ResizeObserver is not defined` dependente da ordem
  de execução, supostamente reproduzível também no baseline intocado. A suíte
  completa rodou 3× na ponta e **não** reproduziu. Fica registrado como suspeita,
  não como resolvido nem como refutado.
- **O stub de object URL em `src/test/setup.ts` é um no-op neste ambiente.**
  Verificado: o `window.URL` do jsdom 29.1.1 realmente não tem os dois métodos,
  mas o `URL` **global** sob o Vitest é o do Node, que os implementa (daí
  `blob:nodedata:<uuid>` na saída, e não o `blob:mock/N` do stub). A guarda
  `if (!URL.createObjectURL)` nunca dispara. É inofensivo e continua sendo rede
  de segurança para ambientes sem os métodos — o comentário foi corrigido para
  dizer isso.
- **`per_page: 10` em `src/test/msw/handlers.ts` é literal escrito à mão**, não
  derivado de `REFUNDS_PER_PAGE`; pode divergir em silêncio num ajuste futuro. O
  mesmo vale para o `perPage: 6` do loader stub em `PageHome.a11y.test.tsx`
  (inerte — nada o assere — mas obsoleto).
- **O `.venv` do `Refund-api` tem shebangs de um caminho antigo**
  (`.../React/Refund-api`): `pytest` e `pylint` só rodam via
  `.venv/bin/python3 -m …`. É problema de ambiente, não de código; vale recriar
  o venv.
- **Sobrou um usuário de teste no banco**, `task1-verify@example.com` (id 15),
  criado na verificação do fast-forward. Junta-se aos outros usuários
  descartáveis já registrados.

### O que a revisão pegou

Onze tasks passaram por revisão individual; duas precisaram de rodada de
correção. Mas os dois achados mais graves vieram da **revisão da branch
inteira**, e os dois são da mesma natureza: **fronteira de sessão**.

1. **Dois leitores do mesmo dado persistido tinham divergido.** A Task 3
   apertou o `AuthContext` para validar a sessão com `storedUserSchema`, e o
   `router-loaders.ts` continuou com uma checagem de presença crua
   (`if (!token || !user)`). Uma sessão antiga, sem `id`, **passava** pelo
   loader, disparava uma requisição autenticada para dentro do cache
   compartilhado sem ninguém logado, e deixava token e usuário no
   `localStorage` para sempre. A origem foi o **plano**: a lista de arquivos da
   Task 3 não incluía o `router-loaders.ts`. Nenhuma revisão por task podia ver
   isso — cada uma olhava um arquivo por vez.
2. **`logout()` não limpava o cache do React Query.** Antes deste ciclo isso já
   era discutível; agora o cache guarda **os bytes de arquivos**. Cenário: A sai,
   B entra na mesma aba, e dentro dos 30s de `staleTime` o `useReceipt` entrega
   a B o Blob do comprovante de A. Agravado pela guarda `isError && !blob` (que
   está correta em si) mantendo o comprovante de A na tela depois do refetch de
   B dar 403. Conserto: `queryClient.clear()` no logout.

E três correções menores que valem como método:

- **Um teste que não pode falhar não é cobertura — e a prova é quebrar o
  código.** A metade do `PageHome.test.tsx` que dizia "reseta a página para 1"
  nunca podia falhar, porque a fixture começava na página 1. Corrigido iniciando
  o router em `?page=2` e **provado** quebrando o ramo de propósito para ver o
  teste ficar vermelho. A mesma técnica pegou algo pior no `useObjectUrl`:
  apagar o `setUrl(null)` deixava **os quatro** testes do hook verdes, com o
  hook devolvendo uma URL permanentemente revogada. Faltava o caso
  `Blob → undefined`.
- **`max-w-3xl` no `DialogContent` não fazia o que parecia.** A base do
  componente traz `max-w-[calc(100%-2rem)] sm:max-w-lg`; o tailwind-merge não
  trata um `max-w-3xl` sem modificador como conflitante com `sm:max-w-lg` (o
  limite de 32rem continuava vencendo acima de 640px), mas **descarta** o
  `max-w-[calc(100%-2rem)]`, colando o painel nas bordas no mobile. Ou seja: não
  alargava e ainda quebrava a margem. O certo é `sm:max-w-3xl`.
- **O badge quase espremeu o nome da linha para fora da tela.** O lado direito
  da linha da Home passou de ~90px (só o valor) para ~170px (badge + gap +
  valor), e o `Badge` carrega `shrink-0` + `whitespace-nowrap` — ele nunca cede.
  Sem `min-w-0` em **cada** nível da cadeia flex até os spans com `truncate`, o
  overflow aparece nos 390px de referência do `AGENTS.md`.

Duas afirmações do **plano** foram registradas como erradas, sem mudança de
código:

- O plano dizia que o `eslint-plugin-boundaries` pegaria um import ao interior
  de uma feature vindo do `src/router-loaders.ts`. **Não pegaria** — aquele é um
  dos 4 arquivos soltos em `src/` classificados como `unknown` e deixados sem
  restrição, lacuna que o `current-state.md` já registra. O import escrito está
  correto de qualquer forma; só a rede de segurança alegada não existia.
- O plano justificava pôr o handler do comprovante antes de `*/refunds/:id`
  dizendo que este engoliria `/refunds/1/receipt`. Instanciado e testado com
  `.parse()`: **não engole** — o segmento `:id` do path-to-regexp nunca atravessa
  uma `/`. A ordem é higiene inofensiva; o perigo alegado não existe.

### O que lembrar

- **O cache guarda os bytes; o componente guarda a URL.** Uma object URL precisa
  ser revogada exatamente uma vez. Cachear a URL põe o ciclo de vida de um
  recurso descartável nas mãos de um garbage collector que não tem cleanup de
  componente: ou ele descarta cedo (imagem quebrada) ou nunca revoga
  (vazamento). Cachear os **bytes** deixa cada componente dono da sua própria
  URL — e os bytes seguem reaproveitados.
- **Uma URL, um dono.** Se dois lugares criam a URL do mesmo Blob, dois lugares
  vão revogá-la. O `ReceiptPreview` cria uma e passa a mesma string ao diálogo.
- **Quando o backend remove uma divergência, o frontend remove a compensação.**
  Um schema que existe só para descrever uma diferença que acabou não é
  "segurança" — é uma mentira mantida por inércia. Apague-o.
- **Uma fronteira de schema dispensa fallback defensivo lá na frente.** Com
  `z.enum` e `.parse()` que joga, um valor desconhecido termina em `isError` e
  nunca chega ao render. Adicionar fallback depois da fronteira é código morto
  que ainda por cima esconderia a quebra de contrato.
- **Um teste que não pode falhar não é cobertura, e a única prova é quebrar o
  código de propósito.** Se a suíte continua verde com o ramo mutilado, o teste
  estava descrevendo, não verificando. Vale para asserção vazia e para o caso de
  transição que ninguém escreveu.
- **Dois leitores do mesmo dado persistido divergem em silêncio.** Apertar a
  validação de um lado (`AuthContext`) sem o outro (`router-loaders.ts`) produz
  uma porta que continua aberta. Ao endurecer a leitura de algo persistido, a
  pergunta é "quem mais lê isto?", e a resposta não está no arquivo que você
  abriu.
- **Sair não é só limpar o `localStorage`.** O cache de server state é estado de
  sessão — e a partir deste ciclo ele guarda **arquivos**. Um logout que não o
  limpa entrega dados do usuário anterior ao próximo que entrar na mesma aba.
- **`revoke` é a metade do trabalho que ninguém lembra de testar.** O teste
  natural prova que a URL é criada; o que quebra na prática é ela sobreviver ao
  Blob, ou morrer antes dele.
- **Um utilitário que o próximo ciclo vai reusar nasce na camada compartilhada.**
  Não por elegância: o `eslint-plugin-boundaries` do Item 9 proíbe uma feature
  importar de outra, então nascer no lugar errado significa mover depois.
- **Uma classe utilitária sem modificador não "vence" uma com modificador.** No
  tailwind-merge, `max-w-3xl` não substitui `sm:max-w-lg`, mas **derruba** o
  `max-w-[calc(100%-2rem)]` da base. Ao sobrescrever classe de um componente do
  registry, confira o que a base declara — inclusive as responsivas.
- **A verificação de uma branch começa medindo o ponto de partida.** Um `tsc` e
  um `eslint` já vermelhos na `main` tornariam sem sentido o portão de qualidade
  de todas as tasks seguintes. Descobrir isso na task 3 é barato; descobrir no
  fim, não.

## Ciclo de feature — Pagamento, histórico de revisões e estatísticas (2026-07-30)

Sétimo ciclo de feature e o segundo inteiramente de backend, na branch
`feat/refund-payment-and-stats` do `Refund-api` (`23c6675..1381241`, 28
commits, 12 tasks). Artefatos em `.superpowers/sdd/2026-07-30-refund-payment-
and-stats/`. Fecha o `UC-012` (pagar reembolso), `UC-013` (histórico de
revisões) e `UC-014` (estatísticas por usuário), e acrescenta um quarto status
(`paid`) ao ciclo de vida do `refunds.status`.

### Por que agora

Depois do workflow de aprovação (ciclo anterior), a máquina de estados parava
em `approved`/`rejected` — sem nenhum jeito de marcar que o dinheiro
efetivamente saiu. Sem `paid`, o card "Total" do frontend não tinha como
distinguir um passivo aprovado de uma despesa já realizada, e não existia
nenhum registro de **quem** pagou nem **quando**. As três rotas novas
(`POST /payment`, `GET /payment-receipt`, `GET /reviews`, `GET
/refund-stats`) e o quarto status vieram juntos porque um não faz sentido
sozinho: pagar sem comprovante não é auditável, e estatísticas sem `paid`
contam a metade da história.

### Achado 1 — o `lock_timeout` que nunca chegava ao Postgres

**Estado anterior.** O pool de conexões (herdado, sem mudança neste ciclo até
agora) tinha `pool_size=2, max_overflow=0, pool_timeout=30`: um teto de duas
operações concorrentes para o processo inteiro. Como `select_for_update` na
revisão segura uma conexão enquanto espera o lock da linha, duas revisões
concorrentes já bastavam para esgotar o pool — e uma terceira requisição
qualquer, até um login, esperava 30s e recebia `500`.

**A correção planejada** era direta: aumentar o pool (`pool_size=5,
max_overflow=10`) e adicionar um `lock_timeout` curto, para que uma espera
por lock falhe rápido e com erro legível em vez de travar a conexão
indefinidamente. O plano especificava a forma que a documentação do asyncpg
recomenda:

```python
connect_args={"server_settings": {"lock_timeout": "3000"}}
```

**A limitação encontrada.** Aplicado exatamente assim, `SHOW lock_timeout`
respondia `0` — sem nenhum erro de conexão, sem exceção, nada. O valor
simplesmente não pegava. A investigação isolou a causa camada por camada:

1. Reproduzido com `asyncpg` puro, sem SQLAlchemy no caminho — mesmo `0`.
   Descartava um bug de tradução do `connect_args`.
2. `SET lock_timeout = '3000'` como comando comum, depois de conectado,
   funcionava (`SHOW` respondia `3s`). O GUC em si estava saudável; o
   problema era só no **pacote de inicialização** da conexão.
3. Sondado quais parâmetros de startup realmente chegam: `application_name`
   sobrevivia, `lock_timeout` e `statement_timeout` — enviados juntos, do
   mesmo jeito — não.
4. `options="-c lock_timeout=3000"` (o parâmetro que proxies costumam usar
   para repassar GUCs arbitrários como uma string opaca) sobreviveu e
   produziu `SHOW lock_timeout = 3s`.

**Causa raiz:** o endpoint do Neon usado (`DATABASE_URL` sem `-pooler`) ainda
passa por um proxy de autenticação/roteamento mesmo fora do modo pooler, e
esse proxy só repassa os parâmetros de startup que o próprio Postgres
"reporta" de volta ao cliente (como `application_name`); os demais —
inclusive `lock_timeout` e `statement_timeout` — são descartados **em
silêncio**, sem erro em lugar nenhum. `SHOW <parâmetro> = 0` com um
`server_settings` corretamente formado é o sintoma; a causa é esse filtro do
proxy, não o código.

```python
# ANTES (nunca aplicado — barrado pela verificação Passo 5 do plano):
connect_args={"server_settings": {"lock_timeout": "3000"}}   # SHOW lock_timeout -> 0

# DEPOIS — o valor sobrevive porque `options` é repassado como string opaca:
connect_args={"server_settings": {"options": "-c lock_timeout=3000"}}   # SHOW lock_timeout -> 3s
```

A decisão de produto (um `lock_timeout` global de 3s) não mudou — só o
transporte. O plano tinha um passo de verificação explícito (`SHOW
lock_timeout` deveria responder `3s`) e a instrução de **não** commitar se
isso não acontecesse; foi exatamente esse portão que impediu a correção
silenciosa de passar. Verificado de novo nesta Task 12, contra o servidor
real e sem mocks: os testes automatizados (`database_connection_handler_pool_
test.py`) só provam que os *parâmetros do engine* são os esperados — não que
o Postgres os aceitou. Só uma consulta `SHOW` contra a conexão real prova
isso, e é exatamente o tipo de verificação que uma suíte verde não cobre.

### Achado 2 — `paid` não era terminal, e o comentário que explicava por quê estava certo até deixar de estar

**Estado anterior.** A regra de transição de status (`BR-017`) vivia num único
comparador no controller:

```python
# RefundReviewerController.review(), antes deste ciclo
if current_status == status:
    raise HttpUnprocessableEntityError(f"Refund is already {status}")
```

E um comentário no validador, escrito **no ciclo anterior**, quando só
existiam três status (`pending`, `approved`, `rejected`), afirmava que essa
única comparação bastava para cobrir a regra inteira — com um aviso explícito
para revisitar o controller **se o conjunto de alvos permitidos fosse
ampliado** (`ALLOWED_REVIEW_STATUSES`).

**A limitação encontrada.** Este ciclo não ampliou o conjunto de *alvos* — ele
ampliou o conjunto de **status de origem alcançáveis**, adicionando `paid`
como um quarto status possível para `refunds.status`. O aviso do comentário
apontava para o eixo errado. Como `paid` nunca é um alvo válido de revisão
(`ALLOWED_REVIEW_STATUSES = {"approved", "rejected"}`), a condição
`current_status == status` nunca é `True` quando `current_status == "paid"` —
e por isso a única guarda existente deixava passar `PATCH
/refunds/{id}/status` num reembolso já pago, revertendo-o silenciosamente
para `approved` ou `rejected` com `200`, sem nenhum erro.

Reproduzido isoladamente antes do conserto (`repro_bug.py`, Task 11.5):

```
BUG REPRODUCED: paid -> approved succeeded with response:
{'type': 'Refund', 'count': 1, 'attributes': {'id': 1, ..., 'status': 'approved', ...}}
insert_review called with: call(..., from_status='paid', to_status='approved', ...)
```

Um `refund_review` era até gravado com `from_status="paid"` — a auditoria
registrava fielmente uma reversão de dinheiro já pago, sem nada que a
impedisse de acontecer primeiro.

**Comparação:**

| | Antes | Depois |
|---|---|---|
| Guarda de terminalidade | nenhuma — dependia de `current_status == status` nunca coincidir com `paid` por construção do conjunto de alvos | guarda explícita, `if current_status == "paid": raise ...`, antes da checagem de repetição |
| `PATCH .../status` num reembolso pago | `200`, reverte o status | `422 "Refund is already paid and cannot be reviewed"` |
| Onde a regra de terminalidade vivia | implícita — dependia dos dois conjuntos (`ALLOWED_REVIEW_STATUSES` e os status de origem alcançáveis) nunca se cruzarem | explícita — uma condição dedicada, que não depende de nenhum outro conjunto |
| Comentário do validador | avisava sobre ampliar o conjunto de **alvos** | avisa sobre ampliar **qualquer um dos dois eixos** — alvos ou origens |

**Estado ajustado:**

```python
# src/controllers/refund_reviewer_controller.py, depois do conserto (commit 5f78777)
if current_status == "paid":
    raise HttpUnprocessableEntityError("Refund is already paid and cannot be reviewed")

if current_status == status:
    raise HttpUnprocessableEntityError(f"Refund is already {status}")
```

O achado só apareceu porque a verificação ponta a ponta desta mesma Task 12
incluiu um cenário que a tabela original do plano não previa (`PATCH` numa
solicitação paga) — a suíte de testes unitários, toda mockada, nunca
exercitou a combinação real "quatro status possíveis, dois deles nunca alvo
de revisão". Uma correção retroativa (**Task 11.5**) fechou a lacuna antes
desta verificação começar; os cenários 12 e 26 desta task confirmam o
conserto contra a API real.

### Verificações

| Comando | Resultado |
|---|---|
| `pytest` | **226 testes**, todos verdes (partiu de 178) |
| `pylint src` | **10.00/10** |
| Ponta a ponta contra a API real | **26/26 cenários**, status HTTP e corpo conferidos um a um, sem nenhum ajustado para caber no resultado |
| `ls uploads/payment_receipts/` antes/depois | vazio (só `.gitkeep`) → 1 arquivo após 1 pagamento bem-sucedido; nenhum arquivo órfão dos 5 cenários de guarda/duplicata |
| Anti-enumeração — `403` de standard, id real vs. inventado | corpos **byte-idênticos** (`diff`) |
| Anti-enumeração — os quatro caminhos `404` do comprovante de pagamento (id inexistente, não é seu, nunca pago, arquivo sumiu do disco) | os **quatro** corpos **byte-idênticos** (`diff` par a par) — verificação mais ampla do que a tabela do plano exigia |
| Contenção do pool — 3 `PATCH` concorrentes na mesma solicitação | nenhum `500`, nenhuma espera de 30s; um `200` e dois `422 "already rejected"`, os três completos em **~1,5s** no total |

Detalhes completos, incluindo a tabela dos 26 cenários e os ids de teste
criados, em `.superpowers/sdd/2026-07-30-refund-payment-and-stats/task-12-
report.md`.

### O que lembrar

- **Um comentário que diz "esta condição cobre a regra inteira" descreve uma
  invariante entre dois conjuntos — e invariantes têm dois lados.** O aviso
  escrito no ciclo anterior sobre `ALLOWED_REVIEW_STATUSES` só cobria o eixo
  que aquele ciclo conseguia imaginar mudar (o conjunto de alvos). O eixo que
  de fato mudou foi o outro (o conjunto de origens alcançáveis). Um aviso
  sobre "não amplie X" vale a pena reler perguntando "e se eu ampliar o outro
  lado da comparação?".
- **`SHOW <parâmetro>` contra a conexão real é a única prova de que um
  `connect_args` funcionou.** Um teste unitário que verifica os argumentos
  passados ao `create_async_engine` prova a intenção, não o efeito — e a
  intenção aqui era exatamente correta segundo a documentação do driver.
  Só faltou ao Postgres real recebê-la.
- **"Sem erro" não é sinônimo de "funcionou".** O proxy do Neon não recusou
  a conexão, não logou nada, não alertou. Um parâmetro de startup
  simplesmente evaporou. Ausência de exceção é a evidência mais fraca que
  existe de que algo deu certo.
- **Um portão de verificação com critério de parada explícito (`SHOW
  lock_timeout` deve responder `3s`, senão não commite) é o que separa "a
  correção parece certa" de "a correção está certa".** Sem esse portão, o
  `server_settings={"lock_timeout": ...}` — plausível, documentado,
  revisado — teria sido commitado quieto, e o comportamento antigo (conexão
  presa indefinidamente numa espera de lock) continuaria existindo atrás de
  uma configuração que parecia consertá-lo.
- **Um teste que não pode falhar contra mock nenhum é o mesmo problema de um
  teste que não pode falhar contra código nenhum.** As duas descobertas mais
  sérias deste ciclo — o `lock_timeout` e o `paid` não-terminal — eram
  ambas invisíveis a uma suíte 100% verde, porque nenhuma delas é
  expressável como uma asserção sobre um mock: uma precisa do Postgres real
  atrás de um proxy real; a outra precisa da combinação de quatro status
  reais que nenhum teste unitário isolado compõe sozinho.

## Ciclo de feature — Workflow de aprovação na UI (2026-07-30)

Oitavo ciclo de feature, o segundo consecutivo inteiramente de frontend, na
branch `feat/refund-review-ui` do `Refund-FrontEnd` (`39e0683..485cecb`, 15
commits, 9 tasks com revisão por task). Artefatos em
`Refund-FrontEnd/.superpowers/sdd/2026-07-30-refund-review-ui/`
([spec](../../Refund-FrontEnd/docs/superpowers/specs/2026-07-30-refund-review-ui-design.md)).
Consome o ciclo de backend anterior (pagamento, histórico e estatísticas) e
constrói a tela de revisão, aprovar/rejeitar, marcar como pago, o histórico de
revisões e o painel do solicitante.

### Por que agora

Isto não era só "a próxima tela do roadmap". Havia uma incompatibilidade ativa
entre o que a `main` do `Refund-api` já produz e o que a `main` do
`Refund-FrontEnd` sabia ler: o backend do ciclo anterior devolve um quarto
status, `"paid"`, e o schema do frontend só conhecia três. A Task 1 deste
ciclo existiu para consertar isso antes de qualquer tela nova ser construída
em cima — e o jeito como ela foi consertada é a primeira lição que vale
preservar.

### Lição 1 — um enum de três valores virou uma queda total da tela principal quando o servidor ganhou o quarto

**O estado que quebrava.** `src/features/refunds/schemas/refund.ts` declarava:

```ts
export const refundStatusSchema = z.enum(["pending", "approved", "rejected"]);
```

O `.parse()` desse schema roda na fronteira de toda resposta de reembolso —
listagem, detalhe, criação. Assim que a API (que já ganhou `paid` no ciclo de
backend anterior) devolvesse **um único** reembolso pago, o Zod levantava, o
`useRefunds` caía em `isError`, e a Home mostrava "Não foi possível carregar
as solicitações" — não para quem tentasse ver aquele reembolso específico,
para **todo usuário**, porque a lista inteira falha se um item dela não
valida. Reproduzido antes do conserto, isolando só o schema:

```
$ npx vitest run src/features/refunds/schemas/refund.test.ts
 ❯ refundSchema > accepts a refund whose status is paid
ZodError: [
  {
    "code": "invalid_value",
    "values": ["pending", "approved", "rejected"],
    "path": ["status"],
    "message": "Invalid option: expected one of \"pending\"|\"approved\"|\"rejected\""
  }
]
```

**A causa raiz não é "esquecer de atualizar um enum".** É que um `z.enum` na
fronteira do cliente e o `status` que o banco aceita são **dois contratos
distintos, mantidos em dois repositórios**, e nada os mantém sincronizados
automaticamente — o tipo do TypeScript é tão fechado quanto a lista de
strings que alguém escreveu à mão, e essa lista só muda quando alguém a
lembra de mudar. Um enum de três valores no cliente não é "menos flexível que
o quarto valor do servidor" por acidente; ele é **exatamente** tão flexível
quanto o último ciclo que o tocou.

**O conserto:**

```ts
export const refundStatusSchema = z.enum(["pending", "approved", "rejected", "paid"]);
```

Uma linha. O que evita a **próxima** versão do mesmo incidente — um quinto
status, ou um rótulo esquecido para o quarto — não é essa linha; é o mapa de
rótulos ao lado dela:

```ts
export const REFUND_STATUS: Record<
  RefundStatus,
  { label: string; variant: "default" | "secondary" | "destructive" | "outline" }
> = {
  pending: { label: "Pendente", variant: "secondary" },
  approved: { label: "Aprovado", variant: "default" },
  rejected: { label: "Rejeitado", variant: "destructive" },
  // paid: ainda não existia aqui — e o TypeScript recusou compilar até existir.
};
```

`Record<RefundStatus, …>` é um tipo mapeado: para cada valor possível do tipo
`RefundStatus` (derivado do `z.enum` acima via `z.output`), o TypeScript
**exige** uma entrada correspondente no objeto. Alargar o `z.enum` sem
acrescentar `paid` ao `REFUND_STATUS` não é um estado que compila e falha em
runtime — é um estado que **não compila**:

```
$ npx tsc -b --noEmit
src/features/refunds/constants/status.ts(5,14): error TS2741: Property 'paid' is
missing in type '{ pending: {...}; approved: {...}; rejected: {...}; }' but
required in type 'Record<"pending" | "approved" | "rejected" | "paid",
{ label: string; variant: "default" | "destructive" | "secondary"; }>'.
```

Esse erro apareceu de propósito, antes do conserto — a Task 1 alargou o enum
primeiro e só então rodou `tsc` para **ver** essa mensagem, em vez de
adicionar as duas mudanças juntas e confiar que o par estava certo. Depois de
acrescentar `paid: { label: "Pago", variant: "outline" }`, o mesmo comando
voltou limpo:

```
$ npx tsc -b --noEmit
EXIT: 0
```

**Por que isso importa mais do que parece.** O `z.enum` e o `Record` resolvem
dois problemas diferentes que parecem o mesmo problema. O `z.enum` protege a
**fronteira** — nenhum valor desconhecido entra no cache ou no render. Mas
sozinho ele não protege o que já passou da fronteira: nada impede alguém de
escrever um `switch` ou uma cadeia de `if` que trata só os status que existiam
quando foi escrita, silenciosamente ignorando um quarto. É o `Record<RefundStatus,
…>` — não o `z.enum` — que fecha esse segundo buraco, porque ele amarra a
**lista de rótulos** ao mesmo tipo que a fronteira produz: qualquer
divergência entre os dois vira um erro de compilação, não um badge faltando
em produção. A revisão da Task 1 confirmou por busca que os dois únicos
lugares que ramificam por status (`PageHome.tsx` e `PageRefundDetails.tsx`)
passam pelo `REFUND_STATUS`, não por um `switch` próprio — então essa rede
cobre tudo o que existe hoje. Ela **não** cobre automaticamente um quinto
status futuro fora desse par (`z.enum` + `Record`); esse é o achado adiado da
Task 1, registrado no ledger.

### Lição 2 — as revisões pararam de achar bugs e passaram a achar testes que não podiam falhar

Ao longo das nove tasks deste ciclo, o código de produção passou por revisão
quase sempre limpo. O que as revisões encontraram, de novo e de novo, não foi
comportamento errado — foi **cobertura ausente exatamente na linha mais
cara de errar**. Dois exemplos concretos valem registrar, porque são o mesmo
padrão em duas formas diferentes.

**Exemplo A — a invalidação de cache sem teste nenhum, na linha cujo
comentário documenta que esse bug já vazou uma vez neste código.**
`useReviewRefund.ts`, o hook por trás de Aprovar/Rejeitar, tem este
comentário sobre a própria chamada de invalidação:

```ts
// Mesmo raciocínio do useDeleteRefund, mas mirando refundKeys.all (não só
// .lists()): a tela de revisão parte do detalhe do PRÓPRIO reembolso
// revisado, então tanto a lista da Home quanto o detalhe (se houver alguém
// olhando) precisam refletir o novo status — ao contrário da exclusão, o
// item revisado continua existindo, só muda de estado. A Home fica
// INATIVA enquanto se revisa, e o refetchType padrão ("active") deixaria
// sua lista velha por até o staleTime; "all" força o refetch mesmo assim.
onSuccess: () => {
  queryClient.invalidateQueries({ queryKey: refundKeys.all, refetchType: "all" });
},
```

"Mesmo raciocínio do `useDeleteRefund`" aponta direto para um bug real deste
diário — a correção de runtime de 2026-07-25, quando `invalidateQueries` sem
`refetchType: "all"` deixava a lista **inativa** (a Home, fora de tela durante
a revisão) sem refazer o `GET`, escondendo a mudança por até o `staleTime`. O
código novo já nasceu citando essa história — mas nasceu **sem teste algum**
que provasse que a citação estava certa. A Task 5 foi para correção com esse
achado como "importante": nada impedia alguém de trocar `refundKeys.all` por
`refundKeys.detail(id)` (um refactor que parece uma limpeza razoável) e
reintroduzir exatamente o bug que o comentário descreve, em silêncio. O
conserto foi um teste de regressão contra um `QueryClient` real, com uma
lista e um detalhe **inativos** propositalmente semeados, provando que os
dois voltam a ser refetchados — o mesmo molde que `useDeleteRefund.test.tsx`
já usava.

**Exemplo B — quatro testes verdes enquanto o componente buscava o endpoint
errado, porque duas fixtures do MSW eram byte-idênticas.** `ReceiptPreview`
recebe um prop `kind` (`"expense"` | `"payment"`) que decide **qual** rota
chamar e **qual** rótulo mostrar. Os handlers de mock para as duas rotas
serviam o mesmo PNG:

```ts
http.get("*/refunds/:id/receipt", () => new HttpResponse(receiptPngBytes, {
  headers: { "Content-Type": "image/png" },
})),
http.get("*/refunds/:id/payment-receipt", () => new HttpResponse(receiptPngBytes, {
  headers: { "Content-Type": "image/png" },
})), // mesmo PNG do handler acima
```

Um `useReceipt` que ignorasse `kind` silenciosamente e sempre chamasse
`/receipt` continuava passando os quatro testes que exercitavam
`kind="payment"` — porque o nome acessível vinha do **prop**, não da resposta
de rede, e a imagem renderizada era indistinguível de qualquer forma. O teste
provava que a etiqueta estava certa; não provava que a busca estava certa.

**O conserto não acrescentou nenhum teste novo.** Deu às duas fixtures **tipos
de mídia diferentes** — a de pagamento virou um PDF (`%PDF`, `application/pdf`)
em vez de outro PNG:

```ts
// O %PDF. Deliberadamente um FORMATO diferente da fixture de despesa acima,
// não só bytes diferentes do mesmo tipo: ReceiptPreview ramifica seu markup
// por blob.type (<img> vs. <object> + fallback <a>), então um teste consegue
// distinguir "o endpoint de pagamento foi realmente chamado" de "o endpoint
// de despesa foi chamado e o resultado só foi rotulado como pagamento" — a
// segunda opção ainda produziria um PNG idêntico se o useReceipt ignorasse
// `kind` em silêncio, mas não consegue produzir um DOM em formato de PDF.
const paymentReceiptPdfBytes = new Uint8Array([37, 80, 68, 70]);
```

Como `ReceiptPreview` renderiza `<img>` para imagem e `<object>` + link de
fallback para PDF, os **testes já escritos** — que checavam o rótulo — agora
só passam se o componente realmente tiver renderizado o ramo de PDF, o que só
acontece se a rota certa tiver sido chamada. Nenhuma asserção nova; a
distinção nasceu inteira da fixture.

### O que lembrar

- **Um enum fechado na fronteira do cliente vale exatamente o que o último
  ciclo que o tocou lembrou de incluir.** Ele não "sincroniza" com o servidor;
  ele descreve uma crença sobre o servidor, escrita numa data específica. Um
  quarto valor do lado de lá não é uma mudança rara — é o próximo passo
  esperado de qualquer máquina de estados viva.
- **`z.enum` protege a entrada; `Record<T, …>` protege o que vem depois dela.**
  São duas redes diferentes contra a mesma classe de erro. A primeira barra um
  valor desconhecido na fronteira; a segunda barra esquecer de tratar um valor
  conhecido mais adiante. Nenhuma substitui a outra, e a segunda só existe se
  **todo** ramo por status passar por um `Record`, nunca por um `switch` ou
  uma cadeia de `if` paralela — o que vale a pena confirmar por busca, não por
  suposição, como a revisão da Task 1 fez.
- **Ver o `tsc` falhar antes de corrigir não é teatro — é a prova de que a
  rede de segurança alegada existe de verdade.** A Task 1 poderia ter feito as
  duas mudanças (enum + rótulo) juntas e simplesmente afirmado que uma
  protege a outra. Em vez disso, alargou uma, rodou `tsc`, leu o erro exato
  que a documentação prometia, e só então corrigiu. A diferença entre
  "deveria falhar" e "vi falhar" é a mesma diferença que apareceu no ciclo de
  backend anterior com o portão do `SHOW lock_timeout`.
- **Uma suíte 100% verde não distingue "a etiqueta está certa" de "a busca
  está certa" — só uma fixture que force os dois caminhos a produzir DOMs
  diferentes faz essa distinção.** Duas fixtures byte-idênticas por trás de
  duas rotas diferentes são, do ponto de vista de qualquer asserção sobre o
  DOM final, a mesma fixture. O teste não estava fraco por acidente; estava
  fraco porque os dados de teste, não o código, eram indistinguíveis.
- **Um comentário que cita um bug antigo é uma promessa, não uma prova.** O
  `useReviewRefund.ts` "citava" corretamente a lição do `useDeleteRefund`, mas
  citar sem testar deixa a promessa quebrável pelo primeiro refactor que
  pareça inocente. A prova é o teste que fica vermelho quando alguém desfaz a
  citação.
- **Quando a revisão para de achar bugs, ela não acabou — mudou de alvo.**
  Onze achados menores deste ciclo (registrados achado a achado no ledger de
  execução, não reproduzidos aqui) são quase todos lacunas de cobertura, não
  comportamento incorreto. Isso não é evidência de que o código está pronto;
  é evidência de que **a pergunta certa mudou** de "isto funciona?" para
  "existe alguma mudança futura, plausível e bem-intencionada, que este teste
  deixaria passar sem avisar?".

### Verificação

| Comando | Resultado |
|---|---|
| `npx vitest run` | **157 testes em 38 arquivos**, todos verdes (partiu de 103 em 31) |
| `npx tsc -b --noEmit` | exit 0 |
| `npm run lint` | 0 erros, 0 warnings |
| `npm run build` | ok; bundle **506,00 → 518,36 kB** (+12,36 kB); aviso de chunk > 500 kB **pré-existente**, presente desde o início deste ciclo |

**Nada deste ciclo foi validado em navegador contra a API real** — toda a
suíte roda contra MSW. É a mesma ressalva já registrada para os ciclos
anteriores até a validação manual do Gabriel acontecer, e continua sendo dele,
não substituível por nenhum número acima. Detalhes completos, task a task,
em `Refund-FrontEnd/.superpowers/sdd/2026-07-30-refund-review-ui/progress.md`
e nos relatórios individuais (`task-1-report.md` a `task-9-report.md`) na
mesma pasta.

## Item 13 — TanStack Table (2026-07-31)

**Status:** concluído em 2026-07-31, dentro do ciclo de feature "Navegação na
revisão e tabela de reembolsos", branch `feat/review-navigation-and-refund-table`
do `Refund-FrontEnd` (`485cecb..722371b`). Fecha o Item 13 do
`learning_path.md`. Ledger de execução em
`Refund-FrontEnd/.superpowers/sdd/2026-07-31-review-navigation-and-refund-table/`.

### Por que estudar

A Home listava reembolsos numa `<ul>` desde sempre. TanStack Table é uma
biblioteca *headless* — não desenha nada sozinha; devolve funções
(`getHeaderGroups`, `getRowModel`, `getCanSort`, …) que o componente chama
para montar `<table>`/`<tr>`/`<td>` do jeito que quiser. O ganho não é visual,
é estrutural: colunas viram uma lista de configuração
(`ColumnDef<Refund>[]`) em vez de JSX repetido, e a biblioteca sabe como
mostrar/ocultar coluna, ordenar cabeçalho e paginar — desde que alguém diga
**quem manda** nesses três comportamentos. É exatamente esse "quem manda" que
motiva a primeira lição.

### Lição 1 — `manualSorting`/`manualFiltering`: por que a ordenação não podia viver dentro do TanStack

TanStack Table sabe ordenar, filtrar e paginar sozinho — mas faz isso sobre o
array `data` que recebeu, e a `RefundsTable` só recebe **uma página** (10 de
N reembolsos). Deixar a ordenação embutida ligada teria feito exatamente o
erro que já existe registrado neste diário como origem de um ciclo de backend
inteiro (a consulta da listagem): um "ordenar" que na verdade só reordena as
10 linhas que já chegaram, parecendo funcionar em qualquer teste manual
superficial e mentindo sobre o restante das N-10 linhas que o usuário nunca
vê reordenadas de verdade.

A configuração que evita isso:

```ts
const table = useReactTable({
  data: refunds,
  columns,
  getCoreRowModel: getCoreRowModel(),
  state: { columnVisibility },
  // O cliente tem 10 de N linhas. Ordenar, filtrar ou paginar aqui
  // trabalharia sobre a página, não sobre o conjunto — o erro que originou
  // o ciclo de backend da consulta da listagem.
  manualSorting: true,
  manualFiltering: true,
  manualPagination: true,
});
```

As três flags `manual*` dizem ao TanStack "eu, chamador, já entreguei os
dados ordenados/filtrados/paginados do jeito certo — não recalcule nada."
Sem `getSortedRowModel()`/`getFilteredRowModel()`/`getPaginationRowModel()`
plugados, a tabela nem teria como ordenar sozinha mesmo que quisesse; as
flags são a declaração explícita da intenção, não só a ausência acidental de
um plugin.

**Por que `sort`/`order` moram na URL, e não no estado interno do TanStack.**
O estado de ordenação do TanStack (`table.getState().sorting`, um array de
`{id, desc}`) é memória de componente: existe enquanto a página está montada
e some no reload. Este projeto já tinha decidido, desde o Item 3
(React Router data APIs), que `page`/`name` vivem na URL — pesquisável,
copiável, sobrevive a um F5, funciona com voltar/avançar do navegador. `sort`
e `order` são a mesma classe de estado (um filtro de visualização da
listagem) que `page`/`name`, então a decisão coerente é usar o mesmo lugar,
não abrir uma segunda fonte de verdade. Concretamente, `RefundsTable` **nunca
lê nem escreve** `table.getState().sorting` — o cabeçalho ativo é decidido
comparando a prop `sort` recebida com o `id` da coluna:

```ts
const isSorted = header.column.id === sort;
const SortIcon = !isSorted ? ChevronsUpDown : order === "asc" ? ArrowUp : ArrowDown;
```

Se o estado do TanStack também guardasse uma ordenação, existiriam **duas**
fontes que precisariam ser mantidas sincronizadas manualmente — a URL (fonte
real, validada por Zod, normalizada pelo loader) e o estado interno da
tabela (decorativo, nunca lido por ninguém). Divergir seria trivial: um
reload trocaria a URL sem tocar o estado do TanStack, ou um clique atualizaria
o TanStack sem escrever a URL, e o cabeçalho mostraria uma seta que não bate
com o que a API realmente devolveu. Eliminar a segunda fonte inteira —
não sincronizá-la — é o que fecha essa classe de bug antes de ela poder
existir.

### Lição 2 — `getCanSort()` devolve `false` em silêncio sem um `accessorFn`

A Task 5 seguiu a receita usual — renderizar um botão sempre que
`header.column.getCanSort()` for `true` — e nenhum cabeçalho virou botão,
nem os que deveriam ser ordenáveis. A causa estava na própria implementação
do TanStack (`@tanstack/table-core`, `getCanSort`):

```js
column.getCanSort = () => {
  return (column.columnDef.enableSorting ?? true)
    && (table.options.enableSorting ?? true)
    && !!column.accessorFn;
};
```

O terceiro termo é a pegadinha: `getCanSort()` só é `true` se a coluna tiver
um `accessorFn` (ou `accessorKey`, que gera um por baixo) — **mesmo que
`enableSorting` nunca tenha sido definido como `false`**. Nenhuma coluna de
`RefundsTable` tinha accessor: as Tasks 3–4 as montaram só com `id` e um
`cell` customizado, porque o valor de cada célula (ícone, badge, link) nunca
precisou de um "acessador" de dado bruto — e a ordenação em si acontece no
servidor, então parecia razoável não ter um. TanStack discorda: para ele,
"esta coluna tem um jeito de ler o valor bruto do dado" é o próprio critério
de "esta coluna pode ser ordenada", não uma decisão independente.

O sintoma foi pego pelo ciclo RED→GREEN do TDD, não por inspeção de código:
depois de ligar o cabeçalho exatamente como planejado, os testes de
ordenação continuaram falhando **da mesma forma** que antes de qualquer
mudança — sinal de que o problema não estava no que foi escrito, estava numa
pré-condição não satisfeita antes daquele código rodar. O conserto foi um
`accessorFn` trivial nas quatro colunas ordenáveis:

```ts
{
  id: "name",
  header: "Título",
  // TanStack only considers a column sortable when it has an accessor
  // (getCanSort checks `!!column.accessorFn`); the value itself is
  // unused, sorting happens on the server, but the accessor is what
  // turns the header into a clickable button below.
  accessorFn: (refund) => refund.name,
  cell: ({ row }) => (/* ... */),
},
```

O valor que o `accessorFn` devolve nunca é lido para ordenar nada — quem
ordena é a API, via `sort`/`order` na URL. A função existe só para satisfazer
o teste de veracidade (`!!column.accessorFn`) e destravar `getCanSort()`.
`category` e `user`, que continuam **não** ordenáveis (a API não aceita esses
dois valores em `sort`), mantêm `enableSorting: false` e nenhum `accessorFn`
— redundante à primeira vista (qualquer um dos dois já bastaria), mas
documentado assim de propósito: se um dia ganhassem um `accessorFn` por
outro motivo (por exemplo, para exibição), o `enableSorting: false` explícito
continua barrando o botão sem depender de ninguém lembrar da regra implícita
do `accessorFn`.

### O que lembrar

- **Uma biblioteca headless delega comportamento, não só renderização — e
  "delegar" tem um oposto que precisa ser dito explicitamente.** `manualSorting`/
  `manualFiltering`/`manualPagination` não são flags de configuração
  incidentais; são a diferença entre "o TanStack decide" e "eu decido, o
  TanStack só desenha o que eu mandei". Confiar no padrão (`false`, deixando
  o TanStack tentar ordenar sozinho) sobre uma tabela paginada no servidor
  reproduziria, silenciosamente, um bug de classe já conhecida neste projeto.
- **Duas fontes de verdade para o mesmo estado não é redundância segura —
  é uma obrigação constante de mantê-las iguais, que qualquer mudança
  futura pode esquecer.** A URL já era a fonte de `page`/`name` desde o
  Item 3; estender a mesma regra para `sort`/`order`, e nunca escrever no
  estado interno do TanStack, elimina a sincronização em vez de prometer
  fazê-la sempre.
- **Uma API pública headless pode ter pré-condições implícitas que só
  aparecem lendo a implementação, não a assinatura.** `getCanSort()` parece
  perguntar "esta coluna pode ordenar?", mas na prática pergunta "esta coluna
  tem um jeito de ler um valor?" — duas perguntas que só coincidem por
  construção da própria biblioteca. O `enableSorting: false` sozinho parecia
  suficiente para desligar ordenação; o `accessorFn` ausente já fazia esse
  trabalho por um motivo diferente, e só a leitura do código-fonte (não da
  documentação da API) revelou a sobreposição.
- **Um teste que falha da mesma forma depois de uma mudança é informação,
  não ruído.** A falha idêntica antes e depois da Task 5 ligar o cabeçalho
  por completo foi o sinal de que a causa não estava no código novo — estava
  numa pré-condição que o código novo dependia e não sabia que faltava.

### Verificação (Task 13, fechamento do ciclo)

| Comando | Resultado |
|---|---|
| `npx vitest run` (×3) | **209 testes em 41 arquivos** nas três rodadas, todos verdes; flake do `ResizeObserver` não apareceu em nenhuma |
| `npx tsc -b --noEmit` | exit 0 |
| `npm run lint` | 0 erros, 0 warnings |
| `npm run build` | ok; bundle **518,36 → 559,51 kB** (+41,15 kB, atribuível ao `@tanstack/react-table` + código novo); aviso de chunk > 500 kB pré-existente |

**Nada deste ciclo foi validado em navegador contra a API real na sessão de
fechamento** — a Task 13 rodou sem navegador disponível; a suíte inteira
segue sendo contra MSW. Um checklist de 16 pontos, derivado da spec, foi
deixado para o Gabriel rodar contra o backend real. Detalhes completos, task
a task, em
`Refund-FrontEnd/.superpowers/sdd/2026-07-31-review-navigation-and-refund-table/`
(`task-1-report.md` a `task-13-report.md`).

## Ciclo de feature — Feedback de carregamento e ajustes de UI (2026-07-31)

Décimo ciclo de feature, o quarto do `Refund-FrontEnd`, na branch
`feat/loading-feedback-and-ui-fixes` (`b65bf33..5e1af46`, 15 commits — 2 de
spec/plano, 13 de implementação em 9 tasks com revisão por task, mais a
Task 10 de fechamento). Artefatos em
`Refund-FrontEnd/.superpowers/sdd/2026-07-31-loading-feedback-and-ui-fixes/`.

### Por que agora

Não veio do roadmap: veio do Gabriel usando o próprio app e relatando seis
problemas — spinners que paravam cedo demais em cinco ações diferentes, um
card de pendentes que faltava no admin, rótulos de card ambíguos, diálogos
que reabriam sujos, uma tela de sucesso sem saída e um hover de sidebar com
falha visual. Os dois primeiros (spinner parando cedo em botões de decisão e
em botões que navegam) tinham o mesmo sintoma — "o botão volta ao normal
antes da tela terminar de atualizar" — por **duas causas mecânicas
diferentes**, e essa distinção é a lição central do ciclo.

### Lição 1 — devolver a promise de um callback de mutation estende `isPending`; descartá-la a encurta

**O estado que quebrava.** Os quatro hooks de mutação da feature
(`useCreateRefund`, `useDeleteRefund`, `usePayRefund`, `useReviewRefund`, em
`src/features/refunds/hooks/`) chamavam a invalidação do cache dentro do
`onSuccess` como uma instrução solta, sem `return`:

```ts
onSuccess: () => {
  queryClient.invalidateQueries({ queryKey: refundKeys.lists(), refetchType: "all" });
},
```

O React Query aceita um `onSuccess` **síncrono ou assíncrono**. Quando ele é
uma função `async`/retorna uma `Promise`, a mutation continua em `isPending`
até essa promise resolver. Quando ele **não** devolve nada — como acima, uma
chamada disparada e ignorada — a função retorna `undefined` no mesmo
instante em que é chamada, e o React Query considera o `onSuccess`
concluído ali mesmo, **mesmo que a invalidação (e o refetch que ela
dispara) ainda estejam em voo**. `isPending` cai assim que o `mutationFn`
(a chamada HTTP) termina, não quando os dados que a tela mostra terminam de
se atualizar. Resultado observável: o botão de "Aprovar" voltava ao estado
normal com o histórico de revisões ainda mostrando a versão antiga — a UI
mentia que o trabalho tinha acabado.

**O conserto** foi trocar a instrução solta por uma expressão — só a
pontuação mudou, nada do alvo ou da lógica de invalidação:

```ts
// A promise é DEVOLVIDA de propósito: o React Query mantém a mutation em
// `isPending` até um callback assíncrono resolver. Sem isso o botão volta
// ao normal quando o HTTP termina, com a tela ainda mostrando o estado
// anterior.
onSuccess: () =>
  queryClient.invalidateQueries({ queryKey: refundKeys.lists(), refetchType: "all" }),
```

`{ ...; }` com `;` é um **corpo de bloco**: qualquer `return` dentro dele
precisa ser escrito explicitamente, e sem ele a função sempre devolve
`undefined`. `() => expressão` sem chaves é um **corpo de expressão**: o
valor da expressão **é** o retorno, automaticamente. A troca de `{ chamada;
}` para `chamada` (sem chaves, sem `;`) é a diferença inteira entre "o
React Query não sabe que ainda há trabalho pendente" e "o React Query
espera o trabalho terminar". A Task 10 confirmou por `git diff` que essa foi
a única mudança nos quatro hooks — nenhum `queryKey` nem `refetchType` foi
alterado junto, então a correção não trocou **o que** é invalidado, só
**quando** o React Query considera a invalidação concluída.

### Lição 2 — esperar dados (React Query) não é o mesmo que esperar a rota (React Router)

Corrigir os quatro hooks resolveu aprovar, rejeitar e marcar como pago — as
três ações que **terminam na mesma tela**, com uma query para o React Query
observar. Login, excluir e criar têm o mesmo sintoma (botão volta ao normal
cedo demais) por uma causa **diferente**: as três terminam em **navegação**
(para `/`, para a tela de sucesso), e não existe uma query cujo `isPending`
descreva "a rota já assentou". `isPending` de uma mutation só sabe sobre a
**mutation**; ele nunca soube, e não tem como saber, que o componente que a
disparou está prestes a ser desmontado por uma troca de rota.

`useNavigation()`, do modo Data do React Router, resolve isso porque
observa uma coisa diferente: o **estado da navegação em si**, não o estado
de uma requisição.

```ts
const navigation = useNavigation();
const isBusy = isDeleting || navigation.state !== "idle";
```

`navigation.state` vale `"idle"` quando nenhuma navegação está em
andamento, e `"loading"`/`"submitting"` enquanto o router está executando
loaders/actions da rota de destino antes de trocar a tela. Combinar os
dois estados (`isDeleting` do hook de mutation **e** `navigation.state`) é
o que faz o botão continuar ocupado do clique até a Home realmente
aparecer — cobre tanto a chamada HTTP quanto o tempo entre "a chamada
terminou" e "a rota nova está pronta para ser mostrada". Usado nos três
lugares que navegam de verdade: `PageLogin.tsx` (login → Home),
`PageRefundDetails.tsx` (excluir → Home) e `RefundFormDialog.tsx` (criar →
tela de sucesso) — e só neles; a Task 10 conferiu por busca que nenhum
outro componente importa `useNavigation` sem ter uma navegação real para
observar.

**O que lembrar dos dois juntos:** "esperar" não é uma operação genérica.
React Query sabe esperar **dados** (uma query, uma mutation); React Router
sabe esperar **a rota**. Uma ação que só atualiza dados na mesma tela
precisa da Lição 1; uma ação que também troca de tela precisa das duas —
a Lição 1 para os dados, a Lição 2 para a rota. Confundir os dois leva a
tentar consertar um problema de navegação mexendo em `invalidateQueries`
(não adianta: a query pode estar perfeitamente sincronizada e o botão
ainda voltar cedo, porque quem não assentou foi a rota), ou a tentar
consertar um problema de dados com `useNavigation` (também não adianta: não
há navegação nenhuma para observar em aprovar/rejeitar/pagar).

### O que mais mudou, mais rápido

- **Card de pendentes do admin** (`usePendingCount`, novo): uma consulta
  dedicada e deliberadamente **global** (`?status=pending&per_page=1`, só
  `total`), que ignora o filtro/busca/página da lista — ao custo de uma
  requisição HTTP a mais por carga da Home do admin.
- **Rótulos de card com escopo declarado**: `"Solicitações (Pago)"` quando
  há filtro de status ativo, porque dois dos três cards da Home seguem o
  filtro e um (pendentes) não — a ambiguidade era justamente não dizer qual
  regra vale para qual card.
- **Diálogos resetam ao fechar, não só ao ter sucesso**, com a limpeza de
  erro **escopada por ação** (`pendingAction`/`errorSource`) para que
  cancelar uma ação não apague o erro de outra ainda relevante na mesma
  tela.
- **Histórico de revisões com `toReversed()`, nunca `.reverse()`**: o array
  vem do cache do React Query, e `.reverse()` muta o array original **no
  lugar** — inverteria a ordem de uma referência que outras partes da UI
  ainda podem estar lendo. `toReversed()` (ES2023) devolve uma cópia
  invertida, deixando o original intacto.
- **Sidebar: `translate-x-2` deslocava a pintura, não a caixa.**
  `translate` é uma transformação visual — desenha o conteúdo deslocado sem
  mover a caixa de layout; o `hover:bg-*`, que pinta a **caixa**, ficava
  para trás, deixando uma faixa sem destaque. `pl-2` (padding, parte do box
  model) move a caixa de verdade. No modo trilho colapsado, a correção
  precisou de uma segunda rodada — a primeira tentativa centralizava o
  ícone dentro do próprio botão (que já não tinha folga nenhuma para
  redistribuir); a aritmética certa era que o `translate-x-2` original
  centralizava o **botão inteiro** dentro do trilho mais largo
  (`(48-32)/2 = 8`). Nenhuma das duas rodadas foi confirmada olhando a tela
  — só matemática de caixa contra o CSS gerado (ver pendências no
  [estado atual do projeto](plans/current-state.md)).

### Verificação (Task 10, fechamento do ciclo)

| Comando | Resultado |
|---|---|
| `npx vitest run` (×3, saída completa salva em arquivo) | **240 testes em 44 arquivos** nas três rodadas, todos verdes; flake do `ResizeObserver` ausente nas três |
| `npx tsc -b --noEmit` | exit 0 |
| `npm run lint` | 0 erros, 0 warnings |
| `npm run build` | ok; bundle **559,51 → 560,74 kB** (+1,23 kB); aviso de chunk > 500 kB pré-existente |

Uma rodada anterior às três formais (sem salvar a saída completa em arquivo)
apresentou o flake do `ResizeObserver`; ficou registrada como evidência
parcial, não como uma quarta rodada limpa — ver a pendência atualizada no
[estado atual do projeto](plans/current-state.md).

**Nada deste ciclo foi validado em navegador contra a API real** — não havia
navegador disponível na sessão de fechamento. Um checklist de 15 pontos,
derivado da spec, foi deixado para o Gabriel rodar contra o backend real,
com atenção especial ao item do sidebar (o único, dos seis problemas
originais, que a suíte automatizada não consegue confirmar nem refutar).
Detalhes completos, task a task, em
`Refund-FrontEnd/.superpowers/sdd/2026-07-31-loading-feedback-and-ui-fixes/`
(`task-1-report.md` a `task-10-report.md`).

## Item 11 — Error boundaries e recuperação (2026-08-03)

**Status:** concluído em 2026-08-03, na branch `feat/error-boundaries` do
`Refund-FrontEnd`, partindo de `6c63ff5`. Fecha o Item 11 do `learning_path.md`.
Retomada da trilha depois de dez ciclos de feature.

### Por que estudar

O item existe para separar três mecanismos de erro que o projeto tratava como
um só. Eles não se substituem:

| Mecanismo | Pega o quê | Estado antes deste item |
|---|---|---|
| `isError` do TanStack Query | falha **assíncrona** (HTTP, parse do Zod) — um estado, não uma exceção | usado em toda tela |
| `ErrorBoundary` do React Router | erro de **loader/action** + erro de **render** das rotas descendentes | existia (`router.tsx`) |
| Error boundary do React | erro de **render** em qualquer ponto da árvore, inclusive **fora** do router | **não existia** |

O ponto de partida era melhor do que a trilha assumia: `router.tsx` já trazia
`ErrorBoundary: PageRouteError` na rota raiz, com teste. O que faltava era
mais específico — e a especificidade é o aprendizado.

### O estado anterior, e as três lacunas

```tsx
// src/main.tsx                        // src/App.tsx
<StrictMode>                           <AuthProvider>        ← fora do router
  <QueryClientProvider client={...}>     <ThemeEffect />     ← fora do router
    <App />                              <RouterProvider router={router} />
```

**Lacuna 1 — tela branca, com caminho real.** Tudo acima do `RouterProvider`
renderizava sem cobertura nenhuma. E havia um gatilho concreto:

```tsx
// src/context/AuthContext.tsx:10-15 (antes)
function loadStoredUser(): AuthUser | null {
  const raw = localStorage.getItem(USER_STORAGE_KEY);   // ← FORA do try
  if (!raw) return null;

  try {                                                  // ← o try só começa aqui
    const result = storedUserSchema.safeParse(JSON.parse(raw));
```

O `try` protege o `JSON.parse` e o `safeParse`, mas não o `getItem`. Acesso a
`localStorage` **lança** quando o navegador bloqueia dados do site. Como isso
roda no inicializador do `useState` do `AuthProvider`, a exceção acontece
durante o render, acima do router: React desmonta a árvore inteira e o usuário
vê uma página em branco, sem mensagem e sem rota de saída.

**Lacuna 2 — o boundary único derrubava o shell.** Estando na rota raiz, acima
de `ProtectedRoute` e `MainLayout`, qualquer erro de render numa página
substituía **tudo** pelo `PageRouteError` (`min-h-screen`, com o próprio
`<main>`). O usuário perdia a navegação junto com a tela que falhou.

**Lacuna 3 — não havia retry.** A única ação era `<Link to="/">`. Quando o que
falhava era a própria `/`, o botão oferecido apontava para a página que
acabara de quebrar.

### Lição 1 — um error boundary do React só pode ser uma classe

`getDerivedStateFromError` e `componentDidCatch` não têm equivalente em hook.
Não é escolha de estilo: a API não existe em componente de função. É a única
classe do projeto, e o comentário no arquivo diz por quê.

Os dois métodos têm papéis distintos, e confundi-los é o erro comum:

```tsx
// src/components/core/AppErrorBoundary.tsx
// Fase de render — não pode ter efeito colateral; só vira o estado.
static getDerivedStateFromError(): AppErrorBoundaryState {
  return { hasError: true };
}

// Fase de commit — aqui efeito é permitido. É a costura onde o log
// estruturado entra quando o Item 24 existir.
componentDidCatch(error: Error, info: ErrorInfo) {
  console.error("Uncaught render error:", error, info.componentStack);
}
```

O que ele **não** pega: event handlers, `setTimeout` e código assíncrono. Só
render, efeitos de layout e construtores. Por isso ele não substitui o
`isError` de nenhuma query — e por isso nenhuma query mudou de comportamento
neste item.

Estando fora do `RouterProvider`, o fallback não pode usar `<Link>` nem
`navigate`: não há router. Recarregar o documento é a única recuperação
disponível dali, e o teste trava esse contrato.

### Lição 2 — o `ErrorBoundary` do React Router renderiza NO LUGAR da rota que falhou

Esta é a sutileza que decidiu o desenho do passo 4. A intenção era "erro de
página não derruba o shell", e a leitura ingênua seria pôr o boundary na rota
do `MainLayout`. Isso faria exatamente o contrário: o boundary substitui o
**elemento da rota à qual está preso**, então o shell sairia junto.

A correção é prender o boundary a uma rota **sem path, abaixo** do
`MainLayout`:

```tsx
// src/router.tsx (depois)
{
  Component: MainLayout,
  children: [
    {
      ErrorBoundary: ContentError,   // ← abaixo do shell, não sobre ele
      children: [ /* todas as páginas */ ],
    },
  ],
}
```

**A prova não foi o teste passar.** Foi mover o boundary para a rota do
`MainLayout` de propósito e ver o teste "keeps the shell rendered when a page
throws" falhar (1 de 5), depois restaurar e ver os 5 voltarem.

### Lição 3 — a fixture que não conseguia falhar, por causa do retry automático do React

A primeira sonda para "o `revalidate()` limpa um erro de **render**?" usou uma
fixture que zerava a própria flag durante o throw:

```tsx
Component: () => {
  if (shouldThrow) {
    shouldThrow = false;      // ← errado
    throw new Error("render boom");
  }
  return <p>conteúdo carregado</p>;
}
```

O resultado foi um DOM com o conteúdo carregado e **o boundary nunca
aparecendo**. A causa: quando um componente lança durante um render
concorrente, o React **re-tenta o render** antes de acionar o boundary — e a
segunda tentativa passava, porque a própria fixture tinha limpado a flag. A
sonda não media o que eu achava que media.

A fixture correta mantém o controle **fora** do componente, para o teste
decidir quando parar de lançar. Vale como padrão geral: uma fixture que muda
de estado ao falhar pode esconder o mecanismo que se quer observar.

### Lição 4 — a hipótese registrada no plano estava errada, e o teste foi quem disse

No plano do item ficou escrito, explicitamente, que eu **não sabia** se
`revalidate()` limparia um erro de *render* (só tinha certeza sobre erro de
*loader*), e que não afirmaria nada sem teste. A sonda corrigida respondeu:

```
boundaryShowed=true   recovered=true   stillErrored=false
```

**Limpa os dois.** A hipótese pessimista estava errada. Os dois casos viraram
testes separados (`recovers from a loader failure…` e `recovers from a render
failure…`) justamente porque são caminhos diferentes dentro do react-router e
o botão poderia virar um no-op silencioso em um deles.

### O que mais mudou

`getErrorMessage` era privada do `PageRouteError`. Com o `ContentError`
nascendo, virou o **segundo uso real** — o gatilho que o `learning_path.md`
define para extrair. Foi para `src/lib/route-error.ts` (camada `shared`, que a
camada `app` pode importar) como `getRouteErrorMessage`. Exportá-la do próprio
`PageRouteError` teria disparado `react-refresh/only-export-components`, que
está ligada fora de `components/ui`.

### O que lembrar

- Boundary do React ≠ `ErrorBoundary` do React Router ≠ `isError` de query.
  O primeiro cobre render em qualquer lugar; o segundo, loader/render dentro
  de rotas; o terceiro é estado assíncrono, não exceção.
- Error boundary **precisa** ser classe. `getDerivedStateFromError` é fase de
  render (sem efeitos); `componentDidCatch` é fase de commit (com efeitos) — e
  é onde o Item 24 vai plugar.
- Nada disso pega erro de event handler, timer ou async.
- O `ErrorBoundary` de uma rota **substitui o elemento daquela rota**. Para
  preservar um layout, o boundary vai numa rota filha sem path, não na rota do
  layout.
- Uma fixture de teste que se conserta ao falhar pode nunca chegar ao
  mecanismo sob teste — o React re-tenta renders concorrentes que lançam.
- `revalidate()` recupera **tanto** erro de loader quanto de render. Foi
  medido, não deduzido.

### Verificação

Ponto de partida medido **antes** de abrir a branch, como a lição do ciclo
anterior exige: 246 testes em 44 arquivos, `tsc` exit 0, lint 0/0, bundle
560,88 kB — todos verdes na `main`.

| Verificação | Antes | Depois |
|---|---|---|
| `npx vitest run` (3 rodadas) | 246 em 44 arquivos | **256 em 46 arquivos**, verdes nas três |
| `npx tsc -b --noEmit` | exit 0 | exit 0 |
| `npm run lint` | 0 erros, 0 warnings | **0 erros, 0 warnings** |
| `npm run build` | 560,88 kB | **562,61 kB** (+1,73 kB) |

O flake do `ResizeObserver` **não apareceu em nenhuma das três rodadas**, e a
saída de todas foi salva em arquivo *antes* de ser lida — a regra que a sessão
anterior registrou ter falhado duas vezes.

Dois testes foram validados por quebra deliberada, não só por passarem: o
boundary global (3 de 4 falham com `getDerivedStateFromError` devolvendo
`false`) e o aninhamento do shell (1 de 5 falha com o boundary na rota do
`MainLayout`).

**Limitação registrada — o gatilho real da Lacuna 1 não foi observado.** O
comportamento com `localStorage` bloqueado só aparece num navegador com essa
configuração ligada; o jsdom não a reproduz. A suíte prova que *um filho que
lança* produz o fallback, não que *este* filho lança naquele cenário. Fica
como item de checklist de navegador, não como validado.

## Item 14 — i18n com bootstrap assíncrono (2026-08-05)

**Status:** concluído em 2026-08-05, na branch `feat/i18n` do `Refund-FrontEnd`,
partindo de `887cd45`. Fecha o Item 14 do `learning_path.md`. Dois catálogos
completos (`pt-BR` e `en-US`), 97 chaves cada.

### Por que estudar

i18n separa **chave de mensagem** de **catálogo por locale**: o componente
deixa de conter o texto e passa a conter uma referência a ele. O que dá nome ao
item é o **bootstrap assíncrono** — se o catálogo carrega depois do primeiro
render, o usuário vê um flash no idioma errado ou chaves cruas.

Registrado com honestidade na apresentação: **o ganho aqui é de aprendizado,
não de produto.** O Refund tem um usuário e um idioma. O que o item compra de
verdade é a disciplina de separar texto de componente — e três descobertas que
só apareceram porque o trabalho foi feito.

### Lição 1 — "dado avaliado na importação" é a categoria que decide tudo

Quatro módulos guardavam texto e são avaliados **uma vez, na importação**,
antes de qualquer locale existir: `nav-items.tsx`, `constants/status.ts`,
`constants/categories.ts` e os schemas Zod. Nenhum pode chamar `t`.

A solução é sempre a mesma — guardar a **chave** e traduzir em quem renderiza:

```ts
// antes                          // depois
{ label: "Pendente", ... }        { labelKey: "status.pending", ... }
```

E o detalhe que vale mais que a solução: **renomear `label` para `labelKey`
transformou uma migração invisível em 14 erros de compilação.** Se o campo
tivesse continuado `label`, cada call site esquecido renderizaria a chave crua
na tela, em silêncio. O compilador virou a lista de tarefas.

Onde a função não é componente, `t` entra por parâmetro:

```ts
// createRefundColumns é função pura, não componente
function createRefundColumns(viewer: RefundViewer | null, t: TFunction) { … }
const columns = useMemo(() => createRefundColumns(viewer, t), [viewer, t]);
```

Passar explicitamente também põe `t` na lista de dependências do `useMemo` —
trocar de idioma reconstrói as colunas, que é exatamente o necessário.

### Lição 2 — um ponto único de exibição vale mais que N pontos de tradução

As mensagens dos schemas Zod viraram chaves. Poderiam ter sido traduzidas em
cada formulário, mas `FormMessage` (`ui/form.tsx:140`) é **o único lugar** onde
qualquer mensagem de validação chega à tela:

```tsx
const body = error ? t(String(error?.message ?? "")) : props.children
```

Uma linha cobre todos os formulários. Duas propriedades tornam isso seguro:
`t()` devolve a string intacta quando ela não é uma chave, então mensagem
literal continua funcionando; e o arquivo é vendorizado do shadcn, então a
edição foi documentada como manual — regenerar pelo CLI perderia a mudança,
exatamente como já acontece com `ui/sidebar.tsx`.

**Como os testes provaram que as duas metades se conectam:** as asserções sobre
a **saída do schema** falharam (agora é chave) e foram atualizadas; as
asserções sobre o **texto renderizado** continuaram passando sem tocar em nada.
São elas que provam que a chave vira português na tela.

### Lição 3 — o plural do CLDR discordou do ternário, e no caso mais fácil de não notar

O ternário antigo:

```tsx
`${total} ${total === 1 ? "solicitação" : "solicitações"}`
```

Trocado por `t("home.requestCount", { count })`, com `_one`/`_other`. O teste
falhou em `count: 0`:

```
expected '0 solicitação' to be '0 solicitações'
```

**`Intl.PluralRules("pt-BR").select(0)` devolve `"one"`.** O CLDR classifica
zero como singular em português. Ou seja, a migração teria mudado o texto de
uma tela vazia — o estado mais comum de um app novo — de forma silenciosa e
"tecnicamente correta".

Medido, não deduzido: o i18next consulta um `_zero` explícito **antes** do
CLDR, então a redação anterior foi preservada de propósito, com um teste que
afirma as duas coisas (a classificação do CLDR e a sobreposição).

A lição geral: **adotar um padrão não é neutro.** O CLDR está certo sobre a
regra e ainda assim a mudança seria uma regressão de produto.

### Lição 4 — bootstrap assíncrono em produção, síncrono em teste

```ts
// main.tsx — espera o catálogo ANTES do primeiro render
initI18n(useUiStore.getState().locale).catch(…).finally(render)
```

O locale sai direto da store, sem hook, porque ainda não há árvore React. E o
`.finally` é deliberado: catálogo que falha ainda renderiza, mostrando chaves
cruas — ruim, mas diagnosticável, contra uma tela branca.

Os testes fazem o oposto (`src/test/i18n.ts`): inicialização **síncrona**, com
os dois catálogos importados estaticamente. Testes renderizam componentes
direto, sem passar pelo bootstrap, então precisam de uma instância pronta. Como
o `pt-BR` fica ativo e o catálogo tem as mesmas strings, **as 260 asserções
existentes continuaram passando sem edição** — o oposto do que a apresentação
do item previu.

### O que mais mudou

- `format.ts` lê o idioma ativo em vez de fixar `pt-BR` em dois lugares.
- `ReviewTimeline` parou de formatar data inline — ele furava o `formatDate` e
  por isso não tinha nem a guarda de data inválida nem o `timeZone: "UTC"`.
  Inconsistência **pré-existente**, fechada de passagem.
- `Accept-Language` em toda requisição. O backend **ignora** hoje; é preparação
  declarada como tal no interceptor, não efeito imediato.
- `PageComponents` ficou **deliberadamente fora**, com o motivo no topo do
  arquivo: é vitrine do design system, com rótulo de amostra e dado fictício.

### O que lembrar

- Texto em módulo avaliado na importação (constantes, schemas, definições de
  rota) **não pode** ser traduzido ali. Guarde a chave.
- Renomeie o campo ao migrar (`label` → `labelKey`): transforma erro silencioso
  de runtime em erro de compilação.
- Ache o **ponto único de exibição** antes de traduzir em N lugares.
- Moeda não é formatação: trocar símbolo sem converter valor é mentira. BRL
  continua BRL nos dois idiomas; muda a convenção de escrita.
- CLDR pode discordar do que o código fazia. Zero é singular em português.
- Bootstrap assíncrono em produção, síncrono em teste — são requisitos
  diferentes, e tentar unificá-los custaria mais que manter os dois.

### Verificação

Ponto de partida medido antes de abrir a branch: 260 testes em 46 arquivos,
`tsc` 0, lint 0/0, bundle 562,61 kB.

| Verificação | Antes | Depois |
|---|---|---|
| `npx vitest run` (3 rodadas) | 260 em 46 | **274 em 48**, verdes nas três |
| `npx tsc -b --noEmit` | exit 0 | exit 0 |
| `npm run lint` | 0/0 | **0/0** |
| `npm run build` | 562,61 kB | **606,92 kB** (+44,31 kB) |

O acréscimo é o runtime do i18next. **Os catálogos saem como chunks separados**
(`pt-BR` 4,17 kB, `en-US` 3,86 kB), então quem nunca troca de idioma nunca
baixa o outro — que é o efeito prático do carregamento sob demanda.

**Não validado em navegador.** A troca de idioma sem flash é justamente o que a
suíte não prova bem: o jsdom não tem pintura. Checklist para o Gabriel:
(1) recarregar com `en-US` salvo e não ver flash de português nem de chave;
(2) trocar o idioma e ver a tela inteira mudar sem recarregar; (3) conferir que
data e moeda mudam de formato junto; (4) confirmar no DevTools que o chunk do
outro catálogo só é baixado ao trocar.

## Item 15 — Motion com propósito (2026-08-05)

**Status:** concluído em 2026-08-05, em duas branches empilhadas do
`Refund-FrontEnd`: `feat/motion` (a camada de reduced-motion) e
`feat/motion-animations` em cima dela (as quatro animações). Partiu de
`887cd45`. Fecha o Item 15 do `learning_path.md`.

### Por que estudar

Animação tem função: explicar **mudança de estado**, **hierarquia** ou
**continuidade**. Sem função, é ruído. E há um lado que não é estético:
`prefers-reduced-motion` é uma preferência de sistema operacional, ligada
tipicamente por quem tem **distúrbio vestibular** — deslocamento na tela
provoca náusea de verdade.

O levantamento inverteu o enquadramento do item. O `learning_path.md` supunha
"animações simples, sem estratégia"; o que havia era:

| Origem | Quantidade |
|---|---|
| Design system (Radix/shadcn): Dialog, Sheet, Tooltip, Select, Sidebar | `animate-in/out` ×6, fade ×10, zoom ×6, slide ×12 |
| `animate-spin` dos botões ocupados | 8 arquivos |
| Código do app | **1** (`transition hover:bg-accent/50`) |

Ou seja: **não havia animação gratuita para remover.** O problema era a
ausência da camada que respeita a preferência — `grep -rn "reduced-motion" src/`
não devolvia nada.

### Lição 1 — neutralizar movimento sem matar a animação

A saída preguiçosa seria `animation: none` em tudo sob a preferência. Isso
remove também o fade, que **não** provoca sintoma vestibular, e deixa a
interface trocando de estado sem nenhum sinal.

A saída cirúrgica saiu de ler o CSS **gerado**, não de supor:

```css
@keyframes enter {
  0% {
    opacity: var(--tw-enter-opacity, 1);
    transform: translate3d(var(--tw-enter-translate-x, 0), …)
               scale3d(var(--tw-enter-scale, 1), …)
               rotate(var(--tw-enter-rotate, 0));
  }
}
```

As keyframes leem variáveis com fallback. Então basta devolvê-las ao valor de
identidade sob a preferência: o movimento some, o fade fica, a animação
continua existindo.

```css
@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after {
    --tw-enter-translate-y: 0 !important;
    --tw-enter-scale: 1 !important;
    /* opacity intocada de propósito */
  }
  .animate-spin { animation: none !important; }
}
```

O `!important` é estrutural, não preguiça: estas regras casam em `*`
(especificidade 0) e as utilitárias do Tailwind casam em classe (0,1,0).

Os spinners param. Rotação contínua é a categoria pior (WCAG 2.2.2, "Pause,
Stop, Hide") porque não termina sozinha — e **nada de significado se perde**,
porque `aria-busy` e o rótulo escrito ("Aprovando…") já carregam o estado. O
teste novo prova exatamente essa premissa, e diz o que **não** prova: o jsdom
não tem engine de CSS, então nenhum teste aqui observa animação começando ou
parando.

### Lição 2 — o bug que só apareceria em desenvolvimento

Para animar "chegou item novo" é preciso saber qual item é novo, e o React não
conta: um re-render é idêntico se a lista cresceu ou apenas refez a busca. A
primeira versão do hook registrava os ids vistos **durante o render**:

```ts
// ERRADO
if (!seen.current.has(id)) {
  entering.add(id);
  seen.current.add(id);   // ← escrita durante o render
}
```

Funciona em produção e **quebra sob `StrictMode`**, que renderiza duas vezes: a
primeira passada registra o id, a segunda — a que o React mantém — encontra-o
já conhecido e reporta "nada entrando". **A animação nunca apareceria no
`npm run dev` enquanto funcionaria no build.** É quase a pior forma de um bug
se comportar.

A correção é separar leitura de escrita:

```ts
const seenIds = seen.current;              // lê no render
useEffect(() => { /* escreve depois */ });
```

As duas passadas calculam a mesma resposta, e a classe ainda entra no mesmo
commit do elemento — não há frame em que o item apareça sem animação.

**Os testes novos renderizam sob `StrictMode` por causa disso**, e a prova não
foi passarem: foi restaurar a versão antiga e ver **3 dos 6 falharem**.

### Lição 3 — uma animação CSS não reinicia se a classe nunca sai

Relatado pelo Gabriel usando o app: o badge pulsava de `pending` para
`approved`, mas não de `approved` para `rejected`. A detecção estava certa; o
problema era CSS.

Uma animação toca quando a classe **aparece** num nó que não a tinha. Entre
duas mudanças consecutivas não existe nenhum render em que `statusChanged`
volte a ser `false` — então a classe permanecia no elemento e o navegador não
tinha o que reiniciar.

```tsx
<Badge key={refund.status} className={cn(statusChanged && "badge-pop")}>
```

O `key` dá um nó novo a cada valor. `statusChanged` continua necessário: sem
ele, abrir a tela animaria um estado que não mudou.

### Lição 4 — `height: auto` não é animável; fração de grid é

O pedido foi explícito: o item novo chega deslizando **e os de baixo se afastam
para recebê-lo**, sem sobreposição. Isso é *layout animation*, o caso clássico
de `framer-motion` (~40 kB num bundle já acima do aviso de 500 kB).

Feito em CSS:

```css
@keyframes timeline-enter {
  from { grid-template-rows: 0fr; opacity: 0; transform: translateX(-1.5rem); }
  to   { grid-template-rows: 1fr; opacity: 1; transform: translateX(0); }
}
```

O `translateX` diz "chegou"; o `grid-template-rows` de `0fr` para `1fr` é o que
**abre espaço de verdade** — os itens abaixo são deslocados por layout, não
cobertos por um transform. `min-height: 0` no filho é obrigatório: sem ele o
conteúdo impõe altura mínima e a linha nunca chega a `0fr`.

### O que ficou sem resolver, e por quê isso é registro e não desculpa

**O "flick" ao abrir a Home continua.** Duas tentativas falharam:

1. `scrollbar-gutter: stable` na `div.flex-1.overflow-auto` do `MainLayout`.
   **Sem efeito nenhum** — aquela div parece o contêiner de rolagem e não é: o
   wrapper do sidebar é `min-h-svh` (altura MÍNIMA), então cresce com o
   conteúdo e a div nunca transborda. Quem rola é o documento.
2. A mesma regra no `html`, o elemento certo. **Também não resolveu**, o que
   descarta a barra de rolagem como causa.

As duas foram removidas a pedido do Gabriel. Fica a hipótese que já incomodava
desde o início: a entrada das linhas usa `opacity` e `translateY`, e **nenhuma
das duas altera layout** — as linhas ocupam a altura final desde o primeiro
frame, então a animação sozinha não explica a página crescer e encolher.

**A lição:** duas correções erradas seguidas são sinal de falta de observação,
não de falta de ideia. O próximo passo, se houver, é medir `scrollHeight` por
frame durante a carga e olhar o número.

### O que lembrar

- Sob `prefers-reduced-motion`, remova **movimento** e preserve **opacidade**.
  Matar toda animação também remove sinal.
- Rotação contínua é a pior categoria; pare os spinners, mas só depois de
  garantir que o estado é carregado por `aria-busy` e por texto.
- Escrita de ref **durante o render** quebra sob `StrictMode`. Leia no render,
  escreva no efeito. E teste sob `StrictMode`, ou o bug espera pelo `dev`.
- Animação CSS não reinicia se a classe nunca sai do nó. `key` resolve.
- `height: auto` não é animável; `grid-template-rows: 0fr → 1fr` é, e é assim
  que se abre espaço sem biblioteca.
- Leia o CSS gerado antes de escrever regra sobre ele. As variáveis do
  tw-animate-css vieram de `grep` no bundle, não de memória.

### Verificação

Ponto de partida medido antes das branches: 274 testes em 48 arquivos, `tsc` 0,
lint 0/0, CSS 59,61 kB, JS 606,92 kB.

| Verificação | Antes | Depois |
|---|---|---|
| `npx vitest run` (3 rodadas) | 274 em 48 | **287 em 51**, verdes nas três |
| `npx tsc -b --noEmit` | exit 0 | exit 0 |
| `npm run lint` | 0/0 | **0/0** |
| CSS | 59,61 kB | **61,54 kB** (+1,93 kB) |
| JS | 606,92 kB | **607,94 kB** (+1,02 kB) |

Praticamente tudo é CSS — nenhuma biblioteca de animação entrou.

`react-hooks/refs` foi desligada **por arquivo, pelo nome**, para
`src/hooks/useEnteredItems.ts`, seguindo o precedente já existente no
`eslint.config.js`. Diretiva inline não funciona ali: a regra segue o valor
através do alias local, então precisaria ser repetida em cada uso.

**Validado em navegador pelo Gabriel em 2026-08-05**, com uma ressalva
importante: o badge, a timeline, a tabela e os banners foram conferidos e
**funcionam**; o flick da Home **não** foi resolvido e ficou registrado como
pendência. A validação do `prefers-reduced-motion` em si (DevTools → Rendering
→ Emulate) **não foi confirmada explicitamente** — ver pendências.

## Item 16 — Pipeline de qualidade (2026-08-06)

**Status:** concluído em 2026-08-06, na branch `feat/ci` de **ambos** os
repositórios. Fecha o Item 16 e, com ele, a **Fase 3** do `learning_path.md`.
Primeiro item que produz artefato nos dois repos ao mesmo tempo.

### Por que estudar, e por que só metade

O item empacota duas coisas com valor muito diferente para este projeto.

**CI:** custo comprovado de não ter. O commit `2d07a8d` deixou a `main` do
frontend quebrada em `tsc`, `eslint` **e** `build`, e ninguém viu por dias
porque nenhuma verificação rodou naquele intervalo.

**Oxlint: DELIBERADAMENTE PULADO**, com o número na mesa. O ESLint leva
**2,1 s** aqui. O Oxlint economizaria ~2 segundos, adicionaria uma segunda
ferramenta de lint com configuração própria e criaria a pergunta "qual das
duas reclamou disso?" a cada falha. O gargalo real é o Vitest, com **9,8 s**,
que o Oxlint não toca. Ele faz sentido quando o lint custa dezenas de
segundos; não é o caso. Decisão do Gabriel, registrada em vez de silenciada —
o item fica cumprido pela metade **explicitamente**, que é mais honesto que
inteiro por obrigação.

### Lição 1 — o runner começa vazio

É a ideia que faz todo o resto encaixar. O runner é uma máquina Ubuntu limpa,
criada a cada execução, que nunca viu o projeto: sem código, sem `node_modules`,
sem Node na sua versão. Quase todo erro de quem começa nasce de esquecer isso.

Daí a ordem obrigatória: `checkout` (clona) → `setup-node`/`setup-python`
(instala runtime) → instala dependências → só então verifica.

Vocabulário, mapeado no que já existia:

| Termo | O que é |
|---|---|
| workflow | arquivo YAML em `.github/workflows/` |
| trigger (`on`) | o evento que dispara (`push`) |
| job | unidade numa máquina própria |
| step | um passo; `run:` = comando, `uses:` = ação pronta |

### Lição 2 — a prova de um portão é vê-lo fechar

Depois do primeiro verde, um erro de tipo foi inserido **de propósito** e
empurrado. O CI reprovou em **23 s** contra 2m11s do verde, e a saída mostrou
por quê:

```
X Run npm run typecheck
- Run npm run lint      ← nem rodou
- Run npm test          ← nem rodou
- Run npm run build     ← nem rodou
```

Os passos vão do mais barato ao mais caro e o job para no primeiro que falha,
então um erro de tipo é reportado sem esperar 10 s de testes. O erro chega
inteiro: `##[error]src/lib/format.ts(13,9): error TS2322: …`.

Mesmo padrão que este projeto já usa nos testes: **passar não é prova; falhar
quando deve é.**

### Lição 3 — o achado que valeu mais que o item inteiro

O CI do backend reprovou no primeiro dia, no `pylint src`. Investigando,
descobriu-se que **ele também reprovava localmente**:

```bash
$ pylint src ; echo $?
Your code has been rated at 10.00/10
8
```

**Nota e código de saída são coisas diferentes.** O pylint não penaliza a nota
por uma mensagem de refatoração, mas sai com código ≠ 0 se emitiu qualquer
mensagem. Nenhuma sessão anterior conferiu o `$?` — todas leram a linha da nota
e registraram "pylint 10.00/10" como aprovação. **A afirmação estava
incompleta em vários ciclos deste diário.** O CI achou em 54 segundos, porque
máquina não lê linha bonita: lê código de saída.

A causa era `R0801` (código duplicado): o envelope de resposta repetido em
**três** controllers — o pylint apontou dois, porque o terceiro (`payer`) o
montava inline. `format_refund_response` foi extraída para junto de
`serialize_refund`.

Os outros três envelopes ficaram de fora **de propósito**: a listagem carrega
`count/total/sum/page`, a exclusão responde `{id, deleted}` e o revisor tem a
forma achatada divergente do `UC-007`. Unificar aqueles seria a abstração
errada — a duplicação real existe só entre os três que de fato concordam.

Confirmado que `--fail-under=10` **não** resolve (continua saindo 8); só
eliminar a duplicação ou desligar a regra zera o código.

### Lição 4 — o CI é mais confiável que a máquina de quem desenvolve

Alegado na apresentação, **comprovado duas vezes**:

1. O `pylint` acima, invisível para quem lia a nota.
2. Sem o `.env`, o `pytest` **nem coleta** os testes: 7 erros de
   `sqlalchemy.exc.ArgumentError`, porque `src/configs` lê `DATABASE_URL` na
   importação e `create_async_engine(None)` estoura antes de qualquer mock
   existir. Verificado escondendo o `.env` localmente, não suposto.

O segundo obrigou o workflow a declarar variáveis fictícias — e isso é
**sintoma, não solução**. Configuração lida em tempo de importação é
exatamente o que o **Item 17 (pydantic-settings)** existe para resolver. O CI
transformou uma pendência abstrata em obstáculo concreto.

### Detalhes que valem lembrar

- **`npm ci`, não `npm install`:** instala exatamente o que o lockfile fixa e
  falha se o `package.json` divergir. É a "CI por lockfile" que a trilha pede.
  Python não tem equivalente direto; o `requirements.txt` com `==` em tudo dá a
  mesma garantia por outro caminho.
- **Nenhum venv no CI.** O runner é descartável, então o isolamento já existe —
  e isso contorna os shebangs quebrados do `.venv` local, que forçam
  `python3 -m` aqui.
- **Versão de ação é código de terceiros.** `@v4` gerou aviso de Node 20
  depreciado nos dois repos; subiu para `@v5`/`@v6`.
- **Runtime fixado ao local** (Node 24, Python 3.9): um CI noutra major
  verificaria algo que ninguém executa.

### O que fica em aberto

**O CI não bloqueia nada.** Ele reporta, mas ainda é possível empurrar para a
`main` com o CI vermelho. Tornar o check obrigatório é **branch protection**,
configuração de painel (Settings → Branches → *Require status checks to
pass*), não do YAML — e não pode ser feita por linha de comando pelo agente.
Enquanto não estiver ligada, o portão avisa mas não tranca.

### O que lembrar

- O runner começa vazio. `checkout` sempre primeiro.
- Ordem barata→cara; o job para no primeiro erro.
- Um portão que nunca foi visto falhando não é um portão.
- **Leia o código de saída, não a linha bonita.** Vale para `pylint`, e é a
  razão de o CI achar em 54 s o que meses de leitura humana não acharam.
- O CI é a fonte da verdade porque parte do zero: sem `.env`, sem `.venv`, sem
  cache local, sem o que a sua máquina acumulou.

### Verificação

| Repositório | Execução | Resultado |
|---|---|---|
| `Refund-FrontEnd` | inicial | ✓ 2m15s |
| `Refund-FrontEnd` | erro de tipo deliberado | **✗ 23s, no typecheck** |
| `Refund-FrontEnd` | revert + ações v5 | ✓ 2m11s, sem avisos |
| `Refund-api` | inicial | **✗ 54s, no pylint** |
| `Refund-api` | depois da extração | ✓ 1m7s |
| `Refund-api` | `setup-python@v6` | ✓ sem avisos |

Local, depois da mudança: `pytest` **235 passed**, `pylint src` **10.00/10 com
exit 0 pela primeira vez**. Frontend inalterado (287 testes, `tsc` 0, lint
0/0).

## Item 17 — Configuração tipada com pydantic-settings (2026-08-07)

**Status:** concluído em 2026-08-07, na branch `feat/typed-settings` do
`Refund-api`. Primeiro item da **Fase 4**. Os Itens 18 e 20 já haviam sido
feitos fora de ordem, no ciclo do workflow de aprovação.

### Por que estudar

Configuração é **entrada externa**, exatamente como o corpo de uma requisição.
O projeto já tratava entrada externa com rigor em dois lugares — Pydantic nos
validators, Zod nas fronteiras do frontend — e tratava a configuração como um
dicionário de strings cruas, sem nenhuma checagem.

### Estado anterior

```python
# src/configs/__init__.py
from dotenv import load_dotenv
load_dotenv()

# src/configs/global_config.py
database_info = {"DATABASE_URL": os.getenv("DATABASE_URL")}
jwt_info = {
    "KEY": os.getenv("JWT_SECRET"),
    "ALGORITHM": os.getenv("JWT_ALGORITHM", "HS256"),
    "EXPIRATION_TIME": int(os.getenv("JWT_EXPIRATION_HOURS", "8")),
}
```

Mais uma configuração fora dali, escrita direto no código:

```python
# src/main/server/server.py:23
allow_origins=["http://localhost:5173"],
```

### A limitação, medida e não deduzida

Os dois modos de falha foram **executados** antes de escrever qualquer linha:

| Cenário | Comportamento anterior | Quando aparecia |
|---|---|---|
| `JWT_SECRET` ausente | `TypeError: Expected a string value` | no **primeiro login de um usuário** |
| `DATABASE_URL` ausente | `ArgumentError: Could not parse SQLAlchemy URL` | no import, culpando a URL, não a variável |

A primeira linha é a que justifica o item sozinha. **A aplicação subia saudável
sem o segredo de assinatura**: `/health` respondia `ok`, a listagem funcionava,
e o sistema só quebrava quando alguém tentava entrar. É o modo de falha mais
caro que existe — o que passa pela verificação e falha na frente do usuário.

O `str(None)` da segunda linha é a armadilha mais sutil das duas: a variável
ausente não vira `None`, vira a **string literal `"None"`**, e a partir daí o
erro fala de sintaxe de URL. A mensagem aponta para o lugar errado.

### Estado ajustado

```python
class Settings(BaseSettings):
    environment: Literal["local", "test", "production"] = "local"
    database_url: Annotated[str, Field(min_length=1)]
    jwt_secret: Annotated[SecretStr, Field(min_length=1)]
    jwt_expiration_hours: Annotated[int, Field(gt=0)] = 8
    cors_origins: Annotated[List[str], NoDecode] = ["http://localhost:5173"]
```

A mudança observável, com `JWT_SECRET` ausente:

```
ANTES  → app sobe; 500 no primeiro login: "Expected a string value"

DEPOIS → app não sobe:
         ValidationError: 1 validation error for Settings
         jwt_secret
           Field required [type=missing]
```

### Cinco coisas aprendidas

**1. `Annotated[T, Field(...)]` não é estilo, é o que faz a análise estática
funcionar.** A primeira versão usava `jwt_secret: SecretStr = Field(min_length=1)`.
Roda igual, mas o `pylint` reprovou com quatro `E1101: Instance of 'FieldInfo'
has no 'get_secret_value' member` — ele infere o tipo do atributo pela
**atribuição**, não pela anotação. Mover a constraint para dentro do
`Annotated` remove a atribuição e o tipo volta a ser o declarado.

**2. `SecretStr` compra um modo de falha a menos.** `repr(settings)` imprime
`SecretStr('**********')`, então um traceback que inclua o objeto de
configuração não vaza a chave de assinatura. O custo é um `.get_secret_value()`
explícito nos dois pontos que realmente precisam do valor — o que é uma
vantagem, não um imposto: marca no código onde o segredo circula.

**3. Um default de ambiente pode ser uma decisão de segurança.** `environment`
tem default `local`, nunca `production`. Isso é o que garante que a guarda de
CORS não possa ser pulada por **omissão** — esquecer a variável não pode ser o
caminho que desliga a proteção.

**4. `NoDecode` existe porque o default do pydantic-settings é JSON.** Para um
campo de tipo complexo (`List[str]`), a biblioteca roda `json.loads` no valor
cru da variável. Sem `NoDecode`, `CORS_ORIGINS` teria de ser escrito como
`["http://a","http://b"]` num arquivo `.env` — válido, e uma armadilha para
qualquer humano editando. Com ele, um `field_validator(mode="before")` assume o
parsing e o arquivo continua separado por vírgula.

**5. A premissa que eu tinha errado, e que o próprio projeto ensina a
desconfiar.** O plano afirmava que tornar o engine preguiçoso permitiria
remover as variáveis fictícias do `ci.yml`. **Não permitiria.** Conferindo os
testes antes de implementar, dois deles exigiam configuração real no import por
motivos que nada tinham a ver com o engine: `database_connection_handler_pool_test.py`
importava o `engine` global, e `jwt_handler_test.py` usava `jwt_info["KEY"]`. É
exatamente o padrão que o `current-state.md` já registra para riscos herdados —
**a premissa deve ser reverificada, não repetida com mais convicção.**

### Engine preguiçoso

O `create_async_engine` no nível do módulo era o que obrigava qualquer import a
ter uma `DATABASE_URL` parseável. A separação:

```python
def build_engine(connection_string: str) -> AsyncEngine:
    return create_async_engine(connection_string, pool_size=5, ...)

@lru_cache(maxsize=1)
def get_engine() -> AsyncEngine:
    return build_engine(settings.database_url)
```

`lru_cache(maxsize=1)` numa função sem argumentos é a forma simples de dizer
"construa uma vez, na primeira chamada". Não precisa de lock: as funções não
têm `await`, então o event loop não consegue intercalar dois chamadores no meio
e construir dois engines.

Efeito colateral bom: o teste de pool ficou **melhor**. Ele passou a chamar
`build_engine("postgresql+asyncpg://test:test@localhost:5432/test")` com URL
literal — testa a tunagem de pool, que é o assunto dele, sem depender de qual
banco a aplicação por acaso aponta.

**A dívida que o engine preguiçoso cria, encontrada por uma pergunta e não
por um teste.** Construir o engine no import era, sem se propor a isso, a
**única coisa que parseava a `DATABASE_URL`**. Adiá-lo adiou junto essa
verificação:

```
DEPOIS DO ENGINE PREGUIÇOSO, ANTES DA CORREÇÃO
  DATABASE_URL="isto-nao-e-uma-url"  →  a app SOBE, e dá 500 na 1ª requisição
```

Ou seja: o item melhorou o `JWT_SECRET` e **piorou** a `DATABASE_URL`,
reintroduzindo pela porta dos fundos exatamente o modo de falha que ele existe
para eliminar. Isso só apareceu porque o Gabriel pediu uma explicação mais
funda do engine preguiçoso e a explicação exigiu testar a afirmação.

A correção não foi voltar atrás no engine: foi um `field_validator` chamando
`sqlalchemy.engine.make_url` na fronteira de configuração, que só parseia — sem
pool, sem rede. A URL malformada volta a impedir o startup, nomeando o campo.

**A lição generaliza:** adiar trabalho para depois do import adia junto as
validações que aquele trabalho fazia por acidente. Antes de tornar algo
preguiçoso, perguntar o que aquele código verificava sem se propor a verificar.

**Um teste tentado e abandonado:** uma rede de proteção para o `lock_timeout`
em `connect_args`. O SQLAlchemy só aplica `connect_args` quando abre uma
conexão de verdade, então um engine que nunca conecta não os expõe em lugar
nenhum alcançável. Abandonado em vez de alcançado por internals do pool; a
prova daquele parâmetro continua sendo o `SHOW lock_timeout` manual.

### Onde a configuração de teste passou a morar

O `ci.yml` declarava `DATABASE_URL` e `JWT_SECRET` fictícias, com um comentário
que corretamente as chamava de sintoma. Elas foram para o `conftest.py` da
raiz — o único hook que roda cedo o bastante, porque o pytest importa o
conftest da rootdir antes de qualquer módulo de teste.

Duas propriedades que isso ganha de graça: a suíte roda para quem clonou o
projeto e não tem `.env`; e como variável de ambiente tem precedência sobre o
`.env` no pydantic-settings, a suíte **não consegue alcançar o banco real por
acidente**, nem numa máquina com `.env` de produção configurado.

### Verificação

| Verificação | Resultado |
|---|---|
| `pytest` | **249 passed** (partiu de 235; 14 novos em `settings_test.py`) |
| `pylint src; echo $?` | 10.00/10, **exit 0** |
| Importar a app sem nenhuma config | `ValidationError` nomeando `database_url` **e** `jwt_secret` |
| Importar com só `DATABASE_URL` | `ValidationError` nomeando `jwt_secret` — o cenário que antes subia saudável |
| `pytest` com o `.env` escondido | **249 passed** — as variáveis do CI são de fato desnecessárias |
| `DATABASE_URL` malformada | **não sobe**, nomeando `database_url` (regressão achada e corrigida) |
| App real: `/health` | `{"status":"ok"}` |
| CORS `Origin: http://localhost:5173` | header devolvido |
| CORS `Origin: https://evil.example.com` | sem header |
| Registro + login + rota autenticada | 201 → token de 3 partes → **200** |
| `ENVIRONMENT=production` + origem localhost | **não sobe**, com a mensagem da guarda |
| `ENVIRONMENT=production` + origem real | sobe |
| `alembic current` | `f76d3be18936 (head)` |

### O que lembrar

- Configuração é entrada externa. Validar no startup transforma um 500 na
  frente do usuário em uma mensagem de erro para quem está implantando.
- **Um default pode ser uma decisão de segurança.** `environment` defaulta para
  `local` para que esquecer a variável nunca desligue a guarda.
- Constraint de Pydantic vai em `Annotated[T, Field(...)]`, não em
  `= Field(...)`, ou a análise estática perde o tipo.
- Antes de implementar, **reverificar a premissa** que justifica o passo — a
  deste plano estava errada e só a leitura dos testes mostrou.
- **Tornar algo preguiçoso adia as validações que aquele código fazia por
  acidente.** O engine parseava a URL sem se propor a isso; adiá-lo abriu um
  buraco que só fechou quando a checagem foi para a fronteira de configuração.
- Uma pergunta do tipo "me explica melhor" encontrou um defeito que três
  rodadas verdes de suíte e doze cenários manuais não encontraram. Explicar
  obriga a verificar o que se afirma.

## Item 19 — PostgreSQL como referência de produção (2026-08-07)

**Status:** concluído em 2026-08-07, na branch `feat/integration-tests` do
`Refund-api`. Segundo item da Fase 4.

### A premissa escrita na trilha estava morta

O `learning_path.md` descreve o item assim: *"`asyncpg` está instalado, mas o
README orienta SQLite local."* **Não orienta mais.** `grep -rni "sqlite"` no
`README.md`, em `src/`, `alembic/` e `docs/` (fora do diário) não devolve nada
além de registro histórico — a migração para o Neon aconteceu meses atrás e
está na ADR-002.

Sobrou um resíduo que ninguém tinha notado: **`aiosqlite==0.22.1` no
`requirements.txt`, importado por nenhum arquivo.** Removido.

Metade do item já estava feita, então o item virou a outra metade: *"PostgreSQL
em container para integração"*.

### A limitação, e por que ela já custou caro duas vezes

Os 249 testes rodam contra mocks. O `conftest.py` dos repositories monta um
`MagicMock` e cada teste configura o que ele deve devolver:

```python
execute_result.inserted_primary_key = [1]
db.session.execute = AsyncMock(return_value=execute_result)
```

Isso prova que o repository **monta** o SQL certo. Nunca que o PostgreSQL o
**aceita**, nem o que ele faz com ele. Mesma limitação que o MSW impõe ao
frontend, e que este projeto já nomeou: *"a suíte roda contra o payload que nós
mesmos escrevemos."*

Dois bugs escaparam exatamente por aí, ambos achados só com banco real:
o **singleton de sessão** do `DatabaseConnectionHandler` (500 e vazamento de
conexão sob concorrência) e o **`paid` não terminal**, registrado no diário
como "invisível à suíte mockada".

### O que cada nível alcança

| Falha | Mock | Postgres real |
|---|---|---|
| Repository monta o SQL errado | ✅ | ✅ |
| Migration não aplica / `downgrade` quebra | ❌ | ✅ |
| `UNIQUE` de e-mail | ❌ | ✅ |
| FK para usuário inexistente | ❌ | ✅ |
| `server_default` do schema | ❌ | ✅ |
| `lock_timeout` chegou ao servidor | ❌ | ✅ |
| `FOR UPDATE` sob contenção | ❌ | ✅ |

### Seis coisas aprendidas

**1. A separação por marker é o que mantém a suíte rápida viável.** `pytest.ini`
traz `addopts = -m "not integration"`, então `pytest` continua sendo 249 testes
em 4,2s sem Docker, e `pytest -m integration` roda os 19 novos — um `-m` na
linha de comando é parseado depois do `addopts` e o sobrescreve. Ninguém é
obrigado a instalar Docker para trabalhar no projeto.

**2. O container tem de ser a mesma versão maior que produção.** Perguntei ao
Neon (`show server_version`): **18.4**. O container é `postgres:18-alpine`.
Testar contra outra maior anularia o item — as diferenças que ele existe para
expor são justamente as que variam entre versões.

**3. A imagem 18 mudou o ponto de montagem, e isso custou uma partida
falhada.** Todo exemplo anterior a 18 usa `/var/lib/postgresql/data`; a 18 move
os dados para um subdiretório com o nome da versão, para o `pg_upgrade`
funcionar através do mount. Montar o caminho antigo faz o container **recusar a
subir**, com "there appears to be PostgreSQL data in /var/lib/postgresql/data
(unused mount/volume)". O `tmpfs` correto é `/var/lib/postgresql`.

**4. Escrevi testes contra interfaces que supus, e o banco real me corrigiu
três vezes.** Em ordem:
- `select_user_by_email` devolve `dict`, não objeto com atributos;
- `select_refunds` devolve **tupla** `(rows, total, sum)`, não dicionário;
- `insert_user` **captura** o `IntegrityError` e levanta `HttpBadRequestError`,
  enquanto `insert_refund` **não captura** — a FK propaga crua. Duas
  repositories, dois contratos de erro diferentes, coisa que só um banco de
  verdade mostra.

E a quarta correção foi de camada: `count_by_status` é um `GROUP BY`, então só
devolve status **que têm linhas**. A garantia das quatro chaves do `UC-014`
mora no `RefundStatsFinderController`, não no repository. Meu teste afirmava na
camada errada; virou um teste que documenta onde a garantia realmente está.

**5. Um teste de concorrência não precisa ser uma corrida.** A pendência falava
em "N operações concorrentes", que é a categoria mais propensa a flake — e este
projeto já pagou caro com o flake do `ResizeObserver`. O desenho adotado é
determinístico: uma transação **toma o lock deliberadamente e segura**, a outra
tem um único desfecho possível. Não há nada a ganhar ou perder.

**6. Um teste que trava na regressão é pior que teste nenhum.** A primeira
versão do teste de contenção passava, mas se o `lock_timeout` sumisse ela
**travaria para sempre** em vez de falhar. Corrigido com `asyncio.wait_for`: sem
o parâmetro, o `TimeoutError` não é `DBAPIError` e o `pytest.raises` reporta
falha em 15s. Provado por quebra deliberada.

### O portão foi visto fechando

Não basta os testes passarem — o projeto já registrou isso três vezes. Removi o
`connect_args` do `build_engine` de propósito:

```
com lock_timeout removido   → 2 failed, 2 passed in 15.54s
restaurado                  → 4 passed in 3.36s
```

Os 15,5s são a guarda do `wait_for` funcionando: falhou, não travou.

### Verificação

| Verificação | Resultado |
|---|---|
| `pytest` (3 rodadas) | **249 passed, 19 deselected**, 4,2s |
| `pytest -m integration` (3 rodadas) | **19 passed**, 4,66s |
| `pylint src; echo $?` | 10.00/10, **exit 0** |
| Quebra deliberada do `lock_timeout` | **2 failed** em 15,5s, sem travar |
| Sem o container de pé | 19 erros com "Is it up? Run: docker compose up -d" |
| Suíte rápida sem o container | **249 passed** — imune |
| `show server_version` (container) | 18.4, igual ao Neon |

### O que lembrar

- **Mock prova que o SQL é montado; só o banco prova que ele é aceito.** As
  duas suítes são complementares, não redundantes.
- Testar migration em SQLite seria pior que não testar — esconderia justamente
  o que se quer ver.
- **Reverificar a premissa do item antes de implementá-lo.** A deste estava
  desatualizada, e metade do trabalho já existia.
- Um teste de concorrência bem desenhado não tem corrida, e um teste que pode
  travar precisa de uma guarda de tempo.

## Item 21 — Consistência entre banco e arquivo (2026-08-07)

**Status:** concluído em 2026-08-07, na branch `feat/file-consistency` do
`Refund-api`. Terceiro item da Fase 4 nesta sessão.

### O conceito

Uma transação SQL cobre o banco. Ela **não** cobre o disco, o S3, o envio de
e-mail. Quando uma operação toca os dois, "ou tudo ou nada" deixa de ser
automático e vira código que alguém escreve. O padrão é a **ação
compensatória**: se o segundo passo falha, desfaça o primeiro.

### O levantamento mudou o tamanho do item

A trilha fala de dois lugares (criação e exclusão de reembolso). São **cinco**:

| Call site | Ordem | Antes |
|---|---|---|
| `RefundCreatorController.create` | `save()` → `insert` | nenhuma compensação |
| `AvatarUploaderController.upload` | `save()` → `update` | nenhuma compensação |
| `RefundDeleterController.delete` | `DELETE` → `storage.delete()` | nenhuma |
| `AvatarRemoverController.remove` | `update` → `storage.delete()` | nenhuma |
| `RefundPayerController.pay` | `save()` → transação | **completa** |

**A ordem já estava certa nos cinco** — isso não foi tocado. O criador salva
antes de inserir porque a linha precisa do `filename`; o deletador apaga o
arquivo depois porque apagar antes destruiria o comprovante de um reembolso que
sobreviveu a uma corrida perdida. Tudo comentado no código e deliberado.

O que faltava era o tratamento da falha. E o pagamento **já tinha a solução
pronta**, escrita e revisada — o item virou "aplicar aos quatro que ficaram
para trás", não "inventar".

### Duas falhas, não uma

**A — arquivo órfão** (criação, upload de avatar). Insert falha, arquivo fica.
Não é hipotético: sete órfãos já foram achados e removidos à mão neste projeto.

**B — 500 numa operação que deu certo** (exclusão de reembolso e de avatar).
Esta ninguém tinha nomeado:

```python
deleted_count = await repository.delete_refund(refund_id)   # ✅ commitado
...
self.__receipt_storage.delete(refund["filename"])           # ❌ os.remove levanta
```

A linha já foi apagada, mas a exceção sobe e a view devolve **500**. O usuário
tenta de novo e recebe **404**. A operação funcionou; a resposta mentiu.

### A regra, e por que ela é assimétrica

```
ANTES do commit  →  desfaça   (o arquivo não tem dono)
DEPOIS do commit →  registre  (o dado durável manda; o arquivo é secundário)
```

Derrubar uma resposta correta por causa de um arquivo sobrando troca um problema
pequeno por um grande.

### A fronteira que quase passou despercebida

O `insert_refund` **dá commit**. Então a compensação da criação cobre **apenas o
insert** — se a releitura seguinte falhar, o arquivo **não** pode ser apagado,
porque já existe uma linha real apontando para ele. Estender o `try` uma linha a
mais transformaria a correção num bug pior que o original.

É a mesma fronteira que o `RefundPayerController` já marcava com sua flag
`committed`. Há um teste dedicado a ela, e ele **falha** quando o `try` é
esticado — verificado.

### A primeira linha de log do projeto

`src/controllers/file_cleanup.py` centraliza a deleção best-effort. Ela engole a
própria falha por dois motivos diferentes conforme o caso (não mascarar a
exceção em voo; não quebrar uma resposta de sucesso) e emite um
`logging.warning` com o nome do arquivo.

`logging` é stdlib — nada instalado. O Item 24 depois troca a **configuração**
(formatter JSON, `request_id`) e estas chamadas passam a sair estruturadas; elas
provavelmente serão **refinadas** para mover o filename da frase para um campo
próprio, mas não precisam esperar por isso para deixar rastro.

Centralizar também evitou três cópias do mesmo `try/except/pass` — e `R0801`
(duplicate-code) já reprovou este projeto uma vez.

### Quatro quebras deliberadas

Passar não é prova:

| Quebra | Resultado |
|---|---|
| Remover a compensação da criação (unit) | 1 failed |
| `delete_quietly` voltar a propagar | **6 failed** em 4 arquivos |
| Esticar o `try` para depois do commit | 2 failed, inclusive o teste da fronteira |
| Remover a compensação (integração) | 1 failed, **mostrando o órfão pelo nome** |

A última é a mais convincente. A saída da falha traz
`assert ['ce2180ea-0b...9fd29b16.png'] == []` — o bug reproduzido ponta a ponta,
com PostgreSQL recusando a FK e um arquivo real sobrando no disco.

Essa evidência **não era possível antes do Item 19**. "Não sobrou arquivo" só
era verificável listando o diretório à mão.

### Verificação

| Verificação | Resultado |
|---|---|
| `pytest` (3 rodadas) | **258 passed, 23 deselected** (partiu de 249) |
| `pytest -m integration` (3 rodadas) | **23 passed** (partiu de 19) |
| `pylint src; echo $?` | 10.00/10, **exit 0** |
| 4 quebras deliberadas | todas pegas pelos testes certos |

### O que lembrar

- **Transação não cobre efeito externo.** Se a operação toca dois sistemas,
  a compensação é código, não configuração.
- **A compensação termina no commit, não no fim do método.** Passar disso
  destrói dado real.
- **Antes do commit desfaça; depois do commit registre.** Um arquivo sobrando é
  menos grave que uma resposta errada.
- Um `SIGKILL` entre o `save()` e o commit continua descoberto — isso exige
  varredura ou fila (Item 28), não compensação em processo.

## Item 22 — Object storage e URLs assinadas (2026-08-07)

**Status:** concluído em 2026-08-07, em **dois repositórios**:
`feat/object-storage` no `Refund-api` e `feat/signed-file-urls` no
`Refund-FrontEnd`. **Nenhuma das duas mesclada.** Quarto item da Fase 4 nesta
sessão, e o maior dela.

### Duas metades, e a segunda foi escolha do Gabriel

Eu recomendei fazer só object storage e adiar as URLs assinadas para um ciclo
próprio. Ele escolheu incluir as duas. A recomendação estava baseada em "URL
assinada é otimização, não correção de perda de dado" — o que continua
verdadeiro, mas as duas juntas evitaram uma migração de contrato em dois
passos.

### O terreno já estava preparado

`read() -> bytes` (e não `-> str` com um caminho) foi escrito no ciclo de
arquivos autenticados com um comentário explícito: *"a path would assert that
the file lives on a local filesystem, which is exactly the claim the
object-storage item (22) will invalidate."*

Resultado: `S3FileStorage` entrou sem tocar em **nenhum** controller. Os oito
composers trocaram `FileStorage(settings.upload_dir)` por
`build_storage("receipts")`.

### O problema que a escolha das URLs assinadas abriu

O motivo de existir URL assinada é `<img src={url}>` funcionar **sem header**.
Mas o `FileStorage` local não tem servidor que assine por ele. Três saídas:

| Opção | Problema |
|---|---|
| Só S3 devolve URL | **Dois contratos** — dev testa uma coisa, produção roda outra |
| Só existe S3 | A aplicação passa a exigir Docker para rodar |
| Assinar também no local | Código a mais |

Escolhida a terceira, e ela saiu barata **porque o projeto já assina**: um JWT
de vida curta com `(storage, filename)`, servido por
`GET /files/{storage}/{filename}`. Mesmo `jwt_secret`, mesmo `JwtHandler`.
Nenhuma criptografia nova, nenhuma dependência nova.

### O achado que só apareceu ao fazer o frontend

Eu tinha feito as rotas devolverem só `{"url": ...}`. Ao migrar o
`ReceiptPreview`, apareceu que ele decide `<img>` vs `<object>` por
`blob.type` — **e uma URL não carrega tipo**. Sem `media_type` na resposta, o
cliente teria que adivinhar pela extensão da URL.

Corrigido no backend antes de continuar: a resposta é
`{"url", "media_type"}`. A regra que sobreviveu inteira é a que importa — o
tipo vem da extensão armazenada, **nunca** de um cabeçalho do cliente.

**A lição é sobre ordem de trabalho:** fazer o backend inteiro antes de olhar o
consumidor escondeu um campo faltando por três horas de implementação.

### O trade-off de segurança, declarado

A rota autenticada **reconferia a autorização a cada requisição**. A URL
assinada **congela a decisão** no momento em que é gerada. Quem copiar o link
mantém acesso até expirar.

O que torna isso aceitável, e diferente da URL pública que a ADR-003 removeu, é
o prazo: **300 segundos** contra "para sempre". E a autorização em si não mudou
de lugar — os controllers continuam decidindo dono-ou-admin antes de qualquer
URL existir.

### Um comportamento perdido de propósito

Os controllers não leem mais o arquivo, então "a linha sobreviveu mas o arquivo
sumiu" deixou de ser 404 ali. O `payment-receipt` tinha **quatro** caminhos de
404 idênticos verificados byte a byte; o quarto mudou de lugar. Os três que
importam seguem intactos — são os que vazariam a existência de um reembolso.
Restaurar o quarto custaria um `HEAD` por URL contra o S3, que é a maior parte
do que o item economiza.

### Quatro coisas aprendidas

**1. `services:` do GitHub Actions não sobrescreve o `command` da imagem.** O
MinIO precisa de `server /data` para subir. Escrevi primeiro um bloco
`services:` com `--entrypoint sh` e um comentário afirmando que funcionava —
não funcionaria, subiria um shell que sai na hora. Trocado por `docker run`
num step, que é verificável.

**2. Porta 9000 é disputada.** Já estava ocupada na primeira máquina. MinIO foi
para 9100/9101, mesmo raciocínio que levou o Postgres para 5433.

**3. `staleTime` precisa ser menor que o TTL da URL.** O default global do
projeto é 30s, o TTL é 300s — nesse caso específico o default já bastaria, mas
fixar 150s explicitamente é o que impede que uma mudança futura no default
entregue uma URL vencida. **O sintoma seria uma imagem quebrada sem erro
nenhum na camada de dados**, que é o pior tipo.

**4. Código morto com comentário justificando existe.** O `useObjectUrl` dizia
morar na camada compartilhada *"porque o ciclo da foto de perfil vai precisar
do mesmo comportamento"*. Deixou de ser verdade no mesmo commit — avatares
também viram URL. Apagado, com o teste junto: deixá-lo mandaria o próximo
leitor por um caminho que não existe mais.

### Verificação

| Verificação | Resultado |
|---|---|
| `pytest` | **277 passed, 32 deselected** (partiu de 261) |
| `pytest -m integration` | **32 passed** (partiu de 23) |
| `pylint src; echo $?` | 10.00/10, **exit 0** |
| `npx vitest run` (3 rodadas) | **283 passed em 51 arquivos** |
| `npx tsc -b --noEmit` | exit 0 |
| `npm run lint` | 0 erros, 0 warnings |
| `npm run build` | ok, 606,92 → **607,87 kB** |
| Quebra: remover a checagem token↔arquivo | 2 failed |
| Quebra: remover a guarda de path traversal | 1 failed |

Os testes de integração baixam uma presigned URL com **urllib** — que não sabe
nada de AWS, então se funciona ali funciona num `<img>` —, confirmam que o
mesmo objeto é **recusado sem a assinatura**, e confirmam que a URL **expira**.

### O que NÃO foi verificado

**Nada disso foi visto num navegador.** É o item em que essa lacuna mais pesa:
o ponto inteiro é uma URL carregar numa tag `<img>` sem header, e a suíte roda
contra MSW — o payload que nós mesmos escrevemos. Ver pendências.

E o **CORS do bucket**: uma implantação com S3 precisa liberar o domínio do
frontend no provedor, ou o navegador bloqueia o download cross-origin. É
configuração de painel, não código, e o startup não tem como verificar.

### O que lembrar

- **Uma boa interface paga juros.** `read() -> bytes` foi escrito dois ciclos
  antes pensando neste item, e por isso nenhum controller foi tocado.
- **Olhe o consumidor antes de declarar o contrato pronto.** O `media_type`
  faltando só apareceu ao migrar a tela.
- URL assinada troca "reconferido sempre" por "válido por N segundos". O
  prazo é a decisão inteira.

## Item 23 — Erros padronizados com Problem Details (2026-08-08)

**Status:** concluído em 2026-08-08, em dois repositórios:
`feat/problem-details` no `Refund-api` e no `Refund-FrontEnd`.

### A limitação

Duas formas para a mesma coisa — `detail` string nos nossos erros, `detail`
lista na validação do FastAPI — e no frontend uma função existindo só para
distinguir as duas, consumida por 7 telas.

A pior consequência não era a duplicação, e sim: **mensagem é texto de UI, e
texto de UI não pode ser chave de lógica.** Para tratar "já foi pago por outro
admin" diferente de "só um aprovado pode ser pago" — ambos 422 — a UI teria que
comparar strings. O projeto acabou de traduzir a interface inteira no Item 14.

### A decisão que fez o item ser barato

**Três handlers globais, zero dos 38 raise sites tocados.** O formato passou a
ser decidido num lugar; quem levanta continua levantando o mesmo. Se algum
`raise` tivesse precisado mudar, seria sinal de que o desenho estava errado.

E a compatibilidade saiu de graça, por uma propriedade da própria RFC:
**`detail` é string nela também**. Então o ramo `typeof detail === "string"` do
frontend continuou funcionando durante toda a migração — inclusive para os
erros de validação, que antes caíam no ramo da lista. **A migração não teve
momento quebrado.**

### Três coisas aprendidas

**1. `@app.exception_handler(HTTPException)` não pega o 404 do router.** A
`HTTPException` do FastAPI é subclasse da do Starlette. Registrar na subclasse
cobre só o que o nosso código levanta; o router levanta a **base** para rota
desconhecida, e esses 404 escapavam com o formato antigo.

Descoberto **perguntando à API rodando** por `/nao-existe`, não lendo código. E
o mais importante: **reintroduzir esse bug não faz nenhum teste falhar** — os
testes chamam os handlers direto, então provam o mapeamento exceção→envelope,
não o registro. Está registrado como limitação no próprio arquivo de teste e
nas pendências.

**2. O `request_id` estava no corpo do 500 e não no header.** Verificado, não
suposto: numa exceção não tratada, ela sobe **passando pelo
`RequestIdMiddleware`** antes de a camada mais externa do Starlette invocar o
handler — então `call_next` nunca retorna e o header nunca é acrescentado. O
corpo tinha o id porque o middleware grava em `request.state` **antes** de
chamar adiante.

Justo na resposta em que alguém mais quereria copiar o id. A correção não foi
mexer na ordem dos middlewares: foi o **próprio envelope** marcar a resposta,
o que torna o comportamento independente de ordenação.

**3. Código morto com comentário é pior que código morto.** O ramo da lista no
`getApiErrorMessage` foi removido, e o comentário novo diz que ele foi removido
**por estar morto**, não por ter deixado de ser necessário — mantê-lo sugeriria
que a API ainda pode responder daquele jeito.

### Verificação

| Verificação | Resultado |
|---|---|
| `pytest` | **295 passed, 32 deselected** (partiu de 277) |
| `pylint src; echo $?` | 10.00/10, **exit 0** |
| `npx vitest run` (3 rodadas) | **289 passed** (partiu de 283) |
| `tsc` / `lint` / `build` | 0 / 0-0 / ok (607,81 kB) |
| API real: 4 caminhos | 400 de negócio, 422 de validação, 404 de rota inexistente, **500 real** — todos com envelope e `X-Request-Id` |
| Quebra: `detail` volta a ser lista | 1 failed |
| Quebra: 500 vaza a mensagem original | 1 failed |
| Quebra: handler na subclasse do FastAPI | **0 failed — a suíte NÃO pega** |

A terceira linha de quebra é a mais honesta da tabela: ela documenta o que a
suíte **não** cobre.

### O que lembrar

- Registrar handler na **classe base** da exceção, não na subclasse.
- **Verifique contra o processo rodando** o que depende de ordem de middleware
  ou de registro — ler o código não mostra nem uma coisa nem outra.
- Uma migração de contrato sem momento quebrado vale muito, e às vezes ela sai
  de graça se o formato novo for escolhido com o antigo em mente.

## Item 24 — Logs estruturados e request ID (2026-08-09)

**Status:** concluído em 2026-08-09, na branch `feat/structured-logs` do
`Refund-api`. Só backend. Detalhes de decisão na
[ADR-006](../decisions/ADR-006-structured-logging.md).

### O estado anterior, medido

Uma chamada de log no projeto inteiro e **zero configuração**, então tudo caía
no `lastResort` do Python: sem hora, sem nível, sem nome do logger. E uma linha
`INFO` era **descartada em silêncio**, porque o `lastResort` corta abaixo de
`WARNING`.

Havia uma promessa pendente do Item 23: ele pôs um `request_id` no corpo de
todo erro dizendo que casaria com um log. Não casava com nada.

### Por que `contextvar` e não parâmetro

`request.state` serve para quem tem o `Request`. Uma linha de log não tem: o
`file_cleanup.py` loga de dentro de um controller, **quatro camadas abaixo da
rota**. Passar o request por essas camadas até um logger seria a forma errada
do problema.

`contextvar` é a ferramenta para "valor ambiente durante esta tarefa". E o
`logging.Filter` é o que garante que **toda** linha o carregue — uma linha que
só às vezes tem o id é quase tão ruim quanto nenhuma, porque não dá para
distinguir "outra requisição" de "alguém esqueceu".

**A dúvida real era se o contextvar atravessa o `BaseHTTPMiddleware`**, que roda
o app downstream em outra task. Atravessa, porque a task copia o contexto no
momento em que é criada e nós gravamos antes de chamar adiante. **Verificado
contra a API rodando**, comparando o `X-Request-Id` do header com o id da linha
de log: iguais.

### O mascaramento tinha alvo concreto

Não é higiene abstrata. O Item 22 serve arquivos por URL assinada:

```
/files/receipts/a3f2.png?token=eyJhbGciOi...
```

Um log de acesso ingênuo grava isso inteiro — **uma credencial funcionando, com
carimbo de hora, num arquivo que sobrevive anos aos cinco minutos do token**.

E é por isso que o access log do uvicorn foi silenciado: ele grava a query
crua. Decisão de segurança, não de estética.

### Duas coisas que só a saída real mostrou

**1. `token=%2A%2A%2A`.** O `urlencode` percent-encodava a máscara. Ilegível e
esconde a intenção. `safe="*"` resolve.

**2. `color_message` vazando com escapes ANSI.** O uvicorn anexa aos próprios
records a mesma mensagem colorida. Minha regra "tudo que não é campo padrão é
extra do usuário" pegava isso e cuspia `\x1b[32m` no log.

Nenhuma das duas apareceria lendo o código.

### A quebra deliberada que não falhou

Três quebras. Duas pegas na hora:

| Quebra | Resultado |
|---|---|
| Mascaramento desligado | **6 failed** |
| `uvicorn.access` volta a logar | 1 failed |
| **Filtro do `request_id` removido** | **0 failed** ← |

A terceira expôs uma lacuna real: meus testes chamavam `RequestIdFilter().filter()`
direto, provando que o filtro **funciona**, e nenhum provava que ele está
**instalado** no handler. São afirmações diferentes, e só a segunda era o risco.
Acrescentei o teste; a quebra passou a falhar.

**É a mesma classe de lacuna do Item 23** (handler registrado na exceção
errada, invisível para a suíte). Duas vezes seguidas o buraco foi "testei a
peça, não a montagem".

### Verificação

| Verificação | Resultado |
|---|---|
| `pytest` | **317 passed, 32 deselected** (partiu de 295) |
| `pylint src; echo $?` | 10.00/10, **exit 0** |
| API real, `ENVIRONMENT=production` | JSON parseável, uma linha por requisição |
| `X-Request-Id` do header vs. log | **iguais** |
| Token na query | `token=***`, zero ocorrências do valor |
| API real, `ENVIRONMENT=local` | linha humana, token também mascarado |

### O que lembrar

- **Testar a peça não é testar a montagem.** Duas vezes seguidas o defeito
  estava no registro/instalação, não na lógica.
- `contextvar` para valor ambiente; parâmetro para dependência.
- Log que grava query string precisa de mascaramento **antes** de existir uma
  URL assinada, não depois.
- Métricas e tracing ficaram de fora por instrução do item: entram quando
  existir onde observá-los.

## Sessão de validação em navegador — 2026-08-09

Não é um item da trilha: é a passada de navegador que três itens seguidos
ficaram devendo. Dezoito verificações num checklist derivado das pendências,
percorridas pelo Gabriel. **Todas passaram — e a sessão achou dois bugs**, que
é a justificativa retroativa para ela ter existido.

### Os dois bugs, e por que a suíte não podia vê-los

**1. A checagem de tipo do Zod roda antes das nossas mensagens.**

```
name: undefined  ->  "Invalid input: expected string, received undefined"
name: ""         ->  "validation.nameRequired"
```

`RefundFormDialog` e `PayRefundDialog` eram os **únicos** formulários sem
`defaultValues`. Um campo não tocado chegava como `undefined`, o Zod falhava no
**tipo** antes de alcançar o `.min(1, …)`, e a mensagem de tipo é o default em
inglês da biblioteca — **que nunca foi uma chave**, logo intraduzível por
construção, não por esquecimento. Um envio vazio produzia **quatro** de uma vez.

**2. Duas mensagens em português cravadas** em `PageLogin` e `PageRegister`,
enquanto o campo vizinho usava chave. Ficavam em português com a UI em inglês.

**A lição generaliza para além do i18n:** o Item 14 verificou que as mensagens
de validação estavam traduzidas, e estavam. Ninguém verificou se elas são
**alcançadas**. Um catálogo completo não prova que suas chaves chegam à tela —
e o teste de paridade do Item 14, que é bom, mede o catálogo, não o caminho.

**É a terceira vez seguida que o buraco tem essa forma.** Item 23: handler
registrado na exceção errada (testei o handler, não o registro). Item 24: filtro
correto mas não instalado (testei a peça, não a montagem). Agora: mensagem certa
mas inalcançável. Sempre a ligação entre as partes, nunca as partes.

### O texto nativo do input de arquivo

Pendência desde o restyle, decidida e resolvida aqui. O
`"Choose File / No file chosen"` pertence ao controle do navegador e **não é
alcançável por CSS nem por JS** — `::file-selector-button` estiliza o botão mas
não o renomeia. A única saída é substituir o controle.

Três detalhes que valem para qualquer controle nativo escondido:

- **`sr-only`, nunca `display:none`** — o segundo tira o input da árvore de
  acessibilidade e do foco.
- **`aria-labelledby`** fixa o nome acessível; sem isso o `<label>` visível é um
  **segundo** rótulo e o leitor de tela anuncia os dois concatenados.
- **O anel de foco migra** para o elemento visível, via `peer`.

### Duas correções ao próprio checklist

**A1 estava ambíguo.** Abrir o detalhe dispara **duas** requisições — a de
metadados (autenticada, devolve `{url, media_type}`) e a do arquivo. Só a
segunda prova o item, e eu não distingui. O Gabriel achou a primeira e ficou
sem entender o que verificar.

**A3 estava errado.** Eu escrevi que a tela cheia não devia gerar requisição
nenhuma — expectativa herdada da versão com `blob:`, em que uma segunda `<img>`
com a mesma string não tocava a rede. Com URL HTTP real, o diálogo monta um
segundo `<img>` e o navegador serve do cache; **é o comportamento correto**, e
é para isso que a rota manda `Cache-Control: private, max-age=60`.

Vale registrar: em 2 das 18 verificações o defeito estava **no checklist**, não
no produto. Quem escrever o próximo deve conferir a expectativa contra o código
atual, não contra a lembrança de como era.

### O número que não é sinal

O Lighthouse deu **Accessibility 100** (fecha a pendência de contraste, que era
o objetivo) e **Performance 54%**. O segundo **não deve ser citado**: a medição
foi contra `npm run dev` — módulos não minificados, sem bundling, com o cliente
de HMR no meio. Mede o servidor de desenvolvimento, não o produto. O assunto de
performance que existe de verdade é o bundle em ~608 kB com o aviso de chunk
> 500 kB aberto desde o restyle, e isso é o Item 31.

### O flick

Não reproduziu. Registrado como **não observado**, não como resolvido: ninguém
achou a causa, então pode ter mudado de condição. Se voltar, o caminho continua
sendo medir `scrollHeight` por frame — duas correções às cegas já falharam.

### O que lembrar

- **Validar no navegador acha o que a suíte não pode achar**, e desta vez o
  retorno foi concreto: dois bugs na tela mais usada do produto.
- **Um catálogo completo não prova que suas chaves chegam à tela.**
- Ao escrever um checklist, conferir a expectativa contra o código **atual**.
- Um número de ferramenta só vale se foi medido no artefato certo.

## Item 25 — Testes de integração e contrato (2026-08-09)

**Status:** concluído em 2026-08-09, em dois repositórios:
`feat/api-contract-tests` no `Refund-api` e `feat/contract-test` no
`Refund-FrontEnd`. Decisões na
[ADR-007](../decisions/ADR-007-contract-testing.md).

### Metade já existia

A prática que o item pede — *"banco descartável, migration do zero, health/auth
e um fluxo de refund via cliente FastAPI"* — tinha os dois primeiros desde o
Item 19. Faltava o **cliente FastAPI**, e faltava contrato.

### Este é o item em que uma dívida venceu

A pendência do Item 23 dizia, textualmente: *"Pegar isso exigiria o TestClient
do FastAPI e portanto httpx como dependência… **Se um dia a conta virar**, é
uma dependência só de teste e destravaria testes de rota de verdade."*

O item pede "via cliente FastAPI". A conta virou, e a dívida foi paga **com
prova**:

```
bug do Item 23 reintroduzido (handler na classe errada):
  testes de UNIDADE      6 passed     ← continuam verdes
  testes HTTP novos      2 failed     ← pegam
```

Era exatamente a lacuna descrita. Três itens seguidos entregaram um defeito da
mesma forma — peça certa, ligação errada — e todos os três foram achados
rodando a aplicação à mão. Estes testes são a versão automatizada disso.

### O engine preguiçoso do Item 17 pagou juros de novo

Apontar a aplicação para o banco de teste é uma linha:

```python
monkeypatch.setattr(settings, "database_url", TEST_DATABASE_URL)
get_engine.cache_clear()
```

Construído no import, como era antes do Item 17, a conexão já existiria antes
de qualquer fixture rodar e isto exigiria variável de ambiente no processo
inteiro. **É a segunda vez que aquele item barateia um posterior** — a primeira
foi o próprio Item 19.

### Quatro suposições minhas que a API real derrubou

Escrevi os testes assumindo o envelope `{type, count, attributes}` em tudo. A
API tem **três estilos**:

| Resposta | Forma |
|---|---|
| login, URL assinada | **plana** |
| criação, detalhe | `{type, count, attributes}` |
| listagem | o mesmo, mais paginação no nível de cima |

Não unifiquei — mudaria contrato, e não é o objeto deste item. Mas agora está
**documentado por um arquivo**, não pela memória de quem leu o código.

### O linter decidiu o formato do contrato

Escrevi um arquivo só. O `eslint-plugin-boundaries` recusou: `src/test` e
`src/schemas` são camada `app`, e uma feature não importa de `app`. Então um
teste da feature de reembolsos **não pode** ler um arquivo que também carregue
o payload de login.

Virou dois arquivos, e a divisão caiu **exatamente na costura que os schemas já
tinham**. Uma regra de arquitetura que produz uma consequência coerente num
lugar que ninguém tinha pensado é um bom sinal de que ela descreve algo real —
e não é o que eu esperava quando comecei a mexer.

### As duas divergências históricas, agora vermelhas

| Quebra | Resultado |
|---|---|
| Remover `"paid"` do `refundStatusSchema` | 1 failed |
| Devolver `user_id` ao topo | 3 failed |

A primeira é a que teria derrubado a Home de **todo** usuário no primeiro
reembolso pago, e que foi descoberta por leitura, não por teste.

### O que este contrato NÃO cobre

A cópia entre os dois repositórios é **manual**. O CI do backend falha se a API
mudou e o arquivo não foi regerado; o do frontend falha se os schemas discordam
do arquivo. **Nenhum dos dois percebe um arquivo regerado que nunca foi
copiado.**

É o preço de dois repositórios independentes, e tem a mesma forma do problema
dos SHAs que este projeto já registrou seis vezes: **nasce verdadeiro e morre em
silêncio**. Está escrito no topo dos três arquivos envolvidos, de propósito.

### Verificação

| Verificação | Resultado |
|---|---|
| `pytest` | **317 passed, 47 deselected** |
| `pytest -m integration` | **47 passed** (partiu de 32) |
| `pylint src; echo $?` | 10.00/10, **exit 0** |
| `npx vitest run` (frontend) | **304 passed** (partiu de 294) |
| Quebra: bug do Item 23 | unidade verde, **HTTP vermelho** |
| Quebra: `"paid"` removido | 1 failed |
| Quebra: `user_id` no topo | 3 failed |

### O que lembrar

- **Testar a peça não é testar a montagem** — pela terceira vez. Agora existe
  a camada que testa a montagem.
- Um contrato entre repositórios independentes tem um vão que nenhum CI fecha.
  Escrever o vão vale mais que fingir que não existe.
- Placeholders de contrato precisam **preservar o tipo**, ou o arquivo mente
  sobre a forma que se propõe a documentar.
- Uma regra de arquitetura boa se paga em lugares que ninguém previu.

## Item 26 — Cobertura como diagnóstico (2026-08-09)

**Status:** concluído em 2026-08-09, na branch `feat/coverage` dos dois
repositórios. Decisões na [ADR-008](../decisions/ADR-008-coverage.md).

### O item foi reapresentado do zero

A primeira apresentação não foi entendida, e com razão: eu abri com o
vocabulário (branch coverage, portão no CI, catraca) antes de estabelecer o que
a ferramenta **faz**. A segunda começou pelo concreto — instalei, rodei, e
mostrei o número real do projeto e uma linha específica que nenhum teste
tocava. Aí a conversa andou.

**Lição de comunicação, não de código:** quando um conceito não entra, o
problema costuma ser a ordem. Ferramenta → número real → achado real →
vocabulário, e não o inverso.

### A tese do item, provada pela história do próprio projeto

O texto do item avisa que *"porcentagem alta não garante boas asserções"*. Aqui
isso não é teoria: **os três defeitos mais recentes viviam em linhas cobertas.**

| Defeito | Linha coberta? | Teste pegava? |
|---|---|---|
| Item 23 — handler na classe errada | sim | não |
| Item 24 — filtro nunca instalado | sim | não |
| 09/08 — mensagem inalcançável | sim | não |

É por isso que nada reprova num número. O caminho mais barato para subir a
porcentagem é escrever asserções fracas.

### Configurar o relatório já é metade do trabalho

O primeiro relatório era quase todo ruído: **treze arquivos de interface a
80%**, porque o `pass` de um método abstrato nunca executa. Ninguém leria uma
lista assim. Excluir interfaces, entidades e o próprio código de teste é o que
fez o sinal aparecer.

E o número depende de **quais testes rodam**: o `s3_file_storage` dá 42% com a
suíte rápida e 97% com a de integração. "A cobertura do projeto" não é um
número só.

### Quatro achados reais, e o item entregou testes

| Achado | O que era |
|---|---|
| `error_handler.py:17` | o caminho de **erro inesperado** — o 500 — nunca executou em 317 testes |
| `storage_factory.py:29` | o ramo `s3` do `build_storage`: **o que produção usaria**, nunca executado (os testes de S3 constroem a classe direto) |
| `refund_routes` 77%, `user_routes` 59% | **todos os fluxos de admin a 0% por HTTP** — pagamento, revisão e as rotas de avatar |
| `useAuth.ts:7` (frontend) | a guarda de "usado fora do AuthProvider", nunca exercitada |

O terceiro é o que o item pede textualmente: *"usar o relatório para encontrar
**autorização** ou falha parcial esquecida"*. Sete testes HTTP novos saíram
dali, incluindo BR-016 (admin não decide o próprio pedido) e BR-021 (qualquer
autenticado lê qualquer avatar).

Backend 94% → **98%**. Frontend 92,5% → **92,7%**. Os números são consequência.

### O ponto cego do instrumento

O `return JSONResponse(...)` final de **toda** rota é reportado como nunca
executado — treze linhas. **Elas executam:** as requisições devolvem 200/201
com o corpo certo, e o dado bruto do coverage mostra a linha imediatamente
acima registrada.

Persegui a causa e **não achei**. `concurrency = thread` não mudou nada; um app
FastAPI isolado sem o middleware deste projeto registra a mesma instrução
normalmente, o que aponta para composição do app — mas a sonda que provaria
isso saiu errada (o arquivo de teste ficou desatualizado e eu quase concluí do
resultado inválido). Fica como **observação, não diagnóstico**.

Não excluí as linhas. Excluir transformaria uma distorção conhecida numa
invisível — e alguém lendo o relatório de cima para baixo iria escrever testes
para código já testado.

### Verificação

| Verificação | Resultado |
|---|---|
| `pytest` | **325 passed** (partiu de 317) |
| `pytest -m integration` | **54 passed** (partiu de 47) |
| `pylint src; echo $?` | 10.00/10, **exit 0** |
| `npx vitest run` | **305 passed** (partiu de 304) |
| Cobertura backend | 94% → **98%** |
| Cobertura frontend | 92,5% → **92,7%** |

### O que lembrar

- Cobertura responde **"isto nunca executou"**. Nunca responde "isto está
  certo".
- **Configurar o relatório é metade do valor** — um relatório barulhento não é
  lido.
- O número depende de quais testes rodam; não existe "a cobertura do projeto".
- **Conheça o ponto cego do seu instrumento**, e escreva-o onde quem lê o
  relatório vai tropeçar nele.
- Quando um conceito não entra, mude a **ordem**: ferramenta, número real,
  achado real, e só então o vocabulário.
