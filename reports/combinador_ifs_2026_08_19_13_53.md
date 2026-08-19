# As estações do INMET acrescentam algo sobre a previsão do ECMWF?

Gerado em 19/08/2026 13:53

Combinador de poucos parâmetros (regressão logística), treinado na **validação** (2025-01 a 2025-08) e medido no **teste intocado** (2025-09 a 2026-07).

A validação é o único período em que as predições do nosso modelo são fora da amostra *e* existe previsão do IFS — treinar em 2024 usaria predição in-sample e inflaria o peso do nosso modelo.

Recalibração não pode melhorar estes números: PR-AUC mede ordenação e transformação monotônica a preserva. Qualquer ganho aqui é informação nova.

A coluna **validação** é dentro da amostra: é onde o combinador foi ajustado. Se uma variante ganha lá e perde no teste, é sobreajuste; se não ganha nem lá, a informação é genuinamente redundante.

| variante | PR-AUC validação (dentro) | PR-AUC estação-dia | PR-AUC operacional | ganho sobre o IFS |
|---|---|---|---|---|
| V0 IFS sozinho | 0.4690 | 0.4634 | 0.3888 | +0.0% |
| V1 IFS + nosso modelo | 0.5057 | 0.4881 | 0.3860 | -0.7% |
| V2 IFS + observação local | 0.4816 | 0.4793 | 0.3953 | +1.7% |
| V3 IFS + modelo + local | 0.5060 | 0.4910 | 0.3844 | -1.1% |
| V4 IFS + orvalho + pressão | 0.4698 | 0.4637 | 0.3900 | +0.3% |
| V5 árvore (com interação) | 0.7818 | 0.4063 | 0.3107 | -20.1% |

## Intervalo de confiança de 95% da diferença contra o IFS

Bootstrap pareado, 2000 reamostragens das mesmas unidades. Um intervalo que não cruza zero é ganho distinguível de variação amostral.

| variante | Δ estação-dia | IC 95% | Δ operacional | IC 95% |
|---|---|---|---|---|
| V1 IFS + nosso modelo | +0.0248 | [-0.0037, +0.0533] | -0.0021 | [-0.0342, +0.0289] |
| V2 IFS + observação local | +0.0161 | [+0.0002, +0.0310] | +0.0069 | [-0.0191, +0.0325] |
| V3 IFS + modelo + local | +0.0280 | [-0.0007, +0.0557] | -0.0038 | [-0.0370, +0.0282] |
| V4 IFS + orvalho + pressão | +0.0003 | [-0.0009, +0.0016] | +0.0013 | [-0.0004, +0.0033] |
| V5 árvore (com interação) | -0.0579 | [-0.0989, -0.0174] | -0.0776 | [-0.1301, -0.0291] |

## Coeficientes (features padronizadas)

Magnitude comparável entre si. Peso próximo de zero numa entrada significa que ela não acrescenta sobre as demais.

```
V1 IFS + nosso modelo
  {'ifs_log': 2.1884, 'p_modelo': 0.1757}
V2 IFS + observação local
  {'ifs_log': 2.3976, 'chuva_24h': 0.0195, 'chuva_3h': 0.0448, 'queda_pressao_24h': 0.0308, 'soil_moisture': 0.1045, 'clima_chuva_mes': 0.1825, 'viz_chuva_3h': -0.0239, 'umidade': -0.086, 'orvalho': -0.0088}
V3 IFS + modelo + local
  {'ifs_log': 2.2303, 'p_modelo': 0.1784, 'chuva_24h': 0.0032, 'chuva_3h': 0.0246, 'queda_pressao_24h': 0.0653, 'soil_moisture': 0.0248, 'clima_chuva_mes': 0.0497, 'viz_chuva_3h': -0.0323, 'umidade': -0.117, 'orvalho': -0.0853}
V4 IFS + orvalho + pressão
  {'ifs_log': 2.4544, 'orvalho': -0.0185, 'queda_pressao_24h': 0.0026}
```
