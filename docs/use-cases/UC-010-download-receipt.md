# UC-010 — Baixar comprovante de reembolso

## Ator principal

Usuário autenticado, com papel `standard` ou `admin`.

## Objetivo

Obter o conteúdo binário do comprovante de uma solicitação para exibição no
frontend.

## Pré-condições

- O usuário possui um JWT válido.
- O usuário possui o identificador de uma solicitação.

## Fluxo principal

1. O usuário escolhe **Abrir comprovante** na tela de detalhes de uma
   solicitação.
2. O frontend solicita `GET /refunds/{refund_id}/receipt` com o JWT no
   cabeçalho `Authorization: Bearer`.
3. A API autentica o usuário, busca a solicitação pelo ID e verifica o escopo
   de acesso conforme o papel — a mesma regra de `GET /refunds/{refund_id}`.
4. A API lê o conteúdo do arquivo do disco e devolve o corpo binário, com o
   `Content-Type` derivado da extensão armazenada no nome do arquivo (nunca de
   um cabeçalho enviado pelo cliente).
5. O frontend exibe o comprovante.

## Autorização

- Proprietário da solicitação: acesso permitido.
- `admin`: acesso permitido a qualquer solicitação.
- Usuário `standard` que não é o proprietário: acesso negado com o mesmo `404`
  usado para um ID inexistente, para não revelar quais identificadores
  existem.

## Tabela de códigos

| Código | Cenário |
| --- | --- |
| `200` | Comprovante encontrado; corpo binário com `Content-Type` de imagem ou PDF conforme a extensão armazenada. |
| `401` | JWT ausente, inválido ou expirado. |
| `404` | Id de solicitação inexistente, solicitação pertencente a outro usuário `standard`, ou arquivo ausente no disco apesar do registro existir. |

## Fluxos alternativos e erros

- Se o cabeçalho estiver ausente ou não usar `Bearer`, a API responde `401`.
- Se o JWT for inválido ou estiver expirado, a API responde `401`.
- Se o ID não existir, a API responde `404` com `Refund not found`.
- Se o ID existir, mas pertencer a outro usuário `standard`, a API devolve o
  mesmo `404` e a mesma mensagem, sem revelar a existência do recurso.
- Se o registro existir, mas o arquivo não for encontrado no disco, a API
  responde o mesmo `404` com `Refund not found` — indistinguível de um ID
  inexistente, pelo mesmo motivo.

## Pós-condições

- Nenhuma solicitação é alterada.
- Em caso de sucesso, o conteúdo do comprovante é entregue ao frontend.
- Em caso de recurso inexistente ou alheio, nenhum byte do arquivo é
  devolvido.

## Regras relacionadas

- [BR-006](../business-rules.md#br-006--autenticação-das-operações-de-reembolso)
- [BR-012](../business-rules.md#br-012--escopo-de-acesso-por-papel)
- [BR-013](../business-rules.md#br-013--recurso-inexistente-ou-alheio)
- [BR-020](../business-rules.md#br-020--acesso-ao-comprovante)

## Evidências

- `src/main/routes/refund_routes.py` protege e expõe
  `GET /refunds/{refund_id}/receipt`, devolvendo um `Response` binário (não um
  `JSONResponse`) com o `Content-Type` calculado pelo controller.
- `src/views/receipt_finder_view.py` extrai `refund_id` da rota e `user_id`/
  `role` do token, e repassa ao controller.
- `src/controllers/receipt_finder_controller.py` aplica a mesma regra de
  `refund_finder_controller.py` — 404 idêntico para ID inexistente e para
  solicitação alheia — lê o arquivo pelo `FileStorage` e deriva o
  `Content-Type` da extensão do nome armazenado com `mimetypes.guess_type`,
  nunca do cabeçalho enviado pelo cliente.
- `src/drivers/file_storage.py` implementa a leitura do arquivo e levanta
  `FileNotFoundError` quando o registro sobrevive, mas o arquivo não existe
  mais no disco — convertido no mesmo `404` de "não encontrado".
