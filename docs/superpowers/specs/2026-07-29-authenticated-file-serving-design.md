# Ciclo de feature — Servir arquivos com autenticação (backend)

Data: 2026-07-29.
Repositório afetado: `Refund-api`.
Este ciclo precede o ciclo de frontend e é pré-requisito dele.

Este ciclo segue o
[fluxo permanente da trilha](../../plans/learning-path-workflow.md).

## Motivação

Comprovantes e avatares são servidos por mounts estáticos do Starlette, **fora
da autenticação**. Verificado durante o levantamento:

```
GET /receipts/<uuid-real>   sem token nenhum   ->   200
```

Os nomes são UUIDv4, então na prática isto é uma **URL-capacidade**: quem
descobre o link tem acesso, e o mantém para sempre — inclusive depois de perder
acesso ao reembolso. Para um documento financeiro isso não é aceitável.

O gatilho de fazer isso **agora** é de ordem, não de urgência: o ciclo de
frontend vai construir o preview do comprovante, e o preview é implementado de
duas formas incompatíveis conforme a resposta. Com mount público, um
`<img src="/receipts/…">` resolve. Sem ele, o frontend precisa de `fetch` com
token → `blob URL` → `revokeObjectURL` no cleanup. Decidir depois significaria
reescrever a tela.

## Decisões tomadas no brainstorming

| Decisão | Escolha | Consequência |
|---|---|---|
| Comprovantes públicos? | Não | Rota autenticada substitui o mount |
| Avatares públicos? | Não | Mesmo tratamento, apesar do custo no cliente |
| Autorização do comprovante | Dono ou admin, 404 caso contrário | Consistente com BR-013 |
| Autorização do avatar | Qualquer usuário autenticado | O avatar já é visível a quem vê a lista |
| Como o driver entrega o arquivo | `read() -> bytes` | Sobrevive ao Item 22 sem mudar de assinatura |
| `filename` na resposta | Sai | O cliente não monta mais URL |
| `avatar_filename` na resposta | Vira `has_avatar` | O cliente só precisa saber se mostra foto ou gradiente |

## Rotas

```
GET /refunds/{refund_id}/receipt     dono ou admin
GET /users/{user_id}/avatar          qualquer usuário autenticado
```

**O comprovante responde 404 tanto para "não existe" quanto para "não é seu".**
Um 403 confirmaria que aquele id é real, dando a um atacante um oráculo para
enumerar reembolsos — exatamente o que a BR-013 evita hoje nas rotas de consulta
e exclusão. A mesma regra, no mesmo lugar: no controller.

O avatar não tem esse problema: qualquer autenticado pode ver qualquer um, então
não há o que vazar. Responde 404 quando o usuário não existe **ou** não tem foto.

## Por que `read() -> bytes` e não um caminho de arquivo

`FileResponse(path)` seria mais eficiente — o Starlette faz streaming, define o
`Content-Type` sozinho e suporta *range requests* de graça. Mas exigiria o driver
expor um **caminho no sistema de arquivos**, e essa afirmação é precisamente a
que o **Item 22** (object storage) invalida. Trocaríamos a assinatura de novo
dentro de poucos ciclos.

`read(filename) -> bytes` não afirma nada sobre onde o arquivo mora: quando o
Item 22 chegar, muda a implementação e a interface fica. O custo é manter até
4 MB em memória por requisição — um teto que já existe
(`upload_info["MAX_FILE_SIZE_BYTES"]`) e é pequeno.

O `Content-Type` sai de `mimetypes.guess_type` sobre a extensão do arquivo
armazenado, **não** de um header do cliente — mesmo princípio que os validators
de upload já aplicam, e pelo mesmo motivo: o header vem de qualquer cliente HTTP
e é pouco confiável.

**Arquivo ausente no disco com linha no banco responde 404, não 500.** Hoje isso
não ocorre (conferido: zero casos), mas é o inverso do arquivo órfão e o
**Item 21** mantém a porta aberta.

Concretamente: `read` deixa o `FileNotFoundError` do `open` subir — o driver não
inventa erro de domínio, porque ele não sabe o que "não encontrado" significa
para quem chama. Quem traduz é o controller, que levanta `HttpNotFoundError` com
a mesma mensagem que já usa para reembolso inexistente. Assim a resposta é
indistinguível de "esse id não existe", que é o comportamento desejado.

**Sem `Content-Disposition: attachment`.** O arquivo é devolvido para exibição,
não para download forçado — quem decide como apresentar é o cliente, que no
frontend vai transformá-lo em `blob URL` para o preview.

## A armadilha: `filename` tem dois usos

`filename` não serve só à resposta. O `refund_deleter_controller` lê
`refund["filename"]` do resultado de `select_refund_by_id` para apagar o arquivo
do disco.

Remover o campo de `__to_refund` quebraria a exclusão — e, como o teste daquele
controller usa mock, **a suíte poderia não perceber**. É a mesma forma de falha
que produziu o Critical do ciclo anterior, quando mover `user_id` quebrou dois
controllers cujos mocks ainda devolviam o formato antigo.

A separação correta:

- **O que o repositório devolve é dado interno** e continua com `filename` e
  `avatar_filename`.
- **O que vira resposta HTTP é contrato** e não os tem.

Hoje as duas coisas estão coladas pelo `**refund` nos serializadores.

## O serializador compartilhado

Com a mudança, três controllers — listagem, detalhe e criação — passam a fazer a
mesma transformação: remover `filename`, converter `avatar_filename` em
`has_avatar`, e serializar `created_at` como ISO. Três cópias da mesma regra é
como um dos campos fica para trás numa mudança futura.

Nasce `src/controllers/refund_serializer.py`, consumido pelos três.

