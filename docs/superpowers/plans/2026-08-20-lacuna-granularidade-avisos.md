# A lacuna de granularidade do alerta regional — Plano de Implementação

> **Para executores agênticos:** SUB-SKILL OBRIGATÓRIA: use
> superpowers:subagent-driven-development ou superpowers:executing-plans para
> implementar tarefa a tarefa. Os passos usam caixas (`- [ ]`).

**Objetivo:** medir com que frequência o fenômeno anunciado por um aviso oficial do INMET é
observado (a) em algum ponto da área coberta e (b) na estação de quem foi avisado — e reportar a
diferença entre os dois, que é a lacuna de granularidade.

**Arquitetura:** três fases independentes. A colheita busca 5.757 avisos por identificador
sequencial e grava em blocos retomáveis. A biblioteca `src/avisos.py` concentra o domínio —
geometria de ponto-em-polígono, extração dos critérios anunciados em texto livre, e casamento com
estação-dia. O medidor consome as duas e produz o relatório. Nenhum modelo é treinado.

**Stack:** Python 3.12, pandas, requests, pyarrow. Sem dependência nova — o ponto-em-polígono é
implementado à mão porque `shapely` não está instalado e não vale um requisito a mais.

**Spec:** `reports/desenho_estudo_avisos_2026_08_20.md`

## Global Constraints

- **Não se mede erro, mede-se taxa de confirmação.** Aviso é comunicação de risco, não afirmação
  determinística. Nenhum texto de código, log ou relatório pode chamar aviso não confirmado de
  "erro", "falso positivo" ou "falha". O termo é **não confirmado**.
- **A mesma régua vale para nós.** Os 30% da nossa regra sobre o ECMWF são taxa de confirmação, e
  o relatório precisa dizê-lo ao comparar.
- **Área e ponto sempre juntos.** Nenhuma das duas unidades pode ser reportada isolada.
- **Cada aviso é verificado contra o critério que ele mesmo anuncia**, e o critério é composto:
  confirma se chuva **ou** rajada cumpriu o anunciado.
- **Tipos incluídos:** Chuvas Intensas, Tempestade, Acumulado de Chuva, Vendaval.
  **Excluídos:** Baixa Umidade, Declínio de Temperatura, Ventos Costeiros.
- **Janela:** ids 49435 (02/01/2025) a 55192 (31/07/2026). Unidade estação-dia ancorada às 12 UTC.
- **Toda execução via `MEM_MAX=11G ./run.sh`.** O padrão de 8 GB é menor que o pico do pipeline.
- **Ser educado com serviço público:** 1 s entre requisições, `User-Agent` identificando o projeto,
  e nunca paralelizar.
- Datas absolutas, nunca relativas. Hoje é 20/08/2026.

## Estrutura de arquivos

| arquivo | responsabilidade |
|---|---|
| `scripts/colher_avisos_inmet.py` | Fase A: baixar os avisos em blocos retomáveis |
| `src/avisos.py` | domínio: geometria, extração de critérios, casamento estação-dia |
| `scripts/medir_lacuna_avisos.py` | Fases B e C: contingência, taxas, curva de área, relatório |
| `tests/test_avisos.py` | a biblioteca inteira, sem rede |
| `tests/test_colher_avisos.py` | o colhedor, sem rede |

---

### Task 1: Colhedor dos avisos (Fase A)

**Files:**
- Create: `scripts/colher_avisos_inmet.py`
- Test: `tests/test_colher_avisos.py`

**Interfaces:**
- Produces: `normalizar_resposta(payload) -> dict | None`, `blocos(id_inicio, id_fim, tamanho) -> list[tuple[int,int]]`,
  `caminho_bloco(lo, hi) -> Path`. Parquets em `cache/avisos_inmet/avisos_<lo>_<hi>.parquet`, uma
  linha por identificador tentado, com colunas `id`, `obtido` (bool), `http` (int) e os campos do aviso.

- [ ] **Step 1: Escrever o teste que falha**

```python
"""O colhedor de avisos: normalização da resposta e divisão em blocos retomáveis."""
import pandas as pd
import pytest

from scripts import colher_avisos_inmet as c


def test_normaliza_as_tres_formas_de_resposta():
    """A API já devolveu lista, objeto solto e objeto com chave 'hoje' — as três valem."""
    alvo = {'id_condicao_severa': '24', 'descricao': 'Chuvas Intensas'}
    assert c.normalizar_resposta([alvo]) == alvo
    assert c.normalizar_resposta(alvo) == alvo
    assert c.normalizar_resposta({'hoje': [alvo]}) == alvo


def test_normaliza_vazio_para_none():
    assert c.normalizar_resposta(None) is None
    assert c.normalizar_resposta([]) is None
    assert c.normalizar_resposta({'hoje': []}) is None


def test_blocos_cobrem_o_intervalo_inteiro_sem_buraco_nem_sobreposicao():
    bs = c.blocos(49435, 55192, 500)
    assert bs[0][0] == 49435 and bs[-1][1] == 55192
    for (_, fim_a), (ini_b, _) in zip(bs, bs[1:]):
        assert ini_b == fim_a + 1
    assert sum(hi - lo + 1 for lo, hi in bs) == 55192 - 49435 + 1


def test_bloco_menor_que_o_tamanho_no_fim():
    bs = c.blocos(1, 7, 3)
    assert bs == [(1, 3), (4, 6), (7, 7)]
```

- [ ] **Step 2: Rodar e ver falhar**

Rodar: `MEM_MAX=4G ./run.sh -m pytest tests/test_colher_avisos.py -q`
Esperado: FAIL com `ModuleNotFoundError: scripts.colher_avisos_inmet`.

- [ ] **Step 3: Implementar**

