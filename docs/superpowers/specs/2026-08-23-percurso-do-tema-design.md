# O percurso de um Tema: índice, Seção por tela e progresso retomável

Design validado em 23/08/2026. Substitui a tela única de um Tema por um percurso
navegável. Nenhuma palavra do conteúdo muda.

## O problema, medido

Um Tema hoje renderiza tudo numa tela só: todas as Seções, depois as Reflexões,
depois o quiz, depois as Fontes. Medido no protótipo, a 390px de largura:

| Tema | altura | telas de rolagem | o quiz começa em |
|---|---|---|---|
| De onde vem a chuva | 4.080px | 5,7 | 4,6 telas abaixo |
| Quando a chuva vira enchente | 7.178px | 10,0 | 7,9 telas abaixo |
| Clima em mudança e risco na cidade | 8.662px | 12,1 | 10,2 telas abaixo |

Três consequências, e são elas que este design ataca:

1. **Parece página, não aplicativo.** É a mesma crítica que motivou o app shell:
   um bloco de texto rolando não é como um app de celular apresenta conteúdo.
2. **Não dá para achar nada de volta.** Sem índice, sem âncora e sem busca,
   reencontrar uma definição exige rolar caçando.
3. **A pessoa desiste no meio.** Doze telas sem marco intermediário: nenhuma
   sensação de avanço, nenhum ponto de parada, nada guardado se sair.

Um quarto problema foi considerado e **descartado**: distribuir as questões do
quiz ao longo do texto, para checar compreensão perto do trecho que a originou.
Não é a dor a resolver, e distribuir custaria reescrever conteúdo.

## Decisões que restringem o design

- **O texto não muda.** `docs/adr/0001` exige revisão humana de toda afirmação
  científica. Este design é de apresentação; nenhum parágrafo é reescrito,
  cortado ou reordenado. As Seções já vêm bem balanceadas (~300 palavras cada) e
  já têm títulos descritivos, então servem de unidade sem tocar no conteúdo.
- **Nada trava.** `docs/adr/0002` fixa que Nível é sinalização, não trava, e a
  tela de resultado do quiz já diz que nada trava o próximo Tema. O quiz é
  alcançável desde o primeiro segundo, com zero Seções lidas.
- **Nada de gamificação.** Sem pontos, sem sequência, sem "desbloqueou", sem
  comemoração. O único número é o resultado do quiz, que já existe.
- **Vocabulário de `CONTEXT.md`.** Trilha, Tema, Nível, Seção, Item, Reflexão,
  Fonte. Este design **não introduz termo novo** — "índice" e "percurso"
  descrevem a navegação, não são entidades do domínio.

## Rotas

| rota | tela |
|---|---|
| `#/estudar` | a Trilha (inalterada) |
| `#/estudar/<tema>` | **índice do Tema** — era o texto inteiro |
| `#/estudar/<tema>/s/<n>` | a Seção `n`, **contada a partir de 1** |
| `#/estudar/<tema>/pensar` | Para pensar (as Reflexões) |
| `#/estudar/<tema>/fontes` | Fontes |
| `#/estudar/<tema>/quiz` | o quiz |

O segmento `s/` antes do número não é enfeite: sem ele, um Tema cujo id fosse
`quiz`, `pensar` ou `fontes` colidiria com as palavras-chave e o roteador
escolheria a tela errada.

**A rota conta a partir de 1 e o armazenamento a partir de 0.** `s/1` é a
primeira Seção, que é `tema.secoes[0]` e que grava `0` em `lidas`. A rota usa a
numeração que a pessoa vê na tela; a lista usa índice de array. A conversão
acontece num lugar só, na entrada do roteador — misturar as duas convenções pelo
código é a origem clássica do erro de um.

Botão voltar do cabeçalho: no índice volta para a Trilha; em qualquer outra tela
do Tema volta para o índice.

Rota inválida (`<n>` fora de faixa, palavra-chave desconhecida) cai no índice do
Tema, do mesmo jeito que uma aba desconhecida hoje cai em `#/estudar`.

## A tela de índice

Título grande com o nome do Tema; subtítulo `<Nível> · <N> min`.

Uma barra de progresso — `3 de 7 seções lidas` — e a lista, com as Seções
numeradas mostrando título e estado (lida / não lida), seguidas de três itens
irmãos: **Para pensar**, **Fontes** e **Quiz — 5 questões**.

O estado de uma Seção é binário e visível sem depender só de cor: o item lido
ganha marca e rótulo textual, não apenas um tom diferente. Isto é interface de
emergência e o brief exige que nada dependa exclusivamente de cor.

## A tela de Seção

Título grande = título da Seção. Subtítulo = `<nome do Tema> · 3 de 7`.

O corpo renderiza com exatamente os mesmos quatro tipos de hoje — `texto`,
`destaque`, `glossario`, `dados` — sem alteração de marcação nem de CSS. O que
muda é o recorte: uma Seção por tela, o que derruba de ~12 telas de rolagem para
cerca de 1,5.

No rodapé, um botão que encadeia o percurso:

```
Seção 1 → Seção 2 → … → Seção n → Para pensar → [Fazer o quiz]
```

Fontes fica **fora** da corrente. É material de consulta, não etapa de leitura;
alcança-se pelo índice.