Vale registrar por que esta abstração se justifica **agora** e não antes: até
este ciclo, cada controller tinha uma forma de resposta própria e a semelhança
entre eles era coincidência. A partir daqui os três produzem **a mesma** forma a
partir da **mesma** fonte — a duplicação passa a ser risco, não repetição.

O `refund_reviewer_controller` fica **de fora**: ele lê de
`RefundStatusRepository.select_for_update`, cuja forma achatada já está
documentada como divergente no `UC-007`.

Consequência a registrar honestamente: depois deste ciclo a resposta da revisão
diverge em **três** pontos, não mais em um — ela carrega `user_id` no topo,
`filename`, e nenhum `has_avatar`. A decisão anterior de que a tela de revisão
não consome esse corpo (ela invalida a query e refaz o `GET`) é o que mantém
isso inofensivo. O `UC-007` precisa ser atualizado para descrever as três
diferenças, não só a primeira.

## Forma da resposta

```
GET /refunds/58
{
  "type": "Refund", "count": 1,
  "attributes": {
    "id": 58, "name": "Estacionamento", "category": "transport",
    "amount_in_cents": 4500, "status": "approved",
    "created_at": "2026-07-28T17:00:25.325003",
    "user": { "id": 13, "name": "Validacao Visual", "has_avatar": true }
  }
}
```

Sem `filename`. Sem `avatar_filename`.

## Camadas

Preserva a Clean Architecture existente: rota → composer → view → controller →
repository/driver.

```
src/drivers/file_storage.py                      + read(filename) -> bytes
src/drivers/interfaces/file_storage_interface.py + a mesma assinatura
src/controllers/refund_serializer.py             (novo) forma de resposta compartilhada
src/controllers/receipt_finder_controller.py     + interface
src/controllers/avatar_finder_controller.py      + interface
src/views/receipt_finder_view.py
src/views/avatar_finder_view.py
src/main/composer/receipt_finder_composer.py
src/main/composer/avatar_finder_composer.py
src/main/routes/refund_routes.py                 + GET /{refund_id}/receipt
src/main/routes/user_routes.py                   + GET /{user_id}/avatar
src/main/server/server.py                        − os dois mounts estáticos
src/controllers/refund_lister_controller.py      usa o serializador
src/controllers/refund_finder_controller.py      usa o serializador
src/controllers/refund_creator_controller.py     usa o serializador
```

`src/models/repositories/refunds_repository.py` **não muda**: `__to_refund`
continua devolvendo `filename` e `avatar_filename`, porque são dados internos.

Cada arquivo com lógica ganha seu `_test.py` ao lado. Composers seguem sem teste,
pela convenção vigente.

## Testes

- **Autorização do comprovante** — dono recebe 200; solicitação alheia dá 404;
  id inexistente dá 404; admin recebe qualquer uma.
- **Avatar** — qualquer autenticado recebe 200; usuário sem foto dá 404; usuário
  inexistente dá 404.
- **Driver** — `read` devolve os bytes gravados; arquivo inexistente levanta o
  erro esperado, e a rota o traduz em 404.
- **Serializador** — remove `filename`, emite `has_avatar` a partir de
  `avatar_filename` (inclusive `False` quando é `None`), e serializa `created_at`.
- **O teste que a mudança exige:** a exclusão continua apagando o arquivo do
  disco. É o comportamento que a remoção de `filename` ameaça, e o único que um
  mock desatualizado esconderia.

## Verificação

```bash
pytest
pylint src
```

Mais uma passada ponta a ponta contra a API real: baixar o comprovante como
dono, como admin e como terceiro; baixar avatar de outro usuário; conferir que
`GET /receipts/<uuid>` agora responde **404** (mount removido); e conferir que a
exclusão de um reembolso pendente ainda remove o arquivo do disco.

## Consequências para o ciclo de frontend

Este ciclo **muda o contrato outra vez**, e a mudança se soma à do ciclo
anterior, que também não foi implantado. O frontend precisará, de uma vez:

- Ler o solicitante de `user` em vez de `user_id` (ciclo anterior).
- Parar de montar URL de comprovante: `getReceiptUrl(filename)` em
  `src/lib/api.ts` deixa de existir, e `PageRefundDetails` passa a buscar
  `/refunds/{id}/receipt` com o token, criando um `blob URL` e revogando-o no
  cleanup.
- Usar `has_avatar` para decidir entre foto e gradiente, e buscar
  `/users/{id}/avatar` da mesma forma.

**Backend e frontend continuam tendo de ir para produção juntos**, agora por dois
motivos acumulados em vez de um.

## Documentação a atualizar no fechamento

- `docs/decisions/ADR-003-local-receipt-storage.md` — o acesso deixa de ser
  público; registrar a data e o raciocínio da URL-capacidade.
- `docs/business-rules.md` — regra de acesso ao comprovante e ao avatar.
- `docs/use-cases/UC-007-review-refund.md` — as TRÊS divergências da resposta da
  revisão, não só a do `user_id`.
- `docs/use-cases/UC-004`, `UC-005`, `UC-003` — `filename` sai, `has_avatar`
  entra.
- `docs/use-cases/` — **UC-010 — Baixar comprovante** e **UC-011 — Baixar foto de
  perfil**, com entrada no `docs/index.md`.
- `README.md` e a coleção do Postman.
- `docs/learning-path-progress.md` e `docs/plans/current-state.md` no fechamento.

## Fora de escopo

- **URL assinada de vida curta** — resolveria privacidade sem custar N fetches
  por página, mas é território do **Item 22** e exige mais maquinário. Registrada
  como alternativa não escolhida.
- **Item 21** (consistência banco+arquivo) e **Item 22** (object storage).
- O frontend, que tem spec própria depois desta.