```python
"""Colhe o arquivo de avisos meteorológicos do INMET, por identificador.

Por que existe: os avisos ficam disponíveis em `avisos/ativos` só enquanto vigem,
mas cada aviso tem um identificador sequencial no tempo e continua acessível por
`aviso/getByID`. Isso permite reconstruir o histórico em vez de esperar meses
coletando — verificado em 20/08/2026: id 45000 é de out/2023, 50912 de jun/2025,
55431 de ago/2026.

Grava em blocos: um parquet por faixa de identificadores, escrito só quando a
faixa inteira foi tentada. Retomar é pular os blocos que já existem, então uma
interrupção custa no máximo um bloco.

Uma linha por identificador TENTADO, inclusive os que não devolveram nada — sem
isso não dá para distinguir "aviso não existe" de "não fui buscar", e a cobertura
do estudo fica sem auditoria.

Uso:
    ./run.sh scripts/colher_avisos_inmet.py           # colhe o que falta
    ./run.sh scripts/colher_avisos_inmet.py --relatar # só diz o que falta
"""
import logging
import sys
import time
from pathlib import Path

import pandas as pd
import requests

from src.config import CACHE_DIR

logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s %(levelname)s %(name)s — %(message)s',
                    datefmt='%H:%M:%S')
logger = logging.getLogger('avisos')

URL = 'https://apiprevmet3.inmet.gov.br/aviso/getByID/{id}'
# Identificar-se é cortesia mínima com um serviço público, e ajuda o INMET a
# distinguir pesquisa de abuso caso olhe os registros.
CABECALHOS = {'User-Agent': 'IA_VAND/1.0 (pesquisa academica; UFRGS)'}

ID_INICIO, ID_FIM = 49435, 55192
TAMANHO_BLOCO = 500
PAUSA = 1.0
DESTINO = CACHE_DIR / 'avisos_inmet'
DESTINO.mkdir(parents=True, exist_ok=True)


def normalizar_resposta(payload):
    """Devolve o aviso como dict, ou None. A API já usou três formatos."""
    if payload is None:
        return None
    if isinstance(payload, list):
        return payload[0] if payload else None
    if isinstance(payload, dict):
        if 'hoje' in payload:
            hoje = payload['hoje']
            return hoje[0] if hoje else None
        return payload or None
    return None


def blocos(id_inicio, id_fim, tamanho):
    return [(lo, min(lo + tamanho - 1, id_fim))
            for lo in range(id_inicio, id_fim + 1, tamanho)]


def caminho_bloco(lo, hi):
    return DESTINO / f'avisos_{lo}_{hi}.parquet'


def _buscar(sessao, aviso_id, tentativas=3):
    """Devolve (dict|None, http). Não levanta: bloco parcial é retomável."""
    espera = 10
    for tentativa in range(tentativas):
        try:
            r = sessao.get(URL.format(id=aviso_id), timeout=30)
            if r.status_code == 404:
                return None, 404
            if r.status_code in (429, 500, 502, 503, 504):
                logger.warning('id %d devolveu %d — espera %ds', aviso_id, r.status_code, espera)
                time.sleep(espera)
                espera *= 2
                continue
            r.raise_for_status()
            return normalizar_resposta(r.json()), r.status_code
        except Exception as exc:
            logger.warning('id %d falhou (%d/%d): %s', aviso_id, tentativa + 1, tentativas, exc)
            time.sleep(espera)
            espera *= 2
    return None, 0


if __name__ == '__main__':
    faixas = blocos(ID_INICIO, ID_FIM, TAMANHO_BLOCO)
    faltando = [(lo, hi) for lo, hi in faixas if not caminho_bloco(lo, hi).exists()]
    logger.info('%d blocos no total, %d a colher (%d avisos)',
                len(faixas), len(faltando), sum(hi - lo + 1 for lo, hi in faltando))
    if '--relatar' in sys.argv:
        raise SystemExit(0)

    sessao = requests.Session()
    sessao.headers.update(CABECALHOS)
    for lo, hi in faltando:
        linhas = []
        for aviso_id in range(lo, hi + 1):
            aviso, http = _buscar(sessao, aviso_id)
            linha = {'id': aviso_id, 'obtido': aviso is not None, 'http': http}
            if aviso:
                linha.update({k: (str(v) if not isinstance(v, (int, float, type(None))) else v)
                              for k, v in aviso.items()})
            linhas.append(linha)
            time.sleep(PAUSA)

        tmp = caminho_bloco(lo, hi).with_suffix('.parquet.tmp')
        pd.DataFrame(linhas).to_parquet(tmp, index=False)
        tmp.rename(caminho_bloco(lo, hi))
        obtidos = sum(1 for l in linhas if l['obtido'])
        logger.info('bloco %d-%d: %d/%d avisos obtidos', lo, hi, obtidos, len(linhas))

    logger.info('COLHEITA COMPLETA — %d blocos em %s', len(faixas), DESTINO)
```

- [ ] **Step 4: Rodar e ver passar**

Rodar: `MEM_MAX=4G ./run.sh -m pytest tests/test_colher_avisos.py -q`
Esperado: PASS, 4 testes.

- [ ] **Step 5: Disparar a colheita em segundo plano**

Rodar: `./run.sh scripts/colher_avisos_inmet.py`
Custo: 5.757 requisições a 1 s ≈ 1h40, mais esperas de repetição. Deixar rodando enquanto as
tarefas seguintes são escritas — elas não dependem do dado, só do formato.

- [ ] **Step 6: Verificar monotonicidade dos identificadores**

A janela (49435–55192) foi localizada por busca binária, que assume que a data cresce com o
identificador. Conferir com amostras espalhadas depois que os blocos existirem:

```bash
MEM_MAX=6G ./run.sh - <<'EOF'
import pandas as pd, glob
df = pd.concat([pd.read_parquet(f) for f in glob.glob('cache/avisos_inmet/*.parquet')])
df = df[df.obtido].sort_values('id')
d = pd.to_datetime(df['data_inicio'], errors='coerce')
fora = (d.diff().dt.total_seconds() < -86400).sum()
print(f'{len(df)} avisos | datas {d.min()} a {d.max()} | quebras de ordem > 1 dia: {fora}')
EOF
```

Esperado: datas entre 2025-01-02 e 2026-07-31, e poucas quebras. Muitas quebras significam que a
sequência não é temporal e a janela precisa ser refeita por varredura, não por busca binária.

- [ ] **Step 7: Commit**

```bash
git add scripts/colher_avisos_inmet.py tests/test_colher_avisos.py
git commit -m "Colhe o arquivo de avisos do INMET por identificador"
```

---

### Task 2: Geometria — ponto em polígono

As estações do INMET trazem código, nome, latitude, longitude e altitude — **não trazem município
nem geocódigo IBGE**. Então o casamento entre estação e aviso é geométrico, sobre o campo
`poligono` do aviso. `shapely` não está instalado e não vale um requisito novo por 25 linhas.

**Files:**
- Create: `src/avisos.py`
- Test: `tests/test_avisos.py`

**Interfaces:**
- Produces: `ponto_em_poligono(lon: float, lat: float, geometria: str | dict) -> bool`.
  Aceita GeoJSON `Polygon` e `MultiPolygon`, como texto JSON ou dicionário. Respeita buracos.

- [ ] **Step 1: Escrever o teste que falha**

