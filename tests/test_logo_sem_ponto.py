"""A logo do cabeçalho fixo não pode ter nenhum pixel vermelho.

ADR 0003: o vermelho é reservado à Severidade do INMET, e a exceção do ponto da
marca só vale enquanto a marca não dividir superfície com ela. O cabeçalho fixo é
essa superfície, então a logo que mora lá é a variante SEM o ponto. Este teste
transforma a regra em asserção: se alguém regenerar o asset e o ponto voltar, ou
trocar o arquivo por um com vermelho, o teste cai.
"""
from pathlib import Path

import pytest

Image = pytest.importorskip('PIL.Image')

ICONES = Path('app/icons')
SEM_PONTO = ('logo-sem-ponto.png', 'logo-sem-ponto-dark.png')
# Mesma detecção que gerou os mark-mono (dominância do canal vermelho).
def _vermelho(r, g, b):
    return r > 140 and r > g * 1.6 and r > b * 1.6


def _pixels_vermelhos(nome):
    img = Image.open(ICONES / nome).convert('RGBA')
    return sum(1 for r, g, b, a in img.getdata() if a > 40 and _vermelho(r, g, b))


def _pixels_opacos(nome):
    img = Image.open(ICONES / nome).convert('RGBA')
    return sum(1 for *_, a in img.getdata() if a > 40)


def test_a_deteccao_enxerga_o_ponto_na_logo_original():
    # Sem isto o teste abaixo seria vácuo: se a detecção não achasse o ponto
    # nem na logo que o tem, "zero pixels vermelhos" não provaria nada.
    assert _pixels_vermelhos('logo.png') > 50


@pytest.mark.parametrize('nome', SEM_PONTO)
def test_logo_do_cabecalho_nao_tem_pixel_vermelho(nome):
    assert _pixels_vermelhos(nome) == 0


@pytest.mark.parametrize('nome', SEM_PONTO)
def test_logo_do_cabecalho_mantem_o_tamanho_e_o_conteudo(nome):
    img = Image.open(ICONES / nome)
    assert img.size == (551, 198)
    # Só o ponto some: o resto (monograma + wordmark) tem de sobrar quase todo.
    original = 'logo.png' if 'dark' not in nome else 'logo-dark.png'
    assert _pixels_opacos(nome) > 0.9 * _pixels_opacos(original)
