# A lacuna de granularidade do alerta regional

**Desenho do estudo** — documento de projeto, não de resultado. Nenhum número
aqui foi medido ainda.

Escrito em 20/08/2026.

---

## 1. A pergunta

Um aviso meteorológico do INMET cobre uma região inteira — o exemplo que
inspecionamos abrangia **197 municípios do Rio Grande do Sul**. A pessoa que
recebe esse aviso mora num ponto, não numa região.

Este estudo mede **quanta informação sobrevive da região até o ponto**: com que
frequência o que o aviso anuncia se observa na área coberta, e com que frequência
se observa na estação mais próxima de quem foi avisado.

A distância entre esses dois números é o objeto do estudo.

## 2. Por que agora

Três medições anteriores deste projeto delimitam o espaço onde ainda há algo a
descobrir:

- A previsão de chuva do **ECMWF** (*European Centre for Medium-Range Weather
  Forecasts*), pelo modelo **IFS** (*Integrated Forecasting System*), prevê
  eventos extremos no RS com desempenho substancial: ordena os dias cerca de 32
  vezes melhor que o acaso.
- A observação local das estações **não acrescenta** sobre essa previsão. Medido
  em 20/08/2026 com intervalo de confiança e verificação de encanamento; o
  resultado é negativo e conclusivo.
- Traduzida em regra de operação, a previsão europeia crua entrega, por exemplo,
  71% dos eventos acima de 50 mm com 30% de confirmação, a cinco avisos por
  estação-ano.

O que **não** foi medido em lugar nenhum é o desempenho dos avisos oficiais
contra observação de superfície, e menos ainda a diferença entre o nível da área
e o nível do ponto. É a lacuna que este estudo ocupa, e ela é exatamente a
justificativa técnica do aplicativo.

## 3. Como um aviso deve ser verificado — e como NÃO deve

**Este é o ponto mais importante do desenho, e ele corrige um erro.**

Um aviso meteorológico não é uma afirmação determinística. Quando o INMET emite
"chuva de até 50 mm/dia", ele não está dizendo *"vai chover 50 mm"* — está
dizendo *"há risco relevante de chover 50 mm"*. Se não chover, **o aviso não
estava errado**: a possibilidade existia, e comunicá-la era a função dele.

Verificar aviso como acerto ou erro binário é o equívoco clássico da avaliação de
sistemas de alerta, e produz a conclusão falsa de que serviços meteorológicos
"erram muito". Serviços de alerta **aceitam deliberadamente** alta taxa de não
confirmação em eventos de alto impacto, porque o custo de não avisar é
assimétrico em relação ao custo de avisar à toa.

Portanto, este estudo **não mede erro**. Ele mede:

> **Taxa de confirmação observada** — entre todos os avisos de um dado nível de
> severidade, em que fração o fenômeno anunciado foi de fato registrado.

Isso é uma afirmação de **calibração**, não de acerto. Se "Perigo Potencial"
confirma em 3 de cada 10 casos de forma estável, isso não é 70% de erro: é a
informação de que aquele nível corresponde a aproximadamente uma chance em três —
e é precisamente o que o cidadão precisa saber ao receber a notificação.

**A mesma régua se aplica a nós.** Os "30% de precisão" da nossa regra sobre o
ECMWF são uma taxa de confirmação, não uma taxa de erro. Seria desonesto aplicar
a leitura generosa ao INMET e a leitura severa a nós mesmos.

**O que continua sendo comparação legítima:** mantendo a taxa de confirmação
constante, qual fonte captura mais eventos? Essa pergunta é justa porque fixa a
tolerância a alarme não confirmado nos dois lados. É o que uma curva de
precisão-recall faz, e é por isso que a comparação com o ECMWF sobrevive à
mudança de vocabulário.

Em resumo: a ressalva muda a **interpretação e o vocabulário**, não a aritmética.

## 4. As duas unidades

| unidade | pergunta | o que ela representa |
|---|---|---|
| **Área** | dado um aviso, **alguma** estação dentro do polígono registrou o fenômeno anunciado? | é o nível em que o aviso é emitido; é justo com quem o emitiu |
| **Ponto** | dado que o aviso cobre o meu município, o fenômeno ocorreu na **minha** estação? | é o que a pessoa avisada experimenta |

As duas são sempre reportadas juntas. Isoladas, qualquer uma delas engana: a de
área superestima o que o aviso significa para o indivíduo, e a de ponto
subestima a qualidade do trabalho de quem emitiu.

## 5. Critério de confirmação

Cada aviso traz, em texto livre, o que promete. Exemplo real (id 45000):

