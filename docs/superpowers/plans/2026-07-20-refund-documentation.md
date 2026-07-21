# Refund Documentation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Criar no `Refund-api` a documentação canônica do estado atual do produto Refund e conectar o `Refund-FrontEnd` a essa fonte única da verdade.

**Architecture:** A documentação funcional compartilhada viverá em `Refund-api/docs/`, com rastreabilidade entre visão, regras de negócio, casos de uso, modelo de domínio e ADRs. Os arquivos `AGENTS.md`, `CLAUDE.md` e `README.md` funcionarão como entradas ou instruções técnicas, sem duplicar requisitos; intenções futuras ficarão isoladas em `roadmap.md`.

**Tech Stack:** Markdown, Git, comandos de verificação com `rg` e `git diff`.

## Global Constraints

- O repositório `Refund-api` é a fonte canônica da documentação compartilhada.
- Documentar somente comportamentos confirmados pelo código, testes ou configuração atual.
- Não inventar funcionalidades futuras; deixar `roadmap.md` preparado para recebê-las.
- Não alterar o comportamento da aplicação nem adicionar dependências.
- Não duplicar regras de negócio nos arquivos específicos de agentes.
- Preservar as instruções técnicas específicas de cada repositório.
- Tratar `Refund-api` e `Refund-FrontEnd` como repositórios Git independentes.

---

### Task 1: Fundação da documentação canônica

**Files:**
- Create: `Refund-api/docs/index.md`
- Create: `Refund-api/docs/vision.md`
- Create: `Refund-api/docs/glossary.md`
- Create: `Refund-api/docs/roadmap.md`

**Interfaces:**
- Consumes: especificação `Refund-api/docs/superpowers/specs/2026-07-20-refund-documentation-design.md` e comportamento observado nos dois repositórios.
- Produces: mapa canônico da documentação, vocabulário comum e separação explícita entre estado atual e intenções futuras.

- [ ] **Step 1: Criar o índice canônico**

Criar `docs/index.md` com esta organização e links relativos:

```markdown
# Documentação do Refund

Esta é a fonte canônica dos requisitos e das decisões compartilhadas pelo
frontend e pela API.

## Produto
- [Visão do produto](vision.md)
- [Glossário](glossary.md)
- [Regras de negócio](business-rules.md)
- [Modelo de domínio](domain-model.md)
- [Roadmap](roadmap.md)

## Casos de uso
- [UC-001 — Cadastrar usuário](use-cases/UC-001-register-user.md)
- [UC-002 — Autenticar usuário](use-cases/UC-002-authenticate-user.md)
- [UC-003 — Criar solicitação de reembolso](use-cases/UC-003-create-refund.md)
- [UC-004 — Listar solicitações](use-cases/UC-004-list-refunds.md)
- [UC-005 — Consultar solicitação](use-cases/UC-005-view-refund.md)
- [UC-006 — Excluir solicitação](use-cases/UC-006-delete-refund.md)

## Decisões
- [ADR-001 — Manter a arquitetura em camadas da API](decisions/ADR-001-layered-api.md)
- [ADR-002 — Utilizar PostgreSQL no Neon](decisions/ADR-002-postgresql-neon.md)
- [ADR-003 — Armazenar comprovantes no disco local](decisions/ADR-003-local-receipt-storage.md)
```

- [ ] **Step 2: Documentar a visão comprovada do produto**

Criar `docs/vision.md` contendo:

```markdown
# Visão do produto

## Problema
Pessoas precisam registrar despesas acompanhadas de comprovantes para solicitar
reembolso e consultar posteriormente essas solicitações.

## Usuários atuais
- Usuário standard: cadastra e consulta somente suas solicitações.
- Administrador: consulta as solicitações de todos os usuários.

## Objetivo atual
Permitir cadastro, autenticação, envio, busca, consulta e exclusão de
solicitações de reembolso com comprovante.

## Dentro do escopo atual
- Cadastrar usuário standard.
- Autenticar usuário.
- Criar solicitação com comprovante.
- Listar e buscar solicitações com paginação.
- Consultar uma solicitação e abrir seu comprovante.
- Excluir uma solicitação e seu comprovante.
- Restringir usuário standard aos próprios registros e permitir que admin
  consulte todos os registros.

## Fora do escopo comprovado
- Aprovar ou rejeitar solicitações.
- Alterar uma solicitação existente.
- Processar pagamentos.
- Manter um fluxo de estados ou histórico de transições.
```

- [ ] **Step 3: Criar o glossário do domínio**

