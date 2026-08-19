# Degradação com previsão em vez de reanálise

Gerado em 19/08/2026 10:50

Threshold fixo de `models/threshold.json`: 0.260 (não reajustado no teste — reajustar seria vazamento).

Fonte da previsão: `ecmwf_ifs025` do historical-forecast-api. Sem o `models` explícito a API devolve o mesmo ERA5 do archive-api, e a medição daria degradação zero por construção.

## Por estação-dia, agregando por max

Unidade dos relatórios anteriores. Serve para comparar as variantes entre si, **não** para comparar com a persistência (ver a última seção).

| variante | F1 | precisão | recall | PR-AUC |
|---|---|---|---|---|
| A referência | 0.3274 | 0.2970 | 0.3648 | 0.2426 |
| B só origem | 0.3075 | 0.3052 | 0.3099 | 0.2276 |
| C só janela | 0.2197 | 0.4146 | 0.1495 | 0.2566 |
| D realista | 0.1632 | 0.3884 | 0.1033 | 0.2352 |

- **B − A** (custo de trocar a fonte): PR-AUC -0.0150
- **C − A** (custo do desalinhamento de janela): PR-AUC +0.0140
- **D − A** (o que a aplicação perde de verdade): PR-AUC -0.0074

## Operacional — um alerta por estação-dia, emitido às 12 UTC

É o enquadramento do produto, e o único em que a comparação com a persistência é limpa: modelo e régua olham a mesma janela futura a partir do mesmo instante. 16652 estação-dias, 195 eventos (1.17%).

| variante | PR-AUC | persistência | ganho |
|---|---|---|---|
| A referência | 0.0787 | 0.0228 | +244.8% |
| B só origem | 0.0825 | 0.0228 | +261.4% |
| C só janela | 0.1131 | 0.0228 | +395.7% |
| D realista | 0.1085 | 0.0228 | +375.4% |

## Por que a persistência não serve como régua na agregação por max

Naquela unidade a persistência marca 0.2900 contra 0.2426 do modelo — e isso é artefato, não resultado. O max de `chuva_24h` do dia cai na hora 0 em 65% dos dias e na hora 23 em outros 6%, e a janela de 24 h passada nessas horas sobrepõe a chuva do próprio dia que o alvo tenta prever. A persistência deixa de ser previsão e vira diagnóstico. Em hora fixa de emissão o modelo ganha por larga margem, como mostra a tabela acima.

## Limitações — o que este número ainda não prova

1. **D é otimista, e a causa é o instante de emissão.** O historical-forecast-api devolve, para cada hora `h`, o valor da rodada mais recente ANTES de `h`. Um sistema real decidindo às 12 UTC usa uma única rodada emitida até as 12 UTC, com leads de 1 a 24 h. A média `t+1..t+24` de D mistura leads e inclui valores de rodadas emitidas até 23 h DEPOIS do momento da decisão. As variantes `*_previous_dayN`, que teriam lead fixo, não carregam as nossas variáveis — por isso a colheita diária de previsões reais (Task 5) continua sendo o único caminho para o número definitivo.
2. **O modelo foi treinado com ERA5 em `t`** e aqui é avaliado com uma distribuição diferente nas 8 colunas. Que ainda assim melhore sugere que retreinar já com a janela alinhada renderia mais — não testado.
3. **O threshold não transfere.** O corte de 0,26 foi calibrado na distribuição da variante A; em C e D as probabilidades deslocam para baixo e o recall por estação-dia cai de 0,36 para 0,10 com a precisão subindo. Recalibrar exige a previsão da janela de validação (jan–ago/2025), que ainda não está em cache.
4. **Uma janela de teste só**, 195 eventos às 12 UTC. Sem repetição de semente.

A variante A precisa reproduzir o relatório de referência (F1 0,3274 | P 0,2970 | R 0,3648 | PR-AUC 0,2426). Se não reproduzir, o harness está errado e as outras três não significam nada.
