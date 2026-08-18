"""
Treinamento com protocolo de validação temporal.

Desenho das janelas:

    treino ───────────────► [embargo] ─► validação ─► [embargo] ─► TESTE
    2015 .......... 2024      24 h        2025          24 h      set/25→

  - treino:    ajusta o modelo; o Optuna roda um TimeSeriesSplit aqui dentro
  - validação: calibra as probabilidades e escolhe o threshold
  - teste:     só mede, nunca é visto por nenhuma decisão de ajuste

O embargo existe porque o alvo é a soma de chuva de t+1 a t+24: sem ele, as
últimas linhas de treino carregam informação das primeiras horas da validação.
"""

import json
import logging

import joblib
import numpy as np
import optuna
import pandas as pd

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

from src.config import (
    EMBARGO_HORAS,
    EXTREME_RAIN_THRESHOLD,
    FEATURE_COLUMNS,
    MODELS_DIR,
    N_OPTUNA_TRIALS,
    N_SPLITS_EVAL,
    N_SPLITS_TUNE,
    REGRESSOR_OBJECTIVE,
    TRAIN_END,
    TWEEDIE_VARIANCE_POWER,
    VALID_END,
)

logger = logging.getLogger(__name__)
optuna.logging.set_verbosity(optuna.logging.WARNING)

_GRID_THRESHOLD = np.arange(0.02, 0.99, 0.02)


def find_best_threshold(y_true, probs):
    """Busca o threshold que maximiza F1 no conjunto fornecido.

    Deve ser chamada apenas na janela de validação — usá-la no teste
    escolhe o corte que favorece o próprio resultado que se quer medir.
    """
    melhor_score, melhor_threshold = 0.0, 0.5
    for t in _GRID_THRESHOLD:
        score = f1_score(y_true, (probs > t).astype(int), zero_division=0)
        if score > melhor_score:
            melhor_score, melhor_threshold = score, float(t)
    return melhor_threshold


