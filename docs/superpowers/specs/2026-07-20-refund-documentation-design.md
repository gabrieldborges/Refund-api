# Documentação canônica do Refund

## Objetivo

Organizar a documentação do produto Refund a partir do comportamento atualmente
comprovado no frontend, na API e nos testes, sem confundir funcionalidades
existentes com intenções futuras.

Esta mudança é exclusivamente documental. Ela não altera o comportamento da
aplicação nem adiciona dependências.

## Fonte canônica

O repositório `Refund-api` será a fonte canônica da documentação compartilhada
do produto. O frontend consultará essa documentação pelo caminho relativo
`../Refund-api/docs/`.

Requisitos e regras de negócio não serão duplicados entre os repositórios. Cada
repositório poderá manter instruções técnicas exclusivas de sua implementação.

## Estrutura

```text
Refund-api/
├── docs/
│   ├── index.md
│   ├── vision.md
│   ├── glossary.md
│   ├── business-rules.md
│   ├── domain-model.md
│   ├── roadmap.md
│   ├── use-cases/
│   └── decisions/
├── AGENTS.md
└── CLAUDE.md
```

### Responsabilidades dos documentos

- `index.md`: mapa da documentação e ordem recomendada de leitura.
- `vision.md`: problema, usuários, objetivo, escopo atual e limites.
- `glossary.md`: significado dos termos do domínio.
- `business-rules.md`: regras confirmadas, identificadas como `BR-NNN`.
- `domain-model.md`: conceitos, relacionamentos e invariantes existentes.
- `roadmap.md`: intenções futuras, sem apresentá-las como requisitos aprovados.
- `use-cases/`: comportamentos observáveis do sistema.
- `decisions/`: registros das decisões arquiteturais relevantes.

## Escopo inicial

A primeira versão cobrirá os comportamentos existentes de:

- cadastro de usuário;
- autenticação;
- criação de solicitação de reembolso com comprovante;
- listagem e busca de solicitações;
- visualização dos detalhes de uma solicitação;
- exclusão de uma solicitação;
- autorização distinta para usuários `standard` e `admin`.

Cada caso de uso registrará ator, objetivo, pré-condições, fluxo principal,
alternativas e erros, pós-condições, regras relacionadas e evidências na
implementação ou nos testes.

Diagramas somente serão incluídos quando esclarecerem uma relação relevante.
O modelo de domínio poderá conter um diagrama textual simples da relação entre
usuário e reembolso.

## Estado atual e intenções futuras

Os documentos funcionais, regras e casos de uso descreverão somente o estado
atualmente comprovado. Funcionalidades futuras ficarão em `roadmap.md`, com um
dos seguintes estados:

- `Ideia`: intenção ainda não analisada;
- `Em análise`: proposta sendo detalhada, ainda não aprovada;
- `Aprovada`: funcionalidade aceita para planejamento, mas ainda não
  implementada.

Uma intenção somente passará a integrar casos de uso e regras do sistema quando
for aprovada e sua documentação deixar explícito que ainda está pendente de
implementação. Depois da implementação e verificação, ela passará a fazer parte
do estado atual.

## Evidências e divergências

As fontes usadas para documentar o estado existente serão:

1. comportamento observável no código atual;
2. testes automatizados;
3. instruções e decisões existentes em `AGENTS.md` e `CLAUDE.md`;
4. histórico recente dos repositórios.

Quando uma descrição antiga divergir do código e dos testes atuais, a
documentação registrará o comportamento implementado. Intenções antigas ainda
relevantes serão movidas para o roadmap, e não apresentadas como fatos.

A divergência já identificada entre o `README.md` da API, que cita SQLite, e a
configuração atual com PostgreSQL no Neon será corrigida.

## Integração com os arquivos existentes

- O `README.md` da API apresentará o ambiente atual e apontará para
  `docs/index.md`.
- O `AGENTS.md` da API orientará os agentes e encaminhará regras e decisões
  duráveis para `docs/`.
- O `CLAUDE.md` da API será um adaptador curto para `AGENTS.md` e
  `docs/index.md`.
- O `AGENTS.md` do frontend apontará para a documentação canônica e preservará
  somente instruções específicas do frontend.
- O `CLAUDE.md` do frontend apontará para seu `AGENTS.md` e para a documentação
  compartilhada.

As orientações específicas de verificação serão preservadas: TypeScript no
frontend; `pytest` e `pylint` na API.

## Verificação

A implementação será verificada por:

- conferência dos links relativos;
- busca por referências a documentos inexistentes;
- validação da numeração das regras de negócio;
- rastreabilidade entre casos de uso e regras;
- comparação dos documentos com rotas, validadores, controladores e testes;
- inspeção do `git diff` de ambos os repositórios.

Como não haverá mudanças em arquivos operacionais, os testes de aplicação não
são necessários para validar esta etapa documental. Se algum arquivo operacional
for alterado, as verificações normais do respectivo projeto passam a ser
obrigatórias.

## Fora do escopo

- alterar comportamento do frontend ou da API;
- adicionar bibliotecas;
- inventar funcionalidades futuras;
- redesenhar a arquitetura existente;
- criar diagramas sem uma dúvida concreta a esclarecer;
- tratar uma intenção do roadmap como funcionalidade implementada.
