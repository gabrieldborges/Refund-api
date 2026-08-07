# ADR-004: Configuração tipada e validada no startup

## Status

Aceita em 2026-08-07, no Item 17 do learning path.

## Contexto

A configuração da API vinha de três dicionários de `os.getenv` em
`src/configs/global_config.py`, carregados via `load_dotenv()` como efeito
colateral de importar `src/configs`. Nenhum valor era validado.

Isso produzia quatro modos de falha, todos tardios e três deles enganosos:

| Cenário | Comportamento anterior | Quando aparecia |
|---|---|---|
| `JWT_SECRET` ausente | `jwt_info["KEY"]` virava `None`; a aplicação subia saudável e o `/health` respondia `ok` | `TypeError: Expected a string value`, no **primeiro login de um usuário** |
| `DATABASE_URL` ausente | `str(None)` virava a string literal `"None"` | `ArgumentError: Could not parse SQLAlchemy URL`, no import — apontando URL malformada, não variável faltando |
| `JWT_EXPIRATION_HOURS` não numérico | `int()` levantava `ValueError` cru | No import, sem nomear a variável |
| Frontend implantado | `allow_origins` fixo em `http://localhost:5173`, escrito no `server.py` | Só no navegador, em produção |

A primeira linha é a mais cara: o segredo de assinatura podia estar ausente
sem que nada na verificação percebesse.

Havia ainda um custo de tipos. `jwt_info["KEY"]` é `Optional[str]` e
`upload_info["UPLOAD_DIR"]` é `object` para qualquer ferramenta de análise, de
modo que uma chave digitada errada passava no lint e só falhava em runtime com
`KeyError`.

## Decisão

Tratar configuração como entrada externa, com o mesmo rigor que os validators
já aplicam a payloads HTTP.

1. **Uma classe `Settings(BaseSettings)`** em `src/configs/settings.py`, com
   campos tipados. Campo sem default é obrigatório: `DATABASE_URL` e
   `JWT_SECRET` são as duas únicas obrigatórias. A instância `settings` é
   construída no import do módulo, de propósito — uma configuração incompleta
   deve parar o processo ali, não virar um 500 na frente do usuário.
2. **`SecretStr` para o segredo de JWT.** `repr(settings)` imprime
   `**********`, então um traceback ou log que inclua o objeto não vaza a
   chave. Ler o valor exige `.get_secret_value()`, o que marca explicitamente
   os dois únicos pontos que precisam dele.
3. **Um campo `environment`** (`local` | `test` | `production`), cujo default é
   `local` — ausência nunca significa `production`, para que a guarda abaixo
   não possa ser pulada por omissão.
4. **CORS por configuração, com default inseguro impossível.** `CORS_ORIGINS`
   é lido como lista separada por vírgula, e um `model_validator` recusa `*`,
   `localhost` ou `127.0.0.1` quando `environment` é `production`. A aplicação
   não sobe com esse erro em vez de subir insegura.
5. **O engine do SQLAlchemy passa a ser preguiçoso.** `build_engine(url)`
   recebe a URL como argumento e `get_engine()` a memoiza com
   `lru_cache(maxsize=1)`, construindo o engine na primeira conexão em vez de
   no import. Importar a aplicação deixa de exigir um banco configurado.
6. **A configuração de teste vive no `conftest.py` da raiz**, com valores
   fictícios. Como variável de ambiente tem precedência sobre o `.env` no
   `pydantic-settings`, a suíte roda com config fictícia mesmo numa máquina com
   `.env` real — e portanto não consegue alcançar o banco real por acidente.

`global_config.py` e a chamada a `load_dotenv()` foram removidos; ler o `.env`
passou a ser responsabilidade do próprio `Settings` (`env_file`).

## Consequências

- Uma variável obrigatória ausente ou com tipo inválido impede o startup, com
  erro que nomeia o campo. O modo de falha "sobe e quebra no primeiro login"
  deixa de existir.
- O acesso à configuração passa a ser tipado e autocompletável
  (`settings.upload_dir`), e um nome errado vira erro de análise estática, não
  `KeyError` em runtime.
- Uma dependência nova, `pydantic-settings`, do mesmo autor do Pydantic que já
  era dependência. `python-dotenv` continua instalado, agora como dependência
  transitiva dela e não mais importado pelo nosso código.
- O `ci.yml` deixou de declarar variáveis de ambiente fictícias: configuração
  de deploy e configuração de teste pararam de dividir o mesmo arquivo.
- O bloqueio de CORS para o primeiro deploy fica resolvido. **Os outros
  bloqueios continuam abertos** — comprovantes em disco efêmero (Item 22),
  ausência de `Dockerfile` (Item 30) e branch protection.
- A guarda de produção é uma lista de negação (`*`, `localhost`,
  `127.0.0.1`), não uma prova de que a origem configurada está correta. Ela
  impede os erros conhecidos, não todo erro possível.
