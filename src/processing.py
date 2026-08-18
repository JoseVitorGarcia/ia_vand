import logging

import numpy as np
import pandas as pd

from src.config import (
    CLIMATOLOGIA_CUTOFF,
    EXTREME_RAIN_THRESHOLD,
    INTERPOLACAO_LIMITE_HORAS,
    VIZINHOS_K,
    VIZINHOS_RAIO_KM,
)

logger = logging.getLogger(__name__)

# Renomeia as colunas do CSV INMET para nomes internos.
# Os cabeçalhos variam de acentuação entre anos; o clean_data normaliza antes.
_RENOMEAR = {
    'PRECIPITACAO TOTAL, HORARIO (MM)': 'precipitacao',
    'TEMPERATURA DO AR - BULBO SECO, HORARIA (C)': 'temperatura',
    'UMIDADE RELATIVA DO AR, HORARIA (%)': 'umidade',
    'PRESSAO ATMOSFERICA AO NIVEL DA ESTACAO, HORARIA (MB)': 'pressao',
    'VENTO, VELOCIDADE HORARIA (M/S)': 'vento',
    # ── Colunas antes descartadas ────────────────────────────────────────────
    'TEMPERATURA DO PONTO DE ORVALHO (C)': 'orvalho',
    'VENTO, RAJADA MAXIMA (M/S)': 'rajada',
    'VENTO, DIRECAO HORARIA (GR) ( (GR))': 'vento_dir',
    'RADIACAO GLOBAL (KJ/M)': 'radiacao',
    'TEMPERATURA MAXIMA NA HORA ANT. (AUT) (C)': 'temp_max',
    'TEMPERATURA MINIMA NA HORA ANT. (AUT) (C)': 'temp_min',
    'UMIDADE REL. MAX. NA HORA ANT. (AUT) (%)': 'umid_max',
    'UMIDADE REL. MIN. NA HORA ANT. (AUT) (%)': 'umid_min',
    'PRESSAO ATMOSFERICA MAX.NA HORA ANT. (AUT) (MB)': 'pressao_max',
    'PRESSAO ATMOSFERICA MIN. NA HORA ANT. (AUT) (MB)': 'pressao_min',
}

# Faixas fisicamente plausíveis. Valores fora disso viram NaN — a coluna, não a
# linha inteira (ver _anular_fora_de_faixa).
_FAIXAS = {
    'precipitacao': (0, 200),
    'temperatura': (-15, 50),
    'umidade': (0, 100),
    'pressao': (850, 1050),
    'vento': (0, 75),
    'orvalho': (-25, 35),
    'rajada': (0, 120),
    'vento_dir': (0, 360),
    'radiacao': (0, 6000),
    'temp_max': (-15, 50),
    'temp_min': (-15, 50),
    'umid_max': (0, 100),
    'umid_min': (0, 100),
    'pressao_max': (850, 1050),
    'pressao_min': (850, 1050),
}

# Colunas numéricas que sofrem interpolação de lacunas curtas
_COLUNAS_NUMERICAS = list(_FAIXAS.keys())


def _normalizar_cabecalho(nome: str) -> str:
    """Reduz o cabeçalho à forma canônica usada em _RENOMEAR.

    Os CSVs do INMET variam a acentuação dos cabeçalhos entre anos
    ('PRECIPITAÇÃO' vs 'PRECIPITACAO', '(°C)' vs '(C)'). Remover acentos e
    símbolos não-ASCII colapsa as variantes numa chave única.
    """
    import unicodedata
    nfd = unicodedata.normalize('NFD', str(nome).strip().upper())
    sem_acento = ''.join(c for c in nfd if unicodedata.category(c) != 'Mn')
    return ''.join(c for c in sem_acento if c.isascii()).strip()


def _renomear_colunas(df: pd.DataFrame) -> pd.DataFrame:
    """Aplica _RENOMEAR sobre os cabeçalhos normalizados, fundindo colisões.

    Colunas diferentes no CSV podem normalizar para o mesmo nome interno — o
    INMET grafa a radiação global ora como '(KJ/m²)', ora como '(Kj/m²)', e as
    duas viram 'radiacao'. Cada arquivo preenche só uma delas, então a fusão é
    um combine_first: a primeira coluna não-nula vence.
    """
    destino = {}
    for coluna in df.columns:
        interno = _RENOMEAR.get(_normalizar_cabecalho(coluna))
        if interno:
            destino.setdefault(interno, []).append(coluna)

    for interno, origens in destino.items():
        serie = pd.to_numeric(df[origens[0]], errors='coerce')
        for extra in origens[1:]:
            serie = serie.combine_first(pd.to_numeric(df[extra], errors='coerce'))
            logger.debug("Colunas '%s' e '%s' fundidas em '%s'", origens[0], extra, interno)
        df = df.drop(columns=origens)
        df[interno] = serie

    return df


