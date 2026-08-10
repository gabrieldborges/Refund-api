# Primeira implantação (Railway + S3) — plano de implementação

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** colocar o Refund no ar pela primeira vez — backend em container e
PostgreSQL na Railway, frontend estático na Railway, arquivos no S3 da AWS.

**Architecture:** três mudanças de código pequenas removem três incompatibilidades
concretas com PaaS (driver síncrono, porta fixa, ausência de servidor estático),
e o resto é configuração. O plano é ordenado para que o impasse circular das
URLs seja resolvido por papelada antes de qualquer deploy, em vez de por
tentativa e erro.

**Tech Stack:** Railway (container + PostgreSQL + estático), AWS S3, Docker,
FastAPI/SQLAlchemy/asyncpg, Vite/React.

## Global Constraints

- Spec: [`2026-08-10-first-deploy-railway-design.md`](../specs/2026-08-10-first-deploy-railway-design.md).
- Branches: **`feat/first-deploy`** no `Refund-api` (já criada, spec em
  `e3a3f5e`) e **`feat/serve-static`** no `Refund-FrontEnd` (a criar).
- **Baseline que nenhuma task pode reduzir**, medida em `18b8678` /
  `b26385e`: backend `pytest` **335 passed, 72 deselected**,
  `pytest -m integration` **72 passed**, `pylint src` **exit 0**; frontend
  **305 testes em 54 arquivos**, `tsc` exit 0, lint 0/0.
- **`pylint src` é aprovado pelo CÓDIGO DE SAÍDA, nunca pela nota.**
  `pylint src; echo $?`.
- Comentários e código em **inglês**; documentação em **português**.
- **Nenhum segredo entra em arquivo versionado.** `JWT_SECRET`,
  `S3_ACCESS_KEY_ID`, `S3_SECRET_ACCESS_KEY` e a senha do banco vivem só no
  painel da Railway. O `.env` é ignorado pelo Git e é de desenvolvimento local.
- **Nenhum segredo entra numa mensagem de chat, num commit ou num log.**
- Fora de escopo: domínio próprio, branch protection, backup, agendamento da
  varredura de órfãos, monitoramento, e os 10 alertas do Dependabot do frontend.

## Quem executa o quê

Este plano tem duas naturezas de task, e confundi-las trava a execução.

| Tasks | Executor | Natureza |
|---|---|---|
| 1, 2, 3 | **Agente** | Código, com teste e commit |
| 4, 5 | **Gabriel** | Console da AWS e painel da Railway |
| 6, 7, 8 | **Gabriel + agente** | Gabriel configura e clica; o agente dita os valores exatos e confere as evidências |
| 9 | **Agente** | Documentação de fechamento |

As tasks 4 a 8 **não podem ser despachadas para um subagente**: elas exigem
credenciais e cliques num navegador. O papel do agente nelas é preparar os
valores exatos, dizer o que observar, e verificar o resultado pelo que for
observável de fora (HTTP, logs, console).

---

## Task 1: a `Settings` recusa um driver síncrono

**Files:**
- Modify: `src/configs/settings.py:116-138` (o `field_validator` existente)
- Test: `src/configs/settings_test.py`

**Interfaces:**
- Consumes: nada
- Produces: nada que outra task importe. O efeito é observável só como recusa
  de startup, e a Task 6 depende dele para que um erro de configuração apareça
  no deploy em vez de no primeiro login.

- [ ] **Step 1: Escrever os testes que falham**

Acrescentar ao fim de `src/configs/settings_test.py`, seguindo o estilo do
arquivo (cada teste constrói sua própria `Settings` com `_env_file=None`):

```python
# A PaaS that injects DATABASE_URL writes the libpq form, `postgresql://`,
# which SQLAlchemy resolves to psycopg2 — a SYNCHRONOUS driver this project
# does not install. make_url parses it happily and the engine is lazy, so
# before this guard the application booted healthy and raised
# ModuleNotFoundError on the first query. That is the exact failure mode this
# whole item exists to remove.
def test_a_synchronous_driver_aborts_startup():
    with pytest.raises(ValidationError) as error:
        Settings(
            _env_file=None,
            database_url="postgresql://user:pass@host:5432/db",
            jwt_secret="s",
        )

    assert "database_url" in str(error.value)


