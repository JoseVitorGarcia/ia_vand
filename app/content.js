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
      secoes: [
        {
          tipo: 'texto',
          titulo: 'A mesma chuva, dois destinos',
          paragrafos: [
            'Ninguém consegue impedir a chuva — e ainda bem. É dela que vêm os açudes, os ' +
              'poços e os reservatórios que abastecem cidades inteiras. O Tema anterior mostrou ' +
              'que a água não é fabricada por ninguém: ela só circula. A chuva é a etapa desse ' +
              'ciclo em que a água volta para o chão.',
            'O que muda tudo é o que ela encontra quando chega lá. Água que cai sobre solo ' +
              'coberto de vegetação infiltra devagar, alimenta o lençol subterrâneo e demora a ' +
              'chegar ao rio. A mesma água caindo sobre asfalto não infiltra: escorre na hora, ' +
              'inteira, para o ponto mais baixo do bairro — e chega ao bueiro toda de uma vez.',
            'É por isso que duas ruas da mesma cidade, debaixo da mesma nuvem, podem terminar ' +
              'a tarde de formas completamente diferentes. A chuva foi igual. O que o chão fez ' +
              'com ela, não.'
          ]
        },
        {
          tipo: 'dados',
          titulo: 'Quarenta minutos',
          itens: [
            { rotulo: 'de chuva forte, em São Paulo, em 28 de novembro de 2001', valor: '40 min' },
            { rotulo: 'pontos de alagamento na cidade', valor: '20' },
            {
              rotulo: 'Carros arrastados pelas ruas, um rio transbordado e o trânsito parado — tudo dentro desses quarenta minutos',
              valor: '',
              largo: true
            }
          ],
          nota:
            'O episódio é o exemplo que o livro oficial do ENCCEJA usa para abrir a discussão. ' +
            'Ele desfaz a intuição de que enchente exige um temporal de dias: quando o solo já ' +
            'não absorve e a drenagem já está no limite, quarenta minutos bastam.'
        },
        {
          tipo: 'texto',
          titulo: 'O que a cidade faz com a água',
          paragrafos: [
            'As alterações que agravam uma enchente quase nunca foram feitas para agravar ' +
              'nada. Foram feitas para facilitar a vida — e o efeito colateral só aparece no dia ' +
              'da chuva. O livro do ENCCEJA lista as principais: córregos canalizados de forma ' +
              'malfeita, cursos de pequenos rios alterados, barragens mal construídas e, acima ' +
              'de tudo, a impermeabilização do solo pelo asfaltamento das ruas e pela ' +
              'pavimentação dos quintais.',
            'Some a isso o que acontece nas margens. Desmatar a beira de um rio para plantar ou ' +
              'criar gado deixa o solo exposto; sem raiz que o segure, ele é levado pela erosão e ' +
              'vai parar no fundo do rio. O leito sobe, a passagem estreita, e o mesmo volume de ' +
              'água que antes cabia passa a transbordar.',
            'O lixo fecha a conta. Jogado na rua ou no córrego, ele é levado pela água até o ' +
              'bueiro e o entope justamente quando o bueiro mais precisa funcionar. É a única ' +
              'peça dessa lista que não depende de obra pública nenhuma para mudar.',
            'E há uma injustiça embutida em tudo isso: quem mora mais perto do rio e da encosta ' +
              'costuma ser quem teve menos escolha sobre onde morar. O risco não se distribui por ' +
              'sorteio — ele se concentra em quem já tinha menos.'
          ]
        },
        {
          tipo: 'glossario',
          titulo: 'Quatro palavras que não são sinônimos',
          termos: [
            {
              palavra: 'Enchente',
              definicao:
                'O nível da água sobe acima do normal por causa do aumento da vazão, mas a ' +
                'água ainda corre dentro do leito do rio. É a palavra mais usada no dia a dia ' +
                '— e a única das quatro que a classificação oficial de desastres não lista.'
            },
            {
              palavra: 'Inundação — COBRADE 1.2.1.0.0',
              definicao:
                'A água submerge áreas fora dos limites normais do curso d’água, que ' +
                'normalmente não ficam submersas. O transbordamento é gradual, e costuma vir ' +
                'de chuva prolongada em área de planície.'
            },
            {
              palavra: 'Enxurrada — COBRADE 1.2.2.0.0',
              definicao:
                'Escoamento superficial de alta velocidade e energia, provocado por chuva ' +
                'intensa e concentrada, normalmente em bacias pequenas de relevo acidentado. A ' +
                'vazão sobe de repente e a calha do rio transborda de forma brusca. É a de ' +
                'maior poder destrutivo.'
            },
            {
              palavra: 'Alagamento — COBRADE 1.2.3.0.0',
              definicao:
                'Acúmulo de água em ruas, calçadas e outras estruturas urbanas porque a ' +
                'capacidade de escoamento da drenagem foi excedida por chuva intensa. É um ' +
                'problema de bueiro e de galeria, não de rio.'
            }
          ],
          nota:
            'Repare no contraste entre as duas do meio, porque ele é a diferença entre ter ' +
            'tempo e não ter: a inundação sobe devagar, em terreno plano, depois de dias de ' +
            'chuva — dá para avisar, dá para sair. A enxurrada desce de uma vez, em terreno ' +
            'inclinado, durante a chuva — e é justamente por isso que mata mais. As três com ' +
            'código são tipos oficiais da Classificação e Codificação Brasileira de Desastres ' +
            '(COBRADE), que a defesa civil usa para registrar cada ocorrência do país. As ' +
            'palavras acima são nossas; os códigos permitem conferir cada uma na fonte.'
        },
        {
          tipo: 'texto',
          titulo: 'Por que nenhuma previsão do tempo prevê alagamento',
          paragrafos: [
            'Repare no que a definição de alagamento diz: capacidade de escoamento do sistema de ' +
              'drenagem. Não há uma palavra sobre atmosfera. Um modelo meteorológico calcula como ' +
              'o ar se comporta — para onde vai a umidade, onde ela condensa, quanta chuva cai em ' +
              'cada pedaço do mapa. Ele não sabe onde ficam os bueiros da sua rua, se estão ' +
              'entupidos, nem que o terreno da esquina é o ponto mais baixo do quarteirão.',
            'Prever chuva e prever alagamento são, portanto, dois problemas diferentes. O ' +
              'primeiro a meteorologia resolve razoavelmente bem. O segundo depende de drenagem, ' +
              'topografia e manutenção — informação que não está em satélite nenhum, e que ' +
              'costuma existir apenas na cabeça de quem mora ali.',
            'É a diferença entre a ameaça e o dano. A previsão descreve a ameaça que vem do céu; ' +
              'o estrago que ela causa depende de vulnerabilidade — quem está exposto, onde, e ' +
              'com que capacidade de se recuperar depois.'
          ]
        },
        {
          tipo: 'destaque',
          titulo: 'Onde este aplicativo entra',
          texto:
            'É exatamente por isso que a aba Registro existe. Nenhum modelo nos diria que a sua ' +
            'esquina alagou — só você pode. E o registro mais valioso não é o "sim, alagou": é o ' +
            '"não, aqui está seco", enviado no meio de uma chuva forte. Sem os dois, existe apenas ' +
            'uma lista de lugares que alagaram, e não dá para aprender onde não alaga a partir de ' +
            'uma lista dessas. O aviso do INMET, que você vê na aba Alerta, cobre uma região ' +
            'inteira; o que acontece na sua rua, dentro dessa região, só o seu registro conta.'
        }
      ],
      reflexoes: [
        'Existe um ponto na sua cidade que alaga toda vez que chove forte? Olhando para ele, o que você vê: asfalto até a guia, um córrego canalizado, terreno mais baixo que a vizinhança, bueiro entupido?',
        'Depois de uma chuva forte onde você mora, quanto tempo a água leva para escoar? E quem você acha que deveria resolver isso — o morador, a prefeitura, os dois?'
      ],
      quiz: [
        {
          enunciado:
            'Duas ruas da mesma cidade recebem exatamente a mesma chuva. Uma alaga, a outra não. O que melhor explica a diferença?',
          alternativas: [
            'A chuva foi mais forte numa delas, mesmo que não pareça',
            'O que cada rua faz com a água depois que ela cai: infiltração, escoamento e drenagem',
            'A sorte, já que enchente é um fenômeno imprevisível',
            'A quantidade de moradores em cada rua'
          ],
          correta: 1,
          explicacao:
            'O enunciado já fixa a chuva como igual nas duas. O que sobra para explicar a ' +
            'diferença é o destino da água: solo que infiltra ou asfalto que não infiltra, ' +
            'terreno alto ou baixo, drenagem que dá conta ou não.'
        },
        {
          enunciado: 'Qual destas alterações feitas pelo ser humano tende a AUMENTAR o risco de enchente?',
          alternativas: [
            'Plantar vegetação na margem de um córrego',
            'Ampliar a área de solo permeável em praças e quintais',
            'Asfaltar ruas e pavimentar quintais em grande extensão',
            'Desassorear o leito de um rio, retirando o material acumulado no fundo'
          ],
          correta: 2,
          explicacao:
            'Asfalto e pavimento impermeabilizam o solo: a água que antes infiltrava passa a ' +
            'escorrer inteira para a drenagem, de uma vez. As outras três opções vão na direção ' +
            'contrária — todas aumentam a capacidade de absorver ou de escoar.'
        },
        {
          enunciado: 'Por que desmatar a margem de um rio aumenta o risco de enchente?',
          alternativas: [
            'Porque as árvores da margem consomem a água que causaria a enchente',
            'Porque sem vegetação o solo sofre erosão, vai para o fundo do rio e reduz a passagem da água',
            'Porque a mata das margens faz a chuva cair em outro lugar',
            'Porque o desmatamento aquece o rio e evapora menos água'
          ],
          correta: 1,
          explicacao:
            'Sem raiz que segure o solo, a erosão carrega terra para dentro do rio. O material se ' +
            'acumula no fundo, o leito perde profundidade, e o volume de água que antes passava ' +
            'sem problema começa a transbordar.'
        },
        {
          enunciado:
            'Uma rua do centro acumula água porque a galeria de drenagem não deu conta do volume, sem que rio nenhum transbordasse. Como se chama isso?',
          alternativas: ['Inundação', 'Enxurrada', 'Alagamento', 'Enchente'],
          correta: 2,
          explicacao:
            'Alagamento é acúmulo de água em área urbana por extrapolação da capacidade do ' +
            'sistema de drenagem. Enchente é o nível subindo dentro do leito do rio; inundação é ' +
            'a água extravasando para fora dele; enxurrada é o escoamento concentrado e violento.'
        },
        {
          enunciado: 'Por que a previsão meteorológica não consegue prever que uma esquina específica vai alagar?',
          alternativas: [
            'Porque a previsão do tempo ainda é uma ciência pouco confiável',
            'Porque alagamento depende de drenagem, topografia e manutenção locais, que o modelo de atmosfera não enxerga',
            'Porque os satélites não cobrem áreas urbanas com detalhe suficiente',
            'Porque só é possível prever chuva com poucas horas de antecedência'
          ],
          correta: 1,
          explicacao:
            'Um modelo meteorológico calcula o comportamento da atmosfera. Bueiro entupido, ' +
            'terreno baixo e galeria subdimensionada não são atmosfera — são a cidade. Por isso a ' +
            'previsão descreve a ameaça que vem do céu, mas não o estrago que ela vai causar em ' +
            'cada ponto.'
        }
      ],
      fontes: [
        {
          obra: 'Ciências — Livro do Estudante, Ensino Fundamental',
          orgao: 'MEC/INEP — ENCCEJA',
          ano: 2006,
          detalhe:
            'Cap. VIII, seção "Chuva de menos: seca. Chuva demais: enchente" (alterações humanas ' +
            'que agravam a enchente e o episódio de São Paulo em 2001) e Cap. IX ' +
            '(impermeabilização urbana, erosão de margens e ocupação de áreas de risco)'
        },
        {
          obra: 'Classificação e Codificação Brasileira de Desastres (COBRADE), Anexo V da Instrução Normativa nº 36',
          orgao: 'Ministério do Desenvolvimento Regional — hoje Ministério da Integração e do Desenvolvimento Regional, Secretaria Nacional de Proteção e Defesa Civil',
          ano: 2020,
          detalhe:
            'Grupo Hidrológico: Inundações (1.2.1.0.0), Enxurradas (1.2.2.0.0) e Alagamentos ' +
            '(1.2.3.0.0). É a classificação em vigor, sucedendo a IN nº 1/2012, que criou o ' +
            'COBRADE, e a IN nº 2/2016. "Enchente" não é um tipo do COBRADE'
        },
        {
          obra:
            'Desastres Hidrológicos: uma cartilha com informações e orientações sobre como agir ' +
            'em situações de risco (Gustavo Gaião Corrêa e Vitória Paula Freitas Marques; org. ' +
            'Cássia Barreto Brandão)',
          orgao: 'UERJ — grupo Prodocência; publicação independente dos autores, hospedada na midiateca do Cemaden Educação',
          ano: 2023,
          detalhe:
            'Os conceitos de risco, vulnerabilidade e resiliência, que sustentam a distinção ' +
            'entre a ameaça que vem do céu e o dano que ela causa. As definições dos quatro ' +
            'termos vêm do COBRADE acima, não daqui'
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
      secoes: [
        {
          tipo: 'texto',
          titulo: 'O mesmo volume, estragos diferentes',
          paragrafos: [
            'O Tema anterior terminou numa constatação: a chuva é igual, o que o chão faz com ' +
              'ela não é. Este Tema pega esse fio e puxa até o fim, porque a diferença entre duas ' +
              'ruas se repete entre dois bairros, entre duas cidades e entre dois países.',
            'O livro oficial do Ensino Médio do ENCCEJA diz, já em 2006, que responsabilizar só ' +
              'a chuva pelas enchentes é simplificar demais o problema. É uma frase escrita pelo ' +
              'MEC quase vinte anos antes desta tela, e ela vale como resumo de tudo o que vem a ' +
              'seguir: desastre não é sinônimo de fenômeno natural. O fenômeno é a ameaça; o ' +
              'desastre é o que acontece quando a ameaça encontra uma população exposta e sem ' +
              'meios de se proteger.',
            'Daí a conta que a defesa civil usa: o risco nasce do encontro entre a ameaça e a ' +
              'vulnerabilidade. Sobre a ameaça, ninguém decide — não se cancela uma frente fria. ' +
              'Sobre a vulnerabilidade, decide-se o tempo todo: onde se deixa construir, quanto se ' +
              'gasta em drenagem, quem é avisado e com quanta antecedência. Por isso um desastre ' +
              'pode ser previsto e, em boa medida, evitado, mesmo que a chuva não possa.'
          ]
        },
        {
          tipo: 'texto',
          titulo: 'O que está mudando, e o que isso faz com a chuva',
          paragrafos: [
            'O efeito estufa não é um defeito: sem os gases que seguram parte do calor na ' +
              'atmosfera, a Terra seria fria demais para a vida como a conhecemos. O problema é a ' +
              'intensidade. Ao acrescentar gás carbônico, metano e óxido nitroso em quantidade, a ' +
              'humanidade tornou esse cobertor mais espesso, e o planeta reteve mais calor do que ' +
              'devolveu.',
            'Cientistas chamam o resultado de novo regime climático — uma expressão que diz mais ' +
              'do que "está mais quente". Ela diz que a régua mudou: os eventos extremos passam a ' +
              'acontecer em maior quantidade, em mais lugares e com mais frequência do que a ' +
              'experiência acumulada de quem vive ali levaria a esperar.',
            'Entre as consequências listadas pelo material oficial, três interessam diretamente a ' +
              'quem mora em cidade: ondas de calor e de frio mais intensas, secas mais severas, e ' +
              'tempestades e enchentes mais drásticas. Repare que seca e enchente aparecem juntas. ' +
              'Não é contradição — é o mesmo ciclo da água ficando mais irregular nas duas pontas.',
            'Para a nossa história, o ponto é este: a chuva que a cidade foi construída para ' +
              'aguentar é a chuva de um clima que está deixando de existir. A drenagem projetada ' +
              'com a estatística de trinta anos atrás encontra hoje uma estatística diferente.'
          ]
        },
        {
          tipo: 'dados',
          titulo: 'A lei que não tira a água, tira a pressa',
          itens: [
            { rotulo: 'a Lei nº 13.276 de São Paulo, apelidada de "Lei das Piscininhas"', valor: '2002' },
            { rotulo: 'é quanto o reservatório precisa segurar a água depois que a chuva termina', valor: '1 hora' },
            {
              rotulo: 'Campina Grande, Campinas, Limeira, Ribeirão Preto, Rio de Janeiro e Curitiba estudaram leis parecidas — e em Campina Grande o alvo era o oposto: guardar água para a seca',
              valor: '',
              largo: true
            }
          ],
          nota:
            'Repare no que a lei faz e no que ela não faz. Ela não diminui um litro do que caiu: ' +
            'obriga cada prédio a guardar a sua parte e a soltá-la só depois que a chuva passou. ' +
            'O que ela devolve à cidade é o atraso que o solo dava de graça antes do asfalto — e ' +
            'é esse atraso, não o volume, que impede a rede pluvial de receber tudo no mesmo ' +
            'instante e transbordar.'
        },
        {
          tipo: 'texto',
          titulo: 'Cinza, verde, e o que a cidade escolhe',
          paragrafos: [
            'Durante muito tempo a resposta a esse problema foi o que se chama de infraestrutura ' +
              'cinza: obras grandes, de concreto, aço e pedra — diques, muros de arrimo, barragens, ' +
              'quebra-mares, canais pavimentados. Elas funcionam, e há situações em que não há ' +
              'substituto para elas.',
            'Mas o material oficial aponta três limites que se acumularam com o tempo. Custam caro ' +
              'para manter, e manutenção é a primeira coisa que some do orçamento. Degradam o ' +
              'ambiente, sobretudo na obra. E são rígidas: foram dimensionadas para um número, e ' +
              'quando o evento extremo passa desse número, elas não se adaptam — falham.',
            'A alternativa que ganhou espaço são as soluções baseadas na natureza: recuperar a ' +
              'várzea em vez de canalizar o córrego, ampliar área permeável, replantar a margem. ' +
              'São mais baratas de manter, e falham devagar em vez de falhar de uma vez.',
            'A piscininha do quadro acima é interessante justamente por ficar no meio do caminho: ' +
              'é concreto, é obra, mas é pequena, distribuída por milhares de lotes e imita o que a ' +
              'terra fazia. Nenhuma das três abordagens dispensa a outra. O que existe é escolha ' +
              'sobre a mistura — e essa escolha é orçamento público, não meteorologia.'
          ]
        },
        {
          tipo: 'texto',
          titulo: 'Vulnerabilizadas, não vulneráveis',
          paragrafos: [
            'O material do Cemaden Educação faz uma correção de vocabulário que muda o sentido da ' +
              'frase inteira: as populações mais atingidas não são vulneráveis por si sós — elas ' +
              'foram vulnerabilizadas. A diferença entre as duas palavras é que a segunda tem ' +
              'agente. Alguém decidiu onde passaria o asfalto, onde iria a escola, qual bairro ' +
              'receberia rede pluvial primeiro.',
            'Os efeitos do clima em mudança não se distribuem por igual. Comunidades negras, ' +
              'indígenas e de minorias étnicas vivem os impactos de forma desproporcional, porque ' +
              'estão com mais frequência em periferias, favelas, margens de rio e encostas — as ' +
              'áreas de risco. Nesses lugares o Estado costuma estar menos presente, e a mesma ' +
              'chuva encontra menos infraestrutura para atravessar. É a isso que se dá o nome de ' +
              'racismo ambiental.',
            'Dentro dessas comunidades, a exposição também não é uniforme: mulheres pobres, ' +
              'crianças, adolescentes, pessoas idosas e pessoas com deficiência são as que menos ' +
              'conseguem sair a tempo e as que mais demoram a se recompor depois.',
            'E há a assimetria que fecha o argumento: são justamente as pessoas que menos ' +
              'contribuíram para as emissões que mais sofrem as consequências delas. É por isso ' +
              'que se fala em justiça climática, e não apenas em adaptação — adaptação é uma ' +
              'questão de engenharia, justiça é uma questão de a quem se dirige a engenharia.'
          ]
        },
        {
          tipo: 'glossario',
          titulo: 'Resiliência: voltar, mudar ou transformar',
          termos: [
            {
              palavra: 'Voltar ao que era',
              definicao:
                'Recuperar a vida de antes o mais rápido possível. É o sentido mais comum da ' +
                'palavra — e o que traz a pergunta incômoda: se o desastre aconteceu, aquela ' +
                'normalidade era mesmo segura, ou já era o problema?'
            },
            {
              palavra: 'Reconstruir com mudanças',
              definicao:
                'Aproveitar a reconstrução para corrigir o que estava errado: melhorar obras, ' +
                'garantir direitos, reforçar leis. Ajuda de verdade, mas chega depois das perdas ' +
                'e trabalha sobre o que restou.'
            },
            {
              palavra: 'Transformar',
              definicao:
                'Mudar a base: repensar como a cidade funciona, questionar as regras que ' +
                'produziram a exposição, discutir quem decide. É a forma mais difícil, e a única ' +
                'que ataca o que fez a sociedade ser vulnerável, e não apenas o desastre.'
            }
          ],
          nota:
            'A distinção é do pesquisador Mark Pelling, apresentada pelo caderno do Cemaden ' +
            'Educação. Ela é útil porque quase todo debate público depois de uma enchente é, no ' +
            'fundo, uma disputa entre estas três ideias — e quase sempre sem que ninguém diga em ' +
            'qual delas está.'
        },
        {
          tipo: 'destaque',
          titulo: 'Onde este aplicativo entra',
          texto:
            'O material oficial descreve um sistema de alerta como quatro eixos ligados: ' +
            'conhecimento do risco, monitoramento, educação e comunicação, e preparação. Vale ' +
            'reparar onde este aplicativo cai. A aba Alerta é comunicação: ela não monitora nada ' +
            '— retransmite o aviso de quem monitora, o INMET. Este Tema que você está lendo é o ' +
            'eixo da educação. A aba Registro é conhecimento do risco vindo de baixo, e há ' +
            'estudos mostrando que a resposta funciona melhor quando a defesa civil leva em ' +
            'conta o que quem mora ali já sabe. Nenhum dos quatro eixos é dispensável, e nenhum ' +
            'deles é o aplicativo sozinho: um aviso que chega não substitui uma cidade que ' +
            'drena, e nenhum dos dois substitui a decisão sobre quem pode morar onde.'
        }
      ],
      reflexoes: [
        'Pense na cidade onde você mora: ela responde à chuva mais com infraestrutura cinza (canal, muro, barragem) ou com área permeável e vegetação? Quem você acha que tomou essa decisão, e quando?',
        'Depois do último desastre de que você se lembra, o que aconteceu: voltou-se ao que era antes, reconstruiu-se com mudanças, ou algo se transformou de verdade? Quem teve voz nessa decisão?'
      ],
      quiz: [
        {
          enunciado:
            'Segundo a forma como a defesa civil trata o assunto, por que um desastre pode ser evitado mesmo quando a chuva não pode?',
          alternativas: [
            'Porque a previsão do tempo consegue impedir a formação das tempestades',
            'Porque o risco nasce do encontro entre a ameaça e a vulnerabilidade, e sobre a vulnerabilidade se decide',
            'Porque desastres só acontecem em cidades mal localizadas geograficamente',
            'Porque a chuva forte, sozinha, raramente causa prejuízo'
          ],
          correta: 1,
          explicacao:
            'A ameaça — a chuva, a frente fria — não está sob controle de ninguém. A ' +
            'vulnerabilidade está: onde se deixa construir, quanto se investe em drenagem, quem é ' +
            'avisado e com quanta antecedência. Reduzir a vulnerabilidade reduz o desastre sem ' +
            'tocar na chuva.'
        },
        {
          enunciado: 'A "Lei das Piscininhas" reduz o risco de enchente porque:',
          alternativas: [
            'Diminui o volume total de chuva que cai sobre a cidade',
            'Impede que a chuva chegue ao solo urbano',
            'Retém a água e a libera depois da chuva, devolvendo à cidade o atraso que o solo dava antes do asfalto',
            'Transfere a água da chuva para outra bacia hidrográfica'
          ],
          correta: 2,
          explicacao:
            'Nenhum litro deixa de cair. O reservatório segura a água e só a solta cerca de uma ' +
            'hora depois do fim da chuva, para que a rede pluvial não receba tudo no mesmo ' +
            'instante. O que a lei devolve é tempo, não volume.'
        },
        {
          enunciado:
            'Qual é a principal fragilidade da infraestrutura cinza (diques, muros de arrimo, canais pavimentados) diante do clima em mudança?',
          alternativas: [
            'Ela é barata demais para ser levada a sério pelos governos',
            'Ela só funciona em cidades pequenas',
            'Ela é rígida: foi dimensionada para um número, e falha quando o evento extremo passa desse número',
            'Ela depende de previsão meteorológica para funcionar'
          ],
          correta: 2,
          explicacao:
            'Além do custo de manutenção e do impacto ambiental da obra, o limite decisivo é a ' +
            'rigidez. Uma estrutura calculada para certa vazão não se adapta quando o evento a ' +
            'supera — e o novo regime climático torna esses eventos mais frequentes.'
        },
        {
          enunciado: 'Por que o material oficial prefere dizer que as populações mais atingidas foram "vulnerabilizadas"?',
          alternativas: [
            'Porque a palavra é mais técnica e soa melhor em documentos',
            'Porque a vulnerabilidade dessas populações é fruto de decisões humanas, e a palavra deixa claro que houve quem decidisse',
            'Porque elas não são realmente vulneráveis a desastres',
            'Porque a palavra "vulnerável" só se aplica a construções, não a pessoas'
          ],
          correta: 1,
          explicacao:
            '"Vulnerável" descreve um estado, como se fosse condição própria daquele grupo. ' +
            '"Vulnerabilizada" tem agente: alguém decidiu onde passaria o asfalto, onde iria a ' +
            'escola, qual bairro receberia drenagem primeiro. A troca de palavra devolve a ' +
            'responsabilidade a quem decidiu.'
        },
        {
          enunciado:
            'Entre as três formas de resiliência descritas, qual é a que a apostila trata como a mais difícil e a mais profunda?',
          alternativas: [
            'Voltar ao que era antes o mais rápido possível',
            'Reconstruir com melhorias pontuais nas obras danificadas',
            'Transformar: mudar as regras e a estrutura que produziram a exposição',
            'Evitar reconstruir, deixando a área permanentemente desocupada'
          ],
          correta: 2,
          explicacao:
            'Voltar ao que era pode significar restaurar justamente o arranjo que produziu o ' +
            'desastre. Reconstruir com mudanças ajuda, mas age depois da perda. Transformar é ' +
            'mexer na base — como a cidade funciona e quem decide — e por isso é a mais exigente.'
        }
      ],
      fontes: [
        {
          obra: 'Ciências da Natureza e suas Tecnologias — Livro do Estudante, Ensino Médio',
          orgao: 'MEC/INEP — ENCCEJA',
          ano: 2006,
          detalhe:
            'Cap. II, seções sobre prevenção, vazão e drenagem urbana — de onde vêm a Lei nº ' +
            '13.276 de São Paulo ("Lei das Piscininhas"), a impermeabilização do solo urbano e a ' +
            'afirmação de que responsabilizar apenas as chuvas pelas enchentes simplifica demais ' +
            'o problema'
        },
        {
          obra: 'Nós no Clima da Mudança: caminhos de Educação e Justiça Climática — Ensino Médio',
          orgao: 'Programa Cemaden Educação (Cemaden/MCTI), com o Ministério do Meio Ambiente e Mudança do Clima e o Ministério da Educação',
          ano: 2025,
          detalhe:
            'Causas e consequências das mudanças do clima; racismo ambiental e populações ' +
            'vulnerabilizadas; infraestrutura cinza e soluções baseadas na natureza; os quatro ' +
            'eixos de um sistema de alerta; e as três formas de resiliência (retorno, transição e ' +
            'transformação) atribuídas pelo caderno ao pesquisador Mark Pelling'
        }
      ]
    }
  ]
};
