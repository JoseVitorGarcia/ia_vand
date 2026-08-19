"""Recalibra calibração e threshold para a construção de features da aplicação.

Por que existe: a medição de 19/08/2026 mostrou que a configuração real da
aplicação (previsão + média t+1..t+24) ordena o risco MELHOR que a de laboratório
— PR-AUC operacional 0,1085 contra 0,0787. Mas o F1 por estação-dia desabou de
0,327 para 0,163, porque tanto a isotônica quanto o corte de 0,26 foram ajustados
na distribuição antiga. O modelo acerta a ordem e erra a escala.

Não retreina: extrai o LightGBM de dentro do CalibratedClassifierCV salvo e
reajusta só a isotônica e o threshold, ambos NA VALIDAÇÃO. Reajustar qualquer um
dos dois no teste seria vazamento.

Uso:
    MEM_MAX=11G ./run.sh scripts/recalibrar_mos.py
"""
import json
import logging

import joblib
import numpy as np
import pandas as pd
from sklearn.calibration import CalibratedClassifierCV

from src.config import FEATURE_COLUMNS, MODELS_DIR, REPORTS_DIR
from src.ingestion import enrich_openmeteo, load_data
from src.model import (avaliar_por_estacao_dia, find_best_threshold_estacao_dia,
                       separar_janelas)
from src.processing import clean_data, create_features
from scripts.medir_degradacao_mos import (HORA_EMISSAO, INICIO_PREV, _media_futura,
                                          _operacional, _trocar_por_previsao)

logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s %(levelname)s %(name)s — %(message)s',
                    datefmt='%H:%M:%S')
logger = logging.getLogger('recalibrar_mos')


def _preparar(feats, mascara):
    """Recorta a janela e aplica a média t+1..t+24 das features Open-Meteo."""
    return _media_futura(feats[mascara].copy())


def _metricas(nome, df, probs, threshold):
    y = df['evento_extremo'].to_numpy()
    por_dia = avaliar_por_estacao_dia(df, probs, y, threshold)
    op = _operacional(df, probs)
    logger.info('%-28s F1 %.4f | P %.4f | R %.4f | PR-AUC %.4f | op %.4f',
                nome, por_dia['f1'], por_dia['precision'], por_dia['recall'],
                por_dia['pr_auc'], op['op_pr_auc'])
    return {'cenário': nome, **por_dia, **op}


if __name__ == '__main__':
    calibrado_antigo = joblib.load(MODELS_DIR / 'classifier.pkl')
    threshold_antigo = json.loads((MODELS_DIR / 'threshold.json').read_text())['threshold']
    base_clf = calibrado_antigo.calibrated_classifiers_[0].estimator
    logger.info('LightGBM base extraído de %s | threshold antigo %.3f',
                type(calibrado_antigo).__name__, threshold_antigo)

    bruto = enrich_openmeteo(clean_data(load_data()))
    fim = bruto['data_hora'].max().strftime('%Y-%m-%d')
    logger.info('substituindo ERA5 por previsão de %s a %s', INICIO_PREV, fim)
    bruto = _trocar_por_previsao(bruto, fim)

    feats = create_features(bruto)
    del bruto
    _treino, validacao, teste = separar_janelas(feats)
    val = _preparar(feats, validacao)
    tes = _preparar(feats, teste)
    del feats

    X_val = val[FEATURE_COLUMNS].astype('float32')
    X_tes = tes[FEATURE_COLUMNS].astype('float32')
    y_val = val['evento_extremo'].to_numpy()

    # ─── o que temos hoje: calibração e corte da distribuição antiga ─────────
    resultados = [
        _metricas('antes (isotônica+corte antigos)', tes,
                  calibrado_antigo.predict_proba(X_tes)[:, 1], threshold_antigo),
    ]

    # ─── só o threshold reajustado, mantendo a isotônica antiga ──────────────
    thr_so_corte = find_best_threshold_estacao_dia(
        val, calibrado_antigo.predict_proba(X_val)[:, 1], y_val)
    logger.info('threshold reajustado (isotônica antiga): %.3f', thr_so_corte)
    resultados.append(
        _metricas('só o corte reajustado', tes,
                  calibrado_antigo.predict_proba(X_tes)[:, 1], thr_so_corte))

    # ─── isotônica E threshold reajustados na validação ──────────────────────
    calibrado_novo = CalibratedClassifierCV(base_clf, method='isotonic', cv='prefit')
    calibrado_novo.fit(X_val, y_val)
    probs_val = calibrado_novo.predict_proba(X_val)[:, 1]
    thr_novo = find_best_threshold_estacao_dia(val, probs_val, y_val)
    logger.info('threshold reajustado (isotônica nova): %.3f', thr_novo)
    resultados.append(
        _metricas('isotônica + corte reajustados', tes,
                  calibrado_novo.predict_proba(X_tes)[:, 1], thr_novo))

    tabela = pd.DataFrame(resultados)
    logger.info('\n%s', tabela[['cenário', 'f1', 'precision', 'recall', 'pr_auc',
                                'op_pr_auc', 'op_ganho']].to_string(index=False))

    melhor = resultados[-1]
    destino = REPORTS_DIR / f"recalibracao_mos_{pd.Timestamp.now():%Y_%m_%d_%H_%M}.md"
    destino.write_text(
        "# Recalibração para a construção de features da aplicação\n\n"
        f"Gerado em {pd.Timestamp.now():%d/%m/%Y %H:%M}\n\n"
        "As features são as da variante D da medição de degradação: previsão "
        "`ecmwf_ifs025` no lugar do ERA5, e média de `t+1..t+24` no lugar do "
        "valor em `t`. O modelo **não** foi retreinado — o LightGBM é o mesmo, "
        "extraído de dentro do `CalibratedClassifierCV` salvo. O que muda é a "
        "isotônica e o corte, **ambos reajustados na validação**.\n\n"
        f"- threshold antigo: **{threshold_antigo:.3f}**\n"
        f"- só o corte reajustado: **{thr_so_corte:.3f}**\n"
        f"- corte com a isotônica nova: **{thr_novo:.3f}**\n\n"
        "## Teste (janela intocada)\n\n"
        "| cenário | F1 | precisão | recall | PR-AUC estação-dia | PR-AUC operacional |\n"
        "|---|---|---|---|---|---|\n" +
        "\n".join(
            f"| {r['cenário']} | {r['f1']:.4f} | {r['precision']:.4f} | "
            f"{r['recall']:.4f} | {r['pr_auc']:.4f} | {r['op_pr_auc']:.4f} |"
            for r in resultados) +
        "\n\nO PR-AUC não muda entre os cenários por construção — calibração "
        "monotônica e threshold não alteram a ordenação. O que eles movem é o "
        "ponto de operação, e é isso que a tabela mede.\n\n"
        f"Referência de laboratório (ERA5, valor em `t`, do relatório de 20:07 "
        f"de 18/08): F1 0,3274 | P 0,2970 | R 0,3648.\n",
        encoding='utf-8')
    logger.info('Relatório salvo em %s', destino)
