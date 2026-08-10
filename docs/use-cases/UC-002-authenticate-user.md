# UC-002 — Autenticar usuário

## Ator principal

Usuário cadastrado.

## Objetivo

Iniciar uma sessão autenticada para acessar as operações de reembolso.

## Pré-condições

- O usuário possui uma conta cadastrada.
- O usuário está na tela pública de login.

## Fluxo principal

1. O usuário informa e-mail e senha.
2. O frontend envia as credenciais para `POST /auth/login`.
3. A API localiza o usuário pelo e-mail e compara a senha com o hash persistido.
4. A API gera um JWT com `user_id` e `role`.
5. A API devolve o token e os dados não sensíveis `name`, `email` e `role`, sem
   retornar a senha.
6. O frontend persiste separadamente o token e os dados do usuário no
   `localStorage`, atualiza a sessão e direciona para `/`.

## Fluxos alternativos e erros

- Se o e-mail não existir ou a senha estiver incorreta, a API devolve a mesma
  mensagem genérica `Invalid credentials`; o frontend exibe o erro e não
  inicia a sessão.
- Se o e-mail não tiver formato válido, a validação da rota rejeita a entrada
  antes da autenticação.
- Se o mesmo cliente exceder o limite de tentativas na janela vigente, a API
  responde `429` **sem verificar a senha** (BR-023). A tentativa não conta como
  falha de credencial: ela não chegou a ser avaliada.

## Pós-condições

- Em caso de sucesso, token e dados não sensíveis do usuário ficam persistidos
  no navegador e a sessão passa a ser considerada autenticada.
- Em caso de erro, não são persistidos novos dados de sessão.

## Regras relacionadas

- [BR-004](../business-rules.md#br-004--proteção-da-senha)
- [BR-005](../business-rules.md#br-005--resposta-genérica-no-login-inválido)
- [BR-023](../business-rules.md#br-023--limite-de-tentativas-em-autenticação-e-cadastro)

## Evidências

- `src/main/routes/auth_routes.py` expõe `POST /auth/login` com
  `UserLoginValidator`.
- `src/controllers/user_login_controller.py` usa a mesma resposta para usuário
  ausente e senha incorreta, gera o JWT e omite a senha da resposta.
- `src/drivers/password_handler.py` compara a senha informada com o hash.
- `../Refund-FrontEnd/src/context/AuthContext.tsx` persiste o token em
  `refund:token` e nome, e-mail e papel em `refund:user`.
- `../Refund-FrontEnd/src/pages/PageLogin.tsx` apresenta erros sem navegar e
  direciona para `/` após o login bem-sucedido.
