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
