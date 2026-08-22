/*
 * Service worker do protótipo: cache-first sobre um conjunto fixo de arquivos,
 * para o app abrir sem rede. O público alvo é quem tem plano de dados curto.
 *
 * Ao mudar qualquer arquivo do app, incremente VERSAO — senão o navegador
 * continua servindo a versão velha do cache.
 */
var VERSAO = 'vand-v2';
var ARQUIVOS = [
  './',
  './index.html',
  './styles.css',
  './content.js',
  './app.js',
  './manifest.webmanifest',
  './icons/icon-192.png',
  './icons/icon-512.png'
];

self.addEventListener('install', function (e) {
  e.waitUntil(
    caches.open(VERSAO).then(function (c) { return c.addAll(ARQUIVOS); }).then(function () {
      return self.skipWaiting();
    })
  );
});

self.addEventListener('activate', function (e) {
  e.waitUntil(
    caches.keys().then(function (nomes) {
      return Promise.all(
        nomes.filter(function (n) { return n !== VERSAO; }).map(function (n) { return caches.delete(n); })
      );
    }).then(function () { return self.clients.claim(); })
  );
});

self.addEventListener('fetch', function (e) {
  if (e.request.method !== 'GET') return;
  e.respondWith(
    caches.match(e.request).then(function (hit) {
      return hit || fetch(e.request).catch(function () { return caches.match('./index.html'); });
    })
  );
});
