# Colheita automática do aviso do INMET para a tela de Alerta

Data: 2026-10-15. Discutido em brainstorm, aprovado em chat. Apresentação do
SIC em 19–23/10/2026 — 4 dias a partir da escrita deste documento.

## Contexto e motivação

A tela de Alerta (`app/app.js`, `renderAlerta`) retransmite um aviso do INMET,
hoje **fixo**: `app/dados.js` é um objeto estático com o aviso real de id
55157 (vigência 28–29/07/2026), escolhido à mão no redesign de 22-23/08/2026.
O app já tem uma colheita diária automatizada desde 14/10/2026
(`.github/workflows/colheita.yml`), mas ela busca só a previsão de chuva do
ECMWF/Open-Meteo para medir a degradação do MOS — nunca tocou o aviso do
INMET, e publica num branch `dados` isolado de propósito do `main` (pra não
disparar o deploy do app a cada dia de colheita de pesquisa).

O pedido: colher o aviso **vigente** do INMET para Porto Alegre e levar isso
até a tela de Alerta, automaticamente.

## Escopo

**Dentro:** um aviso por vez para Porto Alegre (mesmas 3 estações já usadas
pela colheita ECMWF, sem geolocalização real — o app não tem isso, decisão já
registrada em `desenho_aplicacao`); publicação automática em `app/dados.js`;
ajuste do app para não quebrar num dia sem aviso vigente; preservar a
demonstração do estado "com aviso" mesmo nesse caso.

**Fora, deliberado:**
- Não muda `previsao.taxa_confirmacao` (é uma medição histórica da regra
  sobre o ECMWF, não varia por dia).
- Não adiciona geolocalização real nem cobre outro município.
- Não acumula histórico de avisos colhidos (diferente da colheita ECMWF, que
  existe para medir uma série ao longo do tempo — aqui o único consumidor é o
  próprio app, e o histórico de commits do git já é o rastro de auditoria).
- Sem revisão humana antes do deploy — decisão explícita do usuário: o
  workflow commita direto na `main`, o que já dispara `deploy.yml` (ele
  escuta qualquer push na `main`, sem filtro de path — confirmado lendo o
  arquivo).

## Arquitetura

Um script novo, `scripts/colher_aviso_poa.py`, roda uma vez por dia via
GitHub Actions, busca o aviso ativo mais severo que cobre Porto Alegre e
regenera `app/dados.js` inteiro. Se não achar nada ativo, gera a versão
"sem aviso". Se a API falhar ou vier em formato inesperado, o script sai com
erro e **não escreve nada** — o `app/dados.js` do dia anterior continua
valendo até a próxima colheita bem-sucedida. Um workflow novo,
`.github/workflows/avisos.yml`, chama o script e empurra o resultado direto
para a `main` quando há mudança.

```
avisos/ativos (INMET) --> colher_aviso_poa.py --> app/dados.js --> push main --> deploy.yml
                                  |
                      ponto_em_poligono() / estacoes_do_aviso()
                            (reaproveitados de src/avisos.py)
```

## Componente 1 — `scripts/colher_aviso_poa.py`

Reaproveita de `src/avisos.py`:
- `estacoes_do_aviso(aviso, estacoes)` — já recebe um dict de aviso com chave
  `poligono` e um DataFrame de estações com `latitude`/`longitude`/
  `estacao_codigo`, exatamente o formato de `colheita/estacoes.parquet`
  (3 linhas de Porto Alegre, já usado pela colheita ECMWF). Não precisa
  reimplementar ponto-em-polígono.

Passos:
1. `GET https://apiprevmet3.inmet.gov.br/avisos/ativos`, com o mesmo
   `User-Agent` de cortesia que `colher_avisos_inmet.py` já usa
   (`IA_VAND/1.0 (pesquisa academica; UFRGS)`), timeout e retry curtos (a
   API já provou ser estável: 100% de sucesso em ~6 mil requisições no
   estudo da lacuna).
2. Para cada aviso na resposta, rodar `estacoes_do_aviso` contra as 3
   estações de POA. Avisos sem nenhuma estação dentro do polígono são
   descartados.
3. Se mais de um aviso cobrir POA ao mesmo tempo, vence o **mais severo**
   (Grande Perigo > Perigo > Perigo Potencial > qualquer outro) — mesma
   precedência já decidida na política de notificação do
   `desenho_aplicacao`. Critério de desempate (dois avisos da mesma
   severidade): o de `data_inicio` mais recente.
4. Se nenhum aviso cobrir POA: resultado é "sem aviso vigente".
5. **Falha segura**: qualquer erro de rede, JSON malformado, ou ausência de
   campo esperado (`poligono`, `severidade`, etc. nos avisos que sobraram
   depois do passo 2) faz o script sair com código 1 e logar o motivo, sem
   tocar `app/dados.js`. Mesma filosofia de `colher_previsao_diaria.py`:
   rodando sem supervisão humana, o código de saída é o único aviso de que
   o dia falhou.

