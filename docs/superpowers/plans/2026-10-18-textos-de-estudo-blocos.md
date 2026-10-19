# Textos de estudo em blocos Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Trocar o texto corrido das 18 Seções do módulo educacional por blocos curtos e variados (lista, passos, comparação, "Pare e pense"), sem travessões e sem mudar nenhum fato.

**Architecture:** `montarSecao` em `app/app.js` ganha o tipo de Seção `blocos`, cujos blocos saem de um mapa `BLOCOS`; os quatro tipos antigos seguem funcionando, então cada Tema migra num commit verde próprio. O conteúdo novo mora em `app/content.js`; as regras de forma (45 palavras, sem travessão, 2+ tipos de bloco) viram asserções no smoke test.

**Tech Stack:** JavaScript sem build (`app/app.js`, `app/content.js`, `app/styles.css`), HTML de teste headless (`tests/*.html`), Node só para o gerador do arquivo de revisão.

**Spec:** `docs/superpowers/specs/2026-10-18-textos-de-estudo-blocos-design.md`

## Global Constraints

- Nunca ler, exibir ou modificar arquivos `.env` (regra global do usuário).
- **Fatos intactos:** nenhum fato, número, nome próprio, data ou ressalva novo, nenhuma ressalva removida; cada frase nova rastreável a uma antiga. Só reordenar, dividir, cortar repetição e trocar pontuação.
- **Sem travessões:** nem `—` nem `–` em texto visível. Hífen de palavra composta fica. O texto original do INMET (`.aviso-card`) é isento.
- Um `p` tem no máximo **45 palavras** (meta real: 20 a 35). Cada Seção `blocos` usa pelo menos **2 tipos** de bloco.
- ADR 0003: nenhum componente usa amarelo, laranja ou vermelho; paleta neutra/verde do app. Sem CDN, sem fonte externa; o app abre em `file://`.
- Todo texto entra por `textContent` (via `el()`), nunca por HTML.
- Comentários e textos em português; nomes de código em português, como no resto do repo.
- Comandos de teste desta máquina (não usar `python` direto; `./run.sh`):
  - suíte Python: `./run.sh -m pytest tests -q` (baseline: 89 passed)
  - smoke: `google-chrome --headless=new --no-sandbox --disable-gpu --virtual-time-budget=20000 --dump-dom "file://$PWD/tests/app_smoke.html" | grep "^FALHA"` (baseline: 0 falhas, 154 PASS)
  - largura: veja o cabeçalho de `tests/app_largura.html` (baseline: 0 falhas, 185 medições, 37 rotas x 5 larguras; as rotas não mudam, então o número fica igual)
- `app/sw.js`: **incrementar `VERSAO` a cada commit que mexe em `app.js`, `styles.css` ou `content.js`** (hoje `IA_VAND-v13`). Esquecer isso já custou caro: o celular continua com o arquivo antigo.
- Commits com o trailer `Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>`. **Pedir confirmação ao usuário antes de qualquer `git push`.**
- A revisão científica é do usuário: nenhuma Seção é dada como revisada sem o OK dele sobre `reports/revisao_textos_estudo_2026_10_18.md`.

## Review Focus

Entradas que a spec não nomeia e que mais provavelmente quebram, com o teste que as fixa:

1. **Bloco desconhecido ou com campo faltando** não pode derrubar a Seção inteira (Task 2: bloco `{ tipo: 'inexistente' }` na fixture; `destaque` sem `titulo`).
2. **Rótulo longo em `passos`** ("Alerta", "Minuto 0") não pode quebrar o conector nem estourar a largura a 320 px (Task 2: fixture com rótulo longo; `tests/app_largura.html` nas rotas reais).
3. **`<details>` do "Pare e pense"** tem de abrir ao toque e começar fechado; o `summary` precisa de alvo de pelo menos 44 px (Task 2).
4. **Travessão escondido em tela que só aparece com dado** (card de lacuna, Registro com aviso): o teste de texto visível simula `aviso` presente (Task 1).
5. **Texto antigo e novo divergindo em fato** sem ninguém ver: o arquivo de revisão lado a lado (Tasks 3 a 5) e a regra de rastreabilidade; não há teste automático para isso, é revisão humana.

## Desvio consciente da spec

A spec diz que as citações de Fonte "ficam idênticas" e também que não há travessões. Entram em conflito nos campos `obra`, `orgao` e `detalhe` de `fontes`, que usam " — " como separador. **Prevalece a regra dos travessões, só na pontuação**: o separador vira `:` ou parênteses, e nenhuma palavra da citação muda. Registrar na Task 6.

---

### Task 1: Travessões da interface e o verificador de texto visível

**Files:**
- Modify: `app/app.js` (7 textos de interface)
- Modify: `tests/app_smoke.html` (verificador de travessões + função `checarTemaMigrado`)

**Interfaces:**
- Produces (em `tests/app_smoke.html`, usadas pelas Tasks 3 a 5): `function checarTemaMigrado(id)` que afirma, para o Tema `id`: (a) `JSON.stringify(tema)` sem `—` nem `–`; (b) toda Seção é `tipo: 'blocos'`, com 2+ tipos de bloco distintos e todo `p` com no máximo 45 palavras; (c) o texto visível das rotas do Tema (índice, `s/N`, `pensar`, `fontes`, `quiz`) sem `—`/`–`. E `function textoVisivel()` que devolve o texto de `#topbar` + `#tela` sem o conteúdo de `.aviso-card`.

- [ ] **Step 1: Escrever o verificador no smoke (vai falhar)**

Em `tests/app_smoke.html`, logo antes de `function percorre(tema) {`, inserir:

```js
// --- regras de forma dos textos de estudo (spec 2026-10-18) ---
var TRAVESSAO = /[—–]/;

// Texto que o usuário lê, sem o aviso do INMET (texto original, sem edição).
function textoVisivel() {
  var tela = document.getElementById('tela').cloneNode(true);
  [].forEach.call(tela.querySelectorAll('.aviso-card'), function (n) { n.parentNode.removeChild(n); });
  return document.getElementById('topbar').textContent + ' ' + tela.textContent;
}

function checarTemaMigrado(id) {
  var tema = window.VAND_CONTENT.trilha.filter(function (t) { return t.id === id; })[0];
  var nome = '[forma ' + id + '] ';
  ok(!TRAVESSAO.test(JSON.stringify(tema)), nome + 'conteúdo sem travessão');
  var base = '#/estudar/' + id;
  var rotas = [base];
  tema.secoes.forEach(function (s, i) {
    ok(s.tipo === 'blocos', nome + 'Seção ' + (i + 1) + ' é do tipo blocos');
    var tipos = {};
    (s.blocos || []).forEach(function (b) {
      tipos[b.tipo] = true;
      if (b.tipo === 'p') {
        var n = b.texto.trim().split(/\s+/).length;
        ok(n <= 45, nome + 'Seção ' + (i + 1) + ': parágrafo de ' + n + ' palavras (máx. 45)');
      }
    });
    ok(Object.keys(tipos).length >= 2, nome + 'Seção ' + (i + 1) + ' mistura ao menos 2 tipos de bloco');
    rotas.push(base + '/s/' + (i + 1));
  });
  rotas.push(base + '/pensar', base + '/fontes', base + '/quiz');
  rotas.forEach(function (rota) {
    irPara(rota);
    ok(!TRAVESSAO.test(textoVisivel()), nome + 'texto visível sem travessão em ' + rota);
  });
}
```

E, dentro do `try {`, logo antes do comentário `// A logo (sem o ponto vermelho, ADR 0003) mora no cabeçalho fixo de TODA tela.`, inserir:

```js
  // Texto de interface sem travessão. As telas que só mostram certas frases com dado
  // presente (card de lacuna, Registro com aviso) são exercitadas com o exemplo.
  var avisoOriginal = window.VAND_DADOS.aviso;
  window.VAND_DADOS.aviso = window.VAND_DADOS.aviso_exemplo;
  ['#/alerta', '#/alerta/calmo', '#/alerta/exemplo', '#/registro', '#/registro/enviado',
   '#/estudar', '#/estudar/sobre'].forEach(function (rota) {
    irPara(rota);
    ok(!TRAVESSAO.test(textoVisivel()), 'interface sem travessão em ' + rota);
  });
  window.VAND_DADOS.aviso = avisoOriginal;
```

- [ ] **Step 2: Rodar o smoke e ver falhar**

Run: o comando do smoke acima.
Expected: FALHAs `interface sem travessão em ...` para as rotas cujas frases têm `—` (no mínimo `#/alerta/calmo`, `#/alerta/exemplo`, `#/registro` e `#/estudar`). Anote quais rotas falharam: se alguma frase da lista do Step 3 não for exercitada por nenhuma rota, o teste não a cobre e o plano precisa de uma rota a mais.

- [ ] **Step 3: Trocar os 7 textos em `app/app.js`**

Edições exatas (texto antigo → novo):

1. `'Seções lidas. Dá para parar e voltar depois — o app lembra.'` → `'Seções lidas. Dá para parar e voltar depois: o app lembra.'`
2. `'Refazer é livre — nada aqui trava o próximo tema.'` → `'Refazer é livre. Nada aqui trava o próximo tema.'`
3. `'EXEMPLO HISTÓRICO — NÃO É O AVISO DE HOJE'` → `'EXEMPLO HISTÓRICO: NÃO É O AVISO DE HOJE'`
4. `Isto não é previsão de tempo bom — é a ausência de aviso naquela consulta, e um Aviso pode ter sido emitido depois dela.` → `Isto não é previsão de tempo bom: é a ausência de aviso naquela consulta, e um Aviso pode ter sido emitido depois dela.`
5. `'avisado — uma razão de '` → `'avisado: uma razão de '`
6. `(dados.aviso.descricao || 'Acumulado de Chuva') + ' — ' + (dados.aviso.severidade || 'Grande Perigo')` → `(dados.aviso.descricao || 'Acumulado de Chuva') + ' · ' + (dados.aviso.severidade || 'Grande Perigo')`
7. `Pela definição oficial (COBRADE 1.2.3.0.0) ele é extrapolação da capacidade do sistema de drenagem — não há uma palavra sobre atmosfera.` → `Pela definição oficial (COBRADE 1.2.3.0.0), ele é extrapolação da capacidade do sistema de drenagem: não há uma palavra sobre atmosfera.`

