# Quanto a observação local acrescenta sobre o ECMWF — Plano de Implementação

> **Para executores agênticos:** SUB-SKILL OBRIGATÓRIA: use superpowers:subagent-driven-development
> ou superpowers:executing-plans para implementar tarefa a tarefa. Os passos usam
> caixas (`- [ ]`) para acompanhamento.

**Objetivo:** estimar, com o intervalo de confiança mais estreito que o dado permite, quanto a
observação local das estações do INMET acrescenta sobre a previsão de chuva do ECMWF — e, se o
resultado for nulo, publicar o **limite superior** desse acréscimo.

**Arquitetura:** um combinador de poucos parâmetros (regressão logística) recebe a chuva prevista
pelo IFS mais features de observação local, é **ajustado em abr–dez/2024** e medido em
**2025-01 → 2026-07**. Nenhum modelo é retreinado. O ganho de potência vem de três lugares:
a janela de ajuste passa de 142 para 1.359 eventos (no cenário mais amplo), a janela de avaliação
de 214 para até 1.965, e quatro cenários (limiar 50/30 mm × emissão 12 UTC / 00+12 UTC) são
medidos numa passada só, com hierarquia declarada antes de olhar o resultado.

**Stack:** Python 3.12, pandas, scikit-learn (LogisticRegression), LightGBM, pyarrow.
Open-Meteo `historical-forecast-api` com `models=ecmwf_ifs025`.

**Spec:** este documento. O desenho foi fechado em brainstorm em 20/08/2026 sobre as evidências de
`reports/combinador_ifs_2026_08_19_13_53.md`, `reports/vies_ifs_2026_08_19_13_34.md` e
`reports/baseline_ifs_2026_08_19_13_17.md`.

---

## Por que este desenho, e não outro

Três medições anteriores fecham portas, e o plano só existe porque elas fecharam:

1. **Correção de viés está morta.** A identidade da estação explica 0,80% da variância do resíduo do
   IFS, e correções simples pioram o erro (MAE 2,94 → 3,16 aditiva). Não existe "o viés daquela
   estação", que é a forma clássica de MOS.
2. **Recalibração não pode ajudar.** PR-AUC mede ordenação; transformação monotônica a preserva.
   Só informação nova supera 0,3957.
3. **O escore do nosso modelo não é essa informação.** V1 (IFS + nosso modelo) deu +0,0248 com IC
   95% [-0,0037, +0,0533] — cruzando zero.

Sobra uma pergunta: a observação local crua acrescenta? E ela tem uma propriedade que decide o
desenho — **as variantes que não consomem `p_modelo` podem ser ajustadas em 2024 sem vazamento**,
porque 2024 é dentro da amostra para o classificador local, mas não para observações do INMET.

## O erro que este plano corrige em relação ao anterior

O único resultado positivo já publicado — V2, +0,0161 [+0,0002, +0,0310] — está na unidade
**estação-dia**, que `src/model.py:73` calcula como o **máximo das 24 horas do dia**, do escore e do
rótulo. As features da V2 incluem `chuva_24h`, `chuva_3h` e `viz_chuva_3h`: na hora 23 do dia D,
`chuva_24h` já viu a chuva do dia D, e o rótulo do dia D é positivo por causa dessa mesma chuva.

É a circularidade que o projeto já documentou para a persistência (0,2900 em estação-dia contra
0,0228 às 12 UTC). Portanto **estação-dia não é endpoint válido aqui** e entra no relatório apenas
como número secundário, com a ressalva escrita.

## Aritmética de potência (medida em 20/08/2026, antes de implementar)

| cenário | eventos p/ ajustar | eventos p/ avaliar | IC ~± | mín. detectável |
|---|---:|---:|---:|---:|
| **50 mm, 12 UTC — PRIMÁRIO** | 269 | 356 | 0,0200 | 5,1% |
| 50 mm, 00+12 UTC | 583 | 694 | 0,0173 | 4,4% |
| 30 mm, 12 UTC | 682 | 994 | 0,0120 | 3,1% |
| 30 mm, 00+12 UTC | 1.359 | 1.965 | 0,0103 | 2,6% |

Para referência, o desenho antigo tinha 142 eventos de ajuste e 214 de avaliação.

