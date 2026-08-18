import glob
import logging
import os
import re
import unicodedata

import pandas as pd

from src.config import CACHE_DIR, OPENMETEO_COLUNAS, RAW_DATA_DIR, STATES_FILTER

logger = logging.getLogger(__name__)

CACHE_FILE = CACHE_DIR / "dataset.parquet"

# Bump ao mudar o schema produzido por load_data() — invalida caches antigos
# que não têm as colunas novas (estacao_codigo, altitude, ...).
CACHE_SCHEMA_VERSION = 2

# Colunas que load_data() garante existir. Se o cache não tiver todas, é de uma
# versão anterior do schema e precisa ser reconstruído.
_SCHEMA_COLUMNS = ['estacao_codigo', 'estacao_nome', 'latitude', 'longitude', 'altitude']

# Código WMO no nome do arquivo INMET: INMET_S_RS_A801_PORTO ALEGRE_01-01-2025_...
_WMO_PATTERN = re.compile(r'_([A-Z]\d{3})_')


def _normalizar_chave(chave: str) -> str:
    """Reduz a chave de metadado à sua forma canônica (só letras maiúsculas).

    O INMET usa três grafias para o mesmo cabeçalho ao longo dos anos:
        2015-2018  'ESTAÇÃO:'   → bytes latin-1 \\307\\303
        2019       'ESTAC?O:'   → acento substituído por '?' literal na origem
        2020+      'ESTACAO:'   → ASCII puro

    Remover acentos não basta: em 2019 o caractere já foi perdido no arquivo.
    Descartar tudo que não é letra ASCII colapsa as três grafias em chaves
    estáveis ('ESTACAO', 'ESTACO', 'ESTACAO') que o _MAPA_CHAVES resolve.
    """
    nfd = unicodedata.normalize('NFD', chave.strip().upper())
    sem_acento = ''.join(c for c in nfd if unicodedata.category(c) != 'Mn')
    return ''.join(c for c in sem_acento if c.isalpha())


# Formas canônicas possíveis → nome interno. 'ESTACO' vem de 'ESTAC?O' (2019).
_MAPA_CHAVES = {
    'REGIAO': 'regiao', 'REGIO': 'regiao',
    'UF': 'uf',
    'ESTACAO': 'estacao_nome', 'ESTACO': 'estacao_nome',
    'CODIGOWMO': 'codigo_wmo',
    'LATITUDE': 'latitude',
    'LONGITUDE': 'longitude',
    'ALTITUDE': 'altitude',
}


def extrair_metadata(arquivo):
    """Lê o cabeçalho INMET e devolve as chaves já mapeadas para nomes internos."""
    metadata = {}
    with open(arquivo, 'r', encoding='latin-1') as f:
        for _ in range(10):
            linha = f.readline()
            if not linha:
                break
            if ':' in linha:
                chave, valor = linha.split(':', 1)
                interno = _MAPA_CHAVES.get(_normalizar_chave(chave))
                if interno:
                    metadata[interno] = valor.strip().lstrip(';').strip()
    return metadata


def limpar_numero(valor):
    if valor is None:
        return None
    try:
        return float(
            valor.replace(';', '').replace(',', '.').strip()
        )
    except (ValueError, AttributeError):
        return None


def _codigo_wmo(arquivo: str) -> str | None:
    """Extrai o código WMO do nome do arquivo (identidade estável da estação).

    O nome da estação muda entre anos — 'PORTO ALEGRE' vira
    'PORTO ALEGRE - JARDIM BOTANICO' em 2025 — e usá-lo como chave parte a série
    da mesma estação física em duas. O código WMO é imutável.
    """
    match = _WMO_PATTERN.search(os.path.basename(arquivo).upper())
    return match.group(1) if match else None


def _cache_valido() -> bool:
    """Cache é válido se existir, tiver o schema atual e nenhum CSV raw for mais novo."""
    if not CACHE_FILE.exists():
        return False

    try:
        colunas = pd.read_parquet(CACHE_FILE, columns=None).columns
    except Exception as exc:
        logger.warning("Cache ilegível (%s) — reconstruindo", exc)
        return False

    faltando = [c for c in _SCHEMA_COLUMNS if c not in colunas]
    if faltando:
        logger.info("Cache de schema antigo (faltam %s) — reconstruindo", faltando)
        return False

    cache_mtime = CACHE_FILE.stat().st_mtime
    for csv in RAW_DATA_DIR.rglob('*.CSV'):
        if csv.stat().st_mtime > cache_mtime:
            logger.info("Arquivo raw mais novo que cache: %s", csv.name)
            return False
    return True


def _canonicalizar_coordenadas(df: pd.DataFrame) -> pd.DataFrame:
    """Fixa uma única lat/lon/altitude por estação.

    Os metadados do INMET trazem precisões diferentes para a mesma estação em
    anos diferentes. Sem canonicalizar, a mesma estação vira vários pontos
    distintos e o cache do Open-Meteo (chaveado por lat/lon) se multiplica.
    Usa-se a moda — o valor mais repetido entre os anos.
    """
    def _moda(serie):
        modas = serie.dropna().mode()
        return modas.iloc[0] if not modas.empty else None

    canonico = df.groupby('estacao_codigo').agg(
        latitude=('latitude', _moda),
        longitude=('longitude', _moda),
        altitude=('altitude', _moda),
    )

    divergentes = df.groupby('estacao_codigo')['latitude'].nunique()
    n_div = (divergentes > 1).sum()
    if n_div:
        logger.info("%d estações tinham lat/lon divergentes entre anos — canonicalizadas", n_div)

    return (
        df.drop(columns=['latitude', 'longitude', 'altitude'])
          .merge(canonico, left_on='estacao_codigo', right_index=True, how='left')
    )


