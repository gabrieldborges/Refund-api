# UC-004 — Listar solicitações de reembolso

## Ator principal

Usuário autenticado, com papel `standard` ou `admin`.

## Objetivo

Consultar uma página de solicitações, opcionalmente filtrada por parte do nome.

## Pré-condições

- O usuário possui um JWT válido.
- O usuário está em uma área protegida do frontend.

## Fluxo principal

1. O frontend solicita `GET /refunds` com `page`, `per_page` e, quando houver
   busca, `name`.
2. A API valida `page >= 1` e `1 <= per_page <= 100`.
3. Para um usuário `standard`, a API limita a consulta às solicitações cujo
   `user_id` corresponde ao token; para um `admin`, não aplica esse filtro.
4. Quando `name` é informado, a API busca correspondências parciais sem
   diferenciar maiúsculas de minúsculas.
5. A API ordena os resultados de `created_at` mais recente para o mais antigo e
   aplica limite e deslocamento da página.
6. A API devolve os itens e os metadados `count`, `total`, `page`, `per_page` e
   `total_pages`; o frontend apresenta a lista e os controles de paginação.

## Fluxos alternativos e erros

- Se o JWT estiver ausente, inválido ou expirado, a API responde `401`.
- Se `page` for menor que 1, ou `per_page` estiver fora do intervalo de 1 a
  100, a validação da rota rejeita a requisição.
- Se nenhum item corresponder ao escopo e à busca, a API devolve lista vazia e
  o frontend informa que nenhuma solicitação foi encontrada.
- Se a requisição falhar, o frontend informa que não foi possível carregar as
  solicitações.

## Pós-condições

- Nenhuma solicitação é alterada.
- O usuário vê somente os itens permitidos por seu papel, na página solicitada
  e em ordem decrescente de criação.

## Regras relacionadas

- [BR-006](../business-rules.md#br-006--autenticação-das-operações-de-reembolso)
- [BR-012](../business-rules.md#br-012--escopo-de-acesso-por-papel)
- [BR-014](../business-rules.md#br-014--ordem-e-busca-da-listagem)

## Evidências

- `src/main/routes/refund_routes.py` protege `GET /refunds` e define os limites
  de `page` e `per_page` e o filtro opcional `name`.
- `src/controllers/refund_lister_controller.py` distingue `admin` de
  `standard` e calcula os metadados da paginação.
- `src/models/repositories/refunds_repository.py` aplica o filtro parcial
  `ilike`, o escopo por usuário, a ordenação decrescente e a paginação.
- `../Refund-FrontEnd/src/hooks/useRefunds.ts` envia página, tamanho e busca;
  `../Refund-FrontEnd/src/pages/PageHome.tsx` reinicia a página ao buscar e
  apresenta resultados, estado vazio e controles de paginação.
