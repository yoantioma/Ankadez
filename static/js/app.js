/* ReadyMatch · écrans de chargement, thème, messages.
   - Changement de page (lien ou formulaire) : barre de progression + écran de chargement plein.
   - Requête asynchrone (filtres) : barre de progression + cartes squelettes dans la zone mise à jour. */
(function () {
  const bar = document.getElementById('rm-bar');
  const loader = document.getElementById('rm-loader');
  const msg = loader ? loader.querySelector('.ld-msg') : null;
  let timer = null, prog = 0, slow = null;

  function startBar() {
    prog = 8; bar.classList.add('on'); bar.style.width = prog + '%';
    clearInterval(timer);
    timer = setInterval(() => { prog = Math.min(prog + (90 - prog) * 0.12, 90); bar.style.width = prog + '%'; }, 180);
  }
  function endBar() {
    clearInterval(timer); bar.style.width = '100%';
    setTimeout(() => { bar.classList.remove('on'); bar.style.width = '0'; }, 280);
  }
  function showLoader(text) {
    startBar();
    if (msg && text) msg.textContent = text;
    clearTimeout(slow);
    // L'écran plein n'apparaît qu'au-delà de 150 ms, pour ne pas clignoter sur les pages rapides.
    slow = setTimeout(() => loader && loader.classList.add('on'), 150);
  }
  function hideLoader() { clearTimeout(slow); loader && loader.classList.remove('on'); endBar(); }
  window.rmLoader = { show: showLoader, hide: hideLoader };

  // Liens internes
  document.addEventListener('click', (e) => {
    const a = e.target.closest('a[href]');
    if (!a || e.defaultPrevented || e.button !== 0 || e.metaKey || e.ctrlKey || e.shiftKey || e.altKey) return;
    if (a.target === '_blank' || a.hasAttribute('download') || a.dataset.noLoader !== undefined) return;
    const url = new URL(a.href, location.href);
    if (url.origin !== location.origin || (url.pathname === location.pathname && url.hash)) return;
    showLoader(a.dataset.loader || 'Chargement…');
  });

  // Formulaires (sauf ceux gérés en asynchrone)
  document.addEventListener('submit', (e) => {
    const f = e.target;
    if (f.dataset.async !== undefined || e.defaultPrevented) return;
    const b = e.submitter || f.querySelector('[type=submit]');
    if (b) b.classList.add('is-loading');
    showLoader(f.dataset.loader || 'Enregistrement…');
  });

  // Retour arrière (cache du navigateur) : on retire l'écran de chargement
  window.addEventListener('pageshow', () => { hideLoader(); document.querySelectorAll('.is-loading').forEach(b => b.classList.remove('is-loading')); });

  // Filtres asynchrones : <form data-async data-target="#zone" data-skeleton="cartes">
  function skeleton(kind, n) {
    const one = kind === 'liste'
      ? '<div class="skel-card"><div class="skel" style="height:44px;width:44px;border-radius:13px"></div><div class="skel" style="height:14px;width:70%"></div><div class="skel" style="height:12px;width:45%"></div></div>'
      : '<div class="skel-card"><div class="skel" style="height:120px"></div><div class="skel" style="height:16px;width:60%"></div><div class="skel" style="height:12px;width:85%"></div><div class="skel" style="height:36px;border-radius:999px"></div></div>';
    return '<div class="g g3">' + one.repeat(n || 6) + '</div>';
  }
  async function loadInto(form, url) {
    const zone = document.querySelector(form.dataset.target);
    if (!zone) return;
    startBar();
    zone.innerHTML = skeleton(form.dataset.skeleton, 6);
    try {
      const r = await fetch(url, { headers: { 'X-Requested-With': 'fetch' } });
      if (!r.ok) throw new Error(r.status);
      zone.innerHTML = await r.text();
      history.replaceState(null, '', url.replace(/([?&])partiel=1&?/, '$1').replace(/[?&]$/, ''));
    } catch (err) {
      zone.innerHTML = '<div class="empty"><b>Le chargement a échoué.</b><p>Vérifiez votre connexion puis réessayez.</p></div>';
    } finally { endBar(); }
  }
  document.querySelectorAll('form[data-async]').forEach((form) => {
    let t = null;
    const go = () => { const p = new URLSearchParams(new FormData(form)); loadInto(form, form.action.split('?')[0] + '?' + p.toString()); };
    form.addEventListener('submit', (e) => { e.preventDefault(); go(); });
    form.addEventListener('change', go);
    form.querySelectorAll('input[type=search]').forEach(i => i.addEventListener('input', () => { clearTimeout(t); t = setTimeout(go, 350); }));
  });
  // Pagination dans une zone asynchrone
  document.addEventListener('click', (e) => {
    const a = e.target.closest('[data-async-zone] .pag a');
    if (!a) return;
    e.preventDefault(); e.stopPropagation();
    const zone = a.closest('[data-async-zone]');
    const form = document.querySelector(`form[data-target="#${zone.id}"]`);
    if (form) loadInto(form, a.href);
  }, true);

  // Thème clair / sombre (préférence locale)
  const root = document.documentElement;
  try { const t = localStorage.getItem('rm-theme'); if (t) root.dataset.theme = t; } catch (e) {}
  document.querySelectorAll('[data-theme-toggle]').forEach((b) => b.addEventListener('click', () => {
    const dark = root.dataset.theme ? root.dataset.theme === 'dark' : matchMedia('(prefers-color-scheme: dark)').matches;
    root.dataset.theme = dark ? 'light' : 'dark';
    try { localStorage.setItem('rm-theme', root.dataset.theme); } catch (e) {}
  }));

  // Messages : fermeture et disparition automatique
  document.querySelectorAll('.toast').forEach((t) => {
    t.querySelector('button')?.addEventListener('click', () => t.remove());
    setTimeout(() => t.remove(), 7000);
  });

  // Confirmation des actions sensibles
  document.addEventListener('submit', (e) => {
    const c = e.target.dataset.confirm;
    if (c && !confirm(c)) { e.preventDefault(); e.stopImmediatePropagation(); hideLoader(); }
  }, true);
})();
