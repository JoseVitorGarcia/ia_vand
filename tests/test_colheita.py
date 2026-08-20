"""Testes do colhedor diário de previsões.

Este script tem uma característica incômoda: cada execução é irrepetível. A
previsão emitida hoje às 12 UTC não existe em lugar nenhum amanhã, então um
defeito só se descobre quando o dado já foi perdido — e como ele roda à mão,
sem cron, ninguém está olhando o log no momento em que falha. Daí testar aqui
os caminhos que a execução feliz não exercita.
"""
import runpy

import pandas as pd
import pytest

from src import config
from src import openmeteo_client as oc

SCRIPT = 'scripts/colher_previsao_diaria.py'


def _previsao_falsa(lat, lon, variaveis=None, modelo=None):
    horas = pd.date_range('2026-08-20', periods=48, freq='h', tz='UTC')
    df = pd.DataFrame({'data_hora': horas, 'precipitation': 1.0})
    for v in (variaveis or []):
        if v not in df:
            df[v] = 0.0
    return df


@pytest.fixture
def ambiente(monkeypatch, tmp_path):
    """Isola cache e rede: nenhum teste daqui toca a Open-Meteo."""
    monkeypatch.setattr(config, 'OPENMETEO_CACHE_DIR', tmp_path)
    monkeypatch.setattr(oc, 'fetch_forecast', _previsao_falsa)
    monkeypatch.setattr(config, 'OPENMETEO_REQUEST_DELAY', 0.0)
    monkeypatch.setattr('sys.argv', [SCRIPT])
    estacoes = tmp_path / 'colheita'
    estacoes.mkdir()
    pd.DataFrame({'estacao_codigo': ['A801', 'A802'],
                  'latitude': [-30.05, -29.7],
                  'longitude': [-51.17, -53.8]}).to_parquet(
        estacoes / 'estacoes.parquet', index=False)
    return tmp_path / 'colheita'


def _rodar():
    try:
        runpy.run_path(SCRIPT, run_name='__main__')
    except SystemExit as saida:
        return saida.code or 0
    return 0


def test_colhe_o_dia(ambiente):
    assert _rodar() == 0
    (arquivo,) = ambiente.glob('2*.parquet')
    df = pd.read_parquet(arquivo)
    assert set(df['estacao_codigo']) == {'A801', 'A802'}
    # A chuva prevista é a razão de ser da colheita — ver o item 1 no topo do
    # script. Se ela sumir da lista de variáveis, o arquivo continua "válido" e
    # inútil, e meses de acúmulo vão junto.
    assert df['precipitation'].notna().all()
    assert df['emitida_em'].notna().all()


def test_nao_recolhe_o_mesmo_dia(ambiente):
    _rodar()
    (arquivo,) = ambiente.glob('2*.parquet')
    antes = arquivo.read_bytes()
    assert _rodar() == 0
    assert arquivo.read_bytes() == antes


def test_estacao_que_falha_nao_derruba_as_outras(ambiente, monkeypatch):
    def as_vezes(lat, lon, **kwargs):
        if lat == -30.05:
            raise RuntimeError('429')
        return _previsao_falsa(lat, lon, **kwargs)

    monkeypatch.setattr(oc, 'fetch_forecast', as_vezes)
    assert _rodar() == 0
    (arquivo,) = ambiente.glob('2*.parquet')
    assert set(pd.read_parquet(arquivo)['estacao_codigo']) == {'A802'}


def test_dia_totalmente_perdido_sai_com_erro(ambiente, monkeypatch):
    """Rodando à mão, sem log vigiado, o código de saída é o único aviso."""
    def sempre_falha(lat, lon, **kwargs):
        raise RuntimeError('rede caiu')

    monkeypatch.setattr(oc, 'fetch_forecast', sempre_falha)
    assert _rodar() == 1
    assert list(ambiente.glob('2*.parquet')) == []


def test_nao_deixa_temporario_para_tras(ambiente):
    """Um .tmp sobrevivente vira um dia 'já colhido' truncado, e o buraco é permanente."""
    _rodar()
    assert list(ambiente.glob('*.tmp')) == []
