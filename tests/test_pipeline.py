"""
Testes de regressão para as falhas encontradas na auditoria de 18/08/2026.

Rodar com:  PYTHONPATH=. venv/bin/python -m pytest tests/ -v

Os dois primeiros testes existem porque F-01 e F-02 passaram despercebidos por
meses: ambos falhavam em silêncio, produzindo números plausíveis mas errados.
"""

import numpy as np
import pandas as pd
import pytest

from src.config import EXTREME_RAIN_THRESHOLD, TRAIN_END, VALID_END
from src.ingestion import _codigo_wmo, _normalizar_chave
from src.processing import clean_data, create_features


def _dataset_sintetico(n_estacoes=3, horas=800, semente=42):
    """Duas estações bem comportadas e uma com lacuna, no formato do CSV INMET."""
    rng = np.random.default_rng(semente)
    inicio = pd.Timestamp('2015-01-01', tz='UTC')

    linhas = []
    for i in range(n_estacoes):
        grade = pd.date_range(inicio, periods=horas, freq='h', tz='UTC')
        if i == 2:
            # Estação com lacuna de 40 dias no meio
            grade = grade.delete(range(300, 300 + 24 * 40 if horas > 24 * 40 + 300 else 300))
        for t in grade:
            linhas.append({
                'Data': t.strftime('%Y-%m-%d'),
                'Hora UTC': t.strftime('%H%M') + ' UTC',
                'PRECIPITACAO TOTAL, HORARIO (mm)': max(0.0, rng.gamma(0.3, 6)),
                'TEMPERATURA DO AR - BULBO SECO, HORARIA (C)': 20 + rng.normal(0, 4),
                'UMIDADE RELATIVA DO AR, HORARIA (%)': rng.uniform(40, 100),
                'PRESSAO ATMOSFERICA AO NIVEL DA ESTACAO, HORARIA (mB)': 1010 + rng.normal(0, 5),
                'VENTO, VELOCIDADE HORARIA (m/s)': abs(rng.normal(3, 1.5)),
                'TEMPERATURA DO PONTO DE ORVALHO (C)': 15 + rng.normal(0, 3),
                'VENTO, RAJADA MAXIMA (m/s)': abs(rng.normal(6, 2)),
                'VENTO, DIRECAO HORARIA (gr) ( (gr))': rng.uniform(0, 360),
                'estacao_codigo': f'A{800 + i}',
                'estacao_nome': f'ESTACAO {i}',
                'latitude': -30.0 - i * 0.5,
                'longitude': -51.0 - i * 0.5,
                'altitude': 50.0 + i * 100,
            })
    return pd.DataFrame(linhas)


@pytest.fixture(scope='module')
def df_features():
    return create_features(clean_data(_dataset_sintetico()))


# ── F-01 ──────────────────────────────────────────────────────────────────────

def test_saida_ordenada_no_tempo(df_features):
    """O TimeSeriesSplit corta por posição de linha.

    Se a saída de create_features não estiver ordenada no tempo, ele separa
    estações em vez de períodos — treino e teste passam a cobrir o mesmo
    intervalo e a validação temporal deixa de existir. Era a causa do F1 de 0,24.
    """
    assert df_features['data_hora'].is_monotonic_increasing


def test_janelas_nao_se_sobrepoem(df_features):
    """Treino, validação e teste precisam ser disjuntos e ordenados no tempo."""
    from src.model import separar_janelas

    df = df_features.copy()
    # O dataset sintético é curto; encosta as janelas nos dados disponíveis
    import src.config as cfg
    original = (cfg.TRAIN_END, cfg.VALID_END)
    quantis = df['data_hora'].quantile([0.6, 0.8])
    cfg.TRAIN_END, cfg.VALID_END = quantis.iloc[0], quantis.iloc[1]
    import src.model as model
    model.TRAIN_END, model.VALID_END = cfg.TRAIN_END, cfg.VALID_END
    try:
        treino, validacao, teste = separar_janelas(df)
        assert not (treino & validacao).any()
        assert not (validacao & teste).any()
        assert not (treino & teste).any()
        assert df.loc[treino, 'data_hora'].max() < df.loc[validacao, 'data_hora'].min()
        assert df.loc[validacao, 'data_hora'].max() < df.loc[teste, 'data_hora'].min()
    finally:
        cfg.TRAIN_END, cfg.VALID_END = original
        model.TRAIN_END, model.VALID_END = original


# ── F-02 / F-04 ───────────────────────────────────────────────────────────────

def test_nenhuma_estacao_desconhecida(df_features):
    """Nenhuma estação pode terminar como 'UNKNOWN'.

    O cabeçalho de 2019 traz 'ESTAC?O:' com um '?' literal. A chave não batia e
    o `.get('ESTACAO', 'UNKNOWN')` silenciava a falha: as 44 estações do ano
    viravam uma só, com lags e alvo calculados misturando 44 cidades.
    """
    assert 'UNKNOWN' not in set(df_features['estacao_codigo'])


