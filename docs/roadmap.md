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
- **Foto de perfil na interface.** O backend serve avatar desde 2026-07-29 e
  `has_avatar` é sempre `false` porque nenhuma tela renderiza um. É o único
  item de produto ainda não implementado.
- **Agregado por status cruzando usuários.** Não existe endpoint que some por
  status para *todos* os usuários, então o card de dinheiro da Home mostra, para
  o admin, o total solicitado em vez de aprovado + pago.

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
Nenhuma intenção registrada.

## Dívida técnica

Este documento registra **intenções de produto**. A dívida técnica acumulada
vive em [`plans/current-state.md`](plans/current-state.md), na seção de
pendências, que é a lista canônica — e que existe porque a decisão de
2026-08-08 foi **acumular durante a trilha e varrer no fim**, em vez de
corrigir no meio de cada item.

A trilha terminou em 2026-08-09. A varredura é o próximo trabalho.
