# IA_VAND

Sistema de previsão de chuva extrema no Rio Grande do Sul, e o aplicativo que
retransmite aviso oficial, coleta registro de alagamento do cidadão e oferece
conteúdo de estudo. Este glossário fixa as palavras que o código e as telas usam;
decisões e justificativas ficam em `docs/adr/`, nunca aqui.

## Previsão e avisos

**Aviso**:
Alerta meteorológico emitido pelo INMET, com severidade, tipo, polígono e período
de vigência. É de terceiro; nós retransmitimos.
_Avoid_: alerta (reservado para o ato de notificar), warning

**Severidade**:
O grau oficial de um Aviso — Perigo Potencial, Perigo, Grande Perigo. Tem cor
própria definida pelo INMET no campo `aviso_cor`.
_Avoid_: nível (reservado ao módulo educacional), gravidade, criticidade

**Previsão**:
A saída do nosso modelo sobre o ECMWF, para uma estação e uma data. Nunca dispara
notificação; é camada consultável.
_Avoid_: predição, alerta nosso

**Registro**:
Uma observação de alagamento enviada por um cidadão, com local, horário e o Aviso
vigente no momento. Inclui o "não está alagado", que é o dado mais valioso.
_Avoid_: report, ocorrência, denúncia

## Módulo educacional

**Trilha**:
A sequência ordenada completa dos Temas. Existe uma só.
_Avoid_: curso, currículo, jornada

**Tema**:
Uma unidade de estudo percorrível de ponta a ponta — texto, reflexão, quiz e
resultado. É a unidade de escrita e a unidade de escopo.
_Avoid_: módulo (já designa as três funcionalidades do app), capítulo (amarraria
a uma fonte só), lição, aula

**Nível**:
O rótulo Básico, Intermediário ou Avançado de um Tema. É ordenação e sinalização,
não uma trilha separada nem uma trava.
_Avoid_: dificuldade, série, etapa, grau

**Item**:
Uma questão de múltipla escolha do quiz de um Tema, com quatro alternativas e uma
explicação de resposta.
_Avoid_: questão, pergunta, exercício

**Reflexão**:
Uma pergunta aberta, sem correção automática, oferecida junto ao texto de um Tema.
Nunca aparece dentro do quiz.
_Avoid_: atividade, dissertativa

**Fonte**:
A obra oficial que embasa um Tema, citada com título, órgão emissor e capítulo ou
página. O texto exibido é de nossa redação; a Fonte é o que o ancora.
_Avoid_: referência, bibliografia, material
