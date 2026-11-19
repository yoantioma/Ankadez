/* Accueil : thème, apparition des blocs, écrans du récit qui suivent la lecture, diagnostic express. */
(function () {
  var root = document.documentElement;
  root.classList.add('js');
  if (!root.dataset.theme) {
    var t = null;
    try { t = localStorage.getItem('rm-theme'); } catch (e) {}
    root.dataset.theme = t || (matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light');
  }

  var calme = matchMedia('(prefers-reduced-motion: reduce)').matches;
  var rises = document.querySelectorAll('.rv-rise');
  if (calme || !('IntersectionObserver' in window)) {
    rises.forEach(function (el) { el.classList.add('vis'); });
  } else {
    var io = new IntersectionObserver(function (es) {
      es.forEach(function (e) { if (e.isIntersecting) { e.target.classList.add('vis'); io.unobserve(e.target); } });
    }, { rootMargin: '0px 0px -10% 0px' });
    rises.forEach(function (el) { io.observe(el); });
  }

  // Chaque étape du récit affiche son écran dans le téléphone de la colonne
  function afficher(step) {
    var story = step.closest('.rv-story');
    if (!story || !window.rmEcrans) return;
    story.querySelectorAll('.rv-step').forEach(function (s) { s.classList.toggle('on', s === step); });
    var scrs = story.querySelectorAll('.rv-devcol .scr');
    if (step.dataset.s && scrs[0]) window.rmEcrans.render(scrs[0], step.dataset.s);
    if (step.dataset.a && scrs[0]) window.rmEcrans.render(scrs[0], step.dataset.a);
    if (step.dataset.b && scrs[1]) window.rmEcrans.render(scrs[1], step.dataset.b);
  }
  if ('IntersectionObserver' in window) {
    var so = new IntersectionObserver(function (es) {
      es.forEach(function (e) { if (e.isIntersecting) afficher(e.target); });
    }, { rootMargin: '-45% 0px -45% 0px' });
    document.querySelectorAll('.rv-step').forEach(function (s) { so.observe(s); });
  }

  // Diagnostic express : tout reste dans le navigateur
  var form = document.getElementById('diag');
  if (!form) return;
  var out = {
    score: document.querySelector('[data-diag-score]'), barre: document.querySelector('[data-diag-barre]'),
    grade: document.querySelector('[data-diag-grade]'), texte: document.querySelector('[data-diag-texte]')
  };
  var PALIERS = [[90, 'Institutional-Ready'], [75, 'Série A / Growth-Ready'], [60, 'Investment-Ready'], [40, 'Pré-Ready'], [0, 'Structuring']];
  function maj() {
    var total = 0, rep = 0, n = form.querySelectorAll('fieldset').length;
    form.querySelectorAll('input:checked').forEach(function (i) { total += +i.value; rep++; });
    var s = Math.min(total, 59);
    out.score.innerHTML = s + '<small>/100</small>';
    out.barre.style.width = s + '%';
    var g = PALIERS.filter(function (p) { return s >= p[0]; })[0][1];
    out.grade.textContent = rep ? g : 'Répondez aux questions';
    var reste = n - rep;
    if (reste) out.texte.textContent = reste + (reste > 1 ? ' questions restantes.' : ' question restante.');
    else if (total > 59) out.texte.textContent = 'Vos réponses valent ' + total + ' points. Sans pièce déposée, le score reste plafonné à 59 : déposez vos documents pour aller plus haut.';
    else if (s >= 40) out.texte.textContent = 'Les bases sont là. Il reste à compléter le dossier avant de rencontrer un financeur.';
    else out.texte.textContent = 'Commencez par les états financiers et la DSF : ce sont les premières pièces qu’une banque demande.';
  }
  form.addEventListener('change', maj);
})();