Criar `docs/glossary.md` com definições objetivas para: `Usuário`, `Usuário
standard`, `Administrador`, `Solicitação de reembolso`, `Comprovante`,
`Categoria`, `Valor em centavos`, `Autenticação` e `Proprietário da
solicitação`. Explicar que "solicitação" e "reembolso" nomeiam o mesmo
registro no contexto da interface e da API.

- [ ] **Step 4: Preparar o roadmap sem inventar funcionalidades**

Criar `docs/roadmap.md` com as seções `Como usar`, `Ideias`, `Em análise` e
`Aprovadas para planejamento`. Definir os estados `Ideia`, `Em análise` e
`Aprovada`, conforme a especificação. Manter as três listas com a mensagem
`Nenhuma intenção registrada.`

- [ ] **Step 5: Verificar links e escopo**

Run:

```bash
cd Refund-api
rg -n "\[.*\]\([^)]*\)" docs/index.md
rg -n "aprova|rejeita|pagamento|edição" docs/vision.md docs/roadmap.md
git diff --check
```

Expected: o índice lista todos os documentos planejados; funcionalidades não
implementadas aparecem somente como limites de escopo, não como fatos ou itens
inventados do roadmap; `git diff --check` não mostra erros.

- [ ] **Step 6: Commit da fundação**

```bash
git add docs/index.md docs/vision.md docs/glossary.md docs/roadmap.md
git commit -m "docs: add Refund documentation foundation"
```

---

### Task 2: Regras de negócio e modelo de domínio

**Files:**
- Create: `Refund-api/docs/business-rules.md`
- Create: `Refund-api/docs/domain-model.md`

**Interfaces:**
- Consumes: entidades, validadores, controladores, middleware JWT, repositórios e armazenamento de comprovantes da API.
- Produces: identificadores `BR-001` a `BR-015`, referenciados pelos casos de uso da Task 3.

- [ ] **Step 1: Registrar as regras comprovadas**

Criar `docs/business-rules.md` usando exatamente estes identificadores e
significados:

```text
BR-001  Cadastro exige nome, e-mail válido e senha com pelo menos 8 caracteres.
BR-002  E-mail de usuário deve ser único.
BR-003  Cadastro público sempre cria usuário com papel standard.
BR-004  Senha deve ser armazenada de forma protegida e nunca retornada pela API.
BR-005  Login inválido usa mensagem genérica para e-mail ausente ou senha incorreta.
BR-006  Operações de reembolso exigem JWT válido.
BR-007  Solicitação exige nome não vazio, categoria permitida, valor positivo e comprovante.
BR-008  Categorias permitidas são food, lodging, transport, service e others.
BR-009  Comprovante deve ter extensão jpg, jpeg, png ou pdf e tamanho máximo de 4 MiB.
BR-010  Valor recebido em reais é persistido como inteiro em centavos.
BR-011  Cada solicitação pertence obrigatoriamente ao usuário autenticado que a criou.
BR-012  Usuário standard lista e acessa somente suas solicitações; admin pode acessar todas.
BR-013  Consulta ou exclusão de ID inexistente ou alheio responde como não encontrado.
BR-014  Listagem ordena solicitações da mais recente para a mais antiga e permite busca parcial por nome.
BR-015  Exclusão remove o registro e tenta remover seu arquivo de comprovante.
```

Para cada regra, acrescentar `Evidências` com caminhos de arquivos concretos.
Não chamar escolhas como SQLAlchemy, FastAPI ou React Query de regras de
negócio.

- [ ] **Step 2: Documentar o modelo existente**

Criar `docs/domain-model.md` com:

- entidade `User`: `id`, `name`, `email`, senha protegida, `role`, `created_at`;
- entidade `Refund`: `id`, `user_id`, `name`, `category`, `amount_in_cents`,
  `filename`, `created_at`;
- relação `User 1 ---- 0..* Refund`;
- invariantes relacionadas a `BR-002`, `BR-003`, `BR-008`, `BR-010` e `BR-011`;
- observação explícita de que o modelo atual não possui status, aprovação,
  rejeição ou histórico de transições.

- [ ] **Step 3: Validar numeração e evidências**

Run:

```bash
cd Refund-api
for id in $(seq -w 1 15); do rg -q "BR-0${id}" docs/business-rules.md || exit 1; done
rg -n "src/" docs/business-rules.md
git diff --check
```

Expected: todas as regras `BR-001` a `BR-015` existem, cada regra possui ao
menos uma evidência e não há erro de whitespace.

- [ ] **Step 4: Commit das regras e do modelo**

```bash
git add docs/business-rules.md docs/domain-model.md
git commit -m "docs: record Refund business rules and domain"
```

---

