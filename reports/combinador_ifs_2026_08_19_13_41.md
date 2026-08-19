# As estações do INMET acrescentam algo sobre a previsão do ECMWF?

Gerado em 19/08/2026 13:41

Combinador de poucos parâmetros (regressão logística), treinado na **validação** (2025-01 a 2025-08) e medido no **teste intocado** (2025-09 a 2026-07).

A validação é o único período em que as predições do nosso modelo são fora da amostra *e* existe previsão do IFS — treinar em 2024 usaria predição in-sample e inflaria o peso do nosso modelo.

Recalibração não pode melhorar estes números: PR-AUC mede ordenação e transformação monotônica a preserva. Qualquer ganho aqui é informação nova.

A coluna **validação** é dentro da amostra: é onde o combinador foi ajustado. Se uma variante ganha lá e perde no teste, é sobreajuste; se não ganha nem lá, a informação é genuinamente redundante.

| variante | PR-AUC validação (dentro) | PR-AUC estação-dia | PR-AUC operacional | ganho sobre o IFS |
|---|---|---|---|---|
| V0 IFS sozinho | 0.4690 | 0.4634 | 0.3888 | +0.0% |
| V1 IFS + nosso modelo | 0.4919 | 0.4614 | 0.3535 | -9.1% |
| V2 IFS + observação local | 0.4338 | 0.4372 | 0.3477 | -10.6% |
| V3 IFS + modelo + local | 0.4508 | 0.4427 | 0.3131 | -19.5% |
| V4 IFS + orvalho + pressão | 0.4474 | 0.4229 | 0.3472 | -10.7% |
| V5 árvore (com interação) | 0.7191 | 0.4281 | 0.3307 | -14.9% |

## Coeficientes (features padronizadas)

Magnitude comparável entre si. Peso próximo de zero numa entrada significa que ela não acrescenta sobre as demais.

```
V1 IFS + nosso modelo
  {'ifs_log': 1.9369, 'p_modelo': 0.2923}
V2 IFS + observação local
  {'ifs_log': 2.1802, 'chuva_24h': -0.1108, 'chuva_3h': 0.081, 'queda_pressao_24h': 0.1872, 'soil_moisture': 0.1327, 'clima_chuva_mes': 0.0804, 'viz_chuva_3h': 0.0015, 'umidade': -0.0701, 'orvalho': 0.2834}
V3 IFS + modelo + local
  {'ifs_log': 2.0333, 'p_modelo': 0.399, 'chuva_24h': -0.1425, 'chuva_3h': 0.0537, 'queda_pressao_24h': 0.2294, 'soil_moisture': 0.0048, 'clima_chuva_mes': -0.1748, 'viz_chuva_3h': -0.0217, 'umidade': -0.1062, 'orvalho': 0.2281}
V4 IFS + orvalho + pressão
  {'ifs_log': 2.1967, 'orvalho': 0.211, 'queda_pressao_24h': 0.1495}
```
