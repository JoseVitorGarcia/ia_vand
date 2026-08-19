# BDMEP — Validação Cruzada da Série Horária (Fase 0.5, revisada)

> **Para executores agênticos:** SUB-SKILL OBRIGATÓRIA: use
> superpowers:subagent-driven-development (recomendado) ou
> superpowers:executing-plans. Os passos usam checkbox (`- [ ]`).

**Goal:** Usar os 97 arquivos diários do BDMEP como régua independente da nossa
série horária — descobrir em quais estações a limpeza está perdendo ou inventando
chuva, e fechar a Fase 0.5 com um veredito registrado.

**Architecture:** Nenhuma mudança no pipeline. Um script de auditoria compara a
soma horária nossa contra o total diário oficial do INMET, no dia pluviométrico
(12 UTC → 12 UTC), estação por estação. O que sai disso é um relatório e,
possivelmente, uma lista de estações suspeitas — não features novas.

**Tech Stack:** Python 3.12, pandas 2.2. Sem dependências novas.

**Spec:** este documento. A spec original (`roadmap_fases.md`, "Fase 0.5") previa
integrar séries horárias novas; a análise de 18/08/2026 mostrou que essa premissa
é falsa — ver "O que os dados mostraram" abaixo.

## O que os dados mostraram (18/08/2026)

Os arquivos chegaram em `data/raw/bdmep/`: **97 arquivos, todos com
`Periodicidade da Medicao: Diaria`** (o `_D_` no nome), 11 MB no total.

**O teste de aceitação da fase deu NEGATIVO, e de forma inequívoca:**

- 55 estações começam em 2025+ no portal. Dessas, **0 têm histórico anterior a
  2025 no BDMEP.**
- Das 45 estações antigas, o BDMEP começa antes do portal em 7 casos — no máximo
  **1 dia**.
- 3 estações do portal não têm arquivo BDMEP.

**Consequências, todas favoráveis ao que já está construído:**

1. A rede do INMET no RS **dobrou mesmo** depois das enchentes de maio/2024. Não
   era download incompleto. A dúvida que motivou o pedido está respondida.
2. A herança de climatologia por vizinhança (`_herdar_climatologia_de_vizinhas`)
   está **correta e continua necessária** — não há histórico a recuperar para as
   estações novas, em fonte nenhuma.
3. Não há linha de treino nova a ganhar. Dado diário não entra na grade horária:
   `_reamostrar_horario` criaria 23 horas vazias por dia por estação.

**O que os arquivos valem, então:** régua independente. Verificado em A801, com
os 4.182 dias da série: varrendo deslocamentos de 0 a 23 h, o encaixe é
**r = 1,0000 em +11 h** — 99,6% dos dias idênticos dentro de 0,2 mm, e os 69 dias
acima de 50 mm batendo exatamente nas duas fontes. Ou seja, para essa estação a
nossa pipeline horária reproduz o total oficial do INMET **exatamente**.

Isso importa por dois motivos:

- Retira a suspeita sobre as **979.722 linhas (21%) descartadas** por features
  obrigatórias ausentes, ao menos quanto à precipitação: se o descarte estivesse
  comendo chuva, o total diário divergiria.
- Fixa o **dia pluviométrico** do INMET: 12 UTC a 12 UTC (09h local a 09h local).
  O nosso alvo é janela deslizante de 24 h, que é mais fino e continua certo —
  mas qualquer conversa com defesa civil sobre "choveu X no dia" usa a régua
  deles, não a nossa.

## Global Constraints

- Rodar sempre via `./run.sh`; o script desta fase cabe no padrão de 8 GB.
- Nunca ler, exibir ou modificar arquivos `.env`.
- **Não alterar `clean_data` com base numa estação só.** A verificação de A801 é
  amostra de 1; a Task 1 é o que autoriza (ou não) qualquer mudança.
