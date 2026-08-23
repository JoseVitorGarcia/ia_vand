/*
 * Dado que alimenta as abas Alerta e Registro.
 *
 * PROCEDÊNCIA — este NÃO é dado inventado. O Aviso abaixo é o de id 55157,
 * colhido da API de avisos do INMET e guardado em
 * cache/avisos_inmet/avisos_54935_55192.parquet. Severidade, tipo, vigência,
 * riscos, instruções e `aviso_cor` são os campos originais, sem edição.
 *
 * Os números de Previsão e de lacuna vêm de
 * reports/lacuna_granularidade_avisos_2026_08_21_00_29.md.
 *
 * REGRA EDITORIAL (docs/design/brief_telas_alerta_registro.md): taxa de
 * confirmação não é taxa de acerto, e os 30,3% são da NOSSA Previsão — nunca
 * do aviso do INMET. Não atribuir não-confirmação ao INMET.
 *
 * Carregado como script, e não por fetch(), de propósito: o app precisa rodar
 * em file:// e tests/app_smoke.html roda síncrono. Mesmo padrão de content.js.
 */
window.VAND_DADOS = {
    "_procedencia": {
      "origem": "cache/avisos_inmet/avisos_54935_55192.parquet",
      "aviso_id": 55157,
      "nota": "Aviso real colhido da API de avisos do INMET. Severidade, tipo, vigencia, riscos, instrucoes e cor sao os campos originais, sem edicao. Recortado para um municipio de exemplo porque o prototipo nao tem geolocalizacao."
    },
    "aviso": {
      "id": 55157,
      "descricao": "Acumulado de Chuva",
      "severidade": "Grande Perigo",
      "aviso_cor": "#F80703",
      "inicio": "2026-07-28T09:00:00Z",
      "fim": "2026-07-29T10:00:00Z",
      "riscos": [
        "Chuva superior a 60 mm/h ou acima de 100 mm/dia. Grande risco de grandes alagamentos e transbordamentos de rios, grandes deslizamentos de encostas,   em cidades com tais áreas de risco."
      ],
      "instrucoes": [
        "Desligue aparelhos elétricos, quadro geral de energia.",
        "Observe alteração nas encostas.",
        "Permaneça em local abrigado.",
        "Em caso de situação de inundação, ou similar, proteja seus pertences da água envoltos em sacos plásticos.",
        "Obtenha mais informações junto à Defesa Civil (telefone 199) e ao Corpo de Bombeiros (telefone 193)."
      ],
      "municipios_total": 531,
      "municipio_exemplo": "Porto Alegre - RS",
      "geocode_exemplo": "4314902"
    },
    "previsao": {
      "regra": "ECMWF > 30 mm",
      "taxa_confirmacao": 0.303,
      "recall": 0.709,
      "n_alertas": 750,
      "acertos": 227,
      "fonte": "reports/lacuna_granularidade_avisos_2026_08_21_00_29.md",
      "nota_editorial": "Taxa de confirmacao NAO e taxa de acerto. Refere-se a NOSSA Previsao, nunca ao aviso do INMET."
    },
    "lacuna": {
      "severidade": "Grande Perigo",
      "taxa_area": 0.591,
      "taxa_ponto": 0.031,
      "razao": 19.1,
      "fonte": "reports/lacuna_granularidade_avisos_2026_08_21_00_29.md",
      "nota_editorial": "Enquadramento e lacuna de granularidade: o aviso e produto de area recebido num ponto. Nao e avaliacao de quem preve melhor."
    }
  };
