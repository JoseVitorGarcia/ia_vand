"""As estações do INMET acrescentam algo sobre a previsão do ECMWF?

É a pergunta do projeto reduzida ao mínimo testável. A diagnose de viés
(diagnosticar_vies_ifs.py) mostrou que o erro do IFS não é corrigível por escala:
a identidade da estação explica 0,80% da variância do resíduo e toda correção
simples piora o teste. E recalibração não pode melhorar classificação, porque
PR-AUC mede ordenação e transformação monotônica a preserva.

Logo: só INFORMAÇÃO NOVA supera o PR-AUC de 0,3957 do IFS sozinho. Este script
mede se a observação local é essa informação.

Desenho: combinador de poucos parâmetros (regressão logística), treinado na
VALIDAÇÃO — único período em que as predições do nosso modelo são fora da amostra
e existe previsão do IFS — e medido no teste intocado. Árvores foram descartadas
de propósito: com 8 meses de treino, a diagnose já mostrou correção ajustada na
validação não transferindo.

Uso:
    MEM_MAX=11G ./run.sh scripts/combinar_ifs_local.py
"""
import json
import logging

import joblib
import numpy as np
import pandas as pd
from lightgbm import LGBMClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from src.config import FEATURE_COLUMNS, MODELS_DIR, REPORTS_DIR
from src.ingestion import enrich_openmeteo, load_data
from src.model import _agregar_estacao_dia, separar_janelas
from src.processing import clean_data, create_features
from scripts.medir_baseline_ifs import _anexar_regua, _baixar_regua
from scripts.medir_degradacao_mos import HORA_EMISSAO, _media_futura, _trocar_por_previsao

logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s %(levelname)s %(name)s — %(message)s',
                    datefmt='%H:%M:%S')
logger = logging.getLogger('combinar')

# Observação local crua: o que uma estação sabe agora e a grade de 24 km do
# ECMWF não vê. `viz_chuva_3h` é o que as vizinhas mediram — informação
# genuinamente espacial que nenhuma célula de grade carrega.
LOCAIS = ['chuva_24h', 'chuva_3h', 'queda_pressao_24h', 'soil_moisture',
          'clima_chuva_mes', 'viz_chuva_3h', 'umidade', 'orvalho']

VARIANTES = {
    'V0 IFS sozinho':                 [],
    'V1 IFS + nosso modelo':          ['p_modelo'],
    'V2 IFS + observação local':      LOCAIS,
    'V3 IFS + modelo + local':        ['p_modelo'] + LOCAIS,
    # V4 ataca a hipótese de sobreajuste: só as duas locais de maior peso.
    'V4 IFS + orvalho + pressão':     ['orvalho', 'queda_pressao_24h'],
}

# V5 ataca a outra hipótese: o linear não captura interação. Se a observação
# local só importa quando a previsão está incerta, nenhum modelo aditivo vê isso.
USAR_ARVORE = True


def _pr(y, score):
    return float(average_precision_score(np.asarray(y), np.asarray(score)))


def _avaliar(nome, tes, score, dentro=None):
    y = tes['evento_extremo'].to_numpy()
    ag = _agregar_estacao_dia(tes, np.asarray(score), y)
    emissao = (tes['data_hora'].dt.hour == HORA_EMISSAO).to_numpy()
    return {
        'variante': nome,
        'pr_auc_estacao_dia': _pr(ag['y'], ag['p']),
        'pr_auc_operacional': _pr(y[emissao], np.asarray(score)[emissao]),
        'pr_auc_validacao': dentro if dentro is not None else float('nan'),
    }