Depois conferir: `grep -n "—" app/app.js | grep -v "^\s*[0-9]*:\s*\(//\|/\*\|\*\)"` não deve imprimir nada (sobram só comentários).

- [ ] **Step 4: Rodar e ver passar**

Run: smoke. Expected: 0 FALHA (as asserções de forma de Tema ainda não foram chamadas). Suíte Python: `89 passed`.

- [ ] **Step 5: Commit**

```bash
git add app/app.js tests/app_smoke.html
git commit -m "$(cat <<'EOF'
fix(app): tira os travessões dos textos de interface

Também ganha, no smoke, o verificador de texto visível sem travessão e a função
checarTemaMigrado, que as próximas etapas usam para cada Tema.

Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>
EOF
)"
```

(`sw.js` sobe de versão só na Task 2, que mexe no CSS; esta etapa não será publicada sozinha, ou, se for, suba `VERSAO` para `IA_VAND-v14` antes do push.)

---

### Task 2: O tipo `blocos` e os componentes

**Files:**
- Modify: `app/app.js` (`montarSecao`, novo mapa `BLOCOS`)
- Modify: `app/styles.css` (estilos dos blocos)
- Modify: `app/sw.js` (`VERSAO` v14)
- Modify: `tests/app_smoke.html` (fixture e asserções de renderização)
- Modify: `CONTEXT.md` (verbete **Bloco**)

**Interfaces:**
- Produces: tipo de Seção `{ tipo: 'blocos', titulo, blocos: [...] }` e os blocos `p {texto}`, `lista {itens, ordenada?}`, `passos {itens: [{rotulo, titulo?, texto}]}`, `comparacao {lados: [{titulo, itens}, {titulo, itens}]}`, `pergunta {pergunta, resposta}`, `numeros {itens: [{valor, rotulo, largo?}], nota?}`, `destaque {titulo?, texto}`, `glossario {termos: [{palavra, definicao}], nota?}`. Classes de saída: `.bloco-p`, `.bloco-lista`, `.bloco-passos`, `.bloco-comparacao` (`.comp-lado`, `.comp-x`), `details.bloco-pergunta`, `.bloco-numeros`, `.bloco-glossario`.

- [ ] **Step 1: Escrever a fixture e as asserções (vão falhar)**

Em `tests/app_smoke.html`, dentro do `try {`, logo antes do comentário `// Texto de interface sem travessão.` (inserido na Task 1), inserir:

```js
  // --- blocos de Seção: renderização, com um Tema de fixture ---
  var temaFixture = {
    id: 'fixture-blocos', titulo: 'Fixture', nivel: 'Básico', minutos: 1, resumo: 'x',
    secoes: [{
      tipo: 'blocos', titulo: 'Seção de teste',
      blocos: [
        { tipo: 'p', texto: 'Um parágrafo curto.' },
        { tipo: 'lista', itens: ['um', 'dois', 'três'] },
        { tipo: 'lista', ordenada: true, itens: ['a', 'b'] },
        { tipo: 'passos', itens: [
          { rotulo: '1', titulo: 'Primeiro', texto: 'Texto do primeiro.' },
          { rotulo: 'Minuto zero', texto: 'Rótulo longo, sem título.' } ] },
        { tipo: 'comparacao', lados: [
          { titulo: 'Lado A', itens: ['a1', 'a2'] }, { titulo: 'Lado B', itens: ['b1'] } ] },
        { tipo: 'pergunta', pergunta: 'Por quê?', resposta: 'Porque sim.' },
        { tipo: 'numeros', itens: [{ valor: '97%', rotulo: 'salgada' }, { rotulo: 'largo', largo: true }], nota: 'Nota.' },
        { tipo: 'destaque', texto: 'Destaque sem título.' },
        { tipo: 'destaque', titulo: 'Com título', texto: 'Destaque com título.' },
        { tipo: 'glossario', termos: [{ palavra: 'Termo', definicao: 'Definição.' }], nota: 'Nota do glossário.' },
        { tipo: 'inexistente', texto: 'bloco que o app não conhece' },
        { tipo: 'p', texto: 'Último parágrafo, depois do bloco desconhecido.' }
      ]
    }],
    reflexoes: [], quiz: [{ pergunta: 'q', alternativas: ['a', 'b', 'c', 'd'], correta: 0, explicacao: 'e' }], fontes: []
  };
  window.VAND_CONTENT.trilha.push(temaFixture);
  irPara('#/estudar/fixture-blocos/s/1');
  var secFx = document.querySelector('#tela .secao');
  ok(!!secFx, 'blocos: a Seção renderiza');
  ok(secFx.querySelectorAll('.bloco-p').length === 2, 'blocos: p renderiza (e segue depois do bloco desconhecido)');
  ok(secFx.querySelector('ul.bloco-lista') && secFx.querySelectorAll('ul.bloco-lista li').length === 3, 'blocos: lista com 3 itens');
  ok(secFx.querySelectorAll('ol.bloco-lista li').length === 2, 'blocos: lista ordenada usa <ol>');
  ok(secFx.querySelectorAll('ol.bloco-passos > li').length === 2, 'blocos: passos renderiza 2 passos');
  ok(secFx.querySelector('.bloco-passos .passo-marca').textContent === '1', 'blocos: rótulo curto vai no círculo do passo');
  ok(secFx.textContent.indexOf('Minuto zero') > -1 && secFx.querySelectorAll('.passo-marca.ponto').length === 1,
     'blocos: rótulo longo vira texto com marcador de ponto');
  ok(secFx.querySelectorAll('.bloco-comparacao .comp-lado').length === 2 && !!secFx.querySelector('.comp-x'),
     'blocos: comparacao tem 2 lados e o separador');
  var detFx = secFx.querySelector('details.bloco-pergunta');
  ok(!!detFx && detFx.open === false, 'blocos: pergunta começa fechada');
  ok(detFx.querySelector('summary').offsetHeight >= 44, 'blocos: o summary da pergunta tem alvo de toque de 44px');
  detFx.querySelector('summary').click();
  ok(detFx.open === true, 'blocos: tocar no summary abre a resposta');
  ok(secFx.querySelectorAll('.bloco-numeros .dado').length === 2 && secFx.querySelector('.bloco-numeros .nota'),
     'blocos: numeros renderiza os itens e a nota');
  ok(secFx.querySelectorAll('.destaque').length === 2 && secFx.querySelectorAll('.destaque h3').length === 1,
     'blocos: destaque aceita ter ou não ter título');
  ok(secFx.querySelectorAll('.bloco-glossario .termo').length === 1 && secFx.querySelector('.bloco-glossario .nota'),
     'blocos: glossario renderiza termo e nota');
  ok(secFx.textContent.indexOf('bloco que o app não conhece') === -1, 'blocos: bloco desconhecido é ignorado, sem derrubar a Seção');
  window.VAND_CONTENT.trilha.pop();
```

- [ ] **Step 2: Rodar o smoke e ver falhar**

Run: smoke. Expected: FALHAs nas asserções `blocos: ...` (a Seção `blocos` ainda devolve `null` em `montarSecao`, então `.secao` não existe: `blocos: a Seção renderiza` falha e o resto lança exceção). Não deve haver outra falha nova.

- [ ] **Step 3: Implementar `BLOCOS` e o ramo `blocos` em `app/app.js`**

Em `app/app.js`, substituir a função `montarSecao` inteira (de `// Monta UMA Seção.` até o `}` que a fecha, antes de `function renderTrilha()`) por:

```js
  // Blocos de uma Seção do tipo `blocos` (spec 2026-10-18). Cada um devolve UM nó;
  // todo texto entra por textContent, nunca como HTML. O mapa também serve aos
  // tipos antigos `dados` e `glossario`, que são "título + um bloco".
  var BLOCOS = {
    p: function (b) { return el('p', { class: 'bloco-p', text: b.texto }); },
    lista: function (b) {
      return el(b.ordenada ? 'ol' : 'ul', { class: 'bloco-lista' },
        (b.itens || []).map(function (t) { return el('li', { text: t }); }));
    },
    passos: function (b) {
      return el('ol', { class: 'bloco-passos' }, (b.itens || []).map(function (it) {
        // Rótulo curto ("1", "2") vai dentro do círculo; rótulo longo ("Alerta",
        // "Minuto zero") não cabe nele e vira texto acima do corpo, com um ponto.
        var curto = String(it.rotulo).length <= 3;
        return el('li', {}, [
          el('span', { class: curto ? 'passo-marca' : 'passo-marca ponto', text: curto ? String(it.rotulo) : '' }),
          el('div', { class: 'passo-corpo' }, [
            curto ? null : el('span', { class: 'passo-rotulo-longo', text: String(it.rotulo) }),
            it.titulo ? el('strong', { text: it.titulo }) : null,
            el('p', { text: it.texto })
          ])
        ]);
      }));
    },
    comparacao: function (b) {
      var lados = (b.lados || []).map(function (l) {
        return el('div', { class: 'comp-lado' }, [
          el('h3', { text: l.titulo }),
          el('ul', {}, (l.itens || []).map(function (t) { return el('li', { text: t }); }))
        ]);
      });
      if (lados.length === 2) lados.splice(1, 0, el('span', { class: 'comp-x', 'aria-hidden': 'true', text: '×' }));
      return el('div', { class: 'bloco-comparacao' }, lados);
    },
    // "Pare e pense": <details> nativo, acessível e sem JavaScript. Não grava
    // progresso e não é a Reflexão (essa continua em `tema.reflexoes`).
    pergunta: function (b) {
      return el('details', { class: 'bloco-pergunta' }, [
        el('summary', {}, [
          el('span', { class: 'pergunta-rotulo t-caps', text: 'Pare e pense' }),
          el('span', { class: 'pergunta-texto', text: b.pergunta }),
          el('span', { class: 'pergunta-ver', text: 'Ver a resposta' })
        ]),
        el('p', { class: 'pergunta-resposta', text: b.resposta })
      ]);
    },
    numeros: function (b) {
      var grid = el('div', { class: 'dados' });
      (b.itens || []).forEach(function (d) {
        var cls = 'dado' + (d.largo ? ' largo' : '');
        var filhos = d.valor
          ? [el('span', { class: 'valor', text: d.valor }), el('span', { class: 'rotulo', text: d.rotulo })]
          : [el('span', { class: 'rotulo', text: d.rotulo })];
        grid.appendChild(el('div', { class: cls }, filhos));
      });
      return el('div', { class: 'bloco-numeros' }, [grid, b.nota ? el('p', { class: 'nota', text: b.nota }) : null]);
    },
    destaque: function (b) {
      return el('div', { class: 'destaque' }, [
        b.titulo ? el('h3', { text: b.titulo }) : null,
        el('p', { text: b.texto })
      ]);
    },
    glossario: function (b) {
      var lista = el('div', { class: 'glossario' });
      (b.termos || []).forEach(function (t) {
        lista.appendChild(el('div', { class: 'termo' }, [
          el('span', { class: 'palavra', text: t.palavra }),
          el('p', { text: t.definicao })
        ]));
      });
      return el('div', { class: 'bloco-glossario' }, [lista, b.nota ? el('p', { class: 'nota', text: b.nota }) : null]);
    }
  };

  // Monta UMA Seção. O `h2` do título é sempre o primeiro filho: renderSecao o
  // remove na tela de Seção, onde o título já é o grande da tela.
  function montarSecao(s) {
    if (s.tipo === 'blocos') {
      var sb = el('section', { class: 'secao' }, [el('h2', { text: s.titulo })]);
      (s.blocos || []).forEach(function (b) {
        var fazer = BLOCOS[b.tipo];
        var no = fazer ? fazer(b) : null;   // tipo desconhecido: ignora, não derruba a Seção
        if (no) sb.appendChild(no);
      });
      return sb;
    }
    if (s.tipo === 'texto') {
      var bloco = el('section', { class: 'secao' }, [el('h2', { text: s.titulo })]);
      s.paragrafos.forEach(function (par) { bloco.appendChild(el('p', { text: par })); });
      return bloco;
    }
    if (s.tipo === 'destaque') {
      return el('section', { class: 'secao destaque' }, [
        el('h2', { text: s.titulo }),
        el('p', { text: s.texto })
      ]);
    }
    if (s.tipo === 'glossario') {
      return el('section', { class: 'secao' }, [el('h2', { text: s.titulo }), BLOCOS.glossario(s)]);
    }
    if (s.tipo === 'dados') {
      return el('section', { class: 'secao' }, [el('h2', { text: s.titulo }), BLOCOS.numeros(s)]);
    }
    return null;
  }
```

- [ ] **Step 4: Estilos em `app/styles.css`**

Logo depois da regra `.termo p { margin: 0; font-size: .94rem; }`, inserir:

```css
/* ---------- blocos de Seção (spec 2026-10-18) ---------- */
/* Paleta do app (verde/neutro). ADR 0003: nenhum destes usa a cor de severidade. */
.secao .bloco-p { margin: 0 0 12px; }

.bloco-lista { margin: 0 0 14px; padding: 0; list-style: none; display: grid; gap: 10px; }
.bloco-lista li { position: relative; padding-left: 26px; }
ul.bloco-lista li::before {
  content: ""; position: absolute; left: 6px; top: .62em;
  width: 8px; height: 8px; border-radius: 50%; background: var(--accent);
}
ol.bloco-lista { counter-reset: item; }
ol.bloco-lista li { counter-increment: item; }
ol.bloco-lista li::before {
  content: counter(item); position: absolute; left: 0; top: .12em;
  width: 20px; height: 20px; border-radius: 50%;
  background: var(--accent-soft); color: var(--accent-forte);
  font-size: .75rem; font-weight: 720; display: grid; place-items: center;
}

/* Passos: coluna de 34px com o marcador, linha fina ligando um ao próximo. */
.bloco-passos { margin: 0 0 16px; padding: 0; list-style: none; }
.bloco-passos > li {
  position: relative; display: grid; grid-template-columns: 34px minmax(0, 1fr);
  column-gap: 12px; padding-bottom: 14px;
}
.bloco-passos > li:last-child { padding-bottom: 0; }
.bloco-passos > li::before {  /* a linha passa por trás do marcador (z-index) */
  content: ""; position: absolute; left: 16px; top: 17px; bottom: -17px;
  width: 2px; background: var(--border-forte);
}
.bloco-passos > li:last-child::before { display: none; }
.passo-marca {
  position: relative; z-index: 1; width: 34px; height: 34px; border-radius: 50%;
  background: var(--accent); color: var(--accent-text);
  display: grid; place-items: center; font-weight: 720; font-size: .9rem;
}
.passo-marca.ponto { width: 14px; height: 14px; margin: 10px 10px 0; }
.passo-corpo { min-width: 0; padding-top: 5px; }
.passo-corpo strong { display: block; margin-bottom: 2px; }
.passo-corpo p { margin: 0; }
.passo-rotulo-longo {
  display: block; font-size: .72rem; font-weight: 720; letter-spacing: .06em;
  text-transform: uppercase; color: var(--text-dim); margin-bottom: 2px;
}

/* Comparação: empilhada no celular, lado a lado a partir de 520px. */
.bloco-comparacao { display: grid; gap: 8px; margin: 0 0 16px; }
.comp-lado {
  background: var(--surface); border: 1px solid var(--border);
  border-radius: var(--radius); padding: 14px 16px; box-shadow: var(--sombra-1);
}
.comp-lado h3 {
  margin: 0 0 8px; font-size: .82rem; letter-spacing: .05em;
  text-transform: uppercase; color: var(--accent-forte);
}
.comp-lado ul { margin: 0; padding: 0; list-style: none; display: grid; gap: 6px; font-size: .95rem; }
.comp-lado li { position: relative; padding-left: 16px; }
.comp-lado li::before {
  content: ""; position: absolute; left: 0; top: .62em;
  width: 6px; height: 6px; border-radius: 50%; background: var(--accent-2);
}
.comp-x { justify-self: center; font-weight: 720; line-height: 1; color: var(--text-dim); }
@media (min-width: 520px) {
  .bloco-comparacao { grid-template-columns: minmax(0, 1fr) auto minmax(0, 1fr); align-items: stretch; }
  .comp-x { align-self: center; }
}

/* "Pare e pense": a resposta fica atrás do toque. Nada anima, então nada a
   desligar sob prefers-reduced-motion. */
.bloco-pergunta {
  margin: 0 0 16px; background: var(--accent-soft);
  border: 1px solid var(--border); border-radius: var(--radius);
}
.bloco-pergunta summary {
  list-style: none; cursor: pointer; display: grid; gap: 6px;
  padding: 14px 16px; min-height: 44px; border-radius: var(--radius);
}
.bloco-pergunta summary::-webkit-details-marker { display: none; }
.bloco-pergunta summary:focus-visible { outline: 2px solid var(--accent); outline-offset: 2px; }
.pergunta-rotulo { color: var(--accent-forte); }
.pergunta-texto { font-weight: 660; }
.pergunta-ver { color: var(--accent-forte); font-weight: 660; font-size: .9rem; }
.bloco-pergunta[open] .pergunta-ver { display: none; }
.pergunta-resposta { margin: 0; padding: 0 16px 16px; }

/* Destaque e números como bloco dentro de uma Seção. */
.secao .destaque { margin: 0 0 16px; }
.destaque h3 { font-size: 1.02rem; margin: 0 0 8px; color: var(--accent-forte); }
.bloco-numeros, .bloco-glossario { margin: 0 0 14px; }
```

- [ ] **Step 5: Subir o service worker**

Em `app/sw.js`: `var VERSAO = 'IA_VAND-v13';` → `var VERSAO = 'IA_VAND-v14';`.

- [ ] **Step 6: Verbete no `CONTEXT.md`**

Abrir `CONTEXT.md`, localizar o verbete **Seção** (logo antes de **Item**) e acrescentar, depois dele, no mesmo formato dos vizinhos:

```markdown
**Bloco**:
Uma peça de uma Seção do tipo `blocos`: parágrafo curto, lista, passos, comparação,
"Pare e pense", números, destaque ou glossário. Uma Seção é um título mais uma
sequência de Blocos. O "Pare e pense" é um Bloco e não é uma Reflexão: não vai
para a tela de Para pensar e não guarda progresso.
_Evitar_: card, componente, widget.
```

- [ ] **Step 7: Rodar tudo e ver passar**

Run: smoke (esperado: 0 FALHA, incluindo as 15 asserções `blocos: ...`), largura (esperado: 0 falhas, `FIM: 185 medições`), `./run.sh -m pytest tests -q` (esperado: 89 passed). Se `detFx.open` não virar `true` após `summary.click()` no headless, trocar o clique por `detFx.open = true` no teste e registrar a troca num `Ruling` no ledger, sem mexer no app.

- [ ] **Step 8: Commit**

```bash
git add app/app.js app/styles.css app/sw.js tests/app_smoke.html CONTEXT.md
git commit -m "$(cat <<'EOF'
feat(app): blocos de Seção (lista, passos, comparação, Pare e pense)

Novo tipo de Seção `blocos`; os tipos antigos seguem funcionando, então cada
Tema migra por conta própria. sw.js v14.

Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 3: Tema 3 (Clima em mudança e risco na cidade) e o arquivo de revisão

**Files:**
- Modify: `app/content.js` (`secoes` do Tema 3, e os travessões de `quiz`, `fontes` do Tema 3)
- Modify: `app/sw.js` (v15)
- Modify: `tests/app_smoke.html` (chamar `checarTemaMigrado`)
- Create: `scripts/gerar_revisao_textos.js`
- Create: `reports/revisao_textos_estudo_2026_10_18.md` (gerado)
- Create (fora do repo): `$SCRATCH/aplicar_secoes.py`

**Interfaces:**
- Consumes: tipo `blocos` e os blocos da Task 2; `checarTemaMigrado(id)` da Task 1.
- Produces: `scripts/gerar_revisao_textos.js <ref-git-antigo> <id-do-tema>...` que reescreve `reports/revisao_textos_estudo_2026_10_18.md` com o antes e o depois de cada Tema pedido (a Task 4 e a 5 o chamam de novo, cumulativamente, com o mesmo `<ref>`).

- [ ] **Step 1: Chamar a verificação do Tema 3 no smoke (vai falhar)**

Em `tests/app_smoke.html`, logo depois do bloco `window.VAND_CONTENT.trilha.pop();` da Task 2, inserir:

```js
  checarTemaMigrado('clima-em-mudanca-e-risco-na-cidade');
