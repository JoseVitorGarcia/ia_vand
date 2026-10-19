// Gera reports/revisao_textos_estudo_2026_10_18.md: para cada Tema pedido, o texto
// ANTIGO e o NOVO de cada Seção, lado a lado, para o usuário conferir que nenhum
// fato mudou. A revisão científica é humana (ADR 0001); isto só a torna viável.
//
// Uso: node scripts/gerar_revisao_textos.js <ref-git-do-texto-antigo> <id-do-tema>...
const { execSync } = require('child_process');
const fs = require('fs');
const vm = require('vm');

function trilha(src) {
  const w = {};
  vm.runInNewContext(src, { window: w });
  return w.VAND_CONTENT.trilha;
}

const [ref, ...ids] = process.argv.slice(2);
if (!ref || !ids.length) { console.error('uso: node scripts/gerar_revisao_textos.js <ref> <id-do-tema>...'); process.exit(1); }
const antigo = trilha(execSync(`git show ${ref}:app/content.js`, { encoding: 'utf8', maxBuffer: 1 << 26 }));
const novo = trilha(fs.readFileSync('app/content.js', 'utf8'));

const antigoMd = (s) => {
  if (s.paragrafos) return s.paragrafos.join('\n\n');
  if (s.texto) return s.texto;
  const partes = [];
  (s.itens || []).forEach((d) => partes.push(`- ${d.valor ? d.valor + ': ' : ''}${d.rotulo}`));
  (s.termos || []).forEach((t) => partes.push(`- **${t.palavra}**: ${t.definicao}`));
  if (s.nota) partes.push('\n' + s.nota);
  return partes.join('\n');
};

const blocoMd = (b) => {
  switch (b.tipo) {
    case 'p': return b.texto;
    case 'lista': return b.itens.map((t, i) => (b.ordenada ? `${i + 1}. ` : '- ') + t).join('\n');
    case 'passos': return b.itens.map((p) => `- **${p.rotulo}${p.titulo ? ' · ' + p.titulo : ''}**: ${p.texto}`).join('\n');
    case 'comparacao': return b.lados.map((l) => `**${l.titulo}**\n` + l.itens.map((t) => '- ' + t).join('\n')).join('\n\n× \n\n');
    case 'pergunta': return `> **Pare e pense:** ${b.pergunta}\n> *Resposta:* ${b.resposta}`;
    case 'numeros': return b.itens.map((d) => `- ${d.valor ? d.valor + ': ' : ''}${d.rotulo}`).join('\n') + (b.nota ? '\n\n' + b.nota : '');
    case 'destaque': return `> ${b.titulo ? '**' + b.titulo + '.** ' : ''}${b.texto}`;
    case 'glossario': return b.termos.map((t) => `- **${t.palavra}**: ${t.definicao}`).join('\n') + (b.nota ? '\n\n' + b.nota : '');
    default: return `(bloco ${b.tipo})`;
  }
};
const novoMd = (s) => (s.tipo === 'blocos' ? s.blocos.map(blocoMd).join('\n\n') : antigoMd(s));

const saida = [
  '# Revisão dos textos de estudo: antes e depois',
  '',
  `Gerado por \`scripts/gerar_revisao_textos.js\`. Texto antigo tirado de \`${ref}\`.`,
  'Regra da reescrita: nenhum fato, número, nome, data ou ressalva novo, e nenhuma ressalva removida;',
  'só reordenar, dividir, cortar repetição e trocar a pontuação. **Confira, Seção a Seção, se o "Depois" diz o mesmo que o "Antes".**',
  ''
];
ids.forEach((id) => {
  const a = antigo.find((t) => t.id === id);
  const n = novo.find((t) => t.id === id);
  if (!a || !n) { console.error('Tema não encontrado: ' + id); process.exit(1); }
  saida.push(`## ${n.titulo}`, '');
  n.secoes.forEach((sn, i) => {
    saida.push(`### Seção ${i + 1}: ${sn.titulo}`, '', '**Antes**', '', antigoMd(a.secoes[i]), '', '**Depois**', '', novoMd(sn), '', '---', '');
  });
});
fs.mkdirSync('reports', { recursive: true });
fs.writeFileSync('reports/revisao_textos_estudo_2026_10_18.md', saida.join('\n'));
console.log('escrito reports/revisao_textos_estudo_2026_10_18.md (' + ids.length + ' Tema(s))');
