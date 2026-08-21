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
    multi = {'type': 'MultiPolygon', 'coordinates': [
        QUADRADO['coordinates'],
        [[[-45.0, -20.0], [-44.0, -20.0], [-44.0, -19.0], [-45.0, -19.0], [-45.0, -20.0]]]]}
    assert av.ponto_em_poligono(-51.0, -29.0, multi)
    assert av.ponto_em_poligono(-44.5, -19.5, multi)
    assert not av.ponto_em_poligono(-48.0, -25.0, multi)


def test_geometria_invalida_devolve_falso():
    """Aviso sem polígono não pode derrubar o estudo inteiro."""
    assert not av.ponto_em_poligono(-51.0, -29.0, None)
    assert not av.ponto_em_poligono(-51.0, -29.0, 'nao é json')
    assert not av.ponto_em_poligono(-51.0, -29.0, float('nan'))


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


def test_faixa_com_separador_a_pega_o_limite_inferior():
    """Frase real do dado. Com só o separador 'e', a expressão pulava o 50 e
    devolvia 100 — critério mais severo do que o aviso promete."""
    assert av.criterio_mm_dia("Chuva entre 30 a 60 mm/h ou 50 a 100 mm/dia") == 50.0
    assert av.criterio_mm_dia("Chuva entre 30 e 60 mm/h ou 50 e 100 mm/dia") == 50.0
    assert av.criterio_mm_dia("Chuva superior a 60 mm/h ou acima de 100 mm/dia") == 100.0


ESTACOES = pd.DataFrame({'estacao_codigo': ['A801', 'A802'],
                         'latitude': [-29.0, -19.5], 'longitude': [-51.0, -44.5]})


def _aviso(**kw):
    base = {'id': 1, 'poligono': json.dumps(QUADRADO), 'descricao': 'Chuvas Intensas',
            'severidade': 'Perigo', 'id_severidade': 7,
            'data_inicio': '2025-03-10T00:00:00.000Z', 'hora_inicio': '13:00',
            'data_fim': '2025-03-10T00:00:00.000Z', 'hora_fim': '23:00',
            'riscos': 'Chuva de até 50 mm/dia'}
    base.update(kw)
    return pd.DataFrame([base])


def test_estacoes_do_aviso_usa_a_geometria():
    assert av.estacoes_do_aviso({'poligono': json.dumps(QUADRADO)}, ESTACOES) == ['A801']


def test_vigencia_de_um_dia_gera_um_dia():
    r = av.expandir_estacao_dia(_aviso(), ESTACOES)
    assert list(r['estacao_codigo']) == ['A801']
    assert str(r['dia'].iloc[0]) == '2025-03-10'
    assert r['criterio_mm'].iloc[0] == 50.0


def test_vigencia_que_cruza_o_ancoramento_gera_dois_dias():
    """Ancorado às 12 UTC: quem vige das 06:00 do dia 10 às 06:00 do dia 11 toca
    o dia pluviométrico de 09 (que vai até 10 às 12) e o de 10."""
    a = _aviso(id=2, descricao='Tempestade', hora_inicio='06:00',
               data_fim='2025-03-11T00:00:00.000Z', hora_fim='06:00')
    dias = sorted(str(d) for d in av.expandir_estacao_dia(a, ESTACOES)['dia'])
    assert dias == ['2025-03-09', '2025-03-10']


def test_tipo_fora_do_recorte_nao_entra():
    a = _aviso(id=3, descricao='Baixa Umidade', riscos='Umidade entre 12% e 20%')
    assert av.expandir_estacao_dia(a, ESTACOES).empty


def test_aviso_que_nao_cobre_estacao_nenhuma_e_ignorado():
    """Aviso do Nordeste não pode gerar linha para estação do RS."""
    longe = {'type': 'Polygon', 'coordinates': [
        [[-40.0, -10.0], [-39.0, -10.0], [-39.0, -9.0], [-40.0, -9.0], [-40.0, -10.0]]]}
    assert av.expandir_estacao_dia(_aviso(poligono=json.dumps(longe)), ESTACOES).empty


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


def test_taxa_confirmacao_com_amostra_vazia_nao_quebra():
    """Células cruzadas raras (Vendaval x Grande Perigo) podem ficar vazias."""
    p, (lo, hi) = av.taxa_confirmacao(np.array([]))
    assert np.isnan(p) and np.isnan(lo) and np.isnan(hi)
