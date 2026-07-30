# Ciclo de feature — Pagamento, histórico e estatísticas (backend)

Data: 2026-07-30.
Repositório afetado: `Refund-api`.
Este ciclo precede o ciclo de frontend do workflow de aprovação e é
pré-requisito dele.

Este ciclo segue o
[fluxo permanente da trilha](../../plans/learning-path-workflow.md).

## Motivação

O backlog do frontend abre com "workflow de aprovação na UI". O brainstorming
desse item encontrou três lacunas na API que impediriam a tela de ser
construída de forma honesta, e o Gabriel decidiu fechá-las antes — o mesmo
padrão dos ciclos de consulta da listagem e de serving autenticado, ambos
feitos antes do frontend de propósito.

**1. O motivo da rejeição é write-only.** `reason` é validado
(`refund_reviewer_validator.py`), gravado em `refund_reviews`
(`refund_reviews_repository.py`) e **nunca sai**. Nenhum endpoint o devolve, e
não existe rota para `refund_reviews`. Quem tem uma solicitação rejeitada vê o
badge "Rejeitado" e mais nada — o loop do produto não fecha. Exigir uma
justificativa que ninguém pode ler transforma a BR-018 em formalidade.

**2. Não existe estado "pago".** O ciclo de vida termina em `approved`, então o
sistema não sabe distinguir o que a empresa **deve** do que ela **já pagou**.

**3. A soma da listagem ignora status.** `select_refunds` soma
`amount_in_cents` sobre os filtros recebidos, e a Home não envia `status`
(`PageHome.tsx:72` chama `useRefunds({ page, perPage, name })`). Uma
solicitação **rejeitada continua entrando no total**. Hoje passa despercebido
porque quase tudo está `pending`; no dia em que houver rejeições, aquele número
deixa de significar coisa alguma.

O item 3 não é corrigido diretamente aqui — o card é do frontend — mas a regra
que o impede de se repetir nasce neste ciclo.

## O princípio que organiza o ciclo

**Status não é um filtro opcional; é uma dimensão. Nenhum agregado monetário
sem status declarado.**

Os quatro status significam coisas de naturezas diferentes:

| Status | O que o dinheiro é |
|---|---|
| `pending` | previsão — em análise |
| `approved` | **passivo** — aprovado e ainda não pago |
| `paid` | despesa liquidada |
| `rejected` | nada; serve como diagnóstico |

Somar os quatro é somar previsão com passivo com despesa realizada com nada.
É exatamente o defeito do card Total. Toda superfície nova deste ciclo respeita
a regra.

## Decisões tomadas no brainstorming

| Decisão | Escolha | Consequência |
|---|---|---|
| Fechar o loop do motivo | Sim, neste ciclo | Backend deixa de ser só consumidor da UI |
| Como expor o histórico | Rota própria, histórico completo | UC-013; a tabela já guarda tudo |
| Modelagem de "pago" | Quarto valor de `status` | Sem migration para o valor; stats absorvem com uma chave |
| Verbo do pagamento | `POST /refunds/{id}/payment` | Separado do `PATCH /status`: pagar é fato, não decisão |
| Comprovante de pagamento | Obrigatório | Invariante `paid` ⟺ existe arquivo |
| Reversão de pagamento | `paid` é terminal | Regra em uma frase, sem exceção |
| Quem paga | `admin`, nunca a própria | BR-016 estendida |
| Métricas expostas | Só `by_status` (contagem + soma) | Nenhum agregado que misture status |
| Derivadas (taxa, ticket médio) | No cliente | Evita segunda fonte de verdade e arredondamento no contrato |
| Alcance das leituras novas | Dono + admin, com nome do revisor | Uma regra: quem vê o reembolso vê a decisão dele |
| `user_id` na listagem | Admin filtra; standard ignora | Sem caminho de erro novo |
| Pool de conexões | Reajustado neste ciclo | Pendência antiga, citada duas vezes como razão de decisões daqui |

## Ciclo de vida

```
                    ┌──────────────┐
                    │   pending    │  criada pelo solicitante
                    └──┬────────┬──┘
         PATCH /status │        │ PATCH /status
                       ▼        ▼
                ┌──────────┐  ┌──────────┐
                │ approved │◄─┤ rejected │  BR-017: reversível
                └────┬─────┘─►└──────────┘  entre as duas decisões
                     │
                     │ POST /refunds/{id}/payment
                     ▼
                ┌──────────┐
                │   paid   │ ■ terminal
                └──────────┘
```

