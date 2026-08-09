# ADR-008: Cobertura como diagnóstico, sem portão no CI

## Status

Aceita em 2026-08-09, no Item 26 do learning path.

## Contexto

Nenhum dos dois repositórios media cobertura. 317 testes no backend e 304 no
frontend, e **zero visibilidade** sobre o que eles não tocavam — não havia como
responder "qual guarda de autorização não tem teste?".

## Decisão

**Medir branch coverage nos dois repositórios, e não reprovar em nenhum
número.**

A parte de medir é óbvia. A de não reprovar precisa de justificativa, e ela é
local, não filosófica: **os três defeitos mais recentes deste projeto viviam em
linhas que a cobertura reportaria como cobertas.**

| Defeito | Linha coberta? | Teste pegava? |
|---|---|---|
| Item 23 — handler registrado na classe errada | **sim** | não |
| Item 24 — filtro nunca instalado no handler | **sim** | não |
| 2026-08-09 — mensagem traduzida inalcançável | **sim** | não |

Um portão num número dá uma sensação de segurança que os fatos deste projeto
contradizem, e o caminho mais barato para subir a porcentagem é escrever
asserções fracas. O relatório é **lugar para procurar**, não nota para passar.

**Branch, não só linha.** Um `if` conta como dois caminhos. Foi só isso que
tornou visível que o `error_handler` — reportado como coberto — nunca tinha
executado seu caminho de erro inesperado.

**O que sai do relatório**, e cada exclusão tem motivo:

| Excluído | Porquê |
|---|---|
| `*_test.py`, `conftest.py` | teste medindo a si mesmo infla o número e esconde o sinal |
| `interfaces/` | corpo de método abstrato é um `pass` que nunca executa por construção — treze arquivos a 80% eram a coisa mais barulhenta do primeiro relatório e não significavam nada |
| `entities/` | definição declarativa de tabela: dado, não lógica |
| `components/ui/**` (frontend) | copiado do registry do shadcn; `sidebar.tsx` sozinho é maior que a maioria das features daqui e enterrava o código do projeto |

## Consequências

- **O item produziu testes, não um número.** Quatro achados reais foram
  fechados: o caminho de 500 do `error_handler`, o ramo `s3` do
  `build_storage` (que é o que produção usaria e nunca tinha sido executado), a
  guarda do `useAuth` no frontend, e — o maior — **todos os fluxos de admin,
  que estavam a 0% por HTTP**: pagamento, revisão e as rotas de avatar.
- Backend 94% → **98%**; frontend 92,5% → **92,7%**. Os números são
  consequência, não objetivo.
- **O relatório do backend tem um ponto cego conhecido, documentado no
  `.coveragerc`.** O `return JSONResponse(...)` final de **toda** rota é
  reportado como nunca executado — treze linhas — e elas executam: as
  requisições devolvem 200/201 com o corpo certo, e o dado bruto do coverage
  mostra a linha imediatamente acima registrada.

  **A causa não foi isolada.** `concurrency = thread` foi tentado e não mudou
  nada; um app FastAPI isolado, sem o middleware deste projeto, registra a
  mesma instrução normalmente — o que aponta para composição do app, mas a
  sonda que provaria isso saiu errada e a hipótese fica **não provada**. Está
  registrado como observação, não diagnóstico.

  Nada foi excluído para escondê-lo: excluir transformaria uma distorção
  conhecida numa invisível.
- **Ler o relatório exige saber o que ele não vê.** Ele responde "isto nunca
  executou". Nunca responde "isto está certo".
