# Consulta da listagem e foto de perfil (backend) — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Dar à API o que o ciclo de frontend precisa — ordenação e filtro server-side na listagem, quem solicitou em cada resposta de reembolso, e foto de perfil com upload e remoção.

**Architecture:** Preserva a Clean Architecture existente (rota → view → validator → controller → repository/driver). O driver de storage passa a receber o diretório pelo construtor, servindo comprovante e avatar com uma implementação só. Ordenação e filtro vivem no servidor, onde a paginação já vive.

**Tech Stack:** Python 3.9, FastAPI, SQLAlchemy 2.0 (Core, async), asyncpg, PostgreSQL (Neon), Alembic, pytest + pytest-asyncio, pylint.

**Spec:** [`../specs/2026-07-29-refund-query-and-avatar-design.md`](../specs/2026-07-29-refund-query-and-avatar-design.md)

## Global Constraints

- **Python 3.9.** Use `Optional[X]`, **nunca** `X | None`. `list[dict]` e `tuple[...]` são válidos.
- **Não há `python` no PATH e os shebangs do `.venv` estão QUEBRADOS.** Invoque tudo como módulo: `.venv/bin/python -m pytest`, `.venv/bin/python -m pylint`, `.venv/bin/python -m alembic`. **Nunca** `.venv/bin/pytest`.
- **Todo arquivo novo com lógica ganha um `_test.py` ao lado.** Composers (`src/main/composer/`) e scripts de `init/` não têm teste, pela convenção vigente.
- **Testes assíncronos exigem `@pytest.mark.asyncio` explícito.**
- **Comentários em inglês**, curtos, explicando a razão — não o óbvio.
- **`pylint src` deve terminar em 10.00/10.** Baseline atual. Se um pragma for necessário, espelhe a convenção do arquivo vizinho e explique em uma linha.
- **`pytest` 100% verde.** Baseline: **105 testes**.
- **Nunca versionar credenciais.**
- Rodar `pytest` e `pylint src` ao final de **cada** task, antes do commit.

> **Este ciclo quebra o contrato da API sem ordem de deploy segura.** A Task 10
> tira `user_id` do topo das respostas de reembolso e o move para `user.id`. O
> Zod do frontend hoje declara `user_id` como **obrigatório**, então um backend
> novo com frontend velho falha o `.parse` em toda listagem — e o inverso falha
> igual, porque o frontend novo passará a exigir `user`. **Backend e frontend
> têm de ir para produção juntos.** Isso não afeta a implementação, mas quem
> executar este plano precisa saber que a branch não pode ser implantada sozinha.

---

### Task 1: Dívida operacional — ignorar `uploads/` e remover órfãos

Sem código. Fecha duas dívidas antes do avatar criar mais arquivos.

**Files:**
- Modify: `.gitignore`
- Create: `uploads/avatars/.gitkeep`
- Delete: 7 arquivos órfãos em `uploads/receipts/`

**Interfaces:**
- Produces: o diretório `uploads/avatars/` existente, que o mount estático da Task 3 exige

- [ ] **Step 1: Confirmar que os órfãos ainda são 7**

```bash
.venv/bin/python -c "
import asyncio, os, asyncpg
from dotenv import load_dotenv
load_dotenv()
url = os.getenv('DATABASE_URL').replace('postgresql+asyncpg://', 'postgresql://')
async def main():
    c = await asyncpg.connect(url)
    db = {r['filename'] for r in await c.fetch('select filename from refunds')}
    d = 'uploads/receipts'
    orphans = sorted(f for f in os.listdir(d) if f != '.gitkeep' and f not in db)
    for f in orphans: print(f)
    print('total:', len(orphans))
    await c.close()
asyncio.run(main())
"
```

Esperado: 7 nomes. **Se vier número diferente, pare e reporte** — o banco mudou desde o planejamento e a lista precisa ser reconferida antes de apagar qualquer coisa.

- [ ] **Step 2: Apagar somente os órfãos listados**

Apague exatamente os arquivos que o Step 1 imprimiu. Não use glob nem `rm *`.

- [ ] **Step 3: Confirmar que nada que o banco referencia sumiu**

```bash
.venv/bin/python -c "
import asyncio, os, asyncpg
from dotenv import load_dotenv
load_dotenv()
url = os.getenv('DATABASE_URL').replace('postgresql+asyncpg://', 'postgresql://')
async def main():
    c = await asyncpg.connect(url)
    db = {r['filename'] for r in await c.fetch('select filename from refunds')}
    disk = {f for f in os.listdir('uploads/receipts') if f != '.gitkeep'}
    print('no banco sem arquivo no disco:', len(db - disk))
    print('orfaos restantes:', len(disk - db))
    await c.close()
asyncio.run(main())
"
```
Esperado: **ambos zero**. Se "no banco sem arquivo" for maior que zero, você apagou um arquivo em uso — pare e reporte.

- [ ] **Step 4: Criar o diretório de avatares**

```bash
mkdir -p uploads/avatars && touch uploads/avatars/.gitkeep
```

- [ ] **Step 5: Ignorar os uploads**

Acrescente ao final do `.gitignore`:

```gitignore
# Arquivos enviados vivem no disco local (ADR-003) e nunca são versionados.
# As exceções mantêm a estrutura de pastas no repositório.
uploads/**
!uploads/receipts/
!uploads/receipts/.gitkeep
!uploads/avatars/
!uploads/avatars/.gitkeep
```

- [ ] **Step 6: Confirmar que o padrão funciona nos dois sentidos**

```bash
git check-ignore -v uploads/receipts/$(ls uploads/receipts | grep -v gitkeep | head -1)
git check-ignore -v uploads/receipts/.gitkeep || echo ".gitkeep NAO ignorado (correto)"
git status --short
```
Esperado: um arquivo de upload aparece como ignorado; o `.gitkeep` **não**; e o `git status` mostra apenas `.gitignore` e `uploads/avatars/.gitkeep`.

- [ ] **Step 7: Verificar e commitar**

```bash
.venv/bin/python -m pytest -q
.venv/bin/python -m pylint src
git add .gitignore uploads/avatars/.gitkeep
git commit -m "chore: ignore uploaded files and drop orphaned receipts"
```

---

### Task 2: `FileStorage` parametrizado

`ReceiptStorage` tem o diretório cravado. Passa a recebê-lo pelo construtor, para comprovante e avatar dividirem uma implementação.

**Files:**
- Create: `src/drivers/file_storage.py`, `src/drivers/file_storage_test.py`, `src/drivers/interfaces/file_storage_interface.py`
- Delete: `src/drivers/receipt_storage.py`, `src/drivers/receipt_storage_test.py`, `src/drivers/interfaces/receipt_storage_interface.py`
- Modify: `src/main/composer/refund_creator_composer.py`, `src/main/composer/refund_deleter_composer.py`, `src/controllers/refund_creator_controller.py`, `src/controllers/refund_deleter_controller.py`

**Interfaces:**
- Produces: `FileStorage(directory: str)` com `save(original_filename: str, content: bytes) -> str` e `delete(filename: str) -> None`; `FileStorageInterface`. Consumidos pelas Tasks 6 e 7.

- [ ] **Step 1: Ler o teste existente**

Leia `src/drivers/receipt_storage_test.py` inteiro antes de escrever o novo — o novo deve cobrir tudo que ele cobria, mais o diretório injetado.

- [ ] **Step 2: Escrever o teste novo**

`src/drivers/file_storage_test.py`:

```python
import os
from src.drivers.file_storage import FileStorage


# The directory now arrives through the constructor, so the same class serves
# receipts and avatars. tmp_path is a pytest fixture giving a real temp folder.
def test_save_writes_the_file_into_the_injected_directory(tmp_path):
    storage = FileStorage(str(tmp_path))

    filename = storage.save("comprovante.jpg", b"conteudo")

    assert (tmp_path / filename).read_bytes() == b"conteudo"


# The stored name must not be the uploaded one: two users uploading "foto.jpg"
# would otherwise overwrite each other.
def test_save_returns_a_unique_name_preserving_the_extension(tmp_path):
    storage = FileStorage(str(tmp_path))

    first = storage.save("foto.jpg", b"a")
    second = storage.save("foto.jpg", b"b")

    assert first != second
    assert first.endswith(".jpg") and second.endswith(".jpg")
    assert "foto" not in first


def test_two_storages_write_to_their_own_directories(tmp_path):
    receipts = tmp_path / "receipts"
    avatars = tmp_path / "avatars"
    receipts.mkdir()
    avatars.mkdir()

    receipt_name = FileStorage(str(receipts)).save("a.jpg", b"r")
    avatar_name = FileStorage(str(avatars)).save("b.jpg", b"a")

    assert (receipts / receipt_name).exists()
    assert (avatars / avatar_name).exists()
    assert not (avatars / receipt_name).exists()


def test_delete_removes_the_file(tmp_path):
    storage = FileStorage(str(tmp_path))
    filename = storage.save("a.jpg", b"x")

    storage.delete(filename)

    assert not (tmp_path / filename).exists()


# Deleting an already-missing file must not raise: the delete path runs after a
# database delete, and blowing up there would fail a request that already
# succeeded.
def test_delete_is_silent_when_the_file_does_not_exist(tmp_path):
    FileStorage(str(tmp_path)).delete("nao-existe.jpg")
```

- [ ] **Step 3: Rodar e confirmar que falha**

```bash
.venv/bin/python -m pytest src/drivers/file_storage_test.py -v
```
Esperado: `ModuleNotFoundError: No module named 'src.drivers.file_storage'`.

- [ ] **Step 4: Criar a interface**

`src/drivers/interfaces/file_storage_interface.py`:

```python
from abc import ABC, abstractmethod


class FileStorageInterface(ABC):

    @abstractmethod
    def save(self, original_filename: str, content: bytes) -> str:
        pass

    @abstractmethod
    def delete(self, filename: str) -> None:
        pass
```

- [ ] **Step 5: Criar o driver**

`src/drivers/file_storage.py`:

```python
import os
import uuid
from .interfaces.file_storage_interface import FileStorageInterface


class FileStorage(FileStorageInterface):
    # The directory arrives through the constructor instead of being read from
    # config here: receipts and avatars need different folders but identical
    # behaviour, and one implementation is one place to fix a storage bug.
    def __init__(self, directory: str) -> None:
        self.__directory = directory

    def save(self, original_filename: str, content: bytes) -> str:
        extension = os.path.splitext(original_filename)[1]
        unique_filename = f"{uuid.uuid4()}{extension}"
        path = os.path.join(self.__directory, unique_filename)

        with open(path, "wb") as file:
            file.write(content)

        return unique_filename

    def delete(self, filename: str) -> None:
        path = os.path.join(self.__directory, filename)
        if os.path.exists(path):
            os.remove(path)
```

- [ ] **Step 6: Trocar os consumidores**

Em `src/controllers/refund_creator_controller.py` e `src/controllers/refund_deleter_controller.py`, troque o import e o tipo:

```python
from src.drivers.interfaces.file_storage_interface import FileStorageInterface
```
```python
        receipt_storage: FileStorageInterface,
```

Em `src/main/composer/refund_creator_composer.py` e `refund_deleter_composer.py`:

```python
from src.configs.global_config import upload_info
from src.drivers.file_storage import FileStorage
```
```python
    storage = FileStorage(upload_info["UPLOAD_DIR"])
```

- [ ] **Step 7: Apagar os arquivos antigos**

```bash
git rm src/drivers/receipt_storage.py src/drivers/receipt_storage_test.py src/drivers/interfaces/receipt_storage_interface.py
```

- [ ] **Step 8: Confirmar que ninguém mais cita o nome antigo**

```bash
grep -rn "ReceiptStorage\|receipt_storage_interface" src/ || echo "nenhuma referencia restante"
```
Esperado: nenhuma. **O nome do parâmetro `receipt_storage` nos controllers pode ficar** — ali ele descreve o papel daquele storage, não a classe.

- [ ] **Step 9: Verificar e commitar**

```bash
.venv/bin/python -m pytest -q
.venv/bin/python -m pylint src
git add -A src/drivers src/controllers src/main/composer
git commit -m "refactor: parameterise the file storage directory"
```
Esperado: 105 testes (os do driver antigo saem, os novos entram) e pylint 10.00/10.

---

### Task 3: Coluna `avatar_filename`, config e mount

**Files:**
- Modify: `src/models/entities/users.py`, `src/configs/global_config.py`, `src/main/server/server.py`, `README.md`
- Create: `alembic/versions/<hash>_add_user_avatar.py`

**Interfaces:**
- Consumes: a revisão `e03baa8b708b` (head atual), que vira a `down_revision`
- Produces: `users.avatar_filename` (`String`, nullable); `upload_info["AVATAR_DIR"]`; a rota estática `/avatars/{filename}`

- [ ] **Step 1: Adicionar a coluna à entidade**

Em `src/models/entities/users.py`, antes de `created_at`:

```python
    # Nullable is the normal state, not a failure: the product's default avatar
    # is a gradient over the user's initials, and a picture is opt-in.
    Column("avatar_filename", String, nullable=True),
```

- [ ] **Step 2: Adicionar a configuração**

Em `src/configs/global_config.py`, dentro de `upload_info`:

```python
    "AVATAR_DIR": os.getenv("AVATAR_DIR", "uploads/avatars"),
```

- [ ] **Step 3: Gerar a migration**

```bash
.venv/bin/python -m alembic revision --autogenerate -m "add user avatar"
```

- [ ] **Step 4: Ler o arquivo gerado**

Confira que `down_revision = 'e03baa8b708b'`, que `upgrade()` tem
`op.add_column("users", sa.Column("avatar_filename", sa.String(), nullable=True))`
e que `downgrade()` tem `op.drop_column("users", "avatar_filename")`. Corrija à mão o que faltar.

- [ ] **Step 5: Aplicar e conferir o ciclo completo**

```bash
.venv/bin/python -m alembic upgrade head
.venv/bin/python -m alembic current
.venv/bin/python -m alembic downgrade -1
.venv/bin/python -m alembic current
.venv/bin/python -m alembic upgrade head
.venv/bin/python -m alembic current
```
Esperado: head → revisão anterior → head. Uma migration sem `downgrade` testado é uma migration sem volta.

- [ ] **Step 6: Servir os avatares**

Em `src/main/server/server.py`, ao lado do mount de `/receipts`:

```python
app.mount("/avatars", StaticFiles(directory=upload_info["AVATAR_DIR"]), name="avatars")
```

`StaticFiles` estoura no boot se o diretório não existir — a Task 1 já criou `uploads/avatars/`.

- [ ] **Step 7: Subir o servidor e confirmar**

```bash
.venv/bin/python run.py
```
Em outro terminal:
```bash
curl -s -o /dev/null -w "%{http_code}\n" http://localhost:3333/health
curl -s -o /dev/null -w "%{http_code}\n" http://localhost:3333/avatars/nao-existe.jpg
```
Esperado: `200` e `404`. O 404 prova que o mount existe e responde (sem ele viria 404 do router, indistinguível — confirme também que o servidor subiu sem exceção no log).

- [ ] **Step 8: Documentar a variável**

Na seção "Environment setup" do `README.md`, acrescente ao bloco `.env`:

```env
AVATAR_DIR=uploads/avatars
```

- [ ] **Step 9: Verificar e commitar**

```bash
.venv/bin/python -m pytest -q
.venv/bin/python -m pylint src
git add src/models/entities/users.py src/configs/global_config.py src/main/server/server.py alembic/versions README.md
git commit -m "feat: add the user avatar column and static route"
```

---

### Task 4: `update_avatar` no repositório de usuários

**Files:**
- Modify: `src/models/repositories/users_repository.py`, `src/models/repositories/interfaces/users_repository_interface.py`
- Modify: `src/models/repositories/users_repository_test.py`

**Interfaces:**
- Produces: `async update_avatar(user_id: int, avatar_filename: Optional[str]) -> None`, consumido pela Task 6

- [ ] **Step 1: Escrever os testes que falham**

Acrescente em `src/models/repositories/users_repository_test.py` (leia o arquivo antes e reuse as fixtures `mock_db`/`mock_connection` que já existem ali):

```python
@pytest.mark.asyncio
async def test_update_avatar_persists_the_filename(mock_connection, mock_db):
    repository = UsersRepository(mock_connection)

    await repository.update_avatar(7, "abc.jpg")

    mock_db.session.execute.assert_awaited_once()
    mock_db.session.commit.assert_awaited_once()


# Removing the picture is an update to NULL, not a delete: the user row stays.
@pytest.mark.asyncio
async def test_update_avatar_accepts_none_to_clear_the_picture(mock_connection, mock_db):
    repository = UsersRepository(mock_connection)

    await repository.update_avatar(7, None)

    statement = str(mock_db.session.execute.call_args[0][0])
    assert "UPDATE users" in statement
    mock_db.session.commit.assert_awaited_once()
```

