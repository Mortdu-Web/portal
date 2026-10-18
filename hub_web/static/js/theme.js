// Thème clair / sombre.
// Chargé dans le <head>, SANS defer : il pose data-theme avant le premier affichage (pas de flash).
(() => {
  const KEY = 'theme';
  const root = document.documentElement;
  const media = window.matchMedia('(prefers-color-scheme: light)');

  const stored = () => {
    try { const v = localStorage.getItem(KEY); return v === 'light' || v === 'dark' ? v : null; }
    catch { return null; }                       // stockage bloqué : on suit l'OS
  };
  const system = () => (media.matches ? 'light' : 'dark');
  const apply = (theme) => {
    root.dataset.theme = theme;
    const btn = document.getElementById('theme-toggle');
    if (btn) {
      const label = theme === 'dark' ? 'Passer en mode clair' : 'Passer en mode sombre';
      btn.setAttribute('aria-label', label);
      btn.title = label;
    }
  };

  apply(stored() || system());

  document.addEventListener('DOMContentLoaded', () => {
    apply(root.dataset.theme);                   // met à jour l'étiquette du bouton
    const btn = document.getElementById('theme-toggle');
    if (!btn) return;
    btn.addEventListener('click', () => {
      const next = root.dataset.theme === 'dark' ? 'light' : 'dark';
      try { localStorage.setItem(KEY, next); } catch { /* choix non mémorisé */ }
      apply(next);
    });
  });

  // Tant que l'utilisateur n'a rien choisi, on suit les changements de l'OS.
  media.addEventListener('change', () => { if (!stored()) apply(system()); });
})();
