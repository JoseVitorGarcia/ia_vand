# Redesign do app: sistema visual novo e as abas Alerta e Registro — Plano de Implementação

> **Para executores agênticos:** implemente tarefa a tarefa, na ordem. Os passos usam
> caixas (`- [ ]`). Não pule a seção "Restrições não-negociáveis" — ela contém decisões
> de projeto já tomadas que este plano NÃO autoriza reabrir.

**Objetivo:** aplicar o sistema visual de `redesign/` ao aplicativo em `app/`, e construir
as duas abas que hoje são placeholder — Alerta e Registro — usando o dado real já extraído
para `app/dados.js`.

**Entrada:** `redesign/vand_visual_system/DESIGN.md` (tokens), três protótipos em
`redesign/*/code.html` (forma e layout) e `redesign/*/screen.png` (referência visual).

**Stack:** HTML, CSS e JavaScript puros. Sem build, sem framework, sem dependência nova.
Os protótipos são Tailwind + CDN: valem como **referência visual, nunca como código**.

**Spec de produto:** `docs/design/brief_telas_alerta_registro.md`
**Vocabulário:** `CONTEXT.md`
**Decisões vinculantes:** `docs/adr/0001`, `0002`, `0003`

---

## Restrições não-negociáveis

Estas já foram decididas e medidas. Implemente como está escrito; não "melhore".

### 1. A marca NÃO entra no cabeçalho fixo

Os três protótipos põem a logo do VAND no topo de todas as telas. **Isso não vai ser
implementado.** `docs/adr/0003` concede exceção ao ponto vermelho `#ec1b04` da marca com a
condição de ela não dividir superfície com Severidade — e a tela de Alerta do protótipo põe
o ponto vermelho a poucos pixels de um chip vermelho de Grande Perigo.

O cabeçalho continua exatamente como hoje: botão voltar, título, subtítulo, barra de
leitura. A marca segue aparecendo **só** na abertura da Trilha (`.hero`).

Também **não** implemente o avatar circular de usuário do canto superior direito: o app não
tem contas (`ESTADO.md`, `app/app.js`).

### 2. As cores de severidade são as do INMET, não as do DESIGN.md

`redesign/vand_visual_system/DESIGN.md` propõe `severity-low: #ffcc00`,
`severity-medium: #ff8800`, `severity-high: #ec1b04`. **Os três estão errados.** O `#ec1b04`
é o vermelho *da marca*, não do INMET. Os valores reais, conferidos em
`cache/avisos_inmet/*.parquet` no campo `aviso_cor`:

| Severidade | `aviso_cor` |
|---|---|
| Perigo Potencial | `#FFFE00` |
| Perigo | `#F96602` |
| Grande Perigo | `#F80703` |

### 3. A cor da severidade nunca recebe texto pequeno em cima

O protótipo desenha o chip "GRANDE PERIGO" como texto branco sobre o vermelho. Com as cores
reais do INMET isso reprova em contraste, e o Grande Perigo reprova **nos dois sentidos**:

| Severidade | texto branco | texto `#14201a` |
|---|---|---|
| `#FFFE00` | 1,08:1 | 15,53:1 |
| `#F96602` | 3,03:1 | 5,54:1 |
| `#F80703` | **4,18:1** | **4,01:1** |

O padrão a implementar: a cor da severidade é **portadora** — faixa superior do card, borda,
ponto —, e o rótulo vai em texto neutro sobre fundo tingido a 14% da cor sobre branco.
Medido: 16,45:1, 14,40:1 e 13,17:1. Ver a tarefa 5 para o CSS exato.

### 4. O par "sim"/"não" mantém as cores medidas, não as do protótipo

O brief escolheu o par para **empatar em contraste**, para que nenhuma das duas puxe o olho
e vire a resposta sugerida. O protótipo propõe `#3b6188` / `#592f4e`, que dá 6,46:1 contra
10,82:1 — o "não" fica 1,7× mais forte e reintroduz exatamente o viés que a escolha existe
para evitar. Mantenha os valores medidos:

| resposta | claro | escuro |
|---|---|---|
| sim, está alagado | `#285076` (8,40:1) | `#9cbce1` (9,51:1) |
| não, está seco | `#6b3f5f` (8,40:1) | `#e8a5cd` (9,51:1) |
| não sei | superfície neutra + `--text` | idem |

