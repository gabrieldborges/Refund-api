# Dashboard — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Uma tela de indicadores e quatro gráficos, alimentada por um único agregado no servidor, com os dados no escopo do papel de quem olha.

**Architecture:** Um endpoint `GET /refunds/summary` com três `GROUP BY` numa chamada de repositório; o controller aplica o escopo e preenche zeros e meses ausentes. No frontend, os gráficos vivem em `features/refunds` e chegam à página por um contêiner único que faz o `import()` dinâmico — nunca por reexportação direta.

**Tech Stack:** FastAPI, SQLAlchemy Core, pytest. React 19, `@nivo/pie` (já presente) + `@nivo/bar` e `@nivo/line` (novos), TanStack Query, Zod, Vitest, MSW.

**Spec:** [`2026-08-11-dashboard-design.md`](../specs/2026-08-11-dashboard-design.md)

## Global Constraints

- **Escopo por papel no controller**, com o idioma de `refund_lister_controller.py:31`: `filter_user_id = filter_user_id if role == "admin" else user_id`. Um usuário padrão **nunca** agrega dados de outro, mesmo passando `user_id`.
- **Todas as chaves sempre presentes, com zeros**: os 4 status (`ALL_STATUSES`, `refund_stats_finder_controller.py:9`), as 5 categorias (`ALLOWED_CATEGORIES`, `refund_creator_validator.py:6`) e **todos os meses da janela**, inclusive os vazios.
- **Um eixo por gráfico.** Nunca dois eixos y. Valor e contagem não compartilham gráfico.
- **Cor segue a entidade:** as cores de status são idênticas na rosca e no empilhado.
- **Barras por categoria: série única, uma cor, sem legenda.** `sliceColor` **não** pode ser chamada com 5 itens — ela cicla, e a 5ª barra repetiria a 1ª.
- **Nenhum gráfico é reexportado pela fachada.** Só o contêiner, que faz `import()` por dentro. Uma reexportação estática traz o chunk do Nivo ao bundle de entrada sem erro.
- **Erro nunca vira zero.** Um gráfico zerado por falha de rede é indistinguível de quem não tem nada.
- Textos de UI em português nos **dois** catálogos; comentários de teste em inglês.
- `pylint src` — **código de saída**, e **não** através de pipe para `tail`.
- Branch: `feat/dashboard`, nos dois repositórios.
- Baselines: **backend 371** (+72 integração), **frontend 372 em 63 arquivos**.

---

## Task 1: `summarize_refunds` no repositório

**Files:**
- Modify: `Refund-api/src/models/repositories/refunds_repository.py`, e sua interface
- Modify: `Refund-api/src/models/repositories/refunds_repository_test.py`

**Interfaces:**
- Produces: `summarize_refunds(user_id: Optional[int], since: datetime) -> tuple[dict, dict, list]` devolvendo `(by_status, by_category, by_month_rows)`. `by_status` e `by_category` são `{chave: {"count": int, "amount_in_cents": int}}` **apenas com as chaves que o banco devolveu**; `by_month_rows` é uma lista de `{"month": "YYYY-MM", "status": str, "count": int, "amount_in_cents": int}`. Preencher zeros é da Task 2.

- [ ] **Step 1: Escrever os testes que falham**

