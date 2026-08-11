# UC-016 — Consultar usuário

## Ator principal

Usuário autenticado com papel `admin`.

## Objetivo

Obter os dados públicos de um usuário específico, para a página daquela pessoa na
tela de Time — onde o administrador vê a identidade dela ao lado do histórico de
solicitações (UC-014 e UC-004).

## Pré-condições

- O usuário possui um JWT válido.
- O papel registrado no JWT é `admin`.

## Fluxo principal

1. O cliente envia `GET /users/{user_id}` com o JWT no cabeçalho
   `Authorization: Bearer`.
2. A API autentica o usuário e verifica o papel; se não for `admin`, responde
   `404` **antes de qualquer acesso ao banco**.
3. A API busca o usuário por `id`; se não existir, responde `404` com a **mesma**
   mensagem do passo anterior.
4. A API serializa a linha na forma pública do usuário.

## Resposta

```json
{
  "type": "User",
  "count": 1,
  "attributes": {
    "id": 7,
    "name": "Ana",
    "email": "ana@example.com",
    "role": "standard",
    "has_avatar": false,
    "created_at": "2026-01-01T12:00:00"
  }
}
```

Mesma forma pública de UC-015, pelo mesmo `serialize_user` — os dois casos de uso
produzem a mesma forma a partir da mesma fonte, e duas cópias dessa montagem é
como uma delas mantém um campo que a outra removeu. Aqui o campo em risco é o
`password`.

## Autorização

- `admin`: acesso permitido a qualquer usuário.
- Usuário `standard`: acesso negado com `404`, **não** `403` (BR-025), pelo mesmo
  raciocínio anti-enumeração da BR-013 e de UC-014 — um `403` confirmaria que
  aquele `user_id` existe a quem não pode saber.

**A mensagem dos dois `404` é idêntica byte a byte**, e isso é requisito, não
detalhe: uma mensagem mais útil em um dos casos desfaria a razão de responder
`404` em vez de `403`.

## Tabela de códigos

| Código | Cenário |
| --- | --- |
| `200` | Usuário devolvido. |
| `401` | JWT ausente, inválido ou expirado. |
| `404` | Usuário `standard`, **ou** `user_id` inexistente. Indistinguíveis. |
| `422` | `user_id` não numérico. |

## Fluxos alternativos e erros

- Se o JWT estiver ausente, inválido ou expirado, a API responde `401`.
- Se o `user_id` não for um inteiro, a validação nativa do FastAPI responde
  `422` — antes de qualquer checagem de papel.
- Um `admin` consultando um `user_id` inexistente recebe `404`. Diferente de
  UC-014, que não checa existência, esta rota **checa**: ela busca a linha e não
  tem o que devolver sem ela.

## Limitação conhecida

**O papel vem do JWT e não é reconsultado no banco**, com a mesma consequência
descrita em UC-015.

## Pós-condições

- Nenhum dado é alterado.

## Regras relacionadas

- [BR-025](../business-rules.md#br-025--acesso-ao-diretório-de-usuários)
- [BR-013](../business-rules.md#br-013--recurso-inexistente-ou-alheio)

## Evidências

- `src/main/routes/user_routes.py` expõe `GET /users/{user_id}` após as rotas
  mais específicas do mesmo prefixo;
  `src/main/routes/user_routes_test.py::test_the_detail_route_does_not_shadow_the_avatar_route`
  e `::test_the_detail_route_does_not_shadow_the_refund_stats_route` comprovam que
  as duas anteriores continuam alcançando os próprios composers.
- `src/views/user_finder_view.py` extrai `user_id` do path e `role` do token.
- `src/controllers/user_finder_controller.py` aplica os dois `404`;
  `src/controllers/user_finder_controller_test.py::test_a_standard_user_gets_not_found`
  e `::test_a_missing_user_gets_not_found` comprovam que as mensagens coincidem,
  e `::test_the_repository_is_never_reached_for_a_standard_user` que a recusa
  acontece antes do banco.
- `src/models/repositories/users_repository.py::select_user_by_id` já existia e
  foi reaproveitado.
- `contract/users.json` registra a resposta real.