### Task 3: Casos de uso rastreáveis

**Files:**
- Create: `Refund-api/docs/use-cases/UC-001-register-user.md`
- Create: `Refund-api/docs/use-cases/UC-002-authenticate-user.md`
- Create: `Refund-api/docs/use-cases/UC-003-create-refund.md`
- Create: `Refund-api/docs/use-cases/UC-004-list-refunds.md`
- Create: `Refund-api/docs/use-cases/UC-005-view-refund.md`
- Create: `Refund-api/docs/use-cases/UC-006-delete-refund.md`

**Interfaces:**
- Consumes: regras `BR-001` a `BR-015` e os fluxos implementados nas rotas, controladores e telas atuais.
- Produces: descrição verificável dos seis objetivos disponíveis ao usuário.

- [ ] **Step 1: Documentar cadastro e autenticação**

Usar em ambos os arquivos as seções `Ator principal`, `Objetivo`,
`Pré-condições`, `Fluxo principal`, `Fluxos alternativos e erros`,
`Pós-condições`, `Regras relacionadas` e `Evidências`.

- `UC-001`: cadastro com nome, e-mail e senha; sucesso cria `standard` e leva o
  frontend ao login; cobrir e-mail duplicado e entrada inválida; relacionar
  `BR-001` a `BR-004`.
- `UC-002`: login devolve JWT e dados não sensíveis; frontend persiste token e
  usuário; cobrir credenciais inválidas; relacionar `BR-004` e `BR-005`.

- [ ] **Step 2: Documentar criação de solicitação**

No `UC-003`, registrar o envio multipart, validações, geração de nome único
para o comprovante, conversão do valor e associação ao token. Cobrir token
ausente/inválido, nome vazio, categoria inválida, valor não positivo, extensão
inválida e arquivo acima de 4 MiB. Relacionar `BR-006` a `BR-011`.

- [ ] **Step 3: Documentar listagem e consulta**

- `UC-004`: paginação com `page >= 1`, `1 <= per_page <= 100`, busca parcial
  por nome, ordenação decrescente por criação e distinção standard/admin;
  relacionar `BR-006`, `BR-012` e `BR-014`.
- `UC-005`: consulta por ID, exibição e abertura do comprovante; registrar o
  mesmo resultado 404 para inexistente e alheio; relacionar `BR-006`, `BR-012`
  e `BR-013`.

- [ ] **Step 4: Documentar exclusão**

No `UC-006`, registrar confirmação no frontend, validação de propriedade,
remoção do banco, tentativa de remoção do comprovante e retorno à lista.
Relacionar `BR-006`, `BR-012`, `BR-013` e `BR-015`.

- [ ] **Step 5: Verificar rastreabilidade**

Run:

```bash
cd Refund-api
for id in $(seq -w 1 6); do rg -q "UC-00${id}" docs/use-cases || exit 1; done
for id in $(seq -w 1 15); do rg -q "BR-0${id}" docs/use-cases || exit 1; done
rg -L "## Evidências" docs/use-cases/*.md
git diff --check
```

Expected: seis casos de uso encontrados, todas as quinze regras referenciadas
por ao menos um caso, nenhum arquivo sem `Evidências` e nenhum erro de
whitespace.

- [ ] **Step 6: Commit dos casos de uso**

```bash
git add docs/use-cases
git commit -m "docs: add current Refund use cases"
```

---

### Task 4: Decisões arquiteturais atuais

**Files:**
- Create: `Refund-api/docs/decisions/ADR-001-layered-api.md`
- Create: `Refund-api/docs/decisions/ADR-002-postgresql-neon.md`
- Create: `Refund-api/docs/decisions/ADR-003-local-receipt-storage.md`

**Interfaces:**
- Consumes: organização atual da API, configuração de banco e driver `ReceiptStorage`.
- Produces: contexto, decisão e consequências das três escolhas técnicas duráveis atualmente comprovadas.

- [ ] **Step 1: Registrar a organização em camadas**

Criar `ADR-001-layered-api.md` com status `Aceita`, contexto de projeto de
estudo, decisão de manter `models/controllers/views/validators/errors/main`,
injeção pelos composers e consequências: mais arquivos e interfaces, regras
testáveis isoladamente e necessidade de preservar os limites existentes.

- [ ] **Step 2: Registrar PostgreSQL no Neon**

Criar `ADR-002-postgresql-neon.md` com status `Aceita`, data `2026-07-15`,
migração do SQLite, uso de `postgresql+asyncpg`, exigência de `ssl=require` em
vez de `sslmode`, criação de tabelas via `metadata.create_all` e consequências
operacionais. Não registrar segredos nem copiar `DATABASE_URL` real.

