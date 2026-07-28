# Ciclo de feature — Workflow de aprovação (backend)

Data: 2026-07-28.
Repositórios afetados: `Refund-api` (implementação e documentação canônica).
O frontend ganha spec própria depois que esta API existir.

Este ciclo segue o
[fluxo permanente da trilha](../../plans/learning-path-workflow.md).

## Motivação

É o passo 3 do roadmap de ciclos. Hoje uma solicitação de reembolso é só o
registro da despesa e do comprovante: não há análise, decisão nem histórico —
como o próprio [`domain-model.md`](../../domain-model.md) registra em "Limites do
modelo atual". Este ciclo introduz o fluxo de decisão que falta.

Ele também é o **veículo de dois itens da trilha**, e essa é a razão de ser o
próximo:

- **Item 18 — Alembic e migrações.** A tabela `refunds` tem dados. Adicionar uma
  coluna a uma tabela existente é exatamente a operação que `metadata.create_all`
  não faz.
- **Item 20 — Unit of Work.** Aprovar passa a ser duas escritas que precisam
  valer juntas.

Nenhum dos dois entra por completude arquitetural: entram porque a feature cria
o problema que cada um resolve.

## Decisões tomadas no brainstorming

| Decisão | Escolha | Consequência |
|---|---|---|
| O que a aprovação registra | `status` + tabela de histórico | Duas escritas → o Item 20 se justifica |
| Transições | Reversível entre decisões, nunca volta a `pending` | Histórico com N linhas; `from_status` tem significado |
| Autorização | Só admin, e nunca a solicitação própria | Segregação de funções (BR-016) |
| Exclusão de decidida | Proibida | BR-015 ganha condição de estado |
| Forma do Unit of Work | Objeto explícito que expõe os repositories | Fronteira com nome; commit fora do repository |
| Escopo | Só backend | Frontend em spec própria |

## Item 20 — por que o Unit of Work é honesto aqui

O `learning_path.md` avisa: *"estudar com um caso de uso realmente
multioperação. Não refatorar os CRUDs atuais antes disso."*

Hoje cada repository é dono da própria transação:

```python
# src/models/repositories/refunds_repository.py
async def insert_refund(self, refund_info: dict) -> int:
    async with self.__db_connection.connect() as session:
        result = await session.execute(insert(Refunds).values(**refund_info))
        await session.commit()          # o repository decide quando confirmar
        return result.inserted_primary_key[0]
```

Perfeito para uma escrita. Mas aprovar são duas — `UPDATE refunds` e
`INSERT refund_reviews` — e com esse padrão cada uma commita sozinha:

```python
await refunds_repository.update_status(refund_id, "approved")   # commitou
await reviews_repository.insert_review(...)                     # falhou
```

Resultado: **reembolso aprovado sem registro de quem aprovou** — o estado que a
auditoria existe para impedir, e agora irreversível, porque a primeira sessão já
fechou.

Compensar na mão (`try/except` que reverte o status) não resolve: se o processo
morrer entre as duas linhas ninguém compensa, e é reimplementar em Python, pior,
o rollback que o banco já dá de graça.

O Unit of Work move a decisão de commit do repository para o caso de uso: uma
sessão, duas escritas, um commit no fim ou rollback inteiro.

### Escopo do padrão

O UoW entra **somente no caso de uso novo**. `insert_refund`, `select_refunds`,
`select_refund_by_id` e `delete_refund` ficam exatamente como estão — um write
simples não precisa de UoW, e envolvê-los seria a abstração prematura que o
Item 20 manda evitar. Os dois padrões convivem, e a diferença entre eles é a
lição.

## Item 18 — por que Alembic agora

`metadata.create_all` opera na granularidade de **tabela**: cria se não existir,
e nunca altera uma que existe. Adicionar `status` à entidade e reiniciar o
servidor não cria coluna nenhuma — a tabela `refunds` já existe, então
`create_all` a pula inteira, e a primeira query estoura com
`UndefinedColumnError`.

