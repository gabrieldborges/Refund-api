# ADR-003: Armazenar comprovantes no disco local

## Status

Aceita. Emendada em 2026-08-07 (Item 22) para acrescentar uma segunda
implementação de armazenamento e trocar o modo de servir arquivos por URLs
assinadas — ver o amendamento ao final da seção de Decisão. Emendada em
2026-08-07 (Item 21) para definir o que acontece quando o
banco e o disco discordam — ver o amendamento ao final da seção de Decisão.
Emendada em 2026-07-29: primeiro para cobrir também as fotos de
perfil dos usuários; em seguida, no mesmo ciclo, para encerrar o acesso
público aos arquivos. Emendada novamente em 2026-07-30 para cobrir um
terceiro tipo de arquivo, o comprovante de pagamento — ver os amendamentos
ao final da seção de Decisão. Emendada em 2026-08-10 (primeiro deploy) para
registrar qual backend roda em produção e para **corrigir uma consequência que
estava errada** — a de CORS no bucket.

**O título desta ADR não descreve mais a produção**, e fica como está de
propósito: ele nomeia a decisão original, que o amendamento do Item 22 revisou
e o de 2026-08-10 exerceu. O disco local continua sendo o caminho de
desenvolvimento.

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

**Amendamento (2026-08-07, Item 22):** o disco local deixa de ser a única
opção, e a forma de servir arquivos muda.

**Object storage.** `S3FileStorage` é a segunda implementação de
`FileStorageInterface`, escolhida por `STORAGE_BACKEND=s3`. Um bucket, três
prefixos (`receipts/`, `avatars/`, `payments/`), espelhando os três diretórios
do backend local. A coluna do banco continua guardando o **nome do arquivo**, não
a chave completa, então trocar de backend não exige reescrever linha nenhuma.
Erros são traduzidos: `NoSuchKey` do botocore vira `FileNotFoundError`, que é o
que os controllers já capturam — um segundo backend não pode significar um
segundo contrato de erro.

O motivo é o bloqueio nº 3 do primeiro deploy, e ele é o pior dos cinco: a
maioria dos PaaS tem filesystem efêmero, então **todo comprovante evaporaria a
cada redeploy**, em silêncio — a linha e o `filename` sobrevivem, e o download
responde 404 indistinguível de "não é seu".

**URLs assinadas, revertendo parcialmente o amendamento de 2026-07-29.** As três
rotas de arquivo devolvem `{"url": ...}` em vez dos bytes. A razão é concreta:
uma tag `<img>` não envia `Authorization: Bearer`, e era por isso que o frontend
precisava baixar cada arquivo com axios e montar um Blob.

O trade-off, declarado: a rota autenticada **reconferia a autorização a cada
requisição**; a URL assinada **congela a decisão no momento em que é gerada**.
Quem copiar o link continua com acesso até ele expirar. O que torna isso
aceitável — e diferente da URL pública que aquele amendamento removeu — é o
prazo: `FILE_URL_TTL_SECONDS`, padrão **300 segundos**, contra "para sempre".

A autorização em si **não** mudou de lugar: os controllers continuam decidindo
dono-ou-admin antes de gerar qualquer URL.

**O backend local também assina.** Sem isso haveria dois contratos — bytes em
desenvolvimento, URL em produção — e ninguém estaria testando o que roda. Como
disco local não tem provedor que assine por ele, a assinatura é um **JWT de vida
curta** carregando o par (storage, filename), servido por `GET /files/{storage}/{filename}`.
Sem criptografia nova e sem dependência nova: é o mesmo `jwt_secret` e o mesmo
`JwtHandler` do login. A rota confere que o token foi emitido **para aquele
arquivo** — sem isso, um token válido leria todos — e recusa nome de arquivo que
contenha separador de caminho.

**Um comportamento foi perdido, de propósito.** Os controllers não leem mais o
arquivo, então "a linha sobreviveu mas o arquivo sumiu" deixa de ser 404 na rota
de metadados e passa a aparecer quando o navegador segue a URL. O
`payment-receipt` tinha **quatro** caminhos de 404 idênticos verificados byte a
byte; o quarto mudou de lugar. Os três que importam seguem intactos, porque são
os que vazariam a existência de um reembolso a quem não tem direito de saber.
Restaurar o quarto custaria um `HEAD` por URL contra o S3 — a maior parte do que
este item economiza.

**Amendamento (2026-08-10, primeiro deploy):** os dois backends deixam de ser
hipótese e passam a ter cada um o seu lugar.