**O desenho não tem potência para detectar o efeito observado (+0,0069, ou +1,7%).** Isso é sabido
antes de rodar e não é motivo para não rodar: o entregável é um limite superior, e a janela de
ajuste 10x maior separa duas hipóteses que hoje são confundíveis — *"não há o que corrigir"* de
*"não conseguimos estimar a correção"* (8 coeficientes ajustados com 142 eventos são 18 eventos por
parâmetro).

## Regra de leitura, fixada ANTES de ver o resultado

| resultado | conclusão |
|---|---|
| 30 mm positivo, 50 mm nulo | a observação local contribui, mas não alcança a cauda extrema |
| ambos nulos, com limites estreitos | o ECMWF já contém o que as estações sabem, limitado a ~2,6% |
| 50 mm positivo | exige explicação mecanicista antes de ser aceito |

## Global Constraints

- **Nada de retreino.** `models/classifier.pkl` e `models/threshold.json` não são tocados.
- **Endpoint primário:** PR-AUC na unidade operacional, limiar 50 mm, emissão às 12 UTC.
  Declarado aqui, antes da execução. Os outros três cenários são secundários.
- **`p_modelo` é proibido** em qualquer variante ajustada em 2024 — seria dentro da amostra.
- **Sem `class_weight='balanced'`.** Logística não ponderada é regra de pontuação própria; com
  ponderação a perda otimizada deixa de alinhar com PR-AUC. Já custou uma conclusão invertida
  neste projeto.
- **Embargo de `EMBARGO_HORAS` (24 h)** entre ajuste e avaliação: o alvo das últimas linhas do
  ajuste é a soma de t+1..t+24 e invade o início da avaliação.
- **Toda execução via `MEM_MAX=11G ./run.sh`.** O padrão de 8 GB é menor que o pico do pipeline.
- Datas absolutas, nunca relativas. Hoje é 20/08/2026.

---

### Task 1: Parametrizar a janela da previsão arquivada

Hoje `INICIO_PREV` é uma constante derivada de `TRAIN_END` (`= 2025-01-01`), e três funções a leem
do escopo do módulo. O ajuste em 2024 precisa que elas comecem em `2024-04-01`. Sem isso,
`soil_moisture` — que está na lista de features locais e vem da Open-Meteo — seria **ERA5**
(reanálise, que não existe no momento da decisão) na janela de ajuste e **previsão** na de
avaliação. Ajustar numa distribuição e avaliar em outra é o descasamento que a Fase 1 existiu para
medir.

**Files:**
- Modify: `scripts/medir_degradacao_mos.py` (`_trocar_por_previsao`)
- Modify: `scripts/medir_baseline_ifs.py` (`_baixar_regua`, `_anexar_regua`)
- Test: `tests/test_janela_previsao.py`

**Interfaces:**
- Produces: `_trocar_por_previsao(df, fim, inicio=INICIO_PREV)`,
  `_baixar_regua(estacoes, fim, passadas=6, pausa=60.0, inicio=INICIO_PREV)`,
  `_anexar_regua(df, estacoes, fim, inicio=INICIO_PREV)` — todas retrocompatíveis por padrão.

- [ ] **Step 1: Escrever o teste que falha**

```python
"""O parâmetro `inicio` existe para que a janela de ajuste use PREVISÃO, não ERA5."""
import inspect

from scripts import medir_baseline_ifs as base
from scripts import medir_degradacao_mos as deg


def test_funcoes_aceitam_inicio():
    for fn in (deg._trocar_por_previsao, base._baixar_regua, base._anexar_regua):
        assert 'inicio' in inspect.signature(fn).parameters, fn.__name__


def test_padrao_e_none_e_resolve_para_inicio_prev():
    """Default None resolvido no corpo, não na assinatura: congelar a constante no import
    faria o padrão parar de acompanhar TRAIN_END se ele mudar."""
    for fn in (deg._trocar_por_previsao, base._baixar_regua, base._anexar_regua):
        assert inspect.signature(fn).parameters['inicio'].default is None


def test_inicio_none_usa_a_janela_antiga(monkeypatch):
    """O comportamento sem `inicio` tem de continuar idêntico — scripts antigos dependem."""
    vistos = []
    monkeypatch.setattr(deg, 'fetch_forecast_arquivado',
                        lambda lat, lon, ini, fim, **kw: vistos.append(ini) or pd.DataFrame())
    df = pd.DataFrame({'data_hora': pd.to_datetime(['2025-06-01 12:00'], utc=True),
                       'estacao_codigo': ['A801'], 'latitude': [-30.0], 'longitude': [-51.0],
                       'soil_moisture': [0.3]})
    deg._trocar_por_previsao(df.copy(), '2025-06-02')
    assert vistos == [deg.INICIO_PREV]
```

