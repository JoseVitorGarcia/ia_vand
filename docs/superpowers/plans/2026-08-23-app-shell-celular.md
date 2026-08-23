# Estrutura de aplicativo de celular: app shell, título colapsável e moldura — Plano de Implementação

> **Para executores agênticos:** implemente tarefa a tarefa, na ordem. Os passos usam
> caixas (`- [ ]`). A tarefa 2 contém a armadilha central deste plano (a barra de leitura);
> não a pule nem improvise em cima dela.

**Objetivo:** reorganizar `app/index.html` e o layout para uma estrutura de aplicativo de
celular de verdade — cromo fixo, uma única região rolável, título grande que colapsa, e
moldura de celular em tela larga.

**O que está errado hoje:** o documento inteiro rola, então cabeçalho e barra de abas não são
cromo fixo; a ordem no DOM é `nav → header → main`, invertida em relação ao visual; faltam as
metatags de app instalado; não há `overscroll-behavior`, `touch-action` nem supressão do
realce de toque; e em ≥760px o app vira um documento com as abas no topo.

**Stack:** HTML, CSS e JavaScript puros. Sem build, sem framework, sem dependência nova.

**Decisões já tomadas com o humano — não reabrir:**
1. **App shell**: só o `<main>` rola; cabeçalho e barra de abas são cromo fixo.
2. **Título grande que colapsa** numa barra compacta ao rolar.
3. **Moldura de celular centralizada** em tela larga.

**Vinculantes:** `docs/adr/0003`, `docs/design/brief_telas_alerta_registro.md`, `CONTEXT.md`.

---

## Restrições não-negociáveis

- **Não desabilite o zoom.** Os protótipos em `redesign/` usam
  `maximum-scale=1.0, user-scalable=no`. Isso é regressão de acessibilidade e o brief exige
  "acessibilidade acima do normal". A metatag `viewport` mantém `width=device-width,
  initial-scale=1, viewport-fit=cover` e mais nada.
- **Nada de rede.** Nenhum `<link>` ou `@import` para host externo. Ícones seguem SVG inline.
- **`user-select: none` só no cromo** (cabeçalho e barra de abas). O conteúdo precisa
  continuar selecionável — a tela de Aviso traz os telefones da Defesa Civil e do Corpo de
  Bombeiros, e a pessoa pode querer copiar.
- **Tema claro e escuro** nos dois, sempre.
- Movimento atrás de `prefers-reduced-motion`.
- Alvo de toque mínimo 44px.
- Vocabulário de `CONTEXT.md`: Aviso, Severidade, Previsão, Registro.
- Datas absolutas. Hoje é 23/08/2026.

---

## Estrutura de arquivos

| arquivo | o que muda |
|---|---|
| `app/index.html` | esqueleto do shell, ordem do DOM, metatags |
| `app/styles.css` | layout do shell, título colapsável, moldura, toque |
| `app/app.js` | rolagem no container, cabeçalho colapsável, posição por aba |
| `app/manifest.webmanifest` | cores desatualizadas |
| `app/sw.js` | incrementar `VERSAO` |
| `tests/app_smoke.html` | espelhar o shell, e **carregar o `styles.css`** |

---

## Tarefa 1 — O esqueleto em `app/index.html`

- [ ] Reescreva o `<body>` nesta ordem — cabeçalho, conteúdo, abas. A ordem do DOM passa a
      bater com a ordem visual, que é o que o leitor de tela anuncia:

```html
<body>
<div class="app">

  <header class="topbar" id="topbar">
    <button type="button" class="backbtn" id="voltar" hidden aria-label="Voltar">←</button>
    <p class="topbar-titulo" id="topbar-titulo" aria-hidden="true"></p>
    <div class="progresso-leitura" id="progresso-leitura" aria-hidden="true"></div>
  </header>

  <main class="conteudo" id="conteudo" tabindex="-1">
    <div class="wrap" id="tela"></div>
  </main>

  <nav class="tabbar" aria-label="Seções do aplicativo">
    <button type="button" data-aba="alerta"><span class="ico-slot"></span>Alerta<span class="selo" id="selo-alerta" aria-hidden="true"></span></button>
    <button type="button" data-aba="registro"><span class="ico-slot"></span>Registro</button>
    <button type="button" data-aba="estudar"><span class="ico-slot"></span>Estudar</button>
  </nav>

</div>
<script src="dados.js"></script>
<script src="content.js"></script>
<script src="app.js"></script>
</body>
```

