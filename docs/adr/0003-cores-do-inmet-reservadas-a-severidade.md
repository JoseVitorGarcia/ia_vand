# As cores do INMET são reservadas exclusivamente à Severidade de Aviso

O app usa o campo `aviso_cor` do INMET — o hexadecimal oficial da Severidade,
`#FFFE00` para o amarelo e equivalentes para laranja e vermelho — na tela de Aviso.
Amarelo, laranja e vermelho **não podem ser usados como cor decorativa em nenhuma
outra parte do app**. O módulo educacional usa paleta neutra própria.

A razão é a mesma que levou a adotar as cores do INMET: elas já vêm interpretadas
de graça pelo usuário, porque são as que ele vê no noticiário. Esse é o único
código de cor do app que não precisa ser ensinado — e ele só funciona enquanto for
raro. Um card de Tema vermelho ou um botão de quiz laranja gastam esse
significado.

Fica registrado porque é uma decisão barata de desfazer sem querer: qualquer pessoa
escolhendo cores para uma tela nova, daqui a um mês, não teria como adivinhar.

## Exceção: o vermelho da marca

O ponto da logo do VAND é `#ec1b04`, um vermelho. Ele está dispensado da reserva
acima, com uma condição: **a marca não pode dividir superfície com a Severidade**.
Na prática, ela não aparece no cabeçalho fixo, na tela de Aviso nem na
notificação — hoje só na abertura da Trilha.

A razão de a exceção existir é que o ponto não é decorativo nem semântico: é
identidade. A razão de ela ser condicionada é que o risco real nunca foi a cor
isolada, e sim a vizinhança — um ponto vermelho permanente no topo, encostado num
chip de Severidade, faria o usuário ler marca como aviso. Separadas as
superfícies, o código de cor continua raro onde precisa ser.

Se um dia a marca precisar entrar no cabeçalho fixo, esta exceção cai junto: aí
sim a saída é recolorir o ponto, não afrouxar a reserva.

## Atualização de 18/10/2026: a marca no cabeçalho fixo, sem o ponto

O cabeçalho fixo passou a mostrar a logo completa em toda tela (pedido do
usuário: o app não tinha nenhum elemento que remetesse ao VAND). A exceção do
ponto vermelho **não cai**, porque o que sobe é a variante **sem o ponto**
(`logo-sem-ponto.png` e `logo-sem-ponto-dark.png`, geradas por
`scripts/gerar_logo_sem_ponto.py`). Nada vermelho entra no cabeçalho, então a
marca continua sem dividir superfície com a Severidade.

A regra é vigiada por `tests/test_logo_sem_ponto.py`: os dois PNGs não podem ter
pixel de dominância vermelha. O ponto segue restrito à splash, ao recibo de
Registro e à tela Sobre. Se alguém quiser o ponto no cabeçalho, a saída continua
sendo a de cima: recolorir o ponto, não afrouxar a reserva.