- Layout confirmado dos arquivos (medido, não suposto):
  encoding **UTF-8**, separador **`;`**, decimal **ponto**, ausentes como a
  string literal **`null`**, 10 linhas de preâmbulo `Chave: valor`, cabeçalho na
  linha 11, coluna de data `Data Medicao` em `YYYY-MM-DD`, `;` final que produz
  uma coluna `Unnamed`.

## Estrutura de arquivos

| Arquivo | Responsabilidade |
|---|---|
| `scripts/validar_com_bdmep.py` (criar) | Leitura do BDMEP diário + comparação com a série horária + relatório. Um arquivo só: a leitura não tem outro consumidor, e módulo separado aqui seria indireção sem ganho. |
| `tests/test_validar_bdmep.py` (criar) | Testes da leitura e do alinhamento do dia pluviométrico. |
| `reports/validacao_bdmep_<data>.md` | A entrega. |

---

### Task 1: Auditoria das 97 estações

**Files:**
- Create: `scripts/validar_com_bdmep.py`
- Create: `tests/test_validar_bdmep.py`

**Interfaces:**
- Consumes: `src.ingestion.load_data`, `src.processing.clean_data`.
- Produces:
  - `scripts.validar_com_bdmep.ler_bdmep_diario(caminho) -> pd.DataFrame` com
    colunas `dia` (datetime64, sem timezone) e `chuva_bdmep` (float).
  - `scripts.validar_com_bdmep.agregar_dia_pluviometrico(df_horario) -> pd.Series`
    indexada por `dia`, somando a chuva de 13 UTC do dia anterior a 12 UTC.
  - `reports/validacao_bdmep_<timestamp>.md`.

- [x] **Step 1: Escrever os testes que falham**

```python
"""Testes da validação cruzada com o BDMEP diário."""
import pandas as pd
import pytest

from scripts.validar_com_bdmep import agregar_dia_pluviometrico, ler_bdmep_diario

CONTEUDO = """Nome: PORTO ALEGRE - JARDIM BOTANICO
Codigo Estacao: A801
Latitude: -30.05361111
Longitude: -51.17472221
Altitude: 41.18
Situacao: Operante
Data Inicial: 2015-01-01
Data Final: 2026-07-31
Periodicidade da Medicao: Diaria

Data Medicao;PRECIPITACAO TOTAL, DIARIO (AUT)(mm);TEMPERATURA MEDIA, DIARIA (AUT)(°C);
2015-01-01;5;25.8;
2015-01-02;18.8;22.1;
2015-01-03;null;null;
"""


@pytest.fixture
def arquivo(tmp_path):
    caminho = tmp_path / "dados_A801_D_2015-01-01_2026-07-31.csv"
    caminho.write_text(CONTEUDO, encoding="utf-8")
    return caminho


def test_le_codigo_e_chuva(arquivo):
    df = ler_bdmep_diario(arquivo)
    assert df.attrs['estacao_codigo'] == 'A801'
    assert list(df['chuva_bdmep'].head(2)) == [5.0, 18.8]


def test_null_literal_vira_nan(arquivo):
    """O BDMEP escreve 'null' como texto — sem na_values, a coluna inteira vira
    object e a soma quebra em silêncio."""
    df = ler_bdmep_diario(arquivo)
    assert pd.isna(df['chuva_bdmep'].iloc[2])
    assert df['chuva_bdmep'].dtype.kind == 'f'


def test_decimal_e_ponto(arquivo):
    """Os CSVs anuais do portal usam vírgula; o BDMEP usa ponto. Trocar os dois
    faz 18.8 virar 188."""
    df = ler_bdmep_diario(arquivo)
    assert df['chuva_bdmep'].iloc[1] == pytest.approx(18.8)


def test_dia_pluviometrico_vai_de_13utc_a_12utc():
    """Medido em A801 sobre 4.182 dias: r=1,0000 no deslocamento de +11 h.

    A chuva rotulada 13 UTC do dia 1 é a que caiu entre 12 e 13 UTC, e pertence
    ao dia pluviométrico 2. A rotulada 12 UTC do dia 2 ainda é do dia 2; a das
    13 UTC do dia 2 já é do dia 3.
    """
    horas = pd.date_range('2015-01-01 00:00', '2015-01-03 23:00', freq='h', tz='UTC')
    df = pd.DataFrame({'data_hora': horas, 'precipitacao': 0.0})
    df.loc[df['data_hora'] == '2015-01-01 13:00+00:00', 'precipitacao'] = 10.0
    df.loc[df['data_hora'] == '2015-01-02 12:00+00:00', 'precipitacao'] = 5.0
    df.loc[df['data_hora'] == '2015-01-02 13:00+00:00', 'precipitacao'] = 7.0

    diario = agregar_dia_pluviometrico(df)
    assert diario[pd.Timestamp('2015-01-02')] == pytest.approx(15.0)
    assert diario[pd.Timestamp('2015-01-03')] == pytest.approx(7.0)
```

