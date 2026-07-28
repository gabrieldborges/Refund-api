# Workflow de aprovação (backend) — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Dar às solicitações de reembolso um fluxo de decisão — `status`, aprovação/rejeição por admin e histórico auditável — sobre uma transação única.

**Architecture:** Preserva a Clean Architecture existente (rota → view → validator → controller → repository). Duas novidades: o schema passa a ser governado por migrations do Alembic em vez de `metadata.create_all`, e o caso de uso novo escreve através de um Unit of Work, que delimita uma transação abrangendo `UPDATE refunds` e `INSERT refund_reviews`. Os CRUDs existentes não são refatorados.

**Tech Stack:** Python 3.9, FastAPI, SQLAlchemy 2.0 (Core, async), asyncpg, PostgreSQL (Neon), Alembic (novo), pytest + pytest-asyncio, pylint.

**Spec:** [`../specs/2026-07-28-refund-approval-workflow-design.md`](../specs/2026-07-28-refund-approval-workflow-design.md)

## Global Constraints

- **Python 3.9.** Use `Optional[X]`, **nunca** `X | None` (sintaxe de união só existe a partir do 3.10). `list[dict]` e `tuple[...]` são válidos.
- **Todo arquivo novo com lógica ganha um `_test.py` ao lado**, no mesmo diretório — nunca uma pasta `tests/` separada (`AGENTS.md`). **Exceção, conforme a convenção vigente:** composers (`src/main/composer/`) são fiação de injeção de dependência sem lógica e não têm teste — nenhum dos 6 existentes tem; scripts operacionais de `init/` também não.
- **Testes assíncronos exigem `@pytest.mark.asyncio` explícito.** Não há arquivo de configuração do pytest; o modo é estrito.
- **Comentários em inglês**, curtos e descritivos, explicando o cenário ou a razão — não o óbvio (`AGENTS.md`).
- **`pylint src` deve terminar em 10.00/10.** É o patamar atual; qualquer queda é regressão.
- **`pytest` deve terminar 100% verde.** Baseline atual: 73 testes.
- **Nunca versionar credenciais.** A `DATABASE_URL` vive no `.env`; o `alembic.ini` não pode conter URL de banco.
- **Atributos privados usam prefixo `__`** e são injetados pelo construtor, como em todas as camadas existentes.
- Rodar `pytest` e `pylint src` ao final de **cada** task, antes do commit.

---

### Task 1: Alembic assume o schema

Instala e configura o Alembic, cria a migration de baseline representando o schema que já existe, reconcilia o banco atual via `stamp` e remove o `metadata.create_all` do lifespan. Nenhuma mudança de comportamento — só a troca de quem governa o schema.

**Files:**
- Create: `alembic.ini`
- Create: `alembic/env.py`, `alembic/script.py.mako`, `alembic/versions/` (gerados pelo `alembic init`)
- Create: `alembic/versions/<hash>_baseline_users_and_refunds.py`
- Modify: `src/main/server/server.py`
- Modify: `requirements.txt`
- Modify: `README.md`
- Modify: `.gitignore` (nada a ignorar aqui; conferir que `alembic/versions/*.py` **não** está ignorado)

**Interfaces:**
- Consumes: `src/models/settings/metadata.py` (`metadata`), `src/configs/global_config.py` (`database_info`)
- Produces: comando `alembic upgrade head` como forma oficial de criar/atualizar o schema; a revisão de baseline, que será a `down_revision` da Task 2

- [ ] **Step 1: Instalar o Alembic e fixar a versão**

```bash
.venv/bin/pip install alembic
.venv/bin/pip freeze | grep -i "^alembic\|^Mako\|^MarkupSafe" >> requirements.txt
```

Depois **ordene** o `requirements.txt` alfabeticamente para manter o padrão do arquivo (ele está ordenado hoje).

- [ ] **Step 2: Inicializar o Alembic no template assíncrono**

```bash
.venv/bin/alembic init -t async alembic
```

O template `async` é obrigatório: o projeto usa `create_async_engine` com `asyncpg`, e o template padrão (síncrono) falha ao conectar.

- [ ] **Step 3: Apontar o Alembic para a metadata e para a `DATABASE_URL` do `.env`**

Edite `alembic/env.py`. Logo abaixo de `config = context.config`, insira:

```python
from src.models.settings.metadata import metadata
from src.models.entities import users, refunds  # pylint: disable=unused-import
from src.configs.global_config import database_info

# The URL comes from the .env at runtime, never from alembic.ini — that file is
# versioned and must not carry credentials.
config.set_main_option("sqlalchemy.url", str(database_info["DATABASE_URL"]))
```

E troque a linha `target_metadata = None` por:

```python
# Importing the entity modules above is what populates `metadata` with the
# tables; without them autogenerate would see an empty schema and try to drop
# every table in the database.
target_metadata = metadata
```

- [ ] **Step 4: Remover a URL do `alembic.ini`**

Em `alembic.ini`, deixe a chave vazia:

```ini
sqlalchemy.url =
```

Confirme com `grep -i "postgres\|password" alembic.ini` — a saída deve ser vazia.

- [ ] **Step 5: Gerar a migration de baseline**

```bash
.venv/bin/alembic revision --autogenerate -m "baseline users and refunds"
```

- [ ] **Step 6: Ler o arquivo gerado e conferir**

Abra `alembic/versions/<hash>_baseline_users_and_refunds.py`. O `upgrade()` deve conter `op.create_table("users", ...)` e `op.create_table("refunds", ...)`, com as colunas exatamente como em `src/models/entities/`. O `downgrade()` deve derrubar as duas.

**Se aparecer qualquer `op.drop_table` no `upgrade()`, pare:** significa que as entidades não foram importadas no `env.py` e o autogenerate concluiu que as tabelas do banco são sobra. Volte ao Step 3.

- [ ] **Step 7: Reconciliar o banco existente com `stamp`**

```bash
.venv/bin/alembic stamp head
```

Isto grava a revisão na tabela `alembic_version` **sem executar a migration** — as tabelas já existem, e rodá-la falharia com "already exists".

- [ ] **Step 8: Verificar o estado**

```bash
.venv/bin/alembic current
```
Esperado: o hash da baseline, seguido de `(head)`.

```bash
.venv/bin/alembic upgrade head
```
Esperado: nenhuma operação — o banco já está no head. Este é o comportamento que torna `upgrade head` seguro de rodar sempre.

- [ ] **Step 9: Remover o `create_all` do lifespan**

Em `src/main/server/server.py`, substitua o lifespan por:

```python
@asynccontextmanager
async def lifespan(_app: FastAPI):
    # The schema is owned by Alembic migrations (`alembic upgrade head`), not by
    # the application boot. Keeping metadata.create_all here would silently mask
    # a migration that was never applied: it creates missing tables and ignores
    # missing columns, so the app would start against a half-updated schema.
    yield
```

Remova os imports que ficaram sem uso: `engine` e `metadata`. **Mantenha** `from src.models.entities import users, refunds` — ele ainda registra as tabelas na metadata para o resto da aplicação.

- [ ] **Step 10: Subir o servidor e confirmar que ainda funciona**

```bash
.venv/bin/python run.py
```
Em outro terminal:
```bash
curl -s -o /dev/null -w "%{http_code}\n" http://localhost:3333/health
```
Esperado: `200`.

- [ ] **Step 11: Atualizar o README**

Na seção "Rodando localmente", substitua o parágrafo que descreve o `metadata.create_all` por:

```markdown
Antes de subir o servidor pela primeira vez, aplique as migrations:

```bash
alembic upgrade head
```

O schema do banco é governado pelo Alembic (`alembic/versions/`). Rodar
`alembic upgrade head` é seguro a qualquer momento: ele aplica apenas as
migrations que faltam. O `init/schema.sql` continua existindo só como
referência histórica.
```

