# UC-017 — Consultar resumo agregado de reembolsos

## Ator principal

Usuário autenticado, com papel `standard` (resumo das próprias solicitações) ou
`admin` (resumo de toda a empresa, opcionalmente restrito a um solicitante).

## Objetivo

Obter, numa única resposta, os agregados que alimentam a tela de Dashboard:
contagem e soma de `amount_in_cents` por status, por categoria, e por mês ao longo
de uma janela — com o cruzamento mês × status, que é o que permite ver composição
e tempo no mesmo gráfico.

## Pré-condições

- O usuário possui um JWT válido.

## Fluxo principal

1. O cliente envia `GET /refunds/summary` com o JWT no cabeçalho
   `Authorization: Bearer`, opcionalmente com `months` e `user_id`.
2. A API autentica o usuário e resolve o escopo: `admin` sem `user_id` agrega
   todos; `admin` com `user_id` agrega aquele solicitante; usuário `standard`
   agrega **sempre** a si mesmo, e o `user_id` recebido é **ignorado**.
3. A API calcula a janela: o primeiro dia do mês de `months` meses atrás, contando
   o mês corrente.
4. A API executa **três** agregações sobre o mesmo conjunto filtrado — por
   `status`, por `category`, e por mês cruzado com `status`.
5. A API preenche com zero as chaves de status e de categoria ausentes, e **todos
   os meses da janela** que não tiveram nenhuma solicitação.

## Parâmetros

| Parâmetro | Padrão | Faixa | Efeito |
| --- | --- | --- | --- |
| `year` | o ano corrente | `2000`–`2100` | Ano-calendário a resumir, de janeiro a dezembro. |
| `user_id` | ausente | inteiro | Restringe a um solicitante. **Ignorado** para usuário `standard`. |

**É um ano-calendário, não uma janela deslizante.** O Dashboard nomeia o ano no
título de cada card e põe apenas o mês no eixo X — o que só lê corretamente se cada
resposta cobrir janeiro a dezembro de um ano só. Uma janela deslizante colocaria
dois anos diferentes num eixo de nomes de mês sem ano.

**A janela é semiaberta**, `[1º de janeiro do ano, 1º de janeiro do seguinte)`. Um
limite superior fechado exigiria nomear o último instante do ano, e `23:59:59`
descarta em silêncio o que acontecer no último segundo.

**Os limites de `year` são regra, não formatação:** eles impedem um valor absurdo
de chegar ao repositório e de construir um `datetime` inválido. Fora da faixa a
requisição é **recusada com `422`**.

**Sem `year`, o ano é o corrente**, decidido pelo relógio do controller — que é
injetável justamente para os testes não dependerem do ano em que rodam.

## Resposta

```json
{
  "type": "RefundSummary",
  "scope": "user",
  "year": 2026,
  "available_years": [2025, 2026],
  "by_status": {
    "pending":  { "count": 2, "amount_in_cents": 30000 },
    "approved": { "count": 5, "amount_in_cents": 65000 },
    "paid":     { "count": 3, "amount_in_cents": 40000 },
    "rejected": { "count": 1, "amount_in_cents": 10000 }
  },
  "by_category": {
    "food":      { "count": 4, "amount_in_cents": 18000 },
    "lodging":   { "count": 0, "amount_in_cents": 0 },
    "others":    { "count": 0, "amount_in_cents": 0 },
    "service":   { "count": 2, "amount_in_cents": 90000 },
    "transport": { "count": 5, "amount_in_cents": 37000 }
  },
  "by_month": [
    { "month": "2026-03", "count": 0, "amount_in_cents": 0,
      "by_status": { "pending": { "count": 0, "amount_in_cents": 0 }, "…": {} } },
    { "month": "2026-08", "count": 3, "amount_in_cents": 6500,
      "by_status": { "paid": { "count": 2, "amount_in_cents": 5000 }, "…": {} } }
  ]
}
```

**`scope` é `"all"` ou `"user"`**, e é o único campo pelo qual o cliente sabe se
está lendo a empresa ou uma pessoa.

**As quatro chaves de status e as cinco de categoria estão sempre presentes**, com
zeros, pela mesma razão de UC-014: uma chave ausente obriga o cliente a tratar
`undefined`, e num gráfico a barra ausente simplesmente desaparece — "zero" e "não
existe" são afirmações diferentes.