É o toque nesse botão que marca a Seção como lida. A alternativa — rastrear
rolagem — foi descartada por dois motivos: quem só espiou ganharia o selo, e uma
Seção mais curta que a tela nunca dispararia o evento.

A barra de leitura do cabeçalho passa a medir a Seção atual. Ela finalmente
mede algo: numa página de 12 telas ficava praticamente parada.

## Progresso

A chave `vand.progresso.v1` ganha um campo na entrada que já existe:

```js
{ "de-onde-vem-a-chuva": { acertos: 5, total: 5, em: "…", lidas: [0, 1, 2] } }
```

**A versão da chave não muda.** Entrada gravada antes deste design não tem
`lidas` e lê como lista vazia — ninguém perde o quiz que já fez. `lidas` guarda
índices de Seção, é idempotente (reler não desmarca, marcar duas vezes não
duplica) e é independente do resultado do quiz.

Ler uma Seção grava progresso na hora, e não ao fim do Tema: é isso que torna o
Tema retomável, que era a terceira dor.

## A Trilha

O cartão de um Tema hoje mostra `8 min de leitura · 5 questões`. Passa a mostrar
o estado real, para que "retomável" apareça antes de entrar:

| situação | o que o cartão diz |
|---|---|
| não começado | `8 min de leitura · 5 questões` |
| leitura em curso | `8 min de leitura · 3 de 7 seções` |
| quiz feito | `8 min de leitura · quiz: 5 de 5` |

A barra de progresso da Trilha continua contando Temas com quiz feito, como
hoje. Não passa a contar Seções: são grandezas diferentes e somá-las confundiria.

### Uma regressão que este design causa se não for tratada

`renderTrilha` hoje decide "Tema concluído" por **existência de entrada**:

```js
var feitos = prontos.filter(function (t) { return p[t.id]; }).length;
var feito = p[tema.id];   // depois usa feito.acertos
```

Isso funciona hoje porque a entrada só nasce quando o quiz termina. A partir
deste design a entrada nasce ao ler a **primeira Seção** — e então a barra da
Trilha passaria a contar Temas apenas lidos como concluídos, e o cartão
mostraria `quiz: undefined de undefined`.

As duas leituras precisam passar a testar o resultado do quiz, não a entrada:
`p[t.id] && p[t.id].total > 0`. É a única mudança de comportamento que este
design impõe a código que já estava correto, e é obrigatória.

## Fim do quiz

A tela de resultado hoje oferece "Refazer o quiz" e "Voltar à trilha". Ganha um
terceiro destino, porque agora existe um nível intermediário: **"Voltar ao
Tema"**, que leva ao índice. O texto de apoio ("Refazer é livre — nada aqui trava
o próximo tema") não muda.

## Impacto no que já existe

| arquivo | impacto |
|---|---|
| `app/content.js` | **nenhum** — a estrutura de dados já serve |
| `app/app.js` | `renderTema` se desdobra em índice + Seção + Reflexões + Fontes; roteador ganha os segmentos; progresso ganha `lidas` |
| `app/styles.css` | classes novas para o índice e o rodapé de encadeamento; o CSS das Seções não muda |
| `tests/app_smoke.html` | `percorre()` precisa ser reescrita — ver abaixo |
| `app/sw.js` | incrementar `VERSAO` |

`percorre()` hoje conta `.secao`, `.reflexao` e `.fontes li` numa tela só, e
depois responde o quiz ali mesmo. Com o percurso, ela vira uma travessia: abre o
índice, confere que lista todas as Seções, percorre uma a uma pelo botão de
encadeamento, confere que o índice passa a marcar as lidas, e só então entra no
quiz. As asserções de quiz e de gravação de progresso continuam valendo sem
alteração — inclusive a de que refazer pior não apaga o melhor resultado.

## Uma inconsistência de vocabulário, a decidir

`CONTEXT.md` define **Item** como a questão de múltipla escolha e lista
explicitamente `questão` entre os termos a evitar. Mas a interface de hoje já diz
"Questão 1 de 5" no quiz e "5 questões" no cartão da Trilha — ou seja, o desvio é
anterior a este design.

Este design **não resolve** isso, e propaga o termo para a tela de índice ("Quiz
— 5 questões"). São dois caminhos, e é decisão editorial de quem assina:

- trocar a interface inteira para "Item" (`Item 1 de 5`, `5 itens`), ou
- assumir que "Item" é vocabulário interno de código e conteúdo, e que a
  interface fala "questão" de propósito, ajustando o `CONTEXT.md` para dizê-lo.

Enquanto não se decide, a tela nova segue o que as telas existentes já falam —
ser consistente com o app importa mais que ser consistente com o glossário numa
tela só.

## Fora de escopo

Decidido deixar de fora, e não por esquecimento:

- **Tela de fecho entre a leitura e o quiz.** A dor apontada foi o quiz estar
  enterrado, não chegar sem aviso; o último passo do percurso simplesmente diz
  "Fazer o quiz".
- **Questões distribuídas pelo texto.** Ver "O problema, medido".
- **Trava de sequência**, marcar Tema como concluído por leitura, busca dentro do
  Tema, favoritar Seção, anotações, e qualquer contagem além do resultado do quiz.