```python
# acrescentar a refunds_repository_test.py
def _wire_summary(mock_db, status_rows, category_rows, month_rows):
    """Three GROUP BY queries in one session, answered in call order."""
    results = []
    for rows in (status_rows, category_rows, month_rows):
        result = MagicMock()
        result.fetchall = MagicMock(return_value=rows)
        results.append(result)
    mock_db.session.execute = AsyncMock(side_effect=results)


@pytest.mark.asyncio
async def test_summarize_refunds_groups_by_status(mock_connection, mock_db):
    _wire_summary(mock_db, [("pending", 2, 3000), ("paid", 1, 1000)], [], [])

    by_status, _, _ = await RefundsRepository(mock_connection).summarize_refunds(
        user_id=None, since=datetime(2026, 3, 1)
    )

    assert by_status == {
        "pending": {"count": 2, "amount_in_cents": 3000},
        "paid": {"count": 1, "amount_in_cents": 1000},
    }


@pytest.mark.asyncio
async def test_summarize_refunds_groups_by_category(mock_connection, mock_db):
    _wire_summary(mock_db, [], [("food", 3, 4500)], [])

    _, by_category, _ = await RefundsRepository(mock_connection).summarize_refunds(
        user_id=None, since=datetime(2026, 3, 1)
    )

    assert by_category == {"food": {"count": 3, "amount_in_cents": 4500}}


# The month rows carry status too: that cross-tab is what feeds the stacked
# chart, and asking for it separately would be a fourth query over the same rows.
@pytest.mark.asyncio
async def test_summarize_refunds_crosses_month_with_status(mock_connection, mock_db):
    _wire_summary(mock_db, [], [], [(datetime(2026, 7, 1), "paid", 2, 5000)])

    _, _, by_month = await RefundsRepository(mock_connection).summarize_refunds(
        user_id=None, since=datetime(2026, 3, 1)
    )

    assert by_month == [
        {"month": "2026-07", "status": "paid", "count": 2, "amount_in_cents": 5000}
    ]


# A NULL sum cannot happen in a group with rows, but an all-NULL column would
# produce one — the same guard count_by_status already carries.
@pytest.mark.asyncio
async def test_summarize_refunds_guards_a_null_sum(mock_connection, mock_db):
    _wire_summary(mock_db, [("pending", 1, None)], [], [])

    by_status, _, _ = await RefundsRepository(mock_connection).summarize_refunds(
        user_id=None, since=datetime(2026, 3, 1)
    )

    assert by_status["pending"]["amount_in_cents"] == 0


# The window must be in the WHERE of ALL THREE queries: a status total that
# ignored it would disagree with the months that make it up.
@pytest.mark.asyncio
async def test_summarize_refunds_applies_the_window_to_every_query(mock_connection, mock_db):
    _wire_summary(mock_db, [], [], [])

    await RefundsRepository(mock_connection).summarize_refunds(
        user_id=None, since=datetime(2026, 3, 1)
    )

    for call in mock_db.session.execute.call_args_list:
        assert "created_at >=" in str(call[0][0])


# Same for the user filter — the whole point of the scope rule.
@pytest.mark.asyncio
async def test_summarize_refunds_filters_by_user_in_every_query(mock_connection, mock_db):
    _wire_summary(mock_db, [], [], [])

    await RefundsRepository(mock_connection).summarize_refunds(
        user_id=7, since=datetime(2026, 3, 1)
    )

    for call in mock_db.session.execute.call_args_list:
        assert "refunds.user_id =" in str(call[0][0])


@pytest.mark.asyncio
async def test_summarize_refunds_without_a_user_does_not_filter(mock_connection, mock_db):
    _wire_summary(mock_db, [], [], [])

    await RefundsRepository(mock_connection).summarize_refunds(
        user_id=None, since=datetime(2026, 3, 1)
    )

    for call in mock_db.session.execute.call_args_list:
        assert "refunds.user_id =" not in str(call[0][0])
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `cd Refund-api && pytest src/models/repositories/refunds_repository_test.py -q`
Expected: FAIL — `AttributeError: ... has no attribute 'summarize_refunds'`

- [ ] **Step 3: Implementar**

```python
    async def summarize_refunds(
        self, user_id: Optional[int], since: datetime
    ) -> tuple[dict, dict, list]:
        async with self.__db_connection.connect() as session:
            filters = [Refunds.c.created_at >= since]
            if user_id is not None:
                filters.append(Refunds.c.user_id == user_id)

            # Three GROUP BY over the same filtered set. Three queries and not
            # one because the groupings are independent: a single query grouping
            # by status AND category AND month would return the cross product of
            # all three, and the caller would have to re-aggregate it twice.
            #
            # The window is in every one of them. A status total that ignored it
            # would disagree with the months that are supposed to add up to it.
            by_status = self.__grouped(
                await session.execute(self.__group_query(Refunds.c.status, filters))
            )
            by_category = self.__grouped(
                await session.execute(self.__group_query(Refunds.c.category, filters))
            )

            # The month rows carry status as a second key: that cross-tab feeds
            # the stacked chart, and asking for it separately would be a fourth
            # scan of the same rows.
            month = func.date_trunc("month", Refunds.c.created_at)
            month_query = (
                select(
                    month,
                    Refunds.c.status,
                    func.count(),  # pylint: disable=not-callable
                    func.sum(Refunds.c.amount_in_cents),
                )
                .select_from(Refunds)
                .where(*filters)
                .group_by(month, Refunds.c.status)
                .order_by(month.asc())
            )
            by_month = [
                {
                    "month": row[0].strftime("%Y-%m"),
                    "status": row[1],
                    "count": row[2],
                    "amount_in_cents": row[3] or 0,
                }
                for row in (await session.execute(month_query)).fetchall()
            ]

            return by_status, by_category, by_month

    def __group_query(self, column, filters):
        return (
            select(
                column,
                func.count(),  # pylint: disable=not-callable
                func.sum(Refunds.c.amount_in_cents),
            )
            .select_from(Refunds)
            .where(*filters)
            .group_by(column)
        )

    def __grouped(self, result) -> dict:
        # `or 0` guards the NULL that an all-NULL column would produce, the same
        # guard count_by_status carries.
        return {
            key: {"count": count, "amount_in_cents": total or 0}
            for key, count, total in result.fetchall()
        }
