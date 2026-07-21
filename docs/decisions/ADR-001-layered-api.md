# ADR-001: Organizar a API em camadas

## Status

Aceita

## Contexto

O Refund API é um projeto de estudo no qual a separação de responsabilidades
ajuda a tornar explícito o papel de cada parte da aplicação. A organização
atual distribui persistência, regras de negócio, adaptação HTTP, validação,
tratamento de erros e inicialização entre diretórios próprios.

Os módulos de composição em `src/main/composer` constroem as dependências de
cada fluxo e as entregam por interfaces aos controllers e às views.

## Decisão

Manter a organização em `models`, `controllers`, `views`, `validators`,
`errors` e `main`. A montagem dos fluxos permanece nos composers, que injetam
repositórios e drivers nos controllers e controllers nas views.

## Consequências

- Cada funcionalidade exige mais arquivos e interfaces do que uma organização
  sem separação em camadas.
- As regras de negócio podem ser testadas isoladamente com implementações
  substitutas das interfaces.
- Novas funcionalidades precisam preservar os limites existentes e realizar a
  montagem das dependências nos composers.
