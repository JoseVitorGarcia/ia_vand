"""
Módulo de inferência.

Uso básico (apenas features INMET):
    from src.predict import predict
    resultado = predict(features_dict)

Uso com enriquecimento automático Open-Meteo (recomendado):
    resultado = predict(features_dict, lat=-30.05, lon=-51.17)
"""

import json
import logging

import joblib
import numpy as np
import pandas as pd

from src.config import FEATURE_COLUMNS, MODELS_DIR

logger = logging.getLogger(__name__)

_reg = None
_clf = None
_threshold = 0.5


def _load_models():
    global _reg, _clf, _threshold

    if _reg is not None:
        return

    reg_path = MODELS_DIR / "regressor.pkl"
    clf_path = MODELS_DIR / "classifier.pkl"
    thr_path = MODELS_DIR / "threshold.json"

    if not reg_path.exists() or not clf_path.exists():
        raise FileNotFoundError(
            "Modelos não encontrados. Execute 'python main.py' para treinar primeiro."
        )

    _reg = joblib.load(reg_path)
    _clf = joblib.load(clf_path)

    if thr_path.exists():
        with open(thr_path) as f:
            _threshold = json.load(f).get("threshold", 0.5)

    logger.info("Modelos carregados (threshold=%.2f)", _threshold)


def _enrich_with_forecast(data: dict, lat: float, lon: float) -> dict:
    """Adiciona médias das próximas 24h do Open-Meteo ao dicionário de features."""
    try:
        from src.openmeteo_client import fetch_forecast
        forecast = fetch_forecast(lat, lon)

        if forecast.empty:
            return data

        next_24h = forecast.head(24)

        data['cape'] = float(next_24h['cape'].mean()) if 'cape' in next_24h else np.nan
        data['cloud_cover'] = float(next_24h['cloud_cover'].mean()) if 'cloud_cover' in next_24h else np.nan
        data['wind_gusts_10m'] = float(next_24h['wind_gusts_10m'].mean()) if 'wind_gusts_10m' in next_24h else np.nan
        data['soil_moisture'] = float(next_24h['soil_moisture'].mean()) if 'soil_moisture' in next_24h else np.nan
        data['freezing_level'] = float(next_24h['freezing_level'].mean()) if 'freezing_level' in next_24h else np.nan

    except Exception as exc:
        logger.warning("Open-Meteo forecast indisponível: %s — usando NaN", exc)

    return data


def predict(data: dict, lat: float = None, lon: float = None) -> dict:
    """
    Prevê a chuva acumulada nas próximas 24h e o risco de evento extremo.

    Args:
        data: dicionário com as features base (observações INMET processadas).
        lat:  latitude da estação. Se fornecida junto com lon, enriquece
              automaticamente com a previsão Open-Meteo.
        lon:  longitude da estação.

    Returns:
        {
            "chuva_24h_prevista":   float (mm),
            "risco_evento_extremo": float (probabilidade 0–1),
            "alerta":               bool  (True se probabilidade > threshold)
        }
    """
    _load_models()

    data = dict(data)

    if lat is not None and lon is not None:
        data = _enrich_with_forecast(data, lat, lon)

    # Preenche features ausentes com NaN (LightGBM lida nativamente)
    missing = [col for col in FEATURE_COLUMNS if col not in data]
    if missing:
        logger.warning("Features ausentes (serão NaN): %s", missing)
        for col in missing:
            data[col] = np.nan

    df_input = pd.DataFrame([data])
    X = df_input[FEATURE_COLUMNS].astype(float)

    chuva = float(_reg.predict(X)[0])
    risco = float(_clf.predict_proba(X)[0][1])
    alerta = risco > _threshold

    return {
        "chuva_24h_prevista": round(chuva, 2),
        "risco_evento_extremo": round(risco, 4),
        "alerta": alerta,
    }