```

Declarar na interface, e importar `datetime` no topo do módulo.

- [ ] **Step 4: Rodar e ver passar**

Run: `cd Refund-api && pytest -q && pylint src > /tmp/pl.txt 2>&1; echo $?`
Expected: PASS, suíte acima de 371, `pylint` saindo 0

- [ ] **Step 5: Commit**

```bash
cd Refund-api && git add -A
git commit -m "feat: aggregate refunds by status, category and month in one call"
```

---

## Task 2: `RefundSummaryController` — escopo, zeros e meses ausentes

**Files:**
- Create: `Refund-api/src/controllers/refund_summary_controller.py`, `interfaces/refund_summary_controller_interface.py`, `refund_summary_controller_test.py`

**Interfaces:**
- Consumes: `summarize_refunds` (Task 1).
- Produces: `RefundSummaryController(repo, clock=...).summarize(user_id, role, months, filter_user_id=None) -> dict`. **`clock` é injetável** para os testes fixarem "hoje" sem mockar `datetime` global.

- [ ] **Step 1: Escrever os testes que falham**

```python
from datetime import datetime
from unittest.mock import AsyncMock
import pytest
from .refund_summary_controller import RefundSummaryController

NOW = datetime(2026, 8, 11, 12, 0, 0)


def _repo(by_status=None, by_category=None, by_month=None):
    repo = AsyncMock()
    repo.summarize_refunds.return_value = (by_status or {}, by_category or {}, by_month or [])
    return repo


def _controller(repo):
    # The clock is injected rather than patched: a test that froze datetime
    # globally would also freeze it for anything else in the same process.
    return RefundSummaryController(repo, clock=lambda: NOW)


# The four statuses and five categories are always present, zeros included —
# the same contract UC-014 established, for the same reason: an absent key makes
# the client branch on undefined, and "zero" is not "does not exist".
@pytest.mark.asyncio
async def test_every_status_and_category_key_is_present_with_zeros():
    response = await _controller(_repo()).summarize(user_id=1, role="admin", months=6)

    assert set(response["by_status"]) == {"pending", "approved", "paid", "rejected"}
    assert set(response["by_category"]) == {"food", "lodging", "transport", "service", "others"}
    assert response["by_status"]["paid"] == {"count": 0, "amount_in_cents": 0}


# Every month in the window, oldest first, including the empty ones: a gap in
# the series would make the line chart lie about its slope.
@pytest.mark.asyncio
async def test_every_month_in_the_window_is_present_in_order():
    response = await _controller(_repo()).summarize(user_id=1, role="admin", months=6)

    assert [month["month"] for month in response["by_month"]] == [
        "2026-03", "2026-04", "2026-05", "2026-06", "2026-07", "2026-08",
    ]


