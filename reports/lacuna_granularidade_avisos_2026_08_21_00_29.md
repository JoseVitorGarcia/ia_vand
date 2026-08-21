# A lacuna de granularidade do alerta regional

Gerado em 21/08/2026 00:29

**IFS** (*Integrated Forecasting System*) é o modelo global de previsão do **ECMWF** (*European Centre for Medium-Range Weather Forecasts*).

## Como ler estes números

Um aviso meteorológico não afirma que o fenômeno vai ocorrer — comunica que há risco relevante de ocorrer. Aviso não confirmado **não é erro**: a possibilidade existia e comunicá-la era a função dele. Serviços de alerta aceitam deliberadamente alta taxa de não confirmação em eventos de alto impacto, porque o custo de não avisar é assimétrico em relação ao custo de avisar à toa.

Portanto o que segue é **taxa de confirmação** — entre os avisos de um grupo, em que fração o fenômeno anunciado foi registrado. É afirmação de calibração, não de acerto. **A mesma régua se aplica a nós:** a taxa da nossa regra sobre a previsão do ECMWF também é confirmação, não erro.

Cada aviso é verificado contra o critério que **ele mesmo anuncia**, extraído do campo `riscos`, e o critério é composto: confirma se chuva **ou** rajada cumpriu o anunciado.


Janela **2025-01-02 a 2026-07-31**, 95 estações, 26,905 estação-dias, 367 eventos acima de 50 mm em 24 h. 5,773 avisos colhidos na janela, dos quais 1,203 contêm alguma estação. Unidade: um alerta por estação-dia, ancorado às 12 UTC — início do dia pluviométrico do INMET.


## Cobertura dos avisos

**98.4% dos 367 eventos observados tinham aviso vigente**, e 45.0% de todos os estação-dias estavam sob algum aviso dos quatro tipos estudados.


## Taxa de confirmação por severidade

**Área**: alguma estação dentro do polígono registrou o anunciado. **Ponto**: a estação daquele local registrou. As duas nunca são lidas isoladas — a de área superestima o que o aviso significa para o indivíduo, e a de ponto subestima a qualidade de quem o emitiu.

A coluna **climatologia** é a taxa que o acaso entregaria para os mesmos critérios na mesma janela, e **ganho** é quantas vezes o aviso supera isso. Sem essa referência a taxa de confirmação é ininterpretável: o critério de vendaval (40 km/h) se cumpre em cerca de 20% dos dias sozinho, enquanto o de chuva (50 mm/dia) se cumpre em 1,4% — comparar tipos pela confirmação crua compara barras de altura diferente, não habilidades diferentes.

| grupo | unidade | n | taxa | ic_inf | ic_sup | climatologia | ganho |
|---|---|---|---|---|---|---|---|
| Grande Perigo | área | 46 | 0.609 | 0.465 | 0.736 | 0.002 | 310.8 |
| Grande Perigo | ponto | 2750 | 0.034 | 0.028 | 0.041 | 0.002 | 17.3 |
| Perigo | área | 302 | 0.732 | 0.679 | 0.779 | 0.039 | 18.7 |
| Perigo | ponto | 15093 | 0.143 | 0.137 | 0.149 | 0.039 | 3.7 |
| Perigo Potencial | área | 818 | 0.864 | 0.839 | 0.886 | 0.197 | 4.4 |
| Perigo Potencial | ponto | 39222 | 0.281 | 0.276 | 0.285 | 0.197 | 1.4 |

## Taxa de confirmação por tipo de aviso

