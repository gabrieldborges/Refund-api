# UC-008 — Enviar foto de perfil

## Ator principal

Usuário autenticado.

## Objetivo

Definir ou substituir a foto de perfil do usuário autenticado.

## Pré-condições

- O usuário possui um JWT válido.
- O usuário está na tela de perfil ou configurações da conta.

## Fluxo principal

1. O usuário escolhe uma imagem JPG ou PNG para sua foto de perfil.
2. O frontend monta um `FormData` com o arquivo e envia
   `POST /users/me/avatar` como requisição multipart, com o JWT no cabeçalho
   `Authorization: Bearer`.
3. A API autentica o usuário, lê o arquivo e valida sua extensão e tamanho.
4. O armazenamento gera para a foto um nome único baseado em UUID, preserva a
   extensão original e grava o conteúdo no diretório de avatares.
5. A API atualiza `avatar_filename` do usuário para o novo nome.
6. Se o usuário já possuía uma foto anterior, a API remove o arquivo antigo do
   disco somente depois de confirmar a troca no banco.
7. A API responde com o novo `avatar_filename`; o frontend atualiza a foto
   exibida.

## Fluxos alternativos e erros

- Se o cabeçalho estiver ausente ou não usar `Bearer`, a API responde `401`.
- Se o JWT for inválido ou estiver expirado, a API responde `401`; o frontend
  limpa os dados locais de sessão e direciona para `/login`.
- Se o arquivo não tiver extensão `jpg`, `jpeg` ou `png`, a API responde `422`
  com `Avatar must be JPG or PNG`. Diferente do comprovante de reembolso, PDF
  não é aceito como foto de perfil.
- Se o arquivo exceder 4MB, a API responde `422` com
  `Avatar must be smaller than 4MB`.
- Se a requisição falhar, o frontend exibe o erro e mantém a foto atual.

## Pós-condições

- Em caso de sucesso, `avatar_filename` aponta para o novo arquivo, o arquivo
  anterior (quando existia) não existe mais no disco, e uma consulta a
  `GET /avatars/{avatar_filename}` serve a nova imagem publicamente. Um login
  subsequente devolve o novo `avatar_filename`.
- Em caso de falha de validação ou autenticação, nenhuma foto é trocada e o
  arquivo anterior permanece intacto.

## Regras relacionadas

- [BR-006](../business-rules.md#br-006--autenticação-das-operações-de-reembolso)
- [BR-019](../business-rules.md#br-019--formato-e-tamanho-da-foto-de-perfil)

## Evidências

- `src/main/routes/user_routes.py` protege e expõe `POST /users/me/avatar`.
- `src/validators/avatar_upload_validator.py` restringe a extensão a JPG/PNG e
  o tamanho a 4MB, validado pela extensão do arquivo, não pelo `Content-Type`
  informado pelo cliente.
- `src/controllers/avatar_uploader_controller.py` salva o novo arquivo,
  atualiza `avatar_filename` e só então remove o arquivo anterior — nessa
  ordem, para nunca deixar o usuário sem foto caso a atualização falhe.
- `src/drivers/file_storage.py` gera o nome único com UUID e grava o arquivo no
  diretório de avatares.
- `src/main/server/server.py` expõe esse diretório estaticamente em
  `/avatars`.
- `src/controllers/user_login_controller.py` devolve `avatar_filename` na
  resposta do login.
