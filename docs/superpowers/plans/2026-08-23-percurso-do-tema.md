# Percurso do Tema — Plano de Implementação

> **Para executores agênticos:** SUB-SKILL OBRIGATÓRIA: use
> superpowers:subagent-driven-development ou superpowers:executing-plans para
> implementar tarefa a tarefa. Os passos usam caixas (`- [ ]`).

**Objetivo:** substituir a tela única de um Tema por um percurso navegável —
índice, uma Seção por tela, e progresso de leitura retomável.

**Arquitetura:** o roteador por hash ganha segmentos abaixo do Tema
(`/s/<n>`, `/pensar`, `/fontes`, `/quiz`). O que hoje é uma função
(`renderTema`) que despeja tudo vira cinco telas pequenas que compartilham um
montador de Seção. O progresso ganha um campo `lidas` na entrada que já existe
no `localStorage`, sem trocar a versão da chave.

**Stack:** HTML, CSS e JavaScript puros, ES5, sem build e sem dependência nova.
Teste: `tests/app_smoke.html` rodado em Chrome headless.

**Spec:** `docs/superpowers/specs/2026-08-23-percurso-do-tema-design.md` — leia
antes de começar; este plano argumenta a partir dela.

## Global Constraints

- **Nenhuma palavra do conteúdo muda.** `docs/adr/0001` exige revisão humana de
  afirmação científica. `app/content.js` **não é editado neste plano**.
- **Nada trava.** O quiz é alcançável com zero Seções lidas (`docs/adr/0002`).
- **Nada de gamificação**: sem pontos, sequência, "desbloqueou" ou comemoração.
- **Vocabulário de `CONTEXT.md`**: Trilha, Tema, Nível, Seção, Item, Reflexão,
  Fonte. A interface segue dizendo "questão" onde já dizia — ver a seção
  "Uma inconsistência de vocabulário" da spec; não é para resolver aqui.
- **Sem host externo**, sem CDN, sem fonte remota.
- **Tema claro e escuro** em toda tela nova; movimento atrás de
  `prefers-reduced-motion`.
- **Alvo de toque mínimo 44px** — vale para cada item do índice.
- **A rota conta a partir de 1, o armazenamento a partir de 0.** `s/1` é
  `tema.secoes[0]` e grava `0` em `lidas`. A conversão acontece só em
  `passoDoTema()`.
- **A porta 8000 está ocupada nesta máquina.** Use 8791.
- **Commits:** a árvore está limpa a partir de `6bdb6c6` (Task 1 commitada), e
  precisa continuar assim entre as tarefas. Use os caminhos exatos que cada
  passo lista; **nunca `git add -A` nem `git add .`**.
  **Antes de commitar, rode `git status --short` e confirme que só os arquivos
  do passo aparecem.** Se houver arquivo alheio modificado, PARE e relate — não
  tente montar um commit parcial com cirurgia de índice. Um commit precisa ser
  um estado que passa no teste; a Task 1 já falhou nisso uma vez, produzindo um
  commit verde na árvore e vermelho isolado.
- Datas absolutas. Hoje é 23/08/2026.

---

## Estrutura de arquivos

| arquivo | responsabilidade |
|---|---|
| `app/app.js` | roteador, progresso, e as cinco telas do Tema |
| `app/styles.css` | índice do Tema e rodapé de encadeamento |
| `tests/app_smoke.html` | `percorre()` vira travessia; asserções novas |
| `app/sw.js` | `VERSAO` |
| `app/content.js` | **não muda** |

## Como rodar o teste (todas as tarefas usam isto)

```sh
cd /home/jose-garcia/Projetos/Playground/IA_VAND
pgrep -f "http.server 8791" >/dev/null || (python3 -m http.server 8791 >/dev/null 2>&1 &)
sleep 1
google-chrome --headless=new --no-sandbox --dump-dom --virtual-time-budget=10000 \
  http://localhost:8791/tests/app_smoke.html 2>/dev/null \
  | python3 -c "
import sys,re,html
m=re.search(r'<pre id=\"saida\">(.*?)</pre>',sys.stdin.read(),re.S)
l=[x for x in html.unescape(m.group(1)).split(chr(10)) if x.strip()]
print(len([x for x in l if x.startswith('PASS')]),'PASS |',len([x for x in l if 'FALHA' in x]),'FALHA')
[print('  >>',x) for x in l if 'FALHA' in x]
"
```

