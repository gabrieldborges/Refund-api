# Regras de negócio

Este documento registra as regras observáveis na implementação atual do Refund.
Os caminhos em **Evidências** apontam para os locais que aplicam ou garantem cada
regra.

## BR-001 — Dados obrigatórios do cadastro

Cadastro exige nome, e-mail válido e senha com pelo menos 8 caracteres.

**Evidências:** `src/validators/user_register_validator.py` valida nome, formato
do e-mail e tamanho mínimo da senha; `src/main/routes/auth_routes.py` aplica esse
validador ao cadastro público.

## BR-002 — Unicidade do e-mail

E-mail de usuário deve ser único.

**Evidências:** `src/models/entities/users.py` define a restrição de unicidade;
`src/models/repositories/users_repository.py` trata sua violação como e-mail já
cadastrado.

## BR-003 — Papel inicial do usuário

Cadastro público sempre cria usuário com papel `standard`.

**Evidências:** `src/controllers/user_register_controller.py` atribui
explicitamente o papel `standard`; `src/models/entities/users.py` também define
esse valor como padrão de persistência.

## BR-004 — Proteção da senha

Senha deve ser armazenada de forma protegida e nunca retornada pela API.

**Evidências:** `src/controllers/user_register_controller.py` protege a senha
antes da persistência e omite o campo da resposta; `src/drivers/password_handler.py`
implementa a geração e a verificação do hash.

## BR-005 — Resposta genérica no login inválido

Login inválido usa mensagem genérica para e-mail ausente ou senha incorreta.

**Evidências:** `src/controllers/user_login_controller.py` responde com
`Invalid credentials` nos dois casos, sem revelar qual credencial falhou.

## BR-006 — Autenticação das operações de reembolso

Operações de reembolso exigem JWT válido.

**Evidências:** `src/main/routes/refund_routes.py` exige o usuário autenticado em
todas as rotas de reembolso; `src/main/middlewares/auth_jwt.py` rejeita cabeçalho
ausente, token inválido ou token expirado.

## BR-007 — Dados obrigatórios da solicitação

Solicitação exige nome não vazio, categoria permitida, valor positivo e
comprovante.

**Evidências:** `src/validators/refund_creator_validator.py` valida nome,
categoria, valor e arquivo; `src/main/routes/refund_routes.py` declara o
comprovante como obrigatório na criação.

## BR-008 — Categorias permitidas

Categorias permitidas são `food`, `lodging`, `transport`, `service` e `others`.

**Evidências:** `src/validators/refund_creator_validator.py` define e aplica o
conjunto de categorias aceitas.

## BR-009 — Formato e tamanho do comprovante (emendada)

Comprovante deve ter extensão `jpg`, `jpeg`, `png` ou `pdf` e tamanho máximo de
4 MiB. A partir do ciclo de pagamento e estatísticas, a regra vale igualmente
para os **dois** comprovantes de uma solicitação: o de despesa (enviado na
criação) e o de pagamento (enviado em `POST /refunds/{refund_id}/payment`,
UC-012). Mesma extensão aceita, mesmo limite de tamanho, validado por
extensão — nunca pelo `Content-Type` enviado pelo cliente, que é definido
por quem faz o upload e não é confiável na prática.

**Evidências:** `src/validators/refund_creator_validator.py` e
`src/validators/refund_payer_validator.py` validam extensão e tamanho, cada
um com sua própria constante `ALLOWED_EXTENSIONS` — mantidas separadas de
propósito, para que afrouxar a regra de um comprovante não afrouxe a do
outro silenciosamente; `src/configs/global_config.py` fixa o limite
compartilhado `MAX_FILE_SIZE_BYTES` em `4 * 1024 * 1024` bytes;
`src/validators/refund_payer_validator_test.py` cobre extensões aceitas,
extensão inválida e os dois limites de tamanho para o comprovante de
pagamento.

## BR-010 — Persistência do valor monetário

Valor recebido em reais é persistido como inteiro em centavos.