- [ ] **Step 2: Rodar e confirmar que falham**

```bash
.venv/bin/python -m pytest src/models/repositories/users_repository_test.py -v
```
Esperado: `AttributeError` — `update_avatar` não existe.

- [ ] **Step 3: Implementar**

Acrescente `update` ao import do SQLAlchemy no topo de `users_repository.py`, e o método:

```python
    async def update_avatar(self, user_id: int, avatar_filename: Optional[str]) -> None:
        async with self.__db_connection.connect() as session:
            query = (
                update(Users)
                .where(Users.c.id == user_id)
                .values(avatar_filename=avatar_filename)
            )
            await session.execute(query)
            await session.commit()
```

Acrescente `from typing import Optional` se ainda não estiver lá, e o método abstrato na interface:

```python
    @abstractmethod
    async def update_avatar(self, user_id: int, avatar_filename: Optional[str]) -> None:
        pass
```

- [ ] **Step 4: Rodar e confirmar que passam**

```bash
.venv/bin/python -m pytest src/models/repositories/users_repository_test.py -v
```

- [ ] **Step 5: Verificar e commitar**

```bash
.venv/bin/python -m pytest -q
.venv/bin/python -m pylint src
git add src/models/repositories
git commit -m "feat: persist the user avatar filename"
```

---

### Task 5: Validator do avatar

**Files:**
- Create: `src/validators/avatar_upload_validator.py`, `src/validators/avatar_upload_validator_test.py`

**Interfaces:**
- Produces: `avatar_upload_validator(http_request: HttpRequest) -> None`, chamado pela view da Task 7

- [ ] **Step 1: Escrever os testes que falham**

```python
import pytest
from src.errors.types.http_unprocessable_entity_error import HttpUnprocessableEntityError
from src.views.http_types.http_request import HttpRequest
from .avatar_upload_validator import avatar_upload_validator


def valid_body(**overrides) -> dict:
    body = {"filename": "foto.jpg", "content": b"x"}
    body.update(overrides)
    return body


def test_jpg_is_accepted():
    avatar_upload_validator(HttpRequest(body=valid_body()))


def test_png_is_accepted():
    avatar_upload_validator(HttpRequest(body=valid_body(filename="foto.png")))


def test_extension_check_is_case_insensitive():
    avatar_upload_validator(HttpRequest(body=valid_body(filename="FOTO.JPG")))


# PDF is a valid receipt but never a valid avatar.
def test_pdf_is_rejected():
    with pytest.raises(HttpUnprocessableEntityError):
        avatar_upload_validator(HttpRequest(body=valid_body(filename="foto.pdf")))


def test_missing_filename_is_rejected():
    with pytest.raises(HttpUnprocessableEntityError):
        avatar_upload_validator(HttpRequest(body=valid_body(filename=None)))


def test_file_bigger_than_the_limit_is_rejected():
    oversized = b"x" * (4 * 1024 * 1024 + 1)
    with pytest.raises(HttpUnprocessableEntityError):
        avatar_upload_validator(HttpRequest(body=valid_body(content=oversized)))
```

- [ ] **Step 2: Rodar e confirmar que falham**

```bash
.venv/bin/python -m pytest src/validators/avatar_upload_validator_test.py -v
```

- [ ] **Step 3: Implementar**

```python
import os
from src.configs.global_config import upload_info
from src.errors.types.http_unprocessable_entity_error import HttpUnprocessableEntityError
from src.views.http_types.http_request import HttpRequest

# PDF is deliberately absent: it is a valid receipt but cannot be shown as an
# avatar. Same 4MB ceiling as the receipt — a separate constant would only earn
# its place once the two limits need to differ.
ALLOWED_AVATAR_EXTENSIONS = {".jpg", ".jpeg", ".png"}


def avatar_upload_validator(http_request: HttpRequest) -> None:
    body = http_request.body

    # Checked by extension, not by the client-supplied Content-Type: that header
    # is set by whatever HTTP client is uploading and is unreliable in practice.
    extension = os.path.splitext(body.get("filename") or "")[1].lower()
    if extension not in ALLOWED_AVATAR_EXTENSIONS:
        raise HttpUnprocessableEntityError("Avatar must be JPG or PNG")

    if len(body.get("content", b"")) > upload_info["MAX_FILE_SIZE_BYTES"]:
        raise HttpUnprocessableEntityError("Avatar must be smaller than 4MB")
```

- [ ] **Step 4: Rodar, verificar e commitar**

```bash
.venv/bin/python -m pytest -q
.venv/bin/python -m pylint src
git add src/validators
git commit -m "feat: validate avatar format and size"
```

---

### Task 6: Controllers de avatar

**Files:**
- Create: `src/controllers/interfaces/avatar_uploader_controller_interface.py`, `src/controllers/avatar_uploader_controller.py`, `src/controllers/avatar_uploader_controller_test.py`
- Create: `src/controllers/interfaces/avatar_remover_controller_interface.py`, `src/controllers/avatar_remover_controller.py`, `src/controllers/avatar_remover_controller_test.py`

**Interfaces:**
- Consumes: `UsersRepositoryInterface.update_avatar` (Task 4), `FileStorageInterface` (Task 2)
- Produces: `AvatarUploaderController(users_repository, avatar_storage)` com `async upload(user_id: int, original_filename: str, content: bytes) -> dict`; `AvatarRemoverController(users_repository, avatar_storage)` com `async remove(user_id: int) -> dict`. Consumidos pela Task 7.

- [ ] **Step 1: Escrever os testes que falham**

`src/controllers/avatar_uploader_controller_test.py`:

```python
# pylint: disable=w0621
from unittest.mock import AsyncMock, MagicMock
import pytest
from src.errors.types.http_not_found_error import HttpNotFoundError
from .avatar_uploader_controller import AvatarUploaderController


@pytest.fixture
def mock_repository():
    repository = MagicMock()
    repository.select_user_by_id = AsyncMock(
        return_value={"id": 7, "name": "Gabriel", "avatar_filename": None}
    )
    repository.update_avatar = AsyncMock()
    return repository


@pytest.fixture
def mock_storage():
    storage = MagicMock()
    storage.save = MagicMock(return_value="novo.jpg")
    storage.delete = MagicMock()
    return storage


@pytest.mark.asyncio
async def test_upload_saves_the_file_and_persists_its_name(mock_repository, mock_storage):
    controller = AvatarUploaderController(mock_repository, mock_storage)

    response = await controller.upload(user_id=7, original_filename="foto.jpg", content=b"x")

    mock_storage.save.assert_called_once_with("foto.jpg", b"x")
    mock_repository.update_avatar.assert_awaited_once_with(7, "novo.jpg")
    assert response["attributes"]["avatar_filename"] == "novo.jpg"


# Replacing the picture must remove the previous file, or every upload leaves one
# behind forever — which is exactly how this project accumulated orphaned files.
@pytest.mark.asyncio
async def test_replacing_the_picture_deletes_the_previous_file(mock_repository, mock_storage):
    mock_repository.select_user_by_id = AsyncMock(
        return_value={"id": 7, "name": "Gabriel", "avatar_filename": "antiga.jpg"}
    )
    controller = AvatarUploaderController(mock_repository, mock_storage)

    await controller.upload(user_id=7, original_filename="foto.jpg", content=b"x")

    mock_storage.delete.assert_called_once_with("antiga.jpg")


# The first upload has nothing to delete; calling delete(None) would blow up.
@pytest.mark.asyncio
async def test_first_upload_deletes_nothing(mock_repository, mock_storage):
    controller = AvatarUploaderController(mock_repository, mock_storage)

    await controller.upload(user_id=7, original_filename="foto.jpg", content=b"x")

    mock_storage.delete.assert_not_called()


@pytest.mark.asyncio
async def test_unknown_user_raises_not_found(mock_repository, mock_storage):
    mock_repository.select_user_by_id = AsyncMock(return_value=None)
    controller = AvatarUploaderController(mock_repository, mock_storage)

    with pytest.raises(HttpNotFoundError):
        await controller.upload(user_id=999, original_filename="foto.jpg", content=b"x")

    mock_storage.save.assert_not_called()
```

