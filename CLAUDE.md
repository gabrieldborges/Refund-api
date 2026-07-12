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
  estaticamente em `/receipts/{filename}`. Regras: JPG/PNG/PDF, máx. 2MB.
- Autenticação: implementada (`POST /auth/register`, `POST /auth/login`),
  seguindo o padrão do meu projeto `jwt` (drivers `PasswordHandler`/`JwtHandler`),
  adaptado pro estilo SQLAlchemy Core + async deste projeto. Dois papéis:
  `standard` (vê só os próprios reembolsos) e `admin` (vê todos). Registro
  sempre força `role: "standard"` no servidor — nunca aceitar `role` vindo do
  cliente no cadastro (evita auto-promoção a admin). Cada refund tem `user_id`
  (FK obrigatória).
- `src/main/middlewares/auth_jwt.py` tem `get_current_user` (dependency do
  FastAPI que decodifica o JWT do header `Authorization: Bearer`), pronta mas
  ainda não usada em nenhuma rota — será aplicada nas rotas de refund
  (próximo passo), e lá também vamos criar um `require_admin` em cima dela.
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