@pytest.mark.asyncio
async def test_an_empty_month_is_zero_rather_than_absent():
    rows = [{"month": "2026-08", "status": "paid", "count": 2, "amount_in_cents": 5000}]
    response = await _controller(_repo(by_month=rows)).summarize(
        user_id=1, role="admin", months=6
    )

    march = response["by_month"][0]
    assert march["month"] == "2026-03"
    assert march["count"] == 0
    assert march["by_status"]["paid"] == {"count": 0, "amount_in_cents": 0}


# The month's own totals are the sum of its statuses, computed here so the
# client never has to add them up (and never disagrees with the server).
@pytest.mark.asyncio
async def test_a_month_total_is_the_sum_of_its_statuses():
    rows = [
        {"month": "2026-08", "status": "paid", "count": 2, "amount_in_cents": 5000},
        {"month": "2026-08", "status": "pending", "count": 1, "amount_in_cents": 1500},
    ]
    response = await _controller(_repo(by_month=rows)).summarize(
        user_id=1, role="admin", months=6
    )

    august = response["by_month"][-1]
    assert august["count"] == 3
    assert august["amount_in_cents"] == 6500


@pytest.mark.asyncio
async def test_an_admin_without_a_filter_aggregates_everyone():
    repo = _repo()

    response = await _controller(repo).summarize(user_id=1, role="admin", months=6)

    assert response["scope"] == "all"
    assert repo.summarize_refunds.await_args.kwargs["user_id"] is None


@pytest.mark.asyncio
async def test_an_admin_can_narrow_to_one_requester():
    repo = _repo()

    response = await _controller(repo).summarize(
        user_id=1, role="admin", months=6, filter_user_id=7
    )

    assert response["scope"] == "user"
    assert repo.summarize_refunds.await_args.kwargs["user_id"] == 7


# The rule that matters: a standard user's filter_user_id is IGNORED, not
# rejected. They are already locked to themselves, so there is nothing to leak
# and no new error path to document — the same choice refund_lister makes.
@pytest.mark.asyncio
async def test_a_standard_user_only_ever_aggregates_themselves():
    repo = _repo()

    response = await _controller(repo).summarize(
        user_id=1, role="standard", months=6, filter_user_id=7
    )

    assert response["scope"] == "user"
    assert repo.summarize_refunds.await_args.kwargs["user_id"] == 1


@pytest.mark.asyncio
async def test_the_window_starts_at_the_first_day_of_the_oldest_month():
    repo = _repo()

    await _controller(repo).summarize(user_id=1, role="admin", months=6)

    # Truncated to the month, not "180 days ago": a partial oldest month would
    # render as a short bar next to full ones and read as a drop.
    assert repo.summarize_refunds.await_args.kwargs["since"] == datetime(2026, 3, 1)


@pytest.mark.asyncio
async def test_the_response_echoes_the_window():
    response = await _controller(_repo()).summarize(user_id=1, role="admin", months=3)

    assert response["months"] == 3
    assert response["type"] == "RefundSummary"
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `cd Refund-api && pytest src/controllers/refund_summary_controller_test.py -q`
Expected: FAIL — módulo inexistente

- [ ] **Step 3: Implementar**

