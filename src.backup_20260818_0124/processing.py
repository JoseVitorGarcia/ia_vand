import logging

import numpy as np
import pandas as pd

from src.config import EXTREME_RAIN_THRESHOLD

logger = logging.getLogger(__name__)


def clean_data(df):
    df = df.copy()

    df = df.replace(-9999, np.nan)

    df['estacao'] = (
        df['estacao']
        .astype(str)
        .str.replace(';', '')
        .str.strip()
    )

    df = df.rename(columns={
        'PRECIPITAÇÃO TOTAL, HORÁRIO (mm)': 'precipitacao',
        'TEMPERATURA DO AR - BULBO SECO, HORARIA (°C)': 'temperatura',
        'UMIDADE RELATIVA DO AR, HORARIA (%)': 'umidade',
        'PRESSAO ATMOSFERICA AO NIVEL DA ESTACAO, HORARIA (mB)': 'pressao',
        'VENTO, VELOCIDADE HORARIA (m/s)': 'vento'
    })

    cols = ['precipitacao', 'temperatura', 'umidade', 'pressao', 'vento']

    for col in cols:
        df[col] = pd.to_numeric(df[col], errors='coerce')

    # ── Suporte a dois formatos de arquivo INMET ─────────────────────────────
    # Formato antigo (2015-2019): colunas 'DATA (YYYY-MM-DD)' e 'HORA (UTC)'
    #   onde hora já está em HH:MM.
    # Formato novo  (2020+):      colunas 'Data' e 'Hora UTC'
    #   onde hora está em 'HHMM UTC'.
    # O cache pode conter os dois simultaneamente (concat de CSVs de épocas diferentes).

    # Datetime formato antigo
    if 'DATA (YYYY-MM-DD)' in df.columns and 'HORA (UTC)' in df.columns:
        dt_antigo = pd.to_datetime(
            df['DATA (YYYY-MM-DD)'].astype(str)
            + ' '
            + df['HORA (UTC)'].astype(str).str.strip(),
            errors='coerce',
            utc=True,
        )
    else:
        dt_antigo = pd.Series(pd.NaT, index=df.index, dtype='datetime64[ns, UTC]')

    # Datetime formato novo
    hora_utc = (
        df['Hora UTC'].astype(str) if 'Hora UTC' in df.columns
        else pd.Series('', index=df.index)
    )
    hora_normalizada = hora_utc.str.replace(' UTC', '').str.zfill(4)
    hora_ajustada = hora_normalizada.str[:2] + ':' + hora_normalizada.str[2:]

    data_col = (
        df['Data'].astype(str) if 'Data' in df.columns
        else pd.Series('', index=df.index)
    )
    dt_novo = pd.to_datetime(
        data_col + ' ' + hora_ajustada,
        errors='coerce',
        utc=True,
    )

    # Usa formato antigo onde disponível; preenche com novo onde necessário
    df['data_hora'] = dt_antigo.fillna(dt_novo)

    rejected = df['data_hora'].isna().sum()
    if rejected > 0:
        logger.warning(f"{rejected} linhas rejeitadas por timestamp inválido")

    df = df[df['data_hora'].notna()].copy()

    df = df.sort_values(['estacao', 'data_hora'])

    for col in cols:
        df[col] = df.groupby('estacao')[col].transform(
            lambda x: x.interpolate(limit_direction='both')
        )

    df = df[df['umidade'].between(0, 100)]
    df = df[df['pressao'].between(850, 1050)]
    df = df[df['vento'] >= 0]
    df = df[df['precipitacao'] >= 0]

    return df


