# Refund API

Backend do sistema de reembolso (Clean Architecture, mesmo padrão dos outros
projetos Python deste workspace). Frontend em `React/Refund`, consumindo esta API.

## Environment setup

Crie um `.env` na raiz do projeto:

```env
DATABASE_URL=sqlite+aiosqlite:///refund.db
UPLOAD_DIR=uploads/receipts
JWT_SECRET=uma-chave-secreta-aleatoria
JWT_ALGORITHM=HS256
JWT_EXPIRATION_HOURS=8
```

> Não commitar `.env` (já está no `.gitignore`).

## Rodando localmente

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python run.py
```

A API sobe em `http://localhost:3333`.
Documentação automática (Swagger) em `http://localhost:3333/docs`.

O banco (`refund.db`) e a tabela `refunds` são criados automaticamente no
startup do servidor (ver `src/main/server/server.py`), a partir da entidade
definida em `src/models/entities/refunds.py`. Não é preciso rodar `init/schema.sql`
manualmente — ele existe só como referência do schema.

## Estrutura

Segue o mesmo padrão em camadas dos outros projetos Python:

```
src/
├── models/{entities,repositories,settings}   # entidades, acesso a dados, conexão
├── controllers/                              # regra de negócio
├── views/                                    # adaptador HTTP
├── validators/                               # validação de entrada (Pydantic)
├── errors/                                   # erros customizados + handler central
└── main/{composer,routes,server}             # injeção de dependência e bootstrap
```

Os arquivos de recibo enviados ficam em `uploads/receipts/` e são servidos
estaticamente em `/receipts/{filename}`.

## Autenticação

- `POST /auth/register` — `{name, email, password}`. Sempre cria usuário com
  role `standard` (role não é aceito vindo do cliente).
- `POST /auth/login` — `{email, password}`. Retorna um JWT (`token`) contendo
  `user_id` e `role`, expira em `JWT_EXPIRATION_HOURS`.
- Rotas protegidas devem usar `Depends(get_current_user)`
  (`src/main/middlewares/auth_jwt.py`), passando o token no header
  `Authorization: Bearer <token>`.

## Testando no Postman

Importe [`Refund-api.postman_collection.json`](Refund-api.postman_collection.json)
(File > Import). A collection já vem com:
- Variável `host` (`http://localhost:3333`).
- **Auth - Login** salva o token automaticamente na variável `{{token}}` (script
  na aba Tests) — as demais requisições já usam `Authorization: Bearer {{token}}`.
- **Refunds - Create** salva o `id` criado em `{{refund_id}}`, usado por
  **Get by ID** e **Delete**.
- Rode na ordem: Register → Login → Create → List → Get by ID → Delete.
