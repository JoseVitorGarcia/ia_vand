# Colheita automática do aviso do INMET — Plano de implementação

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Colher por dia o aviso vigente do INMET para Porto Alegre, regenerar `app/dados.js` com ele e publicar na `main` sem revisão humana, com o app tolerando dias sem aviso.

**Architecture:** Um script Python (`scripts/colher_aviso_poa.py`) busca `avisos/ativos`, escolhe o aviso de chuva mais severo que cobre as 3 estações de POA e escreve `app/dados.js` do zero (atômico; em qualquer falha não toca o arquivo). O app passa a decidir o estado calmo pelo dado e ganha a rota `#/alerta/exemplo`. Um workflow novo roda o script, commita na `main` e dispara o deploy explicitamente.

**Tech Stack:** Python 3.12 (pandas, requests, pytest), JavaScript sem build (`app/app.js`, `app/sw.js`), GitHub Actions.

**Spec:** `docs/superpowers/specs/2026-10-15-colheita-aviso-inmet-design.md`

## Desvios da spec (descobertos lendo o código e a API real em 18/10/2026)

Cada um tem tarefa e teste abaixo. Registrados também na Task 4.

1. **A API devolve `{"hoje": [...], "futuro": [...]}`**, não uma lista. "Vigente" = só `hoje`; `futuro` é ignorado.
2. **`riscos` e `instrucoes` já chegam como lista** (pendência "verificar" da spec resolvida). **`municipios` é uma string separada por vírgula**, então `municipios_total` conta `geocodes.split(',')`.
3. **Só avisos de chuva** (`Chuvas Intensas`, `Tempestade`, `Acumulado de Chuva`). A tela diz "risco de chuva acima de 30 mm" e a tabela de lacuna é "só chuva"; um aviso de Baixa Umidade em POA sairia sob esse texto. A API de hoje tem Baixa Umidade e Ventos Costeiros.
4. **Mudanças feitas pela `GITHUB_TOKEN` não disparam outros workflows.** O push do bot na `main` NÃO acionaria o `deploy.yml` como a spec supõe. Solução: `deploy.yml` ganha `workflow_dispatch` e o `avisos.yml` o aciona com `gh workflow run`.
5. **`app/sw.js` é cache-first com versão fixa.** Sem mudança, quem já abriu o app veria o `dados.js` velho para sempre. Solução: `dados.js` passa a ser rede-primeiro, com cache como reserva offline.
6. **`tests/app_smoke.html` assume que `#/alerta` sempre mostra o aviso 55157.** Passa a testar o aviso em `#/alerta/exemplo` (estável) e a rota padrão conforme o dado.
7. O `colhido_em` muda a cada execução, então o `dados.js` muda todo dia e haverá um commit diário. É o desejado (a tela mostra a data da última consulta).

## Global Constraints

- Nunca ler, exibir ou modificar arquivos `.env` (regra global do usuário).
- Comentários e mensagens em português; nomes de código em português, como no resto do repo.
- Rodar Python sempre por `./run.sh` (cgroup próprio); nunca `python` direto. Baseline antes do plano: `./run.sh -m pytest tests -q` → **69 passed**.
- `app/dados.js` é carregado como `<script>` (não `fetch()`): o app abre em `file://` e o smoke test é síncrono.
- Regra editorial: taxa de confirmação não é taxa de acerto; os 30,3% são da NOSSA Previsão, nunca do aviso do INMET. Não atribuir não-confirmação ao INMET.
- Campos do aviso vão como vêm da API, sem edição; só `inicio`, `fim`, `municipios_total`, `municipio_exemplo`, `geocode_exemplo` são derivados.
- Falha segura: erro de rede, HTTP ruim, formato inesperado ou campo ausente em aviso de POA → exit 1, `app/dados.js` intocado.
- Commit com trailer `Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>`.
- Antes de `git push` e de disparar workflow: **pedir confirmação ao usuário** (ação externa; o direto-na-`main` já foi decidido, mas o push em si é confirmado na hora).

## Review Focus

Entradas que a spec não nomeia e que mais provavelmente quebram, com o teste que as fixa (entre parênteses):

1. Aviso em `futuro` ou com `encerrado: true` não pode virar o aviso do dia (Task 1: `test_ignora_futuro_e_encerrado`).
2. Aviso que cobre POA mas não é de chuva (Baixa Umidade, Ventos Costeiros) → dia sem aviso, não card de chuva (Task 1: `test_ignora_aviso_que_nao_e_de_chuva`).
3. Aviso de outra região com polígono ausente ou inválido não pode derrubar a colheita (Task 1: `test_poligono_ruim_de_outra_regiao_nao_derruba`).
4. Severidade sem linha na tabela de lacuna → sem card de lacuna e sem exceção (Task 1: `test_severidade_fora_da_tabela_de_lacuna`; Task 2: smoke com `lacuna = null`).
5. Horário: `inicio`/`fim` saem como `<data>T<hora>:00Z`, igual ao aviso 55157 e a `src.avisos._instante`. O INMET provavelmente fala em horário de Brasília e o `formatData` converte para o fuso do aparelho, então o horário exibido pode deslocar 3 h. Herdado do protótipo, não corrigido aqui (Task 1: `test_vigencia_no_mesmo_formato_do_aviso_de_exemplo`).

---

### Task 1: `scripts/colher_aviso_poa.py` e seus testes

**Files:**
- Create: `scripts/colher_aviso_poa.py`
- Create: `tests/test_aviso_poa.py`

