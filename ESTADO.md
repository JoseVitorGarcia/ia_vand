# Estado do IA_VAND

Atualizado em **22/08/2026**. Uma página com onde o projeto está, o que foi
medido, o que está decidido e o que continua em aberto.

> **Divisão de trabalho com o `README.md`:** ele documenta como o pipeline
> funciona e como rodá-lo — instalação, features, configuração, uso da API. Este
> arquivo guarda o **estado**: o que foi medido, o que foi refutado, o que está
> decidido e o que falta. Quando os dois divergirem, vale este.

---

## O que o projeto é hoje

Começou como um modelo próprio para prever chuva extrema no Rio Grande do Sul a
partir de 100 estações do INMET. Ao ser medido contra uma régua forte — a
previsão do **ECMWF** (_European Centre for Medium-Range Weather Forecasts_) —
descobriu-se que a previsão europeia, gratuita e sem treino nenhum, supera o
modelo local por **3,6x** em PR-AUC (área sob a curva precisão-recall) no
enquadramento operacional.

Isso redirecionou o trabalho duas vezes, sempre por medição:

1. **Corrigir a previsão europeia com observação local** (o que a sigla **MOS**,
   _Model Output Statistics_, descreve). Medido e **refutado**.
2. **Medir a lacuna de granularidade** entre o alerta regional oficial e o que se
   observa num ponto — que é a justificativa técnica da aplicação. **Feito.**

O produto passa a ser um aplicativo que retransmite o aviso oficial do INMET por
localização, oferece a previsão europeia como camada consultável e coleta
registros de alagamento dos cidadãos.

---

## O que foi medido

| #   | pergunta                                     | resposta                                                                                    | relatório                                                 |
| --- | -------------------------------------------- | ------------------------------------------------------------------------------------------- | --------------------------------------------------------- |
| 1   | A previsão do ECMWF ganha do nosso modelo?   | **Sim, por 3,6x** em PR-AUC operacional                                                     | `reports/baseline_ifs_2026_08_19_13_17.md`                |
| 2   | O erro de volume do ECMWF é corrigível?      | **Não.** A estação explica 0,80% da variância do resíduo                                    | `reports/vies_ifs_2026_08_19_13_34.md`                    |
| 3   | A observação local acrescenta sobre o ECMWF? | **Não — piora.** −0,0481 [−0,0856, −0,0144]                                                 | `reports/acrescimo_local_2026_08_20_15_58.md`             |
| 4   | A previsão europeia crua é entregável?       | **Sim.** Corte em 30 mm dá 71% dos eventos a 30% de confirmação, 5,1 avisos por estação-ano | `reports/curva_operacao_ifs_2026_08_20_16_12.md`          |
| 5   | Quanto o alerta regional perde até o ponto?  | **De 3,1x a 17,9x**, e quanto mais grave o aviso, maior a lacuna                            | `reports/lacuna_granularidade_avisos_2026_08_21_00_29.md` |

Contexto do estudo 5: 98,4% dos eventos observados tinham aviso vigente, ao preço
de 45% de todos os estação-dias estarem sob algum aviso. Desenho e método em
`reports/desenho_estudo_avisos_2026_08_20.md`.

**Ordem de leitura recomendada:** o desenho (seção 2 resume tudo em cinco
linhas), depois o relatório 5, depois o 4.

---

## Os três objetivos da aplicação

Entrega prevista: **protótipo navegável**, uma pessoa, até outubro de 2026. O
esqueleto do app existe em `app/` desde 21/08/2026, com as três abas; o que está
pronto por baixo dele é o **dado e a medição** que as três funcionalidades
consomem.