def _construir_datahora(df: pd.DataFrame) -> pd.Series:
    """Monta o timestamp UTC a partir dos dois layouts de data do INMET.

    Formato antigo (2015-2019): 'DATA (YYYY-MM-DD)' + 'HORA (UTC)' como 'HH:MM'
    Formato novo  (2020+):      'Data' + 'Hora UTC' como 'HHMM UTC'
    O cache pode conter os dois ao mesmo tempo.
    """
    if 'DATA (YYYY-MM-DD)' in df.columns and 'HORA (UTC)' in df.columns:
        dt_antigo = pd.to_datetime(
            df['DATA (YYYY-MM-DD)'].astype(str).str.strip()
            + ' '
            + df['HORA (UTC)'].astype(str).str.strip(),
            errors='coerce', utc=True, format='mixed',
        )
    else:
        dt_antigo = pd.Series(pd.NaT, index=df.index, dtype='datetime64[ns, UTC]')

    if 'Data' in df.columns and 'Hora UTC' in df.columns:
        hora = (
            df['Hora UTC'].astype(str)
            .str.replace(' UTC', '', regex=False)
            .str.strip().str.zfill(4)
        )
        hora = hora.str[:2] + ':' + hora.str[2:]
        dt_novo = pd.to_datetime(
            df['Data'].astype(str).str.strip() + ' ' + hora,
            errors='coerce', utc=True, format='mixed',
        )
    else:
        dt_novo = pd.Series(pd.NaT, index=df.index, dtype='datetime64[ns, UTC]')

    return dt_antigo.fillna(dt_novo)


def _anular_fora_de_faixa(df: pd.DataFrame) -> pd.DataFrame:
    """Zera (NaN) apenas a coluna fora da faixa física, preservando a linha.

    A versão anterior filtrava linhas com `df[df['umidade'].between(0, 100)]`.
    Como `between` devolve False para NaN, uma linha com precipitação
    perfeitamente medida era descartada porque o anemômetro falhou —
    327 mil observações de chuva válidas perdidas por falha de outro sensor.
    """
    total_anulado = 0
    for col, (lo, hi) in _FAIXAS.items():
        if col not in df.columns:
            continue
        fora = df[col].notna() & ~df[col].between(lo, hi)
        n = int(fora.sum())
        if n:
            df.loc[fora, col] = np.nan
            total_anulado += n
            logger.debug("%s: %d valores fora de [%s, %s] anulados", col, n, lo, hi)

    if total_anulado:
        logger.info("%d valores fora de faixa física anulados (linhas preservadas)", total_anulado)
    return df


def clean_data(df):
    df = df.copy()

    df = df.replace(-9999, np.nan)

    df = _renomear_colunas(df)

    faltando = [c for c in ['precipitacao', 'temperatura', 'umidade', 'pressao', 'vento']
                if c not in df.columns]
    if faltando:
        raise ValueError(f"Colunas essenciais ausentes após renomeação: {faltando}")

    for col in _COLUNAS_NUMERICAS:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')

    df['data_hora'] = _construir_datahora(df)

    rejeitadas = int(df['data_hora'].isna().sum())
    if rejeitadas:
        logger.warning("%d linhas rejeitadas por timestamp inválido", rejeitadas)
    df = df[df['data_hora'].notna()].copy()

    df = _anular_fora_de_faixa(df)

    # Duplicatas de (estação, hora) surgem quando o mesmo período aparece em
    # mais de um arquivo. Sem remover, os acumulados contam a mesma chuva duas
    # vezes e a reamostragem horária quebra.
    antes = len(df)
    df = df.sort_values(['estacao_codigo', 'data_hora'])
    df = df.drop_duplicates(subset=['estacao_codigo', 'data_hora'], keep='first')
    if antes != len(df):
        logger.info("%d duplicatas de (estação, hora) removidas", antes - len(df))

    # `estacao_codigo` como category, aqui e não lá na frente: são ~100 valores
    # distintos em milhões de linhas. Como object custa 237 MB só nesta coluna e
    # obriga cada groupby/pivot/merge do pipeline a hashear strings; como
    # category custa 4,5 MB e as chaves viram códigos inteiros. Feito depois dos
    # filtros de linha para não carregar categorias sem uso.
    df['estacao_codigo'] = df['estacao_codigo'].astype('category')

    # Interpola apenas lacunas curtas. Sem `limit`, uma estação fora do ar por
    # meses recebia valores inventados por interpolação linear — o maior buraco
    # da base tinha 651 dias.
    for col in _COLUNAS_NUMERICAS:
        if col in df.columns:
            df[col] = df.groupby('estacao_codigo', observed=True)[col].transform(
                lambda x: x.interpolate(limit=INTERPOLACAO_LIMITE_HORAS, limit_direction='both')
            )

    logger.info(
        "clean_data: %d linhas | %d estações | %s a %s",
        len(df), df['estacao_codigo'].nunique(),
        df['data_hora'].min().date(), df['data_hora'].max().date(),
    )

    return df.reset_index(drop=True)