**Interfaces:**
- Consumes: `src.avisos.estacoes_do_aviso(aviso: dict, estacoes: DataFrame) -> list[str]` (aviso precisa da chave `poligono`; estações com `estacao_codigo`, `latitude`, `longitude`); `colheita/estacoes.parquet`.
- Produces: `app/dados.js` (ou o caminho em `VAND_DADOS_JS`) definindo `window.VAND_DADOS` com chaves `_procedencia`, `colhido_em` (ISO UTC, `...Z`), `aviso` (dict ou `null`), `aviso_exemplo` (dict, fixo, id 55157), `previsao`, `lacuna` (dict ou `null`), `lacuna_exemplo` (dict, fixo, Grande Perigo). `aviso` tem `id, descricao, severidade, aviso_cor, inicio, fim, riscos, instrucoes, municipios_total, municipio_exemplo, geocode_exemplo`. Exit code 0 sucesso, 1 falha. Env `VAND_DADOS_JS` redireciona a escrita (para testes).

- [ ] **Step 1: Escrever os testes (vão falhar: o script não existe)**

Criar `tests/test_aviso_poa.py`:

```python
"""Testes da colheita do aviso do INMET para Porto Alegre.

Mesma filosofia de test_colheita.py: o script roda sem ninguém olhando, então o
código de saída é o único sinal de que o dia falhou, e a falha precisa ser
SEGURA — um dados.js anterior nunca pode ser sobrescrito por lixo.
"""
import json
import runpy

import pandas as pd
import pytest
import requests

SCRIPT = 'scripts/colher_aviso_poa.py'
ANTERIOR = '/* dados.js do dia anterior */'

_est = pd.read_parquet('colheita/estacoes.parquet')
LON0, LAT0 = float(_est.iloc[0].longitude), float(_est.iloc[0].latitude)


def _quadrado(lon, lat, meia=0.5):
    return json.dumps({'type': 'Polygon', 'coordinates': [[
        [lon - meia, lat - meia], [lon + meia, lat - meia],
        [lon + meia, lat + meia], [lon - meia, lat + meia],
        [lon - meia, lat - meia]]]})


def _aviso(id_, severidade='Perigo', descricao='Chuvas Intensas',
           dentro=True, data_inicio='2026-10-18', **extra):
    aviso = {
        'id': id_, 'descricao': descricao, 'severidade': severidade,
        'aviso_cor': '#FF9900',
        'data_inicio': f'{data_inicio}T00:00:00.000Z', 'hora_inicio': '09:00',
        'data_fim': '2026-10-19T00:00:00.000Z', 'hora_fim': '10:00',
        'riscos': ['risco A'], 'instrucoes': ['instrucao A', 'instrucao B'],
        'geocodes': '4314902,4300000',
        'poligono': _quadrado(LON0 if dentro else LON0 + 10, LAT0),
        'encerrado': False,
    }
    aviso.update(extra)
    return aviso


class _Resposta:
    def __init__(self, payload, status=200):
        self._payload, self.status_code = payload, status

    def json(self):
        return self._payload

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError(str(self.status_code))


@pytest.fixture
def ambiente(monkeypatch, tmp_path):
    destino = tmp_path / 'dados.js'
    destino.write_text(ANTERIOR, encoding='utf-8')
    monkeypatch.setenv('VAND_DADOS_JS', str(destino))
    monkeypatch.setattr('time.sleep', lambda s: None)
    monkeypatch.setattr('sys.argv', [SCRIPT])
    return destino


def _servir(monkeypatch, payload, status=200):
    monkeypatch.setattr(requests, 'get',
                        lambda *a, **k: _Resposta(payload, status))


def _rodar():
    try:
        runpy.run_path(SCRIPT, run_name='__main__')
    except SystemExit as saida:
        return saida.code or 0
    return 0


def _ler(destino):
    texto = destino.read_text(encoding='utf-8')
    corpo = texto.split('window.VAND_DADOS = ', 1)[1].strip().rstrip(';')
    return json.loads(corpo)


def test_aviso_sobre_poa_vira_dados_js(ambiente, monkeypatch):
    _servir(monkeypatch, {'hoje': [_aviso(900, 'Grande Perigo')], 'futuro': []})
    assert _rodar() == 0
    dados = _ler(ambiente)
    aviso = dados['aviso']
    assert aviso['id'] == 900
    assert aviso['severidade'] == 'Grande Perigo'
    assert aviso['riscos'] == ['risco A']
    assert aviso['instrucoes'] == ['instrucao A', 'instrucao B']
    assert aviso['municipios_total'] == 2
    assert aviso['municipio_exemplo'] == 'Porto Alegre - RS'
    assert aviso['geocode_exemplo'] == '4314902'
    assert dados['lacuna']['severidade'] == 'Grande Perigo'
    assert dados['lacuna']['razao'] == 19.1
    assert dados['aviso_exemplo']['id'] == 55157
    assert dados['lacuna_exemplo']['severidade'] == 'Grande Perigo'
    assert dados['previsao']['taxa_confirmacao'] == 0.303
    assert dados['colhido_em'].endswith('Z')


def test_vigencia_no_mesmo_formato_do_aviso_de_exemplo(ambiente, monkeypatch):
    _servir(monkeypatch, {'hoje': [_aviso(900)]})
    assert _rodar() == 0
    aviso = _ler(ambiente)['aviso']
    assert aviso['inicio'] == '2026-10-18T09:00:00Z'
    assert aviso['fim'] == '2026-10-19T10:00:00Z'


def test_vence_o_mais_severo(ambiente, monkeypatch):
    _servir(monkeypatch, {'hoje': [_aviso(1, 'Perigo Potencial'),
                                   _aviso(2, 'Grande Perigo'),
                                   _aviso(3, 'Perigo')]})
    assert _rodar() == 0
    assert _ler(ambiente)['aviso']['id'] == 2


def test_empate_de_severidade_vence_o_inicio_mais_recente(ambiente, monkeypatch):
    _servir(monkeypatch, {'hoje': [_aviso(1, data_inicio='2026-10-17'),
                                   _aviso(2, data_inicio='2026-10-18')]})
    assert _rodar() == 0
    assert _ler(ambiente)['aviso']['id'] == 2


def test_sem_aviso_sobre_poa_gera_estado_vazio(ambiente, monkeypatch):
    _servir(monkeypatch, {'hoje': [_aviso(1, dentro=False)], 'futuro': []})
    assert _rodar() == 0
    dados = _ler(ambiente)
    assert dados['aviso'] is None
    assert dados['lacuna'] is None
    assert dados['aviso_exemplo']['id'] == 55157
    assert dados['colhido_em']


def test_ignora_futuro_e_encerrado(ambiente, monkeypatch):
    _servir(monkeypatch, {'hoje': [_aviso(1, encerrado=True)],
                          'futuro': [_aviso(2, 'Grande Perigo')]})
    assert _rodar() == 0
    assert _ler(ambiente)['aviso'] is None


def test_ignora_aviso_que_nao_e_de_chuva(ambiente, monkeypatch):
    _servir(monkeypatch, {'hoje': [_aviso(1, 'Grande Perigo', descricao='Baixa Umidade'),
                                   _aviso(2, 'Perigo', descricao='Ventos Costeiros')]})
    assert _rodar() == 0
    assert _ler(ambiente)['aviso'] is None


def test_poligono_ruim_de_outra_regiao_nao_derruba(ambiente, monkeypatch):
    sem = _aviso(1)
    del sem['poligono']
    _servir(monkeypatch, {'hoje': [sem, _aviso(2, poligono='isto nao e json'),
                                   _aviso(3, 'Perigo')]})
    assert _rodar() == 0
    assert _ler(ambiente)['aviso']['id'] == 3


def test_severidade_fora_da_tabela_de_lacuna(ambiente, monkeypatch):
    _servir(monkeypatch, {'hoje': [_aviso(1, 'Severidade Nova')]})
    assert _rodar() == 0
    dados = _ler(ambiente)
    assert dados['aviso']['severidade'] == 'Severidade Nova'
    assert dados['lacuna'] is None


@pytest.mark.parametrize('payload', [
    [],                                  # lista, não dict
    {'sem_hoje': []},                    # chave esperada ausente
    {'hoje': 'texto'},                   # tipo errado
])
def test_formato_inesperado_sai_com_1_e_preserva(ambiente, monkeypatch, payload):
    _servir(monkeypatch, payload)
    assert _rodar() == 1
    assert ambiente.read_text(encoding='utf-8') == ANTERIOR


def test_campo_ausente_em_aviso_de_poa_sai_com_1_e_preserva(ambiente, monkeypatch):
    quebrado = _aviso(1)
    del quebrado['instrucoes']
    _servir(monkeypatch, {'hoje': [quebrado]})
    assert _rodar() == 1
    assert ambiente.read_text(encoding='utf-8') == ANTERIOR


def test_http_500_sai_com_1_e_preserva(ambiente, monkeypatch):
    _servir(monkeypatch, {'hoje': []}, status=500)
    assert _rodar() == 1
    assert ambiente.read_text(encoding='utf-8') == ANTERIOR


def test_rede_fora_sai_com_1_e_preserva(ambiente, monkeypatch):
    def cai(*a, **k):
        raise requests.ConnectionError('sem rede')

    monkeypatch.setattr(requests, 'get', cai)
    assert _rodar() == 1
    assert ambiente.read_text(encoding='utf-8') == ANTERIOR
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `./run.sh -m pytest tests/test_aviso_poa.py -q`
Expected: todos FALHAM (o script não existe: `FileNotFoundError`/`No such file`).

- [ ] **Step 3: Implementar o script**

Criar `scripts/colher_aviso_poa.py`:

```python
"""Colhe o aviso vigente do INMET para Porto Alegre e regenera app/dados.js.

Roda sem supervisão (GitHub Actions, .github/workflows/avisos.yml). Por isso a
regra de ouro é a falha segura: qualquer erro de rede, HTTP ruim, formato
inesperado ou campo ausente num aviso de Porto Alegre termina com exit 1 e NÃO
toca o dados.js — o do dia anterior continua valendo. O código de saída é o
único aviso de que o dia falhou.

Escolhas que a spec (docs/superpowers/specs/2026-10-15-colheita-aviso-inmet-design.md)
não previa, descobertas contra a API real em 18/10/2026:
  - a resposta é {"hoje": [...], "futuro": [...]}; vigente = só "hoje";
  - só avisos de CHUVA entram: o texto da tela fala de chuva acima de 30 mm e a
    tabela de lacuna é "só chuva";
  - `municipios` é uma string; o total sai de `geocodes`.

Uso:
    ./run.sh scripts/colher_aviso_poa.py
"""
import json
import logging
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import requests

