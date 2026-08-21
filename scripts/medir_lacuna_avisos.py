"""Quanta informação do aviso regional sobrevive até a estação de quem foi avisado?

NÃO mede erro. Aviso é comunicação de risco: aviso não confirmado é risco que não
se materializou, que é o funcionamento normal de um sistema de alerta. O que se
mede é TAXA DE CONFIRMAÇÃO, que é calibração — e a mesma régua se aplica à nossa
própria regra sobre o ECMWF quando as duas forem comparadas.

Desenho: reports/desenho_estudo_avisos_2026_08_20.md
Plano:   docs/superpowers/plans/2026-08-20-lacuna-granularidade-avisos.md

Uso:
    MEM_MAX=11G ./run.sh scripts/medir_lacuna_avisos.py
"""
import glob
import logging

import numpy as np
import pandas as pd

from src.avisos import expandir_estacao_dia, taxa_confirmacao
from src.config import CACHE_DIR, EXTREME_RAIN_THRESHOLD, REPORTS_DIR
from src.ingestion import enrich_openmeteo, load_data
from src.processing import clean_data, create_features
from scripts.medir_baseline_ifs import _anexar_regua
from scripts.medir_degradacao_mos import _media_futura, _trocar_por_previsao
from scripts.medir_acrescimo_local import INICIO_AJUSTE, separar_ajuste_avaliacao
from scripts.curva_operacao_ifs import varrer

logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s %(levelname)s %(name)s — %(message)s',
                    datefmt='%H:%M:%S')
logger = logging.getLogger('lacuna')

HORA_EMISSAO = 12
CHUVA = 'PRECIPITAÇÃO TOTAL, HORÁRIO (mm)'
RAJADA = 'VENTO, RAJADA MAXIMA (m/s)'
INICIO_JANELA, FIM_JANELA = '2025-01-02', '2026-07-31'
CORTES_MM = [5, 10, 15, 20, 25, 30, 40, 50, 60, 75]
# Abaixo disto a célula não sustenta afirmação: com 59 vendavais e 49 avisos de
# Grande Perigo no conjunto, o cruzamento tipo x severidade produz células de
# dois ou três casos, cujo intervalo de Wilson vai de quase zero a quase um.
MINIMO_CELULA = 30


def observacao_estacao_dia(df):
    """Chuva acumulada e rajada máxima por dia pluviométrico (12 UTC a 12 UTC)."""
    data = df['DATA (YYYY-MM-DD)'].fillna(df['Data']).astype(str).str.replace('/', '-', regex=False)
    hora = df['HORA (UTC)'].fillna(df['Hora UTC']).astype(str).str.slice(0, 2)
    dh = pd.to_datetime(data + ' ' + hora, format='%Y-%m-%d %H', errors='coerce', utc=True)
    t = pd.DataFrame({'estacao_codigo': df['estacao_codigo'].astype(str), 'dh': dh,
                      'mm': pd.to_numeric(df[CHUVA], errors='coerce'),
                      'ms': pd.to_numeric(df[RAJADA], errors='coerce')}).dropna(subset=['dh'])
    t['dia'] = (t['dh'] - pd.Timedelta(hours=HORA_EMISSAO)).dt.date
    g = t.groupby(['estacao_codigo', 'dia'], observed=True).agg(
        chuva_24h_obs=('mm', 'sum'), rajada_max_obs=('ms', 'max'),
        horas=('mm', 'count')).reset_index()
    # Menos de 18 horas medidas não sustentam um acumulado de 24 h.
    g = g[g['horas'] >= 18].drop(columns='horas')
    return g[(g['dia'] >= pd.Timestamp(INICIO_JANELA).date())
             & (g['dia'] <= pd.Timestamp(FIM_JANELA).date())]


def estacoes_de(df):
    e = (df[['estacao_codigo', 'latitude', 'longitude']].dropna()
         .groupby('estacao_codigo', observed=True).first().reset_index())
    e['estacao_codigo'] = e['estacao_codigo'].astype(str)
    return e


def carregar_avisos():
    arquivos = sorted(glob.glob(str(CACHE_DIR / 'avisos_inmet' / '*.parquet')))
    if not arquivos:
        raise SystemExit('cache de avisos vazio — rode scripts/colher_avisos_inmet.py antes')
    df = pd.concat([pd.read_parquet(f) for f in arquivos], ignore_index=True)
    d = pd.to_datetime(df['data_inicio'], errors='coerce')
    na_janela = df['obtido'] & (d >= INICIO_JANELA) & (d <= FIM_JANELA + ' 23:59')
    logger.info('%d identificadores tentados | %d obtidos | %d na janela',
                len(df), int(df['obtido'].sum()), int(na_janela.sum()))
    return df[na_janela].copy()


def painel(obs, par, limiar_mm=EXTREME_RAIN_THRESHOLD):
    """Todo estação-dia da janela, com e SEM aviso.

    O negativo é o que permite calcular recall. Sem ele só existe taxa de
    confirmação, e a frase "os avisos capturam X% dos eventos observados" — que é
    o resultado central — não pode ser dita.

    Quando mais de um aviso cobre o mesmo estação-dia vale o de maior severidade,
    e os critérios ficam os mais brandos entre eles: basta o fenômeno de qualquer
    aviso vigente ter ocorrido para que o dia esteja confirmado.
    """
    coberto = (par.groupby(['estacao_codigo', 'dia'], observed=True)
               .agg(id_severidade=('id_severidade', 'max'),
                    criterio_mm=('criterio_mm', 'min'),
                    criterio_ms=('criterio_ms', 'min')).reset_index())
    p = obs.merge(coberto, on=['estacao_codigo', 'dia'], how='left')
    p['tem_aviso'] = p['id_severidade'].notna()
    p['evento'] = p['chuva_24h_obs'] > limiar_mm
    return p


def confirmado(d):
    """Confirma se QUALQUER critério anunciado foi observado.

    Composto de propósito: 'Chuvas Intensas' também anuncia vento, e exigir os
    dois penalizaria um aviso que acertou o vendaval e não a chuva.
    """
    por_chuva = d['criterio_mm'].notna() & (d['chuva_24h_obs'] >= d['criterio_mm'])
    por_vento = d['criterio_ms'].notna() & (d['rajada_max_obs'] >= d['criterio_ms'])
    return (por_chuva | por_vento).to_numpy()


def _chave(mm, ms):
    """Chave estável para a combinação de critérios.

    NaN não é igual a si mesmo, então tuplas com NaN viram chaves distintas linha
    a linha — 5.590 "combinações" onde existem meia dúzia. Trocar por None
    resolve, porque None é igual a si mesmo.
    """
    return (None if pd.isna(mm) else float(mm), None if pd.isna(ms) else float(ms))


def taxa_base_por_combo(obs, combos):
    """P(chuva >= mm OU rajada >= ms) na climatologia da janela, por combinação.

    Sem isto a taxa de confirmação é ininterpretável. O critério de vendaval
    (40 km/h) se cumpre em ~20% dos dias por acaso, enquanto o de chuva
    (50 mm/dia) se cumpre em ~1,4% — comparar tipos pela confirmação crua compara
    barras de altura diferente, não habilidades diferentes.
    """
    base = {}
    for mm, ms in combos:
        cond = pd.Series(False, index=obs.index)
        if mm is not None:
            cond |= obs['chuva_24h_obs'] >= mm
        if ms is not None:
            cond |= obs['rajada_max_obs'] >= ms
        base[(mm, ms)] = float(cond.mean())
    return base


def _esperado(g, base):
    """Taxa que a climatologia sozinha entregaria para os critérios deste grupo."""
    chaves = [_chave(mm, ms) for mm, ms in zip(g['criterio_mm'], g['criterio_ms'])]
    return float(np.mean([base[k] for k in chaves])) if chaves else float('nan')


def _linha(nome, unidade, conf, n, esperado=float('nan')):
    taxa, (lo, hi) = taxa_confirmacao(conf)
    ganho = taxa / esperado if esperado and not np.isnan(esperado) and esperado > 0 else float('nan')
    return {'grupo': nome, 'unidade': unidade, 'n': n,
            'taxa': round(taxa, 3), 'ic_inf': round(lo, 3), 'ic_sup': round(hi, 3),
            'climatologia': round(esperado, 3), 'ganho': round(ganho, 1)}


def tabela_unidades(par_obs, chaves, base, minimo=0):
    """Taxa de confirmação em PONTO e em ÁREA, agrupada pelas chaves pedidas."""
    linhas = []
    for chave, g in par_obs.groupby(chaves, observed=True):
        nome = ' / '.join(str(k) for k in (chave if isinstance(chave, tuple) else (chave,)))
        esperado = _esperado(g, base)
        # ÁREA: o aviso conta como confirmado se QUALQUER estação dele confirmou.
        por_aviso = g.groupby('id', observed=True)['confirmado'].max()
        if len(por_aviso) < minimo:
            continue
        linhas.append(_linha(nome, 'área', por_aviso.to_numpy(), len(por_aviso), esperado))
        # PONTO: cada (estação, dia, aviso) é uma unidade — o que a pessoa vive.
        linhas.append(_linha(nome, 'ponto', g['confirmado'].to_numpy(), len(g), esperado))
    t = pd.DataFrame(linhas)
    if t.empty:
        return t, t
    lac = (t.pivot(index='grupo', columns='unidade', values='taxa')
           .assign(lacuna=lambda d: (d['área'] - d['ponto']).round(3)).reset_index())
    return t, lac


def previsao_estacao_dia():
    """Chuva prevista pelo ECMWF por estação-dia às 12 UTC, só de cache."""
    bruto = enrich_openmeteo(clean_data(load_data()))
    fim = bruto['data_hora'].max().strftime('%Y-%m-%d')
    geo = (bruto.groupby('estacao_codigo', observed=True)
           .agg(lat=('latitude', 'first'), lon=('longitude', 'first')))
    bruto = _trocar_por_previsao(bruto, fim, inicio=INICIO_AJUSTE)
    feats = create_features(bruto)
    del bruto
    _aju, ava = separar_ajuste_avaliacao(feats)
    d = _media_futura(feats[ava].copy())
    del feats
    d = _anexar_regua(d, geo, fim, inicio=INICIO_AJUSTE)
    d = d[d['data_hora'].dt.hour == HORA_EMISSAO]
    d = d[['estacao_codigo', 'data_hora', 'ifs_chuva_24h']].dropna()
    d['estacao_codigo'] = d['estacao_codigo'].astype(str)
    d['dia'] = (d['data_hora'] - pd.Timedelta(hours=HORA_EMISSAO)).dt.date
    return d[['estacao_codigo', 'dia', 'ifs_chuva_24h']]


def comparar_com_ecmwf(p, previsao):
    """Recall e taxa de confirmação do aviso, ao lado da curva do ECMWF.

    Mesmos estação-dias nos dois lados, mesmo alvo. Nenhuma das fontes é
    penalizada por diferença de unidade.

    A leitura honesta é HORIZONTAL: fixando a taxa de confirmação, qual fonte
    captura mais eventos? Isso mantém constante a tolerância a alarme não
    confirmado dos dois lados, e é a única comparação legítima entre um aviso de
    risco e uma regra automática de corte.
    """
    juntos = p.merge(previsao, on=['estacao_codigo', 'dia'], how='inner')
    y = juntos['evento'].to_numpy().astype(int)
    curva = varrer(y, juntos['ifs_chuva_24h'].to_numpy(), CORTES_MM)
    curva.insert(0, 'fonte', [f'ECMWF > {c:g} mm' for c in curva['corte']])
    curva = curva.drop(columns=['corte', 'f1', 'perdidos'])

    sev = juntos['id_severidade'].fillna(-1)
    pontos = []
    for nivel in sorted(s for s in sev.unique() if s >= 0):
        alerta = (sev >= nivel).to_numpy()
        n = int(alerta.sum())
        acertos = int(y[alerta].sum())
        pontos.append({'fonte': f'aviso INMET, severidade >= {int(nivel)}',
                       'alertas': n, 'acertos': acertos,
                       'precisao': round(acertos / max(n, 1), 3),
                       'recall': round(acertos / max(int(y.sum()), 1), 3)})
    return curva, pd.DataFrame(pontos), int(y.sum()), len(juntos)


def _md(df):
    """Tabela markdown sem depender de `tabulate`.

    O projeto monta as tabelas dos relatórios à mão desde curva_operacao_ifs.py —
    `DataFrame.to_markdown` exige uma dependência opcional que não está no venv, e
    a falha só aparece na última linha do script, depois de todo o cálculo.
    """
    cabecalho = '| ' + ' | '.join(str(c) for c in df.columns) + ' |'
    separador = '|' + '|'.join(['---'] * len(df.columns)) + '|'
    # `:g` depois de arredondar: 310.800 vira 310.8 e 0.609 continua 0.609.
    linhas = ['| ' + ' | '.join(
        f'{round(v, 3):g}' if isinstance(v, float) else str(v) for v in linha) + ' |'
        for linha in df.itertuples(index=False, name=None)]
    return '\n'.join([cabecalho, separador] + linhas)


def escrever_relatorio(secoes):
    destino = REPORTS_DIR / f"lacuna_granularidade_avisos_{pd.Timestamp.now():%Y_%m_%d_%H_%M}.md"
    partes = [
        "# A lacuna de granularidade do alerta regional",
        f"\nGerado em {pd.Timestamp.now():%d/%m/%Y %H:%M}\n",
        "**IFS** (*Integrated Forecasting System*) é o modelo global de previsão do **ECMWF** "
        "(*European Centre for Medium-Range Weather Forecasts*).\n",
        "## Como ler estes números\n",
        "Um aviso meteorológico não afirma que o fenômeno vai ocorrer — comunica que há risco "
        "relevante de ocorrer. Aviso não confirmado **não é erro**: a possibilidade existia e "
        "comunicá-la era a função dele. Serviços de alerta aceitam deliberadamente alta taxa de "
        "não confirmação em eventos de alto impacto, porque o custo de não avisar é assimétrico "
        "em relação ao custo de avisar à toa.\n",
        "Portanto o que segue é **taxa de confirmação** — entre os avisos de um grupo, em que "
        "fração o fenômeno anunciado foi registrado. É afirmação de calibração, não de acerto. "
        "**A mesma régua se aplica a nós:** a taxa da nossa regra sobre a previsão do ECMWF "
        "também é confirmação, não erro.\n",
        "Cada aviso é verificado contra o critério que **ele mesmo anuncia**, extraído do campo "
        "`riscos`, e o critério é composto: confirma se chuva **ou** rajada cumpriu o anunciado.\n",
        f"\n{secoes['contexto']}\n",
        "\n## Cobertura dos avisos\n",
        f"{secoes['recall']}\n",
        "\n## Taxa de confirmação por severidade\n",
        "**Área**: alguma estação dentro do polígono registrou o anunciado. **Ponto**: a estação "
        "daquele local registrou. As duas nunca são lidas isoladas — a de área superestima o que "
        "o aviso significa para o indivíduo, e a de ponto subestima a qualidade de quem o emitiu.\n",
        "A coluna **climatologia** é a taxa que o acaso entregaria para os mesmos critérios na "
        "mesma janela, e **ganho** é quantas vezes o aviso supera isso. Sem essa referência a "
        "taxa de confirmação é ininterpretável: o critério de vendaval (40 km/h) se cumpre em "
        "cerca de 20% dos dias sozinho, enquanto o de chuva (50 mm/dia) se cumpre em 1,4% — "
        "comparar tipos pela confirmação crua compara barras de altura diferente, não "
        "habilidades diferentes.\n",
        _md(secoes['sev']),
        "\n## Taxa de confirmação por tipo de aviso\n",
        _md(secoes['tipo']),
        "\n## A lacuna\n",
        "A diferença entre área e ponto é o resultado central: quantifica quanta informação se "
        "perde entre *o aviso é correto para a região* e *o aviso diz algo sobre a minha rua*.\n",
        "\n### Por severidade\n", _md(secoes['lac_sev']),
        "\n### Por tipo\n", _md(secoes['lac_tipo']),
        "\n## Ao lado da previsão do ECMWF, nos mesmos estação-dias\n",
        "Ler na **horizontal**: fixando a taxa de confirmação (coluna `precisao`), qual fonte "
        "captura mais eventos? Isso mantém constante a tolerância a alarme não confirmado dos "
        "dois lados, e é a única comparação legítima entre um aviso de risco e uma regra "
        "automática de corte.\n",
        "**Os avisos não são independentes do ECMWF** — o INMET usa modelos globais para "
        "emiti-los. A comparação é *aviso curado por meteorologista, por área* contra *regra "
        "automática de corte*, não humano contra máquina do zero.\n",
        _md(secoes['pontos']),
        "\n", _md(secoes['curva']),
        f"\n## Cobertura da extração de critérios\n\n{secoes['cobertura']}\n",
        "\n## Limitações\n",
        "- Os avisos não são independentes da previsão do ECMWF (acima).",
        "- O critério vem de texto livre; a cobertura da extração está declarada acima.",
        "- Municípios sem estação não entram: a lacuna medida é a que as estações enxergam.",
        "- A ordem temporal dos identificadores não é estrita — 188 quebras e recuo máximo de 6 "
        "dias. Por isso a colheita levou margem de 100 identificadores de cada lado, que resgatou "
        "15 avisos dentro da janela.",
        "- **Rajada é medida num ponto e vendaval convectivo é fenômeno de escala pequena.** A "
        "estação pode não estar onde o vento passou, o que deprime a confirmação de vendaval por "
        "razão instrumental, não meteorológica.",
        f"\n- Células com menos de {MINIMO_CELULA} avisos foram omitidas do cruzamento tipo x "
        "severidade: o intervalo de Wilson nelas vai de quase zero a quase um e não sustenta "
        "afirmação.",
    ]
    destino.write_text("\n".join(str(p) for p in partes) + "\n", encoding='utf-8')
    logger.info('Relatório salvo em %s', destino)
    return destino


if __name__ == '__main__':
    df = load_data()
    obs, estacoes = observacao_estacao_dia(df), estacoes_de(df)
    del df

    avisos = carregar_avisos()
    par = expandir_estacao_dia(avisos, estacoes, HORA_EMISSAO)
    logger.info('%d pares (estação, dia, aviso) | %d avisos com estação dentro',
                len(par), par['id'].nunique())

    p = painel(obs, par)
    n_ev = int(p['evento'].sum())
    recall = p.loc[p['evento'], 'tem_aviso'].mean()
    logger.info('%d estação-dias | %.1f%% sob aviso | %d eventos acima de %d mm',
                len(p), 100 * p['tem_aviso'].mean(), n_ev, EXTREME_RAIN_THRESHOLD)
    logger.info('RECALL: %.1f%% dos eventos observados tinham aviso vigente', 100 * recall)

    par_obs = par.merge(obs, on=['estacao_codigo', 'dia'], how='inner')
    par_obs['confirmado'] = confirmado(par_obs)
    logger.info('%d pares com observação | %.1f%% confirmados no ponto',
                len(par_obs), 100 * par_obs['confirmado'].mean())

    combos = {_chave(mm, ms) for mm, ms in zip(par_obs['criterio_mm'], par_obs['criterio_ms'])}
    base = taxa_base_por_combo(obs, combos)
    logger.info('%d combinações de critério | taxa base de %.2f%% a %.2f%%', len(base),
                100 * min(base.values()), 100 * max(base.values()))
    sev, lac_sev = tabela_unidades(par_obs, ['severidade'], base)
    tipo, lac_tipo = tabela_unidades(par_obs, ['descricao'], base)
    logger.info('\n%s', sev.to_string(index=False))
    logger.info('\n%s', lac_sev.to_string(index=False))

    previsao = previsao_estacao_dia()
    curva, pontos, n_ev_comp, n_comp = comparar_com_ecmwf(p, previsao)
    logger.info('\n%s', pontos.to_string(index=False))
    logger.info('\n%s', curva.to_string(index=False))

    cob_mm = 100 * par_obs['criterio_mm'].notna().mean()
    cob_ms = 100 * par_obs['criterio_ms'].notna().mean()
    escrever_relatorio({
        'contexto': (f"Janela **{INICIO_JANELA} a {FIM_JANELA}**, {p['estacao_codigo'].nunique()} "
                     f"estações, {len(p):,} estação-dias, {n_ev} eventos acima de "
                     f"{EXTREME_RAIN_THRESHOLD} mm em 24 h. {avisos['id'].nunique():,} avisos "
                     f"colhidos na janela, dos quais {par['id'].nunique():,} contêm alguma "
                     f"estação. Unidade: um alerta por estação-dia, ancorado às "
                     f"{HORA_EMISSAO:02d} UTC — início do dia pluviométrico do INMET."),
        'recall': (f"**{100 * recall:.1f}% dos {n_ev} eventos observados tinham aviso vigente**, e "
                   f"{100 * p['tem_aviso'].mean():.1f}% de todos os estação-dias estavam sob algum "
                   f"aviso dos quatro tipos estudados."),
        'sev': sev, 'tipo': tipo, 'lac_sev': lac_sev, 'lac_tipo': lac_tipo,
        'pontos': pontos, 'curva': curva,
        'cobertura': (f"Critério de chuva extraído em **{cob_mm:.1f}%** dos pares e critério de "
                      f"vento em **{cob_ms:.1f}%**. A comparação usa {n_comp:,} estação-dias com "
                      f"previsão disponível, contendo {n_ev_comp} eventos."),
    })
