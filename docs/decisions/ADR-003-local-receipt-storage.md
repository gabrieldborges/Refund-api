# ADR-003: Armazenar comprovantes no disco local

## Status

Aceita. Emendada em 2026-07-29 para cobrir também as fotos de perfil dos
usuários.

## Contexto

Cada solicitação de reembolso inclui um comprovante JPG, PNG ou PDF, e cada
usuário pode enviar uma foto de perfil JPG ou PNG. O projeto precisa persistir
esses arquivos e disponibilizá-los pela API sem adicionar um serviço externo
de armazenamento.

Os diretórios de destino são configuráveis pelas variáveis `UPLOAD_DIR`
(padrão `uploads/receipts`) e `AVATAR_DIR` (padrão `uploads/avatars`), ambos
sob o mesmo diretório-pai `uploads/`. A API expõe esses diretórios
estaticamente em `/receipts` e `/avatars`, respectivamente.

## Decisão

Manter um único driver parametrizado, `FileStorage`, como a implementação
única para salvar e excluir tanto comprovantes quanto avatares no disco local
da instância — o diretório de destino chega pelo construtor, e a mesma classe
atende os dois casos sem duplicar a lógica de salvar e excluir. Ao salvar,
gerar o nome com UUID e preservar a extensão do arquivo original. Validar
antes do armazenamento se a extensão, comparada sem diferenciar maiúsculas de
minúsculas, pertence ao conjunto aceito para aquele tipo de arquivo — JPG,
JPEG, PNG ou PDF para comprovantes; JPG, JPEG ou PNG para avatares.

## Consequências

- A solução é simples e não requer infraestrutura adicional de armazenamento.
- Um único driver parametrizado evita duplicar a lógica de salvar e excluir
  entre comprovantes e avatares; um terceiro tipo de arquivo enviado no futuro
  reaproveitaria a mesma classe, bastando seu próprio diretório e seu próprio
  validador de extensão e tamanho.
- Os arquivos dependem do disco e do ciclo de vida da instância que executa a
  API.
- Ambientes com múltiplas instâncias não compartilham os arquivos entre si.
- Não há armazenamento distribuído, replicação ou durabilidade externa para os
  arquivos.
