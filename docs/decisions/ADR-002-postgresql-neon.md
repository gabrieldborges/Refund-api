# ADR-002: Usar PostgreSQL no Neon

## Status

Aceita

Data: 2026-07-15

Amendamento: 2026-07-28 — atualiza a seção de criação do schema, que passou de
`metadata.create_all` para migrations do Alembic.

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
