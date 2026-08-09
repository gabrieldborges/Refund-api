# Refund API

Backend do sistema de reembolso, organizado com Clean Architecture. O frontend
irmão está em [`../Refund-FrontEnd`](../Refund-FrontEnd).

Os requisitos e as decisões compartilhadas do produto estão na
[documentação canônica](docs/index.md).

## Environment setup

Copie o [`.env.example`](.env.example) para `.env` e preencha:

```bash
cp .env.example .env
```

`usuario`, `senha` e `host` são valores de exemplo: substitua-os pelas
credenciais do seu ambiente. Nunca versione o `.env` (ele já está no
`.gitignore`) nem exponha credenciais reais na documentação.

Só duas variáveis são **obrigatórias** — `DATABASE_URL` e `JWT_SECRET`. As
demais têm default. A lista completa, com os defaults, está no `.env.example`.

A configuração é validada no startup por `src/configs/settings.py`
([ADR-004](docs/decisions/ADR-004-typed-settings.md)): se uma variável
obrigatória faltar ou tiver tipo inválido, a aplicação **não sobe** e o erro
nomeia o campo. Antes disso, um `JWT_SECRET` ausente deixava a aplicação subir
normalmente e falhava só no primeiro login de um usuário.

A suíte de testes **não** usa o seu `.env`: o `conftest.py` da raiz fixa valores
fictícios, então `pytest` funciona mesmo sem `.env` e nunca alcança o banco real.

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

## Rotação de secrets

Não há automação para isto — é procedimento, e está escrito porque um segredo
que ninguém sabe como trocar não é trocado.

**`JWT_SECRET`.** Trocar **invalida toda sessão ativa**: os tokens em circulação
foram assinados com a chave antiga e passam a falhar na verificação, então todo
usuário é deslogado. Não há rotação sem interrupção hoje — suportar duas chaves
ao mesmo tempo (verificar com a antiga e a nova, assinar só com a nova) é o que
permitiria, e não existe.

Trocar também **invalida as URLs assinadas de arquivo em voo** (Item 22), que
são assinadas com a mesma chave. Como elas expiram em 5 minutos, o efeito
prático é uma imagem quebrada por alguns minutos, não perda de dado.

**`S3_SECRET_ACCESS_KEY`.** Gere a chave nova no provedor, atualize a variável e
só então revogue a antiga — nessa ordem, ou há uma janela em que nenhum upload
funciona.

**`DATABASE_URL`.** Rotação de senha do banco derruba as conexões do pool. Com
uma instância, reiniciar o processo depois de trocar é suficiente.

**Quando trocar:** ao suspeitar de exposição, ao desligar o acesso de alguém que
teve os valores, e antes do primeiro deploy real — os valores atuais nasceram
em desenvolvimento e já circularam em terminal.

## Testes

São duas suítes, separadas por marker do pytest.

```bash
pytest                  # a suíte mockada: rápida, sem banco, sem Docker
pytest -m integration   # contra um PostgreSQL de verdade (precisa do container)
```

A primeira é a que roda o tempo todo e **não exige nada além das dependências**.
A segunda precisa do banco descartável:

```bash
docker compose up -d    # PostgreSQL 18 (porta 5433) + MinIO (porta 9100)
pytest -m integration
docker compose down     # joga fora
```

O container está fixado na **mesma versão maior que a produção** (Neon reporta
18.4). Testar contra outra maior esconderia justamente as diferenças que os
testes de integração existem para expor — e é por isso que SQLite não é uma
opção aqui, nem como atalho local.

O que cada suíte alcança: a mockada prova que os repositories **montam** o SQL
certo; a de integração prova que o PostgreSQL **aceita** esse SQL e se comporta
como assumimos — constraints, defaults do schema, chaves estrangeiras,
agregados reais, e o `lock_timeout` sob contenção de linha. O MinIO cumpre o
mesmo papel para o object storage: os testes do `S3FileStorage` gravam num
bucket de verdade e baixam por URL assinada de verdade.

## Armazenamento de arquivos

Duas implementações da mesma interface, escolhidas por `STORAGE_BACKEND`:

| | `local` (padrão) | `s3` |
|---|---|---|
| Onde o arquivo mora | disco da instância | bucket S3-compatível |
| Sobrevive a um redeploy | **não** | sim |
| Como a URL é assinada | JWT de vida curta desta API | presigned URL do provedor |

As rotas de arquivo (`/refunds/{id}/receipt`, `/refunds/{id}/payment-receipt`,
`/users/{id}/avatar`) devolvem **uma URL**, não os bytes — é o que permite um
`<img src>` funcionar, já que uma tag `<img>` não sabe enviar
`Authorization: Bearer`.

A autorização continua sendo conferida antes de a URL ser gerada; o que muda é
que ela passa a valer por `FILE_URL_TTL_SECONDS` (padrão 300s) em vez de ser
reconferida a cada requisição. Ver
[ADR-003](docs/decisions/ADR-003-local-receipt-storage.md).

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
