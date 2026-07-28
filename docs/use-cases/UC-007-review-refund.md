# UC-007 — Revisar solicitação de reembolso

## Ator principal

Usuário autenticado com papel `admin`. Ainda não há tela dedicada no frontend;
o caso de uso é exercido diretamente sobre a API.

## Objetivo

Aprovar ou rejeitar uma solicitação de reembolso, registrando a decisão e sua
transição de status.

## Pré-condições

- O usuário possui um JWT válido com `role` igual a `admin`.
- A solicitação a revisar já existe e pertence a outro usuário.

## Fluxo principal

1. O cliente envia `PATCH /refunds/{refund_id}/status` com o corpo
   `{"status": "approved" | "rejected", "reason"?: string}`.
2. A API autentica o usuário e verifica o papel antes de qualquer consulta ao
   banco.
3. A API busca a solicitação pelo ID; se existir, verifica se ela pertence a
   outro usuário que não o revisor.
4. A API verifica se o status atual da solicitação é diferente do status alvo.
5. A API atualiza `Refund.status` para o valor informado e insere uma linha em
   `RefundReview` com `refund_id`, `reviewer_id`, `from_status`, `to_status` e
   `reason`, tudo em uma única transação.
6. A API devolve a solicitação com o novo `status`.

## Corpo da requisição

| Campo | Obrigatório | Descrição |
| --- | --- | --- |
| `status` | Sim | `approved` ou `rejected`. `pending` não é um alvo válido. |
| `reason` | Somente ao rejeitar | Motivo da rejeição; obrigatório quando `status` é `rejected`. |

## Ordem das checagens

A ordem abaixo não é arbitrária — cada checagem só é feita depois que a
anterior passou:

1. **Corpo da requisição (validator).** `src/views/refund_reviewer_view.py`
   chama `refund_reviewer_validator` antes mesmo de invocar o controller.
   `status` fora de `{approved, rejected}`, ou `rejected` sem `reason`,
   responde `422` sem que o controller — e, portanto, o banco — seja tocado.
2. **Papel do revisor.** É a primeira verificação feita pelo controller, antes
   de qualquer consulta ao banco. Um usuário `standard` recebe `403` para
   qualquer id, exista ele ou não — a checagem que nunca consulta o banco não
   pode revelar se um id é real, o mesmo raciocínio anti-enumeração por trás do
   `404` da BR-013.
3. **Existência da solicitação.** Só é consultada depois que o papel já foi
   confirmado como `admin`. Id inexistente responde `404`.
4. **Autoria da solicitação.** Um `admin`, pela BR-012, já pode ver qualquer
   solicitação — não há mais nada a esconder nesse ponto, então recusar a
   revisão da própria solicitação com `403` não vaza informação nova.
5. **Transição de status.** Repetir a decisão vigente é recusado com `422`,
   porque não há mudança de estado a registrar.
6. **Sucesso.** `200`, com a solicitação refletindo o novo `status`.

Note que a validação do corpo (passo 1) precede a checagem de papel (passo 2)
— um corpo malformado nunca chega a acessar o banco, mas também nunca chega a
saber se quem o enviou tinha permissão. A propriedade de segurança que importa
não é "papel é sempre a primeira checagem de todas", e sim que **nenhum acesso
ao banco acontece antes da checagem de papel**: por isso um `standard` recebe
o mesmo `403` para um id real ou inventado, e nunca aprende, pela resposta, se
o id existe.

## Tabela de códigos

| Código | Cenário |
| --- | --- |
| `200` | Revisão aplicada; corpo traz a solicitação com o `status` atualizado. |
| `401` | JWT ausente, inválido ou expirado. |
| `403` | Revisor não é `admin`, ou é `admin` revisando a própria solicitação. |
| `404` | Id de solicitação inexistente. |
| `422` | `status` fora de `{approved, rejected}`, `reason` ausente ao rejeitar, ou a solicitação já está no status alvo. |

## Fluxos alternativos e erros

- Se o JWT estiver ausente, inválido ou expirado, a API responde `401`.
- Se o usuário autenticado não for `admin`, a API responde `403` sem consultar
  o banco.
- Se o ID não existir, a API responde `404` com `Refund not found`.
- Se a solicitação pertencer ao próprio revisor, a API responde `403` com
  `You cannot review your own refund`.
- Se `status` não estiver em `{approved, rejected}`, a API responde `422`.
- Se `status` for `rejected` sem `reason`, a API responde `422`.
- Se a solicitação já estiver no status informado, a API responde `422` com
  `Refund is already {status}`.

## Pós-condições

- Em caso de sucesso, `Refund.status` reflete a decisão e uma nova linha em
  `RefundReview` registra `from_status`, `to_status`, `reviewer_id` e, quando
  aplicável, `reason`.
- Em caso de erro, nenhum dado é alterado.

## Regras relacionadas

- [BR-006](../business-rules.md#br-006--autenticação-das-operações-de-reembolso)
- [BR-012](../business-rules.md#br-012--escopo-de-acesso-por-papel)
- [BR-013](../business-rules.md#br-013--recurso-inexistente-ou-alheio)
- [BR-016](../business-rules.md#br-016--segregação-de-funções-na-revisão)
- [BR-017](../business-rules.md#br-017--transições-de-status-permitidas)

## Evidências

- `src/main/routes/refund_routes.py` protege e expõe
  `PATCH /refunds/{refund_id}/status`.
- `src/views/refund_reviewer_view.py` chama o validator antes do controller;
  `src/views/refund_reviewer_view_test.py::test_invalid_status_short_circuits_before_the_controller`
  comprova que um corpo inválido nunca chega a invocar o controller.
- `src/validators/refund_reviewer_validator.py` restringe `status` a
  `{approved, rejected}` e exige `reason` ao rejeitar.
- `src/controllers/refund_reviewer_controller.py` aplica a ordem das
  checagens, atualiza o status e insere a revisão numa única transação.
- `src/models/settings/unit_of_work.py` delimita a transação que cobre a
  atualização do status e a inserção da revisão.
- `src/models/repositories/refund_reviews_repository.py` insere a linha de
  histórico em `refund_reviews`.
