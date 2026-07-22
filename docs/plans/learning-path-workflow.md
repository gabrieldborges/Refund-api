# Fluxo de trabalho do Learning Path

Este documento define como cada item do [`learning_path.md`](../../../learning_path.md)
deve ser estudado, implementado e encerrado. Ele é um contrato permanente de
aprendizado e colaboração, não uma lista de requisitos do produto.

## Início de cada sessão

Antes de continuar a trilha:

1. Ler este documento.
2. Ler o [`current-state.md`](current-state.md) para descobrir onde a sessão
   anterior terminou.
3. Ler o [`learning-path-progress.md`](../learning-path-progress.md) para
   recuperar o aprendizado já consolidado.
4. Ler o item atual no [`learning_path.md`](../../../learning_path.md).
5. Consultar no [`docs/index.md`](../index.md) os requisitos e decisões
   canônicos relacionados ao item.
6. Conferir o código e o estado do Git nos repositórios envolvidos. Os
   documentos não substituem a verificação do estado real do projeto.

## Um item por vez

- Seguir a ordem das fases do Learning Path.
- Não iniciar o próximo item enquanto o atual não tiver sido explicado,
  aprovado, implementado, verificado, documentado e commitado.
- Não incluir refatorações, bibliotecas ou abstrações que não sejam necessárias
  ao item atual.
- Se uma pendência externa impedir uma verificação, registrá-la explicitamente;
  não apresentar o item como completamente validado.

## Antes da implementação

Para cada item, apresentar ao Gabriel:

1. **Por que aprender:** qual problema o conceito resolve, quando é útil e qual
   complexidade adiciona.
2. **Estado atual:** mostrar os arquivos e trechos reais envolvidos, explicando
   o fluxo que existe hoje e o que já está correto.
3. **Custo de não mudar:** descrever a falha, limitação ou risco concreto de
   manter o estado atual.
4. **Estado desejado:** explicar a menor evolução capaz de resolver o problema.
5. **Comparação visual:** usar diagrama, tabela ou fluxo antes/depois quando isso
   tornar o conceito mais fácil de entender.
6. **Exemplo aplicado ao Refund:** conectar o conceito novo a um caso real do
   projeto, sem depender apenas de uma explicação abstrata.
7. **Plano incremental:** apresentar arquivos, comportamento esperado e
   verificações, explicando qualquer arquitetura ou biblioteca nova.

A implementação só começa depois da aprovação explícita do plano pelo Gabriel.

## Durante a implementação

- Trabalhar em etapas pequenas, mantendo nomes claros e código legível.
- Para cada conceito acima do nível atual, explicar: problema, solução,
  implementação e mudança observável.
- Preservar a arquitetura existente, salvo quando a alteração arquitetural for
  o próprio objeto de estudo e tiver sido aprovada.
- Adicionar testes junto da mudança quando já existir infraestrutura apropriada
  ou quando o item atual for responsável por introduzi-la.
- Não esconder padrões ruins recorrentes: explicá-los antes de corrigi-los.

## Encerramento obrigatório do item

Antes de avançar para o próximo tópico:

1. Executar as verificações exigidas pelos `AGENTS.md` dos repositórios
   modificados e as verificações específicas do item.
2. Registrar resultados, limitações e validações manuais ainda pendentes.
3. Atualizar o [`learning-path-progress.md`](../learning-path-progress.md) com:
   - o motivo do item;
   - o estado anterior, com caminhos e trechos representativos;
   - a limitação encontrada;
   - a comparação visual;
   - o estado ajustado, também com caminhos e trechos;
   - os arquivos modificados;
   - as verificações executadas e seus resultados;
   - um resumo do conceito e do que deve ser lembrado no futuro.
4. Atualizar o [`current-state.md`](current-state.md) com o item concluído, o
   próximo item e qualquer risco ou pendência relevante.
5. Criar commit em cada repositório alterado somente depois das verificações.
6. Apresentar o fechamento ao Gabriel e aguardar autorização antes de iniciar o
   próximo item.

Os exemplos no diário devem preservar o aprendizado sem duplicar arquivos
inteiros: usar somente os trechos necessários para evidenciar a diferença entre
o antes e o depois.

## Commits entre os repositórios

`Refund-api` e `Refund-FrontEnd` são repositórios Git independentes.

- Um item de frontend normalmente gera um commit de implementação no
  `Refund-FrontEnd` e um commit de documentação canônica no `Refund-api`.
- Um item restrito ao backend pode reunir implementação e documentação em um
  único commit no `Refund-api`, se formarem uma mudança coerente.
- As mensagens de commit devem descrever a responsabilidade daquele
  repositório; não apresentar um commit de documentação como se contivesse a
  implementação do outro repositório.

## Critério para avançar

Um item só está encerrado quando há evidência para todos os pontos abaixo:

- conceito explicado e comparado visualmente;
- plano aprovado;
- implementação concluída;
- verificações executadas com resultados informados;
- diário e estado atualizados;
- commits criados nos repositórios afetados;
- fechamento apresentado ao Gabriel.

Mesmo após esse encerramento, o próximo item depende de nova autorização do
Gabriel.