from src.avisos import estacoes_do_aviso

logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s %(levelname)s %(name)s — %(message)s',
                    datefmt='%H:%M:%S')
logger = logging.getLogger('aviso_poa')

RAIZ = Path(__file__).resolve().parent.parent
URL = 'https://apiprevmet3.inmet.gov.br/avisos/ativos'
# Mesmo User-Agent de cortesia de colher_avisos_inmet.py.
CABECALHOS = {'User-Agent': 'IA_VAND/1.0 (pesquisa academica; UFRGS)'}
ESTACOES = RAIZ / 'colheita' / 'estacoes.parquet'
DESTINO = Path(os.environ.get('VAND_DADOS_JS', RAIZ / 'app' / 'dados.js'))

TIPOS_CHUVA = ('Chuvas Intensas', 'Tempestade', 'Acumulado de Chuva')
GRAVIDADE = {'Grande Perigo': 3, 'Perigo': 2, 'Perigo Potencial': 1}
CAMPOS_OBRIGATORIOS = ('id', 'descricao', 'severidade', 'aviso_cor',
                       'data_inicio', 'hora_inicio', 'data_fim', 'hora_fim',
                       'riscos', 'instrucoes', 'geocodes')

# Tabela "só chuva" de reports/lacuna_granularidade_avisos_2026_08_21_00_29.md.
LACUNA = {
    'Grande Perigo': (0.591, 0.031, 19.1),
    'Perigo': (0.564, 0.075, 7.5),
    'Perigo Potencial': (0.309, 0.038, 8.1),
}
LACUNA_FONTE = 'reports/lacuna_granularidade_avisos_2026_08_21_00_29.md'
LACUNA_NOTA = ('Enquadramento e lacuna de granularidade: o aviso e produto de '
               'area recebido num ponto. Nao e avaliacao de quem preve melhor.')

