# Retrospectiva de processo

Este documento não é fonte de requisitos. Ele registra **como este projeto foi
construído** — onde houve retrabalho, o que o causou e o que fazer diferente no
próximo projeto. É o par do [diário de aprendizado](learning-path-progress.md):
o diário guarda o que foi aprendido *sobre código*; este guarda o que foi
aprendido *sobre o processo*.

Escrito em 2026-08-09, no fim da trilha (Itens 1–31 concluídos).

## Método e limites desta análise

Reconstruída a partir de três fontes: os 187 commits do `Refund-api`, os 144 do
`Refund-FrontEnd`, e o [diário](learning-path-progress.md) (5.875 linhas) mais o
[estado atual](plans/current-state.md).

**Onde há inferência, o texto diz.** As datas e contagens vêm do Git e são
verificáveis; as atribuições de causa são leitura de evidência, não confissão de
ninguém. A análise só é possível porque o diário registra as coisas
desconfortáveis — os experimentos inválidos, as premissas falsas, os checks
escritos errados. Um diário que só registrasse sucessos não sustentaria nenhuma
conclusão aqui.

## A inversão de origem

A ordem em que as coisas nasceram, medida no Git:

```
2026-06-15  frontend começa            af7bfe4  (ícones, componentes)
2026-07-12  backend começa             9510354  (estrutura, CRUD)
2026-07-14  frontend: auth + formulário + validação
2026-07-15  migração SQLite → PostgreSQL
2026-07-19  learning_path.md e arquitetura_ideal_adaptada.md
2026-07-20  desenvolvimento_com_ia.md  ← a metodologia doc-first
2026-07-20  docs/ nasce                febfd89
2026-07-22  a trilha começa            2c28133  (Item 1)
2026-08-09  a trilha termina                    (Item 31)
```

O guia `desenvolvimento_com_ia.md`, cuja tese é *"documentar antes de
programar"*, foi escrito **cinco semanas depois do primeiro commit do frontend e
oito dias depois do primeiro do backend**. E as mensagens dos commits daquele dia
dizem o que aconteceu, literalmente:

```
282f0dd  docs: add current Refund use cases
b4b13b6  docs: record current Refund architecture decisions
```

`current`, `record`. Documentação como **arqueologia do que já existia**, não
como decisão prévia.

**A conclusão que importa:** o problema deste projeto não foi documentação
insuficiente nem malfeita — a documentação produzida é boa e é o motivo de esta
retrospectiva existir. O problema foi **ordem de decisão**. Decisões caras de
reverter foram tomadas por descoberta, depois de já terem sido construídas em
cima.

Documentação não conserta isso. Decidir as coisas baratas antes das caras,
conserta.

## As quatro fontes de retrabalho

### 1. Um ciclo demolido pelo seguinte, com um dia de intervalo

O caso mais caro e o mais claro.

| | Ciclo do shell (26–27/07) | Ciclo do restyle (27/07) |
|---|---|---|
| Sidebar | integra `react-pro-sidebar`, tematizada | `react-pro-sidebar` **removido** |
| Ícones | entra `@mui/icons-material` | `@mui/*` e `@emotion/*` **removidos** |
| Cor | paleta própria de tokens; **16 arquivos migrados** | paleta substituída pelos tokens do shadcn |
| Componentes | `atoms/` + `molecules/`, 692 linhas | **deletados**; nasce `ui/`, 2033 linhas |
| Variantes | `tailwind-variants` + `classnames` | ambos **removidos**; entra `cva` + `clsx` |

Um ciclo inteiro virou entulho no dia seguinte. O gatilho está registrado no
diário sem eufemismo:

> *"O gatilho foi estético — a estilização anterior não agradava."*

**Causa:** a direção visual nunca foi decidida antes de ser construída. Foi
decidida **vendo o resultado pronto** — forma legítima de decidir, mas que aqui
custou dois ciclos de construção só para chegar ao momento da decisão.