```python
"""Domínio dos avisos: geometria, critérios anunciados e casamento com estação-dia."""
import json

import numpy as np
import pandas as pd
import pytest

from src import avisos as av

QUADRADO = {'type': 'Polygon', 'coordinates': [
    [[-52.0, -30.0], [-50.0, -30.0], [-50.0, -28.0], [-52.0, -28.0], [-52.0, -30.0]]]}

COM_BURACO = {'type': 'Polygon', 'coordinates': [
    [[-52.0, -30.0], [-50.0, -30.0], [-50.0, -28.0], [-52.0, -28.0], [-52.0, -30.0]],
    [[-51.5, -29.5], [-50.5, -29.5], [-50.5, -28.5], [-51.5, -28.5], [-51.5, -29.5]]]}


def test_ponto_dentro_e_fora():
    assert av.ponto_em_poligono(-51.0, -29.0, QUADRADO)
    assert not av.ponto_em_poligono(-49.0, -29.0, QUADRADO)
    assert not av.ponto_em_poligono(-51.0, -31.0, QUADRADO)


def test_aceita_geojson_como_texto():
    """A coluna vem do parquet como string — o formato de disco é texto."""
    assert av.ponto_em_poligono(-51.0, -29.0, json.dumps(QUADRADO))


def test_buraco_nao_conta_como_dentro():
    assert not av.ponto_em_poligono(-51.0, -29.0, COM_BURACO)
    assert av.ponto_em_poligono(-51.9, -29.9, COM_BURACO)


def test_multipolygon():
    multi = {'type': 'MultiPolygon', 'coordinates': [QUADRADO['coordinates'],
             [[[-45.0, -20.0], [-44.0, -20.0], [-44.0, -19.0], [-45.0, -19.0], [-45.0, -20.0]]]]}
    assert av.ponto_em_poligono(-51.0, -29.0, multi)
    assert av.ponto_em_poligono(-44.5, -19.5, multi)
    assert not av.ponto_em_poligono(-48.0, -25.0, multi)


def test_geometria_invalida_devolve_falso():
    """Aviso sem polígono não pode derrubar o estudo inteiro."""
    assert not av.ponto_em_poligono(-51.0, -29.0, None)
    assert not av.ponto_em_poligono(-51.0, -29.0, 'nao é json')
```

- [ ] **Step 2: Rodar e ver falhar**

Rodar: `MEM_MAX=4G ./run.sh -m pytest tests/test_avisos.py -q`
Esperado: FAIL com `ModuleNotFoundError: src.avisos`.

- [ ] **Step 3: Implementar**

```python
"""Domínio dos avisos meteorológicos do INMET.

Vocabulário desta biblioteca, e ele não é estilístico: um aviso é comunicação de
RISCO, não afirmação determinística. Aviso cujo fenômeno não ocorreu não é erro
nem falso positivo — é NÃO CONFIRMADO. Verificar aviso como acerto binário é o
equívoco clássico da avaliação de sistemas de alerta e produz a conclusão falsa
de que serviços meteorológicos erram muito.
"""
import json
import logging
import re

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


def _anel_contem(x, y, anel):
    """Lançamento de raio: conta cruzamentos de aresta à esquerda do ponto."""
    dentro = False
    n = len(anel)
    j = n - 1
    for i in range(n):
        xi, yi = anel[i][0], anel[i][1]
        xj, yj = anel[j][0], anel[j][1]
        if ((yi > y) != (yj > y)) and (x < (xj - xi) * (y - yi) / (yj - yi) + xi):
            dentro = not dentro
        j = i
    return dentro


def _poligono_contem(x, y, aneis):
    """Primeiro anel é o contorno; os demais são buracos."""
    if not aneis or _fora_da_caixa(x, y, aneis) or not _anel_contem(x, y, aneis[0]):
        return False
    return not any(_anel_contem(x, y, buraco) for buraco in aneis[1:])


def _fora_da_caixa(x, y, aneis):
    """Rejeição barata antes do lançamento de raio.

    São 5.757 avisos x 95 estações = ~547 mil testes, cada um percorrendo
    centenas de vértices em Python puro. A caixa envolvente descarta a grande
    maioria em quatro comparações.
    """
    contorno = aneis[0]
    xs = [c[0] for c in contorno]
    ys = [c[1] for c in contorno]
    return x < min(xs) or x > max(xs) or y < min(ys) or y > max(ys)


def ponto_em_poligono(lon, lat, geometria):
    """True se (lon, lat) está dentro da geometria GeoJSON.

    Aceita Polygon e MultiPolygon, como dicionário ou texto. Geometria ausente ou
    ilegível devolve False em vez de levantar: um aviso malformado não pode
    derrubar o estudo, mas também não pode contar como cobertura.
    """
    if geometria is None or (isinstance(geometria, float) and np.isnan(geometria)):
        return False
    if isinstance(geometria, str):
        try:
            geometria = json.loads(geometria)
        except (ValueError, TypeError):
            return False
    if not isinstance(geometria, dict):
        return False

    tipo = geometria.get('type')
    coords = geometria.get('coordinates')
    if not coords:
        return False
    if tipo == 'Polygon':
        return _poligono_contem(lon, lat, coords)
    if tipo == 'MultiPolygon':
        return any(_poligono_contem(lon, lat, p) for p in coords)
    return False
```

- [ ] **Step 4: Rodar e ver passar**

Rodar: `MEM_MAX=4G ./run.sh -m pytest tests/test_avisos.py -q`
Esperado: PASS, 5 testes.

- [ ] **Step 5: Commit**

```bash
git add src/avisos.py tests/test_avisos.py
git commit -m "Ponto em polígono à mão, para casar estação com área do aviso"
```

---

### Task 3: Extrair o critério que o aviso anuncia

O campo `riscos` é texto livre. Exemplo real do id 45000:

> "Chuva entre 20 e 30 mm/h ou até 50 mm/dia, ventos intensos (40-60 km/h). Baixo risco de corte
> de energia elétrica, queda de galhos de árvores, alagamentos…"

**Files:**
- Modify: `src/avisos.py`
- Test: `tests/test_avisos.py`

**Interfaces:**
- Produces: `criterio_mm_dia(texto) -> float | None` e `criterio_rajada_ms(texto) -> float | None`.
  O segundo já converte km/h para m/s, que é a unidade de `VENTO, RAJADA MAXIMA` no dado do INMET.

- [ ] **Step 1: Escrever o teste que falha**

