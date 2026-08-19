# MOS — Medir a Degradação Antes de Retreinar (Fase 1)

> **Para executores agênticos:** SUB-SKILL OBRIGATÓRIA: use
> superpowers:subagent-driven-development (recomendado) ou
> superpowers:executing-plans para executar tarefa a tarefa. Os passos usam
> checkbox (`- [ ]`) para acompanhamento.

**Goal:** Produzir o primeiro número de desempenho obtido com **previsão**, e não
com reanálise — e saber quanto do F1 de 0,3274 sobrevive fora do laboratório.

**Architecture:** Nenhum retreino. Reconstrói as features só da janela de teste
trocando a origem das 8 colunas Open-Meteo, reusa os `.pkl` já salvos e reavalia.
São quatro variantes que isolam as **duas** fontes de descasamento —
origem do dado (ERA5 vs. previsão arquivada) e janela (valor em `t` vs. média de
`t+1..t+24`) — porque medi-las juntas não diz qual delas custa caro. Em paralelo,
uma colheita diária começa a acumular previsões reais, que é o único caminho
para o número definitivo.

**Tech Stack:** Python 3.12, pandas 2.2, LightGBM, pytest, `requests`. Sem
dependências novas.

**Spec:** `roadmap_fases.md`, seção "Fase 1 — MOS / alinhar treino e inferência
(F-05)". O aviso original está no topo de `src/predict.py`.

## Global Constraints

- Rodar **sempre** via `./run.sh`; treino/avaliação pesada com `MEM_MAX=11G`.
- Testes: `./run.sh -m pytest tests -v`.
- **Nenhum passo deste plano pode reescolher o threshold sobre o teste.** O corte
  vem de `models/threshold.json` (0,26). Reajustá-lo no teste é vazamento e
  transformaria a medição num número inventado.
- A métrica principal é **PR-AUC por estação-dia**, que independe do threshold.
  F1, precisão e recall entram como contexto.
- Nunca ler, exibir ou modificar arquivos `.env`.
- O limite da Open-Meteo é por IP e ponderado por volume. Baixar em passadas e
  aceitar 429 como cota, não como bug.

## O que exatamente está desalinhado

`src/predict.py` documenta: no treino, `soil_moisture` é o valor ERA5 na hora
`t`; na inferência seria a média das próximas 24 h da previsão. São **duas**
diferenças empilhadas na mesma coluna:

1. **Origem:** ERA5 é reanálise — reconstrução publicada com dias de atraso, que
   assimila observações que ainda não existiam no momento da previsão.
2. **Janela:** valor instantâneo em `t` contra média de `t+1..t+24`.

Este plano mede as duas separadamente. Sem isso, um resultado ruim não diz se a
correção é trocar a fonte (caro: rebaixar tudo e retreinar) ou alinhar a janela
(barato: mudar como a feature é construída, nos dois lados).

## Estrutura de arquivos

| Arquivo | Responsabilidade |
|---|---|
| `src/openmeteo_client.py` (modificar) | Ganha `fetch_forecast_arquivado()` — terceira API, cache próprio. |
| `tests/test_openmeteo_client.py` (criar) | Testes do cliente novo com resposta mockada. |
| `scripts/preencher_cache_previsao.py` (criar) | Enche o cache de previsão arquivada da janela de teste. Espelha o preenchedor que já existe. |
| `scripts/medir_degradacao_mos.py` (criar) | As quatro variantes, a avaliação e o relatório. |
| `scripts/colher_previsao_diaria.py` (criar) | Colheita diária de previsões reais, para o número definitivo mais tarde. |
| `reports/degradacao_mos_<data>.md` | A entrega. |

---

### Task 1: Cliente da API de previsão arquivada

**Files:**
- Modify: `src/openmeteo_client.py`
- Create: `tests/test_openmeteo_client.py`
- Modify: `src/config.py`

**Interfaces:**
- Consumes: `_request`, `_parse_response`, `_cache_utilizavel` (já existem em
  `openmeteo_client.py`).
- Produces:
  - `src.openmeteo_client.fetch_forecast_arquivado(lat: float, lon: float, start_date: str, end_date: str) -> pd.DataFrame`
    — mesmas colunas de `fetch_historical` (`data_hora` + `OPENMETEO_COLUNAS`),
    vindas de `historical-forecast-api.open-meteo.com/v1/forecast`.
  - `src.config.OPENMETEO_PREVISAO_CACHE_DIR: Path`.

- [x] **Step 1: Escrever o teste que falha**