- [x] **Step 2: Rodar e ver falhar**

```bash
./run.sh -m pytest tests/test_validar_bdmep.py -v
```

Esperado: FAIL com `ModuleNotFoundError: No module named 'scripts'`. Corrigir
criando `scripts/__init__.py` vazio (o `run.sh` já exporta `PYTHONPATH`).

- [x] **Step 3: Escrever o script**

```python
"""Compara a nossa série horária com os totais diários oficiais do BDMEP.

Por que existe: os arquivos do BDMEP são diários e não acrescentam nenhuma linha
de treino (ver o plano). O que eles são é uma régua independente — se a nossa
limpeza estivesse perdendo ou inventando chuva, o total diário divergiria.

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


def agregar_dia_pluviometrico(df_horario: pd.DataFrame) -> pd.Series:
    """Soma a chuva horária na janela 13 UTC (D-1) → 12 UTC (D)."""
    deslocado = df_horario['data_hora'] + pd.Timedelta(hours=DESLOCAMENTO_DIA_PLUVIOMETRICO)
    return (df_horario.groupby(deslocado.dt.normalize().dt.tz_localize(None))
            ['precipitacao'].sum())


if __name__ == '__main__':
    horario = clean_data(load_data())[['estacao_codigo', 'data_hora', 'precipitacao']]
    por_estacao = dict(list(horario.groupby('estacao_codigo', observed=True)))
    del horario

    linhas = []
    for caminho in sorted(BDMEP_DIR.glob('*.csv')):
        bd = ler_bdmep_diario(caminho)
        codigo = bd.attrs['estacao_codigo']
        if codigo not in por_estacao:
            linhas.append({'estacao': codigo, 'situacao': 'sem série horária'})
            continue

        nosso = agregar_dia_pluviometrico(por_estacao[codigo])
        junto = pd.concat([bd.set_index('dia')['chuva_bdmep'],
                           nosso.rename('chuva_nossa')], axis=1).dropna()
        if len(junto) < 100:
            linhas.append({'estacao': codigo, 'situacao': f'só {len(junto)} dias em comum'})
            continue

        dif = junto['chuva_nossa'] - junto['chuva_bdmep']
        linhas.append({
            'estacao': codigo, 'situacao': 'ok', 'dias': len(junto),
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
    logger.info('\n=== 10 piores encaixes ===\n%s', ok.head(10).to_string(index=False))
    logger.info('\nestações com r > 0,99: %d de %d', int((ok['r'] > 0.99).sum()), len(ok))

    destino = REPORTS_DIR / f"validacao_bdmep_{pd.Timestamp.now():%Y_%m_%d_%H_%M}.md"
    destino.write_text(
        "# Validação cruzada com o BDMEP diário\n\n"
        f"Gerado em {pd.Timestamp.now():%d/%m/%Y %H:%M}\n\n"
        "Compara a soma horária da nossa pipeline com o total diário oficial do "
        "INMET, no dia pluviométrico (12 UTC → 12 UTC).\n\n"
        f"- estações comparadas: {len(ok)}\n"
        f"- com r > 0,99: {int((ok['r'] > 0.99).sum())}\n"
        f"- com r < 0,95: {int((ok['r'] < 0.95).sum())}\n"
        f"- viés médio global: {ok['vies_mm'].mean():+.4f} mm/dia\n\n"
        "## Piores encaixes\n\n" + ok.head(15).to_markdown(index=False) + "\n",
        encoding='utf-8')
    logger.info('Relatório salvo em %s', destino)
```