# The message has to say what to do. Whoever pastes a URL from a provider's
# panel has no reason to know that the driver part of the scheme matters.
def test_the_driver_error_names_the_fix():
    with pytest.raises(ValidationError) as error:
        Settings(
            _env_file=None,
            database_url="postgresql://user:pass@host:5432/db",
            jwt_secret="s",
        )

    assert "asyncpg" in str(error.value)


# An unknown driver must fail as a URL problem, not as an AttributeError from
# somewhere deeper.
def test_an_unknown_driver_aborts_startup():
    with pytest.raises(ValidationError) as error:
        Settings(
            _env_file=None,
            database_url="postgresql+nosuchdriver://user:pass@host:5432/db",
            jwt_secret="s",
        )

    assert "database_url" in str(error.value)
```

- [ ] **Step 2: Rodar e ver falhar**

```bash
.venv/bin/pytest src/configs/settings_test.py -q 2>&1 | tail -5
```

Esperado: **3 falhas**, todas por `DID NOT RAISE` — hoje uma URL síncrona é
aceita. Se alguma passar já, pare: significa que a guarda existe de outra forma
e este plano está desatualizado.

- [ ] **Step 3: Implementar**

Em `src/configs/settings.py`, dentro de `check_the_url_can_be_parsed`, trocar o
corpo do `try` e acrescentar a checagem:

```python
        try:
            url = make_url(value)
            dialect = url.get_dialect()
        except ArgumentError as error:
            raise ValueError(f"is not a valid SQLAlchemy URL: {error}") from error

        # create_async_engine needs an ASYNC dialect, and nothing before this
        # checked. get_dialect() only resolves the dialect CLASS — it works
        # even when the DBAPI is not installed, builds no pool and touches no
        # network, so the check stays at the configuration boundary like every
        # other value here.
        if not dialect.is_async:
            raise ValueError(
                f"uses the synchronous driver '{url.drivername}'. This application "
                "builds an async engine, so the URL needs an async driver — write "
                "postgresql+asyncpg://... instead of postgresql://..."
            )

        return value
```

`NoSuchModuleError` é subclasse de `ArgumentError`, então o driver inexistente
já cai no `except` acima — é por isso que o `get_dialect()` fica dentro do
`try`.

Atualizar o docstring do validador para mencionar as duas coisas que ele agora
garante, em vez de só o parse.

- [ ] **Step 4: Rodar e ver passar**

```bash
.venv/bin/pytest src/configs/settings_test.py -q 2>&1 | tail -3
.venv/bin/pytest -q 2>&1 | tail -1
```

Esperado: o arquivo verde, e a suíte inteira em **338 passed, 72 deselected**
(335 + os 3 novos).

- [ ] **Step 5: Conferir que a URL real continua aceita**

```bash
.venv/bin/pytest src/configs/settings_test.py::test_a_valid_database_url_is_accepted -q 2>&1 | tail -2
```

Esperado: passa. Uma guarda que recusa o caso legítimo apenas troca uma queda
por outra — o teste já existia e precisa continuar verde.

- [ ] **Step 6: `pylint` e commit**

```bash
.venv/bin/pylint src; echo "exit=$?"
git add src/configs/settings.py src/configs/settings_test.py
git commit -m "feat: refuse a synchronous database driver at startup

A PaaS that injects DATABASE_URL writes postgresql://, which SQLAlchemy
resolves to psycopg2 — a driver this project does not install. make_url
parses it happily and the engine is lazy, so the process booted healthy and
died on the first query: the exact failure Item 17 exists to prevent,
re-entering through the driver rather than the URL.

