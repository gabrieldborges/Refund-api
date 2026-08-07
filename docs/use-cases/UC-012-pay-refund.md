# UC-012 — Pagar solicitação de reembolso

> **Amendamento (2026-08-07, Item 22).** Esta rota **não devolve mais o corpo
> binário**. Ela devolve `{"url": "..."}` — uma URL assinada, de vida curta
> (`FILE_URL_TTL_SECONDS`, padrão 300s), que o navegador busca diretamente. O
> motivo é que uma tag `<img>` não sabe enviar `Authorization: Bearer`, o que
> obrigava o cliente a baixar cada arquivo por XHR e montar um Blob.
>
> O `media_type` continua derivado da extensão armazenada, **nunca** de um
> cabeçalho do cliente. Ele fica na resposta porque o cliente precisa escolher
> entre `<img>` e `<object>` antes de buscar. O `Content-Type` real dos bytes é
> definido onde eles são servidos:
> `GET /files/{storage}/{filename}` com o backend local, os metadados do objeto
> com S3.
>
> **A autorização não mudou de lugar:** as regras descritas abaixo continuam
> sendo aplicadas antes de qualquer URL ser gerada. O que muda é que a decisão
> passa a valer pelo prazo do link, em vez de ser reconferida a cada
> requisição. Ver [ADR-003](../decisions/ADR-003-local-receipt-storage.md).
>
> **Um caminho de erro mudou de lugar:** "o arquivo sumiu do disco" deixa de
> ser 404 aqui e passa a aparecer quando o navegador segue a URL. Os 404 de
> "não existe" e "não é seu" seguem idênticos e inalterados.



## Ator principal

Usuário autenticado com papel `admin`. Ainda não há tela dedicada no
frontend; o caso de uso é exercido diretamente sobre a API.

## Objetivo

Registrar que uma solicitação `approved` foi paga, anexando o comprovante de
pagamento obrigatório, e transicionar `Refund.status` para `paid`.

## Pré-condições

- O usuário possui um JWT válido com `role` igual a `admin`.
- A solicitação a pagar já existe, está com `status = "approved"` e pertence
  a outro usuário que não o pagador.

## Fluxo principal

1. O cliente envia `POST /refunds/{refund_id}/payment` como
   `multipart/form-data`, com o campo `file` contendo o comprovante de
   pagamento.
2. A API valida o arquivo (extensão e tamanho) antes de invocar o controller.
3. A API verifica o papel do requisitante antes de qualquer consulta ao
   banco.
4. A API busca a solicitação pelo ID **sem lock** (`select_refund_by_id`); se
   existir, verifica se ela pertence a outro usuário que não o pagador, e se
   seu status atual é `approved`.
5. A API salva o arquivo no disco (diretório `PAYMENT_DIR`) e, em seguida,
   tenta um `UPDATE` condicional (`status='paid'` somente se
   `status='approved'` ainda) e a inserção de uma linha em `RefundReview`
   (`from_status: "approved"`, `to_status: "paid"`, `reason: null`), tudo em
   uma única transação (`UnitOfWork`).
6. Se o `UPDATE` afetar zero linhas — outro admin pagou entre a leitura do
   passo 4 e a escrita deste passo — a API apaga o arquivo recém-salvo como
   compensação e responde `422`.
7. Em caso de sucesso, a API relê a solicitação e devolve o resultado de
   `serialize_refund`, com `status: "paid"`.

## Corpo da requisição

| Campo | Obrigatório | Descrição |
| --- | --- | --- |
| `file` | Sim | Comprovante de pagamento; JPG, PNG ou PDF, até 4MB (BR-009 emendada). |

## Ordem das checagens

A ordem abaixo não é arbitrária — cada checagem só é feita depois que a
anterior passou, espelhando a disciplina de UC-007:

1. **Arquivo (validator).** `src/views/refund_payer_view.py` chama
   `refund_payer_validator` antes mesmo de invocar o controller. Arquivo
   ausente, extensão fora de `{jpg, jpeg, png, pdf}` ou acima de 4MB
   responde `422` sem que o controller — e, portanto, o banco — seja tocado.
2. **Papel do pagador.** É a primeira verificação feita pelo controller,
   antes de qualquer consulta ao banco. Um usuário `standard` recebe `403`
   para qualquer id, exista ele ou não — a checagem que nunca consulta o
   banco não pode revelar se um id é real, o mesmo raciocínio
   anti-enumeração por trás do `404` da BR-013 e da ordem de checagens do
   UC-007.
3. **Existência da solicitação.** Só é consultada depois que o papel já foi
   confirmado como `admin`. Id inexistente responde `404`.
4. **Autoria da solicitação.** Um `admin`, pela BR-012, já pode ver qualquer
   solicitação — não há mais nada a esconder nesse ponto, então recusar o
   pagamento da própria solicitação com `403` (BR-016 estendida) não vaza
   informação nova.
5. **Status atual.** Diferente de `approved` responde `422` — uma
   solicitação `pending` ainda não foi decidida, e uma `rejected` não deve
   nada.
6. **Escrita e corrida.** O arquivo vai para o disco primeiro. O `UPDATE`
   condicional (passo 6 do fluxo principal) fecha a corrida contra outro
   pagamento concorrente sem tomar lock; zero linhas afetadas apaga o
   arquivo recém-gravado e responde `422`.

A propriedade de segurança preservada é a mesma do UC-007: **nenhum acesso
ao banco acontece antes da checagem de papel**, então a resposta a um
`standard` nunca revela se um id existe.

## Formato da resposta

Ao contrário do `PATCH /refunds/{refund_id}/status` (UC-007), que lê
`RefundStatusRepository.select_for_update` e produz o formato plano e
divergente documentado ali, esta resposta **relê a linha gravada e usa
`serialize_refund`** — o mesmo serializador compartilhado por UC-003, UC-004
e UC-005. Isso é deliberado: a superfície nova nasce com a forma
compartilhada (`user` aninhado com `has_avatar`, sem `filename`), em vez de
repetir a divergência de formato que o `PATCH /status` já carrega como
pendência conhecida.

**Nenhuma resposta ganha `has_payment_receipt`.** Como o comprovante de
pagamento é obrigatório para alcançar `paid` (BR-022), `status == "paid"` já
informa que o comprovante existe — é o oposto de `has_avatar`, que existe
justamente porque o avatar é opcional.

## Tabela de códigos

| Código | Cenário |
| --- | --- |
| `200` | Pago; corpo traz a solicitação com `status: "paid"`. |
| `401` | JWT ausente, inválido ou expirado. |
| `403` | Requisitante não é `admin`, ou é `admin` pagando a própria solicitação. |
| `404` | Id de solicitação inexistente. |
| `422` | Arquivo ausente/inválido/grande, status atual diferente de `approved`, ou outro admin pagou a solicitação entre a leitura e a escrita. |

## Fluxos alternativos e erros

- Se o JWT estiver ausente, inválido ou expirado, a API responde `401`.
- Se o arquivo estiver ausente, tiver extensão fora de `{jpg, jpeg, png,
  pdf}` ou exceder 4MB, a API responde `422` sem tocar o banco.
- Se o usuário autenticado não for `admin`, a API responde `403` com `Only
  administrators can pay refunds`, sem consultar o banco.
- Se o ID não existir, a API responde `404` com `Refund not found`.
- Se a solicitação pertencer ao próprio pagador, a API responde `403` com
  `You cannot pay your own refund`.
- Se o status atual não for `approved`, a API responde `422` com `Only an
  approved refund can be paid`.
- Se outro admin pagar a mesma solicitação entre a leitura de guarda e a
  escrita, a API responde o mesmo `422` de "Only an approved refund can be
  paid", e o arquivo recém-salvo é apagado como compensação.