**`by_month` traz sempre doze entradas**, de janeiro a dezembro, inclusive os meses
sem nenhuma solicitação. Um buraco na série faria o gráfico de linha mentir sobre a
inclinação, e um primeiro mês parcial leria como uma queda que nunca houve.

**`available_years` lista apenas os anos que têm solicitações**, do mais antigo ao
mais recente, no mesmo escopo do resto da resposta. Existe para o seletor de ano
não convidar ninguém a abrir um gráfico vazio por construção — e é escopado como
tudo o mais: um usuário `standard` não descobre em que anos **outras** pessoas
tiveram solicitações.

**O total de cada mês é a soma dos status dele**, calculada no servidor para o
cliente nunca somar por conta e nunca discordar da API.

**Não há total geral entre status.** Somar os quatro juntaria previsão
(`pending`), passivo (`approved`), despesa realizada (`paid`) e nada
(`rejected`) — a mesma decisão registrada em UC-014. Quem quiser uma manchete de
dinheiro soma `approved + paid`, que é o número que o card da Home deveria mostrar.

## Autorização

- `admin`: agrega todos, ou um solicitante via `user_id`.
- `standard`: agrega apenas a si mesmo. O `user_id` é **ignorado**, não recusado —
  o usuário já está preso a si mesmo, então não há o que vazar nem novo caminho de
  erro a documentar. É a mesma escolha de UC-004.

## Tabela de códigos

| Código | Cenário |
| --- | --- |
| `200` | Resumo devolvido, possivelmente todo zerado. |
| `401` | JWT ausente, inválido ou expirado. |
| `422` | `year` fora de `2000`–`2100`, ou `user_id` não numérico. |

## Fluxos alternativos e erros

- Sem nenhuma solicitação no ano, a API responde `200` com tudo zerado e os
  meses presentes — não é um erro.
- Um `admin` consultando um `user_id` inexistente recebe `200` zerado, pela mesma
  limitação registrada em UC-014: não há checagem de existência.

## Limitação conhecida

**A agregação por mês é feita em UTC.** `refunds.created_at` tem `server_default
now()`, e o `date_trunc('month', created_at)` opera no fuso do banco. Uma
solicitação criada às 22h de Brasília no último dia do mês cai no mês seguinte.
Converter exigiria decidir de quem é o fuso — do servidor, do solicitante ou de
quem olha o gráfico — e essa decisão não foi tomada.

## Pós-condições

- Nenhuma solicitação é alterada.

## Regras relacionadas

- [BR-006](../business-rules.md#br-006--autenticação-das-operações-de-reembolso)

## Evidências

- `src/main/routes/refund_routes.py` expõe `GET /refunds/summary`, **declarada
  antes de `/{refund_id}`**;
  `src/main/routes/refund_summary_route_test.py::test_the_summary_path_is_not_read_as_a_refund_id`
  comprova que a ordem funciona, e `::test_a_numeric_id_still_reaches_the_finder`
  que a rota anterior não foi quebrada.
- `src/validators/refund_summary_validator.py` recusa a janela fora da faixa;
  `refund_summary_validator_test.py::test_a_year_outside_the_range_raises`.
- `src/controllers/refund_summary_controller.py` aplica o escopo e preenche zeros;
  `refund_summary_controller_test.py::test_a_standard_user_only_ever_aggregates_themselves`,
  `::test_the_year_is_always_twelve_months_from_january`,
  `::test_an_empty_month_is_zero_rather_than_absent`,
  `::test_the_window_is_the_calendar_year_half_open` e
  `::test_an_absent_year_falls_back_to_the_current_one`.
- `src/models/repositories/refunds_repository.py::summarize_refunds` executa as
  três agregações; `refunds_repository_test.py::test_summarize_refunds_applies_the_window_to_every_query`
  e `::test_summarize_refunds_filters_by_user_in_every_query` provam que janela e
  filtro valem nas três.
- `contract/refunds.json` registra as respostas reais nas chaves `refundSummary`
  (escopo de usuário) e `refundSummaryAsAdmin` (escopo global).