```python
RISCO_REAL = ("Chuva entre 20 e 30 mm/h ou até 50 mm/dia, ventos intensos (40-60 km/h). "
              "Baixo risco de corte de energia elétrica, queda de galhos de árvores, alagamentos")


def test_extrai_mm_por_dia():
    assert av.criterio_mm_dia(RISCO_REAL) == 50.0
    assert av.criterio_mm_dia("Chuva de até 100 mm/dia") == 100.0
    assert av.criterio_mm_dia("Chuva entre 30 e 60 mm/dia") == 30.0  # limite INFERIOR


def test_extrai_rajada_em_metros_por_segundo():
    """O aviso anuncia km/h; a estação mede m/s. 40 km/h = 11,11 m/s."""
    assert av.criterio_rajada_ms(RISCO_REAL) == pytest.approx(40 / 3.6, abs=1e-6)
    assert av.criterio_rajada_ms("ventos acima de 100 km/h") == pytest.approx(100 / 3.6, abs=1e-6)


def test_sem_criterio_devolve_none():
    assert av.criterio_mm_dia("Baixa umidade relativa do ar entre 12% e 20%") is None
    assert av.criterio_rajada_ms("Chuva de até 50 mm/dia") is None
    assert av.criterio_mm_dia(None) is None
    assert av.criterio_rajada_ms(None) is None


def test_mm_por_hora_nao_e_confundido_com_mm_por_dia():
    """'20 e 30 mm/h' aparece antes de '50 mm/dia' na mesma frase."""
    assert av.criterio_mm_dia("Chuva entre 20 e 30 mm/h") is None
```

- [ ] **Step 2: Rodar e ver falhar**

Rodar: `MEM_MAX=4G ./run.sh -m pytest tests/test_avisos.py -q -k criterio`
Esperado: FAIL com `AttributeError: module 'src.avisos' has no attribute 'criterio_mm_dia'`.

- [ ] **Step 3: Implementar**

```python
# O limite INFERIOR da faixa anunciada é o que se verifica. "Entre 30 e 60 mm/dia"
# promete pelo menos 30; exigir 60 seria cobrar do aviso o pior caso que ele
# mencionou como teto, e não o patamar que ele comunicou.
_MM_DIA = re.compile(r'(\d+(?:[.,]\d+)?)\s*(?:e\s*\d+(?:[.,]\d+)?\s*)?mm\s*/\s*dia', re.I)
_FAIXA_MM_DIA = re.compile(r'entre\s*(\d+(?:[.,]\d+)?)\s*e\s*(\d+(?:[.,]\d+)?)\s*mm\s*/\s*dia', re.I)
_KMH = re.compile(r'(\d+(?:[.,]\d+)?)\s*(?:-|a|e)?\s*(?:\d+(?:[.,]\d+)?)?\s*km\s*/\s*h', re.I)


def _numero(txt):
    return float(txt.replace(',', '.'))


def criterio_mm_dia(texto):
    """Volume diário anunciado, em mm. None se o aviso não anuncia acumulado diário."""
    if not isinstance(texto, str):
        return None
    faixa = _FAIXA_MM_DIA.search(texto)
    if faixa:
        return _numero(faixa.group(1))
    achado = _MM_DIA.search(texto)
    return _numero(achado.group(1)) if achado else None


def criterio_rajada_ms(texto):
    """Rajada anunciada, convertida de km/h para m/s. None se o aviso não anuncia vento."""
    if not isinstance(texto, str):
        return None
    achado = _KMH.search(texto)
    return _numero(achado.group(1)) / 3.6 if achado else None
```

- [ ] **Step 4: Rodar e ver passar**

Rodar: `MEM_MAX=4G ./run.sh -m pytest tests/test_avisos.py -q`
Esperado: PASS, 9 testes.

- [ ] **Step 5: Conferir à mão numa amostra real** — este passo é obrigatório e não é formalidade

Depois que a colheita da Task 1 terminar:

```bash
MEM_MAX=6G ./run.sh - <<'EOF'
import pandas as pd, glob
from src.avisos import criterio_mm_dia, criterio_rajada_ms
df = pd.concat([pd.read_parquet(f) for f in glob.glob('cache/avisos_inmet/*.parquet')])
df = df[df.obtido & df.descricao.isin(['Chuvas Intensas','Tempestade','Acumulado de Chuva','Vendaval'])]
df['mm'] = df.riscos.map(criterio_mm_dia)
df['ms'] = df.riscos.map(criterio_rajada_ms)
print('avisos dos 4 tipos:', len(df))
print('com critério de chuva: %.1f%% | com critério de vento: %.1f%%'
      % (100*df.mm.notna().mean(), 100*df.ms.notna().mean()))
print('nenhum dos dois: %.1f%%' % (100*(df.mm.isna() & df.ms.isna()).mean()))
print('\n20 amostras para conferência manual:')
for _, r in df.sample(20, random_state=42).iterrows():
    print(f"  mm={r.mm} ms={r.ms:.1f}" if pd.notna(r.ms) else f"  mm={r.mm} ms=None", '|', str(r.riscos)[:105])
EOF
```

Ler as 20 linhas e confirmar que os números batem com o texto. **Se a fração sem nenhum critério
passar de 10%, parar e ajustar as expressões antes de seguir** — número extraído errado contamina
o estudo inteiro e não aparece em nenhum teste.

- [ ] **Step 6: Commit**

```bash
git add src/avisos.py tests/test_avisos.py
git commit -m "Extrai do texto livre o critério que cada aviso anuncia"
```

---

### Task 4: Casar avisos com estação-dia

**Files:**
- Modify: `src/avisos.py`
- Test: `tests/test_avisos.py`

**Interfaces:**
- Produces: `estacoes_do_aviso(aviso, estacoes) -> list[str]` e
  `expandir_estacao_dia(avisos, estacoes, hora_emissao=12) -> pd.DataFrame` com colunas
  `estacao_codigo`, `dia` (date, ancorado em `hora_emissao` UTC), `id`, `descricao`, `severidade`,
  `id_severidade`, `criterio_mm`, `criterio_ms`. Uma linha por (estação, dia, aviso).

- [ ] **Step 1: Escrever o teste que falha**

