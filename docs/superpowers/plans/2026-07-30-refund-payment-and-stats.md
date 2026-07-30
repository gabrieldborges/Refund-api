# Pagamento, histórico e estatísticas — Plano de implementação

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Dar à API o estado `paid` com comprovante obrigatório, expor o histórico de revisões e as estatísticas por usuário, para que o ciclo seguinte construa a tela de revisão contra uma API completa.

**Architecture:** Cinco fatias verticais no padrão existente (`rota → HttpRequest → composer → view → validator → controller → repository`). O pagamento escreve em duas tabelas dentro de um `UnitOfWork`, mas resolve concorrência com `UPDATE` condicional em vez de lock. As leituras novas seguem a autorização já estabelecida: dono ou admin, com `404` anti-enumeração.

**Tech Stack:** Python 3, FastAPI, SQLAlchemy 2.0 (async, driver asyncpg), Alembic, PostgreSQL no Neon, pytest, pylint.

## Global Constraints

- Spec deste ciclo: [`2026-07-30-refund-payment-and-stats-design.md`](../specs/2026-07-30-refund-payment-and-stats-design.md). Em caso de divergência, a spec vence.
- Fluxo obrigatório: [`learning-path-workflow.md`](../../plans/learning-path-workflow.md).
- **Verificação após qualquer mudança** (`AGENTS.md`): `.venv/bin/python3 -m pytest` e `.venv/bin/python3 -m pylint src`.
- **Os executáveis diretos do venv não funcionam** — os shebangs apontam para um caminho antigo. Use sempre `.venv/bin/python3 -m <ferramenta>`.
- Ponto de partida a preservar: **178 testes verdes** e **pylint 10.00/10**.
- Cada camada tem seu `_test.py` **ao lado** do código testado. Comentários de teste e fixture em **inglês**, explicando o cenário ou a razão.
- Nomenclatura de agente: `creator`, `lister`, `finder`, `deleter`, `reviewer`, `payer`.
- Textos de erro em inglês, no padrão dos existentes (`"Refund not found"`).
- Não alterar a Clean Architecture existente; não introduzir biblioteca nova.
- Branch: `feat/refund-payment-and-stats` (já criada, spec já commitada).
- Revisão do Alembic no head hoje: **`bc9699597a1c`**.

## Estrutura de arquivos

**Criar:**

| Arquivo | Responsabilidade |
|---|---|
| `alembic/versions/<hash>_add_refund_payment_filename.py` | Coluna `payment_filename` |
| `src/validators/refund_payer_validator.py` (+`_test`) | Extensão e tamanho do comprovante de pagamento |
| `src/controllers/refund_payer_controller.py` (+`_test`) | Guardas, gravação e compensação do pagamento |
| `src/controllers/interfaces/refund_payer_controller_interface.py` | Contrato do controller |
| `src/views/refund_payer_view.py` (+`_test`) | Validator antes do controller |
| `src/main/composer/refund_payer_composer.py` | Injeção do pagamento |
| `src/controllers/payment_receipt_finder_controller.py` (+`_test`) | Ler o comprovante de pagamento |
| `src/controllers/interfaces/payment_receipt_finder_controller_interface.py` | Contrato |
| `src/views/payment_receipt_finder_view.py` | Resposta binária |
| `src/main/composer/payment_receipt_finder_composer.py` | Injeção |
| `src/controllers/refund_review_lister_controller.py` (+`_test`) | Histórico de um reembolso |
| `src/controllers/interfaces/refund_review_lister_controller_interface.py` | Contrato |
| `src/models/repositories/interfaces/refund_reviews_reader_repository_interface.py` | Contrato da leitura do histórico |
| `src/views/refund_review_lister_view.py` | Envelope JSON |
| `src/main/composer/refund_review_lister_composer.py` | Injeção |
| `src/controllers/refund_stats_finder_controller.py` (+`_test`) | Estatísticas por usuário |
| `src/controllers/interfaces/refund_stats_finder_controller_interface.py` | Contrato |
| `src/views/refund_stats_finder_view.py` | Envelope JSON |
| `src/main/composer/refund_stats_finder_composer.py` | Injeção |
| `uploads/payment_receipts/.gitkeep` | Diretório versionado |

**Modificar:**

| Arquivo | Mudança |
|---|---|
| `src/models/entities/refunds.py` | Coluna `payment_filename` |
| `src/models/settings/database_connection_handler.py` | Configuração do pool |
| `src/models/repositories/refund_status_repository.py` (+`_test`) | `mark_as_paid` |
| `src/models/repositories/interfaces/refund_status_repository_interface.py` | Assinatura |
| `src/models/repositories/refunds_repository.py` (+`_test`) | `count_by_status` |
| `src/models/repositories/interfaces/refunds_repository_interface.py` | Assinatura |
| `src/models/repositories/refund_reviews_repository.py` (+`_test`) | Classe irmã `RefundReviewsReaderRepository` (a existente fica intocada) |
| `src/models/entities/refund_reviews.py` | Comentário: virou log de transição |
| `src/configs/global_config.py` | `PAYMENT_DIR` |
| `src/main/routes/refund_routes.py` | Quatro rotas + `user_id` |
| `src/main/routes/user_routes.py` | Rota de estatísticas |
| `src/controllers/refund_lister_controller.py` (+`_test`) | Filtro `user_id` para admin |
| `.gitignore` | Negações do diretório novo |
| `docs/**` | Casos de uso, regras, modelo, ADR, índice |

---

### Task 1: Coluna `payment_filename` e migration

**Files:**
- Modify: `src/models/entities/refunds.py`
- Create: `alembic/versions/<hash>_add_refund_payment_filename.py`

**Interfaces:**
- Consumes: nada.
- Produces: coluna `refunds.payment_filename` (`String`, nullable) disponível para todas as tasks seguintes.

- [ ] **Step 1: Adicionar a coluna na entidade**

Em `src/models/entities/refunds.py`, depois de `Column("status", ...)`:

```python
    # Nullable on purpose: only a paid refund has one. BR-022 makes the file
    # mandatory to REACH "paid", which is what gives the invariant
    # status == "paid" <=> this column is filled. Nothing in the database
    # enforces that pairing — it lives in RefundPayerController.
    Column("payment_filename", String, nullable=True),
```

- [ ] **Step 2: Gerar a migration**

```bash
.venv/bin/python3 -m alembic revision -m "add refund payment filename"
```

- [ ] **Step 3: Escrever `upgrade` e `downgrade` à mão**

No arquivo gerado, confirme que `down_revision` é `'bc9699597a1c'` e escreva:

```python
def upgrade() -> None:
    op.add_column('refunds', sa.Column('payment_filename', sa.String(), nullable=True))


def downgrade() -> None:
    op.drop_column('refunds', 'payment_filename')
```

- [ ] **Step 4: Aplicar e conferir o ciclo completo contra o banco real**

```bash
.venv/bin/python3 -m alembic upgrade head
.venv/bin/python3 -m alembic downgrade -1
.venv/bin/python3 -m alembic upgrade head
```

Esperado: os três comandos terminam sem erro. Este ciclo é **manual** — automatizá-lo exige o Item 19 (PostgreSQL descartável).

- [ ] **Step 5: Provar que a entidade e o banco batem**

```bash
.venv/bin/python3 -m alembic revision --autogenerate -m "throwaway check"
```

Esperado: o arquivo gerado tem `upgrade`/`downgrade` **vazios** (só `pass`). Se tiver conteúdo, entidade e banco divergem — corrija antes de continuar.

```bash
rm alembic/versions/*throwaway_check.py
```

- [ ] **Step 6: Rodar a suíte**

Run: `.venv/bin/python3 -m pytest`
Expected: 178 passed.

- [ ] **Step 7: Commit**

```bash
git add src/models/entities/refunds.py alembic/versions/
git commit -m "feat: add payment_filename column to refunds"
```

---

### Task 2: Ajuste do pool de conexões

**Files:**
- Modify: `src/models/settings/database_connection_handler.py`
- Create: `src/models/settings/database_connection_handler_pool_test.py`

**Interfaces:**
- Consumes: nada.
- Produces: `engine` com pool maior, pre-ping, recycle e `lock_timeout`. Nenhuma API nova.

- [ ] **Step 1: Escrever o teste que falha**

Crie `src/models/settings/database_connection_handler_pool_test.py`:

```python
# These are revert-nets, not behaviour tests: they read back what we
# configured, so an accidental revert shows up red instead of as a 500 under
# concurrency months later. They CANNOT catch a connect_args shape the driver
# rejects — Step 5 asks PostgreSQL itself, which is the behavioural half.
#
# The private attributes are unavoidable: SQLAlchemy's pool exposes size()
# publicly but has no public accessor for max_overflow, pre_ping or recycle.
from src.models.settings.database_connection_handler import engine


def test_pool_is_sized_for_more_than_two_concurrent_operations():
    assert engine.pool.size() == 5
    # SQLAlchemy exposes the overflow ceiling as a private attribute; there is
    # no public accessor for it.
    assert engine.pool._max_overflow == 10  # pylint: disable=protected-access


def test_dead_connections_are_discarded_before_use():
    # Neon suspends idle compute and drops connections. Without pre-ping the
    # pool hands out a socket the server already closed, and the symptom is
    # characteristic: the first request after an idle period fails, the next
    # one works.
    assert engine.pool._pre_ping is True  # pylint: disable=protected-access
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `.venv/bin/python3 -m pytest src/models/settings/database_connection_handler_pool_test.py -v`
Expected: FAIL — `assert 2 == 5`.

- [ ] **Step 3: Aplicar a configuração**

Em `src/models/settings/database_connection_handler.py`, substitua o bloco `create_async_engine`:

```python
engine = create_async_engine(
    CONNECTION_STRING,
    echo=False,
    # Was pool_size=2, max_overflow=0: a ceiling of TWO concurrent operations
    # for the whole process. The review flow takes a row lock inside a
    # transaction, so two blocked reviewers used to exhaust the pool and a
    # third request — even a login — waited pool_timeout and got a 500.
    pool_size=5,
    max_overflow=10,
    # Lowered from 30s: with a ceiling of 15, waiting half a minute for a
    # connection means something is badly wrong and the browser gave up long
    # ago. Failing at 10s produces a legible error instead of a hung request.
    pool_timeout=10,
    # The DATABASE_URL points at a DIRECT Neon endpoint (no "-pooler"), which
    # suspends idle compute and closes connections. Without pre-ping the pool
    # hands out a connection the server already dropped.
    pool_pre_ping=True,
    pool_recycle=300,
    # Closes the other half of the pool pendency: select_for_update in the
    # review flow used to wait indefinitely while holding a connection. This is
    # GLOBAL — every statement, not just that one — which is acceptable because
    # that is the only place in the system that takes a lock. The surgical
    # alternative would be SET LOCAL lock_timeout inside UnitOfWork.
    #
    # Delivered through `options` rather than as a server_settings key of its
    # own, which is what asyncpg's docs suggest and what this plan first
    # specified. Against this Neon endpoint that silently does nothing: the
    # proxy forwards startup parameters it "reports" (application_name arrives
    # fine) and drops the rest, so SHOW lock_timeout answered 0 with no error
    # anywhere. `options` is passed through as a single opaque string and
    # survives. Verified with SHOW lock_timeout — see Step 5.
    connect_args={"server_settings": {"options": "-c lock_timeout=3000"}},
)
```

- [ ] **Step 4: Rodar e ver passar**

Run: `.venv/bin/python3 -m pytest src/models/settings/ -v`
Expected: PASS.

- [ ] **Step 5: Provar que a configuração chegou ao banco de verdade**

O teste do Step 1 é uma rede contra revert acidental — ele lê o que
configuramos, não o que o servidor recebeu. Este step é a verificação
comportamental, e é **obrigatório**: se `connect_args` estiver na forma errada
para o asyncpg, o teste do Step 1 continua verde e a aplicação quebra na
primeira conexão.

```bash
.venv/bin/python3 -c "
import asyncio
from sqlalchemy import text
from src.models.settings.database_connection_handler import engine