- [ ] **Step 2: Rodar e ver falhar**

Rodar: `MEM_MAX=4G ./run.sh -m pytest tests/test_janela_previsao.py -q`
Esperado: FAIL com `AssertionError: _trocar_por_previsao`.

- [ ] **Step 3: Implementar**

Em `scripts/medir_degradacao_mos.py`, trocar a assinatura e os dois usos de `INICIO_PREV` dentro do
corpo:

```python
def _trocar_por_previsao(df: pd.DataFrame, fim: str, inicio: str = None) -> pd.DataFrame:
    inicio = inicio or INICIO_PREV
    ...
    janela = df['data_hora'] >= pd.Timestamp(inicio, tz='UTC')
    ...
        prev = fetch_forecast_arquivado(latitudes[linhas[0]], longitudes[linhas[0]],
                                        inicio, fim)
```

Em `scripts/medir_baseline_ifs.py`, o mesmo nas duas funções — `_previsao_cache_path(...)` e
`fetch_forecast_arquivado(...)` passam a receber `inicio`.

O padrão é `None` resolvido para `INICIO_PREV` no corpo, e não `inicio=INICIO_PREV` na assinatura:
congelar a constante no momento do import faria o padrão parar de acompanhar `TRAIN_END` se ele
mudar. Os testes do Step 1 já cobrem as duas coisas.

- [ ] **Step 4: Rodar e ver passar**

Rodar: `MEM_MAX=4G ./run.sh -m pytest tests/test_janela_previsao.py -q`
Esperado: PASS, 2 testes.

- [ ] **Step 5: Rodar a suíte inteira** — os scripts antigos importam essas funções.

Rodar: `MEM_MAX=6G ./run.sh -m pytest tests -q`
Esperado: 32 passed (30 de antes + 2 desta tarefa).

- [ ] **Step 6: Commit**

```bash
git add scripts/medir_degradacao_mos.py scripts/medir_baseline_ifs.py tests/test_janela_previsao.py
git commit -m "Permite começar a janela de previsão antes do fim do treino"
```

---

### Task 2: Janelas de ajuste/avaliação e cenários

**Files:**
- Create: `scripts/medir_acrescimo_local.py` (só as funções puras nesta tarefa)
- Test: `tests/test_acrescimo_local.py`

**Interfaces:**
- Produces:
  - `INICIO_AJUSTE = '2024-04-01'`, `FIM_AJUSTE = pd.Timestamp('2024-12-31 23:00', tz='UTC')`
  - `separar_ajuste_avaliacao(df) -> (mask_ajuste, mask_avaliacao)`
  - `CENARIOS: list[dict]` com chaves `nome`, `limiar`, `horas`, `primario`
  - `rotular(df, limiar) -> np.ndarray` (0/1 a partir de `chuva_futura_24h`)

- [ ] **Step 1: Escrever o teste que falha**

