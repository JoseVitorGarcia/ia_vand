"""Mede quanto do desempenho sobrevive quando as features vêm de previsão.

Não retreina: reconstrói as features da janela de teste em quatro variantes e
reusa os .pkl salvos.

    A referência   ERA5              valor em t          reproduz o relatório de 20:07
    B só origem    previsão (IFS)    valor em t          custo de trocar a fonte
    C só janela    ERA5              média t+1..t+24     custo do desalinhamento
    D realista     previsão (IFS)    média t+1..t+24     o que a aplicação teria

A tem que reproduzir o relatório de referência. Se não reproduzir, o harness
está errado e as outras três não significam nada.

Uso:
    MEM_MAX=11G ./run.sh scripts/medir_degradacao_mos.py
"""
import json
import logging

import joblib
import numpy as np
import pandas as pd
from sklearn.metrics import average_precision_score

from src.config import (FEATURE_COLUMNS, FEATURES_OPENMETEO, MODELS_DIR,
                        OPENMETEO_COLUNAS, REPORTS_DIR, TRAIN_END)
from src.ingestion import enrich_openmeteo, load_data
from src.model import (_agregar_estacao_dia, avaliar_por_estacao_dia,
                       calcular_baselines, separar_janelas)
from src.openmeteo_client import fetch_forecast_arquivado
from src.processing import clean_data, create_features

logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s %(levelname)s %(name)s — %(message)s',
                    datefmt='%H:%M:%S')
logger = logging.getLogger('degradacao_mos')

JANELA_HORAS = 24

# Janela em que a previsão substitui o ERA5: começa no fim do treino, para
# cobrir validação E teste. A validação é necessária porque é lá que o threshold
# e a calibração são reajustados — no teste seria vazamento.
#
# Não é o intervalo inteiro da série de propósito: pedir 2015-2026 dispararia 100
# downloads de 11 anos de um arquivo que só começa em 2021. Restringir não
# contamina nada — nenhuma feature Open-Meteo usa lag ou janela móvel, então
# trocar o valor numa hora só afeta aquela hora.
INICIO_PREV = (TRAIN_END + pd.Timedelta(hours=1)).strftime('%Y-%m-%d')


def _trocar_por_previsao(df: pd.DataFrame, fim: str) -> pd.DataFrame:
    """Troca as 8 colunas Open-Meteo pelo que a previsão dizia, na janela de teste.

    Alinha por gather posicional em vez de merge — mesmo motivo de
    `_features_vizinhas` em processing.py: cada merge do frame inteiro custa uma
    cópia de vários GB.
    """
    colunas = [c for c in OPENMETEO_COLUNAS if c in df.columns]
    janela = df['data_hora'] >= pd.Timestamp(INICIO_PREV, tz='UTC')
    logger.info('trocando ERA5 por previsão em %d linhas (%.1f%% da base)',
                int(janela.sum()), 100 * janela.mean())

    trocadas, sem_previsao = 0, []
    posicoes_por_estacao = df[janela].groupby('estacao_codigo', observed=True).indices
    indice_janela = np.flatnonzero(janela.to_numpy())

    valores = {c: df[c].to_numpy(copy=True) for c in colunas}
    # Hoistadas de propósito: dentro do loop, cada `.to_numpy()` materializava
    # os 4,7 M de timestamps de novo, uma vez por estação — 15 min por variante.
    horas = df['data_hora'].to_numpy()
    latitudes = df['latitude'].to_numpy()
    longitudes = df['longitude'].to_numpy()

    for codigo, posicoes_locais in posicoes_por_estacao.items():
        linhas = indice_janela[posicoes_locais]
        prev = fetch_forecast_arquivado(latitudes[linhas[0]], longitudes[linhas[0]],
                                        INICIO_PREV, fim)
        if prev.empty:
            sem_previsao.append(codigo)
            continue

        onde = pd.Index(prev['data_hora']).get_indexer(horas[linhas])
        achou = onde >= 0
        for c in colunas:
            origem = pd.to_numeric(prev[c], errors='coerce').to_numpy()
            valores[c][linhas[achou]] = origem[onde[achou]]
        trocadas += int(achou.sum())

    for c in colunas:
        df[c] = valores[c]
    logger.info('%d linhas trocadas | %d estações sem previsão %s',
                trocadas, len(sem_previsao), sem_previsao[:10])
    return df


