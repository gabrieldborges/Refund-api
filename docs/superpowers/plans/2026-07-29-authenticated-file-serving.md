# Servir arquivos com autenticação (backend) — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fechar os mounts estáticos e servir comprovantes e avatares por rotas autenticadas, com autorização por caso de uso.

**Architecture:** Preserva a Clean Architecture existente (rota → composer → view → controller → repository/driver). O driver ganha `read()` devolvendo bytes, mantendo a interface independente de onde o arquivo mora. Um serializador compartilhado passa a produzir a forma de resposta dos três casos de uso de leitura de reembolso.

**Tech Stack:** Python 3.9, FastAPI, SQLAlchemy 2.0 (Core, async), PostgreSQL (Neon), Alembic, pytest + pytest-asyncio, pylint.

**Spec:** [`../specs/2026-07-29-authenticated-file-serving-design.md`](../specs/2026-07-29-authenticated-file-serving-design.md)

## Global Constraints

- **Python 3.9.** Use `Optional[X]`, **nunca** `X | None`.
- **Não há `python` no PATH e os shebangs do `.venv` estão QUEBRADOS.** Invoque tudo como módulo: `.venv/bin/python -m pytest`, `.venv/bin/python -m pylint`. **Nunca** `.venv/bin/pytest`.
- **Todo arquivo novo com lógica ganha um `_test.py` ao lado.** Composers (`src/main/composer/`) não têm teste, pela convenção vigente.
- **Testes assíncronos exigem `@pytest.mark.asyncio` explícito.**
- **Comentários em inglês**, curtos, explicando a razão — não o óbvio.
- **`pylint src` deve terminar em 10.00/10.** Baseline atual. Se um pragma for necessário, espelhe a convenção do arquivo vizinho e explique em uma linha.
- **`pytest` 100% verde.** Baseline: **154 testes**.
- `docs/` é escrito em português; código e comentários em inglês.

> **A ordem das tasks é deliberada.** As rotas novas nascem **antes** de os mounts serem removidos, e a remoção de `filename` da resposta vem **por último**. Assim a árvore nunca fica num estado em que o comprovante é inalcançável.

---

### Task 1: `FileStorage.read`

**Files:**
- Modify: `src/drivers/file_storage.py`, `src/drivers/interfaces/file_storage_interface.py`, `src/drivers/file_storage_test.py`

**Interfaces:**
- Produces: `read(filename: str) -> bytes` em `FileStorage` e `FileStorageInterface`, consumido pelas Tasks 2 e 3

- [ ] **Step 1: Escrever os testes que falham**

Acrescente em `src/drivers/file_storage_test.py` (o arquivo já usa a fixture `tmp_path` do pytest; siga o mesmo estilo):

```python
def test_read_returns_the_stored_bytes(tmp_path):
    storage = FileStorage(str(tmp_path))
    filename = storage.save("comprovante.jpg", b"conteudo binario")

    assert storage.read(filename) == b"conteudo binario"


# The driver lets FileNotFoundError surface instead of inventing a domain error:
# it does not know what "missing" means to whoever called it. The controller
# translates it into the 404 that fits its use case.
def test_read_raises_when_the_file_does_not_exist(tmp_path):
    storage = FileStorage(str(tmp_path))

    with pytest.raises(FileNotFoundError):
        storage.read("nao-existe.jpg")
```

Acrescente `import pytest` ao topo do arquivo se ainda não estiver lá.

- [ ] **Step 2: Rodar e confirmar que falham**

```bash
.venv/bin/python -m pytest src/drivers/file_storage_test.py -v
```
Esperado: `AttributeError: 'FileStorage' object has no attribute 'read'`.

- [ ] **Step 3: Implementar**

Em `src/drivers/file_storage.py`, entre `save` e `delete`:

```python
    def read(self, filename: str) -> bytes:
        # Returns bytes rather than a path on purpose: a path would assert that
        # the file lives on a local filesystem, which is exactly the claim the
        # object-storage item (22) will invalidate. The 4MB upload ceiling keeps
        # holding a whole file in memory cheap.
        path = os.path.join(self.__directory, filename)

        with open(path, "rb") as file:
            return file.read()
```

E na interface:

```python
    @abstractmethod
    def read(self, filename: str) -> bytes:
        pass
```

- [ ] **Step 4: Rodar e confirmar que passam**

```bash
.venv/bin/python -m pytest src/drivers/file_storage_test.py -v
```

- [ ] **Step 5: Verificar e commitar**

```bash
.venv/bin/python -m pytest -q
.venv/bin/python -m pylint src
git add src/drivers
git commit -m "feat: let the file storage read a stored file"
```
Esperado: 156 testes, pylint 10.00/10.

---

### Task 2: Rota autenticada do comprovante

