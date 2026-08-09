# ADR-009: Controles de abuso na borda

## Status

Aceita em 2026-08-09, no Item 27 do learning path.

## Contexto

O item pede para **modelar as ameaças antes de escrever código** (*"estudar
primeiro threat modeling do login e upload"*). O modelo achou quatro coisas, e
duas delas não eram suposições:

**1. Login sem limite.** O `user_login_controller` já responde a mesma mensagem
para "usuário não existe" e "senha errada" — há um comentário no código
explicando que é para não vazar quais e-mails existem. Mas nada impedia dez mil
tentativas por minuto contra um e-mail conhecido. E o bcrypt torna **cada
tentativa cara para o servidor**, então o login era alvo de credencial *e* de
exaustão de CPU.

**2. O cadastro desfaz o cuidado do login.** Ele responde
`"Email already registered"` — exatamente o que o login se recusa a revelar. A
proteção anti-enumeração estava furada pela porta ao lado.

**3. O upload inteiro ia para a memória antes da checagem de tamanho.** Toda
rota de upload faz `content = await file.read()` e os validators só então
verificam os 4MB. Um POST de 2GB era bufferizado antes de ser recusado, e como
o cadastro é aberto, qualquer um chegava lá.

**4. Nenhum header de segurança.**

As duas primeiras **se combinam**: enumere pelo cadastro, ataque por força
bruta o que achou.

## Decisão

**Rate limit em memória, sem Redis e sem biblioteca.** O item é explícito:
*"escolher Redis somente se o limite precisar ser compartilhado entre
réplicas"*. Há um processo e não há produção. São ~40 linhas; `slowapi` traria
máquina de Redis para um problema que ninguém tem.

Os custos dessa escolha, declarados em vez de descobertos depois: **os
contadores zeram no restart**, e **uma segunda réplica dobraria o limite
efetivo**. Aceitáveis agora, e deixam de ser no dia em que isto rodar mais de
uma vez.

**Janela deslizante, não balde de relógio.** Com baldes fixos, um atacante ganha
`limite` tentativas às 11:59:59 e mais `limite` às 12:00:00 — o dobro em cada
fronteira.

**Contado por endereço do cliente, NÃO por e-mail.** Limitar por e-mail deixaria
qualquer um trancar a conta de uma vítima conhecida, queimando a cota de
propósito: trocaria risco de força bruta por negação de serviço.

**E o endereço vem do peer, não do `X-Forwarded-For`.** Confiar nesse header sem
um proxy na frente significa que qualquer cliente escolhe a própria identidade e
zera o próprio contador trocando uma string.

**O cadastro mantém a mensagem útil.** Enumerar dez e-mails continua possível;
dez mil, não. A solução completa é verificação por e-mail, que exige envio de
e-mail — não existe no projeto. Trade-off consciente, não descuido.

**Limite de corpo antes de bufferizar**, respondendo 413 em documento
problem+json como todo erro (ADR-005).

**Três headers**, cada um com motivo local: `nosniff` porque esta API serve
arquivos enviados por usuários; recusa de enquadramento porque ela não tem UI
própria; e `Referrer-Policy: no-referrer` porque uma URL assinada carrega token
na query e não pode vazar no `Referer`.

**Amendamento (2026-08-09): o enquadramento é decidido POR CAMINHO, e aplicar
`X-Frame-Options: DENY` a tudo foi um erro que quebrou o preview de PDF.**

Um PDF é exibido por `<object>` — e `<object>` **é** enquadramento. Imagens
continuaram funcionando porque `<img>` não é, então o sintoma se leu como "PDF
quebrou" e não como "um header está largo demais". Relatado do navegador; **os
testes deste item não pegaram**, porque afirmavam que o header estava
*presente*, e ele estava.

`SAMEORIGIN` não resolveria: o arquivo vem da porta da API e a página da porta
do frontend, que são origens diferentes. E com `STORAGE_BACKEND=s3` o arquivo
nem passa por este middleware — os dois backends se comportariam de forma
diferente, o que é pior que o bug.

As respostas de `/files/` passam a levar
`Content-Security-Policy: frame-ancestors` com as **mesmas origens já
confiadas para chamar a API** — o header moderno consegue dizer *quem* pode
embutir, coisa que o `X-Frame-Options` não consegue. Todo o resto mantém a
resposta mais estrita, nos dois headers.

## Consequências

- Força bruta e enumeração em massa deixam de ser gratuitas. **As três frentes
  provadas por quebra deliberada**, cada uma falhando o teste certo.
- **Limite conhecido do guarda de tamanho:** ele lê o `Content-Length`
  declarado. Uma requisição *chunked* não manda esse header e passa — a
  checagem de 4MB dos validators é o que a pega, depois de bufferizar, que é
  justamente o que se queria evitar. Fechar isso exige embrulhar o stream ASGI
  e contar bytes; vale no dia em que algo além de navegador e curl postar aqui.
- **A rotação de secrets é procedimento, não código**, e está no README porque
  um segredo que ninguém sabe trocar não é trocado. Registrado ali que trocar o
  `JWT_SECRET` **desloga todo mundo** — não há rotação sem interrupção, e
  suportar duas chaves simultâneas é o que permitiria.
- Os contadores em memória são a primeira coisa a revisar quando existir mais
  de uma réplica.
