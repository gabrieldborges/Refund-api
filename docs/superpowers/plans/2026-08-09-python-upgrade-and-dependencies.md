# Python 3.13 e dependências — plano de implementação

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** tirar o `Refund-api` do Python 3.9, subir para 3.13, e levar as
dependências até as versões que zeram os 37 alertas do Dependabot — sem
alterar comportamento nenhum da aplicação.

**Architecture:** a mudança é de ambiente, não de código. A aplicação só é
tocada se a subida quebrar algo. O plano é desenhado como um **bissetor**: o
Python sobe sozinho na Task 1, com as dependências velhas, e só depois as
dependências sobem na Task 2. Se algo falhar, a task diz qual das duas causas
foi — que é justamente o que um único commit "subiu tudo" tornaria impossível
descobrir.

**Tech Stack:** Python 3.13 (Homebrew), FastAPI, Starlette, SQLAlchemy +
asyncpg, boto3/MinIO, pytest, pylint, Docker, GitHub Actions.

## Global Constraints

- Repositório: **`Refund-api`**. Branch: **`chore/python-313-upgrade`** (já
  criada, com a spec commitada em `9a58a62`).
- Spec: [`2026-08-09-python-upgrade-and-dependencies-design.md`](../specs/2026-08-09-python-upgrade-and-dependencies-design.md).
- **Baseline medida em `befd1f4`, antes da branch:** `pytest` **334 passed, 72
  deselected**; `pylint src` **exit 0**; frontend 305 testes em 54 arquivos.
  Nenhuma task pode reduzir esses números.
- **`pylint src` é aprovado pelo CÓDIGO DE SAÍDA, nunca pela nota.** Sempre
  `pylint src; echo $?` — o comando imprime `10.00/10` e sai com 8 quando
  emitiu qualquer mensagem. O projeto reportou aprovação errada por meses por
  causa disso.
- **Versões fixadas com `==`**, no estilo que os dois arquivos de requirements
  já usam. Nada entra sem número.
- **Nada de refresh geral.** Só sobem os pacotes listados neste plano. Um
  pacote que não tem advisory e não é arrastado por resolução **fica onde
  está**.
- Comentários e código em **inglês**; documentação em **português** — a regra
  dos `AGENTS.md`. Arquivo que já tem comentário em português mantém a língua.
- **Fora de escopo, não tocar:** o import do `boto3` no topo de
  `src/drivers/storage_factory.py`, branch protection, os 3 arquivos órfãos,
  os usuários de teste no banco, e qualquer pendência de frontend que não seja
  ligar o Dependabot.

### Uma nota sobre TDD neste plano

Não há comportamento novo para test-drivar: o ciclo não acrescenta uma
funcionalidade, ele troca o chão embaixo de 406 testes que já existem. O
equivalente honesto ao vermelho-verde aqui são as **quebras deliberadas** da
Task 5 — reintroduzir um bug conhecido e conferir que a suíte o pega. Sem isso,
"tudo verde" prova apenas que nada explodiu, não que a rede continua armada. É
o padrão que o projeto usa desde o Item 19.

### Versões-alvo, todas resolvidas contra o PyPI em 2026-08-09

| Pacote | De | Para | Por quê |
|---|---|---|---|
| Python | 3.9.6 | **3.13** | Nenhuma correção existe abaixo de 3.10 |
| `fastapi` | 0.128.8 | **0.141.1** | 0.128 declara `starlette<1.0.0` e trava a linha corrigida |
| `starlette` | 0.49.3 | **1.6.0** | 5 advisories; a correção mais antiga é 1.0.1, não há patch em 0.x |
| `urllib3` | 1.26.20 | **2.7.0** | 5 advisories; o pin de 1.26 vinha de um marcador do `botocore` para py<3.10 |
| `python-multipart` | 0.0.20 | **0.0.32** | 6 advisories, corrigidos a partir de 0.0.31 |
| `python-dotenv` | 1.2.1 | **1.2.2** | 1 advisory |
| `pytest` (dev) | 8.4.2 | **9.1.1** | 1 advisory |
| `pytest-asyncio` (dev) | 1.2.0 | **1.4.0** | 1.2.0 declara `pytest<9`; arrastado, não escolhido |
| `pylint` (dev) | 3.3.9 | **4.0.7** | Última linha; 3.3 não é publicada para o conjunto novo |
| `astroid` (dev) | 3.3.11 | **4.0.4** | `pylint 4.0.7` exige `>=4.0.2,<=4.1.dev0` — **não** a 4.3.0 |
| `backports.asyncio.runner` | 1.2.0 | **removido** | Declara `Requires-Python <3.11`: recusa instalar em 3.13 |

