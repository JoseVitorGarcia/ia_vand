"""O colhedor de avisos: normalização da resposta e divisão em blocos retomáveis."""
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
    assert c.blocos(1, 7, 3) == [(1, 3), (4, 6), (7, 7)]
