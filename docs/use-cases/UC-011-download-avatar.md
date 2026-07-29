# UC-011 — Baixar foto de perfil

## Ator principal

Usuário autenticado.

## Objetivo

Obter o conteúdo binário da foto de perfil de um usuário, próprio ou alheio,
para exibição no frontend.

## Pré-condições

- O usuário possui um JWT válido.
- O usuário possui o identificador de um usuário cuja foto quer exibir.

## Fluxo principal

1. O frontend precisa exibir a foto de um usuário — por exemplo, o
   solicitante de um reembolso cujo `has_avatar` é verdadeiro.
2. O frontend solicita `GET /users/{user_id}/avatar` com o JWT no cabeçalho
   `Authorization: Bearer`.
3. A API exige apenas que a requisição esteja autenticada — não avalia de
   quem é o JWT, só que ele seja válido.
4. A API busca o usuário pelo ID; se ele existir e tiver `avatar_filename`
   preenchido, lê o arquivo do disco.
5. A API devolve o corpo binário, com o `Content-Type` derivado da extensão
   armazenada no nome do arquivo (nunca de um cabeçalho enviado pelo
   cliente).
6. O frontend exibe a foto.

## Autorização

- Qualquer usuário autenticado pode baixar a foto de perfil de qualquer
  usuário — não há verificação de identidade além de possuir um JWT válido,
  conforme BR-021.

## Tabela de códigos

| Código | Cenário |
| --- | --- |
| `200` | Foto encontrada; corpo binário com `Content-Type` de imagem conforme a extensão armazenada. |
| `401` | JWT ausente, inválido ou expirado. |
| `404` | Id de usuário inexistente, ou usuário sem foto de perfil (`avatar_filename` nulo), ou arquivo ausente no disco apesar do registro existir. |

## Fluxos alternativos e erros

- Se o cabeçalho estiver ausente ou não usar `Bearer`, a API responde `401`.
- Se o JWT for inválido ou estiver expirado, a API responde `401`.
- Se o ID de usuário não existir, a API responde `404` com
  `Avatar not found`.
- Se o usuário existir, mas não tiver foto de perfil, a API devolve o mesmo
  `404` e a mesma mensagem — usuário inexistente e usuário sem foto não são
  distinguíveis pela resposta.
- Se o registro existir, mas o arquivo não for encontrado no disco, a API
  responde o mesmo `404` com `Avatar not found`.

## Pós-condições

- Nenhum dado é alterado.
- Em caso de sucesso, o conteúdo da foto é entregue ao frontend.
- Em caso de usuário inexistente ou sem foto, nenhum byte de arquivo é
  devolvido.

## Regras relacionadas

- [BR-006](../business-rules.md#br-006--autenticação-das-operações-de-reembolso)
- [BR-019](../business-rules.md#br-019--formato-e-tamanho-da-foto-de-perfil)
- [BR-021](../business-rules.md#br-021--acesso-à-foto-de-perfil)

## Evidências

- `src/main/routes/user_routes.py` protege e expõe
  `GET /users/{user_id}/avatar` com `get_current_user`, mas descarta o
  `token_info` retornado — a dependência serve apenas para exigir
  autenticação, não para autorizar por identidade — e devolve um `Response`
  binário com o `Content-Type` calculado pelo controller.
- `src/views/avatar_finder_view.py` extrai apenas `user_id` da rota; não
  recebe identidade de quem pede.
- `src/controllers/avatar_finder_controller.py` trata usuário inexistente e
  usuário sem `avatar_filename` com o mesmo `404`, lê o arquivo pelo
  `FileStorage` e deriva o `Content-Type` da extensão do nome armazenado com
  `mimetypes.guess_type`, nunca do cabeçalho enviado pelo cliente.
- `src/drivers/file_storage.py` implementa a leitura do arquivo e levanta
  `FileNotFoundError` quando o registro sobrevive, mas o arquivo não existe
  mais no disco — convertido no mesmo `404` de "não encontrado".
