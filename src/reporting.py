import logging

from datetime import datetime

from src.config import ENABLE_PLOTS, N_SPLITS_EVAL, REPORTS_DIR

logger = logging.getLogger(__name__)


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
    ad = md.append

    ad("# IA_VAND — Relatório Automático\n")
    ad(f"Gerado em {datetime.now().strftime('%d/%m/%Y %H:%M')}\n")

    # ── Dataset ───────────────────────────────────────────────────────────────
    ad("\n## Dataset\n")
    ad(f"- Registros: {analysis_results['shape'][0]:,}")
    ad(f"- Colunas: {analysis_results['shape'][1]:,}")
    ad(f"- Estações: {analysis_results.get('n_estacoes', 'n/d')}")
    if 'periodo' in analysis_results:
        ad(f"- Período: {analysis_results['periodo'][0]} a {analysis_results['periodo'][1]}")
    ad(f"- Eventos extremos: {analysis_results['event_ratio']:.2%}")
    ad(f"- Esparsidade (horas sem chuva): {analysis_results['zero_ratio']:.2%}")
    if analysis_results.get('n_episodios'):
        ad(f"- Linhas positivas: {analysis_results['n_positivas']:,} "
           f"→ {analysis_results['n_episodios']:,} episódios independentes")

    # ── Protocolo ─────────────────────────────────────────────────────────────
    ad("\n---\n")
    ad("## Protocolo de validação\n")
    ad(f"- Treino: {model_results['n_treino']:,} linhas")
    ad(f"- Validação (calibração + threshold): {model_results['n_validacao']:,} linhas")
    ad(f"- Teste (intocado): {model_results['n_teste']:,} linhas — {model_results['periodo_teste']}")
    ad("""
As três janelas são separadas por data, com embargo de 24 h entre elas — sem o
embargo, o alvo das últimas linhas de treino (soma de chuva de t+1 a t+24)
carregaria informação das primeiras horas da janela seguinte. A calibração
isotônica e o threshold saem da validação; o teste só mede.
""")

    # ── Regressão ─────────────────────────────────────────────────────────────
    ad("\n---\n")
    ad("## Regressão — chuva acumulada em 24 h\n")
    ad(f"- MAE no teste: {model_results['mae']:.4f} mm")
    if model_results.get('mae_com_chuva') == model_results.get('mae_com_chuva'):  # não-NaN
        ad(f"- MAE condicionado a chuva > 1 mm: {model_results['mae_com_chuva']:.4f} mm")
    ad(f"- MAE CV ({N_SPLITS_EVAL}-fold no treino): "
       f"{model_results['mae_cv_mean']:.4f} ± {model_results['mae_cv_std']:.4f} mm")
    ad("""
### Interpretação

O MAE global é dominado pelas linhas sem chuva, que são a maioria do alvo. O MAE
condicionado a eventos com chuva mede o que de fato importa operacionalmente —
acertar o volume quando chove. O objetivo de treino é Tweedie, apropriado para
alvos contínuos com excesso de zeros.
""")

    # ── Classificação ─────────────────────────────────────────────────────────
    ad("\n---\n")
    ad("## Classificação — risco de evento extremo\n")

    dia = model_results.get('por_estacao_dia', {})
    base = model_results.get('baselines', {})

    ad("| Métrica | Por linha horária | Por estação-dia |")
    ad("|---|---|---|")
    ad(f"| F1 | {model_results['f1']:.4f} | {dia.get('f1', float('nan')):.4f} |")
    ad(f"| Precisão | {model_results['precision']:.4f} | {dia.get('precision', float('nan')):.4f} |")
    ad(f"| Recall | {model_results['recall']:.4f} | {dia.get('recall', float('nan')):.4f} |")
    ad(f"| PR-AUC | {model_results['pr_auc']:.4f} | {dia.get('pr_auc', float('nan')):.4f} |")
    ad("")
    ad(f"- Threshold (escolhido na validação): {model_results['threshold']:.3f}")
    ad(f"- Brier Score: {model_results['brier']:.4f}")
    ad(f"- PR-AUC CV ({model_results.get('pr_auc_cv_mean', 0):.4f} ± "
       f"{model_results.get('pr_auc_cv_std', 0):.4f} no treino)")
    if dia:
        ad(f"- Unidade estação-dia: {dia['eventos']:,} eventos em {dia['n']:,} dias-estação")

    if base:
        ad("\n### Baselines\n")
        ad(f"- Persistência (só chuva acumulada em 24 h): PR-AUC {base['persistencia_pr_auc']:.4f}")
        ad(f"- Climatologia (taxa base constante): PR-AUC {base['climatologia_pr_auc']:.4f}")
        ganho = 100 * (model_results['pr_auc'] / base['persistencia_pr_auc'] - 1)
        ad(f"- **Ganho do modelo sobre a persistência: {ganho:+.1f}%**")
        ad("""
A climatologia é a régua trivial. A persistência — prever pelo que já choveu — é
a que um meteorologista usaria sem custo algum, e é contra ela que o mérito do
modelo deve ser lido.
""")

    ad("""
### Interpretação

- **Precisão**: fração dos alertas que eram eventos reais.
- **Recall**: fração dos eventos reais que foram detectados.
- **Por estação-dia**: a unidade em que um alerta é de fato emitido. O alvo é uma
  janela deslizante, então uma única tempestade gera dezenas de linhas positivas
  quase idênticas; medir por linha infla o tamanho amostral.
- **Brier Score**: qualidade da calibração probabilística (menor = melhor).
- **PR-AUC**: área sob a curva precisão-recall, mais informativa que ROC-AUC em
  bases desbalanceadas.
""")

    # ── Features ──────────────────────────────────────────────────────────────
    ad("\n---\n")
    ad("## Top Features\n")
    if feature_importance:
        for feat, score in feature_importance[:20]:
            ad(f"- {feat}: {score}")

    ad("\n---\n")
    ad("## Insights Automáticos\n")
    for insight in analysis_results.get("insights", []):
        ad(f"- {insight}")

    ad("\n---\n")
    ad("## Hiperparâmetros\n")
    ad(f"- Regressor: `{model_results.get('best_reg_params')}`")
    ad(f"- Classificador: `{model_results.get('best_clf_params')}`")

    report_path.write_text("\n".join(md), encoding="utf-8")
    logger.info("Relatório salvo em: %s", report_path)

    if ENABLE_PLOTS:
        _salvar_graficos(y_test, y_pred, feature_importance)
    else:
        logger.info("Gráficos desativados (ENABLE_PLOTS=False)")

    return report_path


