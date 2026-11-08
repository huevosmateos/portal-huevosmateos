/* Service worker minimo de Huevos Mateos.
   Solo existe para que el movil permita instalar la web como app.
   NO guarda nada en cache: cada pagina se pide siempre a internet,
   asi los clientes ven siempre la ultima version y los precios de hoy. */
self.addEventListener('install', function () { self.skipWaiting(); });
self.addEventListener('activate', function (e) { e.waitUntil(self.clients.claim()); });