```

Run: smoke. Expected: FALHAs `[forma clima-em-mudanca-e-risco-na-cidade] Seção N é do tipo blocos` (7), `conteúdo sem travessão`, e os de `texto visível sem travessão`.

- [ ] **Step 2: Escrever o aplicador de Seções (fora do repo)**

Criar `$SCRATCH/aplicar_secoes.py` (SCRATCH = pasta de rascunho da sessão; **não** vai para o git). Ele lê o bloco ```` ```js secoes-tema-N ```` deste plano e o coloca no lugar do `secoes: [ ... ]` do N-ésimo Tema de `app/content.js`:

```python
import re, sys
plano, n = sys.argv[1], int(sys.argv[2])          # n = 1, 2 ou 3 (ordem em content.js)
texto = open(plano, encoding='utf-8').read()
novo = re.search(r'```js secoes-tema-%d\n(.*?)\n```' % n, texto, re.S).group(1)
conteudo = open('app/content.js', encoding='utf-8').read()
abre = [m.end() for m in re.finditer(r'^      secoes: \[\n', conteudo, re.M)][n - 1]
fecha = conteudo.index('      ],\n      reflexoes: [', abre)
open('app/content.js', 'w', encoding='utf-8').write(conteudo[:abre] + novo + '\n' + conteudo[fecha:])
print('Tema', n, 'aplicado:', len(novo), 'caracteres')
```

- [ ] **Step 3: O conteúdo novo do Tema 3**

Este bloco é o texto **exato** que o aplicador cola no lugar das 7 Seções do Tema 3:

```js secoes-tema-3
        {
          tipo: 'blocos',
          titulo: 'O mesmo volume, estragos diferentes',
          blocos: [
            { tipo: 'p', texto: 'O Tema anterior terminou numa constatação: a chuva é igual, o que o chão faz com ela não é.' },
            { tipo: 'p', texto: 'Este Tema pega esse fio e puxa até o fim, porque a diferença entre duas ruas se repete entre dois bairros, entre duas cidades e entre dois países.' },
            { tipo: 'destaque', titulo: 'Já em 2006', texto: 'O livro oficial do Ensino Médio do ENCCEJA diz, já em 2006, que responsabilizar só a chuva pelas enchentes é simplificar demais o problema. É uma frase escrita pelo MEC quase vinte anos antes desta tela.' },
            { tipo: 'p', texto: 'Ela vale como resumo de tudo o que vem a seguir: desastre não é sinônimo de fenômeno natural.' },
            { tipo: 'comparacao', lados: [
              { titulo: 'Fenômeno', itens: ['É a ameaça.'] },
              { titulo: 'Desastre', itens: ['É o que acontece quando a ameaça encontra uma população exposta e sem meios de se proteger.'] }
            ] },
            { tipo: 'p', texto: 'Daí a conta que a defesa civil usa: o risco nasce do encontro entre a ameaça e a vulnerabilidade.' },
            { tipo: 'lista', itens: [
              'Sobre a ameaça, ninguém decide: não se cancela uma frente fria.',
              'Sobre a vulnerabilidade, decide-se o tempo todo: onde se deixa construir, quanto se gasta em drenagem, quem é avisado e com quanta antecedência.'
            ] },
            { tipo: 'p', texto: 'Por isso um desastre pode ser previsto e, em boa medida, evitado, mesmo que a chuva não possa.' }
          ]
        },
        {
          tipo: 'blocos',
          titulo: 'O que está mudando, e o que isso faz com a chuva',
          blocos: [
            { tipo: 'p', texto: 'O efeito estufa não é um defeito: sem os gases que seguram parte do calor na atmosfera, a Terra seria fria demais para a vida como a conhecemos.' },
            { tipo: 'p', texto: 'O problema é a intensidade. Ao acrescentar gás carbônico, metano e óxido nitroso em quantidade, a humanidade tornou esse cobertor mais espesso, e o planeta reteve mais calor do que devolveu.' },
            { tipo: 'p', texto: 'Cientistas chamam o resultado de novo regime climático, uma expressão que diz mais do que "está mais quente".' },
            { tipo: 'p', texto: 'Ela diz que a régua mudou: os eventos extremos passam a acontecer em maior quantidade, em mais lugares e com mais frequência do que a experiência acumulada de quem vive ali levaria a esperar.' },
            { tipo: 'p', texto: 'Entre as consequências listadas pelo material oficial, três interessam diretamente a quem mora em cidade:' },
            { tipo: 'lista', itens: [
              'Ondas de calor e de frio mais intensas.',
              'Secas mais severas.',
              'Tempestades e enchentes mais drásticas.'
            ] },
            { tipo: 'p', texto: 'Repare que seca e enchente aparecem juntas. Não é contradição: é o mesmo ciclo da água ficando mais irregular nas duas pontas.' },
            { tipo: 'destaque', titulo: 'Para a nossa história', texto: 'O ponto é este: a chuva que a cidade foi construída para aguentar é a chuva de um clima que está deixando de existir. A drenagem projetada com a estatística de trinta anos atrás encontra hoje uma estatística diferente.' }
          ]
        },
        {
          tipo: 'blocos',
          titulo: 'A lei que não tira a água, tira a pressa',
          blocos: [
            { tipo: 'numeros', itens: [
              { valor: '2002', rotulo: 'a Lei nº 13.276 de São Paulo, apelidada de "Lei das Piscininhas"' },
              { valor: '1 hora', rotulo: 'é quanto o reservatório precisa segurar a água depois que a chuva termina' },
              { valor: '', rotulo: 'Campina Grande, Campinas, Limeira, Ribeirão Preto, Rio de Janeiro e Curitiba estudaram leis parecidas, e em Campina Grande o alvo era o oposto: guardar água para a seca', largo: true }
            ] },
            { tipo: 'p', texto: 'Repare no que a lei faz e no que ela não faz.' },
            { tipo: 'comparacao', lados: [
              { titulo: 'O que ela não faz', itens: ['Não diminui um litro do que caiu.'] },
              { titulo: 'O que ela faz', itens: ['Obriga cada prédio a guardar a sua parte.', 'Manda soltá-la só depois que a chuva passou.'] }
            ] },
            { tipo: 'pergunta', pergunta: 'Então o que a lei devolve à cidade?', resposta: 'O atraso que o solo dava de graça antes do asfalto. É esse atraso, não o volume, que impede a rede pluvial de receber tudo no mesmo instante e transbordar.' }
          ]
        },
        {
          tipo: 'blocos',
          titulo: 'Cinza, verde, e o que a cidade escolhe',
          blocos: [
            { tipo: 'p', texto: 'Durante muito tempo a resposta a esse problema foi o que se chama de infraestrutura cinza: obras grandes, de concreto, aço e pedra, como diques, muros de arrimo, barragens, quebra-mares e canais pavimentados.' },
            { tipo: 'p', texto: 'Elas funcionam, e há situações em que não há substituto para elas.' },
            { tipo: 'p', texto: 'Mas o material oficial aponta três limites que se acumularam com o tempo:' },
            { tipo: 'lista', ordenada: true, itens: [
              'Custam caro para manter, e manutenção é a primeira coisa que some do orçamento.',
              'Degradam o ambiente, sobretudo na obra.',
              'São rígidas: foram dimensionadas para um número, e quando o evento extremo passa desse número, elas não se adaptam e falham.'
            ] },
            { tipo: 'p', texto: 'A alternativa que ganhou espaço são as soluções baseadas na natureza:' },
            { tipo: 'lista', itens: [
              'Recuperar a várzea em vez de canalizar o córrego.',
              'Ampliar área permeável.',
              'Replantar a margem.'
            ] },
            { tipo: 'p', texto: 'São mais baratas de manter, e falham devagar em vez de falhar de uma vez.' },
            { tipo: 'destaque', titulo: 'A piscininha, no meio do caminho', texto: 'A piscininha do quadro acima é interessante justamente por ficar no meio do caminho: é concreto, é obra, mas é pequena, distribuída por milhares de lotes e imita o que a terra fazia. Nenhuma das três abordagens dispensa a outra. O que existe é escolha sobre a mistura, e essa escolha é orçamento público, não meteorologia.' }
          ]
        },
        {
          tipo: 'blocos',
          titulo: 'Vulnerabilizadas, não vulneráveis',
          blocos: [
            { tipo: 'p', texto: 'O material do Cemaden Educação faz uma correção de vocabulário que muda o sentido da frase inteira: as populações mais atingidas não são vulneráveis por si sós. Elas foram vulnerabilizadas.' },
            { tipo: 'destaque', titulo: 'A diferença entre as duas palavras', texto: 'A segunda tem agente. Alguém decidiu onde passaria o asfalto, onde iria a escola, qual bairro receberia rede pluvial primeiro.' },
            { tipo: 'p', texto: 'Os efeitos do clima em mudança não se distribuem por igual. Comunidades negras, indígenas e de minorias étnicas vivem os impactos de forma desproporcional, porque estão com mais frequência em periferias, favelas, margens de rio e encostas, as áreas de risco.' },
            { tipo: 'p', texto: 'Nesses lugares o Estado costuma estar menos presente, e a mesma chuva encontra menos infraestrutura para atravessar. É a isso que se dá o nome de racismo ambiental.' },
            { tipo: 'p', texto: 'Dentro dessas comunidades, a exposição também não é uniforme. Estas pessoas são as que menos conseguem sair a tempo e as que mais demoram a se recompor depois:' },
            { tipo: 'lista', itens: [
              'Mulheres pobres.',
              'Crianças.',
              'Adolescentes.',
              'Pessoas idosas.',
              'Pessoas com deficiência.'
            ] },
            { tipo: 'p', texto: 'E há a assimetria que fecha o argumento: são justamente as pessoas que menos contribuíram para as emissões que mais sofrem as consequências delas.' },
            { tipo: 'destaque', titulo: 'Justiça climática', texto: 'É por isso que se fala em justiça climática, e não apenas em adaptação: adaptação é uma questão de engenharia, justiça é uma questão de a quem se dirige a engenharia.' }
          ]
        },
        {
          tipo: 'blocos',
          titulo: 'Resiliência: voltar, mudar ou transformar',
          blocos: [
            { tipo: 'glossario', termos: [
              { palavra: 'Voltar ao que era', definicao: 'Recuperar a vida de antes o mais rápido possível. É o sentido mais comum da palavra, e o que traz a pergunta incômoda: se o desastre aconteceu, aquela normalidade era mesmo segura, ou já era o problema?' },
              { palavra: 'Reconstruir com mudanças', definicao: 'Aproveitar a reconstrução para corrigir o que estava errado: melhorar obras, garantir direitos, reforçar leis. Ajuda de verdade, mas chega depois das perdas e trabalha sobre o que restou.' },
              { palavra: 'Transformar', definicao: 'Mudar a base: repensar como a cidade funciona, questionar as regras que produziram a exposição, discutir quem decide. É a forma mais difícil, e a única que ataca o que fez a sociedade ser vulnerável, e não apenas o desastre.' }
            ] },
            { tipo: 'p', texto: 'A distinção é do pesquisador Mark Pelling, apresentada pelo caderno do Cemaden Educação.' },
            { tipo: 'p', texto: 'Ela é útil porque quase todo debate público depois de uma enchente é, no fundo, uma disputa entre estas três ideias, e quase sempre sem que ninguém diga em qual delas está.' }
          ]
        },
        {
          tipo: 'blocos',
          titulo: 'Onde este aplicativo entra',
          blocos: [
            { tipo: 'p', texto: 'O material oficial descreve um sistema de alerta como quatro eixos ligados:' },
            { tipo: 'lista', ordenada: true, itens: [
              'Conhecimento do risco.',
              'Monitoramento.',
              'Educação e comunicação.',
              'Preparação.'
            ] },
            { tipo: 'p', texto: 'Vale reparar onde este aplicativo cai.' },
            { tipo: 'passos', itens: [
              { rotulo: 'Alerta', texto: 'É comunicação: ela não monitora nada, retransmite o aviso de quem monitora, o INMET.' },
              { rotulo: 'Estudar', texto: 'Este Tema que você está lendo é o eixo da educação.' },
              { rotulo: 'Registro', texto: 'É conhecimento do risco vindo de baixo, e há estudos mostrando que a resposta funciona melhor quando a defesa civil leva em conta o que quem mora ali já sabe.' }
            ] },
            { tipo: 'destaque', titulo: 'Nenhum eixo basta sozinho', texto: 'Nenhum dos quatro eixos é dispensável, e nenhum deles é o aplicativo sozinho: um aviso que chega não substitui uma cidade que drena, e nenhum dos dois substitui a decisão sobre quem pode morar onde.' }
          ]
        }
```