O Alembic dá ao schema um histórico versionado, com a revisão atual gravada na
tabela `alembic_version` do próprio banco. `alembic upgrade head` aplica só o que
falta e é seguro rodar sempre.

Até este ciclo nenhuma mudança de schema aconteceu com dados no banco, e
`create_all` bastou. O Alembic entra agora porque agora existe a operação que ele
resolve.

## Modelo de dados

```
refunds
  + status   String  NOT NULL  DEFAULT 'pending'

refund_reviews                              (nova)
  id           Integer  PK
  refund_id    Integer  FK refunds.id   NOT NULL
  reviewer_id  Integer  FK users.id     NOT NULL
  from_status  String                   NOT NULL
  to_status    String                   NOT NULL
  reason       String                   NULL
  created_at   DateTime DEFAULT now()
```

**`status` como `String` com conjunto permitido no validator, não `Enum` do
banco.** É o padrão que `category` já usa (`ALLOWED_CATEGORIES` em
`src/validators/refund_creator_validator.py`). Enum no PostgreSQL exige migration
para cada valor novo; string validada na borda dá a mesma proteção prática e
mantém a consistência interna.

**`reason` obrigatório na rejeição, opcional na aprovação.** A coluna é `NULL` no
banco e a obrigatoriedade condicional vive no validator: o banco não expressa
"obrigatório só quando `to_status = 'rejected'`" sem um CHECK constraint, e a
regra é de aplicação.

**Sem `ON DELETE CASCADE`.** Um refund só ganha review ao ser decidido, e
decidido não pode ser excluído (BR-015 alterada) — logo um refund com histórico é
sempre indeletável e review órfã é impossível por construção. Cascade protegeria
contra um caso que as regras já impedem.

## Migrations

1. Instalar e configurar o Alembic apontando para a `metadata` de
   `src/models/settings/metadata.py`.
2. **Migration de baseline** — autogerada do schema atual (`users`, `refunds`).
3. **`alembic stamp <baseline>`** no banco existente: grava a revisão sem
   executá-la, porque as tabelas já estão lá. É o passo que reconcilia um banco
   criado por `create_all` com um histórico de migrations.
4. **Migration do ciclo** — `status` (com `server_default='pending'`, que
   preenche as linhas existentes no mesmo `ALTER TABLE` e evita o erro de
   `NOT NULL` sobre dados já gravados) e a tabela `refund_reviews`. Com
   `downgrade` funcionando.
5. **Remover `metadata.create_all` do lifespan** (`src/main/server/server.py`).
   Manter os dois convida à divergência: `create_all` mascararia silenciosamente
   uma migration não aplicada. A partir daqui o schema é responsabilidade da
   migration, e o `README.md` passa a instruir `alembic upgrade head`.

O passo 5 muda como o projeto inteiro nasce. É a mudança de maior alcance do
ciclo.

`autogenerate` é rascunho, não resposta: não detecta renomeações (vê `DROP` +
`ADD`, que apagaria dados), costuma ignorar mudanças de `server_default` e falha
em algumas mudanças de tipo. Todo arquivo gerado é lido e ajustado antes de
aplicar.

## Endpoint

```
PATCH /refunds/{refund_id}/status
body: { "status": "approved" | "rejected", "reason": "texto" }
```

Uma rota só, em vez de `/approve` e `/reject` separadas: as duas ações
compartilham autorização, validação de transição e transação, e separá-las
duplicaria composer, view e controller para trocar uma string.

**Resposta de sucesso:** a solicitação atualizada, na mesma forma que
`GET /refunds/{id}` já devolve, agora incluindo `status`. A linha de histórico
recém-criada **não** volta no corpo — nenhuma tela deste ciclo a consome, e
expor o histórico é decisão de um caso de uso de leitura que ainda não existe.

## Mudanças nos casos de uso existentes

**`GET /refunds` e `GET /refunds/{id}` passam a incluir `status`.** É o que
permite ao frontend, no ciclo seguinte, distinguir pendente de decidida.