Havia inclusive um sinal de alerta anterior, registrado e não lido como tal: a
paleta do ciclo do shell apagava as cores padrão do Tailwind
(`@theme { --color-*: initial }`), o que tornava o design system uma **ilha
fechada** — colar qualquer componente de qualquer registry produzia um elemento
sem estilo. Uma decisão que fecha portas foi tomada sem que ninguém tivesse
decidido ainda se as portas seriam usadas.

**O que teria evitado:** escolher o design system é decisão de **uma tarde**
(abrir três candidatos, olhar três telas de cada) e determina semanas de código.
Antes de migrar N arquivos para uma convenção, construa **uma tela real** com ela
e olhe. Uma tela custa uma hora; dezesseis arquivos custam um ciclo.

### 2. O contrato entre os repositórios só virou executável no Item 25 — de 31

Dois repositórios independentes que só conversam por HTTP. O contrato entre eles
viveu em prosa e em dois conjuntos de tipos mantidos à mão, e quebrou o app duas
vezes:

| Data | Mudança no backend | Efeito no frontend |
|---|---|---|
| 29/07 | `user_id` no topo → objeto `user` aninhado | ciclo inteiro só para absorver o contrato |
| 30/07 | quarto status `paid` | `refundStatusSchema` era um `z.enum` de três valores |

A segunda não foi risco teórico. Foi **quebra ativa vivendo na `main`**: o
backend já respondia `"paid"` e o primeiro reembolso pago derrubaria a Home
inteira em `isError`, para todo usuário. Foi descoberta pelo ciclo seguinte por
acaso de ordem, não por um mecanismo.

O mecanismo que teria pegado as duas — testes de contrato que ficam vermelhos
quando os lados divergem — chegou no **Item 25, em 09/08**. O diário registra
que, ao ligá-los, *"as duas divergências históricas viram teste vermelho,
provado por quebra"*. Ou seja: a ferramenta certa existia conceitualmente o tempo
todo e foi construída por último.

**Corolário sobre "backend primeiro".** A estratégia de fazer o backend antes do
frontend foi deliberada e é razoável — **mas só funciona com contrato
verificável**. Sem ele, "backend primeiro" significa, na prática, "o frontend
descobre a mudança quando quebra".

**O que teria evitado:** com dois repositórios, o contrato é a **primeira** peça
de infraestrutura, não a vigésima quinta. Não precisa ser sofisticado: um JSON
versionado com as respostas reais e um teste de cada lado comparando contra ele.
Custa uma tarde.

### 3. "Testei a peça, não a montagem" — quatro ocorrências

O padrão que o próprio diário nomeou e contou:

| Item | O que o teste afirmava | O que estava quebrado |
|---|---|---|
| 14 | as mensagens de validação estão traduzidas | elas eram **inalcançáveis**; um envio vazio produzia quatro em inglês |
| 23 | exceção → envelope mapeia certo | o handler estava na **classe errada**; o 404 do router escapava |
| 24 | o filtro de log funciona | ninguém provava que ele estava **instalado** |
| 27 | o header `X-Frame-Options` está presente | estava — e o preview de **PDF parou de renderizar** |

Nas quatro, a suíte estava verde. Nas quatro, quem achou foi **rodar a coisa de
verdade** — API real ou navegador.

A frase do diário que generaliza melhor, do Item 14:

> *"Um catálogo completo não prova que suas chaves chegam à tela."*

**O que teria evitado:** um punhado de testes que atravessam o sistema pela borda
real desde cedo — HTTP de verdade numa ponta, navegador na outra. O projeto
acabou construindo exatamente isso (`httpx` + testes de API no Item 25), e está
registrado que ele **pega o bug do Item 23 quando reintroduzido**. De novo: a
ferramenta certa, tarde demais.

### 4. Validação em navegador acumulada em lotes

Vários itens foram mesclados e empurrados sem passada de navegador — o Item 22
por decisão explícita, outros por indisponibilidade. Em 09/08 houve uma sessão de
**18 verificações de uma vez**, que encontrou **dois bugs de i18n**, ambos na
primeira tela que qualquer usuário vê, ambos invisíveis à suíte inteira (que roda
contra MSW, ou seja, contra o payload que nós mesmos escrevemos).

**O que teria evitado:** navegador **antes do merge**, não antes de confiar.
Cinco minutos por ciclo contra uma sessão inteira de recuperação.

