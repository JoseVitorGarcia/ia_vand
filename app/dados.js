/*
 * Dado que alimenta as abas Alerta e Registro.
 *
 * ARQUIVO AUTOGERADO por scripts/colher_aviso_poa.py em 2026-10-26T18:37:23Z.
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
window.VAND_DADOS = {
  "_procedencia": {
    "origem": "https://apiprevmet3.inmet.gov.br/avisos/ativos",
    "nota": "Aviso real colhido da API de avisos do INMET. Campos originais, sem edicao, exceto vigencia (inicio/fim) e municipios_total, derivados. Recortado para Porto Alegre porque o prototipo nao tem geolocalizacao."
  },
  "colhido_em": "2026-10-26T18:37:23Z",
  "aviso": null,
  "aviso_exemplo": {
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
  "lacuna": null,
  "lacuna_exemplo": {
    "severidade": "Grande Perigo",
    "taxa_area": 0.591,
    "taxa_ponto": 0.031,
    "razao": 19.1,
    "fonte": "reports/lacuna_granularidade_avisos_2026_08_21_00_29.md",
    "nota_editorial": "Enquadramento e lacuna de granularidade: o aviso e produto de area recebido num ponto. Nao e avaliacao de quem preve melhor."
  }
};