**Files:**
- Create: `src/controllers/interfaces/receipt_finder_controller_interface.py`, `src/controllers/receipt_finder_controller.py`, `src/controllers/receipt_finder_controller_test.py`
- Create: `src/views/receipt_finder_view.py`, `src/views/receipt_finder_view_test.py`
- Create: `src/main/composer/receipt_finder_composer.py`
- Modify: `src/main/routes/refund_routes.py`

**Interfaces:**
- Consumes: `FileStorageInterface.read` (Task 1); `RefundsRepositoryInterface.select_refund_by_id`, que devolve `{id, name, category, amount_in_cents, filename, status, created_at, user: {id, name, avatar_filename}}`
- Produces: `GET /refunds/{refund_id}/receipt`; `ReceiptFinderController(refunds_repository, receipt_storage)` com `async find(refund_id: int, user_id: int, role: str) -> dict` devolvendo `{"content": bytes, "media_type": str}`

- [ ] **Step 1: Escrever os testes do controller**

`src/controllers/receipt_finder_controller_test.py`:

```python
# pylint: disable=w0621
from unittest.mock import AsyncMock, MagicMock
import pytest
from src.errors.types.http_not_found_error import HttpNotFoundError
from .receipt_finder_controller import ReceiptFinderController


@pytest.fixture
def mock_repository():
    repository = MagicMock()
    repository.select_refund_by_id = AsyncMock(
        return_value={
            "id": 1, "name": "Almoço", "filename": "abc.jpg", "status": "pending",
            "user": {"id": 7, "name": "Gabriel", "avatar_filename": None},
        }
    )
    return repository


@pytest.fixture
def mock_storage():
    storage = MagicMock()
    storage.read = MagicMock(return_value=b"bytes do arquivo")
    return storage


@pytest.mark.asyncio
async def test_owner_receives_the_receipt(mock_repository, mock_storage):
    controller = ReceiptFinderController(mock_repository, mock_storage)

    response = await controller.find(refund_id=1, user_id=7, role="standard")

    mock_storage.read.assert_called_once_with("abc.jpg")
    assert response["content"] == b"bytes do arquivo"
    assert response["media_type"] == "image/jpeg"


@pytest.mark.asyncio
async def test_admin_receives_any_receipt(mock_repository, mock_storage):
    controller = ReceiptFinderController(mock_repository, mock_storage)

    response = await controller.find(refund_id=1, user_id=999, role="admin")

    assert response["content"] == b"bytes do arquivo"


# 404, never 403: a 403 would confirm the id is real and let an attacker
# enumerate refunds. Same rule as RefundFinderController (BR-013).
@pytest.mark.asyncio
async def test_someone_elses_receipt_is_not_found(mock_repository, mock_storage):
    controller = ReceiptFinderController(mock_repository, mock_storage)

    with pytest.raises(HttpNotFoundError):
        await controller.find(refund_id=1, user_id=999, role="standard")

    mock_storage.read.assert_not_called()


@pytest.mark.asyncio
async def test_missing_refund_is_not_found(mock_repository, mock_storage):
    mock_repository.select_refund_by_id = AsyncMock(return_value=None)
    controller = ReceiptFinderController(mock_repository, mock_storage)

    with pytest.raises(HttpNotFoundError):
        await controller.find(refund_id=999, user_id=7, role="standard")

    mock_storage.read.assert_not_called()


# The row survived but the file did not (the inverse of an orphaned file, which
# item 21 keeps possible). The same message keeps it indistinguishable from an
# unknown id.
@pytest.mark.asyncio
async def test_missing_file_on_disk_is_not_found(mock_repository, mock_storage):
    mock_storage.read = MagicMock(side_effect=FileNotFoundError())
    controller = ReceiptFinderController(mock_repository, mock_storage)

    with pytest.raises(HttpNotFoundError):
        await controller.find(refund_id=1, user_id=7, role="standard")


@pytest.mark.asyncio
async def test_media_type_comes_from_the_stored_extension(mock_repository, mock_storage):
    mock_repository.select_refund_by_id = AsyncMock(
        return_value={"id": 1, "filename": "doc.pdf", "user": {"id": 7}}
    )
    controller = ReceiptFinderController(mock_repository, mock_storage)

    response = await controller.find(refund_id=1, user_id=7, role="standard")

    assert response["media_type"] == "application/pdf"
```

- [ ] **Step 2: Rodar e confirmar que falham**

```bash
.venv/bin/python -m pytest src/controllers/receipt_finder_controller_test.py -v
```
Esperado: `ModuleNotFoundError`.

- [ ] **Step 3: Criar a interface**

`src/controllers/interfaces/receipt_finder_controller_interface.py`:

```python
from abc import ABC, abstractmethod


class ReceiptFinderControllerInterface(ABC):

    @abstractmethod
    async def find(self, refund_id: int, user_id: int, role: str) -> dict:
        pass
```

- [ ] **Step 4: Implementar o controller**

`src/controllers/receipt_finder_controller.py`:

