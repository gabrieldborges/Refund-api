# UC-009 — Remover foto de perfil

## Ator principal

Usuário autenticado.

## Objetivo

Remover a foto de perfil do usuário autenticado, retornando ao avatar padrão
do produto.

## Pré-condições

- O usuário possui um JWT válido.
- O usuário está na tela de perfil ou configurações da conta.

## Fluxo principal

1. O usuário escolhe remover sua foto de perfil.
2. O frontend envia `DELETE /users/me/avatar` com o JWT no cabeçalho
   `Authorization: Bearer`.
3. A API autentica o usuário e zera `avatar_filename` no banco.
4. Se havia um arquivo associado, a API o remove do disco somente depois de
   confirmar a atualização no banco.
5. A API responde com `avatar_filename` igual a `null`; o frontend volta a
   exibir o avatar padrão.

## Fluxos alternativos e erros

- Se o cabeçalho estiver ausente ou não usar `Bearer`, a API responde `401`.
- Se o JWT for inválido ou estiver expirado, a API responde `401`; o frontend
  limpa os dados locais de sessão e direciona para `/login`.
- Se o usuário já não possuía foto de perfil, a API responde `200` do mesmo
  jeito, sem tentar remover arquivo algum — a operação é idempotente.
- Se a requisição falhar, o frontend exibe o erro e mantém a foto atual.

## Pós-condições

- Em caso de sucesso, `avatar_filename` é `null` e o arquivo anterior (quando
  existia) não existe mais no disco; um login subsequente devolve
  `avatar_filename: null`.
- Repetir a remoção é seguro: a segunda chamada também responde `200` com
  `avatar_filename: null`, sem efeito adicional.
- Em caso de falha de autenticação, nenhuma foto é removida.

## Regras relacionadas

- [BR-006](../business-rules.md#br-006--autenticação-das-operações-de-reembolso)
- [BR-019](../business-rules.md#br-019--formato-e-tamanho-da-foto-de-perfil)

## Evidências

- `src/main/routes/user_routes.py` protege e expõe `DELETE /users/me/avatar`.
- `src/controllers/avatar_remover_controller.py` zera `avatar_filename` e só
  então remove o arquivo anterior — mesma ordem de segurança usada no envio,
  para nunca deixar a coluna apontando para um arquivo já removido.
- `src/drivers/file_storage.py` não falha ao tentar remover um arquivo que já
  não existe, o que garante a idempotência de chamadas repetidas.
- `src/controllers/user_login_controller.py` devolve `avatar_filename` na
  resposta do login.
