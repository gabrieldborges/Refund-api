# Glossário

## Usuário
Pessoa cadastrada no sistema, identificada por uma conta e por um papel de
acesso.

## Usuário standard
Usuário com o papel `standard`, criado pelo fluxo público de cadastro. Pode
cadastrar e consultar somente as próprias solicitações de reembolso.

## Administrador
Usuário com o papel `admin`. Pode consultar as solicitações de todos os
usuários.

## Solicitação de reembolso
Registro de uma despesa enviado por um usuário, com nome, categoria, valor e
comprovante. No contexto da interface e da API, os termos "solicitação" e
"reembolso" nomeiam esse mesmo registro.

## Comprovante
Arquivo enviado com uma solicitação de reembolso e armazenado para consulta
posterior.

## Categoria
Classificação da despesa informada ao criar uma solicitação de reembolso.

## Valor em centavos
Representação inteira do valor monetário da solicitação, persistida pela API
no campo `amount_in_cents`.

## Autenticação
Processo que valida as credenciais do usuário e fornece um token com sua
identidade e seu papel de acesso.

## Proprietário da solicitação
Usuário autenticado associado à solicitação pelo campo `user_id` no momento da
criação.