get_dialect() resolves the dialect class without importing the DBAPI, so the
check costs no pool and no network and stays at the configuration boundary."
```

---

## Task 2: o container respeita `$PORT`

**Files:**
- Modify: `Dockerfile:48` (`EXPOSE`), `:59-60` (`HEALTHCHECK`), `:72` (`CMD`)

**Interfaces:**
- Consumes: nada
- Produces: uma imagem que escuta em `$PORT` quando ele existe e em 3333 quando
  não. A Task 6 depende disso para o serviço da Railway receber tráfego.

- [ ] **Step 1: Medir o comportamento atual, para ter contra o que comparar**

```bash
docker build -t refund-api:port-before . >/dev/null 2>&1
docker run -d --name port-before -e PORT=8080 -p 8080:8080 \
  -e DATABASE_URL="postgresql+asyncpg://refund_test:refund_test@host.docker.internal:5433/refund_test" \
  -e JWT_SECRET=verification-only refund-api:port-before >/dev/null
sleep 5
curl -s -o /dev/null -w "com PORT=8080 -> %{http_code}\n" http://127.0.0.1:8080/health
docker rm -f port-before >/dev/null
```

Esperado: **000** ou recusa de conexão — o processo ignora `$PORT` e escuta em
3333. Este é o defeito, medido antes de ser corrigido.

- [ ] **Step 2: Trocar o `CMD`**

Linha 72, de:

```dockerfile
CMD ["uvicorn", "src.main.server.server:app", "--host", "0.0.0.0", "--port", "3333"]
```

para:

```dockerfile
# Shell form so ${PORT} expands, and `exec` so uvicorn REPLACES the shell
# instead of becoming its child — without it the shell is PID 1, SIGTERM stops
# at the shell, and the platform's graceful shutdown becomes a kill after
# timeout. The default keeps `docker run` with no PORT working exactly as
# before.
CMD ["sh", "-c", "exec uvicorn src.main.server.server:app --host 0.0.0.0 --port ${PORT:-3333}"]
```

- [ ] **Step 3: Fazer o `HEALTHCHECK` acompanhar**

Linhas 59-60, trocar a URL fixa por uma que leia a variável **em Python**, que
evita brigar com aspas no shell:

```dockerfile
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD python -c "import os,urllib.request,sys; port=os.environ.get('PORT','3333'); sys.exit(0 if urllib.request.urlopen(f'http://127.0.0.1:{port}/health', timeout=2).status == 200 else 1)"
```

Sem isto o healthcheck aponta para 3333 enquanto a aplicação escuta noutra
porta, e o container fica `unhealthy` estando são.

- [ ] **Step 4: Anotar o `EXPOSE`**

Linha 48, acrescentar o comentário — `EXPOSE` é documentação, não publica nada:

```dockerfile
# Documents the DEFAULT port. With $PORT set, the process listens there
# instead; EXPOSE does not publish anything, so it does not need to follow.
EXPOSE 3333
```

- [ ] **Step 5: Provar que a porta customizada funciona**

```bash
docker build -t refund-api:port-after . >/dev/null 2>&1
docker run -d --name port-after -e PORT=8080 -p 8080:8080 \
  -e DATABASE_URL="postgresql+asyncpg://refund_test:refund_test@host.docker.internal:5433/refund_test" \
  -e JWT_SECRET=verification-only refund-api:port-after >/dev/null
sleep 6
curl -s -o /dev/null -w "com PORT=8080 -> %{http_code}\n" http://127.0.0.1:8080/health
docker inspect --format 'healthcheck={{.State.Health.Status}}' port-after
docker rm -f port-after >/dev/null
```

Esperado: `200` e o healthcheck saindo de `starting` para `healthy`. Compare com
o Step 1: mesma imagem, mesmo comando, resultado oposto.

- [ ] **Step 6: Provar que o default não regrediu**

```bash
docker compose up -d >/dev/null 2>&1
docker run -d --name port-default -p 3333:3333 \
  -e DATABASE_URL="postgresql+asyncpg://refund_test:refund_test@host.docker.internal:5433/refund_test" \
  -e JWT_SECRET=verification-only refund-api:port-after >/dev/null
sleep 6
curl -s -o /dev/null -w "sem PORT -> %{http_code}\n" http://127.0.0.1:3333/health
curl -s -o /dev/null -w "/ready sem PORT -> %{http_code}\n" http://127.0.0.1:3333/ready
docker rm -f port-default >/dev/null
```

Esperado: `200` nos dois. O `/ready` em 200 confirma que o banco continua
alcançável — é a verificação do Item 30, repetida.

- [ ] **Step 7: Commit**

```bash
git add Dockerfile
git commit -m "feat: listen on \$PORT when the platform provides one