```python
ESTACOES = pd.DataFrame({'estacao_codigo': ['A801', 'A802'],
                         'latitude': [-29.0, -19.5], 'longitude': [-51.0, -44.5]})


def test_estacoes_do_aviso_usa_a_geometria():
    aviso = {'poligono': json.dumps(QUADRADO)}
    assert av.estacoes_do_aviso(aviso, ESTACOES) == ['A801']


def test_vigencia_de_um_dia_gera_um_dia():
    avisos = pd.DataFrame([{
        'id': 1, 'poligono': json.dumps(QUADRADO), 'descricao': 'Chuvas Intensas',
        'severidade': 'Perigo', 'id_severidade': 7,
        'data_inicio': '2025-03-10T00:00:00.000Z', 'hora_inicio': '13:00',
        'data_fim': '2025-03-10T00:00:00.000Z', 'hora_fim': '23:00',
        'riscos': 'Chuva de até 50 mm/dia'}])
    r = av.expandir_estacao_dia(avisos, ESTACOES)
    assert list(r['estacao_codigo']) == ['A801']
    assert str(r['dia'].iloc[0]) == '2025-03-10'
    assert r['criterio_mm'].iloc[0] == 50.0


def test_vigencia_que_cruza_o_ancoramento_gera_dois_dias():
    """Ancorado às 12 UTC: quem começa dia 10 às 06:00 e termina dia 11 às 06:00
    toca o dia pluviométrico de 09 (que vai até 10 às 12) e o de 10."""
    avisos = pd.DataFrame([{
        'id': 2, 'poligono': json.dumps(QUADRADO), 'descricao': 'Tempestade',
        'severidade': 'Perigo', 'id_severidade': 7,
        'data_inicio': '2025-03-10T00:00:00.000Z', 'hora_inicio': '06:00',
        'data_fim': '2025-03-11T00:00:00.000Z', 'hora_fim': '06:00',
        'riscos': 'Chuva de até 50 mm/dia'}])
    dias = sorted(str(d) for d in av.expandir_estacao_dia(avisos, ESTACOES)['dia'])
    assert dias == ['2025-03-09', '2025-03-10']


def test_tipo_fora_do_recorte_nao_entra():
    avisos = pd.DataFrame([{
        'id': 3, 'poligono': json.dumps(QUADRADO), 'descricao': 'Baixa Umidade',
        'severidade': 'Perigo', 'id_severidade': 7,
        'data_inicio': '2025-03-10T00:00:00.000Z', 'hora_inicio': '13:00',
        'data_fim': '2025-03-10T00:00:00.000Z', 'hora_fim': '23:00',
        'riscos': 'Umidade entre 12% e 20%'}])
    assert av.expandir_estacao_dia(avisos, ESTACOES).empty
```

- [ ] **Step 2: Rodar e ver falhar**

Rodar: `MEM_MAX=4G ./run.sh -m pytest tests/test_avisos.py -q -k "aviso or vigencia or tipo_fora"`
Esperado: FAIL com `AttributeError: ... 'estacoes_do_aviso'`.

- [ ] **Step 3: Implementar**

```python
TIPOS_INCLUIDOS = ('Chuvas Intensas', 'Tempestade', 'Acumulado de Chuva', 'Vendaval')


def estacoes_do_aviso(aviso, estacoes):
    """Códigos das estações cuja coordenada cai dentro do polígono do aviso."""
    geom = aviso.get('poligono') if isinstance(aviso, dict) else aviso['poligono']
    return [r.estacao_codigo for r in estacoes.itertuples()
            if ponto_em_poligono(r.longitude, r.latitude, geom)]


def _instante(data, hora):
    """'2025-03-10T00:00:00.000Z' + '13:00' -> Timestamp UTC."""
    dia = pd.to_datetime(str(data)[:10], utc=True)
    h, m = (str(hora) + ':00').split(':')[:2]
    return dia + pd.Timedelta(hours=int(h), minutes=int(m))


def expandir_estacao_dia(avisos, estacoes, hora_emissao=12):
    """Uma linha por (estação, dia pluviométrico, aviso).

    O dia é ancorado em `hora_emissao` UTC — mesma unidade de todo o resto do
    projeto, porque 12 UTC é o início do dia pluviométrico do INMET. Um aviso que
    vige das 06:00 do dia 10 às 06:00 do dia 11 toca DOIS dias pluviométricos, e
    perder isso subestimaria a cobertura dos avisos.
    """
    linhas = []
    for aviso in avisos.to_dict('records'):
        if aviso.get('descricao') not in TIPOS_INCLUIDOS:
            continue
        codigos = estacoes_do_aviso(aviso, estacoes)
        if not codigos:
            continue
        inicio = _instante(aviso['data_inicio'], aviso['hora_inicio'])
        fim = _instante(aviso['data_fim'], aviso['hora_fim'])
        if fim < inicio:
            fim = inicio
        # Dia pluviométrico D = [D 12:00, D+1 12:00). O primeiro dia tocado é o
        # que contém `inicio`; o último é o que contém `fim`.
        primeiro = (inicio - pd.Timedelta(hours=hora_emissao)).normalize()
        ultimo = (fim - pd.Timedelta(hours=hora_emissao)).normalize()
        dias = pd.date_range(primeiro, ultimo, freq='D')
        mm = criterio_mm_dia(aviso.get('riscos'))
        ms = criterio_rajada_ms(aviso.get('riscos'))
        for codigo in codigos:
            for dia in dias:
                linhas.append({'estacao_codigo': codigo, 'dia': dia.date(),
                               'id': aviso['id'], 'descricao': aviso['descricao'],
                               'severidade': aviso.get('severidade'),
                               'id_severidade': aviso.get('id_severidade'),
                               'criterio_mm': mm, 'criterio_ms': ms})
    return pd.DataFrame(linhas, columns=['estacao_codigo', 'dia', 'id', 'descricao',
                                         'severidade', 'id_severidade',
                                         'criterio_mm', 'criterio_ms'])
```

- [ ] **Step 4: Rodar e ver passar**

Rodar: `MEM_MAX=4G ./run.sh -m pytest tests/test_avisos.py -q`
Esperado: PASS, 13 testes.

- [ ] **Step 5: Commit**

```bash
git add src/avisos.py tests/test_avisos.py
git commit -m "Casa aviso com estação-dia por geometria e vigência"
```

---

### Task 5: O painel de estação-dia — com os negativos

**A ausência de aviso é o negativo**, e sem ele não existe recall: não dá para dizer "os avisos
capturam X% dos eventos observados", que é a frase central do estudo. Esta tarefa constrói o painel
completo da janela, com e sem aviso.

**Files:**
- Create: `scripts/medir_lacuna_avisos.py`
- Modify: `src/avisos.py`
- Test: `tests/test_avisos.py`

**Interfaces:**
- Produces em `src/avisos.py`: `taxa_confirmacao(confirmados) -> tuple[float, tuple[float, float]]`
  (proporção e intervalo de 95% por Wilson).
- Produces em `scripts/medir_lacuna_avisos.py`: `observacao_estacao_dia(df) -> pd.DataFrame` com
  `estacao_codigo`, `dia`, `chuva_24h_obs`, `rajada_max_obs`; e
  `painel(obs, par, limiar_mm) -> pd.DataFrame` acrescentando `tem_aviso`, `id_severidade`,
  `criterio_mm`, `criterio_ms`, `evento`.

