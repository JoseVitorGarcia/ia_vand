import pandas as pd

from pathlib import Path

# ==============================
# PATHS
# ==============================

BASE_DIR = Path(__file__).resolve().parent.parent

RAW_DATA_DIR = BASE_DIR / "data" / "raw"
CACHE_DIR = BASE_DIR / "cache"
MODELS_DIR = BASE_DIR / "models"
REPORTS_DIR = BASE_DIR / "reports"

CACHE_DIR.mkdir(exist_ok=True)
MODELS_DIR.mkdir(exist_ok=True)
REPORTS_DIR.mkdir(exist_ok=True)

# ==============================
# DATASET
# ==============================

EXTREME_RAIN_THRESHOLD = 50

# Filtro de estados. Adicione siglas para incluir mais regiões.
# Exemplo: ['RS', 'SC', 'PR']
STATES_FILTER = ['RS']

# ==============================
# LIMPEZA
# ==============================

# Lacunas maiores que isto ficam NaN em vez de receber interpolação linear.
# Sem limite, uma estação fora do ar por meses recebia valores inventados —
# o maior buraco da base tem 651 dias.
INTERPOLACAO_LIMITE_HORAS = 3

# ==============================
# JANELAS TEMPORAIS
# ==============================
# O split é por data, não por proporção de linhas: treino até TRAIN_END,
# validação (calibração + threshold) até VALID_END, teste do que sobra.
# Um embargo separa as janelas — sem ele, o alvo das últimas linhas de treino
# (soma de t+1 a t+24) invade o início da validação.

TRAIN_END = pd.Timestamp('2024-12-31 23:00', tz='UTC')
VALID_END = pd.Timestamp('2025-08-31 23:00', tz='UTC')
EMBARGO_HORAS = 24

# Climatologia por estação usa apenas dados até aqui, para não vazar o futuro
CLIMATOLOGIA_CUTOFF = TRAIN_END

# Folds do TimeSeriesSplit dentro do treino (Optuna e barras de erro)
N_SPLITS_TUNE = 3
N_SPLITS_EVAL = 5

# ==============================
# VIZINHANÇA ESPACIAL
# ==============================

VIZINHOS_K = 5
VIZINHOS_RAIO_KM = 150

# ==============================
# OPEN-METEO
# ==============================

OPENMETEO_CACHE_DIR = CACHE_DIR / 'openmeteo'
OPENMETEO_CACHE_DIR.mkdir(exist_ok=True)

# TTL em horas para o cache da previsão (forecast)
OPENMETEO_FORECAST_TTL_HOURS = 1

# Delay em segundos entre requisições históricas para respeitar o rate limit.
# A API gratuita limita ~600 req/min mas o burst de 100 estações x 12 anos
# dispara 429 sem esse intervalo. 1s garante ~60 req/min — bem abaixo do limite.
OPENMETEO_REQUEST_DELAY = 1.0

# Variáveis que complementam o INMET sem duplicar (não inclui precipitação,
# temperatura, umidade, pressão e vento, que o INMET já fornece).
# `cape` e `freezing_level_height` saíram em 18/08/2026: o ERA5 não os tem e a
# Open-Meteo devolve nulo em silêncio (HTTP 200, coluna inteira vazia). Ficaram
# meses na lista sem que ninguém notasse, e o modelo treinava com duas colunas
# 100% NaN. Variáveis de nível de pressão (temperature_850hPa e afins), o
# substituto natural, também voltam vazias deste endpoint — verificado com
# models=era5 e era5_land. O que sobra de útil é tudo de superfície.
OPENMETEO_HISTORICAL_VARS = [
    # Convecção: nuvem alta é bigorna de convecção profunda. É o proxy mais
    # direto de instabilidade que o arquivo oferece, no lugar do CAPE.
    'cloud_cover_low',
    'cloud_cover_mid',
    'cloud_cover_high',
    'wind_gusts_10m',          # Rajadas (m/s) — INMET fornece só a média
    # Transporte de umidade: o jato de baixos níveis sul-americano traz umidade
    # amazônica para o RS e é o mecanismo dominante de chuva extrema aqui.
    # A 100 m se está muito mais perto dele do que nos 10 m do INMET.
    'wind_speed_100m',
    'wind_direction_100m',
    'soil_moisture_0_to_7cm',    # Saturação superficial (m³/m³)
    'soil_moisture_28_to_100cm', # Camada profunda: decide se a chuva vira enxurrada
]

OPENMETEO_FORECAST_VARS = OPENMETEO_HISTORICAL_VARS + [
    'precipitation_probability',  # disponível apenas em forecast
]

# Nomes longos da API → nomes internos. Fica aqui, e não no cliente, para que
# ingestion e predict derivem as colunas da mesma fonte em vez de repetirem a
# lista na mão — foi assim que `cape` sobreviveu em três lugares diferentes.
OPENMETEO_RENAME = {
    'soil_moisture_0_to_7cm': 'soil_moisture',
    'soil_moisture_28_to_100cm': 'soil_moisture_profundo',
}

