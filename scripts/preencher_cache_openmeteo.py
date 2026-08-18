"""Preenche o cache Open-Meteo até estar completo, sem treinar nada.

Existe porque o enriquecimento dentro do pipeline é frágil ao rate limit da API:
quando um ano falha três vezes, `enrich_openmeteo` degrada a estação inteira
para NaN e segue em frente — silenciosamente. Rodando o download em separado e
até completar, o pipeline depois encontra tudo em cache e não toca na rede.

Cada ano bem-sucedido fica em disco, então as falhas se curam a cada passada.

Uso:
    ./run.sh scripts/preencher_cache_openmeteo.py            # até 5 passadas
    ./run.sh scripts/preencher_cache_openmeteo.py 10 30      # 10 passadas, 30s entre elas
    ./run.sh scripts/preencher_cache_openmeteo.py 0          # só relata o que falta
"""
import logging
import sys
import time

import pandas as pd

from src.config import OPENMETEO_HISTORICAL_VARS, OPENMETEO_RENAME
from src.ingestion import load_data
from src.openmeteo_client import _cache_utilizavel, _hist_cache_path, fetch_historical

logging.basicConfig(
    level=logging.INFO, format='%(asctime)s %(levelname)s %(name)s — %(message)s',
    datefmt='%H:%M:%S',
)
logger = logging.getLogger('preencher_cache')

MAX_PASSADAS = int(sys.argv[1]) if len(sys.argv) > 1 else 5
PAUSA_ENTRE_PASSADAS = float(sys.argv[2]) if len(sys.argv) > 2 else 60.0


def _estacoes():
    """Coordenada canônica e intervalo de datas de cada estação."""
    df = load_data()
    data = pd.to_datetime(
        df['DATA (YYYY-MM-DD)'].fillna(df['Data']).astype(str).str.replace('/', '-', regex=False),
        errors='coerce',
    )
    t = pd.DataFrame({
        'est': df['estacao_codigo'], 'lat': df['latitude'],
        'lon': df['longitude'], 'data': data,
    }).dropna()
    return t.groupby('est').agg(
        lat=('lat', 'first'), lon=('lon', 'first'),
        inicio=('data', 'min'), fim=('data', 'max'),
    )


def _buracos(estacoes):
    """(estação, ano) que ainda não estão em cache com todas as variáveis."""
    faltando = []
    for est, r in estacoes.iterrows():
        for ano in range(r['inicio'].year, r['fim'].year + 1):
            if not _cache_utilizavel(_hist_cache_path(r['lat'], r['lon'], ano)):
                faltando.append((est, ano))
    return faltando


estacoes = _estacoes()
logger.info(
    "%d estações | variáveis exigidas: %s",
    len(estacoes), [OPENMETEO_RENAME.get(v, v) for v in OPENMETEO_HISTORICAL_VARS],
)

for passada in range(1, MAX_PASSADAS + 1):
    faltando = _buracos(estacoes)
    if not faltando:
        logger.info("Cache completo.")
        break

    estacoes_com_buraco = sorted({e for e, _ in faltando})
    logger.info(
        "Passada %d/%d — faltam %d estação-ano em %d estações",
        passada, MAX_PASSADAS, len(faltando), len(estacoes_com_buraco),
    )

    for i, est in enumerate(estacoes_com_buraco, 1):
        r = estacoes.loc[est]
        try:
            fetch_historical(
                r['lat'], r['lon'],
                r['inicio'].strftime('%Y-%m-%d'), r['fim'].strftime('%Y-%m-%d'),
            )
        except Exception as exc:
            # Segue para a próxima: o que já baixou está em cache e a passada
            # seguinte retoma daqui.
            logger.warning("%s falhou (%d/%d): %s", est, i, len(estacoes_com_buraco), exc)

    if passada < MAX_PASSADAS:
        restantes = _buracos(estacoes)
        if not restantes:
            logger.info("Cache completo.")
            break
        logger.info("Ainda faltam %d — pausa de %.0fs antes da próxima passada",
                    len(restantes), PAUSA_ENTRE_PASSADAS)
        time.sleep(PAUSA_ENTRE_PASSADAS)

faltando = _buracos(estacoes)
if faltando:
    por_estacao = pd.Series([e for e, _ in faltando]).value_counts()
    logger.warning("INCOMPLETO: %d estação-ano em %d estações", len(faltando), len(por_estacao))
    logger.warning("piores: %s", por_estacao.head(10).to_dict())
    sys.exit(1)
logger.info("CACHE COMPLETO — o pipeline não vai tocar na rede.")