---

## Task 1: Python 3.13 com as dependências atuais

O bissetor. Nada de dependência sobe aqui — se a suíte quebrar nesta task, a
causa é o interpretador, e só ele.

**Files:**
- Modify: `requirements.txt` (remover uma linha)
- Nenhum arquivo de código

**Interfaces:**
- Consumes: nada
- Produces: um `.venv` em Python 3.13 com shebangs corretos, do qual todas as
  tasks seguintes dependem. A partir daqui, `.venv/bin/pytest` funciona
  diretamente — as tasks seguintes usam essa forma e é assim que se confirma
  que a pendência do shebang morreu.

- [ ] **Step 1: Instalar o Python 3.13**

```bash
brew install python@3.13
/opt/homebrew/bin/python3.13 --version
```

Esperado: `Python 3.13.x`. A máquina hoje só tem o 3.9.6 do sistema; o
Homebrew já está instalado e nenhuma fórmula de Python existe nele.

- [ ] **Step 2: Guardar a lista antiga antes de destruir o venv**

```bash
cd /Users/gabriel/Desktop/Programing/Projects/ToBeBetter/Refund-api
.venv/bin/python3 -m pip freeze > /tmp/venv-39-freeze.txt
wc -l /tmp/venv-39-freeze.txt
```

O venv antigo vai ser apagado no passo seguinte. Esta lista é a única forma de
comparar depois o que entrou e o que saiu.

- [ ] **Step 3: Recriar o `.venv` em 3.13 e ver o install FALHAR**

```bash
rm -rf .venv
/opt/homebrew/bin/python3.13 -m venv .venv
.venv/bin/pip install -r requirements-dev.txt
```

Esperado: **FALHA**, com uma mensagem sobre `backports.asyncio.runner`. O
pacote declara `Requires-Python <3.11` e o pip se recusa a instalá-lo em 3.13.
Esta falha é o primeiro achado da task, não um acidente — se ela **não**
acontecer, pare e entenda por quê antes de seguir.

- [ ] **Step 4: Remover o backport que o 3.13 tornou impossível**

Em `requirements.txt`, apagar a linha:

```
backports.asyncio.runner==1.2.0
```

Vale registrar o que se aprende ao remover: esse pacote é um transitivo do
`pytest-asyncio` em Python antigo — **uma dependência de teste que estava no
`requirements.txt` de produção** e viajava para dentro da imagem Docker. Ele
sai por ser incompatível, mas não deveria estar ali de qualquer forma.

- [ ] **Step 5: Instalar de novo**

```bash
.venv/bin/pip install -r requirements-dev.txt
```

Esperado: sucesso. Se outro pacote reclamar de `Requires-Python`, ele é da
mesma família (backport de 3.9) e a mesma decisão vale — remover e anotar
qual foi.

- [ ] **Step 6: Confirmar que o shebang quebrado morreu**

```bash
head -1 .venv/bin/pytest
```

Esperado: um caminho que aponta para **este** diretório
(`.../Projects/ToBeBetter/Refund-api/.venv/bin/python`), não para
`.../React/Refund-api`. Esta é a pendência do shebang fechando como
subproduto.

- [ ] **Step 7: Rodar a suíte mockada com o Python novo e as dependências velhas**

```bash
.venv/bin/pytest -q 2>&1 | tail -5
```

Esperado: **334 passed, 72 deselected**. Qualquer falha aqui é atribuível ao
interpretador — nenhuma dependência mudou de versão. Anote a falha
literalmente antes de tentar corrigir.

- [ ] **Step 8: Rodar o pylint (ainda o 3.3.9) e conferir o CÓDIGO DE SAÍDA**

```bash
.venv/bin/pylint src; echo "exit=$?"
```

Esperado: `exit=0`. Se o pylint 3.3.9 não conseguir sequer analisar código sob
3.13, é sinal de que ele precisa subir junto — anote e siga; a Task 4 trata
disso.

- [ ] **Step 9: Commit**

```bash
git add requirements.txt
git commit -m "chore: run on Python 3.13 with the dependency set unchanged

Raising Python alone, before any dependency moves, so a failure has one
possible cause instead of two.

backports.asyncio.runner had to go: it declares Requires-Python <3.11 and
pip refuses it on 3.13. It was a pytest-asyncio transitive for old Pythons
that had settled into the production requirements, so it was also shipping
into the Docker image for no reason."
```

