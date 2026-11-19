/* Appareils interactifs de la vitrine (moteur repris du site v2) : écrans iOS / Android, Flip 8, duo, ordinateur.
   Le thème suit celui de la page (bouton « Clair / sombre » géré par app.js). */
(function () {
  var root = document.documentElement;
  var vitrine = document.getElementById('vitrine');
  function estSombre() {
    var t = root.dataset.theme;
    return t ? t === 'dark' : matchMedia('(prefers-color-scheme: dark)').matches;
  }
  function appliquerTheme() {
    var dark = estSombre();
    if (vitrine) vitrine.classList.toggle('sombre', dark);
    document.querySelectorAll('.vp>.app').forEach(function (a) {
      a.classList.toggle('sombre', dark);
      if (a.dataset.main) a.style.background = dark ? '#1A1442' : '#5536E8';
    });
  }
  new MutationObserver(appliquerTheme).observe(root, { attributes: true, attributeFilter: ['data-theme'] });
  matchMedia('(prefers-color-scheme: dark)').addEventListener('change', appliquerTheme);

  function render(scr, name, instant) {
    var plat = scr.dataset.plat, t = document.getElementById('t-' + plat + '-' + name);
    if (!t) return;
    var vp = scr.querySelector('.vp');
    var put = function () {
      vp.innerHTML = t.innerHTML;
      var a = vp.querySelector('.app');
      if (a) {
        if (name === 'Main') a.dataset.main = '1';
        a.classList.toggle('sombre', estSombre());
        if (name === 'Main') a.style.background = estSombre() ? '#1A1442' : '#5536E8';
      }
      scr.dataset.cur = name;
      scr.setAttribute('aria-label', 'Écran interactif : ' + (t.dataset.label || name));
      vp.classList.remove('out');
    };
    if (instant || scr.dataset.cur === undefined) { put(); return; }
    if (scr.dataset.cur === name) return;
    vp.classList.add('out');
    setTimeout(put, 180);
  }
  window.rmEcrans = { render: render };
  document.querySelectorAll('.appareils .scr').forEach(function (s) { render(s, s.dataset.start, true); });
  var cover = document.getElementById('t-cover');
  document.querySelectorAll('.appareils .cover-vp').forEach(function (v) { if (cover) v.innerHTML = cover.innerHTML; });

  // Navigation à l'intérieur des écrans : on reste dans le téléphone (pas d'écran de chargement de page)
  document.addEventListener('click', function (ev) {
    var a = ev.target.closest('.appareils .vp a');
    if (!a) return;
    ev.preventDefault(); ev.stopPropagation();
    var m = (a.getAttribute('href') || '').match(/^([\w-]+?)--/);
    if (m) render(a.closest('.scr'), m[1]);
  }, true);

  // Ouvrir / refermer le Flip
  function basculer(box) {
    var ouvert = box.dataset.state !== 'ouvert';
    box.dataset.state = ouvert ? 'ouvert' : 'plie';
    var btn = box.querySelector('[data-toggle-fold]');
    if (btn) btn.textContent = ouvert ? 'Refermer le Flip' : 'Ouvrir le Flip';
    var vu = box.querySelector(ouvert ? '.flipo' : '.flipp');
    if (vu) { vu.classList.remove('opening'); void vu.offsetWidth; vu.classList.add('opening'); }
  }
  document.addEventListener('click', function (ev) {
    var b = ev.target.closest('.appareils [data-toggle-fold], .appareils [data-unfold]');
    if (b) basculer(b.closest('.foldable'));
  });

  // Onglets d'appareils
  var tabs = [].slice.call(document.querySelectorAll('.ap-tabs [role=tab]'));
  function choisir(k) {
    tabs.forEach(function (t) {
      var on = t.dataset.tab === k;
      t.setAttribute('aria-selected', on); t.tabIndex = on ? 0 : -1;
      document.getElementById('pan-' + t.dataset.tab).hidden = !on;
    });
    document.querySelectorAll('.ap-txt p').forEach(function (p) { p.hidden = p.dataset.for !== k; });
  }
  tabs.forEach(function (t, i) {
    t.addEventListener('click', function () { choisir(t.dataset.tab); });
    t.addEventListener('keydown', function (e) {
      if (e.key !== 'ArrowRight' && e.key !== 'ArrowLeft') return;
      var n = tabs[(i + (e.key === 'ArrowRight' ? 1 : tabs.length - 1)) % tabs.length];
      n.focus(); choisir(n.dataset.tab);
    });
  });
  var reset = document.querySelector('.appareils [data-reset]');
  if (reset) reset.addEventListener('click', function () {
    document.querySelectorAll('.appareils .scr').forEach(function (s) { render(s, s.dataset.start); });
  });

  // Ordinateur : l'écran affiché suit la largeur disponible ; changement de page avec barre de progression
  var frame = document.querySelector('[data-pc-frame]'), url = document.querySelector('[data-pc-url]');
  function ajusterPC() {
    var vue = frame && frame.parentElement;
    if (vue) vue.style.setProperty('--pcs', (vue.clientWidth / 1440).toFixed(4));
  }
  window.addEventListener('resize', ajusterPC);
  new ResizeObserver(ajusterPC).observe(document.querySelector('.appareils .ap-stage'));
  document.querySelectorAll('[data-pc]').forEach(function (b) {
    b.addEventListener('click', function () {
      document.querySelectorAll('[data-pc]').forEach(function (x) { x.classList.toggle('on', x === b); });
      var bar = document.getElementById('rm-bar');
      if (bar) { bar.classList.add('on'); bar.style.width = '60%'; }
      frame.src = b.dataset.pc; if (url) url.textContent = b.dataset.url;
    });
  });
  if (frame) frame.addEventListener('load', function () {
    var bar = document.getElementById('rm-bar');
    if (bar) { bar.style.width = '100%'; setTimeout(function () { bar.classList.remove('on'); bar.style.width = '0'; }, 250); }
  });

  appliquerTheme(); ajusterPC();
  // L'écran de lancement passe seul à l'accueil
  setTimeout(function () {
    document.querySelectorAll('.appareils .scr').forEach(function (s) { if (s.dataset.cur === 'Main') render(s, '01-accueil'); });
  }, 2600);
})();