```python
from datetime import datetime
from typing import Callable, Optional
from src.models.repositories.interfaces.refunds_repository_interface import (
    RefundsRepositoryInterface,
)
from src.controllers.interfaces.refund_summary_controller_interface import (
    RefundSummaryControllerInterface,
)
from src.validators.refund_creator_validator import ALLOWED_CATEGORIES

# Same tuple, same order, same reason as refund_stats_finder_controller: the
# response publishes a fixed set of keys so the client never branches on a
# missing one.
ALL_STATUSES = ("pending", "approved", "paid", "rejected")
ZERO = {"count": 0, "amount_in_cents": 0}


class RefundSummaryController(RefundSummaryControllerInterface):
    def __init__(
        self,
        refunds_repository: RefundsRepositoryInterface,
        clock: Callable[[], datetime] = datetime.now,
    ) -> None:
        self.__refunds_repository = refunds_repository
        # Injected so a test can fix "today" without freezing datetime for the
        # whole process.
        self.__clock = clock

    async def summarize(
        self,
        user_id: int,
        role: str,
        months: int,
        filter_user_id: Optional[int] = None,
    ) -> dict:
        # Same scope idiom as refund_lister_controller: an admin sees everyone
        # and may narrow to one requester; for a standard user the parameter is
        # IGNORED, not rejected — they are already locked to themselves, so
        # there is nothing to leak and no new error path to document.
        target = filter_user_id if role == "admin" else user_id

        window = self.__month_starts(months)
        by_status, by_category, month_rows = await self.__refunds_repository.summarize_refunds(
            user_id=target, since=window[0]
        )

        return {
            "type": "RefundSummary",
            "scope": "all" if target is None else "user",
            "months": months,
            "by_status": self.__filled(by_status, ALL_STATUSES),
            "by_category": self.__filled(by_category, sorted(ALLOWED_CATEGORIES)),
            "by_month": self.__months(window, month_rows),
        }

    def __month_starts(self, months: int) -> list:
        """The first day of each month in the window, oldest first.

        Truncated to the month rather than "N×30 days ago": a partial oldest
        month would render as a short bar beside full ones and read as a drop
        that never happened.
        """
        now = self.__clock()
        starts = []
        year, month = now.year, now.month
        for _ in range(months):
            starts.append(datetime(year, month, 1))
            month -= 1
            if month == 0:
                year, month = year - 1, 12
        return list(reversed(starts))

    def __filled(self, grouped: dict, keys) -> dict:
        return {key: grouped.get(key, dict(ZERO)) for key in keys}

    def __months(self, window: list, rows: list) -> list:
        by_month = {}
        for row in rows:
            bucket = by_month.setdefault(row["month"], {})
            bucket[row["status"]] = {
                "count": row["count"],
                "amount_in_cents": row["amount_in_cents"],
            }

        months = []
        for start in window:
            key = start.strftime("%Y-%m")
            statuses = self.__filled(by_month.get(key, {}), ALL_STATUSES)
            # The month's totals are summed HERE, so the client never adds them
            # up and never disagrees with the server about them.
            months.append(
                {
                    "month": key,
                    "count": sum(entry["count"] for entry in statuses.values()),
                    "amount_in_cents": sum(
                        entry["amount_in_cents"] for entry in statuses.values()
                    ),
                    "by_status": statuses,
                }
            )
        return months
```

- [ ] **Step 4: Rodar e ver passar**

Run: `cd Refund-api && pytest -q`
Expected: PASS, 9 testes novos

- [ ] **Step 5: Commit**

```bash
cd Refund-api && git add -A
git commit -m "feat: scope the summary by role and fill every key the client reads"
```

---

## Task 3: Validator, view, composer e rota

**Files:**
- Create: `Refund-api/src/validators/refund_summary_validator.py` (+ teste)
- Create: `Refund-api/src/views/refund_summary_view.py`, `main/composer/refund_summary_composer.py`
- Modify: `Refund-api/src/main/routes/refund_routes.py` (+ teste)

- [ ] **Step 1: Escrever os testes que falham**

O validator recusa `months` fora de 1–12 com `HttpUnprocessableEntityError`, no
formato de `refund_lister_validator`. **Aqui o validator É necessário**, ao
contrário do Ciclo 1: `months` tem teto, e o teto é a única coisa que limita a
varredura da tabela.

A rota é `GET /refunds/summary` e precisa ser declarada **antes** de
`GET /refunds/{refund_id}` — senão `summary` é lido como um `refund_id` e o
FastAPI responde 422. Teste obrigatório:

```python
def test_the_summary_route_is_not_read_as_a_refund_id():
    _as_standard()
    view = _view({"type": "RefundSummary"})

    with patch("src.main.routes.refund_routes.refund_summary_composer", return_value=view) as s:
        response = client.get("/refunds/summary")

    assert response.status_code == 200
    assert s.called
```

- [ ] **Step 2: Rodar e ver falhar** — `Expected: FAIL` com 422, porque `summary` cai em `/{refund_id}`

- [ ] **Step 3: Implementar** — validator, view (que chama o validator primeiro, como `RefundListerView`), composer, e a rota com `months: int = Query(6, ge=1, le=12)` e `user_id: Optional[int] = Query(None)`, **declarada acima de `/{refund_id}`** com um comentário dizendo por quê