Se `google-chrome` não existir, tente `chromium` ou `chromium-browser`. A
baseline antes da Tarefa 1 é **72 PASS, 0 FALHA**.

---

## Task 1: Progresso por Seção, e a regressão que ele causa na Trilha

O campo `lidas` faz a entrada do `localStorage` nascer ao ler a primeira Seção,
e não mais só ao terminar o quiz. `renderTrilha` decide "Tema concluído" por
**existência de entrada** — então passaria a contar Tema apenas lido como
concluído e a mostrar `quiz: undefined de undefined`. Esta tarefa introduz o
campo e conserta a leitura no mesmo movimento, para que a regressão nunca chegue
a existir na árvore.

**Files:**
- Modify: `app/app.js` (bloco "progresso", e `renderTrilha`)
- Test: `tests/app_smoke.html`

**Interfaces:**
- Produces: `lidasDe(temaId) -> number[]`, `marcarLida(temaId, i) -> void`,
  `quizFeito(entrada) -> boolean`. As tarefas 2 e 3 consomem as três.

- [ ] **Step 1: Escrever a asserção que falha**

Em `tests/app_smoke.html`, logo antes da linha `escritos.forEach(percorre);`,
insira:

```js
// Uma entrada só de leitura (sem quiz) não pode contar como Tema concluído,
// nem produzir "quiz: undefined de undefined" no cartão.
(function () {
  var alvo = escritos[0].id;
  localStorage.setItem('vand.progresso.v1', JSON.stringify(
    (function () { var o = {}; o[alvo] = { lidas: [0] }; return o; })()
  ));
  irPara('#/estudar');
  var card = document.querySelectorAll('.tema-card')[0];
  ok(card.textContent.indexOf('undefined') === -1,
     'cartao de Tema so lido nao mostra "undefined"');
  ok(card.textContent.indexOf('1 de ' + escritos[0].secoes.length + ' seções') > -1,
     'cartao de Tema so lido mostra o progresso de leitura');
  var painel = document.querySelector('.painel .fracao span');
  ok(painel && painel.textContent.indexOf('0/') === 0,
     'barra da Trilha nao conta Tema so lido como concluido');
  localStorage.removeItem('vand.progresso.v1');
})();
```

- [ ] **Step 2: Rodar e confirmar que falha**

Rode o comando da seção "Como rodar o teste".
Esperado: **3 FALHA**, com `undefined` aparecendo no cartão.

- [ ] **Step 3: Acrescentar os três ajudantes de progresso**

Em `app/app.js`, logo depois de `registrarResultado(...)`:

```js
  // Uma entrada de progresso nasce ao ler a primeira Seção, então "tem entrada"
  // deixou de significar "fez o quiz". Toda leitura de conclusão passa por aqui.
  function quizFeito(entrada) {
    return !!(entrada && entrada.total > 0);
  }

  function lidasDe(temaId) {
    var e = lerProgresso()[temaId];
    return (e && e.lidas) || [];
  }

  function marcarLida(temaId, i) {
    var p = lerProgresso();
    var e = p[temaId] || {};
    var l = e.lidas || [];
    if (l.indexOf(i) === -1) {
      l.push(i);
      l.sort(function (a, b) { return a - b; });
    }
    e.lidas = l;
    p[temaId] = e;
    gravarProgresso(p);
  }
```

- [ ] **Step 4: Consertar a contagem da barra da Trilha**

Em `renderTrilha`, troque:

```js
    var feitos = prontos.filter(function (t) { return p[t.id]; }).length;
```

por:

```js
    var feitos = prontos.filter(function (t) { return quizFeito(p[t.id]); }).length;
```

- [ ] **Step 5: Consertar o rodapé do cartão**

Em `renderTrilha`, troque o bloco que monta `meta` por:

```js
      var feito = p[tema.id];
      var lidas = lidasDe(tema.id);

      var meta = el('div', { class: 'meta' }, [
        el('span', { text: tema.minutos + ' min de leitura' })
      ]);
      if (!pronto) {
        meta.appendChild(el('span', { class: 'selo-vazio', text: 'conteúdo em redação' }));
      } else if (quizFeito(feito)) {
        meta.appendChild(
          el('span', {
            class: 'selo-feito',
            text: 'quiz: ' + feito.acertos + ' de ' + feito.total
          })
        );
      } else if (lidas.length) {
        meta.appendChild(
          el('span', { text: lidas.length + ' de ' + tema.secoes.length + ' seções' })
        );
      } else {
        meta.appendChild(el('span', { text: tema.quiz.length + ' questões' }));
      }
```

- [ ] **Step 6: Rodar e confirmar que passa**

Esperado: **75 PASS, 0 FALHA**.

- [ ] **Step 7: Commit**

```bash
git add app/app.js tests/app_smoke.html
git commit -m "feat(app): progresso de leitura por Seção, sem confundir com quiz feito"
```

---

## Task 2: O roteador e as cinco telas do Tema

Tarefa grande de propósito: `percorre()` só pode ser reescrita uma vez, e ela
precisa que todas as rotas existam. Dividir aqui produziria uma árvore com o
teste vermelho no meio.

**Files:**
- Modify: `app/app.js` (`rota`, `ehTema`, `render`, `renderTema` → cinco telas)
- Test: `tests/app_smoke.html` (`percorre` reescrita)

**Interfaces:**
- Consumes: `lidasDe`, `marcarLida`, `quizFeito` (Task 1)
- Produces: `montarSecao(s) -> HTMLElement`, `passoDoTema(resto, tema) -> {tipo, i}`,
  `proximoPasso(tema, passo) -> {rota, rotulo}|null`. A Task 3 estiliza as
  classes `.tema-indice`, `.indice-item`, `.indice-item.lida`, `.encadeia`.

- [ ] **Step 1: Reescrever `percorre()` no teste — vai falhar**

Primeiro, acrescente um ajudante logo depois de `irPara` em
`tests/app_smoke.html`:

```js
// Um clique que NAVEGA só muda location.hash; o evento hashchange do navegador
// é assíncrono e não teria chegado até a próxima asserção. irPara dispara o
// evento à mão, e cliques de navegação precisam do mesmo tratamento.
// Cliques que apenas re-renderizam no lugar (alternativas do quiz, "próxima
// questão", "refazer") NÃO passam por aqui — eles não mexem no hash.
function clicarNavegando(seletor) {
  document.querySelector(seletor).click();
  window.dispatchEvent(new HashChangeEvent('hashchange'));
}
```

Depois substitua a função `percorre` inteira por:

```js
function percorre(tema) {
  var nome = '[' + tema.id + '] ';
  var base = '#/estudar/' + tema.id;

  // --- índice ---
  irPara(base);
  ok(!document.getElementById('voltar').hidden, nome + 'botao voltar aparece');
  ok(!!document.querySelector('.tema-indice'), nome + 'indice do Tema renderiza');
  ok(document.querySelectorAll('.indice-item').length === tema.secoes.length + 3,
     nome + 'indice lista as ' + tema.secoes.length + ' secoes + pensar, fontes e quiz');
  ok(document.querySelectorAll('#tela .secao').length === 0,
     nome + 'indice NAO despeja o texto das secoes');

  // --- percorre as Seções pelo encadeamento ---
  for (var i = 0; i < tema.secoes.length; i++) {
    irPara(base + '/s/' + (i + 1));
    ok(document.querySelectorAll('#tela .secao').length === 1,
       nome + 'secao ' + (i + 1) + ' renderiza uma secao por tela');
    var s = tema.secoes[i];
    if (s.tipo === 'glossario') {
      ok(document.querySelectorAll('.glossario .termo').length === s.termos.length,
         nome + 'glossario exibe os ' + s.termos.length + ' termos');
    }
    clicarNavegando('.encadeia');
  }

  // O encadeamento da última Seção leva a Para pensar.
  ok(tema.reflexoes.length > 0 && document.querySelectorAll('.reflexao').length === tema.reflexoes.length,
     nome + 'as ' + tema.reflexoes.length + ' reflexoes aparecem em Para pensar');

  // --- rota inválida cai no índice, em vez de tela em branco ---
  irPara(base + '/s/999');
  ok(!!document.querySelector('.tema-indice'), nome + 'secao fora de faixa cai no indice');
  irPara(base + '/inventado');
  ok(!!document.querySelector('.tema-indice'), nome + 'palavra-chave desconhecida cai no indice');

  // --- o índice agora marca tudo lido ---
  irPara(base);
  ok(document.querySelectorAll('.indice-item.lida').length === tema.secoes.length,
     nome + 'indice marca as ' + tema.secoes.length + ' secoes como lidas');

  // --- fontes ---
  irPara(base + '/fontes');
  ok(document.querySelectorAll('.fontes li').length === tema.fontes.length,
     nome + 'as ' + tema.fontes.length + ' fontes declaradas');

  // --- quiz, acertando tudo ---
  irPara(base + '/quiz');
  var total = tema.quiz.length;
  for (var q = 0; q < total; q++) {
    var alts = document.querySelectorAll('.quiz .alt');
    ok(alts.length === 4, nome + 'questao ' + (q + 1) + ' tem 4 alternativas');
    alts[tema.quiz[q].correta].click();
    ok(!!document.querySelector('.explica.certa'), nome + 'questao ' + (q + 1) + ' aceitou a correta');
    document.querySelector('.quiz .btn').click();
  }
  var score = document.querySelector('.resultado .score');
  ok(score && score.textContent === total + '/' + total, nome + 'resultado mostra ' + total + '/' + total);
  ok(document.querySelectorAll('.resultado ~ .btn-row .btn').length === 3,
     nome + 'resultado oferece voltar ao Tema, voltar a trilha e refazer');
  var salvo = JSON.parse(localStorage.getItem('vand.progresso.v1'))[tema.id];
  ok(salvo && salvo.acertos === total, nome + 'progresso gravado no localStorage');
  ok(salvo.lidas.length === tema.secoes.length, nome + 'as secoes lidas seguem gravadas');

  // --- refaz errando tudo: o melhor resultado não pode piorar ---
  document.querySelectorAll('.btn-row .btn')[2].click();
  for (var q2 = 0; q2 < total; q2++) {
    var a2 = document.querySelectorAll('.quiz .alt');
    a2[(tema.quiz[q2].correta + 1) % 4].click();
    if (q2 === 0) ok(!!document.querySelector('.explica.errada'), nome + 'resposta errada sinalizada');
    document.querySelector('.quiz .btn').click();
  }
  var depois = JSON.parse(localStorage.getItem('vand.progresso.v1'))[tema.id];
  ok(depois.acertos === total,
     nome + 'refazer pior nao apaga o melhor resultado (ficou ' + depois.acertos + ')');
}
```

- [ ] **Step 2: Rodar e confirmar que falha**

Esperado: muitas FALHA — `.tema-indice` não existe ainda.

- [ ] **Step 3: Extrair o montador de Seção**

Em `app/app.js`, o corpo do `tema.secoes.forEach(...)` de `renderTema` vira uma
função própria. Acrescente antes de `renderTrilha`:

```js
  // Monta UMA Seção. É o mesmo código que a tela única usava, sem alteração de
  // marcação nem de CSS — o que muda é quem chama, e quantas vezes.
  function montarSecao(s) {
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
      var glo = el('section', { class: 'secao' }, [el('h2', { text: s.titulo })]);
      var listaG = el('div', { class: 'glossario' });
      s.termos.forEach(function (t) {
        listaG.appendChild(
          el('div', { class: 'termo' }, [
            el('span', { class: 'palavra', text: t.palavra }),
            el('p', { text: t.definicao })
          ])
        );
      });
      glo.appendChild(listaG);
      if (s.nota) glo.appendChild(el('p', { class: 'nota', text: s.nota }));
      return glo;
    }
    if (s.tipo === 'dados') {
      var sec = el('section', { class: 'secao' }, [el('h2', { text: s.titulo })]);
      var grid = el('div', { class: 'dados' });
      s.itens.forEach(function (d) {
        var cls = 'dado' + (d.largo ? ' largo' : '');
        var filhos = d.valor
          ? [el('span', { class: 'valor', text: d.valor }), el('span', { class: 'rotulo', text: d.rotulo })]
          : [el('span', { class: 'rotulo', text: d.rotulo })];
        grid.appendChild(el('div', { class: cls }, filhos));
      });
      sec.appendChild(grid);
      if (s.nota) sec.appendChild(el('p', { class: 'nota', text: s.nota }));
      return sec;
    }
    return null;
  }
```