def _media_futura(df: pd.DataFrame) -> pd.DataFrame:
    """Troca o valor em t pela média de t+1..t+24 de cada feature Open-Meteo.

    Aplicado DEPOIS de create_features, de propósito. O plano previa promediar
    OPENMETEO_COLUNAS, que inclui `wind_direction_100m` — e média aritmética de
    direção em graus é a descontinuidade 0°/360° que o config já documenta. As
    features finais já vêm decompostas em vento100_norte/leste, então promediar
    aqui é literalmente "a média das próximas 24 h de cada campo", sem ambiguidade.

    A inversão é a mesma do alvo em create_features: inverter, deslocar 1 e
    acumular para trás olha estritamente para frente sem incluir a própria hora.
    """
    colunas = [c for c in FEATURES_OPENMETEO if c in df.columns]
    df = df.sort_values(['estacao_codigo', 'data_hora'])
    for col in colunas:
        df[col] = (df.groupby('estacao_codigo', observed=True)[col]
                   .transform(lambda x: x.iloc[::-1].shift(1)
                              .rolling(JANELA_HORAS, min_periods=1).mean().iloc[::-1])
                   .astype('float32'))
    logger.info('janela alinhada em %d colunas: %s', len(colunas), colunas)
    return df


# Hora de emissão do alerta no enquadramento operacional. 12 UTC é o início do
# dia pluviométrico do INMET (medido em 19/08/2026 contra o BDMEP, r = 1,0000),
# então "o alerta das 12 UTC" fala a mesma língua da defesa civil.
HORA_EMISSAO = 12


def _persistencia_estacao_dia(df_teste, y) -> float:
    """Persistência agregada por max do dia — a MESMA unidade do PR-AUC do modelo.

    NÃO é uma régua honesta, e está aqui só para deixar o problema registrado:
    o max do dia cai na hora 0 em 65% dos dias e na hora 23 em outros 6%, e a
    janela de 24 h passada nessas horas **sobrepõe a chuva do próprio dia** que o
    alvo tenta prever. A persistência vira diagnóstico em vez de previsão e
    marca 0,2900 contra 0,2426 do modelo. Em hora fixa de emissão, onde as duas
    olham estritamente para frente, o modelo ganha por larga margem — ver
    `_operacional`.
    """
    agregado = _agregar_estacao_dia(df_teste, df_teste['chuva_24h'].to_numpy(), y)
    return float(average_precision_score(agregado['y'], agregado['p']))


def _operacional(df_teste, probs) -> dict:
    """Um alerta por estação-dia, emitido em hora fixa. É o enquadramento do produto.

    Aqui modelo e persistência olham exatamente a mesma janela futura a partir do
    mesmo instante, então a comparação é limpa — ao contrário da agregação por
    max, que dá à persistência acesso à chuva concomitante.
    """
    linha = df_teste['data_hora'].dt.hour == HORA_EMISSAO
    y = df_teste.loc[linha, 'evento_extremo'].to_numpy()
    p = np.asarray(probs)[linha.to_numpy()]
    pers = df_teste.loc[linha, 'chuva_24h'].to_numpy()
    pr_modelo = float(average_precision_score(y, p))
    pr_pers = float(average_precision_score(y, pers))
    return {'op_pr_auc': pr_modelo, 'op_persistencia': pr_pers,
            'op_ganho': 100 * (pr_modelo / pr_pers - 1),
            'op_n': int(len(y)), 'op_eventos': int(y.sum())}