| grupo | unidade | n | taxa | ic_inf | ic_sup | climatologia | ganho |
|---|---|---|---|---|---|---|---|
| Acumulado de Chuva | área | 85 | 0.529 | 0.424 | 0.632 | 0.009 | 57.9 |
| Acumulado de Chuva | ponto | 2785 | 0.069 | 0.06 | 0.079 | 0.009 | 7.6 |
| Chuvas Intensas | área | 262 | 0.786 | 0.733 | 0.832 | 0.19 | 4.1 |
| Chuvas Intensas | ponto | 9240 | 0.258 | 0.249 | 0.267 | 0.19 | 1.4 |
| Tempestade | área | 765 | 0.86 | 0.834 | 0.883 | 0.147 | 5.9 |
| Tempestade | ponto | 42238 | 0.228 | 0.224 | 0.232 | 0.147 | 1.6 |
| Vendaval | área | 54 | 0.87 | 0.756 | 0.936 | 0.128 | 6.8 |
| Vendaval | ponto | 2802 | 0.38 | 0.362 | 0.398 | 0.128 | 3 |

## Confirmação apenas pela chuva anunciada

O critério verificado acima é **composto**: confirma se chuva **ou** rajada cumpriu o anunciado. Isso é justo — um aviso de Chuvas Intensas também promete vento, e exigir os dois penalizaria quem acertou o vendaval. Mas a cláusula de vento desses avisos (40 km/h) se cumpre em 19,5% dos dias por acaso, então **quase todo aviso de chuva se confirma pelo vento, não pela chuva**.

A tabela abaixo repete a medição ignorando a cláusula de vento, com a climatologia de referência também recalculada só para chuva. A composta responde *o aviso estava certo sobre alguma coisa?*; esta responde *o aviso estava certo sobre CHUVA?*. As duas juntas são honestas; só a composta, não. Vendaval não aparece porque não anuncia chuva.


### Por severidade

| grupo | unidade | n | taxa | ic_inf | ic_sup | climatologia | ganho |
|---|---|---|---|---|---|---|---|
| Grande Perigo | área | 44 | 0.591 | 0.444 | 0.723 | 0.001 | 397.5 |
| Grande Perigo | ponto | 2722 | 0.031 | 0.025 | 0.038 | 0.001 | 21 |
| Perigo | área | 287 | 0.564 | 0.507 | 0.621 | 0.014 | 41.3 |
| Perigo | ponto | 13990 | 0.075 | 0.071 | 0.079 | 0.014 | 5.5 |
| Perigo Potencial | área | 781 | 0.309 | 0.277 | 0.342 | 0.014 | 22.6 |
| Perigo Potencial | ponto | 37551 | 0.038 | 0.036 | 0.04 | 0.014 | 2.8 |

### Por tipo

| grupo | unidade | n | taxa | ic_inf | ic_sup | climatologia | ganho |
|---|---|---|---|---|---|---|---|
| Acumulado de Chuva | área | 85 | 0.529 | 0.424 | 0.632 | 0.009 | 57.9 |
| Acumulado de Chuva | ponto | 2785 | 0.069 | 0.06 | 0.079 | 0.009 | 7.6 |
| Chuvas Intensas | área | 262 | 0.286 | 0.235 | 0.344 | 0.014 | 20.9 |
| Chuvas Intensas | ponto | 9240 | 0.026 | 0.023 | 0.03 | 0.014 | 1.9 |
| Tempestade | área | 765 | 0.404 | 0.37 | 0.439 | 0.013 | 30.6 |
| Tempestade | ponto | 42238 | 0.05 | 0.048 | 0.053 | 0.013 | 3.8 |

### A lacuna, só por chuva

| grupo | ponto | área | razao | diferenca |
|---|---|---|---|---|
| Grande Perigo | 0.031 | 0.591 | 19.1 | 0.56 |
| Perigo | 0.075 | 0.564 | 7.5 | 0.489 |
| Perigo Potencial | 0.038 | 0.309 | 8.1 | 0.271 |

## A lacuna

O resultado central: quanta informação se perde entre *o aviso é correto para a região* e *o aviso diz algo sobre a minha rua*.

**A leitura principal é a RAZÃO** — quantas vezes o aviso se confirma na área em relação ao ponto. Ela é adimensional e responde direto à pergunta do usuário do alerta.

