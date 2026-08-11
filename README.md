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

**Requer Python 3.13** — a mesma versão do CI e da imagem (`python:3.13-slim`).
O piso é `>= 3.10`, e ele vem de nove pacotes fixados que declaram
`Requires-Python: >=3.10` (entre eles `fastapi`, `starlette`, `urllib3` e
`pytest`); abaixo disso o `pip` recusa o conjunto. Vale conferir antes de criar
o venv, já que em muitos sistemas o `python3` do PATH ainda é uma versão
antiga:

```bash
python3 --version   # precisa ser 3.10+; o projeto usa 3.13
```

1. Crie e ative o ambiente virtual, e instale as dependências:

   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements-dev.txt   # runtime + teste e lint
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

## Endpoints de saúde

São **duas perguntas diferentes**, e confundi-las tem consequência prática:

| Endpoint | Pergunta | Se falhar, o orquestrador deve |
|---|---|---|
| `GET /health` | o processo está vivo? | **reiniciar** |
| `GET /ready` | consegue atender? | **parar de mandar tráfego** |

O `/health` não consulta nada, de propósito: se ele falhasse durante uma queda
de banco, toda instância seria reiniciada em laço — uma indisponibilidade
recuperável viraria apagão. O `/ready` consulta o banco e responde `503`
enquanto ele não estiver acessível, voltando a `200` sozinho quando voltar.

Pela mesma razão, o `HEALTHCHECK` do `Dockerfile` aponta para `/health`, nunca
para `/ready`.

## Produção

O projeto está implantado desde 2026-08-10. A API roda na **Railway**, em
container construído a partir do `Dockerfile` deste repositório; o banco é o
**PostgreSQL da Railway**; os arquivos ficam num **bucket S3 da AWS**; e o
frontend é servido estático por outro serviço da Railway (ver o `README.md` do
`Refund-FrontEnd`).

Para saber se está no ar agora — e não pela existência desta seção:

```bash
curl -s -o /dev/null -w '%{http_code}\n' https://refund-api-production-5a7c.up.railway.app/health
curl -s -o /dev/null -w '%{http_code}\n' https://refund-api-production-5a7c.up.railway.app/ready
```

`/health` é liveness e `/ready` consulta o banco; os dois em 200 significam
processo vivo **e** banco alcançável.

### Variáveis de produção — NOMES, nunca valores

Nenhum valor de produção mora neste repositório. A lista abaixo é o que precisa
existir no ambiente do provedor; os defaults e o formato de cada uma estão no
[`.env.example`](.env.example).

| Variável | Por que ela importa em produção |
|---|---|
| `DATABASE_URL` | **precisa do dialeto `postgresql+asyncpg`** — ver o aviso abaixo |
| `JWT_SECRET` | obrigatória; assina o login **e** as URLs de arquivo do backend `local` |
| `ENVIRONMENT` | com `production`, o startup recusa `CORS_ORIGINS` com `*`, `localhost` ou `127.0.0.1` |
| `CORS_ORIGINS` | precisa conter o domínio do frontend implantado |
| `PUBLIC_BASE_URL` | o domínio público da própria API |
| `STORAGE_BACKEND` | **`s3` em produção** — com `local`, todo arquivo evapora no redeploy |
| `S3_BUCKET`, `S3_REGION` | o bucket e a região dele |
| `S3_ACCESS_KEY_ID`, `S3_SECRET_ACCESS_KEY` | credenciais do usuário de IAM restrito ao bucket |
| `S3_ENDPOINT_URL` | **deixe VAZIA na AWS de verdade**; só se preenche para MinIO ou outro provedor compatível |
| `LOG_LEVEL`, `JWT_ALGORITHM`, `JWT_EXPIRATION_HOURS`, `FILE_URL_TTL_SECONDS` | têm default; só configure para mudar o default |

O `PORT` **não** é configurado por você: a plataforma injeta, e o container
escuta nele. Sem `PORT`, o default de 3333 continua valendo, então
`docker run` local funciona igual.

