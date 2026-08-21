"""Domínio dos avisos meteorológicos do INMET.

Vocabulário desta biblioteca, e ele não é estilístico: um aviso é comunicação de
RISCO, não afirmação determinística. Aviso cujo fenômeno não ocorreu não é erro
nem falso positivo — é NÃO CONFIRMADO. Verificar aviso como acerto binário é o
equívoco clássico da avaliação de sistemas de alerta e produz a conclusão falsa
de que serviços meteorológicos erram muito.

Desenho do estudo: reports/desenho_estudo_avisos_2026_08_20.md
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


def _fora_da_caixa(x, y, aneis):
    """Rejeição barata antes do lançamento de raio.

    São ~5.800 avisos x ~95 estações = mais de meio milhão de testes, cada um
    percorrendo centenas de vértices em Python puro. A caixa envolvente descarta
    a grande maioria em quatro comparações.
    """
    contorno = aneis[0]
    xs = [c[0] for c in contorno]
    ys = [c[1] for c in contorno]
    return x < min(xs) or x > max(xs) or y < min(ys) or y > max(ys)


def _poligono_contem(x, y, aneis):
    """Primeiro anel é o contorno; os demais são buracos."""
    if not aneis or _fora_da_caixa(x, y, aneis) or not _anel_contem(x, y, aneis[0]):
        return False
    return not any(_anel_contem(x, y, buraco) for buraco in aneis[1:])


def ponto_em_poligono(lon, lat, geometria):
    """True se (lon, lat) está dentro da geometria GeoJSON.

    Aceita Polygon e MultiPolygon, como dicionário ou texto. Geometria ausente ou
    ilegível devolve False em vez de levantar: um aviso malformado não pode
    derrubar o estudo, mas também não pode contar como cobertura.
    """
    if geometria is None:
        return False
    if isinstance(geometria, float) and np.isnan(geometria):
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


# O limite INFERIOR da faixa anunciada é o que se verifica. "Entre 30 e 60 mm/dia"
# promete pelo menos 30; exigir 60 seria cobrar do aviso o pior caso que ele
# mencionou como teto, e não o patamar que ele comunicou.
# O separador da faixa é "e" OU "a": os dois aparecem no dado real —
# "50 e 100 mm/dia" e "50 a 100 mm/dia". Tratar só o "e" fazia a expressão pular
# o primeiro número e capturar o segundo, tornando o critério mais severo do que
# o aviso promete. Encontrado na conferência manual de 20/08/2026, invisível
# para qualquer teste que não usasse a frase real.
_FAIXA_MM_DIA = re.compile(
    r'entre\s*(\d+(?:[.,]\d+)?)\s*(?:e|a)\s*(\d+(?:[.,]\d+)?)\s*mm\s*/\s*dia', re.I)
_MM_DIA = re.compile(
    r'(\d+(?:[.,]\d+)?)\s*(?:(?:e|a)\s*\d+(?:[.,]\d+)?\s*)?mm\s*/\s*dia', re.I)
# `km` literal separa isto de "mm/h", que aparece na MESMA frase dos avisos de
# chuva e seria confundido por um padrão que só olhasse "/h".
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
    """Rajada anunciada, convertida de km/h para m/s.

    A unidade importa: o aviso fala em km/h e a estação registra
    `VENTO, RAJADA MAXIMA` em m/s. Comparar sem converter daria confirmação
    quase nula e a conclusão errada de que os avisos de vendaval não se cumprem.
    """
    if not isinstance(texto, str):
        return None
    achado = _KMH.search(texto)
    return _numero(achado.group(1)) / 3.6 if achado else None


# Os quatro tipos com verdade de campo nas estações de superfície. Baixa Umidade,
# Declínio de Temperatura e Ventos Costeiros ficam de fora por falta de
# observação aplicável, não por serem menos importantes.
TIPOS_INCLUIDOS = ('Chuvas Intensas', 'Tempestade', 'Acumulado de Chuva', 'Vendaval')


def estacoes_do_aviso(aviso, estacoes):
    """Códigos das estações cuja coordenada cai dentro do polígono do aviso."""
    geom = aviso['poligono']
    return [r.estacao_codigo for r in estacoes.itertuples()
            if ponto_em_poligono(r.longitude, r.latitude, geom)]


def _instante(data, hora):
    """'2025-03-10T00:00:00.000Z' + '13:00' -> Timestamp UTC."""
    dia = pd.to_datetime(str(data)[:10], utc=True)
    partes = (str(hora) + ':00').split(':')
    return dia + pd.Timedelta(hours=int(partes[0]), minutes=int(partes[1]))


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
        deslocamento = pd.Timedelta(hours=hora_emissao)
        dias = pd.date_range((inicio - deslocamento).normalize(),
                             (fim - deslocamento).normalize(), freq='D')
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


def taxa_confirmacao(confirmados, z=1.96):
    """Proporção confirmada, com intervalo de 95% por Wilson.

    Wilson e não normal: com poucas dezenas de avisos por nível, o intervalo
    normal escapa de [0,1] e colapsa para largura zero quando não há nenhuma
    confirmação — o que afirmaria "a taxa é exatamente 0%", forte demais para o
    dado. Células cruzadas raras (Vendaval x Grande Perigo) tornam isso comum.

    NÃO é taxa de acerto. Aviso não confirmado é risco comunicado que não se
    materializou, que é o funcionamento normal de um sistema de alerta.
    """
    c = np.asarray(confirmados, dtype=float)
    n = len(c)
    if n == 0:
        return float('nan'), (float('nan'), float('nan'))
    p = c.mean()
    denom = 1 + z**2 / n
    centro = (p + z**2 / (2 * n)) / denom
    margem = z * np.sqrt(p * (1 - p) / n + z**2 / (4 * n**2)) / denom
    return float(p), (float(max(0.0, centro - margem)), float(min(1.0, centro + margem)))
