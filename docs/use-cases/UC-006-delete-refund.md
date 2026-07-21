# UC-006 — Excluir solicitação de reembolso

## Ator principal

Usuário autenticado, com papel `standard` ou `admin`.

## Objetivo

Remover uma solicitação e seu comprovante armazenado.

## Pré-condições

- O usuário possui um JWT válido.
- O usuário está na tela de detalhes de uma solicitação.
- Se tiver papel `standard`, o usuário é proprietário da solicitação; um
  `admin` pode excluir qualquer solicitação existente.

## Fluxo principal

1. O usuário escolhe **Excluir** na tela de detalhes.
2. O frontend abre um diálogo que informa que a ação é irreversível e oferece
   as opções **Cancelar** e **Confirmar**.
3. O usuário confirma a exclusão.
4. O frontend envia `DELETE /refunds/{refund_id}`.
5. A API autentica o usuário, busca a solicitação e valida o acesso conforme o
   papel e a propriedade.
6. A API remove o registro do banco de dados e tenta remover o arquivo do
   comprovante quando ele existe.
7. A API confirma a exclusão; o frontend invalida o cache da listagem, fecha o
   diálogo e retorna para `/`.

## Fluxos alternativos e erros

- Se o usuário cancelar no diálogo, nenhuma requisição de exclusão é enviada e
  a solicitação permanece inalterada.
- Se o JWT estiver ausente, inválido ou expirado, a API responde `401`.
- Se o ID não existir, a API responde `404` com `Refund not found`.
- Se o ID existir, mas pertencer a outro usuário `standard`, a API devolve o
  mesmo `404` e a mesma mensagem, sem revelar a existência do recurso.
- Se o arquivo do comprovante já não existir no armazenamento, a tentativa de
  remoção do arquivo não falha por esse motivo.
- Se a exclusão falhar, o frontend exibe o erro e permanece na tela de detalhes.

## Pós-condições

- Em caso de sucesso, o registro não existe mais no banco e o comprovante foi
  removido caso estivesse presente; a listagem será recarregada sem o item.
- Em caso de cancelamento ou erro anterior à remoção, a solicitação permanece.

## Regras relacionadas

- [BR-006](../business-rules.md#br-006--autenticação-das-operações-de-reembolso)
- [BR-012](../business-rules.md#br-012--escopo-de-acesso-por-papel)
- [BR-013](../business-rules.md#br-013--recurso-inexistente-ou-alheio)
- [BR-015](../business-rules.md#br-015--exclusão-da-solicitação-e-do-comprovante)

## Evidências

- `../Refund-FrontEnd/src/pages/PageRefundDetails.tsx` exige confirmação,
  permite cancelar, exibe falhas e retorna para `/` após o sucesso.
- `../Refund-FrontEnd/src/hooks/useDeleteRefund.ts` envia o `DELETE` e invalida
  o cache da listagem.
- `src/main/routes/refund_routes.py` protege e expõe
  `DELETE /refunds/{refund_id}`.
- `src/controllers/refund_deleter_controller.py` aplica a regra de acesso, usa
  o mesmo `404` para ID inexistente ou alheio, remove o registro e solicita a
  remoção do arquivo.
- `src/models/repositories/refunds_repository.py` executa e confirma a remoção
  no banco; `src/drivers/receipt_storage.py` remove o arquivo somente se ele
  existir.