def _reamostrar_horario(df: pd.DataFrame) -> pd.DataFrame:
    """Preenche a grade horária de cada estação com linhas vazias nas lacunas.

    Depois disso, uma janela de 24 posições é exatamente uma janela de 24 horas,
    o que torna corretos todos os `rolling` posicionais — inclusive o alvo.
    Sem isso, atravessar uma lacuna faz 'as próximas 24 linhas' cobrirem meses.

    A coluna `_observado` marca as linhas reais; as sintéticas são descartadas
    no fim de create_features, depois de terem cumprido seu papel de espaçador.
    """
    df = df.copy()
    df['_observado'] = True

    partes = []
    # O reindex apaga o código nas linhas espaçadoras; reescrever com o dtype
    # original preserva o category (um escalar simples degradaria para object).
    dtype_codigo = df['estacao_codigo'].dtype
    for codigo, grupo in df.groupby('estacao_codigo', sort=True, observed=True):
        grade = pd.date_range(
            grupo['data_hora'].min(), grupo['data_hora'].max(), freq='h', tz='UTC',
        )
        g = (
            grupo.set_index('data_hora')
                 .reindex(grade)
                 .rename_axis('data_hora')
                 .reset_index()
        )
        g['estacao_codigo'] = pd.Series(codigo, index=g.index, dtype=dtype_codigo)
        partes.append(g)

    out = pd.concat(partes, ignore_index=True)
    out['_observado'] = out['_observado'].fillna(False).astype(bool)

    sinteticas = int((~out['_observado']).sum())
    logger.info(
        "Grade horária: %d linhas observadas + %d espaçadoras (%.1f%% de lacuna)",
        int(out['_observado'].sum()), sinteticas, 100 * sinteticas / len(out),
    )
    return out


def _distancia_km(lat1, lon1, lat2, lon2):
    """Distância de Haversine em km entre vetores de coordenadas."""
    r = 6371.0
    p1, p2 = np.radians(lat1), np.radians(lat2)
    dp = p2 - p1
    dl = np.radians(lon2 - lon1)
    a = np.sin(dp / 2) ** 2 + np.cos(p1) * np.cos(p2) * np.sin(dl / 2) ** 2
    return 2 * r * np.arcsin(np.sqrt(a))


