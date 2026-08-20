# Quanto a observação local acrescenta sobre a previsão do ECMWF?

Gerado em 20/08/2026 15:21

**IFS** (*Integrated Forecasting System*) é o modelo global de previsão do **ECMWF** (*European Centre for Medium-Range Weather Forecasts*). **PR-AUC** é a área sob a curva precisão-recall — a métrica certa quando o evento é raro.

Combinador de poucos parâmetros ajustado em **2024-04-01 a 2024-12-31** e medido em **2025-01-01 em diante**, sem retreinar modelo nenhum.

**Endpoint primário, declarado no código antes de rodar: 50 mm, 12 UTC.** Os outros três cenários são secundários e existem para separar *não há sinal* de *não há sinal na cauda extrema*.

Nenhuma variante consome o escore do nosso modelo: 2024 é dentro da amostra para ele, e usá-lo aqui inflaria o resultado. As variantes que o usam foram medidas em 19/08/2026 e ficaram com intervalo cruzando zero.

A unidade **estação-dia** foi excluída de propósito: ela toma o máximo das 24 h do dia, e as features locais incluem chuva passada — na hora 23 a janela de 24 h já viu a chuva do dia que o rótulo mede. É a mesma circularidade que inflava a persistência.

**Histórico de seleção, para leitura honesta:** a V2 foi eleita candidata depois de ver o teste em 19/08/2026. Por isso todas as variantes são reportadas aqui, não só ela.

**Dois intervalos.** O *por unidade* reamostra linhas e é comparável com o relatório de 19/08. O *por data* reamostra dias inteiros: chuva extrema é sinótica, e tratar 100 estações da mesma frente como 100 observações independentes é pseudo-replicação. **O intervalo por data é o que vale.**

| cenário | variante | eventos (ajuste/avaliação) | PR-AUC | dentro da amostra | Δ vs IFS | IC 95% por unidade | IC 95% por data |
|---|---|---|---|---|---|---|---|
| 50 mm, 12 UTC | V0 IFS sozinho | 224/302 | 0.4166 | 0.3214 | +0.0000 | [+0.0000, +0.0000] | [+0.0000, +0.0000] |
| 50 mm, 12 UTC **(primário)** | V2 IFS + observação local | 224/302 | 0.3693 | 0.3585 | -0.0481 | [-0.0729, -0.0240] | [-0.0856, -0.0144] |
| 50 mm, 12 UTC **(primário)** | V4 IFS + orvalho + pressão | 224/302 | 0.3482 | 0.3364 | -0.0676 | [-0.0900, -0.0471] | [-0.1033, -0.0351] |
| 50 mm, 12 UTC **(primário)** | V5 árvore (interação) | 224/302 | 0.2539 | 0.7203 | -0.1615 | [-0.2163, -0.1140] | [-0.2396, -0.0852] |
| 50 mm, 00+12 UTC | V0 IFS sozinho | 494/586 | 0.3917 | 0.3896 | +0.0000 | [+0.0000, +0.0000] | [+0.0000, +0.0000] |
| 50 mm, 00+12 UTC | V2 IFS + observação local | 494/586 | 0.3593 | 0.4255 | -0.0331 | [-0.0516, -0.0155] | [-0.0651, -0.0030] |
| 50 mm, 00+12 UTC | V4 IFS + orvalho + pressão | 494/586 | 0.3415 | 0.3992 | -0.0497 | [-0.0642, -0.0368] | [-0.0783, -0.0239] |
| 50 mm, 00+12 UTC | V5 árvore (interação) | 494/586 | 0.2835 | 0.6961 | -0.1080 | [-0.1395, -0.0794] | [-0.1464, -0.0699] |
| 30 mm, 12 UTC | V0 IFS sozinho | 579/832 | 0.5715 | 0.5151 | +0.0000 | [+0.0000, +0.0000] | [+0.0000, +0.0000] |
| 30 mm, 12 UTC | V2 IFS + observação local | 579/832 | 0.5589 | 0.5345 | -0.0120 | [-0.0243, -0.0016] | [-0.0297, +0.0062] |
| 30 mm, 12 UTC | V4 IFS + orvalho + pressão | 579/832 | 0.5579 | 0.5201 | -0.0129 | [-0.0227, -0.0054] | [-0.0261, +0.0005] |
| 30 mm, 12 UTC | V5 árvore (interação) | 579/832 | 0.4858 | 0.7637 | -0.0855 | [-0.1128, -0.0586] | [-0.1204, -0.0531] |
| 30 mm, 00+12 UTC | V0 IFS sozinho | 1167/1642 | 0.5514 | 0.5504 | +0.0000 | [+0.0000, +0.0000] | [+0.0000, +0.0000] |
| 30 mm, 00+12 UTC | V2 IFS + observação local | 1167/1642 | 0.5311 | 0.5698 | -0.0200 | [-0.0303, -0.0116] | [-0.0391, -0.0004] |
| 30 mm, 00+12 UTC | V4 IFS + orvalho + pressão | 1167/1642 | 0.5188 | 0.5593 | -0.0317 | [-0.0412, -0.0245] | [-0.0491, -0.0143] |
| 30 mm, 00+12 UTC | V5 árvore (interação) | 1167/1642 | 0.4774 | 0.7345 | -0.0733 | [-0.0909, -0.0579] | [-0.1012, -0.0440] |

## Limites superiores

Quando o intervalo cruza zero, o resultado não é *nada acontece* — é *o acréscimo, se existir, é menor que o limite abaixo*. **Esse é o entregável deste estudo**, porque a aritmética de potência foi feita antes de rodar: com o número de eventos disponível, o menor efeito detectável é da ordem de 2,6% a 5,1% sobre o IFS, e o efeito medido em 19/08 foi de 1,7%. Nenhum desenho possível com este dado detectaria 1,7%.

| cenário | variante | limite superior (IC por data) |
|---|---|---|
| 50 mm, 12 UTC | V2 IFS + observação local | -0.0144 |
| 50 mm, 12 UTC | V4 IFS + orvalho + pressão | -0.0351 |
| 50 mm, 12 UTC | V5 árvore (interação) | -0.0852 |
| 50 mm, 00+12 UTC | V2 IFS + observação local | -0.0030 |
| 50 mm, 00+12 UTC | V4 IFS + orvalho + pressão | -0.0239 |
| 50 mm, 00+12 UTC | V5 árvore (interação) | -0.0699 |
| 30 mm, 12 UTC | V2 IFS + observação local | +0.0062 |
| 30 mm, 12 UTC | V4 IFS + orvalho + pressão | +0.0005 |
| 30 mm, 12 UTC | V5 árvore (interação) | -0.0531 |
| 30 mm, 00+12 UTC | V2 IFS + observação local | -0.0004 |
| 30 mm, 00+12 UTC | V4 IFS + orvalho + pressão | -0.0143 |
| 30 mm, 00+12 UTC | V5 árvore (interação) | -0.0440 |

## Regra de leitura, fixada antes de ver o resultado

| resultado | conclusão |
|---|---|
| 30 mm positivo, 50 mm nulo | a observação local contribui, mas não alcança a cauda extrema |
| ambos nulos, com limites estreitos | o ECMWF já contém o que as estações sabem |
| 50 mm positivo | exige explicação mecanicista antes de ser aceito |

A coluna **dentro da amostra** é onde o combinador foi ajustado. Se uma variante ganha lá e não ganha na avaliação, é sobreajuste; se não ganha nem lá, a informação é genuinamente redundante — e essa distinção é a razão de a janela de ajuste ter sido ampliada.

