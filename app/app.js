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
  var conteudo = document.getElementById('conteudo');
  var topbarTitulo = document.getElementById('topbar-titulo');
  var progressoLeitura = document.getElementById('progresso-leitura');
  var app = document.querySelector('.app');
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
    grafico:  'M4 20V10h4v10H4zm6 0V4h4v16h-4zm6 0v-7h4v7h-4z',
    recarregar: 'M17.65 6.35A7.96 7.96 0 0012 4a8 8 0 108 8h-2a6 6 0 11-6-6c1.66 0 3.14.69 4.22 1.78L13 11h7V4l-2.35 2.35z'
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
    p.setAttribute('fill-rule', 'evenodd');
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

  // A tela de um Tema sempre abre no topo — ninguém quer reabrir um texto no
  // meio — e por isso não entra na memória de posição por aba.
  function ehTema(hash) {
    var h = (hash || '').replace(/^#\/?/, '');
    var partes = h.split('/').filter(Boolean);
    return partes[0] === 'estudar' && !!partes[1];
  }

  var posicoes = {};
  var rotaAnterior = null;

  function render() {
    var r = rota();

    if (rotaAnterior && !ehTema(rotaAnterior)) posicoes[rotaAnterior] = conteudo.scrollTop;

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
      renderAlerta(r.temaId === 'calmo');
    } else if (r.aba === 'registro') {
      renderRegistro(r.temaId === 'enviado');
    } else {
      ir('#/estudar');
      return;
    }

    var tg = tela.querySelector('.tela-titulo');
    // O -12 faz o título do cabeçalho aparecer um instante antes de o grande
    // sumir por completo, senão há um quadro em que nenhum dos dois aparece.
    limiarColapso = tg ? tg.offsetHeight - 12 : 0;

    var r0 = location.hash;
    conteudo.scrollTop = ehTema(r0) ? 0 : (posicoes[r0] || 0);
    rotaAnterior = r0;

    conteudo.focus({ preventScroll: true });
    aoRolar();
  }

  // ---------- rolagem e cabeçalho colapsável ----------

  var limiarColapso = 0;

  function aoRolar() {
    var y = conteudo.scrollTop;
    app.classList.toggle('compacto', y > limiarColapso);

    // Barra de leitura: fração do Tema já percorrida.
    if (document.body.classList.contains('lendo')) {
      var alcance = conteudo.scrollHeight - conteudo.clientHeight;
      var lido = alcance > 0 ? Math.min(1, y / alcance) : 0;
      progressoLeitura.style.setProperty('--lido', lido.toFixed(4));
    }
  }

  conteudo.addEventListener('scroll', aoRolar, { passive: true });

  // ---------- telas ----------

  function cabecalho(t, s, mostrarVoltar, alvoVoltar) {
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


  function renderTrilha() {
    cabecalho('Estudar', 'Trilha de clima e água', false);
    var p = lerProgresso();
    var prontos = TRILHA.filter(escrito);
    var feitos = prontos.filter(function (t) { return quizFeito(p[t.id]); }).length;

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
        el('h2', { text: 'Seu Progresso' }),
        el('div', { class: 'fracao' }, [
          el('span', { text: feitos + '/' + prontos.length }),
          el('div', { class: 'barra', role: 'progressbar', 'aria-valuenow': String(feitos), 'aria-valuemin': '0', 'aria-valuemax': String(prontos.length) }, [enchimento])
        ]),
        el('p', { class: 'apoio', text: 'Complete os três temas para dominar o essencial.' })
      ]);
      tela.appendChild(painel);
      // Num quadro seguinte, para a barra animar de zero até o valor.
      requestAnimationFrame(function () {
        requestAnimationFrame(function () { enchimento.style.setProperty('--pct', pct + '%'); });
      });
    }

    // Rótulo de seção: "Trilhas de conhecimento".
    tela.appendChild(el('h3', { class: 't-caps', text: 'Trilhas de conhecimento' }));

    TRILHA.forEach(function (tema, indice) {
      var pronto = escrito(tema);
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

      var nomesIcones = ['gota', 'calmo', 'grafico'];
      var traco = indice === 1;  // O ícone "calmo" usa traço
      var iconeCard = el('div', { class: 'tema-icone' }, [icone(nomesIcones[indice] || 'gota', 24, traco)]);

      var card = el(
        'button',
        { class: 'tema-card', type: 'button', disabled: pronto ? false : 'disabled' },
        [
          el('div', { class: 'tema-head' }, [
            el('span', { class: 'nivel', text: tema.nivel }),
            el('h2', { text: tema.titulo })
          ]),
          iconeCard,
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

  // ---------- aba Alerta ----------

  function renderAlerta(calmo) {
    cabecalho('Alerta', 'Aviso oficial do INMET', false);

    var dados = window.VAND_DADOS;
    if (!dados) return;

    // O dado já traz "Porto Alegre - RS"; formata com vírgula e não anexa nada.
    var municipio = (dados.aviso.municipio_exemplo || 'Porto Alegre, RS').replace(' - ', ', ');

    // Município e consulta, como subtítulo de contexto logo abaixo do título
    // grande "Alerta" (que cabecalho() já inseriu no topo do #tela).
    var cabecAlerta = el('div', { class: 'alerta-cabec' }, [
      el('h2', { class: 't-h2', text: municipio }),
      el('div', { class: 'alerta-consulta' }, [
        el('span', { class: 't-caps alerta-consulta-rotulo', text: 'ÚLTIMA CONSULTA: AGORA MESMO' }),
        el('button', { type: 'button', class: 'btn-circular', 'aria-label': 'Consultar de novo' }, [icone('recarregar', 20)])
      ])
    ]);
    tela.appendChild(cabecAlerta);

    if (calmo) {
      // Estado sem Aviso.
      var cardCalmo = el('div', { class: 'card-calmo' }, [
        el('div', { class: 'card-calmo-icone' }, [icone('calmo', 24, true)]),
        el('h2', { text: 'Nenhum Aviso vigente' }),
        el('p', { text: 'Não há Aviso do INMET em vigor para a sua região agora. Isto não é previsão de tempo bom — é a ausência de aviso, conferida neste momento.' }),
        el('a', { href: '#/alerta', class: 'link-exemplo', text: 'Ver um exemplo de Aviso vigente' })
      ]);
      tela.appendChild(cardCalmo);
    } else {
      // Estado com Aviso vigente.
      var aviso = dados.aviso;
      var avisoCard = el('div', { class: 'aviso-card', style: '--sev: ' + aviso.aviso_cor + ';' }, [
        el('div', { class: 'aviso-corpo' }, [
          el('div', { class: 'sev-chip', style: '--sev: ' + aviso.aviso_cor + ';' }, [
            icone('aviso', 18),
            el('span', { text: aviso.severidade || 'Grande Perigo' })
          ]),
          el('h2', { text: aviso.descricao || 'Acumulado de Chuva' }),
          el('div', { class: 'aviso-vigencia' }, [
            icone('relogio', 18),
            el('span', { text: 'Válido de ' + formatData(aviso.inicio) + ' até ' + formatData(aviso.fim) })
          ]),
          el('div', { class: 'aviso-bloco' }, [
            el('span', { class: 'rotulo', text: 'Instruções Oficiais' }),
            el('ul', {}, (aviso.instrucoes || []).map(function (instr) { return el('li', {}, textoComTelefones(instr)); }))
          ]),
          el('div', { class: 'aviso-bloco' }, [
            el('span', { class: 'rotulo', text: 'Riscos' }),
            el('ul', {}, (aviso.riscos || []).map(function (risco) { return el('li', { text: risco }); }))
          ]),
          el('div', { class: 'aviso-rodape', text: 'AVISO DO INMET PARA ' + aviso.municipios_total + ' MUNICÍPIOS · ID ' + aviso.id })
        ])
      ]);
      tela.appendChild(avisoCard);

      // Card de Previsão.
      var previsaoCard = el('div', { class: 'previsao-card' }, [
        el('div', { class: 'rotulo' }, [
          icone('grafico', 18),
          el('span', { text: 'Previsão VAND' })
        ]),
        el('p', { text: 'A nossa Previsão indica risco de chuva acima de 30 mm para a sua região.' }),
        el('div', { class: 'previsao-stat' }, [
          el('div', { class: 'previsao-linha' }, [
            el('span', { class: 'label', text: 'Taxa de confirmação' }),
            el('span', { class: 'valor', text: fmtPct(dados.previsao.taxa_confirmacao, 0) })
          ]),
          el('div', { class: 'barra' }, [
            el('i', { style: 'width: ' + fmtPct(dados.previsao.taxa_confirmacao, 0) + ';' })
          ]),
          el('p', { class: 'nota', text: 'Cerca de 3 em cada 10 Previsões nossas se confirmam na estação, e essa regra captura 71% dos eventos. Taxa de confirmação não é taxa de acerto: uma Previsão não confirmada não é um erro, é risco que existia e não se materializou. É por isso que a nossa Previsão não dispara notificação.' })
        ])
      ]);
      tela.appendChild(previsaoCard);

      // Card de Lacuna. Os números saem todos de VAND_DADOS.lacuna — nenhum é
      // literal aqui, senão o texto para de acompanhar a medição quando ela mudar.
      var lac = dados.lacuna;
      var lacunaCard = el('div', { class: 'lacuna-card' }, [
        el('span', { class: 'rotulo', text: 'Por que "para a sua região"' }),
        el('p', {
          text:
            'Este Aviso cobre ' + aviso.municipios_total + ' municípios. Entre os Avisos de ' +
            lac.severidade + ', ' + fmtPct(lac.taxa_area, 0) + ' se confirmam em algum ponto da ' +
            'área coberta e ' + fmtPct(lac.taxa_ponto, 1) + ' se confirmam na estação de quem foi ' +
            'avisado — uma razão de ' + fmtNum(lac.razao, 0) + ' vezes. O Aviso é produto de área ' +
            'recebido num ponto; a diferença é de granularidade, não de qualidade de quem prevê.'
        })
      ]);
      tela.appendChild(lacunaCard);
    }
  }

  // Número em português: vírgula decimal, e sem casa nenhuma quando casas = 0.
  // Nome com prefixo para não colidir com o `var pct` local de renderTrilha.
  function fmtNum(v, casas) {
    return v.toFixed(casas || 0).replace('.', ',');
  }

  function fmtPct(fracao, casas) {
    return fmtNum(fracao * 100, casas) + '%';
  }

  function formatData(iso) {
    if (!iso) return '';
    var d = new Date(iso);
    var fmt = new Intl.DateTimeFormat('pt-BR', { month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' });
    var partes = fmt.formatToParts(d);
    var dia = '', mes = '', hora = '', min = '';
    partes.forEach(function (p) {
      if (p.type === 'day') dia = p.value;
      else if (p.type === 'month') mes = p.value;
      else if (p.type === 'hour') hora = p.value;
      else if (p.type === 'minute') min = p.value;
    });
    return dia + '/' + mes + ' às ' + hora + ':' + min;
  }

  // Numa tela de emergência, o telefone da Defesa Civil/Corpo de Bombeiros
  // precisa ser tocável. Quebra o texto em nós — nunca monta HTML por
  // concatenação de string — e troca cada "telefone NNN" por um link tel:.
  function textoComTelefones(texto) {
    var partes = [];
    var re = /telefone (\d{3})/g;
    var ultimo = 0;
    var m;
    while ((m = re.exec(texto))) {
      if (m.index > ultimo) partes.push(document.createTextNode(texto.slice(ultimo, m.index)));
      partes.push(document.createTextNode('telefone '));
      var a = document.createElement('a');
      a.href = 'tel:' + m[1];
      a.textContent = m[1];
      partes.push(a);
      ultimo = re.lastIndex;
    }
    if (ultimo < texto.length) partes.push(document.createTextNode(texto.slice(ultimo)));
    return partes;
  }

  var respostaRegistro = null;

  // ---------- aba Registro ----------

  function renderRegistro(enviado) {
    cabecalho('Registro', 'Registro de alagamento', false);

    if (enviado) {
      // Tela de confirmação.
      var dados = window.VAND_DADOS;
      var agora = new Date();
      var fmt = new Intl.DateTimeFormat('pt-BR', { year: 'numeric', month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' });
      var horaAgora = fmt.format(agora);

      var recibo = el('div', { class: 'registro-recibo' }, [
        el('h2', { text: 'Registro enviado' }),
        el('div', { class: 'pares' }, [
          el('div', { class: 'par' }, [
            el('span', { class: 'label', text: 'Resposta' }),
            el('span', { class: 'valor', text: respostaRegistro || 'Não respondido' })
          ]),
          el('div', { class: 'par' }, [
            el('span', { class: 'label', text: 'Local' }),
            el('span', {
              class: 'valor',
              text: (dados && dados.aviso && dados.aviso.municipio_exemplo)
                ? dados.aviso.municipio_exemplo.replace(' - ', ', ')
                : 'Porto Alegre, RS'
            })
          ]),
          el('div', { class: 'par' }, [
            el('span', { class: 'label', text: 'Horário' }),
            el('span', { class: 'valor', text: horaAgora })
          ]),
          dados && dados.aviso ? el('div', { class: 'par' }, [
            el('span', { class: 'label', text: 'Aviso vigente' }),
            el('span', { class: 'valor', text: (dados.aviso.descricao || 'Acumulado de Chuva') + ' — ' + (dados.aviso.severidade || 'Grande Perigo') })
          ]) : null
        ]),
        el('p', { class: 'nota', text: 'É a amarração com o Aviso vigente que torna o seu registro útil depois. O "não está alagado" vale tanto quanto o "sim": sem ele, só se aprende onde alaga, nunca onde não alaga.' }),
        el('button', { class: 'btn ghost', type: 'button', text: 'Voltar' })
      ]);
      recibo.querySelector('.btn').onclick = function () { ir('#/registro'); };
      tela.appendChild(recibo);
    } else {
      // Tela da pergunta.
      var dados = window.VAND_DADOS;
      tela.appendChild(el('div', { class: 'pergunta-local' }, [
        icone('local', 18),
        el('span', { text: 'Localização Atual' })
      ]));

      tela.appendChild(el('h1', { class: 't-display', text: 'Está alagado aí agora?' }));

      var respostas = el('div', { class: 'respostas' });
      var botaoSim = el('button', { class: 'resp resp-sim', type: 'button' }, [
        el('span', { text: 'SIM, está alagado' }),
        icone('gota', 32)
      ]);
      botaoSim.onclick = function () { respostaRegistro = 'Sim, está alagado'; ir('#/registro/enviado'); };

      var botaoNao = el('button', { class: 'resp resp-nao', type: 'button' }, [
        el('span', { text: 'NÃO, está seco' }),
        icone('sol', 32, true)
      ]);
      botaoNao.onclick = function () { respostaRegistro = 'Não, está seco'; ir('#/registro/enviado'); };

      var iconeNsei = icone('duvida', 32, true);
      iconeNsei.classList.add('ico-duvida-fraca');
      var botaoNsei = el('button', { class: 'resp resp-nsei', type: 'button' }, [
        el('span', { text: 'Não sei' }),
        iconeNsei
      ]);
      botaoNsei.onclick = function () { respostaRegistro = 'Não sei'; ir('#/registro/enviado'); };

      respostas.appendChild(botaoSim);
      respostas.appendChild(botaoNao);
      respostas.appendChild(botaoNsei);
      tela.appendChild(respostas);

      var justificativa = el('div', { class: 'justificativa' }, [
        el('div', { class: 'justificativa-linha' }, [
          icone('duvida', 20),
          el('p', { text: 'Alagamento não é chuva. Pela definição oficial (COBRADE 1.2.3.0.0) ele é extrapolação da capacidade do sistema de drenagem — não há uma palavra sobre atmosfera. Nenhum modelo meteorológico prevê alagamento, e é por isso que a pergunta precisa ser feita a uma pessoa.' })
        ])
      ]);
      tela.appendChild(justificativa);

      tela.appendChild(el('div', { class: 'rodape-registro', text: 'SEU REGISTRO SERÁ ASSOCIADO AO AVISO DO INMET VIGENTE PARA FINS DE ANÁLISE.' }));
    }
  }

  // ---------- início ----------

  // Preenche os slots de ícone de cada aba.
  abas.forEach(function (b) {
    var slot = b.querySelector('.ico-slot');
    if (slot) {
      var nomes = { alerta: 'aviso', registro: 'registro', estudar: 'estudar' };
      var svg = icone(nomes[b.dataset.aba] || '', 26);
      slot.parentNode.insertBefore(svg, slot);
      slot.parentNode.removeChild(slot);
    }
    b.onclick = function () { ir('#/' + b.dataset.aba); };
  });

  window.addEventListener('hashchange', render);
  render();

  if ('serviceWorker' in navigator && location.protocol.indexOf('http') === 0) {
    window.addEventListener('load', function () {
      navigator.serviceWorker.register('sw.js').catch(function () {});
    });
  }
})();