- [ ] **Step 12: Rodar a verificação e commitar**

```bash
.venv/bin/python -m pytest -q
.venv/bin/python -m pylint src
git add alembic alembic.ini requirements.txt README.md src/main/server/server.py
git commit -m "feat: put the database schema under alembic migrations"
```

Esperado: 73 testes verdes, pylint 10.00/10. (O diretório `alembic/` fica fora do `pylint src`, que só varre `src`.)

---

### Task 2: Migration do ciclo — `status` e `refund_reviews`

Adiciona a coluna `status` a `refunds` (preenchendo as linhas existentes) e cria a tabela de histórico.

**Files:**
- Create: `src/models/entities/refund_reviews.py`
- Create: `alembic/versions/<hash>_add_refund_status_and_reviews.py`
- Modify: `src/models/entities/refunds.py`
- Modify: `src/main/server/server.py` (importar a entidade nova)
- Modify: `alembic/env.py` (importar a entidade nova)

**Interfaces:**
- Consumes: a revisão de baseline da Task 1 (vira a `down_revision`)
- Produces: `RefundReviews` (`sqlalchemy.Table`) importável de `src.models.entities.refund_reviews`; a coluna `refunds.status`, que as Tasks 4, 7, 9 e 10 leem

- [ ] **Step 1: Criar a entidade do histórico**

`src/models/entities/refund_reviews.py`:

```python
from sqlalchemy import Table, Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.sql import func
from src.models.settings.metadata import metadata

# One row per decision taken on a refund. A refund only gets rows here once it
# has been decided, and a decided refund cannot be deleted (BR-015), so a review
# can never be orphaned — which is why there is no ON DELETE CASCADE.
RefundReviews = Table(
    "refund_reviews",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("refund_id", Integer, ForeignKey("refunds.id"), nullable=False),
    Column("reviewer_id", Integer, ForeignKey("users.id"), nullable=False),
    Column("from_status", String, nullable=False),
    Column("to_status", String, nullable=False),
    # Required only when rejecting (BR-017). The database cannot express a
    # conditional NOT NULL without a CHECK constraint, so the rule lives in
    # refund_reviewer_validator.
    Column("reason", String, nullable=True),
    Column("created_at", DateTime, server_default=func.now()),  # pylint: disable=not-callable
)
```

- [ ] **Step 2: Adicionar a coluna `status` à entidade de refunds**

Em `src/models/entities/refunds.py`, adicione antes de `created_at`:

```python
    # server_default matters beyond new rows: it is what lets the ALTER TABLE in
    # the migration backfill the rows that already exist without violating the
    # NOT NULL constraint.
    Column("status", String, nullable=False, server_default="pending"),
```

- [ ] **Step 3: Registrar a entidade nova nos dois pontos de import**

Em `src/main/server/server.py` e em `alembic/env.py`, troque:

```python
from src.models.entities import users, refunds  # pylint: disable=unused-import
```
por:
```python
from src.models.entities import users, refunds, refund_reviews  # pylint: disable=unused-import
```

- [ ] **Step 4: Gerar a migration**

```bash
.venv/bin/alembic revision --autogenerate -m "add refund status and reviews"
```

- [ ] **Step 5: Ler e ajustar o arquivo gerado**

O `upgrade()` deve conter `op.add_column("refunds", ...)` e `op.create_table("refund_reviews", ...)`.

**Confira o `server_default`:** o autogenerate frequentemente o omite. Se a coluna gerada estiver sem ele, corrija à mão para:

```python
    op.add_column(
        "refunds",
        sa.Column("status", sa.String(), nullable=False, server_default="pending"),
    )
```

Sem `server_default`, o `ALTER TABLE` falha nas 29 linhas existentes com *"column contains null values"*.

Confirme que `downgrade()` tem `op.drop_table("refund_reviews")` **antes** de `op.drop_column("refunds", "status")` — a ordem inversa da criação.

- [ ] **Step 6: Aplicar e verificar o backfill**

```bash
.venv/bin/alembic upgrade head
```

Confirme que as linhas existentes foram preenchidas:

```bash
.venv/bin/python -c "
import asyncio, os, asyncpg
from dotenv import load_dotenv
load_dotenv()
url = os.getenv('DATABASE_URL').replace('postgresql+asyncpg://', 'postgresql://')
async def main():
    c = await asyncpg.connect(url)
    print('por status:', await c.fetch('select status, count(*) from refunds group by status'))
    print('reviews:', await c.fetchval('select count(*) from refund_reviews'))
    await c.close()
asyncio.run(main())
"
```
Esperado: todas as linhas com `status = 'pending'`, e `refund_reviews` com 0 linhas.

- [ ] **Step 7: Verificar que o `downgrade` funciona**

```bash
.venv/bin/alembic downgrade -1
.venv/bin/alembic current      # deve mostrar a baseline
.venv/bin/alembic upgrade head
.venv/bin/alembic current      # de volta ao head
```

Uma migration sem `downgrade` testado é uma migration sem volta. Este é o teste que o Item 18 pede.

> **Limitação conhecida, a registrar no diário:** este teste é **manual**, contra o banco de desenvolvimento. Automatizá-lo exige um PostgreSQL descartável, que é o **Item 19** (PostgreSQL em container) e ainda não existe. Testar migrations em SQLite seria pior que não testar: esconderia justamente as diferenças que o Item 19 existe para expor.

- [ ] **Step 8: Rodar a verificação e commitar**

```bash
.venv/bin/python -m pytest -q
.venv/bin/python -m pylint src
git add src/models/entities alembic/versions src/main/server/server.py alembic/env.py
git commit -m "feat: add refund status column and review history table"
```

---

### Task 3: Erro 403

O projeto só tem tipos de erro para 400, 404 e 422. A spec exige 403, que não existe.

**Files:**
- Create: `src/errors/types/http_forbidden_error.py`
- Modify: `src/errors/error_handler.py`
- Test: `src/errors/error_handler_test.py` (criar se não existir)

**Interfaces:**
- Produces: `HttpForbiddenError(message: str)` com `.status_code == 403`, usado pela Task 7

- [ ] **Step 1: Escrever o teste que falha**

`src/errors/error_handler_test.py`:

```python
import pytest
from fastapi import HTTPException
from src.errors.types.http_forbidden_error import HttpForbiddenError
from .error_handler import error_handler


# A forbidden error must surface as HTTP 403 with its own message, not collapse
# into the generic 500 that error_handler applies to unknown exceptions.
def test_forbidden_error_becomes_a_403_response():
    with pytest.raises(HTTPException) as exception_info:
        error_handler(HttpForbiddenError("Only administrators can review refunds"))

    assert exception_info.value.status_code == 403
    assert exception_info.value.detail == "Only administrators can review refunds"
```

- [ ] **Step 2: Rodar e confirmar que falha**

```bash
.venv/bin/python -m pytest src/errors/error_handler_test.py -v
```
Esperado: `ModuleNotFoundError: No module named 'src.errors.types.http_forbidden_error'`.

- [ ] **Step 3: Criar o tipo de erro**

`src/errors/types/http_forbidden_error.py`:

```python
class HttpForbiddenError(Exception):
    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = 403
        self.error_type = "HTTP_FORBIDDEN"
```

- [ ] **Step 4: Registrar no handler**

Em `src/errors/error_handler.py`, adicione o import e inclua a classe na tupla:

```python
from src.errors.types.http_forbidden_error import HttpForbiddenError
```
```python
    if isinstance(
        error,
        (HttpBadRequestError, HttpForbiddenError, HttpNotFoundError, HttpUnprocessableEntityError),
    ):
```