`src/controllers/avatar_remover_controller_test.py`:

```python
# pylint: disable=w0621
from unittest.mock import AsyncMock, MagicMock
import pytest
from src.errors.types.http_not_found_error import HttpNotFoundError
from .avatar_remover_controller import AvatarRemoverController


@pytest.fixture
def mock_repository():
    repository = MagicMock()
    repository.select_user_by_id = AsyncMock(
        return_value={"id": 7, "name": "Gabriel", "avatar_filename": "atual.jpg"}
    )
    repository.update_avatar = AsyncMock()
    return repository


@pytest.fixture
def mock_storage():
    storage = MagicMock()
    storage.delete = MagicMock()
    return storage


@pytest.mark.asyncio
async def test_remove_clears_the_column_and_deletes_the_file(mock_repository, mock_storage):
    controller = AvatarRemoverController(mock_repository, mock_storage)

    response = await controller.remove(user_id=7)

    mock_repository.update_avatar.assert_awaited_once_with(7, None)
    mock_storage.delete.assert_called_once_with("atual.jpg")
    assert response["attributes"]["avatar_filename"] is None


# Removing when there is no picture is a no-op that still succeeds: the caller
# asked for "no avatar" and that is the resulting state.
@pytest.mark.asyncio
async def test_remove_is_idempotent_when_there_is_no_picture(mock_repository, mock_storage):
    mock_repository.select_user_by_id = AsyncMock(
        return_value={"id": 7, "name": "Gabriel", "avatar_filename": None}
    )
    controller = AvatarRemoverController(mock_repository, mock_storage)

    response = await controller.remove(user_id=7)

    mock_storage.delete.assert_not_called()
    assert response["attributes"]["avatar_filename"] is None


@pytest.mark.asyncio
async def test_unknown_user_raises_not_found(mock_repository, mock_storage):
    mock_repository.select_user_by_id = AsyncMock(return_value=None)
    controller = AvatarRemoverController(mock_repository, mock_storage)

    with pytest.raises(HttpNotFoundError):
        await controller.remove(user_id=999)
```

- [ ] **Step 2: Rodar e confirmar que falham**

```bash
.venv/bin/python -m pytest src/controllers/avatar_uploader_controller_test.py src/controllers/avatar_remover_controller_test.py -v
```

- [ ] **Step 3: Criar as interfaces**

`src/controllers/interfaces/avatar_uploader_controller_interface.py`:

```python
from abc import ABC, abstractmethod


class AvatarUploaderControllerInterface(ABC):

    @abstractmethod
    async def upload(self, user_id: int, original_filename: str, content: bytes) -> dict:
        pass
```

`src/controllers/interfaces/avatar_remover_controller_interface.py`:

```python
from abc import ABC, abstractmethod


class AvatarRemoverControllerInterface(ABC):

    @abstractmethod
    async def remove(self, user_id: int) -> dict:
        pass
```

- [ ] **Step 4: Implementar o upload**

`src/controllers/avatar_uploader_controller.py`:

```python
from src.models.repositories.interfaces.users_repository_interface import UsersRepositoryInterface
from src.drivers.interfaces.file_storage_interface import FileStorageInterface
from src.controllers.interfaces.avatar_uploader_controller_interface import (
    AvatarUploaderControllerInterface,
)
from src.errors.types.http_not_found_error import HttpNotFoundError


class AvatarUploaderController(AvatarUploaderControllerInterface):
    def __init__(
        self,
        users_repository: UsersRepositoryInterface,
        avatar_storage: FileStorageInterface,
    ) -> None:
        self.__users_repository = users_repository
        self.__avatar_storage = avatar_storage

    async def upload(self, user_id: int, original_filename: str, content: bytes) -> dict:
        user = await self.__users_repository.select_user_by_id(user_id)

        if not user:
            raise HttpNotFoundError("User not found")

        new_filename = self.__avatar_storage.save(original_filename, content)
        await self.__users_repository.update_avatar(user_id, new_filename)

        # The old file is deleted LAST, on purpose. Deleting it before the row
        # points at the new one would leave the user with no picture at all if
        # the update failed — losing data instead of leaking a file.
        previous_filename = user.get("avatar_filename")
        if previous_filename:
            self.__avatar_storage.delete(previous_filename)

        return self.__format_response(new_filename)

    def __format_response(self, avatar_filename: str) -> dict:
        return {
            "type": "User",
            "count": 1,
            "attributes": {"avatar_filename": avatar_filename},
        }
```

- [ ] **Step 5: Implementar a remoção**

`src/controllers/avatar_remover_controller.py`:

```python
from src.models.repositories.interfaces.users_repository_interface import UsersRepositoryInterface
from src.drivers.interfaces.file_storage_interface import FileStorageInterface
from src.controllers.interfaces.avatar_remover_controller_interface import (
    AvatarRemoverControllerInterface,
)
from src.errors.types.http_not_found_error import HttpNotFoundError


class AvatarRemoverController(AvatarRemoverControllerInterface):
    def __init__(
        self,
        users_repository: UsersRepositoryInterface,
        avatar_storage: FileStorageInterface,
    ) -> None:
        self.__users_repository = users_repository
        self.__avatar_storage = avatar_storage

    async def remove(self, user_id: int) -> dict:
        user = await self.__users_repository.select_user_by_id(user_id)

        if not user:
            raise HttpNotFoundError("User not found")

        # Clearing the column first, deleting the file after: same ordering rule
        # as the upload — never leave the row pointing at a file that is gone.
        current_filename = user.get("avatar_filename")
        await self.__users_repository.update_avatar(user_id, None)

        if current_filename:
            self.__avatar_storage.delete(current_filename)

        return {
            "type": "User",
            "count": 1,
            "attributes": {"avatar_filename": None},
        }
```

- [ ] **Step 6: Rodar, verificar e commitar**

```bash
.venv/bin/python -m pytest -q
.venv/bin/python -m pylint src
git add src/controllers
git commit -m "feat: upload and remove the profile picture"
```

---

### Task 7: Views, composers e rotas do avatar

**Files:**
- Create: `src/views/avatar_uploader_view.py`, `src/views/avatar_uploader_view_test.py`, `src/views/avatar_remover_view.py`, `src/views/avatar_remover_view_test.py`
- Create: `src/main/composer/avatar_uploader_composer.py`, `src/main/composer/avatar_remover_composer.py`, `src/main/routes/user_routes.py`
- Modify: `src/main/server/server.py`

**Interfaces:**
- Consumes: os controllers da Task 6, `avatar_upload_validator` (Task 5), `FileStorage` (Task 2), `upload_info["AVATAR_DIR"]` (Task 3)
- Produces: `POST /users/me/avatar` e `DELETE /users/me/avatar`

- [ ] **Step 1: Escrever os testes das views**

`src/views/avatar_uploader_view_test.py`:

```python
# pylint: disable=w0621
from unittest.mock import AsyncMock, MagicMock
import pytest
from fastapi import HTTPException
from src.views.http_types.http_request import HttpRequest
from .avatar_uploader_view import AvatarUploaderView


@pytest.fixture
def mock_controller():
    controller = MagicMock()
    controller.upload = AsyncMock(
        return_value={"type": "User", "count": 1, "attributes": {"avatar_filename": "a.jpg"}}
    )
    return controller


@pytest.mark.asyncio
async def test_valid_upload_reaches_the_controller(mock_controller):
    view = AvatarUploaderView(mock_controller)
    http_request = HttpRequest(
        body={"filename": "foto.jpg", "content": b"x"},
        token_info={"user_id": 7, "role": "standard"},
    )

    http_response = await view.handle(http_request)

    mock_controller.upload.assert_awaited_once_with(
        user_id=7, original_filename="foto.jpg", content=b"x"
    )
    assert http_response.status_code == 200


# The validator runs before the controller: a PDF must be refused with 422 and
# must never reach the disk.
@pytest.mark.asyncio
async def test_pdf_is_refused_before_the_controller(mock_controller):
    view = AvatarUploaderView(mock_controller)
    http_request = HttpRequest(
        body={"filename": "foto.pdf", "content": b"x"},
        token_info={"user_id": 7, "role": "standard"},
    )

    with pytest.raises(HTTPException) as exception_info:
        await view.handle(http_request)

    assert exception_info.value.status_code == 422
    mock_controller.upload.assert_not_awaited()
```

