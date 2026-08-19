# Validação cruzada com o BDMEP diário

Gerado em 19/08/2026 09:39

Compara a soma horária da nossa pipeline com o total diário oficial do INMET, no dia pluviométrico (12 UTC → 12 UTC). Entram só os dias em que temos as 24 horas com medição válida — com cobertura parcial a nossa soma subestima o total por construção, e a divergência mediria a falha do sensor, não a da limpeza.

- estações comparadas: 74
- com r > 0,99: 74
- com r < 0,95: 0
- viés médio global: +0.0116 mm/dia
- cobertura (dias completos / dias do BDMEP): mediana 100.0%, pior 52.0%
- fora da comparação: 23

## Piores encaixes

| estacao | situacao | dias | cobertura_% | r | iguais_% | vies_mm | total_nosso | total_bdmep | eventos_nossos | eventos_bdmep |
|---|---|---|---|---|---|---|---|---|---|---|
| B825 | ok | 254.0 | 100.0 | 0.9954 | 99.2126 | -0.0587 | 839.5 | 854.4 | 1.0000 | 1.0000 |
| B831 | ok | 108.0 | 100.0 | 0.9983 | 98.1481 | 0.0528 | 383.3 | 377.6 | 0.0000 | 0.0000 |
| B841 | ok | 251.0 | 100.0 | 0.9983 | 98.8048 | 0.0587 | 982.7 | 968.0 | 4.0000 | 4.0000 |
| B846 | ok | 119.0 | 100.0 | 0.9985 | 94.9580 | 0.1697 | 459.7 | 439.5 | 1.0000 | 1.0000 |
| A805 | ok | 3,733.0 | 99.9732 | 0.9986 | 98.4731 | 0.0547 | 18,642.8 | 18,438.5 | 81.0000 | 81.0000 |
| B836 | ok | 266.0 | 100.0 | 0.9986 | 98.1203 | 0.0102 | 697.0 | 694.3 | 3.0000 | 3.0000 |
| B817 | ok | 263.0 | 100.0 | 0.9989 | 98.8593 | 0.0337 | 1,093.2 | 1,084.4 | 3.0000 | 3.0000 |
| B816 | ok | 214.0 | 100.0 | 0.9990 | 96.7290 | 0.0558 | 957.0 | 945.0 | 4.0000 | 4.0000 |
| A844 | ok | 3,707.0 | 99.9730 | 0.9991 | 98.8131 | 0.0320 | 17,241.7 | 17,123.0 | 47.0000 | 46.0000 |
| A852 | ok | 3,681.0 | 99.9728 | 0.9992 | 98.8318 | 0.0388 | 20,083.3 | 19,940.4 | 89.0000 | 87.0000 |
| B811 | ok | 287.0 | 100.0 | 0.9992 | 98.6063 | -0.0178 | 1,201.3 | 1,206.4 | 4.0000 | 4.0000 |
| B815 | ok | 129.0 | 52.0161 | 0.9992 | 98.4496 | -0.0279 | 497.7 | 501.3 | 2.0000 | 2.0000 |
| A812 | ok | 4,001.0 | 99.9750 | 0.9992 | 99.5501 | 0.0139 | 19,952.8 | 19,897.0 | 79.0000 | 77.0000 |
| A826 | ok | 3,815.0 | 100.0 | 0.9993 | 99.3971 | 0.0242 | 17,314.8 | 17,222.5 | 80.0000 | 78.0000 |
| A809 | ok | 3,573.0 | 99.9720 | 0.9994 | 99.3003 | 0.0205 | 13,331.2 | 13,257.9 | 49.0000 | 48.0000 |

## Menor cobertura

Dias completos como fração dos dias que o BDMEP tem. Cobertura baixa é sensor fora do ar, não erro de limpeza — mas é o que limita quantos dias daquela estação chegam ao treino.

| estacao | dias | cobertura_% | r | vies_mm |
|---|---|---|---|---|
| B815 | 129.0 | 52.0161 | 0.9992 | -0.0279 |
| B807 | 753.0 | 75.1497 | 1.0000 | 0.0000 |
| A808 | 2,655.0 | 89.9695 | 0.9999 | 0.0109 |
| A894 | 3,422.0 | 97.9954 | 0.9999 | 0.0079 |
| A804 | 2,777.0 | 98.1619 | 0.9999 | 0.0144 |
| B819 | 288.0 | 98.6301 | 0.9999 | 0.0090 |
| A840 | 3,637.0 | 98.6974 | 0.9997 | 0.0190 |
| A854 | 3,962.0 | 98.9510 | 0.9994 | 0.0104 |
| A882 | 3,335.0 | 99.0790 | 1.0000 | 0.0001 |
| A836 | 3,893.0 | 99.2100 | 0.9995 | 0.0132 |

## Fora da comparação

| estacao | situacao | cobertura_% |
|---|---|---|
| B833 | só 84 dias completos | 100.0 |
| B834 | só 62 dias completos | 100.0 |
| B835 | só 61 dias completos | 100.0 |
| B837 | só 79 dias completos | 100.0 |
| B838 | só 25 dias completos | 100.0 |
| B840 | só 75 dias completos | 100.0 |
| B842 | só 97 dias completos | 100.0 |
| B843 | só 57 dias completos | 100.0 |
| B844 | só 69 dias completos | 100.0 |
| B845 | só 0 dias completos | 0.0000 |
| B847 | só 23 dias completos | 100.0 |
| B848 | só 0 dias completos | 0.0000 |
| B849 | só 0 dias completos | 0.0000 |
| B851 | só 89 dias completos | 100.0 |
| B852 | só 88 dias completos | 100.0 |
| B853 | só 81 dias completos | 100.0 |
| B856 | só 0 dias completos | 0.0000 |
| B857 | só 0 dias completos | 0.0000 |
| B858 | só 24 dias completos | 100.0 |
| B859 | só 83 dias completos | 100.0 |
| B860 | só 57 dias completos | 100.0 |
| B861 | só 38 dias completos | 100.0 |
| B862 | só 75 dias completos | 100.0 |