```python
"""Janelas e cenários — a parte pura, sem rede e sem modelo."""
import numpy as np
import pandas as pd
import pytest

from scripts import medir_acrescimo_local as m


def _frame(horas):
    return pd.DataFrame({
        'data_hora': pd.to_datetime(horas, utc=True),
        'chuva_futura_24h': np.arange(len(horas), dtype=float) * 10.0,
    })


def test_ajuste_e_avaliacao_nao_se_tocam():
    df = _frame(['2024-03-31 12:00', '2024-04-01 12:00', '2024-12-31 23:00',
                 '2025-01-01 12:00', '2025-01-02 00:00', '2026-07-31 12:00'])
    aju, ava = m.separar_ajuste_avaliacao(df)
    assert list(aju) == [False, True, True, False, False, False]
    # 2025-01-01 12:00 cai dentro do embargo de 24 h e não pode entrar em nenhuma
    assert list(ava) == [False, False, False, False, True, True]
    assert not (aju & ava).any()


def test_embargo_cobre_o_alvo_da_ultima_linha_de_ajuste():
    """O alvo da última linha de ajuste é a soma de t+1..t+24 — invade 2025 se não houver embargo."""
    df = _frame(['2024-12-31 23:00', '2025-01-01 23:00', '2025-01-02 00:00'])
    _aju, ava = m.separar_ajuste_avaliacao(df)
    assert list(ava) == [False, False, True]


def test_rotular_usa_o_limiar_pedido():
    df = _frame(['2025-02-01 12:00'] * 6)   # chuva_futura_24h = 0,10,20,30,40,50
    assert list(m.rotular(df, 50)) == [0, 0, 0, 0, 0, 0]
    assert list(m.rotular(df, 30)) == [0, 0, 0, 0, 1, 1]


def test_ha_exatamente_um_cenario_primario():
    primarios = [c for c in m.CENARIOS if c['primario']]
    assert len(primarios) == 1
    assert primarios[0]['limiar'] == 50 and primarios[0]['horas'] == (12,)


def test_os_quatro_cenarios_estao_declarados():
    assert {(c['limiar'], c['horas']) for c in m.CENARIOS} == {
        (50, (12,)), (50, (0, 12)), (30, (12,)), (30, (0, 12))}
```

- [ ] **Step 2: Rodar e ver falhar**

Rodar: `MEM_MAX=4G ./run.sh -m pytest tests/test_acrescimo_local.py -q`
Esperado: FAIL com `ModuleNotFoundError: scripts.medir_acrescimo_local`.

- [ ] **Step 3: Implementar as funções puras**

Cabeçalho do módulo, com tudo que as tarefas 2–4 usam:

```python
"""Quanto a observação local acrescenta sobre a previsão do ECMWF?

Ajuste em abr-dez/2024, avaliação de 2025 em diante. Ver o plano em
docs/superpowers/plans/2026-08-20-acrescimo-local-sobre-ecmwf.md.

Uso:
    MEM_MAX=11G ./run.sh scripts/medir_acrescimo_local.py
"""
import logging

import numpy as np
import pandas as pd
from lightgbm import LGBMClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from src.config import EMBARGO_HORAS, REPORTS_DIR
from src.ingestion import enrich_openmeteo, load_data
from src.processing import clean_data, create_features
from scripts.medir_baseline_ifs import _anexar_regua, _baixar_regua
from scripts.medir_degradacao_mos import _media_futura, _trocar_por_previsao

logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s %(levelname)s %(name)s — %(message)s',
                    datefmt='%H:%M:%S')
logger = logging.getLogger('acrescimo')


def _pr(y, score):
    score = np.asarray(score, dtype=float)
    ok = ~np.isnan(score)
    return float(average_precision_score(np.asarray(y)[ok], score[ok]))


INICIO_AJUSTE = '2024-04-01'
FIM_AJUSTE = pd.Timestamp('2024-12-31 23:00', tz='UTC')

CENARIOS = [
    {'nome': '50 mm, 12 UTC',    'limiar': 50, 'horas': (12,),   'primario': True},
    {'nome': '50 mm, 00+12 UTC', 'limiar': 50, 'horas': (0, 12), 'primario': False},
    {'nome': '30 mm, 12 UTC',    'limiar': 30, 'horas': (12,),   'primario': False},
    {'nome': '30 mm, 00+12 UTC', 'limiar': 30, 'horas': (0, 12), 'primario': False},
]


def separar_ajuste_avaliacao(df):
    """Ajuste em abr-dez/2024, avaliação depois, com embargo de EMBARGO_HORAS."""
    t = df['data_hora']
    embargo = pd.Timedelta(hours=EMBARGO_HORAS)
    ajuste = (t >= pd.Timestamp(INICIO_AJUSTE, tz='UTC')) & (t <= FIM_AJUSTE)
    avaliacao = t > FIM_AJUSTE + embargo
    return ajuste, avaliacao


def rotular(df, limiar):
    return (df['chuva_futura_24h'] > limiar).astype(int).to_numpy()
```