```python
"""Testes do cliente Open-Meteo — a parte que fala com a API de previsão arquivada."""
import pandas as pd
import pytest

from src import openmeteo_client as oc


RESPOSTA = {
    'hourly': {
        'time': ['2025-09-02T00:00', '2025-09-02T01:00', '2025-09-02T02:00'],
        'cloud_cover_low': [10, 20, 30],
        'cloud_cover_mid': [1, 2, 3],
        'cloud_cover_high': [0, 5, 10],
        'wind_gusts_10m': [4.0, 4.5, 5.0],
        'wind_speed_100m': [8.0, 8.5, 9.0],
        'wind_direction_100m': [90, 180, 270],
        'soil_moisture_0_to_7cm': [0.31, 0.32, 0.33],
        'soil_moisture_28_to_100cm': [0.28, 0.28, 0.29],
    }
}


def test_usa_a_api_de_previsao_arquivada(monkeypatch, tmp_path):
    """Não pode cair no archive-api: aquilo é ERA5, o que este plano quer evitar."""
    monkeypatch.setattr(oc, 'OPENMETEO_PREVISAO_CACHE_DIR', tmp_path)
    chamadas = []

    def falso_request(url, params, **kwargs):
        chamadas.append((url, params))
        return RESPOSTA

    monkeypatch.setattr(oc, '_request', falso_request)
    df = oc.fetch_forecast_arquivado(-30.05, -51.17, '2025-09-02', '2025-09-02')

    assert len(chamadas) == 1
    url, params = chamadas[0]
    assert 'historical-forecast-api' in url
    assert params['start_date'] == '2025-09-02'
    assert len(df) == 3
    assert str(df['data_hora'].dt.tz) == 'UTC'


def test_segunda_chamada_vem_do_cache(monkeypatch, tmp_path):
    """Sem cache, a cota da Open-Meteo estoura antes da janela de teste acabar."""
    monkeypatch.setattr(oc, 'OPENMETEO_PREVISAO_CACHE_DIR', tmp_path)
    chamadas = []

    def falso_request(url, params, **kwargs):
        chamadas.append(url)
        return RESPOSTA

    monkeypatch.setattr(oc, '_request', falso_request)
    oc.fetch_forecast_arquivado(-30.05, -51.17, '2025-09-02', '2025-09-02')
    oc.fetch_forecast_arquivado(-30.05, -51.17, '2025-09-02', '2025-09-02')

    assert len(chamadas) == 1, 'a segunda chamada foi à rede em vez do cache'


def test_colunas_iguais_as_do_historico(monkeypatch, tmp_path):
    """As duas fontes precisam ser intercambiáveis coluna a coluna."""
    from src.config import OPENMETEO_COLUNAS

    monkeypatch.setattr(oc, 'OPENMETEO_PREVISAO_CACHE_DIR', tmp_path)
    monkeypatch.setattr(oc, '_request', lambda url, params, **k: RESPOSTA)
    df = oc.fetch_forecast_arquivado(-30.05, -51.17, '2025-09-02', '2025-09-02')

    assert set(OPENMETEO_COLUNAS) <= set(df.columns)
```

- [x] **Step 2: Rodar e ver falhar**

```bash
./run.sh -m pytest tests/test_openmeteo_client.py -v
```

Esperado: FAIL com `AttributeError: module 'src.openmeteo_client' has no
attribute 'fetch_forecast_arquivado'`.

- [x] **Step 3: Acrescentar a configuração**

Em `src/config.py`, junto das outras chaves `OPENMETEO_`:

```python
# Previsões arquivadas — o que o modelo de previsão dizia no passado, sem a
# assimilação retroativa que o ERA5 tem. É a fonte que a inferência real terá.
OPENMETEO_PREVISAO_CACHE_DIR = OPENMETEO_CACHE_DIR / 'previsao'
OPENMETEO_PREVISAO_CACHE_DIR.mkdir(parents=True, exist_ok=True)
```

- [x] **Step 4: Implementar o cliente**

Em `src/openmeteo_client.py`, ao lado das outras URLs:

```python
_PREVISAO_ARQUIVADA_URL = "https://historical-forecast-api.open-meteo.com/v1/forecast"
```

e a função (importar `OPENMETEO_PREVISAO_CACHE_DIR` do config no topo do módulo):

