# Perfil do desenvolvedor

Antes de decisões de arquitetura, nomenclatura ou estilo neste projeto, consulte
[CODING_PROFILE.md](../../CODING_PROFILE.md) — ele descreve meu stack, convenções,
nível por tecnologia, padrões recorrentes e como prefiro que a IA colabore comigo.

## Notas específicas deste projeto

- Backend do sistema de reembolso (Refund). Frontend irmão em `../Refund` (React).
- Segue a mesma Clean Architecture dos meus outros projetos Python
  (models/controllers/views/validators/errors/main-composer).
- Banco: SQLite local por enquanto (`DATABASE_URL` no `.env`). Migração para
  Postgres em nuvem é um passo futuro planejado, não fazer sem perguntar antes.
- Upload de recibo: salvo em disco local (`uploads/receipts/`), servido
  estaticamente em `/receipts/{filename}`. Regras: JPG/PNG/PDF, máx. 4MB.
- Autenticação: implementada (`POST /auth/register`, `POST /auth/login`),
  seguindo o padrão do meu projeto `jwt` (drivers `PasswordHandler`/`JwtHandler`),
  adaptado pro estilo SQLAlchemy Core + async deste projeto. Dois papéis:
  `standard` (vê só os próprios reembolsos) e `admin` (vê todos). Registro
  sempre força `role: "standard"` no servidor — nunca aceitar `role` vindo do
  cliente no cadastro (evita auto-promoção a admin). Cada refund tem `user_id`
  (FK obrigatória).
- `src/main/middlewares/auth_jwt.py` tem `get_current_user` (dependency do
  FastAPI), já aplicada em `POST /refunds`. **Regra importante**: qualquer
  `Depends(...)` deve levantar `fastapi.HTTPException` diretamente, nunca os
  nossos `Http*Error` customizados — dependencies do FastAPI rodam *antes* da
  rota, fora do `try/except` da view, então nosso `error_handler` nunca as vê
  (descobri isso na prática: sem token, a API devolvia 500 em vez de 401, até
  eu trocar `HttpUnauthorizedError` por `HTTPException(401, ...)` dentro do
  `get_current_user`). Vale a mesma regra para o futuro `require_admin`.
- Reembolsos (`POST /refunds`, multipart/form-data): `RefundCreatorController`
  + `RefundCreatorView` + `refund_creator_validator` (categoria, valor, tipo e
  tamanho do arquivo) + driver `ReceiptStorage` (injetado via interface,
  `ReceiptStorageInterface`, porque toca disco — igual repository). Valor
  convertido de reais pro `amount_in_cents` dentro do controller.
  **Lição aprendida**: o tipo de arquivo é validado pela **extensão do nome**
  (`.jpg/.jpeg/.png/.pdf`), não pelo `Content-Type` que o cliente manda no
  upload — esse header é frágil na prática (o Postman mandava
  `application/octet-stream` pra um JPG de verdade dependendo de como o
  arquivo foi anexado, e isso travava o upload com 422). `ALLOWED_CONTENT_TYPES`
  foi removido do `global_config.py` por ficar sem uso.
- Listagem (`GET /refunds?page=&per_page=&name=`): `RefundListerController` +
  `RefundListerView`. Query params validados direto na rota via `Query(..., ge=1)`
  (sem validator próprio, mesmo princípio do `Form(...)`). Regra de autorização
  fica no controller: `admin` → `user_id=None` (vê todos), `standard` → seu
  próprio `user_id` (repository só filtra o que mandarem). Resposta inclui
  `total`/`page`/`per_page`/`total_pages` pro frontend montar a paginação.
  **Lição aprendida**: o repository devolve `created_at` como `datetime` puro
  (vindo direto da linha do SQLAlchemy) — isso quebra o `JSONResponse` do
  FastAPI (`TypeError: Object of type datetime is not JSON serializable`).
  Convertemos pra `.isoformat()` dentro do `__format_response` do controller
  (é responsabilidade dele moldar a saída pra HTTP, não do repository).
- Detalhes (`GET /refunds/{id}`) e exclusão (`DELETE /refunds/{id}`):
  `RefundFinderController`/`RefundDeleterController` (mesma conversão de
  `created_at` do lister). **Regra de segurança repetida nos dois**: se o
  reembolso não existe OU pertence a outro usuário (e quem pede não é admin),
  devolve `404` nos dois casos — nunca `403`, pra não revelar que aquele ID
  existe (o mesmo princípio do "Invalid credentials" genérico no login).
  `RefundDeleterController` também apaga o arquivo do recibo via
  `ReceiptStorage.delete` depois de remover a linha do banco. Duplicação
  pequena e aceita entre `RefundFinderView`/`RefundDeleterView` (3 linhas pra
  extrair `refund_id`/`user_id`/`role`) — documentada com
  `pylint: disable=duplicate-code`, não virou abstração porque não compensa.
- **Padrão de código: testes com pytest são obrigatórios junto de cada camada
  nova** (não deixar acumular para uma etapa separada no fim). Um `_test.py`
  ao lado de cada arquivo de origem, seguindo o estilo do projeto `FastAPI`
  (fixtures com `MagicMock`/`AsyncMock`, `@pytest.mark.asyncio` em teste
  assíncrono). Fixtures repetidas entre arquivos de teste no mesmo diretório
  vão para um `conftest.py` local (ex: `src/models/repositories/conftest.py`).
  Rodar `pytest` e `pylint src` depois de qualquer mudança antes de dar por
  concluído.
- **Comentários nos testes: sempre descritivos e em inglês.** Cada fixture e
  cada teste devem ter um comentário curto explicando o cenário/porquê (ex:
  "happy path", "security: never expose the password"), não só o que o
  código faz. Isso vale mesmo quando o resto do projeto mistura português
  (notas, comentários gerais) — comentário de teste é sempre inglês.