- [ ] **Step 4: Rodar e ver passar**

Rodar: `MEM_MAX=4G ./run.sh -m pytest tests/test_acrescimo_local.py -q`
Esperado: PASS, 5 testes (37 na suíte inteira).

- [ ] **Step 5: Commit**

```bash
git add scripts/medir_acrescimo_local.py tests/test_acrescimo_local.py
git commit -m "Declara as janelas e os quatro cenários da medição de acréscimo local"
```

---

### Task 3: Bootstrap agrupado por data

Com duas emissões por dia (00 e 12 UTC), as unidades deixam de ser independentes. Pior: chuva
extrema é fenômeno sinótico — uma frente atinge dezenas de estações no mesmo dia, e tratar 100
estações da mesma tempestade como 100 observações independentes é pseudo-replicação.

Este passo entrega **dois** intervalos: o por unidade (comparável com o relatório de 19/08) e o
agrupado por data (conservador). O agrupado é o que vale.

**Files:**
- Modify: `scripts/medir_acrescimo_local.py`
- Test: `tests/test_acrescimo_local.py`

**Interfaces:**
- Produces: `bootstrap_ic(y, base, alt, grupos=None, n=2000, semente=42) -> (media, (lo, hi))`.
  Com `grupos=None` reamostra linhas; com `grupos` (array de rótulos), reamostra grupos inteiros.

- [ ] **Step 1: Escrever o teste que falha**

```python
def test_bootstrap_agrupado_alarga_o_intervalo():
    """Replicar cada unidade 4x não pode estreitar o IC quando o grupo é respeitado."""
    rng = np.random.default_rng(0)
    n = 300
    y = (rng.random(n) < 0.15).astype(int)
    base = rng.random(n) + 0.3 * y
    alt = base + 0.05 * y
    solto = m.bootstrap_ic(np.tile(y, 4), np.tile(base, 4), np.tile(alt, 4), n=300)
    grupos = np.tile(np.arange(n), 4)
    agrupado = m.bootstrap_ic(np.tile(y, 4), np.tile(base, 4), np.tile(alt, 4),
                              grupos=grupos, n=300)
    largura = lambda r: r[1][1] - r[1][0]
    assert largura(agrupado) > largura(solto)


def test_bootstrap_devolve_media_e_intervalo_ordenado():
    rng = np.random.default_rng(1)
    y = (rng.random(200) < 0.2).astype(int)
    base = rng.random(200)
    media, (lo, hi) = m.bootstrap_ic(y, base, base + 0.1 * y, n=200)
    assert lo <= media <= hi
```

- [ ] **Step 2: Rodar e ver falhar**

Rodar: `MEM_MAX=4G ./run.sh -m pytest tests/test_acrescimo_local.py -q -k bootstrap`
Esperado: FAIL com `AttributeError: module ... has no attribute 'bootstrap_ic'`.

- [ ] **Step 3: Implementar**

```python
def bootstrap_ic(y, base, alt, grupos=None, n=2000, semente=42):
    """IC 95% da diferença de PR-AUC, pareado. Se `grupos` vier, reamostra grupos inteiros.

    Pareado: base e alternativa são pontuadas nas MESMAS unidades, e reamostrar
    as unidades preserva o pareamento.

    Agrupado: chuva extrema é sinótica, e as duas emissões de um dia veem a mesma
    atmosfera. Reamostrar linhas soltas trata isso como informação independente e
    devolve um intervalo estreito demais.
    """
    rng = np.random.default_rng(semente)
    y, base, alt = map(np.asarray, (y, base, alt))
    if grupos is None:
        blocos = [np.array([i]) for i in range(len(y))]
    else:
        grupos = np.asarray(grupos)
        _, inverso = np.unique(grupos, return_inverse=True)
        ordem = np.argsort(inverso, kind='stable')
        cortes = np.flatnonzero(np.diff(inverso[ordem])) + 1
        blocos = np.split(ordem, cortes)

    diferencas = np.empty(n)
    for i in range(n):
        escolha = rng.integers(0, len(blocos), len(blocos))
        idx = np.concatenate([blocos[j] for j in escolha])
        if y[idx].sum() == 0:
            diferencas[i] = np.nan
            continue
        diferencas[i] = (average_precision_score(y[idx], alt[idx])
                         - average_precision_score(y[idx], base[idx]))
    return float(np.nanmean(diferencas)), tuple(np.nanpercentile(diferencas, [2.5, 97.5]))
```