```python
def _previsao_cache_path(lat: float, lon: float, ano: int) -> Path:
    return OPENMETEO_PREVISAO_CACHE_DIR / f"prev_{_cache_key(lat, lon)}_{ano}.parquet"


def fetch_forecast_arquivado(lat: float, lon: float,
                             start_date: str, end_date: str) -> pd.DataFrame:
    """Previsões como foram emitidas no passado, não reanálise.

    Mesma assinatura e mesmas colunas de fetch_historical, de propósito: as duas
    precisam ser intercambiáveis para que a medição de degradação troque só a
    origem do dado, mantendo todo o resto igual.

    Cobertura: o arquivo de previsões da Open-Meteo começa em 2021 — bem depois
    do início da nossa série (2015). Por isso este cliente serve para MEDIR na
    janela de teste, não para retreinar a base inteira.
    """
    inicio = pd.Timestamp(start_date)
    fim = pd.Timestamp(end_date)

    partes, faltando = [], []
    for ano in range(inicio.year, fim.year + 1):
        caminho = _previsao_cache_path(lat, lon, ano)
        if _cache_utilizavel(caminho):
            partes.append(pd.read_parquet(caminho))
        else:
            faltando.append(ano)

    if faltando:
        logger.info("Open-Meteo previsão arquivada %s (%.3f, %.3f)", faltando, lat, lon)
        dados = _request(_PREVISAO_ARQUIVADA_URL, {
            'latitude': lat, 'longitude': lon,
            'start_date': start_date, 'end_date': end_date,
            'hourly': ','.join(OPENMETEO_HISTORICAL_VARS),
            'timezone': 'UTC',
        }, timeout=OPENMETEO_TIMEOUT_INTERVALO)

        baixado = _parse_response(dados, OPENMETEO_HISTORICAL_VARS)
        for ano in faltando:
            do_ano = baixado[baixado['data_hora'].dt.year == ano]
            if not do_ano.empty:
                do_ano.to_parquet(_previsao_cache_path(lat, lon, ano), index=False)
        partes.append(baixado)

    if not partes:
        return pd.DataFrame()

    resultado = pd.concat(partes, ignore_index=True).drop_duplicates(subset='data_hora')
    janela = (resultado['data_hora'] >= inicio.tz_localize('UTC')) & \
             (resultado['data_hora'] <= fim.tz_localize('UTC') + pd.Timedelta(hours=23))
    return resultado[janela].sort_values('data_hora').reset_index(drop=True)
```

- [x] **Step 5: Rodar os testes**

```bash
./run.sh -m pytest tests/test_openmeteo_client.py -v
```

Esperado: 3 passando.

- [x] **Step 6: Commit**

```bash
git add src/openmeteo_client.py src/config.py tests/test_openmeteo_client.py
git commit -m "Lê previsões arquivadas da Open-Meteo, não só reanálise"
```

#### CORREÇÃO da Task 1 — medida em 19/08/2026, antes de seguir

O plano previa chamar `historical-forecast-api` sem `models`. **Assim ele
devolve o MESMO ERA5 do archive-api.** Verificado em 1.440 horas (Porto Alegre,
set–out/2025), sem cache no caminho: as 8 colunas voltam **byte a byte
idênticas** — r = 1,0000, viés 0,0000, MAE 0,0000, 100% dos valores iguais. A
causa é o `models=best_match` default resolvendo para reanálise. Sem essa
correção, as Tasks 2 a 4 rodariam inteiras e mediriam **degradação zero por
construção** — e o resultado pareceria a boa notícia de que não há descasamento.

Sondagem das alternativas (Porto Alegre, 15 dias, contra o ERA5):

| configuração | é distinta do ERA5? | soil_moisture |
|---|---|---|
| default (best_match) | **não** — idêntica | ok |
| `models=ecmwf_ifs025` | **sim** (r 0,63–0,96) | **ok** |
| `models=gfs_seamless` | sim | **100% nula** |
| `models=icon_seamless` | sim | **100% nula** |
| `*_previous_day1` / `_day3` | sim | **100% nula** (só vento existe) |

**`ecmwf_ifs025` é a única escolha viável**, porque é a única distinta do ERA5
que ainda tem `soil_moisture` — e `soil_moisture_profundo` é a 3ª feature mais
usada do modelo. Fixado em `OPENMETEO_PREVISAO_MODELO`.

Divergência das 8 variáveis contra o ERA5 (1.440 h), que é o descasamento que
esta fase vai propagar até a métrica:

| coluna | r | MAE / desvio do ERA5 |
|---|---|---|
| soil_moisture_profundo | 0,936 | **1,57** |
| soil_moisture | 0,961 | 0,77 |
| cloud_cover_mid | 0,632 | 0,47 |
| wind_gusts_10m | 0,881 | 0,43 |
| wind_speed_100m | 0,877 | 0,37 |
| cloud_cover_low | 0,791 | 0,31 |
| cloud_cover_high | 0,843 | 0,27 |
| wind_direction_100m | 0,787 | 0,24 |

**Segunda correção:** o cache passou a ser chaveado pela **janela**, não pelo
ano. A janela de previsão é parcial por construção, e um `prev_..._2025.parquet`
com 3 dias dentro fazia qualquer pedido de 2025 ser servido por esses 3 dias, em
silêncio — foi como o problema apareceu.

**Limitação que fica registrada:** o `historical-forecast-api` serve a previsão
válida naquela hora vinda da rodada mais recente, ou seja, lead time curto. As
variantes `_previous_dayN`, que dariam lead de 1 a 7 dias, não têm as nossas
variáveis. Então a variante B mede a troca de fonte com lead curto — é um
**limite inferior** da degradação real, não o número pessimista.

---

### Task 2: Encher o cache de previsão da janela de teste

**Files:**
- Create: `scripts/preencher_cache_previsao.py`