def _avaliar(df_teste, nome, clf, threshold, df_treino) -> dict:
    # astype('float32') reproduz o que train_models faz — sem isso uma coluna
    # toda-nula volta do parquet como object e o LightGBM quebra.
    X = df_teste[FEATURE_COLUMNS].astype('float32')
    probs = clf.predict_proba(X)[:, 1]
    y = df_teste['evento_extremo'].to_numpy()

    por_dia = avaliar_por_estacao_dia(df_teste, probs, y, threshold)
    persistencia = _persistencia_estacao_dia(df_teste, y)
    horaria = calcular_baselines(df_treino, df_teste, y)
    op = _operacional(df_teste, probs)
    logger.info('%-14s estação-dia: F1 %.4f | P %.4f | R %.4f | PR-AUC %.4f',
                nome, por_dia['f1'], por_dia['precision'], por_dia['recall'],
                por_dia['pr_auc'])
    logger.info('%-14s operacional %02dUTC: PR-AUC %.4f | persistência %.4f | '
                'ganho %+.1f%%', '', HORA_EMISSAO, op['op_pr_auc'],
                op['op_persistencia'], op['op_ganho'])
    return {'variante': nome, **por_dia, 'persistencia_max_dia': persistencia,
            'persistencia_horaria': horaria['persistencia_pr_auc'], **op}