- [ ] **Step 4: Rodar e ver passar**

Rodar: `MEM_MAX=4G ./run.sh -m pytest tests/test_acrescimo_local.py -q`
Esperado: PASS, 7 testes (39 na suíte inteira).

- [ ] **Step 5: Commit**

```bash
git add scripts/medir_acrescimo_local.py tests/test_acrescimo_local.py
git commit -m "Bootstrap agrupado por data, para não tratar uma frente como 100 observações"
```

---

### Task 4: O experimento de ponta a ponta

**Files:**
- Modify: `scripts/medir_acrescimo_local.py` (bloco `__main__`)
- Produz: `reports/acrescimo_local_<AAAA_MM_DD_HH_MM>.md`

**Interfaces:**
- Consumes: tudo das tarefas 1–3, mais `_baixar_regua`/`_anexar_regua` (Task 1),
  `_trocar_por_previsao`/`_media_futura`, `create_features`, `clean_data`, `load_data`,
  `enrich_openmeteo`.

**Variantes** — nenhuma consome `p_modelo`, pela Global Constraint:

```python
LOCAIS = ['chuva_24h', 'chuva_3h', 'queda_pressao_24h', 'soil_moisture',
          'clima_chuva_mes', 'viz_chuva_3h', 'umidade', 'orvalho']

VARIANTES = {
    'V2 IFS + observação local':  LOCAIS,
    'V4 IFS + orvalho + pressão': ['orvalho', 'queda_pressao_24h'],
}
USAR_ARVORE = True   # V5' = árvore sobre ifs_log + LOCAIS, sem p_modelo
```

- [ ] **Step 1: Escrever o `__main__`**

```python
if __name__ == '__main__':
    bruto = enrich_openmeteo(clean_data(load_data()))
    fim = bruto['data_hora'].max().strftime('%Y-%m-%d')
    estacoes = (bruto.groupby('estacao_codigo', observed=True)
                .agg(lat=('latitude', 'first'), lon=('longitude', 'first')))

    _baixar_regua(estacoes, fim, inicio=INICIO_AJUSTE)
    bruto = _trocar_por_previsao(bruto, fim, inicio=INICIO_AJUSTE)

    feats = create_features(bruto)
    del bruto
    aju_mask, ava_mask = separar_ajuste_avaliacao(feats)
    aju = _media_futura(feats[aju_mask].copy())
    ava = _media_futura(feats[ava_mask].copy())
    del feats

    aju = _anexar_regua(aju, estacoes, fim, inicio=INICIO_AJUSTE)
    ava = _anexar_regua(ava, estacoes, fim, inicio=INICIO_AJUSTE)

    for d in (aju, ava):
        d['ifs_log'] = np.log1p(d['ifs_chuva_24h'].clip(lower=0))

    antes = len(aju), len(ava)
    obrig = ['ifs_log', 'chuva_futura_24h'] + LOCAIS
    aju = aju.dropna(subset=obrig)
    ava = ava.dropna(subset=obrig)
    logger.info('ajuste %d->%d | avaliação %d->%d linhas após dropna',
                antes[0], len(aju), antes[1], len(ava))
    logger.info('sobrevivência ao dropna: ajuste %.1f%% | avaliação %.1f%%',
                100 * len(aju) / antes[0], 100 * len(ava) / antes[1])

    linhas_relatorio = []
    for cen in CENARIOS:
        linhas_relatorio += _rodar_cenario(cen, aju, ava)
    _escrever_relatorio(linhas_relatorio)
```

- [ ] **Step 2: Escrever `_rodar_cenario`**

