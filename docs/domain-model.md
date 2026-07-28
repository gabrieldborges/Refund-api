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
| `created_at` | Data e hora de criação do usuário. |

## Refund

| Campo | Descrição |
| --- | --- |
| `id` | Identificador único da solicitação. |
| `user_id` | Identificador do usuário proprietário. |
| `name` | Nome ou descrição curta da despesa. |
| `category` | Categoria da despesa. |
| `amount_in_cents` | Valor monetário inteiro em centavos. |
| `filename` | Nome do arquivo de comprovante armazenado. |
| `status` | Estado da solicitação: `pending`, `approved` ou `rejected`. |
| `created_at` | Data e hora de criação da solicitação. |

## RefundReview

| Campo | Descrição |
| --- | --- |
| `id` | Identificador único da revisão. |
| `refund_id` | Identificador da solicitação revisada. |
| `reviewer_id` | Identificador do usuário `admin` que tomou a decisão. |
| `from_status` | Status da solicitação antes da decisão. |
| `to_status` | Status da solicitação depois da decisão (`approved` ou `rejected`). |
| `reason` | Motivo da decisão; obrigatório quando `to_status` é `rejected`. |
| `created_at` | Data e hora em que a decisão foi registrada. |

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
- Somente `admin` decide sobre uma solicitação, e nunca sobre uma de sua própria
  autoria (`BR-016`).
- A partir de `pending`, `Refund.status` só transiciona para `approved` ou
  `rejected`; uma decisão já tomada pode ser trocada pela outra, mas nunca
  retorna a `pending` (`BR-017`).
