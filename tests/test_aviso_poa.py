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