Sem essa linha o erro cairia no `raise HTTPException(status_code=500)` do final — o 403 viraria 500.

- [ ] **Step 5: Rodar e confirmar que passa**

```bash
.venv/bin/python -m pytest src/errors/error_handler_test.py -v
```
Esperado: PASS.

- [ ] **Step 6: Verificar e commitar**

```bash
.venv/bin/python -m pytest -q
.venv/bin/python -m pylint src
git add src/errors
git commit -m "feat: add a 403 error type to the error handler"
```

---

### Task 4: Repositories participantes de transação

Dois repositories no estilo sessão-injetada: recebem a sessão, não abrem e **não commitam**. É o que permite às escritas deles caírem na mesma transação.

**Files:**
- Create: `src/models/repositories/interfaces/refund_status_repository_interface.py`
- Create: `src/models/repositories/refund_status_repository.py`
- Create: `src/models/repositories/refund_status_repository_test.py`
- Create: `src/models/repositories/interfaces/refund_reviews_repository_interface.py`
- Create: `src/models/repositories/refund_reviews_repository.py`
- Create: `src/models/repositories/refund_reviews_repository_test.py`

**Interfaces:**
- Consumes: `RefundReviews` e `refunds.status` (Task 2)
- Produces:
  - `RefundStatusRepository(session)` com `async select_for_update(refund_id: int) -> Optional[dict]` e `async update_status(refund_id: int, status: str) -> None`
  - `RefundReviewsRepository(session)` com `async insert_review(refund_id: int, reviewer_id: int, from_status: str, to_status: str, reason: Optional[str]) -> None`
  - Ambos consumidos pela Task 5

- [ ] **Step 1: Escrever os testes que falham**

`src/models/repositories/refund_status_repository_test.py`:

```python
# pylint: disable=w0621
from unittest.mock import AsyncMock, MagicMock
import pytest
from .refund_status_repository import RefundStatusRepository


@pytest.fixture
def mock_session():
    session = MagicMock()
    session.execute = AsyncMock()
    session.commit = AsyncMock()
    return session


# The row is read with FOR UPDATE so a concurrent reviewer blocks until this
# transaction ends, instead of deciding from a stale status.
@pytest.mark.asyncio
async def test_select_for_update_locks_the_row_and_returns_a_dict(mock_session):
    row = MagicMock()
    row._mapping = {"id": 1, "user_id": 7, "status": "pending"}
    mock_session.execute.return_value.fetchone = MagicMock(return_value=row)

    repository = RefundStatusRepository(mock_session)
    refund = await repository.select_for_update(1)

    assert refund == {"id": 1, "user_id": 7, "status": "pending"}
    statement = str(mock_session.execute.call_args[0][0])
    assert "FOR UPDATE" in statement


@pytest.mark.asyncio
async def test_select_for_update_returns_none_when_the_refund_does_not_exist(mock_session):
    mock_session.execute.return_value.fetchone = MagicMock(return_value=None)

    repository = RefundStatusRepository(mock_session)

    assert await repository.select_for_update(999) is None


# The repository must NOT commit: the UnitOfWork owns that decision, and a commit
# here would defeat the whole point of the transaction boundary.
@pytest.mark.asyncio
async def test_update_status_executes_without_committing(mock_session):
    repository = RefundStatusRepository(mock_session)

    await repository.update_status(1, "approved")

    mock_session.execute.assert_awaited_once()
    mock_session.commit.assert_not_awaited()
```

`src/models/repositories/refund_reviews_repository_test.py`:

```python
# pylint: disable=w0621
from unittest.mock import AsyncMock, MagicMock
import pytest
from .refund_reviews_repository import RefundReviewsRepository


@pytest.fixture
def mock_session():
    session = MagicMock()
    session.execute = AsyncMock()
    session.commit = AsyncMock()
    return session


@pytest.mark.asyncio
async def test_insert_review_records_the_transition_without_committing(mock_session):
    repository = RefundReviewsRepository(mock_session)

    await repository.insert_review(
        refund_id=1,
        reviewer_id=9,
        from_status="pending",
        to_status="rejected",
        reason="Comprovante ilegível",
    )

    mock_session.execute.assert_awaited_once()
    mock_session.commit.assert_not_awaited()


# An approval carries no reason, and that must reach the database as NULL.
@pytest.mark.asyncio
async def test_insert_review_accepts_a_null_reason(mock_session):
    repository = RefundReviewsRepository(mock_session)

    await repository.insert_review(
        refund_id=1, reviewer_id=9, from_status="pending", to_status="approved", reason=None
    )

    mock_session.execute.assert_awaited_once()
```

- [ ] **Step 2: Rodar e confirmar que falham**

```bash
.venv/bin/python -m pytest src/models/repositories/refund_status_repository_test.py src/models/repositories/refund_reviews_repository_test.py -v
```
Esperado: `ModuleNotFoundError` nos dois arquivos.

- [ ] **Step 3: Criar as interfaces**

`src/models/repositories/interfaces/refund_status_repository_interface.py`:

```python
from abc import ABC, abstractmethod
from typing import Optional


class RefundStatusRepositoryInterface(ABC):

    @abstractmethod
    async def select_for_update(self, refund_id: int) -> Optional[dict]:
        pass

    @abstractmethod
    async def update_status(self, refund_id: int, status: str) -> None:
        pass
```

`src/models/repositories/interfaces/refund_reviews_repository_interface.py`:

```python
from abc import ABC, abstractmethod
from typing import Optional


class RefundReviewsRepositoryInterface(ABC):

    @abstractmethod
    async def insert_review(
        self,
        refund_id: int,
        reviewer_id: int,
        from_status: str,
        to_status: str,
        reason: Optional[str],
    ) -> None:
        pass
```

- [ ] **Step 4: Implementar os repositories**

`src/models/repositories/refund_status_repository.py`:

```python
# pylint: disable=w0212
from typing import Optional
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from src.models.entities.refunds import Refunds
from .interfaces.refund_status_repository_interface import RefundStatusRepositoryInterface


class RefundStatusRepository(RefundStatusRepositoryInterface):
    # Unlike RefundsRepository, this one neither opens a session nor commits: it
    # receives the session from the UnitOfWork, so its writes join the same
    # transaction as RefundReviewsRepository's and land (or roll back) together.
    def __init__(self, session: AsyncSession) -> None:
        self.__session = session

    async def select_for_update(self, refund_id: int) -> Optional[dict]:
        query = select(Refunds).where(Refunds.c.id == refund_id).with_for_update()
        result = await self.__session.execute(query)
        refund = result.fetchone()
        return dict(refund._mapping) if refund else None

    async def update_status(self, refund_id: int, status: str) -> None:
        query = update(Refunds).where(Refunds.c.id == refund_id).values(status=status)
        await self.__session.execute(query)
```

`src/models/repositories/refund_reviews_repository.py`:

```python
from typing import Optional
from sqlalchemy import insert
from sqlalchemy.ext.asyncio import AsyncSession
from src.models.entities.refund_reviews import RefundReviews
from .interfaces.refund_reviews_repository_interface import RefundReviewsRepositoryInterface


class RefundReviewsRepository(RefundReviewsRepositoryInterface):
    # Session-injected and commit-free, for the same reason as
    # RefundStatusRepository: the UnitOfWork owns the transaction.
    def __init__(self, session: AsyncSession) -> None:
        self.__session = session

    async def insert_review(
        self,
        refund_id: int,
        reviewer_id: int,
        from_status: str,
        to_status: str,
        reason: Optional[str],
    ) -> None:
        query = insert(RefundReviews).values(
            refund_id=refund_id,
            reviewer_id=reviewer_id,
            from_status=from_status,
            to_status=to_status,
            reason=reason,
        )
        await self.__session.execute(query)
```

