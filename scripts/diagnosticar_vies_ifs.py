"""O erro de volume do IFS é sistemático — e portanto corrigível — ou é ruído?

Contexto: a previsão de chuva do IFS (modelo global do ECMWF) tem MAE de 2,94 mm
contra 4,10 mm do nosso regressor. Antes de construir qualquer correção, é
preciso saber se o erro dela tem estrutura.

Distinção que orienta tudo: **recalibrar não pode melhorar a classificação.**
PR-AUC mede ordenação e qualquer transformação monotônica a preserva exatamente.
Então 0,3957 é piso intransponível por ajuste de escala — só informação nova o
supera. Já na regressão, correção de viés reduz o erro em mm sem informação
alguma. Este script mede o segundo caso.

Tudo é medido na VALIDAÇÃO. O teste fica intocado para o combinador.

Uso:
    MEM_MAX=11G ./run.sh scripts/diagnosticar_vies_ifs.py
"""
import logging

import numpy as np
import pandas as pd
from sklearn.isotonic import IsotonicRegression

from src.config import REPORTS_DIR
from src.ingestion import enrich_openmeteo, load_data
from src.model import separar_janelas
from src.processing import clean_data, create_features
from scripts.medir_baseline_ifs import _anexar_regua, _baixar_regua
from scripts.medir_degradacao_mos import INICIO_PREV

logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s %(levelname)s %(name)s — %(message)s',
                    datefmt='%H:%M:%S')
logger = logging.getLogger('vies_ifs')


def _mae(a, b):
    return float((a - b).abs().mean())


