"""Quanto a observação local acrescenta sobre a previsão do ECMWF?

Três medições anteriores fecharam portas, e este script só existe porque elas
fecharam: (1) o viés do IFS não é corrigível — a identidade da estação explica
0,80% da variância do resíduo; (2) recalibrar não pode ajudar, porque PR-AUC mede
ordenação e transformação monotônica a preserva; (3) o escore do nosso modelo não
é informação nova — o intervalo cruzou zero. Sobra a observação local crua.

O que muda em relação a combinar_ifs_local.py, de 19/08/2026:

  - **ajuste em abr-dez/2024**, não na validação de 2025. Só as variantes que NÃO
    consomem o escore do nosso modelo podem fazer isso, porque 2024 é dentro da
    amostra para ele e fora da amostra para observações do INMET. São 10x mais
    eventos de ajuste, o que separa duas hipóteses hoje confundíveis: "não há o
    que corrigir" de "não conseguimos estimar a correção" (8 coeficientes com 142
    eventos são 18 por parâmetro).
  - **quatro cenários** de limiar e hora de emissão, com o primário declarado
    antes de rodar.
  - **bootstrap agrupado por data**, além do por unidade.
  - **unidade estação-dia excluída.** Ela toma o máximo das 24 h do dia, e as
    features locais incluem chuva passada: na hora 23 a janela de 24 h já viu a
    chuva do dia que o rótulo mede. É a circularidade que inflava a persistência.

Plano: docs/superpowers/plans/2026-08-20-acrescimo-local-sobre-ecmwf.md

Uso:
    MEM_MAX=11G ./run.sh scripts/medir_acrescimo_local.py
"""
import logging
import sys

import numpy as np
import pandas as pd
from lightgbm import LGBMClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from src.config import EMBARGO_HORAS, REPORTS_DIR
from src.ingestion import enrich_openmeteo, load_data
from src.openmeteo_client import _cache_utilizavel, _previsao_cache_path
from src.processing import clean_data, create_features
from scripts.medir_baseline_ifs import _anexar_regua, _baixar_regua
from scripts.medir_degradacao_mos import _media_futura, _trocar_por_previsao

logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s %(levelname)s %(name)s — %(message)s',
                    datefmt='%H:%M:%S')
logger = logging.getLogger('acrescimo')

# O arquivo de previsão do IFS começa entre jan e abr/2024 conforme a estação;
# abr/2024 é o início seguro para todas.
INICIO_AJUSTE = '2024-04-01'
FIM_AJUSTE = pd.Timestamp('2024-12-31 23:00', tz='UTC')

# Endpoint primário declarado AQUI, antes de qualquer resultado existir. Os
# outros três são secundários e existem para separar "não há sinal" de "não há
# sinal na cauda extrema".
CENARIOS = [
    {'nome': '50 mm, 12 UTC',    'limiar': 50, 'horas': (12,),   'primario': True},
    {'nome': '50 mm, 00+12 UTC', 'limiar': 50, 'horas': (0, 12), 'primario': False},
    {'nome': '30 mm, 12 UTC',    'limiar': 30, 'horas': (12,),   'primario': False},
    {'nome': '30 mm, 00+12 UTC', 'limiar': 30, 'horas': (0, 12), 'primario': False},
]

# Observação local crua: o que uma estação sabe agora e a grade de 24 km do ECMWF
# não vê. `viz_chuva_3h` é o que as vizinhas mediram — informação genuinamente
# espacial que nenhuma célula de grade carrega.
LOCAIS = ['chuva_24h', 'chuva_3h', 'queda_pressao_24h', 'soil_moisture',
          'clima_chuva_mes', 'viz_chuva_3h', 'umidade', 'orvalho']