- [ ] **Step 5: Rodar e confirmar que passam**

```bash
.venv/bin/python -m pytest src/models/repositories -v
```
Esperado: os 5 testes novos passam, e os testes existentes de repository continuam verdes.

- [ ] **Step 6: Verificar e commitar**

```bash
.venv/bin/python -m pytest -q
.venv/bin/python -m pylint src
git add src/models/repositories
git commit -m "feat: add session-injected repositories for refund status and reviews"
```

---

### Task 5: Unit of Work

O objeto que delimita a transação e entrega os repositories ligados a ela.

**Files:**
- Create: `src/models/settings/unit_of_work.py`
- Create: `src/models/settings/unit_of_work_test.py`

**Interfaces:**
- Consumes: `DatabaseConnectionHandler.connect()` (Task 0, já existe); `RefundStatusRepository`, `RefundReviewsRepository` (Task 4)
- Produces: `UnitOfWork(database_connection)` usável como `async with`, expondo `.refunds`, `.reviews` e `async commit()`. Consumido pelas Tasks 7 e 8.

- [ ] **Step 1: Escrever os testes que falham**

`src/models/settings/unit_of_work_test.py`:

```python
# pylint: disable=w0621
from unittest.mock import AsyncMock, MagicMock
import pytest
from .unit_of_work import UnitOfWork


@pytest.fixture
def mock_session():
    session = MagicMock()
    session.execute = AsyncMock()
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    return session


@pytest.fixture
def mock_connection(mock_session):
    connection = MagicMock()
    context = MagicMock()
    context.__aenter__ = AsyncMock(return_value=mock_session)
    context.__aexit__ = AsyncMock(return_value=None)
    connection.connect = MagicMock(return_value=context)
    return connection


# Both repositories must share the SAME session — that is the entire mechanism
# by which their writes end up in one transaction.
@pytest.mark.asyncio
async def test_both_repositories_share_the_same_session(mock_connection, mock_session):
    async with UnitOfWork(mock_connection) as unit_of_work:
        await unit_of_work.refunds.update_status(1, "approved")
        await unit_of_work.reviews.insert_review(
            refund_id=1, reviewer_id=9, from_status="pending", to_status="approved", reason=None
        )

    assert mock_session.execute.await_count == 2


@pytest.mark.asyncio
async def test_commit_commits_the_session(mock_connection, mock_session):
    async with UnitOfWork(mock_connection) as unit_of_work:
        await unit_of_work.commit()

    mock_session.commit.assert_awaited_once()


# The safety property: an exception inside the block rolls back, so a partial
# write can never survive.
@pytest.mark.asyncio
async def test_an_exception_inside_the_block_rolls_back(mock_connection, mock_session):
    with pytest.raises(ValueError):
        async with UnitOfWork(mock_connection) as unit_of_work:
            await unit_of_work.refunds.update_status(1, "approved")
            raise ValueError("boom")

    mock_session.rollback.assert_awaited_once()
    mock_session.commit.assert_not_awaited()


# Leaving the block without committing must not persist anything. The failure
# mode is "nothing was written", never "half was written".
@pytest.mark.asyncio
async def test_leaving_without_commit_does_not_commit(mock_connection, mock_session):
    async with UnitOfWork(mock_connection) as unit_of_work:
        await unit_of_work.refunds.update_status(1, "approved")

    mock_session.commit.assert_not_awaited()
```

- [ ] **Step 2: Rodar e confirmar que falham**

```bash
.venv/bin/python -m pytest src/models/settings/unit_of_work_test.py -v
```
Esperado: `ModuleNotFoundError: No module named 'src.models.settings.unit_of_work'`.

- [ ] **Step 3: Implementar o Unit of Work**

`src/models/settings/unit_of_work.py`:

```python
from typing import Optional
from src.models.repositories.refund_status_repository import RefundStatusRepository
from src.models.repositories.refund_reviews_repository import RefundReviewsRepository
from .database_connection_handler import DatabaseConnectionHandler


class UnitOfWork:
    # Delimits ONE transaction for ONE use case, and hands out repositories bound
    # to it. Repositories that take a session (instead of opening their own) can
    # therefore write inside the same transaction and land together.
    #
    # This is deliberately NOT used by the existing single-write CRUDs: with one
    # write there is nothing to coordinate, and wrapping them would add
    # indirection without buying a guarantee.
    def __init__(self, database_connection: DatabaseConnectionHandler) -> None:
        self.__db_connection = database_connection
        self.__session_ctx = None
        self.__session = None
        self.refunds: Optional[RefundStatusRepository] = None
        self.reviews: Optional[RefundReviewsRepository] = None

    async def __aenter__(self) -> "UnitOfWork":
        self.__session_ctx = self.__db_connection.connect()
        self.__session = await self.__session_ctx.__aenter__()
        self.refunds = RefundStatusRepository(self.__session)
        self.reviews = RefundReviewsRepository(self.__session)
        return self

    async def __aexit__(self, exc_type, exc_value, traceback) -> None:
        # Rolling back on the way out is what makes an exception anywhere in the
        # block safe: no caller needs a try/except to undo a partial write.
        if exc_type is not None:
            await self.__session.rollback()
        await self.__session_ctx.__aexit__(exc_type, exc_value, traceback)

    async def commit(self) -> None:
        await self.__session.commit()
```

- [ ] **Step 4: Rodar e confirmar que passam**

```bash
.venv/bin/python -m pytest src/models/settings/unit_of_work_test.py -v
```
Esperado: 4 testes PASS.

- [ ] **Step 5: Verificar e commitar**

```bash
.venv/bin/python -m pytest -q
.venv/bin/python -m pylint src
git add src/models/settings
git commit -m "feat: add a unit of work delimiting one transaction per use case"
```

---

### Task 6: Validator da revisão

**Files:**
- Create: `src/validators/refund_reviewer_validator.py`
- Create: `src/validators/refund_reviewer_validator_test.py`

**Interfaces:**
- Produces: `refund_reviewer_validator(http_request: HttpRequest) -> None`, chamado pela view da Task 8

- [ ] **Step 1: Escrever os testes que falham**

`src/validators/refund_reviewer_validator_test.py`:

```python
import pytest
from src.errors.types.http_unprocessable_entity_error import HttpUnprocessableEntityError
from src.views.http_types.http_request import HttpRequest
from .refund_reviewer_validator import refund_reviewer_validator


def valid_body(**overrides) -> dict:
    body = {"status": "approved", "reason": None}
    body.update(overrides)
    return body


def test_approving_without_a_reason_is_valid():
    refund_reviewer_validator(HttpRequest(body=valid_body()))


def test_rejecting_with_a_reason_is_valid():
    refund_reviewer_validator(
        HttpRequest(body=valid_body(status="rejected", reason="Comprovante ilegível"))
    )


# "pending" is a legal status of a refund but never a legal TARGET of a review:
# nothing returns to pending (BR-017).
def test_pending_is_not_an_acceptable_target_status():
    with pytest.raises(HttpUnprocessableEntityError):
        refund_reviewer_validator(HttpRequest(body=valid_body(status="pending")))


def test_unknown_status_raises():
    with pytest.raises(HttpUnprocessableEntityError):
        refund_reviewer_validator(HttpRequest(body=valid_body(status="whatever")))


# A rejection without justification is useless to whoever receives it.
def test_rejecting_without_a_reason_raises():
    with pytest.raises(HttpUnprocessableEntityError):
        refund_reviewer_validator(HttpRequest(body=valid_body(status="rejected", reason=None)))


def test_rejecting_with_a_blank_reason_raises():
    with pytest.raises(HttpUnprocessableEntityError):
        refund_reviewer_validator(HttpRequest(body=valid_body(status="rejected", reason="   ")))
```