**Interfaces:**
- Consumes: `fetch_forecast_arquivado` (Task 1).
- Produces: cache em `cache/openmeteo/previsao/` cobrindo `2025-09-02` a
  `2026-07-30` (a janela de teste, definida por `VALID_END` + embargo em
  `src/config.py`) para todas as estações.

- [x] **Step 1: Escrever o preenchedor**

```python
"""Enche o cache de previsão arquivada da janela de teste.

Mesma razão de existir do preencher_cache_openmeteo.py: o rate limit da
Open-Meteo é por IP e a falha é silenciosa — quem baixa dentro do pipeline perde
a estação inteira para NaN sem nada gritar.

Uso:
    ./run.sh scripts/preencher_cache_previsao.py        # até 5 passadas
    ./run.sh scripts/preencher_cache_previsao.py 10 60
    ./run.sh scripts/preencher_cache_previsao.py 0      # só relata
"""
import logging
import sys
import time

import pandas as pd

from src.config import VALID_END
from src.ingestion import load_data
from src.openmeteo_client import _cache_utilizavel, _previsao_cache_path, fetch_forecast_arquivado

logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s %(levelname)s %(name)s — %(message)s',
                    datefmt='%H:%M:%S')
logger = logging.getLogger('preencher_previsao')

MAX_PASSADAS = int(sys.argv[1]) if len(sys.argv) > 1 else 5
PAUSA = float(sys.argv[2]) if len(sys.argv) > 2 else 60.0

# A janela de teste começa depois do embargo de 24 h sobre VALID_END.
INICIO = (VALID_END + pd.Timedelta(hours=25)).strftime('%Y-%m-%d')


def _estacoes():
    df = load_data()
    data = pd.to_datetime(
        df['DATA (YYYY-MM-DD)'].fillna(df['Data']).astype(str).str.replace('/', '-', regex=False),
        errors='coerce')
    t = pd.DataFrame({'est': df['estacao_codigo'], 'lat': df['latitude'],
                      'lon': df['longitude'], 'data': data}).dropna()
    return t.groupby('est').agg(lat=('lat', 'first'), lon=('lon', 'first'),
                                fim=('data', 'max'))


estacoes = _estacoes()
FIM = estacoes['fim'].max().strftime('%Y-%m-%d')
logger.info('%d estações | janela de teste %s a %s', len(estacoes), INICIO, FIM)


def _buracos():
    faltando = []
    for est, r in estacoes.iterrows():
        for ano in range(pd.Timestamp(INICIO).year, pd.Timestamp(FIM).year + 1):
            if not _cache_utilizavel(_previsao_cache_path(r['lat'], r['lon'], ano)):
                faltando.append((est, ano))
    return faltando


for passada in range(1, MAX_PASSADAS + 1):
    faltando = _buracos()
    if not faltando:
        break
    com_buraco = sorted({e for e, _ in faltando})
    logger.info('Passada %d/%d — faltam %d estação-ano em %d estações',
                passada, MAX_PASSADAS, len(faltando), len(com_buraco))
    for i, est in enumerate(com_buraco, 1):
        r = estacoes.loc[est]
        try:
            fetch_forecast_arquivado(r['lat'], r['lon'], INICIO, FIM)
        except Exception as exc:
            logger.warning('%s falhou (%d/%d): %s', est, i, len(com_buraco), exc)
    if passada < MAX_PASSADAS and _buracos():
        time.sleep(PAUSA)

faltando = _buracos()
if faltando:
    por_estacao = pd.Series([e for e, _ in faltando]).value_counts()
    logger.warning('INCOMPLETO: %d estação-ano em %d estações', len(faltando), len(por_estacao))
    logger.warning('piores: %s', por_estacao.head(10).to_dict())
    sys.exit(1)
logger.info('CACHE DE PREVISÃO COMPLETO')
```

- [x] **Step 2: Rodar até completar**

```bash
./run.sh scripts/preencher_cache_previsao.py 10 60
```

Esperado: `CACHE DE PREVISÃO COMPLETO`. Se sair com código 1 listando estações,
repetir mais tarde — é cota, e ela reseta (comprovado em 18/08/2026: as mesmas 4
estações que falhavam às 17:18 baixaram inteiras às 18:54).

- [x] **Step 3: Commit**

```bash
git add scripts/preencher_cache_previsao.py
git commit -m "Baixa as previsões arquivadas da janela de teste"
```

---

### Task 3: Medir as quatro variantes

**Files:**
- Create: `scripts/medir_degradacao_mos.py`

**Interfaces:**
- Consumes: `fetch_forecast_arquivado`; `src.model.separar_janelas`,
  `avaliar_por_estacao_dia`, `calcular_baselines`; os `.pkl` em `models/`.
- Produces: `reports/degradacao_mos_<timestamp>.md` e uma tabela no stdout.

**As quatro variantes:**

