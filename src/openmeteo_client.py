"""
Cliente para a API Open-Meteo (gratuita, sem chave).

Dois endpoints:
  - archive-api: dados ERA5 históricos (treino)
  - api:         previsão operacional (inferência)

Cache:
  - Histórico: por (lat, lon, ano) em parquet — permanente
  - Forecast:  por (lat, lon) em parquet — TTL configurável
"""

import hashlib
import logging
import time
from datetime import datetime
from pathlib import Path

import pandas as pd
import requests

from src.config import (
    OPENMETEO_CACHE_DIR,
    OPENMETEO_PREVISAO_CACHE_DIR,
    OPENMETEO_PREVISAO_MODELO,
    OPENMETEO_RENAME,
    OPENMETEO_FORECAST_TTL_HOURS,
    OPENMETEO_HISTORICAL_VARS,
    OPENMETEO_FORECAST_VARS,
    OPENMETEO_REQUEST_DELAY,
    OPENMETEO_TIMEOUT_INTERVALO,
)

logger = logging.getLogger(__name__)

_HISTORICAL_URL = "https://archive-api.open-meteo.com/v1/archive"
_FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
_PREVISAO_ARQUIVADA_URL = "https://historical-forecast-api.open-meteo.com/v1/forecast"



def _cache_key(lat: float, lon: float) -> str:
    lat_s = f"{lat:.3f}".replace('.', 'p').replace('-', 'n')
    lon_s = f"{lon:.3f}".replace('.', 'p').replace('-', 'n')
    return f"{lat_s}_{lon_s}"


def _hist_cache_path(lat: float, lon: float, year: int) -> Path:
    return OPENMETEO_CACHE_DIR / f"hist_{_cache_key(lat, lon)}_{year}.parquet"


def _forecast_cache_path(lat: float, lon: float) -> Path:
    return OPENMETEO_CACHE_DIR / f"forecast_{_cache_key(lat, lon)}.parquet"


def _tag_variaveis(variaveis) -> str:
    """Etiqueta curta e estável do conjunto de variáveis, para a chave do cache.

    Sem ela, o cache das 8 variáveis atmosféricas seria escolhido para um pedido
    de precipitação; `_cache_utilizavel` recusaria o arquivo em silêncio e o
    rebaixe aconteceria de novo a cada chamada.
    """
    return hashlib.sha1(','.join(sorted(variaveis)).encode()).hexdigest()[:8]


def _previsao_cache_path(lat: float, lon: float,
                         start_date: str, end_date: str, variaveis=None) -> Path:
    """Chaveado pela janela pedida, não pelo ano.

    O cache do histórico é por ano porque `_baixar_intervalo` sempre grava anos
    inteiros. Aqui não: a janela de previsão é parcial por construção (começa no
    fim do embargo e termina no fim da série), e um arquivo `_2025.parquet` com
    3 dias dentro fazia qualquer pedido de 2025 ser servido por esses 3 dias,
    em silêncio.
    """
    sufixo = '' if variaveis is None else '_' + _tag_variaveis(variaveis)
    return (OPENMETEO_PREVISAO_CACHE_DIR /
            f"prev_{_cache_key(lat, lon)}_{start_date}_{end_date}{sufixo}.parquet")


def _cache_is_fresh(path: Path, ttl_hours: float) -> bool:
    if not path.exists():
        return False
    return (time.time() - path.stat().st_mtime) < ttl_hours * 3600


def _request(url: str, params: dict, retries: int = 3, timeout: int = 30) -> dict:
    for attempt in range(retries):
        try:
            resp = requests.get(url, params=params, timeout=timeout)
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


def _cache_utilizavel(cache, variaveis=None) -> bool:
    """True se o arquivo existe, é legível e tem todas as variáveis pedidas."""
    if not cache.exists():
        return False
    try:
        colunas = pd.read_parquet(cache).columns
    except Exception:
        return False
    return all(
        OPENMETEO_RENAME.get(v, v) in colunas
        for v in (variaveis or OPENMETEO_HISTORICAL_VARS)
    )