if __name__ == '__main__':
    bruto = enrich_openmeteo(clean_data(load_data()))
    fim = bruto['data_hora'].max().strftime('%Y-%m-%d')
    estacoes = (bruto.groupby('estacao_codigo', observed=True)
                .agg(lat=('latitude', 'first'), lon=('longitude', 'first')))
    _baixar_regua(estacoes, fim)
    bruto = _trocar_por_previsao(bruto, fim)

    feats = create_features(bruto)
    del bruto
    _tr, validacao, teste = separar_janelas(feats)
    val = _media_futura(feats[validacao].copy())
    tes = _media_futura(feats[teste].copy())
    del feats

    val = _anexar_regua(val, estacoes, fim)
    tes = _anexar_regua(tes, estacoes, fim)

    clf = joblib.load(MODELS_DIR / 'classifier.pkl')
    for d in (val, tes):
        d['p_modelo'] = clf.predict_proba(d[FEATURE_COLUMNS].astype('float32'))[:, 1]
        # A chuva prevista é fortemente assimétrica; log1p a torna utilizável por
        # um modelo linear sem transformar o problema.
        d['ifs_log'] = np.log1p(d['ifs_chuva_24h'].clip(lower=0))

    antes = len(val), len(tes)
    val = val.dropna(subset=['ifs_log', 'evento_extremo'] + LOCAIS + ['p_modelo'])
    tes = tes.dropna(subset=['ifs_log', 'evento_extremo'] + LOCAIS + ['p_modelo'])
    logger.info('validação %d->%d | teste %d->%d linhas após dropna',
                antes[0], len(val), antes[1], len(tes))

    y_val = val['evento_extremo'].to_numpy()
    emissao_val = (val['data_hora'].dt.hour == HORA_EMISSAO).to_numpy()

    def dentro_da_amostra(score_val):
        return _pr(y_val[emissao_val], np.asarray(score_val)[emissao_val])

    resultados = [_avaliar('V0 IFS sozinho', tes, tes['ifs_chuva_24h'].to_numpy(),
                           dentro_da_amostra(val['ifs_chuva_24h'].to_numpy()))]
    logger.info('%-28s validação %.4f | TESTE estação-dia %.4f | operacional %.4f',
                'V0 IFS sozinho', resultados[0]['pr_auc_validacao'],
                resultados[0]['pr_auc_estacao_dia'], resultados[0]['pr_auc_operacional'])

    coeficientes = {}
    for nome, extras in VARIANTES.items():
        if not extras:
            continue
        colunas = ['ifs_log'] + extras
        modelo = make_pipeline(StandardScaler(),
                               LogisticRegression(max_iter=2000, C=1.0,
                                                  class_weight='balanced'))
        modelo.fit(val[colunas], y_val)
        score = modelo.predict_proba(tes[colunas])[:, 1]
        r = _avaliar(nome, tes, score,
                     dentro_da_amostra(modelo.predict_proba(val[colunas])[:, 1]))
        resultados.append(r)
        coeficientes[nome] = dict(zip(colunas,
                                      modelo[-1].coef_[0].round(4).tolist()))
        logger.info('%-28s validação %.4f | TESTE estação-dia %.4f | operacional %.4f',
                    nome, r['pr_auc_validacao'], r['pr_auc_estacao_dia'],
                    r['pr_auc_operacional'])

    if USAR_ARVORE:
        colunas = ['ifs_log', 'p_modelo'] + LOCAIS
        arvore = LGBMClassifier(n_estimators=200, learning_rate=0.05, num_leaves=15,
                                min_child_samples=200, reg_lambda=10.0,
                                class_weight='balanced', verbose=-1, random_state=42)
        arvore.fit(val[colunas], y_val)
        r = _avaliar('V5 árvore (com interação)', tes,
                     arvore.predict_proba(tes[colunas])[:, 1],
                     dentro_da_amostra(arvore.predict_proba(val[colunas])[:, 1]))
        resultados.append(r)
        logger.info('%-28s validação %.4f | TESTE estação-dia %.4f | operacional %.4f',
                    'V5 árvore', r['pr_auc_validacao'], r['pr_auc_estacao_dia'],
                    r['pr_auc_operacional'])

    base = resultados[0]['pr_auc_operacional']
    for r in resultados:
        r['ganho_sobre_ifs'] = 100 * (r['pr_auc_operacional'] / base - 1)

    logger.info('\n%s', pd.DataFrame(resultados).to_string(index=False))
    logger.info('\ncoeficientes (features padronizadas):')
    for nome, c in coeficientes.items():
        logger.info('  %-28s %s', nome, c)

    destino = REPORTS_DIR / f"combinador_ifs_{pd.Timestamp.now():%Y_%m_%d_%H_%M}.md"
    destino.write_text(
        "# As estações do INMET acrescentam algo sobre a previsão do ECMWF?\n\n"
        f"Gerado em {pd.Timestamp.now():%d/%m/%Y %H:%M}\n\n"
        "Combinador de poucos parâmetros (regressão logística), treinado na "
        "**validação** (2025-01 a 2025-08) e medido no **teste intocado** "
        "(2025-09 a 2026-07).\n\n"
        "A validação é o único período em que as predições do nosso modelo são "
        "fora da amostra *e* existe previsão do IFS — treinar em 2024 usaria "
        "predição in-sample e inflaria o peso do nosso modelo.\n\n"
        "Recalibração não pode melhorar estes números: PR-AUC mede ordenação e "
        "transformação monotônica a preserva. Qualquer ganho aqui é informação "
        "nova.\n\n"
        "A coluna **validação** é dentro da amostra: é onde o combinador foi "
        "ajustado. Se uma variante ganha lá e perde no teste, é sobreajuste; se "
        "não ganha nem lá, a informação é genuinamente redundante.\n\n"
        "| variante | PR-AUC validação (dentro) | PR-AUC estação-dia | PR-AUC operacional | ganho sobre o IFS |\n"
        "|---|---|---|---|---|\n" +
        "\n".join(f"| {r['variante']} | {r['pr_auc_validacao']:.4f} | "
                  f"{r['pr_auc_estacao_dia']:.4f} | "
                  f"{r['pr_auc_operacional']:.4f} | {r['ganho_sobre_ifs']:+.1f}% |"
                  for r in resultados) +
        "\n\n## Coeficientes (features padronizadas)\n\n"
        "Magnitude comparável entre si. Peso próximo de zero numa entrada "
        "significa que ela não acrescenta sobre as demais.\n\n```\n" +
        "\n".join(f"{n}\n  {c}" for n, c in coeficientes.items()) +
        "\n```\n",
        encoding='utf-8')
    logger.info('Relatório salvo em %s', destino)