```python
# pylint: disable=duplicate-code
# Shares its "404 for both missing and not-yours" guard with
# RefundFinderController; a shared helper would be more machinery than the
# problem needs, and the rule is deliberately identical.
import mimetypes
from src.models.repositories.interfaces.refunds_repository_interface import RefundsRepositoryInterface
from src.drivers.interfaces.file_storage_interface import FileStorageInterface
from src.controllers.interfaces.receipt_finder_controller_interface import (
    ReceiptFinderControllerInterface,
)
from src.errors.types.http_not_found_error import HttpNotFoundError


class ReceiptFinderController(ReceiptFinderControllerInterface):
    def __init__(
        self,
        refunds_repository: RefundsRepositoryInterface,
        receipt_storage: FileStorageInterface,
    ) -> None:
        self.__refunds_repository = refunds_repository
        self.__receipt_storage = receipt_storage

    async def find(self, refund_id: int, user_id: int, role: str) -> dict:
        refund = await self.__refunds_repository.select_refund_by_id(refund_id)

        # Same rule as RefundFinderController: 404 for both "doesn't exist" and
        # "not yours", never a 403 that would confirm the id is real.
        if not refund or (role != "admin" and refund["user"]["id"] != user_id):
            raise HttpNotFoundError("Refund not found")

        filename = refund["filename"]

        try:
            content = self.__receipt_storage.read(filename)
        except FileNotFoundError as exception:
            # The row survived but the file did not. Reusing the message keeps
            # this indistinguishable from an unknown id.
            raise HttpNotFoundError("Refund not found") from exception

        return {"content": content, "media_type": self.__media_type(filename)}

    def __media_type(self, filename: str) -> str:
        # Derived from the stored extension, never from a client header — the
        # same reason the upload validators refuse to trust Content-Type.
        guessed, _ = mimetypes.guess_type(filename)
        return guessed or "application/octet-stream"
```

- [ ] **Step 5: Escrever o teste da view**

`src/views/receipt_finder_view_test.py`:

```python
# pylint: disable=w0621
from unittest.mock import AsyncMock, MagicMock
import pytest
from src.views.http_types.http_request import HttpRequest
from .receipt_finder_view import ReceiptFinderView


@pytest.fixture
def mock_controller():
    controller = MagicMock()
    controller.find = AsyncMock(return_value={"content": b"x", "media_type": "image/jpeg"})
    return controller


@pytest.mark.asyncio
async def test_the_view_passes_the_token_identity_to_the_controller(mock_controller):
    view = ReceiptFinderView(mock_controller)
    http_request = HttpRequest(
        path_params={"refund_id": 1},
        token_info={"user_id": 7, "role": "standard"},
    )

    http_response = await view.handle(http_request)

    mock_controller.find.assert_awaited_once_with(refund_id=1, user_id=7, role="standard")
    assert http_response.status_code == 200
    assert http_response.body["content"] == b"x"
```

- [ ] **Step 6: Implementar a view**

`src/views/receipt_finder_view.py`:

```python
from src.controllers.interfaces.receipt_finder_controller_interface import (
    ReceiptFinderControllerInterface,
)
from src.views.http_types.http_request import HttpRequest
from src.views.http_types.http_response import HttpResponse
from src.errors.error_handler import error_handler


class ReceiptFinderView:
    def __init__(self, controller: ReceiptFinderControllerInterface) -> None:
        self.__controller = controller

    async def handle(self, http_request: HttpRequest) -> HttpResponse:
        try:
            response = await self.__controller.find(
                refund_id=http_request.path_params["refund_id"],
                user_id=http_request.token_info["user_id"],
                role=http_request.token_info["role"],
            )
            # The body carries raw bytes plus their media type instead of a JSON
            # dict: the route turns it into a binary Response, not a JSONResponse.
            return HttpResponse(body=response, status_code=200)
        except Exception as e:
            error_handler(e)
```

- [ ] **Step 7: Criar o composer**

`src/main/composer/receipt_finder_composer.py`:

```python
from src.configs.global_config import upload_info
from src.models.settings.database_connection_handler import database_connection_handler
from src.models.repositories.refunds_repository import RefundsRepository
from src.drivers.file_storage import FileStorage
from src.controllers.receipt_finder_controller import ReceiptFinderController
from src.views.receipt_finder_view import ReceiptFinderView


def receipt_finder_composer():
    repository = RefundsRepository(database_connection_handler)
    storage = FileStorage(upload_info["UPLOAD_DIR"])
    controller = ReceiptFinderController(repository, storage)
    view = ReceiptFinderView(controller)
    return view
```

- [ ] **Step 8: Adicionar a rota**

Em `src/main/routes/refund_routes.py`, acrescente `Response` ao import do FastAPI e o composer novo, e insira a rota **antes** de `@refund_routes.get("/{refund_id}")`:

```python
@refund_routes.get("/{refund_id}/receipt")
async def get_refund_receipt(
    refund_id: int,
    token_info: dict = Depends(get_current_user),
):
    http_request = HttpRequest(path_params={"refund_id": refund_id}, token_info=token_info)
    view = receipt_finder_composer()
    response = await view.handle(http_request)
    # Binary, so not a JSONResponse. No Content-Disposition: the file is meant
    # to be displayed, and the client decides how.
    return Response(
        content=response.body["content"],
        media_type=response.body["media_type"],
        status_code=response.status_code,
    )
```

A ordem importa aqui: `/{refund_id}/receipt` precisa vir antes de `/{refund_id}` para o FastAPI não tratar `receipt` como um id.

- [ ] **Step 9: Rodar, verificar e commitar**

```bash
.venv/bin/python -m pytest -q
.venv/bin/python -m pylint src
git add src/controllers src/views src/main
git commit -m "feat: serve refund receipts through an authenticated route"
```

---

### Task 3: Rota autenticada do avatar

**Files:**
- Create: `src/controllers/interfaces/avatar_finder_controller_interface.py`, `src/controllers/avatar_finder_controller.py`, `src/controllers/avatar_finder_controller_test.py`
- Create: `src/views/avatar_finder_view.py`, `src/views/avatar_finder_view_test.py`
- Create: `src/main/composer/avatar_finder_composer.py`
- Modify: `src/main/routes/user_routes.py`

**Interfaces:**
- Consumes: `FileStorageInterface.read` (Task 1); `UsersRepositoryInterface.select_user_by_id`
- Produces: `GET /users/{user_id}/avatar`; `AvatarFinderController(users_repository, avatar_storage)` com `async find(user_id: int) -> dict` devolvendo `{"content": bytes, "media_type": str}`

**Nota de autorização:** ao contrário do comprovante, **qualquer usuário autenticado vê qualquer avatar** — ele já aparece para quem enxerga a lista, então não há o que vazar. O controller não recebe nem `role` nem a identidade de quem pede; a autenticação é feita pela dependência da rota.

- [ ] **Step 1: Escrever os testes do controller**

`src/controllers/avatar_finder_controller_test.py`:

```python
# pylint: disable=w0621
from unittest.mock import AsyncMock, MagicMock
import pytest
from src.errors.types.http_not_found_error import HttpNotFoundError
from .avatar_finder_controller import AvatarFinderController


@pytest.fixture
def mock_repository():
    repository = MagicMock()
    repository.select_user_by_id = AsyncMock(
        return_value={"id": 7, "name": "Gabriel", "avatar_filename": "foto.png"}
    )
    return repository


@pytest.fixture
def mock_storage():
    storage = MagicMock()
    storage.read = MagicMock(return_value=b"bytes da foto")
    return storage


# Any authenticated user may fetch any avatar, so the controller takes no
# identity of its own: it is not an authorization decision, only a lookup.
@pytest.mark.asyncio
async def test_any_users_avatar_can_be_fetched(mock_repository, mock_storage):
    controller = AvatarFinderController(mock_repository, mock_storage)

    response = await controller.find(user_id=7)

    mock_storage.read.assert_called_once_with("foto.png")
    assert response["content"] == b"bytes da foto"
    assert response["media_type"] == "image/png"


@pytest.mark.asyncio
async def test_user_without_a_picture_is_not_found(mock_repository, mock_storage):
    mock_repository.select_user_by_id = AsyncMock(
        return_value={"id": 7, "name": "Gabriel", "avatar_filename": None}
    )
    controller = AvatarFinderController(mock_repository, mock_storage)

    with pytest.raises(HttpNotFoundError):
        await controller.find(user_id=7)

    mock_storage.read.assert_not_called()


@pytest.mark.asyncio
async def test_unknown_user_is_not_found(mock_repository, mock_storage):
    mock_repository.select_user_by_id = AsyncMock(return_value=None)
    controller = AvatarFinderController(mock_repository, mock_storage)

    with pytest.raises(HttpNotFoundError):
        await controller.find(user_id=999)

    mock_storage.read.assert_not_called()


@pytest.mark.asyncio
async def test_missing_file_on_disk_is_not_found(mock_repository, mock_storage):
    mock_storage.read = MagicMock(side_effect=FileNotFoundError())
    controller = AvatarFinderController(mock_repository, mock_storage)

    with pytest.raises(HttpNotFoundError):
        await controller.find(user_id=7)
```

- [ ] **Step 2: Rodar e confirmar que falham**

```bash
.venv/bin/python -m pytest src/controllers/avatar_finder_controller_test.py -v
```

- [ ] **Step 3: Criar a interface**

`src/controllers/interfaces/avatar_finder_controller_interface.py`:

```python
from abc import ABC, abstractmethod


class AvatarFinderControllerInterface(ABC):

    @abstractmethod
    async def find(self, user_id: int) -> dict:
        pass
```

- [ ] **Step 4: Implementar o controller**

`src/controllers/avatar_finder_controller.py`:

```python
import mimetypes
from src.models.repositories.interfaces.users_repository_interface import UsersRepositoryInterface
from src.drivers.interfaces.file_storage_interface import FileStorageInterface
from src.controllers.interfaces.avatar_finder_controller_interface import (
    AvatarFinderControllerInterface,
)
from src.errors.types.http_not_found_error import HttpNotFoundError


class AvatarFinderController(AvatarFinderControllerInterface):
    def __init__(
        self,
        users_repository: UsersRepositoryInterface,
        avatar_storage: FileStorageInterface,
    ) -> None:
        self.__users_repository = users_repository
        self.__avatar_storage = avatar_storage

    async def find(self, user_id: int) -> dict:
        user = await self.__users_repository.select_user_by_id(user_id)

        # Unknown user and user without a picture answer the same 404: neither is
        # an error worth distinguishing, and both mean "there is no avatar here".
        if not user or not user["avatar_filename"]:
            raise HttpNotFoundError("Avatar not found")

        filename = user["avatar_filename"]

        try:
            content = self.__avatar_storage.read(filename)
        except FileNotFoundError as exception:
            raise HttpNotFoundError("Avatar not found") from exception

        return {"content": content, "media_type": self.__media_type(filename)}

    def __media_type(self, filename: str) -> str:
        # Derived from the stored extension, never from a client header.
        guessed, _ = mimetypes.guess_type(filename)
        return guessed or "application/octet-stream"
```

- [ ] **Step 5: Escrever o teste da view**

`src/views/avatar_finder_view_test.py`:

```python
# pylint: disable=w0621
from unittest.mock import AsyncMock, MagicMock
import pytest
from src.views.http_types.http_request import HttpRequest
from .avatar_finder_view import AvatarFinderView


@pytest.fixture
def mock_controller():
    controller = MagicMock()
    controller.find = AsyncMock(return_value={"content": b"x", "media_type": "image/png"})
    return controller


# The user id comes from the path, not the token: this endpoint serves any
# user's avatar to any authenticated caller.
@pytest.mark.asyncio
async def test_the_view_uses_the_path_user_id(mock_controller):
    view = AvatarFinderView(mock_controller)
    http_request = HttpRequest(
        path_params={"user_id": 13},
        token_info={"user_id": 7, "role": "standard"},
    )

    http_response = await view.handle(http_request)

    mock_controller.find.assert_awaited_once_with(user_id=13)
    assert http_response.status_code == 200
```

- [ ] **Step 6: Implementar a view**

`src/views/avatar_finder_view.py`:

```python
from src.controllers.interfaces.avatar_finder_controller_interface import (
    AvatarFinderControllerInterface,
)
from src.views.http_types.http_request import HttpRequest
from src.views.http_types.http_response import HttpResponse
from src.errors.error_handler import error_handler


class AvatarFinderView:
    def __init__(self, controller: AvatarFinderControllerInterface) -> None:
        self.__controller = controller

    async def handle(self, http_request: HttpRequest) -> HttpResponse:
        try:
            response = await self.__controller.find(
                user_id=http_request.path_params["user_id"]
            )
            return HttpResponse(body=response, status_code=200)
        except Exception as e:
            error_handler(e)
```

- [ ] **Step 7: Criar o composer**

`src/main/composer/avatar_finder_composer.py`:

```python
from src.configs.global_config import upload_info
from src.models.settings.database_connection_handler import database_connection_handler
from src.models.repositories.users_repository import UsersRepository
from src.drivers.file_storage import FileStorage
from src.controllers.avatar_finder_controller import AvatarFinderController
from src.views.avatar_finder_view import AvatarFinderView


def avatar_finder_composer():
    repository = UsersRepository(database_connection_handler)
    storage = FileStorage(upload_info["AVATAR_DIR"])
    controller = AvatarFinderController(repository, storage)
    view = AvatarFinderView(controller)
    return view
```

- [ ] **Step 8: Adicionar a rota**

Em `src/main/routes/user_routes.py`, acrescente `Response` ao import do FastAPI e o composer novo, e a rota:

```python
@user_routes.get("/{user_id}/avatar")
async def get_user_avatar(
    user_id: int,
    token_info: dict = Depends(get_current_user),  # pylint: disable=unused-argument
):
    http_request = HttpRequest(path_params={"user_id": user_id})
    view = avatar_finder_composer()
    response = await view.handle(http_request)
    return Response(
        content=response.body["content"],
        media_type=response.body["media_type"],
        status_code=response.status_code,
    )
```

`token_info` não é usado no corpo, mas a dependência **precisa continuar ali** — é ela que exige autenticação. O pragma explica isso ao pylint; acrescente um comentário de uma linha dizendo que a dependência existe pelo efeito colateral de autenticar.

- [ ] **Step 9: Rodar, verificar e commitar**

```bash
.venv/bin/python -m pytest -q
.venv/bin/python -m pylint src
git add src/controllers src/views src/main
git commit -m "feat: serve profile pictures through an authenticated route"
```

---

### Task 4: Remover os mounts estáticos

**Files:**
- Modify: `src/main/server/server.py`

