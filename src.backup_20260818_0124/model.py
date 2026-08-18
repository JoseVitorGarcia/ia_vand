import json
import logging

import joblib
import numpy as np
import optuna

from lightgbm import LGBMClassifier, LGBMRegressor
from sklearn.calibration import CalibratedClassifierCV
from sklearn.metrics import (
    average_precision_score,
    brier_score_loss,
    classification_report,
    confusion_matrix,
    f1_score,
    mean_absolute_error,
    precision_score,
    recall_score,
)
from sklearn.model_selection import TimeSeriesSplit

from src.config import FEATURE_COLUMNS, MODELS_DIR, N_OPTUNA_TRIALS

logger = logging.getLogger(__name__)
optuna.logging.set_verbosity(optuna.logging.WARNING)

N_SPLITS_TUNE = 3
N_SPLITS_EVAL = 5


def find_best_threshold(y_true, probs):
    """Busca o threshold que maximiza F1 no conjunto fornecido."""
    thresholds = np.arange(0.05, 0.96, 0.05)
    best_score, best_threshold = 0.0, 0.5
    for t in thresholds:
        preds = (probs > t).astype(int)
        score = f1_score(y_true, preds, zero_division=0)
        if score > best_score:
            best_score = score
            best_threshold = float(t)
    return best_threshold


def _lgbm_search_space(trial):
    return {
        'num_leaves':        trial.suggest_int('num_leaves', 31, 255),
        'learning_rate':     trial.suggest_float('learning_rate', 0.01, 0.2, log=True),
        'n_estimators':      trial.suggest_int('n_estimators', 200, 600),
        'min_child_samples': trial.suggest_int('min_child_samples', 10, 100),
        'subsample':         trial.suggest_float('subsample', 0.6, 1.0),
        'colsample_bytree':  trial.suggest_float('colsample_bytree', 0.5, 1.0),
        'lambda_l1':         trial.suggest_float('lambda_l1', 1e-8, 10.0, log=True),
        'lambda_l2':         trial.suggest_float('lambda_l2', 1e-8, 10.0, log=True),
        'max_depth':         trial.suggest_int('max_depth', 4, 12),
        'n_jobs': -1,
        'random_state': 42,
        'verbose': -1,
    }


def _progress_callback(study, trial):
    if (trial.number + 1) % 10 == 0 or trial.number == 0:
        logger.info(
            "Optuna trial %d/%d — valor: %.4f | melhor: %.4f",
            trial.number + 1, N_OPTUNA_TRIALS, trial.value, study.best_value,
        )


def _tune_regressor(X, y_reg, splits):
    def objective(trial):
        params = _lgbm_search_space(trial)
        scores = []
        for train_idx, test_idx in splits:
            reg = LGBMRegressor(**params)
            reg.fit(X.iloc[train_idx], y_reg.iloc[train_idx])
            preds = reg.predict(X.iloc[test_idx])
            scores.append(mean_absolute_error(y_reg.iloc[test_idx], preds))
        return float(np.mean(scores))

    study = optuna.create_study(
        direction='minimize',
        sampler=optuna.samplers.TPESampler(seed=42),
    )
    study.optimize(objective, n_trials=N_OPTUNA_TRIALS, callbacks=[_progress_callback])
    return study.best_params, study.best_value


def _tune_classifier(X, y_clf, splits):
    def objective(trial):
        params = _lgbm_search_space(trial)
        scores = []
        for train_idx, test_idx in splits:
            y_tr = y_clf.iloc[train_idx]
            pos = y_tr.sum()
            neg = len(y_tr) - pos
            scale = neg / pos if pos > 0 else 1.0
            clf = LGBMClassifier(scale_pos_weight=scale, **params)
            clf.fit(X.iloc[train_idx], y_tr)
            probs = clf.predict_proba(X.iloc[test_idx])[:, 1]
            thr = find_best_threshold(y_clf.iloc[test_idx], probs)
            preds = (probs > thr).astype(int)
            scores.append(f1_score(y_clf.iloc[test_idx], preds, zero_division=0))
        return float(np.mean(scores))

    study = optuna.create_study(
        direction='maximize',
        sampler=optuna.samplers.TPESampler(seed=42),
    )
    study.optimize(objective, n_trials=N_OPTUNA_TRIALS, callbacks=[_progress_callback])
    return study.best_params, study.best_value