## Por que pagar não entra no `PATCH /status`

Aprovação e pagamento parecem o mesmo tipo de operação, e não são:

| | Aprovar / rejeitar | Pagar |
|---|---|---|
| natureza | **decisão** de uma pessoa | **fato** — dinheiro se moveu |
| reversível? | sim (BR-017) | não; corrige-se com outro fato |
| exige justificativa? | sim, ao rejeitar | não; exige comprovante |
| carrega arquivo? | não | sim, obrigatório |

`PATCH /refunds/{id}/status` pede `reason` condicional, grava `reviewer_id` e
implementa regras de reversão. Acomodar `"paid"` ali obrigaria aquele endpoint
a aceitar `multipart/form-data` e a responder o que significa voltar de `paid`
para `rejected`. Verbo diferente, rota diferente.

## Mudanças no banco

| Mudança | Migration? |
|---|---|
| `status` aceita `paid` | **Não** — a coluna é `String` puro, sem `ENUM` nem `CHECK` |
| `refunds.payment_filename` (`String`, nullable) | **Sim** |

A ausência de constraint merece registro: **o banco nunca impediu um status
inválido.** A lista branca vive só no validator. Isso já vale para os três
status atuais; o quarto não piora, mas quem ler isto depois deve saber que a
garantia é inteiramente aplicacional.

A migration é escrita à mão e conferida com uma migration descartável que
precisa sair vazia, como o baseline do ciclo de aprovação.

## O log de transição

A transição `approved → paid` grava uma linha em `refund_reviews`, que já é um
log de transição (`from_status`, `to_status`, `reviewer_id`, `reason`,
`created_at`).

**O nome da tabela fica torto** — ela deixa de guardar só revisões. Renomear
custa migration e reescrita de camadas; manter custa um comentário. Decisão:
manter e documentar, tanto na entidade quanto no `domain-model.md`.

Isso também dispensa uma coluna `paid_at`: a data do pagamento é o `created_at`
daquela linha, e o UC-013 a expõe.

## Regras de negócio

Uma regra nova só; as outras três já existem e são **emendadas** em vez de
duplicadas.

- **BR-022 (nova) — comprovante de pagamento obrigatório.** Não há transição
  para `paid` sem arquivo. Daí a invariante `status == "paid"` ⟺ existe
  comprovante de pagamento.
- **BR-009 emendada** — "formato e tamanho do comprovante" passa a valer para
  os **dois** comprovantes: JPG, PNG ou PDF por extensão, no máximo 4MB. Mesma
  regra, mesmo limite, segundo validator.
- **BR-016 estendida** — a segregação de funções passa a valer para pagamento:
  um admin não paga a própria solicitação. Ele já não pode aprová-la; poder
  pagá-la seria uma brecha na mesma regra.
- **BR-017 emendada** — `paid` é terminal. `PATCH /refunds/{id}/status` sobre
  solicitação paga responde `422`. Aprovar e rejeitar seguem reversíveis entre
  si.
- **BR-020 emendada** — "acesso ao comprovante" (dono ou admin) passa a cobrir
  o comprovante de pagamento, com o mesmo `404` para os demais casos.
- **BR-015 intocada** — exclusão segue restrita a `pending`.

## Rotas

```
POST /refunds/{refund_id}/payment            admin, nunca a própria
GET  /refunds/{refund_id}/payment-receipt    dono ou admin
GET  /refunds/{refund_id}/reviews            dono ou admin
GET  /users/{user_id}/refund-stats           o próprio ou admin
GET  /refunds?user_id=                       admin filtra; standard ignora
```

As três rotas novas sob `/refunds/{refund_id}/…` são declaradas **antes** de
`GET /refunds/{refund_id}` em `refund_routes.py`, seguindo a ordenação que o
arquivo já usa para `/{refund_id}/receipt`.

### `POST /refunds/{refund_id}/payment` — UC-012

`multipart/form-data` com `file`. Extensão e tamanho validados como no
comprovante de despesa: **por extensão, não por `Content-Type`** — aquele
cabeçalho é definido pelo cliente e é inconfiável na prática.