PREVISAO = {
    'regra': 'ECMWF > 30 mm',
    'taxa_confirmacao': 0.303,
    'recall': 0.709,
    'n_alertas': 750,
    'acertos': 227,
    'fonte': LACUNA_FONTE,
    'nota_editorial': ('Taxa de confirmacao NAO e taxa de acerto. Refere-se a '
                       'NOSSA Previsao, nunca ao aviso do INMET.'),
}

# Aviso 55157, colhido em jul/2026 (cache/avisos_inmet/avisos_54935_55192.parquet).
# Fixo: alimenta #/alerta/exemplo e NUNCA é sobrescrito pela colheita.
AVISO_EXEMPLO = {
    'id': 55157,
    'descricao': 'Acumulado de Chuva',
    'severidade': 'Grande Perigo',
    'aviso_cor': '#F80703',
    'inicio': '2026-07-28T09:00:00Z',
    'fim': '2026-07-29T10:00:00Z',
    'riscos': [
        'Chuva superior a 60 mm/h ou acima de 100 mm/dia. Grande risco de '
        'grandes alagamentos e transbordamentos de rios, grandes '
        'deslizamentos de encostas,   em cidades com tais áreas de risco.'
    ],
    'instrucoes': [
        'Desligue aparelhos elétricos, quadro geral de energia.',
        'Observe alteração nas encostas.',
        'Permaneça em local abrigado.',
        'Em caso de situação de inundação, ou similar, proteja seus pertences '
        'da água envoltos em sacos plásticos.',
        'Obtenha mais informações junto à Defesa Civil (telefone 199) e ao '
        'Corpo de Bombeiros (telefone 193).'
    ],
    'municipios_total': 531,
    'municipio_exemplo': 'Porto Alegre - RS',
    'geocode_exemplo': '4314902',
}

CABECALHO = """/*
 * Dado que alimenta as abas Alerta e Registro.
 *
 * ARQUIVO AUTOGERADO por scripts/colher_aviso_poa.py em @@QUANDO@@.
 * NÃO edite à mão: a próxima colheita (.github/workflows/avisos.yml) sobrescreve.
 *
 * PROCEDÊNCIA — nada aqui é inventado. `aviso` é o aviso de chuva mais severo
 * que cobre Porto Alegre em https://apiprevmet3.inmet.gov.br/avisos/ativos, com
 * os campos originais da API, sem edição (ou null num dia sem aviso).
 * `aviso_exemplo` é o aviso 55157 (jul/2026), FIXO: alimenta #/alerta/exemplo e
 * nunca é sobrescrito pela colheita. Os números de `previsao` e `lacuna` vêm de
 * reports/lacuna_granularidade_avisos_2026_08_21_00_29.md.
 *
 * REGRA EDITORIAL (docs/design/brief_telas_alerta_registro.md): taxa de
 * confirmação não é taxa de acerto, e os 30,3% são da NOSSA Previsão — nunca
 * do aviso do INMET. Não atribuir não-confirmação ao INMET.
 *
 * Carregado como script, e não por fetch(), de propósito: o app precisa rodar
 * em file:// e tests/app_smoke.html roda síncrono. Mesmo padrão de content.js.
 */
"""


def buscar_ativos(tentativas=3):
    """GET avisos/ativos. Levanta a última exceção se todas as tentativas falham."""
    espera = 5
    for tentativa in range(tentativas):
        try:
            resposta = requests.get(URL, headers=CABECALHOS, timeout=30)
            resposta.raise_for_status()
            return resposta.json()
        except Exception as exc:
            logger.warning('tentativa %d/%d falhou: %s', tentativa + 1, tentativas, exc)
            if tentativa + 1 == tentativas:
                raise
            time.sleep(espera)
            espera *= 2


def _instante(data, hora):
    """Mesmo formato do aviso de exemplo: '2026-10-18' + '09:00' -> '...T09:00:00Z'."""
    return f'{str(data)[:10]}T{hora}:00Z'


def candidatos(payload, estacoes):
    """Avisos de chuva vigentes (`hoje`) que cobrem alguma estação de Porto Alegre."""
    if not isinstance(payload, dict) or not isinstance(payload.get('hoje'), list):
        raise ValueError('formato inesperado: esperava {"hoje": [...]}')
    achados = []
    for aviso in payload['hoje']:
        if aviso.get('encerrado') or aviso.get('descricao') not in TIPOS_CHUVA:
            continue
        try:
            cobre = bool(estacoes_do_aviso(aviso, estacoes))
        except (KeyError, TypeError, ValueError) as exc:
            # Polígono ausente/ilegível num aviso de qualquer lugar do Brasil
            # não pode impedir a colheita de Porto Alegre.
            logger.warning('aviso %s ignorado, polígono inutilizável: %r',
                           aviso.get('id'), exc)
            continue
        if not cobre:
            continue
        faltando = [c for c in CAMPOS_OBRIGATORIOS if aviso.get(c) in (None, '')]
        if faltando:
            raise ValueError(f'aviso {aviso.get("id")} sobre Porto Alegre sem {faltando}')
        achados.append(aviso)
    return achados