Repare em três mudanças de contrato que o `app.js` vai precisar acompanhar:

- O `#tela` **deixa de ser o `<main>`** e vira um `<div>` dentro dele. Quem rola é
  `#conteudo`; quem recebe o conteúdo renderizado continua sendo `#tela`.
- O `<h1 id="titulo">` **sai do cabeçalho**. O título grande passa a ser renderizado no topo
  do conteúdo (tarefa 4), e o cabeçalho ganha um `<p class="topbar-titulo">` que só aparece
  quando o grande sai de vista. É `aria-hidden` porque duplica o `<h1>` do conteúdo.
- `tabindex="-1"` migra para o `#conteudo`, que é o que recebe foco a cada troca de tela.

- [ ] Acrescente as metatags de app instalado, logo depois da `viewport`:

```html
<meta name="mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-status-bar-style" content="default">
<meta name="apple-mobile-web-app-title" content="VAND">
<meta name="color-scheme" content="light dark">
```

`apple-mobile-web-app-capable` está formalmente obsoleta em favor da primeira, mas o iOS
ainda só obedece a ela. As duas ficam.

## Tarefa 2 — O shell em `app/styles.css`

- [ ] Substitua as regras de `html`, `body` e `.wrap` por:

```css
html, body {
  height: 100%;
  margin: 0;
  padding: 0;
  /* O documento não rola: quem rola é .conteudo. Sem isto, o iOS dá o efeito
     elástico no documento inteiro e o cromo fixo balança junto. */
  overflow: hidden;
  overscroll-behavior: none;
  background: var(--bg);
  color: var(--text);
  font-family: system-ui, -apple-system, "Segoe UI", Roboto, sans-serif;
  font-size: clamp(16px, 1rem + .2vw, 18px);
  line-height: 1.62;
  -webkit-text-size-adjust: 100%;
  -webkit-font-smoothing: antialiased;
}

.app {
  position: relative;      /* âncora do brilho de fundo; ver abaixo */
  display: grid;
  grid-template-rows: auto 1fr auto;
  height: 100vh;           /* fallback */
  height: 100dvh;          /* desconta a barra do navegador quando ela aparece */
  overflow: hidden;
  isolation: isolate;
}

.conteudo {
  min-height: 0;           /* sem isto o filho de grid não encolhe e nada rola */
  overflow-y: auto;
  overflow-x: hidden;
  overscroll-behavior-y: contain;
  -webkit-overflow-scrolling: touch;
  scroll-behavior: smooth;
  scroll-padding-top: 20px;
  position: relative;
  z-index: 1;
}

.wrap {
  max-width: 760px;
  margin: 0 auto;
  padding: 0 var(--margem) 40px;
  position: relative;
  z-index: 1;
}
```

- [ ] `body { padding-bottom: ... }` some: o shell é grid, e a barra de abas é uma linha do
      grid em vez de um elemento fixo sobreposto. Remova também o `scroll-padding-top: 76px`
      do `html`.

- [ ] **O brilho de fundo.** Hoje é `body::before` com `position: fixed`. Elemento fixo
      escapa do recorte da moldura (tarefa 6) e ia vazar por cima dela. Mova para dentro do
      shell:

```css
.app::before {
  content: "";
  position: absolute;
  inset: 0 0 auto 0;
  height: 60vh;
  background: radial-gradient(60% 60% at 50% 0%, var(--accent-soft) 0%, transparent 70%);
  opacity: .7;
  pointer-events: none;
  z-index: 0;
}
```

- [ ] **Comportamento de toque.** Acrescente perto do topo do arquivo:

```css
* {
  box-sizing: border-box;
  -webkit-tap-highlight-color: transparent;
}
/* `manipulation` derruba o atraso de ~300ms que o navegador guarda esperando
   um duplo-toque de zoom. Não desabilita o zoom por pinça. */
button, a, [role="button"] { touch-action: manipulation; }
/* Só o cromo. O conteúdo continua selecionável: a tela de Aviso traz telefones. */
.topbar, .tabbar { -webkit-user-select: none; user-select: none; }
```

