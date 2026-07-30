# Modelo de domínio

O modelo atual representa usuários e suas solicitações de reembolso. Os nomes
dos campos abaixo correspondem aos dados persistidos pela API.

## User

| Campo | Descrição |
| --- | --- |
| `id` | Identificador único do usuário. |
| `name` | Nome do usuário. |
| `email` | E-mail único usado na conta. |
| `password` | Senha armazenada de forma protegida. |
| `role` | Papel de acesso do usuário. |
| `avatar_filename` | Nome do arquivo da foto de perfil; nulo quando o usuário usa o avatar padrão. |
| `created_at` | Data e hora de criação do usuário. |

## Refund

| Campo | Descrição |
| --- | --- |
| `id` | Identificador único da solicitação. |
| `user_id` | Identificador do usuário proprietário. |
| `name` | Nome ou descrição curta da despesa. |
| `category` | Categoria da despesa. |
| `amount_in_cents` | Valor monetário inteiro em centavos. |
| `filename` | Nome do arquivo de comprovante de despesa armazenado. |
| `payment_filename` | Nome do arquivo de comprovante de pagamento armazenado; nulo até a solicitação ser paga (BR-022). |
| `status` | Estado da solicitação: `pending`, `approved`, `paid` ou `rejected`. |
| `created_at` | Data e hora de criação da solicitação. |

## RefundReview

Apesar do nome — tanto do conceito de domínio quanto da tabela
`refund_reviews` que o persiste — esta entidade deixou de guardar somente
revisões a partir do ciclo de pagamento: a transição `approved → paid`
(UC-012) também grava uma linha aqui, com `reviewer_id` igual a quem pagou e
`reason` nulo, mesmo pagar sendo um fato e não uma decisão de revisor. Na
prática, `RefundReview` é hoje um **log de transição de status**, não só de
revisões. Renomear a tabela custaria uma migration e a reescrita das
camadas que a referenciam; a decisão foi manter o nome e documentar aqui a
imprecisão, em vez de pagar esse custo.

| Campo | Descrição |
| --- | --- |
| `id` | Identificador único da linha. |
| `refund_id` | Identificador da solicitação afetada. |
| `reviewer_id` | Identificador do usuário `admin` que tomou a decisão ou efetuou o pagamento. |
| `from_status` | Status da solicitação antes da transição. |
| `to_status` | Status da solicitação depois da transição (`approved`, `rejected` ou `paid`). |
| `reason` | Motivo da decisão; obrigatório quando `to_status` é `rejected`. Sempre nulo quando `to_status` é `paid`. |
| `created_at` | Data e hora em que a transição foi registrada. Para `to_status = "paid"`, é também a data do pagamento — não existe uma coluna `paid_at` separada. |

## Relação

```text
User 1 ---- 0..* Refund
Refund 1 ---- 0..* RefundReview
```

Um usuário pode não possuir solicitações ou possuir várias. Cada solicitação
pertence a exatamente um usuário. Cada solicitação pode acumular zero ou várias
revisões — uma por decisão tomada sobre ela — e cada revisão pertence a
exatamente uma solicitação.

## Invariantes

- O e-mail de `User` é único (`BR-002`).
- O cadastro público cria `User` com `role` igual a `standard` (`BR-003`).
- `Refund.category` aceita somente `food`, `lodging`, `transport`, `service` ou
  `others` (`BR-008`).
- `Refund.amount_in_cents` representa em um inteiro o valor recebido em reais
  convertido para centavos (`BR-010`).
- Todo `Refund` possui um `user_id` obrigatório, obtido do usuário autenticado
  que criou a solicitação (`BR-011`).
- Somente `admin` decide sobre uma solicitação, ou a paga, e nunca sobre uma de
  sua própria autoria (`BR-016`).
- A partir de `pending`, `Refund.status` só transiciona para `approved` ou
  `rejected` por revisão; uma decisão já tomada pode ser trocada pela outra,
  mas nunca retorna a `pending` (`BR-017`). `paid`, alcançado somente por
  `POST /refunds/{refund_id}/payment`, é terminal por decisão — ver a
  lacuna conhecida na implementação atual, documentada em
  [UC-007](use-cases/UC-007-review-refund.md#nota-paid-como-status-de-origem-lacuna-conhecida).
- `Refund.status` aceita `paid` como quarto valor sem migration de schema: a
  coluna é um `String` livre, sem `ENUM` nem `CHECK` no banco — a lista de
  valores válidos vive inteiramente na camada de aplicação, para os quatro
  status igualmente.
- `status == "paid"` implica a existência de um comprovante de pagamento
  (`payment_filename` preenchido), porque o arquivo é gravado antes da
  transição e nunca depois dela (`BR-022`).
