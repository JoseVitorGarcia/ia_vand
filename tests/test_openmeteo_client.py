"""Testes do cliente Open-Meteo — a parte que fala com a API de previsão arquivada."""
import pandas as pd
import pytest

from src import openmeteo_client as oc


RESPOSTA = {
    'hourly': {
        'time': ['2025-09-02T00:00', '2025-09-02T01:00', '2025-09-02T02:00'],
        'cloud_cover_low': [10, 20, 30],
        'cloud_cover_mid': [1, 2, 3],
        'cloud_cover_high': [0, 5, 10],
        'wind_gusts_10m': [4.0, 4.5, 5.0],
        'wind_speed_100m': [8.0, 8.5, 9.0],
        'wind_direction_100m': [90, 180, 270],
        'soil_moisture_0_to_7cm': [0.31, 0.32, 0.33],
        'soil_moisture_28_to_100cm': [0.28, 0.28, 0.29],
    }
}


def test_usa_a_api_de_previsao_arquivada(monkeypatch, tmp_path):
    """Não pode cair no archive-api: aquilo é ERA5, o que este plano quer evitar."""
    monkeypatch.setattr(oc, 'OPENMETEO_PREVISAO_CACHE_DIR', tmp_path)
    chamadas = []

    def falso_request(url, params, **kwargs):
        chamadas.append((url, params))
        return RESPOSTA

    monkeypatch.setattr(oc, '_request', falso_request)
    df = oc.fetch_forecast_arquivado(-30.05, -51.17, '2025-09-02', '2025-09-02')

    assert len(chamadas) == 1
    url, params = chamadas[0]
    assert 'historical-forecast-api' in url
    assert params['start_date'] == '2025-09-02'
    assert len(df) == 3
    assert str(df['data_hora'].dt.tz) == 'UTC'


def test_segunda_chamada_vem_do_cache(monkeypatch, tmp_path):
    """Sem cache, a cota da Open-Meteo estoura antes da janela de teste acabar."""
    monkeypatch.setattr(oc, 'OPENMETEO_PREVISAO_CACHE_DIR', tmp_path)
    chamadas = []

    def falso_request(url, params, **kwargs):
        chamadas.append(url)
        return RESPOSTA

    monkeypatch.setattr(oc, '_request', falso_request)
    oc.fetch_forecast_arquivado(-30.05, -51.17, '2025-09-02', '2025-09-02')
    oc.fetch_forecast_arquivado(-30.05, -51.17, '2025-09-02', '2025-09-02')

    assert len(chamadas) == 1, 'a segunda chamada foi à rede em vez do cache'


def test_colunas_iguais_as_do_historico(monkeypatch, tmp_path):
    """As duas fontes precisam ser intercambiáveis coluna a coluna."""
    from src.config import OPENMETEO_COLUNAS

    monkeypatch.setattr(oc, 'OPENMETEO_PREVISAO_CACHE_DIR', tmp_path)
    monkeypatch.setattr(oc, '_request', lambda url, params, **k: RESPOSTA)
    df = oc.fetch_forecast_arquivado(-30.05, -51.17, '2025-09-02', '2025-09-02')

    assert set(OPENMETEO_COLUNAS) <= set(df.columns)


def test_pede_o_modelo_de_previsao_explicitamente(monkeypatch, tmp_path):
    """Sem `models`, a Open-Meteo resolve best_match e devolve ERA5 — medido em
    1.440 horas: as 8 colunas voltam BYTE A BYTE iguais ao archive-api. O plano
    inteiro mediria zero. Com ecmwf_ifs025 a fonte é de fato distinta (r de 0,63
    a 0,96 contra o ERA5).
    """
    from src.config import OPENMETEO_PREVISAO_MODELO

    monkeypatch.setattr(oc, 'OPENMETEO_PREVISAO_CACHE_DIR', tmp_path)
    capturado = {}

    def falso_request(url, params, **kwargs):
        capturado.update(params)
        return RESPOSTA

    monkeypatch.setattr(oc, '_request', falso_request)
    oc.fetch_forecast_arquivado(-30.05, -51.17, '2025-09-02', '2025-09-02')

    assert capturado['models'] == OPENMETEO_PREVISAO_MODELO