if __name__ == '__main__':
    bruto = enrich_openmeteo(clean_data(load_data()))
    fim = bruto['data_hora'].max().strftime('%Y-%m-%d')
    estacoes = (bruto.groupby('estacao_codigo', observed=True)
                .agg(lat=('latitude', 'first'), lon=('longitude', 'first')))
    _baixar_regua(estacoes, fim)

    feats = create_features(bruto)
    del bruto
    _tr, validacao, teste = separar_janelas(feats)
    val = _anexar_regua(feats[validacao].copy(), estacoes, fim)
    tes = _anexar_regua(feats[teste].copy(), estacoes, fim)
    del feats

    val = val[val['ifs_chuva_24h'].notna() & val['chuva_futura_24h'].notna()]
    tes = tes[tes['ifs_chuva_24h'].notna() & tes['chuva_futura_24h'].notna()]
    logger.info('validação %d linhas | teste %d linhas', len(val), len(tes))

    obs, prev = val['chuva_futura_24h'], val['ifs_chuva_24h']
    residuo = obs - prev

    logger.info('=== 1. VIÉS GLOBAL (validação) ===')
    logger.info('observado médio %.4f mm | previsto médio %.4f mm | viés %.4f mm',
                obs.mean(), prev.mean(), residuo.mean())
    logger.info('MAE %.4f mm | desvio do resíduo %.4f mm', _mae(obs, prev), residuo.std())

    logger.info('=== 2. VIÉS POR ESTAÇÃO ===')
    por_est = val.groupby('estacao_codigo', observed=True).apply(
        lambda g: pd.Series({
            'n': len(g),
            'vies': (g['chuva_futura_24h'] - g['ifs_chuva_24h']).mean(),
            'razao': g['chuva_futura_24h'].sum() / max(g['ifs_chuva_24h'].sum(), 1e-9),
        }), include_groups=False)
    logger.info('viés por estação: media %.4f | desvio %.4f | min %.4f | max %.4f',
                por_est['vies'].mean(), por_est['vies'].std(),
                por_est['vies'].min(), por_est['vies'].max())
    logger.info('razão observado/previsto: mediana %.4f | min %.4f | max %.4f',
                por_est['razao'].median(), por_est['razao'].min(), por_est['razao'].max())

    # quanto da variância do resíduo a identidade da estação explica
    media_est = val.groupby('estacao_codigo', observed=True)['chuva_futura_24h'].transform('mean') \
        - val.groupby('estacao_codigo', observed=True)['ifs_chuva_24h'].transform('mean')
    r2_estacao = 1 - ((residuo - media_est) ** 2).sum() / ((residuo - residuo.mean()) ** 2).sum()
    logger.info('variância do resíduo explicada pela estação: %.4f%%', 100 * r2_estacao)

    logger.info('=== 3. VIÉS CONDICIONAL À INTENSIDADE PREVISTA ===')
    faixas = [0, 1, 5, 10, 20, 30, 50, 75, 1e9]
    val = val.assign(faixa=pd.cut(prev, faixas, right=False))
    cond = val.groupby('faixa', observed=True).apply(
        lambda g: pd.Series({
            'n': len(g),
            'previsto_medio': g['ifs_chuva_24h'].mean(),
            'observado_medio': g['chuva_futura_24h'].mean(),
            'vies': (g['chuva_futura_24h'] - g['ifs_chuva_24h']).mean(),
            'razao': g['chuva_futura_24h'].mean() / max(g['ifs_chuva_24h'].mean(), 1e-9),
        }), include_groups=False)
    logger.info('\n%s', cond.to_string())

    logger.info('=== 4. QUANTO UMA CORREÇÃO SIMPLES RECUPERA (ajuste na validação, medido no teste) ===')
    obs_t, prev_t = tes['chuva_futura_24h'], tes['ifs_chuva_24h']
    resultados = [('IFS cru', _mae(obs_t, prev_t))]

    # (a) viés aditivo global
    resultados.append(('+ viés global aditivo', _mae(obs_t, prev_t + residuo.mean())))
    # (b) fator multiplicativo global
    fator = obs.sum() / max(prev.sum(), 1e-9)
    resultados.append((f'x fator global ({fator:.3f})', _mae(obs_t, prev_t * fator)))
    # (c) viés aditivo por estação
    mapa = por_est['vies']
    resultados.append(('+ viés por estação', _mae(obs_t, prev_t + tes['estacao_codigo'].map(mapa).fillna(0))))
    # (d) isotônica sobre a previsão
    iso = IsotonicRegression(out_of_bounds='clip').fit(prev, obs)
    resultados.append(('isotônica sobre a previsão', _mae(obs_t, pd.Series(iso.predict(prev_t), index=tes.index))))

    for nome, mae in resultados:
        logger.info('%-32s MAE %.4f mm', nome, mae)

    destino = REPORTS_DIR / f"vies_ifs_{pd.Timestamp.now():%Y_%m_%d_%H_%M}.md"
    destino.write_text(
        "# O erro de volume do IFS é corrigível?\n\n"
        f"Gerado em {pd.Timestamp.now():%d/%m/%Y %H:%M}\n\n"
        "**IFS** (*Integrated Forecasting System*) é o modelo global do **ECMWF**. "
        "Estrutura do erro medida na validação (2025-01 a 2025-08); as correções "
        "são ajustadas lá e medidas no teste intocado.\n\n"
        "**Nota que orienta a leitura:** recalibrar não pode melhorar a "
        "classificação — PR-AUC mede ordenação e transformação monotônica a "
        "preserva. Só informação nova supera o PR-AUC de 0,3957. Esta página trata "
        "só do erro de volume.\n\n"
        "## Viés global (validação)\n\n"
        f"- observado médio: {obs.mean():.4f} mm\n"
        f"- previsto médio: {prev.mean():.4f} mm\n"
        f"- viés (observado − previsto): **{residuo.mean():+.4f} mm**\n"
        f"- MAE: {_mae(obs, prev):.4f} mm | desvio do resíduo: {residuo.std():.4f} mm\n"
        f"- variância do resíduo explicada pela identidade da estação: "
        f"**{100*r2_estacao:.2f}%**\n\n"
        "## Viés condicional à intensidade prevista\n\n"
        "Se o IFS subestima chuva forte — comportamento comum em modelo numérico — "
        "aparece aqui como razão acima de 1 nas faixas altas.\n\n"
        "```\n" + cond.to_string() + "\n```\n\n"
        "## Quanto uma correção simples recupera (medido no teste)\n\n"
        "| correção | MAE |\n|---|---|\n" +
        "\n".join(f"| {n} | {m:.4f} mm |" for n, m in resultados) +
        f"\n\nReferência: nosso regressor atual, MAE 4,1045 mm no mesmo teste.\n",
        encoding='utf-8')
    logger.info('Relatório salvo em %s', destino)
