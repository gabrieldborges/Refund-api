# Ciclo de deploy — Primeira implantação (Railway + S3)

Data: 2026-08-10.
Repositórios afetados: **os dois**, `Refund-api` e `Refund-FrontEnd`.

Este é o **primeiro deploy do projeto**. Não existe produção hoje — a
verificação de 2026-08-03 estabeleceu isso, e nada mudou desde então.
"Publicado" sempre significou publicado no GitHub.

## Motivação

O [estado atual](../../plans/current-state.md) fecha a trilha com uma frase que
sobreviveu a todas as fases: *"o que a trilha NÃO entregou, e continua
verdadeiro: não existe deploy. Os cinco bloqueios foram endereçados, mas
escolher e configurar um provedor não é código e nunca foi feito."*

Os cinco bloqueios caíram como subproduto da própria trilha — CORS
configurável e configuração tipada no Item 17, object storage no Item 22, CI no
Item 29, container no Item 30. Sobrou exatamente o que não é código. Este ciclo
é isso.

## Decisões tomadas

Todas do Gabriel, em 2026-08-10, e registradas aqui porque cada uma fecha
alternativas que este documento já discutiu:

| Decisão | Escolha | O que ela descarta |
|---|---|---|
| Natureza | **Portfólio / demonstração** | Sem usuários reais, sem backup, cold start tolerável |
| Plataforma | **Railway** | Render, Cloud Run, Fly.io |
| Arquivos | **AWS S3** (plano gratuito, 6 meses) | Volume da Railway, Cloudflare R2 |
| Banco | **PostgreSQL da Railway** | Neon novo, Neon atual |
| Frontend | **Também na Railway** | Cloudflare Pages, Vercel |

Duas consequências que valem estar escritas, porque contrariam decisões
anteriores do projeto:

- **O banco deixa de ser o Neon.** A [ADR-002](../../decisions/ADR-002-postgresql-neon.md)
  escolheu o Neon deliberadamente, e a suíte de integração fixa PostgreSQL 18
  para espelhar o que ele reporta (18.4). A produção passa a rodar no PostgreSQL
  da Railway, cuja versão maior **precisa ser conferida no primeiro deploy** — se
  divergir, a suíte de integração deixa de espelhar produção, que era a razão de
  ela existir. A ADR-002 será amendada com o resultado, não antes.
- **O Neon atual não vira produção.** Ele carrega oito usuários de teste e os
  reembolsos 65–73, um deles com o comprovante apagado do disco de propósito.
  Continua sendo o banco de desenvolvimento, que é o papel que ele de fato tem.

## O impasse circular das URLs

Um redeploy não tem este problema; o **primeiro** tem, e ele produz um sintoma
que já enganou este projeto uma vez.

- `VITE_API_URL` é resolvido em **tempo de build** (`src/lib/api.ts` lê
  `import.meta.env.VITE_API_URL`), então a URL do backend precisa existir antes
  de o frontend ser construído.
- `CORS_ORIGINS` precisa conter a origem do frontend antes de o backend aceitar
  qualquer requisição dela.

Nenhuma das duas existe ainda. Seguir a ordem intuitiva — subir o backend,
depois o frontend — faz o backend subir com um `CORS_ORIGINS` que ninguém
sabia, e o erro resultante **não se parece com um erro de CORS**: o
`CORSMiddleware` do Starlette roda antes dos nossos exception handlers e
responde `400 Disallowed CORS origin` em texto puro, fora do envelope RFC 9457.
Em 2026-08-09 esse mesmo sintoma foi relatado como "não consigo logar nem criar
conta", quando na verdade a requisição real nunca havia sido tentada.

**A saída é separar "ter domínio" de "estar funcionando".** A Railway atribui o
domínio quando o serviço é criado, não quando ele sobe com sucesso. Os três
serviços são criados e os dois domínios gerados **antes** de qualquer variável
ser preenchida; os deploys falham nessa janela, e isso é esperado.

## Escopo — parte de código

Três mudanças, todas pequenas. Duas no `Refund-api`, no espírito de itens que
já existem, e uma no `Refund-FrontEnd` (descrita adiante, junto da configuração
do frontend, porque só faz sentido ao lado do fallback de SPA que ela resolve).

### 1. A `Settings` recusa um driver síncrono

**O problema, reproduzido:** a Railway injeta `DATABASE_URL` no formato padrão
`postgresql://`. O SQLAlchemy lê isso como driver **síncrono**, tenta importar
`psycopg2` — que este projeto não instala — e levanta
`ModuleNotFoundError: No module named 'psycopg2'`.

