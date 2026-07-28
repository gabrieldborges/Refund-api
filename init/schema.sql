-- Referência histórica apenas. O schema autoritativo vive nas migrations do
-- Alembic (alembic/versions/), aplicadas com `alembic upgrade head`; a API não
-- cria mais tabelas no startup. Este arquivo NÃO foi atualizado para
-- acompanhar as migrations mais recentes: falta a coluna `status` em
-- `refunds` e falta a tabela `refund_reviews` inteira. Não use este arquivo
-- para provisionar ou validar o schema atual.

CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    email TEXT NOT NULL UNIQUE,
    password TEXT NOT NULL,
    role TEXT NOT NULL DEFAULT 'standard',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS refunds (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users(id),
    name TEXT NOT NULL,
    category TEXT NOT NULL,
    amount_in_cents INTEGER NOT NULL,
    filename TEXT NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
