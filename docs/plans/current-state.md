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

Atualizado em: 2026-08-11.

## Visão geral

O produto é um sistema de **reembolso de despesas com comprovante**. São dois
repositórios Git irmãos e independentes, cada um com seu remote.

## Estado dos repositórios

**Este bloco não cita mais o SHA das `main` — de propósito.** Ele já esteve
errado seis vezes, e a sexta foi o próprio commit que corrigia a quinta: um
quadro que fixa "a `main` está em X" é invalidado por qualquer commit,
**inclusive o que o atualiza**. As cinco primeiras foram: afirmar que uma
branch não tinha sido mesclada quando já estava; fixar um SHA que commits de
documentação ultrapassaram no mesmo dia; duas vezes por um ciclo ter sido
mesclado sem que o fechamento atualizasse aqui; e uma quinta ao anotar um SHA
que o commit seguinte superou.

A forma que não envelhece é descrever **como descobrir** o estado, não afirmar
qual é. Em cada repositório:

```bash
git fetch origin                      # PRIMEIRO: atualiza a cópia local do remote
git log --oneline -1                  # onde a main local está
git ls-remote origin main             # onde o origin/main está de verdade
git log --oneline origin/main..main   # o que existe local e não foi empurrado
git branch --list                     # branches vivas
```

**O `git fetch` não é opcional.** O `git status` e o `origin/main..main`
comparam com a cópia do remote que o seu repositório guarda, e ela pode estar
velha sem nenhum aviso. O `git ls-remote` é a única das quatro consultas que
fala com o servidor; as outras leem o disco. Se as duas discordarem, o
`ls-remote` é que está certo.

O que era verdade na última verificação (**2026-08-09**), como ponto de
partida e não como afirmação durável:

- **`Refund-api`** — `main` e `origin/main` sincronizados. Branches locais
  antigas já mescladas continuam existindo; nenhuma é trabalho pendente.
- **`Refund-FrontEnd`** — `main` e `origin/main` sincronizados, sem branch de
  trabalho pendente além de `backup/claude-session-2026-07-13`, que nunca foi
  uma.

**Desde 2026-08-10 há uma diferença que nenhum ciclo anterior teve, e ela muda
o que "apagar uma branch" custa.** Há **duas branches das quais a Railway
implanta diretamente** — `feat/first-deploy` (`Refund-api`) e
`feat/serve-static` (`Refund-FrontEnd`) — e não da `main`. Apagar uma delas
com o serviço ainda apontado para lá quebra a produção. **Isto não é a
contagem total de branches não mescladas do momento** — o `Refund-api` também
tem `docs/preset-folder-refs`, de fato não mesclada (confira com `git cherry
-v main docs/preset-folder-refs`, que mostra `+ 166627e`) — só não é uma
branch que a Railway implanta, e é por isso que ela fica de fora desta
contagem. Ver a pendência dedicada na seção de pendências, que também diz onde
conferir a referência de cada serviço (é no painel, não no repositório).

**Esta data já esteve errada de novo.** Em 2026-08-09 ela dizia 2026-08-07, com
**quinze commits** depois — encontrado ao auditar a documentação, não por
alguém tropeçar. É a sétima ocorrência do mesmo padrão, e reforça o que este
bloco já dizia: **rode os comandos acima; não acredite nesta data.**

**OITAVA OCORRÊNCIA, e ela amplia o padrão.** Este documento descrevia as duas
branches do Item 31 (`perf/measured-index` e `perf/self-host-font`) como
**"Não mescladas"**. As duas estavam mescladas — `212c9c8` na `main` do
`Refund-api` e `b26385e` na do `Refund-FrontEnd`, esta última sendo
literalmente o HEAD daquela `main`. Foi encontrada pelo Gabriel ao escrever a
[retrospectiva de processo](../retrospectiva-processo.md), e corrigida no ciclo
de Python 3.13 (2026-08-10), junto de outras três pendências que a triagem
achou mortas.

O que a oitava acrescenta às sete anteriores: até aqui o padrão era lido como
um problema de **SHAs**. Não é. Vale para qualquer afirmação de estado —
**branch mesclada ou não, item concluído ou não, arquivo ainda existente ou
não**. As três outras pendências mortas encontradas na mesma triagem confirmam:
uma citava um arquivo que o Item 22 apagou, outra um problema de acessibilidade
já corrigido, e a terceira uma divergência de contrato que não existe mais. As
quatro nasceram verdadeiras. Nenhuma avisou quando deixou de ser.

A regra que sai daí, e que vale para quem escrever aqui: **uma pendência deve
dizer como conferir se ainda é uma.** Um caminho de arquivo, um comando, um
`grep` — algo que a próxima sessão possa rodar em segundos em vez de reconstruir
o contexto para decidir se o texto ainda vale.

**NONA OCORRÊNCIA, e ela é de um tipo pior — nasceu falsa.** O commit que
registrou a oitava (o fechamento do ciclo de Python 3.13) afirmava, no relato
daquele ciclo, que o diretório do ledger de execução **"foi removido no
fechamento"**. Ele não tinha sido removido, e não seria por quem escreveu a
frase — a remoção é do controlador, e acontece **depois**. A afirmação era
falsa no instante em que foi commitada. Pega na revisão da própria task e
corrigida ali.

A diferença importa. As oito anteriores **nasceram verdadeiras e morreram em
silêncio**; contra elas, a defesa é reverificar. Esta não teve instante de
verdade nenhum, e a defesa contra ela é outra: **não escrever no passado um
fato que ainda não aconteceu.** A causa foi copiar a forma das entradas dos
ciclos anteriores — onde "foi removido no fechamento" é legítimo, porque para
aqueles a remoção já tinha ocorrido — sem notar que o tempo verbal não
transferia para um ciclo ainda em fechamento.

**A correção não foi acertar o tempo verbal, e é isso que vale levar.** Trocar
"foi removido" por "será removido" só teria trocado uma frase que já era falsa
por uma que ficaria falsa depois. A frase foi reescrita para descrever o
**processo** — onde o ledger vive enquanto o ciclo está aberto, e o que passa a
ser o registro depois — de modo que ela é verdadeira nos dois estados e não tem
como apodrecer. É a mesma lição que este bloco aplica aos SHAs desde a primeira
ocorrência, agora numa nona forma: **quando uma frase pode envelhecer, descreva
o mecanismo em vez de afirmar o estado.**

**DÉCIMA E DÉCIMA PRIMEIRA OCORRÊNCIAS, achadas pela revisão de branch inteira
do mesmo ciclo que fechou a nona.** O `docs/roadmap.md` (seção "Em análise")
continuava afirmando que o projeto roda Python 3.9 e que a imagem de produção
é construída sobre ela — falso desde os primeiros commits deste mesmo ciclo. O
`.github/workflows/ci.yml` comentava, no presente, uma pendência dos shebangs
do `.venv` que esta própria seção já registra como **FECHADA COMO SUBPRODUTO**
(ver abaixo). As duas nasceram do ciclo de Python 3.13 e sobreviveram à
varredura de pendências que o motivou: a varredura leu o `Dockerfile`, este
documento e o `AGENTS.md`, mas não passou por um roadmap de produto nem por um
workflow de CI — nenhum dos dois parecia, a priori, um lugar onde uma
afirmação sobre versão de Python pudesse ter ficado para trás. Corrigidas na
onda final de correções antes de oferecer a branch para merge (2026-08-10). A
lição de escopo: **uma varredura de "arquivos que mudaram" não é a mesma coisa
que uma varredura de "arquivos que citam o fato que mudou"** — os dois exigem
buscas diferentes, e só a segunda pega isso.

**DÉCIMA SEGUNDA, DÉCIMA TERCEIRA E DÉCIMA QUARTA OCORRÊNCIAS, achadas na
revisão de branch inteira do ciclo do primeiro deploy — e diferentes das onze
anteriores porque nasceram falsas, em vez de terem apodrecido depois.** As
três viviam no bloco que este próprio documento usa para decidir se é seguro
apagar uma branch — o que torna o erro mais grave que os anteriores, não
menos, porque é exatamente o bloco cuja confiabilidade sustenta essa decisão.

- **Décima segunda:** este documento (`:1721`, `:1897`, `:2095`, antes desta
  correção) e o `docs/roadmap.md` (`:34-35`) descreviam `chore/python-313-upgrade`
  como "não mesclada" / "ainda não mesclada". **Está mesclada** — seus seis
  commits (`8a56ba5`, `8b12240`, `581cd85`, `5458777`, `5bf4e2e`, `6ef5632`)
  são todos ancestrais de `18b8678`, que é o próprio *merge base* desta branch
  com a `main`; confira com `git merge-base --is-ancestor <commit> 18b8678`
  para qualquer um deles. A branch nem existe mais localmente.
- **Décima terceira:** a linha `:2470` (antes desta correção) descrevia
  `fix/auth-storage-access` (`d9d8b6b`, no `Refund-FrontEnd`) como "não
  mesclada", enquanto a linha `:2185`, **no mesmo arquivo**, já registrava que
  ela foi mesclada em 2026-08-05 (`d33fb65..d9d8b6b`, fast-forward). O
  documento se contradizia a poucas centenas de linhas de distância. Confira
  com `git -C ../Refund-FrontEnd merge-base --is-ancestor d9d8b6b main`.
- **Décima quarta:** o bloco de `:58-64` (antes desta correção) afirmava
  "duas branches de trabalho não mescladas", como se fosse a contagem total do
  momento. O `Refund-api` também tem `docs/preset-folder-refs`, de fato não
  mesclada (`git cherry -v main docs/preset-folder-refs` mostra `+ 166627e`).
  A frase foi reescrita para escopar às duas branches **das quais a Railway
  implanta**, que é o fato do qual a pendência de segurança realmente precisa.

O que diferencia estas três das onze anteriores: aquelas nasceram verdadeiras
e morreram em silêncio quando o mundo mudou depois de escritas. Estas já
estavam falsas no instante em que a versão final desta branch (`08506d1`) foi
commitada — os merges de `chore/python-313-upgrade` e de
`fix/auth-storage-access` já tinham acontecido havia muito quando as frases
foram lidas e deixadas como estavam, dentro do próprio bloco cuja função
declarada é ser confiável o bastante para decidir se apagar uma branch é
seguro.

**Correção registrada:** até 2026-08-07 este documento afirmava, nos itens 15
e 16, que aquelas branches não tinham sido mescladas. Já tinham. O bloco de
estado dizia "última verificação 2026-08-03" enquanto os Itens 14, 15 e 16 são
de 08-05/08-06 — ou seja, o documento contradizia a si mesmo, e a contradição
só apareceu porque alguém rodou os comandos acima em vez de ler o texto. É
exatamente a falha que este bloco existe para tornar detectável.

Um commit de documentação posterior a esta linha já a deixa desatualizada de
novo — é para isso que existem os comandos acima.

**Nem todo SHA envelhece igual, e a diferença é o que este bloco aprendeu.** O
de uma branch de trabalho (`d33fb65`) se mantém enquanto ela não for mesclada,
porque identifica um objeto que ninguém vai ultrapassar; o mesmo vale para um
SHA de código citado *dentro* do relato de um ciclo. É o par
`main`/`origin/main` que não sobrevive — ele muda toda vez que alguém trabalha,
que é justamente quando ninguém está lendo este documento.

**EXISTE PRODUÇÃO.** A primeira implantação do projeto aconteceu em
2026-08-10, no ciclo `feat/first-deploy` / `feat/serve-static`. A frase que
sobreviveu às cinco fases da trilha — *"não existe deploy"* — deixou de ser
verdadeira.

- API: `https://refund-api-production-5a7c.up.railway.app`
- Frontend: `https://independent-fascination-production-feea.up.railway.app`

**Este bloco descreve como conferir, não afirma que está no ar.** Um serviço
implantado pode ser desligado, ficar sem crédito ou ser apagado no painel sem
deixar rastro em arquivo nenhum — exatamente a assimetria que a verificação de
2026-08-03 já tinha registrado no sentido oposto (um deploy pode existir
inteiramente no painel do provedor). As duas perguntas continuam sendo duas:

```bash
curl -s -o /dev/null -w '%{http_code}\n' https://refund-api-production-5a7c.up.railway.app/health
curl -s -o /dev/null -w '%{http_code}\n' https://refund-api-production-5a7c.up.railway.app/ready
curl -s -o /dev/null -w '%{http_code}\n' https://independent-fascination-production-feea.up.railway.app/
```

`/health` é liveness e `/ready` consulta o banco: os dois em **200** é a
evidência de que o processo está vivo **e** alcança o PostgreSQL. O que os
comandos não respondem — se os serviços ainda estão conectados às branches
certas, e se a conta ainda está paga — só o painel da Railway responde.

**O que o texto anterior dizia continua sendo a explicação de por que os cinco
bloqueios existiam**, e por isso não foi apagado: até 2026-08-03 este documento
tratava o deploy conjunto como o risco mais grave do projeto e deixava em aberto
se ele era automático a partir da `main` ou manual. **Não era nenhum dos dois:
não havia deploy nenhum.** "Os dois lados estão publicados" sempre significou
publicados no **GitHub**, não implantados em lugar algum. A premissa de que
existia uma produção nunca tinha sido verificada; foi verificada em 2026-08-03,
era falsa, e é dessa verificação que saiu a lista dos cinco bloqueios — os
mesmos que os Itens 17, 22, 29 e 30 fecharam, e sem os quais este deploy não
teria como acontecer.

**O que voltou a ter dentes com a produção existindo.** Três avisos deste
documento eram contingentes a um ambiente que não existia, e deixaram de ser:

1. **A divergência de contrato entre os dois repositórios.** Os dois lados
   subiram juntos na primeira implantação, então a divergência não mordeu — mas
   a partir de agora existe um cliente real, e implantar um lado sem o outro
   volta a poder quebrar a tela de quem está usando.
2. **Trocar o `JWT_SECRET` desloga todo mundo.** Era um efeito sobre uma
   população vazia; agora existem sessões reais. Ver a seção de rotação de
   segredos do [`README.md`](../../README.md).
3. **Uma mudança na forma da sessão salva desloga todo mundo uma vez.** Mesma
   coisa: o mecanismo sempre esteve correto, faltava alguém para sofrê-lo.

O contrato novo (`user` aninhado) e o contrato `paid` seguem mesclados e
**implantados** dos dois lados.

O produto vive em dois repositórios:

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

Em produção a topologia é outra, e desde 2026-08-10 ela existe: os dois lados
rodam na Railway (a API em container a partir do `Dockerfile`, o frontend
servido estático por `serve -s dist`), o banco é o PostgreSQL da própria
Railway e os arquivos ficam num bucket **S3 da AWS**
(`STORAGE_BACKEND=s3`). Nenhum valor de configuração de produção mora neste
repositório — apenas os **nomes** das variáveis, no
[`.env.example`](../../.env.example) e no `README.md`.

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

Ao redor: `pages/` (prefixo `Page`), `features/refunds/` e `features/team/`, cada
uma com fachada pública (Item 8), `stores/` (Zustand), `hooks/`, `context/` (Auth
via Context + `localStorage`), `lib/` (Axios com interceptors) e `schemas/` (Zod). Server
state via TanStack Query; formulário e responses consumidos validados com Zod. O
React Router usa Data Mode com loaders, páginas lazy e erro de rota; busca e
paginação da Home vivem em search params validados. As camadas
(`app`/`feature`/`ui`/`shared`) são verificadas pelo `eslint-plugin-boundaries`
(Item 9).

`src/components/{atoms,molecules}` **não existem mais** — foram substituídos por
`src/components/ui` no ciclo do restyle.

**Duas features, e elas não se falam.** O `eslint-plugin-boundaries` proíbe uma
feature importar a irmã, então a página do membro do time (`PageTeamMember`) é
quem compõe as duas: pega o usuário de `features/team` e o painel de
estatísticas de `features/refunds`. A composição de features acontece sempre na
camada `app`, porque é a única com permissão para isso.

O Dashboard tem quatro gráficos, e todos chegam à tela por **um** contêiner
(`DashboardCharts`), que é o único módulo de gráfico que a fachada exporta e o
único ponto de `import()` dinâmico. Nenhum gráfico é reexportado: uma reexportação
estática traria a árvore do nivo de volta ao bundle de entrada sem erro nenhum. A
verificação é o **tamanho da entrada** no `npm run build`, não a existência de um
chunk separado — o chunk existe de qualquer forma.

**Três features no frontend**, e nenhuma importa a outra: `refunds`, `team` e
`profile`. A `profile` nasceu com a foto de perfil — ela tem endpoints, ramo de cache e
mutações próprios, e é lida por três telas que não têm mais nada em comum: a sidebar da
shell, o diretório de Time e a página do membro.

O avatar chega à tabela de Time por **slot**, não por import: o
`eslint-plugin-boundaries` recusou `team` importando `profile`, e quem compõe as duas é
a página. Foi a regra funcionando, não um obstáculo.

`has_avatar` decide se o cliente pede a URL assinada. A API responde 404 tanto para
"sem foto" quanto para "usuário inexistente", então sem esse campo uma lista de dez
linhas sem foto seria dez requisições que falham.

As três telas prometidas na sidebar estão entregues: `/dashboard`, `/team` (admin) e
`/calendar`. Nenhum item tem selo "em breve", e `NavItem.enabled` segue existindo,
documentado no arquivo, como a máquina do selo para a próxima promessa.

O `RefundLineChart` é compartilhado pelo Dashboard (valor por mês) e pelo Calendário
(contagem por dia), e **não sabe qual é**: recebe pontos já na unidade de exibição
mais o valor exato para o tooltip. Quem converte é o chamador — foi assim que o
Calendário reusou o gráfico sem uma terceira ramificação de métrica.

O calendário mostra a contagem por dia como **mapa de calor**, não como número: uma
matiz quente só, pálido a escuro, com rampa PRÓPRIA no tema escuro (crescendo em
luminância, porque em fundo escuro o que ordena é contraste contra a superfície). O
domínio é adaptativo ao mês, com piso no número de degraus e legenda obrigatória — a
mesma cor vale contagens diferentes em meses diferentes. Cada par de cor e número do
dia foi medido: pior caso 4,56:1.

**Existe UMA paleta categórica** (`chartPalette`: quatro slots mais o vermelho
reservado a "rejeitada"), e o gráfico de categoria não usa cor como identidade — os
nomes das categorias estão escritos no eixo, e a cor seria codificação redundante.
Uma segunda paleta, de cinco slots para as categorias de despesa, foi construída e
revertida no mesmo dia junto com o desenho que a pedia (2026-08-11).

**Dívida de acessibilidade aberta:** a paleta de gráficos falha 4 das 6 checagens
do validador, incluindo o piso de visão normal entre "aprovada" e "paga" (ΔE 12,9,
piso 15). Mitigada no gráfico empilhado, não corrigida. Registrada no
[`roadmap.md`](../roadmap.md) com as cores que passam.

O painel compartilhado é o `RefundStatsPanel` (rosca por status + as
solicitações de uma pessoa), usado pela tela de revisão através do
`RequesterPanel` e pela página do membro direto. Ele **não** renderiza `Card`
nem título: quem monta decide o invólucro, e é isso que evita o nome duplicado
na página do membro. Ele também é o único caminho pelo qual o gráfico entra na
aplicação — o `RefundDonutChart` não é exportado por nenhuma fachada, porque uma
reexportação estática traria os 74 kB gzip do chunk do nivo de volta ao bundle de
entrada sem erro nenhum ([orçamento](../performance-budget.md)).

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
    **Atualização de 2026-08-03:** essa ordem nunca chegou a ser exercida e
    ficou superada pelo ciclo seguinte, que removeu `user_id` do topo e assim
    eliminou qualquer ordem segura. Como não existe produção, as duas `main`
    sobem juntas na primeira implantação e a questão de ordem desaparece.

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
  - **Backend e frontend TÊM de ir para produção juntos** — continua valendo,
    mas para a **primeira** implantação; não existe produção (reclassificado em
    2026-08-03, ver pendências).

- **Ciclo de feature — Servir arquivos com autenticação (backend): CONCLUÍDO.**
  Quinto ciclo, na branch `feat/authenticated-file-serving` (`55be4d4..ba51c4b`,
  8 commits de código), **empilhada sobre `feat/refund-query-and-avatar`**. A
  pilha inteira **foi mesclada na `main`** no início do ciclo do frontend, por
  **fast-forward** (`3fa42b2..ef7c60f`, 33 commits), com `pytest` 178/178 e
  `pylint src` 10.00/10 depois do merge. Desde então a `main` do `Refund-api`
  só recebeu documentação (`d332cb9` e `23c6675`, o fechamento do ciclo do
  frontend), e é onde ela está hoje. Artefatos em `docs/superpowers/`
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
  CONCLUÍDO.** Sexto ciclo e o primeiro de frontend desde o restyle, na branch
  `feat/frontend-contract-and-receipt` do `Refund-FrontEnd`
  (`6326606..39e0683`, 17 commits), executado em 11 tasks com revisão por task
  mais uma revisão da branch inteira. **Mesclada na `main` em 2026-07-29 por
  fast-forward** e empurrada para o `origin/main`; a branch local não existe
  mais. A `main` do frontend está hoje em `39e0683`. Artefatos em
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

- **Ciclo de feature — Pagamento, histórico de revisões e estatísticas
  (backend): CONCLUÍDO e MESCLADO na `main`** por fast-forward
  (`23c6675..30b6f88`, 30 commits) e **publicado no `origin/main`**. Sétimo
  ciclo, o segundo inteiramente
  de backend, na branch `feat/refund-payment-and-stats` do `Refund-api`,
  executado em 12 tasks com revisão por task, mais uma revisão da branch
  inteira. O ledger de execução ficava em `.superpowers/sdd/2026-07-30-refund-payment-and-stats/`
  — **esse diretório foi removido no fechamento**, conforme o fluxo; o registro
  agora é o histórico do Git.
  Fecha `UC-012`/`UC-013`/`UC-014` e acrescenta um quarto status (`paid`) ao
  ciclo de vida de `refunds.status`. O que mudou:
  - **`POST /refunds/{id}/payment`** — só admin, nunca a própria solicitação,
    só sobre `approved`, comprovante JPG/PNG/PDF até 4MB. Marca `paid` com
    `UPDATE` condicional (fecha a corrida com outro admin pagando ao mesmo
    tempo) e grava uma linha em `refund_reviews`
    (`from_status="approved", to_status="paid"`) na mesma transação.
  - **`GET /refunds/{id}/payment-receipt`** — dono ou admin; os quatro
    caminhos de 404 (id inexistente, não é seu, nunca pago, arquivo sumiu do
    disco) respondem **idênticos**, verificado byte a byte na Task 12.
  - **`GET /refunds/{id}/reviews`** — histórico de decisões (quem, quando, de
    qual status para qual, motivo). `RefundReviewsReaderRepository` segue o
    par que o projeto já usa — sessão própria, sem transação — porque a
    leitura não tem nada com que compartilhar uma.
  - **`GET /users/{id}/refund-stats`** — contagem e soma por status, sempre as
    quatro chaves (`pending/approved/paid/rejected`), mesmo com zero linhas
    num status. Dono, admin, ou `404` para terceiro (mesmo raciocínio
    anti-enumeração da BR-013).
  - **`GET /refunds?user_id=`** — admin pode escopar a listagem a um
    solicitante; para `standard` o parâmetro é **ignorado**, não rejeitado.
  - **Pool de conexões** (`pool_size=2, max_overflow=0` → `pool_size=5,
    max_overflow=10`) e um `lock_timeout` de 3s — achado de transporte: a
    forma que a documentação do asyncpg recomenda
    (`server_settings={"lock_timeout": ...}`) é descartada em silêncio pelo
    proxy do Neon; sobrevive como `options="-c lock_timeout=3000"`. Detalhes
    no [diário](../learning-path-progress.md).
  - **`paid` não era terminal.** A única guarda de transição
    (`current_status == status`) nunca cobria `paid`, porque `paid` nunca é um
    alvo válido de revisão — um `PATCH` revertia silenciosamente um reembolso
    já pago. Corrigido numa correção retroativa (Task 11.5, commit `5f78777`)
    com uma guarda dedicada. Achado só na verificação ponta a ponta, invisível
    à suíte mockada. Detalhes no [diário](../learning-path-progress.md).
  - Verificação das 12 tasks: `pytest` (**226 verdes**, partiu de 178),
    `pylint src` (**10.00/10**), **26/26 cenários ponta a ponta** contra a API
    real (a tabela original do plano tinha 25; o 26º veio do achado do `paid`),
    `ls uploads/payment_receipts/` antes/depois provando que os cenários de
    guarda e de duplicata não deixam arquivo órfão, e três `PATCH` concorrentes
    na mesma solicitação completando em ~1,5s, sem `500` nem espera longa.
  - **A revisão da branch inteira achou três interações entre tasks** que a
    revisão por task não podia ver, todas corrigidas em `c242ed7`:
    `payment_filename` vazando pelo `PATCH /status` — o único caminho de
    resposta que não passa pelo serializador compartilhado; uma falha dentro da
    transação de pagamento deixando o arquivo órfão e devolvendo `500` em vez de
    `422`, alcançável só porque o `lock_timeout` global (task 2) e a ordem
    arquivo→transação (task 5) existiam juntos; e `paid` ausente da lista branca
    do filtro `status`, de modo que a listagem exibia um status que não sabia
    filtrar.
  - **A correção dessa segunda interação introduziu uma janela de perda de
    dados, pega pela re-revisão** e corrigida em `30b6f88`: o `try/except`
    envolvia o `async with` inteiro, inclusive o fechamento de sessão que roda
    **depois** do commit — então uma falha ali apagava o comprovante de um
    pagamento já durável. A compensação passou a ser condicionada a `committed`.
  - Números finais na `main`: `pytest` **235 verdes**, `pylint src`
    **10.00/10**.