---

## Task 2: as dependências de runtime, incluindo o major do Starlette

**Files:**
- Modify: `requirements.txt`

**Interfaces:**
- Consumes: o `.venv` 3.13 da Task 1
- Produces: FastAPI 0.141.1 / Starlette 1.6.0 no ambiente, que é o que as
  Tasks 3 e 5 exercitam

- [ ] **Step 1: Editar `requirements.txt` com as cinco versões novas**

Trocar exatamente estas linhas (o resto do arquivo **não** muda):

```
fastapi==0.141.1
python-dotenv==1.2.2
python-multipart==0.0.32
starlette==1.6.0
urllib3==2.7.0
```

Preserve a ordenação existente do arquivo; só o número muda em cada linha.

- [ ] **Step 2: Instalar e deixar o resolvedor falar**

```bash
.venv/bin/pip install -r requirements-dev.txt 2>&1 | tail -20
```

Esperado: sucesso. Se o pip reclamar de conflito, **não afrouxe um pin para
calar o erro** — leia qual pacote impõe a restrição e registre. O caso
conhecido e já resolvido é o `botocore`, que só limita o `urllib3` em
Python < 3.10.

- [ ] **Step 3: Confirmar no ambiente que as versões são as esperadas**

```bash
.venv/bin/pip list | grep -iE "^(fastapi|starlette|urllib3|python-multipart|python-dotenv) "
```

Esperado: as cinco nas versões da tabela. Conferir o ambiente e não o arquivo
é o que pega um pin que o resolvedor silenciosamente sobrepôs.

- [ ] **Step 4: Suíte mockada**

```bash
.venv/bin/pytest -q 2>&1 | tail -5
```

Esperado: **334 passed, 72 deselected**.

Onde olhar se falhar, em ordem de probabilidade: o formato do
`RequestValidationError` (FastAPI 0.128 → 0.141) atinge
`src/main/server/server.py:93` e o envelope RFC 9457; a ordem de
`add_middleware` atinge `server.py:65-68`; o `contextvar` do `request_id`
atravessando `BaseHTTPMiddleware` atinge `src/main/middlewares/request_id.py`.

- [ ] **Step 5: Suíte de integração, que é onde o major encontra rede de verdade**

```bash
docker compose up -d
.venv/bin/pytest -m integration -q 2>&1 | tail -5
```

Esperado: **72 passed**. Os 14 testes HTTP de `src/test_integration/api_test.py`
são os que importam mais aqui: são os únicos que exercitam o **registro** dos
exception handlers, e portanto os únicos que percebem se o Starlette 1.x mudou
como eles são resolvidos.

- [ ] **Step 5b: Confirmar que os avisos do `boto3` sumiram**

```bash
.venv/bin/pytest -m integration 2>&1 | grep -c "PythonDeprecationWarning"
```

Esperado: **0**. Eram **9** avisos, e o `current-state.md` registra que não
foram silenciados de propósito — eram sinal real de que o projeto precisava
subir de Python. O sinal cumpriu sua função e agora deve desaparecer sozinho.
Se ainda aparecerem, o `boto3` está avisando de outra coisa e vale ler o texto
antes de assumir que é o mesmo.

- [ ] **Step 6: Conferir que o contrato versionado não mudou**

```bash
git diff --exit-code contract/
```

Esperado: sem diff, exit 0. A suíte de integração regenera esses arquivos; um
diff aqui significa que a **forma de uma resposta mudou** por causa da subida
— o que seria uma quebra de contrato com o frontend, não um detalhe. Se
aparecer diff, pare e leve o achado ao Gabriel antes de commitar.

- [ ] **Step 7: Commit**

```bash
git add requirements.txt
git commit -m "chore: take the runtime dependencies to their patched versions

Starlette's fixes exist only on the 1.x line — the oldest is 1.0.1 and there
is no 0.x patch — and FastAPI 0.128 declares starlette<1.0.0, so reaching
them means a major of the ASGI framework the whole app runs on.

urllib3 moves for free: botocore only asked for <1.27 while python_version
< 3.10, so the vulnerable pin was an environment marker rather than a choice."
```

---

## Task 3: as ferramentas de teste

Separada da Task 4 porque um plugin de teste que quebra e um linter que
reclama são diagnósticos diferentes, e um revisor pode aprovar um e rejeitar o
outro.

