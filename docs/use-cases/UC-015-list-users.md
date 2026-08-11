# UC-015 — Listar usuários

## Ator principal

Usuário autenticado com papel `admin`.

## Objetivo

Obter uma página dos usuários cadastrados, opcionalmente filtrada por nome, para
alimentar a tela de Time — a lista que permite ao administrador saber quem usa o
sistema.

## Pré-condições

- O usuário possui um JWT válido.
- O papel registrado no JWT é `admin`.

## Fluxo principal

1. O cliente envia `GET /users` com o JWT no cabeçalho
   `Authorization: Bearer`, opcionalmente com `page`, `per_page` e `name`.
2. A API autentica o usuário e verifica o papel; se não for `admin`, responde
   `403` **antes de qualquer acesso ao banco**.
3. A API conta os usuários que casam com o filtro e busca a página pedida, com
   os dois valores derivados dos **mesmos** filtros.
4. A API ordena por `name` ascendente, com `id` ascendente como desempate.
5. A API serializa cada linha na forma pública do usuário e monta o envelope
   com os metadados de paginação.

## Parâmetros

| Parâmetro | Padrão | Faixa | Efeito |
| --- | --- | --- | --- |
| `page` | `1` | `>= 1` | Deslocamento da página. |
| `per_page` | `10` | `1`–`100` | Tamanho da página. |
| `name` | ausente | texto livre | Casamento parcial e case-insensitive sobre `name`. Vazio equivale a ausente. |

**Não há `sort` nem `order`.** A ordenação é fixa, e por isso esta fatia não tem
validator: os limites de `page` e `per_page` são impostos pela declaração
`Query(ge=..., le=...)` do FastAPI, e não existe conjunto de valores permitidos a
expressar. Um validator aqui duplicaria o que o framework já recusa.

## Resposta

```json
{
  "type": "User",
  "count": 2,
  "total": 2,
  "page": 1,
  "per_page": 10,
  "total_pages": 1,
  "attributes": [
    {
      "id": 1,
      "name": "Ana",
      "email": "ana@example.com",
      "role": "standard",
      "has_avatar": false,
      "created_at": "2026-01-01T12:00:00"
    },
    {
      "id": 2,
      "name": "Chefe",
      "email": "chefe@example.com",
      "role": "admin",
      "has_avatar": false,
      "created_at": "2026-01-01T12:00:00"
    }
  ]
}
```

**A resposta não contém `password`.** A tabela `users` guarda o hash bcrypt na
mesma linha que o nome e o e-mail, então a forma pública é montada campo a campo
por `serialize_user`, em vez de a linha ser devolvida sem algumas chaves. A
diferença importa: apagando chaves, uma coluna adicionada a `users` no futuro
passaria a vazar sozinha.

`has_avatar` é booleano derivado de `avatar_filename`. O cliente só precisa saber
se mostra uma foto ou as iniciais; a imagem vem de `GET /users/{user_id}/avatar`
(UC-011).

`total_pages` é `0`, e não `1`, quando não há nenhum usuário — "nenhuma página"
não é a mesma afirmação que "uma página vazia".

## Autorização

- `admin`: acesso permitido.
- Usuário `standard`: acesso negado com `403`, **não** `404` (BR-025). Uma
  listagem não revela nada sobre um `id` em particular, então pode ser honesta
  sobre a falta de permissão.

## Tabela de códigos

| Código | Cenário |
| --- | --- |
| `200` | Página devolvida, possivelmente vazia. |
| `401` | JWT ausente, inválido ou expirado. |
| `403` | Usuário `standard`. |
| `422` | `page` menor que 1, ou `per_page` fora de `1`–`100`. |

## Fluxos alternativos e erros

- Se o JWT estiver ausente, inválido ou expirado, a API responde `401`.
- Se o filtro `name` não casar com ninguém, a API responde `200` com
  `attributes` vazio, `total` igual a `0` e `total_pages` igual a `0` — não é um
  erro.
- Se `page` apontar além da última página, a API responde `200` com `attributes`
  vazio e `page` igual ao valor pedido: uma página além do fim está vazia, mas
  continua sendo a página N.

## Limitação conhecida

**O papel vem do JWT e não é reconsultado no banco.** Um usuário promovido a
`admin` enquanto está autenticado só passa a ser aceito aqui no próximo login,
porque `get_current_user` lê as claims do token e nunca consulta `Users`. Vale
para todo o sistema; esta rota apenas torna a consequência visível.

## Pós-condições

- Nenhum dado é alterado.

## Regras relacionadas

- [BR-025](../business-rules.md#br-025--acesso-ao-diretório-de-usuários)

## Evidências

- `src/main/routes/user_routes.py` expõe `GET /users` com os limites de
  `page` e `per_page`; `src/main/routes/user_routes_test.py::test_the_listing_route_rejects_out_of_range_pagination`
  comprova o `422`.
- `src/views/user_lister_view.py` extrai `role` do token e repassa ao
  controller, sem validator, com a razão registrada no próprio arquivo.
- `src/controllers/user_lister_controller.py` aplica o `403`;
  `src/controllers/user_lister_controller_test.py::test_the_repository_is_never_reached_for_a_standard_user`
  comprova que a recusa acontece antes do banco.
- `src/controllers/user_serializer.py` monta a forma pública;
  `src/controllers/user_serializer_test.py::test_the_password_is_absent_from_the_serialized_user`
  e `::test_only_the_public_fields_are_exposed` comprovam a ausência do hash.
- `src/models/repositories/users_repository.py::select_users` executa a contagem
  e a página; `users_repository_test.py::test_select_users_orders_by_name_with_id_as_the_tiebreaker`
  e `::test_select_users_counts_with_the_same_filter_as_the_page` cobrem a
  ordenação e o filtro.
- `contract/users.json` registra a resposta real, capturada por
  `src/test_integration/contract_test.py`.