> "Chuva entre 20 e 30 mm/h ou até 50 mm/dia, ventos intensos (40-60 km/h).
> Baixo risco de corte de energia elétrica, queda de galhos de árvores,
> alagamentos…"

Dois princípios:

1. **Cada aviso é verificado contra o critério que ele mesmo anuncia**, não
   contra um limiar imposto por nós. A pergunta vira *"quando o INMET anunciou
   50 mm/dia, registrou-se 50 mm?"* — mais justa e mais difícil de contestar.
2. **Os critérios são compostos.** O aviso acima promete chuva **e** vento. Ele
   conta como confirmado se **qualquer** um dos fenômenos anunciados ocorreu.
   Exigir os dois penalizaria um aviso que acertou o vendaval e não a chuva.

Secundariamente, tudo é recalculado contra o limiar fixo de 50 mm em 24 h, para
que o resultado converse com as demais medições do projeto.

## 6. Recorte

**Tipos incluídos** — os quatro com verdade de campo nas estações de superfície:

| tipo | verdade de campo | unidade do critério |
|---|---|---|
| Chuvas Intensas | soma de chuva em 24 h | mm/dia |
| Tempestade | idem | mm/dia |
| Acumulado de Chuva | idem | mm/dia |
| Vendaval | máximo de `VENTO, RAJADA MAXIMA` na vigência | km/h |

**Excluídos:** Baixa Umidade, Declínio de Temperatura e Ventos Costeiros — sem
verdade de campo aplicável a estações de superfície em terra.

**Fonte dos avisos:** `https://apiprevmet3.inmet.gov.br/aviso/getByID/<id>`.
Os identificadores são sequenciais no tempo; a janela de avaliação corresponde
aos ids **49435** (02/01/2025) a **55192** (31/07/2026) — **5.757 avisos**,
Brasil inteiro, dos quais o Rio Grande do Sul é subconjunto.

**Verdade de campo:** série horária do INMET, 95 estações, já auditada contra o
BDMEP (*Banco de Dados Meteorológicos para Ensino e Pesquisa*) com correlação
acima de 0,999.

**Casamento:** a estação pertence ao aviso se o geocódigo IBGE do seu município
consta em `geocodes`, com o polígono GeoJSON como conferência. O dia conta se a
vigência do aviso intersecta a janela de 24 horas ancorada às 12 UTC — o início
do dia pluviométrico do INMET.

**Avisos sobrepostos** no mesmo estação-dia: vale o de maior severidade.
**Ausência de aviso** é o negativo que fecha a tabela.

## 7. O que o estudo entrega

1. **Taxa de confirmação por nível de severidade**, em área e em ponto, com
   intervalo de confiança.
2. **A lacuna** — a diferença entre as duas, que é o resultado principal e a
   justificativa quantitativa do aplicativo.
3. **Os níveis de severidade do INMET plotados sobre a curva de
   precisão-recall do ECMWF**, recalculada na unidade de área para que a
   comparação seja legítima.
4. **Cobertura da extração**: em que fração dos avisos o critério anunciado foi
   extraível do texto livre.

## 8. Limitações que vão declaradas no relatório

- **Os avisos não são independentes do ECMWF.** O INMET usa modelos globais para
  emiti-los. A comparação é "aviso curado por meteorologista, por área" contra
  "regra automática de corte, por ponto" — não humano contra máquina do zero.
- **Extração de texto livre** é o principal risco técnico. Uma amostra será
  conferida à mão antes de qualquer número virar tabela, e a fração não
  extraível entra no relatório.
- **Cobertura espacial das estações.** Municípios sem estação não entram; a
  lacuna medida é a que as 95 estações conseguem enxergar.
- **Monotonicidade dos identificadores** foi assumida na localização da janela e
  precisa de verificação por amostragem.
- **Rajada é medida pontualmente** e vendaval convectivo é fenômeno de escala
  pequena: a estação pode simplesmente não estar onde o vento passou. Isso
  deprime a taxa de confirmação de vendaval por razão instrumental, não
  meteorológica, e precisa ser dito.

## 9. Fases

| fase | conteúdo | custo |
|---|---|---|
| A | coleta dos 5.757 avisos, com passadas e pausa | 1–2 h, segundo plano |
| B | casamento com estação-dia, extração dos critérios, contingência | 1 sessão |
| C | curva do ECMWF em unidade de área e relatório final | 1 sessão |

Nenhum modelo é treinado. O estudo reaproveita a agregação por estação-dia, a
varredura de corte e o padrão de coleta já existentes no repositório.