async def main():
    async with engine.connect() as connection:
        print('lock_timeout =', (await connection.execute(text('SHOW lock_timeout'))).scalar())

asyncio.run(main())
"
```

Esperado: `lock_timeout = 3s`. É o próprio PostgreSQL respondendo qual valor
está em vigor na sessão — nenhum mock no caminho.

**Se aparecer `0`, não conserte adivinhando.** Foi exatamente o que aconteceu na
primeira execução desta task, e a causa não é óbvia: passar `lock_timeout` como
chave própria de `server_settings` — a forma que a documentação do asyncpg
sugere — não produz erro nenhum e mesmo assim não chega ao servidor. O proxy do
Neon repassa os parâmetros de startup que ele "reporta" (`application_name`
chega) e descarta o resto, em silêncio. Por isso o valor vai dentro de
`options`, que trafega como string opaca.

Confirme também que a aplicação sobe:

```bash
.venv/bin/python3 -m uvicorn src.main.server.server:app --port 3333 &
sleep 5
curl -s -o /dev/null -w "%{http_code}\n" localhost:3333/refunds
kill %1
```

Esperado: `401` (sem token) — a aplicação subiu e a rota respondeu. **Não existe
`run:app`** — `run.py` não expõe `app` no nível do módulo.

- [ ] **Step 6: Rodar a suíte inteira e o lint**

Run: `.venv/bin/python3 -m pytest && .venv/bin/python3 -m pylint src`
Expected: 180 passed; `10.00/10`.

- [ ] **Step 7: Commit**

```bash
git add src/models/settings/
git commit -m "fix: size the connection pool and discard dead connections"
```

---

### Task 3: `RefundStatusRepository.mark_as_paid`

**Files:**
- Modify: `src/models/repositories/refund_status_repository.py`
- Modify: `src/models/repositories/interfaces/refund_status_repository_interface.py`
- Modify: `src/models/repositories/refund_status_repository_test.py`

**Interfaces:**
- Consumes: coluna `payment_filename` (Task 1).
- Produces: `async def mark_as_paid(self, refund_id: int, payment_filename: str) -> int` — devolve o número de linhas afetadas (`0` quando o reembolso não está mais `approved`).

- [ ] **Step 1: Escrever os testes que falham**

Acrescente a `src/models/repositories/refund_status_repository_test.py`:

Use a fixture `mock_session` que **já existe** neste arquivo — esta classe recebe
uma `AsyncSession` direto no construtor, então não há `.connect()` a simular.
Não replique o `mock_db` dos testes de `RefundsRepository`/`UsersRepository`:
aquelas classes recebem uma conexão e abrem a sessão sozinhas, e é só por isso
que precisam do `mock_connection` do `conftest.py`.

```python
# The UPDATE is conditional on status='approved' so the database itself refuses
# a second concurrent payment. This is deliberately NOT select_for_update: a
# lock would hold a pool connection while waiting, which is the documented
# pendency this cycle avoids making worse.
@pytest.mark.asyncio
async def test_mark_as_paid_only_touches_a_refund_still_approved(mock_session):
    mock_session.execute = AsyncMock(return_value=MagicMock(rowcount=1))
    repository = RefundStatusRepository(mock_session)

    affected = await repository.mark_as_paid(1, "receipt.pdf")

    assert affected == 1
    # Asserting on the emitted statement, not just on the returned rowcount:
    # with a mocked session the rowcount is whatever we told it to be, so a
    # WHERE clause that lost the status condition would pass a rowcount-only
    # test while silently reopening the double-payment race. Same idiom as
    # refunds_repository_test.py::test_delete_refund_filters_on_pending_status.
    statement = str(mock_session.execute.call_args[0][0])
    assert "status" in statement


# Zero rows means someone else paid first between our guard check and this
# UPDATE. The controller turns that into a 422 and deletes the file it had
# already written.
@pytest.mark.asyncio
async def test_mark_as_paid_reports_zero_when_the_status_already_changed(mock_session):
    mock_session.execute = AsyncMock(return_value=MagicMock(rowcount=0))
    repository = RefundStatusRepository(mock_session)

    affected = await repository.mark_as_paid(1, "receipt.pdf")

    assert affected == 0
```

Se `AsyncMock`, `MagicMock` ou `pytest` ainda não estiverem importados no arquivo, acrescente:

```python
from unittest.mock import AsyncMock, MagicMock
import pytest
```

**Prove que a asserção do statement pode falhar** antes de commitar: remova
`Refunds.c.status == "approved"` do `WHERE`, rode o teste, veja vermelho,
recoloque e veja verde. Uma guarda que ninguém viu falhar ainda não é uma
guarda.

- [ ] **Step 2: Rodar e ver falhar**

Run: `.venv/bin/python3 -m pytest src/models/repositories/refund_status_repository_test.py -v`
Expected: FAIL — `AttributeError: 'RefundStatusRepository' object has no attribute 'mark_as_paid'`.

- [ ] **Step 3: Implementar**

Em `src/models/repositories/refund_status_repository.py`, depois de `update_status`:

```python
    async def mark_as_paid(self, refund_id: int, payment_filename: str) -> int:
        # Conditional on the current status: if a concurrent request already
        # paid this refund, the WHERE matches nothing and rowcount is 0. That
        # closes the race WITHOUT taking a lock, unlike select_for_update above
        # — a lock would hold a pool connection while waiting.
        query = (
            update(Refunds)
            .where(Refunds.c.id == refund_id, Refunds.c.status == "approved")
            .values(status="paid", payment_filename=payment_filename)
        )
        result = await self.__session.execute(query)
        return result.rowcount
```

**Atenção ao name mangling:** dentro da classe o atributo é `self.__session`, mas se você colar este método fora da classe ele não resolve. Ele vai **dentro** de `RefundStatusRepository`.

- [ ] **Step 4: Declarar na interface**

Em `src/models/repositories/interfaces/refund_status_repository_interface.py`:

```python
    @abstractmethod
    async def mark_as_paid(self, refund_id: int, payment_filename: str) -> int:
        pass
```

- [ ] **Step 5: Rodar e ver passar**

Run: `.venv/bin/python3 -m pytest src/models/repositories/ -v`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add src/models/repositories/
git commit -m "feat: mark a refund as paid with a conditional update"
```

---

### Task 4: `refund_payer_validator`

**Files:**
- Create: `src/validators/refund_payer_validator.py`
- Create: `src/validators/refund_payer_validator_test.py`

**Interfaces:**
- Consumes: nada.
- Produces: `def refund_payer_validator(http_request: HttpRequest) -> None` — levanta `HttpUnprocessableEntityError`.

- [ ] **Step 1: Escrever os testes que falham**

Crie `src/validators/refund_payer_validator_test.py`:

```python
import pytest
from src.errors.types.http_unprocessable_entity_error import HttpUnprocessableEntityError
from src.views.http_types.http_request import HttpRequest
from .refund_payer_validator import refund_payer_validator


def build_request(filename="proof.pdf", content=b"x"):
    return HttpRequest(body={"filename": filename, "content": content})


# BR-009 extended: the payment receipt obeys the same format rule as the
# expense receipt. Parametrized rather than looped so a failure names the
# extension that broke instead of hiding the ones after it.
@pytest.mark.parametrize("filename", ["proof.jpg", "proof.jpeg", "proof.png", "proof.pdf"])
def test_accepts_the_allowed_extensions(filename):
    refund_payer_validator(build_request(filename=filename))


# A real upload can arrive named PROOF.PDF. Without this, deleting .lower()
# from the validator would pass the whole suite — every other filename here is
# already lowercase. Mirrors refund_creator_validator_test.py's own case test.
@pytest.mark.parametrize("filename", ["proof.PDF", "PROOF.JPG", "Proof.PnG"])
def test_accepts_the_allowed_extensions_regardless_of_case(filename):
    refund_payer_validator(build_request(filename=filename))


# Validated by extension, never by the client-supplied Content-Type: that
# header is set by whatever HTTP client is uploading and is unreliable.
def test_rejects_a_disallowed_extension():
    with pytest.raises(HttpUnprocessableEntityError):
        refund_payer_validator(build_request(filename="proof.exe"))


def test_rejects_a_missing_file():
    with pytest.raises(HttpUnprocessableEntityError):
        refund_payer_validator(build_request(filename=""))


# The ceiling is read from config, not hardcoded, so this test stays valid if
# the limit changes.
def test_accepts_a_file_exactly_at_the_size_ceiling():
    at_limit = b"x" * upload_info["MAX_FILE_SIZE_BYTES"]
    refund_payer_validator(build_request(content=at_limit))


# Paired with the test above on purpose: testing only MAX + 1 passes whether
# the operator is > or >=, so an off-by-one that started rejecting files of
# exactly 4MB would slip through. The pair pins the boundary.
def test_rejects_a_file_over_the_size_ceiling():
    oversized = b"x" * (upload_info["MAX_FILE_SIZE_BYTES"] + 1)
    with pytest.raises(HttpUnprocessableEntityError):
        refund_payer_validator(build_request(content=oversized))
```