**Evidências:** `src/controllers/refund_creator_controller.py` multiplica o valor
por 100 e o arredonda; `src/models/entities/refunds.py` persiste o resultado no
campo inteiro `amount_in_cents`.

## BR-011 — Propriedade da solicitação

Cada solicitação pertence obrigatoriamente ao usuário autenticado que a criou.

**Evidências:** `src/views/refund_creator_view.py` obtém o `user_id` do token;
`src/controllers/refund_creator_controller.py` associa esse identificador à
solicitação; `src/models/entities/refunds.py` torna a referência obrigatória.

## BR-012 — Escopo de acesso por papel

Usuário `standard` lista e acessa somente suas solicitações; `admin` pode acessar
todas.

**Evidências:** `src/controllers/refund_lister_controller.py` filtra pelo usuário
exceto para `admin`; `src/controllers/refund_finder_controller.py` permite ao
administrador consultar qualquer solicitação e restringe os demais ao
proprietário.

## BR-013 — Recurso inexistente ou alheio

Consulta ou exclusão de ID inexistente ou alheio responde como não encontrado.

**Evidências:** `src/controllers/refund_finder_controller.py` e
`src/controllers/refund_deleter_controller.py` lançam `Refund not found` tanto
para ID ausente quanto para solicitação pertencente a outro usuário.

## BR-014 — Ordem e busca da listagem

Listagem ordena solicitações da mais recente para a mais antiga e permite busca
parcial por nome.

**Evidências:** `src/models/repositories/refunds_repository.py` ordena por
`created_at` decrescente e aplica busca parcial sem distinção entre maiúsculas e
minúsculas ao nome.

## BR-015 — Exclusão da solicitação e do comprovante

Exclusão exige que a solicitação esteja com `status = 'pending'`; remove o
registro e tenta remover seu arquivo de comprovante. Uma solicitação já
decidida (`approved` ou `rejected`) não pode ser excluída.

**Evidências:** `src/controllers/refund_deleter_controller.py` recusa a
exclusão quando `status` não é `pending`, coordena a remoção do registro e do
comprovante; `src/models/repositories/refunds_repository.py` remove o
registro; `src/drivers/file_storage.py` remove o arquivo quando ele existe.

## BR-016 — Segregação de funções na revisão (estendida)

Somente usuário `admin` aprova, rejeita **ou paga** uma solicitação, e nenhum
admin decide — nem paga — sobre solicitação de sua própria autoria. A
extensão a pagamento existe porque um admin que já não pode aprovar a
própria solicitação teria, sem essa regra, uma brecha equivalente ao poder
pagá-la.

**Evidências:** `src/controllers/refund_reviewer_controller.py` verifica o papel
antes de qualquer consulta ao banco e recusa a revisão quando
`refund["user_id"]` é igual ao id do revisor;
`src/controllers/refund_payer_controller.py` aplica a mesma ordem — papel
antes de qualquer consulta — e recusa o pagamento quando
`refund["user"]["id"]` é igual ao id de quem paga;
`src/controllers/refund_payer_controller_test.py::test_admin_cannot_pay_their_own_refund`
comprova a extensão.

## BR-017 — Transições de status permitidas (emendada)

A partir de `pending`, uma solicitação vai para `approved` ou `rejected`. Uma
solicitação já decidida pode ter a decisão trocada (`approved` ↔ `rejected`),
mas nunca retorna a `pending`. Repetir a decisão vigente é recusado, porque não
há mudança de estado a registrar. `paid` — alcançado apenas por
`POST /refunds/{refund_id}/payment` (UC-012), nunca por
`PATCH /refunds/{refund_id}/status` — é **terminal**: o pagamento é um fato
consumado, não uma decisão a ser revista, então nenhuma solicitação paga
retorna a `approved` ou `rejected` — `PATCH /refunds/{refund_id}/status`
sobre uma solicitação paga responde `422`.