# Colunas que enrich_openmeteo acrescenta ao DataFrame, já renomeadas.
OPENMETEO_COLUNAS = [OPENMETEO_RENAME.get(v, v) for v in OPENMETEO_HISTORICAL_VARS]

# Religado em 18/08/2026. Ficou desligado nas fases 1 e 2 porque a mudança de
# identidade de estação (código WMO) alterou as chaves lat/lon do cache: havia
# cobertura para 70 das 100 estações e nenhum dado de 2026. O rebaixe acontece
# na própria execução — fetch_historical baixa e cacheia por (lat, lon, ano), e
# falha de API degrada para NaN naquela estação em vez de derrubar o pipeline.
ENABLE_OPENMETEO = True

# ==============================
# FEATURES
# ==============================

# Features derivadas de observação INMET, disponíveis sempre
FEATURES_INMET = [
    'precipitacao',
    'temperatura',
    'umidade',
    'pressao',
    'vento',

    # Colunas antes descartadas do CSV INMET
    'orvalho',
    'deficit_orvalho',
    'tendencia_orvalho_3h',
    'rajada',
    'rajada_excesso',
    'vento_dir_sin',
    'vento_dir_cos',
    'vento_norte',
    'vento_leste',
    'amplitude_temp',
    'amplitude_pressao',

    # Lags temporais (lookback)
    'lag_1h',
    'lag_3h',
    'lag_6h',
    'lag_24h',

    # Acumulados (lookback)
    'chuva_3h',
    'chuva_6h',
    'chuva_12h',
    'chuva_24h',
    'chuva_48h',
    'chuva_72h',
    'chuva_24h_rel',

    # Volatilidade
    'rolling_std_24h',
    'rolling_max_24h',

    # Tendências
    'tendencia_6h',
    'queda_pressao_3h',
    'queda_pressao_24h',

    # Interação
    'temp_umidade',

    # Cíclicas
    'hora_sin',
    'hora_cos',
    'mes_sin',
    'mes_cos',
    'hora',
    'mes',

    # Localização física (estacao_id foi removido — ver _climatologia_estacao)
    'latitude',
    'longitude',
    'altitude',

    # Climatologia da estação (calculada só no treino)
    'clima_chuva_media',
    'clima_chuva_p99',
    'clima_chuva_mes',
    'clima_umidade_media',
    'clima_pressao_media',

    # Contexto espacial — estações vizinhas
    'viz_chuva_3h',
    'viz_oeste_chuva_3h',
    'viz_queda_pressao_3h',
]

# Features vindas da Open-Meteo (só entram se ENABLE_OPENMETEO)
# `wind_direction_100m` entra decomposto em componentes (ver create_features):
# direção em graus é descontínua em 0°/360° e o modelo não tem como aprender isso.
FEATURES_OPENMETEO = [
    'cloud_cover_low',
    'cloud_cover_mid',
    'cloud_cover_high',
    'wind_gusts_10m',
    'wind_speed_100m',
    'vento100_norte',
    'vento100_leste',
    'soil_moisture',
    'soil_moisture_profundo',
]

FEATURE_COLUMNS = FEATURES_INMET + (FEATURES_OPENMETEO if ENABLE_OPENMETEO else [])

# ==============================
# RELATÓRIO
# ==============================

# Gráficos (matriz de confusão, feature importance) junto do relatório .md.
# Desligados por padrão: o relatório em texto é o que se lê no dia a dia, e
# gerá-los custa a importação do matplotlib em toda execução do pipeline.
ENABLE_PLOTS = False

# ==============================
# OPTUNA
# ==============================

# Número de trials para busca de hiperparâmetros.
# Mais trials = melhor resultado, mas mais tempo de execução.
# 30 custavam ~1h20 por modelo nesta máquina (2,7 min/trial em 3,7 M linhas).
N_OPTUNA_TRIALS = 10

# ==============================
# LIGHTGBM
# ==============================

# Usados como ponto de partida e fallback se o Optuna for desativado.
LGBM_BASE_PARAMS = {
    "n_estimators": 500,
    "learning_rate": 0.05,
    "num_leaves": 64,
    "subsample": 0.8,
    "colsample_bytree": 0.8,
    "random_state": 42,
    "n_jobs": -1,
    "verbose": -1,
}

# Alvo de regressão tem 59% de zeros. MAE puxa a predição para a mediana
# condicional (zero na maioria das linhas) e subestima os volumes altos, que
# são justamente os que importam. Tweedie é feito para alvos zero-inflados.
REGRESSOR_OBJECTIVE = 'tweedie'
TWEEDIE_VARIANCE_POWER = 1.5