- [ ] **Step 1: Escrever o teste que falha**

```python
def test_taxa_confirmacao_e_intervalo():
    p, (lo, hi) = av.taxa_confirmacao(np.array([1, 1, 1, 0, 0, 0, 0, 0, 0, 0]))
    assert p == pytest.approx(0.3)
    assert lo < 0.3 < hi
    assert 0.0 <= lo and hi <= 1.0


def test_intervalo_de_wilson_nao_degenera_com_zero_confirmacoes():
    """Com 0 de 20, o intervalo normal daria [0, 0] — afirmação forte demais."""
    p, (lo, hi) = av.taxa_confirmacao(np.zeros(20, dtype=int))
    assert p == 0.0
    assert lo == 0.0 and hi > 0.05
```

- [ ] **Step 2: Rodar e ver falhar**

Rodar: `MEM_MAX=4G ./run.sh -m pytest tests/test_avisos.py -q -k taxa`
Esperado: FAIL com `AttributeError: ... 'taxa_confirmacao'`.

- [ ] **Step 3: Implementar a função pura em `src/avisos.py`**

```python
def taxa_confirmacao(confirmados, z=1.96):
    """Proporção confirmada, com intervalo de 95% por Wilson.

    Wilson e não normal: com poucas dezenas de avisos por nível, o intervalo
    normal escapa de [0,1] e colapsa para largura zero quando não há nenhuma
    confirmação — o que afirmaria "a taxa é exatamente 0%", forte demais.

    NÃO é taxa de acerto. Aviso não confirmado é risco comunicado que não se
    materializou, que é o funcionamento normal de um sistema de alerta.
    """
    c = np.asarray(confirmados).astype(float)
    n = len(c)
    if n == 0:
        return float('nan'), (float('nan'), float('nan'))
    p = c.mean()
    denom = 1 + z**2 / n
    centro = (p + z**2 / (2 * n)) / denom
    margem = z * np.sqrt(p * (1 - p) / n + z**2 / (4 * n**2)) / denom
    return float(p), (float(max(0.0, centro - margem)), float(min(1.0, centro + margem)))
```

- [ ] **Step 4: Rodar e ver passar**

Rodar: `MEM_MAX=4G ./run.sh -m pytest tests/test_avisos.py -q`
Esperado: PASS, 15 testes.

- [ ] **Step 5: Escrever o medidor, carregando o dado UMA vez**

```python
"""Quanta informação do aviso regional sobrevive até a estação de quem foi avisado?

NÃO mede erro. Aviso é comunicação de risco: aviso não confirmado é risco que não
se materializou, que é o funcionamento normal de um sistema de alerta. O que se
mede é TAXA DE CONFIRMAÇÃO, que é calibração — e a mesma régua se aplica à nossa
própria regra sobre o ECMWF quando as duas forem comparadas.

Desenho em reports/desenho_estudo_avisos_2026_08_20.md

Uso:
    MEM_MAX=11G ./run.sh scripts/medir_lacuna_avisos.py
"""
import glob
import logging

import numpy as np
import pandas as pd

from src.avisos import expandir_estacao_dia, taxa_confirmacao
from src.config import CACHE_DIR, EXTREME_RAIN_THRESHOLD, REPORTS_DIR
from src.ingestion import load_data

logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s %(levelname)s %(name)s — %(message)s',
                    datefmt='%H:%M:%S')
logger = logging.getLogger('lacuna')

HORA_EMISSAO = 12
CHUVA = 'PRECIPITAÇÃO TOTAL, HORÁRIO (mm)'
RAJADA = 'VENTO, RAJADA MAXIMA (m/s)'
INICIO_JANELA, FIM_JANELA = '2025-01-02', '2026-07-31'


def observacao_estacao_dia(df):
    """Chuva acumulada e rajada máxima por dia pluviométrico (12 UTC a 12 UTC)."""
    data = df['DATA (YYYY-MM-DD)'].fillna(df['Data']).astype(str).str.replace('/', '-', regex=False)
    hora = df['HORA (UTC)'].fillna(df['Hora UTC']).astype(str).str.slice(0, 2)
    dh = pd.to_datetime(data + ' ' + hora, format='%Y-%m-%d %H', errors='coerce', utc=True)
    t = pd.DataFrame({'estacao_codigo': df['estacao_codigo'].astype(str), 'dh': dh,
                      'mm': pd.to_numeric(df[CHUVA], errors='coerce'),
                      'ms': pd.to_numeric(df[RAJADA], errors='coerce')}).dropna(subset=['dh'])
    t['dia'] = (t['dh'] - pd.Timedelta(hours=HORA_EMISSAO)).dt.date
    g = t.groupby(['estacao_codigo', 'dia'], observed=True).agg(
        chuva_24h_obs=('mm', 'sum'), rajada_max_obs=('ms', 'max'),
        horas=('mm', 'count')).reset_index()
    # Menos de 18 horas medidas não sustentam um acumulado de 24 h.
    g = g[g['horas'] >= 18].drop(columns='horas')
    return g[(g['dia'] >= pd.Timestamp(INICIO_JANELA).date())
             & (g['dia'] <= pd.Timestamp(FIM_JANELA).date())]


def estacoes_de(df):
    e = (df[['estacao_codigo', 'latitude', 'longitude']].dropna()
         .groupby('estacao_codigo', observed=True).first().reset_index())
    e['estacao_codigo'] = e['estacao_codigo'].astype(str)
    return e


def carregar_avisos():
    arquivos = sorted(glob.glob(str(CACHE_DIR / 'avisos_inmet' / '*.parquet')))
    if not arquivos:
        raise SystemExit('cache de avisos vazio — rode scripts/colher_avisos_inmet.py antes')
    df = pd.concat([pd.read_parquet(f) for f in arquivos], ignore_index=True)
    logger.info('%d identificadores tentados | %d obtidos (%.1f%%)',
                len(df), int(df['obtido'].sum()), 100 * df['obtido'].mean())
    return df[df['obtido']].copy()


def painel(obs, par, limiar_mm=EXTREME_RAIN_THRESHOLD):
    """Todo estação-dia da janela, com e SEM aviso.

    O negativo é o que permite calcular recall. Sem ele só existe taxa de
    confirmação, e a frase "os avisos capturam X% dos eventos observados" — que é
    o resultado central — não pode ser dita.

    Quando mais de um aviso cobre o mesmo estação-dia, vale o de maior severidade,
    e os critérios ficam os mais brandos entre eles (o menor mm e o menor m/s):
    basta o fenômeno de qualquer aviso vigente ter ocorrido.
    """
    coberto = (par.groupby(['estacao_codigo', 'dia'], observed=True)
               .agg(id_severidade=('id_severidade', 'max'),
                    criterio_mm=('criterio_mm', 'min'),
                    criterio_ms=('criterio_ms', 'min')).reset_index())
    p = obs.merge(coberto, on=['estacao_codigo', 'dia'], how='left')
    p['tem_aviso'] = p['id_severidade'].notna()
    p['evento'] = p['chuva_24h_obs'] > limiar_mm
    return p
```