## Pós-condições

- Em caso de sucesso, `Refund.status` passa a `"paid"`,
  `Refund.payment_filename` recebe o nome do arquivo salvo, e uma nova linha
  em `RefundReview` registra `from_status: "approved"`, `to_status: "paid"`,
  `reviewer_id` igual ao pagador e `reason: null`.
- Em caso de erro antes da escrita no disco, nenhum dado é alterado.
- Em caso de corrida perdida (zero linhas afetadas pelo `UPDATE`), o arquivo
  gravado no passo anterior é removido; nenhuma linha de `RefundReview` é
  inserida.
- **Limite conhecido, não resolvido por este ciclo:** um crash entre o
  `save` do arquivo e o `UPDATE` ainda deixa um arquivo órfão no disco — o
  `UnitOfWork` delimita a transação do banco, e o sistema de arquivos não
  participa dela. Mesma fragilidade que a criação de reembolso já tem
  (Item 21 do learning path, não resolvido aqui).

## Regras relacionadas

- [BR-006](../business-rules.md#br-006--autenticação-das-operações-de-reembolso)
- [BR-009](../business-rules.md#br-009--formato-e-tamanho-do-comprovante)
- [BR-012](../business-rules.md#br-012--escopo-de-acesso-por-papel)
- [BR-016](../business-rules.md#br-016--segregação-de-funções-na-revisão)
- [BR-017](../business-rules.md#br-017--transições-de-status-permitidas)
- [BR-022](../business-rules.md#br-022--comprovante-de-pagamento-obrigatório)

## Evidências

- `src/main/routes/refund_routes.py` protege e expõe
  `POST /refunds/{refund_id}/payment`, declarada antes de
  `GET /refunds/{refund_id}` na ordenação do arquivo.
- `src/validators/refund_payer_validator.py` restringe extensão e tamanho do
  arquivo, e valida por extensão, nunca pelo `Content-Type` enviado pelo
  cliente; `src/validators/refund_payer_validator_test.py` cobre extensões
  aceitas, extensão inválida, arquivo ausente e os dois limites de tamanho.
- `src/views/refund_payer_view.py` chama o validator antes do controller;
  `src/views/refund_payer_view_test.py::test_invalid_file_short_circuits_before_the_controller`
  comprova que um arquivo inválido nunca chega a invocar o controller.
- `src/controllers/refund_payer_controller.py` aplica a ordem das checagens
  acima e coordena arquivo + transação;
  `src/controllers/refund_payer_controller_test.py::test_standard_user_is_forbidden_and_the_database_is_never_touched`
  comprova que o papel é checado antes de qualquer consulta;
  `::test_admin_cannot_pay_their_own_refund` comprova BR-016 estendida;
  `::test_a_lost_race_deletes_the_file_it_had_written` comprova a
  compensação da corrida perdida.
- `src/models/repositories/refund_status_repository.py::mark_as_paid` aplica
  o `UPDATE` condicional;
  `src/models/repositories/refund_status_repository_test.py::test_mark_as_paid_only_touches_a_refund_still_approved`
  e `::test_mark_as_paid_reports_zero_when_the_status_already_changed`
  comprovam a condição e o retorno de linhas afetadas.
- `src/models/settings/unit_of_work.py` delimita a transação que cobre o
  `UPDATE` de status e a inserção da revisão.
- `src/controllers/refund_serializer.py` produz a resposta de sucesso, sem
  `filename` nem `payment_filename`.
- `src/main/composer/refund_payer_composer.py` monta `FileStorage` apontando
  para `upload_info["PAYMENT_DIR"]`.
- `src/configs/global_config.py` define `PAYMENT_DIR` (padrão
  `uploads/payment_receipts`) e o limite compartilhado
  `MAX_FILE_SIZE_BYTES`.