- [ ] **A barra de abas deixa de ser `fixed`.** É a última linha do grid:

```css
.tabbar {
  position: relative;      /* era fixed */
  height: calc(var(--tabbar) + env(safe-area-inset-bottom, 0px));
  padding-bottom: env(safe-area-inset-bottom, 0px);
  /* o resto — fundo, blur, borda, display:flex — continua como está */
}
```

  Apague `bottom/left/right` e o `z-index: 30`.

- [ ] **O cabeçalho deixa de ser `sticky`.** É a primeira linha do grid: troque
      `position: sticky; top: 0;` por `position: relative;`, mantenha
      `padding-top: calc(10px + env(safe-area-inset-top, 0px))`, e mantenha a transição de
      `border-color`/`box-shadow` que a classe `.rolado` aciona.

- [ ] **A barra de leitura — a armadilha.** Hoje ela é:

```css
@supports (animation-timeline: scroll()) {
  .lendo .progresso-leitura { animation: encher linear both; animation-timeline: scroll(root block); }
}
```

  `scroll(root)` referencia a rolagem do **documento**, que a partir de agora não rola nunca.
  E trocar por `scroll(nearest)` não resolve: a barra mora no cabeçalho, que está **fora** do
  `.conteudo`, então `nearest` volta a resolver para a raiz. A saída correta em CSS puro
  exigiria `scroll-timeline` nomeada mais `timeline-scope` no `.app`, o que estreita muito o
  suporte de navegador.

  **Apague o bloco `@supports` e o `@keyframes encher`.** A barra passa a ser movida pelo
  mesmo ouvinte de rolagem que o cabeçalho colapsável já vai precisar (tarefa 3), via
  variável CSS:

```css
.progresso-leitura {
  position: absolute;
  left: 0; right: 0; bottom: -1px;
  height: 2px;
  background: linear-gradient(90deg, var(--accent), var(--accent-2));
  transform-origin: 0 50%;
  transform: scaleX(var(--lido, 0));
  border-radius: 0 2px 2px 0;
  opacity: 0;
  transition: opacity .2s var(--ease);
}
.lendo .progresso-leitura { opacity: 1; }
```

  Fica mais simples e funciona em todo navegador, em vez de só nos que têm
  `animation-timeline`.

## Tarefa 3 — Rolagem e cabeçalho colapsável em `app/app.js`

- [ ] Troque as referências de elemento no topo do arquivo: `tela` continua sendo
      `#tela`, e acrescente `conteudo` (`#conteudo`), `topbarTitulo` (`#topbar-titulo`) e
      `app` (`.app`). O `titulo`/`subtitulo` do cabeçalho antigo deixam de existir.

- [ ] **`cabecalho()` muda de contrato.** Em vez de escrever no `<h1>` do cabeçalho, ela
      passa a guardar o título e o subtítulo da tela e a inserir o **título grande** como
      primeiro filho do `#tela`:

```js
  var tituloAtual = '';

  function cabecalho(t, s, mostrarVoltar, alvoVoltar) {
    tituloAtual = t;
    topbarTitulo.textContent = t;
    voltar.hidden = !mostrarVoltar;
    voltar.onclick = function () { ir(alvoVoltar || '#/estudar'); };
    // O título grande vive no conteúdo e rola junto; o do cabeçalho é o que
    // aparece quando este sai de vista.
    tela.appendChild(
      el('div', { class: 'tela-titulo' }, [
        el('h1', { class: 't-h1', text: t }),
        s ? el('p', { class: 'sub', text: s }) : null
      ])
    );
  }
```

  Como `limpar()` esvazia o `#tela` antes de cada `render()`, e todas as telas chamam
  `cabecalho()` como primeira coisa, o título grande sai sempre no topo. **Confira tela a
  tela** que `cabecalho()` é de fato chamada antes de qualquer `tela.appendChild`; onde não
  for, reordene.

- [ ] **A tela de Alerta já tem um `<h1 class="t-h1">` com o município** (`app.js:454`).
      Com o título grande da aba acima dele, ficariam dois títulos grandes empilhados.
      Rebaixe o do município para `.t-h2` e deixe-o como subtítulo de contexto logo abaixo
      do título grande, junto da linha `ÚLTIMA CONSULTA`.

