"""Enche o cache de previsão arquivada da janela de teste.

Mesma razão de existir do preencher_cache_openmeteo.py: o rate limit da
Open-Meteo é por IP e a falha é silenciosa — quem baixa dentro do pipeline perde
a estação inteira para NaN sem nada gritar.

Diferença para o preenchedor do histórico: aqui o cache é por JANELA, não por
ano, porque a janela de teste é parcial por construção. Uma estação está
completa ou não está; não há preenchimento por partes.

Uso:
    ./run.sh scripts/preencher_cache_previsao.py        # até 5 passadas
    ./run.sh scripts/preencher_cache_previsao.py 10 60
    ./run.sh scripts/preencher_cache_previsao.py 0      # só relata
"""
import logging
import sys
import time

import pandas as pd

from src.config import VALID_END, OPENMETEO_PREVISAO_MODELO
from src.ingestion import load_data
from src.openmeteo_client import (_cache_utilizavel, _previsao_cache_path,
                                  fetch_forecast_arquivado)

logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s %(levelname)s %(name)s — %(message)s',
                    datefmt='%H:%M:%S')
logger = logging.getLogger('preencher_previsao')

MAX_PASSADAS = int(sys.argv[1]) if len(sys.argv) > 1 else 5
PAUSA = float(sys.argv[2]) if len(sys.argv) > 2 else 60.0

# A janela de teste começa depois do embargo de 24 h sobre VALID_END.
INICIO = (VALID_END + pd.Timedelta(hours=25)).strftime('%Y-%m-%d')


def _estacoes():
    """Coordenada canônica e fim da série de cada estação."""
    df = load_data()
    data = pd.to_datetime(
        df['DATA (YYYY-MM-DD)'].fillna(df['Data']).astype(str).str.replace('/', '-', regex=False),
        errors='coerce')
    t = pd.DataFrame({'est': df['estacao_codigo'], 'lat': df['latitude'],
                      'lon': df['longitude'], 'data': data}).dropna()
    return t.groupby('est').agg(lat=('lat', 'first'), lon=('lon', 'first'),
                                fim=('data', 'max'))


def _buracos(estacoes, fim):
    """Estações cuja janela de teste ainda não está em cache."""
    return [est for est, r in estacoes.iterrows()
            if not _cache_utilizavel(_previsao_cache_path(r['lat'], r['lon'], INICIO, fim))]


estacoes = _estacoes()
FIM = estacoes['fim'].max().strftime('%Y-%m-%d')
logger.info('%d estações | janela de teste %s a %s | modelo %s',
            len(estacoes), INICIO, FIM, OPENMETEO_PREVISAO_MODELO)

for passada in range(1, MAX_PASSADAS + 1):
    faltando = _buracos(estacoes, FIM)
    if not faltando:
        logger.info('Cache completo.')
        break

    logger.info('Passada %d/%d — faltam %d estações', passada, MAX_PASSADAS, len(faltando))
    for i, est in enumerate(faltando, 1):
        r = estacoes.loc[est]
        try:
            fetch_forecast_arquivado(r['lat'], r['lon'], INICIO, FIM)
        except Exception as exc:
            # Segue: o que baixou está em disco e a passada seguinte retoma.
            logger.warning('%s falhou (%d/%d): %s', est, i, len(faltando), exc)

    if passada < MAX_PASSADAS:
        restantes = _buracos(estacoes, FIM)
        if not restantes:
            logger.info('Cache completo.')
            break
        logger.info('Ainda faltam %d — pausa de %.0fs', len(restantes), PAUSA)
        time.sleep(PAUSA)

faltando = _buracos(estacoes, FIM)
if faltando:
    logger.warning('INCOMPLETO: %d estações sem previsão', len(faltando))
    logger.warning('faltando: %s', faltando[:15])
    sys.exit(1)
logger.info('CACHE DE PREVISÃO COMPLETO')
