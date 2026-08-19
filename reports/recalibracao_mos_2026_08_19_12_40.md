# Recalibração para a construção de features da aplicação

Gerado em 19/08/2026 12:40

As features são as da variante D da medição de degradação: previsão `ecmwf_ifs025` no lugar do ERA5, e média de `t+1..t+24` no lugar do valor em `t`. O modelo **não** foi retreinado — o LightGBM é o mesmo, extraído de dentro do `CalibratedClassifierCV` salvo. O que muda é a isotônica e o corte, **ambos reajustados na validação**.

- threshold antigo: **0.260**
- só o corte reajustado: **0.160**
- corte com a isotônica nova: **0.340**

## Teste (janela intocada)

| cenário | F1 | precisão | recall | PR-AUC estação-dia | PR-AUC operacional |
|---|---|---|---|---|---|
| antes (isotônica+corte antigos) | 0.1632 | 0.3884 | 0.1033 | 0.2352 | 0.1085 |
| só o corte reajustado | 0.3294 | 0.2481 | 0.4901 | 0.2352 | 0.1085 |
| isotônica + corte reajustados | 0.3388 | 0.3197 | 0.3604 | 0.2334 | 0.1084 |

O PR-AUC não muda entre os cenários por construção — calibração monotônica e threshold não alteram a ordenação. O que eles movem é o ponto de operação, e é isso que a tabela mede.

Referência de laboratório (ERA5, valor em `t`, do relatório de 20:07 de 18/08): F1 0,3274 | P 0,2970 | R 0,3648.
