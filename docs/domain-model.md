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
| `created_at` | Data e hora de criação da solicitação. |

## Relação

```text
User 1 ---- 0..* Refund
```

Um usuário pode não possuir solicitações ou possuir várias. Cada solicitação
pertence a exatamente um usuário.

## Invariantes

- O e-mail de `User` é único (`BR-002`).
- O cadastro público cria `User` com `role` igual a `standard` (`BR-003`).
- `Refund.category` aceita somente `food`, `lodging`, `transport`, `service` ou
  `others` (`BR-008`).
- `Refund.amount_in_cents` representa em um inteiro o valor recebido em reais
  convertido para centavos (`BR-010`).
- Todo `Refund` possui um `user_id` obrigatório, obtido do usuário autenticado
  que criou a solicitação (`BR-011`).

## Limites do modelo atual

O modelo atual não possui status, aprovação, rejeição ou histórico de
transições. Portanto, uma solicitação representa apenas o registro da despesa e
de seu comprovante, sem fluxo de análise ou mudança de estado.

**Evidências:** `src/models/entities/users.py`,
`src/models/entities/refunds.py`, `src/controllers/user_register_controller.py`
e `src/controllers/refund_creator_controller.py`.