# Nenhuma consome `p_modelo`: seria dentro da amostra na janela de ajuste.
VARIANTES = {
    # V0b não é hipótese, é VERIFICAÇÃO DE BUG. Uma logística só sobre ifs_log é
    # transformação monotônica da própria régua, e PR-AUC mede ordenação: ela tem
    # de reproduzir o PR-AUC da V0 quase exatamente. Se não reproduzir, o defeito
    # está no encanamento (alinhamento de escore, dropna, máscara de hora) e
    # nenhum outro número desta tabela vale. Faltava no plano original.
    'V0b só IFS, via logística':  [],
    'V2 IFS + observação local':  LOCAIS,
    'V4 IFS + orvalho + pressão': ['orvalho', 'queda_pressao_24h'],
}
USAR_ARVORE = True   # V5 = árvore sobre ifs_log + LOCAIS, para pegar interação


def _pr(y, score):
    score = np.asarray(score, dtype=float)
    ok = ~np.isnan(score)
    return float(average_precision_score(np.asarray(y)[ok], score[ok]))


def separar_ajuste_avaliacao(df):
    """Ajuste em abr-dez/2024, avaliação depois, com embargo de EMBARGO_HORAS.

    O embargo não é formalidade: o alvo da última linha de ajuste é a soma de
    t+1..t+24, que invade o começo da avaliação.
    """
    t = df['data_hora']
    embargo = pd.Timedelta(hours=EMBARGO_HORAS)
    ajuste = (t >= pd.Timestamp(INICIO_AJUSTE, tz='UTC')) & (t <= FIM_AJUSTE)
    avaliacao = t > FIM_AJUSTE + embargo
    return ajuste, avaliacao


def rotular(df, limiar):
    """Rótulo 0/1 a partir da soma futura de 24 h, no limiar pedido."""
    return (df['chuva_futura_24h'] > limiar).astype(int).to_numpy()


def filtrar_estacoes(df, estacoes_ok):
    """Restringe o frame a um conjunto de estações. `None` devolve tudo.

    Existe porque 56% da janela de avaliação são estações que entraram na rede do
    INMET depois de maio/2024 e que o combinador nunca viu no ajuste. Sem separar
    isso, um resultado negativo mistura duas causas: a informação local ser
    redundante, e o combinador não transferir para estações novas.
    """
    if estacoes_ok is None:
        return df
    return df[df['estacao_codigo'].isin(estacoes_ok)]


def bootstrap_ic(y, base, alt, grupos=None, n=2000, semente=42):
    """IC 95% da diferença de PR-AUC, pareado. Com `grupos`, reamostra grupos inteiros.

    Pareado: base e alternativa são pontuadas nas MESMAS unidades, e reamostrar
    as unidades preserva o pareamento — comparar dois números soltos não
    distingue ganho real de variação amostral.

    Agrupado: chuva extrema é sinótica. Uma frente atinge dezenas de estações no
    mesmo dia, e as duas emissões de um dia veem a mesma atmosfera. Reamostrar
    linhas soltas trata isso como informação independente e devolve intervalo
    estreito demais — pseudo-replicação. O intervalo agrupado é o honesto; o
    solto entra no relatório só para comparar com a medição de 19/08/2026.
    """
    rng = np.random.default_rng(semente)
    y, base, alt = map(np.asarray, (y, base, alt))
    if grupos is None:
        blocos = [np.array([i]) for i in range(len(y))]
    else:
        _, inverso = np.unique(np.asarray(grupos), return_inverse=True)
        ordem = np.argsort(inverso, kind='stable')
        cortes = np.flatnonzero(np.diff(inverso[ordem])) + 1
        blocos = np.split(ordem, cortes)

    diferencas = np.empty(n)
    for i in range(n):
        escolha = rng.integers(0, len(blocos), len(blocos))
        idx = np.concatenate([blocos[j] for j in escolha])
        if y[idx].sum() == 0:
            diferencas[i] = np.nan
            continue
        diferencas[i] = (average_precision_score(y[idx], alt[idx])
                         - average_precision_score(y[idx], base[idx]))
    return float(np.nanmean(diferencas)), tuple(np.nanpercentile(diferencas, [2.5, 97.5]))