Ordem das checagens, espelhando o UC-007:

1. **Arquivo (validator).** Ausente, extensão fora da lista ou acima de 4MB
   responde `422` sem o controller — e portanto o banco — ser tocado.
2. **Papel.** Primeira verificação do controller, antes de qualquer consulta.
   Um `standard` recebe `403` para qualquer id, exista ele ou não.
3. **Existência.** `404`.
4. **Autoria.** Admin pagando a própria recebe `403`.
5. **Status atual.** Diferente de `approved` responde `422`.

A propriedade de segurança preservada é a mesma do UC-007: **nenhum acesso ao
banco acontece antes da checagem de papel**, então a resposta a um `standard`
nunca revela se um id existe.

| Código | Cenário |
|---|---|
| `200` | Pago; corpo traz a solicitação com `status: "paid"` |
| `401` | JWT ausente, inválido ou expirado |
| `403` | Não é admin, ou é admin pagando a própria solicitação |
| `404` | Id inexistente |
| `422` | Arquivo ausente/inválido/grande, ou status atual ≠ `approved` |

**A resposta relê a linha gravada e usa `serialize_refund`.** Isso é
deliberado: o `PATCH /status` do ciclo de aprovação montou a resposta a partir
de `RefundStatusRepository.select_for_update` e criou a divergência de formato
que continua nas pendências. Não repetimos o erro — uma superfície nova nasce
com a forma compartilhada.

### `GET /refunds/{refund_id}/payment-receipt`

Dono ou admin, exatamente como `GET /refunds/{refund_id}/receipt`. Responde
`404` **idêntico**, inclusive na mensagem, para os quatro casos: id inexistente,
solicitação alheia, solicitação não paga e arquivo ausente do disco.

### `GET /refunds/{refund_id}/reviews` — UC-013

Dono ou admin (`404` caso contrário, BR-013). Solicitação nunca decidida
devolve `count: 0` e lista vazia — não é erro.

```json
{
  "type": "RefundReview",
  "count": 2,
  "attributes": [
    {
      "from_status": "pending",
      "to_status": "approved",
      "reason": null,
      "reviewer": { "id": 1, "name": "Gabriel" },
      "created_at": "2026-07-30T10:00:00"
    },
    {
      "from_status": "approved",
      "to_status": "paid",
      "reason": null,
      "reviewer": { "id": 1, "name": "Gabriel" },
      "created_at": "2026-07-30T14:20:00"
    }
  ]
}
```

Ordem cronológica crescente, com `id` como desempate — a mesma disciplina de
ordenação estável adotada na listagem.

O nome do revisor é visível para o dono. Foi decisão explícita: uma regra só,
"quem pode ver o reembolso pode ver a decisão dele", em vez de uma resposta que
muda de forma conforme quem pergunta.

### `GET /users/{user_id}/refund-stats` — UC-014

O próprio ou admin; `404` caso contrário, pelo mesmo raciocínio
anti-enumeração da BR-013.

```json
{
  "type": "RefundStats",
  "user_id": 3,
  "by_status": {
    "pending":  { "count": 2, "amount_in_cents":  30000 },
    "approved": { "count": 5, "amount_in_cents":  65000 },
    "paid":     { "count": 3, "amount_in_cents":  40000 },
    "rejected": { "count": 1, "amount_in_cents":  10000 }
  }
}
```

Uma consulta, `GROUP BY status`. **Status sem nenhuma solicitação vem com
zeros, não some da resposta** — senão todo cliente precisa tratar chave
ausente.

**Não há total geral, nem de contagem nem de soma.** A manchete "11
solicitações" é a soma das quatro contagens, feita no cliente. Taxa de
aprovação e ticket médio também ficam no cliente: são divisões dos números
acima, e publicá-las obrigaria o *contrato* a decidir arredondamento.

Por que a forma aninhada: um status novo é uma chave nova e nada mais se move.
A alternativa achatada (`pending_count`, `pending_amount_in_cents`, …) já
nasceria com oito chaves e não comportaria uma segunda dimensão.

### `GET /refunds?user_id=` — emenda ao UC-004

`Optional[int] = Query(None)`, validação nativa do FastAPI como `page` e
`per_page` já usam. Admin filtra por solicitante; para `standard` o parâmetro é
**ignorado**, porque `refund_lister_controller` já trava o filtro no próprio
usuário. Não há vazamento e não nasce caminho de erro novo.

