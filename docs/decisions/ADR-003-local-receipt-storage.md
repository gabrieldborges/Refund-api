# ADR-003: Armazenar comprovantes no disco local

## Status

Aceita. Emendada em 2026-07-29: primeiro para cobrir também as fotos de
perfil dos usuários; em seguida, no mesmo ciclo, para encerrar o acesso
público aos arquivos — ver o amendamento ao final da seção de Decisão.

## Contexto

Cada solicitação de reembolso inclui um comprovante JPG, PNG ou PDF, e cada
usuário pode enviar uma foto de perfil JPG ou PNG. O projeto precisa persistir
esses arquivos e disponibilizá-los pela API sem adicionar um serviço externo
de armazenamento.

Os diretórios de destino são configuráveis pelas variáveis `UPLOAD_DIR`
(padrão `uploads/receipts`) e `AVATAR_DIR` (padrão `uploads/avatars`), ambos
sob o mesmo diretório-pai `uploads/`. Originalmente a API expunha esses
diretórios estaticamente em `/receipts` e `/avatars`, respectivamente —
decisão revertida pelo amendamento ao final da seção de Decisão.

## Decisão

Manter um único driver parametrizado, `FileStorage`, como a implementação
única para salvar e excluir tanto comprovantes quanto avatares no disco local
da instância — o diretório de destino chega pelo construtor, e a mesma classe
atende os dois casos sem duplicar a lógica de salvar e excluir. Ao salvar,
gerar o nome com UUID e preservar a extensão do arquivo original. Validar
antes do armazenamento se a extensão, comparada sem diferenciar maiúsculas de
minúsculas, pertence ao conjunto aceito para aquele tipo de arquivo — JPG,
JPEG, PNG ou PDF para comprovantes; JPG, JPEG ou PNG para avatares.

**Amendamento (2026-07-29):** o acesso aos arquivos deixa de ser público. Um
nome de arquivo com UUID impede adivinhar o link de outro arquivo, mas não
impede que quem já obteve um link o guarde: a antiga URL pública
`/receipts/{filename}` era, na prática, uma *capability URL* — o direito de
acesso morava inteiramente no nome imprevisível, não em quem pedia. Isso
significa que o link sobrevivia à perda de acesso ao reembolso: bastava
copiá-lo uma vez para continuar vendo o comprovante depois de o reembolso
deixar de pertencer a quem o guardou, ou depois de qualquer outra mudança de
autorização. A API passa a servir os arquivos por rotas autenticadas —
`GET /refunds/{refund_id}/receipt` e `GET /users/{user_id}/avatar` — que
reavaliam a autorização a cada requisição, em vez de fixá-la no momento em
que o link foi gerado. Os mounts estáticos em `/receipts` e `/avatars` foram
removidos.

Por coerência, as fotos de perfil recebem o mesmo tratamento, ainda que o
risco fosse menor ali — BR-021 já torna a foto de qualquer usuário acessível
a qualquer usuário autenticado, então não há segredo de autorização por
usuário a proteger, só a exigência de estar autenticado. O custo aceito é uma
requisição autenticada por avatar exibido: uma listagem com N usuários
distintos implica N requisições de imagem, cada uma carregando o JWT no
cabeçalho, em vez de N URLs públicas que o navegador poderia cachear
livremente por conta própria.

**Alternativa não escolhida:** URL assinada de vida curta (um token embutido
no próprio link, com expiração), que preservaria a possibilidade de cache e
de compartilhamento direto do link sem reabrir a janela de acesso permanente.
Não foi adotada nesta branch porque exige gerar e validar assinaturas
temporais — território do Item 22 do learning path, não deste ciclo.

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
- O acesso autenticado troca a URL pública cacheável pelo navegador por uma
  requisição com JWT por arquivo exibido; uma tela com N comprovantes ou
  avatares distintos faz N requisições autenticadas, não N downloads diretos.
