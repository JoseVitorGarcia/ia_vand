/*
 * Conteúdo da Trilha do módulo educacional.
 *
 * IMPORTANTE — ver docs/adr/0001: o texto abaixo é de redação própria, ancorado
 * em material oficial do governo. Nenhum parágrafo é reproduzido das obras
 * citadas. Cada Tema declara suas Fontes com órgão, obra, ano e página.
 *
 * TODA afirmação científica aqui precisa de revisão humana antes de publicar.
 */
window.VAND_CONTENT = {
  trilha: [
    {
      id: 'de-onde-vem-a-chuva',
      titulo: 'De onde vem a chuva',
      nivel: 'Básico',
      minutos: 8,
      resumo:
        'A mesma água circula há bilhões de anos entre o mar, o céu e o solo. ' +
        'Entender esse caminho é o que permite prever quando ela volta.',
      secoes: [
        {
          tipo: 'texto',
          titulo: 'Água que ninguém fabrica',
          paragrafos: [
            'A água que sai da sua torneira hoje não foi criada em lugar nenhum. Ela ' +
              'já foi chuva, já foi rio, já esteve dentro de uma planta e já evaporou de um ' +
              'oceano — muitas vezes. O ciclo da água é o exemplo mais antigo de reciclagem ' +
              'que existe, e ele funciona sem que ninguém precise organizá-lo.',
            'O que muda é o estado e o lugar. O calor do Sol evapora a água da superfície; ' +
              'no alto, mais frio, o vapor se condensa em gotas minúsculas e forma nuvens; ' +
              'quando essas gotas crescem o bastante para o ar não as sustentar mais, elas ' +
              'caem. Parte escorre para rios, parte infiltra no solo e alimenta reservatórios ' +
              'subterrâneos, parte evapora de novo. Nada se perde no caminho — só troca de ' +
              'endereço.',
            'Por isso o problema da água quase nunca é de quantidade total. É de estar na ' +
              'hora certa, no lugar certo e limpa o suficiente para usar.'
          ]
        },
        {
          tipo: 'dados',
          titulo: 'Quanta água existe, de verdade',
          itens: [
            { rotulo: 'Da água do planeta, é salgada', valor: '97%' },
            { rotulo: 'É doce', valor: '3%' },
            {
              rotulo: 'E da parte doce, a maior fatia está congelada em geleiras e calotas polares, ou sob o solo, como água subterrânea',
              valor: '',
              largo: true
            }
          ],
          nota:
            'Rios e lagos — de onde a água é retirada com mais facilidade — são uma ' +
            'fração pequena desses 3%. É o que torna o desperdício e a poluição tão caros: ' +
            'estraga-se justamente a parte acessível.'
        },
        {
          tipo: 'destaque',
          titulo: 'Um poeta gaúcho já tinha dito',
          texto:
            'O livro oficial do ENCCEJA abre a discussão sobre água com um poema de Raul ' +
            'Bopp, nascido no Rio Grande do Sul em 1898, sobre um rio imenso e sem margens ' +
            'que, de tanto correr, um dia secou. O material comenta que essa é a cara do ' +
            'problema da água no Brasil: ora inunda tudo como se os rios não tivessem ' +
            'margem, ora seca o fundo. Cheia e estiagem não são dois problemas — são o ' +
            'mesmo ciclo, visto em dois momentos.'
        },
        {
          tipo: 'texto',
          titulo: 'Como alguém sabe que vai chover',
          paragrafos: [
            'Prever o tempo sempre foi observar a natureza. Durante a maior parte da ' +
              'história isso significou reparar em bichos e plantas — ditados como "cigarra ' +
              'cantou, calor chegou" são exatamente isso. Quando o ser humano passou a ' +
              'plantar e criar animais, acertar a previsão virou questão de sobrevivência.',
            'O método continua sendo observação; o que mudou foi o instrumento. A ' +
              'meteorologia, ciência que estuda a atmosfera, precisa de milhares de pontos ' +
              'de observação espalhados pelo mundo. Esses pontos são as estações ' +
              'meteorológicas, e elas não ficam só no chão: existem estações terrestres, ' +
              'marítimas (em navios e boias) e aéreas (em balões e satélites).',
            'Cada estação mede continuamente coisas como temperatura, umidade, pressão, ' +
              'vento e chuva, e envia esses números para centros meteorológicos. Lá, ' +
              'computadores reúnem tudo e calculam como a atmosfera deve se comportar nas ' +
              'próximas horas e dias. É daí que sai a previsão que você vê no jornal.'
          ]
        },
        {
          tipo: 'destaque',
          titulo: 'Onde este aplicativo entra',
          texto:
            'As estações meteorológicas descritas acima não são um conceito distante: o ' +
            'Instituto Nacional de Meteorologia (INMET) opera uma rede delas no Rio Grande ' +
            'do Sul, e é dessa rede que sai o dado que este projeto estuda. Quando você ' +
            'recebe um aviso na aba Alerta, ele nasceu de medições feitas por estações como ' +
            'as que você acabou de conhecer.'
        }
      ],
      reflexoes: [
        'No seu trabalho, o tempo importa? De que maneira acertar ou errar a previsão muda o seu dia?',
        'Você conhece algum ditado popular que sirva para prever o tempo? Onde ouviu? Ele costuma acertar?'
      ],
      quiz: [
        {
          enunciado: 'Do total de água existente no planeta, aproximadamente quanto é água doce?',
          alternativas: ['Cerca de 3%', 'Cerca de 30%', 'Cerca de 50%', 'Cerca de 97%'],
          correta: 0,
          explicacao:
            'Cerca de 97% da água da Terra é salgada, e só cerca de 3% é doce. A ' +
            'impressão de abundância vem de olhar o volume total, que é quase todo mar.'
        },
        {
          enunciado: 'Dentro dessa pequena parcela de água doce, onde está armazenada a maior parte?',
          alternativas: [
            'Em rios e lagos',
            'Em geleiras, calotas polares e no subsolo',
            'Nas nuvens, em forma de vapor',
            'Em reservatórios construídos por seres humanos'
          ],
          correta: 1,
          explicacao:
            'A maior parte da água doce está congelada em geleiras e calotas polares ou ' +
            'sob o solo, como água subterrânea. Rios e lagos, de onde é mais fácil retirar, ' +
            'são uma fração pequena — por isso poluí-los custa tão caro.'
        },
        {
          enunciado: 'O que a meteorologia estuda?',
          alternativas: [
            'O interior da Terra e os terremotos',
            'Os astros e o sistema solar',
            'A atmosfera',
            'Os rios e as bacias hidrográficas'
          ],
          correta: 2,
          explicacao:
            'Meteorologia é a ciência que estuda a atmosfera. O estudo dos rios e bacias é ' +
            'hidrologia; o do interior da Terra, geologia; o dos astros, astronomia.'
        },
        {
          enunciado: 'Sobre as estações meteorológicas, é correto afirmar que:',
          alternativas: [
            'Existem apenas em terra firme, sempre em cidades grandes',
            'São usadas só depois que o desastre acontece, para medir o estrago',
            'Existem em terra, no mar (navios e boias) e no ar (balões e satélites)',
            'Cada país usa apenas os dados das suas próprias estações'
          ],
          correta: 2,
          explicacao:
            'Há estações terrestres, marítimas e aéreas, e os dados de todas elas são ' +
            'enviados continuamente a centros meteorológicos, que os reúnem para calcular a ' +
            'previsão. Previsão do tempo é, por natureza, um esforço internacional.'
        },
        {
          enunciado:
            'Por que se pode dizer que o ciclo da água é um exemplo de reciclagem que existe na própria natureza?',
          alternativas: [
            'Porque a chuva cria água nova a cada tempestade',
            'Porque a mesma água muda de estado e de lugar, sem ser criada nem destruída',
            'Porque a água do mar se transforma em água doce dentro dos rios',
            'Porque as estações de tratamento devolvem a água ao ciclo'
          ],
          correta: 1,
          explicacao:
            'A água evapora, condensa, precipita, escoa e infiltra — muda de estado e de ' +
            'reservatório continuamente, mas a quantidade total não é criada nem destruída ' +
            'no processo. É a mesma água circulando.'
        }
      ],
      fontes: [
        {
          obra: 'Ciências — Livro do Estudante, Ensino Fundamental',
          orgao: 'MEC/INEP — ENCCEJA',
          ano: 2006,
          detalhe: 'Cap. VII (previsão do tempo, meteorologia e estações) e Cap. IX (ciclo da água e disponibilidade de água doce)'
        }
      ]
    },

    {
      id: 'quando-a-chuva-vira-enchente',
      titulo: 'Quando a chuva vira enchente',
      nivel: 'Intermediário',
      minutos: 10,
      resumo:
        'Chuva forte não explica sozinha uma enchente. O que o solo, o córrego e o ' +
        'asfalto fazem com essa chuva explica o resto.',
      secoes: [],
      reflexoes: [],
      quiz: [],
      fontes: [
        {
          obra: 'Ciências — Livro do Estudante, Ensino Fundamental',
          orgao: 'MEC/INEP — ENCCEJA',
          ano: 2006,
          detalhe: 'Cap. VIII, seção "Chuva de menos: seca. Chuva demais: enchente"'
        },
        {
          obra: 'Desastres Hidrológicos — cartilha de informações e orientações',
          orgao: 'CEMADEN Educação / MCTI',
          ano: 2024,
          detalhe: 'Orientações de o que fazer'
        }
      ]
    },

    {
      id: 'clima-em-mudanca-e-risco-na-cidade',
      titulo: 'Clima em mudança e risco na cidade',
      nivel: 'Avançado',
      minutos: 12,
      resumo:
        'Efeito estufa, drenagem urbana e prevenção: por que o mesmo volume de chuva ' +
        'causa estragos diferentes em cidades diferentes.',
      secoes: [],
      reflexoes: [],
      quiz: [],
      fontes: [
        {
          obra: 'Ciências da Natureza e suas Tecnologias — Livro do Estudante, Ensino Médio',
          orgao: 'MEC/INEP — ENCCEJA',
          ano: 2006,
          detalhe: 'Cap. II (prevenção e drenagem urbana) e Cap. IX (biodiversidade e meio ambiente)'
        },
        {
          obra: 'Nós no Clima da Mudança — Ensino Médio',
          orgao: 'CEMADEN Educação / MCTI',
          ano: 2025,
          detalhe: 'Educação e justiça climática'
        }
      ]
    }
  ]
};
