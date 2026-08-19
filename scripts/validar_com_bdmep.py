"""Compara a nossa série horária com os totais diários oficiais do BDMEP.

Por que existe: os arquivos do BDMEP são diários e não acrescentam nenhuma linha
de treino — das 55 estações que só começam em 2025 no portal, zero têm histórico
anterior lá. O que eles são é uma régua independente: se a nossa limpeza
estivesse perdendo ou inventando chuva, o total diário divergiria.

Uso:
    ./run.sh scripts/validar_com_bdmep.py
"""
import logging
from pathlib import Path

import pandas as pd

from src.config import BASE_DIR, REPORTS_DIR
from src.ingestion import load_data
from src.processing import clean_data

logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s %(levelname)s %(name)s — %(message)s',
                    datefmt='%H:%M:%S')
logger = logging.getLogger('validar_bdmep')

BDMEP_DIR = BASE_DIR / 'data' / 'raw' / 'bdmep'
COLUNA_CHUVA = 'PRECIPITACAO TOTAL, DIARIO (AUT)(mm)'

# O dia pluviométrico do INMET vai de 12 UTC a 12 UTC. Como a chuva rotulada na
# hora H é a que caiu entre H-1 e H, somar de 13 UTC (dia anterior) a 12 UTC dá
# exatamente essa janela. Medido em A801: r=1,0000 contra o total oficial.
DESLOCAMENTO_DIA_PLUVIOMETRICO = 11


def _tabela_md(df: pd.DataFrame) -> str:
    """Markdown à mão — `to_markdown` exigiria tabulate só para formatar."""
    def celula(v):
        if isinstance(v, float):
            return f"{v:.4f}" if abs(v) < 100 else f"{v:,.1f}"
        return "" if pd.isna(v) else str(v)

    cabecalho = "| " + " | ".join(df.columns) + " |"
    separador = "|" + "|".join(["---"] * len(df.columns)) + "|"
    corpo = ["| " + " | ".join(celula(v) for v in linha) + " |"
             for linha in df.itertuples(index=False)]
    return "\n".join([cabecalho, separador, *corpo])


def ler_bdmep_diario(caminho) -> pd.DataFrame:
    """Lê um CSV diário do BDMEP. O código da estação vai em `df.attrs`."""
    caminho = Path(caminho)

    codigo = None
    with open(caminho, 'r', encoding='utf-8') as f:
        for linha in f:
            if linha.upper().startswith('DATA MEDICAO'):
                break
            if ':' in linha:
                chave, valor = linha.split(':', 1)
                if 'CODIGO' in chave.upper():
                    codigo = valor.strip()

    bruto = pd.read_csv(caminho, sep=';', skiprows=10, encoding='utf-8',
                        na_values=['null'])
    bruto = bruto.drop(columns=[c for c in bruto.columns if 'Unnamed' in str(c)],
                       errors='ignore')

    df = pd.DataFrame({
        'dia': pd.to_datetime(bruto['Data Medicao']),
        'chuva_bdmep': pd.to_numeric(bruto[COLUNA_CHUVA], errors='coerce'),
    })
    df.attrs['estacao_codigo'] = codigo
    return df


def agregar_dia_pluviometrico(df_horario: pd.DataFrame,
                              min_horas: int = 1) -> pd.Series:
    """Soma a chuva horária na janela 13 UTC (D-1) → 12 UTC (D).

    `min_horas` é o mínimo de horas com medição válida para o dia contar. O
    default de 1 só evita o pior caso: sem ele, `sum()` devolve 0.0 para um dia
    inteiro de NaN, e um dia sem medição nenhuma entraria na comparação como
    "choveu 0 mm". Com 24, só entram dias de cobertura completa — que é a única
    condição em que a nossa soma é de fato comparável com o total diário.
    """
    deslocado = df_horario['data_hora'] + pd.Timedelta(hours=DESLOCAMENTO_DIA_PLUVIOMETRICO)
    return (df_horario.groupby(deslocado.dt.normalize().dt.tz_localize(None))
            ['precipitacao'].sum(min_count=min_horas))