**Files:**
- Modify: `requirements-dev.txt`

**Interfaces:**
- Consumes: o ambiente da Task 2
- Produces: `pytest` 9 disponível para todas as tasks seguintes

- [ ] **Step 1: Editar `requirements-dev.txt`**

```
pytest==9.1.1
pytest-asyncio==1.4.0
```

O `pytest-asyncio` sobe **arrastado, não escolhido**: a versão 1.2.0 declara
`pytest<9,>=8.2` e bloqueia o pytest 9. `pytest-cov` e `pytest-mock` já
aceitam pytest 9 e **não** mudam.

- [ ] **Step 2: Instalar**

```bash
.venv/bin/pip install -r requirements-dev.txt 2>&1 | tail -10
.venv/bin/pip list | grep -iE "^(pytest|pytest-asyncio|pytest-cov|pytest-mock) "
```

- [ ] **Step 3: As duas suítes**

```bash
.venv/bin/pytest -q 2>&1 | tail -5
.venv/bin/pytest -m integration -q 2>&1 | tail -5
```

Esperado: **334 passed, 72 deselected** e **72 passed**.

Um major de pytest costuma mudar avisos e descoberta de testes, não
asserções. Se a **contagem** mudar (para mais ou para menos), isso é mais
grave que uma falha: significa que a coleta mudou e algum teste deixou de
rodar em silêncio. Compare o número, não só a cor.

- [ ] **Step 4: Commit**

```bash
git add requirements-dev.txt
git commit -m "chore: move the test tooling to pytest 9

pytest-asyncio comes along rather than by choice: 1.2.0 declares pytest<9.
The suite counts are asserted, not just the colour — a major of pytest can
change collection, and a test that silently stops running is worse than one
that fails."
```

---

## Task 4: `pylint` 4

Por último entre as dependências, de propósito: mensagens novas de um major de
linter são ruído que atrapalha diagnosticar falha de runtime. Primeiro o
código funciona; depois ele agrada o linter.

**Files:**
- Modify: `requirements-dev.txt`
- Modify: arquivos de `src/` **apenas** se o pylint 4 apontar algo real
- Modify: `.pylintrc` (na raiz do repositório, 22 KB — é onde a configuração
  vive; não existe `pyproject.toml` neste projeto) se uma regra precisar ser
  desabilitada com motivo

**Interfaces:**
- Consumes: o ambiente da Task 3
- Produces: `pylint src` saindo com **0** no conjunto novo

- [ ] **Step 1: Editar `requirements-dev.txt`**

```
astroid==4.0.4
pylint==4.0.7
```

**Atenção ao `astroid`:** o `pylint 4.0.7` declara `astroid>=4.0.2,<=4.1.dev0`.
A última versão publicada do astroid é a **4.3.0** e ela está **fora** dessa
faixa — pinar a mais nova quebra a instalação. A correta é a última 4.0.x,
que é a **4.0.4**.

- [ ] **Step 2: Instalar e rodar, esperando mensagens novas**

```bash
.venv/bin/pip install -r requirements-dev.txt 2>&1 | tail -5
.venv/bin/pylint src; echo "exit=$?"
```

Esperado nesta primeira execução: **exit diferente de 0**, com mensagens que a
linha 3.3 não emitia. Isso é o trabalho previsto da task, não uma surpresa.

- [ ] **Step 3: Triar cada mensagem nova, uma a uma**

Para cada mensagem, decidir entre duas saídas — e a escolha segue o precedente
que o `eslint.config.js` do frontend estabeleceu e que o `current-state.md`
registra:

1. **Corrigir o código**, quando a mensagem aponta algo real.
2. **Desabilitar com motivo escrito**, quando a regra não se aplica a este
   projeto. Regra **estrutural** desabilita no arquivo de configuração, com
   comentário dizendo por quê; regra de **correção** desabilita por linha ou
   por arquivo, pelo nome, para que um caso novo continue aparecendo.

**Não** desabilite uma categoria inteira para calar um caso. O `R0801`
(duplicação) já reprovou este projeto uma vez e a saída certa foi extrair
`format_refund_response`, não silenciar a regra.

- [ ] **Step 4: Conferir o código de saída, não a nota**

```bash
.venv/bin/pylint src; echo "exit=$?"
```

Esperado: `exit=0`. A nota `10.00/10` sozinha **não** é aprovação — este
projeto reportou aprovação errada por meses exatamente assim.

