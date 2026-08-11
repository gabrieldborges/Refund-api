# UC-018 — Consultar contagem diária de solicitações

## Ator principal

Usuário autenticado, com papel `standard` (as próprias solicitações) ou `admin`
(toda a empresa, opcionalmente restrito a um solicitante).

## Objetivo

Obter, para um mês, quantas solicitações houve em cada dia — a informação que a
grade do calendário desenha e que o gráfico do mês plota.

## Pré-condições

- O usuário possui um JWT válido.

## Fluxo principal

1. O cliente envia `GET /refunds/daily-counts?month=YYYY-MM` com o JWT.
2. A API valida o formato do mês e devolve ano e número já convertidos.
3. A API resolve o escopo: `admin` sem `user_id` conta todos; `admin` com `user_id`
   conta aquele solicitante; usuário `standard` conta **sempre** a si mesmo, e o
   `user_id` recebido é **ignorado**.
4. A API agrupa por dia dentro da janela `[1º do mês, 1º do mês seguinte)`.
5. A API preenche com zero **todos os dias do mês** que não tiveram solicitação.

## Parâmetros

| Parâmetro | Obrigatório | Faixa | Efeito |
| --- | --- | --- | --- |
| `month` | **sim** | `YYYY-MM`, ano `2000`–`2100`, mês `01`–`12` | O mês a contar. |
| `user_id` | não | inteiro | Restringe a um solicitante. **Ignorado** para `standard`. |

**`month` é obrigatório.** Sem ele não há janela a contar, e assumir "este mês" na
rota esconderia um defeito do cliente.

**O comprimento do mês vem do calendário**, não de uma tabela de doze números:
fevereiro tem 28 ou 29 dias, e **2100 é divisível por 4 e não é bissexto**. Como a
faixa aceita anos até 2100, um cálculo `ano % 4 == 0` responderia 29 dias ali.

**A janela é semiaberta.** Um limite superior fechado exigiria nomear o último
instante do mês, e `23:59:59` descarta o que acontecer no último segundo.

## Resposta

```json
{
  "type": "RefundDailyCounts",
  "scope": "user",
  "month": "2026-08",
  "days": [
    { "date": "2026-08-01", "count": 0 },
    { "date": "2026-08-03", "count": 2 },
    { "date": "2026-08-31", "count": 0 }
  ]
}
```

**Todos os dias do mês estão presentes**, com zero, pela mesma razão de UC-014 e
UC-017: o cliente desenha uma grade, e um dia ausente o obrigaria a tratar
`undefined` — além de que "dia que existe e teve zero" é afirmação diferente de "dia
que não existe".

**Não há `amount_in_cents`.** A pergunta é "quando", e a resposta é "quantas".
Publicar valor aqui criaria um campo sem consumidor.

## Autorização

- `admin`: conta todos, ou um solicitante via `user_id`.
- `standard`: conta apenas a si mesmo. O `user_id` é **ignorado**, não recusado — o
  usuário já está preso a si mesmo, então não há o que vazar nem novo caminho de
  erro a documentar. Mesma escolha de UC-004 e UC-017.

## Tabela de códigos

| Código | Cenário |
| --- | --- |
| `200` | Contagem devolvida, possivelmente toda zerada. |
| `401` | JWT ausente, inválido ou expirado. |
| `422` | `month` ausente, mal formado, com ano fora da faixa ou mês fora de `01`–`12`. |

## Fluxos alternativos e erros

- Um mês sem nenhuma solicitação responde `200` com todos os dias em zero — não é
  erro, e é o que a grade limpa do calendário mostra.
- `2026-13` casa com o formato `YYYY-MM` mas não é mês: o validator checa a forma
  **e** o significado, e recusa com `422`.

## Limitação conhecida

**A contagem por dia é feita em UTC.** `refunds.created_at` tem `server_default
now()`, e o agrupamento opera no fuso do banco. Uma solicitação criada às 22h de
Brasília aparece no dia seguinte. É a mesma limitação de UC-017 e a **mais visível
das três telas**, porque aqui o dia é a unidade — no Dashboard ela só desloca um
registro entre meses na virada.

## Pós-condições

- Nenhuma solicitação é alterada.

## Regras relacionadas

- [BR-006](../business-rules.md#br-006--autenticação-das-operações-de-reembolso)

## Evidências

- `src/main/routes/refund_routes.py` expõe `GET /refunds/daily-counts`, declarada
  **antes** de `/{refund_id}`;
  `src/main/routes/refund_daily_counts_route_test.py::test_the_daily_counts_path_is_not_read_as_a_refund_id`
  comprova a ordem, e `::test_the_summary_route_still_reaches_its_own_composer` que a
  rota literal do ciclo anterior não foi quebrada.
- `src/validators/refund_daily_counts_validator.py` devolve ano e mês já convertidos,
  para a view não fazer um segundo parse da mesma string;
  `::test_a_month_number_outside_one_to_twelve_raises` cobre o caso que passa pela
  regex e falha no significado.
- `src/controllers/refund_daily_counts_controller.py` usa `calendar.monthrange`;
  `refund_daily_counts_controller_test.py::test_february_has_twenty_nine_days_in_a_leap_year`
  e `::test_the_century_rule_is_respected` cobrem o mês variável, e
  `::test_december_rolls_into_the_next_year` o limite superior.
- `src/models/repositories/refunds_repository.py::count_by_day` executa o
  `GROUP BY` por dia.
- `contract/refunds.json` registra a resposta real em `refundDailyCounts`.
