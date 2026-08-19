"""
Módulo de inferência.

Uso básico (apenas features INMET):
    from src.predict import predict
    resultado = predict(features_dict)

Uso com enriquecimento automático Open-Meteo:
    resultado = predict(features_dict, lat=-30.05, lon=-51.17)

SOBRE O DESCASAMENTO TREINO/INFERÊNCIA (F-05) — MEDIDO EM 19/08/2026:
    O aviso original dizia que as features Open-Meteo significam coisas
    diferentes no treino e aqui — no treino `soil_moisture` é o valor ERA5 na
    hora t, aqui é a média das próximas 24 h da previsão — e que por isso o
    enriquecimento ficava desligado por padrão.

    A medição desfez o receio, e na direção oposta à esperada. No enquadramento
    operacional (um alerta por estação-dia, emitido às 12 UTC), a configuração
    desta inferência — previsão + janela t+1..t+24 — dá PR-AUC 0,1085 contra
    0,0787 da configuração de treino. **38% melhor, não pior.** Alinhar a janela
    é o efeito dominante: prever chuva de t+1 a t+24 pede a atmosfera ao longo
    dessa janela, não o retrato instantâneo em t. Ver
    `reports/degradacao_mos_2026_08_19_10_50.md`.

    Duas ressalvas antes de religar por padrão:
    1. O THRESHOLD NÃO TRANSFERE. O corte de models/threshold.json foi calibrado
       na distribuição do treino; com as features desta janela as probabilidades
       deslocam para baixo e o recall por estação-dia cai de 0,36 para 0,10.
       Recalibrar na validação, com esta mesma construção, é pré-requisito.
    2. A medição usou previsão arquivada, cujo valor em cada hora vem da rodada
       mais recente antes daquela hora — não de uma única rodada emitida no
       momento da decisão. É um limite inferior da degradação real.

    Até que (1) esteja feito, o enriquecimento continua só sob pedido explícito.
"""

import json
import logging

import joblib
import numpy as np
import pandas as pd

from src.config import FEATURE_COLUMNS, MODELS_DIR, OPENMETEO_COLUNAS

logger = logging.getLogger(__name__)

_reg = None
_clf = None
_threshold = 0.5
_feature_columns = None


def _load_models():
    global _reg, _clf, _threshold, _feature_columns

    if _reg is not None:
        return

    reg_path = MODELS_DIR / "regressor.pkl"
    clf_path = MODELS_DIR / "classifier.pkl"

    if not reg_path.exists() or not clf_path.exists():
        raise FileNotFoundError(
            "Modelos não encontrados. Execute 'python main.py' para treinar primeiro."
        )

    _reg = joblib.load(reg_path)
    _clf = joblib.load(clf_path)

    # O metadata gravado no treino é a fonte da verdade para threshold e ordem
    # das colunas — usar FEATURE_COLUMNS do config arrisca divergir do modelo
    # salvo se a config mudar depois do treino.
    meta_path = MODELS_DIR / "metadata.json"
    if meta_path.exists():
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        _threshold = meta.get("threshold", 0.5)
        _feature_columns = meta.get("feature_columns", FEATURE_COLUMNS)
    else:
        thr_path = MODELS_DIR / "threshold.json"
        if thr_path.exists():
            _threshold = json.loads(thr_path.read_text(encoding="utf-8")).get("threshold", 0.5)
        _feature_columns = FEATURE_COLUMNS
        logger.warning("metadata.json ausente — usando FEATURE_COLUMNS do config")

    logger.info("Modelos carregados (threshold=%.3f, %d features)",
                _threshold, len(_feature_columns))


def _enrich_with_forecast(data: dict, lat: float, lon: float) -> dict:
    """Adiciona médias das próximas 24 h do Open-Meteo ao dicionário de features.

    Ver o aviso no topo do módulo: enquanto o treino usar o valor em t, esta
    agregação diverge do que o modelo aprendeu.
    """
    try:
        from src.openmeteo_client import fetch_forecast
        forecast = fetch_forecast(lat, lon)

        if forecast.empty:
            return data

        next_24h = forecast.head(24)
        for col in OPENMETEO_COLUNAS:
            if col in next_24h:
                data[col] = float(next_24h[col].mean())

    except Exception as exc:
        logger.warning("Open-Meteo forecast indisponível: %s — usando NaN", exc)

    return data


def predict(data: dict, lat: float = None, lon: float = None,
            usar_forecast: bool = False) -> dict:
    """
    Prevê a chuva acumulada nas próximas 24 h e o risco de evento extremo.

    Args:
        data: dicionário com as features (observações INMET já processadas).
        lat, lon: coordenadas da estação, necessárias se usar_forecast=True.
        usar_forecast: enriquece com Open-Meteo. Desativado por padrão — ver
            o aviso no topo do módulo sobre divergência entre treino e inferência.

    Returns:
        {
            "chuva_24h_prevista":   float (mm),
            "risco_evento_extremo": float (probabilidade 0–1),
            "alerta":               bool,
            "threshold":            float
        }
    """
    _load_models()

    data = dict(data)

    if usar_forecast:
        if lat is None or lon is None:
            raise ValueError("usar_forecast=True exige lat e lon")
        data = _enrich_with_forecast(data, lat, lon)

    ausentes = [col for col in _feature_columns if col not in data]
    if ausentes:
        logger.warning("Features ausentes (serão NaN): %s", ausentes)
        for col in ausentes:
            data[col] = np.nan

    X = pd.DataFrame([data])[_feature_columns].astype('float32')

    chuva = float(_reg.predict(X)[0])
    risco = float(_clf.predict_proba(X)[0][1])

    return {
        "chuva_24h_prevista": round(max(chuva, 0.0), 2),
        "risco_evento_extremo": round(risco, 4),
        "alerta": bool(risco > _threshold),
        "threshold": _threshold,
    }