- [x] **Step 4: Rodar os testes e depois o script**

```bash
./run.sh -m pytest tests/test_validar_bdmep.py -v
./run.sh scripts/validar_com_bdmep.py
```

Esperado nos testes: 4 passando. No script: tabela das piores estações e o
relatório salvo.

- [x] **Step 5: Commit**

```bash
git add scripts/validar_com_bdmep.py scripts/__init__.py tests/test_validar_bdmep.py reports/validacao_bdmep_*.md
git commit -m "Valida a série horária contra os totais diários do BDMEP"
```

---

### Task 2: Agir sobre as divergências (condicional)

Só executar se a Task 1 encontrar estações com `r < 0,95` ou viés relevante. Se
todas ficarem acima de 0,99, **pule para a Task 3** — não há problema a
consertar, e mexer em `clean_data` sem evidência é como se introduz regressão.

**Files:**
- Modify: `src/processing.py` (só se a evidência exigir)
- Modify: `tests/test_pipeline.py`

- [x] **Step 1: Classificar cada estação divergente**

Para cada uma, responder com dados qual é a causa, nesta ordem de probabilidade:

1. **Buracos na nossa série** — dias em que o BDMEP tem chuva e nós temos zero
   porque não há hora nenhuma. Diagnóstico:
   `nosso.reindex(bd.index).isna()`. Não é bug: é estação fora do ar, e o
   `INTERPOLACAO_LIMITE_HORAS` já impede inventar valor. Ação: nenhuma no código;
   registrar a cobertura real por estação no relatório.
2. **Descarte por faixa física** — `_anular_fora_de_faixa` zera precipitação
   acima de 200 mm/h. Diagnóstico: procurar no bruto valores acima da faixa nos
   dias divergentes. Ação: rever o teto **só se** aparecer valor plausível sendo
   cortado.
3. **Duplicatas resolvidas de forma diferente** — `keep='first'` em
   `clean_data` sobre horas repetidas. Diagnóstico: contar duplicatas de
   (estação, hora) no bruto daquelas estações.

- [x] **Step 2: Escrever um teste de regressão para a causa encontrada**

Antes de qualquer correção. O teste tem que falhar com o código atual e passar
depois — sem isso, não há como saber se a correção corrigiu.

- [x] **Step 3: Corrigir, rodar a suíte inteira, commitar**

```bash
./run.sh -m pytest tests -v
git add -A && git commit -m "Corrige <causa> encontrada pela validação com o BDMEP"
```

**Atenção:** qualquer mudança em `clean_data` invalida a comparação com
`reports/report_2026_08_18_20_07.md`. Se corrigir algo aqui, o próximo treino
precisa ser lido como base nova, não como continuação do A/B das features.

---

### Task 3: Fechar a fase e decidir o que pedir ao BDMEP

**Files:** memória do projeto.

- [x] **Step 1: Registrar o veredito**

Em `roadmap_fases.md`: Fase 0.5 concluída com veredito **negativo** (as estações
novas são novas mesmo), o que confirma a herança de climatologia e encerra a
dúvida sobre download incompleto. Em `project_ia_vand.md`: o dia pluviométrico
(12 UTC → 12 UTC, r = 1,0000) e o resultado da auditoria.

- [x] **Step 2: Decidir o próximo pedido ao BDMEP, se houver**

O que os arquivos atuais **não** dão e o que pedir para cada objetivo:

| objetivo | o que pedir | ressalva |
|---|---|---|
| mais densidade espacial | **estações convencionais** do RS (rede distinta das automáticas `A###`) | medem 3x ao dia (12, 18, 00 UTC); não entram na grade horária — servem para climatologia e vizinhança em resolução diária |
| série horária das automáticas | periodicidade **Horária** no formulário do BDMEP | pelo que foi medido, seria redundante: as 45 antigas batem com o portal dia a dia, e as 55 novas não têm histórico |
| histórico antes de 2015 | data inicial anterior no formulário | só ajuda a climatologia; o alvo depende de features horárias que já temos desde 2015 |

**Recomendação:** só as convencionais valem um pedido novo, e mesmo elas entram
como plano próprio — não são grade horária. **A prioridade real é a Fase 1**
(`2026-08-18-mos-medir-degradacao.md`), que é o bloqueio do produto.

- [x] **Step 3: Commit**

```bash
git add docs/ && git commit -m "Fecha a Fase 0.5 com o veredito da validação"
```

---

## RESULTADO — fase concluída em 19/08/2026

Relatório: `reports/validacao_bdmep_2026_08_19_09_39.md`. Commit `8a7a06e`.

**Veredito: a limpeza está correta.** Das 97 estações do BDMEP, 74 têm dias
suficientes para comparar, e **todas as 74 batem com o total diário oficial com
r > 0,999**. Viés global de **+0,0116 mm/dia** — a nossa soma horária reproduz o
pluviômetro do INMET. A pior correlação é 0,9954 (B825).

As 23 fora da comparação são estações novas com menos de 100 dias completos; 5
delas (B845, B848, B849, B856, B857) têm **zero** — o arquivo do BDMEP é todo
`null` e uma delas está marcada `Situacao: Pane`. É ausência de dado deles, não
nossa.

### A Task 2 foi executada, e o defeito estava na régua

A primeira passada acusou B819 (Rolante) com **r = 0,890**, abaixo do corte de
0,95. O diagnóstico (categoria 1 do Step 1 — buracos na nossa série) encontrou 3
dias — 28, 29 e 30/07/2026 — em que **as 24 linhas horárias existem e a
precipitação é NaN em todas**, contra 61,4 e 41,9 mm no BDMEP. Sensor horário
fora do ar com o total diário ainda publicado.

Só que isso expôs um defeito no próprio script: `groupby.sum()` devolve **0.0**
para um dia inteiro de NaN. Um dia sem medição nenhuma entrava na comparação
como "choveu 0 mm" e **concordava com o BDMEP toda vez que ele também marcasse
zero** — inflando o `iguais_%` das 74 estações, não só o de B819.

Correção, com teste de regressão antes (`test_dia_sem_hora_valida_vira_nan_e_nao_zero`
e `test_min_horas_exclui_dia_com_cobertura_parcial`):
`agregar_dia_pluviometrico` ganhou `min_horas`, e a auditoria compara só dias
com as 24 horas válidas. Com a régua certa **B819 vai a r = 0,99993** e nenhuma
estação fica abaixo de 0,995.

**Nada foi alterado em `src/`.** A comparação com
`reports/report_2026_08_18_20_07.md` continua válida — o próximo treino é
continuação do A/B, não base nova.

### O que isso permite afirmar

- O descarte das 979.722 linhas (21%) **não come chuva** — agora verificado nas
  74 estações, não só em A801. Um dia sem medição válida é descartado no treino
  (`min_periods=24` em `chuva_futura_24h` + `precipitacao` em `obrigatorias`),
  em vez de virar zero falso. O descarte está protegendo o alvo.
- O dia pluviométrico 12 UTC → 12 UTC está confirmado em escala de rede.
- Cobertura mediana de **100%**; a pior é B815 com 52%, e mesmo assim r = 0,9992.
  Cobertura baixa limita quantos dias da estação chegam ao treino, mas não
  distorce os que chegam.