def escolher(avisos):
    """Mais severo; no empate, o de data_inicio mais recente."""
    if not avisos:
        return None
    return max(avisos, key=lambda a: (GRAVIDADE.get(a['severidade'], 0),
                                      a['data_inicio']))


def montar_aviso(a):
    return {
        'id': a['id'],
        'descricao': a['descricao'],
        'severidade': a['severidade'],
        'aviso_cor': a['aviso_cor'],
        'inicio': _instante(a['data_inicio'], a['hora_inicio']),
        'fim': _instante(a['data_fim'], a['hora_fim']),
        'riscos': a['riscos'],
        'instrucoes': a['instrucoes'],
        'municipios_total': len([g for g in a['geocodes'].split(',') if g.strip()]),
        'municipio_exemplo': 'Porto Alegre - RS',
        'geocode_exemplo': '4314902',
    }


def _linha_lacuna(severidade):
    if severidade not in LACUNA:
        return None
    area, ponto, razao = LACUNA[severidade]
    return {'severidade': severidade, 'taxa_area': area, 'taxa_ponto': ponto,
            'razao': razao, 'fonte': LACUNA_FONTE, 'nota_editorial': LACUNA_NOTA}


def montar_dados(aviso, colhido_em):
    return {
        '_procedencia': {
            'origem': URL,
            'nota': ('Aviso real colhido da API de avisos do INMET. Campos '
                     'originais, sem edicao, exceto vigencia (inicio/fim) e '
                     'municipios_total, derivados. Recortado para Porto Alegre '
                     'porque o prototipo nao tem geolocalizacao.'),
        },
        'colhido_em': colhido_em,
        'aviso': montar_aviso(aviso) if aviso else None,
        'aviso_exemplo': AVISO_EXEMPLO,
        'previsao': PREVISAO,
        'lacuna': _linha_lacuna(aviso['severidade']) if aviso else None,
        'lacuna_exemplo': _linha_lacuna('Grande Perigo'),
    }


def gravar(dados, colhido_em):
    """Escrita atômica: um dados.js pela metade nunca vai ao ar."""
    texto = (CABECALHO.replace('@@QUANDO@@', colhido_em)
             + 'window.VAND_DADOS = '
             + json.dumps(dados, ensure_ascii=False, indent=2) + ';\n')
    temporario = DESTINO.with_name(DESTINO.name + '.tmp')
    temporario.write_text(texto, encoding='utf-8')
    os.replace(temporario, DESTINO)


def main():
    try:
        estacoes = pd.read_parquet(ESTACOES)
        escolhido = escolher(candidatos(buscar_ativos(), estacoes))
        colhido_em = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
        gravar(montar_dados(escolhido, colhido_em), colhido_em)
    except Exception as exc:
        logger.error('colheita falhou, dados.js preservado: %r', exc)
        return 1
    if escolhido:
        logger.info('aviso %s (%s, %s) publicado', escolhido['id'],
                    escolhido['descricao'], escolhido['severidade'])
    else:
        logger.info('nenhum aviso de chuva vigente em Porto Alegre')
    return 0


if __name__ == '__main__':
    sys.exit(main())
```

- [ ] **Step 4: Rodar e ver passar**

Run: `./run.sh -m pytest tests/test_aviso_poa.py -q`
Expected: 15 PASS (13 funções, uma delas com 3 parametrizações). Se algum falhar, corrigir o script, não o teste, a menos que o teste contradiga um desvio listado acima.

- [ ] **Step 5: Suíte inteira (nada regrediu)**

Run: `./run.sh -m pytest tests -q`
Expected: 69 + os novos, 0 falhas.

- [ ] **Step 6: Commit**

```bash
git add scripts/colher_aviso_poa.py tests/test_aviso_poa.py
git commit -m "$(cat <<'EOF'
feat(avisos): colhedor do aviso vigente do INMET para Porto Alegre

Busca avisos/ativos, escolhe o aviso de chuva mais severo que cobre POA e
regenera app/dados.js de forma atômica. Em qualquer falha sai com 1 e não
toca o arquivo.

Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 2: App tolera dia sem aviso, rota `#/alerta/exemplo`, `dados.js` fresco

**Files:**
- Modify: `app/app.js` (roteador ~262; `renderAlerta` ~746–845)
- Modify: `app/sw.js` (VERSAO e handler `fetch`)
- Modify: `tests/app_smoke.html` (bloco "Aba Alerta", ~168–181)
- Regenerate: `app/dados.js` (rodando o script da Task 1)

**Interfaces:**
- Consumes: `window.VAND_DADOS` com `colhido_em`, `aviso|null`, `aviso_exemplo`, `lacuna|null`, `lacuna_exemplo` (Task 1).
- Produces: rotas `#/alerta` (decidida pelo dado), `#/alerta/calmo` (força calmo), `#/alerta/exemplo` (aviso 55157).

- [ ] **Step 1: Baseline do smoke test (antes de mexer)**

Run:
```bash
google-chrome --headless=new --no-sandbox --disable-gpu --virtual-time-budget=20000 --dump-dom "file://$PWD/tests/app_smoke.html" > /tmp/claude-1000/-home-jose-garcia-Projetos-Playground-IA-VAND/99a3a295-48c8-40ca-9215-6ce2040332c4/scratchpad/smoke_antes.html; grep -c "FALHA" /tmp/claude-1000/-home-jose-garcia-Projetos-Playground-IA-VAND/99a3a295-48c8-40ca-9215-6ce2040332c4/scratchpad/smoke_antes.html; grep "FALHA" /tmp/claude-1000/-home-jose-garcia-Projetos-Playground-IA-VAND/99a3a295-48c8-40ca-9215-6ce2040332c4/scratchpad/smoke_antes.html
```
Expected: `RESULTADO` presente; anotar o número e o texto das FALHAs (a memória diz que 2 já existiam por dessincronia de chave do `localStorage`, sem relação com este trabalho). Se o arquivo vier com ~186 bytes, o servidor/abertura falhou (ver `verificar_app.md`): usar `file://` como acima.

