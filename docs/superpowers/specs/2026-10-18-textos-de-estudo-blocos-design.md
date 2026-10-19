# Textos de estudo em blocos: ritmo, componentes e fim dos travessões

Data: 2026-10-18. Discutido em brainstorm, design aprovado em chat. Apresentação
do SIC em 19–23/10/2026, ou seja, a partir de amanhã.

## Contexto e motivação

O módulo educacional (3 Temas, 18 Seções, `app/content.js`) é majoritariamente
texto corrido. Medido em 18/10/2026:

- das 18 Seções, **9 são só texto** (tipo `texto`), com 31 parágrafos de **53
  palavras em média** e o maior com 79; cada Seção de texto tem 150 a 220
  palavras sem nenhuma quebra visual;
- só 3 Seções usam números em destaque (`dados`), 4 usam `destaque` e 2 usam
  `glossario`: os componentes que o app já tem ficam subaproveitados;
- há **55 travessões (—)** no conteúdo e cerca de 7 em textos de interface
  (`app/app.js`). O usuário apontou o travessão como marca de texto gerado por
  IA e quer o texto mais dinâmico e com melhor design.

Restrições herdadas, que esta spec não relaxa:

- **ADR 0001**: o texto é de redação própria, ancorado em fonte oficial. Nunca
  se reproduz o texto do ENCCEJA.
- **Toda afirmação científica precisa de revisão humana** antes de ir ao ar
  (memória do módulo educacional). Por isso a mudança é **de forma, nunca de
  fato**, e vem com um artefato de revisão (ver "Revisão humana").
- **ADR 0003**: o módulo de estudo usa paleta neutra; nenhum componente novo
  pode usar amarelo, laranja ou vermelho.
- O app é offline-first, estático, sem CDN, e abre em `file://`.

## Escopo

**Dentro:**
1. Um tipo novo de Seção, `blocos`, e seis componentes visuais novos.
2. Reescrita da **forma** das 18 Seções, Tema por Tema (parágrafos curtos,
   listas, passos, comparações, perguntas), sem mudar fatos.
3. Remoção de todo travessão (— e –) do texto visível do app.
4. Testes que tornam as regras de forma executáveis.
5. Um diagrama SVG do ciclo da água no Tema 1, **somente se sobrar tempo**
   (última etapa, opcional).

**Fora, deliberado:**
- Os Itens do quiz (perguntas, alternativas, explicações) mudam só no que a
  regra dos travessões exigir; nenhum fato novo.
- As citações de Fonte ficam idênticas.
- Os campos `resumo`, `minutos`, `nivel` não são revisados (exceto
  travessões).
- Nenhum conteúdo novo, nenhum Tema novo, nenhuma Seção nova ou removida.
- Tipografia global, paleta, navegação, progresso (`localStorage`) e o
  percurso do Tema (índice → Seções → Para pensar → quiz) ficam como estão.
- O texto original do INMET no card de aviso (`app/dados.js`) vai sem edição,
  então é isento da regra dos travessões.

## Arquitetura

`montarSecao(s)` em `app/app.js` ganha um ramo `s.tipo === 'blocos'`. A Seção
é uma `<section class="secao">` com o `h2` do título como primeiro filho (o
`renderSecao` já o remove na tela de Seção, como faz hoje) seguido de um filho
por bloco, na ordem do array. Cada tipo de bloco tem uma função pequena que
devolve um nó; um mapa `BLOCOS` liga o nome do tipo à função. Bloco de tipo
desconhecido é ignorado (não derruba a tela). Os quatro tipos antigos
(`texto`, `destaque`, `glossario`, `dados`) continuam existindo e funcionando,
o que permite migrar um Tema por vez com a trilha verde a cada commit.

`escrito(tema)` (`secoes.length > 0 && quiz.length > 0`) e todo o resto do
percurso não mudam.

## Schema dos blocos

Uma Seção nova:

```js
{ tipo: 'blocos', titulo: 'A mesma chuva, dois destinos', blocos: [ ... ] }
```

| bloco | campos | observação |
|---|---|---|
| `p` | `texto` | parágrafo curto: **no máximo 45 palavras** |
| `lista` | `itens: [string]`, `ordenada?: bool` | itens curtos, até 25 palavras cada |
| `passos` | `itens: [{ rotulo, titulo?, texto }]` | sequência numerada com linha conectora; o `rotulo` é livre (`"1"`, `"Minuto 0"`, um ano), então serve de linha do tempo |
| `comparacao` | `lados: [{ titulo, itens: [string] }, { ... }]` | exatamente 2 lados; lado a lado a partir de 520 px, empilhados abaixo |
| `pergunta` | `pergunta`, `resposta` | "Pare e pense": a resposta fica escondida atrás de "Ver a resposta" (`<details>` nativo); **não grava progresso** e não é a Reflexão (essa continua em `reflexoes`) |
| `numeros` | `itens: [{ valor, rotulo, largo? }]`, `nota?` | o `dados` de hoje, como bloco |
| `destaque` | `titulo?`, `texto` | o `destaque` de hoje, como bloco |
| `glossario` | `termos: [{ palavra, definicao }]`, `nota?` | o `glossario` de hoje, como bloco |
| `figura` | `id`, `legenda` | só o diagrama do ciclo da água (opcional), desenhado em SVG inline no `app.js` |