**Interfaces:**
- Consumes: as rotas das Tasks 2 e 3, que já substituem o que os mounts serviam

- [ ] **Step 1: Remover os dois mounts**

Em `src/main/server/server.py`, apague as duas linhas:

```python
app.mount("/receipts", StaticFiles(directory=upload_info["UPLOAD_DIR"]), name="receipts")
app.mount("/avatars", StaticFiles(directory=upload_info["AVATAR_DIR"]), name="avatars")
```

Remova também o import `from fastapi.staticfiles import StaticFiles`, que fica sem uso. **Mantenha** o import de `upload_info` se ele ainda for usado em outro ponto do arquivo — confira antes de apagar.

Acrescente no lugar um comentário curto explicando por que não há mais mount:

```python
# Uploaded files are NOT served statically: the UUID filenames would be
# capability URLs, granting anyone who ever saw a link permanent access even
# after losing access to the refund. They go through authenticated routes
# instead (GET /refunds/{id}/receipt and GET /users/{id}/avatar).
```

- [ ] **Step 2: Subir o servidor e provar que o mount sumiu**

```bash
.venv/bin/python run.py
```
Em outro terminal, com um nome de arquivo real:

```bash
curl -s -o /dev/null -w "receipts sem token -> %{http_code}\n" \
  "http://localhost:3333/receipts/$(ls uploads/receipts | grep -v gitkeep | head -1)"
curl -s -o /dev/null -w "health -> %{http_code}\n" http://localhost:3333/health
```
Esperado: `receipts sem token -> 404` e `health -> 200`. O primeiro era **200** antes desta task — é a prova de que a mudança fez efeito. O segundo prova que o servidor subiu.

- [ ] **Step 3: Verificar e commitar**

```bash
.venv/bin/python -m pytest -q
.venv/bin/python -m pylint src
git add src/main/server/server.py
git commit -m "feat: stop serving uploaded files without authentication"
```

---

### Task 5: Serializador compartilhado

Tira `filename` das respostas e troca `avatar_filename` por `has_avatar`, num único lugar consumido pelos três casos de uso de leitura.

**Files:**
- Create: `src/controllers/refund_serializer.py`, `src/controllers/refund_serializer_test.py`
- Modify: `src/controllers/refund_lister_controller.py`, `src/controllers/refund_finder_controller.py`, `src/controllers/refund_creator_controller.py` e seus `_test.py`

**Interfaces:**
- Consumes: o dicionário que o repositório devolve, com `filename` e `user.avatar_filename`
- Produces: `serialize_refund(refund: dict) -> dict`, a forma de resposta única

> **A armadilha desta task.** `filename` **não** sai do que o repositório devolve — o `refund_deleter_controller` o lê para apagar o arquivo do disco. Ele sai apenas do que vira resposta HTTP. Não toque em `RefundsRepository.__to_refund`. Se você se pegar editando o repositório, pare.

- [ ] **Step 1: Escrever os testes do serializador**

`src/controllers/refund_serializer_test.py`:

```python
from datetime import datetime
from .refund_serializer import serialize_refund


def repository_row(**overrides) -> dict:
    row = {
        "id": 58,
        "name": "Estacionamento",
        "category": "transport",
        "amount_in_cents": 4500,
        "filename": "606771d4-abc.jpg",
        "status": "approved",
        "created_at": datetime(2026, 7, 28, 17, 0, 25),
        "user": {"id": 13, "name": "Validacao Visual", "avatar_filename": "foto.png"},
    }
    row.update(overrides)
    return row


# The stored filename is internal: the client fetches the file from
# GET /refunds/{id}/receipt and has no use for the storage name.
def test_the_storage_filename_is_not_exposed():
    assert "filename" not in serialize_refund(repository_row())


def test_avatar_filename_becomes_a_boolean():
    serialized = serialize_refund(repository_row())

    assert serialized["user"]["has_avatar"] is True
    assert "avatar_filename" not in serialized["user"]


# None means "no picture, show the gradient" — it must become False, not vanish.
def test_a_user_without_a_picture_has_avatar_false():
    row = repository_row(user={"id": 13, "name": "Ana", "avatar_filename": None})

    assert serialize_refund(row)["user"]["has_avatar"] is False


def test_created_at_becomes_an_iso_string():
    assert serialize_refund(repository_row())["created_at"] == "2026-07-28T17:00:25"


def test_a_null_created_at_survives_as_none():
    assert serialize_refund(repository_row(created_at=None))["created_at"] is None


# Everything else passes through untouched.
def test_the_remaining_fields_are_preserved():
    serialized = serialize_refund(repository_row())

    assert serialized["id"] == 58
    assert serialized["name"] == "Estacionamento"
    assert serialized["category"] == "transport"
    assert serialized["amount_in_cents"] == 4500
    assert serialized["status"] == "approved"
    assert serialized["user"]["id"] == 13
    assert serialized["user"]["name"] == "Validacao Visual"


# The serializer must not mutate what the repository handed it: the deleter
# reads `filename` off that same dict to remove the file from disk.
def test_the_input_row_is_not_mutated():
    row = repository_row()

    serialize_refund(row)

    assert row["filename"] == "606771d4-abc.jpg"
    assert row["user"]["avatar_filename"] == "foto.png"
```