- [ ] **Step 4: Ensinar o roteador os segmentos do Tema**

Troque `rota()` por:

```js
  function rota() {
    var h = (location.hash || '#/estudar').replace(/^#\/?/, '');
    var partes = h.split('/').filter(Boolean);
    return { aba: partes[0] || 'estudar', temaId: partes[1] || null, resto: partes.slice(2) };
  }
```

E acrescente logo abaixo:

```js
  // O segmento `s` antes do número existe para que um Tema cujo id fosse
  // "quiz", "pensar" ou "fontes" não colidisse com as palavras-chave.
  // A rota conta a partir de 1; `i` é índice de array. A conversão é só aqui.
  function passoDoTema(resto, tema) {
    if (!resto.length) return { tipo: 'indice' };
    if (resto[0] === 'pensar') return { tipo: 'pensar' };
    if (resto[0] === 'fontes') return { tipo: 'fontes' };
    if (resto[0] === 'quiz') return { tipo: 'quiz' };
    if (resto[0] === 's') {
      var n = parseInt(resto[1], 10);
      if (n >= 1 && n <= tema.secoes.length) return { tipo: 'secao', i: n - 1 };
    }
    return { tipo: 'indice' };   // rota inválida cai no índice
  }

  function proximoPasso(tema, passo) {
    var base = '#/estudar/' + tema.id;
    if (passo.tipo === 'secao') {
      if (passo.i + 1 < tema.secoes.length) {
        return { rota: base + '/s/' + (passo.i + 2), rotulo: 'Próxima seção' };
      }
      if (tema.reflexoes.length) return { rota: base + '/pensar', rotulo: 'Para pensar' };
      return { rota: base + '/quiz', rotulo: 'Fazer o quiz' };
    }
    if (passo.tipo === 'pensar') return { rota: base + '/quiz', rotulo: 'Fazer o quiz' };
    return null;
  }
```

- [ ] **Step 5: `ehTema` passa a cobrir as telas abaixo do Tema**

Toda tela de um Tema abre no topo e não guarda posição. Troque o corpo de
`ehTema` por:

```js
  function ehTema(hash) {
    var h = (hash || '').replace(/^#\/?/, '');
    var partes = h.split('/').filter(Boolean);
    return partes[0] === 'estudar' && !!partes[1];
  }
```

(É o que já está lá; confirme e siga — o `partes.slice(2)` não afeta esta
leitura.)

- [ ] **Step 6: Despachar as cinco telas**

Em `render()`, troque o ramo de `estudar` por:

```js
    if (r.aba === 'estudar') {
      var tema = r.temaId && TRILHA.filter(function (t) { return t.id === r.temaId; })[0];
      if (!tema) { renderTrilha(); }
      else {
        var passo = passoDoTema(r.resto, tema);
        if (passo.tipo === 'indice') renderIndiceTema(tema);
        else if (passo.tipo === 'secao') renderSecao(tema, passo.i);
        else if (passo.tipo === 'pensar') renderPensar(tema);
        else if (passo.tipo === 'fontes') renderFontes(tema);
        else renderQuizTela(tema);
      }
    } else if (r.aba === 'alerta') {
```

- [ ] **Step 7: Escrever as cinco telas**

Substitua a função `renderTema` inteira por:

```js
  function renderIndiceTema(tema) {
    cabecalho(tema.titulo, tema.nivel + ' · ' + tema.minutos + ' min', true, '#/estudar');
    var base = '#/estudar/' + tema.id;
    var lidas = lidasDe(tema.id);

    var enchimento = el('i');
    tela.appendChild(
      el('div', { class: 'painel' }, [
        el('h2', { text: 'Seu progresso neste tema' }),
        el('div', { class: 'fracao' }, [
          el('span', { text: lidas.length + '/' + tema.secoes.length }),
          el('div', {
            class: 'barra',
            role: 'progressbar',
            'aria-valuenow': String(lidas.length),
            'aria-valuemin': '0',
            'aria-valuemax': String(tema.secoes.length)
          }, [enchimento])
        ]),
        el('p', {
          class: 'apoio',
          text: lidas.length === tema.secoes.length
            ? 'Leitura concluída. O quiz está logo abaixo.'
            : 'Seções lidas. Dá para parar e voltar depois — o app lembra.'
        })
      ])
    );
    requestAnimationFrame(function () {
      requestAnimationFrame(function () {
        enchimento.style.setProperty(
          '--pct', Math.round((lidas.length / tema.secoes.length) * 100) + '%');
      });
    });

    var lista = el('div', { class: 'tema-indice' });

    tema.secoes.forEach(function (s, i) {
      var lida = lidas.indexOf(i) > -1;
      var item = el('button', {
        class: 'indice-item' + (lida ? ' lida' : ''),
        type: 'button'
      }, [
        el('span', { class: 'indice-num', text: String(i + 1) }),
        el('span', { class: 'indice-titulo', text: s.titulo }),
        // Estado em texto, não só em cor: interface de emergência não pode
        // depender de cor para ser entendida.
        el('span', { class: 'indice-estado', text: lida ? 'lida' : '' })
      ]);
      item.onclick = function () { ir(base + '/s/' + (i + 1)); };
      lista.appendChild(item);
    });

    [
      { rota: '/pensar', titulo: 'Para pensar', nota: tema.reflexoes.length + ' reflexões' },
      { rota: '/fontes', titulo: 'Fontes', nota: tema.fontes.length + ' obras' },
      { rota: '/quiz', titulo: 'Quiz', nota: tema.quiz.length + ' questões' }
    ].forEach(function (extra) {
      var item = el('button', { class: 'indice-item extra', type: 'button' }, [
        el('span', { class: 'indice-titulo', text: extra.titulo }),
        el('span', { class: 'indice-estado', text: extra.nota })
      ]);
      item.onclick = function () { ir(base + extra.rota); };
      lista.appendChild(item);
    });

    tela.appendChild(lista);
  }

  // Rodapé de encadeamento. É o toque aqui que marca a Seção como lida —
  // rastrear rolagem daria selo a quem só espiou, e nunca dispararia numa
  // Seção mais curta que a tela.
  function encadear(tema, passo) {
    var prox = proximoPasso(tema, passo);
    if (!prox) return null;
    var b = el('button', { class: 'btn encadeia', type: 'button', text: prox.rotulo });
    b.onclick = function () {
      if (passo.tipo === 'secao') marcarLida(tema.id, passo.i);
      ir(prox.rota);
    };
    return el('div', { class: 'btn-row encadeia-row' }, [b]);
  }

  function renderSecao(tema, i) {
    var s = tema.secoes[i];
    cabecalho(s.titulo, tema.titulo + ' · ' + (i + 1) + ' de ' + tema.secoes.length,
              true, '#/estudar/' + tema.id);
    document.body.classList.add('lendo');
    var bloco = montarSecao(s);
    if (bloco) {
      bloco.style.setProperty('--i', 0);
      // O título da Seção já é o título grande da tela; repetir o h2 aqui
      // duplicaria a informação no topo do conteúdo.
      var h2 = bloco.querySelector('h2');
      if (h2) bloco.removeChild(h2);
      tela.appendChild(bloco);
    }
    var rodape = encadear(tema, { tipo: 'secao', i: i });
    if (rodape) tela.appendChild(rodape);
  }

  function renderPensar(tema) {
    cabecalho('Para pensar', tema.titulo, true, '#/estudar/' + tema.id);
    var sec = el('section', { class: 'secao reflexoes' });
    tema.reflexoes.forEach(function (r) {
      sec.appendChild(
        el('div', { class: 'reflexao' }, [
          el('span', { class: 'tag', text: 'Reflexão' }),
          el('p', { text: r })
        ])
      );
    });
    sec.appendChild(
      el('p', {
        class: 'reflexao-aviso',
        text: 'Estas não têm resposta certa e não entram no quiz.'
      })
    );
    tela.appendChild(sec);
    var rodape = encadear(tema, { tipo: 'pensar' });
    if (rodape) tela.appendChild(rodape);
  }

  function renderFontes(tema) {
    cabecalho('Fontes', tema.titulo, true, '#/estudar/' + tema.id);
    tela.appendChild(montarFontes(tema));
  }

  function renderQuizTela(tema) {
    cabecalho('Quiz', tema.titulo, true, '#/estudar/' + tema.id);
    tela.appendChild(montarQuiz(tema));
  }
```

