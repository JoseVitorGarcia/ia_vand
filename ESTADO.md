# Estado do IA_VAND

Atualizado em **21/08/2026**. Uma página com onde o projeto está, o que foi
medido, o que está decidido e o que continua em aberto.

> O `README.md` descreve o escopo **original** — um sistema de aprendizado de
> máquina para prever chuva extrema — e não foi reescrito depois do
> reenquadramento de 19/08/2026. Para entender o projeto hoje, leia este arquivo.

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
- **A lacuna vai ao texto como razão**, por ser adimensional.

## Em aberto

1. **Assimetria de custo com a defesa civil.** É o que escolhe entre alertar a
   20 mm (83% dos eventos, 10 avisos por estação-ano) e a 42 mm (51%, 2,4). Não
   há medição que decida isso — é conversa com quem recebe o alerta.
2. **Colheita diária de previsões.** 2 dias acumulados, ~59 até a apresentação.
   Roda à mão: `./run.sh scripts/colher_previsao_diaria.py`, idealmente às
   **09:00 local (12 UTC)**, que é o enquadramento de todo o resto do projeto.
3. **O protótipo.** Nada construído; nenhuma linha de aplicação no repositório.
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