- [ ] **Step 4: Aplicar as Seções**

Run: `python3 $SCRATCH/aplicar_secoes.py docs/superpowers/plans/2026-10-18-textos-de-estudo-blocos.md 3`
Expected: `Tema 3 aplicado: ... caracteres`. Conferir `node --check app/content.js` (sem saída = sintaxe ok) e `git diff --stat app/content.js`.

- [ ] **Step 5: Travessões fora das Seções do Tema 3**

Em `app/content.js`, dentro do Tema 3, trocar (texto exato como está no arquivo; se alguma aspa ou apóstrofo diferir, ler a linha e ajustar só a pontuação):

- `T3.quiz[0].explicacao`: `A ameaça — a chuva, a frente fria — não está sob controle de ninguém.` → `A ameaça (a chuva, a frente fria) não está sob controle de ninguém.`
- `T3.quiz[2].explicacao`: `não se adapta quando o evento a supera — e o novo regime climático` → `não se adapta quando o evento a supera, e o novo regime climático`
- `T3.quiz[4].explicacao`: `Transformar é mexer na base — como a cidade funciona e quem decide — e por isso é a mais exigente.` → `Transformar é mexer na base (como a cidade funciona e quem decide) e por isso é a mais exigente.`
- `T3.fontes[0].obra`: `Ciências da Natureza e suas Tecnologias — Livro do Estudante, Ensino Médio` → `Ciências da Natureza e suas Tecnologias: Livro do Estudante, Ensino Médio`
- `T3.fontes[0].orgao`: `MEC/INEP — ENCCEJA` → `MEC/INEP (ENCCEJA)`
- `T3.fontes[0].detalhe`: `drenagem urbana — de onde vêm a Lei nº 13.276` → `drenagem urbana, de onde vêm a Lei nº 13.276`
- `T3.fontes[1].obra`: `Nós no Clima da Mudança: caminhos de Educação e Justiça Climática — Ensino Médio` → `Nós no Clima da Mudança: caminhos de Educação e Justiça Climática (Ensino Médio)`

Conferir: `node -e "global.window={};require('vm').runInThisContext(require('fs').readFileSync('app/content.js','utf8'));console.log(/[—–]/.test(JSON.stringify(window.VAND_CONTENT.trilha[2])))"` imprime `false`.

- [ ] **Step 6: Rodar smoke, largura e suíte**

Run: smoke (esperado: 0 FALHA; as asserções `[forma clima-em-mudanca-e-risco-na-cidade] ...` todas PASS), largura (0 falhas, `FIM: 185 medições`), `./run.sh -m pytest tests -q` (89 passed). Se o smoke acusar parágrafo acima de 45 palavras ou travessão, corrigir **o conteúdo**, não o teste.

- [ ] **Step 7: O gerador do arquivo de revisão**

Criar `scripts/gerar_revisao_textos.js`:

```js
// Gera reports/revisao_textos_estudo_2026_10_18.md: para cada Tema pedido, o texto
// ANTIGO e o NOVO de cada Seção, lado a lado, para o usuário conferir que nenhum
// fato mudou. A revisão científica é humana (ADR 0001); isto só a torna viável.
//
// Uso: node scripts/gerar_revisao_textos.js <ref-git-do-texto-antigo> <id-do-tema>...
const { execSync } = require('child_process');
const fs = require('fs');
const vm = require('vm');

function trilha(src) {
  const w = {};
  vm.runInNewContext(src, { window: w });
  return w.VAND_CONTENT.trilha;
}

const [ref, ...ids] = process.argv.slice(2);
if (!ref || !ids.length) { console.error('uso: node scripts/gerar_revisao_textos.js <ref> <id-do-tema>...'); process.exit(1); }
const antigo = trilha(execSync(`git show ${ref}:app/content.js`, { encoding: 'utf8', maxBuffer: 1 << 26 }));
const novo = trilha(fs.readFileSync('app/content.js', 'utf8'));

const antigoMd = (s) => {
  if (s.paragrafos) return s.paragrafos.join('\n\n');
  if (s.texto) return s.texto;
  const partes = [];
  (s.itens || []).forEach((d) => partes.push(`- ${d.valor ? d.valor + ': ' : ''}${d.rotulo}`));
  (s.termos || []).forEach((t) => partes.push(`- **${t.palavra}**: ${t.definicao}`));
  if (s.nota) partes.push('\n' + s.nota);
  return partes.join('\n');
};

const blocoMd = (b) => {
  switch (b.tipo) {
    case 'p': return b.texto;
    case 'lista': return b.itens.map((t, i) => (b.ordenada ? `${i + 1}. ` : '- ') + t).join('\n');
    case 'passos': return b.itens.map((p) => `- **${p.rotulo}${p.titulo ? ' · ' + p.titulo : ''}**: ${p.texto}`).join('\n');
    case 'comparacao': return b.lados.map((l) => `**${l.titulo}**\n` + l.itens.map((t) => '- ' + t).join('\n')).join('\n\n× \n\n');
    case 'pergunta': return `> **Pare e pense:** ${b.pergunta}\n> *Resposta:* ${b.resposta}`;
    case 'numeros': return b.itens.map((d) => `- ${d.valor ? d.valor + ': ' : ''}${d.rotulo}`).join('\n') + (b.nota ? '\n\n' + b.nota : '');
    case 'destaque': return `> ${b.titulo ? '**' + b.titulo + '.** ' : ''}${b.texto}`;
    case 'glossario': return b.termos.map((t) => `- **${t.palavra}**: ${t.definicao}`).join('\n') + (b.nota ? '\n\n' + b.nota : '');
    default: return `(bloco ${b.tipo})`;
  }
};
const novoMd = (s) => (s.tipo === 'blocos' ? s.blocos.map(blocoMd).join('\n\n') : antigoMd(s));

const saida = [
  '# Revisão dos textos de estudo: antes e depois',
  '',
  `Gerado por \`scripts/gerar_revisao_textos.js\`. Texto antigo tirado de \`${ref}\`.`,
  'Regra da reescrita: nenhum fato, número, nome, data ou ressalva novo, e nenhuma ressalva removida;',
  'só reordenar, dividir, cortar repetição e trocar a pontuação. **Confira, Seção a Seção, se o "Depois" diz o mesmo que o "Antes".**',
  ''
];
ids.forEach((id) => {
  const a = antigo.find((t) => t.id === id);
  const n = novo.find((t) => t.id === id);
  if (!a || !n) { console.error('Tema não encontrado: ' + id); process.exit(1); }
  saida.push(`## ${n.titulo}`, '');
  n.secoes.forEach((sn, i) => {
    saida.push(`### Seção ${i + 1}: ${sn.titulo}`, '', '**Antes**', '', antigoMd(a.secoes[i]), '', '**Depois**', '', novoMd(sn), '', '---', '');
  });
});
fs.mkdirSync('reports', { recursive: true });
fs.writeFileSync('reports/revisao_textos_estudo_2026_10_18.md', saida.join('\n'));
console.log('escrito reports/revisao_textos_estudo_2026_10_18.md (' + ids.length + ' Tema(s))');
```

- [ ] **Step 8: Gerar o arquivo de revisão**

Run: `node scripts/gerar_revisao_textos.js 47c5ae1 clima-em-mudanca-e-risco-na-cidade`
Expected: `escrito reports/revisao_textos_estudo_2026_10_18.md (1 Tema(s))`. Abrir o arquivo e conferir que as 7 Seções têm "Antes" e "Depois" preenchidos (`47c5ae1` é o commit da spec, com o `content.js` ainda antigo).

- [ ] **Step 9: Subir o service worker e commitar**

`app/sw.js`: `IA_VAND-v14` → `IA_VAND-v15`.

```bash
git add app/content.js app/sw.js tests/app_smoke.html scripts/gerar_revisao_textos.js reports/revisao_textos_estudo_2026_10_18.md
git commit -m "$(cat <<'EOF'
feat(estudo): Tema 3 em blocos, sem travessões

