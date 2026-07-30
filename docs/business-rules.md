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
`PATCH /refunds/{refund_id}/status` — é **terminal** por decisão: o
pagamento é um fato consumado, não uma decisão a ser revista, então nenhuma
solicitação paga deveria retornar a `approved` ou `rejected`.

**Evidências:** `src/validators/refund_reviewer_validator.py` restringe o alvo a
`approved` ou `rejected`, e `src/controllers/refund_reviewer_controller.py`
recusa quando o status atual já é o alvo. **Lacuna conhecida, documentada em
[UC-007](use-cases/UC-007-review-refund.md#nota-paid-como-status-de-origem-lacuna-conhecida):**
a checagem existente (`current_status == status`) cobre apenas a repetição
da decisão vigente, não o caso em que o status de origem é `paid` — nesse
caso, a implementação atual permite a transição em vez de recusá-la com
`422`. Não há teste automatizado cobrindo o caminho de "`paid` revertido".

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