O arquivo de teste importa `from src.configs.global_config import upload_info`.

**Prove que os dois testes novos podem falhar** antes de commitar: troque `>`
por `>=` e veja o teste de fronteira ficar vermelho; remova o `.lower()` e veja
o teste de maiúsculas ficar vermelho. Restaure os dois e confirme o verde.

- [ ] **Step 2: Rodar e ver falhar**

Run: `.venv/bin/python3 -m pytest src/validators/refund_payer_validator_test.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'src.validators.refund_payer_validator'`.

- [ ] **Step 3: Implementar**

Crie `src/validators/refund_payer_validator.py`:

```python
import os
from src.configs.global_config import upload_info
from src.errors.types.http_unprocessable_entity_error import HttpUnprocessableEntityError
from src.views.http_types.http_request import HttpRequest

# Same set as refund_creator_validator: BR-009 covers both receipts. Kept as a
# separate constant rather than imported so that loosening one file's rule does
# not silently loosen the other's.
ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".pdf"}


def refund_payer_validator(http_request: HttpRequest) -> None:
    body = http_request.body

    # By extension, not by the client-supplied Content-Type header: that header
    # comes from whatever HTTP client is uploading and is unreliable in practice.
    extension = os.path.splitext(body.get("filename") or "")[1].lower()
    if extension not in ALLOWED_EXTENSIONS:
        raise HttpUnprocessableEntityError("Payment receipt must be JPG, PNG or PDF")

    if len(body.get("content", b"")) > upload_info["MAX_FILE_SIZE_BYTES"]:
        raise HttpUnprocessableEntityError("Payment receipt must be smaller than 4MB")
```

- [ ] **Step 4: Rodar e ver passar**

Run: `.venv/bin/python3 -m pytest src/validators/ -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/validators/
git commit -m "feat: validate the payment receipt format and size"
```

---

### Task 5: `RefundPayerController`

**Files:**
- Create: `src/controllers/refund_payer_controller.py`
- Create: `src/controllers/refund_payer_controller_test.py`
- Create: `src/controllers/interfaces/refund_payer_controller_interface.py`

**Interfaces:**
- Consumes: `RefundStatusRepository.mark_as_paid` (Task 3) via `UnitOfWork.refunds`; `RefundsRepository.select_refund_by_id`; `FileStorageInterface.save/delete`.
- Produces: `async def pay(self, refund_id: int, payer_id: int, role: str, filename: str, content: bytes) -> dict` — devolve `{"type": "Refund", "count": 1, "attributes": <serialize_refund>}`.

- [ ] **Step 1: Escrever a interface**

Crie `src/controllers/interfaces/refund_payer_controller_interface.py`:

```python
from abc import ABC, abstractmethod


class RefundPayerControllerInterface(ABC):

    @abstractmethod
    async def pay(
        self,
        refund_id: int,
        payer_id: int,
        role: str,
        filename: str,
        content: bytes,
    ) -> dict:
        pass
```

- [ ] **Step 2: Escrever os testes que falham**

Crie `src/controllers/refund_payer_controller_test.py`:

```python
# pylint: disable=w0621
from unittest.mock import AsyncMock, MagicMock
import pytest
from src.errors.types.http_forbidden_error import HttpForbiddenError
from src.errors.types.http_not_found_error import HttpNotFoundError
from src.errors.types.http_unprocessable_entity_error import HttpUnprocessableEntityError
from .refund_payer_controller import RefundPayerController


def build_unit_of_work(affected=1):
    """Builds a UnitOfWork test double usable as `async with`."""
    unit_of_work = MagicMock()
    unit_of_work.refunds = MagicMock()
    unit_of_work.refunds.mark_as_paid = AsyncMock(return_value=affected)
    unit_of_work.reviews = MagicMock()
    unit_of_work.reviews.insert_review = AsyncMock()
    unit_of_work.commit = AsyncMock()
    unit_of_work.__aenter__ = AsyncMock(return_value=unit_of_work)
    unit_of_work.__aexit__ = AsyncMock(return_value=None)
    return unit_of_work


def build_repository(refund):
    """Repository double whose reads return the nested-user shape."""
    repository = MagicMock()
    repository.select_refund_by_id = AsyncMock(return_value=refund)
    return repository


@pytest.fixture
def approved_refund():
    return {
        "id": 1,
        "name": "Almoço",
        "category": "food",
        "amount_in_cents": 12000,
        "status": "approved",
        "created_at": None,
        "filename": "a.jpg",
        "user": {"id": 7, "name": "Ana", "avatar_filename": None},
    }


@pytest.fixture
def paid_refund(approved_refund):
    return {**approved_refund, "status": "paid"}


@pytest.mark.asyncio
async def test_admin_pays_an_approved_refund(approved_refund, paid_refund):
    unit_of_work = build_unit_of_work()
    repository = build_repository(approved_refund)
    # The re-read after commit must show the new status, so the second call
    # returns the paid row.
    repository.select_refund_by_id = AsyncMock(side_effect=[approved_refund, paid_refund])
    storage = MagicMock()
    storage.save = MagicMock(return_value="stored.pdf")
    controller = RefundPayerController(unit_of_work, repository, storage)

    response = await controller.pay(
        refund_id=1, payer_id=9, role="admin", filename="proof.pdf", content=b"x"
    )

    unit_of_work.refunds.mark_as_paid.assert_awaited_once_with(1, "stored.pdf")
    unit_of_work.reviews.insert_review.assert_awaited_once_with(
        refund_id=1, reviewer_id=9, from_status="approved", to_status="paid", reason=None
    )
    unit_of_work.commit.assert_awaited_once()
    assert response["attributes"]["status"] == "paid"
    # The response uses the shared serializer, so the requester is nested and
    # no filename leaks — unlike the PATCH /status response.
    assert response["attributes"]["user"] == {"id": 7, "name": "Ana", "has_avatar": False}
    assert "filename" not in response["attributes"]
    assert "payment_filename" not in response["attributes"]


# The role check runs BEFORE touching the database on purpose: a check that
# never queries cannot leak whether the id exists, so a standard user gets the
# same 403 for a real id and for a made-up one.
@pytest.mark.asyncio
async def test_standard_user_is_forbidden_and_the_database_is_never_touched(approved_refund):
    unit_of_work = build_unit_of_work()
    repository = build_repository(approved_refund)
    storage = MagicMock()
    controller = RefundPayerController(unit_of_work, repository, storage)

    with pytest.raises(HttpForbiddenError):
        await controller.pay(
            refund_id=1, payer_id=9, role="standard", filename="proof.pdf", content=b"x"
        )

    repository.select_refund_by_id.assert_not_awaited()
    storage.save.assert_not_called()


@pytest.mark.asyncio
async def test_unknown_refund_is_not_found():
    unit_of_work = build_unit_of_work()
    repository = build_repository(None)
    controller = RefundPayerController(unit_of_work, repository, MagicMock())

    with pytest.raises(HttpNotFoundError):
        await controller.pay(
            refund_id=1, payer_id=9, role="admin", filename="proof.pdf", content=b"x"
        )


# BR-016 extended to payment: an admin already cannot approve their own refund,
# so being able to pay it would be a hole in the same rule.
@pytest.mark.asyncio
async def test_admin_cannot_pay_their_own_refund(approved_refund):
    unit_of_work = build_unit_of_work()
    repository = build_repository(approved_refund)
    storage = MagicMock()
    controller = RefundPayerController(unit_of_work, repository, storage)

    with pytest.raises(HttpForbiddenError):
        await controller.pay(
            refund_id=1, payer_id=7, role="admin", filename="proof.pdf", content=b"x"
        )

    # The raised exception alone would not catch a guard that ran AFTER the file
    # was written: the call would still fail with 403 while leaving an orphaned
    # file on disk every time an admin tried to pay their own refund. Guard
    # ordering is a security property, so every guard test pins its side effect.
    storage.save.assert_not_called()


# Only an approved refund can be paid: pending has not been decided and
# rejected owes nothing.
@pytest.mark.asyncio
async def test_a_refund_that_is_not_approved_cannot_be_paid(approved_refund):
    unit_of_work = build_unit_of_work()
    repository = build_repository({**approved_refund, "status": "pending"})
    storage = MagicMock()
    controller = RefundPayerController(unit_of_work, repository, storage)

    with pytest.raises(HttpUnprocessableEntityError):
        await controller.pay(
            refund_id=1, payer_id=9, role="admin", filename="proof.pdf", content=b"x"
        )

    # The file is only written once every guard has passed.
    storage.save.assert_not_called()


# The race the conditional UPDATE closes: another admin paid between our guard
# read and our write. The file we already wrote must not survive the failure.
@pytest.mark.asyncio
async def test_a_lost_race_deletes_the_file_it_had_written(approved_refund):
    unit_of_work = build_unit_of_work(affected=0)
    repository = build_repository(approved_refund)
    storage = MagicMock()
    storage.save = MagicMock(return_value="stored.pdf")
    storage.delete = MagicMock()
    controller = RefundPayerController(unit_of_work, repository, storage)

    with pytest.raises(HttpUnprocessableEntityError):
        await controller.pay(
            refund_id=1, payer_id=9, role="admin", filename="proof.pdf", content=b"x"
        )

    storage.delete.assert_called_once_with("stored.pdf")
    unit_of_work.commit.assert_not_awaited()
    # Pins the ordering too: the log row must not be written for a payment that
    # did not happen. The UnitOfWork would roll it back anyway, but relying on
    # that leaves the ordering unasserted.
    unit_of_work.reviews.insert_review.assert_not_awaited()
```

- [ ] **Step 3: Rodar e ver falhar**

Run: `.venv/bin/python3 -m pytest src/controllers/refund_payer_controller_test.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'src.controllers.refund_payer_controller'`.

- [ ] **Step 4: Implementar**

Crie `src/controllers/refund_payer_controller.py`:

```python
# pylint: disable=duplicate-code
# Shares its response envelope with RefundCreatorController and its role-first
# guard with RefundReviewerController; both are deliberately identical rules.
from src.models.settings.unit_of_work import UnitOfWork
from src.models.repositories.interfaces.refunds_repository_interface import RefundsRepositoryInterface
from src.drivers.interfaces.file_storage_interface import FileStorageInterface
from src.controllers.interfaces.refund_payer_controller_interface import (
    RefundPayerControllerInterface,
)
from src.controllers.refund_serializer import serialize_refund
from src.errors.types.http_forbidden_error import HttpForbiddenError
from src.errors.types.http_not_found_error import HttpNotFoundError
from src.errors.types.http_unprocessable_entity_error import HttpUnprocessableEntityError


class RefundPayerController(RefundPayerControllerInterface):
    def __init__(
        self,
        unit_of_work: UnitOfWork,
        refunds_repository: RefundsRepositoryInterface,
        payment_storage: FileStorageInterface,
    ) -> None:
        self.__unit_of_work = unit_of_work
        self.__refunds_repository = refunds_repository
        self.__payment_storage = payment_storage

    async def pay(
        self,
        refund_id: int,
        payer_id: int,
        role: str,
        filename: str,
        content: bytes,
    ) -> dict:
        # Role first, before any database access. A check that never queries
        # cannot leak whether the id exists, so a standard user gets an
        # identical 403 for a real and for an invented id.
        if role != "admin":
            raise HttpForbiddenError("Only administrators can pay refunds")

        # Read WITHOUT a lock. select_for_update would hold a pool connection
        # while waiting; the conditional UPDATE below closes the race instead.
        refund = await self.__refunds_repository.select_refund_by_id(refund_id)

        if not refund:
            raise HttpNotFoundError("Refund not found")

        # BR-016 extended. A 403 is safe: whoever got here is an admin and, by
        # BR-012, already sees every refund, so nothing is left to leak.
        if refund["user"]["id"] == payer_id:
            raise HttpForbiddenError("You cannot pay your own refund")

        if refund["status"] != "approved":
            raise HttpUnprocessableEntityError("Only an approved refund can be paid")

        # The filename must exist before the UPDATE, so the file goes to disk
        # first. A crash between here and the UPDATE still orphans it — that is
        # Item 21, unresolved, and the UnitOfWork does NOT cover it: it bounds
        # the database transaction, and the filesystem is not part of it.
        stored_filename = self.__payment_storage.save(filename, content)

        async with self.__unit_of_work as unit_of_work:
            affected = await unit_of_work.refunds.mark_as_paid(refund_id, stored_filename)

            if affected == 0:
                # Another admin paid between our read and our write. Compensate
                # for the file we just wrote before failing.
                self.__payment_storage.delete(stored_filename)
                raise HttpUnprocessableEntityError("Only an approved refund can be paid")

            await unit_of_work.reviews.insert_review(
                refund_id=refund_id,
                reviewer_id=payer_id,
                from_status="approved",
                to_status="paid",
                reason=None,
            )
            await unit_of_work.commit()

        # Re-read instead of patching the row we already have. The PATCH /status
        # endpoint built its response from a different repository and created the
        # divergent shape documented in UC-007; a new surface starts correct.
        paid_refund = await self.__refunds_repository.select_refund_by_id(refund_id)

        return {
            "type": "Refund",
            "count": 1,
            "attributes": serialize_refund(paid_refund),
        }
```

- [ ] **Step 5: Rodar e ver passar**

Run: `.venv/bin/python3 -m pytest src/controllers/refund_payer_controller_test.py -v`
Expected: 6 passed.

- [ ] **Step 6: Rodar suíte e lint**

Run: `.venv/bin/python3 -m pytest && .venv/bin/python3 -m pylint src`
Expected: tudo verde; `10.00/10`.

- [ ] **Step 7: Commit**

```bash
git add src/controllers/
git commit -m "feat: pay an approved refund inside one transaction"
```

---

### Task 6: View, composer, configuração e rota do pagamento

**Files:**
- Create: `src/views/refund_payer_view.py`, `src/views/refund_payer_view_test.py`
- Create: `src/main/composer/refund_payer_composer.py`
- Create: `uploads/payment_receipts/.gitkeep`
- Modify: `src/configs/global_config.py`, `.gitignore`, `src/main/routes/refund_routes.py`

**Interfaces:**
- Consumes: `RefundPayerController.pay` (Task 5), `refund_payer_validator` (Task 4).
- Produces: `POST /refunds/{refund_id}/payment` respondendo `200`.

- [ ] **Step 1: Escrever o teste da view**

Crie `src/views/refund_payer_view_test.py`:

```python
from unittest.mock import AsyncMock, MagicMock
import pytest
from src.views.http_types.http_request import HttpRequest
from .refund_payer_view import RefundPayerView


# The validator runs BEFORE the controller, so a malformed upload never reaches
# the database — the same short-circuit RefundReviewerView relies on.
@pytest.mark.asyncio
async def test_invalid_file_short_circuits_before_the_controller():
    controller = MagicMock()
    controller.pay = AsyncMock()
    view = RefundPayerView(controller)
    request = HttpRequest(
        body={"filename": "proof.exe", "content": b"x"},
        path_params={"refund_id": 1},
        token_info={"user_id": 9, "role": "admin"},
    )

    # Assert the SPECIFIC error, not a bare Exception. A loose
    # `pytest.raises(Exception)` is satisfied by any failure from any cause, so
    # a typo like body["filenam"] inside the validator would keep this test
    # green while the endpoint started answering 500 where it owes 422. Follow
    # refund_reviewer_view_test.py, which asserts the status code.
    with pytest.raises(HTTPException) as exception_info:
        await view.handle(request)

    assert exception_info.value.status_code == 422
    controller.pay.assert_not_awaited()


@pytest.mark.asyncio
async def test_a_valid_upload_reaches_the_controller():
    controller = MagicMock()
    controller.pay = AsyncMock(return_value={"type": "Refund", "count": 1, "attributes": {}})
    view = RefundPayerView(controller)
    request = HttpRequest(
        body={"filename": "proof.pdf", "content": b"x"},
        path_params={"refund_id": 1},
        token_info={"user_id": 9, "role": "admin"},
    )

    response = await view.handle(request)

    assert response.status_code == 200
    # Also assert the body: without this, a view that discarded the
    # controller's return value and answered an empty 200 would pass.
    assert response.body == {"type": "Refund", "count": 1, "attributes": {}}
    controller.pay.assert_awaited_once_with(
        refund_id=1, payer_id=9, role="admin", filename="proof.pdf", content=b"x"
    )
```

O teste importa `from fastapi import HTTPException` — o `error_handler` converte
os erros do projeto nele.

**Sobre a ordem da rota:** o plano pede declarar `POST /{refund_id}/payment`
antes de `GET /{refund_id}` seguindo a convenção do arquivo, e isso é boa
prática — mas vale a precisão: **as duas rotas não colidiriam de qualquer
forma.** `/refunds/{refund_id}` compila para um regex ancorado de exatamente um
segmento e `/refunds/{refund_id}/payment` exige dois, além de os métodos
diferirem. A ordem importa de verdade quando duas rotas têm o mesmo número de
segmentos e o mesmo método (um `/refunds/me` contra `/refunds/{refund_id}`, por
exemplo).

- [ ] **Step 2: Rodar e ver falhar**

Run: `.venv/bin/python3 -m pytest src/views/refund_payer_view_test.py -v`
Expected: FAIL — módulo não encontrado.

- [ ] **Step 3: Escrever a view**

Crie `src/views/refund_payer_view.py`:

```python
from src.controllers.interfaces.refund_payer_controller_interface import (
    RefundPayerControllerInterface,
)
from src.validators.refund_payer_validator import refund_payer_validator
from src.views.http_types.http_request import HttpRequest
from src.views.http_types.http_response import HttpResponse
from src.errors.error_handler import error_handler


class RefundPayerView:
    def __init__(self, controller: RefundPayerControllerInterface) -> None:
        self.__controller = controller

    async def handle(self, http_request: HttpRequest) -> HttpResponse:
        try:
            refund_payer_validator(http_request)

            response = await self.__controller.pay(
                refund_id=http_request.path_params["refund_id"],
                payer_id=http_request.token_info["user_id"],
                role=http_request.token_info["role"],
                filename=http_request.body["filename"],
                content=http_request.body["content"],
            )
            return HttpResponse(body=response, status_code=200)
        except Exception as e:
            error_handler(e)
```

- [ ] **Step 4: Configurar o diretório novo**

Em `src/configs/global_config.py`, dentro de `upload_info`:

```python
    "PAYMENT_DIR": os.getenv("PAYMENT_DIR", "uploads/payment_receipts"),
```

Crie o diretório e o marcador:

```bash
mkdir -p uploads/payment_receipts && touch uploads/payment_receipts/.gitkeep
```

Em `.gitignore`, junto das negações existentes:

```
!uploads/payment_receipts/
!uploads/payment_receipts/.gitkeep
```

**Isto não é opcional.** Nenhum código da aplicação cria diretório de upload — não há `makedirs` em lugar nenhum. Sem o `.gitkeep` versionado, um clone limpo dá `FileNotFoundError` no primeiro pagamento.

- [ ] **Step 5: Escrever o composer**

Crie `src/main/composer/refund_payer_composer.py`:

```python
from src.models.settings.database_connection_handler import database_connection_handler
from src.models.settings.unit_of_work import UnitOfWork
from src.models.repositories.refunds_repository import RefundsRepository
from src.drivers.file_storage import FileStorage
from src.configs.global_config import upload_info
from src.controllers.refund_payer_controller import RefundPayerController
from src.views.refund_payer_view import RefundPayerView


def refund_payer_composer():
    # A fresh UnitOfWork per request: it holds a session for one transaction, so
    # sharing one across requests would share a session.
    unit_of_work = UnitOfWork(database_connection_handler)
    repository = RefundsRepository(database_connection_handler)
    storage = FileStorage(upload_info["PAYMENT_DIR"])
    controller = RefundPayerController(unit_of_work, repository, storage)
    view = RefundPayerView(controller)
    return view
```

- [ ] **Step 6: Registrar a rota**

Em `src/main/routes/refund_routes.py`, importe o composer e acrescente a rota **antes** de `@refund_routes.get("/{refund_id}")`:

```python
@refund_routes.post("/{refund_id}/payment")
async def pay_refund(
    refund_id: int,
    file: UploadFile = File(...),
    token_info: dict = Depends(get_current_user),
):
    content = await file.read()
    http_request = HttpRequest(
        path_params={"refund_id": refund_id},
        body={"filename": file.filename, "content": content},
        token_info=token_info,
    )
    view = refund_payer_composer()
    response = await view.handle(http_request)
    return JSONResponse(content=response.body, status_code=response.status_code)
```

- [ ] **Step 7: Rodar e ver passar**

Run: `.venv/bin/python3 -m pytest && .venv/bin/python3 -m pylint src`
Expected: tudo verde; `10.00/10`.

- [ ] **Step 8: Commit**

```bash
git add src/views/ src/main/ src/configs/ .gitignore uploads/payment_receipts/.gitkeep
git commit -m "feat: expose POST /refunds/{id}/payment"
```

---

### Task 7: Servir o comprovante de pagamento

**Files:**
- Create: `src/controllers/payment_receipt_finder_controller.py` (+`_test`), `src/controllers/interfaces/payment_receipt_finder_controller_interface.py`
- Create: `src/views/payment_receipt_finder_view.py`, `src/main/composer/payment_receipt_finder_composer.py`
- Modify: `src/main/routes/refund_routes.py`

**Interfaces:**
- Consumes: `RefundsRepositoryInterface.select_refund_by_id`, `FileStorageInterface.read`.
- Produces: `GET /refunds/{refund_id}/payment-receipt` devolvendo bytes; controller `async def find(self, refund_id: int, user_id: int, role: str) -> dict` com `{"content": bytes, "media_type": str}`.

- [ ] **Step 1: Escrever os testes que falham**

Crie `src/controllers/payment_receipt_finder_controller_test.py`:

```python
# pylint: disable=w0621
from unittest.mock import AsyncMock, MagicMock
import pytest
from src.errors.types.http_not_found_error import HttpNotFoundError
from .payment_receipt_finder_controller import PaymentReceiptFinderController


@pytest.fixture
def paid_refund():
    return {
        "id": 1,
        "status": "paid",
        "payment_filename": "proof.pdf",
        "user": {"id": 7, "name": "Ana", "avatar_filename": None},
    }


def build_controller(refund, content=b"bytes"):
    repository = MagicMock()
    repository.select_refund_by_id = AsyncMock(return_value=refund)
    storage = MagicMock()
    storage.read = MagicMock(return_value=content)
    return PaymentReceiptFinderController(repository, storage), storage


@pytest.mark.asyncio
async def test_owner_reads_the_payment_receipt(paid_refund):
    controller, _ = build_controller(paid_refund)

    response = await controller.find(refund_id=1, user_id=7, role="standard")

    assert response["content"] == b"bytes"
    assert response["media_type"] == "application/pdf"


@pytest.mark.asyncio
async def test_admin_reads_someone_elses_payment_receipt(paid_refund):
    controller, _ = build_controller(paid_refund)

    response = await controller.find(refund_id=1, user_id=99, role="admin")

    assert response["content"] == b"bytes"


# All four failure modes answer with the SAME 404 message: unknown id, someone
# else's refund, a refund that was never paid, and a row whose file vanished.
# Any difference between them would be an oracle.
@pytest.mark.asyncio
async def test_unknown_refund_is_not_found():
    controller, _ = build_controller(None)

    with pytest.raises(HttpNotFoundError, match="Refund not found"):
        await controller.find(refund_id=1, user_id=7, role="standard")


@pytest.mark.asyncio
async def test_someone_elses_refund_is_not_found(paid_refund):
    controller, _ = build_controller(paid_refund)

    with pytest.raises(HttpNotFoundError, match="Refund not found"):
        await controller.find(refund_id=1, user_id=99, role="standard")


@pytest.mark.asyncio
async def test_an_unpaid_refund_is_not_found(paid_refund):
    controller, _ = build_controller({**paid_refund, "status": "approved", "payment_filename": None})

    with pytest.raises(HttpNotFoundError, match="Refund not found"):
        await controller.find(refund_id=1, user_id=7, role="standard")


@pytest.mark.asyncio
async def test_a_missing_file_is_not_found(paid_refund):
    controller, storage = build_controller(paid_refund)
    storage.read = MagicMock(side_effect=FileNotFoundError)

    with pytest.raises(HttpNotFoundError, match="Refund not found"):
        await controller.find(refund_id=1, user_id=7, role="standard")
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `.venv/bin/python3 -m pytest src/controllers/payment_receipt_finder_controller_test.py -v`
Expected: FAIL — módulo não encontrado.

- [ ] **Step 3: Escrever a interface**

Crie `src/controllers/interfaces/payment_receipt_finder_controller_interface.py`:

```python
from abc import ABC, abstractmethod


class PaymentReceiptFinderControllerInterface(ABC):

    @abstractmethod
    async def find(self, refund_id: int, user_id: int, role: str) -> dict:
        pass
```

- [ ] **Step 4: Escrever o controller**

Crie `src/controllers/payment_receipt_finder_controller.py`:

```python
# pylint: disable=duplicate-code
# Shares its "404 for both missing and not-yours" guard with
# ReceiptFinderController; the rule is deliberately identical.
import mimetypes
from src.models.repositories.interfaces.refunds_repository_interface import RefundsRepositoryInterface
from src.drivers.interfaces.file_storage_interface import FileStorageInterface
from src.controllers.interfaces.payment_receipt_finder_controller_interface import (
    PaymentReceiptFinderControllerInterface,
)
from src.errors.types.http_not_found_error import HttpNotFoundError


class PaymentReceiptFinderController(PaymentReceiptFinderControllerInterface):
    def __init__(
        self,
        refunds_repository: RefundsRepositoryInterface,
        payment_storage: FileStorageInterface,
    ) -> None:
        self.__refunds_repository = refunds_repository
        self.__payment_storage = payment_storage

    async def find(self, refund_id: int, user_id: int, role: str) -> dict:
        refund = await self.__refunds_repository.select_refund_by_id(refund_id)

        if not refund or (role != "admin" and refund["user"]["id"] != user_id):
            raise HttpNotFoundError("Refund not found")

        filename = refund.get("payment_filename")

        # An unpaid refund answers exactly like an unknown one. Saying "this
        # refund exists but is not paid" would leak state to someone who may
        # not be entitled to it, and there is no reason to distinguish.
        if not filename:
            raise HttpNotFoundError("Refund not found")

        try:
            content = self.__payment_storage.read(filename)
        except FileNotFoundError as exception:
            raise HttpNotFoundError("Refund not found") from exception

        return {"content": content, "media_type": self.__media_type(filename)}

    def __media_type(self, filename: str) -> str:
        # Derived from the stored extension, never from a client header.
        guessed, _ = mimetypes.guess_type(filename)
        return guessed or "application/octet-stream"
```

- [ ] **Step 5: Expor `payment_filename` na leitura do repositório**

Em `src/models/repositories/refunds_repository.py`, o método privado `__to_refund` monta o dicionário devolvido. Acrescente `payment_filename` ao dicionário, ao lado de `filename`.

O repositório continua devolvendo os dois nomes de arquivo crus — `serialize_refund` é quem os descarta. Mesma disciplina do ciclo de serving autenticado: **quem lê o disco precisa do nome; quem responde HTTP não.**

- [ ] **Step 6: Rodar e ver passar**

Run: `.venv/bin/python3 -m pytest src/controllers/payment_receipt_finder_controller_test.py -v`
Expected: 6 passed.

- [ ] **Step 7: Escrever view, composer e rota**

Crie `src/views/payment_receipt_finder_view.py`:

```python
from src.controllers.interfaces.payment_receipt_finder_controller_interface import (
    PaymentReceiptFinderControllerInterface,
)
from src.views.http_types.http_request import HttpRequest
from src.views.http_types.http_response import HttpResponse
from src.errors.error_handler import error_handler


class PaymentReceiptFinderView:
    def __init__(self, controller: PaymentReceiptFinderControllerInterface) -> None:
        self.__controller = controller

    async def handle(self, http_request: HttpRequest) -> HttpResponse:
        try:
            response = await self.__controller.find(
                refund_id=http_request.path_params["refund_id"],
                user_id=http_request.token_info["user_id"],
                role=http_request.token_info["role"],
            )
            # Raw bytes plus media type: the route turns this into a binary
            # Response, not a JSONResponse.
            return HttpResponse(body=response, status_code=200)
        except Exception as e:
            error_handler(e)
```

Crie `src/main/composer/payment_receipt_finder_composer.py`:

```python
from src.models.settings.database_connection_handler import database_connection_handler
from src.models.repositories.refunds_repository import RefundsRepository
from src.drivers.file_storage import FileStorage
from src.configs.global_config import upload_info
from src.controllers.payment_receipt_finder_controller import PaymentReceiptFinderController
from src.views.payment_receipt_finder_view import PaymentReceiptFinderView


def payment_receipt_finder_composer():
    repository = RefundsRepository(database_connection_handler)
    storage = FileStorage(upload_info["PAYMENT_DIR"])
    controller = PaymentReceiptFinderController(repository, storage)
    view = PaymentReceiptFinderView(controller)
    return view
```

Em `src/main/routes/refund_routes.py`, **antes** de `@refund_routes.get("/{refund_id}")`:

```python
@refund_routes.get("/{refund_id}/payment-receipt", response_class=Response)
async def get_payment_receipt(
    refund_id: int,
    token_info: dict = Depends(get_current_user),
):
    http_request = HttpRequest(path_params={"refund_id": refund_id}, token_info=token_info)
    view = payment_receipt_finder_composer()
    response = await view.handle(http_request)
    return Response(
        content=response.body["content"],
        media_type=response.body["media_type"],
        status_code=response.status_code,
    )
