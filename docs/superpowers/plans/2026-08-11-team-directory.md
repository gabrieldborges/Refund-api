# Diretório do time — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Dar ao administrador uma lista buscável dos usuários cadastrados e uma página por usuário com o histórico de solicitações dela, com os dois endpoints que hoje não existem.

**Architecture:** Backend em camadas (rota → composer → view → controller → repositório), com a autorização no controller e a forma pública num serializador único. Frontend com uma feature nova `team` atrás de fachada, mais a extração do núcleo compartilhado do `RequesterPanel` para que a página do membro e a tela de revisão não tenham duas cópias dos contadores por status.

**Tech Stack:** FastAPI, SQLAlchemy Core, pytest. React 19, TanStack Query, TanStack Table, Zod, react-router 7 (data router), Vitest, MSW.

**Spec:** [`2026-08-11-team-directory-design.md`](../specs/2026-08-11-team-directory-design.md)

## Global Constraints

- **`password` nunca sai numa resposta.** A forma pública do usuário é `{id, name, email, role, has_avatar, created_at}`.
- Textos de UI em **português**; código, identificadores e comentários de teste em **inglês** (`AGENTS.md` dos dois repos).
- Toda chave de i18n entra nos **dois** catálogos, `src/locales/pt-BR.json` e `en-US.json` — há teste de paridade em `src/locales/catalogues.test.ts`.
- Testes de backend colocados como `<modulo>_test.py` **ao lado** do código testado.
- `pylint src; echo $?` — **o código de saída, não a nota**. Zero é aprovação.
- Uma feature do frontend **não pode** importar outra feature nem a camada `app`; só `ui` (`src/components/ui`) e `shared` (`src/lib`, `src/hooks`, `src/stores`). O juiz é `eslint.config.js:39-62`.
- `RefundDonutChart` **não pode** ser reexportado pela fachada de `features/refunds`: uma reexportação estática traz 74,2 kB gzip de volta ao bundle de entrada sem erro nenhum.
- Ordenação da lista de usuários é **fixa** (`name ASC` com desempate por `id`). Não há parâmetro `sort`, e portanto nenhum validator novo.
- Branch de implementação: `feat/team-directory`, criada nos **dois** repositórios.
- Baselines que não podem regredir: **frontend 318 testes em 55 arquivos**; **backend 341 testes** (+72 de integração desmarcados).

---

## Task 1: A forma pública do usuário (`serialize_user`)

Primeiro porque é a única regra deste ciclo cujo erro é grave: um campo sensível
numa lista de usuários. Um serializador único torna isso provável de uma vez.

**Files:**
- Create: `Refund-api/src/controllers/user_serializer.py`
- Create: `Refund-api/src/controllers/user_serializer_test.py`

**Interfaces:**
- Produces: `serialize_user(user: dict) -> dict` e `format_user_list_response(users: list, total: int, page: int, per_page: int) -> dict`, usados pelas Tasks 3 e 4.

- [ ] **Step 1: Escrever o teste que falha**

```python
# Refund-api/src/controllers/user_serializer_test.py
from .user_serializer import serialize_user, format_user_list_response


# A repository row carries every column, including the bcrypt hash. This is the
# row shape select_user_by_id already returns.
def _row(**overrides):
    row = {
        "id": 7,
        "name": "Ana",
        "email": "ana@example.com",
        "password": "$2b$12$hash",
        "role": "standard",
        "avatar_filename": None,
        "created_at": None,
    }
    row.update(overrides)
    return row


# The whole reason this module exists: the hash must never reach a response.
def test_the_password_is_absent_from_the_serialized_user():
    assert "password" not in serialize_user(_row())


# Asserting the exact key set, not just the absence of "password": a column
# added to the table later would otherwise flow straight into the API.
def test_only_the_public_fields_are_exposed():
    assert set(serialize_user(_row())) == {
        "id", "name", "email", "role", "has_avatar", "created_at",
    }


# The client only needs to know whether to show a picture or the initials
# gradient, so the filename itself is not client data.
def test_has_avatar_is_a_boolean_derived_from_the_filename():
    assert serialize_user(_row(avatar_filename="a.png"))["has_avatar"] is True
    assert serialize_user(_row(avatar_filename=None))["has_avatar"] is False


# created_at is nullable in the row mapping, and a formatter that assumed a
# datetime would raise instead of answering.
def test_created_at_is_iso_or_none():
    from datetime import datetime

    assert serialize_user(_row(created_at=datetime(2026, 1, 2, 3, 4, 5)))[
        "created_at"
    ] == "2026-01-02T03:04:05"
    assert serialize_user(_row(created_at=None))["created_at"] is None


def test_the_list_envelope_carries_the_pagination_metadata():
    response = format_user_list_response([_row(), _row(id=8)], total=25, page=2, per_page=10)

    assert response["type"] == "User"
    assert response["count"] == 2
    assert response["total"] == 25
    assert response["page"] == 2
    assert response["per_page"] == 10
    assert response["total_pages"] == 3
    assert len(response["attributes"]) == 2


# total_pages must be 0 rather than 1 for an empty set, matching how the refund
# listing already answers.
def test_total_pages_is_zero_when_there_is_nothing():
    assert format_user_list_response([], total=0, page=1, per_page=10)["total_pages"] == 0
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `cd Refund-api && pytest src/controllers/user_serializer_test.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'src.controllers.user_serializer'`

- [ ] **Step 3: Implementar**

```python
# Refund-api/src/controllers/user_serializer.py
import math
from typing import Optional


# One place turning a users row into the API's public user shape, for the same
# reason refund_serializer.py exists: two use cases (list and detail) produce
# the SAME shape from the SAME source, and two copies is how one of them keeps
# a field the other dropped.
#
# Here that risk is not cosmetic. The row carries `password` — a bcrypt hash —
# so this function is the boundary that keeps it out of every response. It
# builds a NEW dict and names each field explicitly instead of deleting keys
# from the row: a column added to the users table later stays invisible until
# somebody adds it here on purpose.
def serialize_user(user: dict) -> dict:
    return {
        "id": user["id"],
        "name": user["name"],
        "email": user["email"],
        "role": user["role"],
        # The client only needs to know whether to show a picture or the
        # initials gradient; it fetches the image from GET /users/{id}/avatar.
        "has_avatar": bool(user["avatar_filename"]),
        "created_at": _iso(user.get("created_at")),
    }


def format_user_list_response(users: list, total: int, page: int, per_page: int) -> dict:
    return {
        "type": "User",
        "count": len(users),
        "total": total,
        "page": page,
        "per_page": per_page,
        # 0 rather than 1 for an empty set, matching the refund listing.
        "total_pages": math.ceil(total / per_page) if total else 0,
        "attributes": [serialize_user(user) for user in users],
    }


def _iso(created_at) -> Optional[str]:
    return created_at.isoformat() if created_at else None
```

- [ ] **Step 4: Rodar e ver passar**

Run: `cd Refund-api && pytest src/controllers/user_serializer_test.py -v`
Expected: PASS — 6 testes

- [ ] **Step 5: Commit**

```bash
cd Refund-api && git add src/controllers/user_serializer.py src/controllers/user_serializer_test.py
git commit -m "feat: add the public user shape, with the password kept out by construction"
```

---

## Task 2: `select_users` no repositório

**Files:**
- Modify: `Refund-api/src/models/repositories/users_repository.py`
- Modify: `Refund-api/src/models/repositories/interfaces/users_repository_interface.py`
- Create: `Refund-api/src/models/repositories/users_repository_select_users_test.py`

**Interfaces:**
- Produces: `UsersRepository.select_users(page: int, per_page: int, name: Optional[str] = None) -> tuple[list[dict], int]`, devolvendo `(rows, total)`. Consumida pela Task 3.

- [ ] **Step 1: Escrever o teste que falha**

```python
# Refund-api/src/models/repositories/users_repository_select_users_test.py
from unittest.mock import AsyncMock, MagicMock
import pytest
from .users_repository import UsersRepository


# A connection handler whose session returns `total` for the count query and
# `rows` for the page query, in that order — the same order select_users runs
# them. Mocked because this asserts the SQL we intended to build; the real
# PostgreSQL behaviour is covered by the integration suite.
def _handler(rows, total):
    session = AsyncMock()
    count_result = MagicMock()
    count_result.scalar_one.return_value = total
    page_result = MagicMock()
    page_result.fetchall.return_value = rows
    session.execute.side_effect = [count_result, page_result]

    connect = MagicMock()
    connect.return_value.__aenter__ = AsyncMock(return_value=session)
    connect.return_value.__aexit__ = AsyncMock(return_value=False)
    handler = MagicMock()
    handler.connect = connect
    return handler, session


def _row(user_id, name):
    row = MagicMock()
    row._mapping = {  # pylint: disable=protected-access
        "id": user_id, "name": name, "email": f"{name}@example.com",
        "password": "hash", "role": "standard",
        "avatar_filename": None, "created_at": None,
    }
    return row


@pytest.mark.asyncio
async def test_it_returns_the_rows_as_dicts_and_the_total():
    handler, _ = _handler([_row(1, "ana"), _row(2, "bruno")], total=2)

    users, total = await UsersRepository(handler).select_users(page=1, per_page=10)

    assert total == 2
    assert [user["name"] for user in users] == ["ana", "bruno"]
    # Plain dicts, not row objects: the serializer indexes them by key.
    assert isinstance(users[0], dict)


@pytest.mark.asyncio
async def test_it_offsets_by_page():
    handler, session = _handler([], total=0)

    await UsersRepository(handler).select_users(page=3, per_page=10)

    page_query = str(session.execute.call_args_list[1].args[0])
    assert "LIMIT" in page_query and "OFFSET" in page_query