As duas colunas contam coisas diferentes e por isso ficam lado a lado. A **diferença** é quase constante entre os níveis de severidade (0,575, 0,589 e 0,583), o que é uma regularidade notável. A **razão** varia de 3,1x a 17,9x, e essa variação é informativa: quanto mais severo o aviso, maior a razão — chuva extrema é espacialmente mais concentrada que chuva moderada, então o alerta de área perde mais significado no ponto justamente nos casos mais graves.


### Por severidade

| grupo | ponto | área | razao | diferenca |
|---|---|---|---|---|
| Grande Perigo | 0.034 | 0.609 | 17.9 | 0.575 |
| Perigo | 0.143 | 0.732 | 5.1 | 0.589 |
| Perigo Potencial | 0.281 | 0.864 | 3.1 | 0.583 |

### Por tipo

| grupo | ponto | área | razao | diferenca |
|---|---|---|---|---|
| Acumulado de Chuva | 0.069 | 0.529 | 7.7 | 0.46 |
| Chuvas Intensas | 0.258 | 0.786 | 3 | 0.528 |
| Tempestade | 0.228 | 0.86 | 3.8 | 0.632 |
| Vendaval | 0.38 | 0.87 | 2.3 | 0.49 |

## Ao lado da previsão do ECMWF, nos mesmos estação-dias

Ler na **horizontal**: fixando a taxa de confirmação (coluna `precisao`), qual fonte captura mais eventos? Isso mantém constante a tolerância a alarme não confirmado dos dois lados, e é a única comparação legítima entre um aviso de risco e uma regra automática de corte.

**Os avisos não são independentes do ECMWF** — o INMET usa modelos globais para emiti-los. A comparação é *aviso curado por meteorologista, por área* contra *regra automática de corte*, não humano contra máquina do zero.

| fonte | alertas | acertos | precisao | recall |
|---|---|---|---|---|
| aviso INMET, severidade >= 6 | 11025 | 314 | 0.028 | 0.981 |
| aviso INMET, severidade >= 7 | 5017 | 284 | 0.057 | 0.887 |
| aviso INMET, severidade >= 8 | 871 | 143 | 0.164 | 0.447 |


| fonte | alertas | acertos | precisao | recall |
|---|---|---|---|---|
| ECMWF > 5 mm | 4925 | 315 | 0.064 | 0.984 |
| ECMWF > 10 mm | 3138 | 297 | 0.095 | 0.928 |
| ECMWF > 15 mm | 2176 | 286 | 0.131 | 0.894 |
| ECMWF > 20 mm | 1487 | 266 | 0.179 | 0.831 |
| ECMWF > 25 mm | 1058 | 246 | 0.233 | 0.769 |
| ECMWF > 30 mm | 750 | 227 | 0.303 | 0.709 |
| ECMWF > 40 mm | 419 | 183 | 0.437 | 0.572 |
| ECMWF > 50 mm | 244 | 130 | 0.533 | 0.406 |
| ECMWF > 60 mm | 123 | 82 | 0.667 | 0.256 |
| ECMWF > 75 mm | 35 | 26 | 0.743 | 0.081 |

## Cobertura da extração de critérios

Critério de chuva extraído em **95.1%** dos pares e critério de vento em **95.1%**. A comparação usa 24,195 estação-dias com previsão disponível, contendo 320 eventos.


## Limitações

- Os avisos não são independentes da previsão do ECMWF (acima).
- O critério vem de texto livre; a cobertura da extração está declarada acima.
- Municípios sem estação não entram: a lacuna medida é a que as estações enxergam.
- A ordem temporal dos identificadores não é estrita — 188 quebras e recuo máximo de 6 dias. Por isso a colheita levou margem de 100 identificadores de cada lado, que resgatou 15 avisos dentro da janela.
- **Rajada é medida num ponto e vendaval convectivo é fenômeno de escala pequena.** A estação pode não estar onde o vento passou, o que deprime a confirmação de vendaval por razão instrumental, não meteorológica.

- Células com menos de 30 avisos foram omitidas do cruzamento tipo x severidade: o intervalo de Wilson nelas vai de quase zero a quase um e não sustenta afirmação.
