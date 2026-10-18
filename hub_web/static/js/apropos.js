(function () {
  const opener = document.getElementById('cv-open');
  const modal  = document.getElementById('cv-modal');
  const frame  = document.getElementById('cv-frame');
  const close  = document.getElementById('cv-close');

  if (!opener || !modal || !frame) return;

  function openModal(e) {
    e.preventDefault();                       // sans JS, le lien ouvre le PDF dans un onglet
    if (!frame.getAttribute('src')) {
      frame.src = frame.dataset.src;          // le PDF n'est chargé qu'à la première ouverture
    }
    modal.showModal();
    document.body.style.overflow = 'hidden';
  }

  opener.addEventListener('click', openModal);
  close.addEventListener('click', () => modal.close());

  // Clic sur le fond sombre = fermeture
  modal.addEventListener('click', (e) => {
    if (e.target === modal) modal.close();
  });

  // Appelé aussi par la touche Échap
  modal.addEventListener('close', () => {
    document.body.style.overflow = '';
  });
})();