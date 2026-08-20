"""Guarda, todo dia, o que a previsão dizia sobre as próximas 24 h.

Por que existe: a API de previsão arquivada devolve, para cada hora, a rodada
mais recente antes dela — não a rodada que um operador teria visto ao decidir,
com 24 h de antecedência. Por isso o desempenho medido da variante D é
otimista, e a única forma de saber quanto é acumular as previsões conforme elas
são emitidas. Não há atalho: esse dado não existe em arquivo nenhum, só passa a
existir a partir do dia em que se começa a colher.

Três diferenças em relação ao que a inferência pede à mesma API, todas
deliberadas:

  1. pede `precipitation`. As variáveis da inferência excluem chuva de propósito
     (o INMET já fornece), mas a régua do IFS mede justamente a SOMA do volume
     previsto em 24 h — sem essa coluna a colheita acumularia por meses sem a
     única variável que carrega o sinal.
  2. fixa `ecmwf_ifs025`. A comparação futura é contra 0,3957, que foi medido
     com esse modelo; best_match troca de modelo conforme a região e a hora, e a
     comparação viraria maçã com laranja sem nada indicar isso.
  3. congela as coordenadas num parquet de 98 linhas. O desenho original relia
     `load_data()` todo dia — 4,6 milhões de linhas na memória, dentro do
     cgroup, para extrair latitude e longitude que não mudam.

Rodar uma vez por dia (cron ou systemd timer):
    ./run.sh scripts/colher_previsao_diaria.py
    ./run.sh scripts/colher_previsao_diaria.py --forcar   # recolhe hoje
"""
import logging
import sys
import time

import pandas as pd

from src.config import (OPENMETEO_CACHE_DIR, OPENMETEO_FORECAST_VARS,
                        OPENMETEO_PREVISAO_MODELO, OPENMETEO_REQUEST_DELAY)
from src.openmeteo_client import fetch_forecast

logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s %(levelname)s %(name)s — %(message)s',
                    datefmt='%H:%M:%S')
logger = logging.getLogger('colheita')

DESTINO = OPENMETEO_CACHE_DIR / 'colheita'
DESTINO.mkdir(parents=True, exist_ok=True)
ESTACOES = DESTINO / 'estacoes.parquet'

# A chuva prevista não está em OPENMETEO_FORECAST_VARS — ver o item 1 no topo.
VARIAVEIS = OPENMETEO_FORECAST_VARS + ['precipitation']


def _estacoes():
    """Coordenada de cada estação, lida do congelado ou derivada uma única vez."""
    if ESTACOES.exists():
        return pd.read_parquet(ESTACOES)

    logger.info('Primeira execução: derivando coordenadas de load_data()')
    from src.ingestion import load_data
    df = load_data()
    t = (df[['estacao_codigo', 'latitude', 'longitude']].dropna()
         .groupby('estacao_codigo', observed=True).first().reset_index())
    del df
    t.to_parquet(ESTACOES, index=False)
    logger.info('%d estações congeladas em %s', len(t), ESTACOES)
    return t


FORCAR = '--forcar' in sys.argv

hoje = pd.Timestamp.now(tz='UTC').strftime('%Y-%m-%d')
arquivo = DESTINO / f'{hoje}.parquet'
if arquivo.exists() and not FORCAR:
    logger.info('%s já colhido', hoje)
    raise SystemExit(0)

if FORCAR:
    # Sem isto, recolher dentro de uma hora devolveria o parquet em cache com
    # um `emitida_em` novo carimbado por cima — o arquivo diria que a previsão
    # foi emitida agora quando ela é de uma hora atrás. Como o valor inteiro da
    # colheita está em saber QUANDO cada previsão foi emitida, um carimbo falso
    # é pior que não colher.
    import src.openmeteo_client as _cliente
    _cliente.OPENMETEO_FORECAST_TTL_HOURS = 0
    logger.info('--forcar: ignorando o cache de previsão')

estacoes = _estacoes()
partes, falhas = [], []
for _, r in estacoes.iterrows():
    try:
        prev = fetch_forecast(r['latitude'], r['longitude'],
                              variaveis=VARIAVEIS,
                              modelo=OPENMETEO_PREVISAO_MODELO)
        prev['estacao_codigo'] = r['estacao_codigo']
        prev['emitida_em'] = pd.Timestamp.now(tz='UTC')
        partes.append(prev)
    except Exception as exc:
        falhas.append((r['estacao_codigo'], str(exc)))
    # O cliente só pausa nas rotas de histórico; aqui a pausa é por nossa conta.
    time.sleep(OPENMETEO_REQUEST_DELAY)

if not partes:
    # Com o motivo junto: o `except` acima transforma qualquer erro em falha de
    # estação, então uma quebra de código chega aqui com a mesma cara de uma
    # queda de rede. Sem o motivo no log não dá para distinguir as duas.
    logger.error('nenhuma estação colhida em %s — %d falhas: %s',
                 hoje, len(falhas), falhas[:3])
    raise SystemExit(1)

df = pd.concat(partes, ignore_index=True)

# Grava em temporário e renomeia: se o processo morrer no meio da escrita, o
# guarda de "já colhido" lá em cima veria um parquet truncado como dia pronto e
# o buraco ficaria permanente.
tmp = arquivo.with_suffix('.parquet.tmp')
df.to_parquet(tmp, index=False)
tmp.rename(arquivo)

logger.info('%s: %d estações, %d linhas, horizonte até %s',
            hoje, len(partes), len(df), df['data_hora'].max())
if df['precipitation'].isna().all():
    logger.error('coluna precipitation inteiramente nula — a colheita não '
                 'serve para medir a régua do IFS; investigar antes de acumular')
if falhas:
    logger.warning('%d estações falharam: %s', len(falhas), falhas[:5])