Vale registrar que **esta mudança de contrato é segura na direção oposta à do
ciclo anterior**: o Zod do frontend descarta chaves desconhecidas por padrão, e
`status` é um campo *adicionado*, não exigido. Um frontend antigo simplesmente o
ignora. Não há, aqui, a restrição de ordem de deploy que o
`sum_amount_in_cents` impôs — aquela existia porque o frontend declarava o campo
novo como **obrigatório**.

**`DELETE /refunds/{id}` passa a exigir `status = 'pending'`** (BR-015 alterada),
respondendo 422 para solicitação já decidida.

## Fluxo

```
PATCH /refunds/{id}/status
  -> refund_reviewer_composer          injeta UoW + repositories
  -> refund_reviewer_view              try/except + error_handler
  -> refund_reviewer_validator         status ∈ {approved, rejected}
                                       reason obrigatório se rejected
  -> refund_reviewer_controller        autorização + máquina de estados
       async with uow:
          refund = uow.refunds.select_for_update(id)
          [regras]
          uow.refunds.update_status(...)
          uow.reviews.insert_review(...)
          uow.commit()
  -> HttpResponse
```

É o mesmo pipeline dos outros quatro casos de uso. O único elemento inédito é o
`async with uow`.

### O Unit of Work

```python
# src/models/settings/unit_of_work.py
class UnitOfWork:
    def __init__(self, database_connection):
        self.__db_connection = database_connection

    async def __aenter__(self):
        self.__session_ctx = self.__db_connection.connect()
        self.__session = await self.__session_ctx.__aenter__()
        self.refunds = RefundStatusRepository(session=self.__session)
        self.reviews = RefundReviewsRepository(session=self.__session)
        return self

    async def __aexit__(self, exc_type, exc, tb):
        if exc_type:
            await self.__session.rollback()
        await self.__session_ctx.__aexit__(exc_type, exc, tb)

    async def commit(self):
        await self.__session.commit()
```

Três propriedades: a fronteira da transação é visível no `async with`; esquecer
o `commit()` falha para o lado seguro (não gravou, nunca gravou pela metade); e
um `raise` no meio do bloco reverte sozinho, sem `try/except` no controller.

### Os repositories participantes

O UoW precisa de repositories ligados à sessão dele, e o `RefundsRepository`
atual abre a própria. Em vez de torná-lo "dual-mode" — commitando ou não
conforme tenha recebido sessão, o que dá ao mesmo método duas semânticas de
durabilidade — nascem dois repositories novos, sessão-injetada, usados só dentro
do UoW:

```python
class RefundStatusRepository:      # src/models/repositories/refund_status_repository.py
    def __init__(self, session):   # recebe a sessão; não abre nem commita
        self.__session = session

    async def select_for_update(self, refund_id: int) -> Optional[dict]: ...
    async def update_status(self, refund_id: int, status: str) -> None: ...


class RefundReviewsRepository:     # src/models/repositories/refund_reviews_repository.py
    def __init__(self, session): ...
    async def insert_review(self, ...) -> None: ...
```

Trade-off registrado: passam a existir duas classes tocando a tabela `refunds`.
É duplicação conceitual aceita conscientemente; convergir os estilos espera um
segundo caso de uso multi-escrita, para ser refatoração por necessidade e não
por simetria.

### `select_for_update`

Sem trava, dois admins decidindo ao mesmo tempo produzem histórico mentiroso:

```
admin A: lê status = 'pending'
admin B: lê status = 'pending'      (nada commitado ainda)
admin A: UPDATE -> 'approved',  INSERT review (pending -> approved)
admin B: UPDATE -> 'rejected',  INSERT review (pending -> rejected)
```

Dois reviews afirmam ter saído de `pending`, e ambos passaram na validação porque
leram antes de qualquer commit. `.with_for_update()` trava a linha até o fim da
transação: B espera A, relê `approved`, e valida contra o estado real.

Só é possível porque agora existe uma transação em volta da leitura — com o
padrão antigo, a leitura já teria encerrado a própria sessão.

## Regras de negócio

**BR-016 — Segregação de funções na revisão** (nova). Só `admin` aprova ou
rejeita, e nenhum admin decide sobre solicitação própria.