- **Ciclo de feature — Workflow de aprovação na UI (frontend): CONCLUÍDO e
  MESCLADO na `main`** por fast-forward (`39e0683..485cecb`, 15 commits),
  e **publicado no `origin/main`**. Oitavo
  ciclo de feature, o segundo consecutivo inteiramente de frontend, na branch
  `feat/refund-review-ui` do `Refund-FrontEnd`, executado em 9 tasks com revisão
  por task, mais a Task 10 de fechamento e a revisão da branch inteira.
  Verificação repetida depois do merge: 157 testes, `tsc` exit 0, lint 0/0,
  bundle 518,36 kB. Artefatos em
  `Refund-FrontEnd/docs/superpowers/`
  ([spec](../../../Refund-FrontEnd/docs/superpowers/specs/2026-07-30-refund-review-ui-design.md)),
  o ledger de execução ficava em
  `Refund-FrontEnd/.superpowers/sdd/2026-07-30-refund-review-ui/`, **removido no
  fechamento** conforme o fluxo — o registro agora é o histórico do Git.
  Consome o ciclo de backend anterior (pagamento, histórico e estatísticas) e
  **conserta uma quebra ativa**: `refundStatusSchema` só conhecia três status,
  e o backend já respondia `"paid"` — o primeiro reembolso pago derrubaria a
  Home inteira em `isError` para todo usuário. O que mudou:
  - **Contrato absorvido primeiro** (pré-requisito de tudo o resto).
    `refundStatusSchema` ganhou `"paid"`; `REFUND_STATUS`, um
    `Record<RefundStatus, …>`, ganhou a quarta entrada — o próprio TypeScript
    barra a omissão, então a mesma classe de quebra não pode se repetir nos
    rótulos. Dois schemas novos: `refundReviewSchema` e `refundStatsSchema`.
  - **Card "Total" da Home corrigido.** Passou a somar só `approved` + `paid`
    (antes somava todos os status, sem sentido depois de `paid` existir);
    terceiro card "Pendentes" com a contagem. A fonte, para o usuário comum, é
    `GET /users/{id}/refund-stats`; para o admin (visão de todos) não existe
    agregado equivalente — ver pendências.
  - **Rota de revisão `/refunds/:id/review`**, lazy, com `reviewLoader`
    redirecionando para o detalhe quando o papel não é admin ou o reembolso é
    do próprio admin — guarda de usabilidade, não de segurança; quem garante
    é o 403/404 do backend.
  - **Aprovar/rejeitar** (rejeitar exige motivo, validado por Zod, num
    `Dialog`) e **marcar como pago** (`POST /refunds/{id}/payment`,
    multipart, comprovante obrigatório reusando as regras de
    `refundCreateSchema`).
  - **Histórico de revisões** (`GET /refunds/{id}/reviews`) como linha do
    tempo no card de detalhe e na tela de revisão; **comprovante de
    pagamento** reusando o `ReceiptPreview` existente via um prop `kind`.
  - **Painel do solicitante** na tela de revisão: nome, contadores por status
    e a lista de solicitações dele (`GET /refunds?user_id=`), com a mesma
    regra de destino de clique da Home.
  - Verificação: `npx vitest run` (**157 verdes em 38 arquivos**, partiu de
    103 em 31), `npx tsc -b --noEmit` (exit 0), `npm run lint` (**0 erros, 0
    warnings**), `npm run build` (ok; bundle **506,00 → 518,36 kB**,
    +12,36 kB — o aviso de chunk > 500 kB é **pré-existente**, já estava
    presente no ponto de partida deste ciclo, não foi introduzido por ele).
  - **A revisão da branch inteira passou sem nenhum achado Critical ou
    Important.** Ela conferiu por busca — não por leitura de intenção — que
    nenhum ponto do código ainda assume três status, que a regra de destino do
    clique existe numa função só (`lib/getRefundHref.ts`) sem cópia inline
    sobrevivente, e que nenhuma chave de cache colide: os dois tipos de
    comprovante são subárvores distintas, e a lista por usuário não colide com
    a da Home porque o `userId` ausente some do hash da chave. Os **11 achados
    menores** acumulados no ledger foram triados como legitimamente
    pós-merge — são lacunas de cobertura ou arestas de UX, nenhuma afeta
    correção, segurança ou integridade de dados.
  - **Validado visualmente em navegador pelo Gabriel em 2026-07-30** — a única
    evidência que a suíte não substitui, já que ela roda inteira contra o MSW,
    ou seja, contra o payload que nós mesmos escrevemos. Ver pendências para o
    alcance registrado dessa validação.
  - Detalhes completos, incluindo os achados adiados task a task, em
    nas mensagens de commit da branch
    e no [diário](../learning-path-progress.md).

- **Ciclo de feature — Navegação na revisão e tabela de reembolsos
  (frontend): CONCLUÍDO.** Nono ciclo de feature (terceiro do
  `Refund-FrontEnd`), na branch `feat/review-navigation-and-refund-table`
  (`485cecb..722371b`, 16 commits — 4 de planejamento/spec, 12 de
  implementação com revisão por task, mais a Task 13 de fechamento e a
  revisão da branch inteira). Artefatos em `Refund-FrontEnd/docs/superpowers/`
  ([spec](../../../Refund-FrontEnd/docs/superpowers/specs/2026-07-31-review-navigation-and-refund-table-design.md)),
  o ledger de execução ficava em
  `Refund-FrontEnd/.superpowers/sdd/2026-07-31-review-navigation-and-refund-table/`
  e **foi removido no fechamento**, conforme o fluxo — o registro agora é o
  histórico do Git.
  **Fecha o Item 13** da trilha (TanStack Table) e, na mesma branch, resolve
  três lacunas de navegação deixadas pelo ciclo de revisão anterior. O que
  mudou:
  - **Tasks 1–7 — a Home.** `status`, `sort` e `order` passam a ser aceitos
    como search params, validados por Zod com fallback e normalizados pelo
    loader da rota — uma URL com `?sort=inexistente` cai no valor padrão em
    vez de quebrar a tela. A `<ul>` da Home virou uma tabela (TanStack Table)
    com seis colunas (categoria, título, solicitante, data, status, valor); a
    coluna de solicitante some para quem não é admin via `columnVisibility`
    do próprio TanStack, e três colunas colapsam abaixo de `sm` por CSS
    (`meta.className`, não JS medindo viewport). Ordenação é **server-side**:
    os cabeçalhos clicáveis escrevem `sort`/`order` na URL
    (`manualSorting: true`, nunca `getSortedRowModel`); uma toolbar filtra
    por `status`; e o rótulo do card de dinheiro do admin acompanha o filtro
    ativo.
  - **Tasks 8–12 — a tela de revisão.** O comprovante da despesa passa a
    aparecer (antes um admin decidia sem ver o documento que justifica o
    pedido); o painel do solicitante ganhou um contador "Total"; a
    solicitação aberta é destacada no painel (`bg-accent` +
    `aria-current="page"`); setas anterior/próxima andam entre as
    solicitações do mesmo solicitante; e um botão "Próxima pendente" pula
    para a pendente mais antiga que não seja do próprio admin.
  - **Três limpezas triviais de tasks anteriores**, feitas na Task 13: o
    alias de teste redundante (`renderReviewPage`) removido de
    `PageRefundReview.test.tsx`, com os call sites usando
    `renderPageRefundReview` direto; `isLoading: isAdmin && isLoading` em
    `useNextPendingRefund.ts` virou só `isLoading` (uma query desabilitada já
    reporta `isLoading: false` no TanStack Query v5 — mesmo idioma de
    `useRefund.ts`/`useRefundStats.ts`); indentação corrigida em
    `PageRefundReview.tsx` (a `<div className="flex justify-end">` estava um
    nível abaixo do `{refund && (` que a envolve).
  - Verificação (Task 13): `npx vitest run` rodado **três vezes**, sempre
    **209 testes em 41 arquivos**, todos verdes — o flake conhecido do
    `ResizeObserver` (ver pendências) **não apareceu em nenhuma das três**.
    `npx tsc -b --noEmit` (exit 0), `npm run lint` (0 erros, 0 warnings),
    `npm run build` (ok; bundle **518,36 → 559,51 kB**, +41,15 kB —
    atribuível ao `@tanstack/react-table` mais o código novo; o aviso de
    chunk > 500 kB segue **pré-existente**).
  - **A revisão da branch inteira** (Task 13) conferiu por busca, não por
    leitura de intenção: nenhum ponto do código ordena ou filtra reembolsos
    no cliente (`grep -rn "\.sort(\|\.filter(" src/features/refunds
    src/pages`, vazio); `getRefundHref` continua com um único ponto de regra
    (`RefundsTable` e `RequesterPanel` consomem a mesma função, sem cópia
    inline de `role === "admin" && …`); nenhuma chave de cache colide
    (`refundKeys.list` hasheia o objeto de parâmetros inteiro, e a fila de
    pendentes de `useNextPendingRefund` usa `status`/`sort`/`order` fixos,
    distintos dos da Home); e os ids das colunas ordenáveis (`name`,
    `created_at`, `status`, `amount_in_cents`) batem exatamente com a lista
    branca de `refundSortSchema` — `category` e `user` não têm `accessorFn`
    e têm `enableSorting: false` de propósito, então nunca viram botão.
  - **Achado que vale registrar:** `ResizeObserver is not defined` foi
    reproduzido, pela primeira vez, com as mudanças da task **guardadas no
    stash** — ou seja, numa árvore sem elas (1 falha em 9 rodadas completas,
    contra 2 falhas em 4 rodadas com as mudanças aplicadas). Ver a pendência
    atualizada abaixo. Até aqui toda ocorrência tinha sido dentro de um
    ciclo, o que deixava em aberto se a causa era nossa.
  - ~~**Não validado em navegador contra a API real nesta sessão.**~~
    **VALIDADO em 2026-08-03, sem ressalvas.** A verificação da Task 13 rodara
    inteira contra a suíte (MSW) e as ferramentas de build, sem navegador
    disponível; a passada no navegador aconteceu depois e cobriu Home com
    `status`/`sort`/`order` na URL, tabela de seis colunas, ordenação
    server-side pelos cabeçalhos, coluna de solicitante só para admin, colapso
    abaixo de `sm`, comprovante na revisão, setas anterior/próxima e "Próxima
    pendente". Detalhes
    completos, task a task, no [diário](../learning-path-progress.md) e no
    relatório da Task 13
    (`Refund-FrontEnd/.superpowers/sdd/2026-07-31-review-navigation-and-refund-table/task-13-report.md`).