def _modelos():
    modelos = {n: make_pipeline(StandardScaler(),
                                # SEM class_weight: logística não ponderada é regra
                                # de pontuação própria, então o ajuste ótimo dá a
                                # ordenação ótima — que é o que PR-AUC mede. Com
                                # `balanced` a perda deixa de alinhar com a métrica
                                # e já custou uma conclusão invertida aqui.
                                LogisticRegression(max_iter=2000, C=1.0))
               for n in VARIANTES}
    if USAR_ARVORE:
        modelos['V5 árvore (interação)'] = LGBMClassifier(
            n_estimators=200, learning_rate=0.05, num_leaves=15, min_child_samples=200,
            reg_lambda=10.0, verbose=-1, random_state=42)
    return modelos


def _rodar_cenario(cen, aju, ava, sufixo='', estacoes_ok=None):
    """Ajusta as variantes num cenário e devolve as linhas do relatório.

    O ajuste NUNCA é restrito: ele já só tem as estações de 2024. A restrição vale
    para a avaliação, e é o que isola transferência de redundância.
    """
    nome_cen = cen['nome'] + sufixo
    primario = cen['primario'] and not sufixo
    a = aju[aju['data_hora'].dt.hour.isin(cen['horas']).to_numpy()]
    v = filtrar_estacoes(ava, estacoes_ok)
    v = v[v['data_hora'].dt.hour.isin(cen['horas']).to_numpy()]
    y_a, y_v = rotular(a, cen['limiar']), rotular(v, cen['limiar'])

    logger.info('=== %s | ajuste %d linhas / %d eventos | avaliação %d / %d ===',
                nome_cen, len(a), int(y_a.sum()), len(v), int(y_v.sum()))
    if y_a.sum() < 30 or y_v.sum() < 30:
        logger.error('%s tem eventos de menos — não vou reportar', nome_cen)
        return []

    # Uma data = uma atmosfera. É o grupo do bootstrap conservador.
    grupos = v['data_hora'].dt.date.to_numpy()
    base = v['ifs_chuva_24h'].to_numpy()

    saida = [{'cenario': nome_cen, 'variante': 'V0 IFS sozinho', 'primario': primario,
              'pr_auc': _pr(y_v, base), 'dentro': _pr(y_a, a['ifs_chuva_24h']),
              'delta': 0.0, 'ic_solto': (0.0, 0.0), 'ic_data': (0.0, 0.0),
              'n_ajuste': int(y_a.sum()), 'n_avaliacao': int(y_v.sum())}]
    logger.info('%-28s fora %.4f (dentro %.4f)', 'V0 IFS sozinho',
                saida[0]['pr_auc'], saida[0]['dentro'])

    for nome, modelo in _modelos().items():
        extras = LOCAIS if nome.startswith('V5') else VARIANTES[nome]
        colunas = ['ifs_log'] + extras
        modelo.fit(a[colunas], y_a)
        score = modelo.predict_proba(v[colunas])[:, 1]
        media_s, ic_s = bootstrap_ic(y_v, base, score)
        media_d, ic_d = bootstrap_ic(y_v, base, score, grupos=grupos)
        saida.append({'cenario': nome_cen, 'variante': nome, 'primario': primario,
                      'pr_auc': _pr(y_v, score),
                      'dentro': _pr(y_a, modelo.predict_proba(a[colunas])[:, 1]),
                      'delta': media_d, 'ic_solto': ic_s, 'ic_data': ic_d,
                      'n_ajuste': int(y_a.sum()), 'n_avaliacao': int(y_v.sum())})
        logger.info('%-28s fora %.4f (dentro %.4f) | Δ %+.4f | solto [%+.4f, %+.4f] | '
                    'por data [%+.4f, %+.4f]', nome, saida[-1]['pr_auc'],
                    saida[-1]['dentro'], media_d, ic_s[0], ic_s[1], ic_d[0], ic_d[1])
    return saida