- [ ] **Step 5: Rodar as duas suítes de novo**

```bash
.venv/bin/pytest -q 2>&1 | tail -5
.venv/bin/pytest -m integration -q 2>&1 | tail -5
```

Esperado: **334 passed, 72 deselected** e **72 passed**. Correções feitas para
agradar o linter são código mudando — precisam passar pela suíte como
qualquer outra mudança.

- [ ] **Step 6: Commit**

```bash
git add requirements-dev.txt .pylintrc src; git add -u
git commit -m "chore: move to pylint 4 and close what it found

Left for last on purpose: new linter messages are noise while diagnosing a
runtime failure. Approval is the exit code, never the 10.00/10 line."
```

---

## Task 5: as duas quebras deliberadas

O coração da verificação. Tudo verde depois de um major prova que nada
explodiu; **não** prova que a rede continua armada. Estas duas quebras provam.

**Files:**
- Nenhum arquivo fica modificado ao fim da task. Cada quebra é aplicada,
  observada e **revertida**.

**Interfaces:**
- Consumes: o ambiente completo das Tasks 1–4
- Produces: evidência escrita, que entra na mensagem de commit da Task 8

- [ ] **Step 1: Quebra A — o handler na classe errada (o bug real do Item 23)**

Em `src/main/server/server.py`, o handler está registrado na `HTTPException`
do **Starlette**. Trocar temporariamente para a do FastAPI:

```python
# ANTES (linha ~80)
@app.exception_handler(StarletteHTTPException)
async def handle_http_exception(request: Request, exc: StarletteHTTPException):

# QUEBRA DELIBERADA — trocar para a do FastAPI
from fastapi import HTTPException as FastAPIHTTPException
@app.exception_handler(FastAPIHTTPException)
async def handle_http_exception(request: Request, exc: FastAPIHTTPException):
```

Este é o bug histórico: a do FastAPI é subclasse da do Starlette, então
registrar a subclasse deixa o **404 do router** escapar com o formato antigo.

- [ ] **Step 2: Provar que a suíte mockada NÃO pega, e a HTTP pega**

```bash
docker compose up -d
.venv/bin/pytest -q 2>&1 | tail -3
.venv/bin/pytest -m integration -q 2>&1 | tail -5
```

Esperado: a mockada **verde** (ela chama os handlers diretamente e não sabe do
registro) e a de integração **vermelha**, em
`test_an_unknown_route_is_also_a_problem_document`. É exatamente a assimetria
que o Item 25 existe para criar. Se a de integração passar, a rede **não**
sobreviveu ao major — pare e leve o achado ao Gabriel.

- [ ] **Step 3: Reverter a quebra A**

```bash
git checkout src/main/server/server.py
.venv/bin/pytest -m integration -q 2>&1 | tail -3
```

Esperado: 72 passed de novo.

- [ ] **Step 4: Quebra B — o `request_id` some do contextvar**

Em `src/main/middlewares/request_id.py`, comentar a linha 39:

```python
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id
        # _current_request_id.set(request_id)   # QUEBRA DELIBERADA
```

A propagação do contextvar através do `BaseHTTPMiddleware` foi **medida** no
Item 24, contra o Starlette 0.x. A classe mudou de major; a medição precisa
ser refeita e não herdada.

- [ ] **Step 5: Provar que a suíte pega**

```bash
.venv/bin/pytest src/configs/logging_config_test.py -q 2>&1 | tail -5
```

Esperado: **falha** em `test_the_filter_stamps_the_current_request_id`. Se
passar, o filtro deixou de ler o contextvar — o que significa que o log perdeu
a correlação com o `X-Request-Id` em silêncio, que é a promessa inteira do
Item 24.

- [ ] **Step 6: Medir a propagação de ponta a ponta, contra a API rodando**

O teste acima prova a peça. Esta medição prova a montagem — e "testei a peça,
não a montagem" é a falha que este projeto registra **quatro** vezes.

Reverter a quebra, subir a API e comparar o header com o log:

```bash
git checkout src/main/middlewares/request_id.py
.venv/bin/python3 -m uvicorn src.main.server.server:app --port 3333 &
sleep 3
curl -si http://127.0.0.1:3333/rota-que-nao-existe | grep -i "x-request-id"
# comparar com o request_id impresso na linha de log do terminal do servidor
kill %1
```

Esperado: o id do header e o id da linha de log são **iguais**. Este é o
critério que o Item 24 usou e o único que atravessa o `BaseHTTPMiddleware` de
verdade.