@pytest.mark.asyncio
async def test_it_orders_by_name_with_id_as_the_tiebreaker():
    handler, session = _handler([], total=0)

    await UsersRepository(handler).select_users(page=1, per_page=10)

    page_query = str(session.execute.call_args_list[1].args[0])
    # Two keys, not one: without the tiebreaker, two people with the same name
    # have no guaranteed order, so LIMIT/OFFSET can show one of them on two
    # pages and the other on none.
    assert "ORDER BY users.name ASC, users.id" in page_query


@pytest.mark.asyncio
async def test_the_name_filter_is_a_case_insensitive_partial_match():
    handler, session = _handler([], total=0)

    await UsersRepository(handler).select_users(page=1, per_page=10, name="an")

    assert "lower(users.name) LIKE lower" in str(session.execute.call_args_list[1].args[0])


@pytest.mark.asyncio
async def test_the_count_honours_the_same_filter_as_the_page():
    handler, session = _handler([], total=0)

    await UsersRepository(handler).select_users(page=1, per_page=10, name="an")

    # A count that ignored the filter would make total_pages promise pages the
    # page query can never fill.
    assert "lower(users.name) LIKE lower" in str(session.execute.call_args_list[0].args[0])


@pytest.mark.asyncio
async def test_an_empty_name_is_not_a_filter():
    handler, session = _handler([], total=0)

    await UsersRepository(handler).select_users(page=1, per_page=10, name="")

    assert "LIKE" not in str(session.execute.call_args_list[1].args[0])
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `cd Refund-api && pytest src/models/repositories/users_repository_select_users_test.py -v`
Expected: FAIL — `AttributeError: 'UsersRepository' object has no attribute 'select_users'`

- [ ] **Step 3: Implementar**

Adicionar ao topo de `users_repository.py` o import de `func`:

```python
from sqlalchemy import func, insert, select, update
```

Adicionar o método na classe `UsersRepository`:

```python
    async def select_users(
        self, page: int, per_page: int, name: Optional[str] = None
    ) -> tuple[list[dict], int]:
        async with self.__db_connection.connect() as session:
            filters = []
            if name:
                filters.append(Users.c.name.ilike(f"%{name}%"))

            # Counted with the SAME filters as the page: a total that ignored
            # them would make total_pages promise pages the page query cannot
            # fill.
            total_query = (
                select(func.count())  # pylint: disable=not-callable
                .select_from(Users)
                .where(*filters)
            )
            total = (await session.execute(total_query)).scalar_one()

            query = (
                select(Users)
                .where(*filters)
                # Tiebreaker on id for the same reason as
                # RefundsRepository.__order_by: PostgreSQL guarantees no order
                # among rows whose sort key ties, and with LIMIT/OFFSET a tie
                # can put one row on two pages while another never appears.
                # Namesakes are ordinary, so this tie is not hypothetical.
                .order_by(Users.c.name.asc(), Users.c.id.asc())
                .limit(per_page)
                .offset((page - 1) * per_page)
            )
            rows = (await session.execute(query)).fetchall()

            return [dict(row._mapping) for row in rows], total
```

E declarar na interface, em `interfaces/users_repository_interface.py`:

```python
    @abstractmethod
    async def select_users(
        self, page: int, per_page: int, name: Optional[str] = None
    ) -> tuple[list[dict], int]:
        pass
```

- [ ] **Step 4: Rodar e ver passar**

Run: `cd Refund-api && pytest src/models/repositories/users_repository_select_users_test.py -v`
Expected: PASS — 6 testes

- [ ] **Step 5: Commit**

```bash
cd Refund-api && git add src/models/repositories/users_repository.py \
  src/models/repositories/interfaces/users_repository_interface.py \
  src/models/repositories/users_repository_select_users_test.py
git commit -m "feat: let the users repository page and search by name"
```

---

## Task 3: `UserListerController` — 403 antes do banco

**Files:**
- Create: `Refund-api/src/controllers/user_lister_controller.py`
- Create: `Refund-api/src/controllers/interfaces/user_lister_controller_interface.py`
- Create: `Refund-api/src/controllers/user_lister_controller_test.py`

**Interfaces:**
- Consumes: `UsersRepository.select_users` (Task 2), `format_user_list_response` (Task 1).
- Produces: `UserListerController(users_repository).list(page: int, per_page: int, role: str, name: Optional[str] = None) -> dict`. Consumida pela Task 5.

- [ ] **Step 1: Escrever o teste que falha**

```python
# Refund-api/src/controllers/user_lister_controller_test.py
from unittest.mock import AsyncMock
import pytest
from src.errors.types.http_forbidden_error import HttpForbiddenError
from .user_lister_controller import UserListerController


def _repository(rows=None, total=0):
    repository = AsyncMock()
    repository.select_users.return_value = (rows or [], total)
    return repository


def _row(user_id=1, name="Ana"):
    return {
        "id": user_id, "name": name, "email": "ana@example.com",
        "password": "hash", "role": "standard",
        "avatar_filename": None, "created_at": None,
    }


@pytest.mark.asyncio
async def test_an_admin_gets_the_serialized_list():
    controller = UserListerController(_repository([_row()], total=1))

    response = await controller.list(page=1, per_page=10, role="admin")

    assert response["type"] == "User"
    assert response["total"] == 1
    assert response["attributes"][0]["name"] == "Ana"
    # Goes through serialize_user rather than handing the row over.
    assert "password" not in response["attributes"][0]


@pytest.mark.asyncio
async def test_a_standard_user_is_forbidden():
    with pytest.raises(HttpForbiddenError):
        await UserListerController(_repository()).list(page=1, per_page=10, role="standard")


# The important half of the rule: refusing AFTER querying would still expose
# how many users exist through timing, and would run a query for a request that
# was never allowed. Same idiom as refund_reviewer_controller.py:30.
@pytest.mark.asyncio
async def test_the_repository_is_never_reached_for_a_standard_user():
    repository = _repository()

    with pytest.raises(HttpForbiddenError):
        await UserListerController(repository).list(page=1, per_page=10, role="standard")

    repository.select_users.assert_not_called()


@pytest.mark.asyncio
async def test_the_name_filter_reaches_the_repository():
    repository = _repository()

    await UserListerController(repository).list(page=2, per_page=5, role="admin", name="an")

    repository.select_users.assert_awaited_once_with(page=2, per_page=5, name="an")
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `cd Refund-api && pytest src/controllers/user_lister_controller_test.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'src.controllers.user_lister_controller'`

- [ ] **Step 3: Implementar**

```python
# Refund-api/src/controllers/interfaces/user_lister_controller_interface.py
from abc import ABC, abstractmethod
from typing import Optional


class UserListerControllerInterface(ABC):

    @abstractmethod
    async def list(
        self, page: int, per_page: int, role: str, name: Optional[str] = None
    ) -> dict:
        pass
```

```python
# Refund-api/src/controllers/user_lister_controller.py
from typing import Optional
from src.models.repositories.interfaces.users_repository_interface import (
    UsersRepositoryInterface,
)
from src.controllers.interfaces.user_lister_controller_interface import (
    UserListerControllerInterface,
)
from src.controllers.user_serializer import format_user_list_response
from src.errors.types.http_forbidden_error import HttpForbiddenError


class UserListerController(UserListerControllerInterface):
    def __init__(self, users_repository: UsersRepositoryInterface) -> None:
        self.__users_repository = users_repository

    async def list(
        self, page: int, per_page: int, role: str, name: Optional[str] = None
    ) -> dict:
        # Refused BEFORE touching the database, the same idiom the reviewer and
        # payer controllers use. Refusing after querying would run work for a
        # request that was never allowed, and the response time would still
        # tell an outsider roughly how many users exist.
        #
        # 403 here, not 404: a listing reveals nothing about any particular id,
        # so it can be honest about the missing permission. The single-user
        # lookup (BR-025) answers 404 precisely because a 403 there would
        # confirm that the id exists.
        if role != "admin":
            raise HttpForbiddenError("Only administrators can list users")

        users, total = await self.__users_repository.select_users(
            page=page, per_page=per_page, name=name
        )

        return format_user_list_response(users, total, page, per_page)
```

- [ ] **Step 4: Rodar e ver passar**

Run: `cd Refund-api && pytest src/controllers/user_lister_controller_test.py -v`
Expected: PASS — 4 testes

- [ ] **Step 5: Commit**

```bash
cd Refund-api && git add src/controllers/user_lister_controller.py \
  src/controllers/interfaces/user_lister_controller_interface.py \
  src/controllers/user_lister_controller_test.py
git commit -m "feat: list users for admins only, refused before any query runs"
```

---

## Task 4: `UserFinderController` — 404 para quem não pode ver

**Files:**
- Create: `Refund-api/src/controllers/user_finder_controller.py`
- Create: `Refund-api/src/controllers/interfaces/user_finder_controller_interface.py`
- Create: `Refund-api/src/controllers/user_finder_controller_test.py`

**Interfaces:**
- Consumes: `UsersRepository.select_user_by_id` (já existia), `serialize_user` (Task 1).
- Produces: `UserFinderController(users_repository).find(user_id: int, role: str) -> dict`. Consumida pela Task 5.

- [ ] **Step 1: Escrever o teste que falha**

```python
# Refund-api/src/controllers/user_finder_controller_test.py
from unittest.mock import AsyncMock
import pytest
from src.errors.types.http_not_found_error import HttpNotFoundError
from .user_finder_controller import UserFinderController