O que torna isso pior do que um erro comum é **quando** ele acontece. O
`field_validator` do Item 17 chama `make_url`, que só faz parse, e
`postgresql://` é uma URL perfeitamente bem-formada. O engine é preguiçoso
(também Item 17). Então a aplicação **sobe saudável**, o `/health` responde
`200`, e a falha aparece no primeiro acesso ao banco.

Isso é exatamente o modo de falha que o Item 17 existe para eliminar,
reentrando pela porta dos fundos — o mesmo padrão que aquele item já registrou
uma vez, quando o engine preguiçoso removeu a única coisa que parseava a URL.

**A correção:** estender o validador existente para exigir um dialeto
assíncrono, que é o requisito real de `create_async_engine`.

O mecanismo foi **medido, não suposto**:

| URL | dialeto resolvido | `is_async` |
|---|---|---|
| `postgresql+asyncpg://…` | `PGDialect_asyncpg` | `True` |
| `postgresql://…` | `PGDialect_psycopg2` | `False` |
| `postgresql+psycopg2://…` | `PGDialect_psycopg2` | `False` |

`get_dialect()` resolveu `PGDialect_psycopg2` **sem o `psycopg2` estar
instalado** — a checagem é de metadado, não constrói pool e não toca a rede, o
que a mantém na fronteira de configuração onde todo o resto já é validado. É a
mesma justificativa que o docstring atual do validador dá para o `make_url`.

A mensagem de erro precisa dizer o que fazer, não apenas o que está errado:
quem cola uma URL do painel da Railway não sabe que o prefixo importa.

### 2. O `CMD` respeita `$PORT`

A Railway injeta `$PORT` e espera que o processo escute nela; o `Dockerfile`
fixa `--port 3333` na forma exec, que não expande variável.

**A correção:** `${PORT:-3333}`, preservando 3333 como default. Isso resolve na
Railway **e** mantém a imagem portátil — uma imagem que só sobe na Railway seria
a mesma objeção que a [ADR-011](../../decisions/ADR-011-container.md) levantou
para não conteinerizar o frontend.

O `HEALTHCHECK` e o `EXPOSE` referenciam 3333 literalmente e precisam
acompanhar, ou o healthcheck passa a apontar para uma porta onde não há
ninguém. A Railway não usa o `HEALTHCHECK` do Docker, mas o `docker run` local
usa — e foi assim que o Item 30 verificou o container.

## Escopo — parte de configuração

### Backend

| Variável | Valor | Por quê |
|---|---|---|
| `ENVIRONMENT` | `production` | Ativa a guarda que recusa CORS com `*` ou localhost |
| `LOG_LEVEL` | `INFO` | Onde vive a linha de acesso por requisição |
| `DATABASE_URL` | `postgresql+asyncpg://${{Postgres.PGUSER}}:${{Postgres.PGPASSWORD}}@${{Postgres.PGHOST}}:${{Postgres.PGPORT}}/${{Postgres.PGDATABASE}}` | Composta à mão; o valor pronto da Railway tem o driver errado |
| `JWT_SECRET` | **gerado novo** | Nunca o do `.env` local |
| `CORS_ORIGINS` | a URL do frontend | Esquema + host, **sem barra no final** |
| `STORAGE_BACKEND` | `s3` | Disco da instância é efêmero |
| `S3_BUCKET` / `S3_REGION` | do bucket criado | |
| `S3_ACCESS_KEY_ID` / `S3_SECRET_ACCESS_KEY` | do usuário IAM | |
| `S3_ENDPOINT_URL` | **não definir** | Vazio significa AWS real; preenchido significa MinIO |

Nenhuma delas entra em arquivo versionado. O `.env` é ignorado pelo Git e serve
só para desenvolvimento local.

### AWS

- **Bucket privado**, com Block Public Access ligado. O controle de acesso é a
  URL assinada; um bucket público desfaria o Item 22 inteiro.
- **Usuário IAM restrito a esse bucket**, com `GetObject`, `PutObject`,
  `DeleteObject` e `ListBucket`. O `ListBucket` não é opcional — é o que
  `list_files()` usa na varredura de órfãos do Item 28.

### Frontend

