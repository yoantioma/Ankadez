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
  // v3 : le score est déclaré, il oriente sans donner de grade ; on montre la phrase et les pièces manquantes
  var PHRASES = [[80, 'Votre dossier est presque prêt pour un financeur.'], [60, 'Vous avez fait plus de la moitié du chemin.'],
                 [40, 'Vous êtes à la moitié du chemin.'], [20, 'Les bases sont posées.'], [0, 'Tout commence ici.']];
  function maj() {
    var total = 0, rep = 0, n = form.querySelectorAll('fieldset').length, manque = [];
    form.querySelectorAll('input:checked').forEach(function (i) { total += +i.dataset.poids; rep++; if (i.value === '0') manque.push(i.dataset.piece); });
    out.score.innerHTML = total + '<small>/100</small>';
    out.barre.style.width = total + '%';
    out.grade.textContent = rep ? PHRASES.filter(function (p) { return total >= p[0]; })[0][1] : 'Répondez aux questions';
    var reste = n - rep;
    if (reste) out.texte.textContent = reste + (reste > 1 ? ' questions restantes.' : ' question restante.');
    else if (manque.length) out.texte.textContent = 'À rassembler d’abord : ' + manque.slice(0, 3).join(' ; ') + '.';
    else out.texte.textContent = 'Tout est en place : créez votre passeport pour le faire vérifier.';
  }
  form.addEventListener('change', maj);
})();
