# UC-001 — Cadastrar usuário

## Ator principal

Visitante sem sessão autenticada.

## Objetivo

Criar uma conta para acessar as funcionalidades de reembolso.

## Pré-condições

- O visitante está na tela pública de cadastro.

## Fluxo principal

1. O visitante informa nome, e-mail e senha.
2. O frontend envia os dados para `POST /auth/register`.
3. A API valida nome não vazio, formato do e-mail e senha com pelo menos oito
   caracteres.
4. A API protege a senha com hash e cria o usuário com papel `standard`.
5. A API responde com identificador, nome, e-mail e papel, sem retornar a senha.
6. O frontend direciona o usuário para `/login`.

## Fluxos alternativos e erros

- Se nome, e-mail ou senha forem inválidos, a API rejeita a entrada e o
  frontend exibe a mensagem recebida; nenhuma conta é criada.
- Se o e-mail já estiver cadastrado, o repositório rejeita a duplicidade e a
  API informa o erro; nenhuma conta é criada. **A mensagem é explícita de
  propósito**, mesmo revelando que aquele e-mail existe: sem ela, quem já tem
  conta recebe um erro que não explica nada. O risco de enumeração é mitigado
  pelo limite de tentativas (BR-023), não pela omissão.
- Se o mesmo cliente exceder o limite de tentativas na janela vigente, a API
  responde `429` sem processar o cadastro (BR-023).

## Pós-condições

- Em caso de sucesso, existe um novo usuário `standard` com senha protegida.
- O cadastro não inicia uma sessão; o usuário permanece sem token e está na
  tela de login.
- Em caso de erro, nenhum novo usuário é persistido.

## Regras relacionadas

- [BR-001](../business-rules.md#br-001--dados-obrigatórios-do-cadastro)
- [BR-002](../business-rules.md#br-002--unicidade-do-e-mail)
- [BR-003](../business-rules.md#br-003--papel-inicial-do-usuário)
- [BR-004](../business-rules.md#br-004--proteção-da-senha)
- [BR-023](../business-rules.md#br-023--limite-de-tentativas-em-autenticação-e-cadastro)

## Evidências

- `src/main/routes/auth_routes.py` expõe `POST /auth/register` e aplica
  `UserRegisterValidator`.
- `src/validators/user_register_validator.py` exige nome, e-mail válido e senha
  com no mínimo oito caracteres.
- `src/controllers/user_register_controller.py` gera o hash, fixa o papel
  `standard` e forma uma resposta sem senha.
- `src/models/repositories/users_repository.py` converte a violação da
  unicidade do e-mail em erro de e-mail já cadastrado.
- `../Refund-FrontEnd/src/context/AuthContext.tsx` envia o cadastro sem criar
  sessão, e `../Refund-FrontEnd/src/pages/PageRegister.tsx` navega para
  `/login` apenas após o sucesso.