Nenhum campo aceita HTML: todo texto entra por `textContent`.

## Regras de escrita (valem para a reescrita)

1. **Fatos intactos.** Nenhum fato, número, nome próprio, data ou ressalva novo,
   e nenhuma ressalva removida. Cada frase do texto novo é rastreável a uma
   frase do antigo. Reordenar, dividir, cortar repetição e trocar a pontuação
   são permitidos; acrescentar informação não é.
2. **Ritmo.** Um `p` tem até 3 frases e 45 palavras. Sequência vira `passos`,
   enumeração vira `lista`, dois conceitos opostos viram `comparacao`, uma
   pergunta retórica que o texto já faz vira `pergunta`. Uma Seção mistura pelo
   menos dois tipos de bloco.
3. **Sem travessões.** Nem o longo (—) nem o médio (–). Substitui-se, conforme
   o sentido, por ponto, vírgula, dois-pontos ou parênteses. O hífen de palavra
   composta (ex.: "guarda-chuva") fica.
4. **Siglas por extenso** na primeira aparição de cada Tema (já vale hoje).
5. **Sem cor de severidade.** Nada de amarelo, laranja ou vermelho (ADR 0003).

## Design visual (CSS)

Estende `app/styles.css` com as mesmas variáveis do sistema atual
(`--accent`, `--surface`, `--border`, `--radius`, `--sombra-1`), nos dois
temas. Mobile primeiro; nada passa da largura (vigiado por
`tests/app_largura.html`).

- `lista`: marcador na cor de acento, espaçamento entre itens maior que o do
  parágrafo.
- `passos`: círculo com o rótulo à esquerda, linha vertical fina ligando os
  círculos, texto à direita.
- `comparacao`: dois cartões; em tela estreita um sobre o outro, com um
  separador "×" entre eles; lado a lado a partir de 520 px.
- `pergunta`: cartão com o rótulo "Pare e pense", a pergunta em destaque e o
  `<summary>` "Ver a resposta" com alvo de toque de pelo menos 44 px.
- Respeita `prefers-reduced-motion` (a abertura do `<details>` não anima nesse
  caso).

## Revisão humana

Como o risco principal é um fato mudar sem ninguém ver, a entrega de cada Tema
inclui um arquivo de revisão: `reports/revisao_textos_estudo_2026_10_18.md`,
com, para cada Seção, o **texto antigo** e o **texto novo** lado a lado. É o
instrumento que torna a revisão do usuário viável em um dia. As afirmações
científicas só são tratadas como revisadas depois que o usuário confere esse
arquivo.

## Testes

Todos escritos primeiro e vistos falhando (TDD).

`tests/app_smoke.html` (síncrono):
- cada tipo de bloco renderiza a marcação esperada (usando uma Seção de
  fixture, não o conteúdo real);
- um bloco de tipo desconhecido não derruba a Seção;
- `pergunta`: a resposta está dentro de `<details>` fechado e abre ao toque;
- **limite de 45 palavras** em todo `p` de `window.VAND_CONTENT`;
- **nenhum travessão** (— ou –) em `window.VAND_CONTENT` inteiro e no texto
  visível de todas as rotas, exceto dentro de `.aviso-card` (texto original
  do INMET);
- cada Seção migrada tem pelo menos dois tipos de bloco;
- os 62 testes de conteúdo existentes seguem passando.

`tests/app_largura.html`: as rotas das Seções novas, em 320 a 768 px, sem
estouro. Nenhuma mudança no teste, porque ele já percorre todas as rotas;
passa a cobrir os blocos automaticamente.

## Ordem de entrega e riscos

Cada etapa é um commit verde e pode ir ao ar sozinha (`sw.js` sobe de versão a
cada publicação, senão o celular não vê). Etapas:

1. `blocos` + componentes + CSS + testes + travessões da interface.
2. Tema 3 (7 Seções), o que o usuário abriu. Arquivo de revisão do Tema 3.
3. Tema 2 (6 Seções).
4. Tema 1 (5 Seções); diagrama SVG só se sobrar tempo.

Riscos:
- **Prazo.** Apresentação amanhã. Mitigação: a ordem acima entrega valor a cada
  etapa, e as etapas não migradas continuam funcionando no formato antigo.
- **Fato alterado sem querer.** Mitigação: regra de rastreabilidade, arquivo de
  revisão lado a lado, e nenhuma Seção é dada como revisada sem o OK do
  usuário.
- **Cache do celular.** Mitigação: bump do `sw.js` a cada publicação.
- **Um `p` de 45 palavras pode ainda parecer denso.** O teto é um piso de
  qualidade, não a meta: a reescrita mira parágrafos de 20 a 35 palavras.