| objetivo                                                       | o que já existe                                                                                                                                                                                    | o que falta                                                                                                          |
| -------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------- |
| **1. Alerta por localização**, retransmitindo o aviso do INMET | Endpoint verificado e arquivo de **5.958 avisos** colhido. `src/avisos.py` casa estação e aviso por geometria, com 18 testes. Os avisos já trazem geocódigo IBGE, polígono, riscos e instruções prontos para exibir. A medição que justifica a funcionalidade está feita (lacuna de 3,1x a 17,9x). | A tela. A política de notificação está decidida (ver abaixo). |
| **2. Registro de alagamento pelo cidadão**                     | Nada construído. A justificativa técnica está clara: alagamento **não é chuva**, depende de drenagem e topografia, e nenhum modelo meteorológico o prevê — então isto não é o que foi refutado.       | Tudo. E a decisão da coleta do "não", que **não tem conserto retroativo** (ver "Em aberto", item 4).                    |
| **3. Conteúdo de estudo** sobre clima, geografia e meteorologia | A matéria-prima é **material oficial do governo**, não os nossos relatórios: Livros do Estudante do ENCCEJA (MEC/INEP) e a cartilha _Desastres Hidrológicos_ (Corrêa e Marques, UERJ/Prodocência, 2023 — publicação independente **hospedada** no Cemaden Educação, não emitida por ele), todos em `material_estudo_vand_modulo_3/`. Desenho fechado em 21/08/2026 — ver `CONTEXT.md` e `docs/adr/0001` a `0003`. O protótipo existe em `app/` e a Trilha está **completa: os três Temas escritos**, com 62 verificações passando. | Nada. É o único dos três objetivos entregue. |

A camada consultável do objetivo 1 — a nossa previsão ao lado do aviso oficial —
também já tem os números de que precisa: corte em 30 mm dá 71% dos eventos a 30%
de confirmação, e é essa taxa que deve aparecer junto do aviso, não escondida.

**Leitura honesta do estágio:** o objetivo 3 está **entregue** — app, três
Temas e teste. O objetivo 1 está pronto do lado do dado e parado do lado da
interface. O objetivo 2 não começou, e é o único cujo atraso custa caro: cada
dia sem a tela é um dia sem coletar registros, e o valor dele depende de
acumular tempo. Vale reparar que o objetivo concluído é o que menos depende do
relógio, e o que não começou é o que mais depende.

### Política de notificação (decidida em 21/08/2026)

Empurrar todos os avisos daria **413 notificações por pessoa por ano** — mais de
uma por dia. A severidade domina o tipo: filtrar tipos leva 413 para 343;
filtrar severidade leva para 18.

| nível                                     | dispara                                      | por pessoa/ano       |
| ----------------------------------------- | -------------------------------------------- | -------------------- |
| **Interrompe** — acende a tela e vibra    | Grande Perigo, tipos de chuva e vento        | **6,4** (pior mês 4) |
| **Silencioso** — ponto na aba, sem número | Perigo, mesmos tipos                         | 45,1 (pior mês 12)   |
| Não notifica                              | Perigo Potencial e os outros sete tipos      | —                    |

Regras que fazem esses números:

- **Deduplicação de 6 h por localização.** 56,8% das notificações consecutivas na
  mesma estação são o mesmo episódio re-avisado; a dedup sozinha corta o volume
  pela metade e vale mais que qualquer escolha de tipo.
- **Grande Perigo sempre dispara**, mesmo logo após um Perigo. A dedup nunca pode
  rebaixar uma interrupção a selo.
- **Sem horário de silêncio:** só 5,4% chegam entre 22h e 6h, e é o caso em que
  acordar se justifica.
- **O selo indica presença, não contagem.** Um badge com número lê como caixa de
  e-mail e convida a limpar sem ler.
- **Redação: _"aviso de Grande Perigo para a sua região"_**, nunca a rua — a
  confirmação no ponto é de 3,4%, então a lacuna medida precisa estar visível na
  própria frase.
- Cores da severidade vêm do campo `aviso_cor` do próprio INMET.

Como isso aparece no protótipo — os três estados na mesma navegação mostram a
política inteira em três toques:

| nível            | representação na tela                                                                            |
| ---------------- | ------------------------------------------------------------------------------------------------ |
| Grande Perigo    | maquete de notificação: tela de bloqueio ou banner, com o texto _"para a sua região"_             |
| Perigo           | selo na lista de avisos e ponto na aba, sem maquete de notificação                                |
| Perigo Potencial | só na lista, sem selo — presente para quem procura, invisível para quem não                       |

O protótipo é navegável e **não implementa notificação de verdade**: estas regras
são especificação de tela, e servem para a apresentação demonstrar a decisão em
vez de apenas descrevê-la.

---

## Regras que qualquer texto do projeto precisa respeitar

