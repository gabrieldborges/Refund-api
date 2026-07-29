# Ciclo de feature — Consulta da listagem e foto de perfil (backend)

Data: 2026-07-29.
Repositórios afetados: `Refund-api` (implementação e documentação canônica).
O frontend consome esta API no ciclo seguinte, com spec própria.

Este ciclo segue o
[fluxo permanente da trilha](../../plans/learning-path-workflow.md).

## Motivação

O ciclo anterior entregou o workflow de aprovação no backend. O ciclo do
frontend que vem a seguir precisa de três coisas que a API ainda não oferece, e
construir tela contra uma API que muda em seguida é retrabalho garantido. Por
isso o backend vem primeiro.

O gatilho concreto foi uma armadilha descoberta no brainstorming. O plano do
frontend inclui o **TanStack Table com toolbar de filtro e ordenação** (Item 13).
Mas a API pagina no servidor — o frontend pede `per_page=6` e recebe 6 linhas —
e o toolbar do TanStack ordena e filtra **o que está na tabela**. Com 41
reembolsos, o usuário veria um filtro de status que olha 6 deles e uma ordenação
por valor que ordena a página, não o conjunto. **Funciona visualmente e mente**,
que é pior do que não existir.

Ordenação e filtro precisam viver onde vive a paginação: no servidor.

## Escopo

1. **`GET /refunds` ganha** filtro por `status`, `sort`/`order`, e o objeto
   `user` aninhado com quem solicitou.
2. **`POST` e `DELETE /users/me/avatar`**, com `users.avatar_filename`, o arquivo
   servido em `/avatars/{filename}`, e o driver de storage parametrizado.
3. **`POST /refunds` passa a devolver o mesmo formato** das outras respostas de
   reembolso.
4. **Dívida operacional**: `uploads/` ignorado pelo git, e os 7 arquivos órfãos
   removidos.

Fora deste ciclo: as telas (spec própria), o `per_page` de 6 para 10 (é constante
do frontend, não do backend — o default do backend já é 10), o **Item 21**
(consistência banco+arquivo) e o **Item 22** (object storage).

## Decisões tomadas no brainstorming

| Decisão | Escolha | Consequência |
|---|---|---|
| Quem solicitou, na resposta | objeto `user` aninhado | `user_id` sai do topo — quebra de contrato |
| Contrato de ordenação | `sort` + `order` separados | Lista branca em ambos, 422 fora dela |
| Endpoint de avatar | recurso próprio, com `DELETE` | Voltar ao gradiente é um verbo, não um caso especial |
| Driver de storage | parametrizar, não duplicar | Uma implementação; o Item 22 troca só ela |
| Admin vê os próprios na lista | sim | A BR-016 proíbe revisar, não ver |

## O objeto `user` — e o aviso de deploy

```
GET /refunds?page=1&per_page=10&name=&status=pending&sort=amount_in_cents&order=desc

{
  "type": "Refund", "count": 10, "total": 41,
  "sum_amount_in_cents": 481710,
  "page": 1, "per_page": 10, "total_pages": 5,
  "attributes": [{
    "id": 58, "name": "Estacionamento", "category": "transport",
    "amount_in_cents": 4500, "filename": "606771d4-....jpg",
    "status": "approved", "created_at": "2026-07-28T17:00:25.325003",
    "user": { "id": 13, "name": "Validacao Visual", "avatar_filename": "abc.jpg" }
  }]
}
```

`user_id` **sai do nível de cima** e passa a ser `user.id`.

> **Backend e frontend têm de ir para produção JUNTOS.**
>
> Esta quebra não tem lado seguro, ao contrário da do ciclo anterior. O
> `refundBaseSchema` do frontend declara `user_id` como **obrigatório**: um
> backend novo com frontend velho falha o `.parse` em toda listagem. E um
> frontend novo com backend velho falha igual, porque passará a exigir `user`.
>
> O `sum_amount_in_cents` do ciclo anterior tinha uma ordem segura (backend
> primeiro). **Esta não tem nenhuma.** Implantar os dois no mesmo momento é a
> única opção; se isso não for possível, a alternativa é uma versão de transição
> devolvendo `user_id` **e** `user` ao mesmo tempo, removendo `user_id` só depois
> que o frontend novo estiver em produção.

O `JOIN` com `users` entra na query de listagem que já existe — uma consulta, não
uma por linha. A query de `count`/`sum` **não** recebe o `JOIN`: ela só conta e
soma.

`select_refund_by_id` recebe o mesmo `JOIN`, porque `GET /refunds/{id}` também
precisa do objeto `user`. As três respostas passam a sair da mesma forma.