- [ ] **Step 8: Terceiro destino na tela de resultado**

Em `montarQuiz`, dentro de `resultado()`, acrescente antes de `voltarTrilha`:

```js
      var voltarTema = el('button', { class: 'btn', type: 'button', text: 'Voltar ao tema' });
      voltarTema.onclick = function () { ir('#/estudar/' + tema.id); };
```

e troque a última linha da função por:

```js
      raiz.appendChild(el('div', { class: 'btn-row' }, [voltarTema, voltarTrilha, refazer]));
```

A ordem importa: o teste clica em `.btn-row .btn[2]` para refazer.

- [ ] **Step 9: Rodar e confirmar que passa**

Esperado: **0 FALHA**. O total sobe bastante (as Seções passam a ser
verificadas uma a uma).

- [ ] **Step 10: Commit**

```bash
git add app/app.js tests/app_smoke.html
git commit -m "feat(app): percurso do Tema com indice, Secao por tela e quiz como destino"
```

---

## Task 3: O CSS do índice e do encadeamento

**Files:**
- Modify: `app/styles.css`
- Test: `tests/app_smoke.html`

**Interfaces:**
- Consumes: as classes que a Task 2 emite — `.tema-indice`, `.indice-item`,
  `.indice-item.lida`, `.indice-item.extra`, `.indice-num`, `.indice-titulo`,
  `.indice-estado`, `.encadeia-row`.

- [ ] **Step 1: Escrever a asserção que falha**

Em `tests/app_smoke.html`, dentro de `percorre`, logo depois da asserção
`indice lista as ... secoes`, insira:

```js
  // Alvo de toque: o brief exige 44px mínimos, e isto é interface de emergência.
  var itens = document.querySelectorAll('.indice-item');
  var baixos = 0;
  for (var k = 0; k < itens.length; k++) if (itens[k].offsetHeight < 44) baixos++;
  ok(baixos === 0, nome + 'todo item do indice tem ao menos 44px de altura');
```

- [ ] **Step 2: Rodar e confirmar que falha**

Esperado: FALHA — sem CSS, os botões medem menos de 44px.

- [ ] **Step 3: Escrever o CSS**

Em `app/styles.css`, antes do bloco `/* ---------- seções do Tema ---------- */`:

```css
/* ---------- índice do Tema ---------- */
.tema-indice { display: grid; gap: 8px; margin-top: 4px; }

.indice-item {
  appearance: none;
  font: inherit;
  color: inherit;
  text-align: left;
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  padding: 12px 14px;
  min-height: 52px;
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 12px;
  box-shadow: var(--sombra-1);
  transition: transform .16s var(--ease), border-color .16s var(--ease);
  animation: surge .3s var(--ease) both;
}
.indice-item:hover { border-color: var(--border-forte); transform: translateX(2px); }
.indice-item:active { transform: scale(.995); }

.indice-num {
  flex: 0 0 auto;
  width: 26px; height: 26px;
  border-radius: 50%;
  background: var(--surface-3);
  color: var(--text-dim);
  display: grid; place-items: center;
  font-size: .8rem; font-weight: 720;
  font-variant-numeric: tabular-nums;
}
.indice-titulo { flex: 1 1 auto; font-weight: 600; letter-spacing: -0.01em; }
.indice-estado {
  flex: 0 0 auto;
  font-size: .72rem;
  color: var(--text-dim);
  text-transform: uppercase;
  letter-spacing: .07em;
  font-weight: 750;
}

/* Lida: marca, borda e rótulo textual. Nunca só a cor — o brief proíbe
   depender de cor, e vale em cima de tudo numa interface de emergência. */
.indice-item.lida { border-color: color-mix(in srgb, var(--accent) 45%, var(--border)); }
.indice-item.lida .indice-num {
  background: var(--accent);
  color: var(--accent-text);
  font-size: 0;              /* esconde o número que o JS emite */
}
.indice-item.lida .indice-num::after { content: "✓"; font-size: .85rem; }
.indice-item.lida .indice-estado { color: var(--accent-forte); }

.indice-item.extra { background: var(--surface-2); }
.indice-item.extra .indice-titulo { font-weight: 660; }

/* ---------- rodapé de encadeamento ---------- */
.encadeia-row {
  margin-top: 28px;
  padding-top: 20px;
  border-top: 1px solid var(--border);
}
.encadeia { width: 100%; justify-content: center; }
```

