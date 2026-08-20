"""Se a defesa civil alertar quando o ECMWF prevê mais de X mm, o que ela recebe?

Por que existe: todas as métricas do IFS neste projeto são PR-AUC, que é
ordenação. Ordenação não responde a pergunta que decide o produto — "alertando
neste corte, pego quantos eventos e quantos alertas falsos disparo?". Sem essa
tabela, ninguém consegue dizer se a previsão europeia crua já é entregável.

O corte aqui é em MILÍMETROS PREVISTOS, não em probabilidade de modelo. Isso
importa para o produto: a regra vira "alerta quando o ECMWF prevê mais de X mm
em 24 h", que um operador entende e audita sem saber o que é um classificador.

Janela: a mesma avaliação da medição de acréscimo local (2025-01-02 em diante),
unidade operacional — um alerta por estação-dia às 12 UTC.

Uso:
    MEM_MAX=11G ./run.sh scripts/curva_operacao_ifs.py
"""
import logging

import joblib
import numpy as np
import pandas as pd

from src.config import FEATURE_COLUMNS, MODELS_DIR, REPORTS_DIR
from src.ingestion import enrich_openmeteo, load_data
from src.processing import clean_data, create_features
from scripts.medir_baseline_ifs import _anexar_regua
from scripts.medir_degradacao_mos import HORA_EMISSAO, _media_futura, _trocar_por_previsao
from scripts.medir_acrescimo_local import INICIO_AJUSTE, rotular, separar_ajuste_avaliacao

logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s %(levelname)s %(name)s — %(message)s',
                    datefmt='%H:%M:%S')
logger = logging.getLogger('curva')

CORTES_MM = [0.5, 1, 2, 3, 5, 7.5, 10, 15, 20, 25, 30, 40, 50, 60, 75, 100]
RECALLS_ALVO = [0.5, 0.6, 0.7, 0.8, 0.9]


def varrer(y, score, cortes):
    """Precisão, recall e F1 em cada corte. Alerta = score >= corte."""
    y = np.asarray(y)
    score = np.asarray(score, dtype=float)
    positivos = int(y.sum())
    linhas = []
    for corte in cortes:
        alerta = score >= corte
        n = int(alerta.sum())
        acertos = int(y[alerta].sum()) if n else 0
        precisao = acertos / n if n else float('nan')
        recall = acertos / positivos if positivos else float('nan')
        f1 = (2 * precisao * recall / (precisao + recall)
              if n and acertos and (precisao + recall) > 0 else 0.0)
        linhas.append({'corte': corte, 'alertas': n, 'acertos': acertos,
                       'precisao': precisao, 'recall': recall, 'f1': f1,
                       'perdidos': positivos - acertos})
    return pd.DataFrame(linhas)


def _corte_para_recall(y, score, alvo):
    """Maior corte (menos alertas) que ainda alcança o recall pedido."""
    y = np.asarray(y)
    score = np.asarray(score, dtype=float)
    candidatos = np.unique(np.round(score[y == 1], 2))
    melhor = None
    for corte in candidatos:
        alerta = score >= corte
        n = int(alerta.sum())
        if not n:
            continue
        recall = y[alerta].sum() / y.sum()
        if recall >= alvo:
            melhor = {'corte': float(corte), 'alertas': n,
                      'precisao': float(y[alerta].sum() / n), 'recall': float(recall)}
    return melhor


def _tabela(df, total_unidades, estacoes, anos):
    linhas = ["| corte (mm previstos) | alertas | acertos | precisão | recall | F1 | "
              "eventos perdidos | alertas por estação-ano |", "|---|---|---|---|---|---|---|---|"]
    for _, r in df.iterrows():
        por_ano = r['alertas'] / (estacoes * anos)
        linhas.append(
            f"| {r['corte']:g} | {int(r['alertas'])} | {int(r['acertos'])} | "
            f"{r['precisao']:.3f} | {r['recall']:.3f} | {r['f1']:.3f} | "
            f"{int(r['perdidos'])} | {por_ano:.1f} |")
    return "\n".join(linhas)