| variante | origem das 8 colunas | janela | o que mede |
|---|---|---|---|
| A — referência | ERA5 | valor em `t` | reproduz o 0,2426 do relatório de 20:07 |
| B — só a origem | previsão arquivada | valor em `t` | custo de trocar reanálise por previsão |
| C — só a janela | ERA5 | média `t+1..t+24` | custo do desalinhamento de janela |
| D — realista | previsão arquivada | média `t+1..t+24` | o número que a aplicação teria |

A tem que reproduzir o relatório de 20:07 dentro de 0,001. **Se não reproduzir, o
harness está errado e as outras três não significam nada** — pare e conserte
antes de interpretar qualquer coisa.

- [x] **Step 1: Escrever o medidor**

```python
"""Mede quanto do desempenho sobrevive quando as features vêm de previsão.

Não retreina: reconstrói as features da janela de teste em quatro variantes e
reusa os .pkl salvos. ~15 min contra ~1h10 de um retreino.

Uso:
    MEM_MAX=11G ./run.sh scripts/medir_degradacao_mos.py
"""
import json
import logging

import joblib
import numpy as np
import pandas as pd

from src.config import (FEATURE_COLUMNS, MODELS_DIR, OPENMETEO_COLUNAS, REPORTS_DIR)
from src.ingestion import enrich_openmeteo, load_data
from src.model import avaliar_por_estacao_dia, calcular_baselines, separar_janelas
from src.openmeteo_client import fetch_forecast_arquivado
from src.processing import clean_data, create_features

logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s %(levelname)s %(name)s — %(message)s',
                    datefmt='%H:%M:%S')
logger = logging.getLogger('degradacao_mos')

JANELA_HORAS = 24


def _trocar_por_previsao(df: pd.DataFrame) -> pd.DataFrame:
    """Substitui as colunas Open-Meteo pelo que a previsão dizia, por estação."""
    partes = []
    for codigo, grupo in df.groupby('estacao_codigo', sort=False, observed=True):
        lat = grupo['latitude'].iloc[0]
        lon = grupo['longitude'].iloc[0]
        prev = fetch_forecast_arquivado(
            lat, lon,
            grupo['data_hora'].min().strftime('%Y-%m-%d'),
            grupo['data_hora'].max().strftime('%Y-%m-%d'))
        if prev.empty:
            logger.warning('%s sem previsão arquivada — mantendo ERA5', codigo)
            partes.append(grupo)
            continue
        prev = prev.drop_duplicates(subset='data_hora')
        grupo = grupo.drop(columns=[c for c in OPENMETEO_COLUNAS if c in grupo.columns])
        partes.append(grupo.merge(prev, on='data_hora', how='left'))
    return pd.concat(partes, ignore_index=True)


def _media_futura(df: pd.DataFrame) -> pd.DataFrame:
    """Troca o valor em t pela média de t+1..t+24, por estação.

    Mesma inversão usada no alvo (processing.create_features): inverter a série,
    deslocar 1 e acumular para trás é a forma de olhar estritamente para frente
    sem incluir a própria hora t.
    """
    df = df.sort_values(['estacao_codigo', 'data_hora'])
    colunas = [c for c in OPENMETEO_COLUNAS if c in df.columns]
    for col in colunas:
        df[col] = (df.groupby('estacao_codigo', observed=True)[col]
                   .transform(lambda x: x.iloc[::-1].shift(1)
                              .rolling(JANELA_HORAS, min_periods=1).mean().iloc[::-1])
                   .astype('float32'))
    return df


def _avaliar(df_teste: pd.DataFrame, nome: str, clf, threshold: float, df_treino) -> dict:
    # astype('float32') reproduz o que train_models faz em model.py:268 — sem
    # isso, uma coluna toda-nula volta do parquet como object e o LightGBM quebra.
    X = df_teste[FEATURE_COLUMNS].astype('float32')
    probs = clf.predict_proba(X)[:, 1]
    y = df_teste['evento_extremo'].to_numpy()

    por_dia = avaliar_por_estacao_dia(df_teste, probs, y, threshold)
    baselines = calcular_baselines(df_treino, df_teste, y)
    ganho = 100 * (por_dia['pr_auc'] / baselines['persistencia_pr_auc'] - 1)
    logger.info('%-14s F1 %.4f | P %.4f | R %.4f | PR-AUC %.4f | ganho %+.1f%%',
                nome, por_dia['f1'], por_dia['precision'], por_dia['recall'],
                por_dia['pr_auc'], ganho)
    return {'variante': nome, **por_dia, 'ganho_persistencia': ganho}


clf = joblib.load(MODELS_DIR / 'classifier.pkl')
threshold = json.loads((MODELS_DIR / 'threshold.json').read_text())['threshold']
logger.info('Threshold de models/threshold.json: %.3f (NÃO reajustar no teste)', threshold)

base = enrich_openmeteo(clean_data(load_data()))

resultados = []
for nome, trocar_origem, alinhar_janela in [
    ('A referência',  False, False),
    ('B só origem',   True,  False),
    ('C só janela',   False, True),
    ('D realista',    True,  True),
]:
    df = base.copy()
    if trocar_origem:
        df = _trocar_por_previsao(df)
    if alinhar_janela:
        df = _media_futura(df)

    feats = create_features(df)
    del df
    treino, _validacao, teste = separar_janelas(feats)
    resultados.append(_avaliar(feats[teste], nome, clf, threshold, feats[treino]))
    del feats

tabela = pd.DataFrame(resultados)
logger.info('\n%s', tabela.to_string(index=False))

destino = REPORTS_DIR / f"degradacao_mos_{pd.Timestamp.now():%Y_%m_%d_%H_%M}.md"
destino.write_text(
    "# Degradação com previsão em vez de reanálise\n\n"
    f"Gerado em {pd.Timestamp.now():%d/%m/%Y %H:%M}\n\n"
    f"Threshold fixo de `models/threshold.json`: {threshold:.3f} "
    "(não reajustado no teste — reajustar seria vazamento).\n\n"
    "| variante | F1 | precisão | recall | PR-AUC | ganho s/ persistência |\n"
    "|---|---|---|---|---|---|\n" +
    "\n".join(
        f"| {r['variante']} | {r['f1']:.4f} | {r['precision']:.4f} | "
        f"{r['recall']:.4f} | {r['pr_auc']:.4f} | {r['ganho_persistencia']:+.1f}% |"
        for r in resultados
    ) +
    "\n\nA variante A precisa reproduzir o relatório de referência. Se não "
    "reproduzir, o harness está errado e as outras três não significam nada.\n",
    encoding='utf-8')
logger.info('Relatório salvo em %s', destino)
```

