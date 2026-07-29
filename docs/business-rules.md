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

## BR-009 — Formato e tamanho do comprovante

Comprovante deve ter extensão `jpg`, `jpeg`, `png` ou `pdf` e tamanho máximo de
4 MiB.

**Evidências:** `src/validators/refund_creator_validator.py` valida a extensão e
o tamanho do conteúdo; `src/configs/global_config.py` fixa o limite em
`4 * 1024 * 1024` bytes.

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

## BR-016 — Segregação de funções na revisão

Somente usuário `admin` aprova ou rejeita uma solicitação, e nenhum admin decide
sobre solicitação de sua própria autoria.

**Evidências:** `src/controllers/refund_reviewer_controller.py` verifica o papel
antes de qualquer consulta ao banco e recusa a revisão quando
`refund["user_id"]` é igual ao id do revisor.

## BR-017 — Transições de status permitidas

A partir de `pending`, uma solicitação vai para `approved` ou `rejected`. Uma
solicitação já decidida pode ter a decisão trocada (`approved` ↔ `rejected`),
mas nunca retorna a `pending`. Repetir a decisão vigente é recusado, porque não
há mudança de estado a registrar.

**Evidências:** `src/validators/refund_reviewer_validator.py` restringe o alvo a
`approved` ou `rejected`, e `src/controllers/refund_reviewer_controller.py`
recusa quando o status atual já é o alvo.

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
