# ADR-002: Usar PostgreSQL no Neon

## Status

Aceita

Data: 2026-07-15

Amendamento: 2026-07-28 — atualiza a seção de criação do schema, que passou de
`metadata.create_all` para migrations do Alembic.

Amendamento: 2026-08-07 (Item 19) — acrescenta um PostgreSQL descartável em
container para testes de integração; ver o amendamento ao final da seção de
Decisão.

## Contexto

O banco da aplicação foi migrado do SQLite local para PostgreSQL hospedado no
Neon. O acesso continua assíncrono por meio do SQLAlchemy, agora com o driver
`asyncpg`.

O `asyncpg` não aceita o parâmetro `sslmode` normalmente presente em URLs de
conexão PostgreSQL. Para essa combinação de driver e dialeto, a conexão segura
é configurada com `ssl=require`.

## Decisão

Usar PostgreSQL no Neon com uma URL no formato
`postgresql+asyncpg://...?ssl=require`, fornecida pela variável de ambiente
`DATABASE_URL`. Nenhuma credencial ou URL real é mantida na documentação.

O schema é criado e evoluído por migrations do Alembic (`alembic/versions/`),
aplicadas manualmente com `alembic upgrade head`. A tabela `alembic_version`
rastreia qual revisão está aplicada no banco.

**Amendamento (2026-07-28):** a decisão original mandava executar
`metadata.create_all` durante o ciclo de vida do FastAPI, criando as tabelas
definidas nos metadados quando ainda não existiam. Isso deixou de valer: o
`create_all` cria tabelas que faltam, mas nunca altera uma tabela já existente
— quando a solicitação de reembolso ganhou a coluna `status` e a tabela
`refund_reviews`, não havia como o `create_all` adicionar uma coluna a uma
tabela `refunds` que já tinha linhas. A partir daí o schema passou a ser
governado inteiramente pelas migrations do Alembic, e `src/main/server/server.py`
não cria mais tabelas na inicialização.

**Amendamento (2026-08-07, Item 19):** os testes passam a ter um PostgreSQL
próprio, descartável, definido em `docker-compose.yml` e fixado na **mesma
versão maior que a produção** (o Neon reporta 18.4). A aplicação continua
falando com o Neon pela `DATABASE_URL`; o container existe apenas para os
testes marcados com `integration`, que ficam **fora** da suíte padrão para que
ninguém precise de Docker para trabalhar no projeto.

A decisão que isso resolve não é "onde rodar o banco", e sim **contra o que
verificar**. Os 34 testes de repository são mockados: provam que o SQL certo é
**montado**, nunca que o PostgreSQL o **aceita**. Este projeto já perdeu duas
vezes com essa lacuna — o singleton de sessão do `DatabaseConnectionHandler`
(500 e vazamento de conexão sob concorrência) e o `paid` não terminal, este
último registrado no diário como "invisível à suíte mockada".

**SQLite fica descartado, inclusive como atalho local.** A trilha oferecia
"SQLite opcional para feedback rápido"; adotá-lo esconderia justamente as
diferenças que justificam este amendamento — constraints, `FOR UPDATE`,
`lock_timeout`, tipos e comportamento de agregados. O `aiosqlite`, que
sobrevivia no `requirements.txt` sem nenhum import desde a migração para o
Neon, foi removido.

## Consequências

- A execução da aplicação depende da disponibilidade do serviço Neon e de uma
  `DATABASE_URL` válida no ambiente.
- A URL precisa usar o dialeto `postgresql+asyncpg` e `ssl=require`; uma URL com
  `sslmode` é incompatível com o driver adotado.
- A criação e a evolução das tabelas dependem da execução manual de
  `alembic upgrade head`; a aplicação não cria nem altera schema na
  inicialização. Rodar o comando é seguro a qualquer momento, pois ele aplica
  apenas as migrations que ainda faltam.
- `init/schema.sql` deixou de ser a referência de criação do banco; existe só
  como referência histórica, e pode ficar desatualizado em relação às
  migrations mais recentes.
- O banco deixa de ser um arquivo local e passa a exigir conectividade de rede
  e cuidados operacionais com credenciais e limites de conexão.
- Os testes de integração exigem Docker; a suíte padrão, não. Quem não tiver
  Docker continua rodando `pytest` inteiro, e o CI cobre a outra metade.
- O ciclo `upgrade`/`downgrade` das migrations deixa de ser verificado à mão
  e passa a ter teste, incluindo um que percorre **revisão por revisão**.
- O `lock_timeout` deixa de depender de um `SHOW` manual: um teste afirma que
  o parâmetro chega ao servidor e outro que a contenção de linha **desiste**
  em vez de esperar para sempre.
- **O que os testes de integração continuam sem cobrir:** o Neon em si. O
  container é PostgreSQL puro, e o proxy do Neon já mostrou ter comportamento
  próprio — foi ele que descartou em silêncio a forma de `lock_timeout` que a
  documentação do asyncpg recomenda. Um teste verde aqui não prova que aquele
  proxy se comporta igual.
