# Brief de design — abas Alerta e Registro do VAND

Para colar no Claude Design. Descreve as duas telas que faltam do aplicativo; a
aba Estudar já está construída em `app/`.

---

## O produto em cinco linhas

Aplicativo para o Rio Grande do Sul que **retransmite o aviso meteorológico
oficial do INMET por localização**. Não é um modelo próprio disparando alerta: a
nossa previsão entra como camada consultável ao lado do aviso oficial, nunca
como notificação empurrada. Coleta também registros de alagamento enviados pelo
cidadão. Três abas na barra inferior: **Alerta**, **Registro**, **Estudar**.

Entrega: protótipo navegável, uma pessoa, até outubro de 2026. O protótipo **não
implementa notificação de verdade** — as maquetes de notificação são
especificação de tela, para que a apresentação demonstre a decisão em vez de
apenas descrevê-la.

## A marca

![Logo do VAND](../../Logo%20sem%20fundo.png)

Arquivo: `Logo sem fundo.png` na raiz do repositório, PNG com fundo
transparente, 551 × 198 px (proporção 2,78:1).

Três elementos, três cores, medidas do arquivo:

| elemento | cor | papel |
| --- | --- | --- |
| monograma (a forma entrelaçada) | `#2f5e3a` verde-floresta | símbolo, funciona sozinho |
| wordmark "VAND" | `#3b6b7f` azul-ardósia | assinatura, só acompanha |
| ponto superior esquerdo | `#ec1b04` vermelho | acento, 683 px de arte |

**O verde da marca passa a ser o acento do aplicativo.** A paleta segue a marca,
não o contrário — e o valor é bom de qualquer forma: `#2f5e3a` sobre branco dá
7,55:1, nível AAA.

### Duas coisas a resolver com a marca

**1. Ela não sobrevive no tema escuro.** Com fundo transparente sobre `#0d1410`,
o monograma fica em 2,26:1 e o wordmark em 3,22:1 — os dois reprovam. É preciso
uma **variante clara da marca**, e não basta clarear o PNG: os valores que
funcionam são monograma `#6cc98a` (9,2:1) e wordmark `#8fbfd0` (9,4:1). Desenhar
as duas versões, claro e escuro, como entregas separadas.

**2. O ponto é vermelho, e vermelho está reservado.** A regra de cor acima diz
que a faixa quente pertence exclusivamente à Severidade do Aviso. O `#ec1b04` do
ponto a viola. Duas saídas, e é decisão de quem assina o projeto:

- **Abrir exceção explícita para a marca** no ADR 0003. É o caminho usual — logo
  costuma ficar fora de regra semântica de cor. Exige então uma segunda regra: a
  marca **não aparece no cabeçalho persistente** de nenhuma tela, só em abertura,
  splash e tela "sobre". Um ponto vermelho fixo no topo, ao lado de um chip de
  Severidade, cria exatamente a ambiguidade que a regra existe para evitar.
- **Recolorir o ponto.** Mantém o ADR intacto e a marca utilizável em qualquer
  posição, ao custo de mexer numa identidade já feita.

Enquanto isso não se decide, o brief assume a primeira: marca fora do cabeçalho.

## Vocabulário obrigatório

Estas palavras aparecem na interface e não podem ser trocadas por sinônimos:

- **Aviso** — o alerta meteorológico emitido pelo INMET. É de terceiro; nós
  retransmitimos. Não escrever "alerta" para designá-lo, nem "warning".
- **Severidade** — o grau oficial do Aviso: Perigo Potencial, Perigo, Grande
  Perigo. Não escrever "nível", "gravidade" ou "criticidade".
- **Previsão** — a saída do nosso modelo. Nunca dispara notificação. Não
  escrever "predição" nem "alerta nosso".
- **Registro** — a observação de alagamento enviada por um cidadão. Inclui o
  "não está alagado". Não escrever "report", "ocorrência" nem "denúncia".

## Restrição de cor não-negociável

**Amarelo, laranja e vermelho pertencem exclusivamente à Severidade do Aviso**, e
a cor vem do campo `aviso_cor` do próprio INMET. Nenhum desses tons pode aparecer
como cor decorativa, de acento, de botão primário ou de ilustração em lugar
nenhum do aplicativo. Se a paleta de um componente importado usa laranja de
destaque, a paleta muda — o componente não fica.