- [ ] **Um único ouvinte de rolagem**, substituindo o `window.addEventListener('scroll', ...)`
      atual (que hoje só marca `.rolado`):

```js
  var limiarColapso = 0;

  function aoRolar() {
    var y = conteudo.scrollTop;
    topbar.classList.toggle('rolado', y > 4);
    app.classList.toggle('compacto', y > limiarColapso);

    // Barra de leitura: fração do Tema já percorrida.
    if (document.body.classList.contains('lendo')) {
      var alcance = conteudo.scrollHeight - conteudo.clientHeight;
      var lido = alcance > 0 ? Math.min(1, y / alcance) : 0;
      progressoLeitura.style.setProperty('--lido', lido.toFixed(4));
    }
  }

  conteudo.addEventListener('scroll', aoRolar, { passive: true });
```

  `limiarColapso` é recalculado no fim de cada `render()`:
  `var tg = tela.querySelector('.tela-titulo'); limiarColapso = tg ? tg.offsetHeight - 12 : 0;`
  O `- 12` faz o título do cabeçalho aparecer um instante antes de o grande sumir por
  completo, senão há um quadro em que nenhum dos dois está visível.

- [ ] **`render()` deixa de usar `window.scrollTo`.** Troque por `conteudo.scrollTop = <pos>`
      e `conteudo.focus({ preventScroll: true })` no lugar de `tela.focus(...)`.

- [ ] **Posição de rolagem por aba.** Um app de celular volta para onde a pessoa estava.
      Guarde num mapa por rota, salvando a posição da tela que sai antes de limpar:

```js
  var posicoes = {};
  var rotaAnterior = null;
```

  No começo de `render()`, antes de `limpar()`:
  `if (rotaAnterior) posicoes[rotaAnterior] = conteudo.scrollTop;`
  No fim, depois de montar a tela:
  `var r0 = location.hash; conteudo.scrollTop = posicoes[r0] || 0; rotaAnterior = r0;`

  **Exceção:** a tela de um Tema (`#/estudar/<id>`) sempre abre no topo — ninguém quer
  reabrir um texto no meio. Force `0` e não guarde posição para ela.

- [ ] **`raiz.scrollIntoView(...)` no quiz** (`app.js:384`) continua funcionando dentro de um
      container rolável, mas com `scroll-padding-top: 20px` no `.conteudo` em vez dos 76px que
      compensavam a topbar fixa. Confira que a pergunta não fica escondida atrás do cabeçalho.

## Tarefa 4 — CSS do título grande e do cabeçalho compacto

- [ ] O título grande, no topo do conteúdo:

```css
.tela-titulo { padding: 18px 0 14px; }
.tela-titulo h1 { margin: 0; }
.tela-titulo .sub {
  margin: 6px 0 0;
  color: var(--text-dim);
  font-size: .92rem;
}
```

- [ ] O título do cabeçalho, que só entra quando o grande sai:

```css
.topbar-titulo {
  margin: 0;
  font-size: 1.02rem;
  font-weight: 660;
  letter-spacing: -0.015em;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  opacity: 0;
  transform: translateY(6px);
  transition: opacity .22s var(--ease), transform .22s var(--ease);
}
.app.compacto .topbar-titulo { opacity: 1; transform: translateY(0); }
```

- [ ] O cabeçalho fica baixo por padrão e ganha a sombra ao rolar (a classe `.rolado` já
      existe). Garanta `min-height: 56px` e que ele não cresça quando o título entra.

- [ ] Em `prefers-reduced-motion`, o título do cabeçalho aparece sem deslizar — só troca de
      opacidade. As regras globais de `transition-duration` no fim do arquivo já cobrem isso;
      confira que cobrem.

## Tarefa 5 — Correções de bug encontradas na inspeção

Estas são independentes do shell e todas verificadas. Faça todas.

- [ ] **`app.js:454` escreve "Porto Alegre - RS, RS".** O dado
      (`dados.aviso.municipio_exemplo`) já é `"Porto Alegre - RS"` e o código anexa `", RS"`.
      Corrija formatando o próprio dado: troque `" - "` por `", "` e não anexe nada.
      Aplique também em `app.js:589` (tela de Registro enviado), que hoje mostra o valor cru
      com o hífen.