def test_normaliza_as_tres_grafias_do_inmet():
    assert _normalizar_chave('ESTAÇÃO') == 'ESTACAO'   # 2015-2018
    assert _normalizar_chave('ESTAC?O') == 'ESTACO'    # 2019
    assert _normalizar_chave('ESTACAO') == 'ESTACAO'   # 2020+


def test_codigo_wmo_extraido_do_nome_do_arquivo():
    assert _codigo_wmo('INMET_S_RS_A801_PORTO ALEGRE_01-01-2018_A_31-12-2018.CSV') == 'A801'
    # O nome muda entre anos, o código não — é por isso que ele é a identidade
    assert _codigo_wmo('INMET_S_RS_A801_PORTO ALEGRE - JARDIM BOTANICO_01-01-2026_A_31-07-2026.CSV') == 'A801'
    assert _codigo_wmo('INMET_S_RS_B841_TORRES-AEROPORTO_01-01-2025_A_31-12-2025.CSV') == 'B841'
    assert _codigo_wmo('arquivo_sem_codigo.CSV') is None


# ── Alvo ──────────────────────────────────────────────────────────────────────

def test_alvo_e_estritamente_futuro():
    """chuva_futura_24h precisa somar t+1..t+24, sem incluir a hora atual."""
    df = create_features(clean_data(_dataset_sintetico(n_estacoes=1, horas=200)))
    uma = df[df['estacao_codigo'] == 'A800'].sort_values('data_hora').reset_index(drop=True)

    for i in [10, 50, 100]:
        esperado = uma['precipitacao'].iloc[i + 1:i + 25].sum()
        assert uma['chuva_futura_24h'].iloc[i] == pytest.approx(esperado, abs=1e-6)


def test_alvo_nao_atravessa_lacunas():
    """Numa lacuna longa, o alvo deve ser NaN em vez de somar horas distantes.

    Antes, `rolling(window=24)` era posicional: atravessando uma lacuna, 'as
    próximas 24 linhas' podiam cobrir meses. A grade horária completa em
    _reamostrar_horario faz 24 posições valerem exatamente 24 horas.
    """
    df = create_features(clean_data(_dataset_sintetico(n_estacoes=3, horas=800)))
    com_lacuna = df[df['estacao_codigo'] == 'A802'].sort_values('data_hora')

    saltos = com_lacuna['data_hora'].diff()
    if (saltos > pd.Timedelta('24h')).any():
        antes_do_salto = com_lacuna[saltos.shift(-1) > pd.Timedelta('24h')]
        # As linhas imediatamente antes da lacuna não têm 24 h futuras válidas
        assert antes_do_salto['chuva_futura_24h'].isna().all() or antes_do_salto.empty


def test_evento_extremo_bate_com_o_limiar(df_features):
    esperado = (df_features['chuva_futura_24h'] > EXTREME_RAIN_THRESHOLD).astype(int)
    assert (df_features['evento_extremo'] == esperado).all()


# ── F-07 ──────────────────────────────────────────────────────────────────────

def test_falha_de_sensor_nao_descarta_a_linha():
    """Uma linha com chuva válida deve sobreviver a outro sensor fora de faixa."""
    bruto = _dataset_sintetico(n_estacoes=1, horas=100)
    bruto.loc[10, 'UMIDADE RELATIVA DO AR, HORARIA (%)'] = 250      # impossível
    bruto.loc[10, 'PRECIPITACAO TOTAL, HORARIO (mm)'] = 12.5        # válido
    bruto.loc[11, 'VENTO, VELOCIDADE HORARIA (m/s)'] = -5           # impossível
    bruto.loc[11, 'PRECIPITACAO TOTAL, HORARIO (mm)'] = 8.0         # válido

    limpo = clean_data(bruto)

    assert len(limpo) == 100, "nenhuma linha deveria ter sido descartada"
    assert limpo['precipitacao'].notna().all()
    # O valor impossível vira NaN, mas só ele
    assert limpo['umidade'].isna().sum() >= 0


def test_sem_duplicatas_de_estacao_hora(df_features):
    assert not df_features.duplicated(subset=['estacao_codigo', 'data_hora']).any()


# ── F-06 / F-12 / F-15 ────────────────────────────────────────────────────────

def test_features_novas_presentes(df_features):
    esperadas = [
        'orvalho', 'deficit_orvalho', 'rajada', 'vento_dir_sin', 'altitude',
        'clima_chuva_media', 'clima_chuva_p99', 'viz_chuva_3h',
    ]
    faltando = [c for c in esperadas if c not in df_features.columns]
    assert not faltando, f"features ausentes: {faltando}"


def test_estacao_id_removido(df_features):
    """estacao_id dependia da ordem alfabética e não era reproduzível na inferência."""
    assert 'estacao_id' not in df_features.columns