**A `DATABASE_URL` que o provedor injeta vem errada para este projeto.** Ela
chega na forma libpq (`postgresql://...`), que o SQLAlchemy resolve para um
driver **síncrono** que não está instalado aqui. Como a URL faz parse sem
reclamar e o engine é preguiçoso, a aplicação **subia saudável e morria na
primeira query**. Desde 2026-08-10 o `Settings` recusa o startup nesse caso, e
o erro diz o que escrever: `postgresql+asyncpg://...`.

**Antes do primeiro acesso, aplique as migrations** (`alembic upgrade head`) e
promova o primeiro admin (`python -m init.promote_admin <email>`, sobre uma
conta já cadastrada) — o cadastro público sempre cria `standard` (BR-003).

## Varredura de arquivos órfãos

Arquivo órfão é um arquivo em disco (ou no bucket) que **nenhuma linha do banco
referencia**. Eles aparecem por dois caminhos que nenhuma compensação em
processo alcança: um `SIGKILL` entre gravar o arquivo e commitar a linha, e uma
exclusão de arquivo que falha **depois** do commit — nesse caso a resposta é de
sucesso, corretamente, e o arquivo fica.

```bash
python -m init.sweep_orphans            # relata, não remove nada
python -m init.sweep_orphans --apply    # remove o que relatou
```

**Relata por padrão, de propósito.** Isto apaga arquivo de usuário; um comando
que remove na primeira vez que alguém o roda para ver o que ele faz acaba
removendo algo que não devia.

**Só considera órfão o que tem mais de uma hora.** Um arquivo gravado há dois
segundos, cuja transação ainda não commitou, é indistinguível de um órfão — e
apagá-lo destruiria um comprovante em pleno voo. Uma hora é muito mais que
qualquer requisição daqui leva.

Rodar duas vezes é seguro: a segunda não encontra nada, porque a primeira já
removeu.

## Rotação de secrets

Não há automação para isto — é procedimento, e está escrito porque um segredo
que ninguém sabe como trocar não é trocado.

**`JWT_SECRET`.** Trocar **invalida toda sessão ativa**: os tokens em circulação
foram assinados com a chave antiga e passam a falhar na verificação, então todo
usuário é deslogado. Não há rotação sem interrupção hoje — suportar duas chaves
ao mesmo tempo (verificar com a antiga e a nova, assinar só com a nova) é o que
permitiria, e não existe. **Desde 2026-08-10 isso deixou de ser hipotético:**
existe produção, então existem sessões reais para derrubar.

Trocar também **invalida as URLs assinadas de arquivo em voo** (Item 22), que
são assinadas com a mesma chave. Como elas expiram em 5 minutos, o efeito
prático é uma imagem quebrada por alguns minutos, não perda de dado.

**`S3_SECRET_ACCESS_KEY`.** Gere a chave nova no provedor, atualize a variável e
só então revogue a antiga — nessa ordem, ou há uma janela em que nenhum upload
funciona.

**`DATABASE_URL`.** Rotação de senha do banco derruba as conexões do pool. Com
uma instância, reiniciar o processo depois de trocar é suficiente. Repare que o
valor rotacionado precisa manter o dialeto `postgresql+asyncpg`: o provedor
devolve a forma libpq, e o startup recusa a forma síncrona.

**Quando trocar:** ao suspeitar de exposição, ao desligar o acesso de alguém que
teve os valores, e **sempre que um valor de desenvolvimento tiver sido
promovido a produção**. Esta seção listava um terceiro gatilho — "antes do
primeiro deploy real, porque os valores atuais nasceram em desenvolvimento e já
circularam em terminal" —, que o deploy de 2026-08-10 passou. **Qual valor de
produção é novo e qual foi reaproveitado do desenvolvimento não está registrado
aqui, e não dá para deduzir**: só quem configurou o painel sabe. Quem quiser a
garantia deve rotacionar, não conferir — o custo de rotacionar
desnecessariamente é uma sessão derrubada; o de não rotacionar um valor
reaproveitado é um segredo de produção que já circulou em terminal.

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