Railway and most PaaS inject PORT and expect the process to use it; the CMD
pinned 3333 in exec form, which does not expand variables. Shell form with
exec keeps uvicorn as PID 1, so SIGTERM still reaches it and graceful
shutdown is not replaced by a kill after timeout.

The healthcheck reads PORT too, or the container would report unhealthy while
being perfectly fine on another port."
```

---

## Task 3: o frontend serve o build, com fallback de SPA

**Files:**
- Modify: `Refund-FrontEnd/package.json` (devDependencies e scripts)

**Interfaces:**
- Consumes: nada
- Produces: o script `start`, que a Task 7 configura como comando de start do
  serviço na Railway.

- [ ] **Step 1: Criar a branch**

```bash
cd ../Refund-FrontEnd
git checkout -b feat/serve-static
```

- [ ] **Step 2: Medir o ponto de partida**

```bash
npx vitest run 2>&1 | tail -4
npx tsc -b --noEmit; echo "tsc exit=$?"
npm run lint 2>&1 | tail -3
```

Esperado: **305 testes em 54 arquivos**, `tsc` exit 0, lint 0/0. Medir antes de
abrir a branch é a lição registrada em 2026-07-29, quando um commit manual
quebrou a `main` e ninguém notou porque nenhum ciclo mediu o começo.

- [ ] **Step 3: Instalar o `serve`**

```bash
npm install --save-dev serve
```

Dependência nova, e o motivo fica no plano: `vite build` produz arquivos
estáticos e **nada que os sirva**. A alternativa seria um `Dockerfile` com nginx
no frontend, trazendo um arquivo de configuração de servidor para um projeto que
não tem nenhum.

- [ ] **Step 4: Acrescentar o script `start`**

Em `package.json`, na seção `scripts`:

```json
    "start": "serve -s dist -l ${PORT:-4173}"
```

A flag `-s` **é** o fallback de SPA: ela faz qualquer rota desconhecida servir
`index.html`. Sem ela, `/refunds/79/review` funciona ao navegar e devolve 404 ao
recarregar.

- [ ] **Step 5: Provar que o fallback funciona — e que ele é o `-s`**

```bash
npm run build >/dev/null 2>&1
npx serve -s dist -l 4173 >/dev/null 2>&1 &
sleep 2
curl -s -o /dev/null -w "com -s, rota profunda -> %{http_code}\n" http://127.0.0.1:4173/refunds/79/review
kill %1 2>/dev/null

npx serve dist -l 4174 >/dev/null 2>&1 &
sleep 2
curl -s -o /dev/null -w "SEM -s, rota profunda -> %{http_code}\n" http://127.0.0.1:4174/refunds/79/review
kill %1 2>/dev/null
```

Esperado: **200** com `-s` e **404** sem. A segunda metade é a quebra
deliberada — sem ela, "200" só prova que algo respondeu, não que a flag é o que
faz a diferença.

- [ ] **Step 6: Conferir que nada mais mudou**

```bash
npx vitest run 2>&1 | tail -3
npx tsc -b --noEmit; echo "tsc exit=$?"
npm run lint 2>&1 | tail -2
```

Esperado: os mesmos 305 testes, `tsc` 0, lint 0/0. Uma devDependency nova não
deveria mexer em nada disso — se mexeu, entenda por quê antes de commitar.

- [ ] **Step 7: Commit**

```bash
git add package.json package-lock.json
git commit -m "feat: serve the built SPA with a history fallback

vite build produces static files and nothing that serves them. \`serve -s\`
rewrites unknown routes to index.html, which is what a router using real URLs
needs: without it /refunds/79/review works while navigating and 404s on
reload, and reload is exactly what someone does with a link you sent them.

Committed rather than configured in a hosting panel, so it survives recreating
the service and is visible to anyone reading the repository."
```

---

## Task 4 — GABRIEL: bucket e credenciais na AWS