- [x] **Step 2: Rodar**

```bash
MEM_MAX=11G ./run.sh scripts/medir_degradacao_mos.py
```

Esperado: quatro linhas de métrica e o relatório salvo. ~15 min.

- [x] **Step 3: Conferir a variante A antes de olhar as outras**

A tem que dar `F1 0.3274 | P 0.2970 | R 0.3648 | PR-AUC 0.2426`. Divergência
acima de 0,001 significa que o harness não reproduz o pipeline — causas prováveis,
em ordem: `astype('float32')` esquecido, threshold vindo de outro lugar, janela
de teste diferente (conferir `separar_janelas` e o embargo).

- [x] **Step 4: Commit**

```bash
git add scripts/medir_degradacao_mos.py reports/degradacao_mos_*.md
git commit -m "Mede quanto do desempenho sobrevive com previsão em vez de ERA5"
```

---

### Task 4: Interpretar e decidir

**Files:** nenhum de código. Atualiza `reports/degradacao_mos_<data>.md` com a
leitura e a memória do projeto.

- [x] **Step 1: Ler as quatro linhas na ordem certa**

- **D é o número honesto.** É ele, não 0,3274, que pode ser prometido a alguém.
- **B − A** isola o custo de trocar reanálise por previsão.
- **C − A** isola o custo do desalinhamento de janela.
- Se **D ≈ A**, o descasamento era teórico: adotar a janela `t+1..t+24` nos dois
  lados, religar o enriquecimento em `predict.py` e a Fase 1 fecha sem retreino.
- Se **B ≪ A e C ≈ A**, o problema é a fonte. Retreinar com previsão arquivada,
  aceitando a série mais curta (arquivo começa em 2021).
- Se **C ≪ A**, o problema é a janela — e a correção é barata: reconstruir as 8
  colunas como média futura **também no treino** e retreinar uma vez.
- Se **D ≈ 0 e ganho sobre persistência ≈ 0**, a conclusão honesta é que o modelo
  não sobrevive fora da reanálise. É um resultado publicável e vale mais que
  insistir — mas nesse caso releia se `_trocar_por_previsao` não está devolvendo
  NaN em massa (checar `df[OPENMETEO_COLUNAS].isna().mean()` antes de concluir).

- [x] **Step 2: Registrar na memória**

Atualizar `roadmap_fases.md`: Fase 1 deixa de ser "bloqueio de número
desconhecido" e passa a ter um número. Atualizar `project_ia_vand.md` com as
quatro variantes e a decisão tomada.

- [x] **Step 3: Atualizar o aviso de predict.py**

O docstring no topo cita "fase 3 (MOS)" — a numeração mudou para Fase 1. Corrigir
e acrescentar o número medido, para que quem ler o módulo saiba o tamanho real do
problema em vez de só saber que ele existe.

```bash
git add src/predict.py reports/
git commit -m "Registra o desempenho medido com previsão"
```

---

### Task 5: Começar a colheita de previsões reais (pode rodar em paralelo)

