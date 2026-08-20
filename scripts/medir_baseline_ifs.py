"""Quão bem a previsão de chuva do próprio modelo europeu acerta, sozinha?

Por que existe: o projeto compara o modelo contra persistência (supor que amanhã
chove como choveu ontem) e climatologia (supor a média histórica). As duas são
réguas fracas de propósito. A régua forte — e gratuita — é a previsão de chuva do
IFS, o modelo global do ECMWF: qualquer pessoa baixa sem treinar nada.

Se ela ganhar de nós, o valor do projeto está em CORRIGIR localmente o que ela
erra, que é o que a sigla MOS (Model Output Statistics) descreve. Se perder, é a
defesa mais forte possível do trabalho. Nunca foi medido.

Uso:
    MEM_MAX=11G ./run.sh scripts/medir_baseline_ifs.py
"""
import json
import logging
import sys

import joblib
import numpy as np
import pandas as pd
from sklearn.metrics import average_precision_score

from src.config import (EXTREME_RAIN_THRESHOLD, FEATURE_COLUMNS, MODELS_DIR,
                        REPORTS_DIR)
from src.ingestion import enrich_openmeteo, load_data
from src.model import _agregar_estacao_dia, separar_janelas
from src.openmeteo_client import (_cache_utilizavel, _previsao_cache_path,
                                  fetch_forecast_arquivado)
from src.processing import clean_data, create_features
from scripts.medir_degradacao_mos import (HORA_EMISSAO, INICIO_PREV, JANELA_HORAS,
                                          _media_futura, _trocar_por_previsao)

logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s %(levelname)s %(name)s — %(message)s',
                    datefmt='%H:%M:%S')
logger = logging.getLogger('baseline_ifs')

# `precipitation` não está em OPENMETEO_HISTORICAL_VARS de propósito: aquelas 8
# são as que o INMET NÃO fornece. Aqui a chuva prevista é justamente o objeto da
# medição, não uma feature.
VARS_REGUA = ['precipitation', 'precipitation_probability']


def _soma_futura(serie: pd.Series) -> pd.Series:
    """Soma de t+1 a t+24, a mesma construção do alvo em create_features."""
    return (serie.iloc[::-1].shift(1)
            .rolling(JANELA_HORAS, min_periods=JANELA_HORAS).sum().iloc[::-1])


def _max_futuro(serie: pd.Series) -> pd.Series:
    return (serie.iloc[::-1].shift(1)
            .rolling(JANELA_HORAS, min_periods=JANELA_HORAS).max().iloc[::-1])


def _baixar_regua(estacoes, fim, passadas=6, pausa=60.0, inicio=None):
    """Enche o cache da régua. Falha alto: medir com estação faltando mentiria.

    `inicio` recua a janela para antes do fim do treino, quando a medição precisa
    de previsão arquivada em 2024. Mudar o início troca a chave do cache, então
    uma janela nova baixa tudo de novo — é esperado, não é bug.
    """
    import time
    inicio = inicio or INICIO_PREV
    for passada in range(1, passadas + 1):
        faltando = [e for e, r in estacoes.iterrows()
                    if not _cache_utilizavel(
                        _previsao_cache_path(r['lat'], r['lon'], inicio, fim,
                                             VARS_REGUA), VARS_REGUA)]
        if not faltando:
            logger.info('cache da régua completo')
            return
        logger.info('passada %d/%d — faltam %d estações', passada, passadas, len(faltando))
        for est in faltando:
            r = estacoes.loc[est]
            try:
                fetch_forecast_arquivado(r['lat'], r['lon'], inicio, fim,
                                         variaveis=VARS_REGUA)
            except Exception as exc:
                logger.warning('%s falhou: %s', est, exc)
        if passada < passadas:
            time.sleep(pausa)
    logger.error('INCOMPLETO — não vou medir com buraco no cache')
    sys.exit(1)


def _anexar_regua(df, estacoes, fim, inicio=None):
    """Junta ao frame a soma de chuva prevista e o pico de probabilidade em t+1..t+24."""
    inicio = inicio or INICIO_PREV
    horas = df['data_hora'].to_numpy()
    soma = np.full(len(df), np.nan)
    prob = np.full(len(df), np.nan)

    for codigo, posicoes in df.groupby('estacao_codigo', observed=True).indices.items():
        r = estacoes.loc[codigo]
        prev = fetch_forecast_arquivado(r['lat'], r['lon'], inicio, fim,
                                        variaveis=VARS_REGUA)
        if prev.empty:
            continue
        prev = prev.sort_values('data_hora')
        chuva_fut = _soma_futura(pd.to_numeric(prev['precipitation'], errors='coerce'))
        prob_fut = _max_futuro(pd.to_numeric(prev['precipitation_probability'],
                                             errors='coerce'))
        onde = pd.Index(prev['data_hora']).get_indexer(horas[posicoes])
        achou = onde >= 0
        soma[posicoes[achou]] = chuva_fut.to_numpy()[onde[achou]]
        prob[posicoes[achou]] = prob_fut.to_numpy()[onde[achou]]

    df['ifs_chuva_24h'] = soma
    df['ifs_prob_24h'] = prob
    return df


def _pr(y, score):
    ok = ~pd.isna(score)
    return float(average_precision_score(np.asarray(y)[ok], np.asarray(score)[ok]))