- [ ] **Step 3: Registrar armazenamento local de comprovantes**

Criar `ADR-003-local-receipt-storage.md` com status `Aceita`, diretório
configurável por `UPLOAD_DIR`, exposição por `/receipts`, nomes com UUID,
validação por extensão e consequências: simplicidade atual, dependência do
disco da instância e ausência de armazenamento distribuído.

- [ ] **Step 4: Verificar o formato dos ADRs**

Run:

```bash
cd Refund-api
rg -L "## Status" docs/decisions/*.md
rg -L "## Contexto" docs/decisions/*.md
rg -L "## Decisão" docs/decisions/*.md
rg -L "## Consequências" docs/decisions/*.md
git diff --check
```

Expected: nenhum nome de arquivo é impresso pelos quatro primeiros comandos e
não há erro de whitespace.

- [ ] **Step 5: Commit dos ADRs**

```bash
git add docs/decisions
git commit -m "docs: record current Refund architecture decisions"
```

---

### Task 5: Entradas documentais da API

**Files:**
- Modify: `Refund-api/README.md`
- Modify: `Refund-api/AGENTS.md`
- Modify: `Refund-api/CLAUDE.md`

**Interfaces:**
- Consumes: documentação canônica criada nas Tasks 1 a 4.
- Produces: entradas curtas e coerentes para humanos, Codex, Cursor e Claude.

- [ ] **Step 1: Atualizar o README da API**

Corrigir as referências antigas ao frontend (`React/Refund`) para
`../Refund-FrontEnd`, adicionar link para `docs/index.md` e substituir o exemplo
SQLite por PostgreSQL:

```env
DATABASE_URL=postgresql+asyncpg://usuario:senha@host/database?ssl=require
UPLOAD_DIR=uploads/receipts
JWT_SECRET=uma-chave-secreta-aleatoria
JWT_ALGORITHM=HS256
JWT_EXPIRATION_HOURS=8
```

Explicar que a senha e o host são exemplos, que o `.env` não deve ser
versionado e que `metadata.create_all` cria as tabelas no startup. Manter as
instruções de execução, Swagger, autenticação e Postman que ainda correspondem
ao projeto.

- [ ] **Step 2: Transformar AGENTS.md em contrato de trabalho**

Reorganizar `AGENTS.md` com estas seções:

```text
Fonte da verdade
Antes de implementar
Durante a implementação
Regras técnicas da API
Verificação
Em caso de divergência
Depois da implementação
```

Apontar para `docs/index.md`; preservar Clean Architecture, middleware FastAPI,
testes pytest ao lado do código, fixtures em `conftest.py`, comentários de teste
em inglês e comandos `pytest`/`pylint src`. Remover a narrativa funcional que
agora está representada nas regras, casos de uso e ADRs.

- [ ] **Step 3: Reduzir CLAUDE.md a um adaptador**

Substituir o conteúdo por:

```markdown
# Instruções para Claude Code

Leia e siga as instruções compartilhadas em:

@AGENTS.md

O índice canônico da documentação do produto está em:

@docs/index.md

Não trate este arquivo como uma fonte separada de requisitos.
```

- [ ] **Step 4: Verificar entradas e referências obsoletas**

Run:

```bash
cd Refund-api
rg -n "docs/index.md" README.md AGENTS.md CLAUDE.md
rg -n "sqlite|SQLite|React/Refund|../Refund\b" README.md AGENTS.md CLAUDE.md
git diff --check
```

Expected: os três arquivos apontam para o índice; a segunda busca não retorna
referências obsoletas; não há erro de whitespace.

- [ ] **Step 5: Commit das entradas da API**

```bash
git add README.md AGENTS.md CLAUDE.md
git commit -m "docs: connect API entry points to canonical docs"
```

---

### Task 6: Entradas documentais do frontend

**Files:**
- Modify: `Refund-FrontEnd/AGENTS.md`
- Modify: `Refund-FrontEnd/CLAUDE.md`
- Modify: `Refund-FrontEnd/README.md`

**Interfaces:**
- Consumes: `Refund-api/docs/index.md` como fonte canônica compartilhada.
- Produces: referências do frontend para a documentação do produto sem duplicar regras.

- [ ] **Step 1: Reorganizar AGENTS.md do frontend**

Adicionar no início uma seção `Fonte da verdade` com link relativo
`../Refund-api/docs/index.md`. Preservar stack, Atomic Design, textos de UI em
português, identificadores em inglês, processo incremental, regra de explicar
infra transversal, comando `npx tsc -b --noEmit` e lições específicas de
responsividade. Remover ou resumir regras funcionais já canônicas em `docs/`.