## Paleta: verde

O aplicativo é verde, e o verde é o da marca. Neutros levemente esverdeados,
acento em `#2f5e3a` — o mesmo verde-floresta do monograma — no tema claro, e a
sua versão clara `#6cc98a` no escuro. Toda a faixa quente continua reservada à
Severidade, com a ressalva sobre o ponto da marca discutida acima.

| token | claro | escuro |
| --- | --- | --- |
| fundo | `#f6f8f6` | `#0d1410` |
| superfície | `#ffffff` | `#151e18` |
| superfície 2 | `#eaf0ea` | `#1e2a22` |
| borda | `#d6e0d6` | `#2a3a30` |
| texto | `#14201a` | `#e6ece8` |
| texto secundário | `#55685c` | `#93a49a` |
| **acento (verde da marca)** | `#2f5e3a` | `#6cc98a` |
| acento suave | `#dcefe1` | `#16301f` |
| texto sobre acento | `#ffffff` | `#06200f` |

Contraste conferido par a par: nenhum fica abaixo de 4,5:1. O acento dá 7,55:1
no claro e 8,42:1 no escuro, ambos AAA. Raio de borda 14px, barra de abas 62px.

### O verde tem dois riscos, e os dois têm solução

**1. Verde lê como "seguro".** Num aplicativo de aviso meteorológico isso é
perigoso se o verde virar fundo de tudo: a pessoa aprende que a tela verde
significa calma, e um Aviso de Grande Perigo chega dentro de uma moldura que diz
o contrário. A regra é: o verde é a cor da **interface** — barra de abas, botões,
links, seleção —, nunca a cor do **estado**. A tela sem Aviso vigente não é uma
tela verde; é uma tela neutra que diz, em texto, que não há aviso.

**2. O verde colide com o "sim".** A paleta antiga usava verde para o afirmativo.
Se o acento é verde e o "sim" também é, o "sim" ganha peso de ação principal — e
a tela de Registro exige que **sim e não pesem igual**. Então o par de resposta
sai do verde e passa a ser duas cores frias distintas, nenhuma delas o acento:

| resposta | claro | escuro |
| --- | --- | --- |
| sim, está alagado | `#2f5d8a` | `#8fb4dd` |
| não, está seco | `#6b3f5f` | `#e8a5cd` |
| não sei | usa `texto secundário` | usa `texto secundário` |

Azul-ardósia e ameixa: são distinguíveis entre si, distinguíveis do verde da
interface, e — de propósito — **nenhuma das duas parece o botão certo**.

---

## Telas a desenhar

### 1. Alerta — sem aviso vigente

**O estado mais comum, e o mais difícil.** 55% dos dias não têm aviso nenhum.
Precisa comunicar "está tudo calmo e o app está funcionando" sem parecer tela
quebrada, sem parecer tela vazia, e sem inventar tranquilidade que ninguém
mediu. Mostrar a localização ativa e a hora da última consulta.

### 2. Alerta — com aviso vigente

O dado já existe e vem pronto do INMET: severidade, tipo, período de vigência,
polígono, geocódigo IBGE, **riscos** e **instruções**. A tela exibe isso.

Ao lado, a **Previsão** como camada consultável — e a taxa que a acompanha
precisa estar visível, não escondida: no corte de 30 mm, a nossa regra captura
71% dos eventos com **30% de confirmação**. Sete de cada dez avisos nossos não se
confirmariam, e é por isso que a Previsão não empurra notificação. O número
aparece junto do número, não numa nota de rodapé.

**Regra editorial:** taxa de confirmação **não é** taxa de acerto. Um aviso
comunica risco; aviso não confirmado não é erro. A interface não pode marcar
avisos passados como "errados" — vale para o INMET e vale para nós.

### 3. Notificação — Grande Perigo (interrompe)

Maquete de tela de bloqueio ou banner. Acende a tela e vibra. Orçamento medido:
**6,4 por pessoa por ano**, pior mês 4.

Texto obrigatório: **"aviso de Grande Perigo para a sua região"** — nunca o nome
da rua. A confirmação no ponto exato é de 3,4%, então a lacuna medida precisa
estar dentro da própria frase, não numa explicação em outro lugar.