- [ ] **Step 2: Atualizar o smoke test primeiro (vai falhar)**

Em `tests/app_smoke.html`, substituir o bloco

```js
  // Aba Alerta com aviso vigente.
  irPara('#/alerta');
```
por
```js
  // Aba Alerta: a rota padrão segue o DADO (colheita diária), então as asserções
  // detalhadas do aviso usam #/alerta/exemplo, que é fixo.
  irPara('#/alerta');
  var haAviso = !!(window.VAND_DADOS && window.VAND_DADOS.aviso);
  ok(!!document.querySelector(haAviso ? '.aviso-card' : '.card-calmo'),
     'aba Alerta segue o dado: ' + (haAviso ? 'aviso vigente' : 'card calmo'));

  // Sem aviso no dado, a rota padrão mostra o card calmo (e o link de exemplo funciona).
  var avisoReal = window.VAND_DADOS.aviso, lacunaReal = window.VAND_DADOS.lacuna;
  window.VAND_DADOS.aviso = null;
  irPara('#/alerta/calmo');
  irPara('#/alerta');
  ok(!!document.querySelector('.card-calmo'), 'dado sem aviso: rota padrão mostra .card-calmo');
  ok(document.querySelector('.link-exemplo').getAttribute('href') === '#/alerta/exemplo',
     'link do card calmo aponta para #/alerta/exemplo');
  window.VAND_DADOS.aviso = avisoReal;

  // Aviso vigente com severidade fora da tabela de lacuna: sem card de lacuna, sem exceção.
  if (avisoReal) {
    window.VAND_DADOS.lacuna = null;
    irPara('#/alerta/calmo');
    irPara('#/alerta');
    ok(!!document.querySelector('.aviso-card') && !document.querySelector('.lacuna-card'),
       'lacuna null: aviso aparece sem card de lacuna');
    window.VAND_DADOS.lacuna = lacunaReal;
  }

  // Aviso de exemplo (55157), fixo.
  irPara('#/alerta/exemplo');
  ok(document.body.textContent.indexOf('EXEMPLO HISTÓRICO') > -1, 'exemplo traz o rótulo EXEMPLO HISTÓRICO');
  ok(!!document.querySelector('.lacuna-card'), 'exemplo mostra o card de lacuna');
```
(as seis asserções seguintes — `.aviso-card`, `.sev-chip`, "Grande Perigo", 5 instruções, 1 risco, `tel:` — ficam como estão, agora valendo para o exemplo).

- [ ] **Step 3: Rodar o smoke e ver as novas asserções falharem**

Mesmo comando do Step 1, saída para `smoke_meio.html`; `grep FALHA`.
Expected: FALHAs novas (`link do card calmo...`, `EXEMPLO HISTÓRICO...`), pois o app ainda não mudou.

- [ ] **Step 4: Alterar `app/app.js`**

Edição 1 — roteador. Trocar
```js
      renderAlerta(r.temaId === 'calmo');
```
por
```js
      renderAlerta(r.temaId);
```

Edição 2 — cabeçalho da função. Trocar
```js
  function renderAlerta(calmo) {
    cabecalho('Alerta', 'Aviso oficial do INMET', false);

    var dados = window.VAND_DADOS;
    if (!dados) return;

    // O dado já traz "Porto Alegre - RS"; formata com vírgula e não anexa nada.
    var municipio = (dados.aviso.municipio_exemplo || 'Porto Alegre, RS').replace(' - ', ', ');
```
por
```js
  function renderAlerta(sub) {
    cabecalho('Alerta', 'Aviso oficial do INMET', false);

    var dados = window.VAND_DADOS;
    if (!dados) return;

    // Quem decide o estado é o DADO, não a rota: num dia sem Aviso vigente a
    // rota padrão mostra o card calmo. 'calmo' força o card calmo; 'exemplo'
    // mostra o Aviso histórico fixo (`aviso_exemplo`), que a colheita nunca toca.
    var exemplo = sub === 'exemplo' && !!dados.aviso_exemplo;
    var aviso = exemplo ? dados.aviso_exemplo : (sub === 'calmo' ? null : dados.aviso);
    var lac = exemplo ? dados.lacuna_exemplo : dados.lacuna;

    // O dado já traz "Porto Alegre - RS"; formata com vírgula e não anexa nada.
    var base = aviso || dados.aviso || dados.aviso_exemplo || {};
    var municipio = (base.municipio_exemplo || 'Porto Alegre, RS').replace(' - ', ', ');
```

Edição 3 — linha de consulta. Trocar
```js
      el('div', { class: 'alerta-consulta' }, [
        el('span', { class: 't-caps alerta-consulta-rotulo', text: 'ÚLTIMA CONSULTA: AGORA MESMO' }),
        el('button', { type: 'button', class: 'btn-circular', 'aria-label': 'Consultar de novo' }, [icone('recarregar', 20)])
      ])
```
por
```js
      el('div', { class: 'alerta-consulta' }, exemplo ? [
        el('span', { class: 't-caps alerta-consulta-rotulo', text: 'EXEMPLO HISTÓRICO — NÃO É O AVISO DE HOJE' })
      ] : [
        el('span', {
          class: 't-caps alerta-consulta-rotulo',
          text: dados.colhido_em ? 'ÚLTIMA CONSULTA: ' + formatData(dados.colhido_em) : 'ÚLTIMA CONSULTA: INDISPONÍVEL'
        }),
        el('button', { type: 'button', class: 'btn-circular', 'aria-label': 'Consultar de novo' }, [icone('recarregar', 20)])
      ])
```

