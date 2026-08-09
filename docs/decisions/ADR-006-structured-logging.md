# ADR-006: Logs estruturados em JSON com request ID

## Status

Aceita em 2026-08-09, no Item 24 do learning path.

## Contexto

O projeto tinha **uma** chamada de log (`src/controllers/file_cleanup.py`, do
Item 21) e **nenhuma configuração**. Medido, não suposto — o efeito era este:

```
Could not delete file a3f2.png (refund receipt, row deleted); it is now orphaned on disk
Traceback (most recent call last):
  ...
```

Sem timestamp, sem nível, sem nome do logger, sem correlação. É o handler
`lastResort` do Python, que existe justamente para quando ninguém configurou
nada — e que **descarta em silêncio qualquer coisa abaixo de `WARNING`**.

Havia uma promessa pendente: o Item 23 colocou um `request_id` no corpo de todo
erro dizendo que ele casaria com um log. **Não casava com nada.**

## Decisão

**Logs em JSON**, uma linha por evento, com `ts`, `level`, `logger`, `msg`,
`request_id` e os campos que a chamada passar em `extra`.

**Sem dependência nova.** Um formatter JSON tem ~20 linhas. `python-json-logger`
seria a terceira dependência recusada neste projeto pelo mesmo motivo (`httpx`
já foi duas vezes).

**O `request_id` vem de um `contextvar`, não de parâmetro.** `request.state`
serve para quem tem o `Request` — os exception handlers têm. Uma linha de log
não tem: o `file_cleanup.py` loga de dentro de um controller, quatro camadas
abaixo da rota. Passar o request por essas camadas até chegar num logger seria
a forma errada. Um `contextvar` é a ferramenta para "valor ambiente durante
esta tarefa".

E ele é aplicado por um **`logging.Filter`**, não em cada chamada: uma linha que
só às vezes tem o id é quase tão ruim quanto nenhuma, porque não dá para
distinguir "outra requisição" de "alguém esqueceu".

**Uma linha de acesso por requisição** — método, rota, status, duração — escrita
por um middleware próprio, separado do que gera o id.

**Formato por ambiente:** JSON quando `ENVIRONMENT != local`, uma linha legível
em desenvolvimento. O custo é declarado: o formato que se lê localmente **não é**
o que roda em produção. Mitigado por teste afirmando o JSON.

**O access log do uvicorn é silenciado**, e isso é decisão de segurança, não de
estética: ele registra a **query string crua**, o que colocaria uma URL assinada
válida do Item 22 dentro do log. Silenciado no próprio código, não nas opções do
`run.py`, para valer também quando alguém sobe com `uvicorn ...` direto — que é
o que o CI e a maioria dos editores fazem.

## O que nunca vai para o log

- **Corpo de requisição:** nunca registrado. É o que mantém senha fora.
- **Headers:** nunca registrados. É o que mantém o `Authorization: Bearer` fora.
- **Query string:** registrada **com mascaramento** de `token`, `password` e
  `secret`. O nome do parâmetro é preservado — "havia um token" é informação
  útil; o valor não pode estar lá.

O mascaramento cobre só a query porque a query é o **único** conteúdo de
requisição que chega a ser registrado.

## Consequências

- Um `500` passa a ser rastreável ponta a ponta: o usuário cita o `request_id`
  da resposta e ele aparece na linha de acesso e em qualquer log da requisição.
  **Verificado contra a API rodando**, não deduzido.
- Duração por requisição existe, o que é a base para responder "essa rota está
  lenta?".
- Uma requisição que falha com exceção **ainda produz linha de acesso** — as
  requisições que mais importam não podem ser as ausentes do log.
- `LOG_LEVEL` entra na configuração tipada (Item 17), com `INFO` de padrão
  porque é onde a linha de acesso vive.
- **Métricas e tracing ficam de fora**, por instrução do próprio item: *"entram
  depois de existir onde observá-los"*. Não há onde.
- O log vai para **stdout**, sem arquivo e sem rotação. É o que um container
  espera; quem coleta é o ambiente.