- [ ] **Step 2: Rodar e confirmar que falham**

```bash
.venv/bin/python -m pytest src/validators/refund_reviewer_validator_test.py -v
```
Esperado: `ModuleNotFoundError`.

- [ ] **Step 3: Implementar o validator**

`src/validators/refund_reviewer_validator.py`:

```python
from src.errors.types.http_unprocessable_entity_error import HttpUnprocessableEntityError
from src.views.http_types.http_request import HttpRequest

# "pending" is intentionally absent: it is a valid refund status but never a
# valid target of a review — nothing goes back to pending (BR-017).
ALLOWED_REVIEW_STATUSES = {"approved", "rejected"}


def refund_reviewer_validator(http_request: HttpRequest) -> None:
    body = http_request.body

    if body.get("status") not in ALLOWED_REVIEW_STATUSES:
        raise HttpUnprocessableEntityError(
            f"Status must be one of: {', '.join(sorted(ALLOWED_REVIEW_STATUSES))}"
        )

    if body["status"] == "rejected" and not str(body.get("reason") or "").strip():
        raise HttpUnprocessableEntityError("Reason is required when rejecting a refund")
```

- [ ] **Step 4: Rodar e confirmar que passam**

```bash
.venv/bin/python -m pytest src/validators/refund_reviewer_validator_test.py -v
```
Esperado: 6 testes PASS.

- [ ] **Step 5: Verificar e commitar**

```bash
.venv/bin/python -m pytest -q
.venv/bin/python -m pylint src
git add src/validators
git commit -m "feat: validate refund review status and rejection reason"
```

---

### Task 7: Controller da revisão

Autorização, máquina de estados e as duas escritas na transação. É o núcleo do ciclo.

**Files:**
- Create: `src/controllers/interfaces/refund_reviewer_controller_interface.py`
- Create: `src/controllers/refund_reviewer_controller.py`
- Create: `src/controllers/refund_reviewer_controller_test.py`

**Interfaces:**
- Consumes: `UnitOfWork` (Task 5), `HttpForbiddenError` (Task 3), `HttpNotFoundError`, `HttpUnprocessableEntityError`
- Produces: `RefundReviewerController(unit_of_work)` com
  `async review(refund_id: int, reviewer_id: int, role: str, status: str, reason: Optional[str]) -> dict`,
  consumido pela Task 8

- [ ] **Step 1: Escrever os testes que falham**

`src/controllers/refund_reviewer_controller_test.py`:

```python
# pylint: disable=w0621
from unittest.mock import AsyncMock, MagicMock
import pytest
from src.errors.types.http_forbidden_error import HttpForbiddenError
from src.errors.types.http_not_found_error import HttpNotFoundError
from src.errors.types.http_unprocessable_entity_error import HttpUnprocessableEntityError
from .refund_reviewer_controller import RefundReviewerController


def build_unit_of_work(refund=None, insert_review=None):
    """Builds a UnitOfWork test double usable as `async with`."""
    unit_of_work = MagicMock()
    unit_of_work.refunds = MagicMock()
    unit_of_work.refunds.select_for_update = AsyncMock(return_value=refund)
    unit_of_work.refunds.update_status = AsyncMock()
    unit_of_work.reviews = MagicMock()
    unit_of_work.reviews.insert_review = insert_review or AsyncMock()
    unit_of_work.commit = AsyncMock()
    unit_of_work.__aenter__ = AsyncMock(return_value=unit_of_work)
    unit_of_work.__aexit__ = AsyncMock(return_value=None)
    return unit_of_work


@pytest.fixture
def pending_refund():
    return {"id": 1, "user_id": 7, "status": "pending", "name": "Almoço", "filename": "a.jpg"}


@pytest.mark.asyncio
async def test_admin_approves_a_pending_refund(pending_refund):
    unit_of_work = build_unit_of_work(refund=pending_refund)
    controller = RefundReviewerController(unit_of_work)

    response = await controller.review(
        refund_id=1, reviewer_id=9, role="admin", status="approved", reason=None
    )

    unit_of_work.refunds.update_status.assert_awaited_once_with(1, "approved")
    unit_of_work.reviews.insert_review.assert_awaited_once_with(
        refund_id=1, reviewer_id=9, from_status="pending", to_status="approved", reason=None
    )
    unit_of_work.commit.assert_awaited_once()
    assert response["attributes"]["status"] == "approved"


# BR-017: an admin may change their mind, and the history records where it came from.
@pytest.mark.asyncio
async def test_an_approved_refund_can_be_rejected_afterwards():
    unit_of_work = build_unit_of_work(refund={"id": 1, "user_id": 7, "status": "approved"})
    controller = RefundReviewerController(unit_of_work)

    await controller.review(
        refund_id=1, reviewer_id=9, role="admin", status="rejected", reason="Duplicado"
    )

    unit_of_work.reviews.insert_review.assert_awaited_once_with(
        refund_id=1, reviewer_id=9, from_status="approved", to_status="rejected", reason="Duplicado"
    )


# The role check runs BEFORE touching the database on purpose: a check that never
# queries cannot leak whether the id exists, so a standard user gets the same 403
# for a real id and for a made-up one (same reasoning as BR-013's 404).
@pytest.mark.asyncio
async def test_standard_user_is_forbidden_and_the_database_is_never_touched(pending_refund):
    unit_of_work = build_unit_of_work(refund=pending_refund)
    controller = RefundReviewerController(unit_of_work)

    with pytest.raises(HttpForbiddenError):
        await controller.review(
            refund_id=1, reviewer_id=7, role="standard", status="approved", reason=None
        )

    unit_of_work.refunds.select_for_update.assert_not_awaited()


# BR-016: whoever spends does not approve their own spending.
@pytest.mark.asyncio
async def test_admin_cannot_review_their_own_refund(pending_refund):
    unit_of_work = build_unit_of_work(refund=pending_refund)
    controller = RefundReviewerController(unit_of_work)

    with pytest.raises(HttpForbiddenError):
        await controller.review(
            refund_id=1, reviewer_id=7, role="admin", status="approved", reason=None
        )

    unit_of_work.refunds.update_status.assert_not_awaited()


@pytest.mark.asyncio
async def test_missing_refund_raises_not_found():
    unit_of_work = build_unit_of_work(refund=None)
    controller = RefundReviewerController(unit_of_work)

    with pytest.raises(HttpNotFoundError):
        await controller.review(
            refund_id=999, reviewer_id=9, role="admin", status="approved", reason=None
        )


# Repeating the current decision is not a state change, and writing
# "approved -> approved" would pollute the audit trail with an event that never
# happened.
@pytest.mark.asyncio
async def test_repeating_the_current_decision_raises():
    unit_of_work = build_unit_of_work(refund={"id": 1, "user_id": 7, "status": "approved"})
    controller = RefundReviewerController(unit_of_work)

    with pytest.raises(HttpUnprocessableEntityError):
        await controller.review(
            refund_id=1, reviewer_id=9, role="admin", status="approved", reason=None
        )

    unit_of_work.reviews.insert_review.assert_not_awaited()


# THE test of this cycle: if the history insert fails, the status change must not
# survive. Without the UnitOfWork the UPDATE would have committed on its own and
# there would be no way to assert this.
@pytest.mark.asyncio
async def test_the_transaction_is_not_committed_when_the_review_insert_fails(pending_refund):
    failing_insert = AsyncMock(side_effect=RuntimeError("history insert exploded"))
    unit_of_work = build_unit_of_work(refund=pending_refund, insert_review=failing_insert)
    controller = RefundReviewerController(unit_of_work)

    with pytest.raises(RuntimeError):
        await controller.review(
            refund_id=1, reviewer_id=9, role="admin", status="approved", reason=None
        )

    # commit never ran, and __aexit__ received the exception — which is what
    # triggers the rollback proven in unit_of_work_test.py.
    unit_of_work.commit.assert_not_awaited()
    assert unit_of_work.__aexit__.await_args[0][0] is RuntimeError
```

