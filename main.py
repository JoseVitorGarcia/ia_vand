import logging

from src.config import ENABLE_OPENMETEO
from src.ingestion import enrich_openmeteo, load_data
from src.processing import clean_data, create_features
from src.analysis import run_analysis
from src.model import train_models
from src.reporting import generate_report

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(name)s — %(message)s',
    datefmt='%H:%M:%S',
)

logger = logging.getLogger(__name__)


def run_pipeline():
    logger.info("=== IA_VAND ===")

    df = load_data()

    if df.empty:
        logger.error("Nenhum dado carregado.")
        return

    df = clean_data(df)

    if ENABLE_OPENMETEO:
        df = enrich_openmeteo(df)
    else:
        logger.info("Open-Meteo desativado (ENABLE_OPENMETEO=False)")

    df = create_features(df)

    if df.empty:
        logger.error("Dataset vazio após processamento.")
        return

    analysis_results = run_analysis(df)

    reg, clf, model_results, y_test, preds, importance = train_models(df)

    generate_report(
        analysis_results=analysis_results,
        model_results=model_results,
        y_test=y_test,
        y_pred=preds,
        feature_importance=importance,
    )

    logger.info("Pipeline finalizado.")


if __name__ == "__main__":
    run_pipeline()