if __name__ == '__main__':
    horario = clean_data(load_data())[['estacao_codigo', 'data_hora', 'precipitacao']]
    por_estacao = dict(list(horario.groupby('estacao_codigo', observed=True)))
    logger.info('%d estações na série horária', len(por_estacao))
    del horario

    linhas = []
    for caminho in sorted(BDMEP_DIR.glob('*.csv')):
        bd = ler_bdmep_diario(caminho)
        codigo = bd.attrs['estacao_codigo']
        if codigo not in por_estacao:
            linhas.append({'estacao': codigo, 'situacao': 'sem série horária'})
            continue

        bd = bd.set_index('dia')['chuva_bdmep']
        # Só dias de cobertura completa são comparáveis: com menos de 24 horas
        # válidas a nossa soma subestima o total por construção, e a divergência
        # mediria a falha do sensor, não a da limpeza.
        nosso = agregar_dia_pluviometrico(por_estacao[codigo], min_horas=24)
        junto = pd.concat([bd, nosso.rename('chuva_nossa')], axis=1).dropna()

        # Cobertura: dos dias que o BDMEP tem, quantos temos completos.
        dias_bd = int(bd.notna().sum())
        cobertura = 100 * len(junto) / dias_bd if dias_bd else 0.0

        if len(junto) < 100:
            linhas.append({'estacao': codigo,
                           'situacao': f'só {len(junto)} dias completos',
                           'cobertura_%': cobertura})
            continue

        dif = junto['chuva_nossa'] - junto['chuva_bdmep']
        linhas.append({
            'estacao': codigo, 'situacao': 'ok', 'dias': len(junto),
            'cobertura_%': cobertura,
            'r': junto.corr().iloc[0, 1],
            'iguais_%': (dif.abs() < 0.2).mean() * 100,
            'vies_mm': dif.mean(),
            'total_nosso': junto['chuva_nossa'].sum(),
            'total_bdmep': junto['chuva_bdmep'].sum(),
            'eventos_nossos': int((junto['chuva_nossa'] > 50).sum()),
            'eventos_bdmep': int((junto['chuva_bdmep'] > 50).sum()),
        })

    tabela = pd.DataFrame(linhas)
    ok = tabela[tabela['situacao'] == 'ok'].sort_values('r')
    fora = tabela[tabela['situacao'] != 'ok']
    if not fora.empty:
        logger.warning('\n=== fora da comparação ===\n%s', fora.to_string(index=False))
    logger.info('\n=== 10 piores encaixes ===\n%s', ok.head(10).to_string(index=False))
    logger.info('\nestações com r > 0,99: %d de %d', int((ok['r'] > 0.99).sum()), len(ok))
    logger.info('cobertura mediana: %.1f%% | pior: %.1f%%',
                ok['cobertura_%'].median(), ok['cobertura_%'].min())
    logger.info('\n=== 10 menores coberturas ===\n%s',
                ok.sort_values('cobertura_%').head(10)
                [["estacao", "dias", "cobertura_%", "r", "vies_mm"]].to_string(index=False))

    destino = REPORTS_DIR / f"validacao_bdmep_{pd.Timestamp.now():%Y_%m_%d_%H_%M}.md"
    destino.write_text(
        "# Validação cruzada com o BDMEP diário\n\n"
        f"Gerado em {pd.Timestamp.now():%d/%m/%Y %H:%M}\n\n"
        "Compara a soma horária da nossa pipeline com o total diário oficial do "
        "INMET, no dia pluviométrico (12 UTC → 12 UTC). Entram só os dias em que "
        "temos as 24 horas com medição válida — com cobertura parcial a nossa "
        "soma subestima o total por construção, e a divergência mediria a falha "
        "do sensor, não a da limpeza.\n\n"
        f"- estações comparadas: {len(ok)}\n"
        f"- com r > 0,99: {int((ok['r'] > 0.99).sum())}\n"
        f"- com r < 0,95: {int((ok['r'] < 0.95).sum())}\n"
        f"- viés médio global: {ok['vies_mm'].mean():+.4f} mm/dia\n"
        f"- cobertura (dias completos / dias do BDMEP): mediana "
        f"{ok['cobertura_%'].median():.1f}%, pior {ok['cobertura_%'].min():.1f}%\n"
        f"- fora da comparação: {len(fora)}\n\n"
        "## Piores encaixes\n\n" + _tabela_md(ok.head(15)) + "\n"
        + "\n## Menor cobertura\n\n"
          "Dias completos como fração dos dias que o BDMEP tem. Cobertura baixa é "
          "sensor fora do ar, não erro de limpeza — mas é o que limita quantos "
          "dias daquela estação chegam ao treino.\n\n"
        + _tabela_md(ok.sort_values('cobertura_%').head(10)
                     [["estacao", "dias", "cobertura_%", "r", "vies_mm"]]) + "\n"
        + ("\n## Fora da comparação\n\n"
           + _tabela_md(fora[["estacao", "situacao", "cobertura_%"]]) + "\n"
           if not fora.empty else ""),
        encoding='utf-8')
    logger.info('Relatório salvo em %s', destino)
