# UC-014 — Consultar estatísticas de reembolso por usuário

## Ator principal

Usuário autenticado, com papel `standard` (consultando a si mesmo) ou
`admin` (consultando qualquer usuário).

## Objetivo

Obter, para um usuário, a contagem de solicitações e a soma de
`amount_in_cents`, agrupadas por `status`, para alimentar painéis e telas de
detalhe do solicitante.

## Pré-condições

- O usuário possui um JWT válido.

## Fluxo principal

1. O cliente envia `GET /users/{user_id}/refund-stats` com o JWT no
   cabeçalho `Authorization: Bearer`.
2. A API autentica o usuário e verifica: o `user_id` do path é o próprio
   requisitante, ou o requisitante é `admin`; caso contrário, `404`.
3. A API executa uma única consulta agrupada (`GROUP BY status`) contando e
   somando `amount_in_cents` das solicitações daquele usuário.
4. A API monta a resposta com as quatro chaves fixas de status
   (`pending`, `approved`, `paid`, `rejected`), preenchendo com
   `{"count": 0, "amount_in_cents": 0}` qualquer status sem nenhuma
   solicitação.

## Resposta

```json
{
  "type": "RefundStats",
  "user_id": 3,
  "by_status": {
    "pending":  { "count": 2, "amount_in_cents":  30000 },
    "approved": { "count": 5, "amount_in_cents":  65000 },
    "paid":     { "count": 3, "amount_in_cents":  40000 },
    "rejected": { "count": 1, "amount_in_cents":  10000 }
  }
}
```

**Não há total geral, nem de contagem nem de soma, e não há taxas
derivadas.** Somar as quatro contagens ou os quatro valores monetários
misturaria previsão (`pending`), passivo (`approved`), despesa realizada
(`paid`) e nada (`rejected`) — o mesmo defeito que tornava o card "Total" da
Home do frontend um número sem significado assim que existissem
solicitações rejeitadas. Taxa de aprovação, ticket médio e qualquer outra
derivada são divisões destes números e ficam por conta do cliente; publicá-
las no contrato exigiria decidir arredondamento na API, sem necessidade.

## Autorização

- O próprio usuário (`user_id` do path igual ao `user_id` do token): acesso
  permitido.
- `admin`: acesso permitido às estatísticas de qualquer usuário.
- Usuário `standard` consultando outro `user_id`: acesso negado com `404`,
  pelo mesmo raciocínio anti-enumeração da BR-013 — um `403` confirmaria que
  aquele `user_id` existe.

## Tabela de códigos

| Código | Cenário |
| --- | --- |
| `200` | Estatísticas devolvidas, com zeros para status sem nenhuma solicitação. |
| `401` | JWT ausente, inválido ou expirado. |
| `404` | Usuário `standard` consultando um `user_id` diferente do próprio. |

## Fluxos alternativos e erros

- Se o JWT estiver ausente, inválido ou expirado, a API responde `401`.
- Se um usuário `standard` consultar um `user_id` diferente do seu, a API
  responde `404` com `User not found`.
- Se o usuário (o próprio ou, para `admin`, qualquer outro) não tiver
  nenhuma solicitação, a API responde `200` com as quatro chaves zeradas —
  não é um erro.

## Limitação conhecida

**Não há checagem de existência do `user_id` consultado.** Um `admin` que
consulta um `user_id` que não existe recebe uma resposta `200`
indistinguível de "usuário real sem nenhum reembolso" — todas as chaves
zeradas, sem sinal de que o usuário em si não existe. A consulta agrupada
não faz `JOIN` com `Users` e não há nenhuma verificação de existência antes
dela; ela simplesmente devolve um dicionário vazio para um `user_id` sem
linhas em `refunds`, que é exatamente o mesmo resultado de um `user_id`
inexistente. Isso é uma lacuna aceita por este ciclo, não um requisito: uma
checagem de existência exigiria uma consulta adicional a `Users` só para
diferenciar dois casos que, do ponto de vista deste endpoint, produzem a
mesma resposta útil.

## Pós-condições

- Nenhuma solicitação é alterada.

## Regras relacionadas

- [BR-006](../business-rules.md#br-006--autenticação-das-operações-de-reembolso)
- [BR-013](../business-rules.md#br-013--recurso-inexistente-ou-alheio)

## Evidências

- `src/main/routes/user_routes.py` protege e expõe
  `GET /users/{user_id}/refund-stats`.
- `src/views/refund_stats_finder_view.py` extrai `user_id` do path e
  `user_id`/`role` do token e repassa ao controller.
- `src/controllers/refund_stats_finder_controller.py` aplica a checagem
  `404` (não `403`) e preenche as quatro chaves fixas de status;
  `src/controllers/refund_stats_finder_controller_test.py::test_statuses_with_no_refunds_come_back_as_zeros`
  comprova o preenchimento com zeros;
  `::test_the_response_publishes_no_cross_status_total` comprova a ausência
  de total; `::test_admin_reads_someone_elses_stats` e
  `::test_a_standard_user_cannot_read_someone_elses_stats` cobrem a
  autorização.
- `src/models/repositories/refunds_repository.py::count_by_status` executa a
  consulta `GROUP BY status`;
  `src/models/repositories/refunds_repository_test.py::test_count_by_status_builds_a_dict_from_the_grouped_rows`,
  `::test_count_by_status_guards_a_null_sum` e
  `::test_count_by_status_filters_by_user_and_groups_by_status` cobrem a
  consulta.
- `src/main/composer/refund_stats_finder_composer.py` monta a fatia.
