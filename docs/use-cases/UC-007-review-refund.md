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
4. A API verifica, nesta ordem: se o status atual da solicitação já é `paid`
   (terminal, recusado com `422`) e, em seguida, se o status atual é
   diferente do status alvo (repetir a decisão vigente também é recusado
   com `422`).
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
5. **Transição de status.** Duas checagens distintas, nesta ordem:
   1. **`paid` é terminal (BR-017 emendada).** Se o status atual já é
      `paid`, a revisão é recusada com `422` e a mensagem `Refund is
      already paid and cannot be reviewed` — o dinheiro já se moveu, então
      nenhuma revisão pode tirar a solicitação desse estado. Esta checagem é
      independente da seguinte, não uma dependência de ordem: como o
      validator já restringe o alvo a `{approved, rejected}`, as duas
      condições nunca são verdadeiras ao mesmo tempo — `paid` nunca é um
      alvo válido de revisão. Ela vem primeiro só porque produz a mensagem
      mais clara para uma solicitação paga.
   2. **Repetir a decisão vigente** (`current_status == status`) é recusado
      com `422` e a mensagem `Refund is already {status}`, porque não há
      mudança de estado a registrar. As duas checagens têm mensagens
      diferentes porque significam coisas diferentes: a primeira é sobre um
      fato consumado (dinheiro pago), a segunda é sobre um não-evento
      (nenhuma mudança a registrar).
6. **Sucesso.** `200`, com a solicitação refletindo o novo `status`.

Note que a validação do corpo (passo 1) precede a checagem de papel (passo 2)
— um corpo malformado nunca chega a acessar o banco, mas também nunca chega a
saber se quem o enviou tinha permissão. A propriedade de segurança que importa
não é "papel é sempre a primeira checagem de todas", e sim que **nenhum acesso
ao banco acontece antes da checagem de papel**: por isso um `standard` recebe
o mesmo `403` para um id real ou inventado, e nunca aprende, pela resposta, se
o id existe.

## Formato da resposta (divergente das demais)

**Atenção:** ao contrário de UC-003, UC-004 e UC-005 — cujas respostas trazem
o solicitante aninhado em `user` (`{"user": {"id", "name", "has_avatar"}}`) e
nunca incluem o nome do arquivo de comprovante — a resposta deste endpoint
diverge em **três** pontos, porque lê `RefundStatusRepository.select_for_update`
em vez do serializador compartilhado (`src/controllers/refund_serializer.py`):

1. **`user_id` no nível superior**, sem objeto `user` aninhado — o formato
   **plano** da tabela `refunds`, não o formato com `user.id` das demais
   respostas.
2. **`filename` presente** — o nome do arquivo de comprovante, removido de
   toda outra resposta de reembolso, aparece aqui sem tratamento.
3. **Nenhum `has_avatar`** — e, por não haver `JOIN` com `Users`, também não
   há `user.avatar_filename` bruto: o campo simplesmente não existe nesta
   resposta.

Essa é uma inconsistência conhecida entre os endpoints que devolvem
reembolso, e permanece assim deliberadamente nesta branch: `select_for_update`
também alimenta o fluxo de aprovação (com `FOR UPDATE`), e mudar seu formato
de retorno teria efeito cascata sobre esse fluxo. É inofensiva porque a tela
de revisão planejada para o frontend refaz o `GET /refunds/{refund_id}` (que
já devolve o formato aninhado, sem `filename`, com `has_avatar`) em vez de
consumir o corpo desta resposta diretamente. Um cliente que precisasse
consumir esta resposta sem refazer o `GET` exigiria um contrato próprio para
o formato plano, com `filename` exposto e sem `has_avatar`, em vez de
reaproveitar o contrato usado para as demais respostas de reembolso.
Resolver essa divergência é um passo pendente para quando a tela de revisão
for construída no frontend.

## Tabela de códigos

| Código | Cenário |
| --- | --- |
| `200` | Revisão aplicada; corpo traz a solicitação com o `status` atualizado. |
| `401` | JWT ausente, inválido ou expirado. |
| `403` | Revisor não é `admin`, ou é `admin` revisando a própria solicitação. |
| `404` | Id de solicitação inexistente. |
| `422` | `status` fora de `{approved, rejected}`, `reason` ausente ao rejeitar, a solicitação já está paga, ou a solicitação já está no status alvo. |

## Fluxos alternativos e erros

- Se o JWT estiver ausente, inválido ou expirado, a API responde `401`.
- Se o usuário autenticado não for `admin`, a API responde `403` sem consultar
  o banco.
- Se o ID não existir, a API responde `404` com `Refund not found`.
- Se a solicitação pertencer ao próprio revisor, a API responde `403` com
  `You cannot review your own refund`.
- Se `status` não estiver em `{approved, rejected}`, a API responde `422`.
- Se `status` for `rejected` sem `reason`, a API responde `422`.
- Se a solicitação já estiver com `status = "paid"`, a API responde `422`
  com `Refund is already paid and cannot be reviewed` — `paid` é terminal
  (BR-017 emendada), então nenhum alvo é aceito nesse caso.
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
- [BR-022](../business-rules.md#br-022--comprovante-de-pagamento-obrigatório)

## Evidências

- `src/main/routes/refund_routes.py` protege e expõe
  `PATCH /refunds/{refund_id}/status`.
- `src/views/refund_reviewer_view.py` chama o validator antes do controller;
  `src/views/refund_reviewer_view_test.py::test_invalid_status_short_circuits_before_the_controller`
  comprova que um corpo inválido nunca chega a invocar o controller.
- `src/validators/refund_reviewer_validator.py` restringe `status` a
  `{approved, rejected}` e exige `reason` ao rejeitar.
- `src/controllers/refund_reviewer_controller.py` aplica a ordem das
  checagens — incluindo a checagem de terminalidade de `paid` antes da
  checagem de repetição — atualiza o status e insere a revisão numa única
  transação;
  `src/controllers/refund_reviewer_controller_test.py::test_a_paid_refund_cannot_be_reverted_to_approved`
  e `::test_a_paid_refund_cannot_be_reverted_to_rejected` comprovam a
  checagem de terminalidade nas duas direções.
- `src/models/settings/unit_of_work.py` delimita a transação que cobre a
  atualização do status e a inserção da revisão.
- `src/models/repositories/refund_reviews_repository.py` insere a linha de
  histórico em `refund_reviews`.