- [ ] **Step 7: Confirmar que a árvore voltou ao estado limpo**

```bash
git status --short
```

Esperado: **vazio**. Nenhuma quebra deliberada pode sobreviver à task.

- [ ] **Step 8: Sem commit**

Esta task não produz mudança versionada. As evidências entram na mensagem de
commit da Task 8. Registre agora, por escrito, os quatro resultados: mockada
verde com a quebra A, integração vermelha com a quebra A, teste do filtro
vermelho com a quebra B, e os dois ids iguais na medição.

---

## Task 6: CI e Dockerfile

**Files:**
- Modify: `.github/workflows/ci.yml:32` e `:104`
- Modify: `Dockerfile:11` e `:28`

**Interfaces:**
- Consumes: o `requirements.txt`/`requirements-dev.txt` das Tasks 1–4
- Produces: CI e imagem na mesma versão do ambiente local

- [ ] **Step 1: Subir a versão nos dois jobs do CI**

Em `.github/workflows/ci.yml`, linhas 32 e 104:

```yaml
          python-version: '3.13'
```

- [ ] **Step 2: Corrigir o comentário que ficou mentindo**

As linhas 24-26 do mesmo arquivo dizem:

```
      # Python is pinned to the version used locally. A CI on a different minor
      # would be verifying something nobody runs — and this project's local
      # interpreter is 3.9, older than the runner default.
```

A segunda metade deixou de ser verdade. Substituir por:

```
      # Python is pinned to the version used locally. A CI on a different minor
      # would be verifying something nobody runs. It was pinned to 3.9 for a
      # different reason — the local interpreter was older than the runner
      # default — and stayed pinned after 3.13 for the first one.
```

Um comentário que descreve um mundo que acabou é a mesma classe de problema
que este projeto registra oito vezes com os SHAs.

- [ ] **Step 3: Subir a versão nos dois estágios do Dockerfile**

Linhas 11 e 28:

```dockerfile
FROM python:3.13-slim AS builder
...
FROM python:3.13-slim
```

- [ ] **Step 4: Corrigir o comentário do topo do Dockerfile**

As linhas 1-6 hoje dizem:

```
# Packages the API so it runs the same way everywhere, instead of depending on
# somebody rebuilding the environment by hand. The README's seven local steps
# are one `docker run` here — and the class of failure that produced them is
# recorded in this project: a venv that was not activated, a venv with stale
# shebangs, and a CI that has to pin python-version because the local
# interpreter is older than the runner's default.
```

Os dois últimos exemplos deixaram de existir: o venv foi recriado e o
interpretador local não é mais o mais velho. Substituir por:

```
# Packages the API so it runs the same way everywhere, instead of depending on
# somebody rebuilding the environment by hand. The README's seven local steps
# are one `docker run` here — and the class of failure that produced them is
# recorded in this project: a venv that was not activated, and a venv carrying
# shebangs from a path the project had moved away from. Both were environment
# drift that an image cannot have.
```

- [ ] **Step 5: Construir a imagem**

```bash
docker build -t refund-api:py313 .
docker image inspect refund-api:py313 --format '{{.Size}}' | awk '{print $1/1024/1024 " MB"}'
```

O Item 30 registrou **366 MB** com o Python 3.9. Anote o número novo — não é
critério de aprovação, é medição para o registro.

- [ ] **Step 6: Repetir a verificação do Item 30 com o container de pé**

```bash
docker compose up -d
docker run -d --name refund-py313 -p 3334:3333 \
  -e DATABASE_URL="$(grep '^DATABASE_URL=' .env | cut -d= -f2-)" \
  -e JWT_SECRET=verification-only \
  refund-api:py313
sleep 5
curl -s -o /dev/null -w "health=%{http_code}\n" http://127.0.0.1:3334/health
curl -s -o /dev/null -w "ready=%{http_code}\n" http://127.0.0.1:3334/ready
docker inspect --format '{{.State.Health.Status}}' refund-py313
```

Esperado: `health=200`, `ready=200`, healthcheck `healthy`.

- [ ] **Step 7: Provar que `/ready` ainda distingue banco morto de app morto**

```bash
docker compose stop postgres   # ou parar o banco que o container está usando
sleep 3
curl -s -o /dev/null -w "ready_sem_banco=%{http_code}\n" http://127.0.0.1:3334/ready
docker ps --filter name=refund-py313 --format '{{.Status}}'
docker compose start postgres
sleep 5
curl -s -o /dev/null -w "ready_de_volta=%{http_code}\n" http://127.0.0.1:3334/ready
docker rm -f refund-py313
```

