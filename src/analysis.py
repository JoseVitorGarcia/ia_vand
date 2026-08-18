import logging

import pandas as pd

logger = logging.getLogger(__name__)


def run_analysis(df):
    logger.info("=== Análise exploratória ===")

    linhas = []

    def registrar(titulo, conteudo):
        linhas.append(f"\n{titulo}\n{conteudo}")

    registrar("Shape:", str(df.shape))
    registrar("Período:", f"{df['data_hora'].min()} a {df['data_hora'].max()}")
    registrar("Estações:", str(df['estacao_codigo'].nunique()))
    registrar("Estatísticas de chuva horária:", df['precipitacao'].describe().to_string())
    registrar("Distribuição de evento extremo:",
              df['evento_extremo'].value_counts(normalize=True).to_string())
    registrar("Percentis de chuva futura 24h:",
              df['chuva_futura_24h'].quantile([0.5, 0.9, 0.95, 0.99, 0.999]).to_string())
    registrar("Eventos extremos por mês:",
              df.groupby('mes')['evento_extremo'].mean().round(4).to_string())

    # Episódios independentes: o alvo é uma janela deslizante, então uma única
    # tempestade gera dezenas de linhas positivas quase idênticas. Contar
    # episódios mostra o tamanho amostral real por trás das métricas.
    ordenado = df.sort_values(['estacao_codigo', 'data_hora'])
    quebra = (
        ordenado['evento_extremo'].diff().ne(0)
        | ordenado['estacao_codigo'].ne(ordenado['estacao_codigo'].shift())
    ).cumsum()
    episodios = ordenado[ordenado['evento_extremo'] == 1].groupby(quebra).size()

    n_positivas = int(df['evento_extremo'].sum())
    n_episodios = int(len(episodios))
    registrar(
        "Tamanho amostral efetivo:",
        f"{n_positivas:,} linhas positivas correspondem a {n_episodios:,} episódios "
        f"independentes (mediana de {episodios.median():.0f} linhas por episódio)"
        if n_episodios else "sem episódios positivos",
    )

    correlacoes = (
        df.select_dtypes('number').corrwith(df['chuva_futura_24h'])
        .dropna().sort_values(ascending=False)
    )
    registrar("Correlação com chuva futura 24h (top 15):",
              correlacoes.head(15).round(4).to_string())

    zeros = float((df['precipitacao'] == 0).mean())
    extremos = float(df['evento_extremo'].mean())

    insights = []
    if zeros > 0.8:
        insights.append(f"Dataset altamente esparso — {zeros:.1%} das horas sem chuva")
    if extremos < 0.02:
        insights.append(f"Classe extremamente desbalanceada — {extremos:.2%} de eventos")
    if n_episodios and n_positivas / n_episodios > 10:
        insights.append(
            f"Métricas por linha superestimam o n: {n_positivas:,} linhas para "
            f"{n_episodios:,} eventos reais — avaliar por estação-dia"
        )
    if 'chuva_48h' in correlacoes and correlacoes['chuva_48h'] > 0.5:
        insights.append(
            f"Chuva acumulada é forte preditor (r={correlacoes['chuva_48h']:.2f}) — "
            "a baseline de persistência precisa ser reportada"
        )

    registrar("Insights automáticos:", "\n".join(f"- {i}" for i in insights) or "- nenhum")

    logger.info("\n".join(linhas))

    return {
        "shape": df.shape,
        "periodo": (str(df['data_hora'].min()), str(df['data_hora'].max())),
        "n_estacoes": int(df['estacao_codigo'].nunique()),
        "event_ratio": extremos,
        "zero_ratio": zeros,
        "n_positivas": n_positivas,
        "n_episodios": n_episodios,
        "correlations": correlacoes.head(15).to_dict(),
        "insights": insights,
    }