def train_models(df):
    print("Treinando modelos...")

    X = df[FEATURE_COLUMNS].astype(float)

    splits_tune = list(TimeSeriesSplit(n_splits=N_SPLITS_TUNE).split(X))
    splits_eval = list(TimeSeriesSplit(n_splits=N_SPLITS_EVAL).split(X))

    # ─── REGRESSÃO ────────────────────────────────────────────────────────────
    y_reg = df['chuva_futura_24h']

    print(f"\nOtimizando regressao com Optuna ({N_OPTUNA_TRIALS} trials)...")
    best_reg_params, optuna_reg_mae = _tune_regressor(X, y_reg, splits_tune)
    print(f"Melhor MAE (Optuna 3-fold): {optuna_reg_mae:.4f}")

    mae_scores = []
    for train_idx, test_idx in splits_eval:
        reg_cv = LGBMRegressor(**best_reg_params)
        reg_cv.fit(X.iloc[train_idx], y_reg.iloc[train_idx])
        preds_cv = reg_cv.predict(X.iloc[test_idx])
        mae_scores.append(mean_absolute_error(y_reg.iloc[test_idx], preds_cv))

    mae_cv_mean = float(np.mean(mae_scores))
    mae_cv_std = float(np.std(mae_scores))
    print(f"REGRESSAO — MAE CV ({N_SPLITS_EVAL}-fold): {mae_cv_mean:.4f} +/- {mae_cv_std:.4f}")

    train_idx, test_idx = splits_eval[-1]
    X_train, X_test = X.iloc[train_idx], X.iloc[test_idx]
    y_train_reg, y_test_reg = y_reg.iloc[train_idx], y_reg.iloc[test_idx]

    reg = LGBMRegressor(**best_reg_params)
    reg.fit(X_train, y_train_reg)
    mae_final = float(mean_absolute_error(y_test_reg, reg.predict(X_test)))
    print(f"MAE final (ultimo split): {mae_final:.4f}")

    # ─── CLASSIFICAÇÃO ────────────────────────────────────────────────────────
    y_clf = df['evento_extremo']

    print(f"\nOtimizando classificacao com Optuna ({N_OPTUNA_TRIALS} trials)...")
    best_clf_params, optuna_clf_f1 = _tune_classifier(X, y_clf, splits_tune)
    print(f"Melhor F1 (Optuna 3-fold): {optuna_clf_f1:.4f}")

    f1_scores = []
    for train_idx, test_idx in splits_eval:
        y_tr = y_clf.iloc[train_idx]
        pos = y_tr.sum()
        neg = len(y_tr) - pos
        scale = neg / pos if pos > 0 else 1.0
        clf_cv = LGBMClassifier(scale_pos_weight=scale, **best_clf_params)
        clf_cv.fit(X.iloc[train_idx], y_tr)
        probs_cv = clf_cv.predict_proba(X.iloc[test_idx])[:, 1]
        thr_cv = find_best_threshold(y_clf.iloc[test_idx], probs_cv)
        preds_cv = (probs_cv > thr_cv).astype(int)
        f1_scores.append(f1_score(y_clf.iloc[test_idx], preds_cv, zero_division=0))

    f1_cv_mean = float(np.mean(f1_scores))
    f1_cv_std = float(np.std(f1_scores))
    print(f"CLASSIFICACAO — F1 CV ({N_SPLITS_EVAL}-fold): {f1_cv_mean:.4f} +/- {f1_cv_std:.4f}")

    # Modelo final no ultimo split
    train_idx, test_idx = splits_eval[-1]
    X_train, X_test = X.iloc[train_idx], X.iloc[test_idx]
    y_train_clf, y_test_clf = y_clf.iloc[train_idx], y_clf.iloc[test_idx]

    pos = y_train_clf.sum()
    neg = len(y_train_clf) - pos
    scale = neg / pos if pos > 0 else 1.0

    clf = LGBMClassifier(scale_pos_weight=scale, **best_clf_params)
    clf.fit(X_train, y_train_clf)

    # Calibracao isotonica: mapeia probabilidades brutas para probabilidades reais.
    # cv='prefit' indica que o modelo ja foi treinado — apenas aprende o mapeamento.
    clf_cal = CalibratedClassifierCV(clf, method='isotonic', cv='prefit')
    clf_cal.fit(X_test, y_test_clf)

    probs = clf_cal.predict_proba(X_test)[:, 1]
    threshold = find_best_threshold(y_test_clf, probs)
    preds = (probs > threshold).astype(int)

    precision = float(precision_score(y_test_clf, preds, zero_division=0))
    recall    = float(recall_score(y_test_clf, preds, zero_division=0))
    f1        = float(f1_score(y_test_clf, preds, zero_division=0))
    brier     = float(brier_score_loss(y_test_clf, probs))
    pr_auc    = float(average_precision_score(y_test_clf, probs))

    print(f"\n{classification_report(y_test_clf, preds, zero_division=0)}")
    print("Matriz de confusao:")
    print(confusion_matrix(y_test_clf, preds))
    print(f"Brier Score: {brier:.4f}  (quanto menor, melhor calibrado)")
    print(f"PR-AUC:      {pr_auc:.4f}  (area sob curva precisao-recall)")

    importance = sorted(
        zip(FEATURE_COLUMNS, clf.feature_importances_),
        key=lambda x: x[1],
        reverse=True,
    )

    print("\nTOP FEATURES")
    for feat, score in importance[:15]:
        print(f"  {feat}: {score}")

    joblib.dump(reg, MODELS_DIR / "regressor.pkl")
    joblib.dump(clf_cal, MODELS_DIR / "classifier.pkl")

    with open(MODELS_DIR / "threshold.json", "w") as f:
        json.dump({"threshold": threshold}, f)

    print("\nModelos salvos.")

    return reg, clf_cal, {
        "mae":          mae_final,
        "mae_cv_mean":  mae_cv_mean,
        "mae_cv_std":   mae_cv_std,
        "f1_cv_mean":   f1_cv_mean,
        "f1_cv_std":    f1_cv_std,
        "precision":    precision,
        "recall":       recall,
        "f1":           f1,
        "threshold":    threshold,
        "brier":        brier,
        "pr_auc":       pr_auc,
        "best_reg_params": best_reg_params,
        "best_clf_params": best_clf_params,
    }, y_test_clf, preds, importance