- **Nunca citar ganho sobre a persistência** como afirmação de valor. Os ganhos
  de +185% e +375% dos relatórios antigos são reais, mas contra um adversário que
  a previsão europeia supera em 17x. A régua é o ECMWF.
- **Taxa de confirmação não é taxa de acerto.** Um aviso comunica risco; aviso
  não confirmado não é erro. Vale para o INMET e vale para nós — os 30% da nossa
  regra são confirmação, não erro.
- **A lacuna não mede quem prevê melhor.** O aviso é produto de área recebido num
  ponto. O que se quantifica é o que a especificidade pontual acrescenta.
- **A unidade estação-dia por máximo do dia é inválida** para features de chuva
  passada: na hora 23 a janela de 24 h já viu a chuva do dia que o rótulo mede.
  Usar o enquadramento operacional às 12 UTC.
- Os números da previsão arquivada são **estimativa otimista** — ela entrega, a
  cada hora, a rodada mais recente antes dela, e não a que o operador teria.

---

## Decidido

- **Arquitetura do MOS:** fechada com resultado negativo. Não haverá combinador.
- **Produto:** aviso oficial do INMET retransmitido por localização; a nossa
  previsão entra como camada consultável, nunca como notificação empurrada — com
  30% de confirmação, 7 de cada 10 notificações não se confirmariam.
- **Aplicação:** protótipo navegável, três funcionalidades (alerta, registro de
  alagamento, conteúdo de estudo), construído por uma pessoa até outubro.
- **Enquadramento do estudo:** lacuna de granularidade, não avaliação do INMET.
- **Notificação:** dois níveis — Grande Perigo interrompe, Perigo é silencioso,
  Perigo Potencial não notifica; com deduplicação de 6 h. Detalhe acima.
- **A lacuna vai ao texto como razão**, por ser adimensional.

## Em aberto

1. **Assimetria de custo com a defesa civil.** É o que escolhe entre alertar a
   20 mm (83% dos eventos, 10 avisos por estação-ano) e a 42 mm (51%, 2,4). Não
   há medição que decida isso — é conversa com quem recebe o alerta.
2. **Colheita diária de previsões.** 3 dias acumulados, ~58 até a apresentação.
   Roda à mão: `./run.sh scripts/colher_previsao_diaria.py`, idealmente às
   **09:00 local (12 UTC)**, que é o enquadramento de todo o resto do projeto.
3. **O protótipo.** Existe em `app/` desde 21/08/2026 — estático, sem build e
   sem back-end, com as três abas. A aba Estudar está percorrível; Alerta e
   Registro são telas vazias assumidas. É aí que o trabalho continua.
4. **Registro de alagamento:** decidir a coleta do "não" (_"está alagado aí?
   sim / não / não sei"_) **no desenho da tela**. Sem isso o dado é só de
   presença e não treina nada — e não tem conserto retroativo. Vale lembrar por
   que essa funcionalidade não é o que foi refutado: alagamento **não é chuva**,
   depende de drenagem e topografia, e nenhum modelo meteorológico o prevê.

## Dívidas técnicas que não bloqueiam

- O trial 1 do Optuna na regressão nunca é batido, em cinco execuções seguidas.
- 979.722 linhas (21%) descartadas por features obrigatórias ausentes, nunca
  investigadas.
- `models/threshold.json` e `classifier.pkl` ainda são de 18/08; a janela
  t+1..t+24 nunca foi adotada no treino.

---

## Como rodar

```bash
MEM_MAX=11G ./run.sh                              # pipeline completo (~1h10)
MEM_MAX=11G ./run.sh scripts/<script>.py          # uma medição
MEM_MAX=6G  ./run.sh -m pytest tests -q           # 69 testes
```

Nunca rodar `python main.py` direto: o `run.sh` isola o processo num cgroup
próprio, e sem isso um estouro de memória derruba o editor junto.

Planos de execução em `docs/superpowers/plans/`, relatórios em `reports/`,
biblioteca em `src/`, medições e coletores em `scripts/`.

Os relatórios têm data no nome e **não são atualizados**: cada um registra o que
foi medido naquele momento, com o método daquele momento. Quando dois se
contradizem, vale o mais recente — e a tabela da seção "O que foi medido" aponta
sempre para o vigente.
