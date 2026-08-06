# Contrato de trabalho da API

## Fonte da verdade

- Consulte o [índice canônico da documentação](docs/index.md) para requisitos,
  regras de negócio, casos de uso e decisões de arquitetura.
- Consulte [CODING_PROFILE.md](../../CODING_PROFILE.md) antes de decisões de
  arquitetura, nomenclatura ou estilo. Preserve as preferências de aprendizado,
  simplicidade, legibilidade e colaboração descritas nele.

## Antes de implementar

- Leia no índice os requisitos e ADRs relacionados à mudança.
- Quando o trabalho fizer parte do Learning Path, leia e siga
  [o fluxo permanente da trilha](docs/plans/learning-path-workflow.md) antes de
  propor ou implementar o item.
- Explique por que uma arquitetura complexa ou biblioteca nova é necessária.
- Prefira a solução mais simples que resolva o problema e evite abstrações
  prematuras.

## Durante a implementação

- Use nomes claros e preserve a legibilidade.
- Quando introduzir um conceito novo, explique brevemente o problema, a solução
  e o que mudou.
- Adicione testes com pytest junto de cada nova camada, sem acumulá-los para o
  final. Mantenha cada arquivo `_test.py` ao lado do código testado.
- Coloque fixtures repetidas entre testes do mesmo diretório em um
  `conftest.py` local.
- Escreva em inglês comentários curtos e descritivos para cada fixture e teste,
  explicando o cenário ou a razão do teste.

## Regras técnicas da API

- Preserve a Clean Architecture existente em
  `models/controllers/views/validators/errors/main`.
- Em dependencies do FastAPI, especialmente `get_current_user`, levante
  `fastapi.HTTPException` diretamente; esses fluxos não passam pelo `try/except`
  das views.
- Use PostgreSQL pela `DATABASE_URL`; não exponha credenciais reais nem
  versione o `.env`.

## Verificação

Depois de qualquer mudança, execute:

```bash
pytest
pylint src
```

**Confira o código de saída, não a nota.** O `pylint` imprime "rated at
10.00/10" e ainda assim sai com código diferente de zero quando emitiu
qualquer mensagem — a nota não é penalizada por uma mensagem de refatoração.
Este projeto reportou "pylint 10.00/10" como aprovação durante meses enquanto
o comando saía com 8; o CI encontrou isso no primeiro dia porque lê `$?`.

```bash
pylint src; echo $?   # 0 é aprovação; a nota sozinha não é
```

As mesmas verificações rodam no CI (`.github/workflows/ci.yml`) a cada push,
e **o CI é a fonte da verdade**: ele parte de um ambiente limpo, instalado a
partir do `requirements.txt`, sem o `.env` nem o `.venv` da sua máquina.

## Em caso de divergência

- Pare e compare a implementação com a documentação canônica.
- Não invente requisitos nem altere uma decisão arquitetural silenciosamente.
- Se código e documentação divergirem e a intenção não estiver clara, peça
  orientação antes de prosseguir.

## Depois da implementação

- Resuma o que mudou e qualquer conceito novo utilizado.
- Informe os comandos de verificação executados e seus resultados.
- Atualize a documentação canônica quando a mudança alterar requisitos ou
  decisões compartilhadas.