- [ ] **Step 6: Rodar e conferir o painel**

```bash
MEM_MAX=11G ./run.sh - <<'EOF'
from scripts.medir_lacuna_avisos import *
from src.ingestion import load_data
df = load_data()
obs, est = observacao_estacao_dia(df), estacoes_de(df)
del df
par = expandir_estacao_dia(carregar_avisos(), est, HORA_EMISSAO)
p = painel(obs, par)
print(f'{len(p)} estação-dias | {p.tem_aviso.mean()*100:.1f}% com aviso | {int(p.evento.sum())} eventos')
print(f'RECALL: {p.loc[p.evento, "tem_aviso"].mean()*100:.1f}% dos eventos tinham aviso vigente')
EOF
```

Esperado: ~24 mil estação-dias e algumas centenas de eventos, coerente com a curva de operação já
medida (324 eventos acima de 50 mm em 24.444 estação-dias). Divergência grande indica desalinhamento
de dia entre as duas fontes.

- [ ] **Step 7: Commit**

```bash
git add src/avisos.py scripts/medir_lacuna_avisos.py tests/test_avisos.py
git commit -m "Painel de estação-dia com os negativos, para que exista recall"
```

---

### Task 6: As duas unidades, a comparação e o relatório

**Files:**
- Modify: `scripts/medir_lacuna_avisos.py`
- Produz: `reports/lacuna_granularidade_avisos_<AAAA_MM_DD_HH_MM>.md`

**Interfaces:**
- Consumes: `scripts.curva_operacao_ifs.varrer(y, score, cortes) -> pd.DataFrame` com colunas
  `corte`, `alertas`, `acertos`, `precisao`, `recall`, `f1`, `perdidos` — já existe e está testada.

**Decisão de método que simplifica e mantém o rigor:** a comparação com o ECMWF é feita na
**unidade de ponto**, porque ali as duas fontes são avaliadas exatamente nos mesmos estação-dias e
nenhuma é penalizada por diferença de unidade. A taxa de área entra como a leitura justa com quem
emite o aviso, ao lado, e não como base de comparação. Isso dispensa reagregar a previsão por
polígono e elimina a principal fonte de erro do desenho anterior.

- [ ] **Step 1: Escrever as duas unidades e a comparação**

```python
def _confirmado(d):
    """Confirma se QUALQUER critério anunciado foi observado.

    Composto de propósito: 'Chuvas Intensas' também anuncia vento, e exigir os
    dois penalizaria um aviso que acertou o vendaval e não a chuva.
    """
    por_chuva = d['criterio_mm'].notna() & (d['chuva_24h_obs'] >= d['criterio_mm'])
    por_vento = d['criterio_ms'].notna() & (d['rajada_max_obs'] >= d['criterio_ms'])
    return (por_chuva | por_vento).to_numpy()


def _linha(nome, unidade, confirmados, n):
    taxa, (lo, hi) = taxa_confirmacao(confirmados)
    return {'grupo': nome, 'unidade': unidade, 'n': n,
            'taxa_confirmacao': round(taxa, 4), 'ic_inferior': round(lo, 4),
            'ic_superior': round(hi, 4)}


def tabela_unidades(par_com_obs):
    """Taxa de confirmação em PONTO e em ÁREA, por tipo e severidade."""
    par_com_obs = par_com_obs.copy()
    par_com_obs['confirmado'] = _confirmado(par_com_obs)
    linhas = []
    for (desc, sev), g in par_com_obs.groupby(['descricao', 'severidade'], observed=True):
        nome = f'{desc} / {sev}'
        # PONTO: cada (estação, dia, aviso) é uma unidade — o que a pessoa vive.
        linhas.append(_linha(nome, 'ponto', g['confirmado'].to_numpy(), len(g)))
        # ÁREA: o aviso conta como confirmado se QUALQUER estação dele confirmou.
        por_aviso = g.groupby('id', observed=True)['confirmado'].max()
        linhas.append(_linha(nome, 'área', por_aviso.to_numpy(), len(por_aviso)))
    t = pd.DataFrame(linhas)
    lac = (t.pivot(index='grupo', columns='unidade', values='taxa_confirmacao')
           .assign(lacuna=lambda d: d['área'] - d['ponto']).reset_index())
    return t, lac
```

- [ ] **Step 2: Escrever a comparação com o ECMWF, na unidade de ponto**

```python
from scripts.curva_operacao_ifs import varrer

CORTES_MM = [5, 10, 15, 20, 25, 30, 40, 50, 60, 75]


def comparar_com_ecmwf(p, previsao):
    """Recall e taxa de confirmação do aviso, ao lado da curva do ECMWF.

    Mesmos estação-dias nos dois lados, mesmo alvo (chuva observada acima do
    limiar do projeto). Nenhuma das duas fontes é penalizada por unidade.

    A leitura honesta é horizontal: FIXANDO a taxa de confirmação, qual fonte
    captura mais eventos? Isso mantém constante a tolerância a alarme não
    confirmado dos dois lados, e é a única comparação legítima entre um aviso de
    risco e uma regra automática.
    """
    juntos = p.merge(previsao, on=['estacao_codigo', 'dia'], how='inner')
    y = juntos['evento'].to_numpy().astype(int)
    curva = varrer(y, juntos['ifs_chuva_24h'].to_numpy(), CORTES_MM)

    pontos = []
    for sev, g in juntos.groupby(juntos['id_severidade'].fillna(-1), observed=True):
        if sev < 0:
            continue
        alerta = juntos['id_severidade'].fillna(-1) >= sev
        acertos = int(juntos.loc[alerta, 'evento'].sum())
        pontos.append({'fonte': f'aviso INMET, severidade >= {int(sev)}',
                       'alertas': int(alerta.sum()), 'acertos': acertos,
                       'taxa_confirmacao': round(acertos / max(int(alerta.sum()), 1), 3),
                       'recall': round(acertos / max(int(y.sum()), 1), 3)})
    return curva, pd.DataFrame(pontos)
```

`previsao` é um DataFrame com `estacao_codigo`, `dia`, `ifs_chuva_24h`, construído assim — mesmo
caminho de `scripts/curva_operacao_ifs.py`, sem rede porque o cache já está completo:

```python
from src.ingestion import enrich_openmeteo
from src.processing import clean_data, create_features
from scripts.medir_baseline_ifs import _anexar_regua
from scripts.medir_degradacao_mos import _media_futura, _trocar_por_previsao
from scripts.medir_acrescimo_local import INICIO_AJUSTE, separar_ajuste_avaliacao


def previsao_estacao_dia():
    bruto = enrich_openmeteo(clean_data(load_data()))
    fim = bruto['data_hora'].max().strftime('%Y-%m-%d')
    geo = (bruto.groupby('estacao_codigo', observed=True)
           .agg(lat=('latitude', 'first'), lon=('longitude', 'first')))
    bruto = _trocar_por_previsao(bruto, fim, inicio=INICIO_AJUSTE)
    feats = create_features(bruto)
    del bruto
    _aju, ava = separar_ajuste_avaliacao(feats)
    d = _media_futura(feats[ava].copy())
    del feats
    d = _anexar_regua(d, geo, fim, inicio=INICIO_AJUSTE)
    d = d[d['data_hora'].dt.hour == HORA_EMISSAO]
    d = d[['estacao_codigo', 'data_hora', 'ifs_chuva_24h']].dropna()
    d['estacao_codigo'] = d['estacao_codigo'].astype(str)
    d['dia'] = (d['data_hora'] - pd.Timedelta(hours=HORA_EMISSAO)).dt.date
    return d[['estacao_codigo', 'dia', 'ifs_chuva_24h']]
```

- [ ] **Step 3: Escrever o relatório**

```python
def escrever_relatorio(tabela, lacuna, curva, pontos, cobertura, recall_geral):
    destino = REPORTS_DIR / f"lacuna_granularidade_avisos_{pd.Timestamp.now():%Y_%m_%d_%H_%M}.md"
    partes = [
        "# A lacuna de granularidade do alerta regional",
        f"\nGerado em {pd.Timestamp.now():%d/%m/%Y %H:%M}\n",
        "## Como ler estes números\n",
        "Um aviso meteorológico não afirma que o fenômeno vai ocorrer — comunica que há risco "
        "relevante de ocorrer. Aviso não confirmado **não é erro**: a possibilidade existia e "
        "comunicá-la era a função dele. Serviços de alerta aceitam deliberadamente alta taxa de "
        "não confirmação em eventos de alto impacto, porque o custo de não avisar é assimétrico "
        "em relação ao custo de avisar à toa.\n",
        "Portanto o que segue é **taxa de confirmação** — entre os avisos de um nível, em que "
        "fração o fenômeno anunciado foi registrado. É afirmação de calibração, não de acerto. "
        "**A mesma régua se aplica a nós:** a taxa da nossa regra sobre a previsão do ECMWF "
        "também é confirmação, não erro.\n",
        f"\n**Cobertura dos avisos:** {recall_geral}\n",
        "\n## Taxa de confirmação por tipo e severidade\n",
        "**Ponto**: a estação daquele local registrou o anunciado. **Área**: alguma estação dentro "
        "do polígono registrou. As duas nunca são lidas isoladas — a de área superestima o que o "
        "aviso significa para o indivíduo, e a de ponto subestima a qualidade de quem o emitiu.\n",
        tabela.to_markdown(index=False),
        "\n## A lacuna\n",
        "A diferença entre as duas colunas é o resultado central: quantifica quanta informação se "
        "perde entre *o aviso é correto para a região* e *o aviso diz algo sobre a minha rua*.\n",
        lacuna.to_markdown(index=False),
        "\n## Ao lado da previsão do ECMWF, nos mesmos estação-dias\n",
        "Ler na horizontal: fixando a taxa de confirmação, qual fonte captura mais eventos? Isso "
        "mantém constante a tolerância a alarme não confirmado nos dois lados.\n",
        "**Os avisos não são independentes do ECMWF** — o INMET usa modelos globais para "
        "emiti-los. A comparação é *aviso curado por meteorologista, por área* contra *regra "
        "automática de corte*, não humano contra máquina do zero.\n",
        pontos.to_markdown(index=False),
        "\n", curva.to_markdown(index=False),
        f"\n## Cobertura da extração de critérios\n\n{cobertura}\n",
        "\n## Limitações\n",
        "- Os avisos não são independentes da previsão do ECMWF (acima).",
        "- O critério vem de texto livre; a fração não extraível está declarada acima.",
        "- Municípios sem estação não entram: a lacuna medida é a que as estações enxergam.",
        "- A ordem temporal dos identificadores foi verificada por amostragem, não exaustivamente.",
        "- **Rajada é medida num ponto e vendaval convectivo é fenômeno de escala pequena.** A "
        "estação pode não estar onde o vento passou, o que deprime a confirmação de vendaval por "
        "razão instrumental, não meteorológica.",
    ]
    destino.write_text("\n".join(partes) + "\n", encoding='utf-8')
    logger.info('Relatório salvo em %s', destino)
    return destino
```

- [ ] **Step 4: Rodar a suíte inteira**

Rodar: `MEM_MAX=6G ./run.sh -m pytest tests -q`
Esperado: 66 passed (47 de antes + 4 do colhedor + 15 da biblioteca).

- [ ] **Step 5: Rodar o medidor e conferir antes de acreditar**

Rodar: `MEM_MAX=11G ./run.sh scripts/medir_lacuna_avisos.py`

- taxa de **área ≥ taxa de ponto em toda linha**. Se alguma inverter, há erro de agrupamento — a
  área é o máximo sobre as estações do aviso, então não pode ser menor.
- cobertura da extração de critérios **acima de 90%**; abaixo disso, voltar à Task 3.
- o número de eventos tem de bater com a curva de operação já medida (324 acima de 50 mm em
  24.444 estação-dias). Divergência grande significa desalinhamento de dia entre as fontes.
- recall decrescente conforme o corte do ECMWF sobe.

- [ ] **Step 6: Commit**

```bash
git add scripts/medir_lacuna_avisos.py reports/lacuna_granularidade_avisos_*.md
git commit -m "Mede a lacuna entre alerta regional e observação no ponto"
```

---

## O que este plano NÃO faz

- Não treina modelo nenhum e não toca em `models/`.
- Não mede tendência de rajada nos 11 anos — decisão explícita do usuário em 20/08/2026.
- Não constrói nenhuma tela do aplicativo.
- Não avalia avisos de Baixa Umidade, Declínio de Temperatura ou Ventos Costeiros, por falta de
  verdade de campo aplicável a estações de superfície.
