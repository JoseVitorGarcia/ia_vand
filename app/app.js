/*
 * Protótipo navegável do VAND. Sem back-end e sem contas: o progresso vive no
 * localStorage do próprio navegador (ver ESTADO.md / desenho da aplicação).
 *
 * Vocabulário: Trilha, Tema, Nível, Item, Reflexão, Fonte. Ver CONTEXT.md.
 */
(function () {
  'use strict';

  var TRILHA = (window.VAND_CONTENT && window.VAND_CONTENT.trilha) || [];
  var CHAVE = 'vand.progresso.v1';

  var tela = document.getElementById('tela');
  var titulo = document.getElementById('titulo');
  var subtitulo = document.getElementById('subtitulo');
  var voltar = document.getElementById('voltar');
  var abas = Array.prototype.slice.call(document.querySelectorAll('.tabbar button'));

  // ---------- progresso ----------

  function lerProgresso() {
    try {
      return JSON.parse(localStorage.getItem(CHAVE)) || {};
    } catch (e) {
      return {};
    }
  }

  function gravarProgresso(p) {
    try {
      localStorage.setItem(CHAVE, JSON.stringify(p));
    } catch (e) {
      /* navegador em modo restrito: o app segue funcionando sem lembrar. */
    }
  }

  function registrarResultado(temaId, acertos, total) {
    var p = lerProgresso();
    var anterior = p[temaId];
    // Guarda o melhor resultado: refazer o quiz nunca piora o que já foi conquistado.
    if (!anterior || acertos > anterior.acertos) {
      p[temaId] = { acertos: acertos, total: total, em: new Date().toISOString() };
      gravarProgresso(p);
    }
  }

  // ---------- utilidades ----------

  function el(tag, attrs, filhos) {
    var n = document.createElement(tag);
    if (attrs) {
      Object.keys(attrs).forEach(function (k) {
        if (k === 'class') n.className = attrs[k];
        else if (k === 'text') n.textContent = attrs[k];
        else if (attrs[k] !== null && attrs[k] !== false) n.setAttribute(k, attrs[k]);
      });
    }
    (filhos || []).forEach(function (f) { if (f) n.appendChild(f); });
    return n;
  }

  function limpar() { while (tela.firstChild) tela.removeChild(tela.firstChild); }

  function escrito(tema) { return tema.secoes.length > 0 && tema.quiz.length > 0; }

  // ---------- roteamento ----------
  // Hash: #/estudar | #/estudar/<temaId> | #/alerta | #/registro

  function rota() {
    var h = (location.hash || '#/estudar').replace(/^#\/?/, '');
    var partes = h.split('/').filter(Boolean);
    return { aba: partes[0] || 'estudar', temaId: partes[1] || null };
  }

  function ir(hash) { location.hash = hash; }

  function render() {
    var r = rota();
    limpar();
    voltar.hidden = true;
    document.body.classList.remove('lendo');

    abas.forEach(function (b) {
      if (b.dataset.aba === r.aba) b.setAttribute('aria-current', 'page');
      else b.removeAttribute('aria-current');
    });

    if (r.aba === 'estudar') {
      var tema = r.temaId && TRILHA.filter(function (t) { return t.id === r.temaId; })[0];
      if (tema) renderTema(tema);
      else renderTrilha();
    } else if (r.aba === 'alerta') {
      renderVazia(
        'Alerta',
        'Aviso oficial do INMET',
        'Retransmissão do aviso do INMET para a sua região.',
        'Ainda não construída. O dado já existe — 5.958 avisos colhidos e o casamento ' +
          'entre estação e aviso testado —, mas a tela não. Ela aparece aqui vazia de ' +
          'propósito: nada de simulação que pareça real.',
        '◈'
      );
    } else if (r.aba === 'registro') {
      renderVazia(
        'Registro',
        'Registro de alagamento',
        'Enviar se a sua rua está alagada, ou se não está.',
        'Ainda não construída. Quando existir, ela vai perguntar ativamente — "está ' +
          'alagado aí? sim / não / não sei" —, porque o "não" é o dado mais valioso e o ' +
          'mais fácil de esquecer de coletar.',
        '◉'
      );
    } else {
      ir('#/estudar');
      return;
    }

    try { window.scrollTo({ top: 0, behavior: 'instant' }); }
    catch (e) { window.scrollTo(0, 0); }
    tela.focus({ preventScroll: true });
  }

  // ---------- telas ----------

  function cabecalho(t, s, mostrarVoltar, alvoVoltar) {
    titulo.innerHTML = '';
    titulo.appendChild(document.createTextNode(t));
    var sub = el('span', { class: 'sub', text: s });
    sub.id = 'subtitulo';
    titulo.appendChild(sub);
    subtitulo = sub;
    voltar.hidden = !mostrarVoltar;
    voltar.onclick = function () { ir(alvoVoltar || '#/estudar'); };
  }

  function renderVazia(abaNome, h, sub, corpo, icone) {
    cabecalho(abaNome, sub, false);
    tela.appendChild(
      el('div', { class: 'vazia' }, [
        el('div', { class: 'emblema', 'aria-hidden': 'true', text: icone || '◇' }),
        el('h2', { text: h }),
        el('p', { text: corpo })
      ])
    );
  }

  function renderTrilha() {
    cabecalho('Estudar', 'Trilha de clima e água', false);
    var p = lerProgresso();
    var prontos = TRILHA.filter(escrito);
    var feitos = prontos.filter(function (t) { return p[t.id]; }).length;

    // A marca só aparece aqui, na abertura — nunca no cabeçalho fixo.
    // Ver docs/adr/0003 e o brief: o ponto vermelho não pode conviver com um
    // chip de Severidade no topo de todas as telas.
    tela.appendChild(
      el('div', { class: 'hero' }, [
        el('div', { class: 'marca', role: 'img', 'aria-label': 'VAND' }),
        el('p', {
          text:
            'Três temas, do básico ao avançado, escritos a partir de material oficial do ' +
            'governo. Cada um termina num quiz de cinco questões. Comece por onde quiser.'
        })
      ])
    );

    if (prontos.length) {
      var pct = Math.round((feitos / prontos.length) * 100);
      var enchimento = el('i');
      var painel = el('div', { class: 'painel' }, [
        el('span', { class: 'rotulo' }, [
          el('strong', { text: feitos + ' de ' + prontos.length }),
          document.createTextNode(feitos === 1 ? ' tema concluído' : ' temas concluídos')
        ]),
        el('div', {
          class: 'barra',
          role: 'progressbar',
          'aria-valuenow': String(feitos),
          'aria-valuemin': '0',
          'aria-valuemax': String(prontos.length)
        }, [enchimento])
      ]);
      tela.appendChild(painel);
      // Num quadro seguinte, para a barra animar de zero até o valor.
      requestAnimationFrame(function () {
        requestAnimationFrame(function () { enchimento.style.setProperty('--pct', pct + '%'); });
      });
    }

    TRILHA.forEach(function (tema, indice) {
      var pronto = escrito(tema);
      var feito = p[tema.id];

      var meta = el('div', { class: 'meta' }, [
        el('span', { text: tema.minutos + ' min de leitura' })
      ]);
      if (!pronto) {
        meta.appendChild(el('span', { class: 'selo-vazio', text: 'conteúdo em redação' }));
      } else if (feito) {
        meta.appendChild(
          el('span', {
            class: 'selo-feito',
            text: 'quiz: ' + feito.acertos + ' de ' + feito.total
          })
        );
      } else {
        meta.appendChild(el('span', { text: tema.quiz.length + ' questões' }));
      }

      var card = el(
        'button',
        { class: 'tema-card', type: 'button', disabled: pronto ? false : 'disabled' },
        [
          el('div', { class: 'tema-head' }, [
            el('span', { class: 'nivel', text: tema.nivel }),
            el('h2', { text: tema.titulo })
          ]),
          el('p', { text: tema.resumo }),
          meta
        ]
      );
      card.style.setProperty('--i', indice);
      if (pronto) {
        card.onclick = function () { ir('#/estudar/' + tema.id); };
      }
      tela.appendChild(card);
    });
  }

  function renderTema(tema) {
    cabecalho(tema.titulo, tema.nivel + ' · ' + tema.minutos + ' min', true, '#/estudar');
    document.body.classList.add('lendo');

    tema.secoes.forEach(function (s, indice) {
      if (s.tipo === 'texto') {
        var bloco = el('section', { class: 'secao' }, [el('h2', { text: s.titulo })]);
        s.paragrafos.forEach(function (par) { bloco.appendChild(el('p', { text: par })); });
        tela.appendChild(bloco);
      } else if (s.tipo === 'destaque') {
        tela.appendChild(
          el('section', { class: 'secao destaque' }, [
            el('h2', { text: s.titulo }),
            el('p', { text: s.texto })
          ])
        );
      } else if (s.tipo === 'glossario') {
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
        tela.appendChild(glo);
      } else if (s.tipo === 'dados') {
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
        tela.appendChild(sec);
      }
    });

    Array.prototype.forEach.call(tela.querySelectorAll('.secao'), function (n, i) {
      n.style.setProperty('--i', i);
    });

    if (tema.reflexoes.length) {
      var refSec = el('section', { class: 'secao reflexoes' }, [el('h2', { text: 'Para pensar' })]);
      tema.reflexoes.forEach(function (r) {
        refSec.appendChild(
          el('div', { class: 'reflexao' }, [
            el('span', { class: 'tag', text: 'Reflexão' }),
            el('p', { text: r })
          ])
        );
      });
      refSec.appendChild(
        el('p', {
          class: 'reflexao-aviso',
          text: 'Estas não têm resposta certa e não entram no quiz.'
        })
      );
      tela.appendChild(refSec);
    }

    tela.appendChild(montarQuiz(tema));
    tela.appendChild(montarFontes(tema));
  }

  function montarFontes(tema) {
    var lista = el('ul');
    tema.fontes.forEach(function (f) {
      lista.appendChild(
        el('li', { text: f.obra + '. ' + f.orgao + ', ' + f.ano + '. ' + f.detalhe + '.' })
      );
    });
    return el('section', { class: 'fontes' }, [
      el('h2', { text: 'Fontes' }),
      lista,
      el('p', {
        class: 'aviso-redacao',
        text:
          'O texto acima é de redação própria, escrito a partir das obras citadas. ' +
          'Nenhum trecho foi reproduzido delas.'
      })
    ]);
  }

  // ---------- quiz ----------

  function montarQuiz(tema) {
    var raiz = el('section', { class: 'quiz' });
    var indice = 0;
    var acertos = 0;

    function pergunta() {
      while (raiz.firstChild) raiz.removeChild(raiz.firstChild);

      if (indice >= tema.quiz.length) {
        registrarResultado(tema.id, acertos, tema.quiz.length);
        resultado();
        return;
      }

      var item = tema.quiz[indice];
      var trilhoQuiz = el('i');
      trilhoQuiz.style.setProperty('--pct', Math.round((indice / tema.quiz.length) * 100) + '%');
      raiz.appendChild(
        el('p', { class: 'quiz-prog' }, [
          el('span', { text: 'Questão ' + (indice + 1) + ' de ' + tema.quiz.length }),
          el('span', {
            class: 'barra',
            role: 'progressbar',
            'aria-valuenow': String(indice),
            'aria-valuemin': '0',
            'aria-valuemax': String(tema.quiz.length)
          }, [trilhoQuiz])
        ])
      );
      raiz.appendChild(el('h2', { text: item.enunciado }));

      var alts = el('div', { class: 'alts' });
      var botoes = [];
      item.alternativas.forEach(function (texto, i) {
        var b = el('button', { class: 'alt', type: 'button' }, [
          el('span', { class: 'letra', text: 'ABCD'[i] }),
          el('span', { text: texto })
        ]);
        b.style.setProperty('--i', i);
        b.onclick = function () { responder(i, item, botoes); };
        botoes.push(b);
        alts.appendChild(b);
      });
      raiz.appendChild(alts);
      raiz.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }

    function responder(escolha, item, botoes) {
      var certo = escolha === item.correta;
      if (certo) acertos++;

      botoes.forEach(function (b, i) {
        b.onclick = null;
        b.setAttribute('aria-disabled', 'true');
        if (i === item.correta) b.classList.add('certa');
        else if (i === escolha) b.classList.add('errada');
      });

      var trilho = raiz.querySelector('.quiz-prog .barra i');
      if (trilho) {
        trilho.style.setProperty('--pct', Math.round(((indice + 1) / tema.quiz.length) * 100) + '%');
      }

      raiz.appendChild(
        el('div', { class: 'explica ' + (certo ? 'certa' : 'errada'), role: 'status', 'aria-live': 'polite' }, [
          el('strong', { text: certo ? 'Isso mesmo.' : 'Não é essa.' }),
          el('span', { text: item.explicacao })
        ])
      );

      var seguinte = el('button', {
        class: 'btn',
        type: 'button',
        text: indice + 1 < tema.quiz.length ? 'Próxima questão' : 'Ver resultado'
      });
      seguinte.onclick = function () { indice++; pergunta(); };
      raiz.appendChild(el('div', { class: 'btn-row' }, [seguinte]));
    }

    function resultado() {
      var refazer = el('button', { class: 'btn ghost', type: 'button', text: 'Refazer o quiz' });
      refazer.onclick = function () { indice = 0; acertos = 0; pergunta(); };

      var voltarTrilha = el('button', { class: 'btn', type: 'button', text: 'Voltar à trilha' });
      voltarTrilha.onclick = function () { ir('#/estudar'); };

      raiz.appendChild(
        el('div', { class: 'resultado' }, [
          el('div', { class: 'score', text: acertos + '/' + tema.quiz.length }),
          el('p', {
            text:
              acertos === tema.quiz.length
                ? 'Todas certas. Pode seguir para o próximo tema.'
                : 'Refazer é livre — nada aqui trava o próximo tema.'
          })
        ])
      );
      raiz.appendChild(el('div', { class: 'btn-row' }, [voltarTrilha, refazer]));
    }

    pergunta();
    return raiz;
  }

  // ---------- início ----------

  abas.forEach(function (b) {
    b.onclick = function () { ir('#/' + b.dataset.aba); };
  });

  // Sombra da topbar só depois que a página sai do topo.
  var topbar = document.querySelector('.topbar');
  if (topbar) {
    var marcarRolagem = function () {
      topbar.classList.toggle('rolado', window.scrollY > 4);
    };
    window.addEventListener('scroll', marcarRolagem, { passive: true });
    marcarRolagem();
  }

  window.addEventListener('hashchange', render);
  render();

  if ('serviceWorker' in navigator && location.protocol.indexOf('http') === 0) {
    window.addEventListener('load', function () {
      navigator.serviceWorker.register('sw.js').catch(function () {});
    });
  }
})();