As 7 Seções viram blocos curtos (lista, comparação, passos, Pare e pense) e os
travessões saem do conteúdo, do quiz e das fontes. Nenhum fato muda: o arquivo
reports/revisao_textos_estudo_2026_10_18.md traz o antes e o depois para
revisão. sw.js v15.

Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 4: Tema 2 (Quando a chuva vira enchente)

**Files:**
- Modify: `app/content.js`, `app/sw.js` (v16), `tests/app_smoke.html`, `reports/revisao_textos_estudo_2026_10_18.md`

**Interfaces:**
- Consumes: aplicador `$SCRATCH/aplicar_secoes.py` (Task 3, Step 2), `checarTemaMigrado`, gerador de revisão.

- [ ] **Step 1: Chamar a verificação do Tema 2 (vai falhar)**

Em `tests/app_smoke.html`, depois de `checarTemaMigrado('clima-em-mudanca-e-risco-na-cidade');`, inserir `  checarTemaMigrado('quando-a-chuva-vira-enchente');`. Run: smoke. Expected: FALHAs `[forma quando-a-chuva-vira-enchente] ...`.

- [ ] **Step 2: O conteúdo novo do Tema 2**

```js secoes-tema-2
        {
          tipo: 'blocos',
          titulo: 'A mesma chuva, dois destinos',
          blocos: [
            { tipo: 'p', texto: 'Ninguém consegue impedir a chuva, e ainda bem. É dela que vêm os açudes, os poços e os reservatórios que abastecem cidades inteiras.' },
            { tipo: 'p', texto: 'O Tema anterior mostrou que a água não é fabricada por ninguém: ela só circula. A chuva é a etapa desse ciclo em que a água volta para o chão.' },
            { tipo: 'p', texto: 'O que muda tudo é o que ela encontra quando chega lá.' },
            { tipo: 'comparacao', lados: [
              { titulo: 'Solo com vegetação', itens: ['A água infiltra devagar.', 'Alimenta o lençol subterrâneo.', 'Demora a chegar ao rio.'] },
              { titulo: 'Asfalto', itens: ['A água não infiltra.', 'Escorre na hora, inteira, para o ponto mais baixo do bairro.', 'Chega ao bueiro toda de uma vez.'] }
            ] },
            { tipo: 'destaque', titulo: 'Mesma nuvem, tardes diferentes', texto: 'É por isso que duas ruas da mesma cidade, debaixo da mesma nuvem, podem terminar a tarde de formas completamente diferentes. A chuva foi igual. O que o chão fez com ela, não.' }
          ]
        },
        {
          tipo: 'blocos',
          titulo: 'Quarenta minutos',
          blocos: [
            { tipo: 'numeros', itens: [
              { valor: '40 min', rotulo: 'de chuva forte, em São Paulo, em 28 de novembro de 2001' },
              { valor: '20', rotulo: 'pontos de alagamento na cidade' },
              { valor: '', rotulo: 'Carros arrastados pelas ruas, um rio transbordado e o trânsito parado: tudo dentro desses quarenta minutos', largo: true }
            ] },
            { tipo: 'p', texto: 'O episódio é o exemplo que o livro oficial do ENCCEJA usa para abrir a discussão.' },
            { tipo: 'p', texto: 'Ele desfaz a intuição de que enchente exige um temporal de dias: quando o solo já não absorve e a drenagem já está no limite, quarenta minutos bastam.' }
          ]
        },
        {
          tipo: 'blocos',
          titulo: 'O que a cidade faz com a água',
          blocos: [
            { tipo: 'p', texto: 'As alterações que agravam uma enchente quase nunca foram feitas para agravar nada. Foram feitas para facilitar a vida, e o efeito colateral só aparece no dia da chuva.' },
            { tipo: 'p', texto: 'O livro do ENCCEJA lista as principais:' },
            { tipo: 'lista', itens: [
              'Córregos canalizados de forma malfeita.',
              'Cursos de pequenos rios alterados.',
              'Barragens mal construídas.',
              'Acima de tudo, a impermeabilização do solo, pelo asfaltamento das ruas e pela pavimentação dos quintais.'
            ] },
            { tipo: 'p', texto: 'Some a isso o que acontece nas margens.' },
            { tipo: 'passos', itens: [
              { rotulo: '1', titulo: 'Desmata-se', texto: 'A beira do rio é desmatada para plantar ou criar gado, e o solo fica exposto.' },
              { rotulo: '2', titulo: 'Erosão', texto: 'Sem raiz que o segure, o solo é levado pela erosão e vai parar no fundo do rio.' },
              { rotulo: '3', titulo: 'O leito sobe', texto: 'O leito sobe e a passagem estreita.' },
              { rotulo: '4', titulo: 'Transborda', texto: 'O mesmo volume de água que antes cabia passa a transbordar.' }
            ] },
            { tipo: 'p', texto: 'O lixo fecha a conta. Jogado na rua ou no córrego, ele é levado pela água até o bueiro e o entope justamente quando o bueiro mais precisa funcionar. É a única peça dessa lista que não depende de obra pública nenhuma para mudar.' },
            { tipo: 'destaque', titulo: 'Uma injustiça embutida', texto: 'Quem mora mais perto do rio e da encosta costuma ser quem teve menos escolha sobre onde morar. O risco não se distribui por sorteio: ele se concentra em quem já tinha menos.' }
          ]
        },
        {
          tipo: 'blocos',
          titulo: 'Quatro palavras que não são sinônimos',
          blocos: [
            { tipo: 'glossario', termos: [
              { palavra: 'Enchente', definicao: 'O nível da água sobe acima do normal por causa do aumento da vazão, mas a água ainda corre dentro do leito do rio. É a palavra mais usada no dia a dia, e a única das quatro que a classificação oficial de desastres não lista.' },
              { palavra: 'Inundação (COBRADE 1.2.1.0.0)', definicao: 'A água submerge áreas fora dos limites normais do curso d’água, que normalmente não ficam submersas. O transbordamento é gradual, e costuma vir de chuva prolongada em área de planície.' },
              { palavra: 'Enxurrada (COBRADE 1.2.2.0.0)', definicao: 'Escoamento superficial de alta velocidade e energia, provocado por chuva intensa e concentrada, normalmente em bacias pequenas de relevo acidentado. A vazão sobe de repente e a calha do rio transborda de forma brusca. É a de maior poder destrutivo.' },
              { palavra: 'Alagamento (COBRADE 1.2.3.0.0)', definicao: 'Acúmulo de água em ruas, calçadas e outras estruturas urbanas porque a capacidade de escoamento da drenagem foi excedida por chuva intensa. É um problema de bueiro e de galeria, não de rio.' }
            ] },
            { tipo: 'p', texto: 'Repare no contraste entre as duas do meio, porque ele é a diferença entre ter tempo e não ter.' },
            { tipo: 'comparacao', lados: [
              { titulo: 'Inundação', itens: ['Sobe devagar.', 'Em terreno plano.', 'Depois de dias de chuva.', 'Dá para avisar, dá para sair.'] },
              { titulo: 'Enxurrada', itens: ['Desce de uma vez.', 'Em terreno inclinado.', 'Durante a chuva.', 'É justamente por isso que mata mais.'] }
            ] },
            { tipo: 'p', texto: 'As três com código são tipos oficiais da Classificação e Codificação Brasileira de Desastres (COBRADE), que a defesa civil usa para registrar cada ocorrência do país. As palavras acima são nossas; os códigos permitem conferir cada uma na fonte.' }
          ]
        },
        {
          tipo: 'blocos',
          titulo: 'Por que nenhuma previsão do tempo prevê alagamento',
          blocos: [
            { tipo: 'p', texto: 'Repare no que a definição de alagamento diz: capacidade de escoamento do sistema de drenagem. Não há uma palavra sobre atmosfera.' },
            { tipo: 'comparacao', lados: [
              { titulo: 'O que um modelo meteorológico calcula', itens: ['Como o ar se comporta.', 'Para onde vai a umidade.', 'Onde ela condensa.', 'Quanta chuva cai em cada pedaço do mapa.'] },
              { titulo: 'O que ele não sabe', itens: ['Onde ficam os bueiros da sua rua.', 'Se estão entupidos.', 'Que o terreno da esquina é o ponto mais baixo do quarteirão.'] }
            ] },
            { tipo: 'p', texto: 'Prever chuva e prever alagamento são, portanto, dois problemas diferentes. O primeiro a meteorologia resolve razoavelmente bem.' },
            { tipo: 'p', texto: 'O segundo depende de drenagem, topografia e manutenção: informação que não está em satélite nenhum, e que costuma existir apenas na cabeça de quem mora ali.' },
            { tipo: 'pergunta', pergunta: 'Por que a previsão do tempo não diz se a sua rua vai alagar?', resposta: 'Porque o alagamento depende de drenagem, topografia e manutenção, e essa informação não está em satélite nenhum.' },
            { tipo: 'destaque', titulo: 'Ameaça e dano', texto: 'É a diferença entre a ameaça e o dano. A previsão descreve a ameaça que vem do céu; o estrago que ela causa depende de vulnerabilidade: quem está exposto, onde, e com que capacidade de se recuperar depois.' }
          ]
        },
        {
          tipo: 'blocos',
          titulo: 'Onde este aplicativo entra',
          blocos: [
            { tipo: 'p', texto: 'É exatamente por isso que a aba Registro existe. Nenhum modelo nos diria que a sua esquina alagou: só você pode.' },
            { tipo: 'destaque', titulo: 'O registro mais valioso', texto: 'O registro mais valioso não é o "sim, alagou". É o "não, aqui está seco", enviado no meio de uma chuva forte.' },
            { tipo: 'p', texto: 'Sem os dois, existe apenas uma lista de lugares que alagaram, e não dá para aprender onde não alaga a partir de uma lista dessas.' },
            { tipo: 'p', texto: 'O aviso do INMET, que você vê na aba Alerta, cobre uma região inteira; o que acontece na sua rua, dentro dessa região, só o seu registro conta.' }
          ]
        }
```

