# ADR-002: Usar PostgreSQL no Neon

## Status

Aceita

Data: 2026-07-15

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

Na inicialização da API, executar `metadata.create_all` durante o ciclo de vida
do FastAPI para criar as tabelas definidas nos metadados quando ainda não
existirem.

## Consequências

- A execução da aplicação depende da disponibilidade do serviço Neon e de uma
  `DATABASE_URL` válida no ambiente.
- A URL precisa usar o dialeto `postgresql+asyncpg` e `ssl=require`; uma URL com
  `sslmode` é incompatível com o driver adotado.
- A criação inicial das tabelas ocorre automaticamente no início da aplicação,
  sem exigir a execução manual do script SQL.
- O banco deixa de ser um arquivo local e passa a exigir conectividade de rede
  e cuidados operacionais com credenciais e limites de conexão.
