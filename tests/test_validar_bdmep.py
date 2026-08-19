"""Testes da validação cruzada com o BDMEP diário."""
import pandas as pd
import pytest

from scripts.validar_com_bdmep import agregar_dia_pluviometrico, ler_bdmep_diario

CONTEUDO = """Nome: PORTO ALEGRE - JARDIM BOTANICO
Codigo Estacao: A801
Latitude: -30.05361111
Longitude: -51.17472221
Altitude: 41.18
Situacao: Operante
Data Inicial: 2015-01-01
Data Final: 2026-07-31
Periodicidade da Medicao: Diaria

Data Medicao;PRECIPITACAO TOTAL, DIARIO (AUT)(mm);TEMPERATURA MEDIA, DIARIA (AUT)(°C);
2015-01-01;5;25.8;
2015-01-02;18.8;22.1;
2015-01-03;null;null;
"""


@pytest.fixture
def arquivo(tmp_path):
    caminho = tmp_path / "dados_A801_D_2015-01-01_2026-07-31.csv"
    caminho.write_text(CONTEUDO, encoding="utf-8")
    return caminho


def test_le_codigo_e_chuva(arquivo):
    df = ler_bdmep_diario(arquivo)
    assert df.attrs['estacao_codigo'] == 'A801'
    assert list(df['chuva_bdmep'].head(2)) == [5.0, 18.8]


def test_null_literal_vira_nan(arquivo):
    """O BDMEP escreve 'null' como texto — sem na_values, a coluna inteira vira
    object e a soma quebra em silêncio."""
    df = ler_bdmep_diario(arquivo)
    assert pd.isna(df['chuva_bdmep'].iloc[2])
    assert df['chuva_bdmep'].dtype.kind == 'f'


def test_decimal_e_ponto(arquivo):
    """Os CSVs anuais do portal usam vírgula; o BDMEP usa ponto. Trocar os dois
    faz 18.8 virar 188."""
    df = ler_bdmep_diario(arquivo)
    assert df['chuva_bdmep'].iloc[1] == pytest.approx(18.8)


def test_dia_pluviometrico_vai_de_13utc_a_12utc():
    """Medido em A801 sobre 4.182 dias: r=1,0000 no deslocamento de +11 h.

    A chuva rotulada 13 UTC do dia 1 é a que caiu entre 12 e 13 UTC, e pertence
    ao dia pluviométrico 2. A rotulada 12 UTC do dia 2 ainda é do dia 2; a das
    13 UTC do dia 2 já é do dia 3.
    """
    horas = pd.date_range('2015-01-01 00:00', '2015-01-03 23:00', freq='h', tz='UTC')
    df = pd.DataFrame({'data_hora': horas, 'precipitacao': 0.0})
    df.loc[df['data_hora'] == '2015-01-01 13:00+00:00', 'precipitacao'] = 10.0
    df.loc[df['data_hora'] == '2015-01-02 12:00+00:00', 'precipitacao'] = 5.0
    df.loc[df['data_hora'] == '2015-01-02 13:00+00:00', 'precipitacao'] = 7.0

    diario = agregar_dia_pluviometrico(df)
    assert diario[pd.Timestamp('2015-01-02')] == pytest.approx(15.0)
    assert diario[pd.Timestamp('2015-01-03')] == pytest.approx(7.0)


def test_dia_sem_hora_valida_vira_nan_e_nao_zero():
    """`groupby.sum()` devolve 0.0 para um dia inteiro de NaN, e um dia sem
    medição nenhuma passaria a "choveu 0 mm" — concordando com o BDMEP toda vez
    que ele também marcar 0. Medido em B819: 3 dias de julho/2026 com as 24
    linhas presentes e precipitação NaN em todas, contra 61,4 e 41,9 mm no
    BDMEP.
    """
    horas = pd.date_range('2015-01-01 13:00', '2015-01-02 12:00', freq='h', tz='UTC')
    df = pd.DataFrame({'data_hora': horas, 'precipitacao': float('nan')})

    diario = agregar_dia_pluviometrico(df)
    assert pd.isna(diario[pd.Timestamp('2015-01-02')])


def test_min_horas_exclui_dia_com_cobertura_parcial():
    """Um dia com metade das horas subestima o total e não é comparável com o
    diário oficial. Com min_horas=24 só entram dias completos."""
    horas = pd.date_range('2015-01-01 13:00', '2015-01-02 12:00', freq='h', tz='UTC')
    df = pd.DataFrame({'data_hora': horas, 'precipitacao': 1.0})
    df.loc[df.index[:12], 'precipitacao'] = float('nan')

    assert agregar_dia_pluviometrico(df)[pd.Timestamp('2015-01-02')] == pytest.approx(12.0)
    assert pd.isna(agregar_dia_pluviometrico(df, min_horas=24)[pd.Timestamp('2015-01-02')])
