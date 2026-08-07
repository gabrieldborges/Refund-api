# ADR-003: Armazenar comprovantes no disco local

## Status

Aceita. Emendada em 2026-08-07 (Item 21) para definir o que acontece quando o
banco e o disco discordam — ver o amendamento ao final da seção de Decisão.
Emendada em 2026-07-29: primeiro para cobrir também as fotos de
perfil dos usuários; em seguida, no mesmo ciclo, para encerrar o acesso
público aos arquivos. Emendada novamente em 2026-07-30 para cobrir um
terceiro tipo de arquivo, o comprovante de pagamento — ver os amendamentos
ao final da seção de Decisão.

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

**Amendamento (2026-07-30):** o ciclo de pagamento e estatísticas introduziu
um terceiro tipo de arquivo — o comprovante de pagamento (UC-012) — sob o
mesmo `FileStorage` parametrizado desta decisão, agora com **três**
diretórios de destino: `UPLOAD_DIR` (comprovantes de despesa, padrão
`uploads/receipts`), `AVATAR_DIR` (fotos de perfil, padrão
`uploads/avatars`) e o novo `PAYMENT_DIR` (comprovantes de pagamento,
padrão `uploads/payment_receipts`), cada um com seu próprio validator de
extensão e tamanho (BR-009 emendada, mesmo limite dos comprovantes de
despesa). O terceiro tipo de arquivo confirma a consequência já prevista
nesta decisão: reaproveitou a mesma classe `FileStorage`, bastando seu
próprio diretório e seu próprio validador, sem duplicar a lógica de salvar
e excluir.

O acesso ao novo arquivo segue o mesmo modelo de rota autenticada do
amendamento de 2026-07-29 — `GET /refunds/{refund_id}/payment-receipt`,
dono ou `admin`, reavaliando a autorização a cada requisição, nunca um
mount estático (BR-020 emendada) — em vez de reabrir a discussão sobre URL
pública que aquele amendamento já fechou.

Como `uploads/receipts` e `uploads/avatars`, o diretório
`uploads/payment_receipts` existe no repositório só por ter um `.gitkeep`
versionado, com a negação correspondente adicionada ao `.gitignore`
(linhas 19-20). Nenhum código da aplicação cria diretório de upload — vale
a mesma ressalva já registrada para os dois primeiros tipos de arquivo, e
falha do mesmo jeito silencioso num clone limpo sem o `.gitkeep`.

**Amendamento (2026-08-07, Item 21):** uma transação SQL cobre o banco e não
cobre o disco, então "ou tudo ou nada" entre os dois passa a ser escrito à mão.
A regra adotada é uma só, e a assimetria é o ponto:

- **Antes de o dado ficar durável, desfaça.** O arquivo foi escrito e nenhuma
  linha aponta para ele; se a escrita no banco falhar, o arquivo é apagado.
  Vale para a criação de reembolso e para o upload de avatar.
- **Depois de o dado ficar durável, não desfaça — registre.** A linha já foi
  apagada (ou já aponta para o arquivo novo); uma falha ao remover o arquivo
  não pode derrubar a resposta. Vale para a exclusão de reembolso, a remoção de
  avatar e a remoção do avatar anterior numa substituição.

O segundo caso corrigiu um defeito que ninguém tinha nomeado: uma falha de
`os.remove` na exclusão devolvia **500 para uma operação que tinha dado certo**
— a linha já estava apagada, e o usuário que tentasse de novo receberia 404.
Trocar uma resposta correta por um arquivo sobrando é o lado certo dessa troca.

A compensação é sempre **best-effort** e mora em `src/controllers/file_cleanup.py`:
ela engole a própria falha, porque no primeiro caso está dentro de um `except`
prestes a re-levantar algo mais importante, e no segundo não pode quebrar uma
resposta de sucesso. Quando engole, emite um `logging.warning` com o nome do
arquivo — é a primeira linha de log do projeto, e o Item 24 depois a transforma
em registro estruturado.

**O limite da compensação é o commit, não o fim do método.** Na criação, o
`insert_refund` já dá commit, então a compensação cobre **apenas** o insert: uma
falha na releitura seguinte não pode apagar o arquivo, porque a essa altura
existe uma linha real apontando para ele. É a mesma fronteira que o
`RefundPayerController` já marcava com sua flag `committed`.

**O que continua descoberto:** um `SIGKILL` entre o `save()` e o commit. Nenhuma
compensação em processo resolve isso — exigiria varredura posterior ou fila
(Item 28). O `POST /refunds/{id}/payment` e os demais fluxos aceitam esse limite
conscientemente.

## Consequências

- A solução é simples e não requer infraestrutura adicional de armazenamento.
- Um único driver parametrizado evita duplicar a lógica de salvar e excluir
  entre os três tipos de arquivo — comprovante de despesa, avatar e, desde
  2026-07-30, comprovante de pagamento; um quarto tipo de arquivo enviado no
  futuro reaproveitaria a mesma classe, bastando seu próprio diretório e seu
  próprio validador de extensão e tamanho.
- Os arquivos dependem do disco e do ciclo de vida da instância que executa a
  API.
- Ambientes com múltiplas instâncias não compartilham os arquivos entre si.
- Não há armazenamento distribuído, replicação ou durabilidade externa para os
  arquivos.
- Um arquivo órfão deixa de ser criado por falha de banco, mas continua
  possível por queda abrupta do processo; a limpeza desse resto continua manual.
- Uma falha ao remover arquivo deixa de derrubar a resposta e passa a produzir
  um `WARNING` com o nome do arquivo — rastro que antes não existia, e cuja
  ausência fez sete órfãos serem descobertos só ao listar o diretório.
- O acesso autenticado troca a URL pública cacheável pelo navegador por uma
  requisição com JWT por arquivo exibido; uma tela com N comprovantes ou
  avatares distintos faz N requisições autenticadas, não N downloads diretos.
