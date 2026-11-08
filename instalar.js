/* instalar.js - Huevos Mateos
   Permite que el cliente instale la web en su movil como una app (icono en la pantalla de inicio).
   - Android/Chrome: boton "Instalar" que abre la ventana de instalacion del movil.
   - iPhone/Safari y navegadores dentro de otras apps: explica como hacerlo a mano.
   No sale ningun aviso automatico: la instalacion solo empieza cuando el cliente pulsa "Instalar app".
   La app solo se puede instalar desde las paginas para clientes con sesion iniciada (las que llevan el manifest). */
(function () {
  if ('serviceWorker' in navigator) {
    window.addEventListener('load', function () {
      navigator.serviceWorker.register('sw.js').catch(function () {});
    });
  }

  var CLAVE = 'hm_instalar_cerrado';
  var DIAS_OCULTO = 15;
  var esMovil = /Android|iPhone|iPad|iPod/i.test(navigator.userAgent);
  var esIOS = /iPhone|iPad|iPod/i.test(navigator.userAgent);
  var instalada = window.matchMedia('(display-mode: standalone)').matches || window.navigator.standalone === true;
  var eventoInstalar = null;
  // Clases en la pagina para mostrar u ocultar botones de "Instalar app"
  if (esMovil) document.documentElement.classList.add('hm-es-movil');
  if (instalada) document.documentElement.classList.add('hm-app-instalada');

  function cerradoReciente() {
    try {
      var t = parseInt(localStorage.getItem(CLAVE) || '0', 10);
      return t && (Date.now() - t) < DIAS_OCULTO * 86400000;
    } catch (e) { return false; }
  }

  function css() {
    if (document.getElementById('hm-inst-css')) return;
    var s = document.createElement('style'); s.id = 'hm-inst-css';
    s.textContent =
      '.hm-inst{position:fixed;left:0;right:0;bottom:0;z-index:9000;background:#0d0190;color:#fff;' +
      'padding:12px max(14px,env(safe-area-inset-right,0px)) calc(12px + env(safe-area-inset-bottom,0px)) max(14px,env(safe-area-inset-left,0px));' +
      'display:flex;align-items:center;gap:12px;font-family:Manrope,system-ui,sans-serif;box-shadow:0 -4px 18px rgba(0,0,0,.18)}' +
      '.hm-inst img{width:42px;height:42px;border-radius:10px;background:#fff;flex-shrink:0}' +
      '.hm-inst .tx{flex:1;min-width:0;font-size:13px;line-height:1.3}' +
      '.hm-inst .tx b{display:block;font-size:14.5px}' +
      '.hm-inst .bi{background:#f5b301;color:#1d1d27;border:0;border-radius:9px;padding:10px 16px;font:inherit;font-weight:700;font-size:14px;cursor:pointer;flex-shrink:0}' +
      '.hm-inst .bx{background:none;border:0;color:#fff;font-size:22px;line-height:1;padding:4px 6px;cursor:pointer;opacity:.8;flex-shrink:0}' +
      'body.hm-inst-on .wsp-float{bottom:calc(var(--hm-inst-h,80px) + 14px)!important}' +
      '.hm-inst-ayuda{position:fixed;inset:0;z-index:9100;background:rgba(13,1,144,.45);display:flex;align-items:flex-end;justify-content:center}' +
      '.hm-inst-ayuda .cj{background:#fff;color:#1d1d27;width:100%;max-width:480px;border-radius:16px 16px 0 0;' +
      'padding:20px 20px calc(20px + env(safe-area-inset-bottom,0px));font-family:Manrope,system-ui,sans-serif;font-size:15px;line-height:1.5}' +
      '.hm-inst-ayuda h3{margin:0 0 10px;color:#0d0190;font-size:18px}' +
      '.hm-inst-ayuda ol{margin:0 0 14px;padding-left:20px}.hm-inst-ayuda li{margin:6px 0}' +
      '.hm-inst-ayuda .abrir-nav{display:block;text-align:center;text-decoration:none;background:#f5b301;color:#1d1d27;border-radius:9px;padding:12px;font-weight:700;margin:0 0 10px}' +
      '.hm-inst-ayuda button{width:100%;background:#0d0190;color:#fff;border:0;border-radius:9px;padding:12px;font:inherit;font-weight:700;cursor:pointer}';
    document.head.appendChild(s);
  }

  function quitarBanner() {
    var b = document.getElementById('hm-inst');
    if (b) b.remove();
    document.body.classList.remove('hm-inst-on');
  }

  function cerrar() {
    try { localStorage.setItem(CLAVE, String(Date.now())); } catch (e) {}
    quitarBanner();
  }

  // Enlace que abre esta misma pagina fuera de WhatsApp / del navegador interno de otras apps
  function enlaceNavegador() {
    var url = location.href.split('#')[0];
    if (esIOS) return url.replace(/^https:\/\//, 'x-safari-https://');   // iOS 17 o superior abre Safari
    var sinEsquema = url.replace(/^https?:\/\//, '');
    return 'intent://' + sinEsquema + '#Intent;scheme=https;package=com.android.chrome;S.browser_fallback_url=' +
           encodeURIComponent(url) + ';end';
  }

  function ayuda() {
    var pasos;
    if (esIOS) {
      pasos = '<li>Si lo has abierto desde WhatsApp o el correo, pulsa primero el bot&oacute;n amarillo <b>Abrir en Safari</b>.</li>' +
              '<li>Pulsa el bot&oacute;n <b>Compartir</b> (el cuadrado con la flecha hacia arriba).</li>' +
              '<li>Elige <b>A&ntilde;adir a pantalla de inicio</b> y pulsa <b>A&ntilde;adir</b>.</li>';
    } else {
      pasos = '<li>Si has abierto el enlace desde WhatsApp o el correo, pulsa primero el bot&oacute;n amarillo <b>Abrir en Chrome</b>.</li>' +
              '<li>En Chrome, pulsa los <b>tres puntos &#8942;</b> de arriba a la derecha.</li>' +
              '<li>Elige <b>A&ntilde;adir a pantalla de inicio</b> (o <b>Instalar aplicaci&oacute;n</b>).</li>';
    }
    var d = document.createElement('div'); d.className = 'hm-inst-ayuda';
    d.innerHTML = '<div class="cj"><h3>Tener Huevos Mateos en tu m&oacute;vil</h3><ol>' + pasos +
      '</ol><p style="margin:0 0 14px">Te quedar&aacute; un icono en la pantalla de inicio para hacer tus pedidos con un toque.</p>' +
      '<a class="abrir-nav" href="' + enlaceNavegador() + '">' + (esIOS ? 'Abrir en Safari' : 'Abrir en Chrome') + '</a>' +
      '<button type="button">Entendido</button></div>';
    d.addEventListener('click', function (e) { if (e.target === d || e.target.tagName === 'BUTTON') d.remove(); });
    document.body.appendChild(d);
  }

  // Lo usan el boton del aviso y cualquier boton "Instalar app" de las paginas
  function instalar() {
    css();
    if (eventoInstalar) {
      eventoInstalar.prompt();
      eventoInstalar.userChoice.then(function (r) {
        if (r && r.outcome === 'accepted') { quitarBanner(); document.documentElement.classList.add('hm-app-instalada'); }
        eventoInstalar = null;
      });
    } else {
      ayuda();
    }
  }
  window.hmInstalar = instalar;

  function mostrarBanner() {
    if (instalada || !esMovil || cerradoReciente() || document.getElementById('hm-inst')) return;
    css();
    var b = document.createElement('div'); b.className = 'hm-inst'; b.id = 'hm-inst';
    b.innerHTML = '<img src="assets/icono-192.png" alt="">' +
      '<div class="tx"><b>Huevos Mateos en tu m&oacute;vil</b>Tus pedidos con un toque</div>' +
      '<button type="button" class="bi">Instalar</button>' +
      '<button type="button" class="bx" aria-label="Cerrar">&times;</button>';
    b.querySelector('.bi').addEventListener('click', instalar);
    b.querySelector('.bx').addEventListener('click', cerrar);
    document.body.appendChild(b);
    document.body.classList.add('hm-inst-on');
    document.documentElement.style.setProperty('--hm-inst-h', b.offsetHeight + 'px');
  }

  // Android/Chrome avisa cuando la web se puede instalar con su propia ventana
  window.addEventListener('beforeinstallprompt', function (e) {
    e.preventDefault();          // que Chrome no muestre su propio aviso
    eventoInstalar = e;          // se usa solo cuando el cliente pulsa "Instalar app"
  });
  window.addEventListener('appinstalled', function () {
    quitarBanner(); instalada = true; document.documentElement.classList.add('hm-app-instalada');
  });

  // Ya no sale ningun aviso solo. Unica excepcion: el cliente pulso "Instalar app" en la tienda
  // sin haber entrado; tras iniciar sesion, en la tienda privada se le ofrece el boton de instalar.
  function ofrecerTrasLogin() {
    var quiere = false;
    try {
      var t = parseInt(localStorage.getItem('hm_quiere_instalar') || '0', 10);
      quiere = t && (Date.now() - t) < 7 * 86400000;      // pedido en los ultimos 7 dias
    } catch (e) {}
    if (!quiere || !window.HM_PAGINA_PRIVADA || instalada) return;
    try { localStorage.removeItem('hm_quiere_instalar'); } catch (e) {}
    try { localStorage.removeItem(CLAVE); } catch (e) {}
    mostrarBanner();
  }
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', function () { setTimeout(ofrecerTrasLogin, 1500); });
  } else {
    setTimeout(ofrecerTrasLogin, 1500);
  }
})();
