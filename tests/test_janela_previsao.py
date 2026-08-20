"""O parâmetro `inicio` existe para que a janela de ajuste use PREVISÃO, não ERA5.

Sem ele, um combinador ajustado em 2024 veria `soil_moisture` de reanálise no
ajuste e de previsão na avaliação — ajustar numa distribuição e medir em outra é
exatamente o descasamento que a Fase 1 do MOS existiu para medir.
"""
import inspect

import pandas as pd

from scripts import medir_baseline_ifs as base
from scripts import medir_degradacao_mos as deg

FUNCOES = (deg._trocar_por_previsao, base._baixar_regua, base._anexar_regua)


def test_funcoes_aceitam_inicio():
    for fn in FUNCOES:
        assert 'inicio' in inspect.signature(fn).parameters, fn.__name__


def test_padrao_e_none_e_resolve_no_corpo():
    """Congelar INICIO_PREV na assinatura faria o padrão parar de acompanhar TRAIN_END."""
    for fn in FUNCOES:
        assert inspect.signature(fn).parameters['inicio'].default is None, fn.__name__


def test_inicio_none_usa_a_janela_antiga(monkeypatch):
    """O comportamento sem `inicio` tem de continuar idêntico — scripts antigos dependem."""
    vistos = []
    monkeypatch.setattr(deg, 'fetch_forecast_arquivado',
                        lambda lat, lon, ini, fim, **kw: vistos.append(ini) or pd.DataFrame())
    df = pd.DataFrame({'data_hora': pd.to_datetime(['2025-06-01 12:00'], utc=True),
                       'estacao_codigo': ['A801'], 'latitude': [-30.0], 'longitude': [-51.0],
                       'soil_moisture': [0.3]})
    deg._trocar_por_previsao(df.copy(), '2025-06-02')
    assert vistos == [deg.INICIO_PREV]


def test_inicio_explicito_e_respeitado(monkeypatch):
    vistos = []
    monkeypatch.setattr(deg, 'fetch_forecast_arquivado',
                        lambda lat, lon, ini, fim, **kw: vistos.append(ini) or pd.DataFrame())
    df = pd.DataFrame({'data_hora': pd.to_datetime(['2024-06-01 12:00'], utc=True),
                       'estacao_codigo': ['A801'], 'latitude': [-30.0], 'longitude': [-51.0],
                       'soil_moisture': [0.3]})
    deg._trocar_por_previsao(df.copy(), '2024-06-02', inicio='2024-04-01')
    assert vistos == ['2024-04-01']