def _repository(user=None):
    repository = AsyncMock()
    repository.select_user_by_id.return_value = user
    return repository


def _user():
    return {
        "id": 7, "name": "Ana", "email": "ana@example.com",
        "password": "hash", "role": "standard",
        "avatar_filename": None, "created_at": None,
    }


@pytest.mark.asyncio
async def test_an_admin_gets_the_serialized_user():
    response = await UserFinderController(_repository(_user())).find(user_id=7, role="admin")

    assert response["type"] == "User"
    assert response["count"] == 1
    assert response["attributes"]["name"] == "Ana"
    assert "password" not in response["attributes"]


# 404 and not 403: a 403 would confirm that user 7 exists. The two tests below
# must be indistinguishable from the caller's side — that is the point.
@pytest.mark.asyncio
async def test_a_standard_user_gets_not_found():
    with pytest.raises(HttpNotFoundError):
        await UserFinderController(_repository(_user())).find(user_id=7, role="standard")


@pytest.mark.asyncio
async def test_a_missing_user_gets_not_found():
    with pytest.raises(HttpNotFoundError):
        await UserFinderController(_repository(None)).find(user_id=999, role="admin")


@pytest.mark.asyncio
async def test_the_repository_is_never_reached_for_a_standard_user():
    repository = _repository(_user())

    with pytest.raises(HttpNotFoundError):
        await UserFinderController(repository).find(user_id=7, role="standard")

    repository.select_user_by_id.assert_not_called()
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `cd Refund-api && pytest src/controllers/user_finder_controller_test.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'src.controllers.user_finder_controller'`

- [ ] **Step 3: Implementar**

```python
# Refund-api/src/controllers/interfaces/user_finder_controller_interface.py
from abc import ABC, abstractmethod


class UserFinderControllerInterface(ABC):

    @abstractmethod
    async def find(self, user_id: int, role: str) -> dict:
        pass
```

```python
# Refund-api/src/controllers/user_finder_controller.py
from src.models.repositories.interfaces.users_repository_interface import (
    UsersRepositoryInterface,
)
from src.controllers.interfaces.user_finder_controller_interface import (
    UserFinderControllerInterface,
)
from src.controllers.user_serializer import serialize_user
from src.errors.types.http_not_found_error import HttpNotFoundError


class UserFinderController(UserFinderControllerInterface):
    def __init__(self, users_repository: UsersRepositoryInterface) -> None:
        self.__users_repository = users_repository

    async def find(self, user_id: int, role: str) -> dict:
        # 404 and not 403, the same choice refund_stats_finder_controller.py:19
        # makes: answering 403 would confirm that this id exists to somebody who
        # is not allowed to know. Checked before the query for the same reason
        # as the lister — no work for a request that was never allowed.
        if role != "admin":
            raise HttpNotFoundError("User not found")

        user = await self.__users_repository.select_user_by_id(user_id)

        # Deliberately the same error as the branch above, so "you may not see
        # this" and "this does not exist" are indistinguishable from outside.
        if not user:
            raise HttpNotFoundError("User not found")

        return {"type": "User", "count": 1, "attributes": serialize_user(user)}
```

- [ ] **Step 4: Rodar e ver passar**

Run: `cd Refund-api && pytest src/controllers/user_finder_controller_test.py -v`
Expected: PASS — 4 testes

- [ ] **Step 5: Commit**

```bash
cd Refund-api && git add src/controllers/user_finder_controller.py \
  src/controllers/interfaces/user_finder_controller_interface.py \
  src/controllers/user_finder_controller_test.py
git commit -m "feat: find one user for admins, answering 404 to everyone else"
```

---

## Task 5: Views, composers e as duas rotas

**Files:**
- Create: `Refund-api/src/views/user_lister_view.py`, `Refund-api/src/views/user_finder_view.py`
- Create: `Refund-api/src/main/composer/user_lister_composer.py`, `Refund-api/src/main/composer/user_finder_composer.py`
- Modify: `Refund-api/src/main/routes/user_routes.py`
- Create: `Refund-api/src/main/routes/user_routes_test.py`

**Interfaces:**
- Consumes: as Tasks 3 e 4.
- Produces: `GET /users?page=&per_page=&name=` e `GET /users/{user_id}`.

- [ ] **Step 1: Escrever o teste que falha**

```python
# Refund-api/src/main/routes/user_routes_test.py
from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient
from src.main.server.server import app
from src.views.http_types.http_response import HttpResponse

client = TestClient(app)

# The dependency is overridden rather than a real token minted: these tests are
# about routing and wiring, not about JWT decoding, which auth_jwt already
# covers.
ADMIN = {"user_id": 1, "role": "admin"}


def _view(body):
    view = AsyncMock()
    view.handle.return_value = HttpResponse(body=body, status_code=200)
    return view


def _as_admin():
    from src.main.middlewares.auth_jwt import get_current_user

    app.dependency_overrides[get_current_user] = lambda: ADMIN


def teardown_function():
    app.dependency_overrides.clear()


def test_the_listing_route_passes_the_query_and_the_token_through():
    _as_admin()
    view = _view({"type": "User", "attributes": []})

    with patch("src.main.routes.user_routes.user_lister_composer", return_value=view):
        response = client.get("/users?page=2&per_page=5&name=an")

    assert response.status_code == 200
    request = view.handle.call_args.args[0]
    assert request.query == {"page": 2, "per_page": 5, "name": "an"}
    assert request.token_info == ADMIN


def test_the_listing_route_defaults_page_and_per_page():
    _as_admin()
    view = _view({"type": "User", "attributes": []})

    with patch("src.main.routes.user_routes.user_lister_composer", return_value=view):
        client.get("/users")

    assert view.handle.call_args.args[0].query == {"page": 1, "per_page": 10, "name": None}


# Bounds come from FastAPI's Query(ge=, le=), which is why this cycle adds no
# validator: there is no whitelist to express.
def test_the_listing_route_rejects_out_of_range_pagination():
    _as_admin()
    assert client.get("/users?page=0").status_code == 422
    assert client.get("/users?per_page=101").status_code == 422


def test_the_detail_route_passes_the_path_param_through():
    _as_admin()
    view = _view({"type": "User", "count": 1, "attributes": {}})

    with patch("src.main.routes.user_routes.user_finder_composer", return_value=view):
        response = client.get("/users/7")

    assert response.status_code == 200
    assert view.handle.call_args.args[0].path_params == {"user_id": 7}


# The routes added here must not swallow the two that already existed under the
# same {user_id} prefix. Asserting the SPECIFIC composer is the one invoked is
# what proves FastAPI matched the more specific path.
def test_the_detail_route_does_not_shadow_the_avatar_route():
    _as_admin()
    view = _view({"url": "http://x/f.png", "media_type": "image/png"})

    with patch("src.main.routes.user_routes.avatar_finder_composer", return_value=view) as avatar:
        client.get("/users/7/avatar")

    assert avatar.called


def test_the_detail_route_does_not_shadow_the_refund_stats_route():
    _as_admin()
    view = _view({"type": "RefundStats", "user_id": 7, "by_status": {}})

    with patch("src.main.routes.user_routes.refund_stats_finder_composer", return_value=view) as stats:
        client.get("/users/7/refund-stats")

    assert stats.called
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `cd Refund-api && pytest src/main/routes/user_routes_test.py -v`
Expected: FAIL — os dois primeiros com 404 (a rota `/users` não existe) e o `patch` do composer com `AttributeError`

- [ ] **Step 3: Implementar**

```python
# Refund-api/src/views/user_lister_view.py
from src.controllers.interfaces.user_lister_controller_interface import (
    UserListerControllerInterface,
)
from src.views.http_types.http_request import HttpRequest
from src.views.http_types.http_response import HttpResponse
from src.errors.error_handler import error_handler


class UserListerView:
    def __init__(self, controller: UserListerControllerInterface) -> None:
        self.__controller = controller

    async def handle(self, http_request: HttpRequest) -> HttpResponse:
        try:
            # No validator call here, unlike RefundListerView: page and per_page
            # bounds are enforced by FastAPI's Query on the route, and this
            # endpoint has no whitelisted parameter to check.
            response = await self.__controller.list(
                page=http_request.query["page"],
                per_page=http_request.query["per_page"],
                role=http_request.token_info["role"],
                name=http_request.query.get("name"),
            )
            return HttpResponse(body=response, status_code=200)
        except Exception as e:  # noqa: BLE001 - error_handler maps to a response
            error_handler(e)
```

```python
# Refund-api/src/views/user_finder_view.py
from src.controllers.interfaces.user_finder_controller_interface import (
    UserFinderControllerInterface,
)
from src.views.http_types.http_request import HttpRequest
from src.views.http_types.http_response import HttpResponse
from src.errors.error_handler import error_handler


class UserFinderView:
    def __init__(self, controller: UserFinderControllerInterface) -> None:
        self.__controller = controller

    async def handle(self, http_request: HttpRequest) -> HttpResponse:
        try:
            response = await self.__controller.find(
                user_id=http_request.path_params["user_id"],
                role=http_request.token_info["role"],
            )
            return HttpResponse(body=response, status_code=200)
        except Exception as e:  # noqa: BLE001 - error_handler maps to a response
            error_handler(e)
```

```python
# Refund-api/src/main/composer/user_lister_composer.py
from src.models.settings.database_connection_handler import database_connection_handler
from src.models.repositories.users_repository import UsersRepository
from src.controllers.user_lister_controller import UserListerController
from src.views.user_lister_view import UserListerView


def user_lister_composer():
    repository = UsersRepository(database_connection_handler)
    controller = UserListerController(repository)
    view = UserListerView(controller)
    return view