```

- [ ] **Step 8: Rodar suíte e lint**

Run: `.venv/bin/python3 -m pytest && .venv/bin/python3 -m pylint src`
Expected: tudo verde; `10.00/10`.

- [ ] **Step 9: Commit**

```bash
git add src/
git commit -m "feat: serve the payment receipt to the owner or an admin"
```

---

### Task 8: Histórico de revisões

**Files:**
- Modify: `src/models/repositories/refund_reviews_repository.py` (+`_test`), sua interface
- Create: `src/controllers/refund_review_lister_controller.py` (+`_test`), interface, view, composer
- Modify: `src/main/routes/refund_routes.py`

**Interfaces:**
- Consumes: `RefundsRepositoryInterface.select_refund_by_id` (guarda de autorização).
- Produces: `RefundReviewsReaderRepository.select_by_refund_id(refund_id) -> list[dict]`, com as chaves `from_status`, `to_status`, `reason`, `created_at`, `reviewer_id`, `reviewer_name`; controller `async def list(self, refund_id: int, user_id: int, role: str) -> dict`; rota `GET /refunds/{refund_id}/reviews`.

- [ ] **Step 1: Escrever o teste do repositório**

Acrescente a `src/models/repositories/refund_reviews_repository_test.py` (crie o arquivo se não existir, com os imports do padrão):

```python
# The reader opens its own session (via mock_connection from conftest.py),
# unlike RefundReviewsRepository above, which is handed one by the UnitOfWork.
@pytest.mark.asyncio
async def test_select_by_refund_id_returns_every_field_the_timeline_needs(
    mock_db, mock_connection
):
    row = MagicMock()
    row._mapping = {  # pylint: disable=protected-access
        "from_status": "pending",
        "to_status": "approved",
        "reason": None,
        "created_at": datetime(2026, 7, 30, 10, 0, 0),
        "reviewer_id": 1,
        "reviewer_name": "Gabriel",
    }
    result = MagicMock()
    result.fetchall = MagicMock(return_value=[row])
    mock_db.session.execute = AsyncMock(return_value=result)
    repository = RefundReviewsReaderRepository(mock_connection)

    reviews = await repository.select_by_refund_id(1)

    # These six keys are exactly what RefundReviewListerController.__serialize
    # reads. Asserting only "a query ran" would let a SELECT that drops or
    # renames a column pass here and fail at runtime — reviewer_name in
    # particular comes from the join, not from refund_reviews.
    assert set(reviews[0]) == {
        "from_status",
        "to_status",
        "reason",
        "created_at",
        "reviewer_id",
        "reviewer_name",
    }
    assert reviews[0]["reviewer_name"] == "Gabriel"
```

Imports necessários no arquivo de teste: `from datetime import datetime` e
`from unittest.mock import AsyncMock, MagicMock`.

O `mock_connection` vem do `conftest.py` daquele diretório e depende de um
`mock_db` definido no próprio arquivo de teste — siga como os outros testes de
repositório já fazem.

**A ordenação não é verificável aqui:** ela vive no `ORDER BY` do SQL, e a
sessão está mockada. Ela é conferida ponta a ponta na Task 12, cenário 18.

- [ ] **Step 2: Implementar o método numa classe de leitura própria**

`RefundReviewsRepository` recebe uma `AsyncSession` porque o `UnitOfWork` a
injeta, e é commit-free de propósito. Esta leitura **não tem transação a
compartilhar**, então não cabe nela.

A saída não é inventar mecanismo novo: o projeto **já** tem exatamente essa
divisão — `RefundStatusRepository` é injetada por sessão e escreve dentro da
transação, enquanto `RefundsRepository` abre a própria sessão e lê. Siga o
mesmo par. Acrescente ao fim de `src/models/repositories/refund_reviews_repository.py`
uma segunda classe:

```python
class RefundReviewsReaderRepository(RefundReviewsReaderRepositoryInterface):
    # Sibling of RefundReviewsRepository above, split by transaction ownership
    # rather than by table: that one is session-injected because the UnitOfWork
    # drives its writes, this one opens its own session because a standalone
    # read has no transaction to join. Same split as
    # RefundStatusRepository (injected) vs RefundsRepository (own session).
    def __init__(self, db_connection) -> None:
        self.__db_connection = db_connection

    async def select_by_refund_id(self, refund_id: int) -> list[dict]:
        async with self.__db_connection.connect() as session:
            # Joins Users because the timeline shows WHO decided, and the
            # reviewer's name is not on refund_reviews.
            query = (
                select(
                    RefundReviews.c.from_status,
                    RefundReviews.c.to_status,
                    RefundReviews.c.reason,
                    RefundReviews.c.created_at,
                    Users.c.id.label("reviewer_id"),
                    Users.c.name.label("reviewer_name"),
                )
                .select_from(
                    RefundReviews.join(Users, RefundReviews.c.reviewer_id == Users.c.id)
                )
                # Chronological, with id as the tie-breaker: two decisions can
                # share a created_at, and a timeline that reorders itself
                # between requests is worse than one that is merely coarse.
                .order_by(RefundReviews.c.created_at.asc(), RefundReviews.c.id.asc())
                .where(RefundReviews.c.refund_id == refund_id)
            )
            rows = (await session.execute(query)).fetchall()
            return [dict(row._mapping) for row in rows]  # pylint: disable=protected-access
```

Acrescente os imports `select`, `Users` (de `src.models.entities.users`) e a
interface nova `RefundReviewsReaderRepositoryInterface`, em
`src/models/repositories/interfaces/refund_reviews_reader_repository_interface.py`:

```python
from abc import ABC, abstractmethod


class RefundReviewsReaderRepositoryInterface(ABC):

    @abstractmethod
    async def select_by_refund_id(self, refund_id: int) -> list[dict]:
        pass
```

**Não altere `RefundReviewsRepository`** — o `UnitOfWork` depende da assinatura
atual dela.

- [ ] **Step 3: Escrever os testes do controller**

Crie `src/controllers/refund_review_lister_controller_test.py`:

```python
# pylint: disable=w0621
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock
import pytest
from src.errors.types.http_not_found_error import HttpNotFoundError
from .refund_review_lister_controller import RefundReviewListerController


def build_controller(refund, reviews):
    refunds_repository = MagicMock()
    refunds_repository.select_refund_by_id = AsyncMock(return_value=refund)
    reviews_repository = MagicMock()
    reviews_repository.select_by_refund_id = AsyncMock(return_value=reviews)
    return RefundReviewListerController(refunds_repository, reviews_repository)


@pytest.fixture
def refund():
    return {"id": 1, "status": "rejected", "user": {"id": 7, "name": "Ana", "avatar_filename": None}}


@pytest.fixture
def review_rows():
    # A rejection with a real reason, not a fixture of all-nulls. `reason` is
    # the field this endpoint exists to expose — it was write-only until this
    # cycle — and a null-only fixture cannot tell "passed through correctly"
    # from "dropped and defaulted to None".
    return [
        {
            "from_status": "pending",
            "to_status": "rejected",
            "reason": "Comprovante ilegível",
            "created_at": datetime(2026, 7, 30, 10, 0, 0),
            "reviewer_id": 1,
            "reviewer_name": "Gabriel",
        }
    ]


# Closing the loop this cycle exists for: the requester reads why their refund
# was rejected, and who decided.
@pytest.mark.asyncio
async def test_owner_reads_their_own_history(refund, review_rows):
    controller = build_controller(refund, review_rows)

    response = await controller.list(refund_id=1, user_id=7, role="standard")

    assert response["count"] == 1
    # Assert the WHOLE serialized entry, not selected keys. Checking only
    # reviewer and created_at would let a serializer that swapped from_status
    # with to_status — or dropped `reason` altogether — pass the suite.
    assert response["attributes"][0] == {
        "from_status": "pending",
        "to_status": "rejected",
        "reason": "Comprovante ilegível",
        "reviewer": {"id": 1, "name": "Gabriel"},
        "created_at": "2026-07-30T10:00:00",
    }


@pytest.mark.asyncio
async def test_admin_reads_someone_elses_history(refund, review_rows):
    controller = build_controller(refund, review_rows)

    response = await controller.list(refund_id=1, user_id=99, role="admin")

    assert response["count"] == 1


# A refund nobody has decided yet is not an error: it has an empty history.
@pytest.mark.asyncio
async def test_a_never_decided_refund_has_an_empty_history(refund):
    controller = build_controller({**refund, "status": "pending"}, [])

    response = await controller.list(refund_id=1, user_id=7, role="standard")

    assert response["count"] == 0
    assert response["attributes"] == []


@pytest.mark.asyncio
async def test_someone_elses_refund_is_not_found(refund, review_rows):
    controller = build_controller(refund, review_rows)

    with pytest.raises(HttpNotFoundError, match="Refund not found"):
        await controller.list(refund_id=1, user_id=99, role="standard")


@pytest.mark.asyncio
async def test_unknown_refund_is_not_found():
    controller = build_controller(None, [])

    with pytest.raises(HttpNotFoundError, match="Refund not found"):
        await controller.list(refund_id=1, user_id=7, role="standard")
```

- [ ] **Step 4: Rodar e ver falhar**

Run: `.venv/bin/python3 -m pytest src/controllers/refund_review_lister_controller_test.py -v`
Expected: FAIL — módulo não encontrado.

- [ ] **Step 5: Escrever interface e controller**

Interface em `src/controllers/interfaces/refund_review_lister_controller_interface.py`:

```python
from abc import ABC, abstractmethod


class RefundReviewListerControllerInterface(ABC):

    @abstractmethod
    async def list(self, refund_id: int, user_id: int, role: str) -> dict:
        pass
```

Controller em `src/controllers/refund_review_lister_controller.py`:

```python
# pylint: disable=duplicate-code
# Shares the "404 for both missing and not-yours" guard with the finder
# controllers; the rule is deliberately identical.
from src.models.repositories.interfaces.refunds_repository_interface import RefundsRepositoryInterface
from src.models.repositories.interfaces.refund_reviews_reader_repository_interface import (
    RefundReviewsReaderRepositoryInterface,
)
from src.controllers.interfaces.refund_review_lister_controller_interface import (
    RefundReviewListerControllerInterface,
)
from src.errors.types.http_not_found_error import HttpNotFoundError


class RefundReviewListerController(RefundReviewListerControllerInterface):
    def __init__(
        self,
        refunds_repository: RefundsRepositoryInterface,
        reviews_repository: RefundReviewsReaderRepositoryInterface,
    ) -> None:
        self.__refunds_repository = refunds_repository
        self.__reviews_repository = reviews_repository

    async def list(self, refund_id: int, user_id: int, role: str) -> dict:
        # Authorization is about the REFUND, not the reviews: whoever may see
        # the refund may see how it was decided.
        refund = await self.__refunds_repository.select_refund_by_id(refund_id)

        if not refund or (role != "admin" and refund["user"]["id"] != user_id):
            raise HttpNotFoundError("Refund not found")

        reviews = await self.__reviews_repository.select_by_refund_id(refund_id)

        return {
            "type": "RefundReview",
            "count": len(reviews),
            "attributes": [self.__serialize(review) for review in reviews],
        }

    def __serialize(self, review: dict) -> dict:
        created_at = review.get("created_at")
        return {
            "from_status": review["from_status"],
            "to_status": review["to_status"],
            "reason": review["reason"],
            "reviewer": {"id": review["reviewer_id"], "name": review["reviewer_name"]},
            "created_at": created_at.isoformat() if created_at else None,
        }
