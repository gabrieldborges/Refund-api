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
