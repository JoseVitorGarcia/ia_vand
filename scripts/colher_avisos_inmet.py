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
                linha.update({k: (v if isinstance(v, (int, float, type(None))) else str(v))
                              for k, v in aviso.items()})
            linhas.append(linha)
            time.sleep(PAUSA)

        tmp = caminho_bloco(lo, hi).with_suffix('.parquet.tmp')
        pd.DataFrame(linhas).to_parquet(tmp, index=False)
        tmp.rename(caminho_bloco(lo, hi))
        obtidos = sum(1 for l in linhas if l['obtido'])
        logger.info('bloco %d-%d: %d/%d avisos obtidos', lo, hi, obtidos, len(linhas))

    logger.info('COLHEITA COMPLETA — %d blocos em %s', len(faixas), DESTINO)
