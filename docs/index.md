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
- [Retrospectiva de processo](retrospectiva-processo.md) — onde houve
  retrabalho, o que o causou e o que fazer diferente no próximo projeto.
- [Panorama das três telas "em breve"](plans/2026-08-11-tres-telas-panorama.md) —
  decisões travadas e ordem de construção de Time, Dashboard e Calendário. Não é
  spec: cada ciclo ganha o seu no início.

## Produto
- [Visão do produto](vision.md)
- [Glossário](glossary.md)
- [Regras de negócio](business-rules.md)
- [Modelo de domínio](domain-model.md)
- [Roadmap](roadmap.md)
- [Orçamento de performance](performance-budget.md) — linha de base medida, e o que não é sintoma

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
- [UC-010 — Baixar comprovante de reembolso](use-cases/UC-010-download-receipt.md)
- [UC-011 — Baixar foto de perfil](use-cases/UC-011-download-avatar.md)
- [UC-012 — Pagar solicitação de reembolso](use-cases/UC-012-pay-refund.md)
- [UC-013 — Consultar histórico de revisões](use-cases/UC-013-list-refund-reviews.md)
- [UC-014 — Consultar estatísticas de reembolso por usuário](use-cases/UC-014-user-refund-stats.md)
- [UC-015 — Listar usuários](use-cases/UC-015-list-users.md)
- [UC-016 — Consultar usuário](use-cases/UC-016-view-user.md)
- [UC-017 — Consultar resumo agregado de reembolsos](use-cases/UC-017-refund-summary.md)
- [UC-018 — Consultar contagem diária de solicitações](use-cases/UC-018-refund-daily-counts.md)

## Decisões
- [ADR-001 — Manter a arquitetura em camadas da API](decisions/ADR-001-layered-api.md)
- [ADR-002 — Utilizar PostgreSQL no Neon](decisions/ADR-002-postgresql-neon.md)
- [ADR-003 — Armazenar comprovantes no disco local](decisions/ADR-003-local-receipt-storage.md)
- [ADR-004 — Configuração tipada e validada no startup](decisions/ADR-004-typed-settings.md)
- [ADR-005 — Erros padronizados com Problem Details (RFC 9457)](decisions/ADR-005-problem-details.md)
- [ADR-006 — Logs estruturados em JSON com request ID](decisions/ADR-006-structured-logging.md)
- [ADR-007 — Testes de API por HTTP e contrato versionado](decisions/ADR-007-contract-testing.md)
- [ADR-008 — Cobertura como diagnóstico, sem portão no CI](decisions/ADR-008-coverage.md)
- [ADR-009 — Controles de abuso na borda](decisions/ADR-009-abuse-controls.md)
- [ADR-010 — Varredura de órfãos, e por que não uma fila](decisions/ADR-010-orphan-sweep.md)
- [ADR-011 — Empacotar a API em container](decisions/ADR-011-container.md)
