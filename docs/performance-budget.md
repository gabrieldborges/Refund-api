# Orçamento de performance

Linha de base medida em **2026-08-09** (Item 31). Existe para responder uma
pergunta que hoje ninguém consegue: *"isto piorou, ou o projeto só cresceu?"*

O item que originou este documento avisa: **otimização sem medição tende a
aumentar complexidade no lugar errado.** Estes números são para serem
comparados antes de otimizar, não para serem perseguidos.

## Frontend

Medido com `npm run build && npm run preview`, Lighthouse na **tela de login**.

| Métrica | Desktop | Mobile | Limite que trataríamos como regressão |
|---|---|---|---|
| LCP (conteúdo principal aparece) | **0,6 s** | **2,9 s** | Desktop > 1,5 s · Mobile > 4 s |
| TBT (página travada) | **40 ms** | — | > 200 ms |
| Nota de Performance | **90** | — | < 80 |

**Os dois modos não são comparáveis entre si.** Mobile simula 4G lento e
processador 4× mais devagar; Desktop simula ~40 ms de latência e 10 Mbps, com
processador normal. Comparar um com o outro já produziu uma conclusão errada
nesta trilha — sempre compare Mobile com Mobile.

### Peso transferido na primeira visita

| | Bruto | Gzip |
|---|---|---|
| JS + CSS | 813 kB | **243 kB** |
| Fonte (latin) | — | 43 kB |

### De onde vem o peso

| | Gzip |
|---|---|
| React, React DOM, React Router, react-hook-form | ~91 kB |
| TanStack Query | ~21 kB |
| axios | 17 kB |
| Zod | 15 kB |
| i18next | 14 kB |
| tailwind-merge | 9 kB |
| **total de dependências** | **188 kB (81%)** |
| **nosso código** | **~44 kB (19%)** |

**Não há gordura**: nenhuma biblioteca duplicada, nenhum import de raiz
trazendo o que não se usa, nenhuma dependência esquecida. Os 188 kB são o
preço desta pilha, e reduzi-los significaria trocar de biblioteca, não
otimizar.

Medido temporariamente com `manualChunks` por dependência, usando a saída do
próprio Vite — o `source-map-explorer` não lê os sourcemaps deste Vite, que é
rolldown-based. **Ressalva:** o agrupamento cortava nomes no primeiro hífen,
então as famílias `react-*` aparecem somadas. Suficiente para decidir, não para
citar por pacote.

### Gráficos (nivo), medido em 2026-08-11

O gráfico de rosca da tela de revisão usa `@nivo/pie`, que traz junto
`@nivo/core`, `@nivo/arcs`, `react-spring`, `lodash` e sete pacotes `d3-*`.

| Chunk | Bruto | Gzip |
|---|---|---|
| `RefundDonutChart` (sob demanda) | 222,8 kB | **74,2 kB** |
| Entrada (`index`) | 708,7 kB | 219,4 kB |

### Gráficos (nivo), re-medido em 2026-08-11 após o Dashboard

O Dashboard trouxe `@nivo/bar` e `@nivo/line`, e o Rollup redistribuiu a árvore do
nivo em vários chunks compartilhados. Os nomes dos chunks são o de um módulo
pequeno que caiu dentro deles (`chartPalette`, `ChartFrame`) — o conteúdo é o
vendor.

| Chunk | Bruto | Gzip |
|---|---|---|
| `chartPalette` (núcleo do nivo + d3) | 189,2 kB | 65,4 kB |
| `RefundLineChart` | 53,7 kB | 17,8 kB |
| `nivo-bar` | 41,5 kB | 13,0 kB |
| `ChartFrame` | 33,0 kB | 10,9 kB |
| `RefundDonutChart` | 35,3 kB | 10,7 kB |
| `RefundBarChart` + `RefundStackedBarChart` + `line` | 6,3 kB | 3,1 kB |
| **Total de gráficos, sob demanda** | **359,0 kB** | **≈120,7 kB** |
| Entrada (`index`) | 568,0 kB | **174,1 kB** |

**O custo de gráficos subiu de 74,2 para ≈120,7 kB gzip** — os 46,5 kB a mais são
`@nivo/bar` e `@nivo/line`. **A entrada subiu 0,9 kB**, de 173,1 para 174,1: a
divisão continua de pé. Se esses 120 kB estivessem na entrada, ela estaria perto de
294 kB gzip, e é essa comparação que serve de verificação — não a presença de um
chunk separado, que existe de qualquer forma.

O que mantém a divisão: **nenhum gráfico é reexportado por fachada nenhuma**. Quem
a fachada de `features/refunds` exporta é o `DashboardCharts`, que faz o `import()`
dos quatro por dentro. Um `export { default as RefundBarChart } from …` desfaria
isso sem erro nenhum.

**74 kB gzip é um terço de todo o resto da aplicação somado** — por isso o
gráfico é carregado com `React.lazy` a partir do `RequesterPanel`, e não
importado direto. Quem abre a Home, faz login ou cria uma solicitação nunca
baixa nada disso; o custo só existe para o admin que abre uma revisão.

O que mantém essa separação de pé, e quebra em silêncio se alguém mexer: o
`RefundDonutChart` **não** pode ser reexportado pela fachada da feature
(`src/features/refunds/index.ts`). Uma reexportação estática traria o chunk
inteiro de volta para o bundle de entrada, sem erro nenhum — só um `index` 74 kB
mais gordo. Confira no `npm run build`: enquanto houver uma linha
`dist/assets/RefundDonutChart-*.js` separada, a divisão está funcionando.

## Backend

Consulta de listagem (JOIN com `users`, filtro por dono, ordenação por data,
`LIMIT 10`), 20 execuções contra PostgreSQL descartável:

| Escala | Sem índice | Com índice |
|---|---|---|
| 80 linhas (hoje) | **0,33 ms** | planejador ignora o índice |
| 50.000 linhas | 2,07 ms | **0,52 ms** |

O índice `ix_refunds_user_created` existe desde 2026-08-09. **Nada disso é
percebido por um usuário hoje** — 2 ms é invisível. Está aqui como linha de
base para quando o volume mudar.

## Como remedir

```bash
# frontend
cd Refund-FrontEnd && npm run build && npm run preview
# Lighthouse no Chrome, tela de login, MESMO modo do número que vai comparar

# backend
cd Refund-api && docker compose up -d
# EXPLAIN ANALYZE contra o banco descartável, nunca contra o Neon
```

## O que NÃO é sintoma

Escrito porque cada um destes já custou tempo neste projeto:

- **O aviso de "chunk maior que 500 kB" do Vite.** É o limiar padrão de uma
  ferramenta que não sabe nada deste app. Está aberto desde o restyle e não
  corresponde a queixa nenhuma.
- **Lighthouse contra `npm run dev`.** Mede o servidor de desenvolvimento:
  módulos não minificados, sem bundling, com o cliente de recarga no meio. Deu
  54% de Performance em 2026-08-09 e o número foi descartado — corretamente.
- **Um número comparado com outro medido em modo diferente.** Ver a ressalva
  dos dois modos acima.