- [ ] **Step 4: Rodar e ver passar** — `pytest -q` e `pylint src` saindo 0

- [ ] **Step 5: Commit** — `feat: expose GET /refunds/summary`

---

## Task 4: Contrato e UC-017

**Files:**
- Modify: `Refund-api/src/test_integration/contract_test.py`, `contract/refunds.json`
- Create: `Refund-api/docs/use-cases/UC-017-refund-summary.md`
- Modify: `Refund-api/docs/index.md`

- [ ] **Step 1: Capturar as duas formas de escopo**

Em `capture_refunds`, acrescentar **duas** chaves — as formas diferem em `scope`,
e o frontend precisa validar as duas:

```python
        "refundSummary": client.get("/refunds/summary", headers=headers).json(),
        "refundSummaryAsAdmin": client.get("/refunds/summary", headers=admin_headers).json(),
```

`capture_refunds` passa a receber `admin_headers`.

- [ ] **Step 2: Gerar** — `docker compose up -d && pytest -m integration`
Expected: FAIL na primeira vez, dizendo que `contract/refunds.json` foi regerado. Conferir o diff: `scope` deve ser `"user"` na primeira chave e `"all"` na segunda.

- [ ] **Step 3: Rodar de novo** — Expected: PASS

- [ ] **Step 4: UC-017**, no formato dos existentes, registrando: os parâmetros e seus tetos; as chaves fixas; **os meses vazios preenchidos**; o escopo por papel com `user_id` ignorado para padrão; e a **limitação de fuso** (agregação em UTC, uma solicitação das 22h de Brasília cai no mês seguinte na virada). Entrada em `docs/index.md`.

- [ ] **Step 5: Commit** — `docs: capture the summary contract in both scopes and record UC-017`

---

## Task 5: Camada de dados no frontend

**Files:**
- Create: `Refund-FrontEnd/src/features/refunds/schemas/summary.ts`, `api/summaryQueries.ts`, `hooks/useRefundSummary.ts`
- Modify: `Refund-FrontEnd/src/features/refunds/index.ts`, `src/features/refunds/contract/refunds.json`, `contract.test.ts`

**Interfaces:**
- Produces: `refundSummaryQuery(months)`, `useRefundSummary(months)`, o tipo `RefundSummary`, e `refundSummarySearchParamsSchema` (só `months`, com `.catch(6)`).

- [ ] **Step 1: Escrever os testes que falham** — schema aceitando a forma real; `months` inválido caindo em 6; e no `contract.test.ts` da feature, as **duas** chaves capturadas validando, mais uma asserção de que `scope` é `"user"` numa e `"all"` na outra
- [ ] **Step 2: Rodar e ver falhar**
- [ ] **Step 3: Implementar** — `z.record` não serve para `by_status`: as quatro chaves são obrigatórias, então é um `z.object` explícito. O mesmo para as cinco categorias. `by_month` é `z.array` de objeto com `by_status` aninhado
- [ ] **Step 4: Copiar o contrato** — `cp Refund-api/contract/refunds.json Refund-FrontEnd/src/features/refunds/contract/refunds.json`. Cópia manual e obrigatória: cada CI só faz checkout de um repositório
- [ ] **Step 5: Rodar, ver passar, commit** — `feat: add the summary query, validated against both scopes`

---

## Task 6: `chartPalette.ts`

**Files:**
- Rename: `Refund-FrontEnd/src/features/refunds/lib/donutPalette.ts` → `lib/chartPalette.ts` (+ o teste)
- Modify: os importadores (`RefundDonutChart.tsx`)

- [ ] **Step 1: Renomear com `git mv`**, para o histórico seguir o arquivo
- [ ] **Step 2: Acrescentar o comentário que impede o próximo defeito**, no topo de `sliceColor`:

```ts
// APENAS para status, que tem exatamente 4 valores — o mesmo tamanho de PALETTE.
// Esta função indexa por posição e faz `% PALETTE.length`, então chamá-la com 5
// itens (as categorias, por exemplo) repete a primeira cor na quinta fatia, sem
// erro nenhum. Ciclar cor categórica é proibido: cor tem de identificar a
// entidade, e duas entidades da mesma cor não identificam nada.
//
// Gráfico com mais entidades que a paleta não ganha cores novas — ele usa uma
// cor só e deixa a identidade para o eixo, como o de categorias faz.
```

