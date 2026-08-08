# ADR-005: Erros padronizados com Problem Details (RFC 9457)

## Status

Aceita em 2026-08-08, no Item 23 do learning path.

## Contexto

A API devolvia erro em **duas formas**:

```python
# nossos erros de negócio, via src/errors/error_handler.py
{"detail": "Only pending refunds can be deleted"}          # string

# validação do próprio FastAPI, antes de o nosso código rodar
{"detail": [{"msg": "...", "loc": [...], "type": "..."}]}  # lista
```

O frontend carregava uma função cuja única razão de existir era distinguir as
duas (`getApiErrorMessage`, em `src/lib/api.ts`), consumida por **7 telas**.

Três limitações concretas:

1. **Nada legível por máquina.** "Já foi pago por outro admin" e "só um
   aprovado pode ser pago" são ambos `422` com strings diferentes. Para tratar
   os dois casos de forma diferente, a UI teria que **comparar texto** — que
   quebra no dia em que alguém traduzir a mensagem. O projeto acabou de
   traduzir a interface inteira no Item 14; **texto de UI não pode ser chave de
   lógica**.
2. **Sem erro por campo.** Uma falha de validação não conseguia ser ancorada no
   campo do formulário.
3. **`500` sem correlação.** `{"detail": "Internal server error"}`. O usuário
   relatava, e não havia como ligar o relato a nada.

## Decisão

Adotar o envelope da RFC 9457 para **toda** resposta de erro, servido como
`application/problem+json`:

```json
{
  "type": "about:blank",
  "title": "Unprocessable Entity",
  "status": 422,
  "detail": "Only pending refunds can be deleted",
  "instance": "/refunds/12",
  "request_id": "e52a6019-326f-47f4-8bd7-20600fd4a21b",
  "errors": [{"field": "password", "message": "Field required"}]
}
```

**Três handlers globais, nenhum dos 38 pontos que levantam erro foi tocado.**
`error_handler` e os controllers continuam levantando exatamente o que
levantavam; o **formato** passou a ser decidido num lugar só. Se um `raise`
tivesse precisado mudar, seria sinal de que a decisão estava errada.

**`detail` continua sempre string**, e isso não é acidente — é string na RFC
também. É o que faz esta migração não ter momento quebrado: um cliente que lê
`.detail` segue funcionando, **inclusive para os erros de validação**, que
antes chegavam como lista. A informação por campo foi para a extensão `errors`
em vez de sobrecarregar o `detail`.

**`type` fica em `about:blank`**, que é o valor que a própria RFC usa para "não
há código mais específico que o status". Inventar 19 códigos sem nenhum
consumidor pedindo seria abstração antes da necessidade; o campo existe e um
código específico entra no dia em que um cliente realmente ramificar — a mesma
regra de "extrair no segundo uso real" que o projeto aplicou no Item 11.

**`request_id`** é uma extensão, não campo da RFC. Um middleware gera um UUID
por requisição, e ele vai no corpo **e** no header `X-Request-Id`. O id é
sempre **gerado pela API, nunca lido de um header do cliente**: confiar num
valor de fora deixaria qualquer um escolher o que aparece nos nossos logs, que
é como funciona log forging. O **Item 24** vai reusar esse mesmo id nos logs em
vez de criar outro.

## Consequências

- Um consumidor novo precisa entender **um** formato. O ramo do frontend que
  tratava a lista foi removido por estar morto.
- Um `500` passa a ser reportável: o usuário cita o `request_id` e ele casa com
  a requisição.
- O `500` continua **deliberadamente genérico** no `detail` — vazar a mensagem
  original entregaria stack trace ou mensagem de banco ao cliente. Há teste
  afirmando que a mensagem original não aparece no corpo.
- **O handler é registrado na `HTTPException` do Starlette, não na do FastAPI.**
  A do FastAPI é subclasse, então registrar na base cobre as duas; o inverso
  não. O router levanta a do Starlette para rota desconhecida, e registrar a
  subclasse deixava esses `404` escaparem com o formato antigo. **Foi
  descoberto perguntando à API rodando por uma rota inexistente, não lendo o
  código.**
- **Erro de registro de handler é invisível para a suíte.** Os testes chamam os
  handlers diretamente, então provam o mapeamento exceção→envelope, e não que
  estão ligados à exceção certa. Pegar isso exigiria o `TestClient` do FastAPI
  e portanto `httpx` como dependência, que este projeto já dispensou duas
  vezes. Registrado como pendência.
- Os casos de uso **não mudam**: nenhum deles descrevia o formato do corpo de
  erro além do status e da mensagem, e a mensagem continua em `detail`.