**Não é uma task de agente.** O papel do agente é ditar os valores exatos e
conferir o resultado no fim.

- [ ] **Step 1: Criar o bucket**

No console S3: um bucket novo, região de sua escolha (anote — vira
`S3_REGION`), com **Block Public Access LIGADO**.

O bucket é privado de propósito. O acesso é a URL assinada do Item 22; um
bucket público desfaria o item inteiro, e foi exatamente a ADR-003 que removeu
o serving público de arquivos.

- [ ] **Step 2: Criar um usuário IAM com política restrita**

Um usuário novo, sem acesso ao console, só chave programática. Política —
trocando `NOME-DO-BUCKET` pelo real, nos **dois** lugares:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": ["s3:GetObject", "s3:PutObject", "s3:DeleteObject"],
      "Resource": "arn:aws:s3:::NOME-DO-BUCKET/*"
    },
    {
      "Effect": "Allow",
      "Action": ["s3:ListBucket"],
      "Resource": "arn:aws:s3:::NOME-DO-BUCKET"
    }
  ]
}
```

Os dois blocos existem porque `ListBucket` age sobre o **bucket** e os outros
três sobre os **objetos** — ARNs diferentes. E `ListBucket` não é decoração: é o
que `list_files()` usa na varredura de órfãos do Item 28.

- [ ] **Step 3: Gerar a chave de acesso e guardá-la**

Anote `S3_ACCESS_KEY_ID` e `S3_SECRET_ACCESS_KEY`. **Não cole nenhum dos dois
no chat, num commit ou num arquivo do repositório.** Diferente do `JWT_SECRET`,
que compromete só este app, uma chave IAM vazada compromete a conta.

- [ ] **Step 4: Provar que a credencial funciona, antes de depender dela**

No seu terminal, com as variáveis vivendo só nele:

```bash
cd /Users/gabriel/Desktop/Programing/Projects/ToBeBetter/Refund-api
S3_BUCKET=... S3_REGION=... S3_ACCESS_KEY_ID=... S3_SECRET_ACCESS_KEY=... \
.venv/bin/python3 - <<'PY'
import os, boto3
s3 = boto3.client("s3",
    region_name=os.environ["S3_REGION"],
    aws_access_key_id=os.environ["S3_ACCESS_KEY_ID"],
    aws_secret_access_key=os.environ["S3_SECRET_ACCESS_KEY"])