`total` e `sum_amount_in_cents` continuam respeitando todos os filtros ativos.

## Concorrência: `UPDATE` condicional em vez de lock

O pagamento toca duas tabelas (`refunds` e `refund_reviews`), então usa o
`UnitOfWork`, como a revisão. Mas **não toma lock**:

```sql
UPDATE refunds SET status='paid', payment_filename=:f
WHERE id=:id AND status='approved'
```

Zero linhas afetadas significa que outro admin pagou antes; a resposta é `422`.

Isso é deliberado. Uma pendência registrada diz que `select_for_update` segura
uma conexão do pool enquanto espera, e que isso pode esgotar o pool. Criar um
segundo lugar com essa característica aumentaria a chance daquele cenário. O
`UPDATE` condicional fecha a corrida sem espera — mesmo padrão do `DELETE`
condicional que a BR-015 já usa.

### A ordem arquivo → banco

O `payment_filename` precisa existir antes do `UPDATE`, então o arquivo vai
para o disco primeiro. Se o `UPDATE` afetar zero linhas, o arquivo recém-salvo
é apagado como compensação.

Sendo explícito sobre o limite: **isso cobre o caso comum e não resolve o
Item 21.** Um crash entre o `save` e o `UPDATE` ainda deixa órfão. A criação de
reembolso tem a mesma fragilidade; depois deste ciclo serão dois lugares. E
vale antecipar um engano fácil: **o `UnitOfWork` não cobre isso** — ele
delimita a transação do banco, e o sistema de arquivos não participa dela.

## Camadas

Cinco fatias verticais no padrão
`rota → HttpRequest → composer → view → validator → controller → repository`,
com nomenclatura de agente (`creator`, `lister`, `finder`, `deleter`,
`reviewer`).

| Fatia | Arquivos novos | Reaproveita |
|---|---|---|
| Pagar | `refund_payer_{view,validator,controller,composer}` + interface | `FileStorage`, `UnitOfWork`, `serialize_refund` |
| Comprovante de pagamento | `payment_receipt_finder_{view,controller,composer}` + interface | padrão do `receipt_finder` |
| Histórico | `refund_review_lister_{view,controller,composer}` + interface | `RefundReviewsRepository` |
| Estatísticas | `refund_stats_finder_{view,controller,composer}` + interface | — |
| Filtro `user_id` | nenhum | emenda em `refund_routes` e `refund_lister_controller` |

**Métodos de repositório novos:**

- `RefundStatusRepository.mark_as_paid(refund_id, payment_filename)` — o
  `UPDATE` condicional acima; devolve o número de linhas afetadas. Vai **nesta**
  classe, não em `RefundsRepository`: só ela é injetada por sessão e
  commit-free, então só ela escreve dentro da transação do `UnitOfWork` e
  aterrissa junto com a linha do log.
- `RefundsRepository.count_by_status(user_id)` — o `GROUP BY`. Leitura
  independente, sem transação a coordenar, então fica na classe que abre a
  própria sessão.
- `RefundReviewsRepository.select_by_refund_id(refund_id)` — join com `Users`
  para o nome do revisor.

**As guardas leem sem lock.** O controller de pagamento não usa
`select_for_update`: ele lê o reembolso por `RefundsRepository.select_refund_by_id`
(fora da transação) para decidir 404/403/422, e deixa a corrida para o `UPDATE`
condicional. Ler com lock aqui reintroduziria exatamente o que esta spec decidiu
evitar.

**Armadilha do `payment_filename`:** o repositório continua devolvendo o nome
do arquivo (o `payment_receipt_finder` precisa dele para ler o disco), mas
`serialize_refund` **não** o expõe — a mesma disciplina que o ciclo de serving
autenticado aplicou ao `filename` do comprovante de despesa. Nenhuma resposta
ganha `has_payment_receipt`: sendo o arquivo obrigatório, `status == "paid"` já
carrega a informação. É o oposto do `has_avatar`, que existe justamente porque
avatar é opcional.

**Storage e disco:**