```

```python
# Refund-api/src/main/composer/user_finder_composer.py
from src.models.settings.database_connection_handler import database_connection_handler
from src.models.repositories.users_repository import UsersRepository
from src.controllers.user_finder_controller import UserFinderController
from src.views.user_finder_view import UserFinderView


def user_finder_composer():
    repository = UsersRepository(database_connection_handler)
    controller = UserFinderController(repository)
    view = UserFinderView(controller)
    return view
```

Em `user_routes.py`, adicionar aos imports:

```python
from typing import Optional
from fastapi import APIRouter, Depends, Query, UploadFile, File
from src.main.composer.user_lister_composer import user_lister_composer
from src.main.composer.user_finder_composer import user_finder_composer
```

E as duas rotas. **A de listagem vai antes das de `{user_id}`** por legibilidade;
o caminho `""` não colide com `/{user_id}` de nenhum modo, e o teste do Step 1
prova isso:

```python
@user_routes.get("")
async def list_users(
    page: int = Query(1, ge=1),
    per_page: int = Query(10, ge=1, le=100),
    name: Optional[str] = Query(None),
    token_info: dict = Depends(get_current_user),
):
    # No sort/order here: the order is fixed at name ASC in the repository, so
    # there is no whitelist to express and therefore no validator — see
    # UserListerView.
    http_request = HttpRequest(
        query={"page": page, "per_page": per_page, "name": name},
        token_info=token_info,
    )
    view = user_lister_composer()
    response = await view.handle(http_request)
    return JSONResponse(content=response.body, status_code=response.status_code)


@user_routes.get("/{user_id}")
async def get_user(user_id: int, token_info: dict = Depends(get_current_user)):
    http_request = HttpRequest(path_params={"user_id": user_id}, token_info=token_info)
    view = user_finder_composer()
    response = await view.handle(http_request)
    return JSONResponse(content=response.body, status_code=response.status_code)
```

- [ ] **Step 4: Rodar e ver passar**

Run: `cd Refund-api && pytest src/main/routes/user_routes_test.py -v && pytest -q`
Expected: PASS — 6 testes novos, e a suíte inteira acima de 341

- [ ] **Step 5: `pylint` e commit**

```bash
cd Refund-api && pylint src; echo $?   # 0 é aprovação
git add src/views/user_lister_view.py src/views/user_finder_view.py \
  src/main/composer/user_lister_composer.py src/main/composer/user_finder_composer.py \
  src/main/routes/user_routes.py src/main/routes/user_routes_test.py
git commit -m "feat: expose GET /users and GET /users/{id}"
```

---

## Task 6: Contrato e documentação canônica

**Files:**
- Modify: `Refund-api/src/test_integration/contract_test.py`
- Create: `Refund-api/contract/users.json` (gerado, não escrito à mão)
- Create: `Refund-api/docs/use-cases/UC-015-list-users.md`, `UC-016-view-user.md`
- Modify: `Refund-api/docs/index.md`, `Refund-api/docs/business-rules.md`

**Interfaces:**
- Produces: `contract/users.json` com as chaves `userList` e `userDetail`, copiado na Task 8 para o frontend.

- [ ] **Step 1: Estender a captura do contrato**

Em `contract_test.py`, adicionar `"users"` ao `CONTRACT_PATHS`:

```python
CONTRACT_PATHS = {
    "refunds": pathlib.Path("contract/refunds.json"),
    "app": pathlib.Path("contract/app.json"),
    # A third file, landing in the frontend's team feature for the same
    # boundaries reason the other two are split: each half goes where the
    # schemas that validate it live.
    "users": pathlib.Path("contract/users.json"),
}
```

Trocar a assinatura do teste para receber também a fixture de admin, e capturar
as duas respostas novas:

```python
@pytest.mark.integration
def test_the_contract_file_matches_what_the_api_actually_returns(authenticated, admin_headers):
    client, headers, user_id = authenticated
    ...
    # Captured with admin_headers, not `headers`: both routes are admin-only.
    # With both fixtures active there are two users (Ana and Chefe), so the
    # list snapshot has more than one row.
    users_contract = {
        "userList": client.get("/users", headers=admin_headers).json(),
        "userDetail": client.get(f"/users/{user_id}", headers=admin_headers).json(),
    }
```

E incluir `("users", users_contract)` na tupla do laço de comparação.

- [ ] **Step 2: Subir o banco e gerar**

Run: `cd Refund-api && docker compose up -d && pytest -m integration -v`
Expected: FAIL na primeira execução, com a mensagem do próprio teste dizendo que
`contract/users.json` estava obsoleto e **foi regerado**. Conferir o diff.

- [ ] **Step 3: Rodar de novo para ver estabilizar**

Run: `cd Refund-api && pytest -m integration -v`
Expected: PASS — o arquivo agora casa com o que a API responde

- [ ] **Step 4: Escrever a documentação canônica**

`UC-015-list-users.md` e `UC-016-view-user.md` seguindo a forma dos UC existentes
(ator, pré-condições, fluxo principal, fluxos de exceção, resposta). Pontos que
**precisam** estar escritos:

- UC-015: ator é o administrador; `page`, `per_page` (1–100) e `name` (busca
  parcial, case-insensitive); ordem fixa `name ASC`; resposta com
  `{type, count, total, page, per_page, total_pages, attributes}`; **403** para
  usuário padrão.
- UC-016: ator é o administrador; resposta `{type, count, attributes}`; **404**
  tanto para usuário padrão quanto para id inexistente, e a razão.

Em `business-rules.md`, após a BR-024:

```markdown
## BR-025 — Acesso ao diretório de usuários

Somente administradores podem listar usuários ou consultar um usuário
específico.

A listagem responde **403**: ela não revela nada sobre um id em particular, então
pode ser honesta sobre a falta de permissão.

A consulta individual responde **404**, igual ao que responde para um id que não
existe. Um 403 ali confirmaria a existência daquele id a quem não pode vê-lo — a
mesma escolha registrada na BR-013 e aplicada em UC-014.
```

E as duas entradas em `docs/index.md`, na seção de casos de uso.

- [ ] **Step 5: Commit**

```bash
cd Refund-api && git add contract/users.json src/test_integration/contract_test.py \
  docs/use-cases/UC-015-list-users.md docs/use-cases/UC-016-view-user.md \
  docs/index.md docs/business-rules.md
git commit -m "docs: capture the users contract and record BR-025"
```

---

## Task 7: Extrair `RefundStatsPanel` do `RequesterPanel`

O corte que a §5 do spec decidiu. Feito **antes** da feature `team` porque a
página do membro depende dele, e feito num commit próprio para que qualquer
mudança de comportamento na tela de revisão apareça isolada.

**Files:**
- Create: `Refund-FrontEnd/src/features/refunds/components/RefundStatsPanel.tsx`
- Create: `Refund-FrontEnd/src/features/refunds/components/RefundStatsPanel.test.tsx`
- Modify: `Refund-FrontEnd/src/features/refunds/components/RequesterPanel.tsx`
- Modify: `Refund-FrontEnd/src/features/refunds/index.ts`
- Modify: `Refund-FrontEnd/src/locales/pt-BR.json`, `Refund-FrontEnd/src/locales/en-US.json`

**Interfaces:**
- Produces: `RefundStatsPanel` com as props `{ userId: number; userName: string; viewer: RefundViewer | null; currentRefundId?: number; headerActions?: ReactNode }`, exportado pela fachada. Consumido pela Task 11.

- [ ] **Step 1: Escrever o teste que falha**

```tsx
// Refund-FrontEnd/src/features/refunds/components/RefundStatsPanel.test.tsx
import { describe, expect, it } from "vitest";
import { screen } from "@testing-library/react";
import { createMemoryRouter, RouterProvider } from "react-router";
import { render } from "@/test/utils";
import RefundStatsPanel from "./RefundStatsPanel";

const VIEWER = { id: 99, role: "admin" as const };

function renderPanel(props: Partial<React.ComponentProps<typeof RefundStatsPanel>> = {}) {
  const router = createMemoryRouter(
    [
      {
        path: "/",
        element: (
          <RefundStatsPanel userId={1} userName="Ana" viewer={VIEWER} {...props} />
        ),
      },
    ],
    { initialEntries: ["/"] }
  );
  return render(<RouterProvider router={router} />);
}

describe("RefundStatsPanel", () => {
  // The member page has no "current refund", so the highlight must be absent
  // rather than defaulting to the first row.
  it("marks no row as current when currentRefundId is omitted", async () => {
    renderPanel();
    expect(await screen.findByRole("list")).toBeInTheDocument();
    expect(document.querySelector('[aria-current="page"]')).toBeNull();
  });

  it("marks the matching row as current when currentRefundId is given", async () => {
    renderPanel({ currentRefundId: 1 });
    const current = await screen.findByRole("link", { current: "page" });
    expect(current).toBeInTheDocument();
  });

  // headerActions is a slot, so an omitted slot renders nothing at all — the
  // component never decides whether arrows exist.
  it("renders no header actions when the slot is empty", async () => {
    renderPanel();
    await screen.findByRole("list");
    expect(screen.queryByTestId("panel-actions")).toBeNull();
  });

  it("renders whatever the header actions slot contains", async () => {
    renderPanel({ headerActions: <button data-testid="panel-actions">ação</button> });
    expect(await screen.findByTestId("panel-actions")).toBeInTheDocument();
  });

  // The panel does not own a Card or a title: the caller wraps it. This is what
  // keeps the member page from showing the person's name twice.
  it("does not render the person's name as a heading", async () => {
    renderPanel();
    await screen.findByRole("list");
    expect(screen.queryByRole("heading", { name: "Ana" })).toBeNull();
  });
});
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `cd Refund-FrontEnd && npx vitest run src/features/refunds/components/RefundStatsPanel.test.tsx`
Expected: FAIL — `Failed to resolve import "./RefundStatsPanel"`