- [ ] **Step 3: Rodar a suíte inteira** — Expected: PASS, **nenhum teste alterado**; só imports
- [ ] **Step 4: Commit** — `refactor: rename donutPalette to chartPalette and fence off sliceColor`

---

## Task 7: Os três gráficos novos

**Files:**
- Create: `Refund-FrontEnd/src/features/refunds/components/RefundBarChart.tsx`, `RefundLineChart.tsx`, `RefundStackedBarChart.tsx` (+ testes)
- Modify: `package.json` (`@nivo/bar`, `@nivo/line`), os dois catálogos

**Interfaces:**
- Produces: `RefundBarChart({ bars, titleKey, metric })`, `RefundLineChart({ points, titleKey, metric })`, `RefundStackedBarChart({ months, titleKey })`. Todos aceitam `isLoading` e `isError`, como o donut.

- [ ] **Step 1: `npm i @nivo/bar @nivo/line`** e registrar o tamanho do chunk antes e depois

- [ ] **Step 2: Escrever os testes que falham**

Para cada gráfico, os mesmos quatro casos do donut, mais os específicos:

```tsx
// jsdom has no layout engine: nivo measures the container as 0x0 and draws no
// marks at all. So these assert the accessible label and the data plumbing —
// never SVG paths. Same reasoning as RefundDonutChart.test.tsx.
it("names itself with the numbers, for a reader who cannot see the marks", () => { … });
it("shows the empty state when every value is zero", () => { … });
it("announces an error instead of rendering zeros", () => { … });
```

Específicos:

- Barras por categoria: **uma cor para todas as barras** — asserção sobre a prop
  `colors` recebida, não sobre o SVG. E **nenhuma legenda**: série única, o título
  nomeia.
- Linha: um único eixo y. Asserção de que o componente não aceita duas séries de
  unidades diferentes (o tipo já impede; o teste documenta a intenção).
- Empilhado: legenda com os quatro status; e as cores vindas de `sliceColor`,
  **iguais** às da rosca — asserção comparando com `sliceColor`, não com hex
  literal, porque hex literal duplicaria a paleta no teste.

- [ ] **Step 3: Implementar**, repetindo as cinco lições do donut (cromo hex por tema, `usePrefersReducedMotion`, `fontSize` em rem, `role="img"` com os números, e o carregamento sob demanda ficando no contêiner da Task 8), **mais** as duas exigências novas:
  - **tooltip por marca** nos três (`isInteractive` ligado, ao contrário do donut, que tem os valores nas leader lines)
  - **gap de 2px** entre segmentos empilhados e entre barras vizinhas (`innerPadding` / `padding` do Nivo)

- [ ] **Step 4: Rodar, typecheck, lint**
- [ ] **Step 5: Commit** — `feat: add the bar, line and stacked charts`

---

## Task 8: O contêiner, a página e a rota

**Files:**
- Create: `Refund-FrontEnd/src/features/refunds/components/DashboardCharts.tsx`, `src/pages/PageDashboard.tsx` (+ testes, + `.a11y.test.tsx`)
- Modify: `src/features/refunds/index.ts`, `src/router.tsx`, `src/router-loaders.ts`, `src/components/core/nav-items.tsx`, `src/components/core/Sidebar.test.tsx`, `src/test/msw/handlers.ts`, os dois catálogos

- [ ] **Step 1: Handlers do MSW** para `/refunds/summary`, nas duas formas de escopo, com um mês zerado no meio da janela — senão o teste do preenchimento passa por acidente

- [ ] **Step 2: Escrever os testes que falham**
  - `PageDashboard`: os indicadores; **valor = aprovado + pago**, não a soma dos quatro (asserção com números que tornariam as duas contas diferentes); carregando, erro, vazio
  - `dashboardLoader`: normaliza `months`; **não** redireciona usuário padrão
  - `Sidebar`: selos "em breve" em **1**
  - a11y: nenhuma violação WCAG A/AA

