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
