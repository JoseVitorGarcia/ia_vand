import glob
import logging
import os
import unicodedata

import pandas as pd

from src.config import CACHE_DIR, RAW_DATA_DIR, STATES_FILTER

logger = logging.getLogger(__name__)

CACHE_FILE = CACHE_DIR / "dataset.parquet"


def _normalizar_chave(chave: str) -> str:
    """Remove acentos e normaliza para uppercase.
    Garante que 'ESTAÇÃO' e 'ESTACAO' sejam tratados como a mesma chave,
    pois o INMET mudou a convenção de acentos entre versões do formato CSV.
    """
    nfd = unicodedata.normalize('NFD', chave.strip().upper())
    return ''.join(c for c in nfd if unicodedata.category(c) != 'Mn')


def extrair_metadata(arquivo):
    """Lê até 10 linhas de metadado do cabeçalho INMET.
    Normaliza as chaves (sem acentos, uppercase) para compatibilidade
    entre o formato antigo (2015-2019, com acentos) e o novo (2020+, sem acentos).
    Semicolons extras nos valores são removidos (artefato do formato CSV INMET).
    """
    metadata = {}
    with open(arquivo, 'r', encoding='latin-1') as f:
        for _ in range(10):
            linha = f.readline()
            if not linha:
                break
            if ':' in linha:
                chave, valor = linha.split(':', 1)
                metadata[_normalizar_chave(chave)] = valor.strip().lstrip(';').strip()
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


def _cache_valido() -> bool:
    """Cache é válido se existir e nenhum CSV raw for mais novo que ele."""
    if not CACHE_FILE.exists():
        return False
    cache_mtime = CACHE_FILE.stat().st_mtime
    for csv in RAW_DATA_DIR.rglob('*.CSV'):
        if csv.stat().st_mtime > cache_mtime:
            logger.info("Arquivo raw mais novo que cache: %s", csv.name)
            return False
    return True


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
    for arquivo in arquivos:
        try:
            metadata = extrair_metadata(arquivo)

            df = pd.read_csv(
                arquivo,
                sep=';',
                skiprows=8,
                encoding='latin-1',
                decimal=',',
            )

            # Usa chaves normalizadas (sem acento) — compatíveis com formato antigo e novo
            df['estacao'] = metadata.get('ESTACAO', 'UNKNOWN')
            df['latitude'] = limpar_numero(metadata.get('LATITUDE'))
            df['longitude'] = limpar_numero(metadata.get('LONGITUDE'))

            dfs.append(df)

        except Exception as e:
            logger.error("Erro ao carregar %s: %s", arquivo, e)

    if not dfs:
        return pd.DataFrame()

    df = pd.concat(dfs, ignore_index=True)
    df = df.drop(columns=[c for c in df.columns if "Unnamed" in c], errors='ignore')

    logger.info("Total carregado: %d registros", len(df))

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
        DataFrame com colunas adicionais: cape, cloud_cover, wind_gusts_10m,
        soil_moisture, freezing_level.
    """
    from src.openmeteo_client import fetch_historical

    estacoes = (
        df.groupby('estacao')[['latitude', 'longitude']]
        .first()
        .dropna()
        .reset_index()
    )

    logger.info(
        "Enriquecendo %d estações com Open-Meteo histórico...",
        len(estacoes),
    )

    partes = []
    for _, row in estacoes.iterrows():
        grupo = df[df['estacao'] == row['estacao']].copy()

        start = grupo['data_hora'].min().strftime('%Y-%m-%d')
        end = grupo['data_hora'].max().strftime('%Y-%m-%d')

        try:
            om = fetch_historical(row['latitude'], row['longitude'], start, end)
        except Exception as exc:
            logger.warning(
                "Open-Meteo falhou para %s: %s — features serão NaN",
                row['estacao'], exc,
            )
            partes.append(grupo)
            continue

        if om.empty:
            partes.append(grupo)
            continue

        merged = grupo.merge(om, on='data_hora', how='left')
        partes.append(merged)

    result = pd.concat(partes, ignore_index=True)
    result = result.sort_values(['estacao', 'data_hora']).reset_index(drop=True)

    om_cols = [c for c in ['cape', 'cloud_cover', 'wind_gusts_10m', 'soil_moisture', 'freezing_level'] if c in result.columns]
    logger.info("Open-Meteo: %d colunas adicionadas — %s", len(om_cols), om_cols)

    return result