def _escrever_relatorio(linhas):
    destino = REPORTS_DIR / f"acrescimo_local_{pd.Timestamp.now():%Y_%m_%d_%H_%M}.md"
    primario = next(c['nome'] for c in CENARIOS if c['primario'])
    corpo = [
        "# Quanto a observação local acrescenta sobre a previsão do ECMWF?",
        f"\nGerado em {pd.Timestamp.now():%d/%m/%Y %H:%M}\n",
        "**IFS** (*Integrated Forecasting System*) é o modelo global de previsão do **ECMWF** "
        "(*European Centre for Medium-Range Weather Forecasts*). **PR-AUC** é a área sob a curva "
        "precisão-recall — a métrica certa quando o evento é raro.\n",
        f"Combinador de poucos parâmetros ajustado em **{INICIO_AJUSTE} a "
        f"{FIM_AJUSTE:%Y-%m-%d}** e medido em **{FIM_AJUSTE + pd.Timedelta(hours=EMBARGO_HORAS):%Y-%m-%d} "
        "em diante**, sem retreinar modelo nenhum.\n",
        f"**Endpoint primário, declarado no código antes de rodar: {primario}.** "
        "Os outros três cenários são secundários e existem para separar *não há sinal* de "
        "*não há sinal na cauda extrema*.\n",
        "Nenhuma variante consome o escore do nosso modelo: 2024 é dentro da amostra para ele, e "
        "usá-lo aqui inflaria o resultado. As variantes que o usam foram medidas em 19/08/2026 e "
        "ficaram com intervalo cruzando zero.\n",
        "A unidade **estação-dia** foi excluída de propósito: ela toma o máximo das 24 h do dia, e "
        "as features locais incluem chuva passada — na hora 23 a janela de 24 h já viu a chuva do "
        "dia que o rótulo mede. É a mesma circularidade que inflava a persistência.\n",
        "**Histórico de seleção, para leitura honesta:** a V2 foi eleita candidata depois de ver o "
        "teste em 19/08/2026. Por isso todas as variantes são reportadas aqui, não só ela.\n",
        "**Dois intervalos.** O *por unidade* reamostra linhas e é comparável com o relatório de "
        "19/08. O *por data* reamostra dias inteiros: chuva extrema é sinótica, e tratar 100 "
        "estações da mesma frente como 100 observações independentes é pseudo-replicação. "
        "**O intervalo por data é o que vale.**\n",
        "| cenário | variante | eventos (ajuste/avaliação) | PR-AUC | dentro da amostra | "
        "Δ vs IFS | IC 95% por unidade | IC 95% por data |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for r in linhas:
        marca = ' **(primário)**' if r['primario'] and r['variante'] != 'V0 IFS sozinho' else ''
        corpo.append(
            f"| {r['cenario']}{marca} | {r['variante']} | {r['n_ajuste']}/{r['n_avaliacao']} | "
            f"{r['pr_auc']:.4f} | {r['dentro']:.4f} | {r['delta']:+.4f} | "
            f"[{r['ic_solto'][0]:+.4f}, {r['ic_solto'][1]:+.4f}] | "
            f"[{r['ic_data'][0]:+.4f}, {r['ic_data'][1]:+.4f}] |")

    corpo += [
        "\n## Limites superiores\n",
        "Quando o intervalo cruza zero, o resultado não é *nada acontece* — é *o acréscimo, se "
        "existir, é menor que o limite abaixo*. **Esse é o entregável deste estudo**, porque a "
        "aritmética de potência foi feita antes de rodar: com o número de eventos disponível, o "
        "menor efeito detectável é da ordem de 2,6% a 5,1% sobre o IFS, e o efeito medido em "
        "19/08 foi de 1,7%. Nenhum desenho possível com este dado detectaria 1,7%.\n",
        "| cenário | variante | limite superior (IC por data) |",
        "|---|---|---|",
    ]
    for r in linhas:
        if r['variante'] != 'V0 IFS sozinho' and r['ic_data'][0] <= 0:
            corpo.append(f"| {r['cenario']} | {r['variante']} | {r['ic_data'][1]:+.4f} |")

    corpo += [
        "\n## Regra de leitura, fixada antes de ver o resultado\n",
        "| resultado | conclusão |",
        "|---|---|",
        "| 30 mm positivo, 50 mm nulo | a observação local contribui, mas não alcança a cauda extrema |",
        "| ambos nulos, com limites estreitos | o ECMWF já contém o que as estações sabem |",
        "| 50 mm positivo | exige explicação mecanicista antes de ser aceito |",
        "\nA coluna **dentro da amostra** é onde o combinador foi ajustado. Se uma variante ganha "
        "lá e não ganha na avaliação, é sobreajuste; se não ganha nem lá, a informação é "
        "genuinamente redundante — e essa distinção é a razão de a janela de ajuste ter sido "
        "ampliada.\n",
    ]
    destino.write_text("\n".join(corpo) + "\n", encoding='utf-8')
    logger.info('Relatório salvo em %s', destino)
    return destino


if __name__ == '__main__':
    bruto = enrich_openmeteo(clean_data(load_data()))
    fim = bruto['data_hora'].max().strftime('%Y-%m-%d')
    estacoes = (bruto.groupby('estacao_codigo', observed=True)
                .agg(lat=('latitude', 'first'), lon=('longitude', 'first')))

    _baixar_regua(estacoes, fim, inicio=INICIO_AJUSTE)

    # _baixar_regua tem passadas e pausa; _trocar_por_previsao não tem, e morre
    # no primeiro 429 depois de 20 min de trabalho. Medido em 20/08/2026: o
    # download inline quebrou na 79ª de 99 estações. A convenção do projeto é
    # não baixar dentro da medição — falhar agora, apontando o preenchedor, custa
    # segundos em vez de meia hora.
    faltando = [e for e, r in estacoes.iterrows()
                if not _cache_utilizavel(
                    _previsao_cache_path(r['lat'], r['lon'], INICIO_AJUSTE, fim))]
    if faltando:
        logger.error('%d estações sem previsão em cache para %s..%s — %s',
                     len(faltando), INICIO_AJUSTE, fim, faltando[:10])
        logger.error('rode antes: ./run.sh scripts/preencher_cache_previsao.py 10 90 %s',
                     INICIO_AJUSTE)
        sys.exit(1)

    bruto = _trocar_por_previsao(bruto, fim, inicio=INICIO_AJUSTE)

    feats = create_features(bruto)
    del bruto
    aju_mask, ava_mask = separar_ajuste_avaliacao(feats)
    aju = _media_futura(feats[aju_mask].copy())
    ava = _media_futura(feats[ava_mask].copy())
    del feats

    aju = _anexar_regua(aju, estacoes, fim, inicio=INICIO_AJUSTE)
    ava = _anexar_regua(ava, estacoes, fim, inicio=INICIO_AJUSTE)

    for d in (aju, ava):
        # A chuva prevista é fortemente assimétrica; log1p a torna utilizável por
        # um modelo linear sem transformar o problema.
        d['ifs_log'] = np.log1p(d['ifs_chuva_24h'].clip(lower=0))

    antes = len(aju), len(ava)
    obrigatorias = ['ifs_log', 'chuva_futura_24h'] + LOCAIS
    aju = aju.dropna(subset=obrigatorias)
    ava = ava.dropna(subset=obrigatorias)
    logger.info('sobrevivência ao dropna: ajuste %d->%d (%.1f%%) | avaliação %d->%d (%.1f%%)',
                antes[0], len(aju), 100 * len(aju) / max(antes[0], 1),
                antes[1], len(ava), 100 * len(ava) / max(antes[1], 1))

    comuns = set(aju['estacao_codigo'].unique()) & set(ava['estacao_codigo'].unique())
    logger.info('estações: ajuste %d | avaliação %d | comuns %d (%.0f%% da avaliação é nova)',
                aju['estacao_codigo'].nunique(), ava['estacao_codigo'].nunique(), len(comuns),
                100 * (1 - len(comuns) / ava['estacao_codigo'].nunique()))

    linhas = []
    for cen in CENARIOS:
        linhas += _rodar_cenario(cen, aju, ava)
        linhas += _rodar_cenario(cen, aju, ava, sufixo=' — só estações comuns',
                                 estacoes_ok=comuns)
    if linhas:
        _escrever_relatorio(linhas)
    else:
        logger.error('nenhum cenário produziu resultado — nada a reportar')