- [ ] **Step 3: Mover as quatro strings para os catálogos**

Em `pt-BR.json` e `en-US.json`, sob a chave `panel` (as duas com as mesmas
chaves, senão `catalogues.test.ts` quebra):

```json
"panel": {
  "requests": "Solicitações",
  "empty": "Nenhuma solicitação encontrada.",
  "listError": "Não foi possível carregar as solicitações.",
  "seeAll": "Ver todas as solicitações de {{name}} na Home"
}
```

Em `en-US.json`: `"Requests"`, `"No requests found."`,
`"Could not load the requests."`, `"See all of {{name}}'s requests on the Home"`.

- [ ] **Step 4: Criar o `RefundStatsPanel`**

Mover para o arquivo novo, **sem alterar comportamento**: o `STATUS_ORDER`, o
`lazy(() => import("./RefundDonutChart"))` **com o comentário que explica por que
o donut não é reexportado**, o `useRefundStats`, o `useRefunds`, o cálculo de
`currentIndex` e todo o bloco da rosca e da lista. As mudanças em relação ao
original são só estas:

- não há `Card`, `CardHeader` nem `CardTitle` — o arquivo começa no conteúdo;
- `currentRefundId` é `number | undefined`, e `isCurrent` passa a ser
  `currentRefundId !== undefined && refund.id === currentRefundId`;
- onde estavam as duas setas, entra `{headerActions}`;
- as quatro strings passam a `t("panel.requests")`, `t("panel.empty")`,
  `t("panel.listError")` e `t("panel.seeAll", { name: userName })`;
- `requester.id`/`requester.name` viram `userId`/`userName`.

O `currentIndex`, `previousRefund` e `nextRefund` **saem** deste arquivo: são
insumo das setas, que agora vivem no `RequesterPanel`.

- [ ] **Step 5: Reduzir o `RequesterPanel` a invólucro**

Ele mantém `NavigationArrow`, o cálculo de `currentIndex`/`previousRefund`/
`nextRefund` — e portanto precisa da lista, com o **mesmo** `useRefunds({ page:
1, perPage: REFUNDS_PER_PAGE, userId: requester.id })`, que o React Query serve
da mesma entrada de cache que o painel usa, sem segunda requisição — e passa a
renderizar:

```tsx
  return (
    <Card>
      <CardHeader>
        <CardTitle>{requester.name}</CardTitle>
      </CardHeader>
      <CardContent>
        <RefundStatsPanel
          userId={requester.id}
          userName={requester.name}
          viewer={viewer}
          currentRefundId={currentRefundId}
          headerActions={
            <div className="flex items-center gap-1">
              <NavigationArrow
                refund={previousRefund}
                viewer={viewer}
                label={t("review.previousRequest")}
              >
                <ChevronLeft className="size-4" aria-hidden />
              </NavigationArrow>
              <NavigationArrow
                refund={nextRefund}
                viewer={viewer}
                label={t("review.nextRequest")}
              >
                <ChevronRight className="size-4" aria-hidden />
              </NavigationArrow>
            </div>
          }
        />
      </CardContent>
    </Card>
  );
```

Na fachada `index.ts`, acrescentar — mantendo `RequesterPanel` e **sem** tocar no
donut:

```ts
// O núcleo compartilhado do painel do solicitante: rosca de contagens por
// status e a primeira página das solicitações de uma pessoa. Exportado porque a
// página do membro do time o usa direto, sem o cabeçalho e sem as setas de
// revisão. Faz o import() dinâmico do gráfico por dentro — é isso que mantém o
// chunk do nivo fora do bundle de entrada.
export { default as RefundStatsPanel } from "./components/RefundStatsPanel";
```

- [ ] **Step 6: Rodar tudo e ver passar**

Run: `cd Refund-FrontEnd && npx vitest run`
Expected: PASS — os 5 novos, e **os testes existentes de `RequesterPanel` e de
`PageRefundReview` passando sem alteração**. Se algum deles precisar mudar, a
extração alterou a tela de revisão: voltar e corrigir em vez de ajustar o teste.

- [ ] **Step 7: Conferir a divisão do bundle**

Run: `cd Refund-FrontEnd && npm run build`
Expected: uma linha `dist/assets/RefundDonutChart-*.js` ainda presente, e o
`index` **sem** ganhar ~74 kB.

- [ ] **Step 8: Commit**

```bash
cd Refund-FrontEnd && git add src/features/refunds/components/RefundStatsPanel.tsx \
  src/features/refunds/components/RefundStatsPanel.test.tsx \
  src/features/refunds/components/RequesterPanel.tsx \
  src/features/refunds/index.ts src/locales/pt-BR.json src/locales/en-US.json
git commit -m "refactor: extract the shared core of the requester panel"
```

---

## Task 8: Schemas, queries e hooks da feature `team`

**Files:**
- Create: `Refund-FrontEnd/src/features/team/schemas/user.ts`, `api/userQueries.ts`, `hooks/useUsers.ts`, `hooks/useUser.ts`, `constants/pagination.ts`, `index.ts`
- Create: `Refund-FrontEnd/src/features/team/contract/users.json` (cópia manual do gerado na Task 6)
- Create: `Refund-FrontEnd/src/features/team/schemas/user.test.ts`, `Refund-FrontEnd/src/features/team/contract.test.ts`

**Interfaces:**
- Produces: `userListQuery({page, perPage, name})`, `userDetailQuery(id)`, `useUsers`, `useUser`, `userListSearchParamsSchema`, `USERS_PER_PAGE`, e o tipo `TeamUser`. Consumidos pelas Tasks 9, 10 e 11.

- [ ] **Step 1: Escrever os testes que falham**

```ts
// Refund-FrontEnd/src/features/team/schemas/user.test.ts
import { describe, expect, it } from "vitest";
import { userListSearchParamsSchema, userSchema } from "./user";

describe("userSchema", () => {
  it("accepts the API's user shape", () => {
    expect(
      userSchema.parse({
        id: 1, name: "Ana", email: "ana@example.com",
        role: "standard", has_avatar: false, created_at: "2026-01-01T12:00:00",
      }).name
    ).toBe("Ana");
  });

  it("accepts a null created_at", () => {
    expect(
      userSchema.parse({
        id: 1, name: "Ana", email: "ana@example.com",
        role: "admin", has_avatar: true, created_at: null,
      }).created_at
    ).toBeNull();
  });

  it("rejects a role outside the two the API has", () => {
    expect(() =>
      userSchema.parse({
        id: 1, name: "Ana", email: "ana@example.com",
        role: "owner", has_avatar: false, created_at: null,
      })
    ).toThrow();
  });
});

describe("userListSearchParamsSchema", () => {
  // A mistyped URL parameter must fall back to the default instead of putting
  // the whole page into isError.
  it("falls back to page 1 for a non-numeric page", () => {
    expect(userListSearchParamsSchema.parse({ page: "abc" }).page).toBe(1);
  });

  it("treats a blank name as absent", () => {
    expect(userListSearchParamsSchema.parse({ name: "   " }).name).toBeUndefined();
  });

  it("trims the name", () => {
    expect(userListSearchParamsSchema.parse({ name: " ana " }).name).toBe("ana");
  });
});
```

```ts
// Refund-FrontEnd/src/features/team/contract.test.ts
import { describe, expect, it } from "vitest";
import contract from "./contract/users.json";
import { userListResponseSchema, userResponseSchema } from "./schemas/user";

// The contract file is captured from the real API by
// Refund-api/src/test_integration/contract_test.py. This asserts our schemas
// match what the API actually answers, not what we assumed it answers.
describe("the users contract", () => {
  it("matches userListResponseSchema", () => {
    expect(() => userListResponseSchema.parse(contract.userList)).not.toThrow();
  });

  it("matches userResponseSchema", () => {
    expect(() => userResponseSchema.parse(contract.userDetail)).not.toThrow();
  });

  // The whole point of the serializer: if the API ever starts sending the
  // hash, this fails here instead of in a browser.
  it("carries no password field", () => {
    expect(JSON.stringify(contract)).not.toContain("password");
  });
});
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `cd Refund-FrontEnd && npx vitest run src/features/team`
Expected: FAIL — `Failed to resolve import "./user"` e `"./contract/users.json"`

- [ ] **Step 3: Implementar os schemas**

```ts
// Refund-FrontEnd/src/features/team/schemas/user.ts
import { z } from "zod";

// Mirrors the two roles the API's users.role column actually holds. A third
// value must fail here rather than render as an unknown badge.
export const userRoleSchema = z.enum(["standard", "admin"]);

export const userSchema = z.object({
  id: z.number().int().positive(),
  name: z.string(),
  email: z.string(),
  role: userRoleSchema,
  has_avatar: z.boolean(),
  // Nullable for the same reason refund.created_at is: the column has a server
  // default, but the shape does not promise it.
  created_at: z.string().nullable(),
});

export const userResponseSchema = z.object({
  type: z.literal("User"),
  count: z.number().int().nonnegative(),
  attributes: userSchema,
});

export const userListResponseSchema = z.object({
  type: z.literal("User"),
  count: z.number().int().nonnegative(),
  total: z.number().int().nonnegative(),
  page: z.number().int().positive(),
  per_page: z.number().int().min(1).max(100),
  total_pages: z.number().int().nonnegative(),
  attributes: z.array(userSchema),
});