- **Produção roda com `STORAGE_BACKEND=s3`, num bucket da AWS.** Um bucket de
  propósito geral (não um *Directory bucket* / S3 Express One Zone, que força um
  sufixo `--x-s3` no nome e tem comportamento diferente de URL assinada), com
  *Block Public Access* ligado — o acesso é sempre por URL assinada, nunca por
  objeto público. O usuário de IAM é restrito a esse bucket:
  `GetObject`/`PutObject`/`DeleteObject` sobre o ARN dos objetos e `ListBucket`
  sobre o ARN do bucket, que é o mínimo de que os três tipos de arquivo e a
  varredura de órfãos precisam.
- **O caminho `local` continua sendo o de desenvolvimento**, e continua
  assinando com JWT curto, como o amendamento do Item 22 definiu. Os testes de
  integração seguem contra o MinIO.

**Uma correção de código que só a AWS de verdade revelou.** O `boto3`,
configurado com `region_name` e sem `config`, assina a URL para a região certa
mas endereça o **host global** (`bucket.s3.amazonaws.com`); a S3 redireciona
para o host regional e a assinatura, que cobre o cabeçalho `host`, deixa de
bater. O `S3FileStorage` passa a forçar `addressing_style="virtual"` — mas
**apenas quando `s3_endpoint_url` está vazio**, ou seja, só na AWS de verdade:
contra o MinIO o endereçamento virtual produziria `bucket.localhost:9100`, um
nome que não resolve — o endereçamento virtual sem condição teria derrubado os
72 testes de integração. Os **9** testes de integração contra o MinIO não
podiam ver esse defeito, mesmo com três deles sendo especificamente sobre URL
assinada, porque **o MinIO não tem endpoint regional para errar**.

**CORRIGINDO UMA CONSEQUÊNCIA QUE ESTAVA ERRADA — o CORS do bucket.** Esta ADR
afirmava que uma implantação com `STORAGE_BACKEND=s3` "precisa configurar
**CORS no bucket** para o domínio do frontend; caso contrário o navegador
bloqueia o download cross-origin". **É falso para a UI como ela é hoje**, e a
implantação de 2026-08-10 provou: **nenhum CORS de bucket foi configurado** e
os comprovantes renderizam.

O motivo é uma distinção fácil de perder: **CORS governa o que o JavaScript da
página consegue LER, não o que o navegador consegue BUSCAR.** O
`ReceiptPreview.tsx` do frontend renderiza por `<img src>` e `<object data>`;
nos dois casos o navegador busca o recurso e o entrega ao elemento, e a página
nunca toca os bytes — então não há preflight nem exigência de
`Access-Control-Allow-Origin`. É a mesma propriedade que motiva o Item 22: uma
tag `<img>` não sabe mandar `Authorization: Bearer`, e também não esbarra em
CORS.

**A condição que torna a afirmação verdadeira de novo**, e é para isso que ela
fica escrita: qualquer código que busque o arquivo **por JavaScript** — um
`fetch`, um `XMLHttpRequest`, um `axios.get` montando um Blob (que é exatamente
o que este frontend fazia **antes** do Item 22), um `<canvas>` lendo pixels de
uma imagem, ou um download que precise dar um nome próprio ao arquivo. Nesses
casos o navegador passa a exigir o cabeçalho e o bucket precisa liberar a
origem do frontend. **Quem escrever esse código deve tratar o CORS do bucket
como parte da tarefa**, porque nada no startup nem na suíte vai avisar.

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
- O custo de N requisições autenticadas por página **deixa de existir**: o
  navegador volta a baixar direto e a cachear, agora por um link que expira.
- ~~Uma implantação com `STORAGE_BACKEND=s3` precisa configurar **CORS no
  bucket** para o domínio do frontend.~~ **FALSO para a UI atual — derrubado
  pela implantação de 2026-08-10**, que renderiza os comprovantes sem nenhum
  CORS de bucket configurado. `<img src>` e `<object data>` não são requisições
  governadas por CORS. Volta a ser verdadeiro no instante em que algum código
  buscar o arquivo por JavaScript. Ver o amendamento acima.
- **Produção depende da AWS**, com duas contrapartidas registradas: o plano
  gratuito é **por tempo** (a data de término se lê no console da AWS, não
  aqui), e depois dele o que pesa não é o armazenamento — são poucos arquivos e
  pequenos — e sim a **transferência de saída**, já que cada arquivo exibido é
  um download direto do bucket pelo navegador. É o desenho do Item 22, e o
  custo dele.
- **Não há backup nem versionamento dos arquivos** no bucket. Uma exclusão
  acidental é definitiva. Aceito pela natureza de portfólio/demonstração do
  projeto, e registrado para que a aceitação seja explícita.
- O acesso autenticado trocava a URL pública cacheável pelo navegador por uma
  requisição com JWT por arquivo exibido; uma tela com N comprovantes ou
  avatares distintos faz N requisições autenticadas, não N downloads diretos.
