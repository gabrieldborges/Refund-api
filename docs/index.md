# Documentação do Refund

Esta é a fonte canônica dos requisitos e das decisões compartilhadas pelo
frontend e pela API.

## Estado do projeto
- [Estado atual do projeto](plans/current-state.md) — retrato para sessões
  futuras: arquitetura, progresso da trilha de aprendizado e pendências.
- [Fluxo de trabalho do Learning Path](plans/learning-path-workflow.md) — contrato
  permanente para explicar, aprovar, implementar, verificar e encerrar cada
  item da trilha.
- [Progresso de aprendizado](learning-path-progress.md) — diário cumulativo com
  comparações, exemplos antes/depois e conclusões de cada item.

## Produto
- [Visão do produto](vision.md)
- [Glossário](glossary.md)
- [Regras de negócio](business-rules.md)
- [Modelo de domínio](domain-model.md)
- [Roadmap](roadmap.md)

## Casos de uso
- [UC-001 — Cadastrar usuário](use-cases/UC-001-register-user.md)
- [UC-002 — Autenticar usuário](use-cases/UC-002-authenticate-user.md)
- [UC-003 — Criar solicitação de reembolso](use-cases/UC-003-create-refund.md)
- [UC-004 — Listar solicitações](use-cases/UC-004-list-refunds.md)
- [UC-005 — Consultar solicitação](use-cases/UC-005-view-refund.md)
- [UC-006 — Excluir solicitação](use-cases/UC-006-delete-refund.md)
- [UC-007 — Revisar solicitação](use-cases/UC-007-review-refund.md)
- [UC-008 — Enviar foto de perfil](use-cases/UC-008-upload-avatar.md)
- [UC-009 — Remover foto de perfil](use-cases/UC-009-remove-avatar.md)

## Decisões
- [ADR-001 — Manter a arquitetura em camadas da API](decisions/ADR-001-layered-api.md)
- [ADR-002 — Utilizar PostgreSQL no Neon](decisions/ADR-002-postgresql-neon.md)
- [ADR-003 — Armazenar comprovantes no disco local](decisions/ADR-003-local-receipt-storage.md)