```

- [ ] **Step 6: Escrever view, composer e rota**

View em `src/views/refund_review_lister_view.py`, no padrão de `RefundFinderView`, chamando `controller.list(refund_id, user_id, role)` e devolvendo `HttpResponse(body=response, status_code=200)`.

Composer em `src/main/composer/refund_review_lister_composer.py`:

```python
from src.models.settings.database_connection_handler import database_connection_handler
from src.models.repositories.refunds_repository import RefundsRepository
from src.models.repositories.refund_reviews_repository import RefundReviewsReaderRepository
from src.controllers.refund_review_lister_controller import RefundReviewListerController
from src.views.refund_review_lister_view import RefundReviewListerView


def refund_review_lister_composer():
    refunds_repository = RefundsRepository(database_connection_handler)
    # The READER sibling, not RefundReviewsRepository: that one takes an
    # AsyncSession from the UnitOfWork, this one takes the handler and opens
    # its own.
    reviews_repository = RefundReviewsReaderRepository(database_connection_handler)
    controller = RefundReviewListerController(refunds_repository, reviews_repository)
    view = RefundReviewListerView(controller)
    return view
```

Rota em `refund_routes.py`, antes de `@refund_routes.get("/{refund_id}")`:

```python
@refund_routes.get("/{refund_id}/reviews")
async def list_refund_reviews(refund_id: int, token_info: dict = Depends(get_current_user)):
    http_request = HttpRequest(path_params={"refund_id": refund_id}, token_info=token_info)
    view = refund_review_lister_composer()
    response = await view.handle(http_request)
    return JSONResponse(content=response.body, status_code=response.status_code)
```

- [ ] **Step 7: Rodar suíte e lint**

Run: `.venv/bin/python3 -m pytest && .venv/bin/python3 -m pylint src`
Expected: tudo verde; `10.00/10`.

- [ ] **Step 8: Commit**

```bash
git add src/
git commit -m "feat: expose the review history of a refund"
```

---

### Task 9: Estatísticas por usuário

**Files:**
- Modify: `src/models/repositories/refunds_repository.py` (+`_test`), sua interface
- Create: `src/controllers/refund_stats_finder_controller.py` (+`_test`), interface, view, composer
- Modify: `src/main/routes/user_routes.py`

**Interfaces:**
- Consumes: nada de tasks anteriores.
- Produces: `RefundsRepository.count_by_status(user_id: int) -> dict` com `{status: {"count": int, "amount_in_cents": int}}`; rota `GET /users/{user_id}/refund-stats`.

- [ ] **Step 1: Escrever o teste do controller**

Crie `src/controllers/refund_stats_finder_controller_test.py`:

```python
# pylint: disable=w0621
from unittest.mock import AsyncMock, MagicMock
import pytest
from src.errors.types.http_not_found_error import HttpNotFoundError
from .refund_stats_finder_controller import RefundStatsFinderController


def build_controller(totals):
    repository = MagicMock()
    repository.count_by_status = AsyncMock(return_value=totals)
    return RefundStatsFinderController(repository)


# Every status is present even when the user has none of it. Dropping empty
# keys would force every client to handle a missing key.
@pytest.mark.asyncio
async def test_statuses_with_no_refunds_come_back_as_zeros():
    controller = build_controller({"approved": {"count": 2, "amount_in_cents": 5000}})

    response = await controller.find(target_user_id=3, user_id=3, role="standard")

    assert response["by_status"] == {
        "pending": {"count": 0, "amount_in_cents": 0},
        "approved": {"count": 2, "amount_in_cents": 5000},
        "paid": {"count": 0, "amount_in_cents": 0},
        "rejected": {"count": 0, "amount_in_cents": 0},
    }
    assert response["user_id"] == 3


# There is no total, of count or of amount: summing across statuses would add a
# forecast to a liability to a realised expense. Clients derive what they need.
@pytest.mark.asyncio
async def test_the_response_publishes_no_cross_status_total():
    controller = build_controller({})

    response = await controller.find(target_user_id=3, user_id=3, role="standard")

    assert "total" not in response
    assert set(response.keys()) == {"type", "user_id", "by_status"}


@pytest.mark.asyncio
async def test_admin_reads_someone_elses_stats():
    controller = build_controller({})

    response = await controller.find(target_user_id=3, user_id=99, role="admin")

    assert response["user_id"] == 3


# 404 rather than 403, for the same anti-enumeration reason as BR-013: a 403
# would confirm that user id exists.
@pytest.mark.asyncio
async def test_a_standard_user_cannot_read_someone_elses_stats():
    controller = build_controller({})

    with pytest.raises(HttpNotFoundError):
        await controller.find(target_user_id=3, user_id=7, role="standard")
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `.venv/bin/python3 -m pytest src/controllers/refund_stats_finder_controller_test.py -v`
Expected: FAIL — módulo não encontrado.

- [ ] **Step 3: Escrever interface e controller**

Interface em `src/controllers/interfaces/refund_stats_finder_controller_interface.py`:

```python
from abc import ABC, abstractmethod


class RefundStatsFinderControllerInterface(ABC):

    @abstractmethod
    async def find(self, target_user_id: int, user_id: int, role: str) -> dict:
        pass
```

Controller em `src/controllers/refund_stats_finder_controller.py`:

```python
from src.models.repositories.interfaces.refunds_repository_interface import RefundsRepositoryInterface
from src.controllers.interfaces.refund_stats_finder_controller_interface import (
    RefundStatsFinderControllerInterface,
)
from src.errors.types.http_not_found_error import HttpNotFoundError

# The response always carries these four keys, in this order, even when the
# user has no refund in a given status.
ALL_STATUSES = ("pending", "approved", "paid", "rejected")


class RefundStatsFinderController(RefundStatsFinderControllerInterface):
    def __init__(self, refunds_repository: RefundsRepositoryInterface) -> None:
        self.__refunds_repository = refunds_repository

    async def find(self, target_user_id: int, user_id: int, role: str) -> dict:
        # 404, not 403: a 403 would confirm the user id is real, the same
        # anti-enumeration reasoning behind BR-013.
        if role != "admin" and target_user_id != user_id:
            raise HttpNotFoundError("User not found")

        totals = await self.__refunds_repository.count_by_status(target_user_id)

        return {
            "type": "RefundStats",
            "user_id": target_user_id,
            # No total, of count or of amount. Summing across statuses would add
            # a forecast (pending) to a liability (approved) to a realised
            # expense (paid) to nothing (rejected) — the defect that made the
            # Home's "Total" card meaningless. Rates and averages are divisions
            # of these numbers and belong to the client.
            "by_status": {
                status: totals.get(status, {"count": 0, "amount_in_cents": 0})
                for status in ALL_STATUSES
            },
        }
```

- [ ] **Step 4: Rodar e ver passar**

Run: `.venv/bin/python3 -m pytest src/controllers/refund_stats_finder_controller_test.py -v`
Expected: 5 passed.

- [ ] **Step 5: Implementar `count_by_status`**

Em `src/models/repositories/refunds_repository.py`:

```python
    async def count_by_status(self, user_id: int) -> dict:
        async with self.__db_connection.connect() as session:
            # One round trip for every status. SUM over an empty group cannot
            # happen here (a group only exists if it has rows), but `or 0`
            # guards the NULL that a all-NULL column would produce.
            query = (
                select(
                    Refunds.c.status,
                    func.count(),  # pylint: disable=not-callable
                    func.sum(Refunds.c.amount_in_cents),
                )
                .select_from(Refunds)
                .where(Refunds.c.user_id == user_id)
                .group_by(Refunds.c.status)
            )
            rows = (await session.execute(query)).fetchall()

            return {
                status: {"count": count, "amount_in_cents": amount or 0}
                for status, count, amount in rows
            }
```

Declare na interface: `async def count_by_status(self, user_id: int) -> dict`.

Acrescente um teste em `refunds_repository_test.py` provando que a query é executada e que o dicionário é montado a partir das linhas.

- [ ] **Step 6: Escrever view, composer e rota**

View em `src/views/refund_stats_finder_view.py`, no padrão das demais, lendo `http_request.path_params["user_id"]` como `target_user_id` e `http_request.token_info` para `user_id`/`role`.

Composer em `src/main/composer/refund_stats_finder_composer.py`, injetando `RefundsRepository(database_connection_handler)`.

Rota em `src/main/routes/user_routes.py`:

```python
@user_routes.get("/{user_id}/refund-stats")
async def get_refund_stats(user_id: int, token_info: dict = Depends(get_current_user)):
    http_request = HttpRequest(path_params={"user_id": user_id}, token_info=token_info)
    view = refund_stats_finder_composer()
    response = await view.handle(http_request)
    return JSONResponse(content=response.body, status_code=response.status_code)
```

- [ ] **Step 7: Rodar suíte e lint**

Run: `.venv/bin/python3 -m pytest && .venv/bin/python3 -m pylint src`
Expected: tudo verde; `10.00/10`.

- [ ] **Step 8: Commit**

```bash
git add src/
git commit -m "feat: expose per-user refund statistics by status"
```

---

### Task 10: Filtro `user_id` na listagem

**Files:**
- Modify: `src/main/routes/refund_routes.py`
- Modify: `src/controllers/refund_lister_controller.py` (+`_test`)

**Interfaces:**
- Consumes: `RefundsRepository.select_refunds(..., user_id=...)`, que **já aceita o parâmetro**.
- Produces: `GET /refunds?user_id=` filtrando para admin.

- [ ] **Step 1: Escrever os testes que falham**

Acrescente a `src/controllers/refund_lister_controller_test.py`:

```python
# The repository already accepted user_id; only the controller decided it, and
# the route never exposed it. An admin can now scope the list to one requester.
@pytest.mark.asyncio
async def test_admin_can_filter_the_list_by_requester():
    repository = MagicMock()
    repository.select_refunds = AsyncMock(return_value=([], 0, 0))
    controller = RefundListerController(repository)

    await controller.list(page=1, per_page=10, user_id=9, role="admin", filter_user_id=3)

    assert repository.select_refunds.await_args.kwargs["user_id"] == 3


# A standard user is already locked to their own refunds, so the parameter is
# ignored rather than rejected: there is nothing to leak and no new error path.
@pytest.mark.asyncio
async def test_the_filter_is_ignored_for_a_standard_user():
    repository = MagicMock()
    repository.select_refunds = AsyncMock(return_value=([], 0, 0))
    controller = RefundListerController(repository)

    await controller.list(page=1, per_page=10, user_id=9, role="standard", filter_user_id=3)

    assert repository.select_refunds.await_args.kwargs["user_id"] == 9
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `.venv/bin/python3 -m pytest src/controllers/refund_lister_controller_test.py -v`
Expected: FAIL — `list()` não aceita `filter_user_id`.

- [ ] **Step 3: Implementar**

Em `src/controllers/refund_lister_controller.py`, acrescente o parâmetro `filter_user_id: Optional[int] = None` à assinatura de `list` e substitua a linha da regra de autorização:

```python
        # Authorization rule lives here, not in the repository: an admin can see
        # everyone's refunds, a standard user only their own. An admin may also
        # narrow the list to one requester; for a standard user that parameter is
        # IGNORED, not rejected — they are already locked to themselves, so there
        # is nothing to leak and no new error path to document.
        filter_user_id = filter_user_id if role == "admin" else user_id
```

Atualize a chamada a `select_refunds` para passar `user_id=filter_user_id`, e declare o parâmetro na interface do controller.

- [ ] **Step 4: Expor na rota**

Em `src/main/routes/refund_routes.py`, na assinatura de `list_refunds`:

```python
    # Typed as int so FastAPI's native validation rejects garbage, matching how
    # page and per_page already behave. Unlike `status`, there is no whitelist
    # to express, so this project's 422 envelope buys nothing here.
    user_id: Optional[int] = Query(None),
```

E acrescente `"user_id": user_id` ao dicionário `query` do `HttpRequest`. Propague no `RefundListerView` como `filter_user_id`.

- [ ] **Step 5: Rodar suíte e lint**

Run: `.venv/bin/python3 -m pytest && .venv/bin/python3 -m pylint src`
Expected: tudo verde; `10.00/10`.

- [ ] **Step 6: Commit**

```bash
git add src/
git commit -m "feat: let an admin scope the refund list to one requester"
```

---

### Task 11: Documentação canônica

**Files:**
- Create: `docs/use-cases/UC-012-pay-refund.md`, `UC-013-list-refund-reviews.md`, `UC-014-user-refund-stats.md`
- Modify: `docs/use-cases/UC-004-list-refunds.md`, `UC-007-review-refund.md`, `docs/business-rules.md`, `docs/domain-model.md`, `docs/decisions/ADR-003-local-receipt-storage.md`, `docs/index.md`, `src/models/entities/refund_reviews.py`

**Interfaces:**
- Consumes: comportamento implementado nas Tasks 1-10.
- Produces: documentação canônica coerente com o código.

- [ ] **Step 1: Escrever os três casos de uso**

Siga a estrutura dos existentes: ator, objetivo, pré-condições, fluxo principal, corpo/parâmetros, ordem das checagens (quando houver), formato da resposta, tabela de códigos, fluxos alternativos, pós-condições, regras relacionadas, evidências.

UC-012 deve registrar a **ordem das checagens** e a razão: nenhum acesso ao banco antes da checagem de papel.

- [ ] **Step 2: Emendar UC-004 e UC-007**

UC-004: parâmetro `user_id`, com a nota de que é ignorado para `standard`.
UC-007: `paid` é terminal, então `PATCH /status` sobre solicitação paga responde `422`.

- [ ] **Step 3: Escrever e emendar as regras**

Numeração conferida: `business-rules.md` vai até **BR-021**.

- **BR-022 (nova)** — comprovante de pagamento obrigatório, com a invariante `status == "paid"` ⟺ existe comprovante.
- **BR-009 emendada** — formato e tamanho valem para os dois comprovantes.
- **BR-016 estendida** — nenhum admin paga a própria solicitação.
- **BR-017 emendada** — `paid` é terminal.
- **BR-020 emendada** — acesso ao comprovante cobre o de pagamento.

Cada regra precisa da seção **Evidências** apontando para arquivo e teste.

- [ ] **Step 4: Atualizar modelo, ADR e índice**

`domain-model.md`: quarto status, `payment_filename`, e a nota de que `refund_reviews` virou log de transição.
`ADR-003`: emenda registrando que agora são três diretórios.
`index.md`: os três casos de uso novos.
`src/models/entities/refund_reviews.py`: comentário registrando que a tabela guarda transições, não só revisões.

- [ ] **Step 5: Commit**

```bash
git add docs/ src/models/entities/refund_reviews.py
git commit -m "docs: document payment, review history and stats"
```

---

### Task 12: Verificação ponta a ponta e fechamento

**Files:**
- Modify: `docs/plans/current-state.md`, `docs/learning-path-progress.md`

**Interfaces:**
- Consumes: tudo.
- Produces: ciclo encerrado conforme o `learning-path-workflow.md`.

- [ ] **Step 1: Subir a API e preparar os dados**

Suba com `.venv/bin/python3 -m uvicorn src.main.server.server:app --port 3333`
— **não** `run:app`, que não existe. Use os usuários de teste que já existem
(`admin.validacao@example.com`, `validacao.visual@example.com`) ou crie novos
com `init/promote_admin.py`.

- [ ] **Step 2: Percorrer os cenários e anotar o código de cada um**

| # | Cenário | Esperado |
|---|---|---|
| 1 | `POST /refunds/{id}/payment` sem token | `401` |
| 2 | Como `standard`, id real | `403` |
| 3 | Como `standard`, id inventado | `403` **idêntico** ao anterior |
| 4 | Como admin, id inexistente | `404` |
| 5 | Como admin, solicitação própria | `403` |
| 6 | Como admin, solicitação `pending` | `422` |
| 7 | Como admin, solicitação `approved`, sem arquivo | `422` |
| 8 | Como admin, arquivo `.exe` | `422` |
| 9 | Como admin, arquivo > 4MB | `422` |
| 10 | Como admin, `approved` + PDF válido | `200`, `status: "paid"`, `user` aninhado, sem `filename` |
| 11 | Repetir o pagamento da mesma solicitação | `422` |
| 12 | `PATCH /refunds/{id}/status` numa paga | `422` |
| 13 | `DELETE` numa paga | `404` ou `422`, nunca apaga |
| 14 | `GET /refunds/{id}/payment-receipt` como dono | `200`, bytes |
| 15 | Idem como admin | `200` |
| 16 | Idem como terceiro | `404` |
| 17 | Idem numa solicitação não paga | `404` **idêntico** |
| 18 | `GET /refunds/{id}/reviews` como dono | `200`, com o motivo da rejeição |
| 19 | Idem numa nunca decidida | `200`, `count: 0` |
| 20 | Idem como terceiro | `404` |
| 21 | `GET /users/{id}/refund-stats` como o próprio | `200`, quatro chaves |
| 22 | Idem como admin | `200` |
| 23 | Idem como terceiro | `404` |
| 24 | `GET /refunds?user_id=X` como admin | só as de X |
| 25 | Idem como `standard` | as próprias, parâmetro ignorado |

- [ ] **Step 3: Conferir o disco**

```bash
ls uploads/payment_receipts/
```

Esperado: um arquivo por pagamento bem-sucedido, e **nenhum** dos cenários 6-9 e 11 (as guardas rodam antes da gravação, e a corrida compensa).

- [ ] **Step 4: Reproduzir o cenário de contenção do pool**

Dispare três `PATCH /refunds/{id}/status` concorrentes na mesma solicitação. Antes deste ciclo, o terceiro request tomaria 500 depois de 30s. Anote o comportamento observado — é a única evidência possível para o ajuste de pool.

- [ ] **Step 5: Verificação final**

```bash
.venv/bin/python3 -m pytest
.venv/bin/python3 -m pylint src
```

Anote os números.

- [ ] **Step 6: Atualizar o diário e o estado**

`learning-path-progress.md`: motivo do ciclo, estado anterior com trechos, limitação encontrada, comparação, estado ajustado, arquivos, verificações e o que lembrar.

`current-state.md`: ciclo concluído, próximo ciclo (a UI de revisão), e as pendências novas — Item 21 agora em dois lugares, o ajuste de pool sem teste comportamental, e a quarta variante de badge que o frontend vai precisar.

- [ ] **Step 7: Commit**

```bash
git add docs/
git commit -m "docs: close the payment, history and stats cycle"
```

---

## Auto-revisão do plano

**Cobertura da spec:** as seis seções da spec têm task. Modelo de domínio → Task 1; pool → Task 2; concorrência → Tasks 3 e 5; as cinco rotas → Tasks 5-10; testes → embutidos em cada task; documentação → Task 11; verificação → Task 12.

**Um ponto que a primeira versão deste plano deixou em aberto e foi fechado:**
onde vive a leitura do histórico. `RefundReviewsRepository` recebe uma
`AsyncSession` porque o `UnitOfWork` a injeta, e a leitura nova não tem
transação a compartilhar. A resposta não é mecanismo novo — é o par que o
projeto já usa: `RefundStatusRepository` (injetada, escreve na transação) ao
lado de `RefundsRepository` (abre a própria sessão, lê). A Task 8 cria
`RefundReviewsReaderRepository` seguindo exatamente essa divisão, **por posse
de transação, não por tabela**.

**Consistência de tipos:** `mark_as_paid` devolve `int` (rowcount) e é
consumido como `affected == 0`; `count_by_status` devolve `dict` de
`{status: {"count", "amount_in_cents"}}` e é consumido com `.get(status, {...})`;
`select_by_refund_id` devolve `list[dict]` com as chaves `from_status`,
`to_status`, `reason`, `created_at`, `reviewer_id`, `reviewer_name`, exatamente
as lidas em `__serialize`.

**Nomes conferidos contra o código real:** `select_refund_by_id` devolve a forma
com `user` aninhado (é `__to_refund` que a monta, e a Task 7 acrescenta
`payment_filename` ali); `select_for_update` devolve a forma achatada e **não é
usada neste ciclo**; `delete_refund` já usa o `UPDATE`/`DELETE` condicional com
`rowcount` que a Task 3 espelha.
