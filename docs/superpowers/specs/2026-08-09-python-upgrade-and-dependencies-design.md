# Ciclo de varredura — Python 3.13 e dependências (backend)

Data: 2026-08-09.
Repositório afetado: `Refund-api`.
O `Refund-FrontEnd` recebe **uma** ação de configuração (ligar o Dependabot) e
nenhuma mudança de código.

Primeiro ciclo depois do fim do `learning_path.md`. Não é item da trilha: é a
varredura de pendências combinada em 2026-08-08, e este é o seu primeiro
recorte.

## Motivação

A seção de pendências do [estado atual](../../plans/current-state.md) sugere
uma ordem de varredura que abre com dois itens **separados**:

1. Python 3.9 sem correções de segurança, com a imagem de produção construída
   sobre ele.
2. 37 vulnerabilidades do Dependabot (18 high, 11 moderate, 8 low), nunca
   investigadas, e crescendo sem que nenhuma dependência tenha sido adicionada.

A triagem que precedeu esta spec mostrou que **não são dois itens**. São o
mesmo, e o segundo é sintoma do primeiro.

### A evidência, medida e não suposta

As 37 vulnerabilidades se decompõem em **cinco pacotes** —
`urllib3`, `starlette`, `python-multipart`, `python-dotenv` e `pytest` —
contados em dobro porque o `requirements-dev.txt` faz `-r requirements.txt` e o
Dependabot varre os dois manifests como se fossem árvores independentes. O
número assusta mais do que a lista.

**Toda versão corrigida dos cinco exige Python >= 3.10**, verificado com o
resolvedor do pip contra o `.venv` real, não lido de changelog:

| Pacote | Instalado | Corrigido em | Requires-Python da correção |
|---|---|---|---|
| `starlette` | 0.49.3 | 1.3.1 | >= 3.10 |
| `urllib3` | 1.26.20 | 2.7.0 | >= 3.10 |
| `python-multipart` | 0.0.20 | 0.0.31 | >= 3.10 |
| `python-dotenv` | 1.2.1 | 1.2.2 | >= 3.10 |
| `pytest` (dev) | 8.4.2 | 9.0.3 | >= 3.10 |

Ou seja: **nenhuma das 37 é corrigível enquanto o projeto estiver em 3.9.**
Isso também explica o crescimento sem dependência nova, que o documento
registrou como estranho: são advisories novos sobre versões congeladas por
incompatibilidade, não regressões.

O `urllib3` fecha o argumento de forma ainda mais direta. O `botocore 1.42.97`
declara:

```
urllib3<1.27,>=1.25.4;  python_version <  "3.10"
urllib3!=2.2.0,<3,>=1.25.4;  python_version >= "3.10"
```

Os 10 alertas do `urllib3` não vêm de uma escolha nem de um esquecimento: o
Python 3.9 prende a versão na linha 1.26 **através de um marcador de
ambiente**. Subir o Python solta o pin sozinho, sem ninguém editar uma linha.

### Um achado que não estava registrado

O Dependabot está **desabilitado** no `Refund-FrontEnd`. O número "37
vulnerabilidades" é do backend porque ninguém está olhando o outro repositório
— não porque o outro esteja limpo. Isso é ponto cego, não ausência de risco.

## O princípio que organiza o ciclo

**Um repositório, um assunto.** A decisão de 2026-08-08 diz que uma pendência
encontrada no meio de um trabalho é para ser **registrada**, não corrigida na
hora. Este ciclo é uma varredura, então a tentação se inverte: com o ambiente
aberto e a suíte rodando, tudo parece barato de enxertar. A fronteira abaixo
existe para resistir a isso.

Fica **de fora**, deliberadamente:

- **O import do `boto3` no topo do `src/drivers/storage_factory.py`.** É a
  tentação mais forte — mesma área, correção de duas linhas — e é exatamente o
  que o documento registra ter sido escrito, verificado e **revertido** em
  2026-08-08 por ter sido feito sob a hipótese errada de ser a causa de outro
  problema. Entra numa varredura própria, com o teste de subprocesso que a
  armadilha documentada exige.
- Branch protection (decisão consciente já registrada), os 3 arquivos órfãos,
  os usuários de teste no banco, e todas as pendências de frontend.

## Escopo

### 1. Python 3.9.6 → 3.13

Nas quatro superfícies em que a versão está escrita, que hoje concordam entre
si e precisam continuar concordando:

