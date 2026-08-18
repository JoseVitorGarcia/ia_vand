"""
Cliente para a API Open-Meteo (gratuita, sem chave).

Dois endpoints:
  - archive-api: dados ERA5 históricos (treino)
  - api:         previsão operacional (inferência)

Cache:
  - Histórico: por (lat, lon, ano) em parquet — permanente
  - Forecast:  por (lat, lon) em parquet — TTL configurável
"""

import logging
import time
from datetime import datetime
from pathlib import Path

import pandas as pd
import requests

from src.config import (
    OPENMETEO_CACHE_DIR,
    OPENMETEO_RENAME,
    OPENMETEO_FORECAST_TTL_HOURS,
    OPENMETEO_HISTORICAL_VARS,
    OPENMETEO_FORECAST_VARS,
    OPENMETEO_REQUEST_DELAY,
)

logger = logging.getLogger(__name__)

_HISTORICAL_URL = "https://archive-api.open-meteo.com/v1/archive"
_FORECAST_URL = "https://api.open-meteo.com/v1/forecast"



def _cache_key(lat: float, lon: float) -> str:
    lat_s = f"{lat:.3f}".replace('.', 'p').replace('-', 'n')
    lon_s = f"{lon:.3f}".replace('.', 'p').replace('-', 'n')
    return f"{lat_s}_{lon_s}"


def _hist_cache_path(lat: float, lon: float, year: int) -> Path:
    return OPENMETEO_CACHE_DIR / f"hist_{_cache_key(lat, lon)}_{year}.parquet"


def _forecast_cache_path(lat: float, lon: float) -> Path:
    return OPENMETEO_CACHE_DIR / f"forecast_{_cache_key(lat, lon)}.parquet"


def _cache_is_fresh(path: Path, ttl_hours: float) -> bool:
    if not path.exists():
        return False
    return (time.time() - path.stat().st_mtime) < ttl_hours * 3600


def _request(url: str, params: dict, retries: int = 3) -> dict:
    for attempt in range(retries):
        try:
            resp = requests.get(url, params=params, timeout=30)
            resp.raise_for_status()
            return resp.json()
        except Exception as exc:
            if attempt == retries - 1:
                raise RuntimeError(f"Open-Meteo indisponível após {retries} tentativas: {exc}") from exc
            # 429 recebe backoff maior — a API precisa de mais tempo para liberar
            is_429 = '429' in str(exc)
            wait = (10 * (attempt + 1)) if is_429 else (2 ** attempt)
            logger.warning("Open-Meteo falhou (%s), retry em %ds", exc, wait)
            time.sleep(wait)


def _parse_response(data: dict, variables: list) -> pd.DataFrame:
    hourly = data.get('hourly', {})
    df = pd.DataFrame({'data_hora': pd.to_datetime(hourly['time'], utc=True)})
    for var in variables:
        if var in hourly:
            df[var] = hourly[var]
            # A API responde 200 com a coluna inteira nula para variáveis que o
            # modelo não cobre — foi assim que `cape` e `freezing_level_height`
            # passaram meses na lista alimentando o treino só com NaN. Avisar
            # alto é a diferença entre descobrir hoje e descobrir em meses.
            if df[var].isna().all():
                logger.warning(
                    "Open-Meteo devolveu '%s' inteiramente nula — a variável não "
                    "existe neste endpoint; remova-a de OPENMETEO_*_VARS", var,
                )
    return df.rename(columns=OPENMETEO_RENAME)


def fetch_historical(lat: float, lon: float, start_date: str, end_date: str) -> pd.DataFrame:
    """
    Retorna dados ERA5 horários (UTC) para um ponto lat/lon.

    Cache permanente por ano — a API não é chamada novamente para anos já baixados.

    Args:
        lat, lon:    coordenadas da estação
        start_date:  "YYYY-MM-DD"
        end_date:    "YYYY-MM-DD"

    Returns:
        DataFrame com 'data_hora' (UTC) e as variáveis de OPENMETEO_HISTORICAL_VARS
        renomeadas (ex: soil_moisture_0_to_7cm → soil_moisture).
    """
    start = datetime.strptime(start_date, "%Y-%m-%d")
    end = datetime.strptime(end_date, "%Y-%m-%d")

    frames = []
    for year in range(start.year, end.year + 1):
        cache = _hist_cache_path(lat, lon, year)

        if cache.exists():
            cacheado = pd.read_parquet(cache)
            faltando = [
                c for c in (OPENMETEO_RENAME.get(v, v) for v in OPENMETEO_HISTORICAL_VARS)
                if c not in cacheado.columns
            ]
            if not faltando:
                frames.append(cacheado)
                continue
            # Cache de uma lista de variáveis anterior: sem esta checagem, mudar
            # OPENMETEO_HISTORICAL_VARS não teria efeito nenhum enquanto houvesse
            # arquivo em disco, e as colunas novas chegariam ausentes ao modelo.
            logger.info(
                "Cache %s não tem %s — rebaixando", cache.name, faltando,
            )

        y_start = max(start, datetime(year, 1, 1)).strftime("%Y-%m-%d")
        y_end = min(end, datetime(year, 12, 31)).strftime("%Y-%m-%d")

        params = {
            "latitude": lat,
            "longitude": lon,
            "start_date": y_start,
            "end_date": y_end,
            "hourly": ",".join(OPENMETEO_HISTORICAL_VARS),
            "timezone": "UTC",
        }

        logger.info("Open-Meteo histórico %d (%.3f, %.3f)", year, lat, lon)
        data = _request(_HISTORICAL_URL, params)
        df = _parse_response(data, OPENMETEO_HISTORICAL_VARS)
        df.to_parquet(cache, index=False)
        frames.append(df)
        time.sleep(OPENMETEO_REQUEST_DELAY)

    if not frames:
        return pd.DataFrame()

    result = pd.concat(frames, ignore_index=True)

    lo = pd.Timestamp(start_date, tz='UTC')
    hi = pd.Timestamp(end_date, tz='UTC') + pd.Timedelta(days=1)
    mask = (result['data_hora'] >= lo) & (result['data_hora'] < hi)
    return result[mask].reset_index(drop=True)


def fetch_forecast(lat: float, lon: float) -> pd.DataFrame:
    """
    Retorna previsão horária para as próximas 48h para um ponto lat/lon.

    Cache com TTL de OPENMETEO_FORECAST_TTL_HOURS (padrão: 1h).

    Args:
        lat, lon: coordenadas da estação

    Returns:
        DataFrame com 'data_hora' (UTC), variáveis de OPENMETEO_FORECAST_VARS
        renomeadas, incluindo 'precipitation_probability'.
    """
    cache = _forecast_cache_path(lat, lon)

    if _cache_is_fresh(cache, OPENMETEO_FORECAST_TTL_HOURS):
        logger.debug("Forecast cache hit (%.3f, %.3f)", lat, lon)
        return pd.read_parquet(cache)

    params = {
        "latitude": lat,
        "longitude": lon,
        "hourly": ",".join(OPENMETEO_FORECAST_VARS),
        "timezone": "UTC",
        "forecast_days": 2,
    }

    logger.info("Open-Meteo forecast (%.3f, %.3f)", lat, lon)
    data = _request(_FORECAST_URL, params)
    df = _parse_response(data, OPENMETEO_FORECAST_VARS)
    df.to_parquet(cache, index=False)
    return df