- [ ] **Step 3: Aplicar**

Run: `python3 $SCRATCH/aplicar_secoes.py docs/superpowers/plans/2026-10-18-textos-de-estudo-blocos.md 2` e `node --check app/content.js`.

- [ ] **Step 4: Travessões fora das Seções do Tema 2**

Em `app/content.js`, dentro do Tema 2:

- `T2.reflexoes[1]`: `E quem você acha que deveria resolver isso — o morador, a prefeitura, os dois?` → `E quem você acha que deveria resolver isso: o morador, a prefeitura, os dois?`
- `T2.quiz[1].explicacao`: `As outras três opções vão na direção contrária — todas aumentam a capacidade de absorver ou de escoar.` → `As outras três opções vão na direção contrária: todas aumentam a capacidade de absorver ou de escoar.`
- `T2.quiz[4].explicacao`: `não são atmosfera — são a cidade.` → `não são atmosfera, são a cidade.`
- `T2.fontes[0].obra`: `Ciências — Livro do Estudante, Ensino Fundamental` → `Ciências: Livro do Estudante, Ensino Fundamental`
- `T2.fontes[0].orgao`: `MEC/INEP — ENCCEJA` → `MEC/INEP (ENCCEJA)`
- `T2.fontes[1].orgao`: `Ministério do Desenvolvimento Regional — hoje Ministério da Integração e do Desenvolvimento Regional, Secretaria Nacional de Proteção e Defesa Civil` → `Ministério do Desenvolvimento Regional (hoje Ministério da Integração e do Desenvolvimento Regional), Secretaria Nacional de Proteção e Defesa Civil`
- `T2.fontes[2].orgao`: `UERJ — grupo Prodocência; publicação independente` → `UERJ, grupo Prodocência; publicação independente`

Conferir com o mesmo `node -e` da Task 3 trocando `trilha[2]` por `trilha[1]`: imprime `false`.

- [ ] **Step 5: Rodar tudo**

Run: smoke (0 FALHA), largura (0 falhas, 185 medições), suíte (89 passed).

- [ ] **Step 6: Arquivo de revisão, sw e commit**

Run: `node scripts/gerar_revisao_textos.js 47c5ae1 quando-a-chuva-vira-enchente clima-em-mudanca-e-risco-na-cidade`. `app/sw.js`: `IA_VAND-v15` → `IA_VAND-v16`.

```bash
git add app/content.js app/sw.js tests/app_smoke.html reports/revisao_textos_estudo_2026_10_18.md
git commit -m "$(cat <<'EOF'
feat(estudo): Tema 2 em blocos, sem travessões

As 6 Seções viram blocos curtos e os travessões saem do conteúdo, do quiz e
das fontes. Nenhum fato muda; o antes e o depois estão em
reports/revisao_textos_estudo_2026_10_18.md. sw.js v16.

Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 5: Tema 1 (De onde vem a chuva)

**Files:**
- Modify: `app/content.js`, `app/sw.js` (v17), `tests/app_smoke.html`, `reports/revisao_textos_estudo_2026_10_18.md`

**Interfaces:**
- Consumes: as mesmas da Task 4.

- [ ] **Step 1: Chamar a verificação do Tema 1 (vai falhar)**

Em `tests/app_smoke.html`, depois de `checarTemaMigrado('quando-a-chuva-vira-enchente');`, inserir `  checarTemaMigrado('de-onde-vem-a-chuva');`. Run: smoke. Expected: FALHAs `[forma de-onde-vem-a-chuva] ...`.

- [ ] **Step 2: O conteúdo novo do Tema 1**

```js secoes-tema-1
        {
          tipo: 'blocos',
          titulo: 'Água que ninguém fabrica',
          blocos: [
            { tipo: 'p', texto: 'A água que sai da sua torneira hoje não foi criada em lugar nenhum. Ela já foi chuva, já foi rio, já esteve dentro de uma planta e já evaporou de um oceano, muitas vezes.' },
            { tipo: 'p', texto: 'O ciclo da água é o exemplo mais antigo de reciclagem que existe, e ele funciona sem que ninguém precise organizá-lo.' },
            { tipo: 'p', texto: 'O que muda é o estado e o lugar.' },
            { tipo: 'passos', itens: [
              { rotulo: '1', titulo: 'Evapora', texto: 'O calor do Sol evapora a água da superfície.' },
              { rotulo: '2', titulo: 'Condensa', texto: 'No alto, mais frio, o vapor se condensa em gotas minúsculas e forma nuvens.' },
              { rotulo: '3', titulo: 'Cai', texto: 'Quando essas gotas crescem o bastante para o ar não as sustentar mais, elas caem.' },
              { rotulo: '4', titulo: 'Segue o caminho', texto: 'Parte escorre para rios, parte infiltra no solo e alimenta reservatórios subterrâneos, parte evapora de novo.' }
            ] },
            { tipo: 'p', texto: 'Nada se perde no caminho, só troca de endereço.' },
            { tipo: 'destaque', titulo: 'Por isso', texto: 'O problema da água quase nunca é de quantidade total. É de estar na hora certa, no lugar certo e limpa o suficiente para usar.' }
          ]
        },
        {
          tipo: 'blocos',
          titulo: 'Quanta água existe, de verdade',
          blocos: [
            { tipo: 'numeros', itens: [
              { valor: '97%', rotulo: 'Da água do planeta, é salgada' },
              { valor: '3%', rotulo: 'É doce' },
              { valor: '', rotulo: 'E da parte doce, a maior fatia está congelada em geleiras e calotas polares, ou sob o solo, como água subterrânea', largo: true }
            ] },
            { tipo: 'p', texto: 'Rios e lagos, de onde a água é retirada com mais facilidade, são uma fração pequena desses 3%. É o que torna o desperdício e a poluição tão caros: estraga-se justamente a parte acessível.' }
          ]
        },
        {
          tipo: 'blocos',
          titulo: 'Um poeta gaúcho já tinha dito',
          blocos: [
            { tipo: 'p', texto: 'O livro oficial do ENCCEJA abre a discussão sobre água com um poema de Raul Bopp, nascido no Rio Grande do Sul em 1898.' },
            { tipo: 'p', texto: 'O poema fala de um rio imenso e sem margens que, de tanto correr, um dia secou.' },
            { tipo: 'p', texto: 'O material comenta que essa é a cara do problema da água no Brasil:' },
            { tipo: 'comparacao', lados: [
              { titulo: 'Ora cheia', itens: ['Inunda tudo, como se os rios não tivessem margem.'] },
              { titulo: 'Ora estiagem', itens: ['Seca o fundo.'] }
            ] },
            { tipo: 'destaque', titulo: 'O mesmo ciclo', texto: 'Cheia e estiagem não são dois problemas. São o mesmo ciclo, visto em dois momentos.' }
          ]
        },
        {
          tipo: 'blocos',
          titulo: 'Como alguém sabe que vai chover',
          blocos: [
            { tipo: 'p', texto: 'Prever o tempo sempre foi observar a natureza. Durante a maior parte da história, isso significou reparar em bichos e plantas: ditados como "cigarra cantou, calor chegou" são exatamente isso.' },
            { tipo: 'p', texto: 'Quando o ser humano passou a plantar e criar animais, acertar a previsão virou questão de sobrevivência.' },
            { tipo: 'p', texto: 'O método continua sendo observação; o que mudou foi o instrumento. A meteorologia, ciência que estuda a atmosfera, precisa de milhares de pontos de observação espalhados pelo mundo.' },
            { tipo: 'p', texto: 'Esses pontos são as estações meteorológicas, e elas não ficam só no chão. Existem estações:' },
            { tipo: 'lista', itens: [
              'Terrestres.',
              'Marítimas, em navios e boias.',
              'Aéreas, em balões e satélites.'
            ] },
            { tipo: 'pergunta', pergunta: 'Por que a meteorologia usa estações em navios, boias, balões e satélites, e não só no chão?', resposta: 'Porque ela precisa de milhares de pontos de observação espalhados pelo mundo, e as estações não ficam só no chão: existem as terrestres, as marítimas e as aéreas.' },
            { tipo: 'passos', itens: [
              { rotulo: '1', titulo: 'Medem', texto: 'Cada estação mede continuamente coisas como temperatura, umidade, pressão, vento e chuva.' },
              { rotulo: '2', titulo: 'Enviam', texto: 'Os números seguem para centros meteorológicos.' },
              { rotulo: '3', titulo: 'Calculam', texto: 'Lá, computadores reúnem tudo e calculam como a atmosfera deve se comportar nas próximas horas e dias.' },
              { rotulo: '4', titulo: 'Previsão', texto: 'É daí que sai a previsão que você vê no jornal.' }
            ] }
          ]
        },
        {
          tipo: 'blocos',
          titulo: 'Onde este aplicativo entra',
          blocos: [
            { tipo: 'p', texto: 'As estações meteorológicas descritas acima não são um conceito distante.' },
            { tipo: 'p', texto: 'O Instituto Nacional de Meteorologia (INMET) opera uma rede delas no Rio Grande do Sul, e é dessa rede que sai o dado que este projeto estuda.' },
            { tipo: 'destaque', titulo: 'No aplicativo', texto: 'Quando você recebe um aviso na aba Alerta, ele nasceu de medições feitas por estações como as que você acabou de conhecer.' }
          ]
        }
