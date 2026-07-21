# ADR-003: Armazenar comprovantes no disco local

## Status

Aceita

## Contexto

Cada solicitação de reembolso inclui um comprovante JPG, PNG ou PDF. O projeto
precisa persistir o arquivo e disponibilizá-lo pela API sem adicionar um
serviço externo de armazenamento.

O diretório de destino é configurável pela variável `UPLOAD_DIR`, com o padrão
`uploads/receipts`. A API expõe esse diretório estaticamente em `/receipts`.

## Decisão

Manter o driver `ReceiptStorage` para salvar e excluir comprovantes no disco
local da instância. Ao salvar, gerar o nome com UUID e preservar a extensão do
arquivo original. Validar antes do armazenamento se a extensão, comparada sem
diferenciar maiúsculas de minúsculas, pertence ao conjunto JPG, JPEG, PNG ou
PDF.

## Consequências

- A solução é simples e não requer infraestrutura adicional de armazenamento.
- Os comprovantes dependem do disco e do ciclo de vida da instância que executa
  a API.
- Ambientes com múltiplas instâncias não compartilham os arquivos entre si.
- Não há armazenamento distribuído, replicação ou durabilidade externa para os
  comprovantes.