## Componente 2 — geração de `app/dados.js`

O mesmo script, depois de decidir o aviso (ou a ausência dele), escreve
`app/dados.js` do zero. Três blocos ficam **fixos, embutidos no script**
(não lidos do `dados.js` antigo — a geração é sempre do zero, pra não
herdar lixo de uma execução anterior):

- `previsao` — os mesmos valores de hoje (`taxa_confirmacao: 0.303`, etc.),
  cópia literal.
- `aviso_exemplo` — o aviso de id 55157, cópia literal do que é `aviso` hoje
  em `dados.js`. Existe pra alimentar a visão de exemplo (componente 3) e
  **nunca é sobrescrito pela colheita** — é histórico, fixo.
- A tabela de lacuna por severidade, as 3 linhas medidas (confirmadas lendo
  `reports/lacuna_granularidade_avisos_2026_08_21_00_29.md`, tabela "só
  chuva" — a mesma que `dados.js` já usa hoje):

  | severidade | taxa_area | taxa_ponto | razão |
  |---|---|---|---|
  | Grande Perigo | 0,591 | 0,031 | 19,1 |
  | Perigo | 0,564 | 0,075 | 7,5 |
  | Perigo Potencial | 0,309 | 0,038 | 8,1 |

O que varia por execução:
- `aviso` — o aviso colhido (campos originais da API, sem edição, mesmo
  princípio editorial de hoje), ou ausente/`null` se não há nenhum vigente.
  Dois campos são **derivados**, não originais: `municipios_total` =
  `len(aviso['municipios'])`, e `municipio_exemplo`/`geocode_exemplo` ficam
  fixos em `"Porto Alegre - RS"`/`"4314902"` (o escopo é sempre POA — o nome
  do campo manteve "exemplo" só pra não mexer em mais lugares do app.js).
  **Verificar na implementação**: `riscos`/`instrucoes` em `dados.js` hoje
  são arrays (lista de strings), mas não está confirmado se
  `avisos/ativos` já devolve assim ou se precisa de split — conferir contra
  uma resposta real antes de fechar o parsing.
- `lacuna` — a linha da tabela acima que casa com `aviso.severidade`
  (quando há aviso; omitida/irrelevante no estado sem aviso).
- `colhido_em` — timestamp ISO UTC do momento da colheita, campo novo no
  nível raiz de `VAND_DADOS` (não dentro de `aviso`, porque se aplica
  também ao estado sem aviso). Substitui o "ÚLTIMA CONSULTA: AGORA MESMO"
  fixo de hoje, que vira falso assim que a colheita passa a ser periódica.

O comentário de cabeçalho do arquivo gerado deve deixar claro que é
autogerado (nome do script, timestamp), manter a explicação de procedência
e a regra editorial (taxa de confirmação não é taxa de acerto) já presentes
hoje, e explicar o papel de `aviso_exemplo`.

## Componente 3 — mudanças em `app/app.js`

**Problema real, não cosmético:** hoje `renderAlerta(calmo)` só mostra o
estado "sem aviso" quando a rota é explicitamente `#/alerta/calmo` — a rota
padrão `#/alerta` sempre assume que `dados.aviso` existe. Com a colheita
automática, um dia sem aviso vigente em POA (bem provável em 4 dias) faria a
rota padrão quebrar ou renderizar lixo.

**Segundo problema, descoberto neste desenho:** o link "Ver um exemplo de
Aviso vigente" no card calmo hoje aponta pra `#/alerta` — que funciona só
porque `dados.aviso` é sempre o exemplo fixo. Assim que `aviso` passa a
poder ser `null`, esse link vira um loop de volta pro próprio card calmo.

Mudanças:
1. `renderAlerta` passa a receber o sub-segmento da rota (`undefined`,
   `'calmo'` ou `'exemplo'`) em vez de um booleano:
   - sem sub-segmento: mostra `dados.aviso` se existir, senão o card calmo
     (decidido pelo **dado**, não pela rota).
   - `'calmo'`: força o card calmo (mantido pra quem quiser linkar direto
     pra essa demonstração).
   - `'exemplo'` (rota nova, `#/alerta/exemplo`): mostra `dados.aviso_exemplo`
     no mesmo layout de aviso vigente, com um rótulo deixando claro que é
     histórico (não reaproveitar a linha "ÚLTIMA CONSULTA" ali — ela mostra
     a data real da última colheita, que ficaria ao lado de um aviso de
     julho e confundiria).
2. O link do card calmo muda de `#/alerta` para `#/alerta/exemplo`.
3. "ÚLTIMA CONSULTA" para de ser texto fixo e passa a formatar
   `dados.colhido_em` com o `formatData()` que já existe.
4. Conferido: `renderRegistro` já trata `dados.aviso` como opcional
   (`dados && dados.aviso ? ... : null`) — nenhuma mudança necessária ali.

## Componente 4 — `.github/workflows/avisos.yml`

Workflow novo, separado de `colheita.yml` porque aquele é deliberadamente
isolado da `main` e este precisa tocar a `main` de propósito. Espelha os
padrões já em uso em `colheita.yml`:
- `schedule: cron "0 12 * * *"` (mesmo horário, 12 UTC) + `workflow_dispatch`
  pra rodar manualmente antes da apresentação.
- `permissions: contents: write`.
- `concurrency` própria (grupo `avisos`), pra dois disparos não colidirem.
- Dependências: `pandas`, `numpy`, `pyarrow`, `requests` — as mesmas de
  `colheita.yml`. `estacoes_do_aviso` (reaproveitada de `src/avisos.py`)
  recebe um DataFrame, e `colheita/estacoes.parquet` já está versionado no
  repo (é o mesmo arquivo que `colheita.yml` copia para a colheita ECMWF),
  então basta `pd.read_parquet('colheita/estacoes.parquet')` — sem precisar
  do passo de branch/cache que `colheita.yml` faz pra idempotência.
- Commit com a mesma identidade de bot (`avisos-bot
  <avisos-bot@users.noreply.github.com>`), guarda de "nada novo para
  publicar" via `git diff --quiet` antes de commitar (evita commit vazio
  quando o aviso não mudou de um dia pro outro).