def load_data(force_reload=False):
    if not force_reload and _cache_valido():
        logger.info("Carregando cache parquet...")
        return pd.read_parquet(CACHE_FILE)

    logger.info("Buscando arquivos em: %s", RAW_DATA_DIR)

    arquivos = glob.glob(
        os.path.join(RAW_DATA_DIR, '**', '*.CSV'),
        recursive=True,
    )

    # Filtra pelos estados configurados em STATES_FILTER
    filtro = [f'_{s}_' for s in STATES_FILTER]
    arquivos = [
        a for a in arquivos
        if any(f in a.upper() for f in filtro)
    ]

    logger.info("%d arquivos encontrados (estados: %s)", len(arquivos), STATES_FILTER)

    dfs = []
    ignorados = []
    for arquivo in arquivos:
        try:
            codigo = _codigo_wmo(arquivo)
            if codigo is None:
                ignorados.append((arquivo, "código WMO ausente no nome do arquivo"))
                continue

            metadata = extrair_metadata(arquivo)

            lat = limpar_numero(metadata.get('latitude'))
            lon = limpar_numero(metadata.get('longitude'))
            if lat is None or lon is None:
                ignorados.append((arquivo, "latitude/longitude ausentes no cabeçalho"))
                continue

            df = pd.read_csv(
                arquivo,
                sep=';',
                skiprows=8,
                encoding='latin-1',
                decimal=',',
            )

            # Identidade da estação vem do código WMO, não do nome — ver _codigo_wmo().
            df['estacao_codigo'] = codigo
            df['estacao_nome'] = metadata.get('estacao_nome', codigo)
            df['latitude'] = lat
            df['longitude'] = lon
            df['altitude'] = limpar_numero(metadata.get('altitude'))

            dfs.append(df)

        except Exception as e:
            logger.error("Erro ao carregar %s: %s", arquivo, e)
            ignorados.append((arquivo, str(e)))

    if ignorados:
        logger.warning("%d arquivos ignorados:", len(ignorados))
        for arq, motivo in ignorados[:10]:
            logger.warning("  %s — %s", os.path.basename(arq), motivo)

    if not dfs:
        return pd.DataFrame()

    df = pd.concat(dfs, ignore_index=True)
    df = df.drop(columns=[c for c in df.columns if "Unnamed" in c], errors='ignore')

    df = _canonicalizar_coordenadas(df)

    logger.info(
        "Total carregado: %d registros | %d estações (código WMO)",
        len(df), df['estacao_codigo'].nunique(),
    )

    logger.info("Salvando cache parquet...")
    df.to_parquet(CACHE_FILE, index=False)

    return df


def enrich_openmeteo(df: pd.DataFrame) -> pd.DataFrame:
    """
    Enriquece o DataFrame (já limpo) com variáveis ERA5 da Open-Meteo.

    Para cada estação, faz requisições históricas por lat/lon e mescla
    no timestamp. O cache por ano garante que chamadas à API só ocorrem
    na primeira execução.

    Args:
        df: DataFrame pós clean_data(), com 'data_hora' timezone-aware (UTC).

    Returns:
        DataFrame com as colunas de OPENMETEO_COLUNAS acrescentadas.
    """
    from src.openmeteo_client import fetch_historical

    estacoes = (
        df.groupby('estacao_codigo', observed=True)[['latitude', 'longitude']]
        .first()
        .dropna()
        .reset_index()
    )

    logger.info(
        "Enriquecendo %d estações com Open-Meteo histórico...",
        len(estacoes),
    )

    coordenadas = {
        row['estacao_codigo']: (row['latitude'], row['longitude'])
        for _, row in estacoes.iterrows()
    }

    partes = []
    # groupby percorre o DataFrame uma vez; filtrar por estação dentro de um loop
    # faria uma varredura completa por estação (100 x 4,7 M linhas).
    for codigo, grupo in df.groupby('estacao_codigo', sort=False, observed=True):
        if codigo not in coordenadas:
            partes.append(grupo)
            continue

        lat, lon = coordenadas[codigo]
        start = grupo['data_hora'].min().strftime('%Y-%m-%d')
        end = grupo['data_hora'].max().strftime('%Y-%m-%d')

        try:
            om = fetch_historical(lat, lon, start, end)
        except Exception as exc:
            logger.warning(
                "Open-Meteo falhou para %s: %s — features serão NaN",
                codigo, exc,
            )
            partes.append(grupo)
            continue

        if om.empty:
            partes.append(grupo)
            continue

        # Duplicatas de timestamp na resposta multiplicariam linhas no merge.
        om = om.drop_duplicates(subset='data_hora')
        partes.append(grupo.merge(om, on='data_hora', how='left'))

    result = pd.concat(partes, ignore_index=True)
    result = result.sort_values(['estacao_codigo', 'data_hora']).reset_index(drop=True)

    om_cols = [c for c in OPENMETEO_COLUNAS if c in result.columns]
    logger.info("Open-Meteo: %d colunas adicionadas — %s", len(om_cols), om_cols)

    return result