A previsão arquivada da Open-Meteo é o melhor proxy disponível, mas **ainda não é
a previsão com 24 h de antecedência** — é o arquivo do modelo, com defasagem
curta. O número definitivo exige guardar, todo dia, o que a previsão dizia sobre
amanhã. Isso só se constrói com o tempo, então começa agora e amadurece enquanto
as outras fases andam.

**Files:**
- Create: `scripts/colher_previsao_diaria.py`

**Interfaces:**
- Consumes: `src.openmeteo_client.fetch_forecast`.
- Produces: um parquet por dia em `cache/openmeteo/colheita/<AAAA-MM-DD>.parquet`
  com a previsão emitida naquele dia para as 24 h seguintes, por estação.

- [ ] **Step 1: Escrever o colhedor**

```python
"""Guarda, todo dia, o que a previsão dizia sobre as próximas 24 h.

Por que existe: a API de previsão arquivada devolve o arquivo do modelo, com
defasagem curta — não o que um usuário teria visto com 24 h de antecedência.
A única forma de medir isso é acumular as previsões conforme elas são emitidas.

Rodar uma vez por dia (cron ou systemd timer):
    ./run.sh scripts/colher_previsao_diaria.py
"""
import logging

import pandas as pd

from src.config import OPENMETEO_CACHE_DIR
from src.ingestion import load_data
from src.openmeteo_client import fetch_forecast

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(message)s', datefmt='%H:%M:%S')
logger = logging.getLogger('colheita')

DESTINO = OPENMETEO_CACHE_DIR / 'colheita'
DESTINO.mkdir(parents=True, exist_ok=True)

hoje = pd.Timestamp.utcnow().strftime('%Y-%m-%d')
arquivo = DESTINO / f'{hoje}.parquet'
if arquivo.exists():
    logger.info('%s já colhido', hoje)
    raise SystemExit(0)

df = load_data()
estacoes = (df.groupby('estacao_codigo', observed=True)[['latitude', 'longitude']]
            .first().dropna())
del df

partes, falhas = [], []
for codigo, r in estacoes.iterrows():
    try:
        prev = fetch_forecast(r['latitude'], r['longitude'])
        prev['estacao_codigo'] = codigo
        prev['emitida_em'] = pd.Timestamp.utcnow()
        partes.append(prev)
    except Exception as exc:
        falhas.append((codigo, str(exc)))

if partes:
    pd.concat(partes, ignore_index=True).to_parquet(arquivo, index=False)
    logger.info('%s: %d estações colhidas', hoje, len(partes))
if falhas:
    logger.warning('%d estações falharam: %s', len(falhas), falhas[:5])
```

- [ ] **Step 2: Rodar uma vez à mão**

```bash
./run.sh scripts/colher_previsao_diaria.py
```

Esperado: um parquet em `cache/openmeteo/colheita/`. Conferir que tem ~98
estações e 48 h de horizonte.

- [ ] **Step 3: Agendar**

```bash
crontab -l 2>/dev/null | { cat; echo "0 9 * * * cd $PWD && ./run.sh scripts/colher_previsao_diaria.py >> /tmp/colheita.log 2>&1"; } | crontab -
```

Confirmar com `crontab -l`. Trinta dias de colheita já dão uma janela pequena mas
real para medir o desempenho com antecedência verdadeira.

- [x] **Step 4: Commit**

```bash
git add scripts/colher_previsao_diaria.py
git commit -m "Colhe diariamente a previsão emitida, para medir a antecedência real"
```

---

## Fases seguintes (esboço — viram planos próprios quando chegar a vez)

**Fase 2 — ponto de operação.** Um escalar em `models/threshold.json`; a decisão
é de produto, não de F1. Precisa da assimetria de custo declarada por quem recebe
o alerta. A curva do roadmap está desatualizada (medida no treino das 16:18 de
18/08) e precisa ser refeita — reconstruir features e reusar os `.pkl` dá a curva
nova em ~6 min. **Depende da Fase 1:** escolher o ponto de operação sobre um
número de laboratório é escolher errado.

**Fase 3 — ingestão em tempo real.** Hoje o pipeline lê CSVs baixados à mão. A
aplicação precisa do INMET em tempo quase real mais o forecast da Open-Meteo. A
colheita da Task 5 já constrói metade disso — o lado Open-Meteo. Falta o lado
INMET, que não tem API pública estável e provavelmente exige raspagem do portal
de dados ou o serviço de estações automáticas.

**Fase 4 — prototipação.** O exploratório (risco histórico por estação, modelo
contra persistência, navegar os eventos de 2024) pode ser feito a qualquer
momento e é honesto porque não promete previsão operacional. O preditivo depende
do número da Fase 1 — construir interface antes é apoiar a aplicação num
resultado que não se sustenta fora do laboratório.


---

## RESULTADO das Tasks 1-4 — 19/08/2026

Relatório: `reports/degradacao_mos_2026_08_19_10_50.md`. Commits `6f87d18`,
`d083b22`, `4a2718b`, `142aa0f`.