```python
def _rodar_cenario(cen, aju, ava):
    """Ajusta as variantes num cenário e devolve as linhas do relatório."""
    m_aju = aju['data_hora'].dt.hour.isin(cen['horas']).to_numpy()
    m_ava = ava['data_hora'].dt.hour.isin(cen['horas']).to_numpy()
    a, v = aju[m_aju], ava[m_ava]
    y_a, y_v = rotular(a, cen['limiar']), rotular(v, cen['limiar'])

    # Grupos do bootstrap conservador: uma data = uma atmosfera.
    grupos = v['data_hora'].dt.date.to_numpy()
    base = v['ifs_chuva_24h'].to_numpy()

    logger.info('=== %s | ajuste %d linhas / %d eventos | avaliação %d / %d ===',
                cen['nome'], len(a), int(y_a.sum()), len(v), int(y_v.sum()))
    if y_a.sum() < 30 or y_v.sum() < 30:
        logger.error('cenário %s tem eventos demais de menos — não vou reportar', cen['nome'])
        return []

    saida = [{'cenario': cen['nome'], 'variante': 'V0 IFS sozinho',
              'pr_auc': _pr(y_v, base), 'delta': 0.0,
              'ic_solto': (0.0, 0.0), 'ic_data': (0.0, 0.0), 'dentro': _pr(y_a, a['ifs_chuva_24h'])}]

    modelos = {n: make_pipeline(StandardScaler(), LogisticRegression(max_iter=2000, C=1.0))
               for n in VARIANTES}
    if USAR_ARVORE:
        modelos["V5 árvore (interação)"] = LGBMClassifier(
            n_estimators=200, learning_rate=0.05, num_leaves=15, min_child_samples=200,
            reg_lambda=10.0, verbose=-1, random_state=42)

    for nome, modelo in modelos.items():
        extras = LOCAIS if nome.startswith('V5') else VARIANTES[nome]
        colunas = ['ifs_log'] + extras
        modelo.fit(a[colunas], y_a)
        score = modelo.predict_proba(v[colunas])[:, 1]
        media_s, ic_s = bootstrap_ic(y_v, base, score)
        media_d, ic_d = bootstrap_ic(y_v, base, score, grupos=grupos)
        saida.append({'cenario': cen['nome'], 'variante': nome,
                      'pr_auc': _pr(y_v, score), 'delta': media_d,
                      'ic_solto': ic_s, 'ic_data': ic_d,
                      'dentro': _pr(y_a, modelo.predict_proba(a[colunas])[:, 1])})
        logger.info('%-28s fora %.4f (dentro %.4f) | Δ %+.4f solto [%+.4f, %+.4f] '
                    'por data [%+.4f, %+.4f]',
                    nome, saida[-1]['pr_auc'], saida[-1]['dentro'], media_d,
                    ic_s[0], ic_s[1], ic_d[0], ic_d[1])
    return saida
```

- [ ] **Step 3: Escrever `_escrever_relatorio`**

O relatório precisa conter, além da tabela: o endpoint primário declarado, a regra de leitura
fixada, o limite superior quando o IC cruza zero, a ressalva de que estação-dia foi excluída, e o
histórico de seleção da V2 (foi escolhida depois de ver o teste em 19/08).