def _baixar_intervalo(lat: float, lon: float, inicio: datetime, fim: datetime) -> None:
    """Baixa um intervalo de anos numa requisição e grava o cache ano a ano."""
    logger.info(
        "Open-Meteo histórico %d-%d (%.3f, %.3f)",
        inicio.year, fim.year, lat, lon,
    )
    data = _request(_HISTORICAL_URL, {
        "latitude": lat,
        "longitude": lon,
        "start_date": inicio.strftime("%Y-%m-%d"),
        "end_date": fim.strftime("%Y-%m-%d"),
        "hourly": ",".join(OPENMETEO_HISTORICAL_VARS),
        "timezone": "UTC",
    }, timeout=OPENMETEO_TIMEOUT_INTERVALO)
    df = _parse_response(data, OPENMETEO_HISTORICAL_VARS)
    if df.empty:
        return

    for ano, parte in df.groupby(df['data_hora'].dt.year):
        parte.reset_index(drop=True).to_parquet(
            _hist_cache_path(lat, lon, int(ano)), index=False,
        )
    time.sleep(OPENMETEO_REQUEST_DELAY)


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

    # Descobre primeiro o que falta, para pedir tudo numa requisição só. Uma por
    # ano custava ~6,5 s cada, quase toda ela latência do servidor do ERA5;
    # medido em 18/08/2026, os 11 anos de uma estação saem em 32,8 s contra ~78 s
    # em 12 pedidos separados. O cache continua sendo por ano — o que muda é só
    # quantas viagens à rede se faz para preenchê-lo.
    faltantes = [
        ano for ano in range(start.year, end.year + 1)
        if not _cache_utilizavel(_hist_cache_path(lat, lon, ano))
    ]
    if faltantes:
        _baixar_intervalo(lat, lon, max(start, datetime(min(faltantes), 1, 1)),
                          min(end, datetime(max(faltantes), 12, 31)))

    frames = []
    for year in range(start.year, end.year + 1):
        cache = _hist_cache_path(lat, lon, year)

        # O ano pode continuar ausente se a API não cobrir o período pedido
        # (ex.: ano corrente além do alcance do ERA5) — seguir sem ele.
        if _cache_utilizavel(cache):
            frames.append(pd.read_parquet(cache))

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


def fetch_forecast_arquivado(lat: float, lon: float, start_date: str,
                             end_date: str, variaveis=None) -> pd.DataFrame:
    """Previsões como foram emitidas no passado, não reanálise.

    Mesma assinatura e mesmas colunas de fetch_historical, de propósito: as duas
    precisam ser intercambiáveis para que a medição de degradação troque só a
    origem do dado, mantendo todo o resto igual.

    Cobertura: o arquivo de previsões da Open-Meteo começa em 2021 — bem depois
    do início da nossa série (2015). Por isso este cliente serve para MEDIR na
    janela de teste, não para retreinar a base inteira.

    O `models=OPENMETEO_PREVISAO_MODELO` não é opcional; ver a nota no config.
    """
    pedidas = list(variaveis) if variaveis else OPENMETEO_HISTORICAL_VARS
    caminho = _previsao_cache_path(lat, lon, start_date, end_date, variaveis)
    if _cache_utilizavel(caminho, pedidas):
        return pd.read_parquet(caminho)

    logger.info("Open-Meteo previsão arquivada %s..%s (%.3f, %.3f)",
                start_date, end_date, lat, lon)
    dados = _request(_PREVISAO_ARQUIVADA_URL, {
        'latitude': lat, 'longitude': lon,
        'start_date': start_date, 'end_date': end_date,
        'hourly': ','.join(pedidas),
        'models': OPENMETEO_PREVISAO_MODELO,
        'timezone': 'UTC',
    }, timeout=OPENMETEO_TIMEOUT_INTERVALO)

    df = _parse_response(dados, pedidas)
    if df.empty:
        return df

    df = df.sort_values('data_hora').reset_index(drop=True)
    df.to_parquet(caminho, index=False)
    time.sleep(OPENMETEO_REQUEST_DELAY)
    return df