def create_features(df):
    print("Criando features...")

    df = df.copy()

    df['hora'] = df['data_hora'].dt.hour.astype(int)
    df['mes'] = df['data_hora'].dt.month.astype(int)

    # Imputa NaNs das features Open-Meteo com média por (estacao, mês).
    # Estações que a API retornou 429 ficam com NaN — sem imputação, o LightGBM
    # as ignora ao calcular importância, distorcendo o ranking de features.
    _om_cols = [c for c in ['cape', 'cloud_cover', 'wind_gusts_10m', 'soil_moisture', 'freezing_level'] if c in df.columns]
    for _col in _om_cols:
        _means = df.groupby(['estacao', 'mes'])[_col].transform('mean')
        df[_col] = df[_col].fillna(_means)
        _global = df[_col].mean()
        df[_col] = df[_col].fillna(0 if pd.isna(_global) else _global)

    df['hora_sin'] = np.sin(2 * np.pi * df['hora'] / 24)
    df['hora_cos'] = np.cos(2 * np.pi * df['hora'] / 24)
    df['mes_sin'] = np.sin(2 * np.pi * df['mes'] / 12)
    df['mes_cos'] = np.cos(2 * np.pi * df['mes'] / 12)

    df['estacao_id'] = (
        df['estacao']
        .astype('category')
        .cat.codes
    )

    # =========================
    # LAGS TEMPORAIS (lookback apenas)
    # =========================
    for lag in [1, 3, 6, 24]:
        df[f'lag_{lag}h'] = (
            df.groupby('estacao')['precipitacao']
            .shift(lag)
        )

    # =========================
    # ACUMULADOS (lookback apenas — sem leakage)
    # =========================
    for janela in [6, 12, 24, 48]:
        df[f'chuva_{janela}h'] = (
            df.groupby('estacao')['precipitacao']
            .transform(
                lambda x: x.rolling(window=janela, min_periods=1).sum()
            )
        )

    # =========================
    # VOLATILIDADE
    # =========================
    df['rolling_std_24h'] = (
        df.groupby('estacao')['precipitacao']
        .transform(
            lambda x: x.rolling(window=24, min_periods=1).std()
        )
    )

    df['rolling_max_24h'] = (
        df.groupby('estacao')['precipitacao']
        .transform(
            lambda x: x.rolling(window=24, min_periods=1).max()
        )
    )

    df['tendencia_6h'] = df['lag_1h'] - df['lag_6h']

    df['queda_pressao_3h'] = (
        df.groupby('estacao')['pressao'].shift(1)
        - df.groupby('estacao')['pressao'].shift(3)
    )

    df['temp_umidade'] = df['temperatura'] * df['umidade']

    # =========================
    # TARGET REGRESSÃO
    # Soma correta das próximas 24h: x[t+1] + x[t+2] + ... + x[t+24]
    # Derivação: reverter série → shift(1) → rolling(24) → reverter de volta
    # garante que cada posição t recebe a soma estritamente futura.
    # =========================
    df['chuva_futura_24h'] = (
        df.groupby('estacao')['precipitacao']
        .transform(
            lambda x:
            x.iloc[::-1]
             .shift(1)
             .rolling(window=24, min_periods=24)
             .sum()
             .iloc[::-1]
        )
    )

    df['rolling_std_24h'] = df['rolling_std_24h'].fillna(0)
    df['rolling_max_24h'] = df['rolling_max_24h'].fillna(0)
    df['tendencia_6h'] = df['tendencia_6h'].fillna(0)
    df['queda_pressao_3h'] = df['queda_pressao_3h'].fillna(0)

    nan_pct = (df.isna().mean() * 100).sort_values(ascending=False)
    nans_relevantes = nan_pct[nan_pct > 0].head(10)
    if not nans_relevantes.empty:
        logger.debug("NaNs (%%):\n%s", nans_relevantes.to_string())

    required_columns = [
        'precipitacao', 'temperatura', 'umidade', 'pressao', 'vento',
        'lag_1h', 'lag_6h', 'lag_24h',
        'chuva_24h', 'chuva_48h',
        'chuva_futura_24h',
    ]

    df = df.dropna(subset=required_columns)

    df['evento_extremo'] = (
        df['chuva_futura_24h'] > EXTREME_RAIN_THRESHOLD
    ).astype(int)

    print(f"Total após features: {len(df):,}")

    return df