A regra é aplicada por **duas** checagens no controller, e elas significam
coisas diferentes: "`paid` é terminal" é sobre um fato consumado (o dinheiro
já se moveu), enquanto "repetir a decisão vigente" é sobre um não-evento
(nenhuma mudança a registrar) — por isso cada uma recusa com sua própria
mensagem, em vez de caírem no mesmo `422` genérico. As duas checagens são
independentes, não uma dependência de ordem: como o validator já restringe
o alvo a `{approved, rejected}`, as duas condições nunca são verdadeiras ao
mesmo tempo. A checagem de `paid` roda primeiro só porque produz a mensagem
mais clara para uma solicitação paga, não porque a ordem seja necessária
para proteger contra a reversão.

**Nota para quem for adicionar um quinto status:** o raciocínio que antes
tornava uma única checagem suficiente era *baseado em conjuntos*, e quebrou
quando este ciclo ampliou o conjunto de status **de origem** possíveis
(`current_status` passou a poder ser `paid`) — o comentário que justificava
a checagem única só previa alargar o conjunto de status **alvo**
(`ALLOWED_REVIEW_STATUSES`). As duas direções precisam ser revisadas juntas
antes de qualquer novo status: alargar o conjunto de alvos pode fazer um
novo valor colidir com um status atual que o controller não rejeita à
parte; alargar o conjunto de status de origem alcançáveis (isto é, criar um
novo jeito de uma solicitação chegar a um status além de
pending/approved/rejected/paid) exige sua própria guarda no controller, do
mesmo jeito que `paid` passou a exigir.

**Evidências:** `src/validators/refund_reviewer_validator.py` restringe o
alvo a `approved` ou `rejected`, com um comentário que registra as duas
direções acima; `src/controllers/refund_reviewer_controller.py` recusa
primeiro quando o status atual já é `paid` (`Refund is already paid and
cannot be reviewed`) e, em seguida, quando o status atual já é o alvo
(`Refund is already {status}`);
`src/controllers/refund_reviewer_controller_test.py::test_a_paid_refund_cannot_be_reverted_to_approved`
e `::test_a_paid_refund_cannot_be_reverted_to_rejected` comprovam a
checagem de terminalidade nas duas direções possíveis a partir de `paid`.

## BR-018 — Justificativa obrigatória na rejeição

Revisar uma solicitação com `status` alvo igual a `rejected` exige informar
`reason` não vazio. Aprovar (`approved`) não exige `reason`.

**Evidências:** `src/validators/refund_reviewer_validator.py` recusa a
requisição quando `status` é `rejected` e `reason` está ausente, vazio ou
somente espaços.

## BR-019 — Formato e tamanho da foto de perfil

A foto de perfil aceita apenas JPG e PNG, validados pela extensão do arquivo, e
no máximo 4MB. Nulo é um estado válido e representa o avatar padrão do produto.

**Evidências:** `src/validators/avatar_upload_validator.py` restringe extensão e
tamanho; `src/models/entities/users.py` declara `avatar_filename` como nulável.

## BR-020 — Acesso ao comprovante (emendada)

O comprovante de uma solicitação — o de despesa (UC-010) e, desde o ciclo de
pagamento, também o de pagamento (`GET /refunds/{refund_id}/payment-receipt`)
— só é acessível ao seu proprietário e a usuários `admin`. Solicitação
inexistente e solicitação alheia respondem igualmente como não encontrada,
para não revelar quais identificadores existem. Para o comprovante de
pagamento, o mesmo `404`, com a mesma mensagem, também cobre uma solicitação
que existe mas nunca foi paga, e um registro cujo arquivo sumiu do disco —
os quatro cenários são indistinguíveis de propósito, porque qualquer
diferença entre eles seria um oráculo para quem não tem direito de acesso.

