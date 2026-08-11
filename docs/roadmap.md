# Roadmap

## Como usar
Este documento registra somente intenções futuras, sem apresentá-las como
funcionalidades implementadas ou requisitos atuais.

Os estados possíveis são:

- `Ideia`: intenção ainda não analisada.
- `Em análise`: proposta sendo detalhada, ainda não aprovada.
- `Aprovada`: funcionalidade aceita para planejamento, mas ainda não
  implementada.

## Ideias

- **Deploy.** A trilha endereçou os cinco bloqueios técnicos (CORS, configuração
  validada, object storage, container, CI), mas **escolher e configurar um
  provedor nunca foi feito** — e não é código. Enquanto não houver, "publicado"
  neste projeto significa publicado no GitHub.
- ~~**Foto de perfil na interface.** O backend serve avatar desde 2026-07-29 e
  `has_avatar` é sempre `false` porque nenhuma tela renderiza um. É o único
  item de produto ainda não implementado.~~ **CONCLUÍDO em 2026-08-11.** A foto
  aparece na sidebar, na lista de Time e na página do membro, e a pessoa define a
  própria por um diálogo aberto no cabeçalho da sidebar. `has_avatar` deixou de ser
  sempre falso: ele é o que decide se o cliente pede a URL assinada, e é por isso
  que a lista de Time não faz uma requisição 404 por linha.
- **Agregado por status cruzando usuários.** Não existe endpoint que some por
  status para *todos* os usuários, então o card de dinheiro da Home mostra, para
  o admin, o total solicitado em vez de aprovado + pago. **Absorvida pelo Ciclo 2
  (Dashboard)** do [panorama das três telas](plans/2026-08-11-tres-telas-panorama.md):
  o `GET /refunds/summary` planejado lá é exatamente esse agregado.
- **Cargo na empresa.** A tela de Time exibiria o cargo de cada pessoa, mas
  `users` não tem o campo e nada o preencheria — a coluna mostraria "—" para
  todos. Descartado no planejamento de 2026-08-11; a lista mostra o papel
  (`role`) no lugar. Só vale a pena com um caminho de escrita: o admin editando
  o cargo na página do usuário.

- **Trocar a paleta de gráficos pelas cores validadas.** A paleta atual
  (`chartPalette.ts`: `#1D3557`, `#457B9D`, `#A8DADC`, `#F1FAEE`, `#E63946`)
  **falha 4 das 6 checagens** do validador de paletas nos dois modos, medido em
  2026-08-11. A grave: `#A8DADC` (aprovada) e `#F1FAEE` (paga) têm **ΔE 12,9 em
  visão normal**, abaixo do piso de 15 — difíceis de distinguir mesmo com visão de
  cor completa. As demais: faixa de luminosidade, piso de croma e contraste contra
  a superfície.

  O Ciclo 2 do Dashboard **mitigou** no gráfico empilhado (gap de 2px, legenda com
  quadrados, tooltip por segmento) em vez de corrigir, porque trocar a paleta muda
  a cor da rosca já entregue na tela de revisão. **Codificação secundária não
  desculpa o piso de visão normal** — esta é uma dívida de acessibilidade aberta.

  Quatro slots que passam nas duas modalidades: `#2a78d6`, `#eb6834`, `#1baf7a`,
  `#eda100`. Preservar o caráter azul/teal atual **não é possível** em quatro
  slots — foi testado, e dois azuis ficam em ΔE 14,4.

## Em análise

- ~~**Subir a versão do Python.** O projeto roda 3.9, que já não recebe
  correção de segurança, e a imagem de produção é construída sobre ela; o
  `boto3` já anunciou o fim do suporte. É a pendência mais grave registrada, e
  provavelmente destrava boa parte das 37 vulnerabilidades que o Dependabot
  aponta no `Refund-api` — eram 14 dois dias antes, sobre exatamente as
  mesmas dependências.~~ **ENDEREÇADO na branch `chore/python-313-upgrade`,
  mesclada em `18b8678`:** o projeto roda 3.13, a imagem de produção é
  construída sobre `python:3.13-slim`, e o terceiro ponto deixou de ser
  suposição — foi medido: os 19 advisories distintos por trás dos 37 alertas
  estão todos satisfeitos pelas versões fixadas nesta branch. Confira com
  `grep -n "FROM python" Dockerfile`. Relato completo em
  [`current-state.md`](plans/current-state.md).

## Aprovadas para planejamento

- **As três telas "em breve": Time, Dashboard e Calendário.** As três entradas
  desabilitadas da sidebar do frontend. Decisões e ordem de construção travadas
  em [`plans/2026-08-11-tres-telas-panorama.md`](plans/2026-08-11-tres-telas-panorama.md);
  cada uma virou um ciclo, a ser construído na ordem **Time → Dashboard →
  Calendário**, com spec+plan próprios no início de cada ciclo. Todas as três
  exigem backend novo — nenhuma é trabalho só de frontend.
  - ~~**Ciclo 1, Time (admin).** Listagem de usuários com busca por nome e página
    por usuário, somente leitura.~~ **CONCLUÍDO em 2026-08-11.**
  - ~~**Ciclo 2, Dashboard (todos, com escopo por papel).** Quatro gráficos em
    Nivo. Precisa de `GET /refunds/summary`, o agregado citado nas ideias acima.~~
    **CONCLUÍDO em 2026-08-11.** O `GET /refunds/summary` existe e atende também a
    ideia do agregado por status cruzando usuários. O card de dinheiro da Home
    **continua** mostrando o total solicitado: o endpoint que o corrige agora
    existe, mas mudar a Home ficou fora do escopo daquele ciclo.
  - ~~**Ciclo 3, Calendário (todos, com escopo por papel).** Grade do mês com
    contagem por dia e as solicitações do dia escolhido.~~ **CONCLUÍDO em
    2026-08-11.** As três telas estão entregues e a sidebar não promete mais nada.

## Dívida técnica

Este documento registra **intenções de produto**. A dívida técnica acumulada
vive em [`plans/current-state.md`](plans/current-state.md), na seção de
pendências, que é a lista canônica — e que existe porque a decisão de
2026-08-08 foi **acumular durante a trilha e varrer no fim**, em vez de
corrigir no meio de cada item.

A trilha terminou em 2026-08-09. A varredura é o próximo trabalho.
