"""Janelas, cenários e bootstrap da medição de acréscimo local.

A parte pura: sem rede, sem modelo treinado, sem ler o dataset.
"""
import numpy as np
import pandas as pd

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
    # 2025-01-01 12:00 cai dentro do embargo de 24 h e não entra em nenhuma das duas
    assert list(ava) == [False, False, False, False, True, True]
    assert not (aju & ava).any()


def test_embargo_cobre_o_alvo_da_ultima_linha_de_ajuste():
    """O alvo da última linha de ajuste é a soma de t+1..t+24 — invade 2025 sem embargo."""
    df = _frame(['2024-12-31 23:00', '2025-01-01 23:00', '2025-01-02 00:00'])
    _aju, ava = m.separar_ajuste_avaliacao(df)
    assert list(ava) == [False, False, True]


def test_rotular_usa_o_limiar_pedido():
    df = _frame(['2025-02-01 12:00'] * 6)   # chuva_futura_24h = 0,10,20,30,40,50
    assert list(m.rotular(df, 50)) == [0, 0, 0, 0, 0, 0]
    assert list(m.rotular(df, 30)) == [0, 0, 0, 0, 1, 1]


def test_ha_exatamente_um_cenario_primario():
    """O endpoint primário é declarado no código, antes de qualquer resultado existir."""
    primarios = [c for c in m.CENARIOS if c['primario']]
    assert len(primarios) == 1
    assert primarios[0]['limiar'] == 50 and primarios[0]['horas'] == (12,)


def test_os_quatro_cenarios_estao_declarados():
    assert {(c['limiar'], c['horas']) for c in m.CENARIOS} == {
        (50, (12,)), (50, (0, 12)), (30, (12,)), (30, (0, 12))}


def test_nenhuma_variante_consome_p_modelo():
    """2024 é dentro da amostra para o classificador local — usá-lo aqui inflaria tudo."""
    for extras in m.VARIANTES.values():
        assert 'p_modelo' not in extras
    assert 'p_modelo' not in m.LOCAIS


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


def test_variante_de_verificacao_de_bug_existe():
    """Uma logística só sobre ifs_log tem de reproduzir o PR-AUC da régua crua.

    É transformação monotônica da mesma variável, e PR-AUC mede ordenação. Se ela
    divergir, o defeito está no encanamento e nenhum outro número vale.
    """
    assert m.VARIANTES['V0b só IFS, via logística'] == []


def test_filtrar_estacoes():
    df = pd.DataFrame({'estacao_codigo': ['A801', 'A802', 'A803'], 'x': [1, 2, 3]})
    assert list(m.filtrar_estacoes(df, {'A801', 'A803'})['estacao_codigo']) == ['A801', 'A803']
    assert len(m.filtrar_estacoes(df, None)) == 3