`src/views/avatar_remover_view_test.py`:

```python
# pylint: disable=w0621
from unittest.mock import AsyncMock, MagicMock
import pytest
from src.views.http_types.http_request import HttpRequest
from .avatar_remover_view import AvatarRemoverView


@pytest.fixture
def mock_controller():
    controller = MagicMock()
    controller.remove = AsyncMock(
        return_value={"type": "User", "count": 1, "attributes": {"avatar_filename": None}}
    )
    return controller


@pytest.mark.asyncio
async def test_remove_reaches_the_controller_with_the_token_user(mock_controller):
    view = AvatarRemoverView(mock_controller)
    http_request = HttpRequest(token_info={"user_id": 7, "role": "standard"})

    http_response = await view.handle(http_request)

    mock_controller.remove.assert_awaited_once_with(user_id=7)
    assert http_response.status_code == 200
```

- [ ] **Step 2: Rodar e confirmar que falham**

```bash
.venv/bin/python -m pytest src/views/avatar_uploader_view_test.py src/views/avatar_remover_view_test.py -v
```

- [ ] **Step 3: Implementar as views**

`src/views/avatar_uploader_view.py`:

```python
from src.controllers.interfaces.avatar_uploader_controller_interface import (
    AvatarUploaderControllerInterface,
)
from src.validators.avatar_upload_validator import avatar_upload_validator
from src.views.http_types.http_request import HttpRequest
from src.views.http_types.http_response import HttpResponse
from src.errors.error_handler import error_handler


class AvatarUploaderView:
    def __init__(self, controller: AvatarUploaderControllerInterface) -> None:
        self.__controller = controller

    async def handle(self, http_request: HttpRequest) -> HttpResponse:
        try:
            avatar_upload_validator(http_request)

            response = await self.__controller.upload(
                user_id=http_request.token_info["user_id"],
                original_filename=http_request.body["filename"],
                content=http_request.body["content"],
            )
            return HttpResponse(body=response, status_code=200)
        except Exception as e:
            error_handler(e)
```

`src/views/avatar_remover_view.py`:

```python
from src.controllers.interfaces.avatar_remover_controller_interface import (
    AvatarRemoverControllerInterface,
)
from src.views.http_types.http_request import HttpRequest
from src.views.http_types.http_response import HttpResponse
from src.errors.error_handler import error_handler


class AvatarRemoverView:
    def __init__(self, controller: AvatarRemoverControllerInterface) -> None:
        self.__controller = controller

    async def handle(self, http_request: HttpRequest) -> HttpResponse:
        try:
            response = await self.__controller.remove(
                user_id=http_request.token_info["user_id"]
            )
            return HttpResponse(body=response, status_code=200)
        except Exception as e:
            error_handler(e)
```

- [ ] **Step 4: Criar os composers**

`src/main/composer/avatar_uploader_composer.py`:

```python
from src.configs.global_config import upload_info
from src.models.settings.database_connection_handler import database_connection_handler
from src.models.repositories.users_repository import UsersRepository
from src.drivers.file_storage import FileStorage
from src.controllers.avatar_uploader_controller import AvatarUploaderController
from src.views.avatar_uploader_view import AvatarUploaderView


def avatar_uploader_composer():
    repository = UsersRepository(database_connection_handler)
    storage = FileStorage(upload_info["AVATAR_DIR"])
    controller = AvatarUploaderController(repository, storage)
    view = AvatarUploaderView(controller)
    return view
```

`src/main/composer/avatar_remover_composer.py`:

```python
from src.configs.global_config import upload_info
from src.models.settings.database_connection_handler import database_connection_handler
from src.models.repositories.users_repository import UsersRepository
from src.drivers.file_storage import FileStorage
from src.controllers.avatar_remover_controller import AvatarRemoverController
from src.views.avatar_remover_view import AvatarRemoverView


def avatar_remover_composer():
    repository = UsersRepository(database_connection_handler)
    storage = FileStorage(upload_info["AVATAR_DIR"])
    controller = AvatarRemoverController(repository, storage)
    view = AvatarRemoverView(controller)
    return view
```

- [ ] **Step 5: Criar as rotas**

`src/main/routes/user_routes.py`:

```python
from fastapi import APIRouter, Depends, UploadFile, File
from fastapi.responses import JSONResponse
from src.views.http_types.http_request import HttpRequest
from src.main.composer.avatar_uploader_composer import avatar_uploader_composer
from src.main.composer.avatar_remover_composer import avatar_remover_composer
from src.main.middlewares.auth_jwt import get_current_user

user_routes = APIRouter(prefix="/users", tags=["Users"])


@user_routes.post("/me/avatar")
async def upload_avatar(
    file: UploadFile = File(...),
    token_info: dict = Depends(get_current_user),
):
    content = await file.read()
    http_request = HttpRequest(
        body={"filename": file.filename, "content": content},
        token_info=token_info,
    )
    view = avatar_uploader_composer()
    response = await view.handle(http_request)
    return JSONResponse(content=response.body, status_code=response.status_code)


@user_routes.delete("/me/avatar")
async def remove_avatar(token_info: dict = Depends(get_current_user)):
    http_request = HttpRequest(token_info=token_info)
    view = avatar_remover_composer()
    response = await view.handle(http_request)
    return JSONResponse(content=response.body, status_code=response.status_code)
```

Em `src/main/server/server.py`, importe e registre:

```python
from src.main.routes.user_routes import user_routes
```
```python
app.include_router(user_routes)
```

- [ ] **Step 6: Conferir as rotas no servidor**

```bash
.venv/bin/python run.py
```
Em outro terminal:
```bash
curl -s http://localhost:3333/openapi.json | python3 -c "import sys,json; print([p for p in json.load(sys.stdin)['paths'] if 'users' in p])"
```
Esperado: `['/users/me/avatar']`.

- [ ] **Step 7: Verificar e commitar**

```bash
.venv/bin/python -m pytest -q
.venv/bin/python -m pylint src
git add src/views src/main
git commit -m "feat: expose the profile picture endpoints"
```

---

### Task 8: `avatar_filename` na resposta de login

**Files:**
- Modify: `src/controllers/user_login_controller.py`, `src/controllers/user_login_controller_test.py`

**Interfaces:**
- Consumes: `users.avatar_filename` (Task 3)
- Produces: `avatar_filename` no corpo de `POST /auth/login`

- [ ] **Step 1: Escrever o teste que falha**

Leia `src/controllers/user_login_controller_test.py` e reuse as fixtures existentes. Acrescente:

```python
# The sidebar needs the picture right after login. Additive and safe in both
# directions: the frontend's Zod drops unknown keys, so an old client ignores it.
@pytest.mark.asyncio
async def test_login_response_includes_the_avatar_filename(mock_repository):
    controller = UserLoginController(mock_repository)

    response = await controller.login({"email": "a@b.com", "password": "senha"})

    assert "avatar_filename" in response
```

**A fixture existente devolve um usuário sem `avatar_filename`.** Acrescente `"avatar_filename": None` a ela, senão o código novo estoura com `KeyError` nos testes que já passavam.

- [ ] **Step 2: Rodar e confirmar que falha**

```bash
.venv/bin/python -m pytest src/controllers/user_login_controller_test.py -v
```

- [ ] **Step 3: Implementar**

Em `__format_response`, acrescente antes de `"token"`:

```python
            "avatar_filename": user["avatar_filename"],
```

- [ ] **Step 4: Rodar, verificar e commitar**

```bash
.venv/bin/python -m pytest -q
.venv/bin/python -m pylint src
git add src/controllers
git commit -m "feat: return the avatar filename on login"
```

---

### Task 9: Validator da listagem

**Files:**
- Create: `src/validators/refund_lister_validator.py`, `src/validators/refund_lister_validator_test.py`

**Interfaces:**
- Produces: `refund_lister_validator(http_request: HttpRequest) -> None`, chamado pela view da Task 12; e os conjuntos `ALLOWED_STATUS_FILTERS`, `SORTABLE_FIELDS`, `ALLOWED_ORDERS`

- [ ] **Step 1: Escrever os testes que falham**

