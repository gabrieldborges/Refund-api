# ADR-007: Testes de API por HTTP e contrato versionado com o frontend

## Status

Aceita em 2026-08-09, no Item 25 do learning path.

## Contexto

Duas lacunas distintas, com histórico documentado.

**1. Nenhum teste passava por uma rota.** O Item 19 criou a infraestrutura de
integração e chegou a 32 testes — todos **abaixo do HTTP**: repositories,
migrations, contenção de lock, object storage, consistência de arquivo.
Middleware, roteamento, composer, view e o registro dos exception handlers não
eram exercitados por nada.

Isso tem ficha corrida. **Três itens seguidos entregaram um defeito da mesma
forma — uma peça correta que não estava corretamente ligada:**

| Item | Estava certo | Não era testável |
|---|---|---|
| 23 | o handler | o **registro** dele na classe de exceção certa |
| 24 | o filtro | a **instalação** dele no handler |
| 2026-08-09 | a mensagem traduzida | ela ser **alcançada** |

Os três foram achados rodando a aplicação à mão.

**2. O contrato com o frontend era suposição dos dois lados.** O frontend
valida respostas com schemas Zod escritos à mão e roda os testes contra
handlers MSW também escritos à mão. **Quatro divergências reais** já
aconteceram: o `refundStatusSchema` sem `"paid"` (derrubaria a Home de todo
usuário no primeiro reembolso pago), `user_id` virando `user` aninhado, a
fixture da listagem respondendo página 1 para um pedido de página 2, e a
fixture de reviews fora da ordem cronológica que o `UC-013` promete.

## Decisão

**`httpx` entra como dependência de teste.** A pendência registrada no Item 23
previa exatamente isto: *"se um dia a conta virar, é uma dependência só de
teste e destravaria testes de rota de verdade"*. O Item 25 pede "um fluxo de
refund via cliente FastAPI" — a conta virou.

**Testes de API por HTTP** (`src/test_integration/api_test.py`), contra
PostgreSQL e MinIO reais: health, autenticação, os envelopes de erro, o fluxo
completo de um reembolso e o download por URL assinada **sem header**.

Repontar a aplicação para o banco de teste é uma linha **só porque o Item 17
tornou o engine preguiçoso**. Construído no import, como era antes, a conexão
já existiria antes de qualquer fixture rodar.

**Contrato versionado.** `src/test_integration/contract_test.py` dirige a API
real e grava as respostas em `contract/`, comparando com o que está commitado
e **falhando se divergirem**. Valores voláteis (ids, timestamps, tokens) são
normalizados para placeholders **do mesmo tipo** — um id vira outro inteiro,
não a string `"<id>"` —, senão o arquivo mentiria sobre a forma que se propõe
a documentar.

**São DOIS arquivos, e a divisão foi ditada pelo linter do frontend, não por
gosto.** O `eslint-plugin-boundaries` (Item 9) classifica `src/schemas` e
`src/test` como camada `app` e proíbe uma feature importar de lá. Um teste da
feature de reembolsos não pode, portanto, ler um arquivo que também carregue o
payload de login. O contrato se dividiu **exatamente na costura que os schemas
já tinham** — o que é um bom sinal de que a regra descreve algo real.

| Arquivo | Destino no frontend | Validado por |
|---|---|---|
| `contract/refunds.json` | `src/features/refunds/contract/` | schemas da feature |
| `contract/app.json` | `src/test/contract/` | `loginResponseSchema` e o envelope de erro |

## Consequências

- Erro de **registro** de handler passa a ser detectável. Provado: com o bug do
  Item 23 reintroduzido, os testes de unidade continuam **verdes** e os HTTP
  **falham**.
- As duas divergências históricas de contrato viram teste vermelho. Provado
  removendo `"paid"` do enum e devolvendo `user_id` ao topo.
- **O QUE ISTO NÃO COBRE, e precisa ser lido antes de confiar no arquivo:** a
  cópia entre os dois repositórios é **manual**. O CI do backend falha se a API
  mudou e o contrato não foi regerado; o do frontend falha se os schemas
  discordam do arquivo. **Nenhum dos dois percebe um contrato regerado que
  nunca foi copiado.** É o preço de dois repositórios independentes, e tem a
  mesma forma do problema dos SHAs que o `current-state.md` já registrou seis
  vezes: nasce verdadeiro e morre em silêncio.
- Os testes de `file_routes_test.py` **continuam chamando a função direto**, e
  agora por escolha: cobrem lógica, rodam em milissegundos sem container, e o
  que eles nunca poderiam cobrir — que a rota está ligada — passou a ser
  coberto por HTTP.
- Achado ao capturar as respostas: **a API tem três estilos de envelope**.
  Login e URL assinada são planos; reembolsos usam `{type, count, attributes}`;
  a listagem acrescenta paginação no mesmo nível. Não foi unificado neste item
  — mudaria contrato — mas agora está **documentado por um arquivo**, não pela
  memória de quem leu o código.