- [ ] **O chip de Severidade vaza para fora do card.** A causa é
      `.aviso-card > * { padding: 0 20px }`, que empurra padding para todo filho direto; o
      `.sev-chip` tem `padding` próprio e portanto perde o recuo, encostando na borda e
      subindo por cima da faixa de severidade. Substitua o truque por um invólucro real:
      envolva o conteúdo do card num `.aviso-corpo` com `padding: 16px 20px`, e **apague as
      três regras** `.aviso-card > *`, `> *:first-of-type` e `> *:last-of-type`. A faixa
      (`.aviso-card::before`) continua fora do invólucro, coladinha no topo.

- [ ] **O ícone `relogio` renderiza como disco preto sólido.** Os subcaminhos têm o mesmo
      sentido de giro, então `fill-rule: nonzero` preenche tudo. Passe a emitir
      `fill-rule="evenodd"` no `<path>` da função `icone()` — verificado nos 11 ícones: não
      altera nenhum dos outros e conserta este.

- [ ] **O botão de recarregar usa um relógio.** Troque por um ícone de recarregar de verdade,
      acrescentando a `ICONES`:
      `recarregar: 'M17.65 6.35A7.96 7.96 0 0012 4a8 8 0 108 8h-2a6 6 0 11-6-6c1.66 0 3.14.69 4.22 1.78L13 11h7V4l-2.35 2.35z'`
      e use `icone('recarregar', 20)` no botão de `aria-label="Consultar de novo"`.

- [ ] **O ícone `duvida` é um disco preto pesado** e desequilibra o botão "Não sei" contra os
      outros dois. Passe a desenhá-lo com traço (`icone('duvida', 32, true)`) e a colori-lo
      com `var(--text-dim)`.

- [ ] **Estilo embutido no JS.** `app.js:457` carrega um `style` inline gigante para o botão
      redondo. Mova para uma classe `.btn-circular` no `styles.css` (44px, borda 1px
      `--border`, `border-radius: 50%`, `display: grid; place-items: center`) e use
      `{ class: 'btn-circular' }`. Confira os outros usos de `style:` no arquivo e mova os que
      forem aparência fixa; deixe só os que carregam valor calculado (largura de barra).

- [ ] **`app/manifest.webmanifest` está com a paleta antiga.** `background_color` é
      `#f4f7f4` — troque por `#f8faf8`, que é o `--bg` atual. E `theme_color` é `#2f5e3a`
      (verde), que briga com o `<meta name="theme-color" content="#f8faf8">`: em modo
      instalado a barra do sistema fica verde e o topo da página off-white, com uma emenda
      visível. Alinhe `theme_color` em `#f8faf8`.

- [ ] **Telefones tocáveis.** As instruções do INMET trazem "Defesa Civil (telefone 199)" e
      "Corpo de Bombeiros (telefone 193)". Num app de celular, numa tela de emergência, isso
      precisa ser tocável. Ao montar cada `<li>` de instrução, quebre o texto com
      `/telefone (\d{3})/` e troque a captura por um `<a href="tel:199">199</a>`. Estilize
      `.aviso-bloco a` com `color: var(--accent)` e sublinhado. Use `textContent` nos pedaços
      de texto — **não** monte HTML por concatenação de string.

## Tarefa 6 — Moldura de celular em tela larga

- [ ] **Apague inteiro** o bloco `@media (min-width: 760px)` que existe hoje: ele torna o
      cabeçalho estático e joga a barra de abas para o topo, que é exatamente a aparência de
      documento que este plano está removendo.

- [ ] No lugar:

```css
/* ---------- tela larga: o app vira uma moldura de celular ---------- */
@media (min-width: 900px) {
  body {
    display: grid;
    place-items: center;
    background: var(--surface-2);
  }
  .app {
    width: 420px;
    height: min(880px, calc(100dvh - 48px));
    border-radius: 30px;
    border: 1px solid var(--border);
    box-shadow: var(--sombra-3);
    overflow: hidden;
  }
}
```

  O recorte da moldura é o motivo de o brilho de fundo ter saído de `position: fixed` na
  tarefa 2 — elemento fixo ignora o `overflow: hidden` do ancestral e vazaria por cima da
  borda arredondada.

