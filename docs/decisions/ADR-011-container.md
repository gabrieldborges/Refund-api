# ADR-011: Empacotar a API em container

## Status

Aceita em 2026-08-09, no Item 30. **Fecha o quinto e último bloqueio do
primeiro deploy.**

## Contexto

Para esta API rodar, alguém precisava reproduzir um ambiente exato à mão: sete
passos no README, com Python **3.9 especificamente**, venv criado e ativado,
dependências instaladas, `.env` preenchido e migrations aplicadas.

O projeto tem cicatrizes disso registradas: o `.venv` com **shebangs de um
caminho antigo** (por isso `pytest` só roda como `python3 -m pytest`), o CI
tendo de **fixar `python-version: '3.9'`** porque o interpretador local é mais
velho que o padrão do runner, e — em 2026-08-08 — a aplicação **não subindo
porque o venv não estava ativado**.

*(Contexto histórico, preservado como estava quando a decisão foi tomada. As
duas primeiras cicatrizes deixaram de existir em 2026-08-10: o venv foi
recriado ao subir para o Python 3.13 e o CI fixa `python-version: '3.13'`. A
decisão de conteinerizar não dependia delas — o argumento é reprodutibilidade,
que continua valendo.)*

Nenhum serviço de hospedagem sabe seguir sete passos de README.

## Decisão

**Só a API é conteinerizada.** O frontend vira arquivos estáticos depois do
build, e hospedagem estática os serve sem container nenhum. Empacotá-lo também
esbarraria num detalhe que vale registrar: **o `VITE_API_URL` é resolvido em
tempo de build**, então uma imagem de frontend serve a um ambiente só — trocar
exigiria injeção em runtime, máquina que este projeto não tem uso para hoje.

**Build em dois estágios.** O `gcc`, necessário para compilar wheels sem
binário pronto, fica no estágio de build; o runtime recebe só o virtualenv
pronto.

**`requirements.txt` foi dividido**, e a decisão saiu de uma medição dentro da
imagem: **37,7 MB de 115,4 MB de site-packages — um terço — eram pytest,
pylint, coverage e httpx**, código que nunca roda servindo requisição. O CI
instala `requirements-dev.txt`, que puxa o outro. Imagem: **396 → 366 MB**, e
`import pytest` falha lá dentro.

**Usuário não-root** (`refund`, uid 1001).

**Nenhum segredo na imagem.** O `.env` é a primeira linha do `.dockerignore`, e
toda configuração chega por variável de ambiente, validada no startup pelo
Settings (Item 17).

**`/ready` novo, e o `/health` permanece como está.** São perguntas diferentes:

| Endpoint | Pergunta | Se falhar |
|---|---|---|
| `/health` | o processo está vivo? | reinicie |
| `/ready` | consegue atender? | não mande tráfego |

O `/health` respondia 200 **com o banco inalcançável** — medido. Isso está
correto para liveness e errado para readiness, e havia só um endpoint fazendo
os dois papéis.

**O `HEALTHCHECK` do Docker aponta para `/health`, deliberadamente não para
`/ready`.** O Docker reinicia container cujo healthcheck falha; apontá-lo para
o readiness faria uma queda de banco **reiniciar todas as instâncias em laço**,
transformando algo recuperável em apagão.

## Consequências

- Os cinco bloqueios do primeiro deploy estão endereçados. **Falta escolher
  onde implantar**, o que não é código.
- **Rodar com `STORAGE_BACKEND=local` num container perde todo comprovante a
  cada reinício**, em silêncio — a linha do banco sobrevive. É o Item 22 se
  pagando, e está escrito no próprio Dockerfile.
- ~~**A imagem é construída sobre Python 3.9, que já não recebe correções de
  segurança.**~~ **ENDEREÇADO na branch `chore/python-313-upgrade`
  (2026-08-10, não mesclada):** os dois estágios usam `python:3.13-slim`, e a
  imagem foi construída e rodada nessa base sem engordar (366 → 360 MB). Esta
  consequência foi **o argumento mais concreto que motivou aquele ciclo**, e a
  dívida que ela descrevia era maior do que parecia aqui: o Python 3.9 também
  prendia o `urllib3` na linha vulnerável, através de um marcador de ambiente
  do `botocore`. Ver o relato no
  [estado atual](../plans/current-state.md) e no
  [diário](../learning-path-progress.md).
- Migrations continuam **fora** do startup do container (ADR-002): `alembic
  upgrade head` é passo de deploy, não do boot. Um container que migra ao subir
  faz N réplicas migrarem em paralelo.
- Verificado construindo e **rodando**: usuário `refund`, `/health` 200,
  `/ready` 200, `/ready` **503 com o banco parado** e recuperando sozinho
  quando ele volta, `healthcheck` do Docker `healthy`, e nenhum `.env` dentro.
