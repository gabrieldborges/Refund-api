# UC-005 — Consultar solicitação de reembolso

## Ator principal

Usuário autenticado, com papel `standard` ou `admin`.

## Objetivo

Visualizar os dados de uma solicitação específica e abrir seu comprovante.

## Pré-condições

- O usuário possui um JWT válido.
- O usuário possui o identificador de uma solicitação.
- Se tiver papel `standard`, o usuário é proprietário da solicitação; um
  `admin` pode consultar qualquer solicitação existente.

## Fluxo principal

1. O usuário seleciona uma solicitação na lista.
2. O frontend obtém o ID da rota e solicita `GET /refunds/{refund_id}`.
3. A API autentica o usuário, busca a solicitação pelo ID e verifica o escopo de
   acesso conforme o papel.
4. A API devolve os campos da solicitação, inclusive o nome do comprovante.
5. O frontend exibe nome, categoria e valor em modo somente leitura.
6. Quando o usuário escolhe **Abrir comprovante**, o frontend abre em nova aba
   a URL pública `/receipts/{filename}`.

## Fluxos alternativos e erros

- Se o JWT estiver ausente, inválido ou expirado, a API responde `401`.
- Se o ID não existir, a API responde `404` com `Refund not found`.
- Se o ID existir, mas pertencer a outro usuário `standard`, a API devolve o
  mesmo `404` e a mesma mensagem, sem revelar a existência do recurso.
- Se a consulta falhar, o frontend informa que não foi possível encontrar a
  solicitação.

## Pós-condições

- Nenhuma solicitação é alterada.
- Em caso de sucesso, os dados são exibidos e o comprovante pode ser aberto.
- Em caso de recurso inexistente ou alheio, nenhum dado da solicitação é
  exposto.

## Regras relacionadas

- [BR-006](../business-rules.md#br-006--autenticação-das-operações-de-reembolso)
- [BR-012](../business-rules.md#br-012--escopo-de-acesso-por-papel)
- [BR-013](../business-rules.md#br-013--recurso-inexistente-ou-alheio)

## Evidências

- `src/main/routes/refund_routes.py` protege e expõe
  `GET /refunds/{refund_id}`.
- `src/controllers/refund_finder_controller.py` permite acesso global ao
  `admin`, limita o usuário `standard` ao proprietário e usa o mesmo `404` para
  recurso inexistente ou alheio.
- `../Refund-FrontEnd/src/hooks/useRefund.ts` consulta a API pelo ID da rota.
- `../Refund-FrontEnd/src/pages/PageRefundDetails.tsx` exibe os campos como
  somente leitura e oferece o link **Abrir comprovante** em nova aba.
- `../Refund-FrontEnd/src/lib/api.ts` monta a URL
  `/receipts/{filename}` usada pelo link.
