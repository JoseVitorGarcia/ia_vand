# IA_VAND — Chuva extrema no Rio Grande do Sul

Pipeline de aprendizado de máquina sobre dados do INMET e da Open-Meteo, e as medições que ele produziu.

> **Leia [`ESTADO.md`](ESTADO.md) primeiro.** Este README documenta como o pipeline funciona e como rodá-lo. O *estado* do projeto — o que foi medido, o que foi refutado e o que virou produto — está no ESTADO.md, e mudou substancialmente em agosto de 2026.

---

## Índice

1. [O que o sistema faz](#o-que-o-sistema-faz)
2. [Arquitetura](#arquitetura)
3. [Fontes de dados](#fontes-de-dados)
4. [Estrutura de arquivos](#estrutura-de-arquivos)
5. [Instalação](#instalação)
6. [Como usar](#como-usar)
7. [Configuração](#configuração)
8. [Features do modelo](#features-do-modelo)
9. [Métricas e validação](#métricas-e-validação)
10. [API Open-Meteo](#api-open-meteo)
11. [Inferência em produção](#inferência-em-produção)

---

## O que o sistema faz

O sistema resolve dois problemas de previsão climática:

| Problema | Tipo | Target |
|---|---|---|
| Chuva futura | Regressão | Soma de precipitação de t+1 a t+24 (mm) |
| Evento extremo | Classificação | 1 se chuva futura > 50 mm, 0 caso contrário |

Ambos os modelos usam LightGBM com validação cruzada temporal (TimeSeriesSplit de 5 folds), garantindo que o conjunto de teste seja sempre posterior ao de treino.

### O que as medições mostraram

O pipeline acima continua funcionando e é reprodutível. Mas quando o modelo foi comparado com uma régua forte, o resultado redirecionou o projeto:

| medição | resultado |
|---|---|
| A previsão do **ECMWF** supera este modelo | por **3,6x** em PR-AUC operacional |
| A observação local corrige o ECMWF? | **Não — piora.** −0,0481 [−0,0856, −0,0144] |
| A previsão europeia crua é entregável? | **Sim.** Corte em 30 mm → 71% dos eventos a 30% de confirmação |
| Quanto o alerta regional perde até o ponto? | **De 3,1x a 17,9x** |

Consequência: o projeto deixou de tentar competir com a previsão europeia. Detalhes, ponteiros para os relatórios e as regras que qualquer texto do projeto precisa respeitar estão em [`ESTADO.md`](ESTADO.md).

---

## Arquitetura

### Pipeline de treino

```
CSV INMET (data/raw/)
    │
    ▼
load_data()          → cache em cache/dataset.parquet
    │                  (invalidado automaticamente se raw for atualizado)
    ▼
clean_data()         → UTC explícito, interpolação, validações físicas
    │
    ▼
enrich_openmeteo()   → dados ERA5 por estação via Open-Meteo
    │                  (cache por ano em cache/openmeteo/)
    ▼
create_features()    → lags, acumulados, cíclicas, tendências, interações
    │
    ▼
train_models()       → TimeSeriesSplit (5 folds), LightGBM
    │                  salva models/regressor.pkl, classifier.pkl, threshold.json
    ▼
generate_report()    → reports/report_YYYY_MM_DD_HH_MM.md + gráficos
```

### Pipeline de inferência

```
Features INMET do momento atual
    │
    ├── lat/lon disponível?
    │       │
    │       ▼
    │   fetch_forecast()  → Open-Meteo (próximas 48h, cache 1h)
    │                        média das próximas 24h → features
    ▼
predict()            → chuva_24h_prevista (mm) + risco_evento_extremo (0–1) + alerta (bool)
```

---

## Fontes de dados

### INMET (Instituto Nacional de Meteorologia)

- **Formato**: CSVs horários por estação, separador `;`, codificação `latin-1`
- **Local**: `data/raw/` — organizado por ano e estado
- **Variáveis principais**: precipitação, temperatura, umidade, pressão, vento
- **Download**: [portal.inmet.gov.br](https://portal.inmet.gov.br/dadoshistoricos)

### Open-Meteo (ERA5 + previsão operacional)

- **Gratuita**: sem cadastro, sem chave de API
- **Histórico (ERA5)**: disponível desde 1940, resolução horária
- **Forecast**: até 16 dias à frente, resolução horária
- **Documentação**: [open-meteo.com/en/docs](https://open-meteo.com/en/docs)

---

## Estrutura de arquivos

```
IA_VAND/
├── ESTADO.md                  # ESTADO ATUAL do projeto — leia primeiro
├── main.py                    # Entrypoint do pipeline de treino
├── run.sh                     # Roda em cgroup próprio (use SEMPRE — ver "Como usar")
├── requirements.txt
├── README.md
├── src/
│   ├── config.py              # Configurações centralizadas
│   ├── ingestion.py           # Carregamento INMET + enriquecimento Open-Meteo
│   ├── openmeteo_client.py    # Cliente Open-Meteo (histórico + forecast)
│   ├── processing.py          # Limpeza, features, target
│   ├── analysis.py            # Análise exploratória
│   ├── model.py               # Treinamento com validação cruzada temporal
│   ├── predict.py             # Inferência em produção
│   ├── avisos.py              # Avisos do INMET: geometria, critérios, casamento
│   └── reporting.py           # Relatórios e visualizações
├── scripts/                   # Medições e coletores, um assunto por arquivo
├── tests/                     # 69 testes, sem rede
├── docs/superpowers/plans/    # Planos de execução das medições
├── data/
│   └── raw/                   # CSVs do INMET (não versionados)
├── cache/
│   ├── dataset.parquet        # Cache do dataset INMET bruto
│   ├── openmeteo/             # Cache ERA5, previsão arquivada e colheita diária
│   └── avisos_inmet/          # Arquivo de avisos oficiais colhidos por identificador
├── models/
│   ├── regressor.pkl          # Modelo de regressão treinado
│   ├── classifier.pkl         # Modelo de classificação treinado
│   └── threshold.json         # Threshold ótimo do classificador
└── reports/
    ├── report_YYYY_MM_DD.md   # Relatórios de treino
    ├── <medicao>_YYYY_MM_DD.md # Relatórios de medição — não são atualizados;
    │                           # quando dois se contradizem, vale o mais recente
    ├── confusion_matrix.png
    └── feature_importance.png
```

---

## Instalação

### Pré-requisitos

- Python 3.10+
- Ambiente virtual recomendado

### Passos

```bash
cd IA_VAND

python -m venv venv
source venv/bin/activate        # Linux/Mac
# ou: venv\Scripts\activate     # Windows

pip install -r requirements.txt
```

### Dados do INMET

Baixe os CSVs históricos em [portal.inmet.gov.br/dadoshistoricos](https://portal.inmet.gov.br/dadoshistoricos) e coloque em `data/raw/`:

```
data/raw/
├── 2015/
│   ├── INMET_S_RS_A801_PORTO ALEGRE_01-01-2015_A_31-12-2015.CSV
│   └── ...
├── 2024/
│   └── ...
```

O sistema filtra pelos estados em `STATES_FILTER` (padrão: `['RS']`).

---

## Como usar

### Treinamento completo

```bash
python main.py
```

O pipeline executa na ordem:

1. Carrega dados INMET (ou lê cache — invalidado automaticamente se os CSVs foram atualizados)
2. Limpa e valida os dados com timestamps em UTC
3. Enriquece com dados ERA5 da Open-Meteo por estação (requer internet na primeira execução)
4. Cria features de lags, acumulados, tendências e sazonalidade
5. Treina os dois modelos com validação cruzada temporal (5 folds)
6. Salva modelos e threshold em `models/`
7. Gera relatório em `reports/`

**Tempo estimado na primeira execução com Open-Meteo:**
- Cache INMET: rápido se já existir
- Enriquecimento ERA5: 2–5 minutos para RS (~80 estações, cache por ano)
- Treinamento: 5–10 minutos dependendo do hardware

**Execuções subsequentes**: muito mais rápidas — Open-Meteo lê do cache local.

### Desativar Open-Meteo temporariamente

```python
# src/config.py
ENABLE_OPENMETEO = False
```

### Forçar recarregamento dos dados brutos

```python
from src.ingestion import load_data
df = load_data(force_reload=True)
```

Ou delete `cache/dataset.parquet`.

---

## Configuração

Todas as configurações ficam em `src/config.py`:

| Variável | Padrão | Descrição |
|---|---|---|
| `STATES_FILTER` | `['RS']` | Estados para filtrar os CSVs do INMET |
| `EXTREME_RAIN_THRESHOLD` | `50` | Limiar (mm/24h) para evento extremo |
| `ENABLE_OPENMETEO` | `True` | Ativa enriquecimento ERA5 no treino |
| `OPENMETEO_FORECAST_TTL_HOURS` | `1` | TTL do cache de previsão (horas) |
| `LGBM_REGRESSOR_PARAMS` | — | Hiperparâmetros do LightGBM de regressão |
| `LGBM_CLASSIFIER_PARAMS` | — | Hiperparâmetros do LightGBM de classificação |

### Adicionar estados

```python
# src/config.py
STATES_FILTER = ['RS', 'SC', 'PR']
```

Isso inclui CSVs dos três estados e invalida o cache INMET automaticamente.

---

## Features do modelo

### Observações INMET

| Feature | Descrição |
|---|---|
| `precipitacao` | Chuva no período (mm) |
| `temperatura` | Temperatura do ar (°C) |
| `umidade` | Umidade relativa (%) |
| `pressao` | Pressão atmosférica na estação (mB) |
| `vento` | Velocidade do vento (m/s) |

### Lags temporais (lookback puro — sem leakage)

| Feature | Descrição |
|---|---|
| `lag_1h` | Chuva 1h atrás |
| `lag_3h` | Chuva 3h atrás |
| `lag_6h` | Chuva 6h atrás |
| `lag_24h` | Chuva 24h atrás |

### Acumulados (rolling lookback)

| Feature | Descrição |
|---|---|
| `chuva_6h` | Soma das últimas 6h |
| `chuva_12h` | Soma das últimas 12h |
| `chuva_24h` | Soma das últimas 24h |
| `chuva_48h` | Soma das últimas 48h |

### Features derivadas

| Feature | Descrição |
|---|---|
| `rolling_std_24h` | Desvio padrão de chuva nas últimas 24h |
| `rolling_max_24h` | Máximo de chuva nas últimas 24h |
| `tendencia_6h` | `lag_1h - lag_6h` (tendência recente) |
| `queda_pressao_3h` | Queda de pressão em 3h (indicador de frente fria) |
| `temp_umidade` | Interação temperatura × umidade |

### Temporais e localização

| Feature | Descrição |
|---|---|
| `hora_sin`, `hora_cos` | Hora do dia em coordenadas cíclicas |
| `mes_sin`, `mes_cos` | Mês em coordenadas cíclicas |
| `hora`, `mes` | Componentes temporais brutos |
| `latitude`, `longitude` | Localização da estação |
| `estacao_id` | ID numérico da estação |

### Open-Meteo (ERA5 no treino / forecast na inferência)

| Feature | Descrição | Por que complementa o INMET |
|---|---|---|
| `cape` | Energia convectiva disponível (J/kg) | INMET não mede — preditor-chave de tempestades |
| `cloud_cover` | Cobertura de nuvens (%) | INMET não mede |
| `wind_gusts_10m` | Rajadas de vento (m/s) | INMET mede média, não rajadas |
| `soil_moisture` | Umidade do solo 0–7 cm (m³/m³) | Afeta escoamento e inundações |
| `freezing_level` | Altura da isoterma 0°C (m) | Relevante para eventos no sul do Brasil |

---

## Métricas e validação

### Metodologia

A avaliação usa **TimeSeriesSplit com 5 folds** — os splits são sempre ordenados temporalmente, garantindo que o teste nunca "vê" o passado que o modelo viu no treino.

O modelo final é treinado no subconjunto de treino do **último fold** (período mais recente disponível).

### Como interpretar o relatório

```
REGRESSÃO — MAE CV: 1.23 ± 0.18 mm
```
- `1.23 mm`: erro médio absoluto médio nos 5 folds
- `± 0.18 mm`: variabilidade entre períodos — quanto menor, mais estável

```
CLASSIFICAÇÃO — F1 CV: 0.33 ± 0.05
```
- O F1 medido por estação-dia no treino de 18/08/2026 foi **0,3274**, e **0,3388** depois de recalibrar o corte
- Valores acima de 0.93 (como os originais) eram inflados por erro de definição do target
- A faixa de "0.65–0.80" que este README trazia até 21/08/2026 **estava errada por um fator de dois** e nunca correspondeu a uma medição deste projeto
- Para o desempenho comparado à previsão do ECMWF, que é a régua que importa, ver [`ESTADO.md`](ESTADO.md)

---

## API Open-Meteo

O cliente está em `src/openmeteo_client.py` e pode ser usado diretamente:

```python
from src.openmeteo_client import fetch_historical, fetch_forecast

# Dados históricos ERA5 para Porto Alegre
df_hist = fetch_historical(
    lat=-30.05,
    lon=-51.17,
    start_date="2024-01-01",
    end_date="2024-12-31",
)

# Previsão das próximas 48h
df_forecast = fetch_forecast(lat=-30.05, lon=-51.17)
```

**Colunas retornadas:**

| Coluna | Histórico | Forecast |
|---|---|---|
| `data_hora` | UTC | UTC |
| `cape` | ✓ | ✓ |
| `cloud_cover` | ✓ | ✓ |
| `wind_gusts_10m` | ✓ | ✓ |
| `soil_moisture` | ✓ | ✓ |
| `freezing_level` | ✓ | ✓ |
| `precipitation_probability` | — | ✓ |

**Cache:**
- Histórico: `cache/openmeteo/hist_<lat>_<lon>_<ano>.parquet` (permanente)
- Forecast: `cache/openmeteo/forecast_<lat>_<lon>.parquet` (TTL: 1h)

---

## Inferência em produção

```python
from src.predict import predict

# Features da observação atual (calculadas pela estação + create_features)
features = {
    "precipitacao": 0.0,
    "temperatura": 22.5,
    "umidade": 85.0,
    "pressao": 1012.0,
    "vento": 2.1,
    "lag_1h": 0.0,
    "lag_3h": 0.2,
    "lag_6h": 1.5,
    "lag_24h": 3.0,
    "chuva_6h": 1.5,
    "chuva_12h": 2.8,
    "chuva_24h": 4.1,
    "chuva_48h": 8.3,
    "rolling_std_24h": 0.4,
    "rolling_max_24h": 1.2,
    "tendencia_6h": -1.3,
    "queda_pressao_3h": 0.8,
    "temp_umidade": 1912.5,
    "hora_sin": 0.866,
    "hora_cos": 0.5,
    "mes_sin": 0.5,
    "mes_cos": 0.866,
    "hora": 15,
    "mes": 1,
    "latitude": -30.05,
    "longitude": -51.17,
    "estacao_id": 42,
}

# Com enriquecimento automático via Open-Meteo (recomendado)
resultado = predict(features, lat=-30.05, lon=-51.17)

# Sem Open-Meteo (features de Open-Meteo serão NaN — LightGBM lida nativamente)
resultado = predict(features)

print(resultado)
# {
#     "chuva_24h_prevista": 12.45,
#     "risco_evento_extremo": 0.2341,
#     "alerta": False
# }
```

### Campos do retorno

| Campo | Tipo | Descrição |
|---|---|---|
| `chuva_24h_prevista` | float | Chuva acumulada prevista nas próximas 24h (mm) |
| `risco_evento_extremo` | float | Probabilidade de evento extremo (0–1) |
| `alerta` | bool | `True` se probabilidade > threshold ótimo do treino |

O `threshold` é determinado automaticamente durante o treino (otimizando F-beta com beta=0.5) e salvo em `models/threshold.json`. É carregado na primeira chamada a `predict()`.

---

## Dependências

```
pandas==2.2.2
numpy==1.26.4
scikit-learn==1.5.1
lightgbm==4.3.0
joblib==1.4.2
pyarrow==16.1.0
matplotlib==3.9.0
seaborn==0.13.2
requests==2.32.3
```

---

## Notas técnicas

### Definição correta do target

O target `chuva_futura_24h` em cada instante `t` é a soma estritamente futura:

```
chuva_futura_24h[t] = precipitacao[t+1] + ... + precipitacao[t+24]
```

Implementado com rolling reverso para garantir que nenhum dado futuro vaze para as features:

```python
x.iloc[::-1].shift(1).rolling(window=24, min_periods=24).sum().iloc[::-1]
```

### Validação temporal

O loop de validação coleta métricas em **todos os 5 folds** e reporta `média ± desvio`. O modelo final é treinado apenas no split mais recente — não em todos os dados — para que a avaliação seja representativa do desempenho em produção.

### Cache Open-Meteo

O cache histórico é permanente por `(lat, lon, ano)`. Em execuções futuras, apenas novos anos são baixados. O cache de forecast expira em 1 hora (configurável via `OPENMETEO_FORECAST_TTL_HOURS`).

### Tratamento de NaN

LightGBM lida com NaN nativamente. Features da Open-Meteo ausentes por falha de API ou estação sem coordenadas não interrompem o treino nem a inferência.