b = os.environ["S3_BUCKET"]
s3.put_object(Bucket=b, Key="probe.txt", Body=b"ok")
print("put   ok")
print("list  ok:", [o["Key"] for o in s3.list_objects_v2(Bucket=b).get("Contents", [])])
print("get   ok:", s3.get_object(Bucket=b, Key="probe.txt")["Body"].read())
s3.delete_object(Bucket=b, Key="probe.txt")
print("delete ok")
PY
```

Esperado: as quatro linhas. Cada uma exercita uma das quatro permissões, e uma
falha aqui é infinitamente mais barata de diagnosticar do que a mesma falha
dentro de um deploy.

Relate ao agente **apenas** o resultado (quais linhas saíram), nunca as chaves.

---

## Task 5 — GABRIEL: projeto e domínios na Railway

**Não é uma task de agente.** Esta é a etapa que resolve o impasse circular:
os domínios passam a existir **antes** de qualquer variável.

- [ ] **Step 1: Criar o projeto e o banco**

Projeto novo na Railway, e dentro dele um serviço **PostgreSQL**.

- [ ] **Step 2: Criar o serviço do backend**

A partir do repositório `Refund-api`, branch `feat/first-deploy`. A Railway vai
detectar o `Dockerfile`. O deploy vai **falhar** neste ponto, por falta de
`DATABASE_URL` e `JWT_SECRET` — e falhar aqui é o comportamento correto, é o
Item 17 funcionando.

- [ ] **Step 3: Criar o serviço do frontend**

A partir do repositório `Refund-FrontEnd`, branch `feat/serve-static`. Também
vai falhar ou subir errado sem `VITE_API_URL`. Esperado.

- [ ] **Step 4: Gerar os dois domínios públicos**

Em cada um dos dois serviços, gerar o domínio. **É este passo que quebra a
circularidade** — a partir daqui as duas URLs existem e podem ser escritas nas
variáveis uma da outra.

- [ ] **Step 5: Conferir a versão do PostgreSQL**

No banco da Railway, rodar:

```sql
show server_version;
```

Anote o resultado. O `docker-compose.yml` e o CI fixam **PostgreSQL 18** para
espelhar o que o Neon reporta (18.4). Se a Railway servir uma versão maior
diferente, a suíte de integração deixa de espelhar produção — que era a razão
de ela existir —, e isso vira uma decisão a registrar, não um detalhe.

- [ ] **Step 6: Passar as duas URLs ao agente**

URLs públicas não são segredo; são o que o agente precisa para montar os valores
exatos das variáveis das Tasks 6 e 7, incluindo conferir barra final e esquema.

---

## Task 6 — GABRIEL + agente: backend no ar

- [ ] **Step 1: O agente monta a lista de variáveis**

Com a URL do frontend em mãos, o agente produz a lista exata a colar, incluindo
a `DATABASE_URL` composta:

```
ENVIRONMENT=production
LOG_LEVEL=INFO
DATABASE_URL=postgresql+asyncpg://${{Postgres.PGUSER}}:${{Postgres.PGPASSWORD}}@${{Postgres.PGHOST}}:${{Postgres.PGPORT}}/${{Postgres.PGDATABASE}}
JWT_SECRET=<gerado no Step 2>
CORS_ORIGINS=<URL do frontend, sem barra no final>
STORAGE_BACKEND=s3
S3_BUCKET=<da Task 4>
S3_REGION=<da Task 4>
S3_ACCESS_KEY_ID=<da Task 4>
S3_SECRET_ACCESS_KEY=<da Task 4>
```

`S3_ENDPOINT_URL` **não é definida** — vazio significa AWS real; preenchida
significa MinIO.

- [ ] **Step 2: Gerar um `JWT_SECRET` novo**

```bash
python3 -c "import secrets; print(secrets.token_urlsafe(48))"
```

**Nunca o do `.env` local.** Trocar esse segredo desloga todo mundo, o que está
documentado no README como procedimento de rotação.

- [ ] **Step 3: Configurar o comando de pré-deploy**

No serviço do backend, comando de pré-deploy:

```
alembic upgrade head
```

É idempotente, então rodar a cada deploy é correto. O `alembic.ini`, o diretório
`alembic/` e o pacote `alembic` já estão dentro da imagem — verificado.

- [ ] **Step 4: Deploy e leitura do log**

Deixar o deploy rodar e **ler o log**, não só o status. Duas coisas para
procurar: as migrations aplicando, e a ausência de `ValidationError`.

Se aparecer `ValidationError` nomeando `database_url` com a mensagem sobre
driver síncrono, a Task 1 fez o trabalho dela: o prefixo está errado e o
problema apareceu no startup em vez de no primeiro login.

- [ ] **Step 5: As duas verificações que separam "subiu" de "funciona"**

```bash
curl -s -o /dev/null -w "health -> %{http_code}\n" https://<backend>/health
curl -s -o /dev/null -w "ready  -> %{http_code}\n" https://<backend>/ready
```

Esperado: **200 nos dois**. `/health` 200 com `/ready` 503 é o sintoma exato da
armadilha do driver, ou de o banco não estar alcançável — o `/ready` é a única
das duas que prova a conexão.

- [ ] **Step 6: Conferir que o log saiu em JSON com `request_id`**

```bash
curl -si https://<backend>/rota-que-nao-existe | grep -i "x-request-id"
```

Comparar o id do header com a linha de log correspondente no painel da Railway.
Com `ENVIRONMENT=production` o formato JSON do Item 24 passa a valer de verdade
— até aqui ele só tinha sido exercido localmente.

---

## Task 7 — GABRIEL + agente: frontend no ar

- [ ] **Step 1: Variável e comando de start**

No serviço do frontend:

```
VITE_API_URL=<URL do backend, sem barra no final>
```

Comando de start: `npm run start`. O build (`npm run build`) a Railway roda
sozinha ao detectar o projeto Node.

`VITE_API_URL` é lida **em tempo de build** (`src/lib/api.ts`), então mudá-la
depois exige **rebuild**, não restart. Vale saber antes de passar meia hora
mexendo em variável e recarregando a página.

- [ ] **Step 2: Deploy e conferência do fallback**

```bash
curl -s -o /dev/null -w "raiz          -> %{http_code}\n" https://<frontend>/
curl -s -o /dev/null -w "rota profunda -> %{http_code}\n" https://<frontend>/refunds/79/review
```

Esperado: **200 nos dois**. Um 404 no segundo significa que o comando de start
não é o `npm run start` da Task 3, ou que o `-s` sumiu.

- [ ] **Step 3: O teste que fecha a circularidade**

Abrir o frontend no navegador e **fazer login**. Se o `CORS_ORIGINS` do backend
não contiver exatamente esta origem, o navegador recusa a pergunta prévia e o
sintoma **parece rejeição de credencial**, embora a requisição real nunca tenha
sido tentada. Se acontecer, o discriminador é o console do navegador, que fala
em CORS, e não a tela.

---

## Task 8 — GABRIEL + agente: primeiro admin e verificação ponta a ponta

- [ ] **Step 1: Criar o primeiro admin**

Cadastrar um usuário pela tela — o cadastro público só cria `standard` — e
promovê-lo por um comando pontual no serviço do backend:

```
python -m init.promote_admin <email-cadastrado>
```

- [ ] **Step 2: O fluxo que prova o Item 22 contra a AWS de verdade**

No navegador: criar um reembolso com comprovante em imagem, abrir o detalhe, e
na aba Network confirmar que a requisição que busca **os bytes** vai para o S3
com `?X-Amz-...` na query e **sem cabeçalho `Authorization`**.

A distinção importa, e já enganou este checklist uma vez: há **duas**
requisições — a de metadados (`/refunds/{id}/receipt`, autenticada, devolve
`{url, media_type}`) e a do arquivo. Só a segunda prova o item.

- [ ] **Step 3: Confirmar o objeto no bucket**

No console da AWS, ver o objeto sob o prefixo de comprovantes. Isso prova que o
arquivo foi para o S3 e não para o disco efêmero da instância — o pior dos cinco
bloqueios do primeiro deploy, e o único que perde dado em silêncio.

- [ ] **Step 4: O fluxo de admin**

Aprovar, marcar como pago com comprovante, e conferir o histórico de revisões.
Cobre `UC-007`, `UC-012` e `UC-013` num ambiente real.

- [ ] **Step 5: Um erro, ponta a ponta**

Provocar uma falha de validação (enviar o formulário vazio) e confirmar que a
resposta é `problem+json` com `request_id`, e que **o mesmo id aparece no log da
Railway**. Fecha os Itens 23 e 24 em produção.

- [ ] **Step 6: F5 numa rota profunda, já autenticado**

Recarregar `/refunds/{id}` estando logado. Prova o fallback de SPA no caminho
real, não só via `curl`.

---

## Task 9: fechamento e documentação

**Files:**
- Modify: `docs/plans/current-state.md`, `docs/learning-path-progress.md`,
  `docs/decisions/ADR-002-postgresql-neon.md`,
  `docs/decisions/ADR-003-local-receipt-storage.md`, `README.md`
- Modify: `Refund-FrontEnd/README.md`

- [ ] **Step 1: Registrar o deploy no `current-state.md`**

A frase que sobreviveu a todas as fases — *"não existe deploy"* — deixa de ser
verdadeira e precisa ser reescrita, não apagada: o que ela dizia continua sendo
a explicação de por que os cinco bloqueios existiam.

Registrar as URLs, as decisões (Railway, S3, PostgreSQL da Railway), e o que
**passou a ser verdade de novo**: existe produção, então a divergência de
contrato entre os dois repositórios volta a ter dentes, e o aviso de que trocar
o `JWT_SECRET` desloga todo mundo deixa de ser hipotético.

- [ ] **Step 2: Corrigir a afirmação sobre CORS de bucket**

O documento diz que uma implantação com S3 "precisa liberar o domínio do
frontend no CORS do bucket". É falso para a UI atual: `ReceiptPreview.tsx`
renderiza com `<img src>` e `<object data>`, e nenhum dos dois é requisição
controlada por CORS. Corrigir **com a condição** que a tornaria verdadeira de
novo — qualquer código que busque o arquivo por JavaScript.

- [ ] **Step 3: Amendar a ADR-002 com a versão real do PostgreSQL**

Com o resultado do `show server_version` da Task 5. Se divergir do 18 que o
`docker-compose.yml` e o CI fixam, registrar a divergência e o que ela custa: a
suíte de integração deixa de espelhar produção, que era a razão de ela existir.

- [ ] **Step 4: Amendar a ADR-003 com o backend em uso**

Ela documenta o armazenamento de comprovantes. Registrar que produção roda com
`STORAGE_BACKEND=s3` na AWS, e que o caminho `local` continua sendo o de
desenvolvimento.

- [ ] **Step 5: Registrar as pendências novas, uma delas com data**

- **O plano gratuito da AWS termina.** Registrar **a data**, para virar decisão
  antes de virar cobrança.
- **A Railway cobra.** Custo recorrente pequeno, não zero.
- **Instância única:** o rate limit do Item 27 zera a cada restart, e agora isso
  vale sobre algo real.
- **Sem backup** do banco nem dos arquivos.
- **`alembic downgrade` agora alcança produção.** Antes era um comando
  inofensivo numa máquina de desenvolvimento.

- [ ] **Step 6: Atualizar os dois READMEs**

O do backend com as variáveis de produção (nomes, nunca valores) e o de rotação
de segredo; o do frontend com o script `start` e o motivo do `-s`.

- [ ] **Step 7: Acrescentar ao diário**

O que se aprendeu e não cabe no retrato: a armadilha do driver síncrono e por
que ela burlava a guarda do Item 17; o impasse circular das URLs e por que ele
só existe no primeiro deploy; e a afirmação sobre CORS de bucket que a
verificação derrubou.

- [ ] **Step 8: Verificação repetida e commit**

```bash
.venv/bin/pytest -q 2>&1 | tail -1
.venv/bin/pytest -m integration -q 2>&1 | tail -1
.venv/bin/pylint src; echo "exit=$?"
```

Esperado: **338 passed, 72 deselected**, **72 passed**, exit 0.

- [ ] **Step 9: O que fazer com as duas branches — decisão do Gabriel**

O merge é dele, como em todos os ciclos anteriores. Mas aqui há uma diferença
que nenhum ciclo anterior teve, e ela precisa ser dita em voz alta:

**os serviços da Railway foram criados apontando para as branches**
(`feat/first-deploy` e `feat/serve-static`). Depois do merge, cada serviço
precisa ser reapontado para `main`, ou a produção fica presa a uma branch que
ninguém mais atualiza — e, pior, a branch pode ser apagada com os serviços
ainda apontando para ela.

Duas ordens possíveis, e a escolha é dele: reapontar para `main` **antes** de
apagar as branches, ou mesclar, reapontar e só então apagar. A única ordem
errada é apagar primeiro.

Registrar no `current-state.md` a qual referência cada serviço aponta ao fim —
é o tipo de fato que nasce verdadeiro e morre em silêncio, e este documento já
tem onze ocorrências disso.

---

## Verificação final — o critério de pronto

- [ ] `/health` e `/ready` ambos **200** no domínio público
- [ ] Login funcionando pelo navegador (fecha a circularidade do CORS)
- [ ] Comprovante carregando do S3 **sem `Authorization`**, com o objeto
      visível no console da AWS
- [ ] Rota profunda respondendo 200 no F5
- [ ] `request_id` da resposta de erro batendo com a linha de log da Railway
- [ ] Fluxo de admin completo: aprovar, pagar, histórico
- [ ] Versão do PostgreSQL da Railway anotada e comparada com o CI
- [ ] Backend **338 passed**, integração **72 passed**, `pylint` exit 0
- [ ] Frontend **305 testes**, `tsc` 0, lint 0/0
- [ ] Nenhum segredo em arquivo versionado, commit ou log