def _salvar_graficos(y_test, y_pred, feature_importance):
    """Matriz de confusão e feature importance como PNG em reports/.

    O matplotlib é importado aqui dentro, e não no topo do módulo, para que
    desligar os gráficos realmente economize a importação — que é lenta e puxa
    dependências que o relatório em texto não usa.
    """
    import matplotlib

    matplotlib.use("Agg")

    import matplotlib.pyplot as plt

    from sklearn.metrics import ConfusionMatrixDisplay

    if y_test is not None and y_pred is not None:
        fig, ax = plt.subplots(figsize=(6, 6))
        ConfusionMatrixDisplay.from_predictions(y_test, y_pred, ax=ax)
        ax.set_title("Matriz de confusão — teste")
        cm_path = REPORTS_DIR / "confusion_matrix.png"
        fig.savefig(cm_path, bbox_inches="tight", dpi=120)
        plt.close(fig)
        logger.info("Matriz de confusão: %s", cm_path)

    if feature_importance:
        top = feature_importance[:20]
        nomes = [x[0] for x in top]
        valores = [x[1] for x in top]

        fig, ax = plt.subplots(figsize=(10, 8))
        ax.barh(nomes[::-1], valores[::-1], color="#0a6870")
        ax.set_xlabel("Importância (nº de splits)")
        ax.set_title("Feature Importance")
        fi_path = REPORTS_DIR / "feature_importance.png"
        fig.savefig(fi_path, bbox_inches="tight", dpi=120)
        plt.close(fig)
        logger.info("Feature importance: %s", fi_path)
