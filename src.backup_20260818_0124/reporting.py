from datetime import datetime

import matplotlib.pyplot as plt

from sklearn.metrics import ConfusionMatrixDisplay

from src.config import REPORTS_DIR


def generate_report(
    analysis_results,
    model_results,
    y_test=None,
    y_pred=None,
    feature_importance=None,
):
    timestamp = datetime.now().strftime("%Y_%m_%d_%H_%M")
    report_path = REPORTS_DIR / f"report_{timestamp}.md"

    md = []
    md.append("# IA_VAND — Relatório Automático\n")

    md.append("## Dataset\n")
    md.append(f"- Registros: {analysis_results['shape'][0]:,}\n")
    md.append(f"- Features: {analysis_results['shape'][1]:,}\n")
    md.append(f"- Eventos extremos: {analysis_results['event_ratio']:.2%}\n")
    md.append(f"- Sparsidade: {analysis_results['zero_ratio']:.2%}\n")

    md.append("\n---\n")
    md.append("## Regressão\n")
    md.append(f"- MAE (último split): {model_results['mae']:.4f} mm\n")
    md.append(
        f"- MAE CV (5-fold): {model_results['mae_cv_mean']:.4f} ± {model_results['mae_cv_std']:.4f} mm\n"
    )
    md.append("""
### Interpretação

MAE representa o erro médio absoluto na previsão de chuva acumulada em 24h.
O valor CV (média ± desvio entre os 5 folds) é o indicador mais confiável —
reflete a variabilidade temporal do desempenho.
""")

    md.append("\n---\n")
    md.append("## Classificação\n")
    md.append(f"- Precision: {model_results['precision']:.4f}\n")
    md.append(f"- Recall:    {model_results['recall']:.4f}\n")
    md.append(f"- F1-score:  {model_results['f1']:.4f}\n")
    md.append(
        f"- F1 CV (5-fold): {model_results['f1_cv_mean']:.4f} ± {model_results['f1_cv_std']:.4f}\n"
    )
    md.append(f"- Threshold ótimo: {model_results['threshold']:.2f}\n")
    if 'brier' in model_results:
        md.append(f"- Brier Score: {model_results['brier']:.4f}\n")
    if 'pr_auc' in model_results:
        md.append(f"- PR-AUC: {model_results['pr_auc']:.4f}\n")
    md.append("""
### Interpretação

- **Precision**: fração dos alertas que eram eventos reais.
- **Recall**: fração dos eventos reais que foram detectados.
- **F1**: equilíbrio entre precision e recall.
- **F1 CV**: estimativa honesta por validação cruzada temporal (5 splits).
- **Brier Score**: qualidade da calibração probabilística (menor = melhor; 0 = perfeito).
- **PR-AUC**: área sob a curva Precisão-Recall (mais informativo que ROC-AUC em datasets desbalanceados).
""")

    md.append("\n---\n")
    md.append("## Top Features\n")
    if feature_importance:
        for feat, score in feature_importance[:15]:
            md.append(f"- {feat}: {score}\n")

    md.append("\n---\n")
    md.append("## Insights Automáticos\n")
    for insight in analysis_results.get("insights", []):
        md.append(f"- {insight}\n")

    with open(report_path, "w", encoding="utf-8") as f:
        f.write("\n".join(md))

    print(f"Relatório salvo em: {report_path}")

    if y_test is not None and y_pred is not None:
        fig, ax = plt.subplots(figsize=(6, 6))
        ConfusionMatrixDisplay.from_predictions(y_test, y_pred, ax=ax)
        cm_path = REPORTS_DIR / "confusion_matrix.png"
        plt.savefig(cm_path, bbox_inches="tight")
        plt.close()
        print(f"Confusion matrix: {cm_path}")

    if feature_importance:
        top = feature_importance[:15]
        names = [x[0] for x in top]
        values = [x[1] for x in top]

        plt.figure(figsize=(10, 6))
        plt.barh(names[::-1], values[::-1])
        plt.xlabel("Importance")
        plt.title("Feature Importance")
        fi_path = REPORTS_DIR / "feature_importance.png"
        plt.savefig(fi_path, bbox_inches="tight")
        plt.close()
        print(f"Feature importance: {fi_path}")
