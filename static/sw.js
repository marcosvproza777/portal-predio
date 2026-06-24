/**
 * Service Worker — Portal Pred.IO
 *
 * SEGURANÇA:
 *   - NUNCA cacheia: PDFs privados, tokens, dados de sessão, dados de ativos,
 *     relatórios, chamados, alertas, documentos internos, dados de outro cliente.
 *   - SÓ cacheia: assets estáticos públicos (CSS, JS, imagens, ícones, manifest).
 *   - Todos os requests dinâmicos passam direto para a rede (sem cache).
 *
 * ESCOPO:
 *   - Registrado em /app/static/sw.js
 *   - Cacheia apenas requests dentro de /app/static/
 *   - Requests fora do escopo passam sem interceptação
 */

const CACHE_NAME     = 'predio-static-v2';
const STATIC_ORIGIN  = '/app/static/';

// Assets que podem ser cacheados com segurança (apenas estáticos públicos)
const CACHE_PATTERNS = [
  /\/app\/static\/.*\.png$/,
  /\/app\/static\/.*\.svg$/,
  /\/app\/static\/.*\.ico$/,
  /\/app\/static\/manifest\.json$/,
];

// NUNCA cachear (dados sensíveis, dinâmicos, PDFs privados)
const NEVER_CACHE = [
  /\/api\//,
  /\.pdf$/i,
  /token/i,
  /session/i,
  /client_id/i,
  /sid=/,
  /relatorio/i,
  /chamado/i,
  /ativo/i,
  /alerta/i,
  /documento/i,
  /_stcore\//,
  /stream/i,
  /websocket/i,
];

function shouldCache(url) {
  const u = new URL(url);
  // Rejeita qualquer coisa fora de /app/static/
  if (!u.pathname.startsWith(STATIC_ORIGIN)) return false;
  // Rejeita o próprio SW
  if (u.pathname.includes('sw.js')) return false;
  // Rejeita dados sensíveis
  if (NEVER_CACHE.some(p => p.test(u.href))) return false;
  // Aceita apenas padrões estáticos conhecidos
  return CACHE_PATTERNS.some(p => p.test(u.pathname));
}

self.addEventListener('install', event => {
  // Ativa imediatamente sem esperar tabs antigas fecharem
  self.skipWaiting();
  event.waitUntil(
    caches.open(CACHE_NAME).then(cache =>
      cache.addAll([
        '/app/static/manifest.json',
        '/app/static/icons/icon-192.png',
        '/app/static/icons/icon-512.png',
        '/app/static/icons/icon-180.png',
      ]).catch(() => {})  // ignora erros de pre-cache
    )
  );
});

self.addEventListener('activate', event => {
  // Remove caches antigas
  event.waitUntil(
    caches.keys().then(keys =>
      Promise.all(
        keys
          .filter(k => k !== CACHE_NAME)
          .map(k => caches.delete(k))
      )
    ).then(() => self.clients.claim())
  );
});

self.addEventListener('fetch', event => {
  const req = event.request;

  // Apenas GET — nunca intercepta POST/PUT/DELETE
  if (req.method !== 'GET') return;

  // Apenas cacheia o que é seguro
  if (!shouldCache(req.url)) return;

  event.respondWith(
    caches.open(CACHE_NAME).then(cache =>
      cache.match(req).then(cached => {
        if (cached) return cached;
        return fetch(req)
          .then(response => {
            // Só armazena respostas válidas (status 200)
            if (response && response.status === 200 && response.type !== 'opaque') {
              cache.put(req, response.clone());
            }
            return response;
          })
          .catch(() => cached || new Response('', { status: 503 }));
      })
    )
  );
});