**O gate passou:** a variante A reproduziu a referência exatamente
(F1 0,3274 | P 0,2970 | R 0,3648 | PR-AUC 0,2426).

### O número que a fase existia para produzir

Enquadramento operacional — um alerta por estação-dia, emitido às 12 UTC, que é
o início do dia pluviométrico do INMET:

| variante | PR-AUC | persistência | ganho |
|---|---|---|---|
| A ERA5, valor em `t` | 0,0787 | 0,0228 | +245% |
| B previsão, valor em `t` | 0,0825 | 0,0228 | +261% |
| C ERA5, média `t+1..t+24` | 0,1131 | 0,0228 | +396% |
| **D previsão, média `t+1..t+24`** | **0,1085** | 0,0228 | **+375%** |

**D é 38% melhor que A.** A hipótese que motivou a fase — de que o desempenho
medido com reanálise seria um teto otimista — está refutada nesta janela.
Alinhar a janela é o efeito dominante (C−A = +44%); trocar a fonte custa quase
nada (B fica acima de A).

### Três defeitos do plano, corrigidos por medição

1. **`historical-forecast-api` sem `models` devolve ERA5.** Byte a byte, em
   1.440 horas. As quatro variantes teriam rodado e dado degradação zero.
   Corrigido com `ecmwf_ifs025` — a única opção distinta do ERA5 que ainda tem
   `soil_moisture`.
2. **A média `t+1..t+24` não pode ser aplicada a `OPENMETEO_COLUNAS`**, que
   inclui `wind_direction_100m`: média de direção em graus é a descontinuidade
   0°/360°. Movida para depois de `create_features`, sobre as 9 features finais.
3. **O ganho sobre a persistência estava em unidades trocadas** (PR-AUC por
   estação-dia sobre persistência por linha horária → "+829%"). Corrigido, e a
   correção revelou o item abaixo.

### Descoberta lateral: a agregação por max invalida a régua

| unidade | modelo | persistência | ganho |
|---|---|---|---|
| linha horária | 0,0744 | 0,0261 | +185% |
| estação-dia, max do dia | 0,2426 | 0,2900 | **−16%** |
| operacional 12 UTC | 0,0787 | 0,0228 | +245% |
| operacional 00 UTC | 0,0807 | 0,0387 | +109% |

O max de `chuva_24h` do dia cai na hora 0 em 11.281 dos 17.311 dias-estação e na
hora 23 em outros 1.016 — e a janela de 24 h passada nessas horas sobrepõe a
chuva do próprio dia que o alvo tenta prever. A persistência vira diagnóstico.
**O F1 de 0,327 continua válido como descrição do modelo; o que não vale é
comparar com a persistência naquela unidade.**

### O que falta

1. ~~Recalibrar o threshold~~ **FEITO** — `reports/recalibracao_mos_2026_08_19_12_40.md`,
   commit `1beb168`. Reajustando isotônica e corte na validação, o F1 volta a
   **0,3388**, acima da referência de laboratório (0,3274), com P 0,3197 e
   R 0,3604. O desabamento para 0,163 era artefato de escala — o PR-AUC é
   idêntico nos três cenários, então a ordenação nunca se perdeu.

   Bônus para a Fase 2: reajustando só o corte (0,160), o ponto vai para
   **recall 0,4901 / precisão 0,2481** com F1 equivalente (0,3294).
2. **Religar o enriquecimento em `predict.py`** por padrão, depois de (1).
3. **Task 5** — colheita diária de previsões reais. Continua necessária: o
   arquivo devolve, para cada hora, a rodada mais recente antes dela, não a
   rodada disponível no momento da decisão. D é limite inferior.


---

## RESSALVA POSTERIOR — 19/08/2026, 13:17

Este plano mede tudo contra a **persistência**, e conclui com ganhos de +375% a
+396%. Uma medição feita depois de fechá-lo mostra que a régua estava fraca
demais para sustentar essas conclusões como valor do projeto.

A soma da chuva que o próprio ECMWF prevê para as próximas 24 h — gratuita, sem
treinar nada — tem **PR-AUC operacional de 0,3957 contra 0,1085 do nosso modelo**.
A persistência marca 0,0228 no mesmo enquadramento: a previsão europeia a supera
em 17x. Relatório: `reports/baseline_ifs_2026_08_19_13_17.md`, commit `fca8863`.

**O que continua válido deste plano:** a comparação ENTRE as quatro variantes, o
achado de que alinhar a janela para t+1..t+24 é ganho e não perda, a correção do
`models=ecmwf_ifs025`, e a descoberta de que a agregação por max invalida a régua
da persistência. Nada disso depende de qual baseline se usa.

**O que não sustenta mais:** "o modelo ganha +375% da régua trivial" como
afirmação de valor. A régua trivial certa é o IFS, e contra ela perdemos.

O reenquadramento resultante está em `roadmap_fases.md`, seção
"REENQUADRAMENTO — 19/08/2026".