O número da Seção lida dá lugar à marca: `font-size: 0` apaga o texto que o JS
emitiu e o `::after` devolve o tamanho para o `✓`. É determinístico — não depende
de um pseudo-elemento cobrir o texto por sorte de empilhamento.

- [ ] **Step 4: Rodar e confirmar que passa**

Esperado: **0 FALHA**.

- [ ] **Step 5: Conferir a olho, tema claro e escuro**

```sh
google-chrome --headless=new --no-sandbox --hide-scrollbars --window-size=390,844 \
  --screenshot=/tmp/vand-indice.png --virtual-time-budget=6000 \
  "http://localhost:8791/app/index.html#/estudar/quando-a-chuva-vira-enchente"
google-chrome --headless=new --no-sandbox --hide-scrollbars --window-size=390,844 \
  --force-dark-mode --screenshot=/tmp/vand-indice-escuro.png --virtual-time-budget=6000 \
  "http://localhost:8791/app/index.html#/estudar/quando-a-chuva-vira-enchente"
```

**Abra as duas imagens** e confirme: os 6 itens de Seção mais os 3 extras; o ✓
sem número duplicado; contraste legível nos dois temas; nenhum item cortado.

- [ ] **Step 6: Commit**

```bash
git add app/styles.css tests/app_smoke.html
git commit -m "feat(app): estilo do indice do Tema e do rodape de encadeamento"
```

---

## Task 4: Service worker e verificação final

**Files:**
- Modify: `app/sw.js`

- [ ] **Step 1: Incrementar a versão**

Em `app/sw.js`, `VERSAO` está em `vand-v7`. Passe para `vand-v8`. Nenhum arquivo
novo entra no precache — este plano não cria arquivo.

- [ ] **Step 2: Verificação de ponta a ponta**

```sh
# teste de fumaça
<comando da seção "Como rodar o teste">
# nenhum host externo
grep -rn "fonts.googleapis\|cdn.tailwindcss\|https://" app/ --include=*.html --include=*.css --include=*.js
# o conteúdo não foi tocado
git diff --stat app/content.js
```

Esperado: 0 FALHA; nenhuma ocorrência de host externo; `app/content.js` sem
nenhuma linha alterada.

- [ ] **Step 3: Percorrer as telas novas a olho**

Capture e **abra** as cinco: índice, uma Seção, Para pensar, Fontes e Quiz.

```sh
for r in "" "/s/1" "/pensar" "/fontes" "/quiz"; do
  n=$(echo "$r" | tr -d '/' ); n=${n:-indice}
  google-chrome --headless=new --no-sandbox --hide-scrollbars --window-size=390,844 \
    --screenshot=/tmp/vand-tema-$n.png --virtual-time-budget=6000 \
    "http://localhost:8791/app/index.html#/estudar/quando-a-chuva-vira-enchente$r"
done
```

Confirme na Seção que o título não aparece duas vezes (uma como título grande e
outra como `h2` do bloco) e que o botão de encadeamento diz "Próxima seção".

- [ ] **Step 4: Medir que o problema foi resolvido**

A spec abre com a medição que motivou o trabalho. Refaça-a para a Seção mais
longa e registre o número no relatório: a altura precisa cair de ~12 telas para
algo em torno de 1 a 2.

- [ ] **Step 5: Matar o servidor e commitar**

```bash
pkill -f "http.server 8791"
git add app/sw.js
git commit -m "chore(app): sw v8 para o percurso do Tema"
```

---

## Fora de escopo

Não implemente, mesmo que pareça natural: tela de fecho entre leitura e quiz,
questões distribuídas pelo texto, trava de sequência, marcar Tema como concluído
por leitura, busca dentro do Tema, favoritar Seção, anotações, ou qualquer
contagem além do resultado do quiz. Ver a seção "Fora de escopo" da spec.

Também **não** resolva a inconsistência "questão" × "Item" do `CONTEXT.md`: é
decisão editorial pendente, registrada na spec.