- `VITE_API_URL` com a URL do backend, disponível **no build**.
- **Fallback de SPA**: rotas desconhecidas precisam servir `index.html`. Sem
  isso, `/refunds/79/review` funciona ao navegar e devolve 404 ao **recarregar**
  — o React Router usa rotas reais desde o Item 3, e o sintoma só aparece no F5
  ou num link direto, que é justamente o que alguém faz ao receber a URL.

  Isto **não é só configuração de painel**: um `vite build` produz arquivos
  estáticos e nada que os sirva. A escolha adotada é a mais explícita e a única
  que fica versionada — acrescentar `serve` como devDependency e um script
  `start` com `serve -s dist -l $PORT`, onde a flag `-s` **é** o fallback de
  SPA. Uma dependência nova, justificada: a alternativa seria um `Dockerfile`
  com nginx no frontend, o que traz um arquivo de configuração de servidor para
  um projeto que não tem nenhum, para resolver o mesmo problema.

  Versionar isso importa por um motivo que este projeto já pagou: um fallback
  configurado só no painel é invisível no repositório e não sobrevive a
  recriar o serviço.

### Etapas que não são variável de ambiente

- **Migrations**: `alembic upgrade head` como comando de pré-deploy. É
  idempotente, então rodar a cada deploy é correto. O `alembic.ini` e o
  diretório `alembic/` já estão dentro da imagem, e o `alembic` está no
  `requirements.txt` de produção — verificado.
- **Primeiro admin**: não existe. O cadastro público só cria `standard`
  (BR-registrada no `UC-001`); alguém se cadastra pela tela e é promovido com
  `init/promote_admin.py`, que também já está na imagem.

## Verificação

O critério é evidência, não impressão. Em ordem, porque cada uma só faz sentido
se a anterior passou:

1. **`/health` responde 200 e `/ready` responde 200.** O `/ready` é o que
   importa: ele é o único que prova a conexão com o banco, e é exatamente o que
   a armadilha do driver quebraria. `/health` verde com `/ready` vermelho é o
   sintoma dessa armadilha.
2. **Cadastro → login → criar reembolso com comprovante.**
3. **A `<img>` do comprovante carrega da URL assinada do S3 sem cabeçalho
   `Authorization`.** É o ponto inteiro do Item 22, e ele **nunca foi exercido
   contra a AWS de verdade** — a suíte roda contra MinIO, e a validação de
   2026-08-09 rodou contra o backend `local`.
4. **O objeto existe no bucket**, conferido no console da AWS. Prova que o
   arquivo foi para o S3 e não para o disco da instância.
5. **F5 numa rota profunda** (`/refunds/{id}`), provando o fallback de SPA.
6. **Uma ação que falha** devolve `problem+json` com um `request_id` que
   **aparece no log da Railway**. Fecha os Itens 23 e 24 num ambiente real, onde
   o formato JSON de log passa a valer de verdade (`ENVIRONMENT != local`).
7. **Fluxo de admin**: aprovar, marcar como pago com comprovante, e o histórico.
8. **A versão maior do PostgreSQL da Railway**, conferida por
   `show server_version`, comparada com o `18-alpine` que o `docker-compose.yml`
   e o CI fixam.

## Fora de escopo, e registrado

Domínio próprio; branch protection; backup automatizado; agendamento da
varredura de órfãos (exige cron ou agendador do provedor); monitoramento e
alerta; e os 10 alertas do Dependabot do frontend, que continuam como pendência
própria.

## Riscos aceitos conscientemente

- **A Railway não tem camada gratuita permanente.** É custo recorrente pequeno,
  não zero.
- **O plano gratuito da AWS termina.** Vira pendência **com a data**, para não
  chegar como cobrança surpresa — o mesmo hábito que este projeto usa para tudo
  que nasce verdadeiro e morre em silêncio.
- **Instância única.** O rate limit do Item 27 é em memória e zera a cada
  restart; o próprio item registra isso. A diferença é que agora vale sobre algo
  real.
- **A URL assinada congela a autorização** por `FILE_URL_TTL_SECONDS` (300s).
  Trade-off já declarado no Item 22; passa a valer em produção.

## Uma correção de documentação entra junto

O `current-state.md` registra que uma implantação com S3 "precisa liberar o
domínio do frontend no **CORS do bucket**". **Isso está errado para a UI como
ela existe hoje**, e foi verificado: `ReceiptPreview.tsx` renderiza os arquivos
com `<img src={file.url}>` e `<object data={file.url}>`, e nenhum dos dois é uma
requisição controlada por CORS.

A ressalva volta a ser verdadeira no dia em que algum código buscar o arquivo
por JavaScript — um botão de download com `fetch`, por exemplo, ou qualquer
leitura via `canvas`. Fica registrada com essa condição, em vez de removida.