- `.github/workflows/ci.yml`, nos **dois** jobs (`verify` e `integration`).
- `Dockerfile`, nos **dois** estágios (`builder` e final).
- O `.venv` local, recriado com `python3.13` (Homebrew — a máquina só tem o
  3.9.6 do sistema).

A 3.13 foi escolhida sobre a 3.12 e a 3.14 por horizonte, não por
compatibilidade: **todas** as dependências nativas do projeto (`asyncpg`,
`pydantic_core`, `greenlet`, `bcrypt`, `MarkupSafe`, `SQLAlchemy`) publicam
wheel até `cp314`, e `pylint`/`pytest` recentes suportam até 3.14. Nenhuma das
três teria falhado por falta de wheel; a 3.13 tem quase dois anos de rodagem e
suporte de segurança até out/2029.

### 2. As dependências, até zerar os alertas

A cadeia é forçada e vale escrevê-la, porque não existe "subir só o pacote
vulnerável":

```
Python 3.13  →  FastAPI 0.128.8 → 0.141.x  →  Starlette 0.49.3 → 1.3.x
                (0.141 exige >= 3.10)          (0.128 declara starlette<1.0.0)
```

As correções do Starlette existem **apenas** na linha 1.x — a mais antiga é
`1.0.1`, e não há patch em 0.x. Chegar nelas obriga a subir o FastAPI, cujo
`starlette<1.0.0` é o que hoje trava a linha. O mínimo para zerar os
advisories do Starlette é, portanto, **um major do framework ASGI sobre o qual
a aplicação inteira roda**.

Também sobem: `urllib3` para 2.x, `python-multipart` 0.0.31, `python-dotenv`
1.2.2, `pytest` 9.x e `pylint` 4.x. O resto do `requirements.txt` **não** é
atualizado por atualizar: um refresh completo misturaria muitas causas
possíveis numa única falha.

As linhas acima nomeiam o alvo; o plano fixa a **versão exata** de cada uma,
preservando o estilo `==` que os dois arquivos de requirements já usam. Nada
entra sem número.

### 3. `Refund-FrontEnd`: ligar o Dependabot e anotar

Ligar, esperar a primeira varredura, **registrar o resultado nas pendências**.
Nenhuma correção de dependência JS neste ciclo — o volume é desconhecido, e
amarrar o término deste ciclo a ele seria trocar um assunto por dois.

## Ordem de execução, e por que ela é essa

1. Instalar o 3.13 e **recriar o `.venv`**.
2. Subir as dependências e rodar a **suíte mockada** (334 testes, ~4,6s). É o
   portão mais barato e o primeiro sinal.
3. **Suíte de integração** (72 testes, Postgres + MinIO em Docker). É onde o
   major do Starlette encontra rede, disco e banco de verdade.
4. **`pylint` 4** — por último de propósito. Mensagens novas de um major de
   linter são ruído que atrapalha diagnosticar falha de runtime. Primeiro o
   código funciona; depois ele agrada o linter.
5. **CI e `Dockerfile`**, só depois de a versão nova ter passado localmente.
6. **Construir e rodar o container**, repetindo a verificação do Item 30.

O passo 4 inverte a ordem que pareceria natural e é deliberado.

## Análise de risco

### Verificado antes de escrever esta spec, e seguro

| Risco temido | O que a verificação mostrou |
|---|---|
| `BaseHTTPMiddleware` removido no major | Continua em `starlette/middleware/base.py` da 1.3.1 |
| `@app.exception_handler` removido | Removido do **Starlette**; o FastAPI 0.141 define o próprio, e é dele que o `server.py` depende |
| `starlette.exceptions.HTTPException` sumir | Continua existindo — a correção do Item 23 segue válida |
| `on_startup`/`on_shutdown` removidos | O projeto usa `lifespan` desde o Item 18 |
| `urllib3` 2.x conflitar com `botocore` | Só conflita em Python < 3.10; some junto com a subida |

O Starlette 1.0 também removeu os decoradores `@app.route`, `@app.websocket_route`
e `@app.middleware`, e mudou a assinatura do `Jinja2Templates`. Nenhum deles é
usado aqui: as rotas vivem em `APIRouter`, os middlewares entram por
`add_middleware`, e o projeto não renderiza template.

### Risco real, e é onde a verificação precisa apertar

1. **O `contextvar` do `request_id` atravessando o `BaseHTTPMiddleware`.** O
   Item 24 registra explicitamente que essa propagação foi **medida, não
   suposta**. A classe mudou de major, então a medição vale para a versão
   antiga e precisa ser **refeita**, não herdada.