- [ ] **Step 3: Implementar**

`DashboardCharts.tsx` é o **único** ponto de `import()` dinâmico dos quatro
gráficos, e é o único que a fachada exporta:

```ts
// A fachada exporta o CONTÊINER, nunca os gráficos. Uma reexportação estática de
// qualquer um deles traria o chunk do Nivo de volta ao bundle de entrada sem erro
// nenhum — ver docs/performance-budget.md. Um ponto de import() para os quatro, e
// não quatro, porque eles compartilham @nivo/core e os pacotes d3-*.
export { default as DashboardCharts } from "./components/DashboardCharts";
```

`PageDashboard.tsx`: faixa de indicadores + `<DashboardCharts summary={…} />`.
Rota `/dashboard` com `dashboardLoader`, **sem** `requireAdmin` — a tela é para
todos e o escopo é do servidor. `nav-items.tsx`: `enabled: true`, sem `adminOnly`.

- [ ] **Step 4: Rodar as quatro verificações**
- [ ] **Step 5: Ler a saída do `npm run build`** — o chunk dos gráficos cresceu além dos 74,2 kB; registrar o número. Se o `index` engordar nessa ordem, algum gráfico foi importado estaticamente
- [ ] **Step 6: Commit** — `feat: add the dashboard screen`

---

## Task 9: Fechamento

- [ ] **Step 1: As quatro do frontend e as três do backend**, incluindo `pytest -m integration`
- [ ] **Step 2: Atualizar o orçamento** (`docs/performance-budget.md`) com o tamanho medido do chunk dos gráficos, substituindo a tabela de 2026-08-11
- [ ] **Step 3: Navegador**, com a API em `localhost:3333`:
  - [ ] admin e padrão veem números e gráficos **diferentes**
  - [ ] um mês sem solicitação aparece como zero na linha, não como buraco
  - [ ] tooltip funcionando nos três gráficos novos
  - [ ] legenda do empilhado presente, e os quatro status distinguíveis
  - [ ] claro e escuro
  - [ ] 390 × 844, `scrollWidth === clientWidth`
- [ ] **Step 4: Documentação** — `current-state.md`, entrada `## Ciclo de feature — Dashboard` em `learning-path-progress.md`, e o panorama marcando o Ciclo 2 como concluído
- [ ] **Step 5: Roadmap** — registrar como ideia a **troca da paleta pelas cores validadas**, com os números medidos, para não se perder
- [ ] **Step 6: Commit final**

## Self-Review

**Cobertura do spec:** §1 → Tasks 1, 2, 3; §2 → Task 4; §3 → Task 7; §4 → Task 6;
§5 → Task 8; §6 → Task 8 (fachada) e Task 9 (orçamento). Verificação → Task 9.

**Consistência de nomes:** `summarize_refunds(user_id, since) -> (by_status,
by_category, by_month)` (T1) é consumida em T2 com esses argumentos nomeados;
`ALL_STATUSES` e `ZERO` (T2) são internos ao controller; `refundSummaryQuery` e
`useRefundSummary` (T5) são usados em T8; `sliceColor` (T6) é usada só pelo donut
e pelo empilhado.

**Riscos anotados:**

- **A rota `/refunds/summary` tem de vir antes de `/{refund_id}`.** Sem isso o
  FastAPI lê `summary` como id e responde 422. É o único defeito deste ciclo que
  passa em todos os testes unitários e falha no primeiro uso.
- **O relógio é injetado no controller.** Não use `datetime.now()` direto: os
  testes de janela ficariam dependentes do mês em que rodam, e passariam a falhar
  sozinhos na virada.
- **`sliceColor` com 5 itens não dá erro.** Ela repete a primeira cor. O comentário
  da Task 6 é a única barreira; se um gráfico futuro precisar de 5 identidades, a
  resposta é uma cor só e identidade no eixo, não uma quinta cor.
- **A falha de paleta é conhecida e aceita** (ΔE 12,9 em visão normal entre
  "aprovada" e "paga"). Mitigada com gap, legenda, tooltip e rótulo direto. Não a
  trate como resolvida, e não troque a paleta neste ciclo.
