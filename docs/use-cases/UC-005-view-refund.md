# UC-005 — Consultar solicitação de reembolso

## Ator principal

Usuário autenticado, com papel `standard` ou `admin`.

## Objetivo

Visualizar os dados de uma solicitação específica e abrir seu comprovante.

## Pré-condições

- O usuário possui um JWT válido.
- O usuário possui o identificador de uma solicitação.

## Fluxo principal

1. O usuário seleciona uma solicitação na lista.
2. O frontend obtém o ID da rota e solicita `GET /refunds/{refund_id}`.
3. A API autentica o usuário, busca a solicitação pelo ID e verifica o escopo de
   acesso conforme o papel.
4. A API devolve os campos da solicitação, inclusive o `status`
   (`pending`, `approved` ou `rejected`) e o objeto `user` (`id`, `name`,
   `has_avatar`) do solicitante, sem `user_id` no topo e sem o nome do
   arquivo de comprovante.
5. O frontend exibe nome, categoria e valor em modo somente leitura.
6. Quando o usuário escolhe **Abrir comprovante**, o frontend solicita
   `GET /refunds/{refund_id}/receipt` com o JWT no cabeçalho; a foto de
   perfil do solicitante, quando `has_avatar` é verdadeiro, vem de
   `GET /users/{user_id}/avatar`, também autenticada.

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

> **Mudança de contrato:** a resposta não traz mais `user_id` no topo, nem o
> nome do arquivo de comprovante; o solicitante agora vem em `user.id`, ao
> lado de `user.name` e `user.has_avatar`. Além disso, o comprovante e a foto
> de perfil deixam de ter URL pública: precisam ser buscados,
> respectivamente, em `GET /refunds/{refund_id}/receipt` e
> `GET /users/{user_id}/avatar`, ambas autenticadas. Isso quebra nos dois
> sentidos com o frontend anterior — inclusive o link que ele monta hoje para
> `/receipts/{filename}`, que passa a responder `404` — então backend e
> frontend precisam ser implantados juntos.

## Regras relacionadas

- [BR-006](../business-rules.md#br-006--autenticação-das-operações-de-reembolso)
- [BR-012](../business-rules.md#br-012--escopo-de-acesso-por-papel)
- [BR-013](../business-rules.md#br-013--recurso-inexistente-ou-alheio)
- [BR-017](../business-rules.md#br-017--transições-de-status-permitidas)
- [BR-020](../business-rules.md#br-020--acesso-ao-comprovante)
- [BR-021](../business-rules.md#br-021--acesso-à-foto-de-perfil)

## Evidências

- `src/main/routes/refund_routes.py` protege e expõe
  `GET /refunds/{refund_id}` e `GET /refunds/{refund_id}/receipt`.
- `src/controllers/refund_finder_controller.py` permite acesso global ao
  `admin`, limita o usuário `standard` ao proprietário e usa o mesmo `404` para
  recurso inexistente ou alheio.
- `src/models/repositories/refunds_repository.py` faz `JOIN` com `Users` e
  monta o objeto `user` com o `avatar_filename` bruto — dado interno do
  repositório, não o contrato da resposta.
- `src/controllers/refund_serializer.py` é quem converte esse dado interno no
  contrato público: descarta `filename` e reduz `avatar_filename` a
  `has_avatar`.
- `src/controllers/receipt_finder_controller.py` aplica a BR-020 para servir o
  comprovante por `GET /refunds/{refund_id}/receipt`.
- `../Refund-FrontEnd/src/hooks/useRefund.ts` consulta a API pelo ID da rota.
- `../Refund-FrontEnd/src/pages/PageRefundDetails.tsx` exibe os campos como
  somente leitura e oferece o link **Abrir comprovante** em nova aba.
- `../Refund-FrontEnd/src/lib/api.ts` ainda monta a URL pública antiga
  `/receipts/{filename}`; a migração para `GET /refunds/{refund_id}/receipt`
  é o próximo passo do learning path, fora do escopo desta branch.