```python
def _escrever_relatorio(linhas):
    destino = REPORTS_DIR / f"acrescimo_local_{pd.Timestamp.now():%Y_%m_%d_%H_%M}.md"
    primario = next(c['nome'] for c in CENARIOS if c['primario'])
    corpo = [
        "# Quanto a observação local acrescenta sobre a previsão do ECMWF?",
        f"\nGerado em {pd.Timestamp.now():%d/%m/%Y %H:%M}\n",
        "**IFS** (*Integrated Forecasting System*) é o modelo global do **ECMWF**. "
        "**PR-AUC** é a área sob a curva precisão-recall.\n",
        f"Combinador ajustado em **{INICIO_AJUSTE} a {FIM_AJUSTE:%Y-%m-%d}** e medido em "
        f"**{FIM_AJUSTE:%Y-%m-%d} + 24 h em diante**, sem retreinar modelo nenhum.\n",
        f"**Endpoint primário, declarado antes de rodar: {primario}.** Os demais são secundários.\n",
        "Nenhuma variante consome o escore do nosso modelo: 2024 é dentro da amostra para ele, "
        "e usá-lo aqui inflaria o resultado. As variantes que o usam foram medidas em 19/08/2026 "
        "e ficaram com intervalo cruzando zero.\n",
        "A unidade **estação-dia** foi excluída de propósito: ela toma o máximo das 24 h do dia, "
        "e as features locais incluem chuva passada — na hora 23 a janela de 24 h já viu a chuva "
        "do dia que o rótulo mede. É a mesma circularidade que inflava a persistência.\n",
        "**Histórico de seleção, para leitura honesta:** a V2 foi eleita candidata depois de ver o "
        "teste em 19/08/2026. Por isso todas as variantes são reportadas aqui, não só ela.\n",
        "| cenário | variante | PR-AUC | dentro da amostra | Δ vs IFS | IC 95% por unidade | IC 95% por data |",
        "|---|---|---|---|---|---|---|",
    ]
    for r in linhas:
        corpo.append(
            f"| {r['cenario']} | {r['variante']} | {r['pr_auc']:.4f} | {r['dentro']:.4f} | "
            f"{r['delta']:+.4f} | [{r['ic_solto'][0]:+.4f}, {r['ic_solto'][1]:+.4f}] | "
            f"[{r['ic_data'][0]:+.4f}, {r['ic_data'][1]:+.4f}] |")

    corpo.append("\n## Limites superiores\n")
    corpo.append("Quando o intervalo cruza zero, o resultado não é 'nada acontece' — é 'o "
                 "acréscimo, se existir, é menor que o limite abaixo'. Esse é o entregável.\n")
    corpo.append("| cenário | variante | limite superior (IC por data) |")
    corpo.append("|---|---|---|")
    for r in linhas:
        if r['variante'] != 'V0 IFS sozinho' and r['ic_data'][0] <= 0:
            corpo.append(f"| {r['cenario']} | {r['variante']} | {r['ic_data'][1]:+.4f} |")

    destino.write_text("\n".join(corpo) + "\n", encoding='utf-8')
    logger.info('Relatório salvo em %s', destino)
```

- [ ] **Step 4: Rodar o experimento**

Rodar: `MEM_MAX=11G ./run.sh scripts/medir_acrescimo_local.py`

Custo esperado: o cache da previsão arquivada é indexado por `(lat, lon, início, fim, variáveis)`,
e mudar o início de `2025-01-01` para `2024-04-01` **invalida o cache existente**. São ~100
estações × 2 conjuntos de variáveis = ~200 requisições, a 1 s de intervalo, ~10–15 min. Depois,
reconstrução de features (~6 min) e os quatro cenários.

Conferir no log, antes de acreditar em qualquer número:
- cobertura da régua na janela de ajuste (se o arquivo do IFS só começa em abr/2024 para parte das
  estações, a cobertura cai e a contagem de eventos fica abaixo dos 269 previstos);
- contagem de eventos por cenário. **Espere valores ABAIXO** de 269/583/682/1.359 (ajuste) e
  356/694/994/1.965 (avaliação): aqueles números vieram do INMET cru, e o pipeline ainda descarta
  ~21% das linhas por features obrigatórias ausentes, mais o `dropna` das features locais e a
  cobertura da régua. Uma queda de 20–35% é esperada; uma queda de 80% significa janela ou cache
  errados, e aí o número não deve ser reportado.

- [ ] **Step 5: Rodar a suíte inteira**

Rodar: `MEM_MAX=6G ./run.sh -m pytest tests -q`
Esperado: 39 passed.

- [ ] **Step 6: Commit**

```bash
git add scripts/medir_acrescimo_local.py reports/acrescimo_local_*.md
git commit -m "Mede o acréscimo da observação local sobre o ECMWF com ajuste em 2024"
```

---

## O que este plano NÃO faz

- Não retreina o modelo local nem toca em `models/`.
- Não decide o ponto de operação (Fase 2) nem recalibra threshold — PR-AUC não usa corte.
- Não responde se a observação local ajuda em **antecedência curta** (0–6 h), onde modelos
  numéricos são reconhecidamente fracos e a observação tende a ganhar. É a pergunta natural
  seguinte, e exige um alvo com janela diferente.