- **Ciclo de feature — Feedback de carregamento e ajustes de UI (frontend):
  CONCLUÍDO, MESCLADO por fast-forward e EMPURRADO.** Décimo ciclo de feature
  (quarto do `Refund-FrontEnd`), na branch `feat/loading-feedback-and-ui-fixes`
  (`b65bf33..6c63ff5`, 16 commits — 2 de spec/plano, 13 de implementação em 9
  tasks com revisão por task, a Task 10 de fechamento, e um commit final com os
  achados da revisão da branch inteira). Números finais na `main`: **246 testes
  em 44 arquivos** (partiu de 215), `tsc` exit 0, lint 0/0, bundle 559,51 →
  560,88 kB. A spec e o plano ficam em
  `Refund-FrontEnd/docs/superpowers/`; o ledger de execução ficava em
  `.superpowers/sdd/2026-07-31-loading-feedback-and-ui-fixes/` e **foi removido
  no fechamento**, conforme o fluxo — o registro agora é o histórico do Git.
  Nasceu de seis problemas relatados pelo Gabriel usando o app, dois deles com
  a mesma causa raiz. O que mudou:
  - **O estado de carregamento terminava antes do trabalho.** Os quatro hooks
    de mutação (`useCreateRefund`, `useDeleteRefund`, `usePayRefund`,
    `useReviewRefund`, em `src/features/refunds/hooks/`) descartavam a
    *promise* devolvida por `queryClient.invalidateQueries` dentro do
    `onSuccess` — uma instrução solta em vez de um `return`. O React Query só
    mantém `isPending` até o `onSuccess` **resolver**; sem o `return`, ele
    resolve no mesmo instante (a chamada nem foi aguardada), então
    `isPending` cai assim que o HTTP termina, não quando a invalidação (e o
    refetch que ela dispara) termina. Resultado: o botão voltava ao normal
    com a tela ainda mostrando o estado anterior (histórico desatualizado,
    lista antiga). A correção foi devolver a promise nos quatro hooks — só a
    vírgula/`return` mudou, **nenhum alvo de invalidação foi alterado**
    (conferido por `git diff` na Task 10: os quatro `queryKey`/`refetchType`
    são byte a byte iguais ao início do ciclo). Todo botão que dispara uma
    mutação agora mostra spinner, rótulo próprio de ocupado
    (`"Aprovando…"`/`"Rejeitando…"`/`"Marcando como pago…"`/`"Excluindo…"`/
    `"Enviando…"`) e `aria-busy`.
  - **Login, excluir e criar tinham o mesmo sintoma por uma causa diferente.**
    Esses três terminam em **navegação** (`/`, tela de sucesso), não em uma
    query que o React Query saiba esperar. `useNavigation()` do modo Data do
    React Router (`state !== "idle"`) mantém o botão ocupado até a **rota**
    assentar, não até os dados chegarem — usado em `PageLogin.tsx`,
    `PageRefundDetails.tsx` (exclusão) e `RefundFormDialog.tsx` (criação), e
    só onde há navegação de verdade (conferido por grep na Task 10).
  - **Card de pendentes do admin.** `usePendingCount(enabled)`
    (`src/features/refunds/hooks/usePendingCount.ts`, novo) faz uma consulta
    dedicada — `GET /refunds?status=pending&per_page=1`, lendo só `total` —
    deliberadamente **global**: ignora o filtro de status, a busca e a página
    ativos na lista da Home. **Consequência registrada:** isso é **uma
    requisição HTTP a mais por carregamento da Home do admin**, só para esse
    card (o usuário comum não paga esse custo — o dele já vem de
    `GET /users/{id}/refund-stats`, que também é global por construção). Não
    é uma solução para o agregado de valores cruzando usuários (pendência já
    registrada abaixo, "Nenhum endpoint produz um agregado por status
    cruzando usuários") — cobre só a **contagem** de pendentes, com um
    endpoint que já existia.
  - **Rótulos do card de solicitações declaram o escopo.** Com filtro de
    status ativo, o card vira `"Solicitações (Pago)"` etc., porque dois dos
    três cards da Home seguem o filtro e um (o de pendentes) não.
  - **Os dois diálogos resetam ao fechar, não só ao ter sucesso** — cancelar
    um rascunho não deixa mais o formulário sujo para a próxima abertura. Os
    banners de erro são limpos com o mesmo cuidado, e escopados por ação
    (`pendingAction`/`errorSource`), para que cancelar uma rejeição não apague
    um erro de aprovação ainda relevante na mesma tela.
  - **Tela de sucesso com dois botões.** "Nova solicitação" reabre o mesmo
    diálogo (zerado, pelo ponto acima) sem sair da página; "Voltar para a
    Home" navega. O gatilho trafega via `useOutletContext`
    (`MainLayoutOutletContext`, definido em `MainLayout.tsx`) em vez de subir
    o estado do diálogo para um store global ou um search param — os dois
    reabririam o diálogo sozinhos depois de um refresh.
  - **Histórico de revisões em ordem decrescente.** `ReviewTimeline.tsx` usa
    `data.attributes.toReversed()` (não `.reverse()` — o array vive no cache
    do React Query; mutar o cache diretamente seria um bug clássico de
    referência compartilhada) para mostrar a decisão mais recente primeiro.
  - **Alinhamento do sidebar.** `translate-x-2` deslocava o **conteúdo**
    pintado do botão, não a caixa em si — o `hover:bg-*`, que pinta a caixa,
    deixava uma faixa sem destaque à esquerda da linha. Trocado por `pl-2`
    (padding real, parte do box model) no modo expandido. No modo trilho
    (`collapsible=icon`), a correção precisou de uma segunda rodada: a
    primeira tentativa centralizava o ícone **dentro** do próprio botão de
    32px (que já se autocentra, sem folga, com o `p-2!` do variant), quando o
    `translate-x-2` original na verdade centralizava o **botão inteiro**
    dentro do trilho de 48px — `(48-32)/2 = 8`, o valor exato do
    `translate-x-2`. A correção certa foi mover `justify-center` para o
    `<li>` pai (`SidebarMenuItem`). **Sem verificação visual em nenhuma das
    duas rodadas** — só aritmética de box model contra o CSS gerado, e as
    duas rodadas dessa aritmética **discordaram entre si** antes de
    convergir (ver pendências).
  - Verificação (Task 10, três rodadas): `npx vitest run` ×3 — **240 testes
    em 44 arquivos**, todos verdes nas três rodadas oficiais, flake do
    `ResizeObserver` (ver pendências) ausente nas três; `npx tsc -b --noEmit`
    (exit 0); `npm run lint` (0 erros, 0 warnings); `npm run build` (ok;
    bundle **559,51 → 560,74 kB**, +1,23 kB — aviso de chunk > 500 kB
    pré-existente).
  - **Achado maior que o ciclo, registrado como pendência:** o cliente HTTP
    do frontend (`src/lib/api.ts`) não tem timeout configurado, e não existe
    `AbortController` em lugar nenhum de `src/`. Apareceu porque a Task 2
    chegou a propor um "gate" que impedia fechar o diálogo de pagamento
    enquanto a mutação estava pendente — e esse gate foi **revertido** ao se
    perceber que, sem timeout nem cancelamento, uma requisição travada
    deixaria o modal permanentemente sem fechar. Hoje isso não morde (nada
    bloqueia a UI esperando resposta), mas é a mesma lacuna que tornou o gate
    perigoso. Ver pendências.
  - **A fixture compartilhada do histórico de revisões não era cronológica**
    enquanto mockava um contrato (UC-013) que diz que é. Reordenada em
    `src/test/msw/handlers.ts`, com um comentário amarrando a ordem ao
    UC-013.
  - **Dois fluxos de diálogo (excluir, criar) sem cobertura automatizada do
    caminho real do usuário** ("clicar → diálogo fecha → botão continua
    ocupado até a rota assentar"). O jsdom desmonta o `Presence` do Radix
    Dialog de forma síncrona (sem engine de CSS para a animação de saída),
    então o estado ocupado desaparece antes de qualquer polling conseguir
    observá-lo. Os testes desses dois fluxos dirigem o router diretamente
    (`router.navigate()`) em vez de simular o clique real, e dizem isso no
    nome/comentário do teste — uma regressão futura só na interação
    fechar-diálogo↔navegar não seria pega.
  - ~~**Não validado em navegador nesta sessão.**~~ **VALIDADO em 2026-08-03,
    sem ressalvas.** A Task 10 rodara sem navegador disponível; a passada
    aconteceu depois e cobriu o spinner durando até o histórico atualizar (o
    pedido que originou o ciclo), o card de pendentes **não** seguindo o filtro
    de status, o alinhamento dos ícones no modo trilho, "Nova solicitação"
    reabrindo o diálogo zerado e os diálogos resetando ao cancelar.
    **Isto fecha o alinhamento do sidebar**, cujas duas rodadas de aritmética
    de box model se contradisseram e nenhuma tinha sido observada.
    **O ledger de execução foi removido no fechamento**, conforme
    o fluxo — o registro agora é o histórico do Git, e os itens do checklist
    que importam estão resumidos abaixo.
  - **A revisão da branch inteira achou quatro coisas que nenhuma revisão por
    task podia ver**, todas corrigidas em `6c63ff5`:
    - **A correção do sidebar era uma regressão disfarçada.** O `pl-2` que
      substituiu o `translate-x-2` **duplica** o `p-2` que o
      `SidebarMenuButton` já traz da base do shadcn — o `twMerge` mantém os
      dois e o CSS gerado dá a ambos os mesmos 8px. O deslocamento era 8+8=16px
      e virou 8px, desalinhando os itens habilitados do item "em breve" e do
      avatar do cabeçalho, que seguiram em 16px. Corrigido para `pl-4`. O
      revisor chegou nisso compilando a saída real do Tailwind, não raciocinando
      sobre as classes no abstrato.
    - **A regra de "resetar ao fechar" foi aplicada a dois dos TRÊS diálogos.**
      O `PayRefundDialog` continuava resetando só no sucesso, e é montado
      incondicionalmente — depois de um pagamento que falha, reabrir mostrava o
      erro anterior e o arquivo já escolhido.
    - **Um erro podia ser escrito depois de ser limpo.** Fechar o
      `RefundFormDialog` com a criação em voo e ela falhar depois gravava
      `submitError` *após* a limpeza do fechamento, e nada limpava na abertura —
      então o botão "Nova solicitação" da tela de sucesso, criado neste mesmo
      ciclo, abriria um formulário em branco com um banner velho.
    - **Um rótulo declarava metade do próprio escopo.** "Solicitações (Pago)"
      cobria o filtro de status mas não a busca por nome, embora o `total` seja
      estreitado pelos dois.
  - **Nota de implementação:** a regra de lint `set-state-in-effect` bloqueou o
    `useEffect` óbvio para limpar o erro na abertura dos diálogos. A saída foi o
    padrão documentado do React de ajustar estado durante o render comparando
    com o valor anterior (`wasOpen`) — que tem a vantagem de a limpeza entrar no
    mesmo commit, sem um quadro de banner velho visível, coisa que um efeito
    pós-paint não garantiria.

- **Incremento fora de ciclo — spinner nas setas de paginação da Home:
  CONCLUÍDO e MESCLADO.** Branch `feat/pagination-busy-state`, um commit
  (`d33fb65`), 246 → **249 testes**, `tsc` exit 0, lint 0/0. **Validado em
  navegador em 2026-08-03** (a seta da direita gira sozinha ao paginar; a busca
  não gira nenhuma das duas) e **mesclado na `main` por fast-forward**
  (`6c63ff5..d33fb65`) no mesmo dia. Verificação repetida depois do merge:
  249 testes em 44 arquivos, `tsc` exit 0, lint 0/0, bundle 560,88 kB.

  **Feito deliberadamente sem o fluxo completo** (sem brainstorming, spec,
  plano nem subagentes): é uma mudança de um par de botões, seguindo o padrão
  de spinner que o ciclo anterior acabou de estabelecer. Fica registrado como
  precedente — se em retrospecto tiver sido leve demais para o gosto do
  Gabriel, é aqui que a decisão está.

  O que faz: cada seta mostra spinner e `aria-busy` **só quando é ela** que
  está carregando. Trocar de página é navegação do router (o clique reescreve
  os search params e o loader rebusca), então o estado vem de
  `useNavigation()`, não do React Query. A seta que gira é decidida comparando
  a página de `navigation.location` com a página atual, **não** por
  `navigation.state !== "idle"` — isso diz qual das duas gira e impede que uma
  navegação que não muda de página (a busca com debounce) acenda alguma. Essa
  segunda parte evita, por construção, a armadilha que a revisão da branch
  anterior encontrou no `RefundFormDialog`.

  **Dois defeitos que os testes pegaram, e que valem mais que a feature:**
  - A comparação era contra `data.page` (resposta da API) em vez de `page` (do
    loader). Os dois coincidem quando tudo funciona — o bug ficaria dormindo em
    produção. Só o segundo é derivado da URL nos dois lados; `data` pode estar
    servindo a página anterior durante a transição.
  - Um dos três testes **passava pelo motivo errado**: esperava o estado do
    router e então olhava o DOM, mas o React ainda não tinha re-renderizado, de
    modo que a asserção via um render velho e passaria com qualquer
    implementação. Descoberto ao quebrar a lógica de propósito e ver o teste
    continuar verde. Ancorado no `disabled`, que muda de forma observável
    durante qualquer navegação.

  O fixture da listagem em `PageHome.test.tsx` responde `page: 1` a uma
  requisição de página 2, contradizendo o contrato que mocka — os testes novos
  usam um handler local que ecoa a página pedida. **O fixture original segue
  desonesto** para os demais testes do arquivo; é a mesma classe de problema
  que o ciclo anterior corrigiu na fixture de reviews, e não foi corrigida aqui
  porque ela é consumida por muitos testes.

- **Fase 3, Item 11 — Error boundaries e recuperação: CONCLUÍDO.**
  Primeiro item da trilha depois de dez ciclos de feature, na branch
  `feat/error-boundaries` do `Refund-FrontEnd`, partindo de `6c63ff5`.
  **Não mesclada** — aguarda autorização. Detalhes no
  [diário](../learning-path-progress.md). O ponto de partida era melhor do que
  a trilha assumia: `router.tsx` já tinha `ErrorBoundary: PageRouteError` na
  rota raiz, com teste. As três lacunas reais eram outras:
  - **Tela branca acima do router.** `QueryClientProvider`, `AuthProvider` e
    `ThemeEffect` renderizavam sem cobertura nenhuma. Nasce
    `src/components/core/AppErrorBoundary.tsx` (class component — a API do
    React não tem equivalente em hook), ligado no `main.tsx` **por fora do
    `QueryClientProvider`**, cobrindo tudo. Fallback sem `<Link>`, porque ali
    não há router: a recuperação é recarregar o documento.
  - **O boundary único derrubava o shell.** Nasce
    `src/components/core/ContentError.tsx`, preso a uma rota **sem path,
    abaixo** do `MainLayout` — porque o `ErrorBoundary` do React Router
    renderiza **no lugar do elemento da rota à qual está preso**, e pô-lo no
    `MainLayout` levaria sidebar e topbar junto. Agora o erro preenche só o
    `Outlet`.
  - **Não havia retry.** `PageRouteError` ganhou "Tentar novamente" via
    `useRevalidator`, ao lado do link. Medido: `revalidate()` recupera
    **tanto** erro de loader quanto de render — o plano registrava isso como
    hipótese em aberto, e a hipótese pessimista estava errada.
  - `getErrorMessage` virou `getRouteErrorMessage` em `src/lib/route-error.ts`
    ao aparecer o **segundo uso real**, que é o gatilho de extração definido
    pelo próprio `learning_path.md`.
  - Verificação: baseline medido antes de abrir a branch (246 testes / 44
    arquivos, `tsc` 0, lint 0/0, bundle 560,88 kB). Depois: `npx vitest run`
    ×3 → **256 testes em 46 arquivos**, verdes nas três, saída salva em
    arquivo antes de ser lida; `tsc` exit 0; lint **0/0**; build ok, bundle
    **562,61 kB** (+1,73 kB). Flake do `ResizeObserver` ausente nas três.
    Dois testes validados por **quebra deliberada**, não só por passarem.
  - **VALIDADO EM NAVEGADOR em 2026-08-05**, pelo Gabriel, contra a API real,
    nos três pontos e **sem ressalvas**: (1) com o backend derrubado, o erro do
    `homeLoader` preencheu só a área de conteúdo, com sidebar e topbar
    intactos e navegáveis; (2) com o backend de volta, "Tentar novamente"
    mostrou o estado ocupado e recuperou a lista **sem sair da página** nem
    mudar a URL; (3) com os dados do site bloqueados no DevTools, apareceu a
    tela "Algo deu errado" com "Recarregar a página" — **não** a tela branca.
    O ponto (3) é o que motivou o item inteiro e o único que a suíte não
    alcança.
  - ~~**Limitação registrada:** o gatilho real da primeira lacuna
    (`localStorage` bloqueado) não foi observado — o jsdom não reproduz. A
    suíte prova que um filho que lança produz o fallback, não que *aquele*
    filho lança naquele cenário. Ver pendências.~~ **Fechada pela validação
    acima** — o cenário foi observado no navegador.

- **Fase 3, Item 14 — i18n com bootstrap assíncrono: CONCLUÍDO.**
  Na branch `feat/i18n` do `Refund-FrontEnd`, partindo de `887cd45`. Fecha o
  Item 14; dois catálogos **completos** (`pt-BR` e `en-US`), 97 chaves cada,
  com paridade garantida por teste e não por inspeção. Detalhes no
  [diário](../learning-path-progress.md). O que mudou:
  - **`src/lib/i18n.ts`** carrega um catálogo por vez, sob demanda; o
    `main.tsx` **espera** o catálogo antes do primeiro render (o bootstrap que
    dá nome ao item). Catálogo que falha ainda renderiza, mostrando chaves
    cruas — ruim, mas diagnosticável, contra tela branca.
  - **`src/test/i18n.ts` faz o oposto: init síncrono**, com os dois catálogos
    estáticos. Testes renderizam sem passar pelo bootstrap. Como o `pt-BR`
    fica ativo e tem as mesmas strings, **as 260 asserções existentes passaram
    sem edição** — o contrário do que a apresentação do item previu.
  - **Locale na store `ui.ts`** (junto do tema, persistido) e alternador na
    Topbar.
  - **Quatro módulos avaliados na importação** (`nav-items`, `status`,
    `categories`, schemas Zod) passaram a guardar **chave**, não texto.
  - **`format.ts` lê o idioma ativo**; `ReviewTimeline` parou de formatar data
    inline, fechando uma inconsistência **pré-existente** (ele furava o
    `formatDate` e não tinha a guarda de data inválida nem o `timeZone`).
  - **`Accept-Language`** em toda requisição — o backend **ignora** hoje; é
    preparação declarada como tal.
  - **`PageComponents` ficou deliberadamente fora**, com o motivo no topo do
    arquivo: vitrine do design system, com rótulo de amostra e dado fictício.
  - Verificação: baseline medido antes da branch (260 testes em 46 arquivos,
    `tsc` 0, lint 0/0, bundle 562,61 kB). Depois: **274 testes em 48
    arquivos**, verdes em três rodadas; `tsc` 0; lint **0/0**; build ok,
    bundle **606,92 kB** (+44,31 kB, o runtime do i18next). Os catálogos saem
    como **chunks separados** (`pt-BR` 4,17 kB, `en-US` 3,86 kB), então quem
    não troca de idioma não baixa o outro.
  - **VALIDADO EM NAVEGADOR em 2026-08-05**, pelo Gabriel, contra a API real e
    **sem ressalvas**, contra um checklist de 6 pontos: ausência de flash no
    reload, troca sem recarregar, data e moeda acompanhando o idioma, download
    do chunk do outro catálogo só na troca, o plural em zero, e as mensagens
    de validação traduzidas. **Registro honesto do alcance:** o Gabriel
    confirmou o checklist como um todo ("aprovado e checado"), não item a item
    em separado; sabe-se que os seis pontos foram apresentados e aceitos.
  - **Achado que quase virou regressão silenciosa:**
    `Intl.PluralRules("pt-BR").select(0)` devolve `"one"` — o CLDR classifica
    zero como **singular** em português. Migrar o ternário para `_one`/`_other`
    teria mudado a tela vazia de "0 solicitações" para "0 solicitação", em
    silêncio e tecnicamente correto. O i18next consulta um `_zero` explícito
    antes do CLDR, então a redação foi preservada de propósito, com teste
    afirmando as duas coisas. **Adotar um padrão não é neutro.**

- **Fase 3, Item 15 — Motion com propósito: CONCLUÍDO e MESCLADO.**
  Em duas branches empilhadas do `Refund-FrontEnd`: `feat/motion` (camada de
  reduced-motion) e `feat/motion-animations` sobre ela (as quatro animações),
  partindo de `887cd45`. (Este documento afirmou até 2026-08-07 que nenhuma das
  duas tinha sido mesclada; já tinham.) Detalhes no
  [diário](../learning-path-progress.md).
  - **O levantamento inverteu o enquadramento do item.** Não havia animação
    gratuita para remover: quase todo o movimento vem do design system
    (Radix/shadcn) e é razoável. O que faltava era a camada que respeita
    `prefers-reduced-motion` — `grep -rn "reduced-motion" src/` não devolvia
    nada.
  - **Neutraliza movimento, preserva opacidade.** As keyframes do
    `tw-animate-css` leem `--tw-*-translate/scale/rotate` com fallback (lido do
    CSS **gerado**, não suposto), então devolvê-las à identidade remove o
    deslocamento e mantém o fade. Spinners param: rotação contínua é a pior
    categoria (WCAG 2.2.2) e `aria-busy` + rótulo já carregam o estado.
  - **Quatro animações novas**, a pedido do Gabriel: timeline (item novo
    desliza **e abre espaço**, via `grid-template-rows: 0fr → 1fr` — `height:
    auto` não é animável), badge pulsando na mudança de status, entrada
    escalonada da tabela só na primeira montagem, e fade nos três banners de
    **submissão** (os de falha de carregamento ficaram de fora de propósito).
  - **Sem biblioteca.** `framer-motion` custaria ~40 kB num bundle já acima do
    aviso. O custo real foi **+1,93 kB de CSS e +1,02 kB de JS**.
  - Verificação: baseline 274 testes em 48 arquivos → **287 em 51**, verdes em
    três rodadas; `tsc` 0; lint **0/0**; build ok.
  - `react-hooks/refs` desligada **por arquivo, pelo nome**, para
    `src/hooks/useEnteredItems.ts`, seguindo o precedente do `eslint.config.js`.
    Diretiva inline não serve: a regra segue o valor pelo alias local.
  - **Validado em navegador em 2026-08-05.** Badge, timeline, tabela e banners
    conferidos e funcionando. **Duas ressalvas registradas abaixo:** o flick da
    Home não foi resolvido, e a emulação de `prefers-reduced-motion` não foi
    confirmada explicitamente.

- **Fase 3, Item 16 — Pipeline de qualidade: CONCLUÍDO e MESCLADO. Fecha a
  FASE 3.**
  Na branch `feat/ci` de **ambos** os repositórios — o primeiro item a produzir
  artefato nos dois ao mesmo tempo. (Este documento afirmou até 2026-08-07 que
  nenhuma das duas tinha sido mesclada; já tinham.) Detalhes no
  [diário](../learning-path-progress.md).
  - **CI em GitHub Actions** rodando as verificações que os `AGENTS.md` já
    exigiam: `typecheck`/`lint`/`test`/`build` no frontend, `pytest`/`pylint
    src` no backend, a cada push, do mais barato ao mais caro.
  - **Oxlint DELIBERADAMENTE PULADO**, com número: o ESLint leva 2,1 s aqui; o
    gargalo é o Vitest com 9,8 s, que o Oxlint não toca. Decisão do Gabriel.
  - **O portão foi visto fechar:** um erro de tipo deliberado reprovou em 23 s
    (contra 2m11s do verde), com `lint`/`test`/`build` sequer executando.
  - Script `typecheck` separado no frontend (antes só existia dentro do
    `build`), como a trilha pede.
  - **Falta branch protection.** O CI reporta mas **não bloqueia** — ainda é
    possível empurrar com o CI vermelho. É configuração de painel do GitHub
    (Settings → Branches), não do YAML.

- **Fase 4, Item 17 — Configuração tipada com pydantic-settings: CONCLUÍDO.**
  Primeiro item da **Fase 4**, na branch `feat/typed-settings` do `Refund-api`
  (`71e5363..c10a2db`, 2 commits). **Mesclada na `main` por fast-forward e
  empurrada em 2026-08-07**, com verificação repetida depois do merge (249
  testes em três rodadas, `pylint src` exit 0). Detalhes no
  [diário](../learning-path-progress.md) e na
  [ADR-004](../decisions/ADR-004-typed-settings.md). O que mudou:
  - **`src/configs/settings.py`** (novo) com `Settings(BaseSettings)`.
    `DATABASE_URL` e `JWT_SECRET` são as duas únicas obrigatórias; o resto tem
    default. `global_config.py` e o `load_dotenv()` foram **removidos**.
  - **O modo de falha que justificava o item, medido antes:** sem `JWT_SECRET`
    a aplicação **subia saudável** (`/health` respondia `ok`) e quebrava com
    `TypeError: Expected a string value` no **primeiro login de um usuário**.
    Agora não sobe, com `ValidationError` nomeando `jwt_secret`.
  - **`SecretStr`** no segredo de JWT — `repr(settings)` imprime
    `**********`, e ler o valor exige `.get_secret_value()` explícito.
  - **`environment`** (`local`/`test`/`production`, default `local` — nunca
    `production` por omissão) e **`CORS_ORIGINS` por configuração**, com um
    `model_validator` que **recusa o startup** se `production` trouxer `*`,
    `localhost` ou `127.0.0.1`.
  - **Engine do SQLAlchemy preguiçoso.** `build_engine(url)` +
    `get_engine()`/`get_session_factory()` memoizados com `lru_cache(maxsize=1)`.
    Importar a aplicação deixou de exigir banco configurado. O teste de pool
    passou a construir o engine com URL literal, o que o deixou melhor: testa a
    tunagem de pool sem depender de ambiente.
  - **As variáveis fictícias saíram do `ci.yml`** e foram para um `conftest.py`
    na raiz. Como variável de ambiente vence o `.env` no pydantic-settings, a
    suíte roda com config fictícia **inclusive numa máquina com `.env` real** —
    ou seja, não alcança o banco real por acidente. Também roda para quem
    clonou sem `.env`.
  - **Uma premissa do plano estava errada e foi corrigida antes de implementar:**
    o engine preguiçoso **sozinho** não bastava para tirar as variáveis do CI.
    Dois testes exigiam config real no import por motivos alheios ao engine
    (`..._pool_test.py` importava o `engine` global; `jwt_handler_test.py` usava
    `jwt_info["KEY"]`). Achado lendo os testes antes de escrever código.
  - **O engine preguiçoso criou uma dívida, achada depois do primeiro commit e
    corrigida.** Construir o engine no import era a **única coisa que parseava
    a `DATABASE_URL`**; adiá-lo fazia uma URL malformada deixar de impedir o
    startup e virar 500 na primeira requisição — o modo de falha que o item
    existe para eliminar, reintroduzido pela porta dos fundos. Corrigido com um
    `field_validator` chamando `make_url` na `Settings` (só parseia, sem pool e
    sem rede), não desfazendo o engine preguiçoso. **Achado porque o Gabriel
    pediu uma explicação mais funda do conceito**, não pela suíte nem pelos 12
    cenários manuais.
  - **Um teste tentado e abandonado:** rede de proteção para `lock_timeout` em
    `connect_args`. O SQLAlchemy só os aplica ao abrir conexão real, então um
    engine que nunca conecta não os expõe. A prova daquele parâmetro continua
    sendo o `SHOW lock_timeout` manual.
  - Verificação: `pytest` **249 passed** (partiu de 235), `pylint src` 10.00/10
    com **exit 0**, e **13 cenários manuais** — startup sem config, startup só
    com `DATABASE_URL`, startup com `DATABASE_URL` malformada, suíte com o
    `.env` escondido (249 verdes), `/health`,
    CORS com origem permitida e com origem estranha, registro + login + rota
    autenticada (201 → token → 200), a guarda de produção recusando e aceitando,
    e `alembic current`.
  - **Não validado em navegador** — o item não muda nenhuma tela. O frontend
    não foi tocado.

- **Fase 4, Item 19 — PostgreSQL como referência de produção: CONCLUÍDO.**
  Na branch `feat/integration-tests` do `Refund-api` (`4e7aece..a8e8fa8`, 1
  commit). **Mesclada na `main` por fast-forward e empurrada em 2026-08-07**,
  com verificação repetida depois do merge (249 + 19 testes, `pylint src` exit
  0). Detalhes no
  [diário](../learning-path-progress.md); a [ADR-002](../decisions/ADR-002-postgresql-neon.md)
  foi amendada. O que mudou:
  - **A premissa escrita na trilha estava morta.** O item diz "o README orienta
    SQLite local"; não orienta há meses (ADR-002). Sobrava só resíduo:
    **`aiosqlite` no `requirements.txt` sem nenhum import**, agora removido.
    O item virou a outra metade — "PostgreSQL em container para integração".
  - **`docker-compose.yml`** com PostgreSQL **18-alpine em `tmpfs`**, porta
    5433, fixado na mesma versão maior que produção (o Neon reporta **18.4**,
    verificado por `show server_version`).
  - **Duas suítes separadas por marker** (`pytest.ini`): `pytest` continua
    sendo 249 testes em 4,2s **sem Docker**; `pytest -m integration` roda os 19
    novos. Ninguém é obrigado a instalar Docker para trabalhar no projeto.
  - **Fecha a pendência do ciclo `upgrade`/`downgrade` das migrations** — 4
    testes, incluindo um que desce **revisão por revisão** e outro que afirma
    que o schema migrado **não tem diff de autogenerate** contra as entidades.
  - **Fecha a pendência do `lock_timeout` sem teste comportamental** — 4 testes:
    o parâmetro **chega ao servidor** (`SHOW lock_timeout` = `3s`, antes só
    provado à mão), a contenção de linha **desiste** em vez de esperar para
    sempre, o lock é **liberado**, e linhas **diferentes não bloqueiam** entre
    si. Determinístico de propósito: uma transação segura o lock e a outra tem
    um único desfecho — não é uma corrida.
  - **7 testes de repository reais** — id gerado por sequência, `UNIQUE` de
    e-mail, `server_default` do schema, FK para usuário inexistente, agregados
    computados pelo PostgreSQL, o JOIN do `user` aninhado e a contagem de linhas
    da exclusão.
  - **`DatabaseConnectionHandler` aceita um `session_factory` opcional**
    (default inalterado), que é o que permite apontar os repositories reais para
    o banco descartável sem variável de ambiente global.
  - **`alembic/env.py` respeita uma URL já fornecida** pelo chamador, em vez de
    sobrescrever sempre com a `settings.database_url` — é assim que os testes
    apontam o Alembic para o banco descartável sem afetar mais nada.
  - **CI ganhou um segundo job** com `services: postgres`, em paralelo ao
    primeiro. O `pytest` mockado continua não precisando de banco.
  - **O portão foi visto fechando:** removendo o `connect_args` do
    `build_engine`, 2 testes falham em 15,5s; restaurado, 4 verdes. Os 15,5s são
    a guarda `asyncio.wait_for` funcionando — **um teste que trava na regressão
    é pior que teste nenhum**, e a primeira versão travava.
  - **Quatro correções que o banco real impôs** a testes escritos contra
    interfaces supostas: `select_user_by_*` devolve `dict`; `select_refunds`
    devolve **tupla**; `insert_user` traduz `IntegrityError` em
    `HttpBadRequestError` enquanto `insert_refund` deixa propagar; e
    `count_by_status` é um `GROUP BY` que só devolve status **com linhas** — a
    garantia das quatro chaves do `UC-014` mora no controller, não no
    repository.
  - Verificação: `pytest` **249 passed, 19 deselected** (3 rodadas),
    `pytest -m integration` **19 passed** (3 rodadas), `pylint src` **exit 0**,
    e a mensagem de container ausente conferida ("Is it up? Run: docker compose
    up -d").
  - **O CI foi visto rodando os dois jobs**, no push de 2026-08-07 (run
    `31209765881`): `verify` **success** (249 passed, 19 deselected) e
    `integration` **success** (19 passed, 249 deselected), em paralelo, 54s e
    42s. Conferido na **saída**, não só no status verde — um job pode passar
    tendo rodado zero teste se a filtragem por marker estiver errada, e as duas
    linhas de `collected 268 items / … selected` provam que cada job rodou
    exatamente a metade que devia.
  - **Não validado em navegador** — o item não toca nenhuma tela.

- **Fase 4, Item 21 — Consistência entre banco e arquivo: CONCLUÍDO.**
  Na branch `feat/file-consistency` do `Refund-api` (`f3e617e..f7940e0`, 1
  commit). **Mesclada na `main` por fast-forward e empurrada em 2026-08-07**,
  com verificação repetida depois do merge (258 + 23 testes, `pylint src` exit
  0). Detalhes no
  [diário](../learning-path-progress.md); a
  [ADR-003](../decisions/ADR-003-local-receipt-storage.md) foi amendada.
  - **São cinco call sites, não dois.** A trilha cita criação e exclusão de
    reembolso; o levantamento achou também upload de avatar, remoção de avatar
    e o pagamento — este último **já tinha a compensação completa**, escrita no
    ciclo de 2026-07-30. O item virou "aplicar aos quatro que ficaram para
    trás", não "inventar a solução".
  - **A ordem já estava certa nos cinco** e não foi tocada. Faltava o
    tratamento da falha.
  - **Duas falhas distintas.** (A) arquivo órfão quando a escrita no banco
    falha — criação e upload de avatar. (B) **500 numa operação que deu certo**
    — na exclusão, um `os.remove` que levanta derrubava a resposta *depois* de
    a linha já ter sido apagada e commitada; o usuário via erro e, ao tentar de
    novo, 404. **Esta segunda ninguém tinha nomeado.**
  - **A regra: antes do commit desfaça, depois do commit registre.** Derrubar
    uma resposta correta por causa de um arquivo sobrando troca um problema
    pequeno por um grande.
  - **A fronteira é o commit, não o fim do método.** `insert_refund` já dá
    commit, então a compensação da criação cobre **só o insert** — esticar o
    `try` para incluir a releitura apagaria o comprovante de um reembolso real.
    Mesma fronteira que a flag `committed` do pagamento já marcava. Há teste
    dedicado, e ele falha quando o `try` é esticado.
  - **Primeira linha de log do projeto.** `src/controllers/file_cleanup.py`
    centraliza a deleção best-effort e emite `logging.warning` com o nome do
    arquivo. `logging` é stdlib. O **Item 24** depois troca a configuração
    (JSON, `request_id`) e estas chamadas passam a sair estruturadas — serão
    refinadas para mover o filename para campo próprio, mas não precisam
    esperar por isso. Centralizar evitou três cópias do mesmo `try/except`, e
    `R0801` já reprovou este projeto uma vez.
  - **Quatro quebras deliberadas**, todas pegas: remover a compensação da
    criação (1 falha), `delete_quietly` voltar a propagar (**6 falhas** em 4
    arquivos), esticar o `try` para depois do commit (2 falhas, inclusive o
    teste da fronteira) e a versão de integração da primeira — que falha
    **mostrando o órfão pelo nome** (`assert ['ce2180ea-…png'] == []`).
  - **Essa última evidência não era possível antes do Item 19.** "Não sobrou
    arquivo no disco" só era verificável listando o diretório à mão.
  - **O que continua descoberto:** `SIGKILL` entre o `save()` e o commit.
    Nenhuma compensação em processo resolve — exige varredura ou fila
    (Item 28).
  - Verificação: `pytest` **258 passed, 23 deselected** (3 rodadas, partiu de
    249), `pytest -m integration` **23 passed** (3 rodadas, partiu de 19),
    `pylint src` **exit 0**.
  - **Não validado em navegador** — o item não toca nenhuma tela.

- **Fase 4, Item 22 — Object storage e URLs assinadas: CONCLUÍDO.**
  O maior item da sessão, e o primeiro desde o Item 16 a produzir artefato nos
  **dois** repositórios: `feat/object-storage` no `Refund-api`
  (`193299a..6130594`) e `feat/signed-file-urls` no `Refund-FrontEnd`
  (`dc1f30a..5928f4c`). **As duas mescladas por fast-forward e empurradas em
  2026-08-07**, com verificação repetida depois de cada merge.

  **MESCLADO SEM VALIDAÇÃO EM NAVEGADOR, por decisão explícita do Gabriel** —
  ele optou por validar depois. O checklist de 7 pontos segue aberto nas
  pendências e continua sendo a próxima coisa a fazer; as duas `main` já
  carregam o contrato novo, então validar deixou de ser "antes de mesclar" e
  virou "antes de confiar". Detalhes no
  [diário](../learning-path-progress.md); a
  [ADR-003](../decisions/ADR-003-local-receipt-storage.md) foi amendada de novo
  e `UC-010`/`UC-011`/`UC-012` também.
  - **`S3FileStorage`** entrou sem tocar em **nenhum** controller — o
    `read() -> bytes` escrito dois ciclos antes, com um comentário citando este
    item, é o que pagou por isso. Um bucket, três prefixos; a coluna do banco
    segue guardando o **nome**, não a chave, então trocar de backend não
    reescreve linha nenhuma. `NoSuchKey` é traduzido para `FileNotFoundError`.
  - **Fecha o bloqueio nº 3 do primeiro deploy**, o pior dos cinco: disco
    efêmero perdia comprovante em silêncio. **Restam dois** (Dockerfile e
    branch protection).
  - **As três rotas de arquivo devolvem `{"url", "media_type"}`**, não bytes —
    porque uma tag `<img>` não envia `Authorization: Bearer`, que era a razão
    de o frontend baixar tudo por XHR e montar Blob.
  - **O backend local também assina**, senão haveria dois contratos e ninguém
    estaria testando o que roda. JWT de vida curta com `(storage, filename)`,
    servido por `GET /files/{storage}/{filename}` — mesmo `jwt_secret`, mesmo
    `JwtHandler`, zero dependência nova. A rota confere que o token é **daquele
    arquivo** (sem isso, um token válido leria todos) e recusa nome com
    separador de caminho. **As duas guardas provadas por quebra deliberada.**
  - **Trade-off de segurança declarado:** a rota autenticada reconferia a
    autorização **a cada requisição**; a URL assinada **congela** a decisão por
    `FILE_URL_TTL_SECONDS` (300s). O que separa isso da URL pública que a
    ADR-003 removeu é o prazo. A autorização em si não mudou de lugar.
  - **Comportamento perdido de propósito:** "arquivo sumiu do disco" deixou de
    ser 404 nessas rotas. O `payment-receipt` tinha quatro caminhos de 404
    idênticos; o quarto mudou de lugar. Os três que importam seguem intactos.
  - **MinIO no `docker-compose.yml`** (portas 9100/9101 — a 9000 já estava
    ocupada) e no CI **por `docker run` num step**, não por `services:` —
    service container não sobrescreve o `command` da imagem, e o MinIO precisa
    de `server /data`. Um bloco `services:` com `--entrypoint` foi escrito
    primeiro e descartado: teria subido um shell que sai na hora.
  - **Achado que só apareceu ao fazer o frontend:** eu tinha feito as rotas
    devolverem só `{"url"}`, e o `ReceiptPreview` decide `<img>` vs `<object>`
    por tipo — que uma URL não carrega. `media_type` voltou à resposta.
    **Fazer o backend inteiro antes de olhar o consumidor escondeu um campo
    faltando.**
  - **`useObjectUrl` foi APAGADO** (com seu teste): sem Blob, não há object URL.
    O comentário dele justificava a camada compartilhada "porque o ciclo da
    foto de perfil vai precisar" — deixou de valer no mesmo commit, já que
    avatares também viram URL.
  - Verificação: `pytest` **277 passed, 32 deselected**, `pytest -m integration`
    **32 passed**, `pylint src` **exit 0**; no frontend `npx vitest run`
    **283 passed em 51 arquivos** (3 rodadas), `tsc` exit 0, lint **0/0**,
    build ok (606,92 → **607,87 kB**). Os testes de integração baixam a
    presigned URL com **urllib** (que não sabe nada de AWS), confirmam que sem
    assinatura o objeto é recusado, e confirmam que ela **expira**.

- **Fase 4, Item 23 — Erros padronizados com Problem Details: CONCLUÍDO.**
  Em dois repositórios, ambos na branch `feat/problem-details`
  (`fbe7ff6..a62ce26` na api, `5928f4c..8e02f72` no frontend). **As duas
  mescladas por fast-forward e empurradas em 2026-08-09.** Detalhes no
  [diário](../learning-path-progress.md) e na
  [ADR-005](../decisions/ADR-005-problem-details.md).
  - **Três handlers globais, ZERO dos 38 raise sites tocados.** O formato de
    erro passou a ser decidido num lugar; `error_handler` e os controllers
    continuam levantando o mesmo de antes.
  - **`detail` continua sempre string** — é string na RFC também, e é isso que
    fez a migração **não ter momento quebrado**: os 7 call sites do frontend
    seguiram funcionando antes mesmo da mudança do lado deles, inclusive para
    os erros de validação que antes chegavam como lista.
  - **`type` fica em `about:blank`** (o valor que a RFC usa para "sem código
    mais específico que o status"). Códigos por erro entram quando houver
    consumidor — mesma regra de "extrair no segundo uso" do Item 11.
  - **`request_id`** no corpo e no header `X-Request-Id`, sempre **gerado pela
    API**, nunca lido de header do cliente (log forging). O **Item 24** reusa
    esse id nos logs.
  - **Bug achado contra a API rodando:** `@app.exception_handler(HTTPException)`
    com a classe do FastAPI **não pega o 404 do router**, que levanta a do
    Starlette. Registrado na base, que cobre as duas.
  - **Bug achado por medição:** no 500 o `request_id` estava no corpo e **não
    no header** — a exceção sobe passando pelo middleware antes de o handler
    rodar. Corrigido fazendo o próprio envelope marcar a resposta, o que
    independe de ordenação de middleware.
  - Verificação: `pytest` **295 passed** (partiu de 277), `pylint` exit 0;
    frontend **289 passed** (3 rodadas, partiu de 283), `tsc` 0, lint 0/0,
    build ok. Os quatro caminhos de erro conferidos **contra a API rodando**.

- **Fase 4, Item 24 — Logs estruturados e request ID: CONCLUÍDO.**
  Na branch `feat/structured-logs` do `Refund-api` (`a62ce26..160e1cc`), só
  backend, **empilhada sobre o Item 23** — um único fast-forward levou as duas.
  **Mesclada e empurrada em 2026-08-09.** Detalhes no [diário](../learning-path-progress.md) e na
  [ADR-006](../decisions/ADR-006-structured-logging.md).
  - **Cumpre a promessa do Item 23:** o `request_id` do corpo do erro agora
    aparece nos logs. **Verificado contra a API rodando** — o `X-Request-Id` do
    header e o id da linha de log são iguais.
  - **JSON fora de `local`**, linha humana em desenvolvimento. Sem dependência
    nova (formatter de ~20 linhas; `python-json-logger` seria a terceira
    dependência recusada por esse motivo).
  - **`contextvar` + `logging.Filter`** para o id chegar a linhas que estão
    quatro camadas abaixo da rota e não têm o `Request`. A dúvida real —
    atravessa o `BaseHTTPMiddleware`? — foi medida, não suposta.
  - **Access log do uvicorn silenciado por SEGURANÇA:** ele grava a query
    crua, o que colocaria uma URL assinada válida do Item 22 no log.
    Silenciado no código, não no `run.py`, para valer com `uvicorn ...` direto.
  - **Nunca vão para o log:** corpo e headers. A query vai **mascarada**
    (`token`, `password`, `secret`), preservando o nome do parâmetro.
  - **A terceira quebra deliberada NÃO falhou** e revelou lacuna real: os
    testes provavam que o filtro funciona, nenhum provava que está
    **instalado**. Teste acrescentado. **Mesma classe de lacuna do Item 23** —
    duas vezes seguidas o buraco foi "testei a peça, não a montagem".
  - Verificação: `pytest` **317 passed** (partiu de 295), `pylint` exit 0, mais
    a API real nos dois formatos com o token mascarado nos dois.

- **SESSÃO DE VALIDAÇÃO EM NAVEGADOR — 2026-08-09.** Dezoito verificações,
  percorridas pelo Gabriel contra um checklist derivado destas pendências
  (Itens 22, 23, 24 e cinco pendências antigas). **Todas passaram**, com as
  ressalvas de alcance abaixo — e a sessão **encontrou dois bugs**, que é a
  justificativa retroativa para ela ter existido.

  **Alcance do registro, honestamente:** das 18, três têm evidência direta
  descrita pelo Gabriel (A1, A3, C1) e uma virou decisão (C4). As demais foram
  confirmadas **em bloco**, não uma a uma. É a mesma forma que o ciclo de
  2026-07-30 ficou registrado, e pela mesma razão: sabe-se que passaram, não o
  detalhe de cada uma.

  - **A1 — o núcleo do Item 22, confirmado.** A requisição que busca os bytes
    (`/files/receipts/….png?token=…`) chega **sem header `Authorization`**.
    Vale registrar que a instrução original do checklist era ambígua: existem
    **duas** requisições — a de metadados (`/refunds/79/receipt`, autenticada,
    devolve `{url, media_type}`) e a do arquivo. Só a segunda prova o item.
  - **A3 — passou, e o CHECK estava errado, não o código.** Ao abrir a tela
    cheia, requisições reaparecem no Network: é o `.png` servido do **cache**
    do navegador, porque o diálogo monta um segundo `<img>`. Eu havia escrito
    a expectativa herdada da versão com `blob:`, em que uma segunda tag com a
    mesma string não tocava a rede. Com URL HTTP real, tocar o cache é o
    comportamento correto — daí o `Cache-Control: private, max-age=60` da rota.
  - **C1 — pendência do contraste FECHADA com número: Lighthouse
    Accessibility 100**, sem violações. Era exatamente o que faltava: o
    checklist antigo tinha "parece legível" marcado por olho humano e a
    auditoria com ferramenta nunca.
    **Os 54% de Performance da mesma execução NÃO são sinal** e não devem ser
    citados como tal: a medição foi contra `npm run dev`, ou seja, módulos não
    minificados, sem bundling, com o cliente de HMR no meio. O número honesto
    exige `npm run build && npm run preview`. O assunto de performance que
    **existe de verdade** é outro: o bundle em ~608 kB com o aviso de chunk
    > 500 kB aberto desde o restyle — Item 31.
  - **C6 — o flick da Home NÃO REPRODUZIU.** Registrado como **não observado
    em 2026-08-09**, não como resolvido: ninguém identificou a causa, então
    ele pode ter mudado de condição em vez de desaparecer. Se voltar, o
    caminho continua sendo **medir** `scrollHeight` por frame — duas correções
    às cegas já falharam.

- **DOIS BUGS DE i18n ACHADOS NA VALIDAÇÃO DE 2026-08-09, corrigidos e
  mesclados** (`Refund-FrontEnd`, `fix/untranslated-validation-messages` e
  `feat/localized-file-input`, ambas na `main`). Os dois eram invisíveis à
  suíte e visíveis na primeira tela que o usuário usa.

  **1. A checagem de tipo do Zod roda antes das nossas mensagens.**
  `RefundFormDialog` e `PayRefundDialog` eram os **únicos** formulários do
  projeto sem `defaultValues`. Sem isso, um campo não tocado chega ao Zod como
  `undefined`, ele falha no **tipo** antes de alcançar
  `.min(1, "validation.nameRequired")`, e a mensagem de tipo é o default em
  inglês da biblioteca — **que nunca foi uma chave e portanto é intraduzível
  por construção**. Um envio vazio produzia **quatro** delas de uma vez (nome,
  valor, categoria e arquivo): o formulário inteiro em inglês numa UI em
  português.

  Corrigido nos dois lados, porque cada um sozinho deixa buraco:
  `defaultValues` para os campos chegarem como `""`, **e** mensagem na
  checagem de tipo — para `file` não existe valor padrão sensato que se possa
  dar a um `FileList`.

  **2. Duas mensagens em português cravadas no código.** `PageLogin` e
  `PageRegister` escreviam `"E-mail é obrigatório"` como literal enquanto o
  campo vizinho usava chave. Ficavam **em português com a interface em
  inglês** — o espelho do bug acima, e passou por baixo do Item 14 inteiro.

  **A lição, e ela generaliza:** o Item 14 verificou que as mensagens de
  validação estavam traduzidas, e estavam. O que ninguém verificou é se elas
  **são alcançadas**. Um catálogo completo não prova que suas chaves chegam à
  tela.

- **O texto nativo do `<input type="file">` foi RESOLVIDO, não só decidido**
  (Aberto 4/4, pendente desde o restyle). O `"Choose File / No file chosen"`
  vem do navegador, na locale **dele**, e **não é alcançável por CSS nem por
  JS** — `::file-selector-button` estiliza o botão mas não o renomeia, e nada
  endereça o texto ao lado. A única saída é **substituir o controle**: o
  `<input>` real continua na página com toda a acessibilidade, e um `<label>`
  apontando para ele passa a ser a superfície visível, cujo texto é nosso e
  sai do catálogo (`file.chooseButton`).

  Três detalhes que tornam a substituição segura, e que valem para qualquer
  controle nativo escondido no futuro:
  - **`sr-only`, nunca `display:none`** — escondido do segundo jeito o input
    sai da árvore de acessibilidade e deixa de receber foco.
  - **`aria-labelledby`** fixa o nome acessível no rótulo do campo; sem isso o
    `<label>` visível é um **segundo** rótulo do mesmo input e o leitor de
    tela anuncia os dois concatenados.
  - **O anel de foco migra para o elemento visível** (via `peer`), porque o
    input a que ele pertence não é mais visível.

- **Fase 4, Item 25 — Testes de integração e contrato: CONCLUÍDO.**
  Em dois repositórios: `feat/api-contract-tests` no `Refund-api` e
  `feat/contract-test` no `Refund-FrontEnd`. **Mescladas e empurradas em
  2026-08-09.** Detalhes no
  [diário](../learning-path-progress.md) e na
  [ADR-007](../decisions/ADR-007-contract-testing.md).
  - **`httpx` entrou, e isso PAGA a dívida registrada no Item 23.** Aquela
    pendência previa o momento: "se um dia a conta virar". O item pede "um
    fluxo de refund via cliente FastAPI". **Provado**: com o bug do Item 23
    reintroduzido, os testes de unidade seguem **verdes** e os HTTP **falham**.
  - **14 testes de API por HTTP** contra PostgreSQL e MinIO reais — health,
    auth, envelopes de erro, fluxo completo do reembolso, download por URL
    assinada **sem header** e anti-enumeração com corpos idênticos.
  - **O engine preguiçoso do Item 17 pagou juros de novo:** apontar a app para
    o banco de teste é uma linha. Segunda vez que aquele item barateia um
    posterior.
  - **Contrato versionado em DOIS arquivos**, e a divisão foi ditada pelo
    `eslint-plugin-boundaries`, não por gosto: `src/test` e `src/schemas` são
    camada `app`, e feature não importa de `app`. O contrato se partiu na mesma
    costura que os schemas já tinham.
  - **As duas divergências históricas viram teste vermelho**, provado por
    quebra: remover `"paid"` do enum (1 falha) e devolver `user_id` ao topo
    (3 falhas). A primeira é a que teria derrubado a Home de todo usuário.
  - **Achado ao capturar as respostas: a API tem TRÊS estilos de envelope.**
    Login e URL assinada planos; criação/detalhe com `{type, count,
    attributes}`; listagem com paginação no nível de cima. Não unificado —
    mudaria contrato — mas agora documentado por arquivo, não por memória.
  - Verificação: `pytest` **317 + 47 de integração** (partiu de 32),
    `pylint` exit 0; frontend **304** (partiu de 294), `tsc` 0, lint 0/0.

- **A CÓPIA DO CONTRATO ENTRE OS DOIS REPOS É MANUAL — pendência estrutural,
  e ela CONTINUA VALENDO.** O CI do backend falha se a API mudou e `contract/`
  não foi regerado; o do frontend falha se os schemas discordam do arquivo.
  **Nenhum dos dois percebe um contrato regerado que nunca foi copiado.**
  Destinos: `contract/refunds.json` → `src/features/refunds/contract/`;
  `contract/app.json` → `src/test/contract/`. Mesma forma do problema dos SHAs
  que este documento registrou seis vezes: nasce verdadeiro e morre em silêncio.

  **O QUE NÃO É VERDADE: não há divergência ativa.** Os **quatro arquivos**
  (os dois pares) foram conferidos em 2026-08-10 e estão **byte a byte
  iguais**. Foi a quarta pendência que a triagem daquele dia achou morta — mas
  morta só na parte que **afirmava um estado**. O mecanismo manual, que é a
  parte que descreve **como o problema volta**, segue registrado de propósito:
  ele é uma armadilha permanente, não um fato datado. Confira com:

  ```bash
  diff Refund-api/contract/refunds.json \
       Refund-FrontEnd/src/features/refunds/contract/refunds.json
  diff Refund-api/contract/app.json \
       Refund-FrontEnd/src/test/contract/app.json
  ```

  A distinção vale para quem escrever aqui: **pendência que afirma um estado
  envelhece; pendência que descreve um mecanismo, não.** Prefira a segunda
  forma, e quando a primeira for inevitável, deixe o comando que a refuta.

- **Fase 4, Item 26 — Cobertura como diagnóstico: CONCLUÍDO.**
  Branch `feat/coverage` nos dois repositórios, **empilhada sobre a do Item 25
  em cada um** — um fast-forward por repo levou os dois itens. **Mescladas e
  empurradas em 2026-08-09**, com verificação repetida depois de cada merge.
  Detalhes no [diário](../learning-path-progress.md) e na
  [ADR-008](../decisions/ADR-008-coverage.md).
  - **Nada reprova num número, e o motivo é local:** os três defeitos mais
    recentes deste projeto viviam em **linhas cobertas** (handler na classe
    errada, filtro não instalado, mensagem inalcançável). Portão num número dá
    segurança que os fatos daqui contradizem.
  - **O item entregou TESTES, não porcentagem.** Quatro achados fechados: o
    caminho de 500 do `error_handler` (nunca executado em 317 testes), o ramo
    `s3` do `build_storage` (**o que produção usaria**), a guarda do `useAuth`
    no frontend, e — o maior — **todos os fluxos de admin a 0% por HTTP**:
    pagamento, revisão e rotas de avatar. Sete testes HTTP novos, incluindo
    BR-016 e BR-021.
  - Backend 94% → **98%**; frontend 92,5% → **92,7%**.
  - **PONTO CEGO CONHECIDO, documentado no `.coveragerc`:** o
    `return JSONResponse(...)` final de toda rota é reportado como nunca
    executado — 13 linhas que **executam**. Causa **não isolada**:
    `concurrency = thread` não mudou nada, e a sonda que apontaria o middleware
    saiu errada. Registrado como observação, não diagnóstico. Não foi excluído
    de propósito — excluir tornaria a distorção invisível.
  - **A primeira apresentação do item não foi entendida** e foi refeita do
    zero, começando pela ferramenta rodando e por um achado real em vez do
    vocabulário. Lição de comunicação registrada no diário.
  - Verificação: `pytest` **325** (partiu de 317), integração **54** (partiu de
    47), `pylint` exit 0; frontend **305** (partiu de 304).

- **Fase 4, Item 27 — Rate limiting e segurança operacional: CONCLUÍDO.**
  Branch `feat/rate-limiting` do `Refund-api`, só backend. **Mesclada e empurrada em 2026-08-09.**
  Detalhes no [diário](../learning-path-progress.md) e na
  [ADR-009](../decisions/ADR-009-abuse-controls.md).
  - **O threat model que o item exige achou duas coisas reais.** (1) **O
    cadastro desfazia o cuidado do login**: o login responde a mesma mensagem
    para "não existe" e "senha errada" de propósito, e o cadastro ao lado
    responde `"Email already registered"` — exatamente o que o login recusa a
    revelar. (2) **O upload inteiro ia para a memória antes da checagem de
    tamanho**: `await file.read()` na rota, limite de 4MB só no validator.
  - **Rate limit em memória, sem Redis e sem biblioteca**, como o item manda.
    Custos declarados: contadores zeram no restart, e uma segunda réplica
    dobraria o limite efetivo.
  - **Contado por endereço, NÃO por e-mail** — limitar por e-mail deixaria
    trancar a conta de uma vítima de propósito. **Janela deslizante**, não
    balde de relógio. **Peer address, não `X-Forwarded-For`.**
  - **Limite de corpo antes de bufferizar** (413 em problem+json) e **três
    headers** de segurança, cada um com motivo local — `no-referrer` porque
    URL assinada carrega token na query.
  - **Rotação de secrets documentada no README** como procedimento, incluindo
    que trocar o `JWT_SECRET` **desloga todo mundo**.
  - **Limite conhecido:** o guarda de tamanho lê o `Content-Length` declarado;
    requisição *chunked* passa e é pega só pelo validator, depois de
    bufferizar. Escrito no código.
  - Verificação: `pytest` **331** (partiu de 325), integração **60** (partiu de
    54), `pylint` exit 0, cobertura 98%, e **as três frentes provadas por
    quebra deliberada**.

- **Fase 4, Item 28 — Tarefas assíncronas com fila: CONCLUÍDO. FECHA A FASE 4.**
  Branch `feat/orphan-sweep` do `Refund-api`. **Mesclada e empurrada em 2026-08-09.** Detalhes no
  [diário](../learning-path-progress.md) e na
  [ADR-010](../decisions/ADR-010-orphan-sweep.md).
  - **A FILA FOI DISPENSADA, com motivo.** O item diz "não adicionar worker
    para CRUD simples", e o projeto não tem e-mail, relatório nem processamento
    de arquivo — **nada precisa ser desacoplado de uma resposta HTTP**. Mesmo
    raciocínio que manteve o Redis fora do Item 27; mesmo precedente do Oxlint
    no Item 16 (item cumprido pela metade **explicitamente**).
  - **O que foi construído é o que o documento já apontava duas vezes:** a
    varredura de órfãos. Fila desacopla de uma requisição; esta varredura não
    pertence a requisição nenhuma.
  - **Fecha o resto do Item 21.** O `SIGKILL` entre `save()` e commit continua
    criando órfãos — é inerente —, mas agora existe algo que os encontra.
  - **Idade mínima de 1h e dry-run por padrão**, cada um por um motivo
    diferente: um arquivo de dois segundos cuja transação não commitou é
    indistinguível de um órfão, e um comando que apaga na primeira execução
    acaba apagando o que não devia. **Ambos provados por quebra deliberada.**
  - **`FileStorageInterface` ganhou `list_files()`** — a única operação que
    olha o armazenamento de fora. A implementação de S3 **pagina**, porque
    `list_objects_v2` trunca em 1000 chaves em silêncio.
  - **RODOU DE VERDADE: 3 órfãos encontrados** (um por storage), **0 removidos**
    — apagar arquivo é decisão de quem opera. Rodar
    `python -m init.sweep_orphans --apply` os remove.
  - **Não há agendamento** — é comando manual. Automatizar exige cron ou
    agendador do provedor, e não há onde implantar (Itens 29/30).
  - Verificação: `pytest` **331**, integração **68** (partiu de 60), `pylint`
    exit 0, três quebras deliberadas.

- **Fase 5, Item 29 — CI/CD: CONCLUÍDO.** Branch `feat/ci-completeness` nos
  dois repositórios. **Mesclada e empurrada em 2026-08-09.** Detalhes no
  [diário](../learning-path-progress.md).
  - **O título engana:** o corpo do item não menciona deploy — ele lista
    garantias de CI. CD de verdade exige onde implantar (Item 30 + provedor).
  - **Migration check instantâneo, sem banco.** O Item 19 já verifica
    migrations, mas com PostgreSQL de pé. Faltava a checagem de **múltiplas
    heads** — o erro mais comum de Alembic, que só aparece ao tentar aplicar.
    Agora roda na suíte rápida; provado forjando uma segunda head.
  - **Artefatos de cobertura** publicados nos dois CIs, com `if: always()`.
  - **Branch protection NÃO foi ligado, por decisão** — ver a pendência
    reescrita abaixo.
  - Verificação: `pytest` **333** (partiu de 331), integração 68, `pylint`
    exit 0; frontend 305.

- **Fase 5, Item 30 — Containers: CONCLUÍDO. FECHA O ÚLTIMO BLOQUEIO DO
  PRIMEIRO DEPLOY.** Branch `feat/container` do `Refund-api`. **Mesclada e empurrada em 2026-08-09.**
  Detalhes no [diário](../learning-path-progress.md) e na
  [ADR-011](../decisions/ADR-011-container.md).
  - **Só a API.** O frontend vira estático; conteinerizá-lo esbarra no
    `VITE_API_URL` resolvido em **tempo de build**, que prenderia a imagem a um
    ambiente.
  - **`/ready` novo.** O `/health` respondia 200 **com o banco inalcançável** —
    medido. Está certo para liveness e errado para readiness; faltava o
    segundo. **O `HEALTHCHECK` do Docker aponta para `/health` de propósito:**
    apontá-lo para o readiness faria uma queda de banco reiniciar todas as
    instâncias em laço.
  - **`requirements.txt` dividido, por medição:** 37,7 MB de 115,4 MB de
    site-packages (um terço) eram pytest, pylint, coverage e httpx. Imagem
    **396 → 366 MB**, e `import pytest` falha dentro dela.
  - Multi-stage, usuário **não-root** (`refund`), `.env` barrado no
    `.dockerignore`.
  - **Verificado CONSTRUINDO E RODANDO:** `/ready` **503 com o banco parado** e
    recuperando sozinho, container vivo o tempo todo, healthcheck `healthy`,
    nenhum `.env` dentro.
  - **Terceiro experimento inválido da sessão**, pego a tempo: com
    `--network host` no macOS eu não falava com o container — havia outro
    processo na 3333. O log de acesso denunciou.
  - Verificação: `pytest` **334**, integração **70**, `pylint` exit 0.

- ~~**A imagem é construída sobre Python 3.9, sem correções de segurança.**~~
  **RESOLVIDO na branch `chore/python-313-upgrade`, mesclada em `18b8678`:**
  o `Dockerfile` usa `python:3.13-slim` nos dois estágios, e a imagem foi
  construída e rodada nessa base. Confira com
  `grep -n "FROM python" Dockerfile`. O registro original, porque a dívida foi
  exatamente o que motivou o ciclo: o `boto3` já avisava que encerrou o
  suporte; construir imagem de produção sobre um Python sem correção de
  segurança é dívida real, e era o argumento mais concreto acumulado para subir
  de versão.

- **Fase 5, Item 31 — Performance orientada por medição: CONCLUÍDO. FECHA A
  TRILHA.** Branches `perf/measured-index` (`Refund-api`) e
  `perf/self-host-font` (`Refund-FrontEnd`). ~~**Não mescladas.**~~
  **MESCLADAS** — `212c9c8` e `b26385e`; confira com
  `git branch --contains 212c9c8` em cada repo. O texto antigo era a **oitava**
  ocorrência do padrão descrito no bloco de estado dos repositórios. Linha de base
  em [`performance-budget.md`](../performance-budget.md); detalhes no
  [diário](../learning-path-progress.md).
  - **A resposta do item foi PARAR.** A atribuição por dependência mostra
    **188 kB gzip de bibliotecas (81%) e 44 kB de código nosso (19%)**, sem
    gordura nenhuma — nenhuma lib duplicada, nenhum import de raiz, nenhuma
    dependência esquecida. Ganho disponível sem trocar de biblioteca: ~20 kB
    de 232, ou **~0,15s de 2,9s**.
  - **Três premissas minhas caíram em sequência:** (1) "Desktop não simula
    rede" — falso, simula; (2) o primeiro 3s era **Mobile**, não Desktop; (3)
    a fonte não era o gargalo — auto-hospedá-la levou o LCP Mobile de 3s para
    **2,9s**, ruído. A medição que a motivou (0,5s de requisição bloqueante,
    via `curl`) era real, só não era a maior.
  - **A fonte fica**, com registro honesto de que **não moveu o LCP**: a tela
    deixou de depender de um terceiro estar no ar para aparecer.
  - **Índice `ix_refunds_user_created`**, medido: 0,33 ms com 80 linhas (o
    planejador nem usa), 2,07 → **0,52 ms com 50 mil**. Migration testada
    `upgrade`/`downgrade`/`upgrade`, e os índices declarados também nas
    entidades para o autogenerate não acusar diferença.
  - **Orçamento versionado**, com uma seção **"o que NÃO é sintoma"** listando
    os três enganos que já custaram tempo aqui: o aviso de 500 kB do Vite, o
    Lighthouse contra `npm run dev`, e comparar modos diferentes.
  - Verificação: `pytest` **334**, integração **72**, `pylint` exit 0;
    frontend **305**, `tsc` 0, lint 0/0. LCP Desktop **0,6s**.

- **Ciclo de varredura — Python 3.13 e dependências: CONCLUÍDO na branch,
  NÃO MESCLADO.** Primeiro ciclo depois do fim da trilha, e o primeiro item da
  varredura de pendências combinada em 2026-08-08. Branch
  `chore/python-313-upgrade` do `Refund-api`, executada em 8 tasks com revisão
  por task. O ledger de execução vive em
  `.superpowers/sdd/2026-08-09-python-upgrade-and-dependencies/` **enquanto o
  ciclo está aberto**, e o fluxo prevê que o controlador o remova no
  fechamento; depois disso o registro **é** este bloco, o
  [diário](../learning-path-progress.md) e o histórico do Git. Escrito assim de
  propósito: a frase é verdadeira com o diretório em disco e continua
  verdadeira depois que ele sai. Para saber qual dos dois estados vale agora,
  rode `ls .superpowers/sdd/` — **não deduza pela existência desta linha**.
  **O merge é decisão do Gabriel**; para saber onde a branch está, rode os
  comandos do bloco de estado dos repositórios, não acredite nesta linha.
  - **AS PENDÊNCIAS 1 E 2 DA ORDEM DE VARREDURA ERAM UMA SÓ.** Esta é a
    descoberta que justificou o ciclo inteiro, e ela estava escrita errada aqui
    como dois itens separados ("Python 3.9 sem correção de segurança" e "37
    alertas do Dependabot"). A evidência: **toda versão corrigida exige
    `>= 3.10`**, e o `botocore` prendia o `urllib3` na linha vulnerável `1.26`
    através de um **marcador de ambiente** — `urllib3<1.27; python_version <
    "3.10"` — e não por uma escolha de ninguém. Ou seja, a vulnerabilidade era
    **segurada pelo interpretador**. Não havia como fechar o item 2 sem fechar
    o item 1; tentar corrigir alerta por alerta teria falhado na resolução.
  - **A cascata é forçada, nesta ordem:** Python → FastAPI → Starlette. Subir
    o `urllib3` sozinho não resolve, e subir o Python é o que destrava todo o
    resto.
  - **O que mudou de versão:** Python **3.9.6 → 3.13** (local 3.13.15, CI
    3.13.14, imagem `python:3.13-slim`); `fastapi` 0.128.8 → **0.141.1**;
    `starlette` 0.49.3 → **1.6.0** (um **MAJOR**); `urllib3` 1.26.20 →
    **2.7.0**; `python-multipart` 0.0.20 → **0.0.32**; `python-dotenv` 1.2.1 →
    **1.2.2**; `pytest` 8.4.2 → **9.1.1**; `pytest-asyncio` 1.2.0 → **1.4.0**;
    `pylint` 3.3.9 → **4.0.7**; `astroid` 3.3.11 → **4.0.4**.
  - **`backports.asyncio.runner` saiu do `requirements.txt` de produção**, onde
    nunca deveria ter estado: é transitivo do `pytest-asyncio`, ou seja, uma
    dependência **de teste** que estava sendo instalada na imagem. Some sozinho
    no 3.13, porque `asyncio.Runner` é nativo desde o 3.11.
  - **Uma mudança de comportamento, aceita por decisão do Gabriel.** O Python
    3.13 renomeou `HTTPStatus(422).phrase` de "Unprocessable Entity" para
    **"Unprocessable Content"** (RFC 9110). O `title` do envelope de erro deriva
    do registry **de propósito** (ADR-005), então o valor mudou junto. Raio de
    alcance conferido antes de decidir: o frontend **não lê** `title`, o
    `contract/app.json` guarda só um `title` de 404, e **uma** asserção foi
    afetada. A asserção foi atualizada.
  - **A imagem NÃO engordou:** **366 MB → 360 MB** (`docker images` DISK
    USAGE, o número comparável ao do Item 30). Vale saber, porque custou
    confusão: `docker image inspect --format '{{.Size}}'` reportou 78 MB para a
    mesma imagem — com o snapshotter containerd os dois números medem coisas
    diferentes, e só o DISK USAGE é comparável à linha de base antiga.
  - **DUAS PREVISÕES DO PLANO ESTAVAM ERRADAS, as duas pessimistas.** Ficam
    registradas como erros de previsão, não como sucessos:
    1. O **major do Starlette** exigiu **zero** mudança de código de aplicação.
       O plano tratava esse major como o risco central do ciclo.
    2. O **`pylint` 4 + `astroid` 4 emitiram ZERO mensagens novas.** O plano
       tinha orçado uma task de triagem que não teve o que triar. Como "nenhuma
       mensagem" é indistinguível de "o portão parou de funcionar", a
       credibilidade foi estabelecida por três caminhos independentes: um
       arquivo-sonda deliberadamente ruim pelo mesmo binário saiu com **exit
       4**; o `200 modules analysed` com cache limpo bateu exatamente com
       `find src -name '*.py' | wc -l`; e o `.pylintrc` não tem `ignore-paths`,
       `disable=all` nem filtro de confiança. **O assunto do commit `6d6e3fe`
       diz "close what it found" e sugere achados que não existiram** — a
       mensagem ficou como está (rebase interativo não está disponível neste
       ambiente); este parágrafo é o registro durável correto.
  - **A armadilha do `astroid`:** o `pylint 4.0.7` aceita
    `astroid >=4.0.4,<4.1.0-dev0`, e o `astroid` 4.3.0 — mais novo — está
    **fora** dessa faixa. "Mais recente" e "compatível" não são a mesma coisa;
    o par certo é `4.0.7` + `4.0.4`.
  - **As duas quebras deliberadas foram observadas.** A quebra A (registrar o
    exception handler na `HTTPException` do FastAPI em vez da do Starlette)
    manteve a suíte mockada **verde** e deixou a de integração **vermelha** em
    `test_an_unknown_route_is_also_a_problem_document` — a rede sobreviveu ao
    major. A quebra B está no item seguinte, porque revelou mais do que
    pretendia.
  - **O ACHADO MAIS IMPORTANTE DO CICLO: um teste que nunca foi um teste.**
    `test_the_filter_stamps_the_current_request_id` afirmava
    `record.request_id == current_request_id()` **logo depois** de o filtro ter
    escrito `current_request_id()` naquele campo, e nunca definia um id — fora
    de uma requisição os dois lados valem `"-"`, então ele passava até contra
    um filtro que devolvesse `"-"` cravado. Confirmado fazendo exatamente isso.
    Não é apodrecimento causado pelo major: **ele nunca foi rede, em versão
    nenhuma do Starlette.**

    O tamanho do buraco: `current_request_id()` tem **exatamente um** consumidor
    em todo o código — esse filtro. Então a promessa inteira do Item 24 (o
    `request_id` da resposta aparecer no log) descansava nesse teste mais um de
    integração que compara corpo com header, **ambos lidos de `request.state`**,
    um atributo comum e portanto imune a aninhamento de middleware. **Ninguém
    nunca tinha provado que o valor atravessa a fronteira do
    `BaseHTTPMiddleware`.** É a **quinta** ocorrência de "testei a peça, não a
    montagem" — a [retrospectiva](../retrospectiva-processo.md) conta quatro
    (Itens 14, 23, 24 e 27) porque esta foi encontrada depois de ela ser
    escrita. É também a **primeira** fechada com teste permanente em vez de
    conferência manual.
  - **O teste novo prova mais do que foi pedido.**
    `test_a_real_requests_access_log_line_matches_its_response_header` faz uma
    requisição de verdade e compara a linha de log de acesso com o header da
    resposta. A revisão o sondou com **quatro defeitos deliberados**: contextvar
    não setada (só o teste novo falha — logo os dois não são redundantes),
    filtro cravando `"-"` (os dois falham), filtro não estampando nada (o novo
    falha) e — o decisivo — **mover o `RequestIdMiddleware` de mais externo
    para mais interno**, que o novo teste **pega**. Ou seja: a **ORDEM dos
    middlewares agora tem teste**, onde antes tinha só um comentário em prosa
    em `src/main/server/server.py:59-64`.
  - **EXCEÇÃO DELIBERADA À REGRA DE 2026-08-08, e por quê.** A regra diz que
    pendência achada no meio de um item é para ser **registrada, não corrigida
    na hora**. O teste tautológico foi **corrigido na hora**, por decisão do
    Gabriel. O motivo: o propósito declarado daquela task era **provar que a
    rede está armada**; deixar uma mentira conhecida na suíte ao lado de uma
    verdade nova é incoerente com o próprio objetivo da task. Está registrado
    como exceção com a razão para que uma leitura futura não a interprete como
    a regra sendo ignorada — a regra continua valendo.
  - **TRÊS DEFEITOS ESTAVAM NO PLANO, não na implementação**, e foram achados
    durante a execução. Detalhes no [diário](../learning-path-progress.md):
    a verificação do container apontaria para o **Neon** enquanto o passo que
    "provava" o `/ready` em 503 parava um banco **local e diferente** — um falso
    positivo escrito no plano; o serviço do compose chama-se **`postgres-test`**,
    não `postgres`; e o critério de pronto "Dependabot devolve 0" era
    **inalcançável dentro do ciclo** (ver abaixo).
  - **A branch foi REBASEADA e REVERIFICADA.** A `origin/main` andou durante o
    ciclo (o `21920b3` do Gabriel, que trouxe a
    [retrospectiva de processo](../retrospectiva-processo.md)). A branch foi
    rebaseada para preservar a convenção de fast-forward do projeto:
    `54cda88 → 5bf4e2e`, 9 commits, sem conflito. **Reverificada depois**, pelo
    mesmo motivo que este documento já registrou na sessão de 2026-08-05:
    rebase produz uma árvore contra a qual teste nenhum jamais rodou.
  - Verificação final (2026-08-10, com a saída salva em arquivo **antes** de
    lida): `pytest` **335 passed / 72 deselected** em **três rodadas**,
    integração **72 passed**, `pylint src` **exit 0**. O 335 é o 334 anterior
    **mais o teste novo**. CI **verde nos dois jobs** sob 3.13, lido na saída e
    não no tique: `collected 407 items` com `72 deselected` no job `verify` e
    `335 deselected` no `integration` — cada job rodou exatamente a metade que
    devia. Container construído e rodando: `/ready` **200 → 503 (banco parado)
    → 200 (banco de volta)**, container `Up` e saudável o tempo todo, `import
    pytest` falhando dentro da imagem e nenhum `.env` nela.

- **Onda final de correções — revisão de branch inteira do ciclo de Python
  3.13, ANTES do merge.** Três achados Importantes, zero Crítico, na mesma
  branch `chore/python-313-upgrade`, mesclada em `18b8678`.
  - **`docs/roadmap.md` e `.github/workflows/ci.yml` eram a décima e a décima
    primeira ocorrência** do padrão descrito no bloco de estado dos
    repositórios acima — texto que era verdade quando escrito e parou de ser
    em silêncio. Ver o registro lá; a tally foi atualizada.
  - **Cinco pacotes órfãos da era 3.9 saíram do manifesto de produção, por
    decisão do Gabriel:** `async-timeout`, `exceptiongroup`,
    `importlib_metadata` e `zipp` do `requirements.txt`, e `tomli` do
    `requirements-dev.txt`. Todos entravam só sob marcadores de ambiente
    inativos no 3.13 (`python_version < "3.11"` e variantes) ou eram
    transitivos de outro item da própria lista. Não bastou confiar num
    `pip install --dry-run`: o `.venv` foi **recriado do zero**
    (`rm -rf .venv && python3.13 -m venv .venv && pip install -r
    requirements-dev.txt`), `pip check` saiu limpo, nenhum dos cinco voltou
    (`pip list | grep -iE` pelos cinco nomes, zero resultado), as duas suítes
    bateram os mesmos números de sempre (**335 passed/72 deselected** e
    **72 passed**), `pylint src` saiu **0**, e a imagem foi reconstruída e
    **iniciada de verdade** — `/health` 200, `/ready` 200, `HEALTHCHECK` do
    Docker `healthy` — porque os cinco pacotes removidos estavam dentro dela.
  - **A LIÇÃO QUE IMPORTA: `backports.asyncio.runner` já tinha saído do
    `requirements.txt` de produção neste mesmo ciclo (Task 1), mas por um
    motivo que não ensina nada sobre os outros quatro.** Ele saiu porque **o
    `pip` recusou instalá-lo** — a distribuição declara `Requires-Python
    <3.11` e falha sozinha em 3.13. Ninguém teve que procurar; o erro
    apareceu na cara. Os quatro órfãos que sobraram até esta onda
    (`async-timeout`, `exceptiongroup`, `importlib_metadata`, `zipp`, mais o
    `tomli` do arquivo de dev) **instalam sem reclamar** em 3.13 — o marcador
    de ambiente simplesmente nunca é satisfeito, e o `pip` não avisa que uma
    linha do manifesto virou letra morta. Uma falha que se remove sozinha não
    ensina nada sobre as que não se removem; exige varredura deliberada, que é
    exatamente o que a revisão de branch inteira fez e o que a task 1, sozinha,
    não tinha como fazer.
  - **`ci.yml` também mudou de conteúdo, não só a tally.** O comentário que
    justificava não criar venv na CI citava, no presente, os shebangs antigos
    do `.venv` local — uma pendência que este mesmo documento já registra como
    fechada como subproduto (ver a entrada abaixo, "shebangs de um caminho
    antigo"). A frase foi **removida** em vez de reescrita no passado: a
    justificativa que sobra (runner descartável, nada mais instalado nele) já
    é suficiente sozinha, e uma frase a menos é uma frase a menos para
    apodrecer de novo.
  - Verificação desta onda: `pytest` **335 passed / 72 deselected**, integração
    **72 passed**, `pylint src` **exit 0**, `pip check` limpo, imagem
    reconstruída e **rodando** (`/health` 200, `/ready` 200, healthcheck
    `healthy`). Relatório completo em
    `.superpowers/sdd/2026-08-09-python-upgrade-and-dependencies/final-fixes-report.md`.

- **Ciclo — PRIMEIRO DEPLOY (Railway + S3): CONCLUÍDO NA BRANCH, o projeto
  está no ar.** Branches `feat/first-deploy` (`Refund-api`, commits de código
  `2ee7add..057f339`; o commit de spec `e3a3f5e` vem antes dessa faixa) e
  `feat/serve-static` (`Refund-FrontEnd`, commits de código `b26385e..1d77232`;
  o commit de README `0d0e4cb` vem depois). Executado em 9
  tasks de **natureza dividida**: as tasks 1–3 e 9 são de agente; as 4–8
  exigiam console da AWS e painel da Railway e foram feitas pelo Gabriel, com o
  agente preparando valores e conferindo evidências. Detalhes e lições no
  [diário](../learning-path-progress.md).
  **O merge é decisão do Gabriel**; para saber onde as branches estão, rode os
  comandos do bloco de estado dos repositórios, não acredite nesta linha.

  - **As decisões.** Railway para tudo (container da API + PostgreSQL +
    frontend estático), **AWS S3** para os arquivos, e o projeto é
    **portfólio/demonstração** por natureza — o que calibra tudo o que vem
    abaixo: custo pequeno aceito, instância única aceita, ausência de backup
    aceita **enquanto** essa natureza valer.
  - **Três mudanças de código, e as três evitam uma falha real:**
    1. **`Settings` recusa driver de banco síncrono** (`db93c0b`). A Railway
       injeta a `DATABASE_URL` na forma libpq (`postgresql://`), que o
       SQLAlchemy resolve para o `psycopg2` — **não instalado aqui**. O
       `make_url` só faz parse e o engine é preguiçoso, então a aplicação
       **subia saudável e morria na primeira query**: é o modo de falha que o
       Item 17 existe para eliminar, reentrando pelo **driver** em vez de pela
       URL. O `get_dialect()` resolve a classe do dialeto sem importar o DBAPI,
       então a checagem não custa pool nem rede.
    2. **O container escuta em `$PORT`** (`5f5ba01`), com `exec` para o uvicorn
       continuar sendo PID 1 e o `SIGTERM` ainda chegar nele. Sem o `exec`, o
       shell vira PID 1 e o desligamento gracioso da plataforma vira um kill
       por timeout. O `HEALTHCHECK` passou a ler a mesma variável.
    3. **O frontend serve o build com `serve -s dist`** (`1d77232`, no outro
       repo). O `-s` **é** o fallback de history da SPA: sem ele, um F5 numa
       rota profunda responde 404. Provado por quebra deliberada — mesmo build,
       mesma rota, só a flag mudando: **200 com `-s`, 404 sem**.
  - **DOIS DEFEITOS QUE SÓ O DEPLOY REVELOU**, e são a parte mais valiosa deste
    registro. Estão contados no diário; em resumo: `serve` estava em
    `devDependencies` (e plataformas podam dev deps sob `NODE_ENV=production`,
    então o serviço do frontend **nunca subiu** e por isso nunca recebeu
    domínio); e as **URLs assinadas do S3 endereçavam o host GLOBAL**, que a
    AWS redireciona para o regional, quebrando a assinatura.
  - **QUINTA VEZ COM A MESMA FORMA: testei a peça, não a montagem.** O caminho
    do S3 tinha **9 testes de integração** contra o MinIO — incluindo três
    especificamente sobre URL assinada (baixar sem credencial, não ler sem
    assinatura, expirar) — e **nenhum deles podia ver** o defeito, porque **o
    MinIO não tem endpoint regional para errar**. Só a AWS de verdade tinha o
    problema, e só implantar podia revelá-lo. É a lição do ciclo inteiro, e ela
    não é sobre S3: um teste de integração prova que a peça funciona contra o
    **dublê** que você escolheu, e o dublê não tem as arestas que o original
    tem.

    **O número foi recontado, e o ledger deste ciclo estava errado.** Ele
    registrava "32 testes de integração"; o repositório diz **9**. Confira com
    `grep -c "def test_" src/test_integration/s3_storage_test.py` — nenhum
    outro arquivo de integração toca o MinIO
    (`grep -ln "S3FileStorage" src/test_integration/*.py` devolve só esse). Fica
    registrado porque é o mesmo padrão que este documento persegue desde a
    primeira ocorrência: **um número citado de memória, plausível, e falso**. A
    lição do defeito não depende do número, mas o número é conferível, então
    não há motivo para chutá-lo.
  - **Verificado em produção pelo Gabriel, no navegador:** cadastro, login,
    criar reembolso com comprovante, **o comprovante renderizando a partir de
    uma URL assinada da AWS de verdade**, aprovar, marcar como pago com
    comprovante de pagamento (um **segundo** caminho de upload e um **segundo**
    prefixo de URL assinada), o histórico de revisões e um erro aparecendo na
    tela. Ele se promoveu a admin com
    `python -m init.promote_admin <email>` — a forma de caminho simples falha
    porque `src` não fica no `sys.path`, como o próprio docstring do script
    explica; a mesma forma já estava correta em `README.md:141`.
  - **Verificado de fora, por sonda:** `/health` **200**, `/ready` **200**
    (ou seja, o banco é alcançado e a guarda do driver não disparou), o
    fallback da SPA respondendo **200** numa rota profunda, e um **404
    carregando `x-request-id`** — os Itens 23 e 24 vivos em produção. Um
    `POST /auth/login` com conta inexistente devolveu `problem+json` **400
    "Invalid credentials"**, o que prova duas coisas de uma vez: a query
    **alcançou** a tabela `users` (logo o `alembic upgrade head` rodou; schema
    ausente teria dado 500) e a decisão anti-enumeração continua valendo em
    produção.
  - **PostgreSQL da Railway é 18.4** (Debian 18.4-1.pgdg13+1) — o **mesmo major
    e o mesmo minor** que o Neon reporta. A suíte de integração continua
    espelhando produção; a [ADR-002](../decisions/ADR-002-postgresql-neon.md)
    foi amendada registrando **concordância**, não divergência.
  - **AS DUAS BRANCHES SÃO A FONTE DO DEPLOY — leia isto antes de apagar
    qualquer coisa.** Os serviços da Railway foram criados apontando para
    `feat/first-deploy` (API) e `feat/serve-static` (frontend), **não** para a
    `main`. Ver a pendência dedicada na seção de pendências.
  - Verificação: `pytest` **340 passed / 72 deselected** (partiu de 335: +3 da
    guarda do driver, +2 do endereçamento do S3), `pytest -m integration`
    **72 passed**, `pylint src` **exit 0**.
  - **ONDA FINAL DE CORREÇÕES DESTE CICLO, achada pela revisão de branch
    inteira — `S3_REGION` não era obrigatória.** `require_s3_configuration_when_selected`
    (`src/configs/settings.py`) exigia `S3_BUCKET`, `S3_ACCESS_KEY_ID` e
    `S3_SECRET_ACCESS_KEY`, mas `s3_region` tinha um default silencioso,
    `"us-east-1"`. Isso reabria a porta que o próprio `057f339` acabara de
    fechar: com um bucket fora de `us-east-1` e `S3_REGION` não configurada na
    Railway, o endereçamento virtual volta a resolver para o **host global**
    — o defeito exato deste ciclo, de novo, e sem nada barrando o startup para
    avisar. **Correção:** `s3_region` perdeu o default (passou a `""`) e
    entrou na lista de obrigatórias, no mesmo padrão dos outros três campos.
    TDD: o teste novo (`test_s3_backend_without_a_region_aborts_startup`) foi
    rodado FALHANDO antes da mudança (`DID NOT RAISE ValidationError`) e
    PASSANDO depois; os testes que montavam um `Settings` s3 "totalmente
    configurado" sem região foram atualizados para incluir `s3_region`.
    Verificação: `pytest` **341 passed / 72 deselected** (340 + 1),
    `pytest -m integration` **72 passed**, `pylint src` **exit 0**.

- **CORREÇÃO IMPORTANTE — "pylint 10.00/10" nunca significou aprovação.**
  Descoberto pelo CI em 2026-08-06, no primeiro dia. O `pylint src` imprime
  `rated at 10.00/10` **e sai com código 8** quando emitiu qualquer mensagem —
  a nota não é penalizada por uma mensagem de refatoração. Nenhuma sessão
  anterior conferiu o `$?`, então **vários ciclos deste documento e do diário
  registram "pylint 10.00/10" como verificação aprovada quando o comando
  reprovava.** A nota estava certa; a conclusão, não.
  A causa era `R0801` — o envelope de resposta duplicado em **três**
  controllers (o pylint apontava dois; o `payer` o montava inline). Resolvido
  extraindo `format_refund_response` para junto de `serialize_refund`. Os
  outros três envelopes ficaram de fora de propósito (listagem, exclusão e a
  forma divergente do `UC-007`). Desde então: **`pylint src` sai com 0**, e os
  `AGENTS.md` dos dois repos passaram a mandar conferir o código de saída, não
  a nota.

- ~~**Próximo — validar em navegador os dois últimos ciclos, que foram
  mesclados e empurrados sem essa passada.**~~ **RESOLVIDO em 2026-08-03:** o
  Gabriel validou no navegador, contra a API real, **três** conjuntos, todos
  **sem ressalvas**:

  1. **Ciclo de navegação e tabela** — Home com `status`/`sort`/`order` na URL,
     tabela de seis colunas, ordenação server-side pelos cabeçalhos, coluna de
     solicitante só para admin, colapso de colunas abaixo de `sm`, comprovante
     na tela de revisão, setas anterior/próxima e "Próxima pendente".
  2. **Ciclo de feedback de carregamento** — spinner durando até o histórico
     atualizar (o pedido que originou o ciclo), card de pendentes **não**
     seguindo o filtro de status, alinhamento dos ícones no modo trilho,
     "Nova solicitação" reabrindo o diálogo zerado, e os diálogos resetando ao
     cancelar.
  3. **Branch `feat/pagination-busy-state`** — clicar "próxima página" gira só
     a seta da direita; digitar na busca não gira nenhuma das duas.

  **Isto fecha o alinhamento do sidebar**, que era o item mais delicado: duas
  rodadas de aritmética de box model se contradisseram antes de convergir e
  **nenhuma das duas tinha sido observada**. Agora foi. Registrado com a
  granularidade item a item de propósito — o ciclo de 2026-07-30 ficou anotado
  sem ela e este documento já avisava que "sabe-se que a validação aconteceu,
  não o alcance dela".

  **A branch `feat/error-boundaries` (Item 11) NÃO entrou nesta passada** — foi
  escrita depois. Ver a limitação registrada no item e o checklist nas
  pendências.

- **DECIDIDO em 2026-08-08: as pendências serão varridas ao FIM da trilha, não
  ao longo dela.** Uma pendência encontrada no meio de um item é para ser
  **registrada aqui**, não corrigida na hora — mesmo quando a correção é de
  duas linhas. O motivo é o que esta seção já demonstra várias vezes: uma
  correção enxertada num item em curso mistura dois assuntos, e a deste
  documento com pior histórico foi justamente uma feita sob hipótese não
  verificada. Quem retomar a trilha deve continuar acumulando aqui e planejar
  um ciclo próprio de varredura quando o `learning_path.md` acabar.

  **UMA EXCEÇÃO DELIBERADA, em 2026-08-10, com a razão registrada.** No ciclo
  de Python 3.13, um teste tautológico descoberto no meio da task foi
  **corrigido na hora** em vez de registrado aqui — decisão do Gabriel. O
  motivo é específico e não generaliza: aquela task existia **para provar que a
  rede de testes está armada**, e deixar uma mentira conhecida na suíte ao lado
  de uma verdade nova contradiz o objetivo declarado da própria task. A regra
  continua valendo; esta linha existe para que a exceção não seja lida como a
  regra sendo ignorada.

- **A TRILHA ACABOU.** Itens 1 a 31 concluídos, as cinco fases fechadas.

  **O próximo passo combinado em 2026-08-08 é a VARREDURA DE PENDÊNCIAS** —
  esta seção acumulou o que foi encontrado ao longo do caminho e nunca
  corrigido na hora, de propósito. Sugestão de ordem, do mais grave ao menos:
  1. ~~**Python 3.9 sem correção de segurança** + **37 alertas do
     Dependabot**~~ — **ERAM UM ITEM SÓ, e foram ENDEREÇADOS na branch
     `chore/python-313-upgrade`, mesclada em `18b8678`.** Esta lista os
     tratava como as pendências 1 e 2, separadas. Não eram: **toda versão
     corrigida exige `>= 3.10`**, e o `botocore` prendia o `urllib3` na linha
     vulnerável `1.26` através do marcador de ambiente
     `urllib3<1.27; python_version < "3.10"` — a vulnerabilidade era segurada
     **pelo interpretador**, não por uma escolha. Sem subir o Python não havia
     como fechar os alertas; subindo, eles caem juntos. Ver o relato do ciclo
     na seção de progresso e a pendência de contagem pós-merge abaixo.
  2. **Branch protection desligado** — decisão registrada, revisar se houver
     uma segunda pessoa.
  3. **3 arquivos órfãos** aguardando decisão (Item 28).
  4. **10 alertas do Dependabot no `Refund-FrontEnd`** — o repositório passou o
     projeto inteiro com o Dependabot **desligado**; agora está ligado e tem
     número. Ver a pendência abaixo.
  5. O resto desta seção.

  **A lição que essa fusão deixa, e que vale para as próximas varreduras:**
  duas pendências listadas separadamente podem ser **uma causa e um sintoma**.
  Esta lista carregou as duas por dias como itens independentes, e a relação só
  apareceu quando alguém foi ler **por que** a versão vulnerável estava fixada.
  Antes de estimar dois itens, vale perguntar se um deles não é consequência do
  outro.

  ~~**O que a trilha NÃO entregou, e continua verdadeiro:** não existe deploy.~~
  **DEIXOU DE VALER em 2026-08-10** — ver o ciclo do primeiro deploy na seção
  de progresso. O registro original, porque o diagnóstico estava certo: os
  cinco bloqueios foram endereçados pela trilha, mas escolher e configurar um
  provedor não é código, e por isso continuou pendente até existir um ciclo
  próprio para isso.

  **Nenhuma branch de trabalho pendente** — as cinco foram mescladas em
  2026-08-09; as quatro do backend estavam empilhadas, então um fast-forward
  levou os quatro itens. Verificação repetida depois de cada merge.

  **3 órfãos reais aguardando decisão** — ver o Item 28. — as quatro foram mescladas em
  2026-08-09. **Validação em navegador dos Itens 25 e 26: não se aplica**,
  nenhum dos dois toca tela.

  **Nenhuma validação em navegador pendente** pela primeira vez em três itens:
  a sessão de 2026-08-09 zerou o acúmulo dos Itens 22, 23 e 24 e fechou quatro
  pendências antigas.

  **Nenhuma branch de trabalho pendente** — as três foram mescladas em
  2026-08-09, com verificação repetida depois de cada merge. **Validação em
  navegador acumulada: Itens 22, 23 e 24.** O 22 continua sendo o crítico (o
  ponto dele é uma URL carregar numa `<img>`); o 23 e o 24 são baratos de
  conferir junto, numa ação que falhe: a mensagem deve aparecer como sempre, e
  o log do servidor deve trazer o mesmo `request_id` que a resposta. Nenhum dos dois foi
  visto num navegador. O 22 é o mais crítico (o ponto dele é uma URL carregar
  numa `<img>`); o 23 é mais barato de conferir — basta uma ação que falhe e
  ver a mensagem aparecer como antes, já que o contrato foi desenhado para não
  quebrar.

- **VALIDAR EM NAVEGADOR o Item 22.**
  As duas branches estão paradas e é o item em que essa lacuna mais pesa: o
  ponto inteiro é uma URL carregar numa tag `<img>` sem header, e a suíte roda
  contra MSW. Ver pendências para o checklist.

  Depois disso: com 17 a 22 feitos, o próximo em aberto da Fase 4 é o **Item
  23** (Problem Details, RFC 9457), ou o **ciclo de feature da foto de perfil**
  — único item novo restante do backlog do frontend, e que ficou mais barato
  agora que o avatar também chega como URL.

  **Vale olhar fora da trilha:** o GitHub reportou **14 vulnerabilidades do
  Dependabot** no `Refund-api` (5 high, 5 moderate, 4 low) no push de
  2026-08-07. Não foi investigado — e no push de 2026-08-09 já eram **37 (18
  high, 11 moderate, 8 low)**, sem nenhuma dependência nova entre as duas
  datas. **INVESTIGADO em 2026-08-10**, no ciclo de Python 3.13: os 37 são
  **19 advisories distintos contados duas vezes**, e o crescimento de 14 para
  37 era mesmo alerta novo sobre versão velha. Ver a pendência de contagem
  pós-merge.

## Encerramento da sessão de 2026-07-31 → 2026-08-03

O que fica aberto, em ordem de quem depende de quem:

1. ~~**Empurrar o commit de documentação do `Refund-api`**~~ **FEITO em
   2026-08-03:** `842d051`, `c3e6376` e `7c51a86` empurrados; `origin/main`
   saiu de `7aac636`.
2. ~~**Validar em navegador** os dois ciclos mesclados e a branch de
   paginação.~~ **FEITO em 2026-08-03, sem ressalvas** — ver o detalhamento
   item a item acima.
3. ~~**Mesclar `feat/pagination-busy-state`**~~ **FEITO em 2026-08-03:**
   fast-forward `6c63ff5..d33fb65`, com verificação repetida depois do merge.
   Não empurrada ainda.
3b. ~~**Mesclar `feat/error-boundaries`** (Item 11).~~ **FEITO em 2026-08-05:**
   rebase limpo sobre a `main` (`2334028` virou `887cd45`, sem conflito) e
   fast-forward. A ordem foi invertida de propósito — a `fix/auth-storage-access`
   entrou primeiro por já fazer fast-forward, o que economizou um segundo
   rebase.
3c. ~~**Mesclar `fix/auth-storage-access`**.~~ **FEITO em 2026-08-05:**
   fast-forward `d33fb65..d9d8b6b`.

   **A árvore combinada foi verificada antes do merge, não só depois.** Rebase
   produz um estado que nunca existiu em teste nenhum: boundaries, correção do
   `localStorage` e paginação juntos. Números finais na `main`: **260 testes em
   46 arquivos**, verdes em **três rodadas**, `tsc` exit 0, lint **0/0**, build
   ok, bundle **562,61 kB**. Flake do `ResizeObserver` ausente nas três.
4. ~~**Decidir o deploy conjunto.**~~ **RESOLVIDO em 2026-08-03** — por
   verificação, não por implantação. Não existe produção: o risco era
   contingente a um ambiente que nunca foi criado. Ver a pendência reescrita e
   os cinco bloqueios técnicos do primeiro deploy.
5. **Próximo ciclo: foto de perfil.**

Duas coisas que esta sessão aprendeu sobre o próprio processo, e que valem
mais que qualquer item acima:

- **Três achados de revisão foram defeitos do plano, não da implementação** —
  o plano prescrevia comentários na língua errada para o arquivo de destino, e
  os implementadores copiavam fielmente. A regra do `AGENTS.md` é: código e
  comentários em inglês, exceto em arquivos que **já** carregavam comentários
  em português; um arquivo **novo** não tem o que espelhar, logo é inglês.
  Quem escrever o próximo plano deve conferir a língua de cada arquivo de
  destino antes de colar um snippet.
- **"As contas batem" não é o mesmo que "está correto".** O alinhamento do
  sidebar teve duas rodadas de aritmética de caixa que se contradisseram, e a
  primeira parecia igualmente convincente. O mesmo padrão apareceu no spinner
  de paginação, onde uma comparação errada só não quebrava porque dois valores
  coincidem em produção. Quando não há como observar, o registro deve dizer
  "não observado" em vez de "verificado".

## Backlog do frontend — o que ainda falta

O ciclo de 2026-07-29 (`feat/frontend-contract-and-receipt`) absorveu o contrato
novo, o comprovante autenticado, o badge de status e os ajustes pequenos, e **já
está mesclado na `main`** — a `main` do `Refund-FrontEnd` consome a API atual.
O ciclo de 2026-07-30 (workflow de aprovação, ver acima) entregou a rota de
revisão, aprovar/rejeitar, pagamento, histórico, comprovante de pagamento e o
painel do solicitante, **está mesclado na `main` e foi validado visualmente pelo
Gabriel**. Falta implantá-lo junto do backend correspondente — o que, desde a
verificação de 2026-08-03, significa o **primeiro** deploy do projeto, não um
redeploy sobre algo existente (ver pendências).
O ciclo de 2026-07-31 (navegação na revisão e tabela de reembolsos, ver acima)
**fecha o Item 13** — a Home já filtra e ordena `status`/`sort`/`order`
server-side através de uma `RefundsTable`; escopo por `user_id` para o admin
continua fora de escopo desse item (não pedido pela spec) e não aparece no
backlog abaixo.

O que resta, em ciclos próprios (um por vez, na ordem do roadmap):

### 1. Foto de perfil (upload e exibição)

`POST`/`DELETE /users/me/avatar`, gradiente como padrão, `has_avatar` decidindo
entre foto e gradiente, e exibição no Sidebar e na lista. Os schemas já absorvem
`user.has_avatar`, mas **nenhuma tela renderiza avatar** — exibir antes de
existir upload custaria N requisições autenticadas por página, sem cache do
browser. O `src/hooks/useObjectUrl.ts` foi posto na camada compartilhada
justamente para este ciclo poder reusá-lo sem esbarrar no
`eslint-plugin-boundaries`. Aqui também se decide o
`avatar_filename` cru nas respostas de login/upload/remoção (ver pendências).
**Continua sem nenhum consumidor**, inclusive depois do painel do solicitante
do ciclo de revisão: `has_avatar` é sempre `false` até este ciclo existir.

As armadilhas do frontend que continuam valendo (`ui/sidebar.tsx` editado à mão,
a altura `h-17.5`, o diretório `./@/` do CLI do shadcn, os polyfills de jsdom em
`src/test/setup.ts`) estão descritas na seção de pendências abaixo.

## Pendências e riscos conhecidos

### Pendências que nasceram com a produção (2026-08-10)

Estas sete são novas e existem porque existe um ambiente implantado. Antes do
deploy nenhuma delas fazia sentido.

- **OS SERVIÇOS DA RAILWAY IMPLANTAM A PARTIR DAS BRANCHES, NÃO DA `main`.**
  Esta é a mais importante da lista, e é a que morre em silêncio se ninguém
  escrever. No fim deste ciclo, cada serviço rastreia a referência abaixo:

  | Serviço | Repositório | Referência que ele rastreia |
  |---|---|---|
  | API (container) | `Refund-api` | `feat/first-deploy` |
  | Frontend (estático) | `Refund-FrontEnd` | `feat/serve-static` |

  **Como conferir, porque a tabela acima envelhece:** a referência de cada
  serviço só existe no painel da Railway (serviço → Settings → Source). Não há
  arquivo neste repositório que a declare, então nenhum `grep` responde — é a
  mesma assimetria que a verificação de 2026-08-03 registrou ao concluir que
  "um deploy pode ser configurado inteiramente no painel do provedor".

  **O que fazer depois do merge:** repontar cada serviço para `main`. **A única
  ordem errada é apagar a branch primeiro** — um serviço apontando para uma
  branch apagada não tem de onde reconstruir, e a próxima implantação (inclusive
  um restart automático da plataforma) quebra a produção. Duas ordens seguras,
  e a escolha é do Gabriel: repontar para `main` **antes** de apagar as
  branches, ou mesclar, repontar, e só então apagar.

- **O plano gratuito da AWS TERMINA — é por tempo, não por consumo.** A conta
  foi criada para este deploy e a camada gratuita tem prazo. **Não invente a
  data:** leia-a no console da AWS (Billing and Cost Management → Free Tier),
  que mostra o que expira e quando. Vale virar decisão antes de virar cobrança.
  Depois do prazo, o **armazenamento** deste projeto custa centavos — são
  poucos arquivos, pequenos —, mas quem cobra de verdade é a **transferência de
  saída**: cada comprovante exibido é um download direto do bucket pelo
  navegador, e é exatamente esse o desenho do Item 22.

- **A Railway cobra.** Custo recorrente pequeno, **não zero**, e são três
  cobranças no mesmo lugar (a API em container, o PostgreSQL e o serviço
  estático do frontend). Confira no painel da Railway (Usage). Junto com o item
  acima, é o total de custo do projeto — e a razão para ele ser aceitável é a
  natureza de portfólio/demonstração.

- **Nada valida que a `VITE_API_URL` é ABSOLUTA, e o modo de falha mente.**
  Aconteceu neste deploy: o valor foi configurado **sem o esquema `https://`**.
  O Axios trata uma `baseURL` sem esquema como **caminho relativo**, então toda
  requisição foi parar na origem do próprio frontend — onde o `serve -s`
  responde **200 com o `index.html`**. A aplicação recebeu HTML onde esperava
  JSON e falhou imediatamente, e o sintoma na tela lê-se como "o login está
  quebrado" em vez de "a configuração está errada". Diagnosticado com um `grep`
  no bundle construído, procurando o valor que o Vite **assou** ali dentro.
  **A correção pendente são três linhas** que rejeitem uma `VITE_API_URL` sem
  esquema no startup do frontend — a mesma ideia do **Item 17**, que hoje só
  existe no backend. Confira se ainda é pendência com
  `grep -rn "VITE_API_URL" Refund-FrontEnd/src/`: hoje o valor é lido e usado,
  nunca conferido.

- **Instância única: o rate limit do Item 27 zera a cada restart.** Ele é
  em memória e por processo — sempre foi, e está registrado assim desde o
  próprio item. O que mudou é que agora isso vale **sobre algo real**: um
  redeploy ou um restart da Railway devolve o contador a zero, e uma segunda
  instância (se algum dia houver) teria um contador próprio. A decisão original
  (não trazer Redis) continua coerente com a natureza do projeto; o registro
  existe para que ninguém confunda o limite com uma garantia.

- **NÃO HÁ BACKUP — nem do banco, nem dos arquivos.** Nenhum snapshot do
  PostgreSQL da Railway, nenhum versionamento nem replicação no bucket S3. Uma
  exclusão acidental, um `alembic downgrade` errado ou o encerramento de uma
  conta levam o dado embora sem cópia. Aceito hoje pela natureza de
  portfólio/demonstração, e listado aqui para que essa aceitação seja
  **explícita** em vez de acidental.

- **`alembic downgrade` agora ALCANÇA PRODUÇÃO.** Até este deploy era um
  comando inofensivo numa máquina de desenvolvimento, usado o tempo todo para
  provar que as migrations são reversíveis. Com uma `DATABASE_URL` de produção
  no ambiente, o mesmo comando **destrói dado real** — e um `downgrade` que
  remove coluna não tem volta, porque a reversão recria a coluna vazia, não o
  conteúdo dela. Não há hoje nenhuma proteção contra isso; a proteção é saber
  qual `DATABASE_URL` está no ambiente antes de digitar o comando.

### Pendências anteriores

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

- **DEPLOY CONJUNTO — RECLASSIFICADO em 2026-08-03: é uma restrição da
  PRIMEIRA implantação, não um risco ativo.** Este item passou semanas descrito
  aqui como "o risco mais antigo do projeto e o único que produz quebra em
  produção sem ninguém escrever código". Ele repousava numa premissa que nunca
  havia sido verificada — a de que existe uma produção. Foi verificada, e é
  falsa.

  **Evidências levantadas nos dois repositórios em 2026-08-03:**

  | Verificação | Resultado |
  |---|---|
  | `Dockerfile`, `render.yaml`, `vercel.json`, `fly.toml`, `Procfile` | nenhum |
  | `.github/workflows` (CI) | nenhum |
  | CORS do backend (`src/main/server/server.py:23`) | `allow_origins=["http://localhost:5173"]` |
  | `VITE_API_URL` (`Refund-FrontEnd/.env`) | `http://localhost:3333` |
  | URL de produção citada em docs/READMEs | nenhuma |
  | Seção de deploy no `roadmap.md` | nenhuma |
  | Serviço de hospedagem conectado ao GitHub | **nenhum — confirmado pelo Gabriel** |

  A varredura do repositório **não bastaria sozinha**: um deploy pode ser
  configurado inteiramente no painel do provedor (Render, Vercel, Railway
  conectados ao GitHub), sem deixar rastro nenhum no código. Por isso a última
  linha da tabela é uma confirmação do Gabriel, e não uma inferência a partir
  dos arquivos. Quem reabrir este item deve refazer **as duas** perguntas.

  **O CORS é a evidência que fecha o caso.** Ainda que um frontend estivesse
  implantado em algum domínio, o navegador bloquearia **toda** requisição dele
  antes de qualquer `.parse` do Zod rodar. A divergência de contrato nem
  chegaria a ser o modo de falha observado.

  **O que continua verdadeiro.** A divergência é real e as duas `main` não
  podem ser implantadas em momentos diferentes: `user_id` saiu do topo das
  respostas e virou `user.id`, e o backend responde `status: "paid"`, que o
  `refundStatusSchema` de um frontend anterior não conhece. Nenhum dos dois
  lados tolera a versão antiga do outro, em nenhuma ordem. Isso vale
  integralmente para a **primeira** implantação.

  **O que deixou de ser verdadeiro.** Que algo pode quebrar sozinho enquanto
  ninguém age. Não pode: não há processo automático, não há ambiente rodando e
  não há usuário. O custo de errar a ordem no primeiro deploy é uma tela
  quebrada num ambiente ainda sem ninguém dentro — não uma quebra sobre algo em
  uso. A restrição volta a ter dentes no instante em que existir um ambiente
  implantado.

  **A alternativa registrada fica descartada.** A "versão de transição"
  devolvendo `user_id` **e** `user` existia para acomodar um cliente antigo já
  em produção. Não há cliente antigo. Implantar os dois lados a partir das
  `main` atuais é coerente por construção.

  **Lição de processo, que vale mais que o item.** Um risco foi carregado por
  semanas, escalando de tom a cada sessão ("deixou de ser teórica", "a única
  coisa entre o estado atual e uma quebra"), sem que ninguém verificasse a
  premissa que o sustentava — uma verificação de dez minutos. O mesmo padrão
  que este documento já registra para os SHAs ("nasce verdadeira e morre em
  silêncio") vale para riscos: **um risco herdado deve ter sua premissa
  reverificada, não seu tom reforçado.**

- **O primeiro deploy tinha cinco bloqueios, e o contrato não era o principal.**
  Levantados em 2026-08-03, ao verificar que não existia produção. **OS CINCO
  ESTÃO FECHADOS, e não só no papel: o deploy de 2026-08-10 exerceu todos.**
  Ficam registrados porque a lista é o que explica por que a trilha e o deploy
  nunca foram assuntos separados:
  1. ~~**CORS fixo em `localhost:5173`**~~ **RESOLVIDO no Item 17:**
     `allow_origins=settings.cors_origins`, configurável por `CORS_ORIGINS`, e
     um `model_validator` que recusa o startup se `ENVIRONMENT=production`
     trouxer `*`, `localhost` ou `127.0.0.1`.
  2. ~~**Configuração por `os.getenv` sem validação**~~ **RESOLVIDO no Item 17:**
     `Settings(BaseSettings)` valida no startup e a aplicação não sobe com
     variável obrigatória ausente ou de tipo inválido.
  3. ~~**Comprovantes em disco local**~~ **RESOLVIDO no Item 22 e EXERCIDO em
     2026-08-10:** `STORAGE_BACKEND=s3` guarda os arquivos fora da instância, e
     em produção eles vivem num bucket da AWS. O texto original, porque o
     raciocínio continua útil: a maioria dos PaaS tem filesystem efêmero, então
     **todo comprovante evaporaria a cada redeploy**. Note que isto é pior que
     o risco de contrato: perde dado do usuário, em silêncio e sem erro na
     tela.

     **A RESSALVA DE CORS DO BUCKET ESTAVA ERRADA, e a implantação derrubou
     ela.** Este item afirmava que uma implantação com S3 "precisa liberar o
     domínio do frontend no **CORS do bucket**". **Não precisa** — não para a
     UI como ela é hoje. O `ReceiptPreview.tsx` renderiza os arquivos por
     `<img src>` e `<object data>`, e **nenhum dos dois é requisição governada
     por CORS**: o navegador busca o recurso e o entrega ao elemento sem que o
     JavaScript da página leia os bytes, então não há preflight nem exigência
     de `Access-Control-Allow-Origin`. Este deploy confirma na prática:
     **nenhum CORS de bucket foi configurado** e os comprovantes aparecem.

     **A condição que a tornaria verdadeira de novo, e é para isso que ela fica
     escrita:** qualquer código que busque o arquivo **por JavaScript** —
     `fetch`, `XMLHttpRequest`, um `axios.get` que monte um Blob (que é
     exatamente o que este frontend fazia **antes** do Item 22), um `<canvas>`
     lendo pixels de uma imagem, ou um download que precise renomear o arquivo.
     Nesses casos o navegador passa a exigir o cabeçalho, e o bucket precisa
     liberar a origem do frontend. Quem for escrever esse código deve tratar o
     CORS do bucket como parte da tarefa.
  4. ~~**Sem `Dockerfile` nem build de produção**~~ **RESOLVIDO no Item 30 e
     EXERCIDO em 2026-08-10:** é a imagem deste `Dockerfile` que roda na
     Railway, com o ajuste do `$PORT` feito no ciclo do deploy.
  5. ~~**Sem CI que verifique antes de publicar**~~ **RESOLVIDO no Item 29.** O
     episódio do commit `2d07a8d`, que deixou a `main` do frontend quebrada em
     `tsc`, `eslint` **e** `build` sem ninguém notar, é exatamente o que um CI
     teria pego.

  **Consequência para a trilha, agora confirmada pelos fatos:** deploy e
  Learning Path não eram assuntos separados. Os Itens 17 e 22 eram
  pré-requisitos técnicos do primeiro deploy e os Itens 29/30 eram a
  infraestrutura dele; os cinco bloqueios caíram como **subproduto de itens da
  trilha**, não de um esforço paralelo de deploy. O que sobrou para o ciclo do
  deploy foi o que nenhum item da trilha podia entregar: escolher um provedor,
  criar as contas, e as três correções que só apareceram quando havia uma
  plataforma real do outro lado.
- ~~**`AuthContext.loadStoredUser` lê `localStorage` FORA do próprio
  `try`.**~~ **RESOLVIDO em 2026-08-05**, na branch `fix/auth-storage-access`
  do `Refund-FrontEnd` (commit `d9d8b6b`, **mesclada** — ver "3c" na seção de
  encerramento da sessão de 2026-07-31 → 2026-08-03): a leitura entrou
  no bloco que já existia, e a aplicação passa a bootar anônima em vez de
  quebrar. **A prova não foi o teste passar** — o teste novo (`boots anonymous
  when localStorage access itself throws`, com `Storage.prototype.getItem`
  jogando `SecurityError`) foi rodado contra o código **antigo** primeiro, onde
  falha. Verificação: 250 testes (de 249), `tsc` 0, lint 0/0, bundle inalterado.
  **Ficou de fora de propósito:** `login` e `logout` também tocam
  `localStorage`, mas de dentro de um event handler e de uma função assíncrona
  — um storage bloqueado ali vira promise rejeitada ou erro de handler, não
  queda de render. Forma de falha diferente, correção diferente.
  O registro original, porque o raciocínio continua útil:
  Achado no Item 11 (2026-08-03) e **deliberadamente não corrigido na hora**,
  para não misturar uma correção de comportamento com o item em curso.
  `src/context/AuthContext.tsx` linha 11 chama
  `localStorage.getItem(USER_STORAGE_KEY)` **antes** do `try` que começa na
  linha 14 — o bloco protege o `JSON.parse` e o `safeParse`, mas não o acesso
  ao storage. Acesso a `localStorage` **lança** quando o navegador bloqueia
  dados do site (configuração de privacidade, política corporativa), e isso
  roda no inicializador do `useState` do `AuthProvider`, ou seja, **durante o
  render**. Antes do Item 11 isso era uma página em branco; agora o
  `AppErrorBoundary` captura e mostra uma tela de erro com recarregar — que é
  o comportamento correto para uma falha inesperada, mas **não** é o
  comportamento desejável para esta em particular: uma sessão ilegível deveria
  derrubar a sessão, não a aplicação, exatamente como o comentário do próprio
  arquivo já diz sobre o `safeParse`. **A correção é mover a linha 11 para
  dentro do `try`** — uma linha. Fica como decisão do Gabriel porque é
  mudança de comportamento, não de arquitetura.
- ~~**O gatilho real do `AppErrorBoundary` nunca foi observado.**~~
  **RESOLVIDO em 2026-08-05:** o Gabriel bloqueou os dados do site pelo
  DevTools e recarregou; apareceu a tela "Algo deu errado" com "Recarregar a
  página", não a tela branca. Vale registrar que este foi o **único** dos três
  pontos do checklist que a suíte não conseguia alcançar de forma alguma — e
  que a `fix/auth-storage-access` muda o resultado esperado deste mesmo
  cenário: com ela mesclada, a aplicação passa a bootar **anônima** em vez de
  mostrar a tela de erro. Quem revalidar precisa saber qual das duas árvores
  está olhando. O registro original:
  O cenário que
  motivou a lacuna 1 do Item 11 (`localStorage` bloqueado no boot) não é
  reproduzível no jsdom. Os testes provam que *um filho que lança* produz o
  fallback; ninguém viu *aquele* filho lançando. Para observar: DevTools →
  configurações do site → bloquear dados/cookies → recarregar a aplicação.
  Vale rodar junto do checklist de navegador já pendente.
- **O "flick" ao abrir a Home continua sem causa identificada.** Relatado pelo
  Gabriel no Item 15: ao carregar a lista, algo desloca a página
  horizontalmente por um instante. **Duas tentativas falharam e foram
  removidas a pedido dele:**
  1. `scrollbar-gutter: stable` na `div.flex-1.overflow-auto` do `MainLayout` —
     **sem efeito nenhum.** Aquela div *parece* o contêiner de rolagem e não é:
     o wrapper do sidebar é `min-h-svh` (altura **mínima**), então cresce com o
     conteúdo e a div nunca transborda. **Quem rola é o documento.** Vale saber
     antes de tentar qualquer coisa envolvendo rolagem nesta aplicação.
  2. A mesma regra no `html`, o elemento certo. **Também não resolveu** — o que
     descarta a barra de rolagem como causa.

  Hipótese remanescente: a entrada das linhas usa `opacity` e `translateY`, e
  **nenhuma das duas altera layout** — as linhas ocupam a altura final desde o
  primeiro frame, então a animação sozinha não explica a página mudar de
  tamanho. O caminho, se alguém retomar, é **medir** `scrollHeight` por frame
  durante a carga, não tentar uma terceira correção às cegas. Duas correções
  erradas seguidas indicam falta de observação, não de ideia.
- ~~**A emulação de `prefers-reduced-motion` não foi confirmada.**~~
  **CONFIRMADA em 2026-08-09**, na sessão de validação. O registro original: O Item 15
  validou badge, timeline, tabela e banners no navegador, mas o cenário que
  motivou metade do item — DevTools → Rendering → `Emulate CSS
  prefers-reduced-motion: reduce`, conferindo que nada desliza, o badge não
  pulsa e os spinners param — não foi explicitamente confirmado. A suíte não
  alcança isso (o jsdom não tem engine de CSS), então **continua não
  observado**.
- **O cliente HTTP não tem timeout nem `AbortController` em lugar nenhum de
  `src/`.** Descoberto no ciclo de 2026-07-31, ao revisar um "gate" que impedia
  fechar o diálogo de pagamento enquanto a mutation estivesse em voo. O gate foi
  **revertido** justamente por isso: sem timeout, uma requisição travada
  deixaria um modal permanentemente sem saída, e o gate não comprava nada —
  os diálogos são montados incondicionalmente e a mutation continua viva com o
  diálogo fechado. Não morde hoje porque nada mais bloqueia a interface
  esperando resposta, mas é o tipo de ausência que só aparece quando alguém
  escreve o código que depende dela. Candidato a item de backlog: um `timeout`
  no `api` do Axios e/ou `AbortController` nos fluxos longos.
- **Nenhum endpoint produz um agregado por status cruzando usuários.** No card
  "Total" da Home, para o admin (visão de todos os reembolsos), a UI mostra o
  total **solicitado** — rótulo honesto, não `approved + paid` — porque
  `GET /users/{id}/refund-stats` é por usuário; não serve para cruzar todos.
  Decisão registrada na spec do ciclo de revisão: não contornar com N
  requisições (`?status=approved&per_page=1` e `?status=paid&per_page=1`).
  Candidato a um `GET /refunds/stats` global, por status, no backlog do
  backend.
- ~~**ITEM 22 NÃO FOI VALIDADO EM NAVEGADOR.**~~ **VALIDADO em 2026-08-09**,
  junto dos Itens 23 e 24 e de cinco pendências antigas, contra um checklist de
  18 verificações. Ver o bloco de validação logo abaixo. O registro original: As duas
  branches **já foram mescladas e empurradas** (decisão do Gabriel: validar
  depois), então isto não bloqueia mais um merge — bloqueia a confiança de que
  a tela funciona. **As duas `main` mudaram de contrato juntas**, o que é
  coerente por construção e sem risco porque não existe produção. O ponto inteiro do item é uma URL assinada carregar numa tag
  `<img>` **sem cabeçalho de autenticação** — e a suíte do frontend roda contra
  MSW, ou seja, contra o payload que nós mesmos escrevemos. Checklist mínimo,
  com o backend e o frontend rodando das duas branches:
  1. Comprovante de imagem aparece no detalhe do reembolso (o `<img>` carrega
     de `/files/receipts/...?token=...`).
  2. Comprovante em PDF aparece no `<object>`, e o link de fallback abre.
  3. Tela cheia mostra o mesmo arquivo, sem segunda requisição.
  4. Comprovante de **pagamento** aparece na tela de revisão.
  5. Esperar **mais de 5 minutos** com a tela aberta e recarregar a imagem: a
     URL deve ter expirado (o `staleTime` de 150s deve ter buscado outra antes
     — se a imagem quebrar, o número está errado).
  6. Copiar a URL assinada e abrir numa aba anônima: deve funcionar enquanto
     válida (é o comportamento esperado, e é o trade-off do item), e falhar
     depois de expirar.
  7. Adulterar um caractere do token na URL: deve dar 404.
- **O avatar continua sem nenhum consumidor.** `has_avatar` é sempre `false`
  até o ciclo da foto de perfil existir — nem o painel do solicitante do
  ciclo de revisão renderiza avatar (ver o backlog do frontend, item 2, para o
  raciocínio completo).
- **Onze achados menores do ciclo de revisão (2026-07-30) ficaram
  deliberadamente adiados**, a maioria sobre lacuna de teste (um estado de
  formulário que não reseta ao cancelar, um `accept` duplicado à mão em vez de
  derivado de uma constante, uma asserção de montagem de componente que falta,
  um link de PDF genérico entre dois tipos de comprovante, guardas
  redundantes) e não sobre comportamento incorreto em produção. A lista
  completa, achado a achado, está no ledger de execução
  (registrados nas mensagens de commit da branch),
  não reproduzida aqui.
- ~~**Nada do ciclo de revisão (2026-07-30) foi validado em navegador contra a
  API real.**~~ RESOLVIDO em 2026-07-30: o Gabriel validou visualmente o ciclo
  no navegador. **Registrado com menos granularidade que os ciclos anteriores**
  — o do restyle e o do contrato novo têm, cada um, a lista do que passou e do
  que ficou aberto, enquanto aqui há a confirmação sem checklist item a item.
  Quem for reabrir isto não deve inferir que cada tela do ciclo (rota de
  revisão, aprovar/rejeitar, marcar como pago, linha do tempo do histórico,
  comprovante de pagamento, painel do solicitante, os dois cards da Home) foi
  percorrida individualmente; sabe-se que a validação aconteceu, não o alcance
  dela.
- ~~**Efeito colateral esperado do deploy do frontend: todo usuário logado é
  deslogado uma vez.**~~ **SEM EFEITO no primeiro deploy — reclassificado em
  2026-08-03.** O `AuthContext` passou a validar a sessão do `localStorage` com
  `storedUserSchema`, que exige `id`, campo que as sessões antigas não têm. O
  aviso pressupunha uma população de usuários com sessão salva contra uma
  versão anterior **em produção**; não existe produção, logo não existe essa
  população. O único navegador afetado foi o do Gabriel, em desenvolvimento, e
  isso já aconteceu em 2026-07-29. O mecanismo continua correto e o aviso volta
  a valer em qualquer deploy **futuro** que mude a forma da sessão salva.
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

- ~~**`select_for_update` segura uma conexão do pool enquanto espera.**~~
  RESOLVIDO no ciclo de 2026-07-30 (pagamento/estatísticas): `pool_size` subiu
  de 2 para 5 (`max_overflow` de 0 para 10) e um `lock_timeout` de 3s foi
  adicionado — via `connect_args={"server_settings": {"options": "-c
  lock_timeout=3000"}}`, não a forma que a documentação do asyncpg sugere
  (`server_settings={"lock_timeout": ...}`), porque essa forma é descartada em
  silêncio pelo proxy do Neon (achado documentado no
  [diário](../learning-path-progress.md)). Verificado na Task 12 desse ciclo:
  três `PATCH /refunds/{id}/status` concorrentes na mesma solicitação
  completaram em ~1,5s no total, sem `500` e sem espera longa — o cenário que
  antes produzia o 500 depois de 30s. **Pendência nova, mais restrita:** essa
  verificação foi manual (Task 12), não existe teste automatizado que
  exercite contenção real de pool/lock — ver logo abaixo.
- ~~**O ajuste de pool/lock_timeout não tem teste comportamental na suíte.**~~
  **RESOLVIDO no Item 19 (2026-08-07):** `src/test_integration/lock_contention_test.py`
  afirma, contra PostgreSQL real e de forma repetível em CI, que o
  `lock_timeout` **chega ao servidor** (`SHOW lock_timeout` = `3s` — antes só
  provado à mão) e que a contenção de linha **desiste** em vez de esperar para
  sempre, mais que o lock é liberado e que linhas diferentes não bloqueiam
  entre si.

  **Uma diferença deliberada em relação ao que esta pendência pedia:** ela
  falava em "disparar N operações concorrentes", que é a categoria mais
  propensa a flake — e este projeto já pagou caro com o do `ResizeObserver`. O
  desenho adotado **não é uma corrida**: uma transação toma o lock
  deliberadamente e segura, a outra tem um único desfecho possível. O `pool_size`
  continua coberto apenas pelas redes de proteção de parâmetro do
  `database_connection_handler_pool_test.py`; a exaustão de pool em si não tem
  teste comportamental, e isso segue em aberto.

  **O que continua sem cobertura:** o proxy do Neon. O container é PostgreSQL
  puro, e foi justamente o proxy que descartou em silêncio a forma de
  `lock_timeout` recomendada pela documentação do asyncpg. Verde aqui não prova
  que o Neon se comporta igual.
- ~~**O ciclo `upgrade`/`downgrade` das migrations é verificado à mão.**~~
  **RESOLVIDO no Item 19 (2026-08-07):** `src/test_integration/migrations_test.py`
  automatiza o ciclo contra o PostgreSQL descartável do `docker-compose.yml`,
  incluindo um teste que desce **revisão por revisão** e outro que afirma que o
  schema migrado não tem diff de autogenerate contra as entidades. O raciocínio
  original continua valendo e foi honrado: SQLite não foi usado, porque
  esconderia justamente as diferenças que o item existe para expor.
- **Existe um admin de teste no banco.** `admin.validacao@example.com` foi criado
  e promovido durante a verificação ponta a ponta do ciclo de aprovação, junto de
  `validacao.visual@example.com` e seus reembolsos de teste. São descartáveis.
- **O badge de status do frontend cobre só três variantes; vai precisar de uma
  quarta.** `features/refunds/constants/status.ts` mapeia
  `pending`/`approved`/`rejected` para `{label, variant}` do `ui/badge`, sem
  fallback (ver a pendência de fronteira de schema acima — `refundStatusSchema`
  é um `z.enum` e um valor fora dele derruba a query em `isError`). Desde o
  ciclo de 2026-07-30 do backend, `paid` é um quarto valor real de
  `refund.status`. Qualquer resposta de reembolso pago que chegue ao frontend
  atual (schema desatualizado) termina em erro de parse, não em um badge sem
  estilo — o que é o comportamento correto por construção, mas significa que o
  ciclo da UI de aprovação **precisa** adicionar a quarta entrada ao mapa e ao
  `z.enum` antes de qualquer tela poder listar um reembolso pago.
- **Mais usuários de teste no banco, do ciclo de 2026-07-30 (pagamento/
  histórico/estatísticas):** `task12-owner@example.com` (id 17, dono da
  maioria dos reembolsos de teste), `task12-other@example.com` (id 18,
  terceiro sem reembolso nenhum, usado só para os cenários `404`/`403`) e
  `task12-admin@example.com` (id 19, promovido a admin). Reembolsos de teste
  criados sob esses ids: 65–73 (nove reembolsos, cobrindo os quatro status,
  incluindo dois pagos e um com o arquivo do comprovante apagado do disco de
  propósito para testar o quarto caminho de 404 do comprovante de pagamento).
  Somam-se a `admin.validacao@example.com`, `validacao.visual@example.com` e
  `task1-verify@example.com`; todos descartáveis, nenhum removível sem acesso
  direto ao banco (não existe endpoint de exclusão de usuário).

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
- ~~**Aberto 2/4 — contraste nunca foi auditado com ferramenta.**~~
  **RESOLVIDO em 2026-08-09: Lighthouse Accessibility 100**, sem violações de
  contraste. O registro original: O checklist
  distingue "contraste parece legível" (marcado, olho humano) de "contraste
  auditado no DevTools/Lighthouse" (não marcado). Só a segunda forma produz
  número de razão de contraste; a primeira não substitui a auditoria e não é
  auditável em teste automatizado (o jsdom não calcula cor).
- ~~**Aberto 3/4 — rejeição de comprovante por tamanho/extensão em runtime.**~~
  **RESOLVIDO em 2026-08-09**, conferido no navegador. O registro original: O
  upload real (`.jpg`/`.png`/`.pdf`) foi validado, mas o caminho de rejeição não.
  Existe teste automatizado para ele (`RefundFormDialog.test.tsx` cobre a
  rejeição por tamanho), então é conferir a mensagem no navegador, não implementar.
- ~~**Aberto 4/4 — o "Choose File / No file chosen" do input nativo.**~~
  **RESOLVIDO em 2026-08-09** — decisão tomada (seguir o idioma do app) e
  implementada, ver o item sobre a substituição do controle acima. O registro
  original: Marcado como
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
- ~~**Uma diretiva de lint em `src/hooks/useObjectUrl.ts`.**~~ **MORTA — o
  arquivo não existe.** O **Item 22** (object storage e URLs assinadas) o
  apagou junto com seu teste: sem Blob no cliente, não há object URL para criar
  nem revogar. Confira com
  `ls Refund-FrontEnd/src/hooks/useObjectUrl.ts` (não encontra). Encontrada na
  triagem de 2026-08-10; é uma das quatro pendências que a oitava ocorrência do
  padrão trouxe à tona. O registro original, porque a observação sobre a regra
  continua útil se alguém reintroduzir o padrão:
  `// eslint-disable-next-line react-hooks/set-state-in-effect` sobre o
  `setUrl(null)`. A regra reporta **no máximo uma violação por corpo de
  efeito**, então a diretiva silencia o efeito **inteiro** — um `setState`
  acrescentado mais abaixo naquele mesmo efeito não seria checado.

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
- ~~**Fragilidade latente banco+arquivo — agora em DOIS lugares, não um.**~~
  **RESOLVIDO no Item 21 (2026-08-07)**, em **cinco** call sites, não dois: os
  quatro que faltavam ganharam compensação (criação de reembolso, upload de
  avatar) ou deleção que não derruba a resposta (exclusão de reembolso, remoção
  de avatar), e o pagamento passou a usar o mesmo helper compartilhado.

  **Duas correções ao registro original, que estava desatualizado:** (1) a
  compensação do pagamento **não** cobria "só a corrida perdida" — desde os
  commits `c242ed7`/`30b6f88` ela é um `try/except` em volta do bloco inteiro,
  gated por `committed`, cobrindo qualquer exceção antes do commit; (2) o
  levantamento do Item 21 encontrou uma **segunda** falha que este registro não
  mencionava, e que era pior: na exclusão, um `os.remove` que levanta devolvia
  **500 para uma operação que já tinha sido commitada**.

  **O que segue verdadeiro:** um `SIGKILL` entre o `save()` e o commit continua
  órfanando o arquivo. Nenhuma compensação em processo resolve isso — exige
  varredura posterior ou fila (Item 28).
- ~~**Pool de conexões pequeno.**~~ RESOLVIDO no ciclo de 2026-07-30: ver a
  pendência resolvida acima (`select_for_update` segurava conexão) — é o
  mesmo ajuste, `pool_size=5, max_overflow=10`.
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

- ~~**`ResizeObserver is not defined` em `Sidebar.test.tsx`**~~ **RESOLVIDO em
  2026-08-05**, depois de ser reportado desde 2026-07-29 sem causa isolada.
  Apareceu durante a verificação do Item 14 **com a saída completa salva em
  arquivo** — a captura que falhara duas vezes antes. O stack trace nomeou a
  causa: o `useSize` do Radix constrói um `ResizeObserver` num layout effect, o
  jsdom não implementa, e a exceção **não capturada** derruba qualquer teste
  que estiver rodando — não o que montou o tooltip. Essa indireção é por que
  nunca reproduziu isolado; o timing de hover/foco necessário para montar o
  Popper é por que só aparecia em suíte completa. Medido: **2 ocorrências em 5
  rodadas** antes, **8 rodadas limpas** depois do polyfill em
  `src/test/setup.ts` (commit `a194f61`, separado do Item 14). O relato
  original fica preservado abaixo porque a lição de captura não expira.
  O registro anterior:
- **`ResizeObserver is not defined` em `Sidebar.test.tsx` — CONFIRMADO
  pré-existente e independente deste projeto de mudanças, ainda dependente da
  ordem de execução e sem causa isolada.** Relatado pela primeira vez durante
  a onda de correções finais do ciclo de 2026-07-29 (3 rodadas completas na
  ponta da branch não reproduziram); **observado de novo durante a Task 4 do
  ciclo de 2026-07-30** (workflow de aprovação), de novo numa rodada de suíte
  completa e de novo não reproduzível isoladamente; uma terceira ocorrência
  provável, essa menos confiável, ficou registrada sem rastro (saída perdida
  por um corte de API). **A diferença desta vez: durante a Task 12 do ciclo de
  2026-07-31 (navegação na revisão e tabela de reembolsos), o flake apareceu
  numa árvore SEM as mudanças da task**, com elas guardadas no stash. Os
  números exatos, porque a imprecisão aqui já custou caro antes:

  - 3 rodadas completas na base (mudanças no stash): 3/3 verdes;
  - 4 rodadas com as mudanças aplicadas: 2 verdes, 2 com o flake;
  - mais 6 rodadas na base, de novo sem as mudanças: 1 falha, com o erro
    idêntico no mesmo teste.

  Ou seja **1 falha em 9 rodadas sem as mudanças, contra 2 em 4 com elas**.
  Duas ressalvas que impedem conclusão mais forte: a "base" aqui é a ponta da
  Task 11 desta mesma branch, **não a `main`** — nenhuma rodada foi feita na
  `main` limpa; e a taxa maior com as mudanças aplicadas pode ser ruído de
  amostra pequena ou pode não ser, ninguém mediu o suficiente para dizer. O
  que esta observação estabelece é mais estreito do que "o ciclo não causa":
  estabelece que **o flake ocorre sem as mudanças da Task 12**. As três
  rodadas completas da Task 13 (ponta da branch) deram 209/209 sem o flake.

  Múltiplas ocorrências, todas só em conjunto com o resto da suíte, tornam a
  hipótese de coincidência pouco plausível — mas a causa continua desconhecida;
  nenhuma investigação isolou a interação real entre arquivos de teste. Se
  aparecer de novo **com a saída completa capturada**, o caminho segue sendo um
  polyfill guardado em `src/test/setup.ts`, no mesmo padrão dos que já
  existem, mas só depois de entender a ordem que o dispara.

  **Nova ocorrência na Task 10 do ciclo de 2026-07-31 (feedback de
  carregamento), com uma ressalva sobre a qualidade da captura.** A primeira
  rodada de `npx vitest run` da sessão apresentou o flake (mesmo teste,
  `Sidebar.test.tsx`, mesmo `ReferenceError: ResizeObserver is not defined`),
  mas a saída completa **não** foi salva em arquivo naquela tentativa — só o
  final (as últimas ~40 linhas, que incluem o stack trace do erro) ficou
  capturado; o começo da saída (quais testes rodaram antes) não. As **três
  rodadas formais seguintes**, essas com a saída completa salva em arquivo,
  deram **240 testes em 44 arquivos, verdes, sem o flake, nas três**. Ou
  seja: 1 ocorrência (captura parcial) em 4 rodadas totais da sessão, 0 em 3
  quando a captura era completa. Não é a "melhor evidência até agora" que se
  esperava — é uma evidência pior que a de tentativas anteriores, porque
  faltou justamente o começo da saída. Fica registrado para não inflar
  artificialmente a taxa aparente do flake com uma amostra mal capturada, e
  para lembrar: da próxima vez que aparecer, salvar a saída em arquivo **antes**
  de olhar para ela, não depois.

  **E a lição não pegou na mesma sessão.** Na verificação final da branch,
  depois da onda de correção, uma rodada deu `1 failed | 245 passed (246)` —
  e o comando seguinte, um `grep` sobre uma nova execução, veio vazio, o que
  já era a rodada seguinte, verde. **Qual teste falhou não foi capturado.**
  Quatro rodadas depois (uma implícita no grep, três explícitas) deram
  246/246. O sintoma é compatível com este flake — falha isolada, não
  reproduzível, só em suíte completa — mas **isso é inferência, não
  observação**: ninguém viu o nome do teste nem o erro. Registrado assim de
  propósito, do mesmo jeito que a terceira ocorrência do ciclo de 2026-07-30
  ficou registrada como "provável", para que a próxima leitura não conte esta
  como confirmada. A regra prática que falhou duas vezes na mesma sessão:
  **redirecionar a saída para arquivo em toda rodada de verificação**, não só
  quando se espera um problema.
- **Ruído de jsdom `Not implemented: navigation to another Document` —
  pré-existente, confirmado por checkout destacado.** Aparece na saída de
  `npx vitest run` desde antes deste ciclo. A confirmação foi feita rodando a
  suíte em `f3c4234`, o commit base da branch de 2026-07-31 — que difere da
  `main` apenas por documentação, ou seja, com o código idêntico ao dela. O
  aviso sai igual ali. Não falha nenhum teste — é aviso do jsdom sobre navegação real
  não implementada (algum fluxo dispara `location.href =` ou similar em vez de
  um mock) — mas polui a saída e vale saber que não é novo.
- ~~**`per_page: 10` é literal escrito à mão em `src/test/msw/handlers.ts`.**~~
  RESOLVIDO no ciclo de 2026-07-31 (navegação na revisão e tabela de
  reembolsos): `src/test/msw/handlers.ts` e o loader stub de
  `src/pages/PageHome.a11y.test.tsx` passaram a importar `REFUNDS_PER_PAGE` da
  fachada da feature em vez de repetir o número — a mesma classe de problema
  que o ciclo de consulta da listagem havia fechado no código de produção,
  agora fechada também nos testes.
- **Quatro limitações conscientes do ciclo de 2026-07-31 (navegação na
  revisão e tabela de reembolsos), todas decisões documentadas em comentário
  no próprio código, não bugs:**
  - **"Próxima pendente" só enxerga a primeira página da fila.**
    `useNextPendingRefund` consulta `GET /refunds?status=pending&sort=created_at&order=asc`
    só com `page: 1`. Se as 10 pendentes mais antigas forem todas do próprio
    admin, o botão desabilita mesmo havendo outras mais adiante nas páginas
    seguintes. Varrer páginas até achar uma elegível custaria mais do que o
    caso raro vale — decisão registrada em `useNextPendingRefund.ts`.
  - **As setas do painel do solicitante ficam inertes quando a solicitação
    aberta não está entre as 10 carregadas.** O painel busca só a primeira
    página das solicitações do solicitante (`GET /refunds?user_id=`); andar
    para uma solicitação fora dessa janela exigiria paginar o painel, fora do
    escopo deste ciclo.
  - **Solicitante e data ficam ocultos no mobile.** Abaixo de `sm`, a
    `RefundsTable` colapsa as colunas `user` e `created_at` (mais `category`)
    por CSS (`meta.className`), a mesma técnica do restyle — não é perda de
    dado, é economia de largura numa tela de 390px; o admin ainda acessa data
    e solicitante no detalhe/revisão de cada linha.
  - **`category` e `user` não são ordenáveis.** A API não aceita esses dois
    valores em `sort` (a lista branca é
    `created_at`/`amount_in_cents`/`name`/`status`, ver `refundSortSchema`);
    as duas colunas têm `enableSorting: false` e nenhum `accessorFn` de
    propósito, então `column.getCanSort()` nunca as transforma em botão.
    Ordenação por essas duas dimensões exigiria um ciclo de backend antes.
- **O cliente HTTP do frontend não tem timeout nem `AbortController` em
  lugar nenhum de `src/`, candidato a item de backlog.** Achado do ciclo de
  2026-07-31 (feedback de carregamento): `src/lib/api.ts` (instância do
  Axios) não configura `timeout`, e nenhum fluxo de `src/` cria ou consome um
  `AbortController` — o `AbortSignal` que o TanStack Query encaminha ao Axios
  (Item 1) cobre só o cancelamento de **queries** ao trocar de tela, não uma
  requisição travada. Isso apareceu porque a Task 2 chegou a propor um "gate"
  no `PayRefundDialog` que impedia fechar o diálogo enquanto a mutação de
  pagamento estivesse pendente — e o gate foi **revertido** ao se notar que,
  sem timeout nem cancelamento, uma requisição que nunca respondesse deixaria
  esse modal **permanentemente sem fechar**. Hoje isso não morde: nada na UI
  bloqueia à espera de uma resposta (a mutation fica em `isPending`, mas o
  usuário sempre pode navegar para outro lugar), então é uma lacuna latente,
  não um bug ativo — mas foi exatamente essa lacuna que tornou o gate
  perigoso, e o mesmo padrão (algo que espera uma mutation antes de permitir
  fechar/navegar) reintroduziria o risco se implementado de novo sem primeiro
  resolver isto.
- ~~**Duas rodadas de aritmética de box model no sidebar discordaram entre si
  antes de convergir, e nenhuma das duas foi confirmada por observação.**~~
  **OBSERVADO em 2026-08-03, e o resultado convergido está correto** — o
  Gabriel conferiu no navegador o alinhamento dos ícones no modo trilho. O
  relato abaixo fica preservado porque a lição de processo não expira: duas
  contas igualmente convincentes chegaram a resultados diferentes, e só a
  observação decidiu. No
  ciclo de 2026-07-31 (feedback de carregamento), a Task 9 corrigiu o hover
  do item de navegação (`translate-x-2` deslocava só o conteúdo pintado, não
  a caixa que o `hover:bg-*` preenche) trocando por `pl-2`. A primeira
  rodada, no modo trilho colapsado, tentou centralizar o ícone **dentro** do
  botão de 32px — mas esse botão já se autocentra com `p-2!` simétrico, sem
  folga nenhuma para redistribuir; a correção não fazia nada de errado, só
  nada de útil. A revisão dessa task recalculou a partir do zero e achou que
  o `translate-x-2` original centralizava o **botão inteiro** dentro do
  trilho de 48px (`(48-32)/2 = 8`, exatamente o valor do `translate-x-2`), e
  a correção certa foi mover `justify-center` para o `<li>` pai
  (`SidebarMenuItem`), não para o botão. **Nenhuma das duas rodadas foi
  vista rodando** — as duas são geometria de caixa derivada do CSS gerado
  pelo Tailwind, não uma captura de tela nem uma inspeção no DevTools. Fica
  como o item mais preciso do checklist de navegador desta sessão (ver o
  relatório da Task 10) exatamente porque é o único, dos seis problemas do
  ciclo, que a suíte automatizada não consegue provar nem errado nem certo —
  o jsdom não tem engine de layout que resolva `translate`/`padding`/
  `justify-content` em pixels reais.
- **`ReceiptPreview` com `refundId=""` renderiza Skeleton para sempre.** O
  `useReceipt` desabilita a query, e uma query desabilitada do TanStack reporta
  `isPending: true` indefinidamente. A prop é `string` obrigatória e hoje só a
  página de detalhe a preenche, então não há caminho real até lá — mas é uma
  armadilha para o próximo consumidor.
- ~~**O nome acessível do botão de tela cheia é sem contexto** ("Ver em tela
  cheia").~~ **MORTA — já resolvida.** O `ReceiptPreview` decide a cópia por
  uma tabela `RECEIPT_COPY` indexada pelo `kind`, com **duas chaves distintas**:
  `receipt.viewFullscreen` ("Ver comprovante em tela cheia") e
  `receipt.viewPaymentFullscreen` ("Ver comprovante de pagamento em tela
  cheia"). Há inclusive um comentário no
  `Refund-FrontEnd/src/features/refunds/components/ReceiptPreview.tsx` nomeando
  **esta armadilha exata** como a razão da tabela existir. Confira com
  `grep -rn "viewPaymentFullscreen" Refund-FrontEnd/src`. Encontrada na triagem
  de 2026-08-10 — segunda das quatro. O cenário que a motivava continua sendo o
  caso certo de se preocupar: duas prévias na mesma página tornam um "Ver em
  tela cheia" sem qualificação indistinguível para um leitor de tela.
- **`AuthContext.test.tsx`: um dos três testes novos já passava antes.** O que
  restaura uma sessão válida não é vazio (guarda o caminho feliz do
  `storedUserSchema`), mas a prova de que o `id` realmente se propaga descansa
  **só** no segundo teste. Vale saber ao mexer nesse arquivo.
- **Sem `.env`, o `pytest` do backend nem coleta os testes.** Confirmado ao
  montar o CI (2026-08-06), escondendo o `.env` localmente: 7 erros de
  `sqlalchemy.exc.ArgumentError`, porque `src/configs` lê `DATABASE_URL` na
  importação e `create_async_engine(None)` estoura antes de qualquer mock
  existir. O workflow contorna declarando variáveis **fictícias** (nada
  conecta; a suíte é mockada), mas isso é **sintoma, não solução**:
  configuração lida em tempo de importação é exatamente o que o **Item 17**
  existe para resolver. O CI transformou uma pendência abstrata em obstáculo
  concreto.
- **O CI não bloqueia merge nem push — DECISÃO CONSCIENTE desde 2026-08-09,
  não esquecimento.** Confirmado pela API naquele dia: `Branch not protected`.

  **O motivo de não ligar:** exigir que os checks passem **quebra o fluxo
  atual**. Hoje o trabalho é mesclado local e empurrado direto na `main`; com
  checks obrigatórios o GitHub **recusa o push**, porque o check só roda depois
  do push e o push só é aceito depois do check. Na prática obriga Pull Request
  em toda mudança, inclusive num commit de documentação — atrito real para um
  desenvolvedor solo.

  **O que isso deixa em aberto:** a classe de problema que motivou o Item 16
  (o commit `2d07a8d` quebrando a `main` sem ninguém ver) segue **detectável,
  não impedida**.

  **Quando revisar:** quando houver uma segunda pessoa no repositório. Aí o
  custo do PR deixa de ser atrito e passa a ser o mecanismo de revisão.

  O registro original: Ele reporta. Tornar o check
  obrigatório exige **branch protection** no painel do GitHub (Settings →
  Branches → *Require status checks to pass*), nos dois repositórios. Enquanto
  não estiver ligado, o portão avisa mas não tranca — e a classe de problema
  que motivou o item (`2d07a8d` quebrando a `main` sem ninguém ver) fica
  detectável, não impedida.
- ~~**Erro de REGISTRO de exception handler é invisível para a suíte.**~~
  **RESOLVIDO no Item 25 (2026-08-09):** `httpx` entrou e
  `src/test_integration/api_test.py` exercita as rotas por HTTP. Reintroduzir o
  bug agora deixa os testes de unidade verdes e **falha os HTTP** — verificado.
  O registro original: Os testes
  do Item 23 chamam os handlers diretamente, então provam o mapeamento
  exceção→envelope e **não** que cada um está ligado à exceção certa.
  Reintroduzir o bug real que foi encontrado — registrar na `HTTPException` do
  FastAPI em vez da do Starlette, deixando o 404 do router escapar com o
  formato antigo — **não faz nenhum teste falhar**; foi preciso perguntar à API
  rodando. Pegar isso exigiria o `TestClient` do FastAPI e portanto **`httpx`
  como dependência**, que o projeto já dispensou duas vezes (aqui e no
  `file_routes_test.py`). Se um dia a conta virar, é uma dependência só de
  teste e destravaria testes de rota de verdade nos dois lugares.
- **O `boto3` é exigido para subir a aplicação mesmo com
  `STORAGE_BACKEND=local`.** `src/drivers/storage_factory.py` importa
  `S3FileStorage` no topo do módulo, e **todo composer importa essa fábrica** —
  então uma dependência de um caminho que nunca é executado passou a ser
  requisito de startup. Numa máquina com o venv correto isso não morde; morde
  em qualquer ambiente que instale só o necessário.

  **A correção é de duas linhas** (mover o import para dentro do ramo `s3`,
  com `# pylint: disable=import-outside-toplevel`). Foi escrita e verificada em
  2026-08-08 — a app sobe com o `boto3` bloqueado e o modo `s3` continua
  exigindo-o — e depois **revertida**, porque tinha sido feita sob a hipótese
  errada de que era a causa de um problema do Gabriel (era o venv desativado).

  **Armadilha para quem for escrever o teste dessa correção**, aprendida ao
  errar: um teste que bloqueia `__import__("boto3")` **passa isolado e falha na
  suíte completa**. O pytest **importa** `src/test_integration/s3_storage_test.py`
  durante a COLETA, antes de desselecioná-lo pelo marker, então `boto3` já está
  em `sys.modules` e bloquear o import não faz efeito. Pior: o bug real
  acontece no import da aplicação, que já ocorreu antes de qualquer teste
  rodar. A única forma honesta é um **subprocesso** que instale o bloqueio e só
  então importe a app.

- ~~**O boto3 já passou da data em que anunciou o fim do suporte a Python
  3.9.**~~ **FECHADA como SUBPRODUTO em 2026-08-10:** os **9
  `PythonDeprecationWarning`** da suíte de integração são agora **0**, medidos
  antes e depois. A decisão de **não silenciar o aviso** foi o que fez este
  item funcionar: ele era sinal, e o sinal foi obedecido. Vale registrar como o
  contraexemplo mais claro do projeto para "silencie o warning e siga" — um
  aviso suprimido em 2026-08-07 teria removido o argumento que motivou este
  ciclo. O registro original: a versão instalada (1.42.97) emitia
  `PythonDeprecationWarning` dizendo "no longer support Python 3.9 starting
  April 29, 2026", data já passada em 2026-08-07; o CI e o `.venv` estavam em
  3.9 porque foi assim que o projeto começou.
- **REGRESSÃO INTRODUZIDA E CORRIGIDA: o `X-Frame-Options: DENY` do Item 27
  quebrou o preview de PDF.** Relatado pelo Gabriel em 2026-08-09, do
  navegador. O header foi aplicado a **toda** resposta, inclusive `/files/` —
  e um PDF é exibido por `<object>`, que **é** enquadramento. Imagens seguiram
  funcionando porque `<img>` não é, então o sintoma se leu como "PDF quebrou"
  em vez de "um header está largo demais".

  **Os testes do Item 27 não pegaram**, e o motivo é o de sempre nesta sessão:
  eles afirmavam que o header estava **presente** — e estava. Ninguém afirmava
  que um PDF ainda **renderiza**. **Quarta vez com essa forma**: testei a peça,
  não a montagem.

  **Corrigido escopando por caminho**, não afrouxando: `/files/` recebe
  `Content-Security-Policy: frame-ancestors` com as mesmas origens já confiadas
  para chamar a API; todo o resto mantém `DENY` mais `frame-ancestors 'none'`.
  `SAMEORIGIN` não serviria (portas diferentes são origens diferentes), e com
  S3 o arquivo nem passa pelo middleware — os dois backends divergiriam.
  Teste de regressão afirma a **ausência** do header em `/files/`.
- **O erro de CORS é o ÚNICO que escapa do envelope de problem+json.** Uma
  origem não autorizada recebe `400 Bad Request` com o corpo em texto puro
  `Disallowed CORS origin`, gerado pelo `CORSMiddleware` do Starlette. Ele roda
  **antes** dos nossos exception handlers, então não vira documento RFC 9457,
  não tem `request_id` e não aparece com contexto no log de acesso.

  **O sintoma engana**, e isso foi observado de verdade em 2026-08-09: o
  Gabriel rodou `npm run preview` (porta 4173, fora da lista de origens) e
  relatou "não consigo logar nem criar conta, o backend recebe a requisição e
  responde 400". Parecia rejeição de credencial; era a **pergunta prévia do
  navegador** sendo recusada, e o cadastro nunca chegou a ser tentado — provado
  por `curl`, que criou a conta com 201 no mesmo instante.

  **Mitigado, não resolvido:** a porta 4173 entrou no `.env.example` e no `.env`
  local, então o caso concreto não morde mais. Padronizar a resposta exigiria
  um handler próprio antes do CORSMiddleware ou substituí-lo — e vale pesar se
  compensa, porque um erro de CORS é lido no console do navegador, não pelo
  cliente HTTP.
- ~~**O `.venv` do `Refund-api` tem shebangs de um caminho antigo**
  (`.../React/Refund-api`).~~ **FECHADA como SUBPRODUTO em 2026-08-10.** Subir
  para o Python 3.13 **obrigava** a recriar o venv, e o venv novo nasceu com os
  shebangs apontando para este repositório. `.venv/bin/pytest` e
  `.venv/bin/pylint` voltaram a funcionar direto. Confira com
  `head -1 .venv/bin/pytest`. Registrada aqui como pendência de ambiente desde
  antes da trilha acabar; nunca foi de código.
- **Sobrou mais um usuário de teste no banco:** `task1-verify@example.com`
  (id 15), criado na verificação do fast-forward do backend. Não existe endpoint
  de exclusão de usuário. Junta-se a `admin.validacao@example.com` e
  `validacao.visual@example.com`; todos descartáveis.
- **Mais um usuário de teste, do Item 17 (2026-08-07):**
  `item17-verify@example.com`, criado para provar ponta a ponta que a assinatura
  de JWT funciona lendo o segredo pela `Settings` (registro 201 → login com
  token de 3 partes → `GET /refunds` com esse token respondendo 200). Sem
  reembolsos associados; descartável como os demais, e igualmente sem endpoint
  de exclusão.

- **CONFERIR A CONTAGEM DO DEPENDABOT DEPOIS DO MERGE — passo pós-merge, e é
  a única parte do ciclo de Python 3.13 que não pôde ser concluída dentro
  dele.** O critério de pronto original do plano dizia
  `gh api dependabot/alerts?state=open` devolvendo **0**. Ele é **inalcançável
  numa branch**: o Dependabot avalia a **branch padrão**, e os pins vivem em
  `chore/python-313-upgrade`. Confirmado — `default_branch` é `main` e a
  contagem **continua 37**. **Não trate isso como falha das correções**; elas
  simplesmente ainda não estão na `main`.

  **O que ESTÁ provado, deterministicamente e recalculado duas vezes por
  caminhos independentes:**
  - os **37** alertas brutos são **19 advisories distintos contados duas
    vezes**, porque o `requirements-dev.txt` começa com `-r requirements.txt` e
    o Dependabot conta por manifesto;
  - os **19** estão **todos** satisfeitos pelas versões fixadas nesta branch;
  - o teste "pin >= primeira versão corrigida" é **válido aqui**, e isso foi
    verificado em vez de suposto: cada um dos 19 `vulnerable_version_ranges` é
    um **intervalo único e limitado**, cujo limite superior é exatamente o
    `first_patched_version` — não há faixa disjunta nem duas linhas de correção
    paralelas, que é o caso em que essa comparação daria falso verde;
  - o `requirements.txt` é um **fecho transitivo completo** (equivalente a um
    lock), então nenhum pacote poderia ser estruturalmente ignorado.

  **Verificar que a contagem chega a zero é um passo pós-merge**, para o
  Gabriel, com `gh api /repos/:owner/:repo/dependabot/alerts?state=open` depois
  que a branch entrar na `main`. Até lá, este documento **não afirma zero**.

- **O `Refund-FrontEnd` passou o projeto inteiro com o Dependabot DESLIGADO —
  ninguém estava olhando.** Ligado em 2026-08-10 (a API respondia 403
  "disabled" antes disso). **Primeira varredura: 10 alertas, 9 high e 1
  medium** — `brace-expansion` ×3, `js-yaml` ×2, `nanoid` ×2, `postcss` ×2,
  `react-router` ×1. **Nada foi corrigido, de propósito:** o escopo daquela
  task era transformar um ponto cego em um número, não abrir uma segunda frente
  de atualização dentro de um ciclo de backend. Entra na varredura de
  pendências como item próprio.

  Vale notar a assimetria que isso expõe: o `Refund-api` acumulou 37 alertas
  **visíveis e ignorados**; o `Refund-FrontEnd` acumulou 10 **invisíveis**. O
  segundo é o pior dos dois estados, porque não produz nem o incômodo que
  eventualmente força a ação.

- **A saída dos testes deixou de ser limpa: `StarletteDeprecationWarning`.**
  Depois do major, o `TestClient` avisa para usar `httpx2`, e o aviso aparece
  nas duas suítes — é o `1 warning` que acompanha os 341 e os 72 (ver
  `:2085` acima, que já registra a suíte mockada em 341). Ele é
  reportado em `fastapi/testclient.py:1` (o reexport), não no arquivo do
  Starlette de onde vem; procurar pela origem no `starlette/` não acha.
  Não afeta resultado nenhum. Fica registrado porque saída de teste suja é
  como um aviso **real** passa despercebido — e este projeto acabou de
  registrar, logo acima, um ciclo inteiro que existiu porque um warning **não**
  foi silenciado.
  **Esta mesma frase já foi a prova do padrão que ela descreve.** Ela dizia
  335, foi corrigida para 340 no commit `ec29ce1` — e ficou obsoleta **dentro
  do mesmo commit**, porque a outra correção daquela onda (`S3_REGION`
  obrigatória, `:2071` acima) acrescentou um teste e moveu o total real para
  341 antes que o commit fechasse. Duas correções da mesma onda mexeram no
  mesmo fato por direções diferentes; a que rodou por último venceu, e a
  primeira só foi notada certa por um instante.

- **`host.docker.internal` é específico do Docker Desktop e não está
  documentado no repo.** A verificação do container aponta o container para o
  PostgreSQL do `docker-compose` do host por esse nome. Em Docker Engine puro
  no Linux ele não resolve sem `--add-host=host.docker.internal:host-gateway`.
  Quem repetir a verificação em outra máquina precisa saber.

- **`logging_config_test.py` roda `json.loads` sobre cada linha de stdout.** Um
  `print` solto no caminho de requisição vira `JSONDecodeError` em vez de uma
  falha de asserção legível. Falha alto, então não é risco de correção — é
  custo de diagnóstico para quem esbarrar.