// `.catch()` per field: a URL is user-editable, so an invalid value falls back
// to the default instead of turning the page into an error state.
export const userListSearchParamsSchema = z.object({
  page: z.coerce.number().int().positive().catch(1),
  name: z
    .string()
    .trim()
    .transform((value) => value || undefined)
    .optional(),
});

export type TeamUser = z.output<typeof userSchema>;
export type UserRole = z.output<typeof userRoleSchema>;
export type UserListResponse = z.output<typeof userListResponseSchema>;
```

```ts
// Refund-FrontEnd/src/features/team/constants/pagination.ts
// Imported by BOTH the hook and the router loader, so the page size cannot
// drift between the prefetch and the render.
export const USERS_PER_PAGE = 10;
```

```ts
// Refund-FrontEnd/src/features/team/api/userQueries.ts
import { queryOptions } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { userListResponseSchema, userResponseSchema } from "../schemas/user";

interface UserListParams {
  page: number;
  perPage: number;
  name?: string;
}

// Hierarchical like refundKeys: everything derives from `all`, so invalidating
// ["users"] reaches lists and details at once.
export const userKeys = {
  all: ["users"] as const,
  lists: () => [...userKeys.all, "list"] as const,
  list: (params: UserListParams) => [...userKeys.lists(), params] as const,
  detail: (id: string) => [...userKeys.all, "detail", id] as const,
};

export function userListQuery(params: UserListParams) {
  return queryOptions({
    queryKey: userKeys.list(params),
    queryFn: async ({ signal }) => {
      const { data } = await api.get<unknown>("/users", {
        params: {
          page: params.page,
          per_page: params.perPage,
          // Omitted rather than sent empty, so the key and the request agree.
          name: params.name || undefined,
        },
        signal,
      });
      return userListResponseSchema.parse(data);
    },
  });
}

export function userDetailQuery(id: string) {
  return queryOptions({
    queryKey: userKeys.detail(id),
    queryFn: async ({ signal }) => {
      const { data } = await api.get<unknown>(`/users/${id}`, { signal });
      return userResponseSchema.parse(data).attributes;
    },
  });
}
```

```ts
// Refund-FrontEnd/src/features/team/hooks/useUsers.ts
import { useQuery } from "@tanstack/react-query";
import { userListQuery } from "../api/userQueries";
import { USERS_PER_PAGE } from "../constants/pagination";

export function useUsers({
  page,
  perPage = USERS_PER_PAGE,
  name,
}: {
  page: number;
  perPage?: number;
  name?: string;
}) {
  return useQuery(userListQuery({ page, perPage, name }));
}
```

```ts
// Refund-FrontEnd/src/features/team/hooks/useUser.ts
import { useQuery } from "@tanstack/react-query";
import { userDetailQuery } from "../api/userQueries";

export function useUser(id: string | undefined) {
  return useQuery({ ...userDetailQuery(id ?? ""), enabled: !!id });
}
```

```ts
// Refund-FrontEnd/src/features/team/index.ts
// Public API (façade) of the team feature. The rest of the app imports from
// "@/features/team", never from an internal path — eslint-plugin-boundaries
// enforces it. `userKeys` and the response schemas stay internal on purpose.

// Data-access layer: query options reused by the router loaders.
export { userListQuery, userDetailQuery } from "./api/userQueries";

// Hooks: the feature's data API for pages.
export { useUsers } from "./hooks/useUsers";
export { useUser } from "./hooks/useUser";

// URL search-params schema used by the team loader.
export { userListSearchParamsSchema } from "./schemas/user";
export type { TeamUser, UserRole } from "./schemas/user";

export { USERS_PER_PAGE } from "./constants/pagination";
```

- [ ] **Step 4: Copiar o contrato**

```bash
cp Refund-api/contract/users.json Refund-FrontEnd/src/features/team/contract/users.json
```

Cópia **manual e obrigatória**: cada CI só faz checkout de um repositório, e o
`contract_test.py` avisa que essa é justamente a lacuna que ele não cobre.

- [ ] **Step 5: Rodar e ver passar**

Run: `cd Refund-FrontEnd && npx vitest run src/features/team`
Expected: PASS — 9 testes

- [ ] **Step 6: Commit**

```bash
cd Refund-FrontEnd && git add src/features/team
git commit -m "feat: add the team feature's data layer, validated against the contract"
```

---

## Task 9: `UsersTable`

**Files:**
- Create: `Refund-FrontEnd/src/features/team/components/UsersTable.tsx`
- Create: `Refund-FrontEnd/src/features/team/components/UsersTable.test.tsx`
- Modify: `Refund-FrontEnd/src/features/team/index.ts`
- Modify: `Refund-FrontEnd/src/locales/pt-BR.json`, `en-US.json`

**Interfaces:**
- Consumes: `TeamUser` (Task 8).
- Produces: `UsersTable` com props `{ users: TeamUser[] }`, exportado pela fachada. Consumido pela Task 11.

- [ ] **Step 1: Escrever o teste que falha**

```tsx
// Refund-FrontEnd/src/features/team/components/UsersTable.test.tsx
import { describe, expect, it } from "vitest";
import { screen } from "@testing-library/react";
import { createMemoryRouter, RouterProvider } from "react-router";
import { render } from "@/test/utils";
import UsersTable from "./UsersTable";
import type { TeamUser } from "../schemas/user";

const USERS: TeamUser[] = [
  { id: 1, name: "Ana", email: "ana@example.com", role: "standard", has_avatar: false, created_at: "2026-01-02T03:04:05" },
  { id: 2, name: "Chefe", email: "chefe@example.com", role: "admin", has_avatar: false, created_at: null },
];

function renderTable(users = USERS) {
  const router = createMemoryRouter(
    [{ path: "/team", element: <UsersTable users={users} /> }],
    { initialEntries: ["/team"] }
  );
  return render(<RouterProvider router={router} />);
}

describe("UsersTable", () => {
  it("renders one row per user with name and email", () => {
    renderTable();
    expect(screen.getByText("Ana")).toBeInTheDocument();
    expect(screen.getByText("ana@example.com")).toBeInTheDocument();
  });

  it("renders the role as a label, not the raw value", () => {
    renderTable();
    expect(screen.getByText("Administrador")).toBeInTheDocument();
    expect(screen.getByText("Padrão")).toBeInTheDocument();
    expect(screen.queryByText("admin")).toBeNull();
  });

  // created_at is nullable, and a formatter that assumed a date would crash the
  // whole table over one row.
  it("falls back to a dash when created_at is null", () => {
    renderTable();
    expect(screen.getByText("—")).toBeInTheDocument();
  });

  it("links each row to that person's page", () => {
    renderTable();
    expect(screen.getByRole("link", { name: /Ana/ })).toHaveAttribute("href", "/team/1");
  });

  // The API accepts no sort parameter, so a clickable header would either do
  // nothing or sort only the 10 rows of the current page.
  it("has no sortable headers", () => {
    renderTable();
    const headers = screen.getAllByRole("columnheader");
    headers.forEach((header) => expect(header.querySelector("button")).toBeNull());
  });

  it("shows an empty message when there is nobody", () => {
    renderTable([]);
    expect(screen.getByText("Nenhum usuário encontrado.")).toBeInTheDocument();
  });
});
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `cd Refund-FrontEnd && npx vitest run src/features/team/components/UsersTable.test.tsx`
Expected: FAIL — `Failed to resolve import "./UsersTable"`

- [ ] **Step 3: Chaves de i18n**

Sob `team`, nos dois catálogos:

```json
"team": {
  "columnName": "Nome",
  "columnEmail": "E-mail",
  "columnRole": "Papel",
  "columnCreatedAt": "Membro desde",
  "roleAdmin": "Administrador",
  "roleStandard": "Padrão",
  "empty": "Nenhum usuário encontrado.",
  "searchLabel": "Buscar por nome",
  "searchPlaceholder": "Buscar pessoa",
  "loadError": "Não foi possível carregar os usuários."
}
```

Em `en-US.json`, os equivalentes (`"Name"`, `"Email"`, `"Role"`, `"Member since"`,
`"Administrator"`, `"Standard"`, `"No users found."`, `"Search by name"`,
`"Search person"`, `"Could not load the users."`).

- [ ] **Step 4: Implementar**

Criar `constants/roles.ts` na feature, no mesmo padrão de
`features/refunds/constants/status.ts` — mapa de chave de catálogo e variante do
design system, avaliado na importação, por isso guarda `labelKey` e não texto:

```ts
// Refund-FrontEnd/src/features/team/constants/roles.ts
import type { UserRole } from "../schemas/user";

// labelKey, not text: this module is evaluated at import time, before a locale
// exists. Same pattern as REFUND_STATUS and CATEGORIES.
export const USER_ROLE: Record<UserRole, { labelKey: string; variant: "default" | "secondary" }> = {
  admin: { labelKey: "team.roleAdmin", variant: "default" },
  standard: { labelKey: "team.roleStandard", variant: "secondary" },
};
```

E a tabela, com `getCoreRowModel` apenas, colunas `accessorKey`, `Badge` para o
papel, `formatDate` de `src/lib/format.ts` para a data (com `—` no `null`), e a
linha inteira envolvida num `Link` para `/team/${id}`. A mensagem de vazio ocupa
um `TableCell` com `colSpan` igual ao número de colunas, como
`RefundsTable.tsx` já faz.

Acrescentar à fachada:

```ts
// A listagem de usuários como tabela. Sem ordenação: a API não a aceita.
export { default as UsersTable } from "./components/UsersTable";
```

- [ ] **Step 5: Rodar e ver passar**