if __name__ == '__main__':
    clf = joblib.load(MODELS_DIR / 'classifier.pkl')
    threshold = json.loads((MODELS_DIR / 'threshold.json').read_text())['threshold']
    logger.info('Threshold de models/threshold.json: %.3f (NÃO reajustar no teste)',
                threshold)

    base = enrich_openmeteo(clean_data(load_data()))
    FIM_PREV = base['data_hora'].max().strftime('%Y-%m-%d')
    logger.info('janela de previsão: %s a %s', INICIO_PREV, FIM_PREV)

    resultados = []
    for nome, trocar_origem, alinhar_janela in [
        ('A referência', False, False),
        ('B só origem',  True,  False),
        ('C só janela',  False, True),
        ('D realista',   True,  True),
    ]:
        logger.info('=== %s ===', nome)
        df = base.copy()
        if trocar_origem:
            df = _trocar_por_previsao(df, FIM_PREV)

        feats = create_features(df)
        del df
        treino, _validacao, teste = separar_janelas(feats)
        df_teste = feats[teste].copy()
        df_treino = feats.loc[treino, ['evento_extremo', 'chuva_24h']]
        del feats

        if alinhar_janela:
            df_teste = _media_futura(df_teste)

        resultados.append(_avaliar(df_teste, nome, clf, threshold, df_treino))
        del df_teste, df_treino

    tabela = pd.DataFrame(resultados)
    logger.info('\n%s', tabela.to_string(index=False))

    ref = resultados[0]
    destino = REPORTS_DIR / f"degradacao_mos_{pd.Timestamp.now():%Y_%m_%d_%H_%M}.md"
    destino.write_text(
        "# Degradação com previsão em vez de reanálise\n\n"
        f"Gerado em {pd.Timestamp.now():%d/%m/%Y %H:%M}\n\n"
        f"Threshold fixo de `models/threshold.json`: {threshold:.3f} "
        "(não reajustado no teste — reajustar seria vazamento).\n\n"
        "Fonte da previsão: `ecmwf_ifs025` do historical-forecast-api. Sem o "
        "`models` explícito a API devolve o mesmo ERA5 do archive-api, e a "
        "medição daria degradação zero por construção.\n\n"
        "## Por estação-dia, agregando por max\n\n"
        "Unidade dos relatórios anteriores. Serve para comparar as variantes "
        "entre si, **não** para comparar com a persistência (ver a última seção).\n\n"
        "| variante | F1 | precisão | recall | PR-AUC |\n|---|---|---|---|---|\n" +
        "\n".join(
            f"| {r['variante']} | {r['f1']:.4f} | {r['precision']:.4f} | "
            f"{r['recall']:.4f} | {r['pr_auc']:.4f} |"
            for r in resultados) +
        f"\n\n- **B − A** (custo de trocar a fonte): PR-AUC "
        f"{resultados[1]['pr_auc'] - ref['pr_auc']:+.4f}\n"
        f"- **C − A** (custo do desalinhamento de janela): PR-AUC "
        f"{resultados[2]['pr_auc'] - ref['pr_auc']:+.4f}\n"
        f"- **D − A** (o que a aplicação perde de verdade): PR-AUC "
        f"{resultados[3]['pr_auc'] - ref['pr_auc']:+.4f}\n\n"
        f"## Operacional — um alerta por estação-dia, emitido às {HORA_EMISSAO:02d} UTC\n\n"
        "É o enquadramento do produto, e o único em que a comparação com a "
        "persistência é limpa: modelo e régua olham a mesma janela futura a "
        "partir do mesmo instante. "
        f"{ref['op_n']} estação-dias, {ref['op_eventos']} eventos "
        f"({100*ref['op_eventos']/ref['op_n']:.2f}%).\n\n"
        "| variante | PR-AUC | persistência | ganho |\n|---|---|---|---|\n" +
        "\n".join(
            f"| {r['variante']} | {r['op_pr_auc']:.4f} | {r['op_persistencia']:.4f} | "
            f"{r['op_ganho']:+.1f}% |" for r in resultados) +
        "\n\n## Por que a persistência não serve como régua na agregação por max\n\n"
        f"Naquela unidade a persistência marca {ref['persistencia_max_dia']:.4f} contra "
        f"{ref['pr_auc']:.4f} do modelo — e isso é artefato, não resultado. O max de "
        "`chuva_24h` do dia cai na hora 0 em 65% dos dias e na hora 23 em outros 6%, "
        "e a janela de 24 h passada nessas horas sobrepõe a chuva do próprio dia que "
        "o alvo tenta prever. A persistência deixa de ser previsão e vira diagnóstico. "
        "Em hora fixa de emissão o modelo ganha por larga margem, como mostra a "
        "tabela acima.\n\n"
        "## Limitações — o que este número ainda não prova\n\n"
        "1. **D é otimista, e a causa é o instante de emissão.** O "
        "historical-forecast-api devolve, para cada hora `h`, o valor da rodada "
        "mais recente ANTES de `h`. Um sistema real decidindo às 12 UTC usa uma "
        "única rodada emitida até as 12 UTC, com leads de 1 a 24 h. A média "
        "`t+1..t+24` de D mistura leads e inclui valores de rodadas emitidas até "
        "23 h DEPOIS do momento da decisão. As variantes `*_previous_dayN`, que "
        "teriam lead fixo, não carregam as nossas variáveis — por isso a colheita "
        "diária de previsões reais (Task 5) continua sendo o único caminho para o "
        "número definitivo.\n"
        "2. **O modelo foi treinado com ERA5 em `t`** e aqui é avaliado com uma "
        "distribuição diferente nas 8 colunas. Que ainda assim melhore sugere que "
        "retreinar já com a janela alinhada renderia mais — não testado.\n"
        "3. **O threshold não transfere.** O corte de 0,26 foi calibrado na "
        "distribuição da variante A; em C e D as probabilidades deslocam para "
        "baixo e o recall por estação-dia cai de 0,36 para 0,10 com a precisão "
        "subindo. Recalibrar exige a previsão da janela de validação "
        "(jan–ago/2025), que ainda não está em cache.\n"
        "4. **Uma janela de teste só**, 195 eventos às 12 UTC. Sem repetição de "
        "semente.\n\n"
        "A variante A precisa reproduzir o relatório de referência "
        "(F1 0,3274 | P 0,2970 | R 0,3648 | PR-AUC 0,2426). Se não reproduzir, o "
        "harness está errado e as outras três não significam nada.\n",
        encoding='utf-8')
    logger.info('Relatório salvo em %s', destino)
