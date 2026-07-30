# UC-013 — Consultar histórico de revisões

## Ator principal

Usuário autenticado, com papel `standard` (dono da solicitação) ou `admin`.

## Objetivo

Consultar o histórico completo de transições de status de uma solicitação —
aprovações, rejeições e o pagamento — incluindo o motivo registrado em cada
rejeição, hoje write-only em qualquer outra resposta da API.

## Pré-condições

- O usuário possui um JWT válido.
- O usuário possui o identificador de uma solicitação.

## Fluxo principal

1. O cliente envia `GET /refunds/{refund_id}/reviews` com o JWT no cabeçalho
   `Authorization: Bearer`.
2. A API autentica o usuário, busca a solicitação pelo ID e aplica a mesma
   regra de acesso de `GET /refunds/{refund_id}`: dono ou `admin`; caso
   contrário, `404`.
3. A API busca todas as linhas de `RefundReview` associadas àquela
   solicitação, ordenadas por `created_at` crescente, com `id` como
   desempate.
4. A API serializa cada linha com `from_status`, `to_status`, `reason`,
   `reviewer` (`id`, `name`) e `created_at`, e devolve `count` junto da
   lista.

## Resposta

```json
{
  "type": "RefundReview",
  "count": 2,
  "attributes": [
    {
      "from_status": "pending",
      "to_status": "approved",
      "reason": null,
      "reviewer": { "id": 1, "name": "Gabriel" },
      "created_at": "2026-07-30T10:00:00"
    },
    {
      "from_status": "approved",
      "to_status": "paid",
      "reason": null,
      "reviewer": { "id": 1, "name": "Gabriel" },
      "created_at": "2026-07-30T14:20:00"
    }
  ]
}
```

Uma solicitação nunca decidida devolve `count: 0` e `attributes: []` — não é
um erro, é a ausência normal de histórico.

O nome de quem decidiu é visível para o dono da solicitação. É decisão
deliberada: uma regra só — "quem pode ver o reembolso pode ver a decisão
dele" — em vez de uma resposta que muda de forma conforme quem pergunta.

## Autorização

- Proprietário da solicitação: acesso permitido, ao histórico completo,
  incluindo o `reason` de rejeições.
- `admin`: acesso permitido a qualquer solicitação.
- Usuário `standard` que não é o proprietário: acesso negado com o mesmo
  `404` usado para um ID inexistente, para não revelar quais identificadores
  existem (BR-013).

## Tabela de códigos

| Código | Cenário |
| --- | --- |
| `200` | Solicitação encontrada e acessível; corpo traz `count` e a lista de decisões (vazia se nunca decidida). |
| `401` | JWT ausente, inválido ou expirado. |
| `404` | Id de solicitação inexistente, ou solicitação pertencente a outro usuário `standard`. |

## Fluxos alternativos e erros

- Se o cabeçalho estiver ausente ou não usar `Bearer`, a API responde `401`.
- Se o JWT for inválido ou estiver expirado, a API responde `401`.
- Se o ID não existir, a API responde `404` com `Refund not found`.
- Se o ID existir, mas pertencer a outro usuário `standard`, a API devolve o
  mesmo `404` e a mesma mensagem, sem revelar a existência do recurso.
- Se a solicitação nunca foi decidida (ainda `pending`, sem pagamento), a
  API responde `200` com `count: 0` e lista vazia.

## Pós-condições

- Nenhuma solicitação e nenhuma revisão são alteradas.
- Em caso de sucesso, o histórico completo de decisões é devolvido na ordem
  em que aconteceram.

## Regras relacionadas

- [BR-006](../business-rules.md#br-006--autenticação-das-operações-de-reembolso)
- [BR-012](../business-rules.md#br-012--escopo-de-acesso-por-papel)
- [BR-013](../business-rules.md#br-013--recurso-inexistente-ou-alheio)
- [BR-018](../business-rules.md#br-018--justificativa-obrigatória-na-rejeição)

## Evidências

- `src/main/routes/refund_routes.py` protege e expõe
  `GET /refunds/{refund_id}/reviews`, declarada antes de
  `GET /refunds/{refund_id}` na ordenação do arquivo.
- `src/views/refund_review_lister_view.py` extrai `refund_id`, `user_id` e
  `role` e repassa ao controller.
- `src/controllers/refund_review_lister_controller.py` aplica o mesmo `404`
  idêntico de `receipt_finder_controller.py` para id inexistente e
  solicitação alheia, e serializa cada linha do histórico;
  `src/controllers/refund_review_lister_controller_test.py::test_owner_reads_their_own_history`
  comprova a serialização completa, inclusive o `reason` de uma rejeição;
  `::test_admin_reads_someone_elses_history`,
  `::test_a_never_decided_refund_has_an_empty_history`,
  `::test_someone_elses_refund_is_not_found` e
  `::test_unknown_refund_is_not_found` cobrem os demais cenários.
- `src/models/repositories/refund_reviews_repository.py::RefundReviewsReaderRepository.select_by_refund_id`
  faz o `JOIN` com `Users` para o nome de quem decidiu e ordena por
  `created_at` crescente com `id` como desempate.
- `src/main/composer/refund_review_lister_composer.py` monta o
  `RefundReviewsReaderRepository` (que abre sua própria sessão), distinto do
  `RefundReviewsRepository` injetado por sessão que UC-007 e UC-012 usam
  para escrever.