- [ ] **Step 2: Rodar e confirmar que falham**

```bash
.venv/bin/python -m pytest src/controllers/refund_reviewer_controller_test.py -v
```
Esperado: `ModuleNotFoundError`.

- [ ] **Step 3: Criar a interface**

`src/controllers/interfaces/refund_reviewer_controller_interface.py`:

```python
from abc import ABC, abstractmethod
from typing import Optional


class RefundReviewerControllerInterface(ABC):

    @abstractmethod
    async def review(
        self,
        refund_id: int,
        reviewer_id: int,
        role: str,
        status: str,
        reason: Optional[str],
    ) -> dict:
        pass
```

- [ ] **Step 4: Implementar o controller**

`src/controllers/refund_reviewer_controller.py`:

```python
from typing import Optional
from src.models.settings.unit_of_work import UnitOfWork
from src.controllers.interfaces.refund_reviewer_controller_interface import (
    RefundReviewerControllerInterface,
)
from src.errors.types.http_forbidden_error import HttpForbiddenError
from src.errors.types.http_not_found_error import HttpNotFoundError
from src.errors.types.http_unprocessable_entity_error import HttpUnprocessableEntityError


class RefundReviewerController(RefundReviewerControllerInterface):
    def __init__(self, unit_of_work: UnitOfWork) -> None:
        self.__unit_of_work = unit_of_work

    async def review(
        self,
        refund_id: int,
        reviewer_id: int,
        role: str,
        status: str,
        reason: Optional[str],
    ) -> dict:
        # Role first, before any database access. A check that never queries
        # cannot leak whether the id exists, so a standard user gets an identical
        # 403 for a real and for an invented id — the same anti-enumeration
        # reasoning behind BR-013's 404.
        if role != "admin":
            raise HttpForbiddenError("Only administrators can review refunds")

        async with self.__unit_of_work as unit_of_work:
            refund = await unit_of_work.refunds.select_for_update(refund_id)

            if not refund:
                raise HttpNotFoundError("Refund not found")

            # BR-016 — segregation of duties. A 403 is safe here: whoever reached
            # this point is already an admin and, by BR-012, already sees every
            # refund, so there is nothing left to leak.
            if refund["user_id"] == reviewer_id:
                raise HttpForbiddenError("You cannot review your own refund")

            current_status = refund["status"]

            # This single comparison covers BR-017 entirely. The validator already
            # restricts the target to {approved, rejected}, so of the possible
            # (current, target) pairs the only forbidden one left is "no change".
            # A transition table here would be dead code.
            if current_status == status:
                raise HttpUnprocessableEntityError(f"Refund is already {status}")

            await unit_of_work.refunds.update_status(refund_id, status)
            await unit_of_work.reviews.insert_review(
                refund_id=refund_id,
                reviewer_id=reviewer_id,
                from_status=current_status,
                to_status=status,
                reason=reason,
            )
            await unit_of_work.commit()

        return self.__format_response(refund, status)

    def __format_response(self, refund: dict, status: str) -> dict:
        created_at = refund.get("created_at")
        return {
            "type": "Refund",
            "count": 1,
            "attributes": {
                **refund,
                "status": status,
                "created_at": created_at.isoformat() if created_at else None,
            },
        }
```

- [ ] **Step 5: Rodar e confirmar que passam**

```bash
.venv/bin/python -m pytest src/controllers/refund_reviewer_controller_test.py -v
```
Esperado: 7 testes PASS.

- [ ] **Step 6: Verificar e commitar**

```bash
.venv/bin/python -m pytest -q
.venv/bin/python -m pylint src
git add src/controllers
git commit -m "feat: review refunds atomically with authorization and state rules"
```

---

### Task 8: View, composer e rota

Liga o caso de uso ao HTTP.

**Files:**
- Create: `src/views/refund_reviewer_view.py`
- Create: `src/views/refund_reviewer_view_test.py`
- Create: `src/main/composer/refund_reviewer_composer.py`
- Modify: `src/main/routes/refund_routes.py`

**Interfaces:**
- Consumes: `RefundReviewerController` (Task 7), `refund_reviewer_validator` (Task 6), `UnitOfWork` (Task 5)
- Produces: `PATCH /refunds/{refund_id}/status` operacional

- [ ] **Step 1: Escrever o teste da view**

`src/views/refund_reviewer_view_test.py`:

```python
# pylint: disable=w0621
from unittest.mock import AsyncMock, MagicMock
import pytest
from fastapi import HTTPException
from src.views.http_types.http_request import HttpRequest
from .refund_reviewer_view import RefundReviewerView


@pytest.fixture
def mock_controller():
    controller = MagicMock()
    controller.review = AsyncMock(
        return_value={"type": "Refund", "count": 1, "attributes": {"id": 1, "status": "approved"}}
    )
    return controller


@pytest.mark.asyncio
async def test_valid_request_reaches_the_controller_and_returns_200(mock_controller):
    view = RefundReviewerView(mock_controller)
    http_request = HttpRequest(
        path_params={"refund_id": 1},
        body={"status": "approved", "reason": None},
        token_info={"user_id": 9, "role": "admin"},
    )

    http_response = await view.handle(http_request)

    mock_controller.review.assert_awaited_once_with(
        refund_id=1, reviewer_id=9, role="admin", status="approved", reason=None
    )
    assert http_response.status_code == 200


# The validator runs before the controller: an invalid body must short-circuit
# with a 422 and never reach the transaction. The view catches the domain error
# and error_handler converts it, so what surfaces here is HTTPException — the
# same pattern asserted in refund_creator_view_test.py.
@pytest.mark.asyncio
async def test_invalid_status_short_circuits_before_the_controller(mock_controller):
    view = RefundReviewerView(mock_controller)
    http_request = HttpRequest(
        path_params={"refund_id": 1},
        body={"status": "whatever", "reason": None},
        token_info={"user_id": 9, "role": "admin"},
    )

    with pytest.raises(HTTPException) as exception_info:
        await view.handle(http_request)

    assert exception_info.value.status_code == 422
    mock_controller.review.assert_not_awaited()
```

- [ ] **Step 2: Rodar e confirmar que falha**

```bash
.venv/bin/python -m pytest src/views/refund_reviewer_view_test.py -v
```
Esperado: `ModuleNotFoundError`.

- [ ] **Step 3: Implementar a view**

`src/views/refund_reviewer_view.py`:

```python
from src.controllers.interfaces.refund_reviewer_controller_interface import (
    RefundReviewerControllerInterface,
)
from src.validators.refund_reviewer_validator import refund_reviewer_validator
from src.views.http_types.http_request import HttpRequest
from src.views.http_types.http_response import HttpResponse
from src.errors.error_handler import error_handler


class RefundReviewerView:
    def __init__(self, controller: RefundReviewerControllerInterface) -> None:
        self.__controller = controller

    async def handle(self, http_request: HttpRequest) -> HttpResponse:
        try:
            refund_reviewer_validator(http_request)

            response = await self.__controller.review(
                refund_id=http_request.path_params["refund_id"],
                reviewer_id=http_request.token_info["user_id"],
                role=http_request.token_info["role"],
                status=http_request.body["status"],
                reason=http_request.body.get("reason"),
            )
            return HttpResponse(body=response, status_code=200)
        except Exception as e:
            error_handler(e)
```