No claro os dois são **fundo** de botão com texto branco. No escuro são fundo com texto
`#0d1410`. Nunca verde e nunca vermelho para este par.

### 5. Sem rede: nada de CDN

Os protótipos carregam Inter e Material Symbols do Google Fonts. O app é offline-first
(service worker; "enchente derruba rede"). **Nenhum `<link>` ou `@import` para host externo.**
Ícones são SVG inline; tipografia é a pilha `system-ui` que já está no `styles.css`.

### 6. Regra editorial: os 30% são NOSSOS

O protótipo de Alerta escreve: *"Taxa de Confirmação 30% — cerca de 7 em cada 10 avisos
**nesta severidade** não resultam em dano direto no seu ponto exato"*. Está errado duas vezes:

- Os 30,3% são a taxa de confirmação da **nossa Previsão** (regra ECMWF > 30 mm), não do
  aviso do INMET. Para o Grande Perigo do INMET a taxa no ponto é 3,1% — seriam 97 em 100.
- Atribuir a não-confirmação ao INMET viola o princípio 4 do brief ("nada de acusar o
  INMET"). O enquadramento é **lacuna de granularidade**: o aviso é produto de área recebido
  num ponto.

Use os textos exatos que este plano fornece na tarefa 5. Não reescreva número nem frase de
enquadramento sem passar pelo humano.

### 7. Outras invariantes

- Tema claro **e** escuro, os dois obrigatórios em toda tela nova.
- Vocabulário de `CONTEXT.md` na interface: **Aviso**, **Severidade**, **Previsão**,
  **Registro**. Nunca "alerta" para o aviso do INMET, nunca "report"/"ocorrência".
- Tudo que se move fica atrás de `prefers-reduced-motion` no fim do `styles.css`.
- Alvo de toque mínimo 44px.
- Sem gamificação, pontuação ou comemoração no Registro: a pessoa pode estar com água
  dentro de casa.
- Datas absolutas. Hoje é 22/08/2026.

---

## Estrutura de arquivos

| arquivo | o que muda |
|---|---|
| `app/dados.js` | **já existe, não mexer** — aviso real id 55157 + números medidos |
| `app/styles.css` | tokens novos, tipografia, e o CSS das telas novas |
| `app/app.js` | ícones SVG, `renderAlerta`, `renderRegistro`, rotas novas |
| `app/index.html` | uma linha: carregar `dados.js` antes de `app.js` |
| `app/sw.js` | incrementar `VERSAO` e pôr `dados.js` no precache |
| `tests/app_smoke.html` | os dois testes que exigem `.vazia` precisam mudar |

---

## Tarefa 1 — Tokens em `app/styles.css`

Substitua o bloco `:root` e o bloco `@media (prefers-color-scheme: dark)` pelos valores
abaixo. **Mantenha o comentário de cabeçalho do arquivo**, atualizando-o para citar este
plano. Preserve `--ease`, `--dur` e `--marca` como estão.

- [ ] Tokens do tema claro:

```css
:root {
  --bg: #f8faf8;
  --surface: #ffffff;
  --surface-2: #eaf0ea;
  --surface-3: #eceeec;      /* container aninhado: caixa de estatística, instruções */
  --border: #d6e0d6;
  --border-forte: #c1c9be;
  --text: #14201a;
  --text-dim: #435249;       /* 7,88:1 — mais escuro que o #55685c do DESIGN.md de propósito */

  --accent: #2f5e3a;
  --accent-2: #43855a;
  --accent-soft: #dcefe1;
  --accent-forte: #21502d;   /* texto sobre --accent-soft: 7,77:1 */
  --accent-text: #ffffff;

  --sim: #285076;
  --sim-text: #ffffff;
  --nao: #6b3f5f;
  --nao-text: #ffffff;
  --nao-soft: #f3e7ef;

  /* Severidade — valores do campo aviso_cor do INMET. Ver ADR 0003. */
  --sev-potencial: #FFFE00;
  --sev-perigo: #F96602;
  --sev-grande: #F80703;

  --sombra-1: 0 1px 2px rgba(20, 45, 30, .06);
  --sombra-2: 0 4px 16px -6px rgba(20, 45, 30, .18);
  --sombra-3: 0 14px 40px -12px rgba(20, 45, 30, .26);

  --radius: 16px;
  --radius-sm: 10px;
  --tabbar: 64px;
  --margem: 18px;
}
```

- [ ] Tokens do tema escuro — só o que muda:

```css
@media (prefers-color-scheme: dark) {
  :root {
    --bg: #0d1410;
    --surface: #151e18;
    --surface-2: #1e2a22;
    --surface-3: #243026;
    --border: #2a3a30;
    --border-forte: #3a4d41;
    --text: #e6ece8;
    --text-dim: #a8b5ad;

    --accent: #6cc98a;
    --accent-2: #a7e6bd;
    --accent-soft: #17301f;
    --accent-forte: #6cc98a;
    --accent-text: #06200f;

    --sim: #9cbce1;
    --sim-text: #0d1410;
    --nao: #e8a5cd;
    --nao-text: #0d1410;
    --nao-soft: #2e1b28;

    --sombra-1: 0 1px 2px rgba(0, 0, 0, .4);
    --sombra-2: 0 4px 16px -6px rgba(0, 0, 0, .6);
    --sombra-3: 0 14px 40px -12px rgba(0, 0, 0, .7);

    --marca: url('icons/logo-dark.png');
  }
}
```

Repare que `--sev-*` **não** é redefinido no escuro: a cor do INMET é a mesma nos dois temas,
e o que muda é o tingimento do fundo do chip (tarefa 5).

- [ ] Troque o `padding` de `.wrap` e `.topbar` para usar `var(--margem)` no lugar do `18px`
      literal, e o `20px 18px 40px` de `.wrap` para `20px var(--margem) 40px`.

- [ ] Ajuste `<meta name="theme-color">` em `app/index.html`: o claro passa de `#f4f7f4`
      para `#f8faf8`. O escuro continua `#0d1410`.

## Tarefa 2 — Escala tipográfica

O `DESIGN.md` define sete estilos. Adicione-os como classes utilitárias logo depois do bloco
`html, body`, para que as telas novas os usem por nome em vez de repetir valores.

- [ ] Acrescente:

```css
/* Escala do DESIGN.md. Pesos altos (660/720/740/750) são hierarquia sem depender de cor —
   ver o brief: interface de emergência precisa funcionar em sol forte e pouca luz. */
.t-display { font-size: clamp(2rem, 1.5rem + 3.4vw, 3rem); font-weight: 740; line-height: 1.1; letter-spacing: -0.04em; }
.t-h1      { font-size: clamp(1.5rem, 1.2rem + 1.6vw, 2rem); font-weight: 720; line-height: 1.2; letter-spacing: -0.02em; }
.t-h2      { font-size: 1.25rem; font-weight: 660; line-height: 1.32; letter-spacing: -0.02em; }
.t-body-lg { font-size: 1.125rem; font-weight: 400; line-height: 1.62; }
.t-caps    { font-size: .75rem; font-weight: 750; line-height: 1; letter-spacing: .08em; text-transform: uppercase; }
.t-num     { font-size: 1.5rem; font-weight: 720; line-height: 1; font-variant-numeric: tabular-nums; }
```

`t-display` e `t-h1` usam `clamp()` porque a referência é 430px de largura e o `48px` fixo do
DESIGN.md estoura em telas de 360px.

## Tarefa 3 — Ícones SVG inline

Os protótipos usam Material Symbols. Sem CDN, então os ícones passam a ser SVG inline
gerados no JS.

- [ ] Em `app/app.js`, logo depois de `function el(...)`, acrescente:

```js
  // Ícones em SVG inline: sem requisição de rede e sem fonte de ícone externa.
  // Traçados do conjunto Material Symbols, redesenhados em path simples.
  var ICONES = {
    aviso:    'M12 2 1 21h22L12 2zm0 5 7.5 12.9h-15L12 7zm-1 4v4h2v-4h-2zm0 5v2h2v-2h-2z',
    registro: 'M12 2a10 10 0 100 20 10 10 0 000-20zm0 4a6 6 0 110 12 6 6 0 010-12z',
    estudar:  'M12 2 2 8.5 12 15l10-6.5L12 2zm0 15.2L4.6 12.4 2 14l10 6.5L22 14l-2.6-1.6L12 17.2z',
    relogio:  'M12 2a10 10 0 100 20 10 10 0 000-20zm1 5h-2v6l5 3 1-1.7-4-2.3V7z',
    local:    'M12 2a7 7 0 00-7 7c0 5.2 7 13 7 13s7-7.8 7-13a7 7 0 00-7-7zm0 9.5A2.5 2.5 0 1112 6a2.5 2.5 0 010 5.5z',
    gota:     'M12 2.7S5.5 10 5.5 14.2a6.5 6.5 0 0013 0C18.5 10 12 2.7 12 2.7z',
    sol:      'M12 7a5 5 0 100 10 5 5 0 000-10zm0-6v3m0 16v3M1 12h3m16 0h3M4.2 4.2l2.1 2.1m11.4 11.4 2.1 2.1M19.8 4.2l-2.1 2.1M6.3 17.7l-2.1 2.1',
    duvida:   'M12 2a10 10 0 100 20 10 10 0 000-20zm1 15h-2v-2h2v2zm1.8-6.8-.9.9c-.7.7-.9 1.2-.9 2.4h-2v-.5c0-.9.4-1.7 1-2.4l1.2-1.3c.4-.4.6-.9.6-1.4a2 2 0 00-4 0H8a4 4 0 118 0c0 .8-.3 1.6-.9 2.2z',
    calmo:    'M4 13h6l2-4 2 8 2-4h4',
    grafico:  'M4 20V10h4v10H4zm6 0V4h4v16h-4zm6 0v-7h4v7h-4z'
  };

  // `traco` desenha com stroke em vez de fill — só o sol e a linha do estado calmo usam.
  function icone(nome, tamanho, traco) {
    var NS = 'http://www.w3.org/2000/svg';
    var svg = document.createElementNS(NS, 'svg');
    svg.setAttribute('viewBox', '0 0 24 24');
    svg.setAttribute('width', tamanho || 24);
    svg.setAttribute('height', tamanho || 24);
    svg.setAttribute('aria-hidden', 'true');
    svg.setAttribute('focusable', 'false');
    svg.classList.add('ico');
    var p = document.createElementNS(NS, 'path');
    p.setAttribute('d', ICONES[nome] || '');
    if (traco) {
      p.setAttribute('fill', 'none');
      p.setAttribute('stroke', 'currentColor');
      p.setAttribute('stroke-width', '2');
      p.setAttribute('stroke-linecap', 'round');
      p.setAttribute('stroke-linejoin', 'round');
    } else {
      p.setAttribute('fill', 'currentColor');
    }
    svg.appendChild(p);
    return svg;
  }
```

- [ ] Em `app/styles.css`, acrescente `.ico { display: block; flex: 0 0 auto; }` e remova a
      regra `.tabbar button .ico { font-size: 1.2rem; ... }`, trocando-a por
      `.tabbar button .ico { transition: transform .3s var(--ease); }`.

- [ ] Em `app/index.html`, troque os glifos `◈ ◉ ◇` dos três botões da tabbar por
      `<span class="ico-slot"></span>`, e no início do `app.js` preencha cada slot com
      `icone('aviso'|'registro'|'estudar', 26)` conforme o `data-aba` do botão.

## Tarefa 4 — Re-skin da aba Estudar

Compare com `redesign/estudar_trilha_de_clima_e_gua/screen.png`. O que muda em relação ao
que já existe:

- [ ] **Card de progresso.** Hoje é `.painel`, uma linha fina. No protótipo é um card com
      título "Seu Progresso", a fração em número grande à direita, uma frase de apoio e a
      barra embaixo. Reescreva `.painel` para essa forma, mantendo o `role="progressbar"` e
      os `aria-value*` que já existem. Use `.t-h2` no título e `.t-num` na fração. A fração
      é `feitos + '/' + prontos.length` (o protótipo mostra `0/3`).

- [ ] **Rótulo de seção.** Acrescente um `.t-caps` com o texto `Trilhas de conhecimento`
      acima da lista de cartões (no protótipo, "TRILHAS DE CONHECIMENTO").

- [ ] **Cartão de Tema.** A estrutura já bate. Ajustes: o fio de acento à esquerda
      (`.tema-card::before`) passa a ficar **sempre visível** em vez de crescer no hover —
      é o que o protótipo mostra —, com `transform: scaleY(1)` por padrão e largura 3px;
      no Tema já concluído ele fica em `--accent`, no não iniciado em `--border-forte`.
      Acrescente ao cartão um círculo de 40px com ícone à direita do bloco de título
      (`.tema-icone`, fundo `--surface-3`, cor `--text-dim`) — use `gota` para o Tema 1,
      `calmo` (com traço) para o 2 e `grafico` para o 3, por índice.

- [ ] **Rodapé do cartão.** O `.meta` ganha uma borda superior de 1px `--border` com 12px de
      respiro, e uma seta `→` à direita alinhada ao fim da linha. Mantenha os textos atuais
      (`N min de leitura`, `quiz: X de Y`, `conteúdo em redação`).

- [ ] Não mexa no quiz, nas seções de Tema, no glossário nem nas fontes além dos tokens —
      eles herdam a paleta nova automaticamente.

## Tarefa 5 — Aba Alerta

Referência: `redesign/alerta_aviso_vigente_ajustado/screen.png`. Dado: `window.VAND_DADOS`.

**Duas rotas, dois estados.** O brief diz que 55% dos dias não têm Aviso, e que esse é o
estado mais comum e o mais difícil. Uma apresentação que só mostrasse a tela alarmante
enganaria. Então:

- `#/alerta` → **com Aviso vigente** (usa `VAND_DADOS.aviso`)
- `#/alerta/calmo` → **sem Aviso vigente**

- [ ] Em `rota()`, nada muda: `partes[1]` já captura `calmo`. Em `render()`, troque o ramo
      `r.aba === 'alerta'` por uma chamada a `renderAlerta(r.temaId === 'calmo')`.

- [ ] **Cabeçalho da tela.** `cabecalho('Alerta', 'Aviso oficial do INMET', false)`. Depois,
      no corpo, um bloco com o município em `.t-h1` (`VAND_DADOS.aviso.municipio_exemplo`,
      exibido como `Porto Alegre, RS`) e abaixo um `.t-caps` em `--text-dim` com
      `ÚLTIMA CONSULTA: AGORA MESMO`. À direita, um botão redondo de 44px com o ícone
      `relogio` e `aria-label="Consultar de novo"`. O botão não faz requisição: é protótipo;
      ao clicar, apenas re-renderiza a tela.

- [ ] **Estado calmo** (`#/alerta/calmo`): um card `.card-calmo` com o ícone `calmo` em
      traço, título `Nenhum Aviso vigente` em `.t-h2`, e o corpo:

      > Não há Aviso do INMET em vigor para a sua região agora. Isto não é previsão de tempo
      > bom — é a ausência de aviso, conferida neste momento.

      Fundo `--surface`, borda 1px `--border`, **sem verde de fundo**: o brief é explícito
      que verde é a cor da interface e nunca a cor do estado. Abaixo, a mesma linha de
      `ÚLTIMA CONSULTA` e um link discreto para `#/alerta` com o texto
      `Ver um exemplo de Aviso vigente`.

- [ ] **Card do Aviso** (`.aviso-card`), na ordem do protótipo:

  1. Faixa superior de 6px na cor da severidade (`--sev-grande` para Grande Perigo).
  2. Chip de severidade: fundo tingido, texto neutro, ícone `aviso`. CSS exato:

     ```css
     .sev-chip {
       display: inline-flex; align-items: center; gap: 6px;
       padding: 6px 12px; border-radius: var(--radius-sm);
       background: color-mix(in srgb, var(--sev) 14%, var(--surface));
       border: 1px solid color-mix(in srgb, var(--sev) 55%, var(--surface));
       color: var(--text);
     }
     ```

     A cor entra por `style="--sev: <aviso_cor>"` no elemento, lida de
     `VAND_DADOS.aviso.aviso_cor`. **Nunca** texto branco sobre `--sev` — ver restrição 3.
     No tema escuro o `color-mix` já resolve sozinho, porque `--surface` muda.
  3. Tipo do Aviso em `.t-h2` (`Acumulado de Chuva`).
  4. Linha de vigência com ícone `relogio`: monte a partir de `inicio` e `fim` com
     `Intl.DateTimeFormat('pt-BR')`, no formato `Válido de 28/07 às 09:00 até 29/07 às 10:00`.
  5. Bloco `INSTRUÇÕES OFICIAIS` (`.t-caps`) sobre fundo `--surface-3`, `border-radius`
     `var(--radius-sm)`, listando **todas** as `instrucoes` do dado — são cinco, não duas
     como no protótipo. Cada item com marcador próprio, sem `list-style` nativo.
  6. Bloco `RISCOS` com o mesmo tratamento, listando `riscos`.
  7. Rodapé com `.t-caps` em `--text-dim`:
     `AVISO DO INMET PARA 531 MUNICÍPIOS · id 55157` (use `municipios_total` e `id`).

  **Não** implemente o botão "VER ÁREA AFETADA" do protótipo: não existe mapa no app e um
  botão que não faz nada numa tela de emergência é pior que a ausência dele.

- [ ] **Card da Previsão** (`.previsao-card`), abaixo. Barra vertical de 4px em `--accent` à
      esquerda, título `.t-caps` `PREVISÃO VAND` com ícone `grafico`, e:

      > A nossa Previsão indica risco de chuva acima de 30 mm para a sua região.

      Depois, a caixa de estatística sobre `--surface-3`: label `Taxa de confirmação` à
      esquerda e `30%` em `.t-num` à direita, barra de 6px preenchida a 30% em `--accent`, e
      abaixo, em `.t-body-lg` reduzido, **este texto exato**:

      > Cerca de 3 em cada 10 Previsões nossas se confirmam na estação, e essa regra captura
      > 71% dos eventos. Taxa de confirmação não é taxa de acerto: uma Previsão não
      > confirmada não é um erro, é risco que existia e não se materializou. É por isso que
      > a nossa Previsão não dispara notificação.

- [ ] **Card da lacuna** (`.lacuna-card`), por último, sobre `--surface-2` com borda
      tracejada `--border-forte`. Título `.t-caps` `POR QUE "PARA A SUA REGIÃO"`, e:

      > Este Aviso cobre 531 municípios. Entre os Avisos de Grande Perigo, 59% se confirmam
      > em algum ponto da área coberta e 3,1% se confirmam na estação de quem foi avisado —
      > uma razão de 19 vezes. O Aviso é produto de área recebido num ponto; a diferença é
      > de granularidade, não de qualidade de quem prevê.

      Monte os números a partir de `VAND_DADOS.lacuna`, não os escreva literais no código.

## Tarefa 6 — Aba Registro

Referência: `redesign/registro_a_pergunta_ajustado/screen.png`. É a tela mais importante do
app e a decisão sem conserto retroativo — leia a seção 6 do brief antes de escrever.

- [ ] Rotas: `#/registro` (a pergunta) e `#/registro/enviado` (a confirmação). Em `render()`,
      chame `renderRegistro(r.temaId === 'enviado')`.

- [ ] **A pergunta.** `cabecalho('Registro', 'Registro de alagamento', false)`. No corpo:
      linha `.t-caps` em `--accent` com ícone `local` e o texto `LOCALIZAÇÃO ATUAL`, seguida
      do município; depois a pergunta em `.t-display`: **`Está alagado aí agora?`**

- [ ] **As três respostas.** Botões de largura total, empilhados com 12px, `min-height: 76px`,
      `border-radius: 14px`, rótulo à esquerda em `.t-h2` e ícone à direita. **Peso visual
      idêntico** nos três — mesma altura, mesmo raio, mesma sombra, mesma tipografia. O que
      distingue é só a cor de fundo:

  | botão | rótulo | fundo | texto | ícone |
  |---|---|---|---|---|
  | sim | `SIM, está alagado` | `var(--sim)` | `var(--sim-text)` | `gota` |
  | não | `NÃO, está seco` | `var(--nao)` | `var(--nao-text)` | `sol` (traço) |
  | não sei | `Não sei` | `var(--surface-3)` | `var(--text)` | `duvida` |

  Os três navegam para `#/registro/enviado`, guardando a resposta numa variável de módulo
  para a tela seguinte poder citá-la.

- [ ] **Card de justificativa**, abaixo, sobre `--surface-2` com ícone `duvida`:

      > Alagamento não é chuva. Pela definição oficial (COBRADE 1.2.3.0.0) ele é
      > extrapolação da capacidade do sistema de drenagem — não há uma palavra sobre
      > atmosfera. Nenhum modelo meteorológico prevê alagamento, e é por isso que a pergunta
      > precisa ser feita a uma pessoa.

- [ ] **Rodapé** em `.t-caps`, `--text-dim`, centralizado:
      `SEU REGISTRO SERÁ ASSOCIADO AO AVISO DO INMET VIGENTE PARA FINS DE ANÁLISE.`

- [ ] **Tela de confirmação** (`#/registro/enviado`). Sem comemoração, sem pontuação, sem
      ícone de sucesso verde grande. Um card sóbrio que mostra a amarração — que é o que
      torna o dado útil depois:

      - Título `.t-h2`: `Registro enviado`
      - Lista de pares rótulo/valor: **Resposta** (a escolhida), **Local**
        (`municipio_exemplo`), **Horário** (agora, `Intl.DateTimeFormat` pt-BR com data e
        hora), **Aviso vigente** (`descricao` + `severidade` do dado).
      - Nota final em `--text-dim`:
        > É a amarração com o Aviso vigente que torna o seu registro útil depois. O "não
        > está alagado" vale tanto quanto o "sim": sem ele, só se aprende onde alaga, nunca
        > onde não alaga.
      - Botão `.btn ghost` `Voltar` para `#/registro`.

- [ ] Este protótipo **não persiste** registro. Não invente `localStorage` de registros nem
      contador de envios.

## Tarefa 7 — Service worker e `index.html`

- [ ] Em `app/index.html`, acrescente `<script src="dados.js"></script>` **antes** de
      `content.js`.
- [ ] Em `app/sw.js`, incremente `VERSAO` e acrescente `'dados.js'` à lista de precache.
      Confira se `content.js` está na lista e siga o mesmo formato.

## Tarefa 8 — Atualizar o teste de fumaça

`tests/app_smoke.html:83` e `:85` afirmam que Alerta e Registro mostram `.vazia`. Com as
telas construídas, isso deixa de valer.

- [ ] O `<nav class="tabbar">` do teste precisa dos mesmos `<span class="ico-slot"></span>`
      dos botões, senão o preenchimento de ícones quebra.
- [ ] O teste precisa carregar `app/dados.js` junto de `content.js`.
- [ ] Troque as duas asserções de `.vazia` por:
      - `#/alerta` renderiza `.aviso-card`, e o chip de severidade traz o texto
        `Grande Perigo`, e existem 5 itens de instrução e 1 de risco;
      - `#/alerta/calmo` renderiza `.card-calmo` e **não** renderiza `.aviso-card`;
      - `#/registro` renderiza exatamente 3 botões `.resp`, e os três têm a mesma
        `offsetHeight` (é a garantia executável do peso visual igual);
      - `#/registro/enviado` renderiza `.registro-recibo`.
- [ ] Mantenha o resto do teste intacto: a trilha, o quiz certo e errado, e o progresso
      guardado continuam valendo e não podem regredir.

---

## Verificação

Rode a partir da **raiz** do repositório e cole a saída no relatório final:

```sh
python3 -m http.server 8000 &
google-chrome --headless=new --dump-dom http://localhost:8000/tests/app_smoke.html
```

- [ ] A saída **não** contém a palavra `FALHA`.
- [ ] `grep -rn "fonts.googleapis\|cdn.tailwindcss\|material-symbols" app/` não retorna nada.
- [ ] `grep -rn "#ffcc00\|#ff8800\|#ec1b04\|#3b6188\|#592f4e" app/` não retorna nada.
- [ ] `grep -c "VERSAO" app/sw.js` confirma que a versão foi tocada, e o valor é maior que o
      anterior.
- [ ] Percorra as seis telas (`#/estudar`, um Tema, `#/alerta`, `#/alerta/calmo`,
      `#/registro`, `#/registro/enviado`) e confirme que nenhuma tem rolagem horizontal a
      430px de largura.

## Fora de escopo

Não implemente, mesmo que o protótipo ou o brief mencionem: mapa ou polígono, notificação
real, geolocalização, telas de notificação de Grande Perigo e Perigo, lista de registros
próximos, contas de usuário. São itens separados do brief e não estão neste plano.