Esperado: `ready_sem_banco=503`, o container **continua vivo** (o healthcheck
aponta para `/health` justamente para não reiniciar em laço), e
`ready_de_volta=200`. É a verificação exata do Item 30, repetida no Python
novo.

- [ ] **Step 8: Confirmar que a imagem não carrega ferramenta de teste nem `.env`**

```bash
docker run --rm refund-api:py313 python -c "import pytest" 2>&1 | tail -1
docker run --rm refund-api:py313 sh -c "ls -la /app/.env" 2>&1 | tail -1
```

Esperado: `ModuleNotFoundError: No module named 'pytest'` e um erro de arquivo
inexistente. As duas garantias do Item 30 precisam sobreviver.

- [ ] **Step 9: Commit**

```bash
git add .github/workflows/ci.yml Dockerfile
git commit -m "chore: build and verify on Python 3.13 in CI and in the image

Also rewrites two comments that the upgrade made false — one in ci.yml and
one at the top of the Dockerfile, both citing the old interpreter being
older than the runner default as a live problem."
```

- [ ] **Step 10: Empurrar e LER A SAÍDA do CI, não o status**

```bash
git push -u origin chore/python-313-upgrade
gh run watch
gh run view --log | grep -E "collected .* items|selected"
```

Esperado: os **dois** jobs verdes, e as duas linhas de `collected N items / M
selected` provando que cada job rodou a metade que devia. Um job pode passar
tendo rodado zero teste se a filtragem por marker quebrar — o status verde
sozinho não distingue os dois casos.

---

## Task 7: Dependabot nos dois repositórios

**Files:**
- Nenhum arquivo. É configuração de painel e consulta de API.

**Interfaces:**
- Consumes: o push da Task 6, que é o que faz o Dependabot reavaliar
- Produces: os dois números que a Task 8 registra

- [ ] **Step 1: Conferir que os 37 alertas do backend zeraram**

```bash
cd /Users/gabriel/Desktop/Programing/Projects/ToBeBetter/Refund-api
gh api "repos/:owner/:repo/dependabot/alerts?state=open&per_page=100" \
  --jq 'group_by(.security_advisory.severity)|map({sev:.[0].security_advisory.severity,n:length})'
```

Esperado: `[]`.

O Dependabot reavalia após o push, não instantaneamente — se ainda houver
alertas, confira se sobraram nos **dois** manifests ou só num deles, e se o
pacote apontado é um dos cinco. Um alerta remanescente sobre pacote **novo** é
achado legítimo e vai para as pendências; não é motivo para reabrir o ciclo.

- [ ] **Step 2: Ligar o Dependabot no `Refund-FrontEnd`**

Hoje ele está **desabilitado** — a API responde `403: Dependabot alerts are
disabled for this repository`. Ligar em Settings → Advanced Security →
Dependabot alerts, no repositório do frontend.

- [ ] **Step 3: Esperar a primeira varredura e anotar o número**

```bash
cd ../Refund-FrontEnd
gh api "repos/:owner/:repo/dependabot/alerts?state=open&per_page=100" \
  --jq 'group_by(.security_advisory.severity)|map({sev:.[0].security_advisory.severity,n:length})'
gh api "repos/:owner/:repo/dependabot/alerts?state=open&per_page=100" \
  --jq '[.[].dependency.package.name]|group_by(.)|map({pkg:.[0],n:length})|sort_by(-.n)'
```

**Não corrigir nada.** O escopo aqui é transformar um ponto cego em número.
Os dois resultados vão para as pendências na Task 8.

---

## Task 8: fechamento e documentação

**Files:**
- Modify: `docs/plans/current-state.md`
- Modify: `docs/learning-path-progress.md`
- Modify: `README.md` (se citar a versão de Python)

**Interfaces:**
- Consumes: as evidências das Tasks 1–7
- Produces: o documento que a próxima sessão vai ler

- [ ] **Step 1: Repetir as verificações inteiras, três rodadas, salvando em arquivo**

```bash
cd ../Refund-api
for i in 1 2 3; do .venv/bin/pytest -q > /tmp/pytest-run-$i.txt 2>&1; tail -1 /tmp/pytest-run-$i.txt; done
.venv/bin/pytest -m integration -q > /tmp/integration.txt 2>&1; tail -1 /tmp/integration.txt
.venv/bin/pylint src > /tmp/pylint.txt 2>&1; echo "pylint exit=$?"
```