```python
import pytest
from src.errors.types.http_unprocessable_entity_error import HttpUnprocessableEntityError
from src.views.http_types.http_request import HttpRequest
from .refund_lister_validator import refund_lister_validator


def query(**overrides) -> dict:
    base = {"page": 1, "per_page": 10, "name": None, "status": None, "sort": None, "order": None}
    base.update(overrides)
    return base


# All three are optional: leaving them out keeps today's behaviour.
def test_no_optional_parameter_is_valid():
    refund_lister_validator(HttpRequest(query=query()))


@pytest.mark.parametrize("status", ["pending", "approved", "rejected"])
def test_every_allowed_status_is_valid(status):
    refund_lister_validator(HttpRequest(query=query(status=status)))


@pytest.mark.parametrize("sort", ["created_at", "amount_in_cents", "name", "status"])
def test_every_sortable_field_is_valid(sort):
    refund_lister_validator(HttpRequest(query=query(sort=sort)))


@pytest.mark.parametrize("order", ["asc", "desc"])
def test_both_orders_are_valid(order):
    refund_lister_validator(HttpRequest(query=query(order=order)))


def test_unknown_status_raises():
    with pytest.raises(HttpUnprocessableEntityError):
        refund_lister_validator(HttpRequest(query=query(status="whatever")))


# The sort name becomes a lookup key for a real column, so anything outside the
# whitelist must be refused at the boundary.
def test_unknown_sort_field_raises():
    with pytest.raises(HttpUnprocessableEntityError):
        refund_lister_validator(HttpRequest(query=query(sort="password")))


def test_sql_looking_sort_value_raises():
    with pytest.raises(HttpUnprocessableEntityError):
        refund_lister_validator(HttpRequest(query=query(sort="id; DROP TABLE refunds")))


def test_unknown_order_raises():
    with pytest.raises(HttpUnprocessableEntityError):
        refund_lister_validator(HttpRequest(query=query(order="sideways")))
```

- [ ] **Step 2: Rodar e confirmar que falham**

```bash
.venv/bin/python -m pytest src/validators/refund_lister_validator_test.py -v
```

- [ ] **Step 3: Implementar**

```python
from src.errors.types.http_unprocessable_entity_error import HttpUnprocessableEntityError
from src.views.http_types.http_request import HttpRequest

ALLOWED_STATUS_FILTERS = {"pending", "approved", "rejected"}
# These names are keys into RefundsRepository.SORTABLE_COLUMNS, never text
# interpolated into SQL. Refusing anything outside the set here is the first of
# two barriers; the dictionary lookup is the second.
SORTABLE_FIELDS = {"created_at", "amount_in_cents", "name", "status"}
ALLOWED_ORDERS = {"asc", "desc"}


def refund_lister_validator(http_request: HttpRequest) -> None:
    query = http_request.query

    status = query.get("status")
    if status is not None and status not in ALLOWED_STATUS_FILTERS:
        raise HttpUnprocessableEntityError(
            f"Status must be one of: {', '.join(sorted(ALLOWED_STATUS_FILTERS))}"
        )

    sort = query.get("sort")
    if sort is not None and sort not in SORTABLE_FIELDS:
        raise HttpUnprocessableEntityError(
            f"Sort must be one of: {', '.join(sorted(SORTABLE_FIELDS))}"
        )

    order = query.get("order")
    if order is not None and order not in ALLOWED_ORDERS:
        raise HttpUnprocessableEntityError("Order must be one of: asc, desc")
```

- [ ] **Step 4: Rodar, verificar e commitar**

```bash
.venv/bin/python -m pytest -q
.venv/bin/python -m pylint src
git add src/validators
git commit -m "feat: validate the refund list query parameters"
```

---

### Task 10: Repositório — `JOIN`, filtro de status e ordenação

O coração deste ciclo.

**Files:**
- Modify: `src/models/repositories/refunds_repository.py`, `src/models/repositories/interfaces/refunds_repository_interface.py`, `src/models/repositories/refunds_repository_test.py`

**Interfaces:**
- Consumes: `users.avatar_filename` (Task 3)
- Produces:
  - `async select_refunds(page, per_page, name=None, user_id=None, status=None, sort=None, order=None) -> tuple[list[dict], int, int]`
  - `async select_refund_by_id(refund_id: int) -> Optional[dict]`, agora com `user` aninhado
  - Ambos devolvem o reembolso na forma `{id, name, category, amount_in_cents, filename, status, created_at, user: {id, name, avatar_filename}}`. Consumidos pela Task 11.

- [ ] **Step 1: Escrever os testes que falham**

Leia `src/models/repositories/refunds_repository_test.py` antes e reuse suas fixtures. Acrescente:

```python
# The requester's name and picture come from a JOIN, not from a query per row:
# an admin listing 10 refunds must cost one round trip, not eleven.
@pytest.mark.asyncio
async def test_select_refunds_joins_users_and_nests_the_requester(mock_connection, mock_db):
    repository = RefundsRepository(mock_connection)

    await repository.select_refunds(page=1, per_page=10)

    statements = [str(call[0][0]) for call in mock_db.session.execute.call_args_list]
    rows_statement = statements[-1]
    assert "JOIN users" in rows_statement


# The count/sum query needs nothing from users, so joining there would be work
# with no result.
@pytest.mark.asyncio
async def test_the_totals_query_does_not_join_users(mock_connection, mock_db):
    repository = RefundsRepository(mock_connection)

    await repository.select_refunds(page=1, per_page=10)

    totals_statement = str(mock_db.session.execute.call_args_list[0][0][0])
    assert "JOIN users" not in totals_statement


@pytest.mark.asyncio
async def test_status_filter_reaches_both_queries(mock_connection, mock_db):
    repository = RefundsRepository(mock_connection)

    await repository.select_refunds(page=1, per_page=10, status="pending")

    statements = [str(call[0][0]) for call in mock_db.session.execute.call_args_list]
    assert all("refunds.status =" in statement for statement in statements)


@pytest.mark.asyncio
async def test_sort_and_order_reach_the_order_by(mock_connection, mock_db):
    repository = RefundsRepository(mock_connection)

    await repository.select_refunds(page=1, per_page=10, sort="amount_in_cents", order="asc")

    rows_statement = str(mock_db.session.execute.call_args_list[-1][0][0])
    assert "ORDER BY refunds.amount_in_cents ASC" in rows_statement


# Omitting them must preserve today's behaviour exactly.
@pytest.mark.asyncio
async def test_default_ordering_is_newest_first(mock_connection, mock_db):
    repository = RefundsRepository(mock_connection)

    await repository.select_refunds(page=1, per_page=10)

    rows_statement = str(mock_db.session.execute.call_args_list[-1][0][0])
    assert "ORDER BY refunds.created_at DESC" in rows_statement


# An unknown sort name must never reach the query. The validator refuses it
# first, but the repository must not trust that: the dictionary lookup falls
# back to the default instead of interpolating anything.
@pytest.mark.asyncio
async def test_unknown_sort_falls_back_to_the_default_column(mock_connection, mock_db):
    repository = RefundsRepository(mock_connection)

    await repository.select_refunds(page=1, per_page=10, sort="password")

    rows_statement = str(mock_db.session.execute.call_args_list[-1][0][0])
    assert "ORDER BY refunds.created_at DESC" in rows_statement
    assert "password" not in rows_statement
```

- [ ] **Step 2: Rodar e confirmar que falham**

```bash
.venv/bin/python -m pytest src/models/repositories/refunds_repository_test.py -v
```

- [ ] **Step 3: Implementar**

No topo de `src/models/repositories/refunds_repository.py`, acrescente o import de `Users`:

```python
from src.models.entities.users import Users
```

E, no nível do módulo, o mapa de colunas ordenáveis:

```python
# The sort name from the client is a KEY into this dictionary, never text placed
# into SQL. An unknown name cannot produce a column at all — it falls back to the
# default — so no string from a request can ever reach the ORDER BY.
SORTABLE_COLUMNS = {
    "created_at": Refunds.c.created_at,
    "amount_in_cents": Refunds.c.amount_in_cents,
    "name": Refunds.c.name,
    "status": Refunds.c.status,
}
```

Substitua `select_refunds` e `select_refund_by_id` por:

```python
    async def select_refunds(
        self,
        page: int,
        per_page: int,
        name: Optional[str] = None,
        user_id: Optional[int] = None,
        status: Optional[str] = None,
        sort: Optional[str] = None,
        order: Optional[str] = None,
    ) -> tuple[list[dict], int, int]:
        async with self.__db_connection.connect() as session:
            filters = []
            if user_id is not None:
                filters.append(Refunds.c.user_id == user_id)
            if name:
                filters.append(Refunds.c.name.ilike(f"%{name}%"))
            if status:
                filters.append(Refunds.c.status == status)

            # count and sum share the same filters, so they ride in one query
            # instead of two round trips. SUM over an empty set returns NULL,
            # hence the `or 0`. No join here: neither aggregate needs users.
            totals_query = (
                select(func.count(), func.sum(Refunds.c.amount_in_cents))  # pylint: disable=not-callable
                .select_from(Refunds)
                .where(*filters)
            )
            total, total_amount = (await session.execute(totals_query)).one()

            query = (
                select(
                    Refunds,
                    # Labelled because Refunds also has a "name" column; without
                    # the label the two would collide in the row mapping.
                    Users.c.name.label("user_name"),
                    Users.c.avatar_filename,
                )
                .select_from(Refunds.join(Users, Refunds.c.user_id == Users.c.id))
                .where(*filters)
                .order_by(self.__order_by(sort, order))
                .limit(per_page)
                .offset((page - 1) * per_page)
            )
            rows = (await session.execute(query)).fetchall()

            return [self.__to_refund(row) for row in rows], total, total_amount or 0

    async def select_refund_by_id(self, refund_id: int) -> Optional[dict]:
        async with self.__db_connection.connect() as session:
            query = (
                select(
                    Refunds,
                    Users.c.name.label("user_name"),
                    Users.c.avatar_filename,
                )
                .select_from(Refunds.join(Users, Refunds.c.user_id == Users.c.id))
                .where(Refunds.c.id == refund_id)
            )
            refund = (await session.execute(query)).fetchone()
            return self.__to_refund(refund) if refund else None

    def __order_by(self, sort: Optional[str], order: Optional[str]):
        column = SORTABLE_COLUMNS.get(sort or "created_at", Refunds.c.created_at)
        return column.asc() if order == "asc" else column.desc()

    def __to_refund(self, row) -> dict:
        data = dict(row._mapping)
        return {
            "id": data["id"],
            "name": data["name"],
            "category": data["category"],
            "amount_in_cents": data["amount_in_cents"],
            "filename": data["filename"],
            "status": data["status"],
            "created_at": data["created_at"],
            "user": {
                "id": data["user_id"],
                "name": data["user_name"],
                "avatar_filename": data["avatar_filename"],
            },
        }
```

Atualize a assinatura de `select_refunds` na interface, acrescentando os três parâmetros opcionais com os mesmos nomes e tipos.

- [ ] **Step 4: Rodar e confirmar que passam**

```bash
.venv/bin/python -m pytest src/models/repositories -v
```

Os testes existentes de `select_refund_by_id` provavelmente falham agora, porque a linha simulada não tem `user_name`/`avatar_filename`. **Atualize as fixtures para incluir esses campos** — não relaxe as asserções.

- [ ] **Step 5: Verificar e commitar**

```bash
.venv/bin/python -m pytest -q
.venv/bin/python -m pylint src
git add src/models/repositories
git commit -m "feat: join the requester and support status filter and sorting"
```

---

### Task 11: Controllers da listagem e da criação

**Files:**
- Modify: `src/controllers/refund_lister_controller.py`, `src/controllers/refund_lister_controller_test.py`
- Modify: `src/controllers/refund_creator_controller.py`, `src/controllers/refund_creator_controller_test.py`
- Modify: `src/controllers/interfaces/refund_lister_controller_interface.py`

**Interfaces:**
- Consumes: os métodos de repositório da Task 10
- Produces: `list(page, per_page, user_id, role, name=None, status=None, sort=None, order=None)`; a criação devolvendo o formato completo

- [ ] **Step 1: Escrever os testes que falham**

Em `refund_lister_controller_test.py`:

```python
@pytest.mark.asyncio
async def test_list_forwards_status_sort_and_order_to_the_repository(mock_repository):
    controller = RefundListerController(mock_repository)

    await controller.list(
        page=1, per_page=10, user_id=7, role="admin",
        status="pending", sort="amount_in_cents", order="asc",
    )

    mock_repository.select_refunds.assert_awaited_once_with(
        page=1, per_page=10, name=None, user_id=None,
        status="pending", sort="amount_in_cents", order="asc",
    )
```

Em `refund_creator_controller_test.py`:

```python
# The create response must match what GET returns, including status and the
# nested user. Building it from the input dict instead would give three
# different shapes for the same resource — and the frontend reuses one schema
# for all three.
@pytest.mark.asyncio
async def test_create_returns_the_row_it_wrote(mock_repository, mock_storage):
    mock_repository.select_refund_by_id = AsyncMock(
        return_value={
            "id": 1, "name": "Almoço", "category": "food", "amount_in_cents": 1000,
            "filename": "a.jpg", "status": "pending", "created_at": None,
            "user": {"id": 7, "name": "Gabriel", "avatar_filename": None},
        }
    )
    controller = RefundCreatorController(mock_repository, mock_storage)

    response = await controller.create(
        {"name": "Almoço", "category": "food", "amount": 10.0, "filename": "a.jpg", "content": b"x"},
        user_id=7,
    )

    mock_repository.select_refund_by_id.assert_awaited_once_with(1)
    assert response["attributes"]["status"] == "pending"
    assert response["attributes"]["user"]["name"] == "Gabriel"
```

**As fixtures existentes precisam ganhar `select_refund_by_id` como `AsyncMock`** — leia os arquivos e ajuste, sem relaxar as asserções que já existem.

- [ ] **Step 2: Rodar e confirmar que falham**

```bash
.venv/bin/python -m pytest src/controllers -v
```

- [ ] **Step 3: Implementar o lister**

Em `refund_lister_controller.py`, acrescente os parâmetros e repasse-os:

```python
    async def list(
        self,
        page: int,
        per_page: int,
        user_id: int,
        role: str,
        name: Optional[str] = None,
        status: Optional[str] = None,
        sort: Optional[str] = None,
        order: Optional[str] = None,
    ) -> dict:
        # Authorization rule lives here, not in the repository: an admin can see
        # everyone's refunds (no user_id filter), a standard user only their own.
        filter_user_id = None if role == "admin" else user_id

        refunds, total, total_amount = await self.__refunds_repository.select_refunds(
            page=page, per_page=per_page, name=name, user_id=filter_user_id,
            status=status, sort=sort, order=order,
        )

        return self.__format_response(refunds, total, total_amount, page, per_page)
```

Atualize a interface com a mesma assinatura.

- [ ] **Step 4: Implementar o creator**

Em `refund_creator_controller.py`, troque o final de `create` e o `__format_response`:

```python
        refund_id = await self.__refunds_repository.insert_refund(refund_info)

        # Re-reading gives the columns the database filled in (status) and the
        # joined requester, so this response has the same shape as GET.
        refund = await self.__refunds_repository.select_refund_by_id(refund_id)

        return self.__format_response(refund)

    def __format_response(self, refund: dict) -> dict:
        created_at = refund.get("created_at")
        return {
            "type": "Refund",
            "count": 1,
            "attributes": {
                **refund,
                "created_at": created_at.isoformat() if created_at else None,
            },
        }
```

- [ ] **Step 5: Rodar, verificar e commitar**

```bash
.venv/bin/python -m pytest -q
.venv/bin/python -m pylint src
git add src/controllers
git commit -m "feat: forward the new query parameters and return the written row"
```

---

### Task 12: View e rota da listagem

**Files:**
- Modify: `src/views/refund_lister_view.py`, `src/views/refund_lister_view_test.py`, `src/main/routes/refund_routes.py`

**Interfaces:**
- Consumes: `refund_lister_validator` (Task 9), o controller da Task 11
- Produces: `GET /refunds` aceitando `status`, `sort` e `order`

- [ ] **Step 1: Escrever os testes que falham**

Leia `src/views/refund_lister_view_test.py` e reuse suas fixtures. Acrescente:

```python
@pytest.mark.asyncio
async def test_the_new_query_parameters_reach_the_controller(mock_controller):
    view = RefundListerView(mock_controller)
    http_request = HttpRequest(
        query={"page": 1, "per_page": 10, "name": None,
               "status": "pending", "sort": "name", "order": "asc"},
        token_info={"user_id": 7, "role": "admin"},
    )

    await view.handle(http_request)

    assert mock_controller.list.await_args.kwargs["status"] == "pending"
    assert mock_controller.list.await_args.kwargs["sort"] == "name"
    assert mock_controller.list.await_args.kwargs["order"] == "asc"


# The validator runs before the controller: an invalid sort must be refused with
# 422 and never reach the query.
@pytest.mark.asyncio
async def test_invalid_sort_short_circuits_before_the_controller(mock_controller):
    view = RefundListerView(mock_controller)
    http_request = HttpRequest(
        query={"page": 1, "per_page": 10, "name": None,
               "status": None, "sort": "password", "order": None},
        token_info={"user_id": 7, "role": "admin"},
    )

    with pytest.raises(HTTPException) as exception_info:
        await view.handle(http_request)

    assert exception_info.value.status_code == 422
    mock_controller.list.assert_not_awaited()
```

Acrescente `from fastapi import HTTPException` ao topo do arquivo de teste.

- [ ] **Step 2: Rodar e confirmar que falham**

```bash
.venv/bin/python -m pytest src/views/refund_lister_view_test.py -v
```

- [ ] **Step 3: Implementar a view**

Em `src/views/refund_lister_view.py`, acrescente o import do validator e chame-o antes do controller:

```python
from src.validators.refund_lister_validator import refund_lister_validator
```
```python
        try:
            refund_lister_validator(http_request)

            user_id = http_request.token_info["user_id"]
            role = http_request.token_info["role"]

            response = await self.__controller.list(
                page=http_request.query["page"],
                per_page=http_request.query["per_page"],
                name=http_request.query.get("name"),
                user_id=user_id,
                role=role,
                status=http_request.query.get("status"),
                sort=http_request.query.get("sort"),
                order=http_request.query.get("order"),
            )
```

- [ ] **Step 4: Acrescentar os Query params na rota**

Em `src/main/routes/refund_routes.py`, na função `list_refunds`:

```python
async def list_refunds(
    page: int = Query(1, ge=1),
    per_page: int = Query(10, ge=1, le=100),
    name: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    sort: Optional[str] = Query(None),
    order: Optional[str] = Query(None),
    token_info: dict = Depends(get_current_user),
):
    http_request = HttpRequest(
        query={"page": page, "per_page": per_page, "name": name,
               "status": status, "sort": sort, "order": order},
        token_info=token_info,
    )
```

Os três novos ficam como `str` livre de propósito: quem valida é o
`refund_lister_validator`, para que o corpo do erro tenha o mesmo formato
`{"detail": "..."}` do resto do projeto em vez do 422 nativo do FastAPI.

- [ ] **Step 5: Rodar, verificar e commitar**

```bash
.venv/bin/python -m pytest -q
.venv/bin/python -m pylint src
git add src/views src/main
git commit -m "feat: accept status, sort and order on the refund list"
```

---

### Task 13: Verificação ponta a ponta e documentação canônica

**Files:**
- Modify: `docs/domain-model.md`, `docs/business-rules.md`, `docs/index.md`, `docs/decisions/ADR-003-local-receipt-storage.md`
- Modify: `docs/use-cases/UC-003-create-refund.md`, `UC-004-list-refunds.md`, `UC-005-view-refund.md`
- Create: `docs/use-cases/UC-008-upload-avatar.md`, `docs/use-cases/UC-009-remove-avatar.md`
- Modify: `Refund-api.postman_collection.json`

- [ ] **Step 1: Verificação ponta a ponta contra a API real**

Suba o servidor. Faça login como `validacao.visual@example.com` / `Valida123` (o token vem no campo `token`, não `access_token`). Execute e registre o status HTTP real de cada linha:

| Cenário | Esperado |
|---|---|
| `GET /refunds` sem parâmetros novos | 200, ordem por `created_at` desc, cada item com `user` aninhado e sem `user_id` no topo |
| `GET /refunds?status=pending` | 200, só pendentes; `total` e `sum_amount_in_cents` refletindo o filtro |
| `GET /refunds?status=approved` | 200, só aprovados |
| `GET /refunds?sort=amount_in_cents&order=asc` | 200, do menor para o maior |
| `GET /refunds?sort=amount_in_cents&order=desc` | 200, do maior para o menor |
| `GET /refunds?sort=name&order=asc` | 200, alfabética |
| `GET /refunds?sort=status&order=asc` | 200 |
| `GET /refunds?sort=password` | 422 |
| `GET /refunds?order=sideways` | 422 |
| `GET /refunds?status=whatever` | 422 |
| `GET /refunds/{id}` | 200, com `user` aninhado |
| `POST /refunds` | 201, resposta com `status` e `user`, mesmo formato do GET |
| `POST /users/me/avatar` com JPG | 200, `avatar_filename` preenchido |
| `GET /avatars/{filename}` | 200 |
| `POST /users/me/avatar` de novo | 200 — **e o arquivo anterior sumiu de `uploads/avatars/`** |
| `POST /users/me/avatar` com PDF | 422 |
| `DELETE /users/me/avatar` | 200, coluna volta a `NULL` e o arquivo sumiu |
| `DELETE /users/me/avatar` de novo | 200 (idempotente) |
| `POST /auth/login` | 200, com `avatar_filename` |

Confira os arquivos no disco antes e depois das trocas:
```bash
ls uploads/avatars/
```

**Se algum cenário divergir do esperado, PARE e reporte** — é defeito de implementação, não algo para acomodar na documentação.

- [ ] **Step 2: `docs/domain-model.md`**

Acrescente `avatar_filename` à tabela de `User`, descrito como "Nome do arquivo da foto de perfil; nulo quando o usuário usa o avatar padrão".

- [ ] **Step 3: `docs/business-rules.md`**

Acrescente, no formato das vizinhas (regra + **Evidências**):

```markdown
## BR-019 — Formato e tamanho da foto de perfil

A foto de perfil aceita apenas JPG e PNG, validados pela extensão do arquivo, e
no máximo 4MB. Nulo é um estado válido e representa o avatar padrão do produto.

**Evidências:** `src/validators/avatar_upload_validator.py` restringe extensão e
tamanho; `src/models/entities/users.py` declara `avatar_filename` como nulável.
```

- [ ] **Step 4: UC-003, UC-004 e UC-005**

UC-004: documente `status`, `sort` e `order`, com as listas de valores aceitos, o 422 fora delas, e que `total`/`sum_amount_in_cents` respeitam o filtro. Nos três: `user_id` sai do topo e passa a ser o objeto `user` com `id`, `name` e `avatar_filename`. UC-003: a resposta da criação passa a ter o mesmo formato do GET.

- [ ] **Step 5: UC-008 e UC-009**

Crie os dois usando `UC-006-delete-refund.md` como molde estrutural, com endpoint, corpo, tabela de códigos e a regra de que trocar ou remover a foto apaga o arquivo anterior. Acrescente ambos ao `docs/index.md`.

- [ ] **Step 6: ADR-003**

Ela hoje fala só de comprovantes. Amende-a (não crie ADR nova) para cobrir avatares no mesmo diretório-pai, registrar o driver parametrizado como a implementação única, e anotar a data 2026-07-29. Mantenha a estrutura e as convenções do arquivo.

- [ ] **Step 7: Postman**

Acrescente requests para `POST /users/me/avatar`, `DELETE /users/me/avatar` e uma variação de `GET /refunds` com `status`, `sort` e `order`, seguindo a forma dos existentes. Valide:

```bash
.venv/bin/python -m json.tool Refund-api.postman_collection.json > /dev/null
```

- [ ] **Step 8: Verificação final e commit**

```bash
.venv/bin/python -m pytest -q
.venv/bin/python -m pylint src
git add docs Refund-api.postman_collection.json
git commit -m "docs: record the query parameters and the profile picture use cases"
```

---

## Fechamento do ciclo (fora das tasks)

O `learning-path-workflow.md` ainda exige, antes de encerrar:

- **`docs/learning-path-progress.md`** — entrada do ciclo. O aprendizado central aqui não é um item da trilha, é um princípio: **ordenação e filtro têm de viver onde vive a paginação**. Registrar a armadilha que originou o ciclo (um toolbar que filtra 6 de 41 linhas e parece funcionar) e as duas barreiras contra nome de coluna vindo do cliente.
- **`docs/plans/current-state.md`** — o ciclo concluído, o próximo passo (spec do frontend), e a pendência de deploy conjunto.
- **Apresentar o fechamento ao Gabriel** e aguardar autorização.