**Risco aceito, registrado por decisão explícita do usuário:** sem PR nem
revisão humana no meio. Um aviso malformado que passe pelas validações do
script, ou uma mudança de severidade pouco antes da apresentação, redesenha
a tela ao vivo sem ninguém olhar antes. A mitigação que este desenho oferece
é a falha ser sempre segura (nunca publica lixo), não a ausência de
surpresas. Vale considerar pausar o `schedule` (deixando só `workflow_dispatch`) durante
a janela 19–23/10, mas isso é uma decisão operacional de última hora, fora
deste documento.

## Testes

`tests/test_aviso_poa.py`, mesmo padrão sem-rede de `tests/test_colheita.py`
(monkeypatch na função de busca HTTP, `runpy.run_path` pra rodar o script,
código de saída como sinal):
- aviso cobrindo POA é selecionado e vira `app/dados.js` com os campos
  certos;
- dois avisos simultâneos cobrindo POA: vence o mais severo;
- nenhum aviso cobre POA: `app/dados.js` sai no estado sem aviso, sem
  quebrar;
- resposta malformada / exceção de rede: script sai com código 1, não
  escreve `app/dados.js` (fixture com um `dados.js` anterior, confirma que
  continua intacto depois da falha).

Depois de implementado, rodar `tests/app_smoke.html` de novo via Chrome
headless (mesmo processo usado na reforma de design anterior) pra confirmar
que a rota `/alerta/exemplo` e o estado calmo automático não quebram nenhuma
asserção existente.

## Riscos

- **Rede do GitHub Actions até o INMET**: testada nesta sessão
  (`avisos/ativos` respondeu 200 de um ambiente de teste); `colheita.yml` já
  faz esse teste de alcance como diagnóstico a cada execução, então qualquer
  bloqueio futuro aparece no log antes de doer.
- **Deploy automático sem revisão** — ver nota no Componente 4.
- **Schema da API mudar silenciosamente**: campos ausentes fazem o script
  falhar seguro (sai com erro, não publica), não gerar dado incorreto.

## Correções feitas no plano (18/10/2026)

Descobertas ao ler o código e a API real ao escrever
`docs/superpowers/plans/2026-10-18-colheita-aviso-inmet.md`. Onde divergem do
texto acima, **vale esta seção**.

- `avisos/ativos` devolve `{"hoje": [...], "futuro": [...]}`; vigente = `hoje`.
- `riscos`/`instrucoes` já são listas (a pendência "verificar" do Componente 2
  está resolvida); `municipios` é string, o total sai de `geocodes`.
- Só avisos de chuva (`Chuvas Intensas`, `Tempestade`, `Acumulado de Chuva`):
  o texto da tela e a tabela de lacuna são de chuva.
- `lacuna_exemplo` entra no dado (o exemplo 55157 precisa da própria linha).
- O push do bot (`GITHUB_TOKEN`) **não dispara** o `deploy.yml`, ao contrário do
  que o Escopo afirma; o `avisos.yml` aciona o deploy por `workflow_dispatch`.
- O service worker passa a buscar `dados.js` primeiro na rede.
- O `dados.js` muda todo dia (`colhido_em`), então há um commit diário.