**Evidências:** `src/controllers/receipt_finder_controller.py` aplica a mesma
regra de `refund_finder_controller.py` e levanta `HttpNotFoundError` nos dois
casos; `src/controllers/payment_receipt_finder_controller.py` aplica a
mesma regra ao comprovante de pagamento, incluindo os dois cenários
adicionais (não pago, arquivo ausente do disco);
`src/controllers/payment_receipt_finder_controller_test.py` cobre os quatro
cenários com a mesma mensagem `Refund not found`.

## BR-021 — Acesso à foto de perfil

A foto de perfil de qualquer usuário é acessível a qualquer usuário autenticado.
Usuário inexistente e usuário sem foto respondem igualmente como não encontrado.

**Evidências:** `src/controllers/avatar_finder_controller.py` não recebe a
identidade de quem pede; a autenticação é exigida pela dependência da rota em
`src/main/routes/user_routes.py`.

## BR-022 — Comprovante de pagamento obrigatório

Nenhuma solicitação transiciona para `status = "paid"` sem um comprovante de
pagamento anexado. Como o arquivo é obrigatório para alcançar `paid`, vale a
invariante `status == "paid"` ⟺ existe comprovante de pagamento
(`Refund.payment_filename` preenchido). É por isso que nenhuma resposta de
reembolso ganha um campo `has_payment_receipt`: o próprio `status` já
carrega essa informação — o oposto de `has_avatar` (BR-019), que existe
justamente porque o avatar é opcional.

**Evidências:** `src/controllers/refund_payer_controller.py` só tenta a
transição condicional para `paid` depois de salvar o arquivo, e desfaz o
arquivo salvo se a transição falhar (corrida perdida), nunca deixando
`status = "paid"` sem um `payment_filename`; `src/models/entities/refunds.py`
comenta a invariante junto à coluna `payment_filename`, nulável porque nada
no banco a impõe — a garantia é inteiramente aplicacional, como já vale para
o `status` como um todo (nenhum `ENUM` nem `CHECK`);
`src/controllers/refund_payer_controller_test.py::test_admin_pays_an_approved_refund`
comprova que a resposta de sucesso traz `status: "paid"` sem expor
`payment_filename`.

## BR-023 — Limite de tentativas em autenticação e cadastro

Um mesmo cliente tem um número máximo de tentativas por janela de tempo em
`POST /auth/login` e `POST /auth/register`. Excedido o limite, a API responde
`429` sem processar a tentativa. Os valores são configuração
(`LOGIN_RATE_LIMIT`, `REGISTER_RATE_LIMIT`, `RATE_LIMIT_WINDOW_SECONDS`), não
constantes de código.

