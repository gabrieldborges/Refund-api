# Refund API

Backend do sistema de reembolso, organizado com Clean Architecture. O frontend
irmão está em [`../Refund-FrontEnd`](../Refund-FrontEnd).

Os requisitos e as decisões compartilhadas do produto estão na
[documentação canônica](docs/index.md).

## Environment setup

Crie um `.env` na raiz do projeto:

```env
DATABASE_URL=postgresql+asyncpg://usuario:senha@host/database?ssl=require
UPLOAD_DIR=uploads/receipts
AVATAR_DIR=uploads/avatars
PAYMENT_DIR=uploads/payment_receipts
JWT_SECRET=uma-chave-secreta-aleatoria
JWT_ALGORITHM=HS256
JWT_EXPIRATION_HOURS=8
```

`usuario`, `senha` e `host` são valores de exemplo: substitua-os pelas
credenciais do seu ambiente. Nunca versione o `.env` (ele já está no
`.gitignore`) nem exponha credenciais reais na documentação.

## Rodando localmente

1. Crie e ative o ambiente virtual, e instale as dependências:

   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```

2. Aplique as migrations (obrigatório antes de subir o servidor pela primeira
   vez — sem isso a primeira requisição falha com `UndefinedTable`):

   ```bash
   alembic upgrade head
   ```

   O schema do banco é governado pelo Alembic (`alembic/versions/`). Rodar
   `alembic upgrade head` é seguro a qualquer momento: ele aplica apenas as
   migrations que faltam. O `init/schema.sql` continua existindo só como
   referência histórica.

3. Suba o servidor:

   ```bash
   python run.py
   ```

A API sobe em `http://localhost:3333`.
Documentação automática (Swagger) em `http://localhost:3333/docs`.

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

Os arquivos de recibo enviados ficam em `uploads/receipts/`; as fotos de
perfil ficam em `uploads/avatars/`; os comprovantes de pagamento ficam em
`uploads/payment_receipts/`. Nenhum dos três diretórios é servido
estaticamente — todos exigem um JWT válido e são obtidos, respectivamente,
por `GET /refunds/{refund_id}/receipt`, `GET /users/{user_id}/avatar` e
`GET /refunds/{refund_id}/payment-receipt`.

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
  **Get by ID**, **Review Status** e **Delete**.
- Rode na ordem: Register → Login → Create → List → Get by ID → Review Status
  → Delete.
- **Review Status** só funciona logado como `admin` (promova um usuário
  diretamente no banco, já que o cadastro público sempre cria `standard` —
  BR-003) e diferente do dono da solicitação (BR-016); com um usuário
  `standard`, ou revisando a própria solicitação, a API responde `403`.
- Note que **Review Status** decide a solicitação (`approved` ou `rejected`),
  e uma solicitação decidida não pode mais ser excluída (BR-015): rodar
  **Delete** depois de **Review Status** sobre o mesmo `refund_id` responde
  `422`. Para testar o fluxo completo de exclusão, crie uma segunda solicitação
  e pule **Review Status** para ela.
