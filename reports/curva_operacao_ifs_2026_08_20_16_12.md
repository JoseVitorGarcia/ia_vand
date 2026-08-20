# Se a defesa civil alertar quando o ECMWF prevê mais de X mm, o que ela recebe?

Gerado em 20/08/2026 16:12

**IFS** (*Integrated Forecasting System*) é o modelo global de previsão do **ECMWF** (*European Centre for Medium-Range Weather Forecasts*).

Todas as medições anteriores deste projeto usam **PR-AUC** (área sob a curva precisão-recall), que mede ordenação. Ordenação não diz quantos alertas você dispara. Esta página traduz a previsão em regra de operação.

Janela: **2025-01-02 a 2026-07-30** (1.57 anos), 95 estações, 24,444 estação-dias. Um alerta por estação-dia, emitido às 12 UTC — o início do dia pluviométrico do INMET.

A regra é **"alerta quando o ECMWF prevê mais de X mm nas próximas 24 h"**. O corte é em milímetros previstos, não em probabilidade de modelo: um operador audita a regra sem precisar saber o que é um classificador.


## Evento = mais de 50 mm em 24 h

324 eventos em 24,444 estação-dias (taxa base **1.33%**). Alertar sempre daria precisão de 1.33%; é essa a régua do acaso.

| corte (mm previstos) | alertas | acertos | precisão | recall | F1 | eventos perdidos | alertas por estação-ano |
|---|---|---|---|---|---|---|---|
| 0.5 | 10796 | 323 | 0.030 | 0.997 | 0.058 | 1 | 72.3 |
| 1 | 8738 | 323 | 0.037 | 0.997 | 0.071 | 1 | 58.5 |
| 2 | 7157 | 320 | 0.045 | 0.988 | 0.086 | 4 | 47.9 |
| 3 | 6207 | 320 | 0.052 | 0.988 | 0.098 | 4 | 41.6 |
| 5 | 4988 | 318 | 0.064 | 0.981 | 0.120 | 6 | 33.4 |
| 7.5 | 3986 | 309 | 0.078 | 0.954 | 0.143 | 15 | 26.7 |
| 10 | 3179 | 300 | 0.094 | 0.926 | 0.171 | 24 | 21.3 |
| 15 | 2207 | 288 | 0.130 | 0.889 | 0.228 | 36 | 14.8 |
| 20 | 1508 | 270 | 0.179 | 0.833 | 0.295 | 54 | 10.1 |
| 25 | 1074 | 252 | 0.235 | 0.778 | 0.361 | 72 | 7.2 |
| 30 | 760 | 230 | 0.303 | 0.710 | 0.424 | 94 | 5.1 |
| 40 | 423 | 180 | 0.426 | 0.556 | 0.482 | 144 | 2.8 |
| 50 | 247 | 128 | 0.518 | 0.395 | 0.448 | 196 | 1.7 |
| 60 | 125 | 81 | 0.648 | 0.250 | 0.361 | 243 | 0.8 |
| 75 | 35 | 24 | 0.686 | 0.074 | 0.134 | 300 | 0.2 |
| 100 | 6 | 3 | 0.500 | 0.009 | 0.018 | 321 | 0.0 |

**Melhor F1:** corte de 42 mm — precisão 0.457, recall 0.512, 363 alertas (2.4 por estação-ano).


**Se o custo de não avisar for o que manda** — o caso da defesa civil — o corte desce e a precisão cai junto:

| recall pedido | corte (mm) | alertas | precisão | alertas por estação-ano |
|---|---|---|---|---|
| 50% | 42.9 | 347 | 0.467 | 2.3 |
| 60% | 36.6 | 509 | 0.383 | 3.4 |
| 70% | 30.9 | 706 | 0.322 | 4.7 |
| 80% | 22.8 | 1261 | 0.207 | 8.4 |
| 90% | 12.9 | 2568 | 0.114 | 17.2 |

**Nosso modelo, na mesma janela e mesma unidade:** melhor F1 0.214 (precisão 0.289, recall 0.170) contra 0.483 do IFS. A janela é fora da amostra para ele — o treino termina em 2024-12-31.


## Evento = mais de 30 mm em 24 h

907 eventos em 24,444 estação-dias (taxa base **3.71%**). Alertar sempre daria precisão de 3.71%; é essa a régua do acaso.

| corte (mm previstos) | alertas | acertos | precisão | recall | F1 | eventos perdidos | alertas por estação-ano |
|---|---|---|---|---|---|---|---|
| 0.5 | 10796 | 901 | 0.083 | 0.993 | 0.154 | 6 | 72.3 |
| 1 | 8738 | 895 | 0.102 | 0.987 | 0.186 | 12 | 58.5 |
| 2 | 7157 | 885 | 0.124 | 0.976 | 0.219 | 22 | 47.9 |
| 3 | 6207 | 877 | 0.141 | 0.967 | 0.247 | 30 | 41.6 |
| 5 | 4988 | 858 | 0.172 | 0.946 | 0.291 | 49 | 33.4 |
| 7.5 | 3986 | 831 | 0.208 | 0.916 | 0.340 | 76 | 26.7 |
| 10 | 3179 | 792 | 0.249 | 0.873 | 0.388 | 115 | 21.3 |
| 15 | 2207 | 717 | 0.325 | 0.791 | 0.461 | 190 | 14.8 |
| 20 | 1508 | 644 | 0.427 | 0.710 | 0.533 | 263 | 10.1 |
| 25 | 1074 | 545 | 0.507 | 0.601 | 0.550 | 362 | 7.2 |
| 30 | 760 | 456 | 0.600 | 0.503 | 0.547 | 451 | 5.1 |
| 40 | 423 | 319 | 0.754 | 0.352 | 0.480 | 588 | 2.8 |
| 50 | 247 | 198 | 0.802 | 0.218 | 0.343 | 709 | 1.7 |
| 60 | 125 | 105 | 0.840 | 0.116 | 0.203 | 802 | 0.8 |
| 75 | 35 | 30 | 0.857 | 0.033 | 0.064 | 877 | 0.2 |
| 100 | 6 | 4 | 0.667 | 0.004 | 0.009 | 903 | 0.0 |

**Melhor F1:** corte de 26 mm — precisão 0.526, recall 0.584, 1008 alertas (6.8 por estação-ano).


**Se o custo de não avisar for o que manda** — o caso da defesa civil — o corte desce e a precisão cai junto:

| recall pedido | corte (mm) | alertas | precisão | alertas por estação-ano |
|---|---|---|---|---|
| 50% | 30 | 760 | 0.600 | 5.1 |
| 60% | 24.9 | 1095 | 0.501 | 7.3 |
| 70% | 20.1 | 1493 | 0.428 | 10.0 |
| 80% | 14.1 | 2352 | 0.310 | 15.8 |
| 90% | 8.1 | 3779 | 0.218 | 25.3 |

**Nosso modelo, na mesma janela e mesma unidade:** melhor F1 0.330 (precisão 0.270, recall 0.423) contra 0.554 do IFS. A janela é fora da amostra para ele — o treino termina em 2024-12-31.

