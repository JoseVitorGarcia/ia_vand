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
# OPEN-METEO
# ==============================

OPENMETEO_CACHE_DIR = CACHE_DIR / 'openmeteo'
OPENMETEO_CACHE_DIR.mkdir(exist_ok=True)

# TTL em horas para o cache da previsão (forecast)
OPENMETEO_FORECAST_TTL_HOURS = 1

# Delay em segundos entre requisições históricas para respeitar o rate limit.
# A API gratuita limita ~600 req/min mas o burst de 71 estações x 10 anos
# dispara 429 sem esse intervalo. 1s garante ~60 req/min — bem abaixo do limite.
OPENMETEO_REQUEST_DELAY = 1.0

# Variáveis que complementam o INMET sem duplicar (não inclui precipitação,
# temperatura, umidade, pressão e vento, que o INMET já fornece).
OPENMETEO_HISTORICAL_VARS = [
    'cape',                   # Energia convectiva disponível (J/kg)
    'cloud_cover',            # Cobertura de nuvens total (%)
    'wind_gusts_10m',         # Rajadas de vento (m/s) — INMET fornece média
    'soil_moisture_0_to_7cm', # Umidade do solo superficial (m³/m³)
    'freezing_level_height',  # Altura da isoterma 0°C (m)
]

OPENMETEO_FORECAST_VARS = [
    'cape',
    'cloud_cover',
    'wind_gusts_10m',
    'soil_moisture_0_to_7cm',
    'freezing_level_height',
    'precipitation_probability',  # disponível apenas em forecast
]

# Ativa enriquecimento com Open-Meteo no pipeline de treino
ENABLE_OPENMETEO = True

# ==============================
# FEATURES
# ==============================

FEATURE_COLUMNS = [
    # Observações INMET
    'precipitacao',
    'temperatura',
    'umidade',
    'pressao',
    'vento',

    # Lags temporais (lookback)
    'lag_1h',
    'lag_3h',
    'lag_6h',
    'lag_24h',

    # Acumulados (lookback)
    'chuva_6h',
    'chuva_12h',
    'chuva_24h',
    'chuva_48h',

    # Volatilidade
    'rolling_std_24h',
    'rolling_max_24h',

    # Tendências
    'tendencia_6h',
    'queda_pressao_3h',

    # Interação
    'temp_umidade',

    # Cíclicas
    'hora_sin',
    'hora_cos',
    'mes_sin',
    'mes_cos',
    'hora',
    'mes',

    # Localização
    'latitude',
    'longitude',
    'estacao_id',

    # Open-Meteo (atmosfera e solo)
    'cape',
    'cloud_cover',
    'wind_gusts_10m',
    'soil_moisture',
    'freezing_level',
]

# ==============================
# OPTUNA
# ==============================

# Número de trials para busca de hiperparâmetros.
# Mais trials = melhor resultado, mas mais tempo de execução.
# 30 trials × 3 folds ≈ 20-40 min por modelo.
N_OPTUNA_TRIALS = 30

# ==============================
# LIGHTGBM
# ==============================

LGBM_REGRESSOR_PARAMS = {
    "n_estimators": 500,
    "learning_rate": 0.05,
    "num_leaves": 64,
    "subsample": 0.8,
    "colsample_bytree": 0.8,
    "random_state": 42,
    "n_jobs": -1,
}

LGBM_CLASSIFIER_PARAMS = {
    "n_estimators": 500,
    "learning_rate": 0.05,
    "num_leaves": 64,
    "subsample": 0.8,
    "colsample_bytree": 0.8,
    "random_state": 42,
    "n_jobs": -1,
}