- [ ] **Step 2: Rodar e confirmar que falham**

```bash
.venv/bin/python -m pytest src/controllers/refund_serializer_test.py -v
```
Esperado: `ModuleNotFoundError`.

- [ ] **Step 3: Implementar o serializador**

`src/controllers/refund_serializer.py`:

```python
from typing import Optional


# One place turning a repository row into the API's refund shape. It exists
# because three use cases — list, detail and create — now produce the SAME shape
# from the SAME source; three copies is how one of them silently keeps a field
# the others dropped.
#
# The review use case deliberately does NOT use this: it reads a different
# repository whose flat row is documented as divergent in UC-007.
def serialize_refund(refund: dict) -> dict:
    user = refund["user"]

    # A new dict rather than a mutation: the caller's row is also what the
    # deleter reads `filename` from to remove the file from disk.
    return {
        "id": refund["id"],
        "name": refund["name"],
        "category": refund["category"],
        "amount_in_cents": refund["amount_in_cents"],
        "status": refund["status"],
        "created_at": _iso(refund.get("created_at")),
        "user": {
            "id": user["id"],
            "name": user["name"],
            # The client only needs to know whether to show a picture or the
            # gradient; it fetches the image from GET /users/{id}/avatar.
            "has_avatar": bool(user["avatar_filename"]),
        },
    }


def _iso(created_at) -> Optional[str]:
    return created_at.isoformat() if created_at else None
```

- [ ] **Step 4: Rodar e confirmar que passam**

```bash
.venv/bin/python -m pytest src/controllers/refund_serializer_test.py -v
```

- [ ] **Step 5: Ligar os três controllers**

Em `src/controllers/refund_lister_controller.py`: acrescente o import
`from src.controllers.refund_serializer import serialize_refund`, troque a linha
de montagem de `attributes` por

```python
            "attributes": [serialize_refund(refund) for refund in refunds],
```

e **apague o método privado `__serialize` inteiro**, junto com o comentário sobre
`created_at` que fica sem dono — o serializador novo carrega essa explicação.

Em `src/controllers/refund_finder_controller.py`, o `__format_response` inteiro
passa a ser:

```python
    def __format_response(self, refund: dict) -> dict:
        return {
            "type": "Refund",
            "count": 1,
            "attributes": serialize_refund(refund),
        }
```

com o mesmo import. `src/controllers/refund_creator_controller.py` recebe
exatamente o mesmo corpo — os dois já eram idênticos, e é por isso que o
pragma `duplicate-code` existe num deles; confira se ele ainda é necessário
depois da mudança e remova-o se o pylint parar de reclamar.

**Não** toque no `refund_reviewer_controller` nem no `refund_deleter_controller`.

- [ ] **Step 6: Atualizar os testes dos três controllers**

As asserções que esperavam `filename` ou `avatar_filename` na resposta precisam mudar para o contrato novo. **Não relaxe as asserções** — troque o campo esperado, não a força do teste. Onde um teste afirmava a presença de `filename`, ele deve agora afirmar a **ausência**; onde afirmava `avatar_filename`, deve afirmar `has_avatar`.

- [ ] **Step 7: Provar que a exclusão continua apagando o arquivo**

Este é o comportamento que a mudança ameaça. Rode só o teste do deleter e confirme que ele ainda passa **e** ainda afirma que o storage foi chamado:

```bash
.venv/bin/python -m pytest src/controllers/refund_deleter_controller_test.py -v
```

Se ele não afirmar `mock_storage.delete.assert_called_once_with(...)`, acrescente essa asserção agora.

- [ ] **Step 8: Verificar e commitar**

```bash
.venv/bin/python -m pytest -q
.venv/bin/python -m pylint src
git add src/controllers
git commit -m "feat: hide storage filenames behind a shared refund serializer"
```

---

### Task 6: Verificação ponta a ponta e documentação canônica

**Files:**
- Modify: `docs/decisions/ADR-003-local-receipt-storage.md`, `docs/business-rules.md`, `docs/index.md`, `README.md`, `Refund-api.postman_collection.json`
- Modify: `docs/use-cases/UC-003-create-refund.md`, `UC-004-list-refunds.md`, `UC-005-view-refund.md`, `UC-007-review-refund.md`
- Create: `docs/use-cases/UC-010-download-receipt.md`, `docs/use-cases/UC-011-download-avatar.md`

- [ ] **Step 1: Verificação ponta a ponta**

Suba o servidor. Contas de teste: `validacao.visual@example.com` / `Valida123` (comum, dona de reembolsos) e `admin.validacao@example.com` / `Valida123` (admin). O token vem no campo `token`.

Execute e registre o status real de cada linha:

| Cenário | Esperado |
|---|---|
| `GET /receipts/<uuid>` sem token | 404 (mount removido) |
| `GET /avatars/<qualquer>` sem token | 404 (mount removido) |
| `GET /refunds/{id}/receipt` sem token | 401 |
| Dono baixa o próprio comprovante | 200, `Content-Type` de imagem, corpo não vazio |
| Admin baixa comprovante de outro | 200 |
| Comum baixa comprovante alheio | **404** (nunca 403) |
| Comum baixa comprovante de id inexistente | 404 |
| `GET /users/{id}/avatar` sem token | 401 |
| Usuário comum baixa avatar de OUTRO usuário | 200 |
| Avatar de usuário sem foto | 404 |
| `GET /refunds` | itens sem `filename`, com `user.has_avatar` |
| `GET /refunds/{id}` | idem |
| `POST /refunds` | idem |
| Excluir reembolso pendente | 200 **e o arquivo sumiu de `uploads/receipts/`** |

A última linha exige `ls uploads/receipts/` antes e depois — é o comportamento que a Task 5 ameaçou e o único que um mock desatualizado esconderia.

**Se algum cenário divergir, PARE e reporte** — é defeito de implementação, não algo para acomodar na documentação.

- [ ] **Step 2: `docs/decisions/ADR-003-local-receipt-storage.md`**

Amende (não crie ADR nova), com a data 2026-07-29: o acesso deixa de ser público. Registre o raciocínio da URL-capacidade — nomes UUID tornavam o link um direito de acesso permanente, sobrevivendo à perda de acesso ao reembolso — e que avatares receberam o mesmo tratamento por coerência, com o custo de N requisições autenticadas por página no cliente. Registre também a alternativa não escolhida: URL assinada de vida curta, território do Item 22.

- [ ] **Step 3: `docs/business-rules.md`**

Acrescente, no formato das vizinhas (regra + **Evidências**):

```markdown
## BR-020 — Acesso ao comprovante

O comprovante de uma solicitação só é acessível ao seu proprietário e a usuários
`admin`. Solicitação inexistente e solicitação alheia respondem igualmente como
não encontrada, para não revelar quais identificadores existem.

**Evidências:** `src/controllers/receipt_finder_controller.py` aplica a mesma
regra de `refund_finder_controller.py` e levanta `HttpNotFoundError` nos dois
casos.

## BR-021 — Acesso à foto de perfil

A foto de perfil de qualquer usuário é acessível a qualquer usuário autenticado.
Usuário inexistente e usuário sem foto respondem igualmente como não encontrado.

**Evidências:** `src/controllers/avatar_finder_controller.py` não recebe a
identidade de quem pede; a autenticação é exigida pela dependência da rota em
`src/main/routes/user_routes.py`.
```

- [ ] **Step 4: UC-003, UC-004, UC-005 e UC-007**

Nos três primeiros: `filename` sai da resposta e `user.avatar_filename` vira `user.has_avatar`; acrescente que o arquivo é obtido em `GET /refunds/{id}/receipt` e a foto em `GET /users/{id}/avatar`.

No UC-007: a resposta da revisão diverge agora em **três** pontos — `user_id` no topo, `filename` presente, e nenhum `has_avatar`. Descreva os três e mantenha o registro de que é uma inconsistência conhecida, inofensiva porque a tela de revisão refaz o `GET` em vez de consumir esse corpo.

- [ ] **Step 5: UC-010 e UC-011**

Crie os dois usando `UC-005-view-refund.md` como molde estrutural, com endpoint, autorização, tabela de códigos (401, 404, 200) e o fato de o `Content-Type` vir da extensão armazenada. Acrescente ambos ao `docs/index.md`.

- [ ] **Step 6: README e Postman**

No `README.md`, corrija qualquer menção a arquivos servidos estaticamente em `/receipts`. Na coleção, acrescente as duas rotas novas seguindo a forma das existentes, e valide:

```bash
.venv/bin/python -m json.tool Refund-api.postman_collection.json > /dev/null
```

- [ ] **Step 7: Verificação final e commit**

```bash
.venv/bin/python -m pytest -q
.venv/bin/python -m pylint src
git add docs README.md Refund-api.postman_collection.json
git commit -m "docs: record authenticated file access and its use cases"
```

---

## Fechamento do ciclo (fora das tasks)

- **`docs/learning-path-progress.md`** — entrada do ciclo. O aprendizado central: **um nome de arquivo imprevisível é um controle de acesso, e um fraco** — quem vê o link uma vez o mantém para sempre. E a distinção que a Task 5 força: *o que o repositório devolve é dado interno; o que vira resposta é contrato* — colá-los com `**refund` é o que fez `filename` ter dois donos.
- **`docs/plans/current-state.md`** — ciclo concluído, próximo passo (spec do frontend) e o acúmulo de duas quebras de contrato sem deploy no meio.
- **Apresentar o fechamento ao Gabriel** e aguardar autorização.