```

- [ ] **Step 3: Aplicar**

Run: `python3 $SCRATCH/aplicar_secoes.py docs/superpowers/plans/2026-10-18-textos-de-estudo-blocos.md 1` e `node --check app/content.js`.

- [ ] **Step 4: Travessões fora das Seções do Tema 1**

- `T1.quiz[1].explicacao`: `são uma fração pequena — por isso poluí-los custa tão caro.` → `são uma fração pequena. Por isso poluí-los custa tão caro.`
- `T1.quiz[4].explicacao`: `escoa e infiltra — muda de estado e de reservatório` → `escoa e infiltra: muda de estado e de reservatório`
- `T1.fontes[0].obra`: `Ciências — Livro do Estudante, Ensino Fundamental` → `Ciências: Livro do Estudante, Ensino Fundamental`
- `T1.fontes[0].orgao`: `MEC/INEP — ENCCEJA` → `MEC/INEP (ENCCEJA)`

Atenção: as strings `Ciências — Livro do Estudante, Ensino Fundamental` e `MEC/INEP — ENCCEJA` existem **também no Tema 2** (já trocadas na Task 4); aqui só restam as do Tema 1, então a troca é única. Conferir com o `node -e` de antes usando `trilha[0]`: `false`.

- [ ] **Step 5: Verificação global dos travessões**

Run: `node -e "global.window={};require('vm').runInThisContext(require('fs').readFileSync('app/content.js','utf8'));console.log(/[—–]/.test(JSON.stringify(window.VAND_CONTENT)))"`
Expected: `false`. E `grep -n "—" app/content.js` só pode listar linhas de comentário do cabeçalho do arquivo (se alguma), nunca string de dado.

- [ ] **Step 6: Rodar tudo**

Run: smoke (0 FALHA), largura (0 falhas, 185 medições), suíte (89 passed).

- [ ] **Step 7: Arquivo de revisão completo, sw e commit**

Run: `node scripts/gerar_revisao_textos.js 47c5ae1 de-onde-vem-a-chuva quando-a-chuva-vira-enchente clima-em-mudanca-e-risco-na-cidade`. `app/sw.js`: `IA_VAND-v16` → `IA_VAND-v17`.

```bash
git add app/content.js app/sw.js tests/app_smoke.html reports/revisao_textos_estudo_2026_10_18.md
git commit -m "$(cat <<'EOF'
feat(estudo): Tema 1 em blocos, sem travessões

As 5 Seções viram blocos curtos e os travessões saem do conteúdo, do quiz e
das fontes. Os três Temas estão migrados; o arquivo de revisão cobre os três.
sw.js v17.

Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 6: Fechamento (spec e verificação final)

**Files:**
- Modify: `docs/superpowers/specs/2026-10-18-textos-de-estudo-blocos-design.md` (nota de desvio)

- [ ] **Step 1: Registrar o desvio na spec**

Acrescentar ao fim da spec:

```markdown

## Correções feitas no plano (18/10/2026)

- Nos campos `obra`, `orgao` e `detalhe` de `fontes`, o separador " — " virou ":" ou
  parênteses. Prevalece a regra dos travessões, só na pontuação; nenhuma palavra
  da citação mudou. "Citações idênticas" vale para o conteúdo da citação.
- O verificador de texto visível exercita as telas que só mostram certas frases com
  dado presente (card de lacuna, Registro com aviso) simulando `aviso` no teste.
- `tests/app_largura.html` não precisou de mudança: já percorre as 37 rotas.
```

- [ ] **Step 2: Conferência final**

Run, e ler cada saída: smoke (esperado: 0 FALHA), largura (0 falhas, `FIM: 185 medições`), `./run.sh -m pytest tests -q` (89 passed), e o `node -e` de travessões (`false`). Ver, em screenshots a 360 px, uma Seção de cada Tema (por exemplo `.../clima-em-mudanca-e-risco-na-cidade/s/3`, `.../quando-a-chuva-vira-enchente/s/4`, `.../de-onde-vem-a-chuva/s/1`) e conferir: passos com a linha ligando os marcadores, comparação empilhada, "Pare e pense" fechado.

- [ ] **Step 3: Commit**

```bash
git add docs/superpowers/specs/2026-10-18-textos-de-estudo-blocos-design.md docs/superpowers/plans/2026-10-18-textos-de-estudo-blocos.md
git commit -m "$(cat <<'EOF'
docs: plano dos textos de estudo em blocos e desvio registrado na spec

Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>
EOF
)"
```

- [ ] **Step 4: PARAR e pedir confirmação ao usuário antes do push**

Mostrar `git log --oneline origin/main..HEAD` e esperar o "pode". O push publica o app; o `sw.js` já está na v17 desde a Task 5.

---

### Task 7 (opcional, só se sobrar tempo): diagrama do ciclo da água

**Files:**
- Modify: `app/app.js` (bloco `figura`), `app/styles.css`, `app/content.js` (Seção 1 do Tema 1), `app/sw.js` (v18), `tests/app_smoke.html`

**Interfaces:**
- Produces: bloco `figura { id: 'ciclo-da-agua', legenda }`.

- [ ] **Step 1: Asserção (falha)** — na fixture da Task 2 adicionar `{ tipo: 'figura', id: 'ciclo-da-agua', legenda: 'Legenda de teste.' }` e a asserção `ok(!!secFx.querySelector('figure.bloco-figura svg[role="img"]') && secFx.querySelector('figcaption').textContent === 'Legenda de teste.', 'blocos: figura do ciclo da água renderiza o SVG e a legenda');`. Run: smoke → FALHA.

- [ ] **Step 2: Implementar** — em `BLOCOS` de `app/app.js`:

```js
    figura: function (b) {
      if (b.id !== 'ciclo-da-agua') return null;
      var NS = 'http://www.w3.org/2000/svg';
      var svg = document.createElementNS(NS, 'svg');
      svg.setAttribute('viewBox', '0 0 320 180');
      svg.setAttribute('role', 'img');
      svg.setAttribute('aria-label', 'Ciclo da água: a água evapora do mar, forma nuvens, cai como chuva e volta ao mar pelos rios');
      svg.setAttribute('class', 'figura-ciclo');
      svg.innerHTML =
        '<path class="f-terra" d="M0 130 L120 130 L150 100 L190 100 L210 130 L320 130 L320 180 L0 180Z"/>' +
        '<path class="f-mar" d="M200 130 L320 130 L320 180 L200 180Z"/>' +
        '<ellipse class="f-nuvem" cx="150" cy="36" rx="46" ry="16"/><ellipse class="f-nuvem" cx="178" cy="32" rx="28" ry="12"/>' +
        '<path class="f-seta" d="M260 120 C260 90 240 70 200 50" /><path class="f-seta" d="M150 56 L150 84"/><path class="f-seta" d="M110 128 C140 150 190 150 214 138"/>' +
        '<text x="262" y="96">evapora</text><text x="158" y="76">chove</text><text x="104" y="160">escorre e infiltra</text>';
      return el('figure', { class: 'bloco-figura' }, [svg, el('figcaption', { text: b.legenda })]);
    },
```

`app/styles.css`:

```css
.bloco-figura { margin: 0 0 16px; }
.figura-ciclo { width: 100%; height: auto; display: block; background: var(--surface); border: 1px solid var(--border); border-radius: var(--radius); }
.figura-ciclo .f-terra { fill: var(--surface-2); } .figura-ciclo .f-mar { fill: var(--accent-soft); }
.figura-ciclo .f-nuvem { fill: var(--surface-3); stroke: var(--border-forte); }
.figura-ciclo .f-seta { fill: none; stroke: var(--accent); stroke-width: 2; stroke-linecap: round; }
.figura-ciclo text { fill: var(--text-dim); font-size: 11px; font-family: inherit; }
.bloco-figura figcaption { margin-top: 6px; font-size: .86rem; color: var(--text-dim); }
```

Em `app/content.js`, na Seção 1 do Tema 1, inserir depois do bloco `passos` e antes do `p` "Nada se perde no caminho": `{ tipo: 'figura', id: 'ciclo-da-agua', legenda: 'O caminho da água: do mar para o ar, do ar para o chão, do chão de volta ao mar.' },` (a legenda só resume as quatro etapas já descritas). `app/sw.js`: v17 → v18.

- [ ] **Step 3: Rodar tudo e conferir a figura em screenshot a 360 px** (smoke 0 FALHA, largura 0 falhas, suíte 89 passed). Se o desenho ficar feio ou confuso, **não publicar**: reverter a Task 7 inteira (`git checkout`), pois a figura é opcional.

- [ ] **Step 4: Commit** (`feat(estudo): diagrama do ciclo da água no Tema 1`, com o trailer) e **pedir confirmação antes do push**.

---

## Self-review

- **Cobertura da spec:** tipo `blocos` e os blocos (Task 2); reescrita das 18 Seções (Tasks 3 a 5: 7 + 6 + 5); travessões na interface (Task 1) e no conteúdo (Tasks 3 a 5); testes de forma (Task 1 + 2); arquivo de revisão lado a lado (Task 3, incrementado nas 4 e 5); ordem de entrega (componentes, Tema 3, 2, 1, diagrama opcional); `sw.js` a cada publicação; vocabulário no `CONTEXT.md`.
- **Placeholders:** nenhum. O conteúdo das 18 Seções está completo e é o que o aplicador cola; as substituições de travessão fora das Seções listam texto antigo e novo.
- **Consistência de nomes:** `BLOCOS`, `checarTemaMigrado`, `textoVisivel`, classes `.bloco-*`, `.passo-marca`, `.comp-lado`, `.comp-x` iguais em todas as tasks; `SCRATCH` é a pasta de rascunho da sessão.
- **Rastreabilidade (revisão humana):** as frases novas foram escritas só por reordenação, divisão e troca de pontuação sobre o texto antigo; os três pontos em que um bloco reorganiza o sentido (os `pergunta`) usam como resposta frases que já estavam no texto. O usuário confere pelo arquivo de revisão.