**Salvar em arquivo antes de olhar**, não depois. Este projeto perdeu a saída
de um flake duas vezes na mesma sessão por olhar primeiro, e registrou a regra
justamente por isso.

- [ ] **Step 2: Conferir se a versão de Python aparece no `README.md`**

```bash
grep -n "3\.9\|python3" README.md
```

Se as instruções locais citarem 3.9, atualizar para 3.13.

- [ ] **Step 3: Atualizar o `current-state.md` — o ciclo**

Acrescentar o relato do ciclo, na forma que os anteriores usam: o que mudou,
os números antes e depois, e as evidências das quebras deliberadas da Task 5.
Registrar explicitamente:

- que as pendências 1 e 2 da ordem de varredura eram **uma só**, com a
  evidência do marcador do `botocore`;
- o tamanho da imagem antes e depois;
- o `backports.asyncio.runner` que estava no `requirements.txt` de produção
  sendo transitivo de teste;
- o número da primeira varredura do Dependabot no frontend.

- [ ] **Step 4: Atualizar o `current-state.md` — aplicar a triagem**

Matar as quatro pendências que a triagem encontrou mortas, cada uma com a
razão:

1. A diretiva de lint em `src/hooks/useObjectUrl.ts` — o **Item 22 apagou o
   arquivo**.
2. O nome acessível do botão de tela cheia — já resolvido, com
   `receipt.viewFullscreen` e `receipt.viewPaymentFullscreen` distintos e um
   comentário no `ReceiptPreview.tsx` citando a armadilha.
3. "As branches do Item 31 não foram mescladas" — foram, em `212c9c8` e
   `b26385e`. Registrar como a **oitava** ocorrência do padrão, no mesmo bloco
   que já conta as sete anteriores.
4. "A cópia do contrato divergiu" — os quatro arquivos estão byte a byte
   iguais. O mecanismo manual **continua** registrado como pendência
   estrutural; só a divergência ativa é que não existe.

- [ ] **Step 5: Acrescentar ao diário**

Em `docs/learning-path-progress.md`, o que se aprendeu e não cabe no retrato:
a cascata forçada `Python → FastAPI → Starlette`, o marcador de ambiente do
`botocore` prendendo o `urllib3`, a armadilha do `astroid` 4.3.0 estar **fora**
da faixa que o `pylint 4.0.7` aceita, e o que as quebras deliberadas mostraram
sobre o `BaseHTTPMiddleware` ter sobrevivido ao major.

- [ ] **Step 6: Commit**

```bash
git add docs README.md
git commit -m "docs: record the Python 3.13 cycle and apply the pendency triage

Merges pending items 1 and 2 into one, with the evidence: every patched
version requires >= 3.10, and botocore pinned urllib3 to the vulnerable line
through an environment marker rather than a choice.

Also kills four pendencies the triage found dead — including a claim that the
Item 31 branches were unmerged, which is the eighth time this document has
gone stale in exactly that way."
```

- [ ] **Step 7: Entregar, sem mesclar**

```bash
git push
git log --oneline befd1f4..HEAD
```

O merge é **decisão do Gabriel**, como nos ciclos anteriores. Apresente: os
números finais das três rodadas, o resultado das duas quebras deliberadas, o
tamanho da imagem, os dois números do Dependabot, e o que ficou registrado
como pendência nova.

---

## Verificação final — o critério de pronto da spec

- [ ] `gh api dependabot/alerts?state=open` no `Refund-api` devolvendo **0**
- [ ] Dependabot ligado no `Refund-FrontEnd`, número anotado nas pendências
- [ ] `pytest` **334**, três rodadas, saída salva em arquivo antes de lida
- [ ] `pytest -m integration` **72**
- [ ] `pylint src` com **exit 0** (o código, não a nota)
- [ ] CI verde nos **dois** jobs, lido na saída (`collected N / M selected`)
- [ ] Container construído, `/ready` **503** com o banco parado e **200** de
      volta, container vivo o tempo todo
- [ ] `import pytest` falhando dentro da imagem, `.env` ausente
- [ ] As **duas quebras deliberadas** observadas e revertidas, com `git status`
      vazio
- [ ] `current-state.md` com o ciclo relatado e a triagem aplicada
- [ ] **Validação em navegador: não se aplica** — nenhuma tela é tocada
