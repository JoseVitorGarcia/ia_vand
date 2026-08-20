"""A varredura de corte: aritmética simples, mas é ela que vira decisão de produto."""
import numpy as np

from scripts.curva_operacao_ifs import _corte_para_recall, varrer


def test_varrer_conta_certo():
    y = np.array([1, 1, 0, 0, 0])
    score = np.array([10.0, 5.0, 6.0, 1.0, 0.0])
    r = varrer(y, score, [5.0]).iloc[0]
    # alertam: 10, 5, 6 -> 3 alertas, 2 acertos
    assert r['alertas'] == 3 and r['acertos'] == 2
    assert r['precisao'] == 2 / 3
    assert r['recall'] == 1.0
    assert r['perdidos'] == 0


def test_corte_alto_demais_nao_quebra():
    y = np.array([1, 0, 0])
    r = varrer(y, np.array([1.0, 0.5, 0.2]), [99.0]).iloc[0]
    assert r['alertas'] == 0 and r['f1'] == 0.0


def test_corte_para_recall_escolhe_o_maior_que_atende():
    """Entre os cortes que atingem o recall, o maior é o que dispara menos alerta."""
    y = np.array([1, 1, 0, 0, 0, 0])
    score = np.array([20.0, 10.0, 9.0, 8.0, 1.0, 0.0])
    p = _corte_para_recall(y, score, 0.5)
    assert p['corte'] == 20.0 and p['alertas'] == 1 and p['recall'] == 0.5
    p = _corte_para_recall(y, score, 1.0)
    assert p['corte'] == 10.0 and p['alertas'] == 2
