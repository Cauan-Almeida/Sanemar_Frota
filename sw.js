// ⚠️ AUMENTE ESTE NÚMERO SEMPRE QUE FIZER MUDANÇAS NO CÓDIGO
const APP_VERSION = 'v9.0'; // <<< MUDE AQUI PARA FORÇAR ATUALIZAÇÃO
const CACHE_NAME = `frota-sanemar-cache-${APP_VERSION}`;
const OLD_CACHES = [
  'frota-sanemar-cache-v3',
  'frota-sanemar-cache-v4', 
  'frota-sanemar-cache-v5',
  'frota-sanemar-cache-v6-clean',
  'frota-sanemar-cache-v7-final',
  'frota-sanemar-cache-v8-connection'
];
const urlsToCache = [
  '/',
  '/dashboard',
  '/static/style.css',
  '/static/app.js',
  '/static/app-melhorado.js',
  '/static/toast.js',
  '/static/dashboard.js',
  '/static/dashboard-realtime.js',
  '/static/veiculos-tab.js',
  '/static/km-multas.js',
  '/static/relatorios-tab.js',
  '/static/revisoes-tab.js',
  '/static/connection-monitor.js',
  '/static/manifest.json'
];

// Evento de Instalação: abre o cache e armazena os arquivos do app shell
self.addEventListener('install', event => {
  console.log(`[SW ${APP_VERSION}] 🔄 Instalando nova versão...`);
  self.skipWaiting(); // Força ativação imediata
  
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then(cache => {
        console.log(`[SW ${APP_VERSION}] ✅ Cache aberto`);
        return cache.addAll(urlsToCache);
      })
      .catch(err => console.warn('[SW v8] Erro na instalação:', err))
  );
});

// Evento de Fetch: responde com o cache se disponível, senão busca na rede
self.addEventListener('fetch', event => {
  const { request } = event;
  const requestURL = request.url;
  
  // FILTRO 1: Ignora extensões do Chrome - NÃO chama respondWith
  if (requestURL.startsWith('chrome-extension://') || 
      requestURL.startsWith('chrome://') ||
      requestURL.startsWith('moz-extension://')) {
    return; // Deixa passar sem interceptar
  }
  
  // FILTRO 2: Ignora métodos que não sejam GET - NÃO chama respondWith
  if (request.method !== 'GET') {
    return; // Deixa passar sem interceptar
  }
  
  // FILTRO 3: Ignora APIs de tempo real (sempre busca da rede)
  const noCacheAPIs = [
    '/api/veiculos_em_curso',
    '/api/saida',
    '/api/chegada',
    '/api/cancelar',
    '/api/dashboard_realtime',
    '/api/saidas/recent',
    '/api/dashboard_stats'
  ];
  
  if (noCacheAPIs.some(api => requestURL.includes(api))) {
    event.respondWith(
      fetch(request).catch(err => {
        console.warn('[SW v8] Erro na rede para API:', err);
        return new Response('{"error":"Offline"}', { 
          status: 503,
          headers: { 'Content-Type': 'application/json' }
        });
      })
    );
    return;
  }
  
  // Para o resto: cache-first strategy (APENAS arquivos estáticos)
  const url = new URL(request.url);
  const shouldCache = url.pathname.startsWith('/static/');
  
  // Se não for arquivo estático, deixa passar direto (evita redirect loop)
  if (!shouldCache) {
    return;
  }
  
  event.respondWith(
    caches.match(request)
      .then(cachedResponse => {
        if (cachedResponse) {
          // Retorna do cache imediatamente (sem background update para evitar clone())
          return cachedResponse;
        }
        
        // Se não está no cache, busca da rede
        return fetch(request)
          .then(networkResponse => {
            // Não cacheia respostas inválidas, redirects ou já consumidas
            if (!networkResponse || 
                networkResponse.status !== 200 || 
                networkResponse.type === 'opaque' ||
                networkResponse.redirected) {
              return networkResponse;
            }
            
            // Clone ANTES de retornar (Response só pode ser lida uma vez)
            const responseToCache = networkResponse.clone();
            
            caches.open(CACHE_NAME).then(cache => {
              cache.put(request, responseToCache).catch(() => {
                // Silencia erros de cache
              });
            });
            
            return networkResponse;
          })
          .catch(err => {
            console.warn(`[SW ${APP_VERSION}] ⚠️ Erro na rede:`, err);
            return new Response('Offline', { status: 503 });
          });
      })
  );
});

// Evento de Ativação: limpa caches antigos
self.addEventListener('activate', event => {
  console.log(`[SW ${APP_VERSION}] 🔄 Ativando e limpando cache antigo...`);
  
  event.waitUntil(
    Promise.all([
      // Remove TODOS os caches antigos
      caches.keys().then(cacheNames => {
        return Promise.all(
          cacheNames.map(cacheName => {
            if (cacheName !== CACHE_NAME) {
              console.log(`[SW ${APP_VERSION}] 🗑️ Removendo cache antigo: ${cacheName}`);
              return caches.delete(cacheName);
            }
          })
        );
      }),
      // Assume controle imediatamente de TODAS as páginas
      self.clients.claim().then(() => {
        console.log(`[SW ${APP_VERSION}] ✅ Controle assumido - enviando mensagem de reload`);
        // Notifica todos os clientes sobre a atualização
        return self.clients.matchAll().then(clients => {
          clients.forEach(client => {
            client.postMessage({
              type: 'SW_UPDATED',
              version: APP_VERSION
            });
          });
        });
      })
    ])
  );
});