if __name__ == '__main__':
    bruto = enrich_openmeteo(clean_data(load_data()))
    fim = bruto['data_hora'].max().strftime('%Y-%m-%d')
    estacoes_geo = (bruto.groupby('estacao_codigo', observed=True)
                    .agg(lat=('latitude', 'first'), lon=('longitude', 'first')))
    bruto = _trocar_por_previsao(bruto, fim, inicio=INICIO_AJUSTE)

    feats = create_features(bruto)
    del bruto
    _aju, ava_mask = separar_ajuste_avaliacao(feats)
    ava = _media_futura(feats[ava_mask].copy())
    del feats
    ava = _anexar_regua(ava, estacoes_geo, fim, inicio=INICIO_AJUSTE)

    clf = joblib.load(MODELS_DIR / 'classifier.pkl')

    doze = ava[ava['data_hora'].dt.hour == HORA_EMISSAO].copy()
    antes = len(doze)
    doze = doze.dropna(subset=['ifs_chuva_24h', 'chuva_futura_24h'])
    doze['p_modelo'] = clf.predict_proba(doze[FEATURE_COLUMNS].astype('float32'))[:, 1]
    n_est = doze['estacao_codigo'].nunique()
    anos = (doze['data_hora'].max() - doze['data_hora'].min()).days / 365.25
    logger.info('avaliação às %02d UTC: %d->%d estação-dias | %d estações | %.2f anos',
                HORA_EMISSAO, antes, len(doze), n_est, anos)

    partes = [
        "# Se a defesa civil alertar quando o ECMWF prevê mais de X mm, o que ela recebe?",
        f"\nGerado em {pd.Timestamp.now():%d/%m/%Y %H:%M}\n",
        "**IFS** (*Integrated Forecasting System*) é o modelo global de previsão do **ECMWF** "
        "(*European Centre for Medium-Range Weather Forecasts*).\n",
        "Todas as medições anteriores deste projeto usam **PR-AUC** (área sob a curva "
        "precisão-recall), que mede ordenação. Ordenação não diz quantos alertas você dispara. "
        "Esta página traduz a previsão em regra de operação.\n",
        f"Janela: **{doze['data_hora'].min():%Y-%m-%d} a {doze['data_hora'].max():%Y-%m-%d}** "
        f"({anos:.2f} anos), {n_est} estações, {len(doze):,} estação-dias. Um alerta por "
        f"estação-dia, emitido às {HORA_EMISSAO:02d} UTC — o início do dia pluviométrico do INMET.\n",
        "A regra é **\"alerta quando o ECMWF prevê mais de X mm nas próximas 24 h\"**. O corte é em "
        "milímetros previstos, não em probabilidade de modelo: um operador audita a regra sem "
        "precisar saber o que é um classificador.\n",
    ]

    for limiar in (50, 30):
        y = rotular(doze, limiar)
        base = y.mean()
        partes += [
            f"\n## Evento = mais de {limiar} mm em 24 h\n",
            f"{int(y.sum())} eventos em {len(doze):,} estação-dias (taxa base **{100*base:.2f}%**). "
            f"Alertar sempre daria precisão de {100*base:.2f}%; é essa a régua do acaso.\n",
            _tabela(varrer(y, doze['ifs_chuva_24h'], CORTES_MM), len(doze), n_est, anos),
        ]
        sweep = varrer(y, doze['ifs_chuva_24h'], np.arange(0.5, 80, 0.5))
        melhor = sweep.loc[sweep['f1'].idxmax()]
        partes.append(
            f"\n**Melhor F1:** corte de {melhor['corte']:g} mm — precisão {melhor['precisao']:.3f}, "
            f"recall {melhor['recall']:.3f}, {int(melhor['alertas'])} alertas "
            f"({melhor['alertas']/(n_est*anos):.1f} por estação-ano).\n")

        partes.append("\n**Se o custo de não avisar for o que manda** — o caso da defesa civil — "
                      "o corte desce e a precisão cai junto:\n")
        partes.append("| recall pedido | corte (mm) | alertas | precisão | alertas por estação-ano |")
        partes.append("|---|---|---|---|---|")
        for alvo in RECALLS_ALVO:
            p = _corte_para_recall(y, doze['ifs_chuva_24h'].to_numpy(), alvo)
            if p:
                partes.append(f"| {100*alvo:.0f}% | {p['corte']:g} | {p['alertas']} | "
                              f"{p['precisao']:.3f} | {p['alertas']/(n_est*anos):.1f} |")

        # O nosso modelo na MESMA janela e MESMA unidade, para comparação honesta.
        nosso = varrer(y, doze['p_modelo'], np.arange(0.02, 0.98, 0.01))
        mn = nosso.loc[nosso['f1'].idxmax()]
        partes.append(
            f"\n**Nosso modelo, na mesma janela e mesma unidade:** melhor F1 {mn['f1']:.3f} "
            f"(precisão {mn['precisao']:.3f}, recall {mn['recall']:.3f}) contra "
            f"{melhor['f1']:.3f} do IFS. A janela é fora da amostra para ele — o treino termina "
            "em 2024-12-31.\n")

    destino = REPORTS_DIR / f"curva_operacao_ifs_{pd.Timestamp.now():%Y_%m_%d_%H_%M}.md"
    destino.write_text("\n".join(partes) + "\n", encoding='utf-8')
    logger.info('Relatório salvo em %s', destino)