- [ ] **Step 2: Reduzir CLAUDE.md a um adaptador**

Substituir o conteúdo por:

```markdown
# Instruções para Claude Code

Leia e siga as instruções do frontend em:

@AGENTS.md

A documentação canônica do produto está em:

@../Refund-api/docs/index.md

Não trate este arquivo como uma fonte separada de requisitos.
```

- [ ] **Step 3: Substituir o README de template**

Criar um README curto e específico do Refund com: objetivo do frontend, link
para `../Refund-api/docs/index.md`, stack atual, requisitos, comandos
`npm install`, `npm run dev`, `npm run build`, `npm run lint`, dependência da
API em `http://localhost:3333` e exigência de rodar o Vite em
`http://localhost:5173` por causa do CORS atual.

- [ ] **Step 4: Verificar referências do frontend**

Run:

```bash
cd Refund-FrontEnd
rg -n "../Refund-api/docs/index.md" README.md AGENTS.md CLAUDE.md
rg -n "Axios/TanStack Query/react-hook-form/zod entram só|React \+ TypeScript \+ Vite" README.md AGENTS.md CLAUDE.md
npx tsc -b --noEmit
git diff --check
```

Expected: os três arquivos apontam para a fonte canônica; as descrições
obsoletas de fase/template não aparecem; TypeScript termina com código 0; não
há erro de whitespace.

- [ ] **Step 5: Commit das entradas do frontend**

```bash
git add README.md AGENTS.md CLAUDE.md
git commit -m "docs: connect frontend to canonical Refund docs"
```

---

### Task 7: Auditoria documental final

**Files:**
- Modify only if verification finds an error: files created or modified in Tasks 1–6.

**Interfaces:**
- Consumes: toda a documentação e entradas dos dois repositórios.
- Produces: conjunto documental coerente, navegável e sem requisitos duplicados conhecidos.

- [ ] **Step 1: Conferir todos os links Markdown locais da API**

Run from `Refund-api`:

```bash
while IFS= read -r target; do test -e "docs/$target" || { echo "Missing: docs/$target"; exit 1; }; done < <(rg -o '\]\(([^)#]+)' docs/index.md | sed 's/^](//')
```

Expected: código 0, sem imprimir `Missing`.

- [ ] **Step 2: Conferir unicidade e cobertura dos identificadores**

Run from `Refund-api`:

```bash
test "$(rg -o '^## BR-[0-9]{3}' docs/business-rules.md | sort | uniq -d | wc -l | tr -d ' ')" = "0"
for id in $(seq -w 1 15); do rg -q "BR-0${id}" docs/use-cases || exit 1; done
for id in $(seq -w 1 6); do test "$(rg -l "UC-00${id}" docs/use-cases/*.md | wc -l | tr -d ' ')" = "1" || exit 1; done
```

Expected: todos os comandos terminam com código 0.

- [ ] **Step 3: Comparar documentos com a implementação**

Revisar lado a lado:

```text
docs/business-rules.md
docs/use-cases/*.md
src/main/routes/auth_routes.py
src/main/routes/refund_routes.py
src/validators/*.py
src/controllers/*.py
src/models/entities/*.py
src/main/middlewares/auth_jwt.py
../Refund-FrontEnd/src/context/AuthContext.tsx
../Refund-FrontEnd/src/hooks/use*.ts
../Refund-FrontEnd/src/pages/Page*.tsx
```

Confirmar que os documentos não afirmam existir edição, aprovação,
rejeição, pagamento ou alteração de papel pelo cadastro público.

- [ ] **Step 4: Inspecionar os diffs e estados dos dois repositórios**

Run:

```bash
git -C Refund-api diff --check
git -C Refund-api status --short
git -C Refund-FrontEnd diff --check
git -C Refund-FrontEnd status --short
```

Expected: nenhum erro de whitespace; apenas alterações documentais esperadas
aparecem caso ainda não tenham sido commitadas.

- [ ] **Step 5: Corrigir e commitar somente se a auditoria encontrar problemas**

Depois de corrigir os documentos afetados com `apply_patch`, repetir Steps 1–4.
Se houver correções na API:

```bash
git -C Refund-api add docs README.md AGENTS.md CLAUDE.md
git -C Refund-api commit -m "docs: fix Refund documentation consistency"
```

Se houver correções no frontend:

```bash
git -C Refund-FrontEnd add README.md AGENTS.md CLAUDE.md
git -C Refund-FrontEnd commit -m "docs: fix frontend documentation references"
```