**BR-017 — Transições permitidas** (nova). `pending → approved`,
`pending → rejected`, `approved → rejected`, `rejected → approved`. Nada volta
para `pending`. Repetir a decisão vigente (`approved → approved`) é **422**, não
no-op: não houve mudança de estado, e gravar `approved → approved` poluiria a
auditoria com um evento que não aconteceu.

**BR-015 — alterada.** A exclusão passa a exigir `status = 'pending'`.

**BR-012 — intocada.** O escopo de leitura por papel continua como está.

## Ordem das checagens

A ordem é uma decisão de segurança, não detalhe de implementação:

```
1. papel != admin            -> 403   (ANTES de qualquer consulta ao banco)
2. refund não existe         -> 404
3. refund.user_id == admin   -> 403
4. transição inválida        -> 422
5. sucesso                   -> 200
```

O passo 1 vem primeiro de propósito. Se a consulta viesse antes, um usuário
`standard` distinguiria "404 = não existe" de "403 = existe mas não posso",
ganhando um oráculo para enumerar IDs — exatamente o que a BR-013 evita hoje
respondendo 404 para "não é seu". Como a checagem de papel não consulta nada, ela
responde 403 idêntico para ID existente ou inexistente.

O passo 3 pode ser 403 sem risco: quem chega ali já é admin e, pela BR-012, já
enxerga todas as solicitações.

| Situação | Código |
|---|---|
| Sem token / token inválido | 401 |
| `standard` tentando revisar | 403 |
| Admin revisando a própria | 403 |
| Refund inexistente (admin) | 404 |
| `status` fora de `{approved, rejected}` | 422 |
| `reason` ausente numa rejeição | 422 |
| Transição não permitida | 422 |
| Sucesso | 200 + refund atualizado |

## Testes

Cada camada com seu `_test.py` ao lado, conforme o
[`AGENTS.md`](../../../AGENTS.md).

- **Validator** — status inválido; `reason` ausente na rejeição; `reason`
  opcional na aprovação.
- **Controller** — os cinco caminhos da tabela de códigos, um teste cada.
- **Repositories** — `select_for_update`, `update_status`, `insert_review`.
- **Deleter** — decidida → 422; pendente → segue funcionando.
- **Migration** — `upgrade` e `downgrade` em banco vazio, verificando que a
  coluna e a tabela aparecem e somem. É o que o Item 18 pede explicitamente.

### O teste central do ciclo

```python
async def test_status_nao_muda_quando_o_insert_do_review_falha():
    # o insert do histórico quebra de propósito
    with pytest.raises(...):
        await controller.review(refund_id=42, ...)

    refund = await refunds_repository.select_refund_by_id(42)
    assert refund["status"] == "pending"     # o UPDATE foi revertido
```

Sem o Unit of Work este teste **falha**, porque o `UPDATE` teria commitado
sozinho. Ele não testa código: testa a garantia que o padrão comprou.

## Verificação

```bash
pytest
pylint src
```

## Documentação a atualizar no fechamento

- `docs/domain-model.md` — `status`, a entidade `RefundReview` e a remoção do
  parágrafo "Limites do modelo atual".
- `docs/business-rules.md` — BR-016 e BR-017 novas; BR-015 alterada.
- `docs/use-cases/` — **UC-007 — Revisar solicitação** (novo); UC-004 e UC-005
  passam a expor `status`; UC-006 ganha a condição de estado.
- `docs/index.md` — entrada do UC-007.
- `README.md` — `alembic upgrade head` no lugar do `create_all`.
- `docs/learning-path-progress.md` e `docs/plans/current-state.md` — fechamento
  dos Itens 18 e 20.

## Fora de escopo

- **Frontend inteiro** — spec própria depois desta API existir.
- **Filtro por status na listagem** — vem com a tela.
- **Notificação ao solicitante** — nenhum canal de notificação existe no projeto.
- **Convergência dos dois estilos de repository** — espera um segundo caso de uso
  multi-escrita.
- **Item 21 (consistência banco+arquivo)** — pendência conhecida e independente
  deste ciclo.