**Duas ameaças, uma regra.** No login, a [BR-005](#br-005--resposta-genérica-no-login-inválido)
impede descobrir *quais* e-mails existem, mas nada impedia tentar dez mil senhas
contra um e-mail já conhecido — e como a senha é verificada com bcrypt
([BR-004](#br-004--proteção-da-senha)), cada tentativa é cara **para o
servidor**, o que torna o login também um alvo de exaustão de recursos.

No cadastro a ameaça é outra: ele responde `Email already registered`, que é
exatamente o que a BR-005 se recusa a revelar no login. **A mensagem foi
mantida de propósito** — sem ela, quem já tem conta recebe um erro que não
explica nada. O limite não elimina a enumeração, torna a enumeração **em massa**
impraticável: dez e-mails seguem possíveis, dez mil não.

**A contagem é por endereço de rede, nunca por e-mail.** Contar por e-mail
deixaria qualquer pessoa trancar a conta de uma vítima conhecida, queimando a
cota de propósito — trocaria risco de força bruta por negação de serviço.

**Evidências:** `src/main/middlewares/rate_limit.py` implementa janela
deslizante (balde de relógio daria o dobro da cota em cada fronteira) e
identifica o cliente pelo endereço do peer, nunca por `X-Forwarded-For`, que um
cliente escolhe; `src/main/routes/auth_routes.py` aplica o limite antes de
qualquer trabalho; `src/test_integration/api_test.py::test_repeated_login_attempts_are_eventually_refused`
e `::test_bulk_registration_attempts_are_refused` comprovam o `429` por HTTP,
e `::test_the_two_limits_are_independent` que esgotar um não bloqueia o outro.
Decisão e limites em [ADR-009](decisions/ADR-009-abuse-controls.md).

## BR-024 — Teto de tamanho da requisição

Uma requisição cujo `Content-Length` declarado exceda `MAX_REQUEST_BODY_BYTES`
é recusada com `413` **antes** de o corpo ser lido.

Isto não substitui o limite de 4MB por arquivo
([BR-009](#br-009--formato-e-tamanho-do-comprovante)) — é anterior a ele. Os
validators conferem o tamanho do arquivo depois que a rota já fez
`await file.read()`, ou seja, com o conteúdo **inteiro em memória**. O teto
existe para que um corpo de 2GB seja recusado sem nunca chegar lá.

**Limitação conhecida:** a checagem lê o tamanho *declarado*. Uma requisição
`chunked` não envia esse cabeçalho e passa, sendo pega apenas pela BR-009 —
depois de bufferizar, que é o que este teto evita. Fechar isso exigiria contar
bytes no stream ASGI.

**Evidências:** `src/main/middlewares/request_guards.py` recusa por
`Content-Length` e responde em `application/problem+json` como todo erro
([ADR-005](decisions/ADR-005-problem-details.md));
`src/test_integration/api_test.py::test_an_oversized_body_is_refused_before_it_is_buffered`
comprova o `413`, e `::test_a_normal_upload_is_unaffected` que um envio normal
segue passando.

## BR-025 — Acesso ao diretório de usuários

Somente usuários com papel `admin` podem listar usuários
([UC-015](use-cases/UC-015-list-users.md)) ou consultar um usuário específico
([UC-016](use-cases/UC-016-view-user.md)).

**Os dois endpoints recusam com códigos diferentes, e a diferença é a regra.**

A **listagem** responde `403`. Ela não recebe nem revela nada sobre um `id` em
particular, então pode ser honesta sobre a falta de permissão sem entregar
informação nenhuma.

A **consulta individual** responde `404`, com a mesma mensagem que responde para
um `id` inexistente. Um `403` ali confirmaria que aquele `user_id` existe a quem
não pode vê-lo — o mesmo raciocínio anti-enumeração da
[BR-013](#br-013--recurso-inexistente-ou-alheio), já aplicado em UC-014. As duas
mensagens são idênticas byte a byte por requisito: uma mensagem mais útil em um
dos casos desfaria a razão de escolher `404`.

Nos dois casos a checagem acontece **antes de qualquer acesso ao banco**. Recusar
depois de consultar executaria trabalho para uma requisição que nunca foi
permitida, e o tempo de resposta ainda diria a um estranho quantos usuários
existem, aproximadamente.

**Nenhum dos dois expõe `password`.** A tabela `users` guarda o hash bcrypt na
mesma linha que nome e e-mail; a forma pública é montada campo a campo em
`src/controllers/user_serializer.py`, em vez de a linha ser devolvida sem algumas
chaves. Apagando chaves, uma coluna adicionada a `users` no futuro passaria a
vazar sozinha.

**Limitação conhecida:** o papel é lido das claims do JWT e não é reconsultado no
banco, então uma promoção só vale no próximo login. Vale para todo o sistema, e
não só para estas rotas.

**Evidências:** `src/controllers/user_lister_controller.py` e
`src/controllers/user_finder_controller.py` aplicam as duas recusas;
`user_lister_controller_test.py::test_the_repository_is_never_reached_for_a_standard_user`
e `user_finder_controller_test.py::test_the_repository_is_never_reached_for_a_standard_user`
comprovam que nenhuma consulta roda antes da checagem;
`user_finder_controller_test.py::test_a_standard_user_gets_not_found` e
`::test_a_missing_user_gets_not_found` comprovam que as mensagens coincidem;
`user_serializer_test.py::test_only_the_public_fields_are_exposed` fixa o
conjunto exato de campos públicos.