Run: `cd Refund-FrontEnd && npx vitest run src/features/team`
Expected: PASS — 15 testes na feature

- [ ] **Step 6: Commit**

```bash
cd Refund-FrontEnd && git add src/features/team src/locales/pt-BR.json src/locales/en-US.json
git commit -m "feat: render the team as a table"
```

---

## Task 10: `requireAdmin`, loaders, rotas e a sidebar

**Files:**
- Modify: `Refund-FrontEnd/src/router-loaders.ts`
- Modify: `Refund-FrontEnd/src/router.tsx`
- Modify: `Refund-FrontEnd/src/components/core/nav-items.tsx`
- Modify: `Refund-FrontEnd/src/components/core/Sidebar.tsx`
- Modify: `Refund-FrontEnd/src/components/core/Sidebar.test.tsx`
- Create: `Refund-FrontEnd/src/router-loaders.team.test.ts`
- Modify: `Refund-FrontEnd/src/locales/pt-BR.json`, `en-US.json`

**Interfaces:**
- Consumes: `userListQuery`, `userDetailQuery`, `userListSearchParamsSchema`, `USERS_PER_PAGE` (Task 8).
- Produces: `teamLoader`, `teamMemberLoader`, e o campo `adminOnly?: boolean` em `NavItem`.

- [ ] **Step 1: Escrever o teste que falha**

```ts
// Refund-FrontEnd/src/router-loaders.team.test.ts
import { beforeEach, describe, expect, it } from "vitest";
import { TOKEN_STORAGE_KEY, USER_STORAGE_KEY } from "./lib/api";
import { teamLoader } from "./router-loaders";

function signIn(role: "admin" | "standard") {
  localStorage.setItem(TOKEN_STORAGE_KEY, "token");
  localStorage.setItem(
    USER_STORAGE_KEY,
    JSON.stringify({ id: 1, name: "Ana", email: "ana@example.com", role })
  );
}

function loaderArgs(url: string) {
  return { request: new Request(url), params: {}, context: {} } as never;
}

describe("teamLoader", () => {
  beforeEach(() => localStorage.clear());

  // A UI guard, not a security one: the API is what refuses. This only avoids
  // offering a page that would be refused.
  it("redirects a standard user away", async () => {
    signIn("standard");
    const response = (await teamLoader(loaderArgs("http://localhost/team")).catch(
      (thrown) => thrown
    )) as Response;
    expect(response.status).toBe(302);
    expect(response.headers.get("location")).toBe("/");
  });

  it("strips a page parameter that equals the default", async () => {
    signIn("admin");
    const response = (await teamLoader(loaderArgs("http://localhost/team?page=1")).catch(
      (thrown) => thrown
    )) as Response;
    expect(response.headers.get("location")).toBe("/team");
  });

  it("returns the normalized params for an admin", async () => {
    signIn("admin");
    await expect(teamLoader(loaderArgs("http://localhost/team?name=ana"))).resolves.toMatchObject({
      page: 1,
      name: "ana",
    });
  });
});
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `cd Refund-FrontEnd && npx vitest run src/router-loaders.team.test.ts`
Expected: FAIL — `teamLoader is not a function`

- [ ] **Step 3: Implementar os loaders**

Em `router-loaders.ts`, extrair a guarda de papel e adicionar os dois loaders.
Reescrever o `if` do `reviewLoader` para usar a função nova, **sem mudar o
comportamento dele** (ele redireciona para o detalhe, não para a Home):

```ts
// Guarda de UI, não de segurança — a mesma ressalva do reviewLoader: quem
// protege os dados é a API, respondendo 403 na listagem e 404 na consulta
// (BR-025). Isto só evita OFERECER uma página que seria recusada.
function requireAdmin(): void {
  if (readStoredUser()?.role !== "admin") {
    throw redirect("/");
  }
}

export async function teamLoader({ request }: LoaderFunctionArgs) {
  requireSession();
  requireAdmin();

  const url = new URL(request.url);
  const { page, name } = userListSearchParamsSchema.parse({
    page: url.searchParams.get("page") ?? undefined,
    name: url.searchParams.get("name") ?? undefined,
  });

  const normalizedSearchParams = new URLSearchParams(url.searchParams);
  setOrDelete(normalizedSearchParams, "page", page > 1 ? String(page) : undefined);
  setOrDelete(normalizedSearchParams, "name", name);

  if (normalizedSearchParams.toString() !== url.searchParams.toString()) {
    const normalizedSearch = normalizedSearchParams.toString();
    throw redirect(`${url.pathname}${normalizedSearch ? `?${normalizedSearch}` : ""}`);
  }

  const queryParams = { page, perPage: USERS_PER_PAGE, name };

  await queryClient.ensureQueryData(userListQuery(queryParams));

  return queryParams;
}