**`avatar_filename` é o nome do arquivo, não uma URL.** O frontend compõe a URL
com `/avatars/{filename}`, exatamente como já faz com `/receipts/{filename}` do
comprovante. Devolver caminho relativo mantém o host fora do banco e fora da
resposta.

## Por que `POST /refunds` entra neste ciclo

`refund_creator_controller.py` monta a resposta a partir do dicionário de
entrada:

```python
return {"type": "Refund", "count": 1, "attributes": {"id": refund_id, **refund_info}}
```

Como `status` nasce do `server_default` no banco e `user` viria do `JOIN`, a
criação devolveria um formato diferente de `GET /refunds` e `GET /refunds/{id}`.

Concretamente: depois do insert, o controller chama o mesmo
`select_refund_by_id` que o detalhe usa — já com o `JOIN` — em vez de montar a
resposta a partir do que recebeu. Um caminho, um formato.

Isso não é questão de estética. O frontend reusa **o mesmo** `refundBaseSchema`
nas três respostas; a primeira pessoa a acrescentar `status` ali quebra a criação
em produção sem tocar em nada relacionado a ela. A criação passa a **reler a
linha gravada** e devolver o formato único.

## Ordenação e filtro

```
status ∈ {pending, approved, rejected}
sort   ∈ {created_at, amount_in_cents, name, status}
order  ∈ {asc, desc}
```

Fora da lista branca: **422**. Ausentes: o comportamento de hoje
(`created_at desc`, sem filtro de status).

**`sort` nunca vira string dentro da query.** Um dicionário mapeia o nome
permitido para a coluna do SQLAlchemy:

```python
SORTABLE_COLUMNS = {
    "created_at": Refunds.c.created_at,
    "amount_in_cents": Refunds.c.amount_in_cents,
    "name": Refunds.c.name,
    "status": Refunds.c.status,
}
```

São duas barreiras independentes: o validator recusa o que não está na lista, e o
dicionário torna impossível uma string arbitrária chegar ao `ORDER BY`. Aceitar
nome de coluna vindo do cliente e concatenar em SQL é como abrir a porta do
banco.

**`total` e `sum_amount_in_cents` respeitam o filtro de status**, pelo mesmo
motivo que já respeitam o filtro de nome: senão o card de resumo afirma um número
e a lista mostra outro.

## Avatar

```
POST   /users/me/avatar   (multipart: file)  -> 200 { avatar_filename }
DELETE /users/me/avatar                      -> 200  (volta ao gradiente)
```

`users` ganha `avatar_filename` (`String`, **nullable** — nulo é o estado
normal, não uma falha: o padrão do produto é o gradiente sobre as iniciais).
Servido estaticamente em `/avatars/{filename}`, espelhando `/receipts`.

Validação espelhando a do comprovante: **extensão**, não `Content-Type` do
cliente (`.jpg`, `.jpeg`, `.png` — PDF não faz sentido como avatar), e o
**mesmo limite de 4 MB** já usado pelo comprovante
(`upload_info["MAX_FILE_SIZE_BYTES"]`). Um avatar de 4 MB é exagerado na
prática, mas uma constante separada só se justifica quando houver razão para os
dois limites divergirem — e hoje não há.

**Trocar a foto apaga a anterior**, e o `DELETE` também. Sem isso cada upload
deixa um arquivo no disco para sempre — que é exatamente como os 7 órfãos atuais
apareceram.

`POST /auth/login` passa a devolver `avatar_filename` para a sidebar poder
exibi-lo. Isso é **aditivo** e seguro nos dois sentidos: o Zod do frontend
descarta chaves desconhecidas.

## Driver de storage parametrizado

`ReceiptStorage` já faz o que o avatar precisa — nome único por UUID, salvar,
apagar —, mas tem o diretório cravado em `upload_info["UPLOAD_DIR"]`. Avatar e
comprovante não podem dividir pasta.

A classe passa a receber o diretório no construtor e vira `FileStorage`; os
composers dizem qual pasta usar. Duplicar seriam 15 linhas repetidas e o próximo
bug de storage precisaria de duas correções — alguém esqueceria uma.

Há um segundo motivo, de prazo mais longo: quando o **Item 22** (object storage)
chegar, trocar disco local por S3 será substituir **uma** implementação atrás de
uma interface. Com o driver duplicado, seriam duas.

## Dívida operacional incluída