- [ ] Entre 760px e 900px o app ocupa a largura toda, como no celular. É intencional: tablet
      em retrato é uso de app, não de documento.

## Tarefa 7 — Service worker

- [ ] Incremente `VERSAO` em `app/sw.js` (está em `vand-v6`). Nenhum arquivo novo entra no
      precache — o shell não acrescenta arquivo.

## Tarefa 8 — Atualizar o teste de fumaça

`tests/app_smoke.html` monta um esqueleto próprio, e ele vai deixar de bater com o que o
`app.js` espera (`#conteudo`, `#topbar-titulo`, `#tela` dentro do `<main>`).

- [ ] Espelhe o esqueleto da tarefa 1 no `<body>` do teste, mantendo o `<pre id="saida">`
      **fora** do `.app` para continuar legível no `--dump-dom`.

- [ ] **Acrescente `<link rel="stylesheet" href="../app/styles.css">` ao `<head>` do teste.**
      Hoje o teste não carrega CSS nenhum, e por isso a asserção "os 3 botões têm a mesma
      `offsetHeight`" passa trivialmente: sem estilo, os três têm a mesma altura intrínseca de
      qualquer jeito. É a asserção que guarda o requisito de peso visual igual do brief, e
      hoje ela não guarda nada. Com o CSS carregado, ela passa a valer — os três precisam
      medir 76px.

- [ ] Com `html, body { overflow: hidden; height: 100% }`, o `<pre id="saida">` pode ficar
      fora da área visível. Não é problema para `--dump-dom`, que lê o DOM e não o pintado —
      mas dê ao `#saida` `position: relative; z-index: 99; background: #fff` para continuar
      inspecionável a olho se alguém abrir no navegador.

- [ ] Acrescente duas asserções novas:
      - o `#conteudo` é o elemento rolável: `getComputedStyle(conteudo).overflowY === 'auto'`;
      - a tela de Alerta traz um `a[href^="tel:"]` (o telefone da Defesa Civil virou link).

- [ ] Nenhuma asserção existente pode regredir.

---

## Verificação

O `python3 -m http.server 8000` do plano anterior **não sobe nesta máquina** — a porta 8000
está ocupada por outro serviço, que responde `{"detail":"Not Found"}`. Use 8791:

```sh
cd /home/jose-garcia/Projetos/Playground/IA_VAND
python3 -m http.server 8791 &
google-chrome --headless=new --no-sandbox --dump-dom --virtual-time-budget=10000 \
  http://localhost:8791/tests/app_smoke.html
```

- [ ] A saída **não** contém `FALHA`, e o total de asserções é maior que as 70 de hoje.
- [ ] Capture as três abas a 390×844 e **olhe as imagens**, uma a uma:

```sh
for r in alerta registro estudar; do
  google-chrome --headless=new --no-sandbox --hide-scrollbars --window-size=390,844 \
    --screenshot=/tmp/vand-$r.png --virtual-time-budget=6000 \
    "http://localhost:8791/app/index.html#/$r"
done
```

  Confira em cada uma: o cabeçalho não cobre o conteúdo; a barra de abas está colada no
  rodapé sem cortar ícone; o chip de Severidade está **dentro** do card; o botão de recarregar
  mostra uma seta circular e não um disco preto; e o município lê "Porto Alegre, RS" e não
  "Porto Alegre - RS, RS".

- [ ] Capture também a 1280×900 e confirme a moldura centralizada, com o fundo neutro em volta
      e as bordas arredondadas recortando o conteúdo.
- [ ] Confirme que só o `#conteudo` rola: com a página rolada até o fim, o cabeçalho e a barra
      de abas continuam nos mesmos pixels.
- [ ] `grep -rn "user-scalable\|maximum-scale" app/` não retorna nada.
- [ ] `grep -rn "fonts.googleapis\|cdn.tailwindcss\|https://" app/ --include=*.html --include=*.css --include=*.js` não retorna nada.
- [ ] Mate o servidor no fim (`pkill -f "http.server 8791"`).

## Fora de escopo

Não implemente: gesto de arrastar para trocar de aba, transição animada entre telas, pull-to-refresh,
mapa, notificação real, geolocalização, persistência de Registro. Nada disso está neste plano.