Edição 4 — ramo calmo. Trocar
```js
    if (calmo) {
      // Estado sem Aviso.
```
por
```js
    if (!aviso) {
      // Estado sem Aviso.
```
e trocar
```js
        el('a', { href: '#/alerta', class: 'link-exemplo', text: 'Ver um exemplo de Aviso vigente' })
```
por
```js
        el('a', { href: '#/alerta/exemplo', class: 'link-exemplo', text: 'Ver um exemplo de Aviso vigente' })
```

Edição 5 — ramo com aviso. Trocar
```js
      // Estado com Aviso vigente.
      var aviso = dados.aviso;
```
por
```js
      // Estado com Aviso vigente (ou o exemplo histórico).
```

Edição 6 — card de lacuna opcional. Trocar
```js
      var lac = dados.lacuna;
      var lacunaCard = el('div', { class: 'lacuna-card' }, [
```
por
```js
      if (lac) tela.appendChild(el('div', { class: 'lacuna-card' }, [
```
e trocar
```js
      ]);
      tela.appendChild(lacunaCard);
```
por
```js
      ]));
```
(Conferir com `git diff app/app.js` que os parênteses fecham e que `lacunaCard` não aparece mais.)

- [ ] **Step 5: Alterar `app/sw.js`**

Trocar `var VERSAO = 'IA_VAND-v9';` por `var VERSAO = 'IA_VAND-v10';` e, dentro do handler `fetch`, logo depois de `if (e.request.method !== 'GET') return;`, inserir:

```js
  // dados.js é regerado todo dia pela colheita do aviso (avisos.yml). Cache-first
  // com VERSAO fixa o congelaria no aparelho de quem já abriu o app: aqui a rede
  // vem primeiro e o cache só vale offline.
  if (new URL(e.request.url).pathname.slice(-9) === '/dados.js') {
    e.respondWith(
      fetch(e.request, { cache: 'no-cache' }).then(function (r) {
        var copia = r.clone();
        caches.open(VERSAO).then(function (c) { c.put(e.request, copia); });
        return r;
      }).catch(function () { return caches.match(e.request); })
    );
    return;
  }
```
Atualizar também o comentário do topo do arquivo: acrescentar "Exceção: dados.js, rede-primeiro (ver o handler de fetch)."

- [ ] **Step 6: Regenerar `app/dados.js` com dado real**

Run: `./run.sh scripts/colher_aviso_poa.py`
Expected: exit 0 e uma linha de log: `aviso <id> ... publicado` ou `nenhum aviso de chuva vigente em Porto Alegre`. Se exit 1, ler o log: **não** contornar; pode ser rede ou formato novo da API. Conferir: `head -20 app/dados.js` (cabeçalho autogerado) e `git diff --stat app/dados.js`.

- [ ] **Step 7: Smoke test completo**

Rodar o comando do Step 1 para `smoke_depois.html`.
Expected: nenhuma FALHA além das que já existiam no baseline (mesmo texto, mesma contagem); todas as asserções novas passam; `grep -c "aba Alerta" smoke_depois.html` mostra as linhas novas como OK.
Conferir também sem rolagem horizontal: o teste já cobre as seis telas a 430px; `#/alerta/exemplo` usa o mesmo layout.

- [ ] **Step 8: Verificação visual do estado calmo e do exemplo**

Servir em 8791 (a 8000 está ocupada nesta máquina): `./run.sh -m http.server 8791 --directory app &` e abrir `http://localhost:8791/#/alerta/exemplo` e `#/alerta/calmo` no Chrome (ferramentas claude-in-chrome ou screenshot headless a 390×844). Conferir: rótulo "EXEMPLO HISTÓRICO", card de lacuna presente, sem sobreposição no cabeçalho. Encerrar o servidor depois (`kill %1`).

- [ ] **Step 9: Commit**

```bash
git add app/app.js app/sw.js app/dados.js tests/app_smoke.html
git commit -m "$(cat <<'EOF'
feat(app): Alerta decidido pelo dado, rota /alerta/exemplo e dados.js fresco

Num dia sem aviso a rota padrão mostra o card calmo; o link de exemplo vai
para #/alerta/exemplo (aviso 55157, fixo). ÚLTIMA CONSULTA passa a vir de
colhido_em. O service worker busca dados.js primeiro na rede, senão a
colheita diária nunca chegaria a quem já abriu o app. dados.js regenerado
pelo novo colhedor.

Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 3: Workflow `avisos.yml` e deploy acionável

**Files:**
- Create: `.github/workflows/avisos.yml`
- Modify: `.github/workflows/deploy.yml` (adicionar `workflow_dispatch`)

**Interfaces:**
- Consumes: `scripts/colher_aviso_poa.py` (Task 1), `colheita/estacoes.parquet`.
- Produces: commit diário de `app/dados.js` na `main` + disparo do `deploy.yml` (porque push com `GITHUB_TOKEN` não dispara workflows).

- [ ] **Step 1: Habilitar disparo manual do deploy**

Em `.github/workflows/deploy.yml`, trocar
```yaml
on:
  push:
    branches: ["main"]
```
por
```yaml
on:
  push:
    branches: ["main"]
  # Acionado também pelo avisos.yml: pushes feitos com a GITHUB_TOKEN não
  # disparam o evento `push`, então o commit do bot não publicaria sozinho.
  workflow_dispatch:
```

- [ ] **Step 2: Criar o workflow**

Criar `.github/workflows/avisos.yml`:

```yaml
name: Colheita do aviso do INMET

# 12:00 UTC = 09:00 em Porto Alegre, mesmo horário da colheita de previsões.
# O GitHub pode atrasar jobs agendados em horário de pico; `colhido_em` no
# dados.js grava a hora real, e a tela mostra essa hora.
on:
  schedule:
    - cron: "0 12 * * *"
  workflow_dispatch:

# contents: o bot commita na main (decisão explícita: sem PR nem revisão).
# actions: o bot aciona o deploy, que a GITHUB_TOKEN não dispara sozinha.
permissions:
  contents: write
  actions: write

concurrency:
  group: avisos
  cancel-in-progress: false

jobs:
  colher:
    runs-on: ubuntu-latest
    timeout-minutes: 10
    steps:
      - uses: actions/checkout@v4
        with:
          ref: main

      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"

      - name: Instalar dependências da colheita
        run: pip install pandas==2.2.2 numpy==1.26.4 pyarrow==16.1.0 requests==2.32.3

      # Falha segura: se o script sair com erro, o job falha aqui e o dados.js
      # do dia anterior continua no ar.
      - name: Colher o aviso
        env:
          PYTHONPATH: ${{ github.workspace }}
        run: python scripts/colher_aviso_poa.py

      - name: Publicar na main e acionar o deploy
        env:
          GH_TOKEN: ${{ github.token }}
        run: |
          if git diff --quiet -- app/dados.js; then
            echo "nada novo para publicar"
            exit 0
          fi
          git config user.name "avisos-bot"
          git config user.email "avisos-bot@users.noreply.github.com"
          git add app/dados.js
          git commit --quiet -m "avisos: dados de $(date -u +%Y-%m-%d)"
          git push --quiet origin HEAD:main
          gh workflow run deploy.yml --ref main
```

- [ ] **Step 3: Validar a sintaxe YAML**

Run: `./run.sh -c "import yaml,sys; [yaml.safe_load(open(f)) for f in ('.github/workflows/avisos.yml','.github/workflows/deploy.yml')]; print('ok')"`
Expected: `ok`. (Se `yaml` não estiver no venv, usar `ruby -ryaml -e` ou `python3 -c` do sistema; só precisa parsear.)

- [ ] **Step 4: Commit**

```bash
git add .github/workflows/avisos.yml .github/workflows/deploy.yml
git commit -m "$(cat <<'EOF'
feat(ci): colheita diária do aviso do INMET publicando na main

Workflow novo, separado do colheita.yml (que é isolado da main de
propósito). O deploy ganha workflow_dispatch porque o push do bot, feito com
a GITHUB_TOKEN, não o dispara.

Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>
EOF
)"
```

- [ ] **Step 5: PARAR e pedir confirmação ao usuário antes do push**

O push publica na `main` e dispara o deploy do app. Mostrar `git log --oneline origin/main..HEAD` e esperar o "pode".

- [ ] **Step 6: Push e primeira execução manual (após confirmação)**

```bash
git push origin main
gh workflow run avisos.yml --ref main
gh run watch "$(gh run list --workflow=avisos.yml --limit 1 --json databaseId -q '.[0].databaseId')"
```
Expected: job verde; log do passo "Colher o aviso" mostra a linha de resultado; ou "nada novo para publicar", ou um commit `avisos: dados de AAAA-MM-DD` na `main`. Em seguida:
```bash
gh run list --workflow=deploy.yml --limit 3
```
Expected: um run recente do deploy disparado por `workflow_dispatch` (se houve commit do bot) e verde. Abrir a URL do Pages e conferir a tela de Alerta e `#/alerta/exemplo`. Se o deploy NÃO aparecer, o desvio 4 está errado para este repositório: investigar antes de declarar pronto.

---

### Task 4: Registrar os desvios da spec

**Files:**
- Modify: `docs/superpowers/specs/2026-10-15-colheita-aviso-inmet-design.md` (seção nova no fim)

- [ ] **Step 1: Acrescentar ao fim da spec**

```markdown

## Correções feitas no plano (18/10/2026)

Descobertas ao ler o código e a API real ao escrever
`docs/superpowers/plans/2026-10-18-colheita-aviso-inmet.md`. Onde divergem do
texto acima, **vale esta seção**.

- `avisos/ativos` devolve `{"hoje": [...], "futuro": [...]}`; vigente = `hoje`.
- `riscos`/`instrucoes` já são listas (a pendência "verificar" do Componente 2
  está resolvida); `municipios` é string, o total sai de `geocodes`.
- Só avisos de chuva (`Chuvas Intensas`, `Tempestade`, `Acumulado de Chuva`):
  o texto da tela e a tabela de lacuna são de chuva.
- `lacuna_exemplo` entra no dado (o exemplo 55157 precisa da própria linha).
- O push do bot (`GITHUB_TOKEN`) **não dispara** o `deploy.yml`, ao contrário do
  que o Escopo afirma; o `avisos.yml` aciona o deploy por `workflow_dispatch`.
- O service worker passa a buscar `dados.js` primeiro na rede.
- O `dados.js` muda todo dia (`colhido_em`), então há um commit diário.
```

- [ ] **Step 2: Commit**

```bash
git add docs/superpowers/specs/2026-10-15-colheita-aviso-inmet-design.md docs/superpowers/plans/2026-10-18-colheita-aviso-inmet.md
git commit -m "$(cat <<'EOF'
docs: plano da colheita do aviso e correções registradas na spec

Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>
EOF
)"
```

---

## Self-review

- **Cobertura da spec:** Componente 1 → Task 1; 2 → Task 1 (`montar_dados`/`gravar`); 3 → Task 2; 4 → Task 3; Testes → Task 1 e Task 2 (smoke); Riscos (deploy sem revisão, schema mudar) → falha segura testada em Task 1. Cron ligado desde já, por decisão do usuário em 18/10/2026.
- **Placeholders:** nenhum; todo passo de código traz o código.
- **Consistência de nomes:** `VAND_DADOS_JS`, `aviso_exemplo`, `lacuna_exemplo`, `colhido_em`, `renderAlerta(sub)`, `#/alerta/exemplo` usados de forma idêntica nas três tasks.
- **Review Focus:** os cinco itens têm teste nomeado.
