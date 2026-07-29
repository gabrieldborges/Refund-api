# UC-003 — Criar solicitação de reembolso

## Ator principal

Usuário autenticado.

## Objetivo

Registrar uma despesa e seu comprovante como solicitação de reembolso.

## Pré-condições

- O usuário possui um JWT válido.
- O usuário está em uma área protegida do frontend e abriu o formulário de nova
  solicitação.

## Fluxo principal

1. O usuário informa nome, uma das categorias permitidas, valor positivo e um
   comprovante.
2. O frontend valida os campos e monta um `FormData` com `name`, `category`,
   `amount` e `file`.
3. O frontend envia `POST /refunds` como requisição multipart com o JWT no
   cabeçalho `Authorization: Bearer`.
4. A API valida a autenticação, lê o arquivo e valida nome, categoria, valor,
   extensão e tamanho.
5. O armazenamento gera para o comprovante um nome único baseado em UUID,
   preserva a extensão original e grava o conteúdo.
6. A API converte o valor em reais para um inteiro em centavos, associa o
   `user_id` extraído do token e persiste a solicitação.
7. A API responde com a solicitação criada no mesmo formato de
   `GET /refunds/{refund_id}` — sem `user_id` no topo, sem o nome do arquivo
   de comprovante, com `status` e com o objeto `user` (`id`, `name`,
   `has_avatar`) do solicitante — e o frontend direciona para a tela de
   sucesso. O comprovante recém-criado passa a ser obtido em
   `GET /refunds/{refund_id}/receipt`; a foto do solicitante, quando
   `has_avatar` é verdadeiro, em `GET /users/{user_id}/avatar`. Ambas
   autenticadas.

## Fluxos alternativos e erros

- Se o cabeçalho estiver ausente ou não usar `Bearer`, a API responde `401`.
- Se o JWT for inválido ou estiver expirado, a API responde `401`; o frontend
  limpa os dados locais de sessão e direciona para `/login`.
- Se o nome estiver vazio ou contiver apenas espaços, a API rejeita a criação.
- Se a categoria não for `food`, `lodging`, `transport`, `service` ou `others`,
  a API rejeita a criação.
- Se o valor for zero ou negativo, a API rejeita a criação.
- Se o comprovante não tiver extensão `jpg`, `jpeg`, `png` ou `pdf`, a API
  rejeita a criação.
- Se o comprovante exceder 4 MiB (`4 * 1024 * 1024` bytes), a API rejeita a
  criação.
- Antes do envio, o frontend exige uma string de nome não vazia, categoria
  permitida, valor positivo e comprovante com extensão e tamanho aceitos; em
  caso de erro, exibe a mensagem correspondente sem navegar para a tela de
  sucesso. A rejeição de nome composto somente por espaços é feita pela API.

## Pós-condições

- Em caso de sucesso, a solicitação fica vinculada ao usuário do JWT, com valor
  em centavos e nome único do comprovante persistidos.
- O cache da listagem é invalidado para que uma consulta posterior recupere o
  novo item.
- Em caso de falha de validação ou autenticação, nenhuma solicitação é criada.

> **Mudança de contrato:** a resposta não traz mais `user_id` no topo do
> objeto, nem o nome do arquivo de comprovante; o solicitante agora vem em
> `user.id`, ao lado de `user.name` e `user.has_avatar`, no mesmo formato
> usado por `GET /refunds` e `GET /refunds/{refund_id}`. O comprovante passa
> a ser obtido por `GET /refunds/{refund_id}/receipt`, autenticada, em vez de
> uma URL pública. Isso quebra nos dois sentidos com o frontend anterior,
> então backend e frontend precisam ser implantados juntos.

## Regras relacionadas

- [BR-006](../business-rules.md#br-006--autenticação-das-operações-de-reembolso)
- [BR-007](../business-rules.md#br-007--dados-obrigatórios-da-solicitação)
- [BR-008](../business-rules.md#br-008--categorias-permitidas)
- [BR-009](../business-rules.md#br-009--formato-e-tamanho-do-comprovante)
- [BR-010](../business-rules.md#br-010--persistência-do-valor-monetário)
- [BR-011](../business-rules.md#br-011--propriedade-da-solicitação)
- [BR-020](../business-rules.md#br-020--acesso-ao-comprovante)
- [BR-021](../business-rules.md#br-021--acesso-à-foto-de-perfil)

## Evidências

- `../Refund-FrontEnd/src/hooks/useCreateRefund.ts` monta o `FormData`, envia-o
  para `/refunds` e invalida o cache da listagem;
  `../Refund-FrontEnd/src/components/organisms/RefundFormDialog.tsx` direciona
  para `/success` após o sucesso.
- `../Refund-FrontEnd/src/schemas/refund.ts` valida os campos, extensões e o
  limite exato de 4 MiB no cliente.
- `src/main/routes/refund_routes.py` declara os campos multipart, lê o arquivo
  e protege a rota com `get_current_user`.
- `src/main/middlewares/auth_jwt.py` rejeita cabeçalho ausente e token inválido
  ou expirado.
- `src/validators/refund_creator_validator.py` aplica as validações de domínio
  no servidor.
- `src/drivers/file_storage.py` gera o nome único com UUID e grava o arquivo.
- `src/views/refund_creator_view.py` extrai o `user_id` do token, e
  `src/controllers/refund_creator_controller.py` converte o valor, associa o
  usuário, persiste a solicitação e a relê pelo `id` para responder no mesmo
  formato do GET.
- `src/controllers/refund_serializer.py` monta esse formato de resposta a
  partir da linha do repositório: descarta `filename` e reduz
  `avatar_filename` a `has_avatar`, compartilhado com o `GET` e a listagem.