2. **A ordem reversa de `add_middleware`.** Há um comentário no `server.py`
   afirmando essa semântica, e quatro middlewares dependendo dela. Se mudar, o
   `X-Request-Id` some do header no 500 — o bug exato que o Item 23 já pagou
   uma vez.
3. **O formato do `RequestValidationError`** entre FastAPI 0.128 e 0.141. O
   envelope RFC 9457 depende dele.
4. **`pylint` 3.3 → 4.0.** Major de linter num projeto que exige exit 0. É
   trabalho previsível, não risco: mensagens novas se corrigem ou se
   desabilitam com motivo escrito, no precedente que o `eslint.config.js` do
   frontend já estabeleceu (regra estrutural desliga por diretório; regra de
   correção desliga por arquivo, pelo nome).

## Verificação

Nenhum número novo — os que o projeto já tem, e a baseline medida **antes** de
abrir a branch, como a lição de 2026-07-29 exige:

**Baseline em `befd1f4` / `b26385e` (2026-08-09):** `pytest` **334 passed, 72
deselected**; `pylint src` **exit 0**; frontend **305 testes em 54 arquivos**,
`tsc` exit 0.

Ao fim:

- `pytest` 334 · `pytest -m integration` 72 · `pylint src` **exit 0**, conferido
  pelo código de saída e não pela nota.
- Os **14 testes por HTTP** do Item 25 são os únicos que exercitam o *registro*
  dos handlers, e a única rede que pegaria os riscos 2 e 3 acima.
- Container construído e rodando: `/ready` em **503 com o banco parado**,
  recuperando sozinho, container vivo o tempo todo.
- **Duas quebras deliberadas**, no padrão adotado desde o Item 19:
  - reintroduzir o bug do Item 23 (registrar o handler na `HTTPException` do
    FastAPI em vez da do Starlette) e conferir que os testes HTTP **falham**;
  - derrubar o `request_id` do contextvar e conferir que o log **perde o id**.

  As duas provam que a rede sobreviveu ao major — não apenas que a suíte está
  verde, que é coisa diferente.
- CI visto rodando **os dois jobs** na versão nova, lido na **saída**
  (`collected N items / N selected`), não no status verde. Um job pode passar
  tendo rodado zero teste se a filtragem por marker quebrar.

**Validação em navegador: não se aplica.** O ciclo não toca nenhuma tela.

## Critério de pronto

1. `gh api "repos/:owner/:repo/dependabot/alerts?state=open"` no `Refund-api`
   devolvendo **0** — conferido pela API, não pela tela.
2. Dependabot ligado no `Refund-FrontEnd`, com o número da primeira varredura
   registrado nas pendências.
3. Todas as verificações acima.
4. `current-state.md` com a triagem aplicada (ver abaixo).
5. Branch entregue verificada; **o merge é decisão do Gabriel**, como nos
   ciclos anteriores.

## O fechamento aplica a triagem ao `current-state.md`

A triagem que produziu esta spec conferiu ~25 pendências contra o código atual.
Quatro estão **mortas** e precisam sair, ou a próxima sessão refaz o mesmo
trabalho — que é o padrão que o documento já registra sete vezes:

- A diretiva de lint em `src/hooks/useObjectUrl.ts`: o **Item 22 apagou o
  arquivo**.
- O nome acessível do botão de tela cheia "sem contexto": já resolvido, com
  `receipt.viewFullscreen` e `receipt.viewPaymentFullscreen` distintos e um
  comentário no `ReceiptPreview.tsx` citando essa exata armadilha.
- "As branches do Item 31 não foram mescladas": foram — `212c9c8` no
  `Refund-api` e `b26385e` no `Refund-FrontEnd`. **Oitava ocorrência** do
  padrão que o bloco de estado dos repositórios existe para tornar detectável.
- "A cópia do contrato entre os repos divergiu": os quatro arquivos estão
  **byte a byte iguais** hoje. O mecanismo manual segue frágil e continua
  registrado como pendência estrutural, mas não há divergência ativa.

Além disso, o fechamento funde as pendências 1 e 2 numa só, com a evidência do
marcador do `botocore`, e registra o Dependabot desabilitado no frontend.

## Subprodutos

Fecham sem trabalho extra, por serem consequência da subida:

- O `.venv` com shebangs de `.../React/Refund-api`, que hoje obriga a rodar
  tudo como `.venv/bin/python3 -m pytest`.
- Os 9 `PythonDeprecationWarning` do `boto3` que poluem a suíte de integração.
- A dívida registrada de "imagem de produção construída sobre Python sem
  correções de segurança".