def separar_janelas(df):
    """Divide o DataFrame em treino / validação / teste por data, com embargo.

    Devolve três máscaras booleanas alinhadas ao índice de df.
    """
    if not df['data_hora'].is_monotonic_increasing:
        raise ValueError(
            "df precisa estar ordenado por data_hora — sem isso o TimeSeriesSplit "
            "separa estações em vez de períodos."
        )

    embargo = pd.Timedelta(hours=EMBARGO_HORAS)
    t = df['data_hora']

    treino = t <= TRAIN_END - embargo
    validacao = (t > TRAIN_END) & (t <= VALID_END)
    teste = t > VALID_END + embargo

    for nome, mask in [('treino', treino), ('validação', validacao), ('teste', teste)]:
        if not mask.any():
            raise ValueError(f"Janela de {nome} vazia — revise TRAIN_END/VALID_END em config.py")
        logger.info(
            "%-10s %s → %s | %d linhas | %.2f%% eventos",
            nome, t[mask].min().date(), t[mask].max().date(),
            int(mask.sum()), 100 * df.loc[mask, 'evento_extremo'].mean(),
        )

    return treino, validacao, teste


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
    # Cadência proporcional: com poucos trials, log a cada 10 daria só a primeira
    # e a última linha, deixando a execução muda por dezenas de minutos.
    passo = max(1, N_OPTUNA_TRIALS // 5)
    if (trial.number + 1) % passo == 0 or trial.number == 0:
        logger.info(
            "Optuna trial %d/%d — valor: %.4f | melhor: %.4f",
            trial.number + 1, N_OPTUNA_TRIALS, trial.value, study.best_value,
        )


def _splits_com_embargo(datas, n_splits):
    """TimeSeriesSplit descontando as linhas do embargo no fim de cada treino.

    Só é válido sobre dados ordenados no tempo; separar_janelas já garante isso.
    """
    embargo = pd.Timedelta(hours=EMBARGO_HORAS)
    splits = []
    for treino_idx, teste_idx in TimeSeriesSplit(n_splits=n_splits).split(datas):
        limite = datas.iloc[teste_idx[0]] - embargo
        treino_idx = treino_idx[datas.iloc[treino_idx].to_numpy() <= limite]
        if len(treino_idx) == 0:
            continue
        splits.append((treino_idx, teste_idx))
    return splits


def _escala_positivos(y):
    pos = int(y.sum())
    return (len(y) - pos) / pos if pos > 0 else 1.0


def _tune_regressor(X, y, splits):
    def objective(trial):
        params = _lgbm_search_space(trial)
        scores = []
        for tr, te in splits:
            reg = LGBMRegressor(
                objective=REGRESSOR_OBJECTIVE,
                tweedie_variance_power=TWEEDIE_VARIANCE_POWER,
                **params,
            )
            reg.fit(X.iloc[tr], y.iloc[tr])
            scores.append(mean_absolute_error(y.iloc[te], reg.predict(X.iloc[te])))
        return float(np.mean(scores))

    study = optuna.create_study(
        direction='minimize', sampler=optuna.samplers.TPESampler(seed=42),
    )
    study.optimize(objective, n_trials=N_OPTUNA_TRIALS, callbacks=[_progress_callback])
    return study.best_params, study.best_value


def _tune_classifier(X, y, splits):
    def objective(trial):
        params = _lgbm_search_space(trial)
        scores = []
        for tr, te in splits:
            clf = LGBMClassifier(scale_pos_weight=_escala_positivos(y.iloc[tr]), **params)
            clf.fit(X.iloc[tr], y.iloc[tr])
            probs = clf.predict_proba(X.iloc[te])[:, 1]
            # PR-AUC não depende de threshold, então não há como inflar o
            # objetivo escolhendo o corte no próprio fold de avaliação.
            scores.append(average_precision_score(y.iloc[te], probs))
        return float(np.mean(scores))

    study = optuna.create_study(
        direction='maximize', sampler=optuna.samplers.TPESampler(seed=42),
    )
    study.optimize(objective, n_trials=N_OPTUNA_TRIALS, callbacks=[_progress_callback])
    return study.best_params, study.best_value


def avaliar_por_estacao_dia(df_teste, probs, y_true, threshold):
    """Agrega a avaliação para a unidade em que um alerta é de fato emitido.

    O alvo é uma janela deslizante: uma única tempestade gera ~19 linhas
    positivas quase idênticas. Medir por linha trata 83 mil amostras onde há
    ~4 mil eventos independentes, e infla a confiança nas barras de erro.
    """
    agregado = (
        pd.DataFrame({
            'estacao_codigo': df_teste['estacao_codigo'].to_numpy(),
            'dia': df_teste['data_hora'].dt.date.to_numpy(),
            'y': y_true.to_numpy(),
            'p': probs,
        })
        .groupby(['estacao_codigo', 'dia'])
        .agg(y=('y', 'max'), p=('p', 'max'))
    )
    preds = (agregado['p'] > threshold).astype(int)
    return {
        'f1':        float(f1_score(agregado['y'], preds, zero_division=0)),
        'precision': float(precision_score(agregado['y'], preds, zero_division=0)),
        'recall':    float(recall_score(agregado['y'], preds, zero_division=0)),
        'pr_auc':    float(average_precision_score(agregado['y'], agregado['p'])),
        'n':         int(len(agregado)),
        'eventos':   int(agregado['y'].sum()),
    }


def calcular_baselines(df_treino, df_teste, y_teste):
    """Réguas de comparação honestas para o classificador.

    A climatologia (taxa base constante) é a régua trivial. A persistência —
    prever pelo que já choveu nas últimas 24 h — é a que um meteorologista
    usaria de graça, e é contra ela que o ganho do modelo deve ser lido.
    """
    return {
        'climatologia_pr_auc': float(
            average_precision_score(y_teste, np.full(len(y_teste), df_treino['evento_extremo'].mean()))
        ),
        'persistencia_pr_auc': float(
            average_precision_score(y_teste, df_teste['chuva_24h'].to_numpy())
        ),
    }


def train_models(df):
    logger.info("Treinando modelos...")

    treino, validacao, teste = separar_janelas(df)

    X = df[FEATURE_COLUMNS].astype('float32')
    y_reg = df['chuva_futura_24h']
    y_clf = df['evento_extremo']

    X_tr, X_va, X_te = X[treino], X[validacao], X[teste]
    datas_treino = df.loc[treino, 'data_hora'].reset_index(drop=True)

    splits_tune = _splits_com_embargo(datas_treino, N_SPLITS_TUNE)
    splits_eval = _splits_com_embargo(datas_treino, N_SPLITS_EVAL)

    X_tr_ri = X_tr.reset_index(drop=True)

    # ─── REGRESSÃO ────────────────────────────────────────────────────────────
    y_reg_tr = y_reg[treino].reset_index(drop=True)

    logger.info("Otimizando regressão com Optuna (%d trials)...", N_OPTUNA_TRIALS)
    best_reg_params, optuna_reg_mae = _tune_regressor(X_tr_ri, y_reg_tr, splits_tune)
    logger.info("Melhor MAE (Optuna %d-fold): %.4f", N_SPLITS_TUNE, optuna_reg_mae)

    mae_scores = []
    for tr, te in splits_eval:
        reg_cv = LGBMRegressor(
            objective=REGRESSOR_OBJECTIVE,
            tweedie_variance_power=TWEEDIE_VARIANCE_POWER,
            **best_reg_params,
        )
        reg_cv.fit(X_tr_ri.iloc[tr], y_reg_tr.iloc[tr])
        mae_scores.append(mean_absolute_error(y_reg_tr.iloc[te], reg_cv.predict(X_tr_ri.iloc[te])))

    mae_cv_mean, mae_cv_std = float(np.mean(mae_scores)), float(np.std(mae_scores))
    logger.info("REGRESSÃO — MAE CV (%d-fold no treino): %.4f ± %.4f",
                N_SPLITS_EVAL, mae_cv_mean, mae_cv_std)

    reg = LGBMRegressor(
        objective=REGRESSOR_OBJECTIVE,
        tweedie_variance_power=TWEEDIE_VARIANCE_POWER,
        **best_reg_params,
    )
    reg.fit(X_tr, y_reg[treino])

    pred_teste = reg.predict(X_te)
    mae_final = float(mean_absolute_error(y_reg[teste], pred_teste))

    # MAE global é dominado pelos 59% de linhas sem chuva; o erro condicionado
    # aos casos com chuva relevante diz muito mais sobre utilidade operacional.
    com_chuva = y_reg[teste] > 1.0
    mae_com_chuva = float(
        mean_absolute_error(y_reg[teste][com_chuva], pred_teste[com_chuva])
    ) if com_chuva.any() else float('nan')

    logger.info("MAE no teste: %.4f mm | condicionado a chuva > 1 mm: %.4f mm",
                mae_final, mae_com_chuva)

    # ─── CLASSIFICAÇÃO ────────────────────────────────────────────────────────
    y_clf_tr = y_clf[treino].reset_index(drop=True)

    logger.info("Otimizando classificação com Optuna (%d trials)...", N_OPTUNA_TRIALS)
    best_clf_params, optuna_clf_ap = _tune_classifier(X_tr_ri, y_clf_tr, splits_tune)
    logger.info("Melhor PR-AUC (Optuna %d-fold): %.4f", N_SPLITS_TUNE, optuna_clf_ap)

    pr_auc_scores, f1_scores = [], []
    for tr, te in splits_eval:
        clf_cv = LGBMClassifier(
            scale_pos_weight=_escala_positivos(y_clf_tr.iloc[tr]), **best_clf_params,
        )
        clf_cv.fit(X_tr_ri.iloc[tr], y_clf_tr.iloc[tr])
        probs_cv = clf_cv.predict_proba(X_tr_ri.iloc[te])[:, 1]
        pr_auc_scores.append(average_precision_score(y_clf_tr.iloc[te], probs_cv))
        # Threshold do fold anterior seria mais rigoroso, mas aqui serve só como
        # indicador de dispersão entre folds — o número que vale é o do teste.
        thr_cv = find_best_threshold(y_clf_tr.iloc[te], probs_cv)
        f1_scores.append(f1_score(y_clf_tr.iloc[te], (probs_cv > thr_cv).astype(int), zero_division=0))

    pr_auc_cv_mean, pr_auc_cv_std = float(np.mean(pr_auc_scores)), float(np.std(pr_auc_scores))
    f1_cv_mean, f1_cv_std = float(np.mean(f1_scores)), float(np.std(f1_scores))
    logger.info("CLASSIFICAÇÃO — PR-AUC CV (%d-fold no treino): %.4f ± %.4f",
                N_SPLITS_EVAL, pr_auc_cv_mean, pr_auc_cv_std)

    clf = LGBMClassifier(
        scale_pos_weight=_escala_positivos(y_clf[treino]), **best_clf_params,
    )
    clf.fit(X_tr, y_clf[treino])

    # Calibração e threshold saem da VALIDAÇÃO, nunca do teste. A versão
    # anterior ajustava ambos em X_test e media no mesmo X_test.
    clf_cal = CalibratedClassifierCV(clf, method='isotonic', cv='prefit')
    clf_cal.fit(X_va, y_clf[validacao])

    probs_va = clf_cal.predict_proba(X_va)[:, 1]
    threshold = find_best_threshold(y_clf[validacao], probs_va)
    logger.info("Threshold escolhido na validação: %.3f", threshold)

    # ─── AVALIAÇÃO FINAL (teste intocado) ─────────────────────────────────────
    y_te = y_clf[teste]
    probs = clf_cal.predict_proba(X_te)[:, 1]
    preds = (probs > threshold).astype(int)

    precision = float(precision_score(y_te, preds, zero_division=0))
    recall    = float(recall_score(y_te, preds, zero_division=0))
    f1        = float(f1_score(y_te, preds, zero_division=0))
    brier     = float(brier_score_loss(y_te, probs))
    pr_auc    = float(average_precision_score(y_te, probs))

    por_dia = avaliar_por_estacao_dia(df[teste], probs, y_te, threshold)
    baselines = calcular_baselines(df[treino], df[teste], y_te)

    logger.info("\n%s", classification_report(y_te, preds, zero_division=0))
    logger.info("Matriz de confusão:\n%s", confusion_matrix(y_te, preds))
    logger.info("TESTE por linha       — F1 %.4f | P %.4f | R %.4f | PR-AUC %.4f | Brier %.4f",
                f1, precision, recall, pr_auc, brier)
    logger.info("TESTE por estação-dia — F1 %.4f | P %.4f | R %.4f | PR-AUC %.4f (%d eventos em %d dias-estação)",
                por_dia['f1'], por_dia['precision'], por_dia['recall'], por_dia['pr_auc'],
                por_dia['eventos'], por_dia['n'])
    logger.info("Baselines PR-AUC      — persistência %.4f | climatologia %.4f",
                baselines['persistencia_pr_auc'], baselines['climatologia_pr_auc'])
    logger.info("Ganho sobre persistência: %+.1f%%",
                100 * (pr_auc / baselines['persistencia_pr_auc'] - 1))

    importance = sorted(
        zip(FEATURE_COLUMNS, clf.feature_importances_),
        key=lambda x: x[1], reverse=True,
    )
    logger.info("TOP FEATURES: %s", ', '.join(f"{f}({s})" for f, s in importance[:10]))

    joblib.dump(reg, MODELS_DIR / "regressor.pkl")
    joblib.dump(clf_cal, MODELS_DIR / "classifier.pkl")

    # O predict precisa reconstruir exatamente as mesmas colunas, na mesma ordem
    with open(MODELS_DIR / "metadata.json", "w", encoding="utf-8") as f:
        json.dump({
            "threshold": threshold,
            "feature_columns": FEATURE_COLUMNS,
            "extreme_rain_threshold": EXTREME_RAIN_THRESHOLD,
            "train_end": str(TRAIN_END),
            "valid_end": str(VALID_END),
        }, f, indent=2)

    # Mantido por compatibilidade com versões anteriores do predict
    with open(MODELS_DIR / "threshold.json", "w", encoding="utf-8") as f:
        json.dump({"threshold": threshold}, f)

    logger.info("Modelos salvos em %s", MODELS_DIR)

    resultados = {
        "mae":              mae_final,
        "mae_com_chuva":    mae_com_chuva,
        "mae_cv_mean":      mae_cv_mean,
        "mae_cv_std":       mae_cv_std,
        "f1_cv_mean":       f1_cv_mean,
        "f1_cv_std":        f1_cv_std,
        "pr_auc_cv_mean":   pr_auc_cv_mean,
        "pr_auc_cv_std":    pr_auc_cv_std,
        "precision":        precision,
        "recall":           recall,
        "f1":               f1,
        "threshold":        threshold,
        "brier":            brier,
        "pr_auc":           pr_auc,
        "por_estacao_dia":  por_dia,
        "baselines":        baselines,
        "n_treino":         int(treino.sum()),
        "n_validacao":      int(validacao.sum()),
        "n_teste":          int(teste.sum()),
        "periodo_teste":    f"{df.loc[teste, 'data_hora'].min().date()} a {df.loc[teste, 'data_hora'].max().date()}",
        "best_reg_params":  best_reg_params,
        "best_clf_params":  best_clf_params,
    }

    return reg, clf_cal, resultados, y_te, preds, importance