- [ ] **Step 4: Criar o composer**

`src/main/composer/refund_reviewer_composer.py`:

```python
from src.models.settings.database_connection_handler import database_connection_handler
from src.models.settings.unit_of_work import UnitOfWork
from src.controllers.refund_reviewer_controller import RefundReviewerController
from src.views.refund_reviewer_view import RefundReviewerView


def refund_reviewer_composer():
    # A fresh UnitOfWork per request: it holds a session for the duration of one
    # transaction, so sharing one across requests would share a session — the very
    # bug fixed in DatabaseConnectionHandler.
    unit_of_work = UnitOfWork(database_connection_handler)
    controller = RefundReviewerController(unit_of_work)
    view = RefundReviewerView(controller)
    return view
```

- [ ] **Step 5: Adicionar a rota**

Em `src/main/routes/refund_routes.py`, adicione o import do composer novo e, **antes** da rota `@refund_routes.get("/{refund_id}")`, insira:

```python
@refund_routes.patch("/{refund_id}/status")
async def review_refund(
    refund_id: int,
    body: dict = Body(...),
    token_info: dict = Depends(get_current_user),
):
    http_request = HttpRequest(
        path_params={"refund_id": refund_id},
        body=body,
        token_info=token_info,
    )
    view = refund_reviewer_composer()
    response = await view.handle(http_request)
    return JSONResponse(content=response.body, status_code=response.status_code)
```

Acrescente `Body` ao import do FastAPI no topo do arquivo:

```python
from fastapi import APIRouter, Depends, Form, UploadFile, File, Query, Body
```

- [ ] **Step 6: Rodar e confirmar que passa**

```bash
.venv/bin/python -m pytest src/views/refund_reviewer_view_test.py -v
```
Esperado: 2 testes PASS.

- [ ] **Step 7: Conferir a rota no servidor**

```bash
.venv/bin/python run.py
```
Em outro terminal:
```bash
curl -s http://localhost:3333/openapi.json | python3 -c "import sys,json; print([p for p in json.load(sys.stdin)['paths'] if 'status' in p])"
```
Esperado: `['/refunds/{refund_id}/status']`.

- [ ] **Step 8: Verificar e commitar**

```bash
.venv/bin/python -m pytest -q
.venv/bin/python -m pylint src
git add src/views src/main
git commit -m "feat: expose PATCH /refunds/{id}/status"
```

---

### Task 9: `status` nas respostas de listagem e detalhe

`select(Refunds)` já seleciona todas as colunas e os controllers já espalham `**refund`, então o campo aparece sozinho assim que a coluna existe. Esta task **prova** isso com teste em vez de assumir.

**Files:**
- Modify: `src/controllers/refund_lister_controller_test.py`
- Modify: `src/controllers/refund_finder_controller_test.py`

**Interfaces:**
- Consumes: coluna `refunds.status` (Task 2)
- Produces: garantia de regressão de que `status` aparece nas respostas de `GET /refunds` e `GET /refunds/{id}`

- [ ] **Step 1: Adicionar os testes**

Em `src/controllers/refund_finder_controller_test.py`:

```python
# The detail response must carry status: it is what lets the frontend tell a
# pending refund from a decided one. It flows automatically because
# select(Refunds) selects every column and __format_response spreads the row —
# this test is here so a future refactor cannot drop it silently.
@pytest.mark.asyncio
async def test_detail_response_includes_the_status(mock_repository):
    mock_repository.select_refund_by_id = AsyncMock(
        return_value={"id": 1, "user_id": 7, "status": "approved", "filename": "a.jpg"}
    )
    controller = RefundFinderController(mock_repository)

    response = await controller.find(refund_id=1, user_id=7, role="standard")

    assert response["attributes"]["status"] == "approved"
```

Em `src/controllers/refund_lister_controller_test.py` (a fixture `mock_repository` existente devolve `([{"id": 1}, {"id": 2}], 2, 19290)`; este teste a sobrescreve para incluir o status):

```python
# Same guarantee as the detail response, for the list: every item carries status.
@pytest.mark.asyncio
async def test_list_items_include_the_status(mock_repository):
    mock_repository.select_refunds = AsyncMock(
        return_value=([{"id": 1, "status": "pending"}, {"id": 2, "status": "approved"}], 2, 19290)
    )
    controller = RefundListerController(mock_repository)

    response = await controller.list(page=1, per_page=10, user_id=7, role="admin")

    assert [item["status"] for item in response["attributes"]] == ["pending", "approved"]
```

- [ ] **Step 2: Rodar**

```bash
.venv/bin/python -m pytest src/controllers -v
```
Esperado: PASS sem mudança de código de produção. **Se falhar**, algo no caminho está filtrando colunas explicitamente — investigue antes de seguir, porque contradiz a premissa desta task.

- [ ] **Step 3: Verificar e commitar**

```bash
.venv/bin/python -m pytest -q
.venv/bin/python -m pylint src
git add src/controllers
git commit -m "test: pin refund status into the list and detail responses"
```

---

### Task 10: Exclusão restrita a solicitações pendentes

**Files:**
- Modify: `src/controllers/refund_deleter_controller.py`
- Modify: `src/controllers/refund_deleter_controller_test.py`

**Interfaces:**
- Consumes: coluna `refunds.status` (Task 2)
- Produces: BR-015 com condição de estado

- [ ] **Step 1: Escrever os testes que falham**

Adicione em `src/controllers/refund_deleter_controller_test.py`:

```python
# BR-015 (amended): deleting a decided refund would erase the very audit trail
# this cycle created — and the owner is exactly who has an interest in erasing a
# rejection.
@pytest.mark.asyncio
async def test_deleting_a_decided_refund_is_rejected(mock_repository, mock_storage):
    mock_repository.select_refund_by_id = AsyncMock(
        return_value={"id": 1, "user_id": 7, "status": "approved", "filename": "abc.jpg"}
    )
    controller = RefundDeleterController(mock_repository, mock_storage)

    with pytest.raises(HttpUnprocessableEntityError):
        await controller.delete(refund_id=1, user_id=7, role="standard")

    mock_repository.delete_refund.assert_not_awaited()
    mock_storage.delete.assert_not_called()


@pytest.mark.asyncio
async def test_deleting_a_pending_refund_still_works(mock_repository, mock_storage):
    mock_repository.select_refund_by_id = AsyncMock(
        return_value={"id": 1, "user_id": 7, "status": "pending", "filename": "abc.jpg"}
    )
    controller = RefundDeleterController(mock_repository, mock_storage)

    await controller.delete(refund_id=1, user_id=7, role="standard")

    mock_repository.delete_refund.assert_awaited_once_with(1)
```

Adicione o import no topo do arquivo de teste:

```python
from src.errors.types.http_unprocessable_entity_error import HttpUnprocessableEntityError
```

**A fixture `mock_repository` existente devolve um refund sem `status`.** Atualize-a para incluir `"status": "pending"`, senão os testes já existentes quebram no `KeyError`.

- [ ] **Step 2: Rodar e confirmar que falham**

```bash
.venv/bin/python -m pytest src/controllers/refund_deleter_controller_test.py -v
```
Esperado: `test_deleting_a_decided_refund_is_rejected` falha (a exclusão acontece).

- [ ] **Step 3: Implementar a regra**

Em `src/controllers/refund_deleter_controller.py`, adicione o import e, **depois** da checagem de 404 e **antes** do `delete_refund`:

```python
from src.errors.types.http_unprocessable_entity_error import HttpUnprocessableEntityError
```
```python
        # BR-015: only a pending refund can be deleted. After a decision the
        # request is immutable to its owner — otherwise deleting would be a way to
        # erase one's own rejection along with its history.
        if refund["status"] != "pending":
            raise HttpUnprocessableEntityError("Only pending refunds can be deleted")
```

A ordem importa: o 404 continua vindo primeiro, para não revelar a existência de uma solicitação alheia através de um 422.

- [ ] **Step 4: Rodar e confirmar que passam**

```bash
.venv/bin/python -m pytest src/controllers/refund_deleter_controller_test.py -v
```
Esperado: todos PASS.

- [ ] **Step 5: Verificar e commitar**

```bash
.venv/bin/python -m pytest -q
.venv/bin/python -m pylint src
git add src/controllers
git commit -m "feat: restrict refund deletion to pending requests"
```

---

### Task 11: Admin de teste, verificação ponta a ponta e documentação canônica

**Files:**
- Create: `init/promote_admin.py`
- Modify: `docs/domain-model.md`
- Modify: `docs/business-rules.md`
- Create: `docs/use-cases/UC-007-review-refund.md`
- Modify: `docs/use-cases/UC-004-list-refunds.md`, `UC-005-view-refund.md`, `UC-006-delete-refund.md`
- Modify: `docs/index.md`

**Interfaces:**
- Consumes: tudo das tasks anteriores
- Produces: a documentação canônica alinhada ao comportamento

- [ ] **Step 1: Criar o script de promoção a admin**

**Por que existe:** `POST /auth/register` sempre cria `standard` (BR-003), então hoje **não há nenhum admin no banco** com quem exercitar o endpoint. Um script explícito é melhor que um `UPDATE` manual copiado de um chat.

`init/promote_admin.py`:

```python
"""Promotes an existing user to admin.

Registration always creates standard users (BR-003), so there is no way to get
the first admin through the API. Run it as:

    python init/promote_admin.py someone@example.com
"""
import asyncio
import sys
from sqlalchemy import update, select
from src.models.settings.database_connection_handler import database_connection_handler
from src.models.entities.users import Users


async def promote(email: str) -> None:
    async with database_connection_handler.connect() as session:
        found = (await session.execute(select(Users).where(Users.c.email == email))).fetchone()
        if not found:
            print(f"No user with email {email}")
            return

        await session.execute(update(Users).where(Users.c.email == email).values(role="admin"))
        await session.commit()
        print(f"{email} is now an admin")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("usage: python init/promote_admin.py <email>")
        sys.exit(1)
    asyncio.run(promote(sys.argv[1]))
```

- [ ] **Step 2: Verificação ponta a ponta contra a API real**

Suba o servidor (`.venv/bin/python run.py`) e, em outro terminal, promova um usuário e exercite os caminhos. Substitua os e-mails pelos que existirem no seu banco — **são necessários dois usuários distintos**, porque um admin não pode revisar a própria solicitação.

```bash
.venv/bin/python init/promote_admin.py <email-do-admin>
```

Confirme, um a um:

| Cenário | Esperado |
|---|---|
| `standard` faz PATCH em qualquer id | 403 |
| admin faz PATCH num id inexistente | 404 |
| admin faz PATCH na própria solicitação | 403 |
| admin aprova solicitação de outro | 200, `status: "approved"` |
| admin repete a mesma aprovação | 422 |
| admin rejeita sem `reason` | 422 |
| admin rejeita com `reason` | 200, `status: "rejected"` |
| `GET /refunds` | itens trazem `status` |
| dono exclui solicitação decidida | 422 |
| dono exclui solicitação pendente | 200 |

E confirme que o histórico registrou as transições:

```bash
.venv/bin/python -c "
import asyncio, os, asyncpg
from dotenv import load_dotenv
load_dotenv()
url = os.getenv('DATABASE_URL').replace('postgresql+asyncpg://', 'postgresql://')
async def main():
    c = await asyncpg.connect(url)
    for r in await c.fetch('select refund_id, reviewer_id, from_status, to_status, reason from refund_reviews order by id'):
        print(dict(r))
    await c.close()
asyncio.run(main())
"
```

- [ ] **Step 3: Atualizar `docs/domain-model.md`**

Adicione `status` à tabela de `Refund`; crie a seção `RefundReview` com suas colunas; atualize a relação para `Refund 1 ---- 0..* RefundReview`; adicione as invariantes de BR-016 e BR-017; e **remova a seção "Limites do modelo atual"**, que afirma não haver status, aprovação nem histórico — deixá-la seria contradizer o código.

- [ ] **Step 4: Atualizar `docs/business-rules.md`**

Acrescente ao final do arquivo, seguindo o formato das BRs existentes (título `##`, regra, e o campo **Evidências**):

```markdown
## BR-016 — Segregação de funções na revisão

Somente usuário `admin` aprova ou rejeita uma solicitação, e nenhum admin decide
sobre solicitação de sua própria autoria.

**Evidências:** `src/controllers/refund_reviewer_controller.py` verifica o papel
antes de qualquer consulta ao banco e recusa a revisão quando
`refund["user_id"]` é igual ao id do revisor.

## BR-017 — Transições de status permitidas

A partir de `pending`, uma solicitação vai para `approved` ou `rejected`. Uma
solicitação já decidida pode ter a decisão trocada (`approved` ↔ `rejected`),
mas nunca retorna a `pending`. Repetir a decisão vigente é recusado, porque não
há mudança de estado a registrar.

**Evidências:** `src/validators/refund_reviewer_validator.py` restringe o alvo a
`approved` ou `rejected`, e `src/controllers/refund_reviewer_controller.py`
recusa quando o status atual já é o alvo.
```

E altere a **BR-015** para exigir `status = 'pending'`, mantendo o texto sobre a remoção do comprovante e acrescentando que uma solicitação decidida não pode ser excluída.

- [ ] **Step 5: Criar `docs/use-cases/UC-007-review-refund.md`**

Siga a estrutura dos UCs existentes (leia `UC-006-delete-refund.md` como molde). Deve conter o endpoint, o corpo, a tabela de códigos da spec e a **ordem das checagens**, explicando por que o papel é verificado antes de consultar o banco.

- [ ] **Step 6: Atualizar UC-004, UC-005, UC-006 e o índice**

UC-004 e UC-005: o campo `status` passa a compor a resposta. UC-006: exclusão exige `pending`, com 422 caso contrário. `docs/index.md`: entrada do UC-007 na lista de casos de uso.

- [ ] **Step 7: Verificação final e commit**

```bash
.venv/bin/python -m pytest -q
.venv/bin/python -m pylint src
git add init docs
git commit -m "docs: record the refund review use case and its business rules"
```

Esperado: pytest verde (73 + os ~24 novos), pylint 10.00/10.

---

## Fechamento do ciclo (fora das tasks)

Depois da Task 11, o `learning-path-workflow.md` ainda exige, antes de considerar os Itens 18 e 20 encerrados:

- **`docs/learning-path-progress.md`** — entrada do ciclo: motivo, estado anterior com trechos, limitação encontrada, comparação visual, estado ajustado, arquivos, verificações e "o que lembrar". Registrar explicitamente que o teste de `upgrade`/`downgrade` é **manual** enquanto o Item 19 não existir.
- **`docs/plans/current-state.md`** — Itens 18 e 20 concluídos, o próximo passo (spec do frontend deste ciclo) e as pendências novas.
- **Apresentar o fechamento ao Gabriel** e aguardar autorização antes do próximo item.
