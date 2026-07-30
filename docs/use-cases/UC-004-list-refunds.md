# UC-004 — Listar solicitações de reembolso

## Ator principal

Usuário autenticado, com papel `standard` ou `admin`.

## Objetivo

Consultar uma página de solicitações, opcionalmente filtrada por parte do
nome, por `status`, e ordenada pelo campo escolhido.

## Pré-condições

- O usuário possui um JWT válido.
- O usuário está em uma área protegida do frontend.

## Fluxo principal

1. O frontend solicita `GET /refunds` com `page`, `per_page` e, opcionalmente,
   `name`, `status`, `sort`, `order` e `user_id`.
2. A API valida `page >= 1` e `1 <= per_page <= 100`, e que `status`, `sort` e
   `order`, quando informados, pertencem às listas de valores aceitos.
3. Para um usuário `standard`, a API limita a consulta às solicitações cujo
   `user_id` corresponde ao token; para um `admin`, não aplica esse filtro.
4. Quando `name` é informado, a API busca correspondências parciais sem
   diferenciar maiúsculas de minúsculas. Quando `status` é informado, a API
   restringe o resultado às solicitações naquele status.
5. A API ordena os resultados pelo campo de `sort` (`created_at` por padrão) na
   direção de `order` (`desc` por padrão) e aplica limite e deslocamento da
   página.
6. A API devolve os itens — cada um com seu `status` (`pending`, `approved`,
   `paid` ou `rejected`) e o objeto `user` (`id`, `name`, `has_avatar`) do solicitante,
   sem `user_id` no topo e sem o nome do arquivo de comprovante — e os
   metadados `count`, `total`, `sum_amount_in_cents`, `page`, `per_page` e
   `total_pages`; o frontend apresenta a lista e os controles de paginação.
   O comprovante de cada item, quando aberto, é obtido em
   `GET /refunds/{refund_id}/receipt`; a foto do solicitante, quando
   `has_avatar` é verdadeiro, em `GET /users/{user_id}/avatar`.

`status` aceita `pending`, `approved`, `paid` ou `rejected`. `sort` aceita
`created_at`, `amount_in_cents`, `name` ou `status`. `order` aceita `asc` ou
`desc`.

`user_id` restringe a listagem a um solicitante específico, mas só tem
efeito para `admin`: para um usuário `standard`, a API **ignora** o
parâmetro — o filtro por usuário já está fixado no próprio token pela
BR-012, então não há nada a vazar e nenhum caminho de erro novo nasce dessa
combinação. Diferente de `status`, `sort` e `order`, `user_id` não tem uma
lista de valores aceitos para validar: é tipado como inteiro na própria
rota, e a validação nativa do FastAPI já rejeita um valor que não seja um
número.

`sum_amount_in_cents` é a soma, em centavos, de todos os reembolsos que casam
o filtro — respeitando a mesma regra de autorização da listagem (admin vê
todos; usuário comum, apenas os seus) e o mesmo `status`, quando informado.
Junto com `total`, o valor cobre o conjunto filtrado inteiro, não apenas os
itens da página atual — ambos mudam conforme `status` restringe o conjunto.

## Fluxos alternativos e erros

- Se o JWT estiver ausente, inválido ou expirado, a API responde `401`.
- Se `page` for menor que 1, ou `per_page` estiver fora do intervalo de 1 a
  100, a validação da rota rejeita a requisição.
- Se `status` não for `pending`, `approved`, `paid` ou `rejected`, a API
  responde `422`.
- Se `sort` não for `created_at`, `amount_in_cents`, `name` ou `status`, a API
  responde `422`.
- Se `order` não for `asc` ou `desc`, a API responde `422`.
- Se nenhum item corresponder ao escopo e à busca, a API devolve lista vazia e
  o frontend informa que nenhuma solicitação foi encontrada.
- Se a requisição falhar, o frontend informa que não foi possível carregar as
  solicitações.

> **Mudança de contrato:** a resposta não traz mais `user_id` no topo de cada
> item, nem o nome do arquivo de comprovante; o solicitante agora vem em
> `user.id`, ao lado de `user.name` e `user.has_avatar`. Isso quebra nos dois
> sentidos com o frontend anterior, então backend e frontend precisam ser
> implantados juntos.

## Pós-condições

- Nenhuma solicitação é alterada.
- O usuário vê somente os itens permitidos por seu papel, na página solicitada
  e na ordem de `sort`/`order` pedida (por padrão, `created_at` decrescente).

## Regras relacionadas

- [BR-006](../business-rules.md#br-006--autenticação-das-operações-de-reembolso)
- [BR-012](../business-rules.md#br-012--escopo-de-acesso-por-papel)
- [BR-014](../business-rules.md#br-014--ordem-e-busca-da-listagem)
- [BR-017](../business-rules.md#br-017--transições-de-status-permitidas)
- [BR-020](../business-rules.md#br-020--acesso-ao-comprovante)
- [BR-021](../business-rules.md#br-021--acesso-à-foto-de-perfil)

## Evidências

- `src/main/routes/refund_routes.py` protege `GET /refunds` e define os limites
  de `page` e `per_page`, os filtros opcionais `name`, `status`, `sort` e
  `order`, e o filtro `user_id` (tipado como `Optional[int]`, sem lista de
  valores a validar).
- `src/validators/refund_lister_validator.py` restringe `status`, `sort` e
  `order` às respectivas listas de valores aceitos e responde `422` fora
  delas — a primeira das duas barreiras contra um nome de coluna vindo do
  cliente.
- `src/views/refund_lister_view.py` repassa o `user_id` da query ao
  controller como `filter_user_id`, distinto do `user_id` do token.
- `src/controllers/refund_lister_controller.py` distingue `admin` de
  `standard`, calcula os metadados da paginação e usa
  `src/controllers/refund_serializer.py` para produzir cada item sem
  `filename` e com `user.has_avatar`. Decide `filter_user_id` só para
  `admin`; para `standard`, sempre usa o `user_id` do próprio token, mesmo
  que `filter_user_id` tenha sido informado.
  `src/controllers/refund_lister_controller_test.py::test_admin_can_filter_the_list_by_requester`
  e `::test_the_filter_is_ignored_for_a_standard_user` cobrem os dois casos.
- `src/models/repositories/refunds_repository.py` aplica o filtro parcial
  `ilike`, o filtro por `status`, o escopo por usuário, a ordenação por
  `sort`/`order` (com `created_at` decrescente como padrão) e a paginação, e
  calcula `total` e `sum_amount_in_cents` numa única consulta sobre o mesmo
  filtro. A coluna de ordenação vem de um dicionário fixo indexado pelo nome
  recebido — a segunda barreira: um `sort` desconhecido não produz coluna
  nenhuma, então nenhuma string da requisição chega a um `ORDER BY`.
- `../Refund-FrontEnd/src/features/refunds/hooks/useRefunds.ts` envia página, tamanho e busca;
  `../Refund-FrontEnd/src/pages/PageHome.tsx` reinicia a página ao buscar e
  apresenta resultados, estado vazio e controles de paginação.
