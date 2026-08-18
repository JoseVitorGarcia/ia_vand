import pandas as pd


def run_analysis(df):
    print("\n================ IA_VAND ANALYSIS 7.0 ================")

    print("\n📦 Shape:")
    print(df.shape)

    print("\n🧠 Dtypes:")
    print(df.dtypes.value_counts())

    print("\n🌧️ Estatísticas chuva:")
    print(df['precipitacao'].describe())

    print("\n🎯 Distribuição evento extremo:")
    print(
        df['evento_extremo']
        .value_counts(normalize=True)
    )

    print("\n📊 Percentis chuva futura:")
    print(
        df['chuva_futura_24h']
        .quantile([0.5, 0.9, 0.95, 0.99])
    )

    print("\n📅 Sazonalidade mensal:")
    print(
        df.groupby('mes')['precipitacao']
        .agg(['mean', 'sum', 'max'])
    )

    print("\n⏰ Sazonalidade horária:")
    print(
        df.groupby('hora')['precipitacao']
        .mean()
    )

    print("\n🔥 Eventos extremos por mês:")
    print(
        df.groupby('mes')['evento_extremo']
        .mean()
    )

    print("\n📊 Correlação:")
    corr = (
        df.corr(numeric_only=True)
        ['chuva_futura_24h']
        .sort_values(ascending=False)
    )

    print(corr.head(20))

    insights = []

    zeros = (df['precipitacao'] == 0).mean()

    if zeros > 0.8:
        insights.append(
            "Dataset altamente esparso"
        )

    extremos = df['evento_extremo'].mean()

    if extremos < 0.02:
        insights.append(
            "Dataset altamente desbalanceado"
        )

    if corr['chuva_48h'] > 0.7:
        insights.append(
            "Chuva acumulada é forte preditor"
        )

    print("\n📈 Insights automáticos:")

    for i in insights:
        print(f"✅ {i}")

    print("\n======================================================")

    return {
        "shape": df.shape,
        "event_ratio": extremos,
        "zero_ratio": zeros,
        "correlations": corr.head(20).to_dict(),
        "insights": insights
    }