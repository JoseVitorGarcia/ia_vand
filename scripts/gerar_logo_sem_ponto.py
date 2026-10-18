"""Gera a logo do cabeçalho fixo: a logo completa SEM o ponto vermelho.

Por quê: ADR 0003 reserva o vermelho à Severidade do INMET e só dispensa o ponto
da marca enquanto ela não dividir superfície com a Severidade. O cabeçalho fixo
é essa superfície (fica no topo da tela de Aviso), então a logo que mora lá não
pode ter o ponto. O ponto vive dentro do monograma; o wordmark "VAND" não o tem.

Parte de `logo.png` e `logo-dark.png` (a variante escura já vem recolorida) e
apaga os pixels de dominância vermelha — a mesma detecção que gerou os
`mark-mono*.png` — mais a franja anti-aliasada em volta, que não passa no limiar
mas ficaria como um halo rosado.

Uso:
    ./run.sh scripts/gerar_logo_sem_ponto.py
"""
from pathlib import Path

from PIL import Image

ICONES = Path(__file__).resolve().parent.parent / 'app' / 'icons'
PARES = (('logo.png', 'logo-sem-ponto.png'),
         ('logo-dark.png', 'logo-sem-ponto-dark.png'))
MARGEM = 3  # px em volta do ponto onde a franja anti-aliasada ainda conta


def _vermelho(r, g, b):
    return r > 140 and r > g * 1.6 and r > b * 1.6


def _avermelhado(r, g, b):
    """Franja: ainda puxa para o vermelho, mas fraco demais para o limiar."""
    return r > g + 25 and r > b + 25


def sem_ponto(origem):
    img = Image.open(origem).convert('RGBA')
    px = img.load()
    larg, alt = img.size
    miolo = [(x, y) for y in range(alt) for x in range(larg)
             if px[x, y][3] > 40 and _vermelho(*px[x, y][:3])]
    if not miolo:
        raise SystemExit(f'{origem.name}: nenhum pixel vermelho achado — o ponto mudou?')
    x0, x1 = min(x for x, _ in miolo), max(x for x, _ in miolo)
    y0, y1 = min(y for _, y in miolo), max(y for _, y in miolo)
    for y in range(max(0, y0 - MARGEM), min(alt, y1 + MARGEM + 1)):
        for x in range(max(0, x0 - MARGEM), min(larg, x1 + MARGEM + 1)):
            r, g, b, a = px[x, y]
            if a and (_vermelho(r, g, b) or _avermelhado(r, g, b)):
                px[x, y] = (r, g, b, 0)
    return img


if __name__ == '__main__':
    for entrada, saida in PARES:
        sem_ponto(ICONES / entrada).save(ICONES / saida)
        print('gerado', saida)