export async function teamMemberLoader({ params }: LoaderFunctionArgs) {
  requireSession();
  requireAdmin();

  if (!params.id) {
    throw new Response("User ID is required", { status: 400 });
  }

  await queryClient.ensureQueryData(userDetailQuery(params.id));

  return { id: params.id };
}
```

Importar de `@/features/team` o que for usado, e no `reviewLoader` trocar a
condição para:

```ts
  if (readStoredUser()?.role !== "admin" || refund.user.id === readStoredUser()?.id) {
```

— **não**: manter o `session` local como está e apenas deixar o `reviewLoader`
intacto. `requireAdmin` redireciona para `/`, e o `reviewLoader` precisa
redirecionar para o detalhe, então **os dois não são a mesma função** e o
`reviewLoader` não deve chamá-la. Registrar isso num comentário para ninguém
"unificar" depois.

- [ ] **Step 4: Rotas, nav e sidebar**

Em `router.tsx`, dentro do bloco com `ErrorBoundary: ContentError`:

```tsx
                  {
                    path: "/team",
                    loader: teamLoader,
                    handle: { titleKey: "routes.team" },
                    lazy: async () => ({ Component: (await import("./pages/PageTeam")).default }),
                  },
                  {
                    path: "/team/:id",
                    loader: teamMemberLoader,
                    handle: { titleKey: "routes.teamMember" },
                    lazy: async () => ({
                      Component: (await import("./pages/PageTeamMember")).default,
                    }),
                  },
```

Chaves `routes.team` ("Time") e `routes.teamMember` ("Membro do time") nos dois
catálogos.

Em `nav-items.tsx`: `enabled: true` no item de Time e o campo novo na interface:

```ts
  // Some da sidebar para quem não é admin. A rota também tem guarda própria
  // (teamLoader); esta prop só evita mostrar um caminho que seria recusado.
  adminOnly?: boolean;
```

Em `Sidebar.tsx`, filtrar antes do `map` — o componente já tem acesso ao usuário
para desenhar o cabeçalho:

```tsx
const items = NAV_ITEMS.filter((item) => !item.adminOnly || user?.role === "admin");
```

- [ ] **Step 5: Ajustar o teste da sidebar**

Em `Sidebar.test.tsx`, o `toHaveLength(3)` passa a **2**, e entram dois casos:

```tsx
  // Time is admin-only, so a standard user must not even see the path.
  it("hides admin-only items from a standard user", () => {
    renderSidebar({ role: "standard" });
    expect(screen.queryByText("Time")).toBeNull();
  });

  it("shows admin-only items to an admin", () => {
    renderSidebar({ role: "admin" });
    expect(screen.getByRole("link", { name: "Time" })).toBeInTheDocument();
  });
```

Ajustar `renderSidebar` para aceitar o papel se ele ainda não aceitar.

- [ ] **Step 6: Rodar e ver passar**

Run: `cd Refund-FrontEnd && npx vitest run && npm run typecheck && npm run lint`
Expected: PASS nas três, com 0 erros e 0 warnings no lint

- [ ] **Step 7: Commit**

```bash
cd Refund-FrontEnd && git add src/router-loaders.ts src/router-loaders.team.test.ts src/router.tsx \
  src/components/core/nav-items.tsx src/components/core/Sidebar.tsx \
  src/components/core/Sidebar.test.tsx src/locales/pt-BR.json src/locales/en-US.json
git commit -m "feat: route /team behind an admin guard and unhide it in the sidebar"
```

---

## Task 11: As duas páginas

**Files:**
- Create: `Refund-FrontEnd/src/pages/PageTeam.tsx`, `PageTeamMember.tsx`
- Create: `Refund-FrontEnd/src/pages/PageTeam.test.tsx`, `PageTeam.a11y.test.tsx`, `PageTeamMember.test.tsx`
- Modify: `Refund-FrontEnd/src/test/msw/handlers.ts`

**Interfaces:**
- Consumes: `useUsers`, `useUser`, `UsersTable`, `USERS_PER_PAGE` (Tasks 8 e 9); `RefundStatsPanel` (Task 7); `teamLoader`, `teamMemberLoader` (Task 10).

- [ ] **Step 1: Handlers do MSW**

Em `src/test/msw/handlers.ts`, adicionar `userFixture` e os dois handlers,
honrando `name` e `page` — um handler que ignora a busca provaria só que a
página renderiza uma lista:

```ts
export const userFixture = {
  id: 1, name: "Ana", email: "ana@example.com",
  role: "standard" as const, has_avatar: false, created_at: "2026-01-02T03:04:05",
};

const USERS = [
  userFixture,
  { ...userFixture, id: 2, name: "Chefe", email: "chefe@example.com", role: "admin" as const },
];

http.get("*/users", ({ request }) => {
  const url = new URL(request.url);
  const name = url.searchParams.get("name")?.toLowerCase();
  const page = Number(url.searchParams.get("page") ?? 1);
  const perPage = Number(url.searchParams.get("per_page") ?? USERS_PER_PAGE);
  const filtered = name
    ? USERS.filter((user) => user.name.toLowerCase().includes(name))
    : USERS;
  const start = (page - 1) * perPage;
  const attributes = filtered.slice(start, start + perPage);
  return HttpResponse.json({
    type: "User", count: attributes.length, total: filtered.length,
    page, per_page: perPage,
    total_pages: filtered.length ? Math.ceil(filtered.length / perPage) : 0,
    attributes,
  });
}),

http.get("*/users/:id", ({ params }) => {
  const user = USERS.find((candidate) => candidate.id === Number(params.id));
  if (!user) return new HttpResponse(null, { status: 404 });
  return HttpResponse.json({ type: "User", count: 1, attributes: user });
}),
```

⚠️ O handler de `*/users/:id` precisa vir **depois** de `*/users/:id/avatar` e
`*/users/:id/refund-stats` se o MSW resolver por ordem de registro; conferir que
os testes existentes de avatar e stats continuam passando.

- [ ] **Step 2: Escrever os testes que falham**

```tsx
// Refund-FrontEnd/src/pages/PageTeam.test.tsx
import { describe, expect, it } from "vitest";
import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { createMemoryRouter, RouterProvider } from "react-router";
import { render } from "@/test/utils";
import PageTeam from "./PageTeam";
import { teamLoader } from "../router-loaders";
import { TOKEN_STORAGE_KEY, USER_STORAGE_KEY } from "@/lib/api";

function renderPage(entry = "/team") {
  localStorage.setItem(TOKEN_STORAGE_KEY, "token");
  localStorage.setItem(
    USER_STORAGE_KEY,
    JSON.stringify({ id: 9, name: "Chefe", email: "c@example.com", role: "admin" })
  );
  const router = createMemoryRouter(
    [{ path: "/team", loader: teamLoader, Component: PageTeam }],
    { initialEntries: [entry] }
  );
  return { router, ...render(<RouterProvider router={router} />) };
}

describe("PageTeam", () => {
  it("lists the users", async () => {
    renderPage();
    expect(await screen.findByText("Ana")).toBeInTheDocument();
    expect(screen.getByText("Chefe")).toBeInTheDocument();
  });

  // Debounced search writes to the URL, which is what re-runs the loader — the
  // same mechanism the Home uses.
  it("writes the debounced search into the URL", async () => {
    const { router } = renderPage();
    await screen.findByText("Ana");

    await userEvent.type(screen.getByLabelText("Buscar por nome"), "ana");

    await waitFor(
      () => expect(router.state.location.search).toContain("name=ana"),
      { timeout: 2000 }
    );
  });
});
```

```tsx
// Refund-FrontEnd/src/pages/PageTeamMember.test.tsx
// (mesma montagem, com teamMemberLoader e a rota "/team/:id")
describe("PageTeamMember", () => {
  it("shows the person's identity", async () => {
    renderMember("/team/1");
    expect(await screen.findByRole("heading", { name: "Ana" })).toBeInTheDocument();
    expect(screen.getByText("ana@example.com")).toBeInTheDocument();
  });

  // The reason RefundStatsPanel does not own a Card or a title.
  it("does not show the name twice", async () => {
    renderMember("/team/1");
    await screen.findByRole("heading", { name: "Ana" });
    expect(screen.getAllByRole("heading", { name: "Ana" })).toHaveLength(1);
  });

  it("renders the person's requests panel", async () => {
    renderMember("/team/1");
    expect(await screen.findByText("Solicitações")).toBeInTheDocument();
  });
});
```

```tsx
// Refund-FrontEnd/src/pages/PageTeam.a11y.test.tsx
// Mesma forma de PageHome.a11y.test.tsx: renderiza, espera o conteúdo e roda
// axe, esperando nenhuma violação.
```

- [ ] **Step 3: Rodar e ver falhar**

Run: `cd Refund-FrontEnd && npx vitest run src/pages/PageTeam`
Expected: FAIL — `Failed to resolve import "./PageTeam"`

- [ ] **Step 4: Implementar as páginas**

`PageTeam.tsx`: lê `useLoaderData<typeof teamLoader>()`, chama `useUsers`, e
monta busca + `UsersTable` + paginação. A busca é um sub-componente local
`TeamSearch`, **copiando a forma do `RefundSearch`** (`PageHome.tsx:40-73`):
`useState` local, `useDebouncedValue`, `useEffect` escrevendo na URL com
`replace: true`, submit no Enter sem replace, e montado com `key={name ?? ""}`.
Paginação com os mesmos botões e `disabled` de `PageHome`. Carregando →
`Skeleton`; erro → `<p role="alert" className="text-sm text-destructive">`.

`PageTeamMember.tsx`: `useParams()` → `useUser(id)`; um `Card` de identidade com
`CardTitle` = nome (o **único** `heading` com o nome), e-mail, `Badge` do papel e
"Membro desde"; abaixo, um segundo `Card` com `<RefundStatsPanel userId={user.id}
userName={user.name} viewer={viewer} />`, onde `viewer` vem de `useAuth()` — a
página é camada `app`, então pode.

- [ ] **Step 5: Rodar e ver passar**

Run: `cd Refund-FrontEnd && npx vitest run`
Expected: PASS — suíte inteira, acima de 318

- [ ] **Step 6: Commit**

```bash
cd Refund-FrontEnd && git add src/pages/PageTeam.tsx src/pages/PageTeamMember.tsx \
  src/pages/PageTeam.test.tsx src/pages/PageTeam.a11y.test.tsx \
  src/pages/PageTeamMember.test.tsx src/test/msw/handlers.ts
git commit -m "feat: add the team list and the team member pages"
```

---

## Task 12: Fechamento — verificação, documentação e navegador

**Files:**
- Modify: `Refund-api/docs/plans/current-state.md`, `Refund-api/docs/learning-path-progress.md`
- Modify: `Refund-api/docs/plans/2026-08-11-tres-telas-panorama.md`

- [ ] **Step 1: As quatro verificações do frontend, na ordem do CI**

```bash
cd Refund-FrontEnd && npm run typecheck && npm run lint && npx vitest run && npm run build
```
Expected: as quatro passando, lint com 0 erros e 0 warnings.

- [ ] **Step 2: Conferir a divisão do bundle na saída do build**

Ler a saída do `npm run build`: a linha `dist/assets/RefundDonutChart-*.js` ainda
existe e o `index` não ganhou ~74 kB. Registrar os números.

- [ ] **Step 3: As verificações do backend**

```bash
cd Refund-api && pytest && pylint src; echo $?
docker compose up -d && pytest -m integration
```
Expected: `pytest` verde, `pylint` saindo **0**, integração verde.

- [ ] **Step 4: Checklist de navegador, com a API em `localhost:3333`**

- [ ] Admin: "Time" aparece na sidebar, sem o selo "em breve"
- [ ] A lista pagina, e a busca por nome filtra com o atraso do debounce
- [ ] Clicar numa pessoa abre `/team/:id`; o nome aparece **uma** vez
- [ ] O painel mostra a rosca e as solicitações daquela pessoa
- [ ] Usuário padrão: "Time" **não** aparece; digitar `/team` redireciona para `/`
- [ ] Tela de revisão **inalterada**: destaque da linha atual e as duas setas
- [ ] Claro e escuro
- [ ] 390 × 844, com `document.documentElement.scrollWidth === clientWidth`

- [ ] **Step 5: Fechar a documentação**

- `current-state.md`: as duas rotas novas, a feature `team`, o `RefundStatsPanel`
  e as suítes atualizadas.
- `learning-path-progress.md`: entrada `## Ciclo de feature — Diretório do time
  (2026-08-11)`, na forma dos ciclos pós-trilha.
- No panorama, marcar o **Ciclo 1 como concluído** e anotar as duas correções que
  este ciclo trouxe: o validator que não era necessário e a extração que o reuso
  direto exigiu.

- [ ] **Step 6: Commit final**

```bash
cd Refund-api && git add docs/ && git commit -m "docs: close the team directory cycle"
```

## Self-Review

**Cobertura do spec**, seção por seção: §1 → Tasks 2, 3, 5; §2 → Tasks 4, 5;
§3 → Task 6; §4 → Task 6; §5 → Task 7; §6 → Tasks 8, 9; §7 → Tasks 10, 11.
Testes do spec → distribuídos por task, com o do `password` na Task 1 e na 8.
Verificação do spec → Task 12.

**Consistência de nomes** entre tasks: `serialize_user` e
`format_user_list_response` (T1) são consumidos em T3 e T4;
`select_users(page, per_page, name) -> (rows, total)` (T2) é chamado em T3 com
exatamente esses argumentos nomeados; `RefundStatsPanel` (T7) é montado em T11
com as cinco props declaradas; `USERS_PER_PAGE` (T8) é usado em T10 e nos
handlers de T11; `userListQuery`/`userDetailQuery` (T8) são os nomes usados nos
loaders de T10.

**Riscos anotados para quem executar:**

- A Task 7 é a única que mexe em código que já funciona. O critério de sucesso é
  negativo: **nenhum** teste existente de `RequesterPanel` ou `PageRefundReview`
  muda. Se mudar, a extração alterou a tela de revisão.
- A Task 6 exige Docker. Sem ele, `users.json` não é gerado e a Task 8 não tem o
  que copiar — pare e diga, em vez de escrever o JSON à mão: um contrato inventado
  é pior que nenhum, porque parece verificado.
- Na Task 10, `requireAdmin` **não** substitui a checagem do `reviewLoader`: os
  destinos de redirecionamento são diferentes.