def _features_vizinhas(df: pd.DataFrame) -> pd.DataFrame:
    """Traz o estado atual das estações vizinhas como feature.

    Chuva é advectiva: um sistema que atinge Uruguaiana chega a Santa Maria
    horas depois. Tratar cada estação como uma ilha joga fora essa informação,
    que já está na base.

    Duas visões por estação: a média das k vizinhas mais próximas dentro do raio,
    e a média apenas das vizinhas a oeste — no RS os sistemas entram por
    W/SW, então o setor oeste é o que antecipa a chegada.
    """
    coords = (
        df.groupby('estacao_codigo', observed=True)[['latitude', 'longitude']]
        .first().dropna()
    )
    if len(coords) < 2:
        logger.warning("Menos de 2 estações com coordenadas — features de vizinhança puladas")
        for c in ['viz_chuva_3h', 'viz_oeste_chuva_3h', 'viz_queda_pressao_3h']:
            df[c] = np.nan
        return df

    codigos = coords.index.to_numpy()
    lats = coords['latitude'].to_numpy()
    lons = coords['longitude'].to_numpy()

    # Matriz de distâncias entre todas as estações (100x100 — trivial)
    dist = _distancia_km(
        lats[:, None], lons[:, None], lats[None, :], lons[None, :],
    )
    np.fill_diagonal(dist, np.inf)

    vizinhas, vizinhas_oeste = {}, {}
    for i, cod in enumerate(codigos):
        dentro = np.where(dist[i] <= VIZINHOS_RAIO_KM)[0]
        mais_proximas = dentro[np.argsort(dist[i][dentro])][:VIZINHOS_K]
        vizinhas[cod] = codigos[mais_proximas]
        # 'A oeste' = longitude menor (mais negativa) que a da estação
        oeste = [j for j in mais_proximas if lons[j] < lons[i]]
        vizinhas_oeste[cod] = codigos[oeste] if oeste else np.array([], dtype=object)

    medias = [len(v) for v in vizinhas.values()]
    logger.info(
        "Vizinhança: %.1f vizinhas por estação (raio %d km, k=%d)",
        float(np.mean(medias)), VIZINHOS_RAIO_KM, VIZINHOS_K,
    )

    # Tabela hora x estação para cada variável de interesse
    def _pivot(col):
        return df.pivot_table(
            index='data_hora', columns='estacao_codigo', values=col, aggfunc='first',
            observed=True,
        )

    piv_chuva = _pivot('chuva_3h')
    piv_pressao = _pivot('queda_pressao_3h')

    def _media_vizinhas(pivot, mapa):
        saida = pd.DataFrame(index=pivot.index, columns=pivot.columns, dtype='float32')
        for cod in pivot.columns:
            v = [c for c in mapa.get(cod, []) if c in pivot.columns]
            saida[cod] = pivot[v].mean(axis=1) if v else np.nan
        return saida

    viz_chuva = _media_vizinhas(piv_chuva, vizinhas)
    viz_oeste = _media_vizinhas(piv_chuva, vizinhas_oeste)
    viz_pressao = _media_vizinhas(piv_pressao, vizinhas)

    # Volta da tabela hora x estação para as linhas do DataFrame por indexação
    # posicional, não por stack + merge. O caminho antigo custava caro duas vezes:
    # o stack densificava a grade inteira (105 mil horas x 100 estações = 10,5 M
    # linhas, contra 4,7 M reais) e cada um dos três merges alocava uma cópia nova
    # do frame de ~50 colunas enquanto a antiga ainda estava viva. Aqui a tabela
    # já é pequena (105k x 100 float32 = 40 MB); só falta ler a célula certa para
    # cada linha, o que é um gather de dois vetores de índices.
    def _indexadores(tabela):
        linha = tabela.index.get_indexer(df['data_hora'])
        coluna = tabela.columns.get_indexer(df['estacao_codigo'])
        # pivot_table descarta linhas/colunas totalmente vazias — daí o -1
        return linha, coluna, (linha >= 0) & (coluna >= 0)

    idx_chuva = _indexadores(piv_chuva)
    idx_pressao = _indexadores(piv_pressao)

    def _aplicar(tabela, nome, idx):
        linha, coluna, valido = idx
        valores = np.full(len(df), np.nan, dtype='float32')
        valores[valido] = tabela.to_numpy(dtype='float32')[linha[valido], coluna[valido]]
        df[nome] = valores

    _aplicar(viz_chuva, 'viz_chuva_3h', idx_chuva)
    _aplicar(viz_oeste, 'viz_oeste_chuva_3h', idx_chuva)
    _aplicar(viz_pressao, 'viz_queda_pressao_3h', idx_pressao)

    return df