### 4. Notificação — Perigo (silencioso)

Selo na lista de avisos e ponto na aba. **Sem número.** Um badge com contagem lê
como caixa de e-mail e convida a limpar sem ler; o selo indica presença, não
quantidade. 45,1 por pessoa por ano, pior mês 12. Sem maquete de notificação.

### 5. Perigo Potencial — sem selo

Aparece só na lista. Presente para quem procura, invisível para quem não. Não
notifica.

Os três estados acima precisam ser alcançáveis na mesma navegação: a política
inteira demonstrável em três toques.

### 6. Registro — a pergunta

**É a tela mais importante do aplicativo, e a decisão que não tem conserto
retroativo.**

A pergunta é *"está alagado aí?"* com três respostas: **sim / não / não sei**.

As três precisam de **peso visual igual**. Se "sim" for botão grande e "não" for
um link discreto, ninguém responde "não" — e o dado vira só de presença, uma
lista de lugares que alagaram, com a qual não se aprende onde *não* alaga. O
"não" é o dado mais valioso que este aplicativo coleta e a interface precisa
querer recebê-lo tanto quanto o "sim".

O "não sei" existe para que ninguém chute. Ele não é descarte: é uma terceira
resposta legítima.

Justificativa técnica que a tela pode expor: alagamento **não é chuva**. Pela
definição oficial (COBRADE 1.2.3.0.0) ele é extrapolação da capacidade do
sistema de drenagem — não há uma palavra sobre atmosfera. Nenhum modelo
meteorológico prevê alagamento, e é por isso que a pergunta precisa ser feita a
uma pessoa.

### 7. Registro — depois de enviar

O que a pessoa vê ao confirmar. O registro guarda local, horário e **o Aviso
vigente naquele momento** — vale mostrar essa amarração, porque é ela que torna
o dado útil depois.

Evitar gamificação, pontuação e comemoração. A pessoa pode estar com água dentro
de casa.

### 8. Registro — o que há por perto (opcional)

Lista ou mapa dos registros recentes na região. Se existir, precisa mostrar os
"não" com o mesmo destaque dos "sim" — caso contrário reintroduz o viés de
presença pela porta dos fundos.

---

## Princípios que atravessam todas as telas

1. **Sem drama.** O orçamento de interrupção é 6,4 por ano. Uma interface que
   grita a cada aviso queima esse orçamento e ensina a ignorar.
2. **A incerteza aparece, não se esconde.** Todo número de confirmação vai junto
   do número que ele qualifica.
3. **"Para a sua região", nunca "na sua rua".** O aviso é produto de área
   recebido num ponto; a lacuna medida vai de 3,1x a 17,9x.
4. **Nada de acusar o INMET.** O enquadramento é lacuna de granularidade, não
   avaliação de quem prevê melhor.
5. **Acessibilidade acima do normal.** Isto é interface de emergência: contraste
   real, alvo de toque generoso, e nada que dependa só de cor para ser entendido
   — inclusive porque a cor está reservada à Severidade.

## Restrições técnicas

- **Mobile-first**, largura de referência 430px.
- **Tema claro e escuro**, ambos obrigatórios, ambos desenhados.
- **HTML, CSS e JavaScript puros.** Sem build, sem framework, sem back-end.
  Componente que chegar em React/Tailwind precisa ser reescrito — vale como
  referência visual, não como código.
- Roteamento por hash, progresso em `localStorage`, service worker para uso
  offline. O app precisa funcionar sem rede, porque enchente derruba rede.

## O que já existe e serve de referência

A aba **Estudar** está construída e é o padrão de **forma** a seguir: cartões
com borda de 1px, superfície branca sobre fundo levemente tingido, tipografia
sem serifa, seções empilhadas com respiro, glossário com barra de acento à
esquerda. Ver `app/styles.css`.

A **cor** dela, porém, ainda é a antiga — acento azul-petróleo `#0f6b66`. A
paleta verde acima é a nova, e o `app/styles.css` precisa ser migrado para ela.
Enquanto isso não acontece, copie a estrutura da aba Estudar e a cor desta
seção, não a cor que está na tela.