- `PAYMENT_DIR` em `upload_info` (`src/configs/global_config.py`).
- `FileStorage(upload_info["PAYMENT_DIR"])` nos dois composers que precisam.
- `uploads/payment_receipts/.gitkeep` versionado **e** as duas negações
  correspondentes no `.gitignore`.

Este último item falha silenciosamente na máquina de quem desenvolveu e
explode num clone limpo: **nenhum código da aplicação cria diretório de
upload.** Não há `makedirs` em lugar nenhum — `uploads/receipts` e
`uploads/avatars` existem porque têm `.gitkeep` versionado, com negações
explícitas nas linhas 15-18 do `.gitignore`.

## Pool de conexões

Pendência antiga, resolvida aqui porque este ciclo a citou duas vezes como
razão de decisões de design.

**Estado atual:** `pool_size=2, max_overflow=0, pool_timeout=30`. Teto de duas
operações simultâneas no processo inteiro; a terceira espera 30s e recebe 500 —
exatamente o cenário da pendência do `select_for_update`.

Duas ausências que não estavam registradas em lugar nenhum e importam mais que
o número: **`pool_pre_ping` desligado** e **`pool_recycle` indefinido**. O
`DATABASE_URL` aponta para um endpoint **direto** do Neon (sem `-pooler`), que
suspende a computação quando ocioso e derruba conexões. Sem pre-ping o pool
entrega uma conexão já fechada pelo servidor, e o sintoma é característico: o
primeiro acesso depois de um tempo parado falha, o seguinte funciona.

```python
engine = create_async_engine(
    CONNECTION_STRING,
    echo=False,
    pool_size=5,           # 2 -> 5
    max_overflow=10,       # 0 -> 10; teto vira 15
    pool_timeout=10,       # 30 -> 10; falhar rápido em vez de pendurar
    pool_pre_ping=True,    # novo
    pool_recycle=300,      # novo
    connect_args={"server_settings": {"lock_timeout": "3000"}},  # novo
)
```

`lock_timeout` fecha a outra metade da pendência: a espera indefinida do
`select_for_update` vira erro em 3 segundos. É **global** — vale para qualquer
statement, não só para o fluxo de revisão. Aceito porque aquele é o único lugar
do sistema que toma lock; a alternativa cirúrgica seria `SET LOCAL lock_timeout`
dentro do `UnitOfWork`, ao custo de mais código.

Quinze conexões por processo é seguro para o limite do Neon. **Rodar com
múltiplos workers do uvicorn multiplica esse número** — registrar no fechamento.

## Testes

`_test.py` ao lado de cada camada, comentários em inglês, conforme o
`AGENTS.md`.

- **Validator de pagamento** — arquivo ausente, extensão fora da lista, acima
  de 4MB.
- **Controller de pagamento** — papel checado **antes de qualquer consulta ao
  banco** (espelhando
  `test_invalid_status_short_circuits_before_the_controller`); admin pagando a
  própria → `403`; status ≠ `approved` → `422`; caminho feliz grava arquivo,
  status e linha de log.
- **`mark_as_paid`** — retorna zero linhas afetadas quando o status já mudou.
  É a prova de que a corrida está fechada.
- **Compensação** — `UPDATE` de zero linhas apaga o arquivo recém-salvo.
- **`count_by_status`** — devolve **zeros** para status sem solicitação, não
  chaves ausentes.
- **Histórico** — solicitação nunca decidida → `count: 0`, não erro; ordem
  cronológica com desempate estável.
- **Comprovante de pagamento** — os quatro caminhos de `404` respondem
  idênticos, inclusive na mensagem.
- **Listagem** — `user_id` filtra para admin e é ignorado para `standard`.

## Verificação

- `pytest` — parte de 178 verdes.
- `pylint src` — manter 10.00/10.
- Ciclo `upgrade`/`downgrade` contra o banco real, **à mão**: automatizá-lo
  exige um PostgreSQL descartável, que é o Item 19. Limitação aceita e
  registrada, como no ciclo de aprovação.
- Cenários ponta a ponta contra a API real, com os códigos HTTP conferidos um a
  um, como nos ciclos de aprovação (10/10), consulta (19/19) e serving (14/14).

### O que não é verificável por teste

O ajuste de pool é a mudança de **maior alcance e menor verificabilidade** do
ciclo: cinco linhas que afetam todo request que toca o banco, sem teste que
prove "o pool está melhor". A evidência possível:

1. Um teste que afirma os valores configurados — fraco, mas pega regressão
   acidental.
2. O cenário da pendência reproduzido à mão: três revisões concorrentes da
   mesma solicitação. Antes, a terceira toma 500 depois de 30s; depois, falha
   rápido ou passa.
3. `pool_pre_ping`: deixar a aplicação parada além do tempo de suspensão do
   Neon e fazer um request.

Nenhum dos três roda no `pytest`. Isso vai marcado como limitação no
fechamento, do mesmo jeito que o ciclo de migrations fica marcado como manual.

## Consequências para o ciclo de frontend

O ciclo seguinte (`Refund-FrontEnd`) já tem estas decisões tomadas no
brainstorming e **não deve recomeçar do zero**:

- Rota dedicada `/refunds/:id/review`, em vez de ações na página de detalhe.
- Destino do clique na Home decidido por dono: solicitação alheia →
  `/refunds/:id/review`; a própria → `/refunds/:id` normal, com Excluir. A
  regra é `role === "admin" && refund.user.id !== me`, e espelha a BR-016 na
  navegação.
- Guarda no loader: quem não pode revisar é redirecionado para `/refunds/:id`,
  sem tela de erro. O loader já busca o reembolso, então decide papel **e**
  propriedade antes de renderizar.
- Dois botões, com o botão do status atual ausente — o `422` de "já está nesse
  status" fica impossível de disparar pela UI. Rejeitar abre `Dialog` com
  textarea obrigatória, no padrão do diálogo de exclusão que já existe.
- Painel do solicitante na tela de revisão: perfil, contadores por status e a
  lista clicável das solicitações dele.
- Terceiro card na faixa de resumo, adiado desde o restyle.

E ganha duas obrigações novas vindas daqui:

- **Quarta variante de badge.** `src/components/ui/badge.tsx` tem três
  (`default`, `secondary`, `destructive`); `paid` precisa da quarta.
- **Corrigir o card Total**, que hoje soma os quatro status. Com `paid`
  existindo, a correção deixa de ser cosmética.

## Documentação a atualizar no fechamento

- **Casos de uso novos:** UC-012 (pagar), UC-013 (histórico de revisões),
  UC-014 (estatísticas por usuário).
- **Emendas:** UC-004 (`user_id`), UC-007 (`paid` terminal).
- **Regras:** BR-022 nova; BR-009, BR-016, BR-017 e BR-020 emendadas. A
  numeração foi conferida contra o arquivo: `business-rules.md` já vai até
  BR-021, e BR-019/BR-020/BR-021 tratam de avatar e de acesso a arquivo.
- `domain-model.md` — quarto status, `payment_filename`, e a nota de que
  `refund_reviews` passou a ser um log de transição, não só de revisões.
- `business-rules.md`, `index.md`.
- **ADR-003** — decide "armazenar comprovantes no disco local" falando de um
  tipo de arquivo; agora são três diretórios. Emenda, não ADR nova.
- `current-state.md` e `learning-path-progress.md`, conforme o fluxo da trilha.

## Fora de escopo

- **Recorte por período nas estatísticas** (`from`/`to`). Cabe como query
  params aditivos quando existir tela que use, sem quebrar o contrato.
- **Recorte por categoria.** Entraria como bloco `by_category`, irmão de
  `by_status`.
- **Tempo médio até decisão.** Cruzaria `refunds.created_at` com
  `refund_reviews.created_at`; mede a fila de aprovação, não diz nada sobre um
  solicitante.
- **Série temporal para gráfico.** Volume de dados diferente, endpoint
  diferente.
- **Pagamento parcial e estorno.** O pagamento é integral e único por decisão;
  se um dia deixar de ser, a resposta é uma tabela `refund_payments`, não mais
  valores de status.
- **Renomear `refund_reviews`.** Custa migration e reescrita de camadas.
- **Item 21 (consistência banco+arquivo).** Este ciclo o agrava e o documenta;
  resolvê-lo é item próprio.
- **Item 19 (PostgreSQL descartável).** É o que permitiria automatizar o teste
  de migrations.
- **Divergência de formato do `PATCH /status`.** Continua; o frontend decidiu
  não consumir aquele corpo, e mexer em `select_for_update` ripplaria no fluxo
  de aprovação.
