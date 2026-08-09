# ADR-010: Varredura de órfãos, e por que não uma fila

## Status

Aceita em 2026-08-09, no Item 28 do learning path. **Encerra a Fase 4.**

## Contexto

O Item 28 pede tarefas assíncronas com fila, e começa se autolimitando:
*"Não adicionar worker para CRUD simples."*

A primeira pergunta, então, é se este projeto tem trabalho que justifique uma
fila. Os candidatos que o próprio item nomeia — *"processamento de comprovante,
e-mail ou relatório"* — foram procurados:

| Candidato | Existe aqui? |
|---|---|
| Envio de e-mail | não |
| Geração de relatório ou export | não |
| Processamento de imagem | não |
| Processamento de comprovante | não — o arquivo é gravado como veio |

Tudo o que esta API faz é CRUD mais uma escrita de arquivo. **Nada precisa ser
desacoplado de uma resposta HTTP.**

Mas existe trabalho de fundo real, e o `current-state.md` aponta para este item
**duas vezes**, com a mesma frase: *"um `SIGKILL` entre o `save()` e o commit
continua órfanando o arquivo. Nenhuma compensação em processo resolve isso —
exige varredura posterior ou fila (Item 28)."*

E há um segundo produtor de órfãos, do Item 21: quando a exclusão do arquivo
falha **depois** do commit, o `delete_quietly` registra um aviso e segue — que
é a decisão certa, porque derrubar uma resposta de sucesso por causa de um
arquivo sobrando é a troca pior. Só que nada nunca remove o que ele deixou.

## Decisão

**Uma varredura de reconciliação, não uma fila.**

Fila desacopla trabalho de uma **requisição**. Este trabalho não pertence a
requisição nenhuma — é uma comparação periódica entre o que está no
armazenamento e o que está no banco. São categorias diferentes, e chamar a
segunda de fila só para cumprir o título do item seria montar Redis e um
processo worker para um problema que ninguém tem.

É o mesmo raciocínio que manteve o Redis fora do Item 27, e o mesmo precedente
do Oxlint no Item 16: **o item fica cumprido pela metade explicitamente**, o
que é mais honesto que inteiro por obrigação.

**As três propriedades que o item exige de um job foram implementadas, e cada
uma tem teste:**

| Propriedade | Como |
|---|---|
| idempotente | rodar duas vezes não remove nada na segunda — a primeira já fez os arquivos não existirem |
| observável | toda decisão passa pelo logging do Item 24, com o nome do arquivo |
| seguro | idade mínima de 1h **e** dry-run por padrão |

**A idade mínima é o argumento de segurança inteiro.** Um arquivo gravado há
dois segundos, cuja transação não commitou, é indistinguível de um órfão.
Apagá-lo destruiria um comprovante em voo — o que é pior que o vazamento que a
varredura existe para limpar.

**`FileStorageInterface` ganhou `list_files()`.** É a única operação que precisa
olhar o armazenamento **de fora**: todo outro chamador já sabe o nome que quer,
porque uma linha do banco disse. As duas implementações a cumprem, e a do S3
**pagina** — `list_objects_v2` corta em 1000 chaves e responde truncado em
silêncio, então uma varredura que lesse só a primeira página reportaria o resto
do bucket como "não órfão" simplesmente por nunca ter olhado.

## Consequências

- **O resto do Item 21 fecha.** O `SIGKILL` entre `save()` e commit continua
  criando órfãos — isso é inerente —, mas agora existe algo que os encontra e
  remove.
- **Rodada de verdade contra o projeto, achou 3 órfãos reais**, um em cada
  storage. Não foram removidos: apagar arquivo é decisão de quem opera.
- **Não há agendamento.** É um comando, rodado à mão. Automatizar exige um cron
  ou um agendador do provedor, e não há onde implantar — território dos Itens
  29 e 30.
- **A fila continua sem justificativa, e isso pode mudar.** O gatilho está
  nomeado: se o `STORAGE_BACKEND=s3` for ligado em produção, o
  `storage.save()` vira uma chamada de rede **síncrona dentro da requisição**
  (pendência do Item 22), e aí desacoplar passa a ter motivo. Mas tiraria junto
  a garantia de que o comprovante existe quando a resposta volta — **mudança de
  produto, não otimização.**