def test_cache_de_janela_parcial_nao_serve_janela_maior(monkeypatch, tmp_path):
    """O cache por ano dava a janela pedida como completa quando só tinha alguns
    dias dela: 3 dias gravados de 2025 faziam qualquer pedido de 2025 devolver
    esses 3 dias, em silêncio. Aqui a janela é parcial por construção — o
    arquivo de previsão só cobre a janela de teste, nunca o ano inteiro.
    """
    monkeypatch.setattr(oc, 'OPENMETEO_PREVISAO_CACHE_DIR', tmp_path)
    chamadas = []

    def falso_request(url, params, **kwargs):
        chamadas.append(params['end_date'])
        return RESPOSTA

    monkeypatch.setattr(oc, '_request', falso_request)
    oc.fetch_forecast_arquivado(-30.05, -51.17, '2025-09-02', '2025-09-02')
    oc.fetch_forecast_arquivado(-30.05, -51.17, '2025-09-02', '2025-09-30')

    assert chamadas == ['2025-09-02', '2025-09-30'], \
        'a janela maior foi servida pelo cache da menor'


RESPOSTA_CHUVA = {
    'hourly': {
        'time': ['2025-09-02T00:00', '2025-09-02T01:00', '2025-09-02T02:00'],
        'precipitation': [0.0, 1.2, 3.4],
        'precipitation_probability': [10, 55, 80],
    }
}


def test_aceita_conjunto_de_variaveis_proprio(monkeypatch, tmp_path):
    """A régua do IFS precisa de `precipitation`, que não está em
    OPENMETEO_HISTORICAL_VARS — aquelas 8 são de propósito as que o INMET não
    fornece."""
    monkeypatch.setattr(oc, 'OPENMETEO_PREVISAO_CACHE_DIR', tmp_path)
    capturado = {}

    def falso_request(url, params, **kwargs):
        capturado.update(params)
        return RESPOSTA_CHUVA

    monkeypatch.setattr(oc, '_request', falso_request)
    df = oc.fetch_forecast_arquivado(-30.05, -51.17, '2025-09-02', '2025-09-02',
                                     variaveis=['precipitation',
                                                'precipitation_probability'])

    assert capturado['hourly'] == 'precipitation,precipitation_probability'
    assert list(df.columns) == ['data_hora', 'precipitation', 'precipitation_probability']
    assert df['precipitation'].tolist() == [0.0, 1.2, 3.4]


def test_cache_nao_mistura_conjuntos_de_variaveis(monkeypatch, tmp_path):
    """Sem o conjunto na chave, o cache das 8 variáveis atmosféricas seria
    servido para um pedido de precipitação — e `_cache_utilizavel` recusaria o
    arquivo em silêncio a cada chamada, rebaixando tudo de novo toda vez."""
    monkeypatch.setattr(oc, 'OPENMETEO_PREVISAO_CACHE_DIR', tmp_path)

    monkeypatch.setattr(oc, '_request', lambda url, params, **k: RESPOSTA)
    oc.fetch_forecast_arquivado(-30.05, -51.17, '2025-09-02', '2025-09-02')

    chamadas = []

    def falso_request(url, params, **kwargs):
        chamadas.append(params['hourly'])
        return RESPOSTA_CHUVA

    monkeypatch.setattr(oc, '_request', falso_request)
    df = oc.fetch_forecast_arquivado(-30.05, -51.17, '2025-09-02', '2025-09-02',
                                     variaveis=['precipitation'])

    assert len(chamadas) == 1, 'o cache das 8 variáveis foi servido para a chuva'
    assert 'precipitation' in df.columns