if __name__ == '__main__':
    bruto = enrich_openmeteo(clean_data(load_data()))
    fim = bruto['data_hora'].max().strftime('%Y-%m-%d')
    estacoes = (bruto.groupby('estacao_codigo', observed=True)
                .agg(lat=('latitude', 'first'), lon=('longitude', 'first')))
    logger.info('%d estações | régua %s de %s a %s',
                len(estacoes), VARS_REGUA, INICIO_PREV, fim)
    _baixar_regua(estacoes, fim)

    bruto = _trocar_por_previsao(bruto, fim)
    feats = create_features(bruto)
    del bruto
    _tr, _va, teste = separar_janelas(feats)
    tes = _media_futura(feats[teste].copy())
    del feats

    tes = _anexar_regua(tes, estacoes, fim)
    cobertura = tes['ifs_chuva_24h'].notna().mean()
    logger.info('régua cobre %.2f%% das linhas de teste', 100 * cobertura)

    clf = joblib.load(MODELS_DIR / 'classifier.pkl')
    reg = joblib.load(MODELS_DIR / 'regressor.pkl')
    X = tes[FEATURE_COLUMNS].astype('float32')
    tes['p_modelo'] = clf.predict_proba(X)[:, 1]
    tes['reg_modelo'] = reg.predict(X)
    y = tes['evento_extremo'].to_numpy()

    candidatos = {
        'nosso modelo (variante D)': tes['p_modelo'],
        'IFS — soma de chuva prevista 24 h': tes['ifs_chuva_24h'],
        'IFS — pico de prob. de precipitação': tes['ifs_prob_24h'],
        'persistência (chuva das últimas 24 h)': tes['chuva_24h'],
    }

    linhas = []
    logger.info('=== CLASSIFICAÇÃO: prever chuva > %d mm em 24 h ===', EXTREME_RAIN_THRESHOLD)
    emissao = tes['data_hora'].dt.hour == HORA_EMISSAO
    for nome, score in candidatos.items():
        ag = _agregar_estacao_dia(tes, score.to_numpy(), y)
        pr_dia = _pr(ag['y'], ag['p'])
        pr_op = _pr(tes.loc[emissao, 'evento_extremo'].to_numpy(),
                    score[emissao].to_numpy())
        linhas.append({'candidato': nome, 'pr_auc_estacao_dia': pr_dia,
                       'pr_auc_operacional': pr_op})
        logger.info('%-40s estação-dia %.4f | operacional %.4f', nome, pr_dia, pr_op)

    logger.info('=== REGRESSÃO: acertar o volume em mm ===')
    alvo = tes['chuva_futura_24h']
    reg_linhas = []
    for nome, pred in [('nosso regressor', tes['reg_modelo']),
                       ('IFS — chuva prevista 24 h', tes['ifs_chuva_24h'])]:
        ok = pred.notna() & alvo.notna()
        mae = float((pred[ok] - alvo[ok]).abs().mean())
        chovendo = ok & (alvo > 1)
        mae_chuva = float((pred[chovendo] - alvo[chovendo]).abs().mean())
        reg_linhas.append({'candidato': nome, 'mae': mae, 'mae_chuva_1mm': mae_chuva})
        logger.info('%-30s MAE %.4f mm | com chuva > 1 mm: %.4f mm', nome, mae, mae_chuva)

    tabela = pd.DataFrame(linhas)
    melhor = tabela.loc[tabela['pr_auc_operacional'].idxmax(), 'candidato']
    logger.info('\nMELHOR no enquadramento operacional: %s', melhor)

    destino = REPORTS_DIR / f"baseline_ifs_{pd.Timestamp.now():%Y_%m_%d_%H_%M}.md"
    destino.write_text(
        "# A régua do IFS — quão bem o modelo europeu acerta sozinho\n\n"
        f"Gerado em {pd.Timestamp.now():%d/%m/%Y %H:%M}\n\n"
        "**IFS** (*Integrated Forecasting System*) é o modelo global do **ECMWF** "
        "(*European Centre for Medium-Range Weather Forecasts*), o centro europeu "
        "de previsão. A régua é a chuva que ele mesmo previu para as próximas "
        "24 h — disponível de graça, sem treinar nada.\n\n"
        f"Janela de teste, {len(tes)} linhas horárias, régua cobrindo "
        f"{100*cobertura:.1f}% delas.\n\n"
        "## Classificação — prever chuva acima de "
        f"{EXTREME_RAIN_THRESHOLD} mm em 24 h\n\n"
        "PR-AUC (área sob a curva precisão-recall): mede se o candidato ORDENA o "
        "risco corretamente, independente de onde se coloca o corte do alerta.\n\n"
        "| candidato | PR-AUC estação-dia | PR-AUC operacional (12 UTC) |\n"
        "|---|---|---|\n" +
        "\n".join(f"| {r['candidato']} | {r['pr_auc_estacao_dia']:.4f} | "
                  f"{r['pr_auc_operacional']:.4f} |" for r in linhas) +
        "\n\n## Regressão — acertar o volume\n\n"
        "| candidato | MAE | MAE com chuva > 1 mm |\n|---|---|---|\n" +
        "\n".join(f"| {r['candidato']} | {r['mae']:.4f} mm | "
                  f"{r['mae_chuva_1mm']:.4f} mm |" for r in reg_linhas) +
        f"\n\n**Melhor no enquadramento operacional: {melhor}.**\n",
        encoding='utf-8')
    logger.info('Relatório salvo em %s', destino)