**`uploads/` não está no `.gitignore`.** São 163 MB de JPEGs elegíveis para
entrar num commit; um `git add .` distraído os versiona, e removê-los depois
exige reescrever histórico. O padrão precisa preservar os `.gitkeep` que mantêm a
estrutura de pastas:

```gitignore
uploads/**
!uploads/receipts/
!uploads/receipts/.gitkeep
!uploads/avatars/
!uploads/avatars/.gitkeep
```

**Sete arquivos órfãos, 11,4 MB**, sem linha correspondente no banco — quatro com
0 bytes (uploads que falharam) e três de ~3,8 MB (testes do limite de 4 MB). São
a manifestação concreta do **Item 21**: o arquivo é salvo antes do insert, e se o
insert falha o arquivo fica. O inverso não ocorreu — nenhuma linha aponta para
arquivo inexistente.

Este ciclo **remove** os órfãos, mas **não** trata a causa: o Item 21 continua
aberto, e o upload de avatar nasce com a mesma fragilidade. O Unit of Work não
ajuda aqui — disco não participa de transação SQL.

## Camadas

Preserva a Clean Architecture existente. Nada de novo na forma: rota →
composer → view → validator → controller → repository/driver.

**Avatar**
```
src/models/entities/users.py                    + avatar_filename (nullable)
alembic/versions/<hash>_add_user_avatar.py      encadeia em e03baa8b708b
src/drivers/file_storage.py                     ReceiptStorage parametrizado
src/drivers/interfaces/file_storage_interface.py
src/validators/avatar_upload_validator.py
src/controllers/avatar_uploader_controller.py   + interface
src/controllers/avatar_remover_controller.py    + interface
src/views/avatar_uploader_view.py
src/views/avatar_remover_view.py
src/main/composer/avatar_uploader_composer.py
src/main/composer/avatar_remover_composer.py
src/main/routes/user_routes.py                  POST/DELETE /users/me/avatar
src/models/repositories/users_repository.py     + update_avatar
src/main/server/server.py                       mount /avatars
src/configs/global_config.py                    + AVATAR_DIR
```

**Listagem**
```
src/validators/refund_lister_validator.py       listas brancas
src/models/repositories/refunds_repository.py   JOIN + filtro + order_by
src/controllers/refund_lister_controller.py
src/controllers/refund_creator_controller.py    relê a linha gravada
src/views/refund_lister_view.py                 chama o validator novo
src/main/routes/refund_routes.py                Query params novos
src/controllers/user_login_controller.py        avatar_filename na resposta
```

Cada arquivo com lógica ganha seu `_test.py` ao lado. Composers e scripts de
`init/` seguem sem teste, pela convenção vigente.

## Testes

- **Validators** — cada valor fora da lista branca de `sort`, `order` e `status`
  dá 422; ausência dos três mantém o comportamento atual; extensão e tamanho do
  avatar.
- **Repository** — a query emitida contém o `JOIN`, o `WHERE` de status e o
  `ORDER BY` da coluna certa na direção certa; a query de `count`/`sum` **não**
  contém o `JOIN`; `total` e `sum` respeitam o filtro de status.
- **Controllers** — upload substitui a foto **e apaga a anterior**; remoção volta
  a `NULL` e apaga o arquivo; listagem repassa os parâmetros novos; criação
  devolve o formato completo.
- **Migration** — `upgrade`/`downgrade`, verificado à mão contra o banco real
  (automatizar depende do Item 19).

## Verificação

```bash
pytest
pylint src
```

Mais uma passada ponta a ponta contra a API real, cobrindo: ordenar por cada
coluna permitida nas duas direções, filtrar por cada status, um `sort` inválido
(422), upload de avatar, troca de avatar (conferindo que o arquivo antigo sumiu
do disco), e remoção.

## Documentação a atualizar no fechamento

- `docs/domain-model.md` — `avatar_filename` em `User`.
- `docs/business-rules.md` — regra do formato/tamanho do avatar.
- `docs/use-cases/UC-004-list-refunds.md` — filtro, ordenação e o objeto `user`.
- `docs/use-cases/UC-003-create-refund.md` — o formato novo da resposta.
- `docs/use-cases/UC-005-view-refund.md` — o objeto `user`.
- **UC-008 — Enviar foto de perfil** e **UC-009 — Remover foto de perfil** (novos),
  com entrada no `docs/index.md`.
- `docs/decisions/ADR-003-local-receipt-storage.md` — passa a cobrir avatares
  também, e registra o driver parametrizado.
- `README.md` — a variável `AVATAR_DIR`.
- `docs/learning-path-progress.md` e `docs/plans/current-state.md` no fechamento.