## Uma quinta lição, sobre a forma da documentação

Distinta das quatro acima porque não produziu retrabalho de código, e sim
retrabalho de verificação.

O [`current-state.md`](plans/current-state.md) catalogou **sete** vezes o mesmo
defeito: um bloco que **afirma um estado** (SHAs das `main`, branches mescladas
ou não, datas de última verificação) nasce verdadeiro e morre em silêncio. A
sétima foi encontrada auditando a documentação, não por alguém tropeçar.

**A oitava foi encontrada ao escrever esta retrospectiva:** o documento descrevia
as duas branches do Item 31 como "não mescladas". As duas estavam mescladas —
`perf/self-host-font` é literalmente o HEAD da `main` do frontend.

O documento já tinha derivado a regra certa e ela continua valendo: **descreva
como descobrir o estado, não afirme qual é.** O que a oitava ocorrência
acrescenta é que a regra precisa valer para *branches mescladas* e *itens
concluídos* também, não só para SHAs.

## O que NÃO foi retrabalho

Registrado com o mesmo peso, para que uma leitura futura não corrija a coisa
errada.

- **O Item 10 feito duas vezes foi desenho, não desperdício.** A primeira
  passagem integrou uma lib pronta; a segunda possuiu o código. São os dois lados
  de uma decisão real de engenharia. Numa trilha cujo método declarado é
  *"aprendizado acima de velocidade"*, isso é o produto.
- **Parar no Item 31 foi acerto.** A medição mostrou 81% do bundle em
  bibliotecas sem gordura e ~0,15s de ganho disponível em 2,9s. A resposta foi
  parar, e está escrita.
- **Dispensar Redis (Item 27), fila (Item 28) e Oxlint (Item 16), com motivo
  numérico**, é item cumprido conscientemente pela metade — não item incompleto.
- **A honestidade do registro é o maior ativo do projeto.** Frases como *"não
  observado"*, *"o CHECK estava errado, não o código"*, *"terceira vez na sessão
  que quase concluí de um experimento inválido"* são raras e são a razão de esta
  análise existir.

## O que fazer diferente no próximo projeto

Em ordem de retorno:

1. **Decida na ordem inversa do custo de mudança.** Antes da segunda tela:
   design system, forma do contrato de API, estratégia de estado, versão de
   runtime. São decisões de horas que determinam semanas.
2. **Com dois repositórios, o contrato é a primeira infraestrutura.** Respostas
   reais versionadas e um teste de cada lado, antes da terceira feature.
3. **Um teste que atravessa a montagem inteira, desde o dia um.** Um só. HTTP
   real numa ponta, navegador na outra. As quatro ocorrências de "testei a peça"
   morrem nele.
4. **Navegador antes do merge, sempre.** Cinco minutos. Não acumule.
5. **A versão do runtime é decisão de dia zero.** Este projeto nasceu em Python
   3.9 *"porque foi assim que começou"* e precisou, no fim de tudo, de um ciclo
   de 8 tasks para sair — com 37 alertas de segurança acumulados e um teste
   quebrando já na primeira task (`HTTPStatus(422).phrase` mudou de string no
   3.13). Escolher o runtime custa cinco minutos no início e um ciclo no fim.

## A meta-lição

**Uma metodologia doc-first foi aplicada a um projeto que já existia.** O
`desenvolvimento_com_ia.md` está certo; ele só chegou no dia 35, depois de o
projeto já ter respondido sozinho, por construção e desgosto, as perguntas que
ele faz.

No próximo projeto ele é o **primeiro** arquivo.

## Calibragem

Para que esta retrospectiva não seja lida como um balanço negativo: em cerca de
oito semanas — das quais os **18 últimos dias** foram os mais produtivos —
saíram 31 itens de trilha, dez ciclos de feature, 334 testes mockados e 72 de
integração no backend, 305 no frontend, CI nos dois repositórios, container,
object storage com URLs assinadas, i18n completo em dois idiomas e um orçamento
de performance medido.

O retrabalho foi real e está mapeado acima. Ele não foi a característica
dominante do percurso.