def _herdar_climatologia_de_vizinhas(df, clima, mensal):
    """Dá climatologia às estações que não existiam antes do cutoff.

    A rede do INMET dobrou de tamanho em 2025: 55 das 100 estações só têm dados
    de 2025/26 e ficam de fora do recorte pré-cutoff que define a climatologia.
    Elas chegavam à inferência com `clima_chuva_mes` — a feature mais usada do
    modelo — em NaN, e o efeito medido não era erro e sim silêncio: as
    probabilidades saíam baixas demais e o threshold nunca disparava. Recall por
    estação-dia de 0,008 nessas estações, contra 0,69 nas demais, apesar de o
    PR-AUC ser o mesmo nos dois grupos — o modelo ordenava o risco bem, só não
    alcançava o corte.

    Herdar das k vizinhas mais próximas põe essas estações na mesma escala das
    que o modelo viu no treino. Não vaza futuro: a climatologia das vizinhas vem
    inteira de dados pré-cutoff.

    Deliberadamente não marca quais estações herdaram: essa coluna seria
    constante no treino (nenhuma estação nova aparece lá) e o modelo não teria
    como aprender nada com ela.
    """
    coords = (
        df.groupby('estacao_codigo', observed=True)[['latitude', 'longitude']]
        .first().dropna()
    )
    faltantes = [c for c in coords.index if c not in clima.index]
    com_clima = [c for c in clima.index if c in coords.index]

    if not faltantes:
        return clima, mensal
    if not com_clima:
        logger.warning("Nenhuma estação com climatologia — herança impossível")
        return clima, mensal

    origem = coords.loc[com_clima]
    lats, lons = origem['latitude'].to_numpy(), origem['longitude'].to_numpy()

    linhas_clima, linhas_mensal = [], []
    distancias = []
    for cod in faltantes:
        lat, lon = coords.loc[cod, 'latitude'], coords.loc[cod, 'longitude']
        d = _distancia_km(lat, lon, lats, lons)
        vizinhas = np.argsort(d)[:VIZINHOS_K]
        codigos = [com_clima[i] for i in vizinhas]
        distancias.append(float(d[vizinhas].mean()))
        linhas_clima.append(clima.loc[codigos].mean())
        linhas_mensal.append(mensal.loc[codigos].mean())

    def _anexar(tabela, linhas):
        novos = pd.DataFrame(linhas, columns=tabela.columns)
        novos.index = pd.CategoricalIndex(
            faltantes, categories=tabela.index.categories,
        ) if isinstance(tabela.index, pd.CategoricalIndex) else pd.Index(faltantes)
        return pd.concat([tabela, novos])

    logger.info(
        "Climatologia herdada por %d estações sem histórico pré-cutoff "
        "(média das %d vizinhas mais próximas, a %.0f km em média)",
        len(faltantes), VIZINHOS_K, float(np.mean(distancias)),
    )
    return _anexar(clima, linhas_clima), _anexar(mensal, linhas_mensal)


def _climatologia_estacao(df: pd.DataFrame) -> pd.DataFrame:
    """Descreve cada estação por seu regime de chuva, não por um código arbitrário.

    Substitui `estacao_id` (cat.codes), que era inútil fora do treino: o código
    dependia da ordem alfabética do conjunto presente, mudava ao acrescentar uma
    estação e não podia ser reconstruído na inferência. Estas features
    generalizam para estações novas, que é o que o código nunca faria.

    Calculada apenas com dados até CLIMATOLOGIA_CUTOFF para não vazar o futuro.
    """
    treino = df[df['data_hora'] <= CLIMATOLOGIA_CUTOFF]
    if treino.empty:
        logger.warning("Nenhum dado antes do cutoff de climatologia — usando base inteira")
        treino = df

    clima = treino.groupby('estacao_codigo', observed=True).agg(
        clima_chuva_media=('precipitacao', 'mean'),
        clima_chuva_p99=('precipitacao', lambda x: x.quantile(0.99)),
        clima_umidade_media=('umidade', 'mean'),
        clima_pressao_media=('pressao', 'mean'),
    )

    # Chuva acumulada média por mês do ano — regime sazonal local.
    # Como tabela estação x mês (não em formato longo) para permitir o gather abaixo.
    mensal = (
        treino.groupby(['estacao_codigo', treino['data_hora'].dt.month], observed=True)['precipitacao']
        .mean().unstack()
    )

    clima, mensal = _herdar_climatologia_de_vizinhas(df, clima, mensal)

    # Gather posicional em vez de merge, pelo mesmo motivo de _features_vizinhas:
    # as duas tabelas têm ~100 linhas, mas cada merge alocava uma cópia inteira do
    # frame de ~60 colunas com a anterior ainda viva. Era o maior pico do pipeline.
    def _por_estacao(tabela, valores):
        pos = tabela.index.get_indexer(df['estacao_codigo'])
        saida = np.full(len(df), np.nan)
        saida[pos >= 0] = valores[pos[pos >= 0]]
        return saida

    for col in clima.columns:
        df[col] = _por_estacao(clima, clima[col].to_numpy())

    linha = mensal.index.get_indexer(df['estacao_codigo'])
    coluna = mensal.columns.get_indexer(df['mes'])
    valido = (linha >= 0) & (coluna >= 0)
    clima_mes = np.full(len(df), np.nan)
    clima_mes[valido] = mensal.to_numpy()[linha[valido], coluna[valido]]
    df['clima_chuva_mes'] = clima_mes

    logger.info(
        "Climatologia calculada em %d estações com dados até %s",
        len(clima), CLIMATOLOGIA_CUTOFF.date(),
    )
    return df


