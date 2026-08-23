# app/ — protótipo navegável do IA_VAND

Estático: HTML, CSS e JavaScript sem build, sem framework e sem back-end.

## Rodar

Com Docker, a partir da raiz do repositório:

```sh
docker compose up --build     # http://localhost:8781
```

Sem Docker, para editar conteúdo com recarga rápida:

```sh
cd app && python3 -m http.server 8000
```

Precisa de servidor (e não de `file://`) por causa do service worker. Para abrir
no celular na mesma rede, troque `localhost` pelo IP da máquina — mas repare que
instalação na tela inicial e modo offline só funcionam em HTTPS ou `localhost`.

### O que o Docker adiciona

`Dockerfile` (nginx sem root, porta 8080 interna) + `docker/nginx.conf`. A
configuração do nginx tem duas regras que **não são detalhe**: `sw.js` sai com
`Cache-Control: no-cache` — senão o navegador segue rodando o service worker
velho — e o `.webmanifest` sai com `application/manifest+json`, sem o que o
Chrome ignora o manifesto e não oferece instalar.

O `.dockerignore` também não é opcional: o repositório tem 5,5 GB de dado e
modelo, e sem ele o build tentaria mandar tudo isso para o daemon.

## Estrutura

| arquivo                | o que é                                                                 |
| ---------------------- | ----------------------------------------------------------------------- |
| `index.html`           | as três abas e o esqueleto da página                                    |
| `app.js`               | roteamento por hash, telas, quiz e progresso                            |
| `content.js`           | **o conteúdo da Trilha** — é aqui que se escreve um Tema novo           |
| `styles.css`           | paleta neutra, layout mobile-first, tema claro e escuro                 |
| `sw.js`                | cache para funcionar offline; **incremente `VERSAO` ao mudar arquivos** |
| `manifest.webmanifest` | instalação na tela inicial do celular                                   |

## Antes de mexer

- `CONTEXT.md` na raiz: o que significam Trilha, Tema, Nível, Item, Reflexão e Fonte.
- `docs/adr/0001`: o texto é de redação própria, ancorado em fonte oficial. Não cole
  parágrafo de livro do ENCCEJA aqui.
- `docs/adr/0002`: uma Trilha só, com o Nível como selo. Não criar trilhas paralelas.
- `docs/adr/0003`: amarelo, laranja e vermelho são exclusivos da severidade de aviso
  do INMET. Não usar como cor decorativa.

## Verificar

```sh
python3 -m http.server 8000            # a partir da RAIZ do repositório
google-chrome --headless=new --dump-dom http://localhost:8000/tests/app_smoke.html
```

Procure por `FALHA` na saída. O teste percorre a trilha, responde o quiz certo e
errado, e confere o progresso guardado.