def create_features(df):
    logger.info("Criando features...")

    df = df.copy()

    # A grade horária completa faz janela posicional == janela temporal
    df = _reamostrar_horario(df)
    df = df.sort_values(['estacao_codigo', 'data_hora']).reset_index(drop=True)

    grupo = df.groupby('estacao_codigo', sort=True, observed=True)

    df['hora'] = df['data_hora'].dt.hour.astype(int)
    df['mes'] = df['data_hora'].dt.month.astype(int)

    df['hora_sin'] = np.sin(2 * np.pi * df['hora'] / 24)
    df['hora_cos'] = np.cos(2 * np.pi * df['hora'] / 24)
    df['mes_sin'] = np.sin(2 * np.pi * df['mes'] / 12)
    df['mes_cos'] = np.cos(2 * np.pi * df['mes'] / 12)

    # =========================
    # UMIDADE — ponto de orvalho (coluna antes descartada)
    # =========================
    if 'orvalho' in df.columns:
        # Déficit de saturação: quanto o ar precisa esfriar para condensar.
        # Perto de zero = ar saturado. Sinal mais direto de chuva iminente que
        # a umidade relativa, que confunde umidade com temperatura.
        df['deficit_orvalho'] = df['temperatura'] - df['orvalho']
    else:
        df['orvalho'] = np.nan
        df['deficit_orvalho'] = np.nan

    # =========================
    # VENTO — direção decomposta (coluna antes descartada)
    # =========================
    if 'vento_dir' in df.columns:
        rad = np.radians(df['vento_dir'])
        df['vento_dir_sin'] = np.sin(rad)
        df['vento_dir_cos'] = np.cos(rad)
        # Componente meridional: vento de norte traz ar quente e úmido ao RS
        df['vento_norte'] = -np.cos(rad) * df['vento']
        df['vento_leste'] = -np.sin(rad) * df['vento']
    else:
        for c in ['vento_dir_sin', 'vento_dir_cos', 'vento_norte', 'vento_leste']:
            df[c] = np.nan

    if 'rajada' not in df.columns:
        df['rajada'] = np.nan
    # Rajada acima da média sustentada indica turbulência convectiva
    df['rajada_excesso'] = df['rajada'] - df['vento']

    # Amplitudes horárias — proxy de instabilidade
    if 'temp_max' in df.columns and 'temp_min' in df.columns:
        df['amplitude_temp'] = df['temp_max'] - df['temp_min']
    else:
        df['amplitude_temp'] = np.nan
    if 'pressao_max' in df.columns and 'pressao_min' in df.columns:
        df['amplitude_pressao'] = df['pressao_max'] - df['pressao_min']
    else:
        df['amplitude_pressao'] = np.nan

    # =========================
    # LAGS (posicional == horário graças à grade completa)
    # =========================
    for lag in [1, 3, 6, 24]:
        df[f'lag_{lag}h'] = grupo['precipitacao'].shift(lag)

    # =========================
    # ACUMULADOS — janelas agora verdadeiramente temporais
    # =========================
    for janela in [3, 6, 12, 24, 48, 72]:
        df[f'chuva_{janela}h'] = grupo['precipitacao'].transform(
            lambda x: x.rolling(window=janela, min_periods=1).sum()
        )

    df['rolling_std_24h'] = grupo['precipitacao'].transform(
        lambda x: x.rolling(window=24, min_periods=1).std()
    )
    df['rolling_max_24h'] = grupo['precipitacao'].transform(
        lambda x: x.rolling(window=24, min_periods=1).max()
    )

    df['tendencia_6h'] = df['lag_1h'] - df['lag_6h']

    df['queda_pressao_3h'] = grupo['pressao'].shift(1) - grupo['pressao'].shift(3)
    df['queda_pressao_24h'] = grupo['pressao'].shift(1) - grupo['pressao'].shift(24)

    df['tendencia_orvalho_3h'] = df['orvalho'] - grupo['orvalho'].shift(3)

    df['temp_umidade'] = df['temperatura'] * df['umidade']

    # =========================
    # CONTEXTO ESPACIAL E CLIMATOLÓGICO
    # =========================
    df = _features_vizinhas(df)
    df = _climatologia_estacao(df)

    # Chuva acumulada relativa ao normal da estação — 40 mm é rotina no litoral
    # e excepcional na Campanha; o modelo precisa da referência local.
    df['chuva_24h_rel'] = df['chuva_24h'] / (df['clima_chuva_p99'] + 0.1)

    # =========================
    # ALVO — soma estritamente futura de t+1 a t+24
    # A grade horária completa garante que 24 posições = 24 horas.
    # Derivação: reverter série → shift(1) → rolling(24) → reverter de volta.
    # =========================
    df['chuva_futura_24h'] = (
        df.groupby('estacao_codigo', sort=True, observed=True)['precipitacao']
        .transform(
            lambda x:
            x.iloc[::-1]
             .shift(1)
             .rolling(window=24, min_periods=24)
             .sum()
             .iloc[::-1]
        )
    )

    for col in ['rolling_std_24h', 'tendencia_6h', 'queda_pressao_3h',
                'queda_pressao_24h', 'rajada_excesso']:
        df[col] = df[col].fillna(0)

    obrigatorias = [
        'precipitacao', 'temperatura', 'umidade', 'pressao', 'vento',
        'lag_1h', 'lag_6h', 'lag_24h',
        'chuva_24h', 'chuva_48h',
        'chuva_futura_24h',
    ]

    # Os dois filtros e a ordenação final valiam três cópias do frame inteiro
    # (~3 GB cada, com a anterior ainda viva). Resolvendo as posições primeiro e
    # aplicando um único `take`, é uma cópia só — mesmas linhas, mesma ordem.
    #
    # Descarta as espaçadoras (já cumpriram o papel de manter as janelas
    # alinhadas ao tempo) e as linhas sem as features obrigatórias.
    observado = df['_observado'].to_numpy()
    completo = df[obrigatorias].notna().all(axis=1).to_numpy()
    posicoes = np.flatnonzero(observado & completo)
    logger.info(
        "%d linhas descartadas por features obrigatórias ausentes",
        int(observado.sum()) - len(posicoes),
    )

    # Ordenação temporal global — o TimeSeriesSplit corta por posição de linha,
    # então sem isto ele separa estações (ordem alfabética) em vez de períodos.
    # Era a causa do F1 de 0,24: treino e teste cobriam 2015-2026 nos dois lados.
    # `quicksort` reproduz exatamente o desempate do sort_values original.
    instantes = df['data_hora'].astype('int64').to_numpy()[posicoes]
    posicoes = posicoes[np.argsort(instantes, kind='quicksort')]

    # Reconstrói consumindo o frame antigo coluna a coluna, em vez de
    # `df.take(posicoes)`. create_features acrescenta ~40 colunas uma a uma, então
    # o frame chega aqui com dezenas de blocos soltos, e tanto o `take` quanto o
    # construtor a partir de Series consolidam tudo num bloco único antes de
    # copiar. Medido em isolado neste formato (5,4 M x 69): pico de 2,99 GB para
    # 10,79 GB, para produzir 2 GB de saída. Com `pop`, cada coluna de origem é
    # liberada assim que a nova é escrita e o pico fica em 3,00 GB.
    df.pop('_observado')
    dados = {}
    for coluna in list(df.columns):
        dados[coluna] = df.pop(coluna).array.take(posicoes)
    df = pd.DataFrame(dados, copy=False)

    df['evento_extremo'] = (df['chuva_futura_24h'] > EXTREME_RAIN_THRESHOLD).astype(int)

    assert df['data_hora'].is_monotonic_increasing, \
        "DataFrame precisa estar ordenado no tempo antes do split temporal"

    logger.info(
        "Total após features: %d linhas | %d estações | eventos extremos: %.2f%%",
        len(df), df['estacao_codigo'].nunique(), 100 * df['evento_extremo'].mean(),
    )

    return